"""Focused contracts for the frozen target-domain/exclusion pilot result."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_target_exclusion_pilot.json"
DRIVER = ROOT / "tools/phase4_target_exclusion_pilot.py"
PRIMARY_C = ROOT / "tools/phase4_target_exclusion_prover.c"
CROSS_C = ROOT / "tools/phase4_target_exclusion_crosscheck.c"

LOCAL_BASES = [
    "SCUS_942_88:0x80018a4c:jr:s6",
    "SCUS_942_88:0x80018b1c:jr:s6",
    "SCUS_942_88:0x80018bec:jr:s6",
    "SCUS_942_88:0x80018cbc:jr:s6",
]
TARGETS = ["0x80018cc4", "0x80018f4c", "0x80019244"]


@pytest.fixture(scope="module")
def pilot() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_artifact_is_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(DRIVER), "--check"], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_freeze_precedes_outcomes(pilot: dict) -> None:
    assert pilot["inputs"]["pre_outcome_freeze_commit"] == (
        "2e67ac74498c96989a858e08918983aaf5bdf73a")
    assert pilot["inputs"]["freeze_artifact_sha256"] == (
        "8b6cb83f9d2b95b099606f87e3b0f76b8520e391bdebfc5629f0bf45e1864ad2")
    assert pilot["configuration"]["pilot_frozen_before_outcomes"] is True
    assert pilot["pilot"]["attempted_count"] == 12


def test_both_c_implementations_agree(pilot: dict) -> None:
    controls = pilot["c_controls"]
    assert controls["primary_selftest"]["passed"] == 9
    assert controls["primary_selftest"]["total"] == 9
    assert controls["primary_selftest"]["verdict"] is True
    assert controls["independent_selftest"] == {
        "tool": "phase4_target_exclusion_crosscheck",
        "passed": 8, "total": 8, "verdict": True,
    }
    assert controls["all_12_classifications_agree"] is True
    assert controls["all_landed_exact_target_sets_agree"] is True
    assert controls["instruction_decoding_in_python"] is False


def test_four_exact_domains_are_local_bases_not_landed_proofs(pilot: dict) -> None:
    result = pilot["pilot"]
    assert result["landed_count"] == 0
    assert result["landed_site_ids"] == []
    assert result["local_domain_basis_count"] == 4
    assert result["local_domain_basis_site_ids"] == LOCAL_BASES
    local = [row for row in result["outcomes"]
             if row["local_proof_basis_kind"]]
    assert [row["site"] for row in local] == LOCAL_BASES
    for row in local:
        assert row["outcome"] == "NOT_LANDED_EXTERNAL_INTERIOR_ENTRY_UNIVERSE"
        assert row["proof_kind"] is None
        assert row["local_proof_basis_kind"] == "entry_scoped_full_target_domain"
        assert row["targets"] == TARGETS
        assert row["protected_set_intersection"] == []
        assert row["primary"]["full_target_domain_complete"] is True
        assert row["independent"]["full_target_domain_complete"] is True
        assert row["independent"]["targets"] == TARGETS
        assert [owner["entry"] for owner in row["target_owner_entries"]] == TARGETS
        assert all(owner["range_type"] in {"code", "thunk"}
                   for owner in row["target_owner_entries"])
        assert row["wall"]["reason"] == "blocked_external_interior_entry_universe"
        assert row["wall"]["entry_source_count"] == 175


def test_gate_grade_scope_reuses_and_tightens_entry_gate(pilot: dict) -> None:
    scope = pilot["gate_grade_entry_scope"]
    assert scope["owner"]["entry"] == "0x80018850"
    assert scope["owner"]["end"] == "0x80018cc4"
    assert scope["accepted_gate_helper_unknown_count"] == 156
    assert len(scope["accepted_gate_helper_unknown_site_ids"]) == 156
    assert scope["corrected_union_additional_count"] == 19
    assert len(scope["corrected_union_additional_site_ids"]) == 19
    assert scope["locally_exact_internal_site_ids"] == LOCAL_BASES
    assert scope["unresolved_entry_source_count"] == 175
    assert len(scope["unresolved_entry_source_ids"]) == 175
    assert scope["unresolved_internal_source_ids"] == [
        "SCUS_942_88:0x8001897c:jr:ra"]
    assert scope["unresolved_external_source_count"] == 174
    assert len(scope["unresolved_external_source_ids"]) == 174
    assert scope["concrete_external_interior_entries"] == []
    assert scope["entry_scope_closed"] is False
    assert (set(scope["accepted_gate_helper_unknown_site_ids"])
            | set(scope["corrected_union_additional_site_ids"])) == set(
                scope["unresolved_entry_source_ids"])


def test_dead_lexical_target_is_not_inflated(pilot: dict) -> None:
    assert pilot["pilot"]["dead_lexical_definition_correction"] == [{
        "site": "SCUS_942_88:0x80018cbc:jr:s6",
        "excluded_definition_occurrences": [{
            "definition_pc": "0x800188ec",
            "definition_word": "0x36d6961c",
            "excluded_from_domain": True,
            "proved": False,
            "reason": "definition_not_reachable_from_declared_entry",
        }],
    }]
    last = next(row for row in pilot["pilot"]["outcomes"]
                if row["site"] == "SCUS_942_88:0x80018cbc:jr:s6")
    assert "0x8001961c" not in last["targets"]
    assert last["targets"] == TARGETS


def test_every_failed_attempt_names_instruction_and_chain(pilot: dict) -> None:
    failures = [row for row in pilot["pilot"]["outcomes"]
                if not row["local_proof_basis_kind"]]
    assert len(failures) == 8
    reasons = [row["wall"]["reason"] for row in failures]
    assert reasons == [
        "query_site_not_entry_reachable",
        "source_constant_not_path_complete_or_evaluators_disagree",
        "source_constant_not_path_complete_or_evaluators_disagree",
        "entry_path_without_definition",
        "entry_path_without_definition",
        "entry_path_without_definition",
        "entry_path_without_definition",
        "entry_path_without_definition",
    ]
    assert all(re.fullmatch(r"0x[0-9a-f]{8}", row["wall"]["pc"])
               and re.fullmatch(r"0x[0-9a-f]{8}", row["wall"]["word"])
               for row in failures)
    assert all(row["register_or_cell_chain"]["primary_derivations"]
               for row in failures)
    assert all(row["writer_recursion_cycle"] == [] for row in failures)
    assert pilot["pilot"]["not_landed_count"] == 12
    assert pilot["pilot"]["not_landed_site_ids"] == pilot["pilot"]["site_ids"]
    assert all(re.fullmatch(r"0x[0-9a-f]{8}", row["wall"]["pc"])
               and re.fullmatch(r"0x[0-9a-f]{8}", row["wall"]["word"])
               for row in pilot["pilot"]["outcomes"])


def test_no_go_is_mandatory_and_stops_the_cascade(pilot: dict) -> None:
    decision = pilot["decision"]
    assert decision["verdict"] == "NO-GO"
    assert decision["go_conditions"] == {
        "at_least_four_landed": False,
        "at_least_one_whole_table_value_domain_invariant": False,
        "runtime_crosscheck_clean": False,
        "soundness_violation_absent": True,
    }
    assert decision["full_pass_authorized"] is False
    assert decision["cascade_started"] is False
    assert decision["queued_successor"] is None
    assert pilot["pilot"]["whole_table_candidate_count"] == 0
    assert pilot["pilot"]["whole_table_invariant_landed_count"] == 0
    assert pilot["stage_c_not_run"] == {
        "closure_census_delta": None,
        "caller_domain_frozen_20_rerun": False,
        "typed_state_regenerated": False,
        "campaign_regenerated": False,
        "old_pins_replaced": [],
    }


def test_no_go_prices_the_exact_remaining_bar(pilot: dict) -> None:
    report = pilot["no_go_report"]
    assert report["full_union_count"] == 179
    assert report["remaining_without_this_proof_count"] == 179
    assert len(report["remaining_without_this_proof_ids"]) == 179
    assert report["attempted_wall_count"] == 12
    assert report["unattempted_due_pilot_stop_count"] == 167
    assert report["remaining_stratum_histogram"] == {
        "table_backed": 74,
        "computed": 19,
        "register_provenance": 6,
        "return_like": 0,
        "return_like_unproved_incoming_ra": 9,
        "unclassified_opaque_definition": 38,
        "mixed_reaching_definitions": 33,
    }
    assert sum(report["remaining_stratum_histogram"].values()) == 179
    assert report["writer_recursion_cycle_count"] == 0
    assert report["writer_recursion_cycles"] == []
    paragraph = report["item2_bar_facts_no_recommendation"]
    assert "would have to accept exclusion for all 179" in paragraph
    assert "all 74 table/cell-backed candidates" in paragraph
    assert "175 unresolved transfer sites" in paragraph
    assert "zero source-site/indirect-target tuples" in paragraph
    assert report["recommendation_to_lower_bar"] is None


def test_gate_movement_is_staged_but_not_applied(pilot: dict) -> None:
    movement = pilot["per_edge_gate_movement"]
    assert movement["baseline_proved_site_count"] == 87
    assert movement["baseline_proved_edge_count"] == 492
    assert movement["local_proof_basis_site_ids"] == LOCAL_BASES
    assert movement["local_proof_basis_site_count"] == 4
    assert movement["local_proof_basis_edge_occurrence_count"] == 12
    assert len(movement["local_proof_basis_edge_ids"]) == 12
    assert movement["candidate_gate_grade_site_ids"] == []
    assert movement["candidate_gate_grade_edge_ids"] == []
    assert movement["candidate_gate_grade_site_count"] == 0
    assert movement["candidate_gate_grade_edge_occurrence_count"] == 0
    assert movement["applied_site_additions"] == []
    assert movement["applied_edge_additions"] == []
    assert movement["current_proved_site_count"] == 87
    assert movement["current_proved_edge_count"] == 492


def test_retained_runtime_evidence_is_not_promoted(pilot: dict) -> None:
    runtime = pilot["capsule_and_preserved_session_crosscheck"]
    assert runtime["status"] == "UNAVAILABLE_SITE_TIME_INDIRECT_TARGETS"
    assert runtime["capsule_universe"] == 50
    assert runtime["capsule_site_time_target_records"] == 0
    assert runtime["site_time_observations"] == []
    assert runtime["all_observed_targets_within_proved_sets"] is None
    assert runtime["soundness_violation"] is False
    assert runtime["clean_for_go"] is False
    assert runtime["locally_decided_but_not_gate_grade_site_ids"] == LOCAL_BASES
    assert [row["hits_capped_at_60"] for row in runtime[
        "preserved_entry_observations"]] == [0, 60, 60, 60]
    assert runtime["live_or_instrumented_replay_performed"] is False


def test_f01_and_protected_surfaces_do_not_move(pilot: dict) -> None:
    assert pilot["protected_state"] == {
        "f01_status": "partial",
        "item_2": "not_met",
        "dimension_promoted": False,
        "item2_ready_for_review": False,
        "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
        "mechanics_baseline_modified": False,
        "registry_modified": False,
        "gate_receipt_modified": False,
        "writer_universe_gate_modified": False,
        "value_domain_gate_modified": False,
    }


def test_both_c_sources_rebuild_with_werror(tmp_path: Path) -> None:
    expected = {PRIMARY_C: 9, CROSS_C: 8}
    for source, count in expected.items():
        binary = tmp_path / source.stem
        compile_run = subprocess.run(
            ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-o", str(binary), str(source)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert compile_run.returncode == 0, compile_run.stderr
        selftest = subprocess.run(
            [str(binary), "--self-test"], cwd=ROOT,
            capture_output=True, text=True,
        )
        assert selftest.returncode == 0, selftest.stdout + selftest.stderr
        assert json.loads(selftest.stdout)["passed"] == count
