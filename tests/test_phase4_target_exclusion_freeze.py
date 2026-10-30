"""Contracts for the mandatory target-exclusion Stage-0/1 freeze."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_target_exclusion_freeze.json"
DRIVER = ROOT / "tools/phase4_target_exclusion_freeze.py"
STAGE1_C = ROOT / "tools/phase4_target_exclusion_stage1.c"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"

EXPECTED_PILOT = [
    "SCUS_942_88:0x80011128:jr:ra",
    "SCUS_942_88:0x800163d8:jr:ra",
    "SCUS_942_88:0x800172d4:jr:ra",
    "SCUS_942_88:0x8001897c:jr:ra",
    "SCUS_942_88:0x80018a4c:jr:s6",
    "SCUS_942_88:0x80018b1c:jr:s6",
    "SCUS_942_88:0x80018bec:jr:s6",
    "SCUS_942_88:0x80018cbc:jr:s6",
    "SCUS_942_88:0x80018f44:jr:ra",
    "SCUS_942_88:0x8001923c:jr:ra",
    "SCUS_942_88:0x80019614:jr:ra",
    "SCUS_942_88:0x80019b3c:jr:ra",
]


@pytest.fixture(scope="module")
def freeze() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_artifact_is_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(DRIVER), "--check"], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_exact_union_and_masking_sets(freeze: dict) -> None:
    stage0 = freeze["stage_0_union"]
    movement = stage0["movement"]
    assert stage0["image_counts"] == {
        "LEVEL07_LEVEL1": 1, "MEMORY": 12, "SCUS_942_88": 166}
    assert movement["pre_mask_union_count"] == 261
    assert movement["corrected_union_count"] == 179
    assert len(movement["corrected_sites_in"]) == 179
    assert len(set(movement["corrected_sites_in"])) == 179
    assert movement["masked_out_count"] == 82
    assert len(movement["masked_sites_out"]) == 82
    assert movement["unexpected_added_ids"] == []
    assert all(row["reason"] == "pinned_data_record_false_decode"
               for row in movement["masked_sites_out"])
    assert all({region["type"] for region in row["containing_ranges"]} == {"data"}
               for row in movement["masked_sites_out"])
    assert [(row["before_count"], row["after_count"],
             len(row["removed_ids"]), len(row["added_ids"]))
            for row in movement["per_root_supersets"]] == [
                (255, 178, 77, 0),
                (255, 178, 77, 0),
                (258, 178, 80, 0),
                (261, 179, 82, 0),
            ]


def test_stage1_is_total_and_fail_closed(freeze: dict) -> None:
    stage1 = freeze["stage_1_classification"]
    assert stage1["universe_count"] == 179
    assert stage1["histogram"] == {
        "table_backed": 74,
        "computed": 19,
        "register_provenance": 6,
        "return_like": 0,
        "return_like_unproved_incoming_ra": 9,
        "unclassified_opaque_definition": 38,
        "mixed_reaching_definitions": 33,
    }
    assert sum(stage1["histogram"].values()) == 179
    assert len(stage1["sites"]) == 179
    assert {row["id"] for row in stage1["sites"]} == set(
        freeze["stage_0_union"]["movement"]["corrected_sites_in"])
    for row in stage1["sites"]:
        instruction = row["instruction_evidence"]
        reaching = row["reaching_definition_evidence"]
        assert instruction["id"] == row["id"]
        assert instruction["decoded_kind"] == row["kind"]
        assert instruction["decoded_register"] == row["register"]
        assert instruction["delay_slot_pc"].startswith("0x")
        assert instruction["delay_slot_word"].startswith("0x")
        assert reaching["targeted_sites"] == 1
        assert reaching["register"] == row["register"]
        assert row["owner"]["range_type"] in {"code", "thunk"}
    table_rows = [row for row in stage1["sites"] if row["stratum"] == "table_backed"]
    assert len(table_rows) == 74
    assert all(row["classification_evidence"][
        "candidate_only_not_a_stage2_invariant"] is True for row in table_rows)


def test_protected_set_is_exact(freeze: dict) -> None:
    protected = freeze["protected_set"]
    assert protected["known_writer_count"] == 58
    assert len(protected["known_writer_ids"]) == 58
    assert len(set(protected["known_writer_ids"])) == 58
    assert protected["window_site_count"] == 124
    assert len(protected["window_site_ids"]) == 124
    assert set(protected["known_writer_ids"]) <= set(protected["window_site_ids"])
    assert protected["closure_root_count"] == 4
    assert protected["combined_unique_image_pc_count"] == 128


def test_pilot_was_selected_and_logged_before_outcomes(freeze: dict) -> None:
    selection = freeze["pilot_selection"]
    assert selection["selection_is_pre_outcome"] is True
    assert selection["root_candidate_count"] == 179
    assert selection["writer_cone"]["candidate_count"] == 0
    assert selection["candidate_union_count"] == 179
    assert selection["truncation_limit"] == 12
    assert selection["truncated_count"] == 167
    assert selection["pilot_ids"] == EXPECTED_PILOT
    assert [row["rank"] for row in selection["pilot"]] == list(range(1, 13))
    text = EXPERIMENT.read_text()
    marker = "target-exclusion pilot frozen (PRE-OUTCOME record)"
    assert marker in text
    section = text.split(marker, 1)[1].split("\n## ", 1)[0]
    positions = [section.index(f"`{site}`") for site in EXPECTED_PILOT]
    assert positions == sorted(positions)
    assert "No Stage-2 target-domain proof" in section
    assert "No exclusion/disjointness outcome" in section
    assert "No GO/NO-GO decision" in section


def test_outcome_and_protected_state_do_not_move(freeze: dict) -> None:
    barrier = freeze["outcome_barrier"]
    assert set(barrier.values()) == {False}
    protected = freeze["protected_state"]
    assert protected == {
        "f01_status": "partial",
        "item_2": "not_met",
        "dimension_promoted": False,
        "item2_ready_for_review": False,
        "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
        "mechanics_baseline_modified": False,
        "runtime_replay_performed": False,
        "instrumented_run_performed": False,
    }


def test_stage1_c_rebuilds_with_werror(tmp_path: Path) -> None:
    binary = tmp_path / "stage1"
    proc = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(binary), str(STAGE1_C)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    run = subprocess.run(
        [str(binary), "--self-test"], cwd=ROOT, capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == {
        "tool": "phase4_target_exclusion_stage1",
        "passed": 6, "total": 6, "verdict": True,
    }
