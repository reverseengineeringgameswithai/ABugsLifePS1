"""Contracts for the frozen Phase-4 discipline-proof pilot negative."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_discipline_pilot.json"
DRIVER = ROOT / "tools/phase4_discipline_pilot.py"
EXPERIMENT = ROOT / "ObsidianVault/Experiments/EXP_2026-08-05_phase4_f01_objective_lifecycle.md"


@pytest.fixture(scope="module")
def pilot() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_artifact_is_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(DRIVER), "--check"], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_per_site_outcomes_tile_only_the_frozen_sample(pilot: dict) -> None:
    universe = pilot["universes"]["frozen_indirect_site_universe"]
    sample = pilot["universes"]["pilot"]
    rows = pilot["per_site_outcomes"]
    assert universe["count"] == len(universe["site_ids"]) == 179
    assert sample["count"] == len(sample["site_ids"]) == len(rows) == 39
    assert sample["sample_is_not_universe"] is True
    assert sample["frozen_before_outcomes"] is True
    assert [row["site"] for row in rows] == sample["site_ids"]
    assert len({row["site"] for row in rows}) == 39
    assert all(row["outcome"] == "NAMED_WALL" for row in rows)
    assert all(row["gate_grade_proved"] is False for row in rows)
    assert all(row["proof_kind"] is None for row in rows)
    assert all(row["site_instruction"]["word"].startswith("0x") for row in rows)


def test_counts_and_wall_shapes_are_hard_failures(pilot: dict) -> None:
    assert pilot["counts"] == {
        "D1_return": {"sampled": 19, "proved": 0, "named_walls": 19},
        "D2_switch_computed": {"sampled": 8, "proved": 0, "named_walls": 8},
        "D3_pointer_dispatch": {"sampled": 12, "proved": 0, "named_walls": 12},
    }
    assert pilot["wall_tallies"]["D1_return"]["by_shape"] == {
        "structure-shaped": 17, "technique-shaped": 2}
    assert pilot["wall_tallies"]["D2_switch_computed"]["by_shape"] == {
        "structure-shaped": 8}
    assert pilot["wall_tallies"]["D3_pointer_dispatch"]["by_shape"] == {
        "technique-shaped": 12}


def test_entry_scoped_candidate_is_not_promoted_and_runtime_falsifies_one(
        pilot: dict) -> None:
    candidates = pilot["entry_scoped_candidate_facts_not_proofs"]
    assert len(candidates) == 5
    assert all(row["primary_and_independent_crosscheck_agree"] for row in candidates)
    assert all(row["accepted_as_discipline_proof"] is False for row in candidates)
    violations = pilot["runtime_crosscheck"]["candidate_violations"]
    assert violations == [{
        "site": "SCUS_942_88:0x80018cbc:jr:s6",
        "candidate_targets": ["0x80018cc4", "0x80018f4c", "0x80019244"],
        "observed_targets_outside_candidate": ["0x8001961c"],
        "finding": "runtime falsifies promotion of the entry-scoped C result",
    }]
    assert pilot["runtime_crosscheck"]["landed_proof_result"] == (
        "NOT_ESTABLISHED_EMPTY_PROOF_SET")
    assert pilot["independent_crosscheck"]["called_clean"] is False


def test_D3_writer_universe_and_protected_set_stay_open(pilot: dict) -> None:
    scan = pilot["D3_shared_cell_writer_probe"]
    assert scan["image_count"] == len(scan["per_image"]) == 21
    assert scan["unresolved_write_count"] == 4266
    assert scan["full_width_unresolved_write_count"] == 2244
    assert scan["writer_universe_closed"] is False
    assert all(row["truncated"] is False for row in scan["per_image"])
    protected = pilot["universes"]["protected_set"]
    assert protected["known_writer_count"] == 58
    assert protected["window_site_count"] == 124
    assert protected["closure_root_count"] == 4
    assert protected["combined_unique_image_pc_count"] == len(
        protected["combined_ids"]) == 128
    assert pilot["corpus_undecided_stores"] == {
        "general_F01_typed_state_table_0x80090748": 5012,
        "D3_shared_dispatch_cell_0x8007fbc4": 4266,
        "D3_shared_dispatch_cell_full_width": 2244,
        "counts_are_for_distinct_questions": True,
    }


def test_decision_is_no_go_and_f01_does_not_move(pilot: dict) -> None:
    decision = pilot["decision"]
    assert decision["verdict"] == "NO-GO"
    assert decision["explicit_sentence"].startswith("NO-GO:")
    assert all(not row["satisfied"] for row in decision["conditions"].values())
    assert decision["full_pass_authorized"] is False
    assert decision["stage_2_consumption_performed"] is False
    assert pilot["residual"] == {
        "before": 179, "after": 179, "proved_site_delta": 0,
        "scale_changed": False,
        "operator_item2_bar_effect": (
            "none: the result does not reduce the 179-site indirect-control-flow residual"),
    }
    assert pilot["protected_state"] == {
        "f01_status": "partial", "item_2": "not_met",
        "item2_ready_for_review": False,
        "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
        "gate_or_closure_mutated": False, "full_chain_regenerated": False,
        "runtime_replay_performed": False, "instrumented_run_performed": False,
    }


def test_owner_subsystem_progress_is_exact_but_transfer_is_caveated(pilot: dict) -> None:
    progress = pilot["owner_subsystem_progress"]
    assert sum(progress["universe_buckets_from_corrected_work_order"].values()) == 179
    assert {row["subsystem"]: row["sampled"] for row in progress["pilot"]} == {
        "E01/E03/E11 render + geometry": 34,
        "E07/E08 props, movers, event VM": 1,
        "E16 streaming, loaders, overlays": 1,
        "unnamed / other": 3,
    }
    assert all(row["proved"] == 0 for row in progress["pilot"])
    assert "hypothesis" in progress["transfer_caveat"]


def test_experiment_records_table_before_explicit_decision(pilot: dict) -> None:
    text = EXPERIMENT.read_text()
    marker = "discipline-proof pilot outcome (reviewed negative)"
    assert marker in text
    section = text.split(marker, 1)[1]
    table = section.find("| # | discipline | site | outcome |")
    decision = section.find(pilot["decision"]["explicit_sentence"])
    assert 0 <= table < decision
    for site_id in pilot["universes"]["pilot"]["site_ids"]:
        assert f"`{site_id}`" in section[:decision]
