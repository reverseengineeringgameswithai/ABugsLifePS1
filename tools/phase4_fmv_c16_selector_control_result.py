#!/usr/bin/env python3
"""Bank the failed unstaged and intrinsically valid staged C16 controls."""
from __future__ import annotations

import argparse
import copy
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import phase4_common as common
import phase4_duckstation_batch as live


CONFIG_PATH = (
    common.ROOT / "config/phase4_fmv_c16_selector_control_result.yaml")
OUTPUT = common.ROOT / "analysis/phase4_fmv_c16_selector_control_result.json"
LEGACY_INDEX = common.ROOT / "analysis/phase4_method_legacy_live_index.json"
METHOD_VALIDATOR = common.ROOT / "tools/phase4_method_metrics.py"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIGURATION["run_root"]).resolve()
STAGING_ERROR = (
    "nonzero movie-frame capture requires one atomic staged_prelude")


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


def _artifact_at(run_root: Path, spec: dict, label: str) -> tuple[Path, dict]:
    path = (run_root / spec["relative_path"]).resolve()
    _require(run_root in path.parents, f"{label} escapes retained run root")
    _require(
        path.is_file() and path.stat().st_size == spec["bytes"] and
        common.sha256(path) == spec["sha256"],
        f"{label} identity drifted")
    return path, common.load_json(path)


def _plan(spec: dict) -> dict:
    path = common.ROOT / spec["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["sha256"],
        "executed plan identity drifted")
    plan = common.load_yaml(path)
    errors = live.validate_plan(plan, allow_executed=True)
    _require(
        any(STAGING_ERROR in error for error in errors),
        "current adapter does not reject the unstaged movie-frame plan")
    return plan


def _memory(capture: dict, label: str) -> dict:
    rows = [
        row for row in capture.get("memory") or []
        if row.get("label") == label]
    _require(len(rows) == 1, f"capture lacks unique {label} memory dump")
    return rows[0]


def _normalized_precise_capture(capture: dict) -> dict:
    value = copy.deepcopy(capture)
    value["memory"] = [
        row for row in value.get("memory") or []
        if row.get("label") != "scene_flow_callsite"]
    for row in ((value.get("traces") or {}).get("access") or {}).get(
            "watches") or []:
        row.pop("watch_id", None)
    return value


def validate_run(spec: dict, receipt: dict, batch: dict, raw: dict,
                 cleanup: dict, plan: dict) -> dict:
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
    anchor = experiment["anchor"]
    bound = experiment["execution"]["bound"]
    _require(
        anchor["media_sha256"] == media["bin_sha256"] and
        anchor["movie_sha256"] == media["movie_sha256"] and
        anchor["state_sha256"] == media["state_sha256"] and
        anchor["start"] == {
            "clock": "movie_frame", "value": spec["typed_start"]} and
        bound == {
            "clock": "movie_frame", "start": spec["typed_start"],
            "stop": 4006, "stop_inclusive": False} and
        experiment["adapter_source_sha256"] ==
        debugger["adapter_sha256_at_execution"],
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
        run = result["run"]
        capture = result["capture"]
        _require(
            run["start_playback_index"] == 0 and
            run["target_frame"] == run["frames_advanced"] == 4006 and
            capture["movie"]["reproducible"] is True and
            capture["movie"]["truncated"] is False,
            f"{role} observed playback span drifted")
    if spec["precise"]:
        positive = jobs[0]["result"]
        negative = jobs[1]["result"]
        _require(
            positive["after_load"] == {
                "address": "0x800500d4",
                "after": "0x24040028",
                "before": "0x2404002e",
                "code_invalidated": True,
                "kind": "code_write",
                "original_word": "0x2404002e",
                "replacement_word": "0x24040028",
                "written": 4,
            } and negative.get("after_load") is None,
            "precise after-load write/readback identity drifted")
        for result in (positive, negative):
            traces = result["capture"]["traces"]
            _require(
                traces["functions"] == [] and
                traces["access"]["events"] == [] and
                traces["access"]["total"] == 0 and
                traces["execution"]["events"] == [] and
                traces["execution"]["total"] == 0,
                "unexpected lifecycle observer event appeared")
    _require(
        raw.get("schema") == "abl-phase4-live-raw-results/1" and
        raw.get("complete") is True and raw.get("errors") == [] and
        raw["counters"]["atomic_jobs"] == 2 and
        all(
            row["replay_start"] == 265211 and
            row["replay_stop"] == 269217
            for row in raw["results"]),
        f"{role} emitted raw counters drifted")
    _require(
        all(
            row["replay_start"] < bound["start"] or
            row["replay_stop"] > bound["stop"]
            for row in raw["results"]),
        f"{role} raw counter mismatch is no longer reproduced")
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        cleanup.get("complete") is True and
        cleanup.get("owned_pid_stopped") is True and
        str(cleanup.get("config_dir") or "").startswith("/var/tmp/"),
        f"{role} owned-PID cleanup drifted")
    _require(
        receipt["evidence"]["raw_results"]["sha256"] ==
        spec["raw_results"]["sha256"] and
        receipt["evidence"]["owned_pid_cleanup"]["sha256"] ==
        spec["cleanup"]["sha256"],
        f"{role} receipt evidence joins drifted")
    return {
        "role": role,
        "precise": spec["precise"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "raw_results_sha256": spec["raw_results"]["sha256"],
        "cleanup_sha256": spec["cleanup"]["sha256"],
        "typed_movie_start": spec["typed_start"],
        "observed_movie_start": 0,
        "observed_movie_stop": 4006,
        "emitted_raw_span": [265211, 269217],
        "jobs": jobs,
        "plan_guard_errors": [
            error for error in live.validate_plan(
                plan, allow_executed=True)
            if STAGING_ERROR in error],
        "receipt_admissible": False,
    }


def _staged_plan(spec: dict) -> dict:
    path = common.ROOT / spec["plan"]["path"]
    _require(
        path.is_file() and common.sha256(path) == spec["plan"]["sha256"],
        "staged plan identity drifted")
    plan = common.load_yaml(path)
    _require(
        live.validate_plan(plan, allow_executed=True) == [],
        "staged plan no longer passes the live adapter guard")
    return plan


def _first_loader_entry(result: dict) -> dict:
    rows = [
        row for row in result["capture"]["traces"]["functions"]
        if row["function"] == "0x8003e7c0" and row["type"] == "entry"]
    _require(rows, "staged trace lacks a loader entry")
    return rows[0]


def _initial_limit_write(result: dict) -> dict:
    rows = [
        row for row in result["capture"]["traces"]["access"]["events"]
        if row["address"] == "0x80131eee"]
    _require(rows, "staged trace lacks an FMV limit write")
    return rows[0]


def _instruction_pc(reported_pc: str, expected: str, label: str) -> str:
    """Separate the access callback's post-instruction PC from its writer."""
    _require(
        reported_pc.startswith("0x") and
        int(reported_pc, 16) - 4 == int(expected, 16),
        f"{label} reported/instruction PC relation drifted")
    return expected


def _method_admission(successor: dict, staged_runs: list[dict]) -> dict:
    spec = successor["method_admission"]
    validator = spec["validator"]
    legacy_spec = spec["legacy_index"]
    _require(
        validator["path"] == "tools/phase4_method_metrics.py" and
        common.sha256(METHOD_VALIDATOR) == validator["sha256"],
        "trial-pinned method validator identity drifted")
    _require(
        legacy_spec["path"] ==
        "analysis/phase4_method_legacy_live_index.json" and
        common.sha256(LEGACY_INDEX) == legacy_spec["sha256"],
        "trial-pinned legacy index identity drifted")
    legacy = common.load_json(LEGACY_INDEX)
    overlap_spec = spec["overlapping_entry"]
    overlaps = [
        row for row in legacy.get("entries") or []
        if row.get("escalation_id") == overlap_spec["escalation_id"]]
    _require(
        len(overlaps) == 1 and
        overlaps[0]["source_entry_sha256"] ==
        overlap_spec["source_entry_sha256"] and
        overlaps[0]["normalization"] == overlap_spec["normalization"] ==
        "conservative_deny" and
        overlaps[0]["target_row"] == CONFIGURATION["row_id"] and
        overlaps[0]["media_sha256"] == CONFIGURATION["media"]["bin_sha256"] and
        overlaps[0]["movie_sha256"] ==
        CONFIGURATION["media"]["movie_sha256"] and
        overlaps[0]["state_sha256"] is None,
        "conservative legacy-overlap identity drifted")
    _require(
        spec["intrinsic_v2_receipts_valid"] == len(staged_runs) == 2 and
        spec["method_trial_receipts_admissible"] == 0 and
        spec["status"] == "rejected_conservative_pre_v2_overlap",
        "method-admission disposition drifted")
    return {
        **spec,
        "receipt_sha256s": sorted(
            row["receipt_sha256"] for row in staged_runs),
    }


def _teardown_quad(result: dict) -> list[dict]:
    return [
        {
            key: row[key] for key in (
                "type", "function", "caller", "return_address",
                "frame", "synthetic_unwind")
        }
        for row in result["capture"]["traces"]["functions"]
        if (
            (row["function"], row["caller"]) in {
                ("0x8007094c", "0x800b749c"),
                ("0x800709ac", "0x800b74a4"),
            } and
            row["frame"] == min(
                event["frame"]
                for event in result["capture"]["traces"]["functions"]
                if (event["function"], event["caller"]) in {
                    ("0x8007094c", "0x800b749c"),
                    ("0x800709ac", "0x800b74a4"),
                }))
    ]


def validate_staged_run(
        configuration: dict, spec: dict, receipt: dict, batch: dict,
        raw: dict, cleanup: dict, plan: dict) -> dict:
    role = spec["role"]
    media = CONFIGURATION["media"]
    debugger = configuration["debugger"]
    stage_stop = spec["stage_stop"]
    _require(
        receipt.get("schema") == "abl-phase4-live-run-receipt/2" and
        receipt.get("complete") is True and receipt.get("errors") == [] and
        receipt.get("precise") is spec["precise"] and
        receipt.get("escalation_id") == configuration["escalation_id"] and
        receipt.get("missing_fact_id") == configuration["missing_fact_id"],
        f"{role} staged receipt closure identity drifted")
    experiment = receipt["experiment"]
    _require(
        experiment["anchor"] == {
            "kind": "movie_start_state",
            "media_sha256": media["bin_sha256"],
            "movie_sha256": media["movie_sha256"],
            "settings_sha256":
                "e030ef17c97fa30cd71d84a14ea15075a4fdb6b33e12bb439a3374066d9c08d1",
            "start": {"clock": "movie_frame", "value": 0},
            "state_sha256": media["state_sha256"],
        } and
        experiment["execution"]["bound"] == {
            "clock": "movie_frame", "start": 0, "stop": 4006,
            "stop_inclusive": False} and
        experiment["execution"]["capture_window"] == {
            "clock": "movie_frame", "start": spec["observer_start"],
            "stop": 4006, "stop_inclusive": False} and
        experiment["adapter_source_sha256"] ==
        debugger["adapter_sha256_at_execution"] and
        experiment["duckstation_executable_sha256"] ==
        debugger["binary_sha256"],
        f"{role} staged typed experiment identity drifted")
    _require(
        batch.get("schema") == "abl-phase4-duckstation-batch-result/1" and
        batch.get("row_ids") == [CONFIGURATION["row_id"]] and
        batch.get("escalation_ids") == [configuration["escalation_id"]] and
        batch["result"]["state"] == "completed" and
        batch["expected_media"]["sha256"] == media["cue_sha256"] and
        batch["expected_media"]["tracks"][0]["sha256"] ==
        media["bin_sha256"] and
        batch["mounted_media"]["game_serial"] == media["serial"] and
        batch["expected_debugger"]["binary_sha256"] ==
        debugger["binary_sha256"],
        f"{role} staged batch/media/debugger identity drifted")
    jobs = batch["result"]["jobs"]
    _require(
        len(jobs) == 2 and all(row["state"] == "completed" for row in jobs),
        f"{role} staged atomic jobs are incomplete")
    stages = []
    for job in jobs:
        result = job["result"]
        stage = result["staged_prelude"]
        run = result["run"]
        capture = result["capture"]
        stages.append(stage)
        _require(
            stage["start_playback_index"] == 0 and
            stage["target_frame"] == stage["frames_advanced"] == stage_stop and
            stage["movie"]["playback_index"] == stage_stop and
            stage["movie"]["truncated"] is False and
            run["start_playback_index"] == stage_stop and
            run["target_frame"] == 4006 and
            run["frames_advanced"] == 4006 - stage_stop and
            capture["movie"]["reproducible"] is True and
            capture["movie"]["truncated"] is False,
            f"{role} staged playback span drifted")
    _require(
        stages[0]["status"] == stages[1]["status"],
        f"{role} same-anchor staged status diverged")
    _require(
        raw.get("schema") == "abl-phase4-live-raw-results/1" and
        raw.get("complete") is True and raw.get("errors") == [] and
        raw["counters"]["atomic_jobs"] == 2 and
        raw["counters"]["launches"] == 1 and
        raw["counters"]["replay_frames"] == 8012 and
        raw["counters"]["observer_frames"] ==
        2 * (4006 - spec["observer_start"]) and
        all(
            row["replay_start"] == 0 and row["replay_stop"] == 4006 and
            row["observer_start"] == spec["observer_start"] and
            row["observer_stop"] == 4006 and row["status"] == "completed"
            for row in raw["results"]),
        f"{role} staged raw counters drifted")
    _require(
        cleanup.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        cleanup.get("complete") is True and
        cleanup.get("owned_pid_stopped") is True and
        str(cleanup.get("config_dir") or "").startswith("/var/tmp/"),
        f"{role} staged owned-PID cleanup drifted")
    _require(
        receipt["evidence"]["raw_results"]["sha256"] ==
        spec["raw_results"]["sha256"] and
        receipt["evidence"]["owned_pid_cleanup"]["sha256"] ==
        spec["cleanup"]["sha256"],
        f"{role} staged receipt evidence joins drifted")
    if spec["precise"]:
        _require(
            receipt["prelude_receipt"]["sha256"] ==
            next(
                row["receipt"]["sha256"]
                for row in configuration["receipts"]
                if not row["precise"]),
            "precise receipt lost its passive-prelude join")
        positive = jobs[0]["result"]
        negative = jobs[1]["result"]
        _require(
            positive["after_load"] == {
                "address": "0x800500d4",
                "after": "0x24040028",
                "before": "0x2404002e",
                "code_invalidated": True,
                "kind": "code_write",
                "original_word": "0x2404002e",
                "replacement_word": "0x24040028",
                "written": 4,
            } and negative.get("after_load") is None,
            "staged after-load write/readback identity drifted")
        positive_limit = _initial_limit_write(positive)
        negative_limit = _initial_limit_write(negative)
        _require(
            {
                key: positive_limit[key]
                for key in ("address", "pc", "frame", "new_value")
            } == {
                "address": "0x80131eee", "pc": "0x800b6dc4",
                "frame": 265826, "new_value": 3162,
            } and
            {
                key: negative_limit[key]
                for key in ("address", "pc", "frame", "new_value")
            } == {
                "address": "0x80131eee", "pc": "0x800b6dc4",
                "frame": 265826, "new_value": 281,
            },
            "staged selector limit interface drifted")
        negative_completion = [
            row for row in negative["capture"]["traces"]["access"]["events"]
            if row["address"] == "0x800cac10" and
            row["pc"] == "0x800b6b4c" and row["new_value"] == 1]
        positive_completion = [
            row for row in positive["capture"]["traces"]["access"]["events"]
            if row["address"] == "0x800cac10" and
            row["pc"] == "0x800b6b4c" and row["new_value"] == 1]
        _require(
            len(negative_completion) == 1 and
            negative_completion[0]["frame"] == 266492 and
            positive_completion == [],
            "bounded completion-request observation drifted")
    return {
        "role": role,
        "precise": spec["precise"],
        "receipt_sha256": spec["receipt"]["sha256"],
        "batch_result_sha256": spec["batch_result"]["sha256"],
        "raw_results_sha256": spec["raw_results"]["sha256"],
        "cleanup_sha256": spec["cleanup"]["sha256"],
        "stage_start": 0,
        "stage_stop": stage_stop,
        "observer_start": spec["observer_start"],
        "replay_stop": 4006,
        "emulator_launches": 1,
        "completed_atomic_jobs": 2,
        "intrinsic_v2_valid": True,
        "method_trial_admissible": False,
        "jobs": jobs,
    }


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def build() -> dict:
    historical_runs = []
    for spec in CONFIGURATION["receipts"]:
        _receipt_path, receipt = _artifact(
            spec["receipt"], f"{spec['role']} receipt")
        _batch_path, batch = _artifact(
            spec["batch_result"], f"{spec['role']} batch")
        _raw_path, raw = _artifact(
            spec["raw_results"], f"{spec['role']} raw result")
        _cleanup_path, cleanup = _artifact(
            spec["cleanup"], f"{spec['role']} cleanup")
        plan = _plan(spec["plan"])
        historical_runs.append(validate_run(
            spec, receipt, batch, raw, cleanup, plan))

    passive = next(
        row for row in historical_runs if row["role"] == "passive")
    precise = next(
        row for row in historical_runs if row["role"] == "precise")
    passive_jobs = passive.pop("jobs")
    precise_jobs = precise.pop("jobs")
    _require(
        passive_jobs[0]["result"]["capture"] ==
        passive_jobs[1]["result"]["capture"],
        "passive repeat endpoints diverged")
    positive = precise_jobs[0]["result"]
    negative = precise_jobs[1]["result"]
    _require(
        positive["after_load"] == {
            "address": "0x800500d4",
            "after": "0x24040028",
            "before": "0x2404002e",
            "code_invalidated": True,
            "kind": "code_write",
            "original_word": "0x2404002e",
            "replacement_word": "0x24040028",
            "written": 4,
        } and negative.get("after_load") is None,
        "precise after-load write/readback identity drifted")
    for result in (positive, negative):
        traces = result["capture"]["traces"]
        _require(
            traces["functions"] == [] and
            traces["access"]["events"] == [] and
            traces["access"]["total"] == 0 and
            traces["execution"]["events"] == [] and
            traces["execution"]["total"] == 0,
            "unexpected lifecycle observer event appeared")
    positive_callsite = _memory(
        positive["capture"], "scene_flow_callsite")["hex"]
    negative_callsite = _memory(
        negative["capture"], "scene_flow_callsite")["hex"]
    _require(
        positive_callsite == (
            negative_callsite[:96] + "28000424" + negative_callsite[104:]) and
        _normalized_precise_capture(positive["capture"]) ==
        _normalized_precise_capture(negative["capture"]),
        "precise branches differ outside the written callsite word")

    successor = CONFIGURATION["staged_successor"]
    successor_root = Path(successor["run_root"]).resolve()
    _before_path, before_ledger = _artifact_at(
        successor_root, successor["before_ledger"],
        "staged successor before-ledger")
    before_matches = [
        row for row in before_ledger.get("entries") or []
        if row.get("id") == successor["escalation_id"] and
        row.get("missing_fact_id") == successor["missing_fact_id"] and
        row.get("target_row") == CONFIGURATION["row_id"] and
        row.get("state") == "planned"]
    _require(
        len(before_matches) == 1,
        "staged successor lacks a unique immutable planned before-ledger join")
    _offline_path, offline_receipt = _artifact_at(
        successor_root, successor["offline_receipt"],
        "staged successor offline receipt")
    _require(
        offline_receipt.get("schema") == "abl-phase4-offline-query/1" and
        offline_receipt.get("complete") is True and
        offline_receipt.get("execution", {}).get("exit_code") == 0 and
        offline_receipt.get("errors") == [],
        "staged successor offline receipt is not closed")
    staged_runs = []
    for spec in successor["receipts"]:
        _receipt_path, receipt = _artifact_at(
            successor_root, spec["receipt"],
            f"{spec['role']} staged receipt")
        _batch_path, batch = _artifact_at(
            successor_root, spec["batch_result"],
            f"{spec['role']} staged batch")
        _raw_path, raw = _artifact_at(
            successor_root, spec["raw_results"],
            f"{spec['role']} staged raw result")
        _cleanup_path, cleanup = _artifact_at(
            successor_root, spec["cleanup"],
            f"{spec['role']} staged cleanup")
        plan = _staged_plan(spec)
        staged_runs.append(validate_staged_run(
            successor, spec, receipt, batch, raw, cleanup, plan))

    staged_passive = next(
        row for row in staged_runs if row["role"] == "staged_passive")
    staged_precise = next(
        row for row in staged_runs if row["role"] == "staged_precise")
    staged_passive_jobs = staged_passive.pop("jobs")
    staged_precise_jobs = staged_precise.pop("jobs")
    method_admission = _method_admission(successor, staged_runs)
    _require(
        staged_passive_jobs[0]["result"]["capture"] ==
        staged_passive_jobs[1]["result"]["capture"],
        "staged passive repeat endpoints diverged")
    positive = staged_precise_jobs[0]["result"]
    negative = staged_precise_jobs[1]["result"]
    positive_loader = _first_loader_entry(positive)
    negative_loader = _first_loader_entry(negative)
    _require(
        positive_loader["arguments"] == [
            "0x00000028", "0x00000000", "0x00000000", "0x00000000"] and
        negative_loader["arguments"] == [
            "0x0000002e", "0x00000000", "0x00000000", "0x00000000"] and
        {
            key: positive_loader[key]
            for key in ("function", "caller", "return_address",
                        "frame", "cycle")
        } == {
            "function": "0x8003e7c0",
            "caller": "0x800500d8",
            "return_address": "0x800500e0",
            "frame": 265655,
            "cycle": 150414500686,
        } == {
            key: negative_loader[key]
            for key in ("function", "caller", "return_address",
                        "frame", "cycle")
        },
        "staged selector loader interface drifted")
    positive_limit = _initial_limit_write(positive)
    negative_limit = _initial_limit_write(negative)
    limit_instruction_pc = _instruction_pc(
        positive_limit["pc"], "0x800b6dc0", "positive limit")
    _require(
        _instruction_pc(
            negative_limit["pc"], "0x800b6dc0", "negative limit") ==
        limit_instruction_pc,
        "staged limit instruction PCs diverged")
    _require(
        {
            key: positive_limit[key]
            for key in ("address", "pc", "frame", "new_value")
        } == {
            "address": "0x80131eee", "pc": "0x800b6dc4",
            "frame": 265826, "new_value": 3162,
        } and
        {
            key: negative_limit[key]
            for key in ("address", "pc", "frame", "new_value")
        } == {
            "address": "0x80131eee", "pc": "0x800b6dc4",
            "frame": 265826, "new_value": 281,
        },
        "staged selector limit interface drifted")
    expected_teardown = [
        {
            "type": "entry", "function": "0x8007094c",
            "caller": "0x800b749c", "return_address": "0x800b74a4",
            "synthetic_unwind": False,
        },
        {
            "type": "exit", "function": "0x8007094c",
            "caller": "0x800b749c", "return_address": "0x800b74a4",
            "synthetic_unwind": False,
        },
        {
            "type": "entry", "function": "0x800709ac",
            "caller": "0x800b74a4", "return_address": "0x800b74ac",
            "synthetic_unwind": False,
        },
        {
            "type": "exit", "function": "0x800709ac",
            "caller": "0x800b74a4", "return_address": "0x800b74ac",
            "synthetic_unwind": False,
        },
    ]
    positive_teardown = _teardown_quad(positive)
    negative_teardown = _teardown_quad(negative)
    _require(
        [
            {key: row[key] for key in row if key != "frame"}
            for row in positive_teardown
        ] == expected_teardown and
        {row["frame"] for row in positive_teardown} == {267891} and
        [
            {key: row[key] for key in row if key != "frame"}
            for row in negative_teardown
        ] == expected_teardown and
        {row["frame"] for row in negative_teardown} == {266545},
        "staged balanced teardown interface drifted")
    negative_completion = [
        row for row in negative["capture"]["traces"]["access"]["events"]
        if row["address"] == "0x800cac10" and
        row["pc"] == "0x800b6b4c" and row["new_value"] == 1]
    positive_completion = [
        row for row in positive["capture"]["traces"]["access"]["events"]
        if row["address"] == "0x800cac10" and
        row["pc"] == "0x800b6b4c" and row["new_value"] == 1]
    _require(
        len(negative_completion) == 1 and
        negative_completion[0]["frame"] == 266492 and
        positive_completion == [],
        "bounded completion-request observation drifted")
    completion_instruction_pc = _instruction_pc(
        negative_completion[0]["pc"], "0x800b6b48",
        "native completion request")
    positive_callsite = _memory(
        positive["capture"], "scene_flow_callsite")["hex"]
    negative_callsite = _memory(
        negative["capture"], "scene_flow_callsite")["hex"]
    _require(
        positive_callsite == (
            negative_callsite[:96] + "28000424" + negative_callsite[104:]),
        "staged branches lost their single callsite-word basis")
    return {
        "schema": "abl-phase4-fmv-c16-selector-control-result/3",
        "generated": _stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "historical_unstaged_attempt": {
            "escalation_id": CONFIGURATION["escalation_id"],
            "missing_fact_id": CONFIGURATION["missing_fact_id"],
            "receipts": historical_runs,
            "observation": {
                "after_load_write_verified": True,
                "after_load_code_invalidated": True,
                "only_endpoint_code_difference":
                    "0x800500d4:0x2404002e->0x24040028",
                "actual_movie_playback_start": 0,
                "declared_movie_playback_starts": [299, 300],
                "all_lifecycle_observer_events": 0,
                "all_jobs_untruncated_and_reproducible": True,
            },
            "falsifier": {
                "predicate": (
                    "the typed 299/300-frame prelude is executed before the "
                    "selector write and lifecycle observer window"),
                "outcome": "falsified",
                "reasons": [
                    "movie_playback_started_at_zero",
                    "raw_counters_escape_typed_movie_frame_bound",
                    "no_selector_limit_completion_or_teardown_event",
                ],
            },
            "record_counts": {
                "emulator_launches": 2,
                "completed_atomic_jobs": 4,
                "exact_after_load_writes": 1,
                "lifecycle_observer_events": 0,
                "owned_pids_stopped": 2,
                "admissible_live_receipts": 0,
            },
            "claim_boundary": CONFIGURATION["claim_boundary"],
        },
        "escalation_id": successor["escalation_id"],
        "missing_fact_id": successor["missing_fact_id"],
        "offline_receipt_sha256":
            successor["offline_receipt"]["sha256"],
        "receipts": staged_runs,
        "observation": {
            "after_load_write_verified": True,
            "after_load_code_invalidated": True,
            "only_initial_code_difference":
                "0x800500d4:0x2404002e->0x24040028",
            "same_anchor_loader_interface": {
                "function": "0x8003e7c0",
                "caller": "0x800500d8",
                "return_address": "0x800500e0",
                "frame": 265655,
                "cycle": 150414500686,
                "positive_selector": 40,
                "negative_selector": 46,
            },
            "same_frame_initial_limit_interface": {
                "instruction_pc": limit_instruction_pc,
                "reported_pc": positive_limit["pc"],
                "address": "0x80131eee",
                "frame": 265826,
                "positive_limit": 3162,
                "negative_limit": 281,
            },
            "balanced_teardown_interface": {
                "functions": ["0x8007094c", "0x800709ac"],
                "callers": ["0x800b749c", "0x800b74a4"],
                "positive_first_frame": 267891,
                "negative_first_frame": 266545,
            },
            "negative_native_completion_request": {
                "instruction_pc": completion_instruction_pc,
                "reported_pc": negative_completion[0]["pc"],
                "address": "0x800cac10",
                "new_value": 1,
                "frame": 266492,
            },
            "positive_natural_completion_request_observed": False,
            "all_jobs_untruncated_and_reproducible": True,
        },
        "record_counts": {
            "emulator_launches": 2,
            "completed_atomic_jobs": 4,
            "replay_frames": 16024,
            "observer_frames": 14826,
            "exact_after_load_writes": 1,
            "owned_pids_stopped": 2,
            "intrinsically_valid_live_receipts": 2,
            "method_trial_admissible_live_receipts": 0,
        },
        "falsifier": {
            "predicate": (
                "a same-anchor, frame-300 selector-only perturbation either "
                "fails to change the first loader/limit pair as predicted or "
                "changes its caller, mode, return, frame, or code basis"),
            "outcome": "survived",
            "evidence": [
                "both branches staged from movie frame 0 to 300 at the same "
                "guest frame/cycle",
                "the sole initial word difference changed selector 46 to 40",
                "loader caller/mode/return/frame/cycle stayed fixed while "
                "the selector and initial limit changed to 40/3162",
                "both branches retained balanced stop-ring/callback teardown",
            ],
        },
        "claim_boundary": successor["claim_boundary"],
        "method_admission": method_admission,
        "source_dependencies": {
            str(CONFIG_PATH.relative_to(common.ROOT)):
                common.sha256(CONFIG_PATH),
            "tools/phase4_fmv_c16_selector_control_result.py":
                common.sha256(Path(__file__)),
            "tools/phase4_duckstation_batch.py":
                common.sha256(common.ROOT /
                              "tools/phase4_duckstation_batch.py"),
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
            raise SystemExit("phase4 C16 selector-control result is stale")
    else:
        print(rendered, end="")
    print(
        "PASS: C16 staged selector interface intrinsically validated; "
        "conservative legacy overlap admits 0 receipts; no dimension promoted",
        file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
