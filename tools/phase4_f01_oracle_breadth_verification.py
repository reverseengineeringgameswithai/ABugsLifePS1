#!/usr/bin/env python3
"""Recompute the offline half of the F01 oracle/breadth adjudication.

Live replay receipts are intentionally retained as observations in the verdict
artifact.  This checker recomputes every claim that can be decided from tracked
sources plus the locally preserved, hash-named movies: assertion-mutation
behavior, cycle-window sensitivity, preservation pins, corpus arithmetic,
authority flags, and the two submitted dimension bars.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "analysis/phase4_f01_oracle_breadth_verification.json"
ORACLE = ROOT / "analysis/phase4_f01_original_oracle.json"
BREADTH = ROOT / "analysis/phase4_f01_breadth_assertions.json"
OBSERVATION_SWEEP = ROOT / "analysis/phase4_f01_campaign_breadth.json"
FIXTURES = ROOT / "analysis/phase0_2_external_fixture_set.json"
PRIOR_WITNESS = ROOT / "analysis/phase4_f01_finalizer_witness.json"
ORACLE_TOOL = ROOT / "tools/phase4_f01_original_oracle.py"
BREADTH_TOOL = ROOT / "tools/phase4_f01_breadth_assert.py"
SUBMITTED_COMMIT = "a3aa41270c0c78373d4afb85e8f4e94f6731059b"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def submitted_bytes(path: Path) -> bytes:
    """Read the adjudicated submission, not whatever repaired bytes exist now."""
    rel = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "show", f"{SUBMITTED_COMMIT}:{rel}"], cwd=ROOT
    )


def submitted_json(path: Path) -> dict:
    return json.loads(submitted_bytes(path))


def external_identity(path_value: str, fixture_keys: set[str]) -> str:
    """Return a repository-relative identity without trusting its old checkout root."""
    path = Path(path_value)
    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        matches = sorted(
            key for key in fixture_keys
            if path.as_posix().endswith(f"/{key}")
        )
        if len(matches) != 1:
            raise ValueError(
                f"cannot map external path to exactly one central identity: {path}"
            )
        return matches[0]


def provisioned_path(identity: str) -> Path:
    """Resolve only inside the verifier's explicitly provisioned checkout tree."""
    return ROOT / identity


def assertion_passes(assertion: dict, actual) -> bool:
    expected = assertion["expected"]
    if assertion["op"] == "le":
        return actual is not None and actual <= expected
    if assertion["op"] == "ge":
        return actual is not None and actual >= expected
    return actual == expected


def oracle_mutations(assertions: list[dict]) -> list[dict]:
    adverse = {
        "objective_completed_naturally": False,
        "consumer_proceeded": 0,
        "request_produced_by_gameplay_not_injected": [2],
        "other_skip_condition_ruled_out": [1],
        "finalizer_ran_for_this_decision": 0,
        "finalizer_immediately_follows_the_decision": 201,
    }
    rows = []
    for assertion in assertions:
        mutated = adverse[assertion["id"]]
        rows.append({
            "id": assertion["id"],
            "retained_passes": assertion_passes(assertion, assertion["actual"]),
            "mutation": mutated,
            "mutation_passes": assertion_passes(assertion, mutated),
        })
    return rows


def breadth_window_analysis(breadth: dict) -> dict:
    rows = []
    for level, result in sorted(breadth["results"].items()):
        finalizers = [
            decision["cycle"] + decision["delta_cycles"]
            for decision in result["decisions"]
            if decision["finalizer_observed"]
        ]
        for decision in result["decisions"]:
            later = sorted(cycle - decision["cycle"] for cycle in finalizers
                           if cycle > decision["cycle"])
            rows.append({
                "level": level,
                "cycle": decision["cycle"],
                "predicts_call": decision["law_predicts_finalizer"],
                "nearest_later_finalizer_cycles": later[0] if later else None,
            })

    call_deltas = sorted({row["nearest_later_finalizer_cycles"] for row in rows
                          if row["predicts_call"]})
    skip_deltas = sorted(row["nearest_later_finalizer_cycles"] for row in rows
                         if not row["predicts_call"] and
                         row["nearest_later_finalizer_cycles"] is not None)

    def failures(window: int) -> int:
        count = 0
        for row in rows:
            observed = (row["nearest_later_finalizer_cycles"] is not None and
                        0 < row["nearest_later_finalizer_cycles"] <= window)
            count += observed != row["predicts_call"]
        return count

    transitions = []
    previous = None
    for window in range(0, 10001):
        current = failures(window)
        if current != previous:
            transitions.append({"window": window, "law_failures": current})
            previous = current

    return {
        "windows_evaluated": 10001,
        "range": [0, 10000],
        "call_deltas": call_deltas,
        "nearest_skip_to_later_finalizer_cycles": skip_deltas[0],
        "stable_passing_interval": [call_deltas[-1], skip_deltas[0] - 1],
        "retained_window": breadth["law"]["cycle_window"],
        "retained_window_inside_stable_interval": (
            call_deltas[-1] <= breadth["law"]["cycle_window"] < skip_deltas[0]
        ),
        "transitions_through_10000": transitions,
    }


def build_offline() -> dict:
    oracle_bytes = submitted_bytes(ORACLE)
    breadth_bytes = submitted_bytes(BREADTH)
    oracle = json.loads(oracle_bytes)
    breadth = json.loads(breadth_bytes)
    observation = submitted_json(OBSERVATION_SWEEP)
    fixtures = submitted_json(FIXTURES)["entries"]
    prior = submitted_json(PRIOR_WITNESS)
    oracle_source = submitted_bytes(ORACLE_TOOL).decode()
    breadth_source = submitted_bytes(BREADTH_TOOL).decode()

    fixture_keys = set(fixtures)
    oracle_movie_identity = external_identity(
        oracle["fixture"]["movie"], fixture_keys)
    oracle_movie = provisioned_path(oracle_movie_identity)
    oracle_movie_doc = load(oracle_movie)
    oracle_pin = fixtures.get(oracle_movie_identity)

    breadth_identities = []
    save_identities = []
    for level, result in sorted(breadth["results"].items()):
        movie_identity = external_identity(result["movie"], fixture_keys)
        path = provisioned_path(movie_identity)
        central = fixtures.get(movie_identity)
        breadth_identities.append({
            "level": level,
            "movie": movie_identity,
            "actual_matches_artifact": sha256_file(path) == result["movie_sha256"],
            "central_pin_matches": bool(
                central and central.get("sha256") == result["movie_sha256"]
            ),
        })
        start_state = load(path).get("start_state") or {}
        if start_state.get("from_boot") is False:
            save_rel = external_identity(start_state["path"], fixture_keys)
            save_path = provisioned_path(save_rel)
            save_pin = fixtures.get(save_rel)
            save_identities.append({
                "actual_matches_movie_metadata": (
                    sha256_file(save_path) == start_state.get("sha256")),
                "central_pin_matches": bool(
                    save_pin and save_pin.get("sha256") == start_state.get("sha256")
                ),
            })

    formal_mutations = oracle_mutations(oracle["assertions"])
    decision_rows = [decision for result in breadth["results"].values()
                     for decision in result["decisions"]]
    level_decisions = {level: len(result["decisions"])
                       for level, result in sorted(breadth["results"].items())}

    structured_type_keys = {
        "level_types", "level_type_mapping", "type_mapping", "taxonomy"
    }
    structured_applicability_keys = {
        "applicability_universe", "applicability_matrix", "coverage_matrix"
    }
    return {
        "submitted_hashes": {
            "original_oracle": hashlib.sha256(oracle_bytes).hexdigest(),
            "campaign_breadth": hashlib.sha256(breadth_bytes).hexdigest(),
        },
        "original_oracle": {
            "formal_assertions": len(formal_mutations),
            "formal_assertions_passing": sum(
                row["retained_passes"] for row in formal_mutations),
            "formal_mutations_rejected": sum(
                not row["mutation_passes"] for row in formal_mutations),
            "formal_mutation_ids_rejected": [
                row["id"] for row in formal_mutations
                if not row["mutation_passes"]
            ],
            "movie_actual_matches_artifact": (
                sha256_file(oracle_movie) == oracle["fixture"]["movie_sha256"]),
            "movie_metadata_from_boot": (
                oracle_movie_doc.get("start_state", {}).get("from_boot") is True),
            "movie_metadata_start_path_empty": (
                oracle_movie_doc.get("start_state", {}).get("path") == ""),
            "movie_central_pin_present": oracle_pin is not None,
            "generator_derives_from_boot_from_movie": (
                "get(\"start_state\")" in oracle_source or
                "get('start_state')" in oracle_source),
            "generator_gates_trace_truncation": (
                "truncated" in oracle_source.split("assertions =", 1)[1]
                .split("doc =", 1)[0]),
            "natural_request_values": oracle["leaves"]["request_at_decision"],
            "prior_request2_witness_anchor": prior["identity"]["anchor_class"],
            "prior_request2_witness_is_injected": (
                "writes u16 2" in prior["claim"]["observation_scope"]),
        },
        "campaign_breadth": {
            "levels": len(breadth["results"]),
            "decisions": len(decision_rows),
            "predicted_call": sum(row["law_predicts_finalizer"]
                                  for row in decision_rows),
            "predicted_skip": sum(not row["law_predicts_finalizer"]
                                  for row in decision_rows),
            "law_failures": len(breadth["law_failures"]),
            "levels_with_at_least_one_decision": sum(
                count > 0 for count in level_decisions.values()),
            "untruncated_levels": sum(
                result["exec_trace_truncated"] is False
                for result in breadth["results"].values()),
            "actual_movie_hashes_matching": sum(
                row["actual_matches_artifact"] for row in breadth_identities),
            "central_movie_pins_matching": sum(
                row["central_pin_matches"] for row in breadth_identities),
            "state_anchors": len(save_identities),
            "state_anchor_hashes_matching": sum(
                row["actual_matches_movie_metadata"] for row in save_identities),
            "central_state_anchor_pins_matching": sum(
                row["central_pin_matches"] for row in save_identities),
            "empty_result_set_would_pass_consolidator": True,
            "zero_decision_level_would_pass_consolidator": True,
            "truncated_level_would_pass_consolidator": True,
            "why_meta_mutations_pass": (
                "consolidate gates only `not fails` and `not errs`; it does not "
                "require an exact level universe, a decision, or non-truncation"),
            "structured_level_type_mapping_present": any(
                key in observation or key in breadth for key in structured_type_keys),
            "structured_applicability_matrix_present": any(
                key in observation or key in breadth
                for key in structured_applicability_keys),
            "window_sensitivity": breadth_window_analysis(breadth),
        },
        "authority": {
            "oracle_cannot_promote": (
                oracle["authority"]["promotes_row_or_dimension"] is False),
            "breadth_cannot_promote": (
                breadth["authority"]["promotes_campaign_breadth"] is False and
                breadth["authority"]["changes_f01_status"] is False),
            "oracle_scope": oracle["authority"]["bounded_to"],
            "breadth_movies_from_boot": sum(
                result["from_boot"] for result in breadth["results"].values()),
        },
        "source_shape_witnesses": {
            "oracle_from_boot_literal_is_hardcoded": '"from_boot": True' in oracle_source,
            "oracle_media_path_is_not_normalized": (
                '"path": media.get("path")' in oracle_source),
            "breadth_consolidator_gate": (
                '(not fails) and not errs' in breadth_source),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print", dest="print_report", action="store_true")
    args = parser.parse_args()

    offline = build_offline()
    if args.print_report:
        print(json.dumps(offline, indent=1, sort_keys=True))
    if args.check:
        retained = load(VERDICT)
        if retained.get("offline_recomputed") != offline:
            print("[f01-verifier] FAIL: retained offline evidence differs")
            return 1
        print("[f01-verifier] PASS: offline evidence reproduces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
