from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_present_rect_height_function_trace_result as result  # noqa: E402


def _precise_jobs() -> tuple[dict, dict, int]:
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == "precise"
    )
    batch = json.loads(
        (result.RUN_ROOT / spec["batch_result"]["relative_path"]).read_text()
    )
    jobs = batch["result"]["jobs"]
    return jobs[0]["result"], jobs[1]["result"], spec["function_max_events"]


def _append_contiguous_entry(row: dict) -> None:
    functions = row["capture"]["traces"]["functions"]
    entry = copy.deepcopy(functions[0])
    entry["index"] = len(functions) + 1
    functions.append(entry)


def _fill_trace_to_capacity(row: dict, maximum: int) -> None:
    functions = row["capture"]["traces"]["functions"]
    functions.extend(copy.deepcopy(functions[: maximum - len(functions)]))
    for index, event in enumerate(functions, start=1):
        event["index"] = index


def test_three_call_cardinality_falsifier_is_banked_without_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "falsified"
    assert document["falsifier"]["reasons"] == [
        "observed_call_count_11_not_predicted_3",
        "function_trace_caller_is_call_instruction_0x800B6C34",
        "first_exit_is_observer_synthetic_unwind",
    ]
    evidence = document["falsifier"]["evidence"]
    assert evidence["predicted_calls"] == 3
    assert evidence["observed_calls_per_branch"] == 11
    assert evidence["observed_function_events_per_branch"] == 22
    assert evidence["headroom_events_per_branch"] == 10
    assert evidence["argument_class_call_counts"] == [1, 1, 9]
    assert evidence["synthetic_exit_indexes"] == [2]
    assert evidence["precise_repeat_equal"] is True
    assert evidence["passive_repeat_equal"] is True
    assert evidence["owned_pids_stopped"] == 2
    assert document["static_join"] == {
        "sha256": (
            "998d975f91d218d2d8e71b94e713d66679a6cef455b9d0797523508510725673"
        ),
        "owning_helper": "0x800B6C24",
        "call_instruction": "0x800B6C34",
        "return_address": "0x800B6C3C",
        "call_instruction_word": "0x0C02DA9F",
        "player_boundary_base": "0x800CABE0",
    }
    boundary = document["claim_boundary"]
    assert boundary["selected_hypothesis_disproven"] is True
    assert boundary["bounded_window_cardinality_observed"] is True
    assert boundary["predicted_three_call_cardinality_closed"] is False
    assert boundary["lifecycle_promoted"] is False
    assert boundary["dimension_promoted"] is False
    assert boundary["next_lane"] == "static"
    assert document["record_counts"][
        "promotion_admissible_live_receipts"
    ] == 0
    assert result.OUTPUT.read_text() == (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    )


def test_same_anchor_precise_branches_retain_the_same_ordered_trace():
    native, repeat, maximum = _precise_jobs()
    native_observation = result._trace_observation(native, maximum)
    repeat_observation = result._trace_observation(repeat, maximum)
    assert native_observation == repeat_observation
    assert native_observation["call_count"] == 11
    assert native_observation["first_retained_index"] == 1
    assert native_observation["last_retained_index"] == 22
    assert native_observation["call_instruction"] == "0x800b6c34"
    assert native_observation["owning_helper"] == "0x800b6c24"


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda row: row["capture"]["traces"]["functions"][0].update(
                {"index": 2}
            ),
            "indexes are not contiguous",
        ),
        (
            lambda row: row["capture"]["traces"]["functions"][0].update(
                {"caller": "0x800b6c24"}
            ),
            "call-instruction field drifted",
        ),
        (
            lambda row: row["capture"]["traces"]["functions"][1].update(
                {"arguments": ["0x00000000"] * 4}
            ),
            "pair arguments or ordering drifted",
        ),
        (
            _append_contiguous_entry,
            "entries and exits are not paired",
        ),
    ],
)
def test_trace_identity_pairing_and_cardinality_mutations_are_rejected(
    mutator, error
):
    native, _, maximum = _precise_jobs()
    changed = copy.deepcopy(native)
    mutator(changed)
    with pytest.raises(ValueError, match=error):
        result._trace_observation(changed, maximum)


def test_trace_saturation_would_reject_the_bounded_observation():
    native, _, maximum = _precise_jobs()
    changed = copy.deepcopy(native)
    _fill_trace_to_capacity(changed, maximum)
    with pytest.raises(ValueError, match="saturated or truncated"):
        result._trace_observation(changed, maximum)


def test_shared_receipt_validator_consumes_both_live_receipts():
    checked = {
        spec["role"]: result._load_run(spec)
        for spec in result.CONFIGURATION["receipts"]
    }
    assert checked["passive"]["receipt_sha256"] == (
        "5b820de153b9874f3f3d08eb996676aac72965b4c37301ad10437491ffaa1ba8"
    )
    assert checked["precise"]["receipt_sha256"] == (
        "29b4e6f4031d997a3081305ce52a1f8899e040bd0c891a083f222ca4832951c6"
    )
