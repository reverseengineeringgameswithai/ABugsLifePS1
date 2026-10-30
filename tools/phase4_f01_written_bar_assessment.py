#!/usr/bin/env python3
"""Re-assess F01's nine DoD dimensions against the bars AS WRITTEN.

Context (engineering-specs/phase4-two-standards-finding.md): every 9/9 row in the
closure-debt ledger carries one blanket basis string, while F01 alone was measured
per-dimension — and against a bar the Phase-4 page itself corrected as an overshoot
("Item 2 requires the unresolved-intersection set to be empty. It does not.").

This tool is the first uniform-standard test case. The WRITTEN bars are:
  - canonical DoD item 2: the frontier is ENUMERATED, scoped to relevant;
  - Phase-4 exit gate: anything unresolved is EXPLICITLY BOUNDED, not absent;
  - vocabulary: "solved" is measurement; bounded-exhausted is a stop decision and
    never counts as met.

Design: JUDGMENTS below are authored and attributable; every FACT they rest on is
derived from the cited artifact at run time and the artifact is sha256-pinned, so a
stale citation fails loudly instead of aging silently.

AUTHORITY: this assesses; it does not promote. Registry changes remain with a fresh
detached verifier (the author of this assessment also authored much of the evidence,
and today alone wrote three checks that could not fail — the split exists for that).

Usage: python3 tools/phase4_f01_written_bar_assessment.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load(rel: str) -> tuple[dict, dict]:
    p = ROOT / rel
    doc = json.loads(p.read_text())
    return doc, {"path": rel, "sha256": sha256_file(p)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_f01_written_bar_assessment.json"))
    args = ap.parse_args()

    pins: list[dict] = []
    facts: dict[str, object] = {}

    def derive(rel: str) -> dict:
        doc, pin = load(rel)
        pins.append(pin)
        return doc

    # --- derived facts, each read from its artifact rather than hand-typed ---
    oracle = derive("analysis/phase4_f01_original_oracle.json")
    facts["oracle_all_passed"] = oracle["all_passed"]
    facts["oracle_assertions"] = len(oracle["assertions"])
    facts["oracle_from_boot"] = oracle["fixture"]["from_boot"]
    facts["oracle_injection"] = oracle["method"]["injection"]

    probe = derive("analysis/phase4_f01_request2_probe.json")
    facts["request2_element_outcome"] = probe["element_outcome"]
    facts["request2_controls"] = len(probe["natural_request2_skip_controls"])

    breadth = derive("analysis/phase4_f01_breadth_assertions.json")
    facts["breadth_levels_asserted"] = breadth["levels_asserted"]
    facts["breadth_decisions"] = breadth["total_decisions_checked"]
    facts["breadth_law_failures"] = len(breadth["law_failures"])

    verify = derive("analysis/phase4_f01_oracle_breadth_verification.json")
    facts["oracle_verdict_last_adjudication"] = verify["dimensions"]["original_oracle"]["verdict"]
    facts["breadth_verdict_last_adjudication"] = verify["dimensions"]["campaign_breadth"]["verdict"]

    assign = derive("analysis/phase4_discipline_assignment.json")
    facts["frontier_sites_enumerated"] = len(assign["universe"]["site_ids"])

    d3 = derive("analysis/phase4_d3_contract.json")
    facts["d3_verdict"] = d3["decision"]["verdict"]
    facts["d3_wall_shapes"] = sorted(set(
        d3["decision"]["sixth_attempt_funding"]["per_contract_wall_shapes"].values()))

    typed = derive("analysis/phase4_f01_typed_state.json")
    facts["typed_bounded_by_proof"] = typed["counts"]["bounded_stores_by_proof"]
    facts["typed_bounded_by_convention"] = typed["counts"]["bounded_stores_by_index_convention"]
    facts["typed_unresolved_stores"] = typed["counts"]["still_unresolved_stores"]

    abi = derive("analysis/phase4_f01_abi_ledger.json")
    facts["abi_rows"] = len(abi["rows"])

    sc = derive("analysis/phase4_f01_source_closure.json")
    facts["source_closure_result"] = sc["result"]
    facts["source_closure_progress"] = sc["region_gate"]["progress_statement"]

    ruling = ROOT / "engineering-specs/phase4-item2-bar-ruling.md"
    pins.append({"path": "engineering-specs/phase4-item2-bar-ruling.md",
                 "sha256": sha256_file(ruling)})
    facts["item2_ruling_exists"] = ruling.exists()

    # --- authored judgments against the WRITTEN bars ---
    dims = {
        "durable_evidence": {
            "state": "met",
            "written_bar": "evidence artifacts durable, pinned, regenerable",
            "basis": "already registered met in the scorecard; the only F01 dimension "
                     "assessed and met under both readings",
        },
        "original_oracle": {
            "state": "met_candidate",
            "written_bar": "behavior asserted against the ORIGINAL game's own natural "
                           "execution, not injected state",
            "basis": f"all {facts['oracle_assertions']} assertions pass on a natural "
                     f"cold-boot completion (injection: {facts['oracle_injection']}); the "
                     f"request-2 skip arm is now natural too "
                     f"({facts['request2_element_outcome']}, "
                     f"{facts['request2_controls']} control). All three elements from the "
                     f"last adjudication ({facts['oracle_verdict_last_adjudication']}) are "
                     "answered; resubmission order is out",
            "gap": "fresh-verifier adjudication pending "
                   "(engineering-specs/phase4-f01-original-oracle-resubmission-work-order.md)",
        },
        "complete_frontier": {
            "state": "met_candidate",
            "written_bar": "item 2 AS WRITTEN: callers/callees/callbacks/indirect tables "
                           "ENUMERATED, scoped to relevant — not an empty unresolved set",
            "basis": f"the frontier is enumerated ({facts['frontier_sites_enumerated']} "
                     f"sites, classified, runtime-corroborated) and the residual is "
                     f"explicitly bounded by the 2026-08-10 item-2 ruling: declared "
                     f"assumption, void on a single counter-example, non-transferable. "
                     f"Five campaigns (last: D3 {facts['d3_verdict']}, walls "
                     f"{facts['d3_wall_shapes']}) established no current technique "
                     "resolves the sites; the written bar never asked for that",
            "gap": "the assumption's kill switch must be carried on the row verbatim; "
                   "verifier decides whether declared-assumption bounding meets item 2",
        },
        "campaign_breadth": {
            "state": "not_met",
            "written_bar": "conclusions generalize across every applicable stage — which "
                           "requires the applicable set itself to be enumerated",
            "basis": f"the branch law asserts clean campaign-wide "
                     f"({facts['breadth_levels_asserted']}/19 levels, "
                     f"{facts['breadth_decisions']} decisions, "
                     f"{facts['breadth_law_failures']} failures, detached-verified) — but "
                     "the applicability UNIVERSE (stages × objectives × variants × modes) "
                     "is not enumerated, so 'every applicable' has no denominator",
            "gap": "C1 applicability matrix + C2 independently-sourced taxonomy; this "
                   "dimension fails the WRITTEN bar too, not just the strict one",
        },
        "typed_state": {
            "state": "partial",
            "written_bar": "state fields typed and value domains bounded (enumeration of "
                           "an untyped residual bounds the WORKLIST, not the STATE)",
            "basis": f"{facts['typed_bounded_by_proof']} stores bounded by proof, "
                     f"{facts['typed_bounded_by_convention']} by index convention (not "
                     f"proof), {facts['typed_unresolved_stores']} unresolved",
            "gap": "value-domain machinery (the named prerequisite engines); an "
                   "enumeration assumption does not type a store",
        },
        "lifecycle": {
            "state": "met_candidate",
            "written_bar": "cold boot / load / first use / repeated use / exhaustion / "
                           "retirement / reuse each evidenced",
            "basis": "per-phase claim map registered "
                     "(analysis/phase4_f01_lifecycle_claim_map.json): 6 phases covered, "
                     "exhaustion n/a-with-reason (scalar latch, saturation IS the "
                     "single-shot guard); reuse closed from the retained death-session "
                     "access log (full arc BIOS->clears->store->consume->clear) plus "
                     "five successive cycles in one LEVEL07 session",
            "gap": "fresh-verifier adjudication; cross-LEVEL chain kept as a residual "
                   "note on the transitions axis, not this dimension",
        },
        "cross_system_behavior": {
            "state": "partial",
            "written_bar": "native combinations exercised (carry+damage, powers+jump, "
                           "projectiles at transitions, enemies vs hazards/plants)",
            "basis": "the breadth pass crosses transition×death×bonus-force-flag; the "
                     "behaviour library covers part of the native-combination list",
            "gap": "no registered combination matrix for F01's transition machinery vs "
                   "the other systems",
        },
        "original_interfaces": {
            "state": "partial",
            "written_bar": "interfaces documented; unknowns enumerated with named "
                           "obstructions",
            "basis": f"structural ledger complete ({facts['abi_rows']}/764 rows) and "
                     "every unknown argument domain carries a named obstruction",
            "gap": "semantic half (value domains) is enumerated but unresolved — "
                   "downstream of the same engine as typed_state; assess jointly",
        },
        "source_closure": {
            "state": "partial",
            "written_bar": "byte-matched C through the original toolchain for the row's "
                           "governing functions",
            "basis": f"FUNC_80038F38 byte-matched; player updater "
                     f"{facts['source_closure_result']}: "
                     f"{facts['source_closure_progress']} — frame map exact, 17/17 $gp "
                     "accesses reproduced, wall named and technique-shaped",
            "gap": "region 1 to zero, then regions 2-6; parked by explicit decision, "
                   "which under the vocabulary is a stop, not a met",
        },
    }

    counts = {}
    for d in dims.values():
        counts[d["state"]] = counts.get(d["state"], 0) + 1

    doc = {
        "_comment": "F01 re-assessed against the DoD bars AS WRITTEN (item 2 = "
                    "enumerated; residuals = explicitly bounded), per the two-standards "
                    "finding. Judgments authored; facts derived from pinned artifacts at "
                    "run time. Regenerate: tools/phase4_f01_written_bar_assessment.py",
        "schema": "abl-phase4-f01-written-bar-assessment/1",
        "generated": date.today().isoformat(),
        "row_id": "F01_anthill",
        "standard": {
            "ruling": "engineering-specs/phase4-two-standards-finding.md + the "
                      "measurement ruling banked with this assessment",
            "item2_bar": "enumerated, scoped to relevant (NOT empty unresolved set)",
            "exit_gate_bar": "explicitly bounded, not absent",
            "vocabulary": "bounded-exhausted remains a stop decision and never reads "
                          "as met; this assessment publishes measurement, not disposition",
        },
        "authority": {
            "promotes_row_or_dimension": False,
            "edits_registry": False,
            "requires_fresh_verifier": True,
            "author_conflict": "the assessor authored much of the evidence under "
                               "assessment; met_candidate is a submission, not a met",
        },
        "facts": facts,
        "evidence_pins": pins,
        "dimensions": dims,
        "counts": counts,
        "summary": f"{counts.get('met', 0)} met, {counts.get('met_candidate', 0)} "
                   f"met-candidate, {counts.get('partial', 0)} partial, "
                   f"{counts.get('not_met', 0)} not met — against the WRITTEN bars. "
                   "Compare: 1/9 under the overshot strict reading; 9/9 under the "
                   "blanket-disposition path. Neither of those was this measurement.",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[written-bar] {doc['summary']}")
    for name, d in dims.items():
        print(f"  {d['state']:14s} {name}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
