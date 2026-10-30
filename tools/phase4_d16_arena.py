#!/usr/bin/env python3
"""D16 arena: what actually bounds Thumper.

The arena is NOT in the level and NOT in the bytecode. It is a per-actor number.

`random_dir_step` (0x8004C278) does, per step:

    s4          = [roster_record + 0x14] << 4        ; set once at 0x8004C194
    angle       = 12 bits from the noise cursor 0x800822F4
    [actor+0x34] = [actor+0x28] + (sin(angle) * s4) >> 9     ; target X from ANCHOR X
    [actor+0x38] = [actor+0x2C]                              ; target Y = anchor Y, unchanged
    [actor+0x3C] = [actor+0x30] + (cos(angle) * s4) >> 9     ; target Z from ANCHOR Z

Because the target is derived from a FIXED ANCHOR each time rather than from the
current position, this is a bounded circle, not a drifting random walk -- provided the
anchor really is fixed. That proviso is the whole question, so it is asserted here
rather than assumed.

Three things, one run:
  1. read the wander radius from the roster record (+0x14) and derive s4;
  2. WATCH the anchor (+0x28/+0x2C/+0x30) for writes -- if it moves during the fight,
     the circle is per-step, not per-fight, and that is the finding;
  3. watch the target (+0x34/+0x3C) and check every sampled target lies within the
     predicted radius of the anchor.

    tools/phase4_d16_arena.py --port 23690
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCAN_LO, SCAN_HI = 0x8009F000, 0x800A1000
THUMPER_CB = 0x8004A0F4
CB_OFF, ROSTER_PTR_OFF = 0x7C, 0x80
ANCHOR = {0x28: "anchor X", 0x2C: "anchor Y", 0x30: "anchor Z"}
TARGET = {0x34: "target X", 0x38: "target Y", 0x3C: "target Z"}
RADIUS_OFF = 0x14           # roster record +0x14, shifted left 4 -> s4
SIN_TABLE = 0x80074970      # amplitude is READ from the table, never assumed


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
            return out, bool(page.get("truncated"))
        off += len(got)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--movie", type=Path,
                    default=ROOT / "movies/Phase4/Interpreter/D16_Thumper_Defeat.movie.json")
    ap.add_argument("--disc", type=Path,
                    default=ROOT / "Disney-Pixar A Bug's Life (v1.0).cue")
    ap.add_argument("--launcher", type=Path,
                    default=ROOT / "tools/launch_repro_playback.sh")
    ap.add_argument("--execution-mode", default="Interpreter")
    ap.add_argument("--port", type=int, default=23690)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--json", type=Path, default=ROOT / "analysis/phase4_d16_arena.json")
    args = ap.parse_args()

    tmp = Path("/tmp/abl-scratch/d16-arena")
    tmp.mkdir(parents=True, exist_ok=True)
    pid = launch(args.port, args.token, args.disc, tmp / "cfg", tmp / "launch.log",
                 args.launcher, ROOT, args.execution_mode)

    out = {
        "row": "D16_thumper",
        "question": "arena -- what bounds Thumper",
        "movie": str(args.movie.relative_to(ROOT)),
        "mechanism": ("random_dir_step 0x8004C278 derives the TARGET from a fixed ANCHOR "
                      "each step: target = anchor + (sin(random) * s4) >> 9, with "
                      "s4 = [roster+0x14] << 4 (set at 0x8004C194). A bounded circle "
                      "rather than a drifting walk -- IF the anchor is fixed, which is "
                      "what this run tests."),
    }
    watch = {}
    try:
        c = DebuggerClient("127.0.0.1", args.port, "ws")
        c.authenticate(args.token)
        c.transport.sock.settimeout(900)
        c.call("movie.load", {"path": str(args.movie)})
        c.call("movie.startPlayback", {"load_start_state": True})

        def rd(a, n):
            return bytes.fromhex(c.call("debugger.readMemory",
                                        {"address": "0x%08x" % a, "length": n})["hex"])

        # ⚠️ READ TIMING, twice-learned. Values sampled before mover_init_from_record
        # runs (frame 37025 here) are PRE-INIT garbage -- that is what made 0x800776AC
        # look like Thumper's VM program, and what made roster+0x14 read 0. Values
        # sampled AFTER playback ends are equally useless. So: arm first, run into the
        # middle of the fight, pause, and read there.
        # The species dispatcher installs +0x7C at LEVEL LOAD, before this movie's
        # start state, so the actor can be located immediately -- which lets the
        # watches cover the WHOLE fight instead of only the tail.
        blob = rd(SCAN_LO, SCAN_HI - SCAN_LO)
        b = THUMPER_CB.to_bytes(4, "little")
        i = blob.find(b)
        if i < 0 or i % 4:
            out["error"] = "Thumper's callback pointer not found in the scan window"
            print(json.dumps(out, indent=1))
            return 1
        base = SCAN_LO + i - CB_OFF

        c.call("accessLog.clear", {})
        for o, n in list(ANCHOR.items()) + list(TARGET.items()):
            c.call("accessLog.addWatch", {"address": "0x%08x" % (base + o), "length": 4,
                                          "type": "write", "max_events": 60000})
            watch[base + o] = n

        # now run into the middle of the fight and take the POST-INIT reads there
        c.call("debugger.resume", {})
        time.sleep(25)
        c.call("debugger.pause", {})

        rec = rd(base, 0x84)
        roster = int.from_bytes(rec[ROSTER_PTR_OFF:ROSTER_PTR_OFF + 4], "little")
        radius_raw = int.from_bytes(rd(roster + RADIUS_OFF, 2), "little")
        s4 = radius_raw << 4
        # amplitude DERIVED from the live table, not assumed. Assuming 4096 (the usual
        # 1.3.12 convention) predicted 3200 against an observed 12800 and made a correct
        # model look refuted; the table is 1.2.14, amplitude 16384.
        tbl = rd(SIN_TABLE, 4096 * 2)
        amp = max(struct.unpack("<%dh" % 4096, tbl))
        predicted = (amp * s4) >> 9

        out["thumper_addr"] = "0x%08X" % base
        out["roster_record"] = "0x%08X" % roster
        out["roster_plus_0x14"] = radius_raw
        out["s4_step_scale"] = s4
        out["sin_amplitude_measured"] = amp
        out["predicted_max_offset_from_anchor"] = predicted
        out["anchor_mid_fight"] = {n: s32(int.from_bytes(rec[o:o + 4], "little"))
                                   for o, n in ANCHOR.items()}

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
        events, truncated = collect(c)
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
        r = by.setdefault(b0, {"name": watch[b0], "count": 0, "writers": {}, "vals": []})
        r["count"] += 1
        pc = str(e.get("instruction_pc") or e.get("pc") or "").lower()
        r["writers"][pc] = r["writers"].get(pc, 0) + 1
        v = e.get("new_value")
        if v is not None:
            r["vals"].append(s32(v & 0xFFFFFFFF))

    out["by_field"] = {
        "0x%08X" % a: {"name": r["name"], "writes": r["count"],
                       "writer_pcs": sorted(r["writers"].items(), key=lambda kv: -kv[1])[:5],
                       "distinct_values": len(set(r["vals"])),
                       "values": r["vals"][:40]}
        for a, r in sorted(by.items())
    }

    # ---- the three findings ------------------------------------------------
    anchor_moves = {}
    for o, n in ANCHOR.items():
        r = by.get(base + o)
        anchor_moves[n] = 0 if not r else len(set(r["vals"]))
    # The horizontal plane is what "arena" means. Y is driven separately by the overlay
    # (Thumper's hop), so including it would call a fixed arena "moving".
    # <=2 distinct: the BIOS/init write plus the settled value. More than that means
    # something relocated the anchor during play.
    anchor_fixed = anchor_moves["anchor X"] <= 2 and anchor_moves["anchor Z"] <= 2

    ax = out["anchor_mid_fight"]["anchor X"]
    az = out["anchor_mid_fight"]["anchor Z"]
    tx = by.get(base + 0x34, {}).get("vals", [])
    tz = by.get(base + 0x3C, {}).get("vals", [])
    offs = [math.hypot(x - ax, z - az) for x, z in zip(tx, tz)]
    out["target_samples"] = len(offs)
    out["max_observed_offset"] = round(max(offs), 1) if offs else None
    within = (max(offs) <= predicted * 1.02) if offs else None
    tight = (max(offs) >= predicted * 0.95) if offs else None

    out["findings"] = {
        "1_radius_is_per_actor_roster_data": {
            "roster_record": out["roster_record"],
            "field": "+0x14",
            "raw": radius_raw,
            "s4": s4,
            "predicted_max_offset": predicted,
            "verdict": ("the arena is a NUMBER attached to the actor, not level geometry "
                        "and not bytecode: roster+0x14 scaled x16 sets the step scale"),
        },
        "2_is_the_anchor_fixed": {
            "distinct_values_per_axis": anchor_moves,
            "writer_pcs": {n: (by.get(base + o, {}).get("writers") or {})
                           for o, n in ANCHOR.items()},
            "note": ("anchor Y is EXPECTED to move: the overlay drives Thumper's hop "
                     "(0x800B400C adds 4096 per step). Only X/Z define the arena."),
            "verdict": ("X/Z FIXED -- the arena is a fixed horizontal circle" if anchor_fixed else
                        "MOVES -- the bound is per-STEP, not per-fight; the wander can "
                        "migrate, so 'arena' is not a fixed region"),
        },
        "3_do_targets_stay_inside_the_circle": {
            "samples": len(offs),
            "max_observed_offset": out["max_observed_offset"],
            "predicted_max": predicted,
            "bound_is_reached": tight,
            "verdict": (None if within is None else
                        (("every sampled target lies within the predicted radius, and "
                          "the maximum REACHES it -- a real radius, not a loose upper "
                          "bound") if tight else
                         "every sampled target lies within the predicted radius"
                        if within else
                        "targets EXCEED the predicted radius -- the model is wrong or "
                        "something else moves him")),
        },
    }
    out["ring_truncated_note"] = ("if the ring truncated, the 'anchor is fixed' result is "
                                  "not a sound negative") if out.get("ring_truncated") else None

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in
                      ("roster_plus_0x14", "s4_step_scale", "sin_amplitude_measured",
                       "predicted_max_offset_from_anchor", "target_samples",
                       "max_observed_offset", "ring_truncated", "findings")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
