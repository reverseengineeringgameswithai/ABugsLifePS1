#!/usr/bin/env python3
"""Generate and validate the Phase-4 pre-run live-escalation ledger."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import phase4_common as common


SOURCE = common.ROOT / "config/phase4_live_escalations.yaml"
QUEUE = common.ROOT / "analysis/phase4_offline_opportunity_queue.json"
CAPSULES = common.ROOT / "analysis/phase4_trace_capsule_set.json"
OUTPUT = common.ROOT / "analysis/phase4_live_escalations.json"
REQUIRED = (
    "id", "target_row", "hypothesis", "relevant_capsules", "offline_queries",
    "answers_obtained", "missing_information", "live_experiment",
    "native_control", "expected_evidence", "priority_justification",
)
EXECUTION_REQUIRED = (
    "profiles", "collections", "runtime_executable_sha256", "media",
    "record_counts", "frame_chunks_byte_identical", "offline_analysis",
    "observed_answers",
)
ATOMIC_EXECUTION_REQUIRED = (
    "profiles", "external_receipts", "runtime_executable_sha256", "media",
    "record_counts", "banked_analysis", "observed_answers",
)
V2_EXECUTION_REQUIRED = ATOMIC_EXECUTION_REQUIRED + ("control_outcome",)
RECEIPT_PLAN_KEYS = {"schema", "receipts"}
RECEIPT_PLAN_ROW_KEYS = {
    "id", "movie", "movie_sha256", "precise", "observer_method",
    "atomic_method", "execution_bound", "capture_window",
    "prelude_receipt_id",
}
PRECISE_OBSERVER_METHODS = {
    "accessLog.addWatch", "execTrace.run", "functionTrace.start",
    "provenanceLog.start", "transferLog.start", "gpu.causality.start",
    "spu.trace.start", "movie.traceToFrame", "debugger.addBreakpoint",
}
PASSIVE_OBSERVER_METHODS = {
    "debugger.readMemory", "debugger.getRegisters",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _typed_range(
        entry_id: str, receipt_id: str, name: str, value: object,
        errors: list[str]) -> dict:
    if not isinstance(value, dict) or set(value) != {
            "clock", "start", "stop", "stop_inclusive"}:
        errors.append(
            f"{entry_id}: receipt {receipt_id} has malformed {name}")
        return {}
    if value.get("clock") not in {"emulator_frame", "movie_frame"} or \
            not all(isinstance(value.get(key), int) and
                    not isinstance(value.get(key), bool) and
                    value[key] >= 0 for key in ("start", "stop")) or \
            value.get("stop", -1) < value.get("start", 0) or \
            not isinstance(value.get("stop_inclusive"), bool):
        errors.append(
            f"{entry_id}: receipt {receipt_id} has invalid {name}")
        return {}
    return value


def validate_receipt_plan(
        entry_id: str, entry: dict, errors: list[str]) -> None:
    """Reject live plans that cannot produce admissible v2 receipts."""
    plan = entry.get("receipt_plan")
    if plan is None:
        errors.append(f"{entry_id}: planned entry lacks receipt_plan")
        return
    if not isinstance(plan, dict) or set(plan) != RECEIPT_PLAN_KEYS or \
            plan.get("schema") != "abl-phase4-live-receipt-plan/1":
        errors.append(f"{entry_id}: receipt_plan schema is invalid")
        return
    receipts = plan.get("receipts")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 128:
        errors.append(f"{entry_id}: receipt_plan requires 1..128 receipts")
        return
    fixtures = (common.load_json(common.FIXTURE_SET_PATH).get("entries") or {})
    by_id: dict[str, dict] = {}
    for row in receipts:
        if not isinstance(row, dict) or set(row) != RECEIPT_PLAN_ROW_KEYS:
            errors.append(f"{entry_id}: receipt_plan row schema is invalid")
            continue
        receipt_id = str(row.get("id") or "")
        if not receipt_id or receipt_id in by_id:
            errors.append(
                f"{entry_id}: receipt_plan has an empty/duplicate receipt ID")
            continue
        by_id[receipt_id] = row
        movie = row.get("movie")
        fixture = fixtures.get(movie)
        if not isinstance(movie, str) or not isinstance(fixture, dict) or \
                fixture.get("sha256") != row.get("movie_sha256") or \
                fixture.get("media_class") not in {
                    "pristine", "pristine_serial"} or \
                fixture.get("preservation_required") is not True:
            errors.append(
                f"{entry_id}: receipt {receipt_id} movie is not centrally "
                "pinned pristine evidence")
        method = row.get("observer_method")
        if method not in PRECISE_OBSERVER_METHODS | PASSIVE_OBSERVER_METHODS:
            errors.append(
                f"{entry_id}: receipt {receipt_id} observer is not closed")
        expected_precise = method in PRECISE_OBSERVER_METHODS
        if not isinstance(row.get("precise"), bool) or \
                row.get("precise") != expected_precise:
            errors.append(
                f"{entry_id}: receipt {receipt_id} precise flag disagrees "
                "with its observer")
        if row.get("atomic_method") != "scenario.runBatch":
            errors.append(
                f"{entry_id}: receipt {receipt_id} lacks scenario.runBatch")
        bound = _typed_range(
            entry_id, receipt_id, "execution_bound",
            row.get("execution_bound"), errors)
        capture = _typed_range(
            entry_id, receipt_id, "capture_window",
            row.get("capture_window"), errors)
        if bound and capture and (
                capture["clock"] != bound["clock"] or
                capture["start"] < bound["start"] or
                capture["stop"] > bound["stop"]):
            errors.append(
                f"{entry_id}: receipt {receipt_id} capture escapes its bound")
        prelude_id = row.get("prelude_receipt_id")
        if expected_precise and not isinstance(prelude_id, str):
            errors.append(
                f"{entry_id}: precise receipt {receipt_id} lacks prelude ID")
        elif not expected_precise and prelude_id is not None:
            errors.append(
                f"{entry_id}: passive receipt {receipt_id} names a prelude")
    for receipt_id, row in by_id.items():
        if not row.get("precise"):
            continue
        prelude = by_id.get(row.get("prelude_receipt_id"))
        if prelude is None or prelude.get("precise") is not False:
            errors.append(
                f"{entry_id}: precise receipt {receipt_id} prelude is absent "
                "or not passive")
            continue
        if (prelude.get("movie"), prelude.get("movie_sha256")) != \
                (row.get("movie"), row.get("movie_sha256")):
            errors.append(
                f"{entry_id}: precise receipt {receipt_id} changes anchor "
                "from its prelude")
        current = row.get("capture_window") or {}
        prior = prelude.get("capture_window") or {}
        strictly_wider = (
            current.get("clock") == prior.get("clock") and
            current.get("start", -1) >= prior.get("start", 0) and
            current.get("stop", 0) <= prior.get("stop", -1) and
            (current.get("start") > prior.get("start") or
             current.get("stop") < prior.get("stop"))
        )
        if not strictly_wider:
            errors.append(
                f"{entry_id}: precise receipt {receipt_id} lacks a strictly "
                "wider passive prelude")


def validate_execution(entry_id: str, entry: dict, current_capsules: list[dict],
                       errors: list[str]) -> None:
    """Validate retained execution evidence without trusting an authored pass flag."""
    result = entry.get("execution_result") or {}
    execution_kind = result.get("execution_kind", "trace_capsule_collection")
    if execution_kind == "v2_receipt_set":
        for key in V2_EXECUTION_REQUIRED:
            if result.get(key) in (None, "", []):
                errors.append(
                    f"{entry_id}: v2 receipt execution lacks "
                    f"execution_result.{key}")
        pre_run = entry.get("pre_run_audit") or {}
        for key in ("queue_sha256", "generated_ledger_sha256", "queue_counts",
                    "target_queue_rank", "target_classification",
                    "higher_priority_offline_ready_rows",
                    "relevant_capsule_count"):
            if key not in pre_run:
                errors.append(
                    f"{entry_id}: executed entry lacks pre_run_audit.{key}")
        if pre_run.get("target_classification") != "offline_partial" or \
                pre_run.get("relevant_capsule_count") != \
                len(entry.get("relevant_capsules") or []) or \
                pre_run.get("higher_priority_offline_ready_rows") != []:
            errors.append(
                f"{entry_id}: v2 pre-run audit does not retain the selected "
                "partial/capsule/priority condition")
        profiles = result.get("profiles") or []
        expected_profile_count = len(
            (entry.get("receipt_plan") or {}).get("receipts") or [])
        if len(profiles) != expected_profile_count or len({
                row.get("config_dir") for row in profiles}) != \
                expected_profile_count or len({
                row.get("port") for row in profiles}) != \
                expected_profile_count:
            errors.append(
                f"{entry_id}: v2 execution profile count differs from its "
                "receipt plan")
        for profile in profiles:
            if not str(profile.get("config_dir") or "").startswith(
                    "/var/tmp/") or profile.get("owned_pid_stopped") is not True:
                errors.append(
                    f"{entry_id}: v2 profile is not isolated/closed")
        rpc_manifest = common.load_json(
            common.ROOT / "analysis/phase3_duckstation_rpc_manifest.json")
        current_runtime = (
            rpc_manifest.get("binaries") or {}).get(
                "build-release/bin/duckstation-qt", {}).get("sha256")
        executed_runtime = result.get("runtime_executable_sha256")
        media = result.get("media") or {}
        if media.get("cue_sha256") != \
                "463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644" or \
                media.get("bin_sha256") != \
                "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566" or \
                media.get("mounted_serial") != "SCUS-94288":
            errors.append(f"{entry_id}: v2 execution media identity drifted")
        declared: set[tuple[str, str, int]] = set()
        receipt_runtime_hashes: set[str] = set()
        batch_runtime_hashes: set[str] = set()
        for receipt in result.get("external_receipts") or []:
            path = Path(str(receipt.get("absolute_path") or ""))
            digest = receipt.get("sha256")
            size = receipt.get("bytes")
            if not path.is_file() or sha256(path) != digest or \
                    path.stat().st_size != size:
                errors.append(f"{entry_id}: v2 external receipt drifted")
                continue
            declared.add((str(path), digest, size))
            try:
                retained = common.load_json(path)
            except (OSError, json.JSONDecodeError):
                errors.append(
                    f"{entry_id}: v2 external receipt is not retained JSON")
                continue
            schema = retained.get("schema")
            if schema == "abl-phase4-live-run-receipt/2":
                receipt_runtime_hashes.add(str(
                    (retained.get("experiment") or {}).get(
                        "duckstation_executable_sha256") or ""))
            elif schema in {
                    "abl-phase4-duckstation-batch-result/1",
                    "abl-phase4-fmv-levelb-region-b-dma-exact-pc-live-result/1",
                    "abl-phase4-fmv-levelb-two-pc-first-hit-live-result/1",
            }:
                identity_hash = str(
                    ((retained.get("identity_results") or {}).get(
                        "debugger.capabilities") or {}).get(
                            "binary", {}).get("sha256") or "")
                if schema == "abl-phase4-duckstation-batch-result/1":
                    capability_hash = str(
                        (retained.get("capabilities") or {}).get(
                            "binary", {}).get("sha256") or "")
                    expected_hash = str(
                        (retained.get("expected_debugger") or {}).get(
                            "binary_sha256") or "")
                else:
                    capability_hash = str(
                        (retained.get("normalized_identity") or {}).get(
                            "executable_sha256") or "")
                    expected_hash = identity_hash
                if len({capability_hash, identity_hash, expected_hash}) != 1:
                    errors.append(
                        f"{entry_id}: retained v2 batch runtime identities "
                        "disagree")
                batch_runtime_hashes.add(capability_hash)
            else:
                errors.append(
                    f"{entry_id}: v2 external receipt schema is not closed")
        if receipt_runtime_hashes != {executed_runtime} or \
                batch_runtime_hashes != {executed_runtime}:
            errors.append(
                f"{entry_id}: retained v2 runtime identity does not join its "
                "receipt and batch results")
        entry["derived_runtime_identity"] = {
            "executed_sha256": executed_runtime,
            "current_manifest_sha256": current_runtime,
            "current_manifest_match": executed_runtime == current_runtime,
            "retained_receipt_and_batch_match": (
                receipt_runtime_hashes == {executed_runtime}
                and batch_runtime_hashes == {executed_runtime}
            ),
            "classification": (
                "current" if executed_runtime == current_runtime
                else "historical_exact_not_current"
            ),
        }
        analysis = result.get("banked_analysis") or {}
        analysis_path = common.ROOT / str(analysis.get("path") or "")
        analysis_doc = None
        if not analysis_path.is_file() or \
                common.sha256(analysis_path) != analysis.get("sha256"):
            errors.append(
                f"{entry_id}: v2 banked analysis is missing/hash-mismatched")
        else:
            analysis_doc = common.load_json(analysis_path)
            analysis_view = analysis_doc
            historical = analysis_doc.get("historical_unstaged_attempt")
            if isinstance(historical, dict) and \
                    historical.get("escalation_id") == entry_id:
                analysis_view = historical
            expected_hashes = {
                row[key] for row in analysis_view.get("receipts") or []
                for key in ("receipt_sha256", "batch_result_sha256")
            }
            if {row[1] for row in declared} != expected_hashes:
                errors.append(
                    f"{entry_id}: v2 receipt/result preservation set drifted")
            if result.get("record_counts") != analysis_view.get(
                    "record_counts"):
                errors.append(
                    f"{entry_id}: v2 execution record counts drifted")
            if result.get("control_outcome") != \
                    (analysis_view.get("falsifier") or {}).get("outcome"):
                errors.append(
                    f"{entry_id}: v2 control outcome drifted")
        return
    if execution_kind in {
            "atomic_batch_control", "phase_neutral_movie_control"}:
        for key in ATOMIC_EXECUTION_REQUIRED:
            if result.get(key) in (None, "", []):
                errors.append(
                    f"{entry_id}: controlled execution lacks "
                    f"execution_result.{key}")
        pre_run = entry.get("pre_run_audit") or {}
        for key in ("queue_sha256", "generated_ledger_sha256", "queue_counts",
                    "target_queue_rank", "target_classification",
                    "higher_priority_offline_ready_rows", "relevant_capsule_count"):
            if key not in pre_run:
                errors.append(f"{entry_id}: executed entry lacks pre_run_audit.{key}")
        for key in ("queue_sha256", "generated_ledger_sha256"):
            value = str(pre_run.get(key) or "")
            if len(value) != 64 or any(
                    character not in "0123456789abcdef" for character in value):
                errors.append(f"{entry_id}: pre_run_audit.{key} is not a SHA-256")
        if pre_run.get("target_classification") != "offline_partial" or \
                pre_run.get("relevant_capsule_count") != \
                len(entry.get("relevant_capsules") or []):
            errors.append(
                f"{entry_id}: pre-run audit does not retain the selected partial/capsule condition")
        if pre_run.get("higher_priority_offline_ready_rows") != []:
            errors.append(f"{entry_id}: pre-run audit had a higher-priority offline-ready row")
        profiles = result.get("profiles") or []
        if len(profiles) < 1 or len({row.get("config_dir") for row in profiles}) != len(profiles):
            errors.append(
                f"{entry_id}: controlled execution profiles are absent or duplicated")
        for profile in profiles:
            config_dir = Path(str(profile.get("config_dir") or ""))
            if not str(config_dir).startswith("/var/tmp/") or \
                    not profile.get("owned_pid_stopped"):
                errors.append(
                    f"{entry_id}: controlled profile is not isolated or its retained "
                    "PID cleanup declaration is incomplete")
        expected_runtime = (common.load_json(CAPSULES).get(
            "duckstation_runtime_bundle") or {}).get("executable", {}).get("sha256")
        if result.get("runtime_executable_sha256") != expected_runtime:
            errors.append(f"{entry_id}: execution runtime does not match preserved runtime")
        media = result.get("media") or {}
        if media.get("cue_sha256") != "463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644" or \
                media.get("bin_sha256") != \
                "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566" or \
                media.get("mounted_serial") != "SCUS-94288":
            errors.append(f"{entry_id}: controlled execution media identity drifted")
        superseded_by = str(result.get("superseded_by") or "")
        if superseded_by:
            reason = str(result.get("supersession_reason") or "").strip()
            if len(reason) < 30:
                errors.append(
                    f"{entry_id}: superseded execution lacks a bounded reason")
            for receipt in result.get("external_receipts") or []:
                receipt_path = Path(str(receipt.get("absolute_path") or ""))
                if not receipt_path.is_file() or \
                        sha256(receipt_path) != receipt.get("sha256") or \
                        receipt_path.stat().st_size != receipt.get("bytes"):
                    errors.append(
                        f"{entry_id}: superseded external receipt drifted")
            return
        analysis = result.get("banked_analysis") or {}
        analysis_path = common.ROOT / str(analysis.get("path") or "")
        analysis_doc = None
        if not analysis_path.is_file() or common.sha256(analysis_path) != analysis.get("sha256"):
            errors.append(
                f"{entry_id}: banked controlled analysis is missing or "
                "hash-mismatched")
        else:
            analysis_doc = common.load_json(analysis_path)
            preserved = {
                (row.get("absolute_path"), row.get("sha256"), row.get("bytes"))
                for row in analysis_doc.get("external_receipts") or []
            }
            declared = {
                (row.get("absolute_path"), row.get("sha256"), row.get("bytes"))
                for row in result.get("external_receipts") or []
            }
            if declared != preserved or any(
                    not Path(path).is_file() or sha256(Path(path)) != digest or
                    Path(path).stat().st_size != size
                    for path, digest, size in declared):
                errors.append(
                    f"{entry_id}: external controlled receipt preservation drifted")
        counts = result.get("record_counts") or {}
        expected_counts = analysis_doc.get("record_counts") \
            if analysis_doc is not None else None
        if expected_counts is None:
            # Compatibility for the first banked atomic artifact, whose
            # tracked schema predated a top-level record-count summary.
            expected_counts = {
                "atomic_batches": 3, "jobs": 6, "function_events": 16}
        if counts != expected_counts:
            errors.append(
                f"{entry_id}: controlled execution record counts drifted")
        return
    if execution_kind != "trace_capsule_collection":
        errors.append(f"{entry_id}: unsupported execution_result.execution_kind")
        return
    for key in EXECUTION_REQUIRED:
        if result.get(key) in (None, "", []):
            errors.append(f"{entry_id}: executed entry lacks execution_result.{key}")
    pre_run = entry.get("pre_run_audit") or {}
    for key in ("queue_sha256", "generated_ledger_sha256", "queue_counts",
                "target_queue_rank", "target_classification",
                "higher_priority_offline_ready_rows", "relevant_capsule_count"):
        if key not in pre_run:
            errors.append(f"{entry_id}: executed entry lacks pre_run_audit.{key}")
    for key in ("queue_sha256", "generated_ledger_sha256"):
        value = str(pre_run.get(key) or "")
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            errors.append(f"{entry_id}: pre_run_audit.{key} is not a SHA-256")
    if pre_run.get("target_classification") != "live_required" or \
            pre_run.get("relevant_capsule_count") != 0:
        errors.append(f"{entry_id}: pre-run audit does not retain the missing-capsule condition")
    if pre_run.get("higher_priority_offline_ready_rows") != []:
        errors.append(f"{entry_id}: pre-run audit had a higher-priority offline-ready row")

    profiles = result.get("profiles") or []
    if len(profiles) != 2 or len({row.get("config_dir") for row in profiles}) != 2 or \
            len({row.get("port") for row in profiles}) != 2:
        errors.append(f"{entry_id}: execution did not retain two distinct isolated profiles")
    for profile in profiles:
        config_dir = str(profile.get("config_dir") or "")
        if not config_dir.startswith("/var/tmp/") or not profile.get("owned_pid_stopped"):
            errors.append(f"{entry_id}: profile is not isolated under /var/tmp or owned PID was not stopped")
    runtime_hash = result.get("runtime_executable_sha256")
    expected_runtime = (common.load_json(CAPSULES).get("duckstation_runtime_bundle") or {}).get(
        "executable", {}).get("sha256")
    if runtime_hash != expected_runtime:
        errors.append(f"{entry_id}: execution runtime does not match the preserved capsule runtime")

    collection_rows = result.get("collections") or []
    if len(collection_rows) != 2:
        errors.append(f"{entry_id}: execution does not retain two collection roots")
    for collection in collection_rows:
        root = Path(str(collection.get("root") or ""))
        for name, key in (("collection.json", "collection_manifest_sha256"),
                          ("batch.json", "batch_manifest_sha256")):
            path = root / name
            if not path.is_file() or sha256(path) != collection.get(key):
                errors.append(f"{entry_id}: retained {name} pin mismatch under {root}")
    if result.get("frame_chunks_byte_identical") is not True:
        errors.append(f"{entry_id}: independent frame chunks are not byte-identical")
    expected_records = sum(int(row.get("frames") or 0) + 1 for row in current_capsules)
    if result.get("record_counts", {}).get("total") != expected_records:
        errors.append(f"{entry_id}: execution record count does not match current capsules")
    analysis = result.get("offline_analysis") or {}
    analysis_path = common.ROOT / str(analysis.get("path") or "")
    if not analysis_path.is_file() or common.sha256(analysis_path) != analysis.get("sha256"):
        errors.append(f"{entry_id}: offline analysis artifact is missing or hash-mismatched")


def stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = json.loads(OUTPUT.read_text()).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


def build(source: dict | None = None, queue: dict | None = None,
          capsules: dict | None = None) -> dict:
    source = source or common.load_yaml(SOURCE)
    queue = queue or common.load_json(QUEUE)
    capsules = capsules or common.load_json(CAPSULES)
    errors: list[str] = []
    if source.get("schema") != "abl-phase4-live-escalation-source/1":
        errors.append("live escalation source schema is invalid")
    if queue.get("schema") != "abl-phase4-offline-opportunity-queue/1" or not queue.get("valid"):
        errors.append("offline opportunity queue is absent or invalid")
    rows = {row["row_id"]: row for row in queue.get("rows") or []}
    capsule_rows = {row["movie"]: row for row in capsules.get("capsules") or []}
    entries: list[dict] = []
    seen: set[str] = set()
    for raw in source.get("entries") or []:
        entry = dict(raw)
        entry_id = str(entry.get("id") or "")
        if entry_id in seen:
            errors.append(f"duplicate escalation ID: {entry_id}")
        seen.add(entry_id)
        for key in REQUIRED:
            value = entry.get(key)
            empty_capsule_set = key == "relevant_capsules" and value == []
            if value is None or value == "" or (value == [] and not empty_capsule_set):
                errors.append(f"{entry_id or '<missing>'}: required field {key} is empty")
        target = rows.get(entry.get("target_row"))
        if not target:
            errors.append(f"{entry_id}: target row is absent from the current queue")
            entries.append(entry)
            continue
        if target.get("current_completion_state") != "open":
            errors.append(f"{entry_id}: target row is not open")
        state = entry.get("state", "planned")
        if state not in {"planned", "executed"}:
            errors.append(f"{entry_id}: state must be planned or executed")
        execution_kind = (entry.get("execution_result") or {}).get(
            "execution_kind", "trace_capsule_collection")
        typed_v2 = execution_kind == "v2_receipt_set"
        if (state == "planned" or typed_v2) and not str(
                entry.get("missing_fact_id") or "").strip():
            errors.append(
                f"{entry_id}: typed entry lacks missing_fact_id")
        if state == "planned" or typed_v2:
            validate_receipt_plan(entry_id, entry, errors)
        historical_atomic = state == "executed" and \
            execution_kind == "atomic_batch_control"
        declared_capsules = entry.get("relevant_capsules") or []
        expected_capsules = {row["movie"] for row in target.get("relevant_capsules") or []}
        observed_capsules = {
            row.get("movie") if isinstance(row, dict) else row
            for row in declared_capsules
        }
        if historical_atomic:
            retained_count = (entry.get("pre_run_audit") or {}).get(
                "relevant_capsule_count")
            if not observed_capsules <= expected_capsules or \
                    retained_count != len(observed_capsules):
                errors.append(
                    f"{entry_id}: historical atomic capsule set does not match "
                    "its retained pre-run audit or current capsule identities")
        elif observed_capsules != expected_capsules:
            errors.append(
                f"{entry_id}: relevant capsules do not exhaust the queue row: "
                f"observed={sorted(observed_capsules)} expected={sorted(expected_capsules)}")
        for row in declared_capsules:
            if not isinstance(row, dict):
                errors.append(f"{entry_id}: capsule declaration must include current hashes")
                continue
            current = capsule_rows.get(row.get("movie"))
            if not current:
                errors.append(f"{entry_id}: unknown capsule {row.get('movie')}")
                continue
            for key in ("movie_sha256", "capsule_manifest_sha256", "capsule_tree_sha256"):
                if row.get(key) != current.get(key):
                    errors.append(f"{entry_id}: stale {key} for {row.get('movie')}")
        queries = entry.get("offline_queries") or []
        for index, query in enumerate(queries):
            if not isinstance(query, dict) or not all(
                    query.get(key) for key in ("command", "window", "domains", "answer")):
                errors.append(f"{entry_id}: offline query {index} lacks command/window/domains/answer")
        for key in ("missing_information", "live_experiment", "native_control",
                    "expected_evidence"):
            if len(str(entry.get(key) or "").strip()) < 30:
                errors.append(f"{entry_id}: {key} is too generic")
        missing_text = " ".join(
            str(entry.get("missing_information") or "").lower().split())
        if any(phrase in missing_text for phrase in (
                "needs exact causality/control",
                "needs exact causality and control",
                "requires exact causality/control")):
            errors.append(
                f"{entry_id}: missing_information uses forbidden generic causality wording")
        justification = entry.get("priority_justification") or {}
        if not isinstance(justification, dict) or not all(
                str(justification.get(key) or "").strip()
                for key in ("reason", "higher_priority_offline_ready", "load_bearing_evidence")):
            errors.append(f"{entry_id}: priority justification is incomplete")
        elif len(str(justification.get("reason") or "").strip()) < 30:
            errors.append(f"{entry_id}: priority justification reason is too generic")
        higher = [
            row["row_id"] for row in queue.get("rows") or []
            if row["priority"]["rank"] < target["priority"]["rank"]
            and row["current_completion_state"] == "open"
            and row["classification"] == "offline_ready"
        ]
        current_audit = {
            "target_queue_rank": target["priority"]["rank"],
            "target_classification": target["classification"],
            "higher_priority_offline_ready_rows": higher,
            "queue_source_hashes": queue.get("inputs"),
        }
        if state == "executed":
            validate_execution(entry_id, entry, target.get("relevant_capsules") or [], errors)
            entry["derived_pre_run_audit"] = entry.get("pre_run_audit")
            entry["derived_post_run_audit"] = current_audit
        else:
            entry["derived_pre_run_audit"] = current_audit
        if higher and not str(justification.get("load_bearing_evidence") or "").strip():
            errors.append(f"{entry_id}: higher-priority offline-ready rows are not displaced by evidence")
        entries.append(entry)
    entries_by_id = {
        str(entry.get("id") or ""): entry for entry in entries
    }
    for entry in entries:
        superseded_by = str(
            (entry.get("execution_result") or {}).get("superseded_by") or "")
        if not superseded_by:
            continue
        superseding = entries_by_id.get(superseded_by)
        if superseding is None:
            errors.append(
                f"{entry.get('id')}: superseding escalation {superseded_by} "
                "is absent")
        elif superseding is entry:
            errors.append(
                f"{entry.get('id')}: an escalation cannot supersede itself")
        elif superseding.get("state") != "executed":
            errors.append(
                f"{entry.get('id')}: superseding escalation {superseded_by} "
                "is not executed")
        elif superseding.get("target_row") != entry.get("target_row"):
            errors.append(
                f"{entry.get('id')}: superseding escalation {superseded_by} "
                "targets a different row")
    return {
        "_comment": "Generated pre-run Phase-4 live-escalation ledger. An empty ledger authorizes no live run.",
        "schema": "abl-phase4-live-escalations/1",
        "generated": stable_generated(),
        "inputs": {
            "source_sha256": common.sha256(SOURCE),
            "queue_sha256": common.sha256(QUEUE),
            "capsule_index_sha256": common.sha256(CAPSULES),
        },
        "entries": entries,
        "counts": {
            "entries": len(entries),
            "planned": sum(row.get("state", "planned") == "planned" for row in entries),
            "executed": sum(row.get("state") == "executed" for row in entries),
        },
        "errors": sorted(set(errors)),
        "valid": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if document["errors"]:
        for error in document["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.write:
        OUTPUT.write_text(rendered)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            print("phase4 live-escalation ledger is missing or stale", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    print(f"PASS: {len(document['entries'])} live escalation entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
