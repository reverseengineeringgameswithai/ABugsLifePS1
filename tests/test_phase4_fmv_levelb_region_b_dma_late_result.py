from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_levelb_region_b_dma_late_result as result  # noqa: E402


def _passive_batch() -> dict:
    spec = result.CONFIGURATION["passive"]["batch_result"]
    return json.loads((result.RUN_ROOT / spec["relative_path"]).read_text())


def test_staged_passive_is_banked_without_a_dma_or_dimension_claim():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "not_evaluated"
    assert document["falsifier"]["method_outcome"] == "rejected"
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
        "d1c901b7c9aebcf9141088332cf4d625f5101d10c10410c50d65d7f14ccce833"
    )
    assert document["receipts"][0]["batch_result_sha256"] == (
        "ee8b36d851409dfa4dcdc8c6ab3fd1c7912c874d49f18b19e4c76466912cf414"
    )
    boundary = document["claim_boundary"]
    assert boundary["passive_control_closed"] is True
    assert boundary["precise_dma_claim_admitted"] is False
    assert boundary["first_region_b_dma_identified"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "static"
    assert document["record_counts"]["investigator_live_receipts"] == 1
    assert document["record_counts"]["offline_queries"] == 0
    assert document["record_counts"]["offline_queries_reused"] == 1
    assert document["record_counts"]["precise_live_receipts"] == 0
    assert document["record_counts"]["promotion_admissible_live_receipts"] == 0
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_staged_same_anchor_jobs_have_identical_endpoints():
    jobs = _passive_batch()["result"]["jobs"]
    assert (
        jobs[0]["result"]["staged_prelude"]
        == jobs[1]["result"]["staged_prelude"]
    )
    assert (
        jobs[0]["result"]["run"]["status"]
        == jobs[1]["result"]["run"]["status"]
    )
    assert jobs[0]["result"]["capture"] == jobs[1]["result"]["capture"]
    endpoint = result._validate_passive()["endpoint"]
    assert endpoint["staged_start_frame"] == 1
    assert endpoint["staged_stop_frame"] == 15720
    assert endpoint["staged_frames_advanced"] == 15719
    assert endpoint["frame"] == 16120
    assert endpoint["cycle"] == 9126623583
    assert endpoint["pc"] == "0x8004fea4"
    assert endpoint["sp"] == "0x801fffd0"


def test_staged_counter_mutation_is_rejected():
    original = result.CONFIGURATION["expected_endpoint"]
    result.CONFIGURATION["expected_endpoint"] = {
        **original,
        "staged_frames_advanced": original["staged_frames_advanced"] - 1,
    }
    try:
        with pytest.raises(ValueError, match="staged atomic jobs"):
            result._validate_passive()
    finally:
        result.CONFIGURATION["expected_endpoint"] = original


def test_precise_receipt_presence_would_reject_nonpromotion(monkeypatch):
    spec = result.CONFIGURATION["precise_rejection"]
    receipt_path = result.RUN_ROOT / spec["receipt_relative_path"]
    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if path == receipt_path:
            return True
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fake_exists)
    with pytest.raises(ValueError, match="gained evidence"):
        result._validate_precise_rejection()


def test_static_destination_mutation_is_rejected(monkeypatch):
    original = result.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "phase4_fmv_region_b_replacement_ownership.json":
            document = copy.deepcopy(document)
            document["completed_level_b_replacement_policy"][
                "common_resource_policy"
            ]["destination"] = "0x800B578C"
        return document

    monkeypatch.setattr(result.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="static replacement request"):
        result._validate_static_source()


def test_work_packet_falsifier_mutation_is_rejected(monkeypatch):
    original = result.common.load_json

    def changed_load(path: Path):
        document = original(path)
        if path.name == "iteration-1-work-packet.json":
            document = copy.deepcopy(document)
            document["falsifier"] = "accept every transfer page"
        return document

    monkeypatch.setattr(result.common, "load_json", changed_load)
    with pytest.raises(ValueError, match="work packet"):
        result._validate_authorization()
