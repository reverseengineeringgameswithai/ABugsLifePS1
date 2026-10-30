#!/usr/bin/env python3
"""F02 Tunnels: census the live actor pool in stage 2 and find the falling debris.

THE ROW ITEM
------------
F02_tunnels ("Stage 2 Tunnels: gates + falling debris") is unstarted -- no
experiment, no artifact, no Canon. Its registry `next` reads: "Capture
falling-debris actors in stage 2; bind them to their spawner and damage class."

This does the capture half: enumerate the live actor pool from a stage-2 save
state and report every occupied slot with the fields that identify a species and
distinguish a hazard from scenery.

POOL LAYOUT, inherited rather than rediscovered:
  base 0x8009FD80, stride 0x84  (0x8009FE04 is SLOT 1, not the base -- the earlier
  census enumerated from slot 1 and that off-by-one has bitten this project before)
  +0x7C  species callback           +0x5C  flags word
  +0x6E  hp / KO marker             +0x08  the record most stores are made against

Read-only: no pokes, no writes. A save state is loaded and sampled.
"""
from __future__ import annotations

import argparse, json, struct, subprocess, sys, time
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
# The ENEMY actor pool (0x8009FD80, stride 0x84) is the wrong pool for this row.
# Censusing it across 300 frames in all three stage-2 saves showed the player
# state changing while the pool never did -- gates and falling debris are CONTACT
# OBJECTS, not enemy actors. Canon: fixed pool of 64 records of 0x38 bytes at
# 0x800B0D18, round-robin cursor at 0x8008234C, contact gate is signed
# record+0x22 > 0 plus flags bit 0x02.
POOL_BASE, STRIDE, SLOTS = 0x800B0D18, 0x38, 64
CURSOR = 0x8008234C


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default="level02.sav")
    ap.add_argument("--port", type=int, default=23487)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_f02")
    ap.add_argument("--settle", type=int, default=120, help="frames to advance before sampling")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f02_actor_census.json"))
    args = ap.parse_args()

    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(300)

    def snap():
        hx = c.call("debugger.readMemory",
                    {"address": "0x%08x" % POOL_BASE, "length": STRIDE * SLOTS})["hex"]
        return bytes.fromhex(hx)

    # emulator.getStatus / emulator.status / system.status do not exist on this
    # fork. advanceFrames itself RETURNS {"frame": N, "cycle": ...} -- use that.
    # An earlier version probed for a status method, got None, and printed
    # "frames advanced None" while still reporting a confident zero-motion result.
    try:
        c.call("emulator.loadState", {"path": str(ROOT / args.save)})
        f0 = c.call("emulator.advanceFrames", {"frames": args.settle}).get("frame")
        a = snap()
        player_a = c.call("debugger.readMemory",
                          {"address": "0x800a6500", "length": 0xB0})["hex"]
        f1 = c.call("emulator.advanceFrames", {"frames": 60}).get("frame")
        b = snap()
        player_b = c.call("debugger.readMemory",
                          {"address": "0x800a6500", "length": 0xB0})["hex"]
        # POSITIVE CONTROL: a census that reports "nothing moved" is worthless if
        # the emulator never advanced. Prove time passed before trusting a zero.
        frames_advanced = (f1 - f0) if (f0 is not None and f1 is not None) else None
        ram_changed = a != b
        # SECOND control: the player block must change, or the guest is not running
        # and a static pool proves nothing about the pool.
        guest_is_live = player_a != player_b
        scene_hx = c.call("debugger.readMemory", {"address": "0x800823a0", "length": 4})["hex"]
    finally:
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    def u16(buf, off): return struct.unpack_from("<H", buf, off)[0]
    def u32(buf, off): return struct.unpack_from("<I", buf, off)[0]

    actors = []
    for i in range(SLOTS):
        o = i * STRIDE
        raw_a = a[o:o + STRIDE]
        if not any(raw_a):
            continue
        rec = {
            "slot": i,
            "addr": "0x%08X" % (POOL_BASE + o),
            "byte_0x0C": a[o + 0x0C],   # NOT confirmed to be the kind -- see note
            "gate_0x22": struct.unpack_from("<h", a, o + 0x22)[0],
            "flags_0x20": "0x%04X" % u16(a, o + 0x20),
            "x": struct.unpack_from("<i", a, o + 0x00)[0],
            "y": struct.unpack_from("<i", a, o + 0x04)[0],
            "z": struct.unpack_from("<i", a, o + 0x08)[0],
            "raw": raw_a.hex(),
        }
        # a MOVING actor is the debris candidate: falling means y changes
        rec["moved_in_60f"] = a[o:o + 0x0C] != b[o:o + 0x0C]
        rec["record_changed"] = raw_a != b[o:o + STRIDE]
        rec["dy_60f"] = struct.unpack_from("<i", b, o + 0x04)[0] - rec["y"]
        actors.append(rec)

    by_species = Counter(r["byte_0x0C"] for r in actors)
    movers = [r for r in actors if r["moved_in_60f"]]
    fallers = sorted((r for r in movers if r["dy_60f"] != 0),
                     key=lambda r: -abs(r["dy_60f"]))

    out = {
        "_comment": "F02 Tunnels live actor census from a stage-2 save state. "
                    "Regenerate: tools/phase4_f02_actor_census.py",
        "generated": str(date.today()),
        "row_id": "F02_tunnels",
        "row_item": "Capture falling-debris actors in stage 2; bind them to their spawner "
                    "and damage class",
        "save": args.save,
        "settle_frames": args.settle,
        "pool": {"base": "0x%08X" % POOL_BASE, "stride": "0x%02X" % STRIDE, "slots": SLOTS,
                 "note": "0x8009FE04 is SLOT 1, not the base"},
        "goal_latch_0x800823A0": scene_hx,
        "control_frames_advanced": frames_advanced,
        "control_guest_is_live": guest_is_live,
        "control_pool_ram_changed": ram_changed,
        "reading": ("If the guest is live and the pool is static, the objects in this save "
                    "are UNTRIGGERED -- which is exactly what gates and not-yet-falling "
                    "debris look like. A static pool is then a real observation about the "
                    "fixture, not an instrument failure."),
        "occupied_slots": len(actors),
        "distinct_byte_0x0C_values": len(by_species),
        "byte_0x0C_histogram": {str(k): v for k, v in by_species.most_common()},
        "byte_0x0C_caveat": ("Offset 0x0C is NOT confirmed as the kind field for this pool. "
                             "Canon puts contact kinds in 0..49 (descriptor table 0x80096B98) "
                             "and these values reach 248, so either the offset is wrong or "
                             "these records are not all live contact objects. Reported as a "
                             "raw byte, not as a kind."),
        "records_changing": sum(1 for r in actors if r["record_changed"]),
        "moving_slots": len(movers),
        "falling_candidates": fallers[:12],
        "actors": actors,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"CONTROL: frames advanced {frames_advanced}, guest live {guest_is_live}, "
          f"pool changed {ram_changed}")
    print(f"occupied slots {len(actors)}  distinct species {len(by_species)}  moving {len(movers)}")
    print("   byte@0x0C (offset UNVERIFIED):", dict(by_species.most_common(8)))
    print("   records changing in 60f:", sum(1 for r in actors if r["record_changed"]))
    print("\nfalling candidates (dy over 60 frames):")
    for r in fallers[:8]:
        print("   slot %-3d b0C=%-4d dy=%-9d gate=%-6d flags=%s"
              % (r["slot"], r["byte_0x0C"], r["dy_60f"], r["gate_0x22"], r["flags_0x20"]))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
