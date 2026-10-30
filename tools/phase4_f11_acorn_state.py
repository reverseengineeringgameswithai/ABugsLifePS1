#!/usr/bin/env python3
"""F11: what the acorn state machine downstream of 0x800B41A8 actually does.

Static read of LEVEL02/LEVEL1.BIN, 0x800B41A8..0x800B4220 (a0 = acorn + 0x62):

    lw   v0,-6(a0)                  ; the word at acorn+0x5C
    andi v0,v0,0x5000
    bne  v0,0x1000 -> 0x800B4224    ; require marked (0x1000) AND 0x4000 CLEAR
    lh   v0,0x0C(a0)                ; acorn+0x6E (HP)
    beq  v0,zero  -> 0x800B4224     ; already retired -> skip
    ... walk the live actor table 0x80090748 looking for this acorn ...
    beq  s3,-1    -> 0x800B4224     ; FOUND in the table -> skip
    sh   zero,0x0C(a0)              ; acorn+0x6E := 0     <- HP zeroed
    sh   zero,-8(a0)                ; acorn+0x5A := 0
    sh   5,0(a0)                    ; acorn+0x62 := 5

So the machine is a RETIREMENT path: an acorn that has been marked and is no longer
present in the live actor table is retired -- HP zeroed and +0x62 set to 5.

This watches all three written fields across all seven acorns, so the retirement is
measured rather than read off the branch. The prediction is specific and falsifiable:
+0x6E -> 0 and +0x62 -> 5 should occur together, from PCs 0x800B4218 and 0x800B4220.

    tools/phase4_f11_acorn_state.py --port 23800
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
ACORN0, STRIDE, N = 0x800A14B4, 0x84, 7
FIELDS = [(0x5A, "plus5A"), (0x62, "plus62"), (0x6E, "hp")]
RETIRE_HP_PC, RETIRE_62_PC = "0x800b4218", "0x800b4220"
DEFAULT_MOVIE = "movies/Phase4/Interpreter/Any% Runs/LEVEL11_THETREE.movie.json"


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


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
    ap.add_argument("--port", type=int, default=23800)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_acorn_state.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f11-acornstate")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "F11_the_tree",
        "question": "what the acorn state machine downstream of 0x800B41A8 does",
        "movie": str(args.movie),
        "static_prediction": ("an acorn that is MARKED (flags 0x1000 set, 0x4000 clear), "
                              "has nonzero HP, and is NOT present in the live actor "
                              "table 0x80090748 gets RETIRED: +0x6E := 0 (PC 0x800B4218), "
                              "+0x5A := 0 (0x800B421C), +0x62 := 5 (0x800B4220)"),
        "falsifiable_as": ("if no acorn's +0x6E goes to 0 from 0x800B4218, or +0x62 "
                           "never becomes 5 from 0x800B4220, the retirement reading is "
                           "wrong"),
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
        for n in range(N):
            for off, lab in FIELDS:
                a = ACORN0 + n * STRIDE + off
                c.call("accessLog.addWatch", {"address": "0x%08x" % a, "length": 2,
                                              "type": "write", "max_events": 60000})
                watch[a] = "acorn%d.%s" % (n, lab)

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
            r["seq"].append({"f": e.get("frame"), "pc": pc, "v": s16(v & 0xFFFF)})

    out["by_field"] = {
        "0x%08X" % a: {"label": r["label"], "writes": len(r["seq"]),
                       "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:5],
                       "distinct_values": sorted({x["v"] for x in r["seq"]})[:12]}
        for a, r in sorted(by.items())
    }

    retire_hp = [{"acorn": (a - ACORN0) // STRIDE, "f": x["f"]}
                 for a, r in by.items() if r["label"].endswith(".hp")
                 for x in r["seq"] if x["pc"] == RETIRE_HP_PC]
    retire_62 = [{"acorn": (a - ACORN0) // STRIDE, "f": x["f"], "v": x["v"]}
                 for a, r in by.items() if r["label"].endswith(".plus62")
                 for x in r["seq"] if x["pc"] == RETIRE_62_PC]

    out["findings"] = {
        "retirement_hp_zero_events": sorted(retire_hp, key=lambda e: e["f"])[:20],
        "retirement_plus62_events": sorted(retire_62, key=lambda e: e["f"])[:20],
        "acorns_retired": sorted({e["acorn"] for e in retire_hp}),
        "plus62_values_at_retire": sorted({e["v"] for e in retire_62}),
    }
    if retire_hp and retire_62 and set(out["findings"]["plus62_values_at_retire"]) == {5}:
        out["findings"]["verdict"] = (
            "CONFIRMED: %d retirement(s) across acorn(s) %s -- 0x800B4218 zeroes +0x6E "
            "and 0x800B4220 writes +0x62 = 5, exactly as the static read predicted. The "
            "acorn state machine is a RETIREMENT path for a marked acorn that has left "
            "the live actor table."
            % (len(retire_hp), out["findings"]["acorns_retired"]))
    elif not retire_hp:
        out["findings"]["verdict"] = (
            "NOT OBSERVED: no acorn was retired via 0x800B4218 in this run, so the "
            "retirement reading is UNCONFIRMED -- the branch's table-absence condition "
            "was never met here.")
    else:
        out["findings"]["verdict"] = (
            "PARTIAL: hp-zero events %d, +0x62 events %d, +0x62 values %s -- does not "
            "match the predicted pairing." % (len(retire_hp), len(retire_62),
                                              out["findings"]["plus62_values_at_retire"]))

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"frames": out.get("frames"),
                      "ring_truncated": out.get("ring_truncated"),
                      "findings": out["findings"]}, indent=1)[:2200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
