"""Falsification guards for E15 selected-limit natural completion."""

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_natural_exit_cause as cause  # noqa: E402


def document() -> dict:
    return json.loads(cause.OUTPUT.read_text())


def receipt() -> dict:
    spec = cause.CONFIGURATION["external_receipt"]
    return json.loads(
        (cause.EXTERNAL_ROOT / spec["relative_path"]).read_text())


def test_summary_rebuilds_from_result_and_cleanup_receipts():
    assert cause.render(cause.build()) == cause.OUTPUT.read_bytes()
    doc = document()
    assert doc["valid"] is True and doc["errors"] == []
    assert doc["record_counts"] == {
        "atomic_batches": 1,
        "jobs": 2,
        "function_events": 12,
        "access_events": 33,
        "resident_causal_access_events": 7,
    }
    assert {row["role"] for row in doc["external_receipts"]} == {
        "atomic_batch_result", "owned_pid_cleanup"}
    assert doc["raw_external_bytes_committed"] is False


def test_natural_completion_is_instruction_attributed_and_bounded():
    observed = document()["observations"]
    natural = observed["natural_selected_limit_completion"]
    cause_row = natural["cause"]
    assert cause_row["selected_frame_limit_write"] == {
        "frame": 4418, "cycle": 2501102830,
        "instruction_pc": "0x800b6dc0", "old_value": 0, "new_value": 386}
    assert cause_row["late_backloc_writes"][1] == {
        "frame": 5216, "cycle": 2952949785,
        "instruction_pc": "0x80070a8c", "old_value": 381, "new_value": 384}
    assert cause_row["completion_set"] == {
        "frame": 5253, "cycle": 2973774887,
        "instruction_pc": "0x800b6b48",
        "instruction": "sw v0, -0x53f0(at)",
        "old_value": 0, "new_value": 1}
    assert cause_row["stop_latch_write_count"] == 0
    assert natural["common_exit"]["frame"] == 5305
    assert natural["endpoint"]["fmv_bin_resident"] is True
    assert observed["start_same_anchor_control"]["post_retirement_access_untyped"] is True


def test_residuals_do_not_promote_lifecycle_or_post_retirement_addresses():
    doc = document()
    assert len(doc["residuals"]) == 4
    assert "one LEV1A" in doc["residuals"][0]
    assert "deliberately untyped" in doc["residuals"][2]
    registry = yaml.safe_load(
        (ROOT / "config/phase4_campaigns.yaml").read_text())
    campaign = next(row for row in registry["child_campaigns"]
                    if row["id"] == "fmv_playback")
    assert campaign["dimension_claims"].get("lifecycle") is None


def test_receipt_guard_rejects_completion_writer_drift():
    mutated = receipt()
    natural = next(row for row in mutated["result"]["jobs"]
                   if row["id"] == "natural_no_input_control")
    events = natural["result"]["capture"]["traces"]["access"]["events"]
    completion = next(
        row for row in events
        if row["address"] == "0x800cac10" and row["new_value"] == 1)
    completion["instruction_pc"] = "0x800b6b24"
    with pytest.raises(
            ValueError, match="completion-request set writer provenance drifted"):
        cause.validate_receipt(mutated, verify_identity=False)


def test_receipt_guard_rejects_stop_latch_hit_and_access_truncation():
    mutated = receipt()
    natural = next(row for row in mutated["result"]["jobs"]
                   if row["id"] == "natural_no_input_control")
    access = natural["result"]["capture"]["traces"]["access"]
    stop = next(row for row in access["watches"]
                if row["label"] == "decode_stop_latch")
    stop["hit_count"] = 1
    with pytest.raises(ValueError, match="stop latch was written"):
        cause.validate_receipt(mutated, verify_identity=False)
    mutated = receipt()
    natural = next(row for row in mutated["result"]["jobs"]
                   if row["id"] == "natural_no_input_control")
    natural["result"]["capture"]["traces"]["access"]["truncated"] = True
    with pytest.raises(ValueError, match="provenance truncated"):
        cause.validate_receipt(mutated, verify_identity=False)


def test_receipt_guard_rejects_resident_endpoint_drift():
    mutated = receipt()
    natural = next(row for row in mutated["result"]["jobs"]
                   if row["id"] == "natural_no_input_control")
    memory = natural["result"]["capture"]["memory"]
    selected = next(row for row in memory
                    if row["label"] == "selected_frame_limit")
    selected["hex"] = "8101"
    with pytest.raises(ValueError, match="resident endpoint state drifted"):
        cause.validate_receipt(mutated, verify_identity=False)


def test_cleanup_guard_rejects_payload_drift(monkeypatch):
    _path, actual = cause.validate_cleanup_receipt()
    mutated = deepcopy(actual)
    mutated["credentials_retained"] = True
    monkeypatch.setattr(cause.common, "load_json", lambda _path: mutated)
    with pytest.raises(ValueError, match="cleanup receipt payload drifted"):
        cause.validate_cleanup_receipt()


def test_batch_plan_guard_rejects_instrumentation_drift(monkeypatch):
    plan = deepcopy(yaml.safe_load(cause.BATCH_PLAN.read_text()))
    plan["jobs"][0]["instrumentation"][1]["method"] = "functionTrace.start"
    monkeypatch.setattr(cause.yaml, "safe_load", lambda _text: plan)
    with pytest.raises(ValueError, match="canonical hash drifted"):
        cause.validate_plan()
