#!/usr/bin/env python3
"""Bank the falsified E15 decoded-record absence control without promotion."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

from build_identity import verify_staged_input
import phase4_common as common
import phase4_duckstation_batch as live
import phase4_fmv_interface_frontier as frontier


CONFIG_PATH = common.ROOT / "config/phase4_fmv_decoded_record_control_result.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_decoded_record_control_result.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()
FMV_REL = "FMV/FMV.BIN"
FMV_PATH = common.ROOT / "REBUILD/files" / FMV_REL


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _artifact(spec: dict, label: str) -> tuple[Path, dict]:
    path = (RUN_ROOT / spec["relative_path"]).resolve()
    _require(RUN_ROOT in path.parents, f"{label} escapes retained run root")
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_json(path)


def _run_artifact(run_root: Path, spec: dict, label: str) -> tuple[Path, dict]:
    path = (run_root / spec["relative_path"]).resolve()
    _require(run_root in path.parents, f"{label} escapes retained run root")
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_json(path)


def _plan(spec: dict) -> dict:
    path = common.ROOT / spec["plan"]["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["plan"]["sha256"],
        f"{spec['role']} plan identity drifted")
    plan = common.load_yaml(path)
    _require(
        live.validate_plan(plan, allow_executed=True) == [],
        f"{spec['role']} plan no longer validates")
    return plan


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row for row in capture.get("memory") or []
        if row.get("label") == label]
    _require(len(rows) == 1, f"capture lacks unique {label} dump")
    return rows[0]


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def validate_run(spec: dict, receipt: dict, batch: dict, raw: dict,
                 cleanup: dict, pagination: dict, command_events: dict,
                 plan: dict) -> dict:
    role = spec["role"]
    media = CONFIGURATION["media"]
    debugger = CONFIGURATION["debugger"]
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2" and
        receipt.get("complete") is True and receipt.get("errors") == [] and
        receipt.get("precise") is spec["precise"] and
        receipt.get("escalation_id") == CONFIGURATION["escalation_id"] and
        receipt.get("missing_fact_id") == CONFIGURATION["missing_fact_id"],
        f"{role} receipt closure identity drifted")
    experiment = receipt["experiment"]
    _require(
        experiment["anchor"] == {
            "kind": "movie_start_state",
            "media_sha256": media["bin_sha256"],
            "movie_sha256": media["movie_sha256"],
            "settings_sha256": media["settings_sha256"],
            "start": {"clock": "movie_frame", "value": 0},
            "state_sha256": media["state_sha256"],
        } and
        experiment["execution"]["bound"] == {
            "clock": "movie_frame", "start": 0,
            "stop": spec["replay_stop"], "stop_inclusive": False} and
        experiment["execution"]["capture_window"] == {
            "clock": "movie_frame", "start": spec["observer_start"],
            "stop": spec["replay_stop"], "stop_inclusive": False} and
        experiment["adapter_source_sha256"] ==
        debugger["adapter_sha256_at_execution"] and
        experiment["duckstation_executable_sha256"] ==
        debugger["binary_sha256"],
        f"{role} typed experiment identity drifted")
    _require(
        batch.get("schema") == "abl-phase4-duckstation-batch-result/1" and
        batch.get("row_ids") == [CONFIGURATION["row_id"]] and
        batch.get("escalation_ids") == [CONFIGURATION["escalation_id"]] and
        batch["result"]["state"] == "completed" and
        batch["expected_media"]["sha256"] == media["cue_sha256"] and
        batch["expected_media"]["tracks"][0]["sha256"] ==
        media["bin_sha256"] and
        batch["mounted_media"]["game_serial"] == media["serial"] and
        batch["expected_debugger"]["binary_sha256"] ==
        debugger["binary_sha256"],
        f"{role} batch/media/debugger identity drifted")
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2 and all(row["state"] == "completed" for row in jobs),
        f"{role} atomic jobs are incomplete")
    for job in jobs:
        result = job["result"]
        stage = result["staged_prelude"]
        run = result["run"]
        _require(
            stage["start_playback_index"] == 0 and
            stage["target_frame"] == stage["frames_advanced"] ==
            spec["stage_stop"] and
            stage["movie"]["playback_index"] == spec["stage_stop"] and
            stage["movie"]["truncated"] is False and
            run["start_playback_index"] == spec["stage_stop"] and
            run["target_frame"] == spec["replay_stop"] and
            run["frames_advanced"] ==
            spec["replay_stop"] - spec["stage_stop"] and
            result["capture"]["movie"]["truncated"] is False,
            f"{role} staged playback span drifted")
    expected_replay_frames = 2 * spec["replay_stop"]
    expected_observer_frames = 2 * (
        spec["replay_stop"] - spec["observer_start"])
    _require(
        raw.get("schema") == "abl-phase4-live-raw-results/1" and
        raw.get("complete") is True and raw.get("errors") == [] and
        raw["counters"]["atomic_jobs"] == 2 and
        raw["counters"]["launches"] == 1 and
        raw["counters"]["replay_frames"] == expected_replay_frames and
        raw["counters"]["observer_frames"] == expected_observer_frames and
        all(
            row["replay_start"] == 0 and
            row["replay_stop"] == spec["replay_stop"] and
            row["observer_start"] == spec["observer_start"] and
            row["observer_stop"] == spec["replay_stop"] and
            row["status"] == "completed"
            for row in raw["results"]),
        f"{role} raw counters drifted")
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        cleanup.get("complete") is True and cleanup.get("errors") == [] and
        cleanup.get("owned_pid_stopped") is True and
        str(cleanup.get("config_dir") or "").startswith("/var/tmp/") and
        [row.get("kind") for row in cleanup.get("actions") or []] == [
            "stop_owned_pid", "confirm_pid_stopped"],
        f"{role} owned-PID cleanup drifted")
    _require(
        pagination.get("schema") == "abl-phase4-live-pagination/1" and
        pagination.get("complete") is True and pagination.get("errors") == [] and
        pagination.get("pages_complete") is True and
        pagination.get("truncated") is False,
        f"{role} pagination drifted")
    _require(
        command_events.get("schema") ==
        "abl-phase4-live-command-events/1" and
        command_events.get("complete") is True and
        command_events.get("errors") == [] and
        [row.get("method") for row in command_events.get("events") or []] == [
            "debugger.capabilities", "debugger.status",
            "emulator.getMediaInfo", "scenario.runBatch",
            "scenario.getBatch", "scenario.getBatch"],
        f"{role} command stream drifted")
    for key in ("raw_results", "owned_pid_cleanup", "pagination",
                "command_events"):
        config_key = {
            "owned_pid_cleanup": "cleanup",
        }.get(key, key)
        _require(
            receipt["evidence"][key]["sha256"] ==
            spec[config_key]["sha256"],
            f"{role} receipt evidence join drifted for {key}")
    if spec["precise"]:
        _require(
            receipt["prelude_receipt"]["sha256"] ==
            next(
                row["receipt"]["sha256"]
                for row in CONFIGURATION["receipts"]
                if not row["precise"]),
            "precise receipt lost its passive-prelude join")
    return {
        "role": role,
        "precise": spec["precise"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "raw_results_sha256": spec["raw_results"]["sha256"],
        "cleanup_sha256": spec["cleanup"]["sha256"],
        "pagination_sha256": spec["pagination"]["sha256"],
        "command_events_sha256": spec["command_events"]["sha256"],
        "stage_start": 0,
        "stage_stop": spec["stage_stop"],
        "observer_start": spec["observer_start"],
        "replay_stop": spec["replay_stop"],
        "jobs": jobs,
    }


def _positive_observation(result: dict) -> dict:
    _require(
        result["after_load"] == {
            "address": "0x800b6c40",
            "after": "0x1000000e",
            "before": "0x1220000e",
            "code_invalidated": True,
            "kind": "code_write",
            "original_word": "0x1220000e",
            "replacement_word": "0x1000000e",
            "written": 4,
        },
        "positive after-load write/readback drifted")
    access = result["capture"]["traces"]["access"]
    _require(
        access["total"] == 1 and access["truncated"] is False and
        len(access["events"]) == 1,
        "positive latch access cardinality drifted")
    event = access["events"][0]
    expected = {
        "address": "0x800b9a54",
        "cycle": 150531213774,
        "frame": 265861,
        "instruction": "sb v0, -0x65ac(at)",
        "instruction_pc": "0x800b6c84",
        "instruction_word": "0xa0229a54",
        "new_value": 1,
        "pc": "0x800b6c88",
        "reported_pc": "0x800b6c88",
        "type": "write",
        "value": 0,
        "width": 1,
    }
    _require(
        {key: event[key] for key in expected} == expected,
        "positive instruction-attributed latch write drifted")
    functions = result["capture"]["traces"]["functions"]
    expected_order = [
        ("entry", "0x800b6c24", "0x800b7280", 1),
        ("exit", "0x800b6c24", "0x800b7280", 2),
        ("entry", "0x8007094c", "0x800b749c", 3),
        ("exit", "0x8007094c", "0x800b749c", 4),
        ("entry", "0x800709ac", "0x800b74a4", 5),
        ("exit", "0x800709ac", "0x800b74a4", 6),
    ]
    observed_order = [
        (row["type"], row["function"], row["caller"], row["index"])
        for row in functions]
    _require(
        observed_order == expected_order and
        all(row["frame"] == 265861 for row in functions),
        "positive ordered decode/teardown trace drifted")
    return {
        "predicate_write": result["after_load"],
        "latch_write": expected,
        "ordered_functions": observed_order,
        "latch_endpoint": _memory(
            result["capture"], "decode_stop_latch")["hex"],
    }


def _negative_saturation(result: dict, max_events: int) -> dict:
    _require(result.get("after_load") is None, "negative gained a perturbation")
    access = result["capture"]["traces"]["access"]
    _require(
        access["events"] == [] and access["total"] == 0 and
        access["truncated"] is False,
        "negative latch access exclusion drifted")
    functions = result["capture"]["traces"]["functions"]
    indexes = [row["index"] for row in functions]
    _require(
        len(functions) == max_events and indexes == list(range(27, 91)),
        "negative function-trace saturation signature drifted")
    _require(
        all(
            row["function"] == "0x800b6c24" and
            row["type"] == ("entry" if row["index"] % 2 else "exit")
            for row in functions),
        "negative retained function-trace suffix drifted")
    return {
        "access_events": 0,
        "access_truncated": False,
        "configured_max_events": max_events,
        "retained_events": len(functions),
        "first_retained_index": indexes[0],
        "last_retained_index": indexes[-1],
        "discarded_prefix_events": indexes[0] - 1,
        "saturated": True,
        "latch_endpoint": _memory(
            result["capture"], "decode_stop_latch")["hex"],
        "scene_endpoint": _memory(result["capture"], "scene")["hex"],
    }


def _retention_decomposition(precise_batch_sha256: str) -> dict:
    spec = CONFIGURATION["retention_query"]
    run_root = Path(spec["run_root"]).resolve()
    _receipt_path, receipt = _run_artifact(
        run_root, spec["receipt"], "retention query receipt")
    _output_path, output = _run_artifact(
        run_root, spec["output"], "retention query output")
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1" and
        receipt.get("complete") is True and receipt.get("errors") == [] and
        receipt.get("execution") == {
            "exit_code": 0,
            "stdout": "PASS: offline query\n",
            "stdout_sha256":
                "bf6d15363b59d2dd48e0d3cc4ff9a4e4577ce43de049899bcdde9416a6c6057c",
        } and
        receipt["reader"] == {
            "scope": "repo",
            "path": spec["reader"]["path"],
            "sha256": spec["reader"]["sha256"],
        } and
        receipt["outputs"] == [{
            "scope": "run",
            "path": spec["output"]["relative_path"],
            "sha256": spec["output"]["sha256"],
        }],
        "retention query receipt closure drifted")
    _require(
        receipt["external_inputs"] == [{
            "scope": "run",
            "path": (
                "iteration-1-receipts/inputs/"
                "e15-decoded-record-absence-control.batch-result.json"),
            "sha256": precise_batch_sha256,
        }],
        "retention query lost its precise batch input")
    expected = spec["successor_contract"]
    observed = output.get("observed") or {}
    contract = output.get("successor_retention_contract") or {}
    _require(
        output.get("schema") ==
        "abl-phase4-offline-function-event-retention-result/1" and
        output.get("source") == {
            "bytes": 295593,
            "sha256": precise_batch_sha256,
        } and
        observed.get("configured_max_events") ==
        expected["prior_max_events"] and
        observed.get("first_retained_index") == 27 and
        observed.get("last_retained_index") ==
        expected["observed_total_events"] and
        observed.get("discarded_prefix_events") == 26 and
        observed.get("total_emitted_events") ==
        expected["observed_total_events"] and
        observed.get("retained_function") == "0x800b6c24" and
        observed.get("retained_caller") == "0x800b7280" and
        observed.get("event_rate") == {
            "events": 90,
            "movie_frames": 200,
            "events_per_movie_frame": "0.450000",
        },
        "retention query observation drifted")
    _require(
        contract == {
            "same_anchor_window": expected["window"],
            "max_events": expected["proposed_max_events"],
            "observed_event_upper_bound": expected["observed_total_events"],
            "headroom_events": expected["actual_headroom_events"],
            "required_headroom_events": expected[
                "required_headroom_events"],
            "require_first_retained_index": expected[
                "require_first_retained_index"],
            "require_last_retained_index_lte": expected[
                "require_last_retained_index_lte"],
            "require_returned_events_lte": expected[
                "require_returned_events_lte"],
            "require_returned_events_lt_max": expected[
                "require_returned_events_lt_max"],
            "discarded_event_types_claimed": False,
            "bounded_for_same_anchor_window": True,
        },
        "successor retention contract drifted")

    fmv = FMV_PATH.read_bytes()
    verify_staged_input(FMV_REL, fmv)
    static = spec["static_callsite"]
    payload = frontier._slice(
        fmv, static["start"], static["end"],
        base=frontier.FMV_BASE, header=0)
    _require(
        hashlib.sha256(payload).hexdigest() == static["sha256"],
        "decoded-record player callsite window drifted")
    instructions = [
        frontier._instruction(
            fmv, pc, base=frontier.FMV_BASE, header=0)
        for pc in range(static["start"], static["end"], 4)
    ]
    by_pc = {row["pc"]: row for row in instructions}
    _require(
        by_pc["0x800B7280"]["mnemonic"] == "jal 0x800b6c24" and
        by_pc["0x800B728C"]["mnemonic"] == "lbu v0,-26028(v0)" and
        by_pc["0x800B7294"]["mnemonic"] == "beq v0,s4,0x800b7464",
        "decoded-record helper/latch/exit callsite drifted")
    return {
        "offline_receipt_sha256": spec["receipt"]["sha256"],
        "offline_output_sha256": spec["output"]["sha256"],
        "source_batch_sha256": precise_batch_sha256,
        "static_callsite": {
            "fmv_bin_sha256": common.sha256(FMV_PATH),
            "start": f"0x{static['start']:08X}",
            "end": f"0x{static['end']:08X}",
            "sha256": static["sha256"],
            "instructions": instructions,
            "helper_call": f"0x{static['helper_call']:08X}",
            "helper_target": f"0x{static['helper_target']:08X}",
            "latch_read": f"0x{static['latch_read']:08X}",
            "exit_branch": f"0x{static['exit_branch']:08X}",
        },
        "observed_same_anchor_rate": {
            "window": expected["window"],
            "total_function_events": observed["total_emitted_events"],
            "events_per_movie_frame":
                observed["event_rate"]["events_per_movie_frame"],
            "retained_suffix_events": observed["retained_events"],
            "discarded_prefix_events":
                observed["discarded_prefix_events"],
            "discarded_event_types_claimed": False,
        },
        "successor_retention_contract": contract,
        "claim": (
            "For the identical native movie-frame 650..850 branch, the "
            "completed saturated result emitted 90 total function events. "
            "A 128-event ring has 38 events of finite headroom."),
        "falsifier": (
            "Reject the successor if its native branch does not retain "
            "contiguous indexes 1..90, emits more than 90 events, or reaches "
            "the 128-event limit."),
    }


def build() -> dict:
    _before_path, before = _artifact(
        CONFIGURATION["before_ledger"], "immutable before ledger")
    planned = [
        row for row in before.get("entries") or []
        if row.get("id") == CONFIGURATION["escalation_id"]]
    _require(
        len(planned) == 1 and planned[0].get("state") == "planned",
        "immutable before ledger lacks the unique planned escalation")
    _offline_path, offline = _artifact(
        CONFIGURATION["offline_receipt"], "offline query receipt")
    _require(
        offline.get("schema") == "abl-phase4-offline-query/1" and
        offline.get("complete") is True and offline.get("errors") == [] and
        offline["execution"]["exit_code"] == 0,
        "offline receipt is not closed")

    runs = []
    for spec in CONFIGURATION["receipts"]:
        _receipt_path, receipt = _artifact(
            spec["receipt"], f"{spec['role']} receipt")
        _batch_path, batch = _artifact(
            spec["batch_result"], f"{spec['role']} batch")
        _raw_path, raw = _artifact(
            spec["raw_results"], f"{spec['role']} raw result")
        _cleanup_path, cleanup = _artifact(
            spec["cleanup"], f"{spec['role']} cleanup")
        _pagination_path, pagination = _artifact(
            spec["pagination"], f"{spec['role']} pagination")
        _events_path, events = _artifact(
            spec["command_events"], f"{spec['role']} command events")
        runs.append(validate_run(
            spec, receipt, batch, raw, cleanup, pagination, events,
            _plan(spec)))

    passive = next(row for row in runs if row["role"] == "passive")
    precise = next(row for row in runs if row["role"] == "precise")
    passive_jobs = passive.pop("jobs")
    precise_jobs = precise.pop("jobs")
    first = passive_jobs[0]["result"]
    second = passive_jobs[1]["result"]
    _require(
        first["staged_prelude"]["status"] ==
        second["staged_prelude"]["status"] and
        first["capture"] == second["capture"],
        "passive same-anchor endpoints diverged")
    positive = _positive_observation(precise_jobs[0]["result"])
    negative = _negative_saturation(
        precise_jobs[1]["result"],
        next(
            row["function_max_events"]
            for row in CONFIGURATION["receipts"]
            if row["precise"]))
    retention = _retention_decomposition(
        next(
            row["batch_result_sha256"]
            for row in runs if row["role"] == "precise"))
    return {
        "schema": "abl-phase4-fmv-decoded-record-control-result/1",
        "generated": _stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "missing_fact_id": CONFIGURATION["missing_fact_id"],
        "before_ledger_sha256": CONFIGURATION["before_ledger"]["sha256"],
        "offline_receipt_sha256": CONFIGURATION["offline_receipt"]["sha256"],
        "retention_decomposition": retention,
        "receipts": runs,
        "observation": {
            "passive_repeat_equal": True,
            "positive": positive,
            "negative": negative,
        },
        "falsifier": {
            "predicate": (
                "any planned observer truncation or saturation rejects the "
                "positive/negative control as lifecycle evidence"),
            "outcome": "falsified",
            "reason": "negative_function_trace_saturated_and_dropped_prefix",
            "evidence": {
                "configured_max_events": negative["configured_max_events"],
                "retained_events": negative["retained_events"],
                "first_retained_index": negative["first_retained_index"],
                "last_retained_index": negative["last_retained_index"],
                "discarded_prefix_events":
                    negative["discarded_prefix_events"],
            },
        },
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 3500,
            "observer_frames": 902,
            "exact_after_load_writes": 1,
            "positive_latch_writes": 1,
            "negative_latch_writes": 0,
            "negative_retained_function_events": 64,
            "negative_discarded_function_events": 26,
            "owned_pids_stopped": 2,
            "promotion_admissible_live_receipts": 0,
        },
        "claim_boundary": CONFIGURATION["claim_boundary"],
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
            "tools/phase4_fmv_decoded_record_control_result.py":
                common.sha256(Path(__file__)),
            "tools/phase4_duckstation_batch.py":
                common.sha256(common.ROOT /
                              "tools/phase4_duckstation_batch.py"),
            "tools/phase4_offline_receipt_query.py":
                common.sha256(common.ROOT /
                              "tools/phase4_offline_receipt_query.py"),
            f"REBUILD/files/{FMV_REL}": common.sha256(FMV_PATH),
        },
        "raw_external_bytes_committed": False,
        "valid": True,
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 decoded-record control result is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: decoded-record positive retained; native function trace "
        "saturated 64/64 with 26 dropped; no dimension promoted",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
