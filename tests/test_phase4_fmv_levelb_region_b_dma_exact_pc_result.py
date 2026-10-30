from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_exact_pc_result as result  # noqa: E402


def test_repeated_exact_pc_falsifier_is_banked_without_dma_claim():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "falsified_repeated"
    assert document["observation"]["exact_pc_repeat_equal"] is True
    assert document["observation"]["dma_events_claimed"] == 0
    assert document["record_counts"]["investigator_live_receipts"] == 3
    boundary = document["claim_boundary"]
    assert boundary["fresh_verifier_pending"] is True
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "static"
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_precise_runs_are_independent_and_repeat_the_bounded_failure():
    rows = result.build()["receipts"]
    native, repeat = rows[1:]
    assert native["server_session_id"] != repeat["server_session_id"]
    assert native["anchor_frame"] == repeat["anchor_frame"] == 15816
    assert native["failure_frame"] == repeat["failure_frame"] == 15881
    assert native["frame_ceiling"] == repeat["frame_ceiling"] == 15880
    assert native["transfer_events"] == repeat["transfer_events"] == 0
    assert native["terminal_method"] == repeat["terminal_method"] == "debugger.pause"


def test_falsifier_reason_mutation_is_rejected():
    original = result.CONFIGURATION["expected"]
    result.CONFIGURATION["expected"] = {
        **original,
        "falsifier_reason": "accept an escaped frame",
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
        if path.name == "receipt.json" and "exact-pc-native" in str(path):
            document = copy.deepcopy(document)
            document["evidence"]["command_events"]["sha256"] = "0" * 64
        return document

    monkeypatch.setattr(result.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="command_events evidence"):
        result.build()
