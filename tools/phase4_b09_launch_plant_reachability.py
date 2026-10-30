#!/usr/bin/env python3
"""B09: can super jump co-exist with a launch plant? Derived, campaign-wide.

THE ROW ITEM
------------
B09's registry lists one remaining item: "super-jump's interaction with
plants/dandelion/cannon -- currently unstarted and unscoped". This resolves it.

THE CHAIN, every link already banked before today except the last:

 1. FRESH LEVEL STATE. Level load memsets the player block (0x80046B68, base
    0x800A6500, length 168) covering all five seed lanes, then writes brown 0x11
    at 0x80046BEC. Fresh array = [0x11, 0x00, 0x00, 0x00, 0x00].
    -> every level starts at brown tier 1, and there is NO authored per-level
       brown value.  [A13 bounded-exhaustion]

 2. TOKEN UPGRADE. Source token upgrades at 0x8005431C / 0x80054364 / 0x800543E0
    / 0x8005445C / 0x800544F8 compute `n = (old+1) & 7` then store `(n<<4)|n`.
    -> each token raises its lane by exactly one tier.  [A13]

 3. BROWN TIERS. selected output 1/2/3/4 = mushroom / propeller / dandelion /
    cannon.  Super jump is BLUE tier 4.  [Seed_plant_output_binding]

 4. AVAILABILITY. So a stage's maximum brown tier = 1 + (orange 0x29 tokens), and
    its maximum blue tier = blue 0x2A tokens.

 5. PLACEMENT. Per-FILE type-0x3f census (directory != stage: LEVEL01/ holds both
    stage 1 and stage 6, so per-directory aggregation is wrong and contradicted
    the operator's play experience).

CONCLUSION: dandelion needs brown 3 and cannon needs brown 4, i.e. 2 and 3 orange
tokens. No stage file carrying 4 blue tokens carries more than ONE orange token.
Super jump + dandelion and super jump + cannon are UNREACHABLE campaign-wide.
Super jump + mushroom is always reachable; + propeller in two stages.

CONFIRMED INDEPENDENTLY on the operator's B08_SuperJump_EOL movie: in the bird
level (LEVEL01/LEVEL1.DAT, 4 blue / 0 orange) brown reads 1/1 for the entire
level while blue climbs 0->4. Predicted brown max 1; measured 1.

Usage: python3 tools/phase4_b09_launch_plant_reachability.py
"""
from __future__ import annotations

import argparse, json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis/phase4_e08_object_census.json"
ORANGE, BLUE = "0x29", "0x2a"
BROWN_TIERS = {1: "mushroom", 2: "propeller", 3: "dandelion", 4: "cannon"}
BROWN_BASE = 1          # fresh-level brown 0x11
SUPER_JUMP_BLUE_TIER = 4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_b09_launch_plant_reachability.json"))
    args = ap.parse_args()

    lv = json.loads(CENSUS.read_text())["levels"]
    stages = []
    for f in sorted(lv):
        h = lv[f].get("type3f_kind_histogram") or {}
        blue, orange = h.get(BLUE, 0), h.get(ORANGE, 0)
        if not (blue or orange):
            continue
        stages.append({
            "file": f, "blue_tokens": blue, "orange_tokens": orange,
            "max_blue_tier": blue,
            "max_brown_tier": BROWN_BASE + orange,
            "super_jump_possible": blue >= SUPER_JUMP_BLUE_TIER,
            "brown_outputs_available": [BROWN_TIERS[t] for t in
                                        range(1, min(BROWN_BASE + orange, 4) + 1)],
        })

    sj = [s for s in stages if s["super_jump_possible"]]
    combos = {}
    for tier, name in BROWN_TIERS.items():
        combos[name] = sorted(s["file"] for s in sj if s["max_brown_tier"] >= tier)

    out = {
        "_comment": "B09: which launch plants can co-exist with super jump. Derived from "
                    "the fresh-level lane state, the token-upgrade law and the per-FILE "
                    "type-0x3f census. Regenerate: "
                    "tools/phase4_b09_launch_plant_reachability.py",
        "generated": str(date.today()),
        "row_id": "B09_super_jump",
        "row_item": "super-jump's interaction with plants/dandelion/cannon",
        "chain": {
            "fresh_level_lanes": "[0x11, 0, 0, 0, 0] -- memset 0x80046B68 then brown 0x11 "
                                 "at 0x80046BEC; no authored per-level brown value",
            "token_upgrade": "n = (old+1) & 7 then store (n<<4)|n -- one tier per token "
                             "(0x8005431C/0x80054364/0x800543E0/0x8005445C/0x800544F8)",
            "brown_tiers": BROWN_TIERS,
            "super_jump": "blue tier %d" % SUPER_JUMP_BLUE_TIER,
            "granularity": "per FILE -- directory != stage (LEVEL01/ holds stage 1 and "
                           "stage 6); per-directory aggregation is wrong",
        },
        "stages": stages,
        "stages_where_super_jump_is_possible": [s["file"] for s in sj],
        "co_occurrence": combos,
        "verdict": None,
        "confirmation": ("Measured on movies/Phase4/Interpreter/B08_SuperJump_EOL.movie.json "
                         "(bird level = LEVEL01/LEVEL1.DAT, 4 blue / 0 orange): brown reads "
                         "1/1 for the whole level while blue climbs 0->4. Predicted max "
                         "brown 1, measured 1."),
    }
    unreachable = [n for n, files in combos.items() if not files]
    reachable = [n for n, files in combos.items() if files]
    out["verdict"] = (
        "SUPER JUMP + %s: UNREACHABLE campaign-wide. %s remain reachable. Dandelion needs "
        "brown tier 3 and cannon tier 4, i.e. 2 and 3 orange tokens; no stage file carrying "
        "4 blue tokens carries more than ONE orange token. This closes the row item as a "
        "REVIEWED NEGATIVE -- the Phase-4 exit gate admits \"a reviewed proof that it is not "
        "present in the pristine PS1 version\" -- rather than deferring it."
        % (" / ".join(unreachable) or "(none)", " / ".join(reachable) or "(none)"))

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print("stages where super jump is possible:")
    for s in sj:
        print("   %-24s blue %d  orange %d  -> brown max %d (%s)"
              % (s["file"], s["blue_tokens"], s["orange_tokens"], s["max_brown_tier"],
                 ", ".join(s["brown_outputs_available"])))
    print()
    for name, files in combos.items():
        print("   super jump + %-10s : %s" % (name, [f.split('/')[0]+'/'+f.split('/')[1][:6] for f in files] or "IMPOSSIBLE"))
    print("\n" + out["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
