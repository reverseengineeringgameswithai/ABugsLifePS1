#!/usr/bin/env python3
"""Phase-1 live censuses: contact-object kinds + chunk-31 actor records, per level.

Closes the two remaining Phase-1 exit-gate items (registry rows E06/C11 and D01/E08):
  * KIND CENSUS  — dump the contact-object kind->descriptor pointer table at
    0x80096B98 (kinds 0..49; extent verified live: contiguous plausible pointers
    end at kind 49) plus each referenced 0xC-byte descriptor.
  * ACTOR CENSUS — dump the in-RAM chunk-31 spawn-record table at 0x8009FE04
    (FIXED BSS buffer, verified across levels; stride 0x84; header = u32 id,
    s32 X,Y,Z world coords (<<5 applied); record tails hold pointers incl.
    mover-VM program addresses in 0x8007745C+).

Roles are NOT guessed: ids/kinds get a Canon binding only where one already
exists; everything else is recorded as explicit unknown.

Requires the isolated debugger instance started by the operator/session:
    launch_debugger_instance.sh start --config-dir /tmp/duckstation-debugger-phase1 \
        --port 23470 --token debugger-1000 --disc "<pristine>.cue"

Usage: python3 tools/phase1_census.py [--port 23470] [--out analysis/phase1_kind_actor_census.json]
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

KIND_TABLE = 0x80096B98
KIND_PROBE = 256          # slots probed to DERIVE the extent (recorded, not assumed)
RECORDS_BASE = 0x8009FE04
RECORD_STRIDE = 0x84
RECORD_CAP = 160
RAM_LO, RAM_HI = 0x80000000, 0x80200000

# Boss/setpiece movie anchors probed IN ADDITION to the level saves, so the
# Thud/hopper/bird evidence regenerates with the census instead of living in a
# hand-appended addendum. Each is compared against its owning level's census.
BOSS_ANCHORS = [
    ("thud_boss_movie.movie.sav", "stage09_bug_bar",
     "mid-Thud-fight anchor; tests whether the Bug Bar arena populates chunk-31"),
    ("hopper_boss.movie.sav", "stage15_canyon_showdown",
     "Hopper showdown anchor; corroboration for the stage-15 census"),
    ("bird.movie.sav", "stage06_birdnest",
     "bird encounter anchor; corroboration for the stage-6 census"),
]

# Pristine level anchors (save states on the pristine image).
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

# Canon bindings that ALREADY exist (no new guesses here).
KNOWN_KINDS = {
    0x1D: "sprite descriptor class (pickup-render Canon)",
    0x22: "gold-berry drop type 34 (golddrop Canon)",
    0x26: "mercy health leaf type 38 (player-health Canon)",
    0x30: "dewdrop telescope (green-gem Canon)",
}
KNOWN_ACTOR_IDS = {
    14: "Dot guide NPC (chunk-31 type 0x070E id 14, Canon dot-guide-npc)",
    16: "Thumper boss (Canon thumper-boss-solved)",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=23470)
    ap.add_argument("--token", default="debugger-1000")
    ap.add_argument("--out", default=str(ROOT / "analysis" / "phase1_kind_actor_census.json"))
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

    def read_records(cap: int = RECORD_CAP) -> list:
        """Chunk-31 spawn records at the fixed buffer until the termination rule."""
        buf = rd(RECORDS_BASE, RECORD_STRIDE * cap)
        records = []
        for i in range(cap):
            rec = buf[i * RECORD_STRIDE:(i + 1) * RECORD_STRIDE]
            rid, x, y, z = struct.unpack_from("<Iiii", rec, 0)
            if rid == 0 and x == 0 and y == 0 and z == 0:
                break
            if rid > 0x2000 or abs(x) > 0x400000 or abs(y) > 0x400000 or abs(z) > 0x400000:
                break
            ptr_fields = {f"+0x{off:02x}": f"0x{w:08x}"
                          for off in range(0x10, RECORD_STRIDE, 4)
                          for (w,) in (struct.unpack_from("<I", rec, off),)
                          if RAM_LO <= w < RAM_HI}
            records.append({"index": i, "addr": f"0x{RECORDS_BASE + i*RECORD_STRIDE:08x}",
                            "id": rid, "xyz": [x, y, z], "pointer_fields": ptr_fields})
        return records

    def probe_kind_slots() -> list:
        """Raw probe of KIND_PROBE table slots. The extent is NOT derived per level
        (past-end BSS sometimes contains plausible-looking pointers whose count
        varies by level); it is derived AFTER the sweep by cross-level intersection:
        a real table has one size, so the extent is the largest k with slots 0..k-1
        plausible on EVERY level. Raw slots are recorded so the proof reproduces."""
        tab = rd(KIND_TABLE, KIND_PROBE * 4)
        return [struct.unpack_from("<I", tab, i * 4)[0] for i in range(KIND_PROBE)]

    levels = {}
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

        # player position corroborates the level identity
        px, py, pz = struct.unpack("<iii", rd(0x800A6500, 12))

        # ---- actor census: chunk-31 spawn records --------------------------
        records = read_records()

        # ---- kind census: raw slot probe + descriptors for plausible slots --
        raw_ptrs = probe_kind_slots()
        kinds = {}
        for k in range(KIND_PROBE):
            p = raw_ptrs[k]
            if RAM_LO <= p < RAM_HI:
                kinds[str(k)] = {"ptr": f"0x{p:08x}", "descriptor_hex": rd(p, 0xC).hex()}
        first_break = next((i for i in range(KIND_PROBE)
                            if not (RAM_LO <= raw_ptrs[i] < RAM_HI)), KIND_PROBE)

        levels[label] = {
            "save": sav, "save_sha256": sha256_file(path),
            "player_xyz": [px, py, pz],
            "actor_records": records,
            "actor_id_histogram": {},
            "kind_table": kinds,          # trimmed to the cross-level extent below
            "kind_slot_first_break": first_break,
            "kind_raw_slots": [f"0x{p:08x}" for p in raw_ptrs],
        }
        hist: dict = {}
        for rec in records:
            hist[str(rec["id"])] = hist.get(str(rec["id"]), 0) + 1
        levels[label]["actor_id_histogram"] = dict(sorted(hist.items(), key=lambda kv: int(kv[0])))
        print(f"[census] {label}: {len(records)} actor records, ids "
              f"{sorted({r['id'] for r in records})}")

    # ---- boss/setpiece anchors: regenerable addendum probes -----------------
    addendum = {}
    for sav, owner, why in BOSS_ANCHORS:
        path = ROOT / sav
        if not path.exists():
            addendum[sav] = {"error": "save missing"}
            continue
        inspect_state_before_load(c, path, media_identity)
        r = c.call("emulator.loadState", {"path": str(path), "pause_after_load": True})
        if not r.get("loaded") or r.get("game_serial") != "SCUS-94288":
            addendum[sav] = {"error": f"loadState failed/mismatch: {r}"}
            continue
        recs = read_records()
        ids = sorted({rec["id"] for rec in recs})
        owner_ids = sorted({rec["id"] for rec in
                            levels.get(owner, {}).get("actor_records", [])})
        addendum[sav] = {
            "save_sha256": sha256_file(path), "purpose": why,
            "records": len(recs), "ids": ids,
            "owner_level": owner, "owner_level_ids": owner_ids,
            "matches_owner_census": ids == owner_ids,
        }
        print(f"[census] anchor {sav}: {len(recs)} records, ids {ids} "
              f"(owner match: {ids == owner_ids})")
    thud = addendum.get("thud_boss_movie.movie.sav", {})
    addendum["conclusion_bounded"] = (
        "Bug Bar authors no chunk-31 spawn records at either the level save or the "
        "mid-fight anchor; Thud is not sourced from this table (consistent with Canon "
        "trigger-spawned setpieces). Thud's actor source remains an explicit unknown "
        "(registry row F09)." if thud.get("records") == 0 else
        "REVIEW: the mid-Thud anchor now shows chunk-31 records — update row F09.")

    # cross-level rollups + explicit-unknown classification
    all_ids = sorted({r["id"] for lv in levels.values()
                      for r in lv.get("actor_records", [])})
    # cross-level kind-table extent: a real table has ONE size, so the extent is
    # bounded by the first level whose next slot stops being a plausible pointer.
    # Slots beyond it that look plausible on SOME levels are past-end BSS noise —
    # recorded per level (kind_raw_slots / rejected list) so the proof reproduces.
    breaks = {lbl: lv["kind_slot_first_break"] for lbl, lv in levels.items()
              if "kind_slot_first_break" in lv}
    extent = min(breaks.values())
    rejected_past_end = {}
    for lbl, lv in levels.items():
        if "kind_raw_slots" not in lv:
            continue
        rej = [{"slot": i, "ptr": lv["kind_raw_slots"][i]}
               for i in range(extent, KIND_PROBE)
               if RAM_LO <= int(lv["kind_raw_slots"][i], 16) < RAM_HI]
        if rej:
            rejected_past_end[lbl] = rej
        # trim the per-level census to the proven extent; past-end descriptor
        # reads stay out of the kind census
        lv["kind_table"] = {k: v for k, v in lv["kind_table"].items()
                            if int(k) < extent}
    kind_extent_proof = {
        "probed_slots_per_level": KIND_PROBE,
        "rule": "cross-level intersection: extent = min over levels of the first "
                "non-plausible slot index; plausible = pointer in 0x80000000..0x80200000",
        "first_break_per_level": breaks,
        "derived_extent": extent,
        "levels_breaking_exactly_at_extent": sorted(
            l for l, b in breaks.items() if b == extent),
        "rejected_past_end_slots_by_level": rejected_past_end,
        "note": "past-end slot plausibility VARIES by level (a real table cannot), "
                "which is itself evidence those slots are not table entries",
    }
    kinds_nonnull = sorted({int(k) for lv in levels.values()
                            for k, v in lv.get("kind_table", {}).items()
                            if v.get("descriptor_hex")})
    doc = {
        "_comment": "Phase-1 live censuses (contact-object kinds + chunk-31 actor "
                    "records) from pristine save states on the verified retail image. "
                    "Roles bound ONLY where Canon already binds them; all other ids/"
                    "kinds are explicit unknowns. Regenerate: tools/phase1_census.py "
                    "against an isolated debugger instance with the pristine disc.",
        "generated": date.today().isoformat(),
        "media": {"serial": status.get("game_serial"), "title": status.get("game_title")},
        "method": {
            "kind_table": f"0x{KIND_TABLE:08x} (extent derived by cross-level "
                          "intersection; see kind_extent_proof)",
            "records_base": f"0x{RECORDS_BASE:08x} (fixed BSS buffer, verified across levels)",
            "record_stride": hex(RECORD_STRIDE),
            "record_header": "u32 id, s32 X, s32 Y, s32 Z (world, <<5 applied)",
            "termination": "id==0 with zero XYZ, or implausible id/coords; cap 160",
        },
        "kind_extent_proof": kind_extent_proof,
        "addendum_probes": addendum,
        "actor_ids_observed": all_ids,
        "actor_ids_with_canon_binding": {str(k): v for k, v in KNOWN_ACTOR_IDS.items() if k in all_ids},
        "actor_ids_unknown_role": [i for i in all_ids if i not in KNOWN_ACTOR_IDS],
        "kinds_with_descriptors": kinds_nonnull,
        "kinds_with_canon_binding": {str(k): v for k, v in KNOWN_KINDS.items() if k in kinds_nonnull},
        "kinds_unknown_role": [k for k in kinds_nonnull if k not in KNOWN_KINDS],
        "levels": levels,
    }
    out = Path(args.out)
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[census] wrote {out}")
    print(f"  actor ids observed: {all_ids}")
    print(f"  unknown-role actor ids: {doc['actor_ids_unknown_role']}")
    print(f"  kinds with descriptors: {len(kinds_nonnull)}; unknown-role kinds: "
          f"{len(doc['kinds_unknown_role'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
