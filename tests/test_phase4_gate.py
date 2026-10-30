"""Falsification tests for the low-level Phase-4 whole-phase gate."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_common as common  # noqa: E402
import phase4_coverage  # noqa: E402
import phase4_gate  # noqa: E402


def test_removing_or_duplicating_a_low_level_row_owner_turns_registry_red():
    registry = common.load_yaml(common.REGISTRY_PATH)
    removed = copy.deepcopy(registry)
    removed["families"][0]["primary_rows"].remove("A01_move_run")
    gaps = common.validate_registry(removed)
    assert any("A01_move_run" in gap and "without a primary family" in gap for gap in gaps)

    duplicated = copy.deepcopy(registry)
    duplicated["families"][1]["primary_rows"].append("A01_move_run")
    gaps = common.validate_registry(duplicated)
    assert any("A01_move_run" in gap and "duplicated primary ownership" in gap
               for gap in gaps)


def test_self_certified_completed_campaign_does_not_cover_a_row():
    registry = common.load_yaml(common.REGISTRY_PATH)
    mutated = copy.deepcopy(registry)
    mutated["child_campaigns"].append({
        "id": "self_certified",
        "family": "input_player_actions",
        "rows": ["A09_seed_pickup_drop"],
        "status": "completed",
        "passes": True,
        "complete": True,
        "gate_met": True,
    })
    coverage = phase4_coverage.build(registry=mutated)
    audit = coverage["campaign_audits"]["self_certified"]
    assert audit["completed_from_low_level_evidence"] is False
    assert audit["gaps"]
    assert coverage["rows"]["A09_seed_pickup_drop"]["state"] == "open"
    assert coverage["counts"]["complete_total"] == 16


def test_assertions_cannot_read_a_high_level_gate_flag():
    artifact = ROOT / "analysis/phase3_gate_audit.json"
    gaps = common.audit_assertion({
        "artifact": "analysis/phase3_gate_audit.json",
        "sha256": common.sha256(artifact),
        "json_path": "gate_met",
        "op": "eq",
        "expected": True,
    })
    assert any("self-certifying" in gap for gap in gaps)


def test_exact_phase4_gate_recomputes_all_four_predicates_open():
    gate = phase4_gate.build()
    assert gate["gate_met"] is False
    assert gate["coverage_counts"]["baseline_rows"] == 107
    assert gate["coverage_counts"]["complete_total"] == 16
    assert gate["coverage_counts"]["campaign_complete"] == 15
    assert gate["coverage_counts"]["reviewed_absent"] == 1
    assert gate["coverage_counts"]["open"] == 91
    assert all(row["met"] is False for row in gate["predicates"].values())
    assert gate["prerequisites"]["inventory_structural"] is True
    assert gate["prerequisites"]["retained_artifacts_fresh"] is True
    assert gate["prerequisites"]["phase3_confidence_handoff_preserved"] is True
    assert gate["prerequisites"]["pristine_build_identity"] is True


def test_retained_non_gate_artifacts_match_semantic_recomputation():
    gate = phase4_gate.build()
    assert all(gate["freshness"].values()), gate["freshness"]


def test_gate_was_banked_from_a_clean_tracked_input_state():
    gate = phase4_gate.build()
    inventory = gate["phase3_recomputed"]["inventory"]
    assert inventory["summary"]["tracked_input_mutations"] == []
    assert inventory["retained_artifact_fresh"] is True


def test_gate_preserves_retained_generated_date_across_calendar_days(
        monkeypatch, tmp_path):
    retained = tmp_path / "phase4_gate.json"
    retained.write_text('{"generated":"2001-02-03"}\n')
    monkeypatch.setattr(phase4_gate, "OUTPUT", retained)
    assert phase4_gate.stable_generated() == "2001-02-03"
    assert phase4_gate.build()["generated"] == "2001-02-03"
