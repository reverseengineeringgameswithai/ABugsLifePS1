#!/usr/bin/env python3
"""Phase-4 D18/F09: Thud's mover-VM "phase/attack FSM" — resolution artifact.

Offline mode (default): regenerates the deterministic sections of
analysis/phase4_d18_thud_vm_fsm.json from committed sources —
  - programs #19..#23 (0x80077798..0x8007782B) extracted from the committed
    E07 corpus (analysis/phase4_e07_static.json),
  - the campaign-wide program-usage join over the committed phase-1 census
    (+0x70 pointers per level anchor),
  - the row-address correction (0x800777A6 is the jump_back IP inside program
    #19, recorded live in phase3_thud.json as Thud's parked VM IP — it is NOT
    a program entry; the 40-entry table has no such entry).
Live sections (idle watch / pokes / defeat / proximity / fight replay poll)
carry their own provenance inside the artifact and re-run via --live.

Usage: python3 tools/phase4_d18_thud_vm_fsm.py [--check | --write] \
           [--artifact analysis/phase4_d18_thud_vm_fsm.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROGRAM_ENTRIES = ["0x80077798", "0x800777ac", "0x800777d4", "0x800777f8", "0x80077814"]
PROGRAM_NAMES = {
    "0x80077798": "p19_parked_idle",
    "0x800777ac": "p20_stationary_two_clip_cycle",
    "0x800777d4": "p21_gated_wander(park_arrive_test)",
    "0x800777f8": "p22_wander",
    "0x80077814": "p23_authored_path_patrol",
}


def find_programs(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("programs", "decoded_programs") and isinstance(v, list):
                return v
            r = find_programs(v)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = find_programs(v)
            if r is not None:
                return r
    return None


def offline_sections():
    e07 = json.loads((ROOT / "analysis/phase4_e07_static.json").read_text())
    corpus = find_programs(e07)
    programs = {}
    entries_in_table = set()
    for p in corpus:
        entries_in_table.add(str(p["entry"]).lower())
        if str(p["entry"]).lower() in PROGRAM_ENTRIES:
            programs[str(p["entry"]).lower()] = {
                "name": PROGRAM_NAMES[str(p["entry"]).lower()],
                "instruction_count": p["instruction_count"],
                "instructions": [
                    {"ip": i["ip"], "name": i["name"], "operands": i.get("operands", [])}
                    for i in p["instructions"]],
            }
    assert len(programs) == 5, sorted(programs)
    assert "0x800777a6" not in entries_in_table  # the row's address is NOT an entry

    thud = json.loads((ROOT / "analysis/phase3_thud.json").read_text())
    observed_ip = thud["boss_identity"]["mover_vm_ip_at_0x70"].lower()
    assert observed_ip == "0x800777a6"

    census = json.loads((ROOT / "analysis/phase1_kind_actor_census.json").read_text())
    ranges = [(int(e, 16), n) for e, n in PROGRAM_NAMES.items()]
    bounds = sorted(int(e, 16) for e in PROGRAM_ENTRIES) + [0x8007782C]
    usage = {}
    for lvl, rec in census.get("levels", {}).items():
        for r in rec.get("actor_records", []):
            p = r.get("pointer_fields", {}).get("+0x70")
            if not p:
                continue
            v = int(p, 16)
            for i in range(5):
                if bounds[i] <= v < bounds[i + 1]:
                    key = PROGRAM_NAMES[f"0x{bounds[i]:08x}"]
                    usage.setdefault(key, []).append({"actor_id": r["id"], "level": lvl})
    for k in usage:
        usage[k] = sorted(usage[k], key=lambda d: (d["actor_id"], d["level"]))

    return {
        "row_address_correction": {
            "claim": "D18/F09's 0x800777A6 is NOT a program entry: it is the jump_back "
                     "instruction inside program #19 (0x80077798, parked idle). "
                     "phase3_thud.json recorded it as Thud's LIVE VM IP "
                     "(boss_identity.mover_vm_ip_at_0x70) and the rows transcribed "
                     "the IP as if it were a program.",
            "observed_ip_source": "analysis/phase3_thud.json boss_identity",
        },
        "programs": programs,
        "census_program_usage": usage,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify the artifact's offline sections match committed sources")
    ap.add_argument("--write", action="store_true",
                    help="rewrite the artifact's offline sections in place")
    ap.add_argument("--artifact", default=str(ROOT / "analysis/phase4_d18_thud_vm_fsm.json"))
    args = ap.parse_args()

    sections = offline_sections()
    art_path = Path(args.artifact)
    if args.write:
        art = json.loads(art_path.read_text()) if art_path.exists() else {}
        art.update(sections)
        art_path.write_text(json.dumps(art, indent=1) + "\n")
        print(f"wrote offline sections into {art_path}")
        return 0
    art = json.loads(art_path.read_text())
    ok = True
    for key, val in sections.items():
        if art.get(key) != val:
            ok = False
            print(f"MISMATCH in section: {key}")
    print("offline sections match committed sources" if ok else "CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
