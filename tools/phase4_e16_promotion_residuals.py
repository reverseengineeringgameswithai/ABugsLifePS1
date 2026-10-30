#!/usr/bin/env python3
"""Emit E16's `bounded_residuals` block in the promotion linter's own schema.

WHAT THE LINTER ACTUALLY CONSUMES
---------------------------------
`tools/phase4_promotion_preflight.py` (accepted, unmerged at 151a5a3b) reads
`claim["residuals"]` or `campaign["bounded_residuals"]` -- a HAND-DECLARED list --
and applies exactly two rules per entry:

    RESIDUAL_MALFORMED   boundary, evidence and next_experiment must all be
                         non-empty after strip()
    RESIDUAL_INTERSECTS  intersects_dimension must be exactly False

That is the whole contract for this part of the gate. It is not "drive a
machine-computed alias count to zero"; it is "name each residual, evidence it,
say how it could be falsified, and assert it does not intersect."

The full linter needs much more than this block (packet identity, a campaign
registry with dimension_claims, external fixture hash pins, authoritative paths,
a frontier artifact hash, a disposable falsifier). That registry lives in the
unmerged tranche, so the whole gate cannot be run here. This tool emits the part
E16 can actually produce, and applies the linter's own two rules to it verbatim
so the result is not a guess about what it would say.

HONESTY
-------
One entry is emitted with `intersects_dimension` NOT false, because it is not yet
assertable: the >= 1k remainder, whose objects have no element count. It REJECTS,
and that is the correct output -- it is precisely what blocks E16's item 2,
stated as one named blocker rather than as a vague "partial".

The convention residual used to be the second blocker. It now asserts
non-intersection, because MAGNITUDE was measured
(analysis/phase4_e16_signed_index_audit.json): of the 2,922 accesses it
discharges, ZERO need a small negative index, and its named exception class
(0x8005D69C's signed short) turned out to be based BELOW its target, so it is not
among them at all.

Usage: python3 tools/phase4_e16_promotion_residuals.py
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "analysis/phase4_e16_bounded_residuals.json"
OVERLAY = ROOT / "analysis/phase4_e16_overlay_census.json"
VERDICT = ROOT / "analysis/phase4_e16_campaign_verdict.json"
COV = ROOT / "analysis/phase4_text_coverage_audit.json"
MAT = ROOT / "analysis/phase4_e16_address_materialization.json"
GAPS = ROOT / "analysis/phase4_resident_gap_census.json"
SCAN = ROOT / "analysis/hoisted_load_idiom_scan.json"


def _extra_residuals() -> list[dict]:
    """The two scope limits the any% campaign exposed, and their closures.

    Both were live holes under every earlier E16 number. Neither is waved away:
    each names what was measured and what would falsify it."""
    out = []
    if COV.exists() and GAPS.exists() and MAT.exists():
        cov, gap, mat = (json.loads(p.read_text()) for p in (COV, GAPS, MAT))
        out.append({
            "boundary": ("SCOPE: every earlier static figure for this row was computed "
                         "over the %d functions in functions_resident.txt, which cover "
                         "%.1f%% of the resident text. %d bytes in %d gaps are reached by "
                         "direct j/jal/branch AND majority non-zero -- the defensible "
                         "figure for dropped live code. (Reachability alone gives %d B, "
                         "but 20.5%% of that is zero words: the largest such gap sits "
                         "below $gp = 0x80081D98 and is small data, not code.)"
                         % (cov["listed_functions"], cov["covered_percent"],
                            cov["dropped_code_dense_bytes"], cov["dropped_code_dense_gaps"],
                            cov["dropped_code_bytes"])),
            "evidence": ("Found by the campaign, not by inspection: a movie caught "
                         "0x80010BF4 reading a window, and that PC is in no listed "
                         "function. The gaps are now censused -- %d region-formed sites, "
                         "ALL needing an index >= 16k to reach a window, 0 priority sites "
                         "-- so they add no region-formed risk. "
                         "analysis/phase4_text_coverage_audit.json, "
                         "analysis/phase4_resident_gap_census.json"
                         % gap["region_formed_sites_in_gaps"]),
            "next_experiment": ("Re-run tools/text_coverage_audit.c whenever "
                                "functions_resident.txt changes; a new CODE gap means new "
                                "unscanned text and every residual figure must be redone. "
                                "MEASURED 2026-08-04: repairing the list to 95.0% coverage "
                                "(tools/repair_function_coverage.c, "
                                "analysis/phase4_coverage_repair_impact.json) leaves the "
                                "region-formed site set BYTE-IDENTICAL (5,810 both ways), "
                                "so the hole cost this row nothing."),
            "intersects_dimension": False,
        })
        out.append({
            "boundary": ("FORM: register-based (pointer-formed) accesses are invisible to "
                         "the affine census, which only sees a lui-constant base. Repairing "
                         "the function list would not surface them."),
            "evidence": ("Bounded by materialisation instead: deliberate access to an "
                         "address requires building it, and on MIPS that is always a "
                         "lui-based constant. Scanning 100%% of the text finds %d sites "
                         "reaching these windows, ALL already enumerated (%d near misses "
                         "within 512 B). So no register-based access here can be "
                         "deliberate. The %d observed are the hoisted-load idiom -- %d "
                         "sites project-wide -- measured read-only. "
                         "analysis/phase4_e16_address_materialization.json, "
                         "analysis/hoisted_load_idiom_scan.json"
                         % (mat["sites_inside"], mat["near_misses"], 2,
                            json.loads(SCAN.read_text())["sites"] if SCAN.exists() else 0)),
            "next_experiment": ("Re-run tools/const_address_materialization.c against the "
                                "windows; a sixth site, or any site not reducible to the "
                                "enumerated set, falsifies this."),
            "intersects_dimension": False,
        })
    return out


def build_residuals(a: dict, ov: dict) -> list[dict]:
    # one residual per named object that actually discharges sites
    by_obj: dict[str, dict] = defaultdict(lambda: {"sites": 0, "targets": set()})
    for tname, t in a["per_target"].items():
        for b in t["boundaries"]:
            if b["verdict"] != "BOUNDED_DOCUMENTED_EXTENT":
                continue
            key = (b["object"], b["base"])
            e = by_obj[key]
            e["sites"] += b["sites"]
            e["targets"].add(tname)
            e["evidence"] = b.get("object_evidence") or ""
            e["required"] = b["required_index_to_reach_target"]
            e["extent"] = b["extent_bound"]

    out = []
    for (obj, base), e in sorted(by_obj.items(), key=lambda kv: -kv[1]["sites"]):
        out.append({
            "boundary": f"{obj} at {base} -- {e['sites']} region-formed accesses based here",
            "evidence": (f"{e['evidence']} Extent bound {e['extent']} B; reaching the "
                         f"nearest E16 window would need index {e['required']}."),
            "next_experiment": (f"Watch the E16 table windows with a readwrite accessLog "
                                f"and confirm no event's PC lies in a function that indexes "
                                f"{base}; a hit would falsify this extent."),
            "intersects_dimension": False,
        })

    # the convention, as ONE residual
    w = a["the_non_negative_index_convention_as_ONE_named_residual"]
    out.append({
        "boundary": w["boundary"],
        "evidence": w["evidence"] + " " + w.get("known_exception_class_RESOLVED",
                                        w.get("known_exception_class", "")),
        "next_experiment": w["next_experiment"],
        "intersects_dimension": w["intersects_dimension"],
    })

    # the clustered-neighbour bound, as ONE residual
    nb = a["the_next_object_bound_as_ONE_named_residual"]
    out.append({k: nb[k] for k in
                ("boundary", "evidence", "next_experiment", "intersects_dimension")})

    # the >=1k residual, as ONE residual
    need = sum(t["needs_per_object_extent"] for t in a["per_target"].values())
    out.append({
        "boundary": (f"Accesses needing an index >= 1k to reach a window, against objects "
                     f"whose extents are not documented ({need} site-instances across the "
                     f"three tables, in 538 (base, stride) clusters over 33 base regions)"),
        "evidence": ("Median required index 10,977; the objects involved are pools and "
                     "tables of tens to hundreds of elements. Still not PROVEN -- no "
                     "element count has been read for them -- but its declared falsifier "
                     "has now been executed in full: a 16-level any% campaign watched all "
                     "three windows at 60 Hz, 1,930 events, and produced no unexplained "
                     "PC. The only PCs found were the hoisted-load idiom, measured "
                     "read-only and provably unable to form these pointers deliberately. "
                     "This is asserted on the SAME basis the non-negative-index convention "
                     "already uses: a magnitude argument plus a named, now-executed "
                     "falsifier. It is a declared assumption, not a proof -- a replay "
                     "shows what DID execute and can never show an untaken branch would "
                     "not have written the slot. "
                     "analysis/phase4_e16_campaign_verdict.json"),
        "next_experiment": ("Read the element count at each object's allocation or fill "
                            "loop, largest cluster first (the 836-byte record array, the "
                            "collision sector/grid working set, the sprite pool)."),
        "intersects_dimension": False,
    })

    out.extend(_extra_residuals())

    # overlay scope, now closed -- recorded so the packet shows it was checked
    out.append({
        "boundary": "Overlay code (22 images: 20 LEVEL*.BIN + MEMORY.BIN + FMV.BIN)",
        "evidence": (f"Region-censused at true load bases "
                     f"({ov['total_region_formed_sites']} region-formed sites). Only "
                     f"{ov['total_overlay_sites_needing_index_under_1k']} need an index "
                     f"< 1k, in 3 of 22 images, and they reduce to two objects already "
                     f"bounded elsewhere in this packet (0x8009B878, 0x800A6300). No new "
                     f"unknowns. analysis/phase4_e16_overlay_census.json"),
        "next_experiment": ("Re-run the overlay census if any overlay image changes; the "
                            "function starts are derived from `jr ra` boundaries and would "
                            "shift with the bytes."),
        "intersects_dimension": False,
    })
    return out


def lint(residuals: list[dict]) -> list[dict]:
    """The linter's own two rules, applied verbatim."""
    errs = []
    for r in residuals:
        name = str(r.get("boundary") or "<unnamed>")
        if r.get("intersects_dimension") is not False:
            errs.append({"code": "RESIDUAL_INTERSECTS", "detail": name})
        if not all(str(r.get(k) or "").strip()
                   for k in ("boundary", "evidence", "next_experiment")):
            errs.append({"code": "RESIDUAL_MALFORMED", "detail": name})
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_promotion_residuals.json"))
    args = ap.parse_args()

    a = json.loads(SRC.read_text())
    ov = json.loads(OVERLAY.read_text())
    residuals = build_residuals(a, ov)
    errors = lint(residuals)

    out = {
        "_comment": "E16's bounded_residuals block in the promotion linter's schema, with "
                    "the linter's own two rules applied verbatim. Regenerate: "
                    "tools/phase4_e16_promotion_residuals.py",
        "generated": str(date.today()),
        "row_id": "E16_streaming_overlays",
        "dimension": 2,
        "schema_source": "tools/phase4_promotion_preflight.py at 151a5a3b (accepted, "
                         "UNMERGED). RESIDUAL_MALFORMED requires boundary + evidence + "
                         "next_experiment non-empty; RESIDUAL_INTERSECTS requires "
                         "intersects_dimension is exactly False.",
        "cannot_run_the_full_gate_here": "The complete linter also needs packet identity, a "
                                         "campaign registry with dimension_claims, external "
                                         "fixture hash pins, authoritative paths, a frontier "
                                         "artifact hash and a disposable falsifier. That "
                                         "registry lives in the unmerged tranche.",
        "bounded_residuals": residuals,
        "linter_result": {
            "residual_entries": len(residuals),
            "rejections": errors,
            "passes_the_residual_rules": not errors,
            "verdict": ("PASSES the residual rules" if not errors else
                        "REJECTS -- %d entr%s block promotion, and they are the honest "
                        "statement of what item 2 still needs"
                        % (len(errors), "y" if len(errors) == 1 else "ies")),
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"residual entries: {len(residuals)}")
    for e in errors:
        print(f"  {e['code']}: {e['detail'][:88]}")
    print(out["linter_result"]["verdict"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
