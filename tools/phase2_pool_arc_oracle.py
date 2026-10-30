#!/usr/bin/env python3
"""Phase-2 final gate items: berry-arc sentinel, contact-pool census/digest,
pool-capacity stress, and the remaining native-action attempts.

Contact pool per Canon MEM_800B0D18 (the first version of this tool derived the
base empirically as 0x800B0D48 — 0x30 INTO the real array, caught by external
review; always consult Canon first): 64 records x 0x38 at 0x800B0D18, runtime
XYZ at +0x00, live gate = active_type(+0x22) > 0 AND flags(+0x33) bit 0x80.
Pickups/tokens/projectiles are pool records, so the per-anchor pool digest is
the DIRECT missing-tokens sentinel, and a thrown berry occupies slot 52 in
red_berry_thrown.sav whose per-frame trajectory is the arc sentinel.

Sections:
  arc_sentinel     red_berry_thrown.sav (hash-pinned, mid-flight, in-flight
                   counter 0x800A6596 == 1): 20 per-frame samples of the
                   projectile triple -> trajectory + gravity fit (Y+ is down),
                   sampled twice from reload to prove determinism, plus flight
                   frame hashes (visibility).
  pool_census      per identity anchor: active-slot count, per-slot headers, and
                   sha256 of the full pool region (missing-pickup sentinel).
  capacity_stress  from the thrown save: spam Square, track the in-flight
                   counter and active-slot count -> observed concurrency bound
                   and post-stress stability.
  action_attempts  seed interactions at the Training anchor (Square at each
                   censused record: carry/handstand candidates) and a downhill
                   slide attempt at the canyon anchor — outcomes recorded
                   honestly, including nulls.

Usage: python3 tools/phase2_pool_arc_oracle.py [--port 23472]
Output: analysis/phase2_pool_arc_oracle.json
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
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)
from phase2_compare import validate_repro_config

# Canon frame (MEM_800B0D18 — consulted AFTER external review caught an
# empirically mis-derived base 0x30 into the array): 64 records x 0x38 at
# 0x800B0D18; runtime XYZ at +0x00; live gate = active_type (+0x22) > 0 AND
# flags (+0x33) bit 0x80 (alloc-occupied); action_id +0x20; state +0x2C.
POOL_BASE, POOL_SLOTS, POOL_STRIDE = 0x800B0D18, 64, 0x38
POOL_SIZE = POOL_SLOTS * POOL_STRIDE
PROJ_SLOT = 52                   # (0x800B1878-0x800B0D18)/0x38 — red_berry_thrown.sav
PROJ_XYZ = POOL_BASE + PROJ_SLOT * POOL_STRIDE   # XYZ at +0x00
INFLIGHT = 0x800A6596

IDENTITY_ANCHORS = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"), ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"), ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"), ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"), ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"), ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
    ("bonus1_spiders", "movies/Bonus_Level_01.movie.sav"),
    ("bonus2_mushrooms", "movies/Bonus_Level_02.movie.sav"),
    ("bonus3_grasshoppers", "movies/Bonus_Level_03.movie.sav"),
]


def sha_payload(result: dict) -> str:
    for key in ("data", "png", "base64", "image"):
        if isinstance(result.get(key), str):
            return hashlib.sha256(base64.b64decode(result[key])).hexdigest()
    raise KeyError(f"no payload: {list(result)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23472)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--repro-config-dir", required=True,
                    help="dedicated config created by tools/launch_repro_playback.sh")
    args = ap.parse_args()
    try:
        repro_profile = validate_repro_config(Path(args.repro_config_dir))
    except ValueError as exc:
        raise SystemExit(f"REPRO PROFILE GUARD: {exc}")

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
        inspect_state_before_load(c, ROOT / sav, media_identity)
        r = c.call("emulator.loadState", {"path": str(ROOT / sav),
                                          "pause_after_load": True})
        assert r.get("loaded") and r.get("game_serial") == "SCUS-94288", r
        c.call("emulator.clearControllerState", {"port": 0})

    def pool_read():
        buf = rd(POOL_BASE, POOL_SIZE)
        active = []
        for i in range(POOL_SLOTS):
            e = buf[i * POOL_STRIDE:(i + 1) * POOL_STRIDE]
            active_type = struct.unpack_from("<H", e, 0x22)[0]
            flags = e[0x33]
            # DUAL gate semantics (walker disasm 0x80058730..4C, tenth pass):
            # TYPED   = active_type(+0x22) > 0            (allocated + typed)
            # WALKED  = typed AND flags(+0x33) & 0x02     (the walker's own gate;
            #           bit 2 toggles dynamically — often clear at a paused anchor)
            if active_type > 0:
                active.append({"slot": i,
                               "xyz": list(struct.unpack_from("<iii", e, 0)),
                               "action_id": struct.unpack_from("<H", e, 0x20)[0],
                               "active_type": active_type,
                               "flags": flags,
                               "enabled": bool(flags & 0x2),
                               "alloc_occupied": bool(flags & 0x80)})
        return buf, active

    def wr32(a, v):
        c.call("debugger.writeU32", {"address": "0x%08x" % a, "value": v & 0xFFFFFFFF})

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)
    out: dict = {"pool_layout": {
        "base": f"0x{POOL_BASE:08X}", "slots": POOL_SLOTS, "stride": hex(POOL_STRIDE),
        "canon": "MEM_800B0D18 (contact/pickup array); XYZ +0x00. WALKER GATE "
                 "(disassembled at FUNC_800586B0+0x80..0x9C): active_type(+0x22)>0 "
                 "AND flags(+0x33)&0x02; bit 2 toggles dynamically so a paused "
                 "anchor may show typed slots with bit 2 clear. Census reports "
                 "BOTH counts. Alloc cursor 0x8008234C (pre-increment, wraps 0x40); "
                 "filled by FUNC_80059E44, walked by FUNC_800586B0.",
    }}

    # Run the from-boot lane before any loadState call. Save states restore an
    # embedded memory card; this movie requires the launcher's seeded card.
    # ---- allocator cursor observation (allocation churn in NATIVE gameplay) ---
    # Allocator semantics per src_re/contact_alloc_80059e44.c (CONFIRMED C):
    # round-robin FREE-SLOT SEARCH — advance cursor (wrap 0x40), SKIP slots that
    # are occupied (flags&0x80 && active_type!=0), NO full-array escape: if all
    # 64 slots are occupied the allocator SPINS (capacity hang risk). Cursor
    # wraps therefore prove >64 allocations over time (churn + slot reuse) —
    # NOT saturation and NOT an overwrite-oldest policy (earlier claim wrong).
    r = c.call("movie.load",
               {"path": str(ROOT / "movies/go_to_end/LEVEL03.movie.json")})
    stpb = c.call("movie.startPlayback", {"load_start_state": True})
    assert stpb.get("playing") and stpb.get("reproducible"), stpb
    c.call("debugger.pause", {})
    frames_total = r["frame_count"]
    cursor_series = []
    prev = None
    wraps = 0
    cur = 0
    while cur < frames_total:
        cur = min(cur + 200, frames_total)
        c.call("movie.advanceToFrame",
               {"frame": cur, "max_frames": frames_total + 700}, timeout=900)
        val = struct.unpack("<H", rd(0x8008234C, 2))[0]
        valid = val < 0x40
        # count wraps only between VALID in-domain values (the pre-game cursor
        # holds garbage like 32383; review caught the bogus 32383->0 "wrap")
        if prev is not None and valid and val < prev:
            wraps += 1
        if valid:
            prev = val
        cursor_series.append({"frame": cur, "cursor": val, "valid": valid})
    out["allocator_cursor"] = {
        "cursor_address": "0x8008234C", "wrap_modulus": 0x40,
        "semantics": "round-robin free-slot search; skips occupied "
                     "(flags&0x80 && active_type!=0); NO full-array escape — "
                     "allocator SPINS if all 64 slots occupied (capacity hang "
                     "risk; src_re/contact_alloc_80059e44.c)",
        "movie": "movies/go_to_end/LEVEL03.movie.json",
        "series": cursor_series,
        "valid_wraps_observed": wraps,
        "evidence": "wraps prove >64 allocations over the run (churn + reuse), "
                    "NOT saturation, NOT overwrite-oldest",
    }
    print(f"[cursor] valid in-domain wraps across the LEVEL03 run: {wraps}")

    # ---- arc sentinel ---------------------------------------------------------
    runs = []
    frame_hashes = {}
    for rep in range(2):
        load("red_berry_thrown.sav")
        assert rd(INFLIGHT, 1)[0] == 1, "expected one in-flight projectile"
        traj = []
        for f in range(20):
            c.call("emulator.advanceFrames", {"frames": 1})
            c.call("debugger.pause", {})
            traj.append(list(struct.unpack("<iii", rd(PROJ_XYZ, 12))))
            if rep == 0 and f in (2, 8, 14):
                snap = c.call("gpu.frameSnapshot",
                              {"buffer": "displayed", "format": "raw16"})
                frame_hashes[str(f)] = sha_payload(snap)
        runs.append(traj)
    dy = [b[1] - a[1] for a, b in zip(runs[0], runs[0][1:])]
    gravity = [b - a for a, b in zip(dy, dy[1:])]
    out["arc_sentinel"] = {
        "save": "red_berry_thrown.sav",
        "projectile_slot": PROJ_SLOT, "projectile_xyz_addr": f"0x{PROJ_XYZ:08X}",
        "trajectory": runs[0],
        "deterministic_across_reloads": runs[0] == runs[1],
        "per_frame_dy": dy, "gravity_per_frame": gravity,
        "gravity_constant_estimate": (sorted(gravity)[len(gravity) // 2]
                                      if gravity else None),
        "flight_frame_hashes": frame_hashes,
    }
    print(f"[arc] deterministic={runs[0] == runs[1]} "
          f"gravity~{out['arc_sentinel']['gravity_constant_estimate']}/f^2 "
          f"hashes={len(frame_hashes)}")

    # ---- pool census per anchor ----------------------------------------------
    census = {}
    for label, sav in IDENTITY_ANCHORS:
        load(sav)
        buf, active = pool_read()
        walked = [a for a in active if a["enabled"]]
        census[label] = {"save": sav,
                         "typed_slots": len(active),
                         "walker_enabled_slots": len(walked),
                         "active_slots": len(active),   # legacy alias = typed
                         "slots": active,
                         "pool_sha256": hashlib.sha256(buf).hexdigest()}
        print(f"[pool] {label}: typed={len(active)} walker-enabled={len(walked)}")
    out["pool_census"] = census

    # ---- capacity stress -------------------------------------------------------
    load("red_berry_thrown.sav")
    max_inflight, counts = 0, []
    for burst in range(40):
        c.call("emulator.setControllerState", {"port": 0, "buttons": {"square": True}})
        c.call("emulator.advanceFrames", {"frames": 3})
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 9})
        c.call("debugger.pause", {})
        infl = rd(INFLIGHT, 1)[0]
        max_inflight = max(max_inflight, infl)
        if burst % 5 == 4:
            _, active = pool_read()
            counts.append({"after_throws": burst + 1, "in_flight": infl,
                           "active_slots": len(active)})
    c.call("emulator.clearControllerState", {"port": 0})
    st = c.call("debugger.status", {})
    final = {"scene": struct.unpack("<I", rd(0x80082504, 4))[0],
             "guest_valid": st.get("valid", True)}
    out["capacity_stress"] = {
        "save": "red_berry_thrown.sav", "throw_attempts": 40,
        "max_in_flight_observed": max_inflight,
        "samples": counts, "post_stress": final,
        "stable": bool(final["guest_valid"]) and final["scene"] == 1,
        "note": "repeated-use stress; TRUE capacity behavior is the ring allocator "
                "observation below (cursor wraps at 0x40 in native gameplay)",
    }
    print(f"[stress] max in-flight={max_inflight} post={final}")

    # ---- remaining native-action attempts --------------------------------------
    attempts = {}

    def player_probe():
        return {"xyz": list(struct.unpack("<iii", rd(0x800A6500, 12))),
                "grounded": rd(0x800A6582, 1)[0],
                "state_block": rd(0x800A6580, 0x20).hex()}

    # seed interactions at the Training anchor: Square at each censused record
    load("phase3_pristine_training_gameplay_i5.sav")
    recs = []
    buf = rd(0x8009FE04, 0x84 * 10)
    for i in range(10):
        rid, x, y, z = struct.unpack_from("<Iiii", buf, i * 0x84)
        if (rid == 0 and x == 0 and y == 0 and z == 0) or rid > 0x2000:
            break
        recs.append((i, rid, x, y, z))
    seed_results = []
    for i, rid, x, y, z in recs:
        load("phase3_pristine_training_gameplay_i5.sav")
        for addr, val in ((0x800A6500, x), (0x800A6510, x),
                          (0x800A6504, y), (0x800A6514, y),
                          (0x800A6508, z), (0x800A6518, z)):
            wr32(addr, val)
        c.call("emulator.advanceFrames", {"frames": 30})   # settle/approach
        c.call("debugger.pause", {})
        before = player_probe()
        c.call("emulator.setControllerState", {"port": 0, "buttons": {"square": True}})
        c.call("emulator.advanceFrames", {"frames": 20})
        c.call("debugger.pause", {})
        during = player_probe()
        c.call("emulator.clearControllerState", {"port": 0})
        c.call("emulator.advanceFrames", {"frames": 20})
        c.call("debugger.pause", {})
        after = player_probe()
        changed = before["state_block"] != during["state_block"]
        seed_results.append({"record": {"index": i, "id": rid, "xyz": [x, y, z]},
                             "before": before, "during_square": during,
                             "after_release": after,
                             "state_block_changed": changed})
    attempts["training_seed_square"] = seed_results
    print(f"[actions] training square-at-record attempts: {len(seed_results)} "
          f"({sum(1 for s in seed_results if s['state_block_changed'])} with state change)")

    # downhill slide attempt at the canyon anchor
    load("level04.sav")
    c.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    c.call("emulator.advanceFrames", {"frames": 40})
    c.call("debugger.pause", {})
    pre = player_probe()
    # double-tap X then hold while moving
    for press in (True, False, True):
        c.call("emulator.setControllerState",
               {"port": 0, "buttons": {"up": True, "cross": press}})
        c.call("emulator.advanceFrames", {"frames": 4})
    c.call("emulator.advanceFrames", {"frames": 40})
    c.call("debugger.pause", {})
    mid = player_probe()
    c.call("emulator.clearControllerState", {"port": 0})
    attempts["canyon_slide_attempt"] = {
        "anchor": "level04.sav", "input": "run 40f, double-tap X (4f cadence), hold 40f",
        "before": pre, "after": mid,
        "state_block_changed": pre["state_block"] != mid["state_block"],
        "note": "recognizer-level attempt; slope location not verified — a null "
                "result bounds the fixture need, it does not prove absence",
    }
    print(f"[actions] canyon slide attempt: state change="
          f"{attempts['canyon_slide_attempt']['state_block_changed']}")
    out["action_attempts"] = attempts

    doc = {
        "_comment": "Phase-2 final gate items: berry-arc sentinel (projectile pool "
                    "slot trajectory + gravity fit), contact-pool census/digest per "
                    "anchor (direct missing-pickup sentinel), pool-capacity stress, "
                    "remaining native-action attempts. Regenerate: "
                    "tools/phase2_pool_arc_oracle.py.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial")},
        "repro_profile": repro_profile,
        **out,
    }
    path = ROOT / "analysis" / "phase2_pool_arc_oracle.json"
    path.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[pool_arc] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
