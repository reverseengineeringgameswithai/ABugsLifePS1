#!/usr/bin/env python3
"""F11: is CLIMBING a discrete mechanic, or ordinary movement up geometry?

The row's name lists climbing as one of its four mechanics. Canon
(SYS_player_action_state_laws) documents the player state word 0x800A6580 as "the real
player state selector", with an observed domain of:

    0 grounded/idle   1 airborne   2 swing-release launch
    4 slam/dive       5 landing/skid AND swing-attached   6 handstand dismount

There is no climb state in that domain. So the question has a sharp form: across a full
run of the stage whose name claims climbing, does the state word ever take a value
OUTSIDE the documented set?

  * a new value  -> climbing is a discrete state, and this finds it
  * no new value -> climbing is not a discrete mechanic here; it is ordinary movement
                    over geometry, and the row's "climbing" is level design not code

Either answer bounds the row's last open mechanic. The negative is the more likely one
and is just as useful, provided it is stated as what it is: the state word carries no
climb state, NOT "there is no climbing".

Also polls Flik's Y so the climb windows are visible alongside the states, and watches
`grounded` (0x800A6582), which Canon says is 0 while airborne/mounted/attached -- a climb
that used an attachment mechanism would show there.

    tools/phase4_f11_climbing.py --port 23780
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
STATE_WORD = 0x800A6580
GROUNDED = 0x800A6582
FLIK_Y = 0x800A6504
DOCUMENTED = {0, 1, 2, 4, 5, 6}
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
    ap.add_argument("--port", type=int, default=23780)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_climbing.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f11-climb")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "F11_the_tree",
        "question": "is climbing a discrete player state, or ordinary movement?",
        "movie": str(args.movie),
        "documented_state_domain": sorted(DOCUMENTED),
        "basis": "SYS_player_action_state_laws: 0x800A6580 is the real state selector",
        "caveat": ("a negative here means THE STATE WORD carries no climb state -- not "
                   "that the stage has no climbing"),
    }
    watch, y_samples = {}, []
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
        for a, n, lab in ((STATE_WORD, 2, "player state word"),
                          (GROUNDED, 2, "grounded flag")):
            c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": n,
                                          "type": "write", "max_events": 200000})
            watch[a] = lab

        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        while time.time() - began < args.timeout:
            time.sleep(0.4)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
                y = s32(int.from_bytes(bytes.fromhex(c.call(
                    "debugger.readMemory",
                    {"address": "0x%08x" % FLIK_Y, "length": 4})["hex"]), "little"))
                y_samples.append({"i": idx, "y": y})
            except Exception:
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 25:
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
            r["seq"].append({"f": e.get("frame"), "pc": pc, "v": v & 0xFFFF})

    sw = by.get(STATE_WORD, {"seq": [], "writers": {}})
    seen = sorted({s["v"] for s in sw["seq"]})
    novel = sorted(set(seen) - DOCUMENTED)

    out["state_word"] = {
        "writes": len(sw["seq"]),
        "distinct_values": seen,
        "values_outside_documented_domain": novel,
        "writer_pcs": sorted(sw["writers"].items(), key=lambda kv: -kv[1])[:8],
        "first_frame_per_value": {str(v): next(s["f"] for s in sw["seq"] if s["v"] == v)
                                  for v in seen},
    }
    g = by.get(GROUNDED, {"seq": [], "writers": {}})
    out["grounded"] = {
        "writes": len(g["seq"]),
        "distinct_values": sorted({s["v"] for s in g["seq"]}),
        "writer_pcs": sorted(g["writers"].items(), key=lambda kv: -kv[1])[:6],
    }
    # coarse Y envelope, to show the climbs exist at all
    ys = [s["y"] for s in y_samples if s["y"] is not None]
    out["flik_y"] = {"samples": len(ys), "min": min(ys) if ys else None,
                     "max": max(ys) if ys else None,
                     "timeline": y_samples[::max(1, len(y_samples) // 40)][:40]}

    if novel:
        out["verdict"] = ("CLIMBING MAY BE DISCRETE: the state word took value(s) %s "
                          "outside the documented domain %s -- investigate those."
                          % (novel, sorted(DOCUMENTED)))
    else:
        out["verdict"] = (
            "NO CLIMB STATE. Across %d writes the state word only ever took %s, all "
            "within the documented domain. Climbing in this stage is not a discrete "
            "player state -- it is ordinary movement over geometry. ⚠️ This bounds THE "
            "STATE WORD only; it does not prove the stage has no climbing, and a climb "
            "implemented purely as collision/geometry would look exactly like this."
            % (len(sw["seq"]), seen))

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"frames": out.get("frames"), "ring_truncated": out.get("ring_truncated"),
                      "state_word": {k: out["state_word"][k] for k in
                                     ("writes", "distinct_values",
                                      "values_outside_documented_domain",
                                      "first_frame_per_value")},
                      "grounded": out["grounded"],
                      "flik_y_range": [out["flik_y"]["min"], out["flik_y"]["max"]],
                      "verdict": out["verdict"]}, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
