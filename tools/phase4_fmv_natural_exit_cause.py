#!/usr/bin/env python3
"""Validate and summarize the external E15 selected-limit completion receipt."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import yaml

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_natural_exit_cause.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_natural_exit_cause.json"
BATCH_PLAN = common.ROOT / "config/phase4_fmv_natural_exit_cause_batch.yaml"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
EXTERNAL_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()

SHARED_INITIALIZATION = [
    {
        "type": "entry", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515397349,
        "synthetic_unwind": False,
    },
    {
        "type": "exit", "function": "0x8007094c", "caller": "0x8006d3bc",
        "return_address": "0x8006d3c4", "frame": 4443, "cycle": 2515399779,
        "synthetic_unwind": False,
    },
]
EXIT_SHAPE = [
    {"type": "entry", "function": "0x8007094c", "caller": "0x800b749c",
     "return_address": "0x800b74a4"},
    {"type": "exit", "function": "0x8007094c", "caller": "0x800b749c",
     "return_address": "0x800b74a4"},
    {"type": "entry", "function": "0x800709ac", "caller": "0x800b74a4",
     "return_address": "0x800b74ac"},
    {"type": "exit", "function": "0x800709ac", "caller": "0x800b74a4",
     "return_address": "0x800b74ac"},
]


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def render(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def canonical_plan_sha256(plan: dict) -> str:
    payload = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _subset(observed: dict, expected: dict) -> bool:
    return all(observed.get(key) == value for key, value in expected.items())


def _memory(job: dict) -> dict[str, dict]:
    rows = job["result"]["capture"]["memory"]
    mapped = {row["label"]: row for row in rows}
    _require(len(mapped) == len(rows) == 8, "atomic memory capture shape drifted")
    return mapped


def _little(row: dict) -> int:
    return int.from_bytes(bytes.fromhex(row["hex"]), "little")


def validate_plan() -> dict:
    plan = yaml.safe_load(BATCH_PLAN.read_text())
    expected = CONFIGURATION["batch_plan"]
    _require(BATCH_PLAN.relative_to(common.ROOT).as_posix() == expected["path"] and
             canonical_plan_sha256(plan) == expected["canonical_sha256"],
             "executed batch plan canonical hash drifted")
    _require(plan.get("campaign_id") == "fmv_playback" and
             plan.get("row_ids") == ["E15_fmv"] and
             plan.get("escalation_ids") == [CONFIGURATION["escalation_id"]],
             "batch plan selection drifted")
    _require([row.get("id") for row in plan.get("jobs") or []] ==
             ["start_skip_positive", "natural_no_input_control"] and
             len(plan.get("control_pairs") or []) == 1,
             "batch plan control shape drifted")
    expected_methods = [
        "functionTrace.start", "accessLog.addWatch", "accessLog.addWatch",
        "accessLog.addWatch", "accessLog.addWatch"]
    for job in plan["jobs"]:
        _require(job.get("auto_select_disc") is False and
                 job.get("run", {}).get("frames") == CONFIGURATION["run"]["frames"],
                 "batch plan shared execution bound drifted")
        _require([row.get("method") for row in job.get("instrumentation") or []] ==
                 expected_methods, "batch plan instrumentation drifted")
        _require(job.get("capture", {}).get("trace_limit") ==
                 CONFIGURATION["run"]["atomic_trace_limit"],
                 "batch plan atomic trace limit drifted")
    return plan


def validate_external_fixtures() -> dict:
    fixture = CONFIGURATION["fixture"]
    rows = {}
    for kind in ("movie", "state"):
        path = OPERATOR_ROOT / fixture[f"{kind}_path"]
        _require(path.is_file() and
                 common.sha256(path) == fixture[f"{kind}_sha256"],
                 f"E15 {kind} fixture identity drifted")
        rows[kind] = {
            "path": fixture[f"{kind}_path"],
            "sha256": fixture[f"{kind}_sha256"],
            "bytes": path.stat().st_size,
            "media_class": "pristine_serial" if kind == "movie" else "pristine",
        }
    _require(rows["state"]["bytes"] == fixture["state_bytes"],
             "E15 state fixture size drifted")
    return rows


def validate_cleanup_receipt() -> tuple[Path, dict]:
    spec = CONFIGURATION["cleanup_receipt"]
    path = EXTERNAL_ROOT / spec["relative_path"]
    _require(path.is_file() and path.stat().st_size == spec["bytes"] and
             common.sha256(path) == spec["sha256"],
             "owned-PID cleanup receipt identity drifted")
    receipt = common.load_json(path)
    profile = CONFIGURATION["profile"]
    _require(receipt.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
             receipt.get("config_dir") == profile["config_dir"] and
             receipt.get("owned_pid") == profile["owned_pid"] and
             receipt.get("instance_pid_absent_after_stop") is True and
             receipt.get("owned_pid_alive_after_stop") is False and
             receipt.get("credentials_retained") is False and
             receipt.get("runtime_executable_sha256") ==
             CONFIGURATION["debugger"]["binary_sha256"],
             "owned-PID cleanup receipt payload drifted")
    return path, receipt


def _validate_functions(job_id: str, events: list[dict]) -> dict:
    key = "start_exit" if job_id == "start_skip_positive" else "natural_exit"
    expected = CONFIGURATION["expected"][key]
    _require(len(events) == 6 and
             all(_subset(row, wanted)
                 for row, wanted in zip(events[:2], SHARED_INITIALIZATION)),
             f"{job_id}: initialization or function-event shape drifted")
    exit_events = events[2:]
    _require(all(_subset(row, wanted)
                 for row, wanted in zip(exit_events, EXIT_SHAPE)) and
             [row["frame"] for row in exit_events] == [expected["frame"]] * 4 and
             [row["cycle"] for row in exit_events] == expected["cycles"] and
             exit_events[-1]["synthetic_unwind"] is
             expected["teardown_exit_synthetic_unwind"],
             f"{job_id}: common-exit sequence drifted")
    return {
        "frame": expected["frame"],
        "st_clear_ring": {
            "address": exit_events[0]["function"],
            "caller": exit_events[0]["caller"],
            "return_address": exit_events[0]["return_address"],
            "entry_cycle": exit_events[0]["cycle"],
            "exit_cycle": exit_events[1]["cycle"],
        },
        "callback_teardown": {
            "address": exit_events[2]["function"],
            "caller": exit_events[2]["caller"],
            "return_address": exit_events[2]["return_address"],
            "entry_cycle": exit_events[2]["cycle"],
            "exit_cycle": exit_events[3]["cycle"],
            "exit_is_synthetic_unwind": exit_events[3]["synthetic_unwind"],
        },
    }


def _event_projection(row: dict) -> dict:
    return {
        "frame": row["frame"],
        "cycle": row["cycle"],
        "instruction_pc": row["instruction_pc"],
        "old_value": row["value"],
        "new_value": row["new_value"],
    }


def _watch_map(access: dict) -> dict[str, dict]:
    rows = {row["label"]: row for row in access.get("watches") or []}
    _require(set(rows) == {
        "completion_request", "selected_frame_limit", "late_str_backloc",
        "decode_stop_latch"}, "access watch shape drifted")
    return rows


def _events_for(access: dict, watch: dict) -> list[dict]:
    return [row for row in access.get("events") or []
            if row.get("watch_id") == watch["watch_id"]]


def validate_natural_access(job: dict) -> dict:
    access = job["result"]["capture"]["traces"]["access"]
    _require(access.get("truncated") is False and access.get("total") == 7 and
             len(access.get("events") or []) == 7,
             "natural access provenance truncated or count drifted")
    watches = _watch_map(access)
    selected = _events_for(access, watches["selected_frame_limit"])
    completion = _events_for(access, watches["completion_request"])
    backloc = _events_for(access, watches["late_str_backloc"])
    stop = _events_for(access, watches["decode_stop_latch"])
    expected = CONFIGURATION["expected"]
    _require(len(selected) == 1 and
             _event_projection(selected[0]) == expected["selected_frame_limit"],
             "selected-limit writer provenance drifted")
    _require(len(completion) == 2 and
             _event_projection(completion[0]) == expected["completion_clear"],
             "completion-request clear provenance drifted")
    completion_set = {**_event_projection(completion[1]),
                      "instruction": completion[1]["instruction"]}
    _require(completion_set == expected["completion_set"],
             "completion-request set writer provenance drifted")
    _require([_event_projection(row) for row in backloc] ==
             expected["late_backloc"], "late STR-backloc provenance drifted")
    _require(watches["decode_stop_latch"]["hit_count"] == 0 and stop == [],
             "decoded-record stop latch was written on the natural path")
    _require(backloc[1]["new_value"] ==
             selected[0]["new_value"] - 2 and
             completion[1]["cycle"] > backloc[-1]["cycle"],
             "selected-limit ordering relation drifted")
    return {
        "access_event_count": len(access["events"]),
        "access_ring_truncated": False,
        "selected_frame_limit_write": _event_projection(selected[0]),
        "completion_clear": _event_projection(completion[0]),
        "late_backloc_writes": [_event_projection(row) for row in backloc],
        "completion_set": completion_set,
        "stop_latch_write_count": 0,
        "limit_minus_two_reached_before_completion": True,
    }


def validate_receipt(document: dict, *, verify_identity: bool = True,
                     path: Path | None = None) -> dict:
    spec = CONFIGURATION["external_receipt"]
    if verify_identity:
        _require(path is not None and path.is_file() and
                 path.stat().st_size == spec["bytes"] and
                 common.sha256(path) == spec["sha256"],
                 "selected-limit receipt identity drifted")
    _require(document.get("schema") == "abl-phase4-duckstation-batch-result/1" and
             document.get("plan_sha256") ==
             CONFIGURATION["batch_plan"]["canonical_sha256"],
             "selected-limit receipt plan identity drifted")
    debugger = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(document.get("generator_sha256") == debugger["batch_generator_sha256"] and
             document.get("client_sha256") == debugger["client_sha256"] and
             capabilities.get("api", {}).get("version") == debugger["api_version"] and
             capabilities.get("api", {}).get("schema_version") ==
             debugger["schema_version"] and
             capabilities.get("binary", {}).get("sha256") ==
             debugger["binary_sha256"] and
             capabilities.get("source", {}).get("revision") ==
             debugger["source_revision"] and
             capabilities.get("source", {}).get("dirty_state_hash") ==
             debugger["source_dirty_state_hash"],
             "debugger capability identity drifted")
    _require({"debugger.capabilities", "scenario.runBatch",
              "scenario.loadStateAndRun", "provenanceLog.start",
              "capture.atomic"} <= set(capabilities.get("required_methods") or []),
             "required debugger surface drifted")
    media = CONFIGURATION["media"]
    mounted = document.get("mounted_media") or {}
    _require(mounted.get("game_serial") == media["serial"] and
             Path(str(mounted.get("path") or "")).name ==
             "Disney-Pixar A Bug's Life (v1.0).cue",
             "mounted media identity drifted")
    inspections = document.get("state_inspections") or []
    state_info = (inspections[0].get("state_info") or {}) if len(inspections) == 1 else {}
    _require(state_info.get("valid") is True and
             state_info.get("serial") == media["serial"] and
             state_info.get("file_size") == CONFIGURATION["fixture"]["state_bytes"],
             "inspected state identity drifted")
    result = document.get("result") or {}
    _require(result.get("state") == "completed" and
             result.get("total_jobs") == result.get("processed_jobs") ==
             result.get("succeeded_jobs") == 2 and
             result.get("failed_jobs") == 0,
             "atomic batch completion drifted")
    jobs = {row["id"]: row for row in result.get("jobs") or []}
    _require(set(jobs) == {"start_skip_positive", "natural_no_input_control"},
             "selected-limit control jobs drifted")
    summaries = {}
    for job_id, job in jobs.items():
        payload = job.get("result") or {}
        capture = payload.get("capture") or {}
        run = CONFIGURATION["run"]
        _require(job.get("state") == "completed" and job.get("attempts") == 1 and
                 job.get("recipe") == "loadStateAndRun" and
                 payload.get("run", {}).get("frames_advanced") == run["frames"] and
                 capture.get("frame") == run["endpoint_emulator_frame"] and
                 capture.get("cycle") == run["endpoint_cycle"] and
                 capture.get("trigger") == run["trigger"] and
                 capture.get("atomic") is True,
                 f"{job_id}: execution bound drifted")
        _require(payload.get("media_verified") is True and
                 payload.get("media", {}).get("sha256") == media["cue_sha256"] and
                 payload.get("media", {}).get("game_serial") == media["serial"],
                 f"{job_id}: post-load media proof drifted")
        functions = capture.get("traces", {}).get("functions") or []
        summaries[job_id] = {
            "common_exit": _validate_functions(job_id, functions),
            "function_event_count": len(functions),
        }
    natural = jobs["natural_no_input_control"]
    memory = _memory(natural)
    endpoint = CONFIGURATION["expected"]["natural_endpoint"]
    head_sha = hashlib.sha256(
        bytes.fromhex(memory["fmv_bin_head"]["hex"])).hexdigest()
    _require(head_sha == endpoint["fmv_bin_head_sha256"] and
             _little(memory["decode_stop_latch"]) == endpoint["decode_stop_latch"] and
             _little(memory["completion_request"]) == endpoint["completion_request"] and
             _little(memory["selected_frame_limit"]) ==
             endpoint["selected_frame_limit"] and
             _little(memory["str_backloc"]) == endpoint["str_backloc"],
             "natural resident endpoint state drifted")
    summaries["natural_no_input_control"]["cause"] = validate_natural_access(natural)
    summaries["natural_no_input_control"]["endpoint"] = {
        "fmv_bin_resident": True,
        "fmv_bin_head_sha256": head_sha,
        "decode_stop_latch": _little(memory["decode_stop_latch"]),
        "completion_request": _little(memory["completion_request"]),
        "selected_frame_limit": _little(memory["selected_frame_limit"]),
        "str_backloc": _little(memory["str_backloc"]),
    }
    positive_access = jobs["start_skip_positive"]["result"]["capture"]["traces"]["access"]
    _require(positive_access.get("truncated") is False,
             "Start control access provenance truncated")
    summaries["start_skip_positive"]["access_event_count"] = positive_access["total"]
    summaries["start_skip_positive"]["post_retirement_access_untyped"] = True
    return summaries


def build() -> dict:
    _require(CONFIGURATION.get("schema") ==
             "abl-phase4-fmv-natural-exit-cause-source/1",
             "selected-limit source schema drifted")
    validate_plan()
    fixtures = validate_external_fixtures()
    receipt_spec = CONFIGURATION["external_receipt"]
    receipt_path = EXTERNAL_ROOT / receipt_spec["relative_path"]
    jobs = validate_receipt(common.load_json(receipt_path), path=receipt_path)
    cleanup_path, _cleanup = validate_cleanup_receipt()
    profile = CONFIGURATION["profile"]
    _require(profile.get("owned_pid_stopped") is True,
             "isolated profile cleanup declaration drifted")
    natural = jobs["natural_no_input_control"]
    return {
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "valid": True,
        "errors": [],
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "fixtures": fixtures,
        "external_receipts": [
            {
                "absolute_path": str(receipt_path),
                "sha256": receipt_spec["sha256"],
                "bytes": receipt_spec["bytes"],
                "role": "atomic_batch_result",
                "media_class": "external game-derived evidence; never commit",
                "preservation_required": True,
            },
            {
                "absolute_path": str(cleanup_path),
                "sha256": CONFIGURATION["cleanup_receipt"]["sha256"],
                "bytes": CONFIGURATION["cleanup_receipt"]["bytes"],
                "role": "owned_pid_cleanup",
                "media_class": "external non-game cleanup evidence; never commit",
                "preservation_required": True,
            },
        ],
        "profiles": [profile],
        "observations": {
            "natural_selected_limit_completion": natural,
            "start_same_anchor_control": jobs["start_skip_positive"],
            "cause_discriminators": {
                "completion_writer": "0x800b6b48",
                "selected_limit_writer": "0x800b6dc0",
                "late_backloc_writer": "0x80070a8c",
                "stop_latch_writes_while_resident": 0,
                "frame_order_regression_writer_excluded": "0x800b6b24",
                "stream_start_clear_writer_excluded": "0x800b6dd0",
                "no_record_stop_writer_excluded": "0x800b6c84",
            },
        },
        "record_counts": {
            "atomic_batches": 1,
            "jobs": 2,
            "function_events": sum(
                row["function_event_count"] for row in jobs.values()),
            "access_events": (
                jobs["natural_no_input_control"]["cause"]["access_event_count"] +
                jobs["start_skip_positive"]["access_event_count"]),
            "resident_causal_access_events": 7,
        },
        "bounded_causal_conclusion": (
            "At the inspected pristine LEV1A anchor, the no-input path reaches "
            "backloc 384 (selected limit 386), later receives completion "
            "request 0→1 from instruction 0x800B6B48, records no decoded-record "
            "stop-latch write while FMV.BIN remains resident, and then enters "
            "the balanced common exit at frame 5305. This distinguishes the "
            "selected-limit path from the other statically known converging "
            "writers for this one run."
        ),
        "residuals": [
            "This closes one LEV1A selected-limit completion cause, not level-B, alternate, lose, advert or viewer breadth.",
            "Pause, explicit stop, repeated playback, scene unload/reload, decode timeout, CD failure and malformed-stream outcomes remain open.",
            "The Start control's access watches continue after FMV.BIN retirement; those post-retirement addresses are deliberately untyped and are not causal evidence.",
            "E12 audio, C17 viewer selection/unlocks, E14 persistence and E16 generic overlay loading retain separate interfaces.",
        ],
        "raw_external_bytes_committed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    payload = render(document)
    if args.write:
        OUTPUT.write_bytes(payload)
    if args.check and (not OUTPUT.is_file() or OUTPUT.read_bytes() != payload):
        print(f"ERROR: stale {OUTPUT.relative_to(common.ROOT)}")
        return 1
    if not args.write and not args.check:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        print("PASS: 2 E15 jobs; selected-limit completion writer is 0x800B6B48")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
