#!/usr/bin/env python3
"""F11: characterise the stage overlay's ENTIRE state surface against a full run.

A dataflow scan of LEVEL02/LEVEL1.BIN (the blob that actually runs scene 12) shows the
overlay owns exactly ELEVEN state words, 0x800B4A24..0x800B4A4C. Two are already known:

    0x800B4A48   scouts remaining (= 5 - found)
    0x800B4A4C   the post-find / cue timer

This watches all eleven across the operator's full Any% run, with writer PCs and value
timelines, so the rest of the stage's state machine is mapped rather than guessed at. The
row's remaining named mechanics are ACORNS and CLIMBING; if either has overlay state, it
is in this block.

⚠️ This is a DISCOVERY pass, not a binding pass. A word that moves during a run is a
candidate; naming it needs its writer read and, for anything behavioural, a correlation
the run can actually support.

    tools/phase4_f11_overlay_state.py --port 23770
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STATE_LO, STATE_HI = 0x800B4A24, 0x800B4A50          # 11 words
KNOWN = {0x800B4A48: "scouts remaining (5 - found)", 0x800B4A4C: "cue/post-find timer"}
GOAL_LATCH, SCENE_ID = 0x800823A0, 0x80082504
DEFAULT_MOVIE = "movies/Phase4/Interpreter/Any% Runs/LEVEL11_THETREE.movie.json"


def s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


def launch(port, token, disc, cfg, log, launcher, cwd, mode):
    subprocess.run(["rm", "-rf", str(cfg)], check=False)
    with Path(log).open("w") as fh:
        subprocess.run(["bash", str(launcher), "--execution-mode", mode,
                        "--config-dir", str(cfg), "--port", str(port), "--token", token,
                        "--disc", str(disc)], cwd=str(cwd), stdout=fh, stderr=fh,
                       check=False)
    text = Path(log).read_text()
    if "READY" not in text:
        raise SystemExit("launch failed:\n" + text[-800:])
    return text.split("pid=")[1].split()[0]


def collect(c):
    out, off = [], 0
    while True:
        page = c.call("accessLog.get", {"offset": off, "limit": 10000})
        got = page.get("events") or []
        out.extend(got)
        if len(got) < 10000:
            return out, bool(page.get("truncated")), page.get("total")
        off += len(got)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path, default=ROOT / DEFAULT_MOVIE)
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23770)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_overlay_state.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f11-state")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "F11_the_tree",
        "question": "map the stage overlay's entire state surface; look for acorn state",
        "movie": str(args.movie),
        "state_block": "0x%08X..0x%08X (11 words)" % (STATE_LO, STATE_HI - 4),
        "basis": ("dataflow scan of LEVEL02/LEVEL1.BIN -- these are ALL the absolute "
                  "globals in 0x800B3000-0x800B6000 the overlay stores to"),
        "caveat": ("DISCOVERY pass. A word that moves is a candidate, not a binding; "
                   "naming one needs its writer read."),
    }
    watch = {}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(1200)
        st = c.call("movie.load", {"path": str(args.movie)})
        out["frames"] = st.get("frame_count")
        if not c.call("movie.startPlayback", {"load_start_state": True}).get("playing"):
            out["error"] = "playback refused"
            print(json.dumps(out, indent=1))
            return 1

        c.call("accessLog.clear", {})
        for a in range(STATE_LO, STATE_HI, 4):
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": 4,
                                          "type": "write", "max_events": 60000})
            watch[a] = KNOWN.get(a, "unknown")
        for a, n, lab in ((GOAL_LATCH, 2, "goal latch"), (SCENE_ID, 4, "scene id")):
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": n,
                                          "type": "write", "max_events": 60000})
            watch[a] = lab

        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < args.timeout:
            time.sleep(0.5)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 20:
                    break
            else:
                stalls = 0
            last = idx
        out["final_playback_index"] = last
        events, truncated, total = collect(c)
        out["event_total"] = total
        out["ring_truncated"] = truncated
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    by = {}
    for e in events:
        a = int(str(e.get("address", "0")), 16) & 0x1FFFFFFF | 0x80000000
        b0 = max((w for w in watch if w <= a), default=None)
        if b0 is None:
            continue
        r = by.setdefault(b0, {"label": watch[b0], "seq": [], "writers": {}})
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        r["writers"][pc] = r["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None:
            r["seq"].append({"f": e.get("frame"), "v": s32(v & 0xFFFFFFFF)})

    fields = {}
    for a in sorted(by):
        r = by[a]
        vals = [x["v"] for x in r["seq"]]
        trans = [x for i, x in enumerate(r["seq"]) if i == 0 or x["v"] != r["seq"][i-1]["v"]]
        fields["0x%08X" % a] = {
            "label": r["label"],
            "writes": len(r["seq"]),
            "distinct_values": len(set(vals)),
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
            "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:5],
            "transitions": [{"f": t["f"], "v": t["v"]} for t in trans][:30],
            "transition_count": len(trans),
        }
    out["fields"] = fields
    out["silent"] = ["0x%08X" % a for a in watch if a not in by]

    # a counter-shaped word: small bounded values, several distinct steps
    counters = {k: v for k, v in fields.items()
                if v["max"] is not None and 0 <= v["min"] and v["max"] <= 64
                and v["distinct_values"] >= 3}
    out["counter_shaped"] = counters
    out["note"] = ("'counter_shaped' is a HEURISTIC shortlist (small bounded range, >=3 "
                   "distinct values). It is where to look next, not a set of findings.")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"frames": out.get("frames"), "ring_truncated": out.get("ring_truncated"),
                      "silent": out["silent"],
                      "fields": {k: {kk: v[kk] for kk in
                                     ("label", "writes", "distinct_values", "min", "max",
                                      "transition_count")}
                                 for k, v in fields.items()}}, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
