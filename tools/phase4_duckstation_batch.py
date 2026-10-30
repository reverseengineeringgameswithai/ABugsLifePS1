#!/usr/bin/env python3
"""Validate and run an atomic, provenance-rich Phase-4 DuckStation batch."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import yaml

import phase4_common as common


CAPSULE_SET = common.ROOT / "analysis/phase4_trace_capsule_set.json"
DEBT = common.ROOT / "analysis/phase4_closure_debt.json"
ESCALATIONS = common.ROOT / "analysis/phase4_live_escalations.json"
RPC_MANIFEST = common.ROOT / "analysis/phase3_duckstation_rpc_manifest.json"
FIXTURE_SET = common.ROOT / "analysis/phase0_2_external_fixture_set.json"
LAUNCHER = (
    Path.home() / "duckstation/scripts/debugger-client/launch_debugger_instance.sh"
)
PRISTINE_TRACK_SHA256 = (
    "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566"
)
REQUIRED_METHODS = {
    "debugger.capabilities", "debugger.status", "emulator.getMediaInfo",
    "emulator.getStateInfo",
    "scenario.runBatch", "scenario.getBatch", "scenario.cancelBatch",
    "scenario.resumeBatch", "scenario.loadStateAndRun", "scenario.bootAndRun",
    "capture.atomic", "provenanceLog.start", "provenanceLog.get",
}
TERMINAL_BATCH_STATES = {
    "completed", "completed_with_errors", "failed", "cancelled",
}
RECIPE_INSTRUMENTATION_METHODS = {
    "accessLog.addWatch", "execTrace.addWatch", "execTrace.addRangeWatch",
    "accessHistory.start", "accessTrace.start", "transferLog.start",
    "provenanceLog.start", "gp0Trace.start", "gpu.causality.start",
    "spu.trace.start", "functionTrace.start", "reverse.start",
}
MAX_STAGED_PRELUDE_FRAMES = 100000
TRANSFER_LOG_MAX_EVENTS = 100000
TRANSFER_LOG_MAX_PAGE_SIZE = 10000
TRANSFER_LOG_MAX_PAGES = 10


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_bytes(plan: dict) -> bytes:
    return (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def render(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render(value))


def sha256(path: Path) -> str:
    return common.sha256(path)


def artifact_ref(path: Path, run_root: Path) -> dict[str, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"receipt artifact is outside run root: {path}") from exc
    return {
        "scope": "run",
        "path": relative,
        "sha256": sha256(resolved),
    }


def _is_sha256(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _job_anchor(job: dict) -> dict:
    recipe = job.get("recipe")
    if recipe == "loadStateAndRun":
        anchor = {
            "recipe": recipe,
            "state_path": job.get("state_path"),
            "auto_select_disc": job.get("auto_select_disc"),
        }
    else:
        anchor = {
            "recipe": recipe,
            "media_path": job.get("media_path"),
            "fast_boot": job.get("fast_boot"),
        }
    anchor["staged_prelude"] = job.get("staged_prelude")
    anchor["run"] = job.get("run")
    return anchor


def _scenario_media_identity(media: dict) -> dict:
    return {key: media[key] for key in ("path", "serial", "title", "sha256")
            if media.get(key) not in (None, "")}


def _after_load_code_write(operation: object) -> dict[str, int | str]:
    expected = {"kind", "address", "original_word", "replacement_word"}
    if not isinstance(operation, dict) or set(operation) != expected:
        raise ValueError(
            "after_load must contain exactly kind, address, original_word, "
            "and replacement_word")
    if operation["kind"] != "code_write":
        raise ValueError("after_load kind must be code_write")
    normalized: dict[str, int | str] = {"kind": "code_write"}
    for key in ("address", "original_word", "replacement_word"):
        value = operation[key]
        if not isinstance(value, int) or isinstance(value, bool) or \
                not 0 <= value <= 0xFFFFFFFF:
            raise ValueError(f"after_load {key} must be a 32-bit integer")
        normalized[key] = value
    address = int(normalized["address"])
    if address % 4 or not 0x80000000 <= address <= 0x801FFFFC:
        raise ValueError(
            "after_load address must be an aligned cached main-RAM word")
    if normalized["original_word"] == normalized["replacement_word"]:
        raise ValueError("after_load code words must differ")
    return normalized


def _staged_prelude(operation: object) -> dict[str, int | str]:
    expected = {"kind", "target_frame", "max_frames"}
    if not isinstance(operation, dict) or set(operation) != expected:
        raise ValueError(
            "staged_prelude must contain exactly kind, target_frame, and "
            "max_frames")
    if operation["kind"] != "movie_advance":
        raise ValueError("staged_prelude kind must be movie_advance")
    normalized: dict[str, int | str] = {"kind": "movie_advance"}
    for key in ("target_frame", "max_frames"):
        value = operation[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"staged_prelude {key} must be a positive integer")
        normalized[key] = value
    if normalized["max_frames"] > MAX_STAGED_PRELUDE_FRAMES:
        raise ValueError(
            "staged_prelude max_frames exceeds the debugger recipe limit")
    if normalized["max_frames"] < normalized["target_frame"]:
        raise ValueError(
            "staged_prelude max_frames cannot reach target_frame from index zero")
    return normalized


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _transfer_pagination_plan_errors(
        jobs: list[dict], observer_plan: dict, assertion_plan: dict) -> list[str]:
    errors: list[str] = []
    limits = observer_plan.get("result_limits") or {}
    if limits.get("max_records") != TRANSFER_LOG_MAX_EVENTS or \
            limits.get("max_pages") != TRANSFER_LOG_MAX_PAGES:
        errors.append(
            "v2_receipt transfer observer must retain the complete "
            "100000-event ring in at most 10 pages")
    if assertion_plan.get("require_truncated") is not False:
        errors.append(
            "v2_receipt transfer assertion must require truncated false")
    if assertion_plan.get("require_contiguous_indexes") is not True:
        errors.append(
            "v2_receipt transfer assertion must require contiguous indexes")
    for job in jobs:
        job_id = str(job.get("id") or "<missing>")
        transfer_arms = [
            operation for operation in (job.get("instrumentation") or [])
            if isinstance(operation, dict)
            and operation.get("method") == "transferLog.start"
        ]
        if len(transfer_arms) != 1:
            errors.append(
                f"{job_id}: transfer observer requires exactly one "
                "transferLog.start arm")
        pagination = (job.get("capture") or {}).get("transfer_pagination")
        if not isinstance(pagination, dict) or \
                set(pagination) != {"page_size", "max_pages"}:
            errors.append(
                f"{job_id}: capture transfer_pagination must contain "
                "exactly page_size and max_pages")
            continue
        page_size = pagination.get("page_size")
        max_pages = pagination.get("max_pages")
        if not _positive_int(page_size) or \
                page_size > TRANSFER_LOG_MAX_PAGE_SIZE:
            errors.append(
                f"{job_id}: transfer page_size must be 1.."
                f"{TRANSFER_LOG_MAX_PAGE_SIZE}")
            continue
        if not _positive_int(max_pages) or max_pages > TRANSFER_LOG_MAX_PAGES:
            errors.append(
                f"{job_id}: transfer max_pages must be 1.."
                f"{TRANSFER_LOG_MAX_PAGES}")
            continue
        if page_size * max_pages < TRANSFER_LOG_MAX_EVENTS:
            errors.append(
                f"{job_id}: transfer pagination capacity cannot retain the "
                f"{TRANSFER_LOG_MAX_EVENTS}-event ring")
        if max_pages != limits.get("max_pages") or \
                page_size * max_pages != limits.get("max_records"):
            errors.append(
                f"{job_id}: transfer pagination envelope differs from typed "
                "observer result limits")
    return errors


def _central_fixture(path_text: str, entries: dict, operator_root: Path) -> tuple[str | None, dict | None]:
    raw = Path(path_text)
    path = raw.resolve() if raw.is_absolute() else (operator_root / raw).resolve()
    try:
        rel = str(path.relative_to(operator_root))
    except ValueError:
        rel = None
    if rel and rel in entries:
        return rel, entries[rel]
    matches = [(key, row) for key, row in entries.items()
               if path.name == Path(key).name and (operator_root / key).resolve() == path]
    return matches[0] if len(matches) == 1 else (None, None)


def validate_plan(plan: dict, operator_root: Path | None = None,
                  debt_doc: dict | None = None,
                  escalation_doc: dict | None = None,
                  capsule_doc: dict | None = None,
                  allow_executed: bool = False) -> list[str]:
    operator_root = (operator_root or Path(os.environ.get(
        "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL")))).resolve()
    errors: list[str] = []
    if plan.get("schema") != "abl-phase4-duckstation-batch/1":
        errors.append("batch plan schema is invalid")
    debt = debt_doc or common.load_json(DEBT)
    selected = {row["campaign_id"] for row in
                (debt.get("scheduler") or {}).get("selected_campaigns") or []}
    if plan.get("campaign_id") not in selected:
        errors.append(
            f"campaign is not selected by current closure debt: {plan.get('campaign_id')!r}")
    row_ids = plan.get("row_ids") or []
    if not row_ids or len(row_ids) > debt["scheduler"]["wip_limits"]["rows"]:
        errors.append("batch must contain one to the configured maximum row count")
    debt_rows = {row["row_id"]: row for row in debt.get("rows") or []}
    for row_id in row_ids:
        if row_id not in debt_rows:
            errors.append(f"batch names unknown Phase-4 row: {row_id}")
        elif debt_rows[row_id]["campaign_id"] != plan.get("campaign_id"):
            errors.append(f"{row_id}: row does not belong to the selected campaign")
    escalation_ids = set(plan.get("escalation_ids") or [])
    escalation_rows = {
        row["id"]: row for row in
        (escalation_doc or common.load_json(ESCALATIONS)).get("entries") or []
    }
    if not escalation_ids:
        errors.append("live batch has no pre-run escalation ID")
    for escalation_id in escalation_ids - set(escalation_rows):
        errors.append(f"unknown live escalation ID: {escalation_id}")
    for escalation_id in escalation_ids & set(escalation_rows):
        escalation = escalation_rows[escalation_id]
        if escalation.get("target_row") not in row_ids:
            errors.append(f"{escalation_id}: escalation target is outside the batch rows")
        allowed_states = {"planned", "executed"} if allow_executed else {"planned"}
        if escalation.get("state") not in allowed_states:
            errors.append(f"{escalation_id}: live batch requires a current planned escalation")
        if not isinstance(escalation.get("derived_pre_run_audit"), dict):
            errors.append(f"{escalation_id}: escalation lacks its generated pre-run audit")
    media = plan.get("expected_media") or {}
    capsule_set = capsule_doc or common.load_json(CAPSULE_SET)
    pristine_rows = capsule_set.get("pristine_media") or []
    pristine_by_path = {
        str(Path(row["absolute_path"]).resolve()): row for row in pristine_rows
    }
    if media.get("serial") != "SCUS-94288":
        errors.append("expected media serial must be SCUS-94288")
    media_path = Path(str(media.get("path") or ""))
    if not media_path.is_absolute():
        errors.append("expected media path must be absolute")
        media_pin = None
    else:
        media_pin = pristine_by_path.get(str(media_path.resolve()))
    if not media_pin or media.get("sha256") != media_pin.get("sha256"):
        errors.append("expected media path/sha256 is not a pinned pristine retail input")
    elif not media_path.is_file() or common.sha256(media_path) != media_pin["sha256"]:
        errors.append("expected media bytes differ from the pristine media pin")
    track_rows = media.get("tracks") or []
    for row in track_rows:
        if not Path(str(row.get("path") or "")).is_absolute():
            errors.append("expected media track path must be absolute")
        if not _is_sha256(row.get("sha256")):
            errors.append("expected media track sha256 is invalid")
    expected_tracks = {
        (str(Path(row.get("path") or "").resolve()), row.get("sha256"))
        for row in track_rows
    }
    required_tracks = {
        (str(Path(row["absolute_path"]).resolve()), row["sha256"])
        for row in pristine_rows if not media_pin or row is not media_pin
    }
    if expected_tracks != required_tracks:
        errors.append("expected media tracks do not exhaust the central pristine media set")
    for track_path, track_hash in expected_tracks:
        path = Path(track_path)
        if not path.is_file() or common.sha256(path) != track_hash:
            errors.append(f"pristine media track hash mismatch: {track_path}")
    expected_debugger = plan.get("expected_debugger") or {}
    for key in ("api_version", "schema_version", "source_revision"):
        if not str(expected_debugger.get(key) or "").strip():
            errors.append(f"expected debugger lacks {key}")
    if not _is_sha256(expected_debugger.get("binary_sha256")):
        errors.append("expected debugger binary_sha256 is invalid")
    if not isinstance(expected_debugger.get("source_dirty"), bool):
        errors.append("expected debugger source_dirty must be boolean")
    if expected_debugger.get("source_dirty") and not str(
            expected_debugger.get("dirty_state_hash") or "").strip():
        errors.append("dirty debugger source lacks dirty_state_hash")
    planned_escalations = [
        escalation_rows[row] for row in escalation_ids & set(escalation_rows)
        if escalation_rows[row].get("state") == "planned"
    ]
    if planned_escalations:
        rpc_manifest = common.load_json(RPC_MANIFEST)
        manifest_source = rpc_manifest.get("source") or {}
        manifest_binary = (
            (rpc_manifest.get("binaries") or {}).get(
                "build-release/bin/duckstation-qt") or {}
        )
        expected_current = {
            "binary_sha256": manifest_binary.get("sha256"),
            "source_revision": manifest_source.get("revision"),
            "source_dirty": manifest_source.get("dirty"),
            "dirty_state_hash": manifest_source.get("dirty_state_hash"),
        }
        observed_current = {
            key: expected_debugger.get(key) for key in expected_current
        }
        if observed_current != expected_current:
            errors.append(
                "planned live batch debugger identity differs from the "
                "candidate-HEAD RPC manifest")
    jobs = plan.get("jobs") or []
    if not 1 <= len(jobs) <= 128:
        errors.append("scenario batch requires 1..128 jobs")
    job_ids = [str(row.get("id") or "") for row in jobs]
    if any(not value for value in job_ids) or len(job_ids) != len(set(job_ids)):
        errors.append("scenario job IDs must be non-empty and unique")
    entries = common.load_json(common.FIXTURE_SET_PATH).get("entries") or {}
    after_load_jobs: list[tuple[str, dict[str, int | str]]] = []
    staged_prelude_jobs: list[tuple[str, dict[str, int | str]]] = []
    for job in jobs:
        job_id = job.get("id", "<missing>")
        recipe = job.get("recipe")
        if recipe not in {"loadStateAndRun", "bootAndRun"}:
            errors.append(f"{job_id}: unsupported recipe {recipe!r}")
        if job.get("expected_media") != media:
            errors.append(f"{job_id}: job media identity differs from the plan")
        run = job.get("run") or {}
        if sum(key in run for key in ("frames", "movie_frame", "until")) != 1:
            errors.append(f"{job_id}: run must name exactly one execution bound")
        instrumentation = job.get("instrumentation") or []
        if len(instrumentation) > 32:
            errors.append(f"{job_id}: instrumentation exceeds the atomic recipe limit")
        for arm in instrumentation:
            method = str(arm.get("method") or "") if isinstance(arm, dict) else ""
            if method not in RECIPE_INSTRUMENTATION_METHODS:
                errors.append(f"{job_id}: non-arming instrumentation entry {method!r}")
        if job.get("staged_prelude") is not None:
            if recipe != "loadStateAndRun":
                errors.append(
                    f"{job_id}: staged_prelude is valid only for loadStateAndRun")
            try:
                prelude = _staged_prelude(job["staged_prelude"])
            except ValueError as exc:
                errors.append(f"{job_id}: {exc}")
            else:
                staged_prelude_jobs.append((str(job_id), prelude))
                movie = job.get("movie") or {}
                if not movie.get("path"):
                    errors.append(
                        f"{job_id}: staged_prelude requires a centrally pinned movie")
                if movie.get("start_frame", 0) != 0:
                    errors.append(
                        f"{job_id}: staged_prelude requires movie start_frame zero")
                if set(run) != {"movie_frame"}:
                    errors.append(
                        f"{job_id}: staged_prelude requires one movie_frame run bound")
                elif prelude["target_frame"] >= run["movie_frame"]:
                    errors.append(
                        f"{job_id}: staged_prelude target must precede the run target")
        if job.get("after_load") is not None:
            if recipe != "loadStateAndRun":
                errors.append(
                    f"{job_id}: after_load is valid only for loadStateAndRun")
            try:
                operation = _after_load_code_write(job["after_load"])
            except ValueError as exc:
                errors.append(f"{job_id}: {exc}")
            else:
                after_load_jobs.append((str(job_id), operation))
        external_paths: list[str] = []
        if recipe == "loadStateAndRun":
            if not job.get("state_path"):
                errors.append(f"{job_id}: loadStateAndRun lacks a centrally pinned state_path")
            else:
                external_paths.append(str(job["state_path"]))
            if job.get("auto_select_disc") is not False:
                errors.append(
                    f"{job_id}: loadStateAndRun must retain the verified mounted disc")
        else:
            if not job.get("media_path"):
                errors.append(f"{job_id}: bootAndRun lacks media_path")
            else:
                boot_media = Path(str(job["media_path"]))
                if not boot_media.is_absolute():
                    errors.append(
                        f"{job_id}: DuckStation fixture path must be absolute: "
                        f"{job['media_path']}")
                elif not media_path.is_absolute() or \
                        boot_media.resolve() != media_path.resolve():
                    errors.append(
                        f"{job_id}: bootAndRun media_path differs from the "
                        "plan's pinned pristine media")
        movie = job.get("movie") or {}
        if movie.get("path"):
            external_paths.append(str(movie["path"]))
        for path_text in external_paths:
            if not Path(path_text).is_absolute():
                errors.append(f"{job_id}: DuckStation fixture path must be absolute: {path_text}")
            rel, pin = _central_fixture(path_text, entries, operator_root)
            path = Path(path_text).resolve() if Path(path_text).is_absolute() \
                else (operator_root / path_text).resolve()
            if not rel or not pin:
                errors.append(f"{job_id}: external fixture is not centrally declared: {path_text}")
                continue
            if pin.get("media_class") not in {"pristine", "pristine_serial"}:
                errors.append(f"{job_id}: fixture is not pristine eligible: {rel}")
            if not path.is_file():
                errors.append(f"{job_id}: fixture is absent: {path_text}")
            elif common.sha256(path) != pin.get("sha256") or path.stat().st_size != pin.get("size"):
                errors.append(f"{job_id}: fixture hash/size differs from central pin: {rel}")
        if not isinstance(job.get("capture"), dict) or not job.get("capture"):
            errors.append(f"{job_id}: atomic job lacks a bounded capture")
    pairs = plan.get("control_pairs") or []
    if not pairs:
        errors.append("live batch requires at least one native positive/negative control pair")
    for pair in pairs:
        positive = pair.get("positive_job")
        negative = pair.get("negative_job")
        if positive not in job_ids or negative not in job_ids or positive == negative:
            errors.append("control pair does not name two distinct batch jobs")
        elif _job_anchor(jobs[job_ids.index(positive)]) != \
                _job_anchor(jobs[job_ids.index(negative)]):
            errors.append("control pair jobs do not share the same anchor and run bound")
        if len(str(pair.get("assertion") or "").strip()) < 20:
            errors.append("control pair assertion is missing or too generic")
    for job_id, _operation in after_load_jobs:
        matched = [
            pair for pair in pairs if pair.get("positive_job") == job_id
            and not next(
                (job.get("after_load") is not None for job in jobs
                 if job.get("id") == pair.get("negative_job")),
                True,
            )
        ]
        if len(matched) != 1:
            errors.append(
                f"{job_id}: after_load must be the sole difference in one "
                "positive/negative control pair")
    if len(after_load_jobs) > 1:
        errors.append("batch permits at most one typed after_load code-write job")
    receipt = plan.get("v2_receipt")
    if after_load_jobs and receipt is None:
        errors.append("after_load requires a typed v2_receipt perturbation plan")
    if receipt is not None:
        if not isinstance(receipt, dict):
            errors.append("v2_receipt must be an object")
        else:
            expected_receipt_keys = {
                "id", "missing_fact_id", "precise", "anchor", "execution",
                "domain", "observer_plan", "perturbation_plan", "control_role",
                "assertion_plan", "settings_snapshot",
            }
            if set(receipt) != expected_receipt_keys:
                errors.append("v2_receipt keys differ from the closed batch schema")
            if receipt.get("missing_fact_id") != next(
                    (escalation_rows[row].get("missing_fact_id")
                     for row in escalation_ids if row in escalation_rows), None):
                errors.append("v2_receipt missing_fact_id differs from escalation")
            if not isinstance(receipt.get("precise"), bool):
                errors.append("v2_receipt precise flag is invalid")
            if receipt.get("domain") not in {
                    "ram", "register", "dma", "gpu", "spu", "interface",
                    "native_control"}:
                errors.append("v2_receipt domain is invalid")
            if receipt.get("control_role") not in {
                    "baseline", "positive", "negative"}:
                errors.append("v2_receipt control role is invalid")
            if not isinstance(receipt.get("assertion_plan"), dict) or \
                    not receipt.get("assertion_plan"):
                errors.append("v2_receipt assertion plan is missing")
            assertion_plan = receipt.get("assertion_plan") or {}
            if assertion_plan.get("kind") == \
                    "c16_decoded_record_retention_lifecycle_discriminator":
                retention_contract = {
                    "retention_source_receipt_sha256":
                        "7156595a5e9822afa871075802ccfe0fd7b4f5ef60fc46aa89fe00f72f329b1b",
                    "prior_emitted_function_events": 90,
                    "function_max_events": 128,
                    "required_first_function_index": 1,
                    "required_last_function_index_lte": 90,
                    "required_function_events_lte": 90,
                    "require_function_events_lt_max": True,
                }
                if any(
                        assertion_plan.get(key) != value
                        for key, value in retention_contract.items()):
                    errors.append(
                        "decoded-record retention assertion does not exactly "
                        "match the banked 90-event/128-capacity contract")
                observer_functions = [
                    operation for operation in (
                        (receipt.get("observer_plan") or {}).get(
                            "operations") or [])
                    if isinstance(operation, dict)
                    and operation.get("method") == "functionTrace.start"
                ]
                expected_trace = {
                    "functions": [0x800B6C24, 0x8007094C, 0x800709AC],
                    "all_symbols": False,
                    "capture_memory": False,
                    "max_events": 128,
                }
                if len(observer_functions) != 1 or \
                        observer_functions[0].get("args") != expected_trace:
                    errors.append(
                        "decoded-record retention observer does not exactly "
                        "match the guarded function trace")
                job_functions = [
                    operation
                    for job in jobs
                    for operation in (job.get("instrumentation") or [])
                    if isinstance(operation, dict)
                    and operation.get("method") == "functionTrace.start"
                ]
                if len(job_functions) != len(jobs) or any(
                        operation.get("params") != expected_trace
                        for operation in job_functions):
                    errors.append(
                        "decoded-record retention job instrumentation does "
                        "not exactly match the guarded function trace")
            if not isinstance(receipt.get("settings_snapshot"), dict) or \
                    not receipt.get("settings_snapshot"):
                errors.append("v2_receipt settings snapshot is missing")
            try:
                from phase4_method_metrics import (
                    _canonical_live_key, _validate_observer_plan,
                    _validate_perturbation_plan,
                )
                _validate_observer_plan(
                    receipt.get("observer_plan"), "v2_receipt observer_plan")
                _validate_perturbation_plan(
                    receipt.get("perturbation_plan"),
                    "v2_receipt perturbation_plan")
                perturbation = receipt.get("perturbation_plan") or {}
                code_writes = [
                    {key: value for key, value in operation.items()
                     if key != "sequence"}
                    for operation in perturbation.get("operations") or []
                    if isinstance(operation, dict)
                    and operation.get("kind") == "code_write"
                ]
                planned_writes = [
                    operation for _job_id, operation in after_load_jobs
                ]
                if code_writes != planned_writes or (
                        after_load_jobs and (
                            perturbation.get("kind") != "operations"
                            or len(perturbation.get("operations") or []) != 1)):
                    errors.append(
                        "v2_receipt code-write perturbation does not exactly "
                        "match the positive job after_load operation")
                provisional = {
                    "experiment": {
                        "executor_role": "investigator",
                        "anchor": {
                            **(receipt.get("anchor") or {}),
                            "settings_sha256": sha256_bytes(
                                render(receipt.get("settings_snapshot"))),
                        },
                        "execution": receipt.get("execution"),
                        "domain": receipt.get("domain"),
                        **{
                            key: "0" * 64 for key in (
                                "observer_plan_sha256",
                                "perturbation_plan_sha256",
                                "control_plan_sha256",
                                "duckstation_source_sha256",
                                "duckstation_executable_sha256",
                                "api_surface_sha256",
                                "adapter_source_sha256",
                            )
                        },
                    },
                }
                _canonical_live_key(provisional)
            except (ImportError, KeyError, TypeError, ValueError, RuntimeError) as exc:
                errors.append(f"v2_receipt schema is invalid: {exc}")
            execution = receipt.get("execution") or {}
            bound = execution.get("bound") or {}
            capture = execution.get("capture_window") or {}
            if receipt.get("anchor", {}).get("kind") == "cold_boot_movie" and \
                    any(job.get("recipe") == "bootAndRun" for job in jobs) and \
                    capture.get("start") != bound.get("start"):
                errors.append(
                    "v2_receipt cold-boot capture must begin at the execution "
                    "bound because bootAndRun arms instrumentation before the "
                    "first guest frame and has no staged prelude")
            if bound.get("clock") == "movie_frame":
                matching_preludes = [
                    prelude for _job_id, prelude in staged_prelude_jobs
                ]
                capture_start = capture.get("start")
                if isinstance(capture_start, int) and capture_start != 0:
                    if len(matching_preludes) != len(jobs):
                        errors.append(
                            "v2_receipt nonzero movie-frame capture requires "
                            "one atomic staged_prelude in every job")
                    elif any(
                            prelude["target_frame"] != capture_start
                            for prelude in matching_preludes):
                        errors.append(
                            "v2_receipt movie-frame capture start differs from "
                            "the staged_prelude target")
                if staged_prelude_jobs and bound.get("start") != 0:
                    errors.append(
                        "v2_receipt staged_prelude execution bound must retain "
                        "the actual movie playback start at index zero")
            observer_operations = (
                (receipt.get("observer_plan") or {}).get("operations") or []
            )
            if any(
                    isinstance(operation, dict) and
                    operation.get("method") == "transferLog.start"
                    for operation in observer_operations):
                errors.extend(_transfer_pagination_plan_errors(
                    jobs, receipt.get("observer_plan") or {},
                    assertion_plan))
            settings = receipt.get("settings_snapshot") or {}
            if settings.get("binary_sha256") != expected_debugger.get(
                    "binary_sha256"):
                errors.append(
                    "v2_receipt settings binary differs from expected debugger")
    return sorted(set(errors))


def make_request(plan: dict) -> dict:
    """Return only the closed-schema fields accepted by scenario.runBatch."""
    jobs = []
    for source in plan["jobs"]:
        job = {key: value for key, value in source.items()
               if key not in {"notes", "expected_assertions"}}
        expected_media = _scenario_media_identity(plan["expected_media"])
        if job.get("recipe") == "loadStateAndRun":
            # The pre-run audit above pins the currently mounted absolute path.
            # A valid state may then restore its recorded absolute path from an
            # older clean checkout, so post-load identity is byte/serial/title
            # strict while allowing that directory relocation.
            expected_media.pop("path", None)
        job["expected_media"] = expected_media
        jobs.append(job)
    return {
        "continue_on_error": bool(plan.get("continue_on_error", True)),
        "jobs": jobs,
    }


def _load_client_module() -> Any:
    path = Path(os.environ.get(
        "ABL_DUCKSTATION_CLIENT",
        str(Path.home() / "duckstation/scripts/debugger-client/duckstation_debug_client.py"),
    )).resolve()
    if not path.is_file():
        raise RuntimeError(f"DuckStation debugger client is absent: {path}")
    spec = importlib.util.spec_from_file_location("phase4_duckstation_client", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load DuckStation debugger client: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_live(plan: dict, port: int, token: str, output: Path,
             poll_seconds: float = 1.0) -> dict:
    if common.ROOT == output.resolve() or common.ROOT in output.resolve().parents:
        raise ValueError("live batch output must remain outside the Git worktree")
    module = _load_client_module()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(300)
    capabilities = client.call("debugger.capabilities", {})
    methods = set((capabilities.get("methods") or {}).keys())
    missing = sorted(REQUIRED_METHODS - methods)
    if missing:
        raise RuntimeError(f"running DuckStation lacks required methods: {missing}")
    expected_debugger = plan["expected_debugger"]
    observed_debugger = {
        "api_version": (capabilities.get("api") or {}).get("version"),
        "schema_version": (capabilities.get("api") or {}).get("schema_version"),
        "binary_sha256": (capabilities.get("binary") or {}).get("sha256"),
        "source_revision": (capabilities.get("source") or {}).get("revision"),
        "source_dirty": (capabilities.get("source") or {}).get("dirty"),
        "dirty_state_hash": (capabilities.get("source") or {}).get("dirty_state_hash"),
    }
    if observed_debugger != expected_debugger:
        raise RuntimeError(
            f"running DuckStation identity differs from the plan: {observed_debugger}")
    status = client.call("debugger.status", {})
    media = client.call("emulator.getMediaInfo", {})
    expected = plan["expected_media"]
    actual_serial = media.get("serial") or media.get("game_serial")
    actual_path = Path(str(media.get("path") or ""))
    actual_hash = common.sha256(actual_path) if actual_path.is_file() else None
    if (actual_serial != expected["serial"]
            or actual_path.resolve() != Path(expected["path"]).resolve()
            or actual_hash != expected["sha256"]):
        raise RuntimeError(
            f"mounted media mismatch: path={actual_path} serial={actual_serial!r} "
            f"sha256={actual_hash!r}")
    for track in expected.get("tracks") or []:
        path = Path(track["path"])
        if not path.is_file() or common.sha256(path) != track["sha256"]:
            raise RuntimeError(f"mounted-media companion track drift: {path}")
    state_inspections = []
    inspected_states: set[str] = set()
    for job in plan["jobs"]:
        if job.get("recipe") != "loadStateAndRun":
            continue
        state_path = str(Path(job["state_path"]).resolve())
        if state_path in inspected_states:
            continue
        inspected_states.add(state_path)
        state_info = client.call("emulator.getStateInfo", {"path": state_path})
        state_serial = state_info.get("serial") or state_info.get("game_serial")
        if state_info.get("exists") is not True or state_info.get("valid") is not True:
            raise RuntimeError(f"save-state inspection failed before load: {state_info}")
        if state_serial != expected["serial"]:
            raise RuntimeError(
                f"save-state serial differs from mounted pristine media: {state_info}")
        state_media_path = Path(str(state_info.get("media_path") or ""))
        expected_media_path = Path(expected["path"])
        if (not state_media_path.is_absolute()
                or state_media_path.name != expected_media_path.name
                or state_info.get("title") != expected["title"]
                or state_info.get("media_subimage_index") not in (None, 0)):
            raise RuntimeError(
                f"save-state media metadata differs from mounted pristine media: {state_info}")
        if state_info.get("file_size") != Path(state_path).stat().st_size:
            raise RuntimeError(
                f"save-state inspected size differs from pinned fixture bytes: {state_info}")
        state_inspections.append({"path": state_path, "state_info": state_info})
    submitted = client.call("scenario.runBatch", make_request(plan))
    batch_id = submitted.get("batch_id")
    if not batch_id:
        raise RuntimeError(f"scenario.runBatch returned no batch_id: {submitted}")
    polls = []
    while True:
        result = client.call("scenario.getBatch", {
            "batch_id": batch_id, "include_results": True,
        })
        polls.append(result)
        state = str(result.get("state") or result.get("status") or "")
        if state in TERMINAL_BATCH_STATES:
            break
        time.sleep(max(0.1, min(poll_seconds, 5.0)))
    if state == "completed":
        _validate_transfer_batch_result(plan, result)
    document = {
        "schema": "abl-phase4-duckstation-batch-result/1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "port": port,
        "generator_sha256": common.sha256(Path(__file__)),
        "client_sha256": common.sha256(Path(module.__file__)),
        "plan_sha256": sha256_bytes(plan_bytes(plan)),
        "campaign_id": plan["campaign_id"],
        "row_ids": plan["row_ids"],
        "escalation_ids": plan["escalation_ids"],
        "expected_media": expected,
        "expected_debugger": expected_debugger,
        "capabilities": {
            "api": capabilities.get("api"),
            "source": capabilities.get("source"),
            "binary": capabilities.get("binary"),
            "required_methods": sorted(REQUIRED_METHODS),
        },
        "identity_results": {
            "debugger.capabilities": capabilities,
            "debugger.status": status,
            "emulator.getMediaInfo": media,
        },
        "mounted_media": media,
        "state_inspections": state_inspections,
        "batch_id": batch_id,
        "batch_submission": submitted,
        "batch_polls": polls,
        "result": result,
        "control_pairs": plan["control_pairs"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return document


def _normalized_capabilities(
        capabilities: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    declared = set((manifest.get("methods") or {}).get("committed") or ()) | \
        set((manifest.get("methods") or {}).get("dirty_only") or ())
    schemas = {
        method: sha256_bytes(canonical_bytes(schema))
        for method, schema in sorted((capabilities.get("methods") or {}).items())
        if method in declared
    }
    if not schemas:
        raise RuntimeError("debugger capabilities contain no manifest-declared methods")
    source_sha256 = sha256_bytes(canonical_bytes(manifest["source"]))
    api_surface_sha256 = sha256_bytes(canonical_bytes(manifest["methods"]))
    return {
        "source_sha256": source_sha256,
        "executable_sha256": capabilities["binary"]["sha256"],
        "api_surface_sha256": api_surface_sha256,
        "method_schemas": schemas,
    }


def _trace_totals(job_result: dict[str, Any]) -> tuple[int, bool]:
    capture = (job_result.get("result") or {}).get("capture") or {}
    traces = capture.get("traces") or {}
    total = 0
    truncated = False
    transfer_pagination = traces.get("transfer_pagination")
    for key, value in traces.items():
        if key == "transfers" and isinstance(transfer_pagination, dict) and \
                transfer_pagination:
            continue
        if isinstance(value, dict):
            if isinstance(value.get("total"), int):
                total += value["total"]
            if value.get("truncated") is True:
                truncated = True
        elif isinstance(value, list):
            total += len(value)
    movie = (job_result.get("result") or {}).get("movie") or {}
    if movie.get("truncated") is True:
        truncated = True
    return total, truncated


def _validated_transfer_pages(
        job_result: dict[str, Any], capture_spec: dict[str, Any],
        result_limits: dict[str, Any], assertion_plan: dict[str, Any],
) -> tuple[int, list[dict[str, int]]]:
    job_id = str(job_result.get("id") or "<missing>")
    pagination = (
        ((job_result.get("result") or {}).get("capture") or {})
        .get("traces", {}).get("transfer_pagination")
    )
    expected_keys = {
        "page_size", "max_pages", "page_count", "total", "returned",
        "truncated", "enabled", "pagination_complete", "pages",
    }
    if not isinstance(pagination, dict) or set(pagination) != expected_keys:
        raise RuntimeError(
            f"{job_id}: transfer pagination result has an incomplete schema")
    expected = capture_spec.get("transfer_pagination") or {}
    page_size = pagination.get("page_size")
    max_pages = pagination.get("max_pages")
    if page_size != expected.get("page_size") or \
            max_pages != expected.get("max_pages"):
        raise RuntimeError(
            f"{job_id}: transfer pagination result differs from its plan")
    if page_size * max_pages > result_limits.get("max_records", -1) or \
            max_pages > result_limits.get("max_pages", -1):
        raise RuntimeError(
            f"{job_id}: transfer pagination result escapes typed limits")
    total = pagination.get("total")
    returned = pagination.get("returned")
    page_count = pagination.get("page_count")
    pages = pagination.get("pages")
    if not all(_positive_int(value) for value in (total, returned, page_count)):
        raise RuntimeError(
            f"{job_id}: transfer pagination totals must be positive integers")
    if pagination.get("enabled") is not True or \
            pagination.get("pagination_complete") is not True or \
            pagination.get("truncated") is not False:
        raise RuntimeError(
            f"{job_id}: transfer pagination is incomplete or truncated")
    if total != returned or total > result_limits["max_records"]:
        raise RuntimeError(
            f"{job_id}: transfer pagination did not retain its exact total")
    if not isinstance(pages, list) or len(pages) != page_count or \
            page_count > max_pages:
        raise RuntimeError(
            f"{job_id}: transfer page count differs from retained pages")

    next_offset = 0
    indexes: list[int] = []
    retained_pages: list[dict[str, int]] = []
    for page_number, page in enumerate(pages):
        if not isinstance(page, dict) or \
                set(page) != {"offset", "limit", "returned", "events"}:
            raise RuntimeError(
                f"{job_id}: transfer page {page_number} schema is incomplete")
        events = page.get("events")
        count = page.get("returned")
        if page.get("offset") != next_offset or page.get("limit") != page_size \
                or not _positive_int(count) or not isinstance(events, list) \
                or len(events) != count or count > page_size:
            raise RuntimeError(
                f"{job_id}: transfer page {page_number} is not contiguous")
        if page_number + 1 < page_count and count != page_size:
            raise RuntimeError(
                f"{job_id}: transfer page {page_number} ended before the "
                "final page")
        for event in events:
            index = event.get("index") if isinstance(event, dict) else None
            if not _positive_int(index):
                raise RuntimeError(
                    f"{job_id}: transfer event index is not a positive integer")
            indexes.append(index)
        retained_pages.append({
            "page": page_number,
            "offset": next_offset,
            "record_count": count,
        })
        next_offset += count
    if next_offset != returned:
        raise RuntimeError(
            f"{job_id}: transfer pages do not sum to returned total")
    first_index = assertion_plan.get("required_first_transfer_index")
    if indexes[0] != first_index:
        raise RuntimeError(
            f"{job_id}: first transfer index differs from assertion")
    if assertion_plan.get("require_contiguous_indexes") is True and \
            indexes != list(range(indexes[0], indexes[0] + len(indexes))):
        raise RuntimeError(
            f"{job_id}: transfer event indexes are not contiguous")
    return total, retained_pages


def _validate_transfer_batch_result(
        plan: dict[str, Any], result: dict[str, Any],
) -> list[dict[str, int | str]]:
    receipt = plan.get("v2_receipt") or {}
    observer = receipt.get("observer_plan") or {}
    has_transfer_observer = any(
        isinstance(operation, dict)
        and operation.get("method") == "transferLog.start"
        for operation in (observer.get("operations") or [])
    )
    if not has_transfer_observer:
        return []
    planned_jobs = {str(row["id"]): row for row in plan.get("jobs") or []}
    observed_jobs = result.get("jobs") or []
    if [str(row.get("id")) for row in observed_jobs] != list(planned_jobs):
        raise RuntimeError(
            "transfer batch result job order differs from atomic plan")
    retained: list[dict[str, int | str]] = []
    for row in observed_jobs:
        job_id = str(row["id"])
        _total, pages = _validated_transfer_pages(
            row, planned_jobs[job_id].get("capture") or {},
            observer.get("result_limits") or {},
            receipt.get("assertion_plan") or {},
        )
        retained.extend({"job_id": job_id, **page} for page in pages)
    return retained


def _raw_result_document(
        document: dict[str, Any], session_id: str,
        execution: dict[str, Any]) -> dict[str, Any]:
    bound = execution.get("bound") or {}
    capture = execution.get("capture_window") or {}
    clock = bound.get("clock")
    if clock != capture.get("clock"):
        raise RuntimeError("execution bound and capture window clocks differ")
    if clock not in {"emulator_frame", "movie_frame"}:
        raise RuntimeError(
            f"raw result adapter cannot derive counters for {clock!r}")
    rows = []
    for job in (document["result"].get("jobs") or []):
        result = job.get("result") or {}
        run = result.get("run") or {}
        advanced = run.get("frames_advanced")
        if clock == "movie_frame":
            observer_start = run.get("start_playback_index")
            stop = run.get("target_frame")
            staged = result.get("staged_prelude")
            if staged is not None:
                staged_advanced = staged.get("frames_advanced")
                staged_start = staged.get("start_playback_index")
                staged_stop = staged.get("target_frame")
                staged_movie_stop = (staged.get("movie") or {}).get(
                    "playback_index")
                if not all(isinstance(value, int) for value in (
                        staged_advanced, staged_start, staged_stop,
                        staged_movie_stop)):
                    raise RuntimeError(
                        f"{job.get('id')}: staged prelude lacks movie counters")
                if staged_start < 0 or staged_stop <= staged_start or \
                        staged_stop - staged_start != staged_advanced or \
                        staged_movie_stop != staged_stop or \
                        staged_stop != observer_start:
                    raise RuntimeError(
                        f"{job.get('id')}: staged prelude is not contiguous "
                        "with the observed movie run")
                start = staged_start
            else:
                start = observer_start
        else:
            stop = (result.get("status") or {}).get("frame")
            start = stop - advanced if isinstance(stop, int) and \
                isinstance(advanced, int) else None
            observer_start = start
        if not all(isinstance(value, int) for value in (
                advanced, start, observer_start, stop)):
            raise RuntimeError(f"{job.get('id')}: batch result lacks frame counters")
        if start < 0 or observer_start < start or stop < observer_start or \
                stop - observer_start != advanced:
            raise RuntimeError(f"{job.get('id')}: batch frame counters run backwards")
        if start < bound.get("start", 0) or stop > bound.get("stop", -1):
            raise RuntimeError(
                f"{job.get('id')}: observed {clock} span {start}..{stop} "
                f"escapes typed bound {bound.get('start')}.."
                f"{bound.get('stop')}")
        if observer_start < capture.get("start", 0) or \
                stop > capture.get("stop", -1):
            raise RuntimeError(
                f"{job.get('id')}: observed {clock} observer span "
                f"{observer_start}..{stop} escapes capture window "
                f"{capture.get('start')}..{capture.get('stop')}")
        rows.append({
            "job_id": job["id"],
            "server_session_id": session_id,
            "status": job.get("state"),
            "replay_start": start,
            "replay_stop": stop,
            "observer_start": observer_start,
            "observer_stop": stop,
            "instruction_start": 0,
            "instruction_stop": 0,
        })
    counters = {
        "server_session_id": session_id,
        "launches": 1,
        "atomic_jobs": len(rows),
        "replay_frames": sum(
            row["replay_stop"] - row["replay_start"] for row in rows),
        "observer_frames": sum(
            row["observer_stop"] - row["observer_start"] for row in rows),
        "instructions": 0,
    }
    return {
        "schema": "abl-phase4-live-raw-results/1",
        "complete": document["result"].get("state") == "completed",
        "errors": [],
        "counters": counters,
        "sessions": [{
            "server_session_id": session_id,
            "launch_sequence": 0,
        }],
        "results": rows,
    }


def stop_owned_instance(
        config_dir: Path, binary: Path, owned_pid: int) -> tuple[dict[str, Any], dict[str, Any]]:
    completed = subprocess.run(
        [
            str(LAUNCHER), "stop",
            "--config-dir", str(config_dir),
            "--binary", str(binary),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    stopped = not Path(f"/proc/{owned_pid}").exists()
    cleanup = {
        "schema": "abl-phase4-owned-pid-cleanup/1",
        "complete": completed.returncode == 0 and stopped,
        "errors": [] if completed.returncode == 0 and stopped else [
            "owned DuckStation PID did not stop cleanly"
        ],
        "owned_pid": owned_pid,
        "owned_pid_stopped": stopped,
        "config_dir": str(config_dir.resolve()),
        "actions": [
            {"sequence": 0, "kind": "stop_owned_pid", "pid": owned_pid},
            {"sequence": 1, "kind": "confirm_pid_stopped", "pid": owned_pid},
        ],
    }
    raw = {
        "command": [
            str(LAUNCHER), "stop", "--config-dir", str(config_dir),
            "--binary", str(binary),
        ],
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "owned_pid_stopped": stopped,
    }
    return cleanup, raw


def emit_v2_receipt(
        plan: dict[str, Any], document: dict[str, Any], receipt_dir: Path,
        run_root: Path, cleanup: dict[str, Any], cleanup_raw: dict[str, Any],
        prelude_receipt: Path | None,
) -> Path:
    receipt_spec = plan["v2_receipt"]
    receipt_path = receipt_dir / "receipt.json"
    if receipt_path.exists():
        raise FileExistsError(f"refusing to overwrite live receipt: {receipt_path}")
    receipt_dir.mkdir(parents=True, exist_ok=True)

    settings_path = receipt_dir / "settings-snapshot.json"
    observer_path = receipt_dir / "observer-plan.json"
    perturbation_path = receipt_dir / "perturbation-plan.json"
    control_path = receipt_dir / "control-plan.json"
    raw_path = receipt_dir / "raw-results.json"
    pagination_path = receipt_dir / "pagination.json"
    media_path = receipt_dir / "media-capabilities.json"
    events_path = receipt_dir / "command-events.json"
    cleanup_path = receipt_dir / "owned-pid-cleanup.json"
    cleanup_raw_path = receipt_dir / "owned-pid-cleanup-raw.json"
    preservation_path = receipt_dir / "preservation.json"
    batch_path = receipt_dir / "batch-result.json"

    if not batch_path.exists():
        write_json(batch_path, document)
    write_json(settings_path, receipt_spec["settings_snapshot"])
    write_json(observer_path, receipt_spec["observer_plan"])
    write_json(perturbation_path, receipt_spec["perturbation_plan"])
    write_json(cleanup_path, cleanup)
    write_json(cleanup_raw_path, cleanup_raw)

    manifest = common.load_json(RPC_MANIFEST)
    capabilities = document["identity_results"]["debugger.capabilities"]
    normalized = _normalized_capabilities(capabilities, manifest)
    source_sha256 = normalized["source_sha256"]
    executable_sha256 = normalized["executable_sha256"]
    api_surface_sha256 = normalized["api_surface_sha256"]

    observer_sha256 = sha256(observer_path)
    perturbation_sha256 = sha256(perturbation_path)
    adapter_sha256 = sha256(Path(__file__))
    experiment_without_control = {
        "anchor": {
            **receipt_spec["anchor"],
            "settings_sha256": sha256(settings_path),
        },
        "execution": receipt_spec["execution"],
        "domain": receipt_spec["domain"],
        "observer_plan_sha256": observer_sha256,
        "perturbation_plan_sha256": perturbation_sha256,
        "duckstation_source_sha256": source_sha256,
        "duckstation_executable_sha256": executable_sha256,
        "api_surface_sha256": api_surface_sha256,
        "adapter_source_sha256": adapter_sha256,
    }
    assertion_plan_sha256 = sha256_bytes(
        canonical_bytes(receipt_spec["assertion_plan"]))
    control = {
        "schema": "abl-phase4-control-plan/1",
        "role": receipt_spec["control_role"],
        "paired_run_basis_sha256": sha256_bytes(
            canonical_bytes(experiment_without_control)),
        "anchor_sha256": sha256_bytes(
            canonical_bytes(experiment_without_control["anchor"])),
        "only_difference_plan_sha256": perturbation_sha256,
        "assertion_plan_sha256": assertion_plan_sha256,
    }
    write_json(control_path, control)
    control_sha256 = sha256(control_path)
    experiment = {
        "executor_role": "investigator",
        **experiment_without_control,
        "control_plan_sha256": control_sha256,
    }
    atomic_plan_sha256 = sha256_bytes(canonical_bytes({
        "anchor": experiment["anchor"],
        "execution": experiment["execution"],
        "observer_plan_sha256": observer_sha256,
        "perturbation_plan_sha256": perturbation_sha256,
        "control_plan_sha256": control_sha256,
    }))
    session_id = sha256_bytes(canonical_bytes({
        "config_dir": cleanup["config_dir"],
        "owned_pid": cleanup["owned_pid"],
        "port": document.get("port"),
        "batch_id": document["batch_id"],
        "executable_sha256": executable_sha256,
    }))

    raw = _raw_result_document(document, session_id, experiment["execution"])
    if raw["complete"] is not True or any(
            row["status"] != "completed" for row in raw["results"]):
        raise RuntimeError("cannot close receipt over an incomplete batch")
    write_json(raw_path, raw)
    record_count = 0
    truncated = False
    for job in document["result"].get("jobs") or []:
        job_count, job_truncated = _trace_totals(job)
        record_count += job_count
        truncated = truncated or job_truncated
    transfer_pages = _validate_transfer_batch_result(plan, document["result"])
    pagination_pages = (
        [
            {"page": index, "record_count": page["record_count"]}
            for index, page in enumerate(transfer_pages)
        ]
        if transfer_pages else [{"page": 0, "record_count": record_count}]
    )
    pagination = {
        "schema": "abl-phase4-live-pagination/1",
        "complete": not truncated,
        "errors": [] if not truncated else ["retained trace reported truncation"],
        "truncated": truncated,
        "pages_complete": not truncated,
        "pages": pagination_pages,
    }
    write_json(pagination_path, pagination)

    media = {
        "schema": "abl-phase4-live-media-capabilities/1",
        "complete": True,
        "errors": [],
        "mounted_serial": (
            document["identity_results"]["emulator.getMediaInfo"].get("serial")
            or document["identity_results"]["emulator.getMediaInfo"].get(
                "game_serial")
        ),
        "pristine_media_sha256": PRISTINE_TRACK_SHA256,
        "duckstation_source_sha256": source_sha256,
        "duckstation_executable_sha256": executable_sha256,
        "api_surface_sha256": api_surface_sha256,
        "capabilities": {
            "api_version": capabilities["api"]["version"],
            "method_schemas": normalized["method_schemas"],
        },
    }
    write_json(media_path, media)

    job_ids = [row["job_id"] for row in raw["results"]]
    event_rows = [
        ("debugger.capabilities", {}, normalized),
        ("debugger.status", {}, {
            "game_serial": (
                document["identity_results"]["debugger.status"].get("game_serial")
            ),
        }),
        ("emulator.getMediaInfo", {}, {
            "serial": media["mounted_serial"],
            "sha256": PRISTINE_TRACK_SHA256,
        }),
        ("scenario.runBatch", {"plan_sha256": atomic_plan_sha256}, {
            "batch_id": document["batch_id"],
            "job_ids": job_ids,
        }),
    ]
    for poll in document["batch_polls"]:
        event_rows.append((
            "scenario.getBatch",
            {
                "batch_id": document["batch_id"],
                "include_results": True,
            },
            {
                "batch_id": document["batch_id"],
                "status": poll.get("state") or poll.get("status"),
                "job_ids": [
                    row.get("id") for row in poll.get("jobs") or []
                    if row.get("id")
                ] or job_ids,
            },
        ))
    events = {
        "schema": "abl-phase4-live-command-events/1",
        "complete": True,
        "errors": [],
        "events": [
            {
                "sequence": sequence,
                "server_session_id": session_id,
                "method": method,
                "params": params,
                "result_sha256": sha256_bytes(canonical_bytes(result)),
                "result": result,
            }
            for sequence, (method, params, result) in enumerate(event_rows)
        ],
    }
    write_json(events_path, events)

    receipt = {
        "schema": "abl-phase4-live-run-receipt/2",
        "complete": True,
        "errors": [],
        "escalation_id": plan["escalation_ids"][0],
        "missing_fact_id": receipt_spec["missing_fact_id"],
        "precise": receipt_spec["precise"],
        "prelude_receipt": (
            artifact_ref(prelude_receipt, run_root)
            if prelude_receipt is not None else None
        ),
        "experiment": experiment,
        "evidence": {
            "raw_results": artifact_ref(raw_path, run_root),
            "pagination": artifact_ref(pagination_path, run_root),
            "media_capabilities": artifact_ref(media_path, run_root),
            "command_events": artifact_ref(events_path, run_root),
            "observer_plan": artifact_ref(observer_path, run_root),
            "perturbation_plan": artifact_ref(perturbation_path, run_root),
            "control_plan": artifact_ref(control_path, run_root),
            "adapter_source": {
                "scope": "repo",
                "path": "tools/phase4_duckstation_batch.py",
                "sha256": adapter_sha256,
            },
            "settings_snapshot": artifact_ref(settings_path, run_root),
            "owned_pid_cleanup": artifact_ref(cleanup_path, run_root),
            "external_preservation_manifest": {},
        },
    }
    if receipt["precise"] != (prelude_receipt is not None):
        raise RuntimeError("precise receipt/prelude relationship is invalid")
    evidence_paths = [
        raw_path, pagination_path, media_path, events_path, observer_path,
        perturbation_path, control_path, Path(__file__), settings_path,
        cleanup_path, batch_path, cleanup_raw_path,
    ]
    preservation = {
        "schema": "abl-phase4-method-external-preservation/1",
        "complete": True,
        "errors": [],
        "entries": [
            {
                "sha256": sha256(path),
                "size": path.stat().st_size,
                "media_class": (
                    "tool_source" if path.resolve() == Path(__file__).resolve()
                    else "runtime_receipt"
                ),
                "preservation_required": True,
            }
            for path in evidence_paths
        ],
    }
    digests = [row["sha256"] for row in preservation["entries"]]
    if len(digests) != len(set(digests)):
        raise RuntimeError("v2 receipt preservation identities are not unique")
    write_json(preservation_path, preservation)
    receipt["evidence"]["external_preservation_manifest"] = artifact_ref(
        preservation_path, run_root)
    write_json(receipt_path, receipt)
    return receipt_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--owned-pid", type=int)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--prelude-receipt", type=Path)
    args = parser.parse_args()
    plan = yaml.safe_load(args.plan.read_text())
    # Historical plan revalidation is read-only. Actual execution retains the
    # fail-closed requirement for a current planned escalation.
    errors = validate_plan(plan, allow_executed=args.validate_only)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.validate_only:
        print(f"PASS: {len(plan['jobs'])} atomic jobs and {len(plan['control_pairs'])} controls")
        return 0
    if args.port is None or not args.token or args.output is None:
        parser.error("live execution requires --port, --token and external --output")
    wants_receipt = args.receipt_dir is not None
    receipt_args = (
        args.run_root, args.config_dir, args.owned_pid, args.binary,
    )
    if wants_receipt and (plan.get("v2_receipt") is None or
                          any(value is None for value in receipt_args)):
        parser.error(
            "v2 receipt execution requires plan.v2_receipt, --run-root, "
            "--config-dir, --owned-pid and --binary")
    if not wants_receipt and any(value is not None for value in receipt_args) or \
            (not wants_receipt and args.prelude_receipt is not None):
        parser.error("receipt lifecycle arguments require --receipt-dir")
    cleanup = None
    cleanup_raw = None
    try:
        document = run_live(
            plan, args.port, args.token, args.output, args.poll_seconds)
    finally:
        if wants_receipt:
            cleanup, cleanup_raw = stop_owned_instance(
                args.config_dir.resolve(), args.binary.resolve(), args.owned_pid)
    if wants_receipt:
        if cleanup["complete"] is not True:
            raise RuntimeError("owned DuckStation cleanup did not close")
        receipt_path = emit_v2_receipt(
            plan, document, args.receipt_dir.resolve(),
            args.run_root.resolve(), cleanup, cleanup_raw,
            args.prelude_receipt.resolve()
            if args.prelude_receipt is not None else None,
        )
        print(f"closed live receipt: {receipt_path} sha256={sha256(receipt_path)}")
    result = document["result"]
    state = result.get("state") or result.get("status")
    print(f"batch {document['batch_id']}: {state}; output={args.output}")
    return 0 if state == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
