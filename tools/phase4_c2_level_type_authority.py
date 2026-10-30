#!/usr/bin/env python3
"""C2: derive the eight-type level taxonomy from a PRE-OUTCOME authority, or say it can't be.

The adjudicated bar: "a pre-outcome row/Canon-owned mapping... labels chosen from these
outcomes would not" satisfy it. The authority used here is the frozen F-row names in
analysis/mechanics_baseline.yaml — committed a month before the breadth pass existed, so
they cannot encode its outcomes.

Method: DECLARED keyword rules applied mechanically to the frozen text, matched substring
recorded per hit so every label is auditable back to pre-outcome words. Where the text
supports no rule, the cell is UNKNOWN — accepted even though it keeps campaign_breadth
not_met. A level may carry several types. `normal` is the declared residual (no match).

Outcome-independence: the rules reference only the frozen names; unknowns are kept
rather than filled. This procedure can and does fail to demonstrate coverage.

Usage: python3 tools/phase4_c2_level_type_authority.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# type -> case-sensitive keywords over the frozen row NAME text
RULES = {
    "bonus": ["Bonus"],
    "boss": ["defeat Thumper", "defeat Thud", "defeat Molt", "drive Hopper"],
    "chase": ["chase"],
    "city": ["City"],
    "traversal-special": ["flight", "climbing", "swinging"],
    # interior / exterior: NO textual criterion exists in the frozen names.
}
UNDERIVABLE = {
    "interior": "no frozen text names interiority; a data-derived criterion exists in "
                "principle (chunk-29 backdrop/sky content per level) but is unbuilt",
    "exterior": "same as interior — geometry property, not named in any frozen text",
}
# breadth session label per F-row (identity join, not classification)
SESSION = {
    "F00_training": "LEVEL00_Training", "F01_anthill": "LEVEL01_Anthill",
    "F02_tunnels": "LEVEL02_Tunnels", "F03_council_chamber": "LEVEL03_CouncilChamber",
    "F04_cliffside_canyon": "LEVEL04_Cliffside", "F05_riverbed_run": "LEVEL05_RiverbedCanyon",
    "F06_birdnest": "LEVEL06", "F07_city_entrance": "LEVEL07_CITYENTRANCE",
    "F08_city_square": "LEVEL08_CITYSQUARE", "F09_bug_bar": "LEVEL09_BUGBAR",
    "F10_clover_forest": "LEVEL10_CLOVERFOREST", "F11_the_tree": "LEVEL11_THETREE",
    "F12_battle_arena": "LEVEL12_BATTLEARENA", "F13_anthill_two": "LEVEL13_ANTHILLPT2",
    "F14_riverbed_flight": "LEVEL14_RIVERBEDFLIGHT", "F15_canyon_showdown": "LEVEL15",
    "F16_bonus1_spiders": "F16_Bonus01", "F17_bonus2_mushrooms": "F17_Bonus02",
    "F18_bonus3_grasshoppers": "F18_Bonus03",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_c2_level_type_authority.json"))
    args = ap.parse_args()

    base = ROOT / "analysis/mechanics_baseline.yaml"
    doc = yaml.safe_load(base.read_text())
    rows = doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc
    names = {r["id"]: r["name"] for r in rows
             if isinstance(r, dict) and r.get("id") in SESSION}

    mapping, per_type = {}, {t: [] for t in list(RULES) + ["normal"]}
    for rid, name in sorted(names.items()):
        hits = []
        for t, kws in RULES.items():
            for kw in kws:
                if kw in name:
                    hits.append({"type": t, "matched": kw})
                    per_type[t].append(rid)
                    break
        if not hits:
            hits = [{"type": "normal", "matched": None,
                     "rule": "declared residual: no keyword matched"}]
            per_type["normal"].append(rid)
        mapping[rid] = {"frozen_name": name, "session": SESSION[rid], "types": hits}

    demonstrated = {t: sorted(set(v)) for t, v in per_type.items() if v}
    result = {
        "derivable_types": sorted(demonstrated),
        "underivable_types": UNDERIVABLE,
        "taxonomy_coverage_demonstrated": False,
        "why": "6 of 8 types derive mechanically from the frozen pre-outcome text; "
               "interior and exterior have no textual authority, so the eight-type bar "
               "is NOT demonstrated. campaign_breadth stays not_met. The named path "
               "forward is a DATA-derived criterion (chunk-29 backdrop classification "
               "per level), which would be outcome-independent by construction.",
    }
    out = {
        "_comment": "C2 element: eight-type taxonomy derived from the frozen "
                    "mechanics-baseline F-row names via declared keyword rules — a "
                    "pre-outcome authority. Regenerate: tools/phase4_c2_level_type_authority.py",
        "schema": "abl-phase4-c2-level-type-authority/1",
        "generated": date.today().isoformat(),
        "authority": {"promotes_row_or_dimension": False, "requires_fresh_verifier": True,
                      "source": "analysis/mechanics_baseline.yaml F-row names (frozen "
                                "pre-outcome)",
                      "source_sha256": hashlib.sha256(base.read_bytes()).hexdigest()},
        "rules": RULES,
        "mapping": mapping,
        "types_with_at_least_one_level": demonstrated,
        "result": result,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"[c2] derivable: {sorted(demonstrated)}")
    print(f"[c2] underivable: {sorted(UNDERIVABLE)} -> coverage NOT demonstrated")
    for t, ls in sorted(demonstrated.items()):
        print(f"  {t:18s} {ls}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
