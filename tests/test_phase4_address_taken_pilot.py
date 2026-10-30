"""Focused contract tests for the frozen four-root address-taken pilot."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_address_taken_pilot as pilot  # noqa: E402

ARTIFACT = ROOT / "analysis/phase4_address_taken_pilot.json"
PRIMARY = ROOT / "tools/phase4_address_taken_pilot.c"
INDEPENDENT = ROOT / "tools/phase4_address_taken_crosscheck.c"


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_receipt_is_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(ROOT / "tools/phase4_address_taken_pilot.py"), "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_pre_outcome_freeze_is_exact_and_ancestral(receipt: dict) -> None:
    assert receipt["inputs"]["issued_baseline_commit"] == pilot.BASELINE_COMMIT
    assert receipt["inputs"]["pre_outcome_freeze_commit"].startswith(pilot.FREEZE_COMMIT)
    assert receipt["pilot_universe"]["targets"] == [
        {"root": pilot._target_key(row), "witness": pilot._witness_key(row)}
        for row in pilot.TARGETS
    ]
    assert receipt["pilot_universe"]["root_count"] == 4
    assert receipt["pilot_universe"]["unique_witness_address_count"] == 3


def test_prior_receipt_did_not_record_address_occurrences(receipt: dict) -> None:
    for row in receipt["prior_receipt_witness_semantics"]:
        assert row["source_field"].endswith("relevant_unproved_indirect_edges[0]")
        assert row["was_recorded_as_address_taken_occurrence"] is False
        assert row["prior_address_taken_occurrence_count"] == 0


def test_stage_a_exact_occurrence_sets_and_second_implementation(receipt: dict) -> None:
    roots = receipt["stage_a"]["primary"]["roots"]
    assert {row["key"]: row["occurrence_count"] for row in roots} == {
        "LEVEL02_LEVEL1:0x800b3f08": 0,
        "LEVEL08_LEVEL1:0x800b4084": 0,
        "LEVEL05_LEVEL:0x800b3d80": 0,
        "SCUS_942_88:0x8005c58c": 1,
    }
    resident = roots[-1]["occurrences"]
    assert resident == [{
        "coexists_with_root": True,
        "containing_range": None,
        "id": "SCUS_942_88:0x8001b854:aligned_literal_word",
        "image": "SCUS_942_88",
        "kind": "aligned_literal_word",
        "proved_table_membership": {
            "hi": "0x8001b87c",
            "lo": "0x8001b848",
            "source": "phase3_jr_tables",
        },
        "va": "0x8001b854",
    }]
    exact = receipt["stage_a"]["exact_sets_both_directions"]
    assert exact["per_data_region_member_ids"] == {
        "SCUS_942_88:0x8001b848..0x8001b87c": [
            "SCUS_942_88:0x8005c58c@SCUS_942_88:0x8001b854:aligned_literal_word"
        ]
    }
    cross = receipt["stage_a"]["independent_crosscheck"]
    assert cross["all_exact_sets_agree"] is True
    assert cross["disagreements"] == []
    assert cross["primary_selftest"]["passed"] == 10
    assert cross["independent_selftest"]["passed"] == 4


def test_fixed_witness_labels_are_machine_falsified(receipt: dict) -> None:
    rows = receipt["fixed_witness_resolution"]
    assert [(row["witness"], row["word"], row["containing_range"]["type"],
             row["relationship"]) for row in rows] == [
        ("MEMORY:0x800b970c", "0x00400008", "code",
         "indirect_transfer_site_not_data_word"),
        ("MEMORY:0x800b970c", "0x00400008", "code",
         "indirect_transfer_site_not_data_word"),
        ("LEVEL05_LEVEL:0x800b4228", "0x006b0008", "data",
         "data_word_not_named_entry"),
        ("LEVEL03_LEVEL:0x800b4b38", "0x0008cd09", "data",
         "data_word_not_named_entry"),
    ]
    assert all(row["word_equals_expected_entry"] is False for row in rows)
    assert all(row["work_order_data_word_label_confirmed"] is False for row in rows)
    assert rows[2]["decoded_as_control_transfer_only_if_code"] is False
    assert rows[3]["decoded_as_control_transfer_only_if_code"] is False


def test_memory_dispatch_local_domain_is_proved_but_not_promoted(receipt: dict) -> None:
    proof = receipt["stage_b_pilot"]["guarded_table_proofs"]
    assert len(proof) == 1
    proof = proof[0]
    assert proof["site"] == "MEMORY:0x800b970c"
    assert proof["status"] == "PROVED_LOCAL_ADDRESS_DOMAIN"
    assert proof["index_interval"] == {"min": 0, "max": 7, "reg": "a0", "stride": 4}
    assert proof["table_extent"] == {
        "lo": "0x800b57b4", "hi": "0x800b57d4", "slot_count": 8,
        "extent_basis": "sltiu guard x four-byte stride",
    }
    assert proof["slot_occurrence_count"] == 8
    assert len(proof["slots"]) == 8
    assert proof["hoisted_load_check"]["load_executes_after_guard"] is True
    assert proof["static_image_slot_values_enumerated"] is True
    assert proof["per_edge_gate_target_set_proved"] is False
    assert proof["whole_region_consumer_universe_proved"] is False
    assert proof["gate_grade_region_closure"] is False


def test_data_decode_inflation_is_retracted_as_exact_sets(receipt: dict) -> None:
    movements = receipt["corrected_indirect_universe_movement"]
    assert [(row["prior_unproved_indirect_count"],
             row["corrected_code_only_unproved_indirect_count"],
             len(row["removed_ids"]), len(row["added_ids"])) for row in movements] == [
        (255, 178, 77, 0),
        (255, 178, 77, 0),
        (258, 178, 80, 0),
        (261, 179, 82, 0),
    ]
    audits = receipt["removed_false_decode_audit"]
    assert [row["removed_false_data_decode_count"] for row in audits] == [77, 77, 80, 82]
    assert all(row["unexpected_non_data_removed_ids"] == [] for row in audits)
    assert all(len(row["removed_false_data_decode_ids"]) ==
               row["removed_false_data_decode_count"] for row in audits)


def test_no_go_and_replacement_argument_are_explicit(receipt: dict) -> None:
    decision = receipt["decision"]
    assert decision["verdict"] == "NO-GO"
    assert decision["closed_root_count"] == 0
    assert decision["closed_root_ids"] == []
    assert decision["open_root_count"] == 4
    assert decision["full_pass_authorized"] is False
    assert "per-site target-domain/exclusion proof" in decision["recommended_replacement_argument"]
    assert "whole-table value-domain invariants" in decision["recommended_replacement_argument"]
    assert receipt["stage_c_not_run"]["caller_domain_frozen_20_rerun"] is False
    assert receipt["stage_c_not_run"]["old_pins_replaced"] == []


def test_f01_and_runtime_surfaces_do_not_move(receipt: dict) -> None:
    protected = receipt["protected_state"]
    assert protected["f01_status"] == "partial"
    assert protected["item_2"] == "not_met"
    assert protected["dimension_promoted"] is False
    assert protected["item2_ready_for_review"] is False
    assert protected["review_blockers"] == [
        "IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"]
    assert protected["mechanics_baseline_modified"] is False
    assert receipt["configuration"]["runtime_replay_performed"] is False
    assert receipt["configuration"]["instrumented_run_performed"] is False
    assert receipt["capsule_crosscheck"]["status"] == "NOT_APPLICABLE_NO_CLOSED_ROOTS"
    assert receipt["capsule_crosscheck"]["clean_for_go"] is False


def test_both_c_sources_rebuild_with_werror(tmp_path: Path) -> None:
    for source in (PRIMARY, INDEPENDENT):
        binary = tmp_path / source.stem
        proc = subprocess.run(
            ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-o", str(binary), str(source)],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        run = subprocess.run(
            [str(binary), "--self-test"], cwd=ROOT, capture_output=True, text=True,
        )
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)["verdict"] is True
