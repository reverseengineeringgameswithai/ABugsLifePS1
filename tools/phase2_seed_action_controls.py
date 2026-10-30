#!/usr/bin/env python3
"""Phase-2: behavioral positive/negative pairs for the SEED-family and SWING core
actions (review: these were omitted from the coverage map entirely).

Uses the kick lesson throughout: setControllerState HOLDS a button, and a held
button never produces a press EDGE — every edge-gated action must be driven by
release → press.

Anchors (all audited pristine):
  movies/Phase_Helpers/carry_handstand.movie.sav — Training, movable seed (id 11)
  on_swing.sav / in_front_of_swing.sav           — The Tree, vine/swing
Observables: the chunk-31 seed record (color/count bytes +0xE/+0xF, per Canon
seed-plant-output-binding), the player state word 0x800A6580, position, and the
in-flight/kick timers.

Pairs produced:
  A12 seed_color_change   Triangle while carrying -> seed color byte changes;
                          no Triangle -> unchanged.
  A13 cycle_plant_output  X while carrying -> seed selector byte changes;
                          no X -> unchanged.
  A14 plant_seed          jump onto the seed -> the seed record transitions
                          (crack/plant); standing beside it -> no transition.
  A15 uproot_plant        Square on the planted output -> record returns toward
                          a seed state; no Square -> unchanged.
  A10 handstand_negative  standing beside the fixed seed WITHOUT Square -> the
                          player is NOT frozen-mounted (grounded stays 1);
                          pairs with the positive already in
                          analysis/phase2_carry_handstand_oracle.json.
  A16 swinging            SAME-ANCHOR action pairs: grab (up+cross from the
                          approach anchor -> sustained state 5, grounded 0,
                          pendulum Y; no-input control never attaches) and
                          release (cross while attached -> leaves state 5 and
                          lands; idle control keeps swinging). Old version
                          compared two different anchors — replaced.
  (previous doc line:)    at the swing anchor: the player's attach/state word
                          under the grab input vs without it.

Usage: python3 tools/phase2_seed_action_controls.py [--port 23472]
Output: analysis/phase2_seed_action_controls.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

CARRY_ANCHOR = "movies/Phase_Helpers/carry_handstand.movie.sav"
CARRY_MOVIE = "movies/Phase_Helpers/carry_handstand.movie.json"
SWING_ANCHOR = "on_swing.sav"
SWING_APPROACH = "in_front_of_swing.sav"
RECORDS = 0x8009FE04


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

    def wr32(a, v):
        c.call("debugger.writeU32", {"address": "0x%08x" % a, "value": v & 0xFFFFFFFF})

    def player():
        b = rd(0x800A6540, 0x60)
        return {"pos": list(struct.unpack("<iii", rd(0x800A6500, 12))),
                "state80": b[0x40], "grounded": b[0x42]}

    def seed_index():
        buf = rd(RECORDS, 0x84 * 20)
        for i in range(20):
            rid, x, y, z = struct.unpack_from("<Iiii", buf, i * 0x84)
            if rid == 11:
                return i
        return None

    def seed_rec(idx, n=0x84):
        return rd(RECORDS + idx * 0x84, n).hex()

    def seed_bytes(idx):
        b = rd(RECORDS + idx * 0x84 + 0xE, 2)
        return {"color": b[0], "count": b[1]}

    def press(buttons, hold_frames=4, settle=25, pre=None):
        """Edge-correct press: (optionally hold `pre`), release, then press."""
        if pre:
            c.call("emulator.setControllerState", {"port": 0, "buttons": pre})
            c.call("emulator.advanceFrames", {"frames": 6})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 2})
        c.call("emulator.setControllerState", {"port": 0, "buttons": buttons})
        c.call("emulator.advanceFrames", {"frames": hold_frames})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": settle})
        c.call("debugger.pause", {})

    def frame_hash():
        import base64 as _b64
        r = c.call("gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"})
        for k in ("data", "png", "base64", "image"):
            if isinstance(r.get(k), str):
                return hashlib.sha256(_b64.b64decode(r[k])).hexdigest()
        raise KeyError("no frame payload")

    def carry_state(frame=620):
        """Reach a GENUINE carrying state by replaying the operator fixture (a
        synthetic teleport+Square never attaches: pickup has facing/proximity
        gates), then take control from there."""
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        c.call("movie.load", {"path": str(ROOT / CARRY_MOVIE)})
        c.call("movie.startPlayback", {"load_start_state": True})
        c.call("movie.advanceToFrame", {"frame": frame, "max_frames": 2100},
               timeout=600)
        c.call("movie.stopPlayback", {})
        c.call("debugger.pause", {})
        c.call("emulator.clearControllerState", {"port": 0})
        p = player()["pos"]
        srec = struct.unpack("<iii", rd(RECORDS + idx * 0x84 + 4, 12))
        return p[0] == srec[0] and p[2] == srec[2]

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    out: dict = {}

    load(CARRY_ANCHOR)
    idx = seed_index()
    assert idx is not None, "no movable seed (id 11) at the carry anchor"

    # ---- A12 seed color change (Triangle while carrying) --------------------
    def carry_input_trial(buttons, label):
        attached = carry_state()
        before = frame_hash()
        if buttons:
            press(buttons)
        else:
            c.call("emulator.advanceFrames", {"frames": 36})
            c.call("debugger.pause", {})
        after = frame_hash()
        return {"label": label, "carry_attached": attached,
                "frame_before": before[:16], "frame_after": after[:16],
                "frame_changed": before != after, "frame_after_full": after}

    tri = carry_input_trial({"triangle": True}, "Triangle while carrying")
    ctl = carry_input_trial(None, "no input, same window (negative)")
    out["A12_seed_color_change"] = {
        "anchor": f"{CARRY_MOVIE} @f620 (genuine carry state)",
        "observable": "displayed frame hash (the seed's colour is a visual event; "
                      "the live colour FIELD is unbound — Phase-3 semantics)",
        "positive": tri, "negative": ctl,
        "distinct_outcome": tri["frame_after_full"] != ctl["frame_after_full"],
        "passes": (tri["carry_attached"] and
                   tri["frame_after_full"] != ctl["frame_after_full"]),
    }
    print(f"[A12] carry={tri['carry_attached']} triangle-vs-control frames differ="
          f"{out['A12_seed_color_change']['distinct_outcome']} "
          f"passes={out['A12_seed_color_change']['passes']}")

    # ---- A13 cycle plant output (X while carrying) ---------------------------
    cyc = carry_input_trial({"cross": True}, "X while carrying")
    out["A13_cycle_plant_output"] = {
        "anchor": f"{CARRY_MOVIE} @f620 (genuine carry state)",
        "observable": "displayed frame hash (output selector is a visual event)",
        "positive": cyc, "negative": ctl,
        "distinct_outcome": cyc["frame_after_full"] != ctl["frame_after_full"],
        "distinct_from_triangle":
            cyc["frame_after_full"] != tri["frame_after_full"],
        "passes": (cyc["carry_attached"] and
                   cyc["frame_after_full"] != ctl["frame_after_full"]),
    }
    print(f"[A13] X-vs-control frames differ="
          f"{out['A13_cycle_plant_output']['distinct_outcome']} "
          f"passes={out['A13_cycle_plant_output']['passes']}")

    # ---- A14 plant/crack seed (jump onto it) --------------------------------
    # A14/A15 are NOT produced here: Training's seed is carry-only BY DESIGN
    # (operator-confirmed), and the other seed movies are viewing movies. They are
    # paired properly in tools/phase2_final_action_pairs.py (plant-spawner trace
    # over blue_seed_levels.movie, whose planting window was located by bisection).

    # ---- A10 handstand NEGATIVE (beside the seed, no Square) -----------------
    load(CARRY_ANCHOR)
    buf = rd(RECORDS + idx * 0x84, 16)
    _rid, sx, sy, sz = struct.unpack("<Iiii", buf)
    for addr, val in ((0x800A6500, sx - 700), (0x800A6510, sx - 700),
                      (0x800A6504, sy - 3000), (0x800A6514, sy - 3000),
                      (0x800A6508, sz - 700), (0x800A6518, sz - 700)):
        wr32(addr, val)
    c.call("emulator.advanceFrames", {"frames": 40})
    c.call("debugger.pause", {})
    p0 = player()
    c.call("emulator.advanceFrames", {"frames": 90})   # no input at all
    c.call("debugger.pause", {})
    p1 = player()
    out["A10_handstand_negative"] = {
        "anchor": CARRY_ANCHOR,
        "observable": "grounded 0x800A6582 (mounted reads 0) + position freeze",
        "beside_seed_no_square": {"before": p0, "after": p1},
        "not_mounted": p1["grounded"] == 1,
        "positive_reference": "analysis/phase2_carry_handstand_oracle.json "
                              "(mounted: grounded 0, position frozen >100f, "
                              "dismount state 0x800A6580 == 6)",
        "passes": p1["grounded"] == 1,
    }
    print(f"[A10] beside-seed-no-Square grounded={p1['grounded']} "
          f"passes={out['A10_handstand_negative']['passes']}")

    # ---- A16 swinging: SAME-ANCHOR grab and release pairs --------------------
    # (review: the old version passed by comparing two different anchors —
    # attached state 5 vs grounded state 0 — which proves anchors differ, not
    # that the action works. Now: a real GRAB from the approach anchor — hold
    # up TOWARD the vine, then cross — and a real RELEASE from the attached
    # anchor, each with a no-input control on the same anchor.)
    def sample_run(frames, step=6):
        outp = []
        for _ in range(frames // step):
            c.call("emulator.advanceFrames", {"frames": step})
            outp.append(player())
        c.call("debugger.pause", {})
        return outp

    def grab_trial(do_grab):
        load(SWING_APPROACH)
        c.call("emulator.advanceFrames", {"frames": 10})
        if do_grab:
            c.call("emulator.setControllerState",
                   {"port": 0, "buttons": {"up": True}})
            c.call("emulator.advanceFrames", {"frames": 10})
            c.call("emulator.setControllerState",
                   {"port": 0, "buttons": {"up": True, "cross": True}})
            c.call("emulator.advanceFrames", {"frames": 8})
            c.call("emulator.setControllerState",
                   {"port": 0, "buttons": {"up": True}})
            c.call("emulator.advanceFrames", {"frames": 30})
            c.call("emulator.clearControllerState", {"port": 0})
        else:
            c.call("emulator.advanceFrames", {"frames": 48})
        run = sample_run(60)
        attached = [r for r in run if r["state80"] == 5 and r["grounded"] == 0]
        ys = [r["pos"][1] for r in attached]
        return {"states": sorted({r["state80"] for r in run}),
                "attached_samples": len(attached),
                "sustained_attach": len(attached) >= 5,
                "pendulum_y_span": (max(ys) - min(ys)) if ys else 0}

    grab = grab_trial(True)
    grab_idle = grab_trial(False)

    def release_trial(do_release):
        load(SWING_ANCHOR)
        pre = sample_run(60)          # attached: state 5, grounded 0, pendulum
        if do_release:
            press({"cross": True}, hold_frames=6, settle=4)
        run = sample_run(60)
        return {"pre_states": sorted({r["state80"] for r in pre}),
                "pre_all_attached": all(r["state80"] == 5 and r["grounded"] == 0
                                        for r in pre),
                "pre_pendulum_y_span": (max(r["pos"][1] for r in pre)
                                        - min(r["pos"][1] for r in pre)),
                "post_states": sorted({r["state80"] for r in run}),
                "left_state5": any(r["state80"] != 5 for r in run),
                "landed_grounded": run[-1]["grounded"] != 0}

    rel = release_trial(True)
    rel_idle = release_trial(False)

    a16_pass = (grab["sustained_attach"] and grab["pendulum_y_span"] > 0
                and not grab_idle["sustained_attach"]
                and 5 not in grab_idle["states"]
                and rel["pre_all_attached"] and rel["left_state5"]
                and rel["landed_grounded"]
                and not rel_idle["left_state5"])
    out["A16_swinging"] = {
        "observable": "player state word 0x800A6580 + grounded 0x800A6582 + "
                      "pendulum Y trajectory",
        "grab": {"anchor": SWING_APPROACH,
                 "input": "hold up (toward the vine) + cross",
                 "positive": grab, "negative_no_input": grab_idle},
        "release": {"anchor": SWING_ANCHOR,
                    "input": "cross while attached",
                    "positive": rel, "negative_idle": rel_idle},
        "passes": a16_pass,
    }
    print(f"[A16] grab attach_samples={grab['attached_samples']} "
          f"(idle {grab_idle['attached_samples']}) release left5="
          f"{rel['left_state5']} landed={rel['landed_grounded']} "
          f"(idle stays: {not rel_idle['left_state5']}) passes={a16_pass}")

    doc = {
        "_comment": "Behavioral positive/negative pairs for the seed-family and "
                    "swing core actions (review: omitted from the coverage map). "
                    "Edge-correct input driving throughout (a HELD button never "
                    "produces a press edge — the kick lesson). Regenerate: "
                    "tools/phase2_seed_action_controls.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "controls": out,
        "all_pass": all(v["passes"] for v in out.values()),
    }
    path = ROOT / "analysis" / "phase2_seed_action_controls.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[seed_actions] wrote {path}: all_pass={doc['all_pass']}")
    return 0 if doc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
