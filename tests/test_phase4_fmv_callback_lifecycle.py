"""Falsification guards for the E15 callback lifecycle control."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_callback_lifecycle as lifecycle  # noqa: E402


def document() -> dict:
    return json.loads(lifecycle.OUTPUT.read_text())


def test_summary_rebuilds_from_three_hash_pinned_external_receipts():
    assert lifecycle.render(lifecycle.build()) == lifecycle.OUTPUT.read_bytes()
    doc = document()
    assert doc["valid"] is True and doc["errors"] == []
    assert len(doc["external_receipts"]) == 3
    assert all(row["media_class"].endswith("never commit")
               for row in doc["external_receipts"])
    assert doc["raw_external_bytes_committed"] is False


def test_common_exit_is_start_positive_only_and_exactly_ordered():
    observed = document()["observations"]
    assert observed["shared_initialization"] == {
        "present_in_both_controls": True,
        "function": "StClearRing",
        "address": "0x8007094c",
        "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4",
        "emulator_frame": 4443,
        "entry_cycle": 2515397349,
        "exit_cycle": 2515399779,
    }
    common_exit = observed["positive_common_exit"]
    assert common_exit["negative_control_absent"] is True
    assert common_exit["emulator_frame"] == 4671
    assert common_exit["st_clear_ring"] == {
        "caller": "0x800b749c", "return_address": "0x800b74a4",
        "entry_cycle": 2644271877, "exit_cycle": 2644274307,
    }
    assert common_exit["callback_teardown"] == {
        "address": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac", "entry_cycle": 2644274321,
        "exit_cycle": 2644284120, "exit_is_synthetic_unwind": True,
        "exit_v0": "0x00000001",
    }
    assert common_exit["entry_gap_after_st_clear_ring_exit_cycles"] == 14


def test_movie_end_residency_and_fixed_words_keep_residuals_explicit():
    observed = document()["observations"]
    assert observed["movie_end_residency_control"] == {
        "positive_fmv_bin_resident": False,
        "negative_fmv_bin_resident": True,
        "negative_fmv_head_sha256":
            "ab33c20549aa18877259dbd83cc4925c9ea24db0e160b3f450eaad29551954db",
    }
    assert observed["fixed_callback_words"] == {
        "positive": "0018801f0118801f0218801f0318801f",
        "negative": "0018801f0118801f0218801f0318801f",
        "equal_after_capture": True,
    }
    assert len(document()["falsified_hypotheses"]) == 3
    assert len(document()["residuals"]) == 4
    assert "synthetic unwind" in document()["residuals"][0]


def test_schema_and_registry_bank_the_fact_without_promoting_lifecycle():
    schema = yaml.safe_load(
        (ROOT / "config/phase4_fmv_callback_lifecycle.yaml").read_text())
    assert schema["schema"] == "abl-phase4-fmv-callback-lifecycle-source/1"
    assert schema["external_receipts"][-1]["frames"] == 541
    assert schema["expected_callback_words_hex"] == \
        "0018801f0118801f0218801f0318801f"
    registry = yaml.safe_load((ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    assert campaign["dimension_claims"].get("lifecycle") is None
    assert campaign["dimension_claims"]["original_interfaces"]["claim"] == "partial"
    assert campaign.get("next_lane_override") is None
    assert sum(
        row["artifact"] == "analysis/phase4_fmv_callback_lifecycle.json"
        for rows in campaign["evidence"].values() for row in rows) == 8


def test_receipt_guard_rejects_function_caller_drift():
    spec = lifecycle.CONFIGURATION["external_receipts"][-1]
    path = lifecycle.EXTERNAL_ROOT / spec["relative_path"]
    mutated = json.loads(path.read_text())
    mutated["result"]["jobs"][0]["result"]["capture"]["traces"]["functions"][4][
        "caller"] = "0x80000000"
    with pytest.raises(ValueError, match="function caller/order/cycle drifted"):
        lifecycle.validate_receipt(mutated, spec, verify_identity=False)


def test_receipt_guard_rejects_false_negative_control_teardown():
    spec = lifecycle.CONFIGURATION["external_receipts"][-1]
    path = lifecycle.EXTERNAL_ROOT / spec["relative_path"]
    mutated = json.loads(path.read_text())
    negative = mutated["result"]["jobs"][1]["result"]["capture"]["traces"]["functions"]
    negative.extend(deepcopy(lifecycle.PLAYER_EXIT_EVENTS[2:]))
    with pytest.raises(ValueError, match="function event count drifted"):
        lifecycle.validate_receipt(mutated, spec, verify_identity=False)


def test_receipt_guard_rejects_media_and_residency_drift():
    spec = lifecycle.CONFIGURATION["external_receipts"][-1]
    path = lifecycle.EXTERNAL_ROOT / spec["relative_path"]
    mutated = json.loads(path.read_text())
    mutated["result"]["jobs"][0]["result"]["media"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="post-load media proof drifted"):
        lifecycle.validate_receipt(mutated, spec, verify_identity=False)
    mutated = json.loads(path.read_text())
    mutated["result"]["jobs"][1]["result"]["capture"]["memory"][5]["hex"] = "00" * 256
    with pytest.raises(ValueError, match="FMV.BIN residency drifted"):
        lifecycle.validate_receipt(mutated, spec, verify_identity=False)


def test_batch_plan_guard_rejects_lifecycle_bound_drift(monkeypatch):
    plan = lifecycle.yaml.safe_load(lifecycle.BATCH_PLAN.read_text())
    plan["jobs"][0]["run"]["frames"] = 540
    monkeypatch.setattr(
        lifecycle.yaml, "safe_load",
        lambda _text: plan,
    )
    with pytest.raises(ValueError, match="canonical hash drifted"):
        lifecycle.validate_plan()
