#!/usr/bin/env python3
"""F11 (The Tree): locate the scout-found progression state by diffing the five saves.

The row's own `next` is "Diff the LEVEL11_1-5 saves to locate the scout-found progression
state." The five saves are numbered snapshots of the same stage at successive points, so
the state that tracks progress should move MONOTONICALLY across 1 -> 5 while almost
everything else (position, timers, RNG, animation phase) does not.

Method: load each save into one isolated instance, dump all 2 MiB of main RAM, and rank
addresses by how progression-shaped they are:

  * strictly monotonic across all five saves (increasing or decreasing)
  * small, bounded values (a counter, not a coordinate or a pointer)
  * a small total span

⚠️ This finds CANDIDATES, not the answer. A monotonic value can easily be a frame counter,
an elapsed-time field, or anything else that happens to grow while the player plays. The
output is a ranked shortlist to be confirmed by finding its writer -- not a binding.

    tools/phase4_f11_scout_progression.py --port 23740
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAM_BASE, RAM_SIZE = 0x80000000, 0x200000
SAVES = ["LEVEL11_1.sav", "LEVEL11_2.sav", "LEVEL11_3.sav", "LEVEL11_4.sav",
         "LEVEL11_5.sav"]


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23740)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_f11_scout_progression.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/f11")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {"row": "F11_the_tree", "saves": SAVES,
           "method": ("load each save, dump 2 MiB of RAM, rank addresses that move "
                      "monotonically across 1->5 with small bounded values"),
           "caveat": ("candidates only -- a monotonic value can be a frame/elapsed "
                      "counter. Confirm by finding the writer before binding anything.")}
    dumps = []
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)
        for name in SAVES:
            p = ROOT / name
            if not p.exists():
                out["error"] = "missing save: %s" % name
                print(json.dumps(out, indent=1))
                return 1
            # ⚠️ loadState hard-crashes if a different disc is mounted than the state was
            # made on -- this instance is launched on the pristine disc the saves used.
            c.call("emulator.loadState", {"path": str(p), "pause_after_load": True})
            time.sleep(1.0)
            blob = bytearray()
            CH = 0x20000
            for off in range(0, RAM_SIZE, CH):
                hexs = c.call("debugger.readMemory",
                              {"address": "0x%08x" % (RAM_BASE + off),
                               "length": CH})["hex"]
                blob += bytes.fromhex(hexs)
            dumps.append(bytes(blob))
            st = c.call("debugger.status", {})
            out.setdefault("per_save", []).append(
                {"save": name, "pc": st.get("pc"), "frame": st.get("frame"),
                 "bytes": len(blob)})
    finally:
        subprocess.run(["kill", pid], check=False)
        time.sleep(2)

    if len(dumps) != len(SAVES):
        out["error"] = "only %d dumps" % len(dumps)
        print(json.dumps(out, indent=1))
        return 1

    # scene id sanity: all five should be the same stage
    def u32(b, a):
        return struct.unpack_from("<I", b, a - RAM_BASE)[0]
    out["scene_ids"] = [u32(d, 0x80082504) for d in dumps]

    cands = {}
    for width, fmt, step in ((2, "<H", 2), (4, "<I", 4)):
        for a in range(0, RAM_SIZE - width, step):
            vals = [struct.unpack_from(fmt, d, a)[0] for d in dumps]
            if len(set(vals)) < len(vals):
                continue                       # needs to change at EVERY step
            inc = all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
            dec = all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))
            if not (inc or dec):
                continue
            span = max(vals) - min(vals)
            if max(vals) > 0x400 or span > 0x100:
                continue                       # counters, not coords/pointers/timers
            cands["0x%08X" % (RAM_BASE + a)] = {
                "width": width, "values": vals,
                "direction": "increasing" if inc else "decreasing", "span": span}

    ranked = sorted(cands.items(), key=lambda kv: (kv[1]["span"], max(kv[1]["values"])))
    out["candidate_count"] = len(ranked)
    out["candidates"] = [{"addr": k, **v} for k, v in ranked[:40]]

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"scene_ids": out["scene_ids"],
                      "per_save": out.get("per_save"),
                      "candidate_count": out["candidate_count"],
                      "top": out["candidates"][:15]}, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
