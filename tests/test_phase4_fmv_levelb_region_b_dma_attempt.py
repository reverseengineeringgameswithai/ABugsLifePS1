from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_attempt as attempt  # noqa: E402


def _passive_batch() -> dict:
    spec = attempt.CONFIGURATION["passive"]["batch_result"]
    return json.loads(
        (attempt.RUN_ROOT / spec["relative_path"]).read_text()
    )


def test_passive_receipt_is_banked_without_a_dma_or_dimension_claim():
    document = attempt.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "not_evaluated"
    assert document["falsifier"]["reasons"] == [
        "precise_receipt_absent",
        "transfer_pagination_rejected_before_receipt",
    ]
    evidence = document["falsifier"]["evidence"]
    assert evidence["passive_repeat_equal"] is True
    assert evidence["passive_receipt_closed"] is True
    assert evidence["precise_receipt_closed"] is False
    assert evidence["precise_dma_events_admitted"] == 0
    assert document["receipts"][0]["receipt_sha256"] == (
        "abe75bc65b419092c4858efbc3afc18d54c045ec92271f7c008a1024f96fcbe2"
    )
    assert document["receipts"][0]["batch_result_sha256"] == (
        "15d5d47e05e0afc11cb52aa96ed65349d31088583f50faf965e768e1a317c03d"
    )
    boundary = document["claim_boundary"]
    assert boundary["passive_control_closed"] is True
    assert boundary["precise_dma_claim_admitted"] is False
    assert boundary["first_region_b_dma_identified"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "live_method"
    assert document["record_counts"]["investigator_live_receipts"] == 1
    assert document["record_counts"]["precise_live_receipts"] == 0
    assert document["record_counts"]["promotion_admissible_live_receipts"] == 0
    assert attempt.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_passive_same_anchor_jobs_have_identical_endpoints():
    jobs = _passive_batch()["result"]["jobs"]
    assert jobs[0]["result"]["run"]["status"] == jobs[1]["result"]["run"]["status"]
    assert jobs[0]["result"]["capture"] == jobs[1]["result"]["capture"]
    endpoint = attempt._validate_passive()["endpoint"]
    assert endpoint["frame"] == 16120
    assert endpoint["cycle"] == 9126623583
    assert endpoint["pc"] == "0x8004fea4"
    assert endpoint["movie_frame_count"] == 15230


def test_endpoint_mutation_is_rejected():
    batch = _passive_batch()
    changed = copy.deepcopy(batch["result"]["jobs"][0]["result"]["capture"])
    changed["frame"] -= 1
    expected = attempt.CONFIGURATION["expected_endpoint"]
    assert changed["frame"] != expected["frame"]
    with pytest.raises(ValueError, match="passive endpoint contract drifted"):
        original = attempt.CONFIGURATION["expected_endpoint"]
        attempt.CONFIGURATION["expected_endpoint"] = {
            **original,
            "frame": original["frame"] - 1,
        }
        try:
            attempt._validate_passive()
        finally:
            attempt.CONFIGURATION["expected_endpoint"] = original


def test_precise_receipt_presence_would_reject_nonpromotion(monkeypatch):
    spec = attempt.CONFIGURATION["precise_rejection"]
    receipt_path = attempt.RUN_ROOT / spec["receipt_relative_path"]
    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if path == receipt_path:
            return True
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fake_exists)
    with pytest.raises(ValueError, match="gained evidence"):
        attempt._validate_precise_rejection()


def test_static_destination_mutation_is_rejected(monkeypatch):
    original = attempt.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_region_b_replacement_ownership.json":
            document = copy.deepcopy(document)
            document["completed_level_b_replacement_policy"][
                "common_resource_policy"
            ]["destination"] = "0x800B578C"
        return document

    monkeypatch.setattr(attempt.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="static replacement request"):
        attempt._validate_static_source()
