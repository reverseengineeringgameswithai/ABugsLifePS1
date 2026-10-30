from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_decoded_record_control_result as result  # noqa: E402


def _evidence(
        role: str) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    spec = next(
        row for row in result.CONFIGURATION["receipts"]
        if row["role"] == role)
    run_root = Path(result.CONFIGURATION["run_root"])
    receipt = json.loads(
        (run_root / spec["receipt"]["relative_path"]).read_text())
    batch = json.loads(
        (run_root / spec["batch_result"]["relative_path"]).read_text())
    raw = json.loads(
        (run_root / spec["raw_results"]["relative_path"]).read_text())
    cleanup = json.loads(
        (run_root / spec["cleanup"]["relative_path"]).read_text())
    pagination = json.loads(
        (run_root / spec["pagination"]["relative_path"]).read_text())
    events = json.loads(
        (run_root / spec["command_events"]["relative_path"]).read_text())
    plan = result.common.load_yaml(ROOT / spec["plan"]["path"])
    return spec, receipt, batch, raw, cleanup, pagination, events, plan


def test_saturation_falsifier_is_banked_without_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"] == {
        "predicate": (
            "any planned observer truncation or saturation rejects the "
            "positive/negative control as lifecycle evidence"),
        "outcome": "falsified",
        "reason": "negative_function_trace_saturated_and_dropped_prefix",
        "evidence": {
            "configured_max_events": 64,
            "retained_events": 64,
            "first_retained_index": 27,
            "last_retained_index": 90,
            "discarded_prefix_events": 26,
        },
    }
    latch = document["observation"]["positive"]["latch_write"]
    assert (latch["instruction_pc"], latch["address"], latch["value"],
            latch["new_value"], latch["width"]) == (
                "0x800b6c84", "0x800b9a54", 0, 1, 1)
    assert document["observation"]["negative"]["access_events"] == 0
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["lifecycle_promoted"] is False
    assert document["record_counts"][
        "promotion_admissible_live_receipts"] == 0
    retention = document["retention_decomposition"]
    assert retention["observed_same_anchor_rate"] == {
        "window": {"clock": "movie_frame", "start": 650, "stop": 850},
        "total_function_events": 90,
        "events_per_movie_frame": "0.450000",
        "retained_suffix_events": 64,
        "discarded_prefix_events": 26,
        "discarded_event_types_claimed": False,
    }
    assert retention["successor_retention_contract"][
        "max_events"] == 128
    assert retention["successor_retention_contract"][
        "headroom_events"] == 38
    assert retention["successor_retention_contract"][
        "require_first_retained_index"] == 1
    assert retention["static_callsite"]["instructions"][2] == {
        "pc": "0x800B7280",
        "word": "0x0C02DB09",
        "mnemonic": "jal 0x800b6c24",
    }
    assert document["claim_boundary"]["next_lane"] == "live"
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n")


@pytest.mark.parametrize(
    ("target", "mutator", "error"),
    [
        (
            "batch",
            lambda row: row["result"]["jobs"][0]["result"][
                "capture"]["traces"]["access"]["events"][0].update(
                    {"instruction_pc": "0x800b6c80"}),
            "instruction-attributed latch write",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][0]["result"][
                "capture"]["traces"]["access"]["events"][0].update(
                    {"new_value": 2}),
            "instruction-attributed latch write",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"][
                "capture"]["traces"]["access"].update(
                    {"events": [{"address": "0x800b9a54"}], "total": 1}),
            "negative latch access exclusion",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"][
                "capture"]["traces"]["functions"].pop(0),
            "saturation signature",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"][
                "capture"]["traces"]["functions"][0].update({"index": 1}),
            "saturation signature",
        ),
        (
            "cleanup",
            lambda row: row.update({"owned_pid_stopped": False}),
            "owned-PID cleanup",
        ),
        (
            "receipt",
            lambda row: row["prelude_receipt"].update({"sha256": "0" * 64}),
            "passive-prelude join",
        ),
    ],
)
def test_precise_low_level_mutations_are_rejected(target, mutator, error):
    spec, receipt, batch, raw, cleanup, pagination, events, plan = _evidence(
        "precise")
    values = {
        "receipt": copy.deepcopy(receipt),
        "batch": copy.deepcopy(batch),
        "raw": copy.deepcopy(raw),
        "cleanup": copy.deepcopy(cleanup),
        "pagination": copy.deepcopy(pagination),
        "events": copy.deepcopy(events),
    }
    mutator(values[target])
    with pytest.raises(ValueError, match=error):
        checked = result.validate_run(
            spec, values["receipt"], values["batch"], values["raw"],
            values["cleanup"], values["pagination"], values["events"], plan)
        jobs = checked["jobs"]
        result._positive_observation(jobs[0]["result"])
        result._negative_saturation(
            jobs[1]["result"], spec["function_max_events"])


def test_passive_endpoint_mutation_is_rejected():
    spec, receipt, batch, raw, cleanup, pagination, events, plan = _evidence(
        "passive")
    batch = copy.deepcopy(batch)
    batch["result"]["jobs"][1]["result"]["capture"]["frame"] += 1
    checked = result.validate_run(
        spec, receipt, batch, raw, cleanup, pagination, events, plan)
    jobs = checked["jobs"]
    with pytest.raises(ValueError, match="passive same-anchor endpoints"):
        result._require(
            jobs[0]["result"]["capture"] == jobs[1]["result"]["capture"],
            "passive same-anchor endpoints diverged")


def test_retention_contract_rejects_artifact_drift(monkeypatch):
    original = result._run_artifact

    def drifted(run_root, spec, label):
        path, document = original(run_root, spec, label)
        if label == "retention query output":
            document = copy.deepcopy(document)
            document["successor_retention_contract"]["max_events"] = 127
        return path, document

    monkeypatch.setattr(result, "_run_artifact", drifted)
    with pytest.raises(ValueError, match="successor retention contract"):
        result._retention_decomposition(
            "4d43e6ee87a8d822a57c55b95d8756973e1fbeea69bd9f5dbf2e86114a1a7968")
