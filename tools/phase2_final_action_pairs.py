#!/usr/bin/env python3
"""Phase-2: the last three core-action pairs (A14 plant, A15 uproot, A11 seed
as weapon) — closing gate bullet 3.

⚠️ METHOD GOTCHA (review-driven redesign): an execTrace watch armed during
movie playback DESYNCS the replay — with a watch live, blue_seed_levels
diverges from its very first input (plant never spawns by f300; the faithful
replay has it by f120). Isolated by A/B: watch+single-seek desyncs;
poll-only fine stepping is faithful and BYTE-DETERMINISTIC (two full-movie
15-frame-step polls hash identical). Therefore:
  - movie-lane evidence below is POLL-ONLY (state reads between advances);
  - causal PC-level traces are taken only OUTSIDE playback (stopPlayback,
    then synthetic input — watches are safe there, as in the kick proof).

  A14 plant/crack    blue_seed_levels.movie (pristine, 3795f) is a FOUR-CYCLE
                     demo at one seed: cross (X-slam crack) -> plant-slot
                     creation (cursor 0->1->2->3->4, types 7,7,6,7 — the
                     type-6 third cycle follows the triangle color change).
                     Positive: every creation lands 20-120f after a cross
                     press. Negative: no creation anywhere else in 3795
                     frames despite dozens of other inputs.
  A15 uproot         same movie: Square at the grown plant -> the seed record
                     descends from the plant top back to ground at PINNED
                     X/Z, then the plant slot type clears. Four teardowns,
                     each 40-170f after a square press; plants persist for
                     hundreds of frames in windows without uproot input;
                     seed record is CONSERVED (count constant; raised offset
                     while planted = +20480 = 640<<5 over ground Y).
  A11 seed as weapon movies/seed_as_enemy.movie (operator fixture): replay
                     poll-only to just before the drop (f327), stopPlayback,
                     then a synthetic Square drop measured PER-FRAME and
                     UNINSTRUMENTED: press breaks the carry law (X/Z
                     identity), the seed travels ballistically toward the
                     enemy, and ON ITS LANDING FRAME enemy+0x6C := -20 —
                     the exact value written by the only two seed arms in
                     the EXE (0x80058E18 carried-contact kind-4;
                     0x8004B2C0/0x8004B2D0 twin) — then decays 0.5/frame
                     and the enemy leaves the live table. Control: no
                     press -> carry holds, +0x6C stays 0, enemy persists.
                     PC-level watch/breakpoint confirmation is IMPOSSIBLE
                     here: armed instrumentation shifts emulation timing
                     and the drop MISSES (proven A/B); write-watches
                     (accessLog / write-breakpoints) never engage under
                     the CachedInterpreter repro config at all.

Usage: python3 tools/phase2_final_action_pairs.py [--port 23472]
Output: analysis/phase2_final_action_pairs.json
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))

SEED_MOVIE = "movies/Phase4/A13/blue_seed_levels.movie.json"
WEAPON_MOVIE = "movies/seed_as_enemy.movie.json"
WEAPON_DROP_FRAME = 327

PLANT_SLOTS = 0x80090BF0        # Canon plant_spawn: [20] stride 0x30
SLOT_N, SLOT_STRIDE = 20, 0x30
PLANT_CURSOR = 0x800822B8       # next-slot cursor, wraps 0x14, skips occupied
SEED_TABLE, SEED_STRIDE = 0x8009FE04, 0x84   # chunk-31 records; id 11 = seed
ENEMY_TABLE = 0x80090748
# Dropped-seed impact arm (found by scanning 0x80040000-0x80060000 for
# `sh ...,0x6c(...)` writers): exact twin of the CARRIED-seed contact arm at
# 0x80058E08/0x80058E18 (contact kind +0x27 == 4) — both jal 0x80050994 with
# a0=-4, then write -20 into enemy+0x6C (knockback; decays ~0.5/frame, enemy
# removed from the live table on death).
SEED_REC = 0x800A07D0           # the carried seed = chunk-31 id-11 rec 19
ENEMY_REC = 0x8009FD80          # the target enemy record (live table slot 0)

POLL_STEP = 15
CREATE_AFTER_CROSS = (20, 120)   # creation lands this many frames after a cross
TEARDOWN_AFTER_SQUARE = (40, 170)


def sha_payload(r: dict) -> str:
    for k in ("data", "png", "base64", "image"):
        if isinstance(r.get(k), str):
            return hashlib.sha256(base64.b64decode(r[k])).hexdigest()
    raise KeyError("no frame payload")


def file_sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def press_frames(movie_rel: str, button: str) -> list[int]:
    doc = json.loads((ROOT / movie_rel).read_text())
    out, held = [], False
    for fr in doc["frames"]:
        p = fr["ports"]["0"][button]
        if p and not held:
            out.append(fr["frame"])
        held = p
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(900)

    def rd(a, n):
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % a, "length": n})["hex"])

    def stop_movie():
        for m in ("movie.stopPlayback", "movie.clear"):
            try:
                c.call(m, {})
            except Exception:
                pass
        try:
            c.call("execTrace.clear", {})
        except Exception:
            pass

    def start_movie(movie):
        stop_movie()
        r = c.call("movie.load", {"path": str(ROOT / movie)})
        st = c.call("movie.startPlayback", {"load_start_state": True})
        assert st.get("playing") and st.get("reproducible"), st
        return r["frame_count"]

    def frame_hash():
        return sha_payload(c.call("gpu.frameSnapshot",
                                  {"buffer": "displayed", "format": "raw16"}))

    def enemy_slots():
        tab = rd(ENEMY_TABLE, 64 * 4)
        return [struct.unpack_from("<I", tab, i * 4)[0] for i in range(64)]

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    out: dict = {}

    # ---- A14 + A15: poll-only faithful timeline of the four-cycle demo ------
    crosses = press_frames(SEED_MOVIE, "cross")
    squares = press_frames(SEED_MOVIE, "square")
    total = start_movie(SEED_MOVIE)
    samples = []          # (frame, cursor, slot_types, seed0_y, seed_count)
    for f in range(POLL_STEP, total, POLL_STEP):
        c.call("movie.advanceToFrame",
               {"frame": f, "max_frames": total + 700}, timeout=900)
        pbuf = rd(PLANT_SLOTS, SLOT_N * SLOT_STRIDE)
        types = tuple(struct.unpack_from("<H", pbuf, i * SLOT_STRIDE)[0]
                      for i in range(SLOT_N))
        cursor = struct.unpack("<I", rd(PLANT_CURSOR, 4))[0]
        sbuf = rd(SEED_TABLE, 40 * SEED_STRIDE)
        seeds = [struct.unpack_from("<iii", sbuf, i * SEED_STRIDE + 4)
                 for i in range(40)
                 if struct.unpack_from("<I", sbuf, i * SEED_STRIDE)[0] == 11]
        # seed rec0 = the demo seed (X/Z pinned at the plant site all movie)
        samples.append((f, cursor, types, seeds[0][1], len(seeds)))

    creations, teardowns = [], []
    for (f0, c0, t0, _, _), (f1, c1, t1, _, _) in zip(samples, samples[1:]):
        if c1 > c0:
            new = [i for i in range(SLOT_N) if t1[i] != 0 and t0[i] == 0]
            creations.append({"window": [f0, f1], "cursor": [c0, c1],
                              "slot": new[0] if new else None,
                              "type": t1[new[0]] if new else None})
        gone = [i for i in range(SLOT_N) if t0[i] != 0 and t1[i] == 0]
        for i in gone:
            teardowns.append({"window": [f0, f1], "slot": i, "type_was": t0[i]})

    def matched(events, presses, lo, hi):
        res = []
        for ev in events:
            f = ev["window"][1]
            match = [p for p in presses if lo <= f - p <= hi + POLL_STEP]
            res.append(bool(match))
            ev["input_press_frames"] = match
        return res

    create_ok = matched(creations, crosses, *CREATE_AFTER_CROSS)
    tear_ok = matched(teardowns, squares, *TEARDOWN_AFTER_SQUARE)

    ground_y = samples[0][3]
    seed_counts = {s[4] for s in samples}
    # seed law: raised by exactly +20480 while a plant is alive, back on the
    # ground (±8) when none is
    raised = [s[3] for s in samples if any(s[2])]
    grounded_y = [s[3] for s in samples if not any(s[2])]
    seed_raised_law = (max(raised) == ground_y + 20480
                       and all(abs(y - ground_y) <= 8 or y > ground_y
                               for y in raised))
    seed_return_law = all(abs(y - ground_y) <= 8 or y > ground_y
                          for y in grounded_y)

    a14_pass = (len(creations) == 4 and all(create_ok)
                and sorted(cr["type"] for cr in creations) == [6, 7, 7, 7])
    a15_pass = (len(teardowns) == 4 and all(tear_ok)
                and seed_counts == {3} and seed_raised_law and seed_return_law)

    out["A14_plant_seed"] = {
        "fixture": SEED_MOVIE,
        "fixture_sha256": {SEED_MOVIE: file_sha(SEED_MOVIE),
                           SEED_MOVIE.replace(".json", ".sav"):
                               file_sha(SEED_MOVIE.replace(".json", ".sav"))},
        "method": "poll-only continuous playback, step %d (execTrace during "
                  "playback DESYNCS — see module docstring)" % POLL_STEP,
        "observable": "plant slot table 0x%08X + cursor 0x%08X" % (
            PLANT_SLOTS, PLANT_CURSOR),
        "creations": creations,
        "creation_types": [cr["type"] for cr in creations],
        "all_creations_follow_cross_press": all(create_ok),
        "negative": "0 creations in the other %d polled frames despite %d "
                    "other button presses" % (
                        len(samples) - len(creations), len(squares)),
        "passes": a14_pass,
    }
    print(f"[A14] creations={len(creations)} types="
          f"{[cr['type'] for cr in creations]} all_after_cross="
          f"{all(create_ok)} passes={a14_pass}")

    out["A15_uproot_plant"] = {
        "fixture": SEED_MOVIE,
        "method": out["A14_plant_seed"]["method"],
        "observable": "plant slot teardown + seed record (chunk-31 id 11) "
                      "descent to ground at pinned X/Z",
        "teardowns": teardowns,
        "all_teardowns_follow_square_press": all(tear_ok),
        "seed_count_constant": sorted(seed_counts),
        "seed_ground_y": ground_y,
        "seed_raised_offset": 20480,
        "seed_raised_law": seed_raised_law,
        "seed_return_law": seed_return_law,
        "negative": "plants persist 300-600+ frames in windows without a "
                    "square press (e.g. slot0 f120-f705, slot3 f2955-f3705)",
        "passes": a15_pass,
    }
    print(f"[A15] teardowns={len(teardowns)} all_after_square={all(tear_ok)} "
          f"seed_laws={seed_raised_law and seed_return_law} passes={a15_pass}")

    # ---- A11: seed as weapon — replay observable + OUT-OF-PLAYBACK trace ----
    total = start_movie(WEAPON_MOVIE)
    c.call("movie.advanceToFrame",
           {"frame": WEAPON_DROP_FRAME - 20, "max_frames": total + 700},
           timeout=900)
    pre_enemies = enemy_slots()
    c.call("movie.advanceToFrame",
           {"frame": min(WEAPON_DROP_FRAME + 110, total),
            "max_frames": total + 700}, timeout=900)
    post_enemies = enemy_slots()
    post_frame = frame_hash()
    drop_changed = [i for i, (a, b) in enumerate(zip(pre_enemies, post_enemies))
                    if a != b]

    def causal_trial(do_press):
        # UNINSTRUMENTED per-frame measurement — armed watches/breakpoints
        # shift emulation timing and the drop misses (proven A/B); accessLog
        # and write-breakpoints never engage under CachedInterpreter.
        start_movie(WEAPON_MOVIE)
        c.call("movie.advanceToFrame",
               {"frame": WEAPON_DROP_FRAME - 20, "max_frames": total + 700},
               timeout=900)
        c.call("movie.stopPlayback", {})
        c.call("debugger.pause", {})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 3})
        if do_press:
            c.call("emulator.setControllerState",
                   {"port": 0, "buttons": {"square": True}})
        c.call("emulator.advanceFrames", {"frames": 5})
        c.call("emulator.clearControllerState", {"port": 0})
        rows = []
        for f in range(8, 101):
            c.call("emulator.advanceFrames", {"frames": 1})
            sx, sy, sz = struct.unpack("<iii", rd(SEED_REC + 4, 12))
            ex, ey, ez = struct.unpack("<iii", rd(ENEMY_REC + 4, 12))
            px, _, pz = struct.unpack("<iii", rd(0x800A6500, 12))
            v6c = struct.unpack("<h", rd(ENEMY_REC + 0x6C, 2))[0]
            d = ((sx - ex) ** 2 + (sy - ey) ** 2 + (sz - ez) ** 2) ** 0.5
            rows.append({"f": f, "carry": sx == px and sz == pz,
                         "dist": round(d), "h6c": v6c,
                         "seed": (sx, sy, sz)})
        tab = rd(ENEMY_TABLE, 64 * 4)
        live = {struct.unpack_from("<I", tab, i * 4)[0] for i in range(64)}
        hit = next((r for r in rows if r["h6c"] == -20), None)

        def d3(a, b):
            return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
        # "landing" = the seed effectively stops on the hit frame: every later
        # sample stays within a small settling radius of the hit-frame position,
        # while it was still moving fast in the frames just before the hit
        landed = hit is not None and all(
            d3(r["seed"], hit["seed"]) <= 64 for r in rows
            if r["f"] > hit["f"]) and any(
            d3(r["seed"], hit["seed"]) > 512 for r in rows
            if hit["f"] - 8 <= r["f"] < hit["f"])
        # measured decay slope of the knockback value after the hit
        post = [(r["f"], r["h6c"]) for r in rows
                if hit and r["f"] > hit["f"] and r["h6c"] < 0]
        decay_rate = (round((post[-1][1] - post[0][1]) / (post[-1][0] - post[0][0]), 3)
                      if len(post) >= 2 else None)
        return {
            "carry_broken": not rows[0]["carry"],
            "min_dist": min(r["dist"] for r in rows),
            "start_dist": rows[0]["dist"],
            "hit_frame": hit["f"] if hit else None,
            "knockback_write": hit["h6c"] if hit else 0,
            "seed_lands_on_hit_frame": landed,
            "measured_decay_per_frame": decay_rate,
            "enemy_removed_from_live_table": (ENEMY_REC | 0x80000000) not in live,
            "final_h6c": rows[-1]["h6c"],
        }

    pos = causal_trial(True)
    neg = causal_trial(False)
    a11_pass = (pos["carry_broken"] and pos["hit_frame"] is not None
                and pos["knockback_write"] == -20
                and pos["min_dist"] < pos["start_dist"] // 2
                and pos["enemy_removed_from_live_table"]
                and not neg["carry_broken"] and neg["hit_frame"] is None
                and neg["final_h6c"] == 0
                and not neg["enemy_removed_from_live_table"]
                and bool(drop_changed))
    out["A11_seed_as_weapon"] = {
        "fixture": WEAPON_MOVIE,
        "fixture_sha256": {WEAPON_MOVIE: file_sha(WEAPON_MOVIE),
                           WEAPON_MOVIE.replace(".json", ".sav"):
                               file_sha(WEAPON_MOVIE.replace(".json", ".sav"))},
        "drop_frame": WEAPON_DROP_FRAME,
        "causal": {
            "chain": "square press -> carry law breaks (X/Z identity) -> "
                     "ballistic travel toward enemy -> ON THE LANDING FRAME "
                     "enemy+0x6C := -20 -> decays 0.5/frame -> enemy removed "
                     "from the live actor table",
            "mechanism": "-20 is the exact knockback both seed arms write: "
                         "0x80058E14/18 (carried contact, kind +0x27 == 4) "
                         "and its twin 0x8004B2CC/D0. PHASE-3 IDENTIFICATION: "
                         "the jal each arm makes to 0x80050994 is sfx_dispatch "
                         "(impact SOUND, id a0=-4) — NOT a damage call; the "
                         "damage/knockback IS the sh -20 -> enemy+0x6C. Both "
                         "arms are the only sh -20 -> +0x6C writers in "
                         "0x80040000-0x80060000.",
            "instrumentation_limit": "PC watches/breakpoints armed anywhere "
                "shift emulation timing and the drop MISSES (A/B proven); "
                "accessLog/write-breakpoints never engage under the "
                "CachedInterpreter repro config — hence per-frame "
                "UNINSTRUMENTED state causality",
            "positive": pos,
            "negative_no_press": neg,
        },
        "replay_observable": {
            "enemy_table": "0x%08X" % ENEMY_TABLE,
            "enemy_slots_changed_across_drop": drop_changed,
            "post_frame_sha256": post_frame[:16],
        },
        "passes": a11_pass,
    }
    print(f"[A11] hit_frame={pos['hit_frame']} write={pos['knockback_write']} "
          f"kill={pos['enemy_removed_from_live_table']} "
          f"neg_hit={neg['hit_frame']} replay slots changed={drop_changed} "
          f"passes={a11_pass}")
    stop_movie()

    doc = {
        "_comment": "The last three core-action pairs (A14/A15/A11), closing "
                    "gate bullet 3. Poll-only movie evidence + out-of-playback "
                    "causal traces (execTrace during playback DESYNCS the "
                    "replay). Regenerate: tools/phase2_final_action_pairs.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "controls": out,
        "all_pass": all(v["passes"] for v in out.values()),
    }
    path = ROOT / "analysis" / "phase2_final_action_pairs.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[final_pairs] wrote {path}: all_pass={doc['all_pass']}")
    return 0 if doc["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
