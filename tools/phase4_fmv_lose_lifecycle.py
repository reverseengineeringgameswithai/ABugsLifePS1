#!/usr/bin/env python3
"""Validate and summarize the C16 natural LOSE lifecycle receipts."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path

import yaml

import phase4_common as common


CONFIG_PATH = common.ROOT / "config/phase4_fmv_lose_lifecycle.yaml"
OUTPUT = common.ROOT / "analysis/phase4_fmv_lose_lifecycle.json"
CONFIGURATION = common.load_yaml(CONFIG_PATH)
EXTERNAL_ROOT = Path(os.environ.get(
    "ABL_EXTERNAL_EVIDENCE_ROOT",
    str(Path.home() / "Downloads" / "ABL-external-evidence"))).resolve()
OPERATOR_ROOT = Path(os.environ.get(
    "ABL_OPERATOR_ROOT", str(Path.home() / "Downloads" / "ABL"))).resolve()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


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


def _little(row: dict) -> int:
    return int.from_bytes(bytes.fromhex(row["hex"]), "little")


def _memory(capture: dict) -> dict[str, dict]:
    rows = capture.get("memory") or []
    return {row["label"]: row for row in rows}


def _receipt(role: str, *, verify_identity: bool = True) -> tuple[Path, dict]:
    spec = next(
        row for row in CONFIGURATION["external_receipts"]
        if row["role"] == role)
    path = EXTERNAL_ROOT / spec["relative_path"]
    if verify_identity:
        _require(
            path.is_file() and path.stat().st_size == spec["bytes"] and
            common.sha256(path) == spec["sha256"],
            f"{role} receipt identity drifted")
    return path, common.load_json(path)


def validate_fixtures() -> dict:
    spec = CONFIGURATION["fixture"]
    rows = {}
    for label in ("movie", "state"):
        path = OPERATOR_ROOT / spec[f"{label}_path"]
        _require(
            path.is_file() and path.stat().st_size == spec[f"{label}_bytes"] and
            common.sha256(path) == spec[f"{label}_sha256"],
            f"C16 {label} identity drifted")
        rows[label] = {
            "path": spec[f"{label}_path"],
            "sha256": spec[f"{label}_sha256"],
            "bytes": spec[f"{label}_bytes"],
            "media_class":
                "pristine_serial" if label == "movie" else "pristine",
        }
    return rows


def validate_cleanup(role: str, profile: dict) -> dict:
    _path, receipt = _receipt(role)
    debugger = CONFIGURATION["debugger"]
    _require(
        receipt.get("schema") == "abl-phase4-owned-pid-cleanup/1" and
        receipt.get("config_dir") == profile["config_dir"] and
        receipt.get("owned_pid") == profile["owned_pid"] and
        receipt.get("instance_pid_absent_after_stop") is True and
        receipt.get("owned_pid_alive_after_stop") is False and
        receipt.get("credentials_retained") is False and
        receipt.get("runtime_executable_sha256") ==
        debugger["binary_sha256"],
        f"{role} cleanup payload drifted")
    return receipt


def _validate_capabilities(document: dict) -> None:
    debugger = CONFIGURATION["debugger"]
    capabilities = document.get("capabilities") or {}
    _require(
        (capabilities.get("api") or {}).get("version") ==
        debugger["api_version"] and
        (capabilities.get("api") or {}).get("schema_version") ==
        debugger["schema_version"] and
        (capabilities.get("binary") or {}).get("sha256") ==
        debugger["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        debugger["source_revision"] and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        debugger["source_dirty_state_hash"],
        "debugger capability identity drifted")


def validate_atomic_attempt(document: dict) -> dict:
    expected = CONFIGURATION["expected"]["failed_positive"]
    _require(
        document.get("schema") ==
        "abl-phase4-duckstation-batch-result/1" and
        document.get("plan_sha256") ==
        CONFIGURATION["batch_plan"]["canonical_sha256"],
        "frame-zero batch identity drifted")
    _validate_capabilities(document)
    result = document.get("result") or {}
    _require(
        result.get("state") == "completed" and
        result.get("total_jobs") == result.get("processed_jobs") ==
        result.get("succeeded_jobs") == 2 and
        result.get("failed_jobs") == 0,
        "frame-zero batch completion drifted")
    jobs = {row["id"]: row for row in result.get("jobs") or []}
    _require(
        set(jobs) == {
            "gameover_movie_positive", "gameover_no_input_control"},
        "frame-zero control job set drifted")
    summaries = {}
    endpoint_memory = None
    for job_id, job in jobs.items():
        payload = job["result"]
        capture = payload["capture"]
        access = capture["traces"]["access"]
        watches = {row["label"]: row for row in access["watches"]}
        memory = _memory(capture)
        summary = {
            "frame": capture["frame"],
            "cycle": capture["cycle"],
            "scene": _little(memory["scene"]),
            "movie_playback_index": payload["movie"]["playback_index"],
            "movie_reproducible": payload["movie"]["reproducible"],
            "function_events": len(capture["traces"]["functions"]),
            "selected_limit_hits": watches[
                "selected_frame_limit"]["hit_count"],
            "completion_hits": watches["completion_request"]["hit_count"],
            "access_ring_truncated": access["truncated"],
        }
        _require(
            summary["frame"] == expected["endpoint_frame"] and
            summary["cycle"] == expected["endpoint_cycle"] and
            summary["scene"] == expected["scene"] and
            summary["function_events"] ==
            expected["precise_function_events"] and
            summary["selected_limit_hits"] ==
            expected["selected_limit_hits"] and
            summary["completion_hits"] == expected["completion_hits"] and
            summary["access_ring_truncated"] is False,
            f"{job_id}: failed-attempt boundary drifted")
        current_memory = [
            (row["label"], row["hex"]) for row in capture["memory"]]
        if endpoint_memory is None:
            endpoint_memory = current_memory
        else:
            _require(
                current_memory == endpoint_memory,
                "failed positive and no-input endpoint memory differ")
        summaries[job_id] = summary
    _require(
        summaries["gameover_movie_positive"]["movie_playback_index"] ==
        expected["playback_index"] and
        summaries["gameover_movie_positive"]["movie_reproducible"] is False and
        summaries["gameover_no_input_control"]["movie_playback_index"] == 0 and
        summaries["gameover_no_input_control"]["movie_reproducible"] is True,
        "observer-desync classification drifted")
    return summaries


def _project_stop(row: dict) -> dict:
    return {
        "frame": row["frame"], "cycle": row["cycle"],
        "address": row["address"], "caller": row["caller"],
        "return_address": row["ra"], "arguments": row["arguments"],
    }


def validate_staged(document: dict) -> dict:
    expected = CONFIGURATION["expected"]
    _require(
        document.get("schema") == "abl-phase4-fmv-lose-staged-live/1" and
        document.get("method", {}).get("stage_movie_frame") ==
        expected["cached_stage"]["movie_frame"],
        "staged receipt identity drifted")
    _validate_capabilities(document)
    stage = document["cached_stage"]
    comparison = stage["trace"]["comparison"]
    fingerprint = stage["fingerprint"]
    stage_expected = expected["cached_stage"]
    _require(
        comparison == {
            "cycle_neutral": True, "same_cycle": True,
            "same_frame": True, "same_ram": True,
            "same_registers": True} and
        stage["movie_status"]["reproducible"] is True and
        stage["movie_status"]["truncated"] is False and
        stage["movie_status"]["playback_index"] ==
        stage_expected["movie_frame"] and
        fingerprint["frame"] == stage_expected["emulator_frame"] and
        fingerprint["pc"] == stage_expected["pc"] and
        fingerprint["ram_sha256"] == stage_expected["ram_sha256"] and
        fingerprint["vram_sha256"] == stage_expected["vram_sha256"] and
        fingerprint["spu_ram_sha256"] == stage_expected["spu_ram_sha256"],
        "cached stage or retained capsule-domain join drifted")

    observations = document["observations"]
    loader = observations["loader"]
    loader_expected = expected["loader"]
    entry = _project_stop(loader["entry"])
    _require(
        entry == {
            **loader_expected["entry"],
            "return_address": loader_expected["entry"]["return_address"]} and
        loader["return"]["frame"] == loader_expected["return"]["frame"] and
        loader["return"]["cycle"] == loader_expected["return"]["cycle"] and
        loader["return"]["address"] == loader_expected["return"]["address"] and
        loader["return"]["v0"] == loader_expected["return"]["v0"],
        "LOSE loader entry/return provenance drifted")

    rings = observations["st_clear_ring_calls"]
    _require(len(rings) == len(expected["ring_calls"]),
             "StClearRing call count drifted")
    ring_summary = []
    for row, wanted in zip(rings, expected["ring_calls"]):
        summary = {
            "frame": row["entry"]["frame"],
            "entry_cycle": row["entry"]["cycle"],
            "exit_cycle": row["return"]["cycle"],
            "caller": row["entry"]["caller"],
            "return_address": row["entry"]["ra"],
        }
        _require(summary == wanted, "StClearRing ordering drifted")
        ring_summary.append(summary)
    callback = observations["callback_teardown"]
    callback_summary = {
        "frame": callback["entry"]["frame"],
        "entry_cycle": callback["entry"]["cycle"],
        "exit_cycle": callback["return"]["cycle"],
        "caller": callback["entry"]["caller"],
        "return_address": callback["entry"]["ra"],
    }
    _require(
        callback_summary == expected["callback_teardown"],
        "callback teardown ordering drifted")

    capture = observations["atomic_after_loader_return"]
    access = capture["traces"]["access"]
    watches = {
        row["watch_id"]: row["label"] for row in access["watches"]}
    event_summary = [{
        "label": watches[row["watch_id"]],
        "frame": row["frame"], "cycle": row["cycle"],
        "instruction_pc": row["instruction_pc"],
        "old_value": row["value"], "new_value": row["new_value"],
    } for row in access["events"]]
    _require(
        access["truncated"] is False and access["total"] == 3 and
        event_summary == expected["access_events"],
        "LOSE selected-limit/completion provenance drifted")
    memory = _memory(capture)
    endpoint = expected["endpoint"]
    endpoint_summary = {
        "movie_frame": capture["movie"]["playback_index"],
        "frame": capture["frame"], "cycle": capture["cycle"],
        "scene": _little(memory["scene"]),
        "fmv_running_latch": _little(memory["fmv_running_latch"]),
        "completion_request": _little(memory["completion_request"]),
        "selected_frame_limit": _little(memory["selected_frame_limit"]),
        "movie_reproducible": capture["movie"]["reproducible"],
        "fmv_bin_head_sha256": hashlib.sha256(
            bytes.fromhex(memory["fmv_bin_head"]["hex"])).hexdigest(),
    }
    _require(
        {key: endpoint_summary[key] for key in endpoint} == endpoint and
        endpoint_summary["movie_reproducible"] is True and
        endpoint_summary["fmv_bin_head_sha256"] ==
        "ab33c20549aa18877259dbd83cc4925c9ea24db0e160b3f450eaad29551954db",
        "LOSE loader-return endpoint drifted")
    return {
        "cached_stage": {
            "comparison": comparison,
            "movie_frame": stage_expected["movie_frame"],
            "emulator_frame": stage_expected["emulator_frame"],
            "domain_hashes": {
                "ram": fingerprint["ram_sha256"],
                "vram": fingerprint["vram_sha256"],
                "spu_ram": fingerprint["spu_ram_sha256"],
            },
        },
        "loader": {"entry": entry, "return": loader["return"]},
        "ring_calls": ring_summary,
        "callback_teardown": callback_summary,
        "access_events": event_summary,
        "endpoint": endpoint_summary,
    }


def build() -> dict:
    errors = []
    fixtures = {}
    attempt = {}
    staged = {}
    receipts = []
    try:
        fixtures = validate_fixtures()
        for spec in CONFIGURATION["external_receipts"]:
            path, _document = _receipt(spec["role"])
            receipts.append({
                "role": spec["role"], "absolute_path": str(path),
                "sha256": spec["sha256"], "bytes": spec["bytes"]})
        _attempt_path, attempt_doc = _receipt("frame_zero_atomic_attempt")
        attempt = validate_atomic_attempt(attempt_doc)
        _staged_path, staged_doc = _receipt("staged_positive")
        staged = validate_staged(staged_doc)
        validate_cleanup(
            "frame_zero_owned_pid_cleanup",
            CONFIGURATION["profiles"][0])
        validate_cleanup(
            "staged_owned_pid_cleanup",
            CONFIGURATION["profiles"][1])
    except (OSError, KeyError, StopIteration, TypeError, ValueError) as error:
        errors.append(str(error))
    record_counts = {
        "atomic_batches": 1,
        "jobs": 2,
        "failed_positive_function_events": (
            attempt.get("gameover_movie_positive", {}).get(
                "function_events", 0)),
        "cached_control_pairs": 1 if staged else 0,
        "staged_exact_stops": (
            2 + 2 * len(staged.get("ring_calls") or []) + 2
            if staged else 0),
        "staged_access_events": len(staged.get("access_events") or []),
    }
    return {
        "_comment": (
            "Natural C16 game-over LOSE interface evidence. The invalid "
            "frame-zero positive is retained as observer-desync provenance."),
        "schema": CONFIGURATION["tracked_summary"]["schema"],
        "generated": stable_generated(),
        "campaign_id": CONFIGURATION["campaign_id"],
        "row_id": CONFIGURATION["row_id"],
        "escalation_id": CONFIGURATION["escalation_id"],
        "valid": not errors,
        "errors": errors,
        "fixtures": fixtures,
        "external_receipts": receipts,
        "profiles": CONFIGURATION["profiles"],
        "record_counts": record_counts,
        "observations": {
            "frame_zero_attempt": attempt,
            "natural_lose": staged,
        },
        "claims": {
            "observation": (
                "A cycle-neutral cached prelude reaches fmv_bin_load from "
                "0x800500D8 with selector 46/mode 0. The player selects limit "
                "281, publishes completion, executes initialization and common "
                "exit StClearRing calls, then callback teardown and returns."),
            "inference": (
                "The static direct-call census and LOSE.STR manifest case "
                "identify this as the natural game-over LOSE stream."),
            "causal_confirmation": (
                "Exact entry/return stops and instruction-attributed writes "
                "bind the runtime caller, arguments, limit, completion and "
                "teardown sequence. The same-save no-input job reaches none of "
                "those events."),
        },
        "residuals": [
            (
                "The frame-zero movie-positive precise observer changed input "
                "reproducibility; only the staged positive is behavioral "
                "evidence, while the failed attempt remains provenance."),
            (
                "One C16 game-over anchor does not establish alternate "
                "continue/quit choices, repeat, pause, viewer, CD/decode "
                "failure or malformed-stream behavior."),
            (
                "This adds a distinct natural LOSE lifecycle and cross-system "
                "join but does not promote lifecycle, campaign breadth, "
                "cross-system behavior or original interfaces."),
        ],
        "raw_external_bytes_committed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = render(document)
    if document["errors"]:
        for error in document["errors"]:
            print(f"ERROR: {error}")
        return 1
    if args.write:
        OUTPUT.write_bytes(rendered)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_bytes() != rendered:
            print("phase4 FMV LOSE lifecycle artifact is stale")
            return 1
    if not args.write and not args.check:
        print(rendered.decode(), end="")
    print(
        "PASS: C16 LOSE selector 46, limit 281, balanced common teardown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
