#!/usr/bin/env python3
"""Phase-4 E05: LIVE confirmation of the per-id model pointer registry.

Static basis (tools/phase4_e05_model_binding_extract.py): level_chunk_loader
persists each loaded model's pointer at 0x800A6300 + 4*id under a first-load
guard; ids 1..41 come from the pool dispatch (paths hardcoded per id), slot 0 is
the scene-selected Flik variant, slots 104..117 are the plant models (the Canon
plant table 0x800A649C+4N is the same storage).

This pass loads every per-level save and asserts, per level:
  A. pointer[0] (Flik) is a valid RAM pointer;
  B. every distinct chunk-31 pool id in 1..41 has pointer[id] != 0;
  C. all non-null slots point into main RAM;
and records the scene word [0x80082504] (Flik-variant selector), the observed
non-null slot set (loads can be a superset of pool ids), and each pointed-to
model header's s16 at +4 (skeleton-bank slot, per the post-load code at
0x8005e2ac's cases).

Poll-only (loadState + readMemory): safe on any fixture regardless of CPU mode.

Usage: python3 tools/phase4_e05_live_model_pointers.py --port 23700 \
           [--token debugger-1000] [--out analysis/phase4_e05_model_pointers_live.json]
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
sys.path.insert(0, str(ROOT / "tools"))

from live_session_provenance import (inspect_state_before_load,
                                     verified_media_identity)

POINTER_ARRAY = 0x800A6300
ANM_ARRAY = 0x800A2188      # second per-id registry, consulted by level_chunk_loader
                            # (lw a3,8584($at)) on the first-load path. Probed live:
                            # where non-null it EQUALS the 0x800A6300 model pointer;
                            # null for id 11 (seed) everywhere and for slot 0 (Flik)
                            # on scenes {4,5,7,9,12}. Role attribution OPEN (writer
                            # unattributed) — do not name it an .ANM table.
POINTER_SLOTS = 128
POOL_BASE = 0x8009FD80
POOL_STRIDE = 0x84
POOL_SLOTS = 64
SCENE_WORD = 0x80082504
RAM_LO, RAM_HI = 0x80000000, 0x80200000

SAVES = [
    ("training", "phase3_pristine_training_gameplay_i5.sav"),
    ("stage01_anthill", "level01.sav"),
    ("stage02_tunnels", "level02.sav"),
    ("stage03_council_chamber", "level03.sav"),
    ("stage04_cliffside_canyon", "level04.sav"),
    ("stage05_riverbed_run", "level05.sav"),
    ("stage06_birdnest", "level_06.sav"),
    ("stage07_city_entrance", "level_07.sav"),
    ("stage08_city_square", "level_08.sav"),
    ("stage09_bug_bar", "level_09.sav"),
    ("stage10_clover_forest", "level_10.sav"),
    ("stage11_the_tree", "level_11.sav"),
    ("stage12_battle_arena", "level_12.sav"),
    ("stage13_anthill_two", "level_13.sav"),
    ("stage14_riverbed_flight", "level_14.sav"),
    ("stage15_canyon_showdown", "level_15.sav"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=23700)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e05_model_pointers_live.json"))
    args = ap.parse_args()

    from duckstation_debug_client import DebuggerClient
    c = DebuggerClient("127.0.0.1", args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(60)

    def rd(addr: int, n: int) -> bytes:
        return bytes.fromhex(c.call("debugger.readMemory",
                                    {"address": "0x%08x" % addr, "length": n})["hex"])

    status = c.call("debugger.status", {})
    assert status.get("game_serial") == "SCUS-94288", f"wrong media: {status}"
    media_identity = verified_media_identity(c, status)

    static = json.loads((ROOT / "analysis/phase4_e05_model_binding_static.json").read_text())
    id_to_path = {r["actor_id"]: r["path"] for r in static["table1_actor_models"]}

    levels, failures = {}, []
    for label, sav in SAVES:
        path = ROOT / sav
        if not path.exists():
            levels[label] = {"error": f"save missing: {sav}"}
            continue
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        if not r.get("loaded") or r.get("game_serial") != "SCUS-94288":
            levels[label] = {"error": f"loadState failed/mismatch: {r}"}
            continue

        scene = struct.unpack("<I", rd(SCENE_WORD, 4))[0]
        pool = rd(POOL_BASE, POOL_STRIDE * POOL_SLOTS)
        pool_ids = []
        for i in range(POOL_SLOTS):
            rid = struct.unpack_from("<I", pool, i * POOL_STRIDE)[0]
            if 1 <= rid <= 41:
                pool_ids.append(rid)
        distinct_ids = sorted(set(pool_ids))

        ptrs = struct.unpack("<%dI" % POINTER_SLOTS, rd(POINTER_ARRAY, POINTER_SLOTS * 4))
        nonnull = {i: p for i, p in enumerate(ptrs) if p != 0}

        anm = struct.unpack("<%dI" % POINTER_SLOTS, rd(ANM_ARRAY, POINTER_SLOTS * 4))
        anm_nonnull = sorted(i for i, p in enumerate(anm) if p != 0)
        anm_only = sorted(set(anm_nonnull) - set(nonnull))
        model_only = sorted(set(nonnull) - set(anm_nonnull))
        second_eq = sorted(i for i in anm_nonnull if i in nonnull and anm[i] == nonnull[i])
        second_neq = sorted(i for i in anm_nonnull if i in nonnull and anm[i] != nonnull[i])

        bad_range = {i: f"0x{p:08x}" for i, p in nonnull.items()
                     if not (RAM_LO <= p < RAM_HI)}
        missing = [i for i in distinct_ids if ptrs[i] == 0]
        flik_ok = 0 in nonnull and not (0 in bad_range)

        # model header probe: s16 at ptr+4 = skeleton-bank slot (post-load code fact)
        headers = {}
        for i in sorted(nonnull):
            p = nonnull[i]
            if RAM_LO <= p < RAM_HI - 8:
                skel = struct.unpack("<h", rd(p + 4, 2))[0]
                headers[str(i)] = {"ptr": f"0x{p:08x}", "skel_slot": skel,
                                   "path": id_to_path.get(i)}

        ok = flik_ok and not missing and not bad_range
        if not ok:
            failures.append(label)
        levels[label] = {
            "save": sav, "save_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scene_word": scene,
            "pool_distinct_ids": distinct_ids,
            "pool_id_count": len(pool_ids),
            "nonnull_slots": sorted(nonnull),
            "assert_flik_slot0": flik_ok,
            "assert_pool_ids_have_pointers": not missing,
            "missing_pointers_for_pool_ids": missing,
            "non_ram_pointers": bad_range,
            "slot_details": headers,
            "anm_array_nonnull_slots": anm_nonnull,
            "anm_without_model": anm_only,
            "model_without_anm": model_only,
            "second_registry_equal_model_ptr": second_eq,
            "second_registry_differs_model_ptr": second_neq,
            "ok": ok,
        }
        print(f"{label}: scene={scene} pool_ids={distinct_ids} "
              f"nonnull={sorted(nonnull)} ok={ok}")

    out = {
        "_comment": "Phase-4 E05 live confirmation: model pointer registry "
                    "0x800A6300+4*id, per level. Regenerate: "
                    "tools/phase4_e05_live_model_pointers.py",
        "generated": str(date.today()),
        "media_identity": media_identity,
        "static_artifact_exe_sha256": static["exe_sha256"],
        "levels": levels,
        "failing_levels": failures,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {args.out}; failing levels: {failures or 'none'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
