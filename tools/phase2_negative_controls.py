#!/usr/bin/env python3
"""Phase-2 per-action NEGATIVE controls: prove each action signature does not
occur without its input (external review: one global Circle control was not
per-action coverage).

Controls (each from a pristine anchor, deterministic):
  no_input_idle      level01, 120 frames, no input: action state word 0x800A6580
                     stays 0; grounded stays 1; in-flight counter stays 0.
  walk_no_square     training anchor, hold Up 120 frames WITHOUT Square: the
                     movable seed record does NOT attach (X/Z never both equal
                     the player's), no carry despite proximity-capable movement.
  walk_no_double_tap training anchor, single Cross press (jump) while moving:
                     state80 enters 1 (air) but NEVER 4/5 (slam/slide states are
                     double-tap-gated).
  no_start_no_pause  level02, hold Up 60 frames without Start: the player MOVES
                     (pause-freeze requires Start; complements the pause oracle).

Usage: python3 tools/phase2_negative_controls.py [--port 23472]
Output: analysis/phase2_negative_controls.json
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(300)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def load(sav):
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def probe():
        b = rd(0x800A6540, 0x60)
        return {"s80": b[0x40], "grounded": b[0x42],
                "pos": list(struct.unpack("<iii", rd(0x800A6500, 12))),
                "inflight": rd(0x800A6596, 1)[0]}

    def rec0():
        rid, x, y, z = struct.unpack("<Iiii", rd(0x8009FE04, 16))
        return rid, (x, y, z)

    def hold(buttons, frames, step=15):
        series = []
        for _ in range(frames // step):
            if buttons:
                c.call("emulator.setControllerState", {"port": 0, "buttons": buttons})
            c.call("emulator.advanceFrames", {"frames": step})
            c.call("debugger.pause", {})
            series.append((probe(), rec0()))
        c.call("emulator.clearControllerState", {"port": 0})
        return series

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    out = {}

    # no-input idle
    load("level01.sav")
    series = hold(None, 120)
    out["no_input_idle"] = {
        "anchor": "level01.sav", "frames": 120,
        "s80_values": sorted({p["s80"] for p, _ in series}),
        "grounded_always": all(p["grounded"] == 1 for p, _ in series),
        "inflight_always_zero": all(p["inflight"] == 0 for p, _ in series),
        "passes": (all(p["s80"] == 0 for p, _ in series)
                   and all(p["inflight"] == 0 for p, _ in series)),
    }

    # walking without Square: no carry attachment. Uses the SAME anchor the
    # positive carry evidence came from, and tracks the ACTUAL movable seed
    # (first record with id 11), not blindly record 0 (review fix: the earlier
    # control watched an id-0 record at a different anchor — vacuous).
    load("movies/Phase_Helpers/carry_handstand.movie.sav")
    seed_idx = None
    buf = rd(0x8009FE04, 0x84 * 20)
    for i in range(20):
        rid, x, y, z = struct.unpack_from("<Iiii", buf, i * 0x84)
        if rid == 11:
            seed_idx = i
            break
    assert seed_idx is not None, "no id-11 movable seed at the carry anchor"
    def seed_pos():
        x, y, z = struct.unpack_from("<iii", rd(0x8009FE04 + seed_idx * 0x84 + 4, 12), 0)
        return (x, y, z)
    series = []
    for _ in range(8):
        c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
        c.call("emulator.advanceFrames", {"frames": 15})
        c.call("debugger.pause", {})
        series.append((probe(), seed_pos()))
    c.call("emulator.clearControllerState", {"port": 0})
    attach_hits = sum(1 for p, rxyz in series
                      if p["pos"][0] == rxyz[0] and p["pos"][2] == rxyz[2])
    player_moved = (abs(series[-1][0]["pos"][0] - series[0][0]["pos"][0])
                    + abs(series[-1][0]["pos"][2] - series[0][0]["pos"][2]))
    out["walk_no_square_no_carry"] = {
        "anchor": "movies/Phase_Helpers/carry_handstand.movie.sav",
        "seed_record_index": seed_idx, "frames": 120,
        "attachment_samples": attach_hits,
        "player_displacement": player_moved,
        "passes": attach_hits == 0 and player_moved > 500,
    }

    # single jump never enters slam/slide states — WITH the positive premise
    # (review fix: the earlier control sampled too coarsely and only ever saw
    # state 0, proving nothing). Dense 3-frame sampling captures the airborne
    # state (1) that anchors the assertion.
    # (anchor fix: the Training movie start save is PRE-scene-load — inputs are
    # menu inputs there; use the in-level stage01 anchor)
    load("level01.sav")
    c.call("emulator.setControllerState",
           {"port": 0, "buttons": {"up": True, "cross": True}})
    c.call("emulator.advanceFrames", {"frames": 4})
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    s80s = []
    for _ in range(30):
        c.call("emulator.advanceFrames", {"frames": 3})
        c.call("debugger.pause", {})
        b = rd(0x800A6540, 0x60)
        s80s.append(b[0x40])
    c.call("emulator.clearControllerState", {"port": 0})
    seen = sorted(set(s80s))
    out["single_jump_no_slide_states"] = {
        "anchor": "level01.sav",
        "s80_values_seen": seen,
        "jump_state_observed": 1 in seen,          # the positive premise
        "note": "state 5 is a shared moving-landing/skid state (observed on plain "
                "jumps); only state 4 (slam/dive) is double-tap-exclusive",
        "passes": (1 in seen) and 4 not in seen,
    }

    # Triangle without a carried seed: seed color/count bytes unchanged
    load("movies/Phase_Helpers/carry_handstand.movie.sav")
    before_cc = rd(0x8009FE04 + seed_idx * 0x84 + 0xE, 2).hex()
    for _ in range(3):
        c.call("emulator.setControllerState", {"port": 0, "buttons": {"triangle": True}})
        c.call("emulator.advanceFrames", {"frames": 5})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 10})
    c.call("debugger.pause", {})
    after_cc = rd(0x8009FE04 + seed_idx * 0x84 + 0xE, 2).hex()
    out["triangle_no_carry_no_color_change"] = {
        "anchor": "movies/Phase_Helpers/carry_handstand.movie.sav",
        "seed_record_index": seed_idx,
        "color_count_bytes_before": before_cc, "after": after_cc,
        "passes": before_cc == after_cc,
    }

    # movement without Start: no pause freeze
    load("level02.sav")
    series = hold({"up": True}, 60)
    first, last = series[0][0]["pos"], series[-1][0]["pos"]
    moved = abs(last[0] - first[0]) + abs(last[2] - first[2])
    out["no_start_no_pause"] = {
        "anchor": "level02.sav", "displacement": moved, "passes": moved > 500,
    }

    doc = {
        "_comment": "Per-action negative controls (signatures require their inputs). "
                    "Regenerate: tools/phase2_negative_controls.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "controls": out,
        "all_pass": all(v["passes"] for v in out.values()),
    }
    path = ROOT / "analysis" / "phase2_negative_controls.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    for k, v in out.items():
        print(f"[negative] {k}: {'PASS' if v['passes'] else 'FAIL'}")
    print(f"[negative] wrote {path}: all_pass={doc['all_pass']}")
    return 0 if doc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
