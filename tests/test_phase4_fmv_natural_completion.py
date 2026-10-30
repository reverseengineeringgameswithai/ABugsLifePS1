"""Falsification guards for the E15 natural level-A completion control."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_natural_completion as natural  # noqa: E402


def document() -> dict:
    return json.loads(natural.OUTPUT.read_text())


def test_summary_rebuilds_from_hash_pinned_result_and_cleanup_receipts():
    assert natural.render(natural.build()) == natural.OUTPUT.read_bytes()
    doc = document()
    assert doc["valid"] is True and doc["errors"] == []
    assert doc["record_counts"] == {
        "atomic_batches": 1, "jobs": 2, "function_events": 12}
    assert len(doc["external_receipts"]) == 2
    assert {row["role"] for row in doc["external_receipts"]} == {
        "atomic_batch_result", "owned_pid_cleanup"}
    assert all(row["media_class"].endswith("never commit")
               for row in doc["external_receipts"])
    assert doc["raw_external_bytes_committed"] is False


def test_natural_completion_reaches_same_interface_later_and_returns_normally():
    observed = document()["observations"]
    common = observed["common_interface"]
    assert common == {
        "same_static_callers_and_returns": True,
        "start_exit_frame": 4671,
        "natural_exit_frame": 5305,
        "natural_after_start_frames": 634,
        "natural_after_prior_boundary_frames": 529,
        "start_teardown_synthetic_unwind": True,
        "natural_teardown_synthetic_unwind": False,
    }
    natural_exit = observed["natural_completion"]["common_exit"]
    assert natural_exit["st_clear_ring"] == {
        "address": "0x8007094c", "caller": "0x800b749c",
        "return_address": "0x800b74a4", "entry_cycle": 3003377970,
        "exit_cycle": 3003380400,
    }
    assert natural_exit["callback_teardown"] == {
        "address": "0x800709ac", "caller": "0x800b74a4",
        "return_address": "0x800b74ac", "entry_cycle": 3003380414,
        "exit_cycle": 3003384397, "exit_is_synthetic_unwind": False,
    }


def test_prior_boundary_and_endpoint_residency_are_fail_closed():
    doc = document()
    assert doc["prior_no_input_boundary"] == {
        "artifact": "analysis/phase4_fmv_callback_lifecycle.json",
        "sha256": "d6f049488927a476a59ad36c58b0ea7cab682ed533b8a193516e7beaf3f43f85",
        "frames_advanced": 541,
        "emulator_frame": 4776,
        "str_backloc": 162,
        "selected_frame_limit": 386,
        "fmv_bin_resident": True,
    }
    assert doc["observations"]["endpoint"]["both_fmv_bin_retired"] is True
    assert doc["observations"]["endpoint"]["region_b_typed_fields_valid"] is False
    assert len(doc["residuals"]) == 4
    assert "reachability only" in doc["bounded_conclusion"]
    assert "does not identify" in doc["bounded_conclusion"]


def test_registry_keeps_lifecycle_partial_after_banking_one_fact():
    registry = yaml.safe_load((ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    assert campaign["dimension_claims"].get("lifecycle") is None
    assert campaign["dimension_claims"]["original_interfaces"]["claim"] == "partial"
    assert any(row.get("artifact") == "analysis/phase4_fmv_natural_completion.json"
               for row in campaign["evidence"]["lifecycle"])


def test_receipt_guard_rejects_natural_caller_and_unwind_drift():
    spec = natural.CONFIGURATION["external_receipt"]
    path = natural.EXTERNAL_ROOT / spec["relative_path"]
    mutated = json.loads(path.read_text())
    events = mutated["result"]["jobs"][1]["result"]["capture"]["traces"]["functions"]
    events[4]["caller"] = "0x80000000"
    with pytest.raises(ValueError, match="common-exit call shape drifted"):
        natural.validate_receipt(mutated, verify_identity=False)
    mutated = json.loads(path.read_text())
    events = mutated["result"]["jobs"][1]["result"]["capture"]["traces"]["functions"]
    events[5]["synthetic_unwind"] = True
    with pytest.raises(ValueError, match="teardown unwind classification drifted"):
        natural.validate_receipt(mutated, verify_identity=False)


def test_receipt_guard_rejects_media_and_endpoint_residency_drift():
    spec = natural.CONFIGURATION["external_receipt"]
    path = natural.EXTERNAL_ROOT / spec["relative_path"]
    mutated = json.loads(path.read_text())
    mutated["result"]["jobs"][0]["result"]["media"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="post-load media proof drifted"):
        natural.validate_receipt(mutated, verify_identity=False)
    mutated = json.loads(path.read_text())
    memory = mutated["result"]["jobs"][1]["result"]["capture"]["memory"]
    head = next(row for row in memory if row["label"] == "fmv_bin_head")
    head["hex"] = "00" * 256
    with pytest.raises(ValueError, match="Region-B retirement drifted"):
        natural.validate_receipt(mutated, verify_identity=False)


def test_batch_plan_guard_rejects_completion_bound_drift(monkeypatch):
    plan = deepcopy(yaml.safe_load(natural.BATCH_PLAN.read_text()))
    plan["jobs"][0]["run"]["frames"] = 1499
    monkeypatch.setattr(natural.yaml, "safe_load", lambda _text: plan)
    with pytest.raises(ValueError, match="canonical hash drifted"):
        natural.validate_plan()


def test_cleanup_guard_is_hash_pinned_and_does_not_require_profile_directory(
        monkeypatch):
    path, receipt = natural.validate_cleanup_receipt()
    assert receipt["instance_pid_absent_after_stop"] is True
    mutated = deepcopy(receipt)
    mutated["owned_pid_alive_after_stop"] = True
    monkeypatch.setattr(natural.common, "load_json", lambda _path: mutated)
    with pytest.raises(ValueError, match="cleanup receipt payload drifted"):
        natural.validate_cleanup_receipt()
    assert not natural.build.__doc__ or "/var/tmp" not in natural.build.__doc__
