#!/usr/bin/env python3
"""Bank the saturated E15 presentation-RECT height writer control."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
from pathlib import Path
from typing import Any

import phase4_common as common
import phase4_fmv_cd_event_exit_result as receipt_validation


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_present_rect_height_writer_result.yaml"
)
OUTPUT = (
    common.ROOT / "analysis/phase4_fmv_present_rect_height_writer_result.json"
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


def _endpoint(capture: dict) -> dict:
    present = _memory(capture, "present_rect")
    limit = _memory(capture, "selected_frame_limit")
    latch = _memory(capture, "fmv_running_latch")
    scene = _memory(capture, "scene")
    _require(
        present["hex"] == "0000380018008000"
        and limit["hex"] == "8201"
        and latch["hex"] == "00000000"
        and scene["hex"] == "01000000",
        "terminal RECT/lifecycle endpoint drifted",
    )
    return {
        "emulator_frame": capture["frame"],
        "cycle": capture["cycle"],
        "pc": capture["cpu"]["registers"]["registers_hex"]["pc"],
        "present_rect_hex_le": present["hex"],
        "present_rect_height": int.from_bytes(
            bytes.fromhex(present["hex"])[6:8], "little", signed=True
        ),
        "selected_frame_limit": int.from_bytes(
            bytes.fromhex(limit["hex"]), "little", signed=True
        ),
        "fmv_running_latch": int.from_bytes(
            bytes.fromhex(latch["hex"]), "little"
        ),
        "scene": int.from_bytes(bytes.fromhex(scene["hex"]), "little"),
    }


def _normalized_event(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "watch_id"}


def _trace_observation(result: dict, max_events: int) -> dict:
    _require(
        result.get("after_load") is None,
        "native writer control unexpectedly perturbed guest state",
    )
    access = result["capture"]["traces"]["access"]
    watches = access.get("watches") or []
    events = access.get("events") or []
    _require(
        len(watches) == 1
        and watches[0]["address"].lower() == "0x800cac0a"
        and watches[0]["length"] == 2
        and watches[0]["type"] == "write"
        and watches[0]["stop_on_hit"] is False
        and watches[0]["max_events"] == max_events,
        "presentation-RECT write-watch contract drifted",
    )
    _require(
        access["truncated"] is False
        and access["total"] == len(events)
        and watches[0]["hit_count"] == len(events),
        "access event totals/truncation drifted",
    )
    _require(
        len(events) == max_events,
        "predeclared access-capacity saturation falsifier no longer holds",
    )
    for event in events:
        _require(
            event["address"].lower() == "0x800cac0a"
            and event["type"] == "write"
            and event["width"] == 2
            and isinstance(event.get("value"), int)
            and isinstance(event.get("new_value"), int)
            and event.get("instruction_pc")
            and event.get("instruction_word"),
            "typed halfword writer event drifted",
        )
    _require(
        events[0]["instruction_pc"].lower() == "0x800b6f18"
        and events[0]["instruction_word"].lower() == "0xa430ac0a"
        and events[0]["value"] == 0
        and events[0]["new_value"] == 240,
        "static 240 initializer event drifted",
    )
    transitions = [
        row for row in events if row["value"] == 240 and row["new_value"] == 128
    ]
    _require(
        len(transitions) == 1
        and transitions[0]["instruction_pc"].lower() == "0x800b6bf0"
        and transitions[0]["instruction_word"].lower() == "0xa624002a"
        and transitions[0]["frame"] == 4452
        and transitions[0]["cycle"] == 2520652688,
        "first retained 240-to-128 writer drifted",
    )
    counts = Counter(row["instruction_pc"].lower() for row in events)
    _require(
        counts
        == Counter(
            {
                "0x800b6f18": 1,
                "0x800b6bf0": 3,
                "0x80064178": 28,
            }
        ),
        "retained writer-PC census drifted",
    )
    return {
        "returned_events": len(events),
        "configured_max_events": max_events,
        "capacity_headroom": max_events - len(events),
        "trace_truncated": access["truncated"],
        "writer_pc_counts": dict(sorted(counts.items())),
        "static_initializer": _normalized_event(events[0]),
        "first_240_to_128_writer": _normalized_event(transitions[0]),
        "last_retained_event": _normalized_event(events[-1]),
        "normalized_events": [_normalized_event(row) for row in events],
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
    _require(
        "saturation falsifies this CPU-owner hypothesis"
        in rows[0].get("hypothesis", ""),
        "immutable before-ledger lost the saturation falsifier",
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
    runtime = source["runtime_writer_frontier"]
    typed = source["typed_reclassification"]
    _require(
        source.get("schema")
        == "abl-phase4-fmv-file-open-divergence-ownership/1"
        and source.get("row") == CONFIGURATION["row_id"]
        and runtime["native_height_128_writer_attributed"] is False
        and runtime["classified_direct_height_writers"] == ["0x800B6F18"]
        and typed["captured_range"]["start"] == "0x800CAC08"
        and typed["captured_range"]["end"] == "0x800CAC0C"
        and typed["static_initializer"]["height_constant"] == 240
        and typed["static_initializer"]["height_store"] == "0x800B6F18"
        and source["claim_boundary"]["runtime_writer_closed"] is False,
        "static presentation-RECT ownership contract drifted",
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
    return receipt_validation.validate_run(
        spec,
        receipt,
        batch,
        raw,
        cleanup,
        pagination,
        events,
        _plan(spec),
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
    passive_endpoint = _endpoint(passive_jobs[0]["result"]["capture"])

    precise_spec = next(
        row for row in CONFIGURATION["receipts"] if row["role"] == "precise"
    )
    precise_jobs = runs["precise"]["jobs"]
    native_result = precise_jobs[0]["result"]
    repeat_result = precise_jobs[1]["result"]
    _require(
        native_result["staged_prelude"]["status"]
        == repeat_result["staged_prelude"]["status"],
        "precise staged endpoints diverged",
    )
    native_endpoint = _endpoint(native_result["capture"])
    repeat_endpoint = _endpoint(repeat_result["capture"])
    _require(
        native_endpoint == repeat_endpoint,
        "precise terminal RECT/lifecycle endpoints diverged",
    )
    native_trace = _trace_observation(
        native_result, precise_spec["access_max_events"]
    )
    repeat_trace = _trace_observation(
        repeat_result, precise_spec["access_max_events"]
    )
    _require(
        native_trace["normalized_events"] == repeat_trace["normalized_events"],
        "precise ordered writer sequences diverged",
    )
    for row in (native_trace, repeat_trace):
        row.pop("normalized_events")

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
            "The repeated 240-to-128 CPU event is a bounded lead only because "
            "both traces reached the configured event capacity."
        ),
        "schema": "abl-phase4-fmv-present-rect-height-writer-result/1",
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
                "endpoint": passive_endpoint,
            },
            "precise": {
                "ordered_events_repeat_equal": True,
                "endpoint_repeat_equal": True,
                "native": {
                    "endpoint": native_endpoint,
                    **native_trace,
                },
                "repeat": {
                    "endpoint": repeat_endpoint,
                    **repeat_trace,
                },
            },
        },
        "falsifier": {
            "claim": (
                "Both unmodified precise jobs must retain the same ordered, "
                "unsaturated CPU writer sequence through the native height-128 "
                "endpoint; reaching the configured capacity falsifies it."
            ),
            "outcome": "falsified",
            "reason": "returned_event_count_reached_configured_bound",
            "evidence": {
                "native_returned_events": native_trace["returned_events"],
                "repeat_returned_events": repeat_trace["returned_events"],
                "configured_max_events": precise_spec["access_max_events"],
                "capacity_headroom_per_job": 0,
                "trace_truncated": False,
                "ordered_events_repeat_equal": True,
                "endpoint_repeat_equal": True,
                "first_240_to_128_writer_pc": "0x800b6bf0",
                "owned_pids_stopped": 2,
            },
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 1060,
            "observer_frames": 440,
            "access_events": 64,
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
        "phase4 FMV presentation-RECT writer result: PASS "
        "(32/32 saturation falsifier; 0 lifecycle promotions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
