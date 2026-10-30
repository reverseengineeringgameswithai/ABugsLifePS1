from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_file_open_failure_result as result  # noqa: E402


def _precise_jobs() -> tuple[dict, dict, int]:
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == "precise"
    )
    path = (
        result.RUN_ROOT / spec["batch_result"]["relative_path"]
    )
    batch = json.loads(path.read_text())
    jobs = batch["result"]["jobs"]
    return jobs[0]["result"], jobs[1]["result"], spec["function_max_events"]


def test_file_open_diagnostic_route_falsifier_is_banked_without_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"] == {
        "claim": (
            "The one-word positive must record one diagnostic sequence from "
            "0x800B6E54 before rejoining shared initialization; the native "
            "negative must omit it."
        ),
        "outcome": "falsified",
        "evidence": {
            "positive_diagnostic_sequences": 0,
            "native_diagnostic_sequences": 0,
            "positive_shared_initialization_sequences": 1,
            "native_shared_initialization_sequences": 1,
            "positive_function_events": 12,
            "native_function_events": 12,
            "configured_max_events": 128,
            "headroom_events_per_branch": 116,
            "truncated": False,
            "passive_repeat_equal": True,
            "owned_pids_stopped": 2,
        },
    }
    assert document["observation"]["positive"][
        "selected_frame_limit_hex_le"
    ] == "1800f000"
    assert document["observation"]["native_negative"][
        "selected_frame_limit_hex_le"
    ] == "18008000"
    boundary = document["claim_boundary"]
    assert boundary["selected_hypothesis_disproven"] is True
    assert boundary["file_open_diagnostic_route_fact_closed"] is False
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
            lambda row: row["capture"]["traces"]["functions"][0].update(
                {"index": 2}
            ),
            "indexes are not contiguous",
        ),
        (
            lambda row: row["capture"]["traces"].update(
                {"execution": {"events": [], "total": 0, "truncated": True}}
            ),
            "saturated or truncated",
        ),
        (
            lambda row: row["capture"]["traces"]["functions"][4].update(
                {"caller": "0x800b6e64"}
            ),
            "shared-initialization call sequence",
        ),
    ],
)
def test_trace_mutations_are_rejected(mutator, error):
    positive, _, maximum = _precise_jobs()
    changed = copy.deepcopy(positive)
    mutator(changed)
    with pytest.raises(ValueError, match=error):
        result._trace_observation(changed, maximum)


def test_diagnostic_event_would_falsify_the_banked_omission():
    positive, _, maximum = _precise_jobs()
    changed = copy.deepcopy(positive)
    trace = changed["capture"]["traces"]["functions"]
    trace.append(
        {
            "caller": "0x800b6e54",
            "function": "0x8005f7dc",
            "index": 13,
            "type": "entry",
        }
    )
    observation = result._trace_observation(changed, maximum)
    assert observation["diagnostic_sequences"] == 1
    assert observation["headroom_events"] == 115


def test_shared_receipt_validator_accepts_an_explicit_configuration():
    spec = next(
        row
        for row in result.CONFIGURATION["receipts"]
        if row["role"] == "passive"
    )
    checked = result._load_run(spec)
    assert checked["role"] == "passive"
    assert checked["receipt_sha256"] == (
        "ea877606c378687c24ee4115f115fccd3518609413c2c03eb8208d64ee9a4576"
    )
