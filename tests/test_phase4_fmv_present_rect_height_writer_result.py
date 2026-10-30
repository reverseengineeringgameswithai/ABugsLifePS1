from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_present_rect_height_writer_result as result  # noqa: E402


def _precise_jobs() -> tuple[dict, dict, int]:
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == "precise"
    )
    path = result.RUN_ROOT / spec["batch_result"]["relative_path"]
    batch = json.loads(path.read_text())
    jobs = batch["result"]["jobs"]
    return (
        jobs[0]["result"],
        jobs[1]["result"],
        spec["access_max_events"],
    )


def test_saturated_writer_falsifier_is_banked_without_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"] == {
        "claim": (
            "Both unmodified precise jobs must retain the same ordered, "
            "unsaturated CPU writer sequence through the native height-128 "
            "endpoint; reaching the configured capacity falsifies it."
        ),
        "outcome": "falsified",
        "reason": "returned_event_count_reached_configured_bound",
        "evidence": {
            "native_returned_events": 32,
            "repeat_returned_events": 32,
            "configured_max_events": 32,
            "capacity_headroom_per_job": 0,
            "trace_truncated": False,
            "ordered_events_repeat_equal": True,
            "endpoint_repeat_equal": True,
            "first_240_to_128_writer_pc": "0x800b6bf0",
            "owned_pids_stopped": 2,
        },
    }
    native = document["observation"]["precise"]["native"]
    assert native["writer_pc_counts"] == {
        "0x80064178": 28,
        "0x800b6bf0": 3,
        "0x800b6f18": 1,
    }
    assert native["first_240_to_128_writer"]["value"] == 240
    assert native["first_240_to_128_writer"]["new_value"] == 128
    assert native["endpoint"]["present_rect_height"] == 128
    boundary = document["claim_boundary"]
    assert boundary["first_240_to_128_event_observed"] is True
    assert boundary["complete_writer_sequence_closed"] is False
    assert boundary["cpu_writer_hypothesis_promoted"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "static"
    assert document["record_counts"][
        "promotion_admissible_live_receipts"
    ] == 0
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda access: access.update({"total": 31}),
            "totals/truncation",
        ),
        (
            lambda access: access["watches"][0].update({"max_events": 64}),
            "write-watch contract",
        ),
        (
            lambda access: access["events"][1].update(
                {"instruction_pc": "0x800b6bf4"}
            ),
            "240-to-128 writer",
        ),
        (
            lambda access: access["events"][2].update({"width": 4}),
            "typed halfword writer",
        ),
    ],
)
def test_writer_trace_mutations_are_rejected(mutator, error):
    native, _, maximum = _precise_jobs()
    changed = copy.deepcopy(native)
    mutator(changed["capture"]["traces"]["access"])
    with pytest.raises(ValueError, match=error):
        result._trace_observation(changed, maximum)


def test_unsaturated_trace_would_reject_the_banked_saturation_outcome():
    native, _, maximum = _precise_jobs()
    changed = copy.deepcopy(native)
    access = changed["capture"]["traces"]["access"]
    access["events"].pop()
    access["total"] = access["watches"][0]["hit_count"] = 31
    with pytest.raises(ValueError, match="saturation falsifier"):
        result._trace_observation(changed, maximum)


def test_repeat_sequence_is_equal_after_watch_id_normalization():
    native, repeat, maximum = _precise_jobs()
    native_row = result._trace_observation(native, maximum)
    repeat_row = result._trace_observation(repeat, maximum)
    assert native_row["normalized_events"] == repeat_row["normalized_events"]


def test_shared_receipt_validator_accepts_the_precise_v2_receipt():
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == "precise"
    )
    checked = result._load_run(spec)
    assert checked["role"] == "precise"
    assert checked["receipt_sha256"] == (
        "fcff7c2012a29255824096e3bb7f782cc7bbb1772c58da379faf19113c04ad8f"
    )
