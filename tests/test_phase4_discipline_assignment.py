"""Contracts for the Phase-4 discipline assignment and pre-outcome pilot freeze."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "analysis/phase4_discipline_assignment.json"
DRIVER = ROOT / "tools/phase4_discipline_assignment.py"
C_SOURCE = ROOT / "tools/phase4_discipline_assignment.c"


@pytest.fixture(scope="module")
def assignment() -> dict:
    return json.loads(ARTIFACT.read_text())


def test_artifact_is_byte_current() -> None:
    proc = subprocess.run(
        ["python3", str(DRIVER), "--check"], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_assignment_tiles_the_frozen_universe_exactly(assignment: dict) -> None:
    universe = assignment["universe"]
    by_discipline = assignment["assignments"]["by_discipline"]
    sets = [set(by_discipline[name]) for name in (
        "D1_return", "D2_switch_computed", "D3_pointer_dispatch")]
    assert universe["count"] == universe["assignment_count"] == 179
    assert len(universe["site_ids"]) == len(set(universe["site_ids"])) == 179
    assert universe["exact_both_directions"] is True
    assert universe["unassigned_residual_count"] == 0
    assert universe["unassigned_residual_site_ids"] == []
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    assert set().union(*sets) == set(universe["site_ids"])
    assert assignment["assignments"]["counts"] == {
        "D1_return": 19, "D2_switch_computed": 20,
        "D3_pointer_dispatch": 140,
    }


def test_every_assignment_cites_instruction_bytes_and_owner(assignment: dict) -> None:
    sites = assignment["assignments"]["sites"]
    assert len(sites) == 179
    for row in sites:
        assert row["word"].startswith("0x")
        assert row["delay_slot_word"].startswith("0x")
        assert row["decoded_kind"] in {"jr", "jalr"}
        assert row["decoded_register"] == row["id"].split(":")[3]
        assert row["owner"]["range_type"] in {"code", "thunk"}
        if row["discipline"] == "D1_return":
            assert (row["decoded_kind"], row["decoded_register"]) == ("jr", "ra")
        elif row["discipline"] == "D2_switch_computed":
            assert row["decoded_kind"] == "jr" and row["decoded_register"] != "ra"
        else:
            assert row["discipline"] == "D3_pointer_dispatch"
            assert row["decoded_kind"] == "jalr" and row["link_register"] == "ra"
    assert assignment["owner_functions"]["count"] == 110
    assert len(assignment["owner_functions"]["owners"]) == 110


def test_pilot_is_mechanical_and_frozen_before_outcomes(assignment: dict) -> None:
    pilot = assignment["pilot_selection"]
    assert pilot["frozen_before_outcomes"] is True
    assert pilot["total_count"] == len(pilot["site_ids"]) == 39
    assert len(set(pilot["site_ids"])) == 39
    assert pilot["D1"]["count"] == 19
    assert pilot["D2"]["count"] == 8
    assert pilot["D3"]["table_backed_count"] == 8
    assert pilot["D3"]["next_count"] == 4
    assert pilot["D3"]["direct_phase3_jr_table_match_count"] == 0
    assert pilot["D3"]["direct_phase3_jr_table_match_site_ids"] == []
    assert pilot["site_ids"] == (
        pilot["D1"]["site_ids"] + pilot["D2"]["site_ids"]
        + pilot["D3"]["table_backed_site_ids"] + pilot["D3"]["next_site_ids"])
    assert set(assignment["outcome_barrier"].values()) == {False}


def test_runtime_crosscheck_reports_disagreements_without_promoting_them(
        assignment: dict) -> None:
    runtime = assignment["runtime_crosscheck"]
    assert runtime["authority"].startswith("runtime evidence only")
    assert (runtime["observed_site_count"], runtime["silent_site_count"]) == (79, 100)
    assert [(runtime["coverage"][name]["observed"],
             runtime["coverage"][name]["silent"])
            for name in ("D1_return", "D2_switch_computed", "D3_pointer_dispatch")] == [
                (15, 4), (15, 5), (49, 91)]
    disagreements = runtime["disagreements"]
    assert len(disagreements["D1_strict_return_discipline"]) == 7
    assert len(disagreements["D2_static_switch_locality"]) == 6
    assert disagreements["prior_entry_scoped_domain_falsification"] == [[
        "SCUS_942_88:0x80018cbc:jr:s6", "0x8001961c"]]
    assert runtime["overlay_caveat"]["trusted_for_assignment_crosscheck"] is False
    assert runtime["dynamic_loader_contract_residual"]["status"] == "NAMED_NOT_PROVED"


def test_protected_state_did_not_move(assignment: dict) -> None:
    assert assignment["protected_state"] == {
        "f01_status": "partial", "item_2": "not_met",
        "item2_ready_for_review": False,
        "review_blockers": ["IMAGE_CENSUS_INCOMPLETE", "MECHANICALLY_INCOMPLETE"],
        "runtime_replay_performed": False, "instrumented_run_performed": False,
    }


def test_c_probe_rebuilds_and_selftests_with_werror(tmp_path: Path) -> None:
    binary = tmp_path / "assignment"
    proc = subprocess.run(
        ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
         "-o", str(binary), str(C_SOURCE)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    run = subprocess.run(
        [str(binary), "--self-test"], cwd=ROOT,
        capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(run.stdout) == {
        "tool": "phase4_discipline_assignment",
        "passed": 4, "total": 4, "verdict": True,
    }
