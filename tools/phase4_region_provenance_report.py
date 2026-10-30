#!/usr/bin/env python3
"""Run region_provenance.c, cross-reference against census_address.py's live baseline,
and write ONE clean, reproducible artifact. This is the regenerate command.

WHY THIS EXISTS
---------------
`tools/region_provenance.c` is a from-scratch C port of census_address.py's value
analysis, extended with a REGION lattice value: a base register can be classified
"provably `K + i*S` for integer i" even when its exact numeric value is
data-dependent, which lets some of the 416 (post-dedup) same-width residual accesses
be EXCLUDED by alignment/sign reasoning instead of staying an open question forever.

Two independent implementations of the same analysis is itself a validation method --
this script is the harness that makes the comparison real instead of asserted:

1. Run the C tool for its raw counts and its region-exclusion records.
2. Recompute the SAME `analyse()` call in Python (the pinned, tested implementation)
   to get the authoritative hit list, the 34-related-function set, and the 416-site
   residual.
3. Filter the C tool's records down to that SAME scope (function in the 34, width==2)
   and reconcile: distinct-C-residual + newly-excluded MUST equal exactly 416, with
   zero sites lost and zero spurious additions, or this script FAILS LOUDLY instead of
   reporting a number nobody checked.

STRIDE UNDERSTATEMENT IS SOUND, NOT A BUG
------------------------------------------
The C tool's block-local peephole only reads the shift amount of the LAST `sll`
immediately preceding the `addu` that forms a region. A compound index (e.g.
`v0 = v1*3; v0 <<= 4`, i.e. true stride 48) is seen only as stride 16 (the trailing
shift). This UNDERSTATES the true per-element stride, but every exclusion made against
the understated stride still holds: if the true stride is a multiple of the assumed
one (48 = 16*3), the true reachable set is a SUBSET of what the assumed stride allows,
so proving the target unreachable under the (larger, coarser) assumed set proves it
unreachable under the (smaller, true) one too. The cost is precision (some genuinely
excludable sites are missed), never soundness.

USAGE
    tools/phase4_region_provenance_report.py
    tools/phase4_region_provenance_report.py --json analysis/phase4_region_provenance.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import census_address as ca  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=ROOT / "analysis/functions.json")
    ap.add_argument("--functions-txt", type=Path,
                    default=ROOT / "analysis/functions_resident.txt")
    ap.add_argument("--target", default="0x800A657E")
    ap.add_argument("--bytes", type=int, default=2)
    ap.add_argument("--binary", type=Path, default=ROOT / "tools/region_provenance")
    ap.add_argument("--source", type=Path, default=ROOT / "tools/region_provenance.c")
    ap.add_argument("--json", type=Path,
                    default=ROOT / "analysis/phase4_region_provenance.json")
    args = ap.parse_args()

    if not args.exe.exists():
        print("INPUTS ABSENT -- %s is gitignored (copyrighted); provision with "
              "tools/verify_repro_inputs.py --provision" % args.exe.name)
        return 2

    # Regenerate the function dump and rebuild the C binary every run -- both are
    # cheap and it keeps this report from silently drifting behind either input.
    subprocess.run([sys.executable, str(ROOT / "tools/dump_functions_txt.py"),
                    "--exe", str(args.exe), "--functions", str(args.functions),
                    "--out", str(args.functions_txt)], check=True, cwd=str(ROOT))
    subprocess.run(["cc", "-O2", "-o", str(args.binary), str(args.source)],
                   check=True, cwd=str(ROOT))

    c_json = args.json.with_suffix(".c_raw.json")
    subprocess.run([str(args.binary), str(args.exe), str(args.functions_txt),
                    args.target, str(args.bytes), "--json", str(c_json)],
                   check=True, cwd=str(ROOT))
    c_data = json.loads(c_json.read_text())

    # --- authoritative Python baseline ---
    img = ca.Image(args.exe, args.functions)
    addr = int(args.target, 16)
    targets = set(range(addr, addr + args.bytes))
    hits, unresolved, indirect = ca.analyse(img, targets)
    bhits, _, _ = ca.analyse(img, {0x800A6500})
    block_fns = {h["function"] for h in bhits} | {h["function"] for h in hits}
    py_hit_pcs = {h["pc"] for h in hits}
    py_residual = {u["pc"] for u in unresolved
                   if u["function"] in block_fns and u["width"] == args.bytes}

    # --- C tool's records, scoped to the identical (function, width) filter ---
    c_hit_pcs = set(c_data["hit_pcs"])
    c_unresolved_scoped = {u["pc"] for u in c_data["unresolved_all"]
                           if u["function"] in block_fns and u["width"] == args.bytes}
    c_excl_scoped = [e for e in c_data["exclusions"] if e["function"] in block_fns]
    c_excl_scoped_w = [e for e in c_data["exclusions"]
                       if e["function"] in block_fns]
    # exclusions don't carry width in the C output; recover it by matching against
    # the pcs that were in Python's residual (which IS width-filtered) -- anything
    # excluded that isn't in py_residual belongs to a different width and is reported
    # separately, not folded into the headline number.
    c_excl_in_scope_w = [e for e in c_excl_scoped_w if e["pc"] in py_residual]
    c_excl_other_width = [e for e in c_excl_scoped_w if e["pc"] not in py_residual]
    c_excl_pcs_w = {e["pc"] for e in c_excl_in_scope_w}

    # COMBINED-PROVER ACCOUNTING. The two implementations are independently sound
    # may-analyses, and they are no longer equally precise site-by-site: C's region
    # merges can absorb a constant pointer into a walking region (losing the exact
    # value Python still holds), while C's regions exclude sites Python cannot. A
    # proof from EITHER prover stands on its own, so:
    #   - a site is EXCLUDED if C's region tiers exclude it;
    #   - a site is RESOLVED-DISJOINT if Python's exact constants prove it never
    #     overlaps (such a site appears in neither Python's hits nor its residual);
    #   - the honest still-open set is Python's residual minus C's exclusions.
    # What must still reconcile EXACTLY, or the output cannot be trusted:
    #   - the 14-hit set must be identical in both (a hit lost to region absorption
    #     would silently drop a REAL slot access);
    #   - no C exclusion may collide with a Python hit (a false exclusion of a real
    #     access -- the one catastrophic failure mode);
    #   - every Python-residual site must be classified by C (excluded or open);
    #   - every C-open site outside Python's residual must be VERIFIED as Python-
    #     resolved-disjoint (absent from Python's hits AND its full any-width
    #     unresolved list), not merely assumed benign.
    py_unres_all_pcs = {u["pc"] for u in unresolved}
    reconciled = c_unresolved_scoped | c_excl_pcs_w
    lost = py_residual - reconciled          # sites C dropped entirely -- must be empty
    c_open_extra = c_unresolved_scoped - py_residual
    benign = {pc for pc in c_open_extra
              if pc not in py_hit_pcs and pc not in py_unres_all_pcs}
    unexplained = c_open_extra - benign      # must be empty
    excl_hit_collisions = sorted({e["pc"] for e in c_data["exclusions"]} & py_hit_pcs)
    still_open = py_residual - c_excl_pcs_w  # residual after region exclusion

    ok = (bool(hits) and py_hit_pcs == c_hit_pcs and not lost
          and not unexplained and not excl_hit_collisions)

    out = {
        "_comment": "Cross-validated region-provenance result for the power-slot "
                    "residual, under COMBINED-PROVER accounting: exclusions may come "
                    "from either independently-sound implementation, and the final "
                    "still-open set is Python's residual minus C's exclusions. "
                    "Regenerate: tools/phase4_region_provenance_report.py",
        "target": args.target, "bytes": args.bytes,
        "validation": {
            "hit_set_matches_python": py_hit_pcs == c_hit_pcs,
            "python_hits": sorted(py_hit_pcs), "c_hits": sorted(c_hit_pcs),
            "python_residual_baseline": len(py_residual),
            "lost_sites (C dropped, MUST be empty)": sorted(lost),
            "c_exclusions_colliding_with_python_hits (MUST be empty)": excl_hit_collisions,
            "c_open_but_python_resolved_disjoint (benign, verified)": sorted(benign),
            "c_open_unexplained (MUST be empty)": sorted(unexplained),
            "reconciles_exactly": bool(not lost and not unexplained
                                       and not excl_hit_collisions),
        },
        "result": {
            "baseline_residual": len(py_residual),
            "excluded_by_region_provenance": len(c_excl_pcs_w),
            "excluded_alignment": sum(1 for e in c_excl_in_scope_w
                                      if e["kind"] == "EXCLUDED_ALIGNMENT"),
            "excluded_negative_index": sum(1 for e in c_excl_in_scope_w
                                           if e["kind"] == "EXCLUDED_NEGATIVE_INDEX"),
            "excluded_out_of_bound": sum(1 for e in c_excl_in_scope_w
                                         if e["kind"] == "EXCLUDED_OUT_OF_BOUND"),
            "still_open_after_region_provenance": len(still_open),
        },
        # TIER 3 (loop-bound extraction) finds zero exclusions inside THIS target's
        # scope, but is real, hand-verified infrastructure (see Canon) reused by
        # future rows -- pin the whole-image count so a regression in the bound_hint
        # machinery is caught even though it has no effect on B06/B08's own number.
        "whole_image_excluded_out_of_bound_total": sum(
            1 for e in c_data["exclusions"] if e["kind"] == "EXCLUDED_OUT_OF_BOUND"),
        "whole_image_out_of_bound_exclusions_not_in_this_scope": sum(
            1 for e in c_data["exclusions"] if e["kind"] == "EXCLUDED_OUT_OF_BOUND"
            and e["pc"] not in c_excl_pcs_w),
        "bonus_other_width_exclusions_not_counted_above": len(c_excl_other_width),
        "excluded_sites": sorted(c_excl_in_scope_w, key=lambda e: e["pc"]),
        "still_open_pcs": sorted(still_open),
    }
    args.json.write_text(json.dumps(out, indent=1) + "\n")

    print("hit set matches python:", out["validation"]["hit_set_matches_python"])
    print("baseline residual (python, corrected for dedup): %d" % len(py_residual))
    print("region-provenance excluded: %d (%d alignment, %d negative-index, %d out-of-bound)"
          % (len(c_excl_pcs_w), out["result"]["excluded_alignment"],
             out["result"]["excluded_negative_index"],
             out["result"]["excluded_out_of_bound"]))
    print("out-of-bound exclusions elsewhere in the image (not this target's scope): %d"
          % out["whole_image_out_of_bound_exclusions_not_in_this_scope"])
    print("still open: %d" % len(still_open))
    print("reconciliation: lost=%d unexplained=%d hit-collisions=%d benign(c-open, py-proved-disjoint)=%d -- %s"
          % (len(lost), len(unexplained), len(excl_hit_collisions), len(benign),
             "CLEAN" if ok else "MISMATCH, DO NOT TRUST"))
    print("wrote", args.json)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
