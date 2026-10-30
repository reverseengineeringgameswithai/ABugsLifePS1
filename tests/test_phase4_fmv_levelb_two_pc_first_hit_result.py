from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_two_pc_first_hit_result as result  # noqa: E402


def test_bounded_two_pc_falsifier_is_banked_without_branch_or_dimension():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "falsified"
    assert document["observation"]["passive_repeat_equal"] is True
    assert document["observation"]["candidate_pc_hits"] == 0
    assert document["record_counts"]["investigator_live_receipts"] == 2
    assert document["record_counts"]["direct_command_events"] == 74
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "static"
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_native_failure_retains_finite_bound_and_owned_cleanup():
    native = result.build()["receipts"][1]
    assert native["anchor_frame"] == 15792
    assert native["frame_ceiling"] == 15856
    assert native["failure_frame"] == 15857
    assert native["candidate_hits"] == 0
    assert native["owned_breakpoints_removed"] == 2
    assert native["remaining_breakpoints"] == 0


def test_falsifier_reason_mutation_is_rejected():
    original = result.CONFIGURATION["expected"]
    result.CONFIGURATION["expected"] = {
        **original,
        "falsifier_reason": "accept an escaped first-hit window",
    }
    try:
        with pytest.raises(ValueError, match="falsifier payload"):
            result.build()
    finally:
        result.CONFIGURATION["expected"] = original


def test_receipt_evidence_hash_mutation_is_rejected(monkeypatch):
    original = result.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "receipt.json" and "first-hit-native" in str(path):
            document = copy.deepcopy(document)
            document["evidence"]["command_events"]["sha256"] = "0" * 64
        return document

    monkeypatch.setattr(result.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="command_events evidence"):
        result.build()
