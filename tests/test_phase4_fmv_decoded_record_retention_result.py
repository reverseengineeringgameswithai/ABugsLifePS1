from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_decoded_record_retention_result as result  # noqa: E402


def _evidence(
    role: str,
) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == role
    )
    run_root = Path(result.CONFIGURATION["run_root"])
    receipt = json.loads(
        (run_root / spec["receipt"]["relative_path"]).read_text()
    )
    batch = json.loads(
        (run_root / spec["batch_result"]["relative_path"]).read_text()
    )
    raw = json.loads(
        (run_root / spec["raw_results"]["relative_path"]).read_text()
    )
    cleanup = json.loads(
        (run_root / spec["cleanup"]["relative_path"]).read_text()
    )
    pagination = json.loads(
        (run_root / spec["pagination"]["relative_path"]).read_text()
    )
    events = json.loads(
        (run_root / spec["command_events"]["relative_path"]).read_text()
    )
    plan = result.common.load_yaml(ROOT / spec["plan"]["path"])
    return spec, receipt, batch, raw, cleanup, pagination, events, plan


def test_retention_falsifier_survives_without_dimension_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "survived"
    assert document["falsifier"]["evidence"] == {
        "configured_max_events": 128,
        "retained_events": 90,
        "first_retained_index": 1,
        "last_retained_index": 90,
        "discarded_prefix_events": 0,
        "headroom_events": 38,
        "truncated": False,
        "native_latch_writes": 0,
    }
    native = document["observation"]["native_negative"]
    assert (
        native["helper_calls"],
        native["helper_function"],
        native["helper_caller"],
        native["teardown_events"],
    ) == (45, "0x800b6c24", "0x800b7280", 0)
    positive = document["observation"]["positive"]
    assert (
        positive["latch_write"]["instruction_pc"],
        positive["latch_write"]["address"],
        positive["latch_write"]["value"],
        positive["latch_write"]["new_value"],
    ) == ("0x800b6c84", "0x800b9a54", 0, 1)
    assert document["claim_boundary"]["observer_retention_fact_closed"] is True
    assert document["claim_boundary"]["lifecycle_promoted"] is False
    assert document["claim_boundary"]["dimension_promoted"] is False
    assert document["claim_boundary"]["next_lane"] == "static"
    assert document["record_counts"][
        "promotion_admissible_live_receipts"
    ] == 0
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


@pytest.mark.parametrize(
    ("target", "mutator", "error"),
    [
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"
            ]["functions"][0].update({"index": 27}),
            "retention signature",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"
            ]["functions"].pop(),
            "retention signature",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"
            ]["functions"][20].update({"caller": "0x800b7000"}),
            "complete helper sequence",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"
            ]["access"].update(
                {"events": [{"address": "0x800b9a54"}], "total": 1}
            ),
            "latch access exclusion",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][0]["result"]["capture"][
                "traces"
            ]["access"]["events"][0].update(
                {"instruction_pc": "0x800b6c80"}
            ),
            "instruction-attributed latch write",
        ),
        (
            "cleanup",
            lambda row: row.update({"owned_pid_stopped": False}),
            "owned-PID cleanup",
        ),
        (
            "receipt",
            lambda row: row["prelude_receipt"].update(
                {"sha256": "0" * 64}
            ),
            "passive-prelude join",
        ),
    ],
)
def test_precise_low_level_mutations_are_rejected(target, mutator, error):
    spec, receipt, batch, raw, cleanup, pagination, events, plan = _evidence(
        "precise"
    )
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
            spec,
            values["receipt"],
            values["batch"],
            values["raw"],
            values["cleanup"],
            values["pagination"],
            values["events"],
            plan,
        )
        jobs = checked["jobs"]
        result._positive_observation(
            jobs[0]["result"], spec["function_max_events"]
        )
        result._negative_observation(
            jobs[1]["result"], spec["function_max_events"]
        )


def test_passive_endpoint_and_command_body_mutations_are_rejected():
    spec, receipt, batch, raw, cleanup, pagination, events, plan = _evidence(
        "passive"
    )
    changed_batch = copy.deepcopy(batch)
    changed_batch["result"]["jobs"][1]["result"]["capture"]["frame"] += 1
    checked = result.validate_run(
        spec,
        receipt,
        changed_batch,
        raw,
        cleanup,
        pagination,
        events,
        plan,
    )
    jobs = checked["jobs"]
    with pytest.raises(ValueError, match="passive same-anchor endpoints"):
        result._require(
            jobs[0]["result"]["capture"] == jobs[1]["result"]["capture"],
            "passive same-anchor endpoints diverged",
        )

    changed_events = copy.deepcopy(events)
    changed_events["events"][0]["result"]["source_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="result body/hash"):
        result.validate_run(
            spec,
            receipt,
            batch,
            raw,
            cleanup,
            pagination,
            changed_events,
            plan,
        )
