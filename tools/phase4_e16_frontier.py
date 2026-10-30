#!/usr/bin/env python3
"""Phase-4 E16 static frontier: can exit-gate item 2 be MET for this row?

Exit-gate item 2 is "no unresolved field, dispatch, asset, or overlay intersects
that subsystem's behavior without being explicitly bounded". For a state region
that means: every access that could reach it is either resolved or explicitly
excluded, with nothing left merely "possible".

E16 was picked for this because it looked structurally better placed than any
row tried before. B06/B08 stopped against pointer provenance into the player
block; E15 came back ADVANCED-not-MET. E16's registered-chunk tables are
absolute-addressed globals, never (apparently) held in a pointer -- so the
escape argument the analyser itself documents,

    "If no store anywhere does [write a block pointer to memory], then no memory
     location can ever hold such a pointer, so no `lw`-loaded base can be one"

looked available here. If it holds, the whole ~12,000-site unresolved-base
residual collapses at once and item 2 is met.

This driver runs the (now fixed -- see below) analyser over all three tables and
reports whether that argument is established. It is written to make a NEGATIVE
result legible, not to manufacture a positive one.

TWO ANALYSER DEFECTS FOUND AND FIXED ON THE WAY (see
tests/test_region_provenance_bound_soundness.py):
  1. TIER 3 EXCLUDED_OUT_OF_BOUND was unsound -- it asserted a bound from the
     mere existence of a comparison and propagated it to the branch where the
     comparison FAILED. It excluded 0x8003BF48, an access runtime shows firing
     36 times.
  2. The escape test inspected K_CONST only, so a K_REGION value -- which is the
     ONLY shape E16's table pointers ever take -- could never be flagged. Its
     "0 stores may write a block pointer" was structurally vacuous for this row.

Usage: python3 tools/phase4_e16_frontier.py [--out analysis/phase4_e16_frontier.json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD/files/SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"

TABLES = [
    ("markers_0x30_0x57", 0x8009B5A8, 160),
    ("markers_0x28_0x2F", 0x8009C210, 32),
    ("markers_0x58_0x5F", 0x800A65B0, 32),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_frontier.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16fr_"))
    tool = str(tmp / "regprov")
    subprocess.run(["cc", "-O2", "-o", tool, str(ROOT / "tools/region_provenance.c")],
                   check=True)

    rows = {}
    for name, base, ln in TABLES:
        jf = tmp / f"{name}.json"
        r = subprocess.run([tool, str(EXE), str(FUNCS), "0x%08X" % base, str(ln),
                            "--block", "0x%08X" % base, "0x%08X" % (base + ln),
                            "--json", str(jf)],
                           capture_output=True, text=True, check=True)
        err = r.stderr
        undecided = int(re.search(r"UNDECIDED unbounded-region values seen\): (\d+)", err).group(1))
        partial = int(re.search(r"partial-width sb/sh[^)]*\): (\d+)", err).group(1))
        d = json.loads(jf.read_text())
        rows[name] = {
            "window": "0x%08X..0x%08X" % (base, base + ln - 1),
            "hits": d["hits"],
            "unresolved_after_region": d["unresolved_after_region"],
            "exclusions_total": d["exclusions_total"],
            "indirect_unresolved": d["indirect_unresolved"],
            "full_width_escaping_stores": len(d["pb_taint"]["tainted_stores"]),
            "arg_passing_call_sites": d["pb_taint"]["arg_passing_call_sites"],
            "partial_width_stores": partial,
            "undecided_unbounded_regions": undecided,
        }

    any_undecided = any(v["undecided_unbounded_regions"] > 0 for v in rows.values())
    total_unresolved = sum(v["unresolved_after_region"] for v in rows.values())

    out = {
        "_comment": "Phase-4 E16 static frontier against exit-gate item 2. Regenerate: "
                    "tools/phase4_e16_frontier.py",
        "generated": str(date.today()),
        "row": "E16_streaming_overlays",
        "question": "Exit-gate item 2 -- is every access that could reach E16's "
                    "registered-chunk state either resolved or explicitly bounded?",
        "scope": {
            "covered": "the three registered-chunk pointer tables ONLY -- the part of "
                       "E16 whose state is a small, absolutely-addressed region",
            "NOT_covered": "the rest of the row's universe: overlay region A and its 42 "
                           "entries, the resident streaming table 0x8007EFE8, the high "
                           "heap holding decompressed chunks, and the LEVEL.RAW/DAT/BIN "
                           "assets. Item 2 is a per-SUBSYSTEM bar, so closing the tables "
                           "alone would not close the row.",
        },
        "per_table": rows,
        "the_escape_argument": {
            "statement": "If no store anywhere writes a pointer to this region into "
                         "memory, and no call passes one as an argument, then no memory "
                         "location can hold one, so no lw-loaded base can be one -- and "
                         "the entire unresolved-base residual is excluded at a stroke.",
            "decidable_result": "0 full-width escaping stores and 0 argument-passing call "
                                "sites across all three tables.",
            "why_that_is_NOT_enough": "Those zeroes range over DECIDABLE values only. "
                                      "~20,180 region values per run carry no proven index "
                                      "bound, so the analyser cannot say whether they may "
                                      "point into the table. An arithmetic progression with "
                                      "an unknown index reaches everything; treating those "
                                      "as escapes makes the test a tautology (measured: 57 "
                                      "stores / 258 call sites flagged for a 160-byte "
                                      "stride-4 window), and treating them as non-escapes "
                                      "assumes the conclusion. They are therefore COUNTED "
                                      "as undecided.",
            "established": False,
        },
        "verdict": {
            "item_2_met": False,
            "reason": "The escape argument is not established, so ~%d unresolved-base "
                      "accesses per table remain merely possible rather than bounded."
                      % (total_unresolved // len(rows)),
            "wall": "Same class of wall B06/B08 stopped against, reached through a "
                    "different door. B06's blocker was 4,490 image-wide stores with "
                    "unresolved DESTINATIONS; E16's is ~20,180 region values with no "
                    "proven INDEX BOUND. Both are the same deficiency -- the image does "
                    "not statically yield the bounds the argument needs -- and neither is "
                    "row-specific.",
            "what_this_says_about_the_gate": "E16 was the best-positioned candidate left "
                    "and it fails for a non-row-specific reason. That is a second "
                    "independent data point (after B06/B08 and E15) that item 2 as "
                    "written is not reachable with current technique, and the next move "
                    "is a general capability -- index/pointer bound recovery -- not "
                    "another row.",
        },
        "what_DID_improve": [
            "TIER 3 EXCLUDED_OUT_OF_BOUND was unsound and is fixed; 35 unsound "
            "image-wide exclusions disappeared. B06's committed 416/165/251 is "
            "byte-identical (its artifact records 0 in-scope out-of-bound exclusions).",
            "The escape test no longer reports a vacuous 0 for region-addressed targets; "
            "undecidable values are counted and surfaced instead of silently dropped.",
            "region_provenance.c takes an optional --block LO HI, so a subsystem other "
            "than B06's can be analysed without editing the tool.",
        ],
        "any_undecided": any_undecided,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    for n, v in rows.items():
        print(f"{n}: unresolved={v['unresolved_after_region']} "
              f"escaping_stores={v['full_width_escaping_stores']} "
              f"arg_sites={v['arg_passing_call_sites']} "
              f"UNDECIDED={v['undecided_unbounded_regions']}")
    print(f"\nitem_2_met: {out['verdict']['item_2_met']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
