from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import phase4_fmv_cd_event_exit_result as result  # noqa: E402


def _evidence(
    role: str,
) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    spec = next(
        row for row in result.CONFIGURATION["receipts"] if row["role"] == role
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


def test_cd_event_player_interface_falsifier_survives_without_promotion():
    document = result.build()
    assert document["valid"] is True and document["errors"] == []
    assert document["falsifier"]["outcome"] == "survived"
    assert document["falsifier"]["evidence"] == {
        "positive_target_exit_events": 6,
        "negative_target_exit_events": 0,
        "positive_total_function_events": 12,
        "configured_max_events": 128,
        "headroom_events": 116,
        "passive_repeat_equal": True,
        "truncated": False,
        "owned_pids_stopped": 2,
    }
    positive = document["observation"]["positive"]
    assert positive["one_word_write"] == {
        "address": "0x800b7420",
        "after": "0x24020001",
        "before": "0x8c422484",
        "code_invalidated": True,
        "kind": "code_write",
        "original_word": "0x8c422484",
        "replacement_word": "0x24020001",
        "written": 4,
    }
    assert positive["ordered_exit_functions"][:6] == [
        ("entry", "0x8006d8e8", "0x800b746c", 1),
        ("exit", "0x8006d8e8", "0x800b746c", 2),
        ("entry", "0x8007094c", "0x800b749c", 3),
        ("exit", "0x8007094c", "0x800b749c", 4),
        ("entry", "0x800709ac", "0x800b74a4", 5),
        ("exit", "0x800709ac", "0x800b74a4", 6),
    ]
    assert document["observation"]["native_negative"][
        "target_exit_events"
    ] == 0
    assert document["claim_boundary"][
        "player_consumer_interface_fact_closed"
    ] is True
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
            lambda row: row["result"]["jobs"][0]["result"][
                "after_load"
            ].update({"replacement_word": "0x24020000"}),
            "one-word write/readback",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][0]["result"]["capture"][
                "traces"
            ]["functions"][0].update({"caller": "0x800b7468"}),
            "ordered CD-event exit sequence",
        ),
        (
            "batch",
            lambda row: row["result"]["jobs"][1]["result"]["capture"][
                "traces"
            ]["functions"].append({"index": 1}),
            "native negative exit-sequence exclusion",
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
        result._negative_observation(jobs[1]["result"])


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
