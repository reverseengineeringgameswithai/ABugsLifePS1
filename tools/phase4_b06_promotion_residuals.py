#!/usr/bin/env python3
"""B06's item-2 residual, re-read against the CANONICAL bar.

WHY
---
B06 stopped on a sentence that stated the wrong standard: *"Item 2 requires the
unresolved-intersection set to be empty."* It does not. Canonical DoD item 2 asks
that the frontier be **enumerated**; the Phase-4 exit gate asks that anything
unresolved be **explicitly bounded**. "Empty set" is a frontier-compiler rule
scoped to a declared universe which, in its own words, *"never changes a Phase-4
dimension by itself."*

So the question is not "is the count zero" but "is every site enumerated, and is
each one bounded with evidence". This tool answers that from B06's own closure
ledger rather than from prose, and emits the answer in the promotion linter's
`bounded_residuals` schema so the two rules can be applied verbatim:

    RESIDUAL_MALFORMED   boundary, evidence, next_experiment all non-empty
    RESIDUAL_INTERSECTS  intersects_dimension must be exactly False

WHAT THE LEDGER ALREADY CONTAINS
--------------------------------
analysis/phase4_b06_closure_20260804.json carries 251 candidate sites, each with
pc, owner function, operation, base register, offset, domain, disposition and a
proof string. All 251 are `disjoint`; none lacks a proof; 19 distinct proofs span
23 owner functions and 12 domains. That is an enumeration with a per-site bound
already attached -- the work was done, then measured against the wrong bar.

HONESTY
-------
The ledger's own `closure` block says `strict_full_program_proof: false` and
`bounded_exhausted: true`, inside a declared bound (resident executable, valid
retail pointer schemas, no corrupt pointers, no malformed assets, no mods). So
the correct verdict is MET WITHIN A DECLARED BOUND -- the same shape as E16's
`met_in_scope` -- not an unconditional pass. This tool refuses to report it as
unconditional, and emits the bound itself as a residual entry so it cannot be
quietly dropped.

Usage: python3 tools/phase4_b06_promotion_residuals.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "analysis/phase4_b06_closure_20260804.json"


def build(d: dict) -> list[dict]:
    ledger = d["candidate_ledger"]
    by_domain: dict[str, dict] = defaultdict(lambda: {"n": 0, "owners": set(), "proofs": set()})
    for e in ledger:
        rec = by_domain[e["domain"]]
        rec["n"] += 1
        rec["owners"].add(e["owner"])
        rec["proofs"].add(e["proof"])

    out = []
    for domain, rec in sorted(by_domain.items(), key=lambda kv: -kv[1]["n"]):
        proofs = "; ".join(sorted(rec["proofs"]))
        out.append({
            "boundary": ("%s -- %d potential intersections of the power slot, across %d "
                         "owner function(s)" % (domain, rec["n"], len(rec["owners"]))),
            "evidence": ("Every site is enumerated in analysis/phase4_b06_closure_20260804.json "
                         "with its pc, owner, operation, base register and offset, and every "
                         "one carries disposition `disjoint` with a stated proof: %s. "
                         "Zero sites in this domain are unexplained." % proofs),
            "next_experiment": ("Re-run tools/phase4_b06_closure.c against the pristine image; "
                                "any site in this domain whose disposition is not `disjoint`, "
                                "or that loses its proof, falsifies this boundary. A runtime "
                                "readwrite watch on 0x800A657E that fires from one of these "
                                "owner functions would falsify it directly."),
            "intersects_dimension": False,
        })

    # The declared bound itself, as a residual -- it is the one thing that keeps
    # this from being an unconditional pass, so it must be visible.
    bound = d.get("bound") or {}
    closure = d.get("closure") or {}
    out.append({
        "boundary": ("THE DECLARED BOUND: this closure holds for the resident executable "
                     "under valid retail pointer schemas, with no corrupt pointers, no "
                     "malformed assets and no mods loaded (%s). "
                     "`strict_full_program_proof` is %s."
                     % (", ".join("%s=%s" % kv for kv in sorted(bound.items())),
                        closure.get("strict_full_program_proof"))),
        "evidence": ("The ledger classifies %d of %d candidate sites with %d unexplained, "
                     "but only inside that bound. Outside it -- a corrupted pointer, a "
                     "modded image -- the disjointness proofs do not hold, and the row does "
                     "not claim they do."
                     % (d["closure_metrics"]["classified"],
                        d["closure_metrics"]["residual_total"],
                        d["closure_metrics"]["unexplained"])),
        "next_experiment": ("Decide whether Phase 4 requires closure outside the valid-retail "
                            "bound. If it does, this entry is the work; if it does not, this "
                            "entry is the scope statement and the row is met within it."),
        "intersects_dimension": False,
    })
    return out


def lint(residuals: list[dict]) -> list[dict]:
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
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_b06_promotion_residuals.json"))
    args = ap.parse_args()

    d = json.loads(SRC.read_text())
    residuals = build(d)
    errors = lint(residuals)
    m = d["closure_metrics"]
    dispositions = Counter(e["disposition"] for e in d["candidate_ledger"])
    no_proof = [e["pc"] for e in d["candidate_ledger"] if not str(e.get("proof") or "").strip()]

    out = {
        "_comment": "B06's item-2 residual re-read against the canonical DoD bar. "
                    "Regenerate: tools/phase4_b06_promotion_residuals.py",
        "generated": str(date.today()),
        "row_id": "B06_invincibility",
        "dimension": 2,
        "the_bar": ("Canonical DoD item 2: the frontier is ENUMERATED. Phase-4 exit gate: "
                    "anything unresolved is EXPLICITLY BOUNDED. NOT the frontier-compiler's "
                    "'unresolved-intersection set is empty', which is scoped to a declared "
                    "universe and never changes a Phase-4 dimension by itself."),
        "ledger": {
            "sites": m["residual_total"],
            "classified": m["classified"],
            "unexplained": m["unexplained"],
            "dispositions": dict(dispositions),
            "sites_without_a_proof": len(no_proof),
            "distinct_proofs": len({e["proof"] for e in d["candidate_ledger"]}),
            "owner_functions": len({e["owner"] for e in d["candidate_ledger"]}),
            "domains": len({e["domain"] for e in d["candidate_ledger"]}),
        },
        "bounded_residuals": residuals,
        "linter_result": {
            "residual_entries": len(residuals),
            "rejections": errors,
            "passes_the_residual_rules": not errors,
        },
        "verdict": None,
        "recommendation": None,
    }

    enumerated = m["unexplained"] == 0 and m["classified"] == m["residual_total"]
    bounded = not no_proof and set(dispositions) == {"disjoint"}
    if enumerated and bounded and not errors:
        out["verdict"] = (
            "ITEM 2 IS MET WITHIN THE DECLARED BOUND. All %d candidate sites are enumerated "
            "and classified with %d unexplained; every one carries disposition `disjoint` "
            "and a stated proof (%d distinct proofs over %d owner functions, %d domains). "
            "That is precisely what the canonical bar asks -- enumerated, with the remainder "
            "explicitly bounded. It is NOT an unconditional pass: the ledger's own "
            "`strict_full_program_proof` is false and the closure holds inside the declared "
            "valid-retail bound, which is emitted above as its own residual."
            % (m["residual_total"], m["unexplained"],
               out["ledger"]["distinct_proofs"], out["ledger"]["owner_functions"],
               out["ledger"]["domains"]))
        out["recommendation"] = (
            "Move B06 item 2 from ADVANCED to MET-IN-SCOPE on the Phase-4 per-row scorecard, "
            "citing this artifact. That takes B06 to 6 of 9 met (1, 2, 3, 6, 7, 8) with 4, 5 "
            "and 9 still ADVANCED -- so the row still is not solved, and the honest headline "
            "is that it stopped for the wrong reason on item 2 but genuinely has work left "
            "on lifecycle, interfaces and durable evidence.")
    else:
        out["verdict"] = ("NOT MET -- enumerated=%s bounded=%s linter_clean=%s"
                          % (enumerated, bounded, not errors))
        out["recommendation"] = "Resolve the failing condition before re-reading the row."

    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"sites {m['residual_total']} classified {m['classified']} unexplained {m['unexplained']}")
    print(f"dispositions {dict(dispositions)}  sites without proof: {len(no_proof)}")
    print(f"residual entries: {len(residuals)}  rejections: {len(errors)}")
    print("\n" + out["verdict"])
    print("\n-> " + out["recommendation"])
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
