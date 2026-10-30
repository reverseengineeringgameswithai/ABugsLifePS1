#!/usr/bin/env python3
"""Bank the falsified E15 file-open diagnostic-route control."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_fmv_cd_event_exit_result as receipt_validation


CONFIG_PATH = common.ROOT / "config/phase4_fmv_file_open_failure_result.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_file_open_failure_result.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def _artifact(spec: dict, label: str) -> tuple[Path, dict]:
    return receipt_validation._artifact(
        spec, label, run_root=RUN_ROOT
    )


def _plan(spec: dict) -> dict:
    return receipt_validation._plan(spec)


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row for row in capture.get("memory") or [] if row.get("label") == label
    ]
    _require(len(rows) == 1, f"{label} capture is not unique")
    row = rows[0]
    _require(
        row.get("valid_bytes") == row.get("length")
        and len(row.get("hex") or "") == 2 * row["length"],
        f"{label} capture is incomplete",
    )
    return row


def _trace_observation(result: dict, function_max_events: int) -> dict:
    traces = result["capture"]["traces"]
    functions = traces["functions"]
    indexes = [row["index"] for row in functions]
    _require(
        indexes == list(range(1, len(functions) + 1)),
        "function trace indexes are not contiguous",
    )
    _require(
        len(functions) < function_max_events
        and traces["access"]["truncated"] is False
        and traces["execution"]["truncated"] is False,
        "function trace saturated or truncated",
    )
    diagnostic = [
        row
        for row in functions
        if row["function"].lower() == "0x8005f7dc"
        or row["caller"].lower() == "0x800b6e54"
    ]
    shared = [
        row
        for row in functions
        if row["function"].lower() == "0x800b7c34"
        and row["caller"].lower() == "0x800b6e68"
    ]
    helper = [
        row
        for row in functions
        if row["function"].lower() == "0x800b8a78"
        and row["caller"].lower() == "0x800b8cf4"
    ]
    _require(
        [row["type"] for row in shared] == ["entry", "exit"],
        "shared-initialization call sequence drifted",
    )
    _require(
        [row["type"] for row in helper] == ["entry", "exit"],
        "file-open helper call sequence drifted",
    )
    return {
        "function_events": len(functions),
        "first_retained_index": indexes[0],
        "last_retained_index": indexes[-1],
        "configured_max_events": function_max_events,
        "headroom_events": function_max_events - len(functions),
        "diagnostic_events": len(diagnostic),
        "diagnostic_sequences": sum(
            row["type"] == "entry" for row in diagnostic
        ),
        "shared_initialization_events": len(shared),
        "shared_initialization_sequences": 1,
        "shared_initialization_entry": {
            key: shared[0][key]
            for key in ("caller", "cycle", "frame", "function", "index", "type")
        },
        "file_open_helper_events": len(helper),
        "file_open_helper_sequences": 1,
        "file_open_helper_entry": {
            key: helper[0][key]
            for key in ("caller", "cycle", "frame", "function", "index", "type")
        },
        "access_truncated": traces["access"]["truncated"],
        "execution_truncated": traces["execution"]["truncated"],
    }


def _validate_before_ledger() -> dict:
    _, ledger = _artifact(CONFIGURATION["before_ledger"], "before ledger")
    rows = [
        row
        for row in ledger.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]
    ]
    _require(
        len(rows) == 1
        and rows[0].get("state") == "planned"
        and rows[0].get("target_row") == CONFIGURATION["row_id"]
        and rows[0].get("missing_fact_id")
        == CONFIGURATION["missing_fact_id"],
        "immutable before-ledger did not authorize the planned escalation",
    )
    return rows[0]


def _validate_static_source() -> dict:
    spec = CONFIGURATION["static_source"]
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        "static source identity drifted",
    )
    source = common.load_json(path)
    file_open = source["failure_paths"]["file_open"]
    player = file_open["player"]
    selected = source["selected_control"]
    _require(
        source.get("schema") == "abl-phase4-fmv-failure-frontier/1"
        and source.get("row") == CONFIGURATION["row_id"]
        and file_open["native_runtime_outcome_claimed"] is False
        and player
        == {
            "diagnostic_call": "0x800B6E54",
            "failure_rejoins_shared_initialization": True,
            "failure_target": "0x800B6E4C",
            "helper_call": "0x800B6DD8",
            "predicate": "0x800B6DE8",
            "shared_initialization_call": "0x800B6E68",
        }
        and selected["only_difference"]["address"] == "0x800B6DE8"
        and selected["only_difference"]["original_word"] == "0x12020018"
        and selected["only_difference"]["replacement_word"] == "0x10000018"
        and selected["native_failed_handle_claimed"] is False
        and selected["user_visible_policy_claimed"] is False,
        "static file-open route contract drifted",
    )
    return source


def _load_run(spec: dict) -> dict:
    _, receipt = _artifact(spec["receipt"], f"{spec['role']} receipt")
    _, batch = _artifact(
        spec["batch_result"], f"{spec['role']} batch result"
    )
    _, raw = _artifact(spec["raw_results"], f"{spec['role']} raw results")
    _, cleanup = _artifact(spec["cleanup"], f"{spec['role']} cleanup")
    _, pagination = _artifact(
        spec["pagination"], f"{spec['role']} pagination"
    )
    _, events = _artifact(
        spec["command_events"], f"{spec['role']} command events"
    )
    plan = _plan(spec)
    return receipt_validation.validate_run(
        spec,
        receipt,
        batch,
        raw,
        cleanup,
        pagination,
        events,
        plan,
        configuration=CONFIGURATION,
        run_root=RUN_ROOT,
    )


def build() -> dict[str, Any]:
    _validate_before_ledger()
    _validate_static_source()
    runs = {
        spec["role"]: _load_run(spec) for spec in CONFIGURATION["receipts"]
    }
    passive_jobs = runs["passive"]["jobs"]
    _require(
        passive_jobs[0]["result"]["capture"]
        == passive_jobs[1]["result"]["capture"],
        "passive same-anchor endpoints diverged",
    )

    precise_spec = next(
        row for row in CONFIGURATION["receipts"] if row["role"] == "precise"
    )
    precise_jobs = runs["precise"]["jobs"]
    positive = precise_jobs[0]["result"]
    native = precise_jobs[1]["result"]
    _require(
        positive["staged_prelude"]["status"]
        == native["staged_prelude"]["status"],
        "precise staged endpoints diverged",
    )
    for result in (positive, native):
        _require(
            result["capture"]["frame"] == 4475
            and result["capture"]["cycle"] == 2533180622,
            "precise finite capture endpoint drifted",
        )

    write = positive.get("after_load")
    _require(
        write
        == {
            "address": "0x800b6de8",
            "after": "0x10000018",
            "before": "0x12020018",
            "code_invalidated": True,
            "kind": "code_write",
            "original_word": "0x12020018",
            "replacement_word": "0x10000018",
            "written": 4,
        }
        and native.get("after_load") is None,
        "one-word write/readback control drifted",
    )
    positive_route = _memory(positive["capture"], "file_open_route")
    native_route = _memory(native["capture"], "file_open_route")
    route_differences = [
        index
        for index, (left, right) in enumerate(
            zip(
                bytes.fromhex(positive_route["hex"]),
                bytes.fromhex(native_route["hex"]),
                strict=True,
            )
        )
        if left != right
    ]
    _require(
        route_differences == [18, 19],
        "retained file-open route changed outside the declared word",
    )

    positive_trace = _trace_observation(
        positive, precise_spec["function_max_events"]
    )
    native_trace = _trace_observation(
        native, precise_spec["function_max_events"]
    )
    _require(
        positive_trace["diagnostic_sequences"] == 0
        and native_trace["diagnostic_sequences"] == 0,
        "diagnostic omission falsifier no longer holds",
    )
    positive_limit = _memory(
        positive["capture"], "selected_frame_limit"
    )["hex"]
    native_limit = _memory(native["capture"], "selected_frame_limit")["hex"]
    _require(
        positive_limit == "1800f000"
        and native_limit == "18008000"
        and positive_limit != native_limit,
        "selected-frame-limit discriminator drifted",
    )

    receipt_rows = [
        {
            key: run[key]
            for key in (
                "role",
                "precise",
                "receipt_sha256",
                "batch_result_sha256",
                "raw_results_sha256",
                "cleanup_sha256",
                "pagination_sha256",
                "command_events_sha256",
                "stage_start",
                "stage_stop",
                "observer_start",
                "replay_stop",
            )
        }
        for run in runs.values()
    ]
    document = {
        "_comment": (
            "Generated from two closed, hash-pinned investigator receipts. "
            "This disproves only the predeclared bounded counterfactual; it "
            "does not describe a native retail file-open failure."
        ),
        "schema": "abl-phase4-fmv-file-open-failure-result/1",
        "generated": _stable_generated(),
        "campaign": CONFIGURATION["campaign_id"],
        "row": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "valid": True,
        "errors": [],
        "receipts": receipt_rows,
        "inputs": {
            "config": {
                "path": CONFIG_PATH.relative_to(common.ROOT).as_posix(),
                "sha256": common.sha256(CONFIG_PATH),
            },
            "before_ledger": CONFIGURATION["before_ledger"],
            "static_source": CONFIGURATION["static_source"],
            "receipts": receipt_rows,
        },
        "observation": {
            "passive": {
                "repeat_equal": True,
                "capture_frame": passive_jobs[0]["result"]["capture"]["frame"],
                "capture_cycle": passive_jobs[0]["result"]["capture"]["cycle"],
            },
            "positive": {
                "one_word_write": write,
                "capture_frame": positive["capture"]["frame"],
                "capture_cycle": positive["capture"]["cycle"],
                "capture_pc": positive["capture"]["cpu"]["registers"][
                    "registers_hex"
                ]["pc"],
                "selected_frame_limit_hex_le": positive_limit,
                **positive_trace,
            },
            "native_negative": {
                "one_word_write": None,
                "capture_frame": native["capture"]["frame"],
                "capture_cycle": native["capture"]["cycle"],
                "capture_pc": native["capture"]["cpu"]["registers"][
                    "registers_hex"
                ]["pc"],
                "selected_frame_limit_hex_le": native_limit,
                **native_trace,
            },
        },
        "falsifier": {
            "claim": (
                "The one-word positive must record one diagnostic sequence "
                "from 0x800B6E54 before rejoining shared initialization; "
                "the native negative must omit it."
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
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 1000,
            "observer_frames": 340,
            "function_events": 24,
            "diagnostic_sequences": 0,
            "shared_initialization_sequences": 2,
            "exact_after_load_writes": 1,
            "investigator_live_receipts": 2,
            "promotion_admissible_live_receipts": 0,
            "owned_pids_stopped": 2,
        },
    }
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.write and not args.check:
        parser.error("choose --write and/or --check")
    document = build()
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(payload)
    if args.check:
        _require(OUTPUT.is_file(), f"missing generated artifact: {OUTPUT}")
        _require(OUTPUT.read_text() == payload, "generated artifact is stale")
    print(
        "phase4 FMV file-open failure result: PASS "
        "(falsified diagnostic-route claim; 0 lifecycle promotions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
