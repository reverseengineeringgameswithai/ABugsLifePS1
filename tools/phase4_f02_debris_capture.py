#!/usr/bin/env python3
"""F02 Tunnels: catch the falling debris in the contact pool during a real run.

WHY A MOVIE AND NOT A SAVE STATE
--------------------------------
tools/phase4_f02_actor_census.py established the pool (contact objects at
0x800B0D18, 64 records of 0x38, cursor 0x8008234C -- NOT the enemy actor pool at
0x8009FD80, which is static in every stage-2 save) and then found that all three
stage-2 fixtures are UNTRIGGERED: guest demonstrably live, player block changing,
pool byte-identical across 300 frames. Gates that have not opened and debris that
has not been released look exactly like that.

I then asked the operator to record a Tunnels movie -- which they had already
recorded, as LEVEL02_Tunnels in the 16-level any% campaign. Check the fixtures
you already have before asking for more.

WHAT THIS DOES
--------------
Replays that movie at 60 Hz and samples the whole contact pool repeatedly, then
reports, per slot: how often the record changed, how far Y travelled, and whether
motion was monotonic downward over a stretch -- which is what falling looks like.

Replay is 60 Hz (debugger.resume + poll), never movie.advanceToFrame: the
recording is state-anchored and armed_while_paused (CLAUDE.md).

Usage: python3 tools/phase4_f02_debris_capture.py
"""
from __future__ import annotations

import argparse, json, struct, subprocess, sys, time
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
from duckstation_debug_client import DebuggerClient  # noqa: E402

DISC = ROOT / "Disney-Pixar A Bug's Life (v1.0).cue"
POOL, STRIDE, SLOTS = 0x800B0D18, 0x38, 64
PLAYER = 0x800A6500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--movie", default="movies/Phase4/Interpreter/Any% Runs/LEVEL02_Tunnels.movie.json")
    ap.add_argument("--port", type=int, default=23493)
    ap.add_argument("--config-dir", default="/tmp/dsrepro_f02d")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f02_debris_capture.json"))
    args = ap.parse_args()

    subprocess.run([str(ROOT / "tools/launch_repro_playback.sh"),
                    "--config-dir", args.config_dir, "--port", str(args.port),
                    "--disc", str(DISC), "--execution-mode", "Interpreter"], check=True)
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate("debugger-1000")
    c.transport.sock.settimeout(900)

    samples = []
    try:
        c.call("movie.load", {"path": str(ROOT / args.movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        frames = st.get("frame_count") or 0
        c.call("debugger.resume", {})
        began, last, stalls = time.time(), -1, 0
        budget = 90 + frames / 30.0
        while time.time() - began < budget:
            time.sleep(0.6)
            try:
                idx = c.call("movie.status", {}).get("playback_index")
                pool = bytes.fromhex(c.call("debugger.readMemory",
                    {"address": "0x%08x" % POOL, "length": STRIDE * SLOTS})["hex"])
                ply = c.call("debugger.readMemory",
                    {"address": "0x%08x" % PLAYER, "length": 16})["hex"]
                samples.append((idx, pool, ply))
            except Exception:                                   # noqa: BLE001
                idx = last
            if idx == last:
                stalls += 1
                if stalls >= 10:
                    break
            else:
                stalls = 0
            last = idx
    finally:
        subprocess.run([str(Path.home() / "duckstation/scripts/debugger-client/"
                             "launch_debugger_instance.sh"), "stop",
                        "--config-dir", args.config_dir], check=False)

    guest_live = len({s[2] for s in samples}) > 1
    changes = defaultdict(int)
    ytrack = defaultdict(list)
    for (i0, p0, _), (i1, p1, _) in zip(samples, samples[1:]):
        for s in range(SLOTS):
            o = s * STRIDE
            if p0[o:o + STRIDE] != p1[o:o + STRIDE]:
                changes[s] += 1
            y0 = struct.unpack_from("<i", p0, o + 4)[0]
            y1 = struct.unpack_from("<i", p1, o + 4)[0]
            if y0 != y1:
                ytrack[s].append((i1, y1 - y0))

    slots = []
    for s in sorted(changes, key=lambda k: -changes[k]):
        deltas = [d for _i, d in ytrack.get(s, [])]
        down = sum(1 for d in deltas if d > 0)
        up = sum(1 for d in deltas if d < 0)
        slots.append({
            "slot": s, "addr": "0x%08X" % (POOL + s * STRIDE),
            "record_changes": changes[s],
            "y_moves": len(deltas),
            "y_down_steps": down, "y_up_steps": up,
            "total_y_travel": sum(abs(d) for d in deltas),
            "max_single_step": max((abs(d) for d in deltas), default=0),
            "first_y_move_at_index": ytrack[s][0][0] if ytrack.get(s) else None,
        })

    fallers = [s for s in slots if s["y_down_steps"] >= 3 and
               s["y_down_steps"] > 2 * s["y_up_steps"]]

    out = {
        "_comment": "F02 Tunnels: contact-pool activity across the any% Tunnels run. "
                    "Regenerate: tools/phase4_f02_debris_capture.py",
        "generated": str(date.today()),
        "row_id": "F02_tunnels",
        "movie": args.movie,
        "movie_frames": frames,
        "pool": {"base": "0x%08X" % POOL, "stride": "0x%02X" % STRIDE, "slots": SLOTS,
                 "source": "Canon SYS_contact_object_pool"},
        "samples_taken": len(samples),
        "control_guest_live": guest_live,
        "slots_that_changed": len(changes),
        "slots": slots[:24],
        "falling_candidates": fallers,
        "why_not_a_save_state": ("All three stage-2 save fixtures are UNTRIGGERED: guest "
                                 "live, player moving, contact pool byte-identical over 300 "
                                 "frames. The event only exists in a run."),
        "verdict": None,
    }
    if not guest_live:
        out["verdict"] = ("INCONCLUSIVE -- the player block never changed, so the replay did "
                          "not run and a quiet pool proves nothing.")
    elif fallers:
        out["verdict"] = ("CAPTURED -- %d contact slot(s) show sustained downward Y motion "
                          "during the Tunnels run, against %d slots showing any change at "
                          "all. These are the falling-debris records the row asked for."
                          % (len(fallers), len(changes)))
    elif changes:
        out["verdict"] = ("POOL IS ACTIVE BUT NO CLEAN FALLER -- %d slots changed, none with "
                          "sustained downward motion. Either the debris uses a different "
                          "field for its descent, or the sampling (~0.6 s) is too coarse to "
                          "catch a short drop." % len(changes))
    else:
        out["verdict"] = "POOL STATIC across the whole run despite a live guest -- unexpected."

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"samples {len(samples)}  guest live {guest_live}  slots changed {len(changes)}")
    for s in slots[:10]:
        print("   slot %-3d changes=%-5d ymoves=%-4d down=%-4d up=%-4d travel=%d"
              % (s["slot"], s["record_changes"], s["y_moves"], s["y_down_steps"],
                 s["y_up_steps"], s["total_y_travel"]))
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
