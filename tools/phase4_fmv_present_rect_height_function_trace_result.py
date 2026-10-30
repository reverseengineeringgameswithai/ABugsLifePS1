#!/usr/bin/env python3
"""Bank the falsified E15 presentation-RECT function cardinality control."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_fmv_cd_event_exit_result as receipt_validation


CONFIG_PATH = (
    common.ROOT
    / "config/phase4_fmv_present_rect_height_function_trace_result.yaml"
)
OUTPUT = (
    common.ROOT
    / "analysis/phase4_fmv_present_rect_height_function_trace_result.json"
)
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
    return receipt_validation._artifact(spec, label, run_root=RUN_ROOT)


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
    _require(
        "exactly three times" in rows[0].get("hypothesis", "")
        and "more or fewer than three" in rows[0].get("hypothesis", ""),
        "immutable before-ledger lost the cardinality falsifier",
    )
    return rows[0]


def _validate_offline_query() -> dict:
    source = CONFIGURATION["offline_query"]
    _, receipt = _artifact(source["receipt"], "offline query receipt")
    _, preservation = _artifact(
        source["preservation"], "offline preservation manifest"
    )
    _, output = _artifact(source["output"], "offline query output")
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0,
        "offline query receipt is not closed",
    )
    inputs = receipt.get("external_inputs") or []
    _require(
        len(inputs) == 1
        and inputs[0].get("sha256") == source["external_index_sha256"],
        "offline query input identity drifted",
    )
    _require(
        receipt.get("query", {}).get("terms") == source["expected_zero_terms"],
        "offline query terms drifted",
    )
    terms = output.get("terms") or {}
    _require(
        output.get("schema") == "abl-phase4-offline-json-search-result/1"
        and set(terms) == set(source["expected_zero_terms"])
        and all(
            terms[term].get("count") == 0
            and terms[term].get("paths") == []
            and terms[term].get("paths_truncated") is False
            for term in source["expected_zero_terms"]
        ),
        "offline index no longer returns the expected complete zero-result set",
    )
    preservation_entries = preservation.get("entries") or []
    _require(
        preservation.get("complete") is True
        and preservation.get("errors") == []
        and any(
            row.get("sha256") == source["external_index_sha256"]
            and row.get("media_class") == "derived_pristine_evidence"
            and row.get("preservation_required") is True
            for row in preservation_entries
        ),
        "offline input is not centrally preserved derived-pristine evidence",
    )
    return {
        "receipt_sha256": source["receipt"]["sha256"],
        "preservation_sha256": source["preservation"]["sha256"],
        "output_sha256": source["output"]["sha256"],
        "external_index_sha256": source["external_index_sha256"],
        "zero_result_terms": len(terms),
        "truncated": False,
    }


def _validate_static_source() -> dict:
    spec = CONFIGURATION["static_source"]
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        "static ownership source identity drifted",
    )
    source = common.load_json(path)
    publish = source["overlay_cached_height_publish"]
    _require(
        source.get("schema")
        == "abl-phase4-fmv-present-rect-height-static-ownership/1"
        and source.get("row") == CONFIGURATION["row_id"]
        and publish["helper_to_commit_call"]
        == {
            "mnemonic": "jal 0x800b6a7c",
            "pc": "0x800B6C34",
            "word": "0x0C02DA9F",
        }
        and publish["helper_argument_preservation"]["pc"] == "0x800B6C2C"
        and publish["player_boundary_base"] == "0x800CABE0"
        and publish["direct_callers"]["0x800B6A7C"]
        == [publish["helper_to_commit_call"]]
        and publish["direct_callers"]["unclassified"] == [],
        "static helper/call-instruction ownership contract drifted",
    )
    return {
        "sha256": spec["sha256"],
        "owning_helper": "0x800B6C24",
        "call_instruction": "0x800B6C34",
        "return_address": "0x800B6C3C",
        "call_instruction_word": "0x0C02DA9F",
        "player_boundary_base": publish["player_boundary_base"],
    }


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
    _require(
        len(functions) % 2 == 0
        and all(
            functions[index]["type"] == "entry"
            and functions[index + 1]["type"] == "exit"
            for index in range(0, len(functions), 2)
        ),
        "function entries and exits are not paired",
    )
    expected_identity = {
        "function": "0x800b6a7c",
        "caller": "0x800b6c34",
        "return_address": "0x800b6c3c",
    }
    _require(
        all(
            all(row.get(key, "").lower() == value for key, value in expected_identity.items())
            for row in functions
        ),
        "function trace identity or call-instruction field drifted",
    )
    pairs = [
        (functions[index], functions[index + 1])
        for index in range(0, len(functions), 2)
    ]
    _require(
        all(
            entry["arguments"] == exit_row["arguments"]
            and entry["cycle"] <= exit_row["cycle"]
            and entry["frame"] <= exit_row["frame"]
            for entry, exit_row in pairs
        ),
        "function trace pair arguments or ordering drifted",
    )
    projections = [
        {
            key: row[key]
            for key in (
                "index",
                "type",
                "function",
                "caller",
                "return_address",
                "frame",
                "cycle",
                "arguments",
                "synthetic_unwind",
            )
        }
        for row in functions
    ]
    entry_arguments = [entry["arguments"] for entry, _ in pairs]
    classes: list[dict[str, Any]] = []
    for arguments in entry_arguments:
        if any(row["arguments"] == arguments for row in classes):
            continue
        classes.append(
            {
                "arguments": arguments,
                "call_count": entry_arguments.count(arguments),
                "entry_frames": [
                    entry["frame"]
                    for entry, _ in pairs
                    if entry["arguments"] == arguments
                ],
            }
        )
    synthetic_exits = [
        exit_row["index"]
        for _, exit_row in pairs
        if exit_row.get("synthetic_unwind") is True
    ]
    return {
        "function_events": len(functions),
        "call_count": len(pairs),
        "first_retained_index": indexes[0],
        "last_retained_index": indexes[-1],
        "configured_max_events": function_max_events,
        "headroom_events": function_max_events - len(functions),
        "call_instruction": "0x800b6c34",
        "owning_helper": "0x800b6c24",
        "return_address": "0x800b6c3c",
        "argument_classes": classes,
        "synthetic_exit_indexes": synthetic_exits,
        "direct_exit_count": len(pairs) - len(synthetic_exits),
        "ordered_events": projections,
        "access_truncated": traces["access"]["truncated"],
        "execution_truncated": traces["execution"]["truncated"],
    }


def _endpoint(result: dict) -> dict:
    capture = result["capture"]
    return {
        "frame": capture["frame"],
        "cycle": capture["cycle"],
        "pc": capture["cpu"]["registers"]["registers_hex"]["pc"],
        "presentation_rect_hex_le": _memory(capture, "present_rect")["hex"],
        "cached_height_hex_le": _memory(capture, "cached_height")["hex"],
        "selected_frame_limit_hex_le": _memory(
            capture, "selected_frame_limit"
        )["hex"],
        "fmv_running_latch_hex_le": _memory(
            capture, "fmv_running_latch"
        )["hex"],
        "scene_hex_le": _memory(capture, "scene")["hex"],
    }


def build() -> dict[str, Any]:
    _validate_before_ledger()
    offline = _validate_offline_query()
    static = _validate_static_source()
    runs = {
        spec["role"]: _load_run(spec) for spec in CONFIGURATION["receipts"]
    }

    passive_jobs = runs["passive"]["jobs"]
    _require(
        passive_jobs[0]["result"]["capture"]
        == passive_jobs[1]["result"]["capture"],
        "passive same-anchor endpoints diverged",
    )
    passive_endpoint = _endpoint(passive_jobs[0]["result"])
    _require(
        passive_endpoint["frame"] == 4505
        and passive_endpoint["cycle"] == 2550166735,
        "passive finite endpoint drifted",
    )

    precise_spec = next(
        row for row in CONFIGURATION["receipts"] if row["role"] == "precise"
    )
    precise_jobs = runs["precise"]["jobs"]
    native = precise_jobs[0]["result"]
    repeat = precise_jobs[1]["result"]
    _require(
        native["staged_prelude"]["status"]
        == repeat["staged_prelude"]["status"],
        "precise staged endpoints diverged",
    )
    _require(
        native["capture"] == repeat["capture"],
        "precise ordered traces or terminal captures diverged",
    )
    native_trace = _trace_observation(
        native, precise_spec["function_max_events"]
    )
    repeat_trace = _trace_observation(
        repeat, precise_spec["function_max_events"]
    )
    _require(
        native_trace == repeat_trace,
        "precise trace projections diverged",
    )
    precise_endpoint = _endpoint(native)
    _require(
        precise_endpoint
        == {
            "frame": 4495,
            "cycle": 2544504697,
            "pc": "0x800b98e8",
            "presentation_rect_hex_le": "0000380018008000",
            "cached_height_hex_le": "80000000",
            "selected_frame_limit_hex_le": "8201",
            "fmv_running_latch_hex_le": "00000000",
            "scene_hex_le": "01000000",
        },
        "precise terminal interface drifted",
    )
    _require(
        native_trace["call_count"] == 11
        and native_trace["function_events"] == 22
        and native_trace["headroom_events"] == 10
        and native_trace["synthetic_exit_indexes"] == [2]
        and [row["call_count"] for row in native_trace["argument_classes"]]
        == [1, 1, 9],
        "retained cardinality falsifier no longer holds",
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
            "Generated from one closed offline receipt and two closed, "
            "hash-pinned investigator receipts. It banks a bounded "
            "falsification and promotes no roadmap dimension."
        ),
        "schema": (
            "abl-phase4-fmv-present-rect-height-function-trace-result/1"
        ),
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
            "offline_query": offline,
            "static_source": CONFIGURATION["static_source"],
            "receipts": receipt_rows,
        },
        "static_join": static,
        "observation": {
            "offline": offline,
            "passive": {
                "repeat_equal": True,
                "endpoint": passive_endpoint,
            },
            "precise": {
                "repeat_equal": True,
                "endpoint": precise_endpoint,
                "native": native_trace,
                "repeat": repeat_trace,
            },
        },
        "falsifier": {
            "claim": (
                "Both native branches must retain exactly three balanced "
                "calls (six events) of 0x800B6A7C from the helper named "
                "0x800B6C24, with equal unsaturated traces and endpoints."
            ),
            "outcome": "falsified",
            "reasons": [
                "observed_call_count_11_not_predicted_3",
                "function_trace_caller_is_call_instruction_0x800B6C34",
                "first_exit_is_observer_synthetic_unwind",
            ],
            "evidence": {
                "predicted_calls": 3,
                "observed_calls_per_branch": 11,
                "predicted_function_events": 6,
                "observed_function_events_per_branch": 22,
                "configured_max_events": 32,
                "headroom_events_per_branch": 10,
                "call_instruction": "0x800b6c34",
                "owning_helper": "0x800b6c24",
                "synthetic_exit_indexes": [2],
                "argument_class_call_counts": [1, 1, 9],
                "precise_repeat_equal": True,
                "passive_repeat_equal": True,
                "truncated": False,
                "owned_pids_stopped": 2,
            },
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "record_counts": {
            "offline_queries": 1,
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 1060,
            "observer_frames": 440,
            "function_events": 44,
            "observed_calls": 22,
            "investigator_live_receipts": 2,
            "promotion_admissible_live_receipts": 0,
            "owned_pids_stopped": 2,
            "promoted_dimensions": 0,
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
        "phase4 FMV presentation-RECT function trace result: PASS "
        "(11 calls; predicted-three falsified; 0 lifecycle promotions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
