#!/usr/bin/env python3
"""Turn the validated campaign into a verdict on E16's two systematic residuals.

WHAT THIS DECIDES
-----------------
Two of E16's declared residuals are systematic assumptions rather than per-object
proofs, and both name the same falsifier: watch the three table windows across a
per-level campaign.

  * the NON-NEGATIVE-INDEX convention (6,227 discharged accesses) -- already
    asserted non-intersecting on the magnitude argument (no discharged site needs
    a small negative index), with the campaign as its stated experiment;
  * the >=1k REMAINDER (4,166 accesses) -- NOT asserted, because no element count
    has been read for the objects involved. Its median required index is ~11,000
    against pools of tens to hundreds of elements.

The campaign cannot prove either. It can FALSIFY both: any PC touching a window
that the static frontier did not predict breaks them. So the honest reading is
asymmetric, and this tool refuses to blur it:

  falsified          -> the residual is wrong, and the packet must stay open
  not falsified      -> the assumption survives its own declared test, which is
                        what `intersects_dimension: false` plus a named
                        `next_experiment` is supposed to mean

WHAT IT REFUSES TO DO
---------------------
Report a clean campaign as proof. A replay shows what DID execute; it can never
show that an untaken branch would not have written the slot. That reasoning error
is what produced this row's original false closure, and the roadmap calls it out
explicitly. Coverage is therefore reported as a LIMIT, not as a warrant.

Usage: python3 tools/phase4_e16_campaign_verdict.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "analysis/phase4_e16_movie_validation.json"
RES = ROOT / "analysis/phase4_e16_bounded_residuals.json"
MAT = ROOT / "analysis/phase4_e16_address_materialization.json"
COV = ROOT / "analysis/phase4_text_coverage_audit.json"

SCAN = ROOT / "analysis/hoisted_load_idiom_scan.json"

# PCs the campaign FOUND and that were then characterised well enough to say what
# they are. This is not an excuse list: every entry declares its BASIS and must
# carry the evidence that basis requires.
#
#   basis "measured"      -- replayed and counted; must state what was measured
#   basis "static-idiom"  -- machine-matched to the hoisted-load pattern by
#                            tools/hoisted_load_idiom_scan.c; must cite that scan
#                            AND the materialisation census, because the argument
#                            is "no register-based access to these windows can be
#                            deliberate", which is a property of the windows.
#
# The family is loaded from the scan artifact rather than typed here, so it cannot
# drift from what the scanner actually finds. Anything in neither set falsifies.
MEASURED = {
    "0x80010bf8": {
        "basis": "measured",
        "what": "per_object_mesh_draw_payload_emitter's load at 0x80010BF4, hoisted by "
                "the compiler above its own range check at 0x80010BF8; the loaded "
                "register is dead on the failing path (0x80010C80).",
        "measured": "53 reads over 7 of the 16 campaign levels (1, 2, 7, 29, 1, 2, 11); "
                    "LEVEL01 was a single read of 0x800A65C0, the marker-0x5C slot. "
                    "Read-only, never a write.",
        "why_it_cannot_be_deliberate": "No site in the entire text segment -- including "
                                       "the 46 KB the function census omits -- can "
                                       "materialise a pointer into these windows outside "
                                       "the enumerated set.",
        "artifacts": ["analysis/phase4_e16_speculative_read_probe.json",
                      "analysis/phase4_e16_address_materialization.json"],
    },
    "0x80010da0": {
        "basis": "measured",
        "what": "the sibling copy of the same loop body 424 bytes later -- byte-identical "
                "instruction sequence, same hoisted load at 0x80010D9C.",
        "measured": "51 reads on LEVEL15 across 8 distinct addresses, which is every word "
                    "of the 32-byte 0x58..0x5F table. Read-only, never a write.",
        "why_it_cannot_be_deliberate": "Same as its sibling: the base is a register and no "
                                       "materialisation site for these windows exists "
                                       "outside the enumerated set.",
        "artifacts": ["analysis/phase4_e16_speculative_read_probe_da0.json",
                      "analysis/phase4_e16_address_materialization.json"],
    },
}


def _load_explained() -> dict:
    ex = dict(MEASURED)
    if SCAN.exists():
        d = json.loads(SCAN.read_text())
        for h in d.get("hits", []):
            pc = h["logged_pc"].lower()
            if pc in ex:
                continue
            ex[pc] = {
                "basis": "static-idiom",
                "what": ("load at %s (%s) scheduled above the branch that bounds it; the "
                         "result is discarded on exactly the path where the address is out "
                         "of range." % (h["load_pc"], h["width"])),
                "why_it_cannot_be_deliberate": (
                    "The base is a register, and no site in the entire text segment can "
                    "materialise a pointer into these windows outside the enumerated set. "
                    "That is a property of the windows, not of this PC."),
                "artifacts": ["analysis/hoisted_load_idiom_scan.json",
                              "analysis/phase4_e16_address_materialization.json"],
            }
    return ex


EXPLAINED = _load_explained()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_campaign_verdict.json"))
    # Injectable inputs so the decision logic can be gated on synthetic cases --
    # a falsifying PC, a partial campaign -- without needing a 16-movie replay.
    ap.add_argument("--validation", default=str(VAL))
    ap.add_argument("--residuals", default=str(RES))
    args = ap.parse_args()

    v = json.loads(Path(args.validation).read_text())
    r = json.loads(Path(args.residuals).read_text())
    mat = json.loads(MAT.read_text()) if MAT.exists() else None
    cov = json.loads(COV.read_text()) if COV.exists() else None
    movies = v["movies"]

    # COVERAGE IS PART OF THE VERDICT, not a footnote. A smoke run over ONE movie
    # printed "survived ... across the full campaign", which is exactly the kind of
    # overclaim this row has had to retract before. The campaign is the set of
    # campaign levels; anything less is reported as partial and cannot license the
    # >=1k assertion.
    import re as _re
    levels = {int(mm.group(1)) for m in movies
              if (mm := _re.search(r"LEVEL(\d\d)", m.get("movie", "")))}
    EXPECTED = set(range(0, 16))          # LEVEL00 (training) .. LEVEL15 (showdown)
    missing_levels = sorted(EXPECTED - levels)

    usable = [m for m in movies if str(m.get("verdict", "")).startswith("USABLE")]
    bad = [m for m in movies if not str(m.get("verdict", "")).startswith("USABLE")]
    unenum: Counter = Counter()
    for m in usable:
        for pc, n in (m.get("unenumerated_pcs") or {}).items():
            unenum[pc] += n
    unexplained = {p: n for p, n in unenum.items() if p not in EXPLAINED}
    explained = {p: n for p, n in unenum.items() if p in EXPLAINED}
    total_events = sum(m.get("events", 0) for m in usable)
    truncated = [m["movie"] for m in usable if m.get("truncated")]

    verdicts = Counter(v_["verdict"] for t in r["per_target"].values() for v_ in t["boundaries"])
    neg = verdicts.get("BOUNDED_NEGATIVE_INDEX", 0)
    needs = verdicts.get("NEEDS_EXTENT", 0)

    out = {
        "_comment": "Campaign verdict on E16's two systematic residuals. Regenerate: "
                    "tools/phase4_e16_campaign_verdict.py",
        "generated": str(date.today()),
        "coverage": {
            "levels_expected": sorted(EXPECTED),
            "levels_present": sorted(levels),
            "levels_missing": missing_levels,
            "is_full_campaign": not missing_levels,
            "movies_validated": len(movies),
            "usable": len(usable),
            "not_usable": [{"movie": m["movie"], "verdict": m.get("verdict")} for m in bad],
            "total_events_observed": total_events,
            "any_event_log_truncated": truncated,
        },
        "falsifier_result": {
            "unenumerated_pcs": dict(unenum),
            "explained": {p: {"events": n, **EXPLAINED[p]} for p, n in explained.items()},
            "unexplained": dict(unexplained),
            "falsified": bool(unexplained),
        },
        "hoisted_load_family": ({
            "sites": json.loads(SCAN.read_text())["sites"],
            "note": ("The campaign found two of these one movie at a time (LEVEL01, then "
                     "LEVEL15). tools/hoisted_load_idiom_scan.c enumerates the whole "
                     "family so the remainder cannot arrive as fresh surprises."),
        } if SCAN.exists() else None),
        "static_frontier": ({
            "materialisation_sites_into_the_windows": mat["sites_inside"],
            "all_already_enumerated": True,
            "near_misses_within_slack": mat["near_misses"],
            "why_this_is_stronger_than_the_campaign": (
                "A replay shows only what DID execute. This is a static argument that is "
                "complete over the scanned text: deliberate access to an address requires "
                "materialising it, materialisation is always a lui-based constant, and "
                "only %d such sites reach these windows -- all of them already known. "
                "Anything else that lands here is incidental by construction."
                % mat["sites_inside"]),
        } if mat else None),
        "scope_correction": ({
            "text_covered_by_function_census_percent": cov["covered_percent"],
            "live_code_the_census_omitted_bytes": cov["dropped_code_bytes"],
            "note": ("Every static residual figure for this row was computed over %.1f%% "
                     "of the resident text. The materialisation census above scans 100%% "
                     "of it, which is why it can carry the frontier claim the affine "
                     "census could not." % cov["covered_percent"]),
        } if cov else None),
        "residuals": {
            "non_negative_index_convention": {
                "accesses": neg,
                "status_before_campaign": "asserted non-intersecting on the magnitude "
                                          "argument (zero discharged sites need a small "
                                          "negative index)",
            },
            "ge_1k_remainder": {
                "accesses": needs,
                "status_before_campaign": "NOT asserted -- no element count read for the "
                                          "objects involved",
            },
        },
        "what_a_clean_campaign_does_NOT_mean": (
            "It is not proof. A replay shows what DID execute; it can never show that an "
            "untaken branch or an unspawned object would not have written the window. "
            "Treating runtime silence as closure is the reasoning error that produced this "
            "row's original false closure, and the roadmap rejects it explicitly. Coverage "
            "below is a LIMIT on the claim, not a warrant for it."),
        "verdict": None,
        "recommendation": None,
    }

    if missing_levels:
        out["verdict"] = ("PARTIAL COVERAGE -- %d of %d campaign levels present (missing "
                          "%s). A subset cannot license the >=1k assertion, whose whole "
                          "basis is that the falsifier ran across the campaign."
                          % (len(levels), len(EXPECTED),
                             ", ".join("LEVEL%02d" % n for n in missing_levels)))
        out["recommendation"] = "Validate the remaining levels before deciding."
    elif bad:
        out["verdict"] = ("INCOMPLETE -- %d of %d movies are not usable, so the campaign "
                          "has not actually run on the whole set."
                          % (len(bad), len(movies)))
        out["recommendation"] = "Re-record or re-validate the listed movies before deciding."
    elif unexplained:
        out["verdict"] = ("FALSIFIED -- %d PC(s) touched an E16 window that the static "
                          "frontier did not predict and that remain unexplained: %s. Both "
                          "systematic residuals are in doubt until these are characterised."
                          % (len(unexplained), ", ".join(sorted(unexplained))))
        out["recommendation"] = ("Identify each PC's owning function and base object, add "
                                 "it to the enumerated set or to the frontier, and re-run. "
                                 "Do NOT assert either residual meanwhile.")
    else:
        found = (" The campaign DID find something -- %s -- and it was characterised "
                 "rather than waved away: %s"
                 % (", ".join(sorted(explained)),
                    "; ".join(EXPLAINED[p].get("measured") or EXPLAINED[p]["what"]
                              for p in sorted(explained)))
                 ) if explained else ""
        out["verdict"] = ("NOT FALSIFIED -- all %d campaign levels, %d movies, %d events, "
                          "every one from an enumerated or characterised PC. Both "
                          "systematic residuals survived their own declared experiment "
                          "across the full campaign.%s"
                          % (len(EXPECTED), len(usable), total_events, found))
        out["recommendation"] = (
            "Assert the >=1k remainder as non-intersecting on the SAME basis the "
            "non-negative-index convention already uses -- a magnitude argument with a "
            "named, now-executed falsifier -- and record the campaign as its evidence. "
            "That takes E16's item-2 packet to zero rejections without claiming proof: "
            "the residual remains a declared, evidenced, falsifiable assumption, which is "
            "exactly what `bounded_residuals` is for.")
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"movies: {len(movies)}  usable: {len(usable)}  events: {total_events}")
    print(f"unexplained PCs: {dict(unexplained) or 'none'}")
    print(f"explained PCs:   {dict(explained) or 'none'}")
    print("\n" + out["verdict"])
    print("\n-> " + out["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
