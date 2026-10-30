#!/usr/bin/env python3
"""Validate and summarize the evidence chain for the Phase-4 method trial.

The retained manifest is deliberately a locator, not a scorecard.  Every metric in
the summary is derived from hash-bound evidence.  This is the executable companion
to ``Phase 4 - Reverse Engineering Operating Method.md``.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "abl-phase4-method-metrics/2"
TRIAL_SCHEMA = "abl-phase4-method-trial-root/1"
SUMMARY_SCHEMA = "abl-phase4-method-metrics-summary/2"
LIVE_SCHEMA = "abl-phase4-live-run-receipt/2"
OFFLINE_SCHEMA = "abl-phase4-offline-query/1"
TERMINAL_FAILURE_SCHEMA = "abl-phase4-method-terminal-failure/1"
LEGACY_SCHEMA = "abl-phase4-method-legacy-live-index/2"
LEGACY_SOURCE_PROJECTION = "exclude-derived-post-run-audit/1"
REF_KEYS = {"scope", "path", "sha256"}
MANIFEST_KEYS = {
    "schema", "iteration", "campaign_id", "row_ids", "base_commit",
    "tested_commit", "started_at", "finished_at", "validator", "evidence",
}
EVIDENCE_KEYS = {
    "debt_before", "debt_after", "progress_receipt",
    "offline_query_receipts", "live_run_receipts",
    "escalation_ledger_before", "escalation_ledger_after",
    "verifier_decision", "controller_events", "command_log",
    "validation_report", "knowledge_report", "vault_report",
    "clean_checkout_report",
}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
LIVE_ADAPTER_PATH = re.compile(
    r"tools/(?:phase4_duckstation_batch|"
    r"phase4_duckstation_late_batch|"
    r"phase4_duckstation_exact_pc_batch|"
    r"phase4_duckstation_two_pc_first_hit|"
    r"phase4_[a-z0-9_]+_live)\.py"
)
REPORT_KEYS = {
    "schema", "tested_commit", "generated_at", "complete", "errors", "checks",
}
CHECK_KEYS = {
    "command", "started_at", "finished_at", "exit_code",
    "accepted_exit_codes", "ok", "output_sha256", "output", "output_tail",
}
LIVE_RECEIPT_KEYS = {
    "schema", "complete", "errors", "escalation_id", "missing_fact_id",
    "precise", "prelude_receipt", "experiment", "evidence",
}
LIVE_EVIDENCE_KEYS = {
    "raw_results", "pagination", "media_capabilities", "command_events",
    "observer_plan", "perturbation_plan", "control_plan", "adapter_source",
    "settings_snapshot", "owned_pid_cleanup", "external_preservation_manifest",
}
OBSERVER_METHODS = {
    "debugger.readMemory",
    "debugger.getRegisters",
    "debugger.addBreakpoint",
    "accessLog.addWatch",
    "execTrace.run",
    "functionTrace.start",
    "provenanceLog.start",
    "transferLog.start",
    "gpu.causality.start",
    "spu.trace.start",
    "movie.traceToFrame",
}
PRECISE_OBSERVER_METHODS = {
    "debugger.addBreakpoint",
    "accessLog.addWatch",
    "execTrace.run",
    "functionTrace.start",
    "provenanceLog.start",
    "transferLog.start",
    "gpu.causality.start",
    "spu.trace.start",
    "movie.traceToFrame",
}
REQUIRED_LIVE_COMMAND_METHODS = {
    "debugger.capabilities", "debugger.status", "emulator.getMediaInfo",
}
REQUIRED_ATOMIC_COMMAND_METHODS = {"scenario.runBatch", "scenario.getBatch"}
DIRECT_OBSERVER_COMMAND_METHODS = {"movie.traceToFrame"}
DIRECT_EXACT_PC_COMMAND_METHODS = {
    "debugger.status",
    "debugger.pause",
    "debugger.listBreakpoints",
    "debugger.addBreakpoint",
    "debugger.resume",
    "debugger.runUntilAddress",
    "debugger.getRegisters",
    "debugger.removeBreakpoint",
    "transferLog.clear",
    "transferLog.start",
    "transferLog.stop",
    "transferLog.get",
    "capture.atomic",
}
PRISTINE_MEDIA_SHA256 = (
    "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566"
)
MAX_CLOCK_VALUE = (1 << 63) - 1
MAX_RESULT_LIMITS = {
    "max_records": 1_000_000,
    "max_bytes": 256 * 1024 * 1024,
    "max_pages": 100_000,
}
EXPECTED_REPORT_COMMANDS = {
    "abl-phase4-validation-report/1": (
        ((sys.executable, "tools/phase4_closure_debt.py", "--check"), (0,)),
        ((sys.executable, "tools/phase4_offline_queue.py", "--check"), (0,)),
        ((sys.executable, "tools/phase4_derived_index.py", "--check"), (0,)),
        ((sys.executable, "-m", "pytest", "-q",
          "tests/test_phase4_closure_debt.py",
          "tests/test_phase4_offline_queue.py",
          "tests/test_phase4_derived_index.py",
          "tests/test_phase4_gate.py",
          "tests/test_phase4_method_metrics.py"), (0,)),
    ),
    "abl-phase4-knowledge-report/1": (
        ((sys.executable, "tools/phase4_reconcile_assertion_pins.py", "--check"), (0,)),
        ((sys.executable, "-m", "pytest", "-q",
          "tests/test_phase4_registry.py",
          "tests/test_knowledge_closure.py"), (0,)),
    ),
    "abl-phase4-vault-report/1": (
        ((sys.executable, "tools/validate_vault.py", "--check"), (0,)),
    ),
    "abl-phase4-clean-checkout-report/1": (
        ((sys.executable, "tools/build_identity.py", "--verify"), (0,)),
        ((sys.executable, "tools/phase4_gate.py"), (0, 1)),
    ),
}
EXPECTED_REPORT_OUTPUTS = {
    ("tools/phase4_closure_debt.py", "--check"): ("PASS: rows=",),
    ("tools/phase4_offline_queue.py", "--check"): ("PASS: rows=107",),
    ("tools/phase4_derived_index.py", "--check"): ("PASS: ", " reusable indexes"),
    ("tools/phase4_reconcile_assertion_pins.py", "--check"): (
        "PASS: ", " assertion pins match current retained artifacts",
    ),
    ("tools/validate_vault.py", "--check"): (
        "ObsidianVault consistency report",
        "dangling_links         0",
        "evidence_policy        0",
        "evidence_deadfile      0",
        "dup_address            0",
        "missing_alias          0",
        "schema                 0",
    ),
    ("tools/build_identity.py", "--verify"): (
        "[build_identity] PASS: 327/327 staged inputs match their pins",
    ),
}

# These ordered arrays are part of the method contract and are pinned by the
# validator source hash.  Do not infer favorable classifications for unknown paths.
SEMANTIC_SOURCE = (
    "src/main/**", "src_re/**", "symbols/**", "asm/**",
    "config/record_types.yaml", "config/semantic_state.yaml",
    "config/phase4_*.yaml", "analysis/mechanics_baseline.yaml",
)
GENERATOR_GUARD = (
    "tools/phase4_*.py", "tests/test_phase4_*.py", "tests/scenarios/**",
)
JOINED_ONLY = (
    "analysis/phase4_closure_debt.json",
    "analysis/phase4_coverage_matrix.json",
    "analysis/phase4_derived_index.json",
    "analysis/phase4_generator_inventory.json",
    "analysis/phase4_live_escalations.json",
    "analysis/phase4_offline_opportunity_queue.json",
    "analysis/phase4_upstream_dependency_reconciliation.json",
    "analysis/phase4_assertion_pin_reconciliation.json",
    "analysis/phase4_gate.json",
    "analysis/phase0_2_external_fixture_set.json",
    "analysis/phase2_fixture_audit.json",
)


class MetricsError(RuntimeError):
    """A retained measurement is invalid or cannot be reproduced."""


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise MetricsError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=lambda _: (_ for _ in ()).throw(
                MetricsError("floating-point JSON values are forbidden")),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise MetricsError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MetricsError(f"{path}: top level must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
    delta = set(value) ^ expected
    if delta:
        raise MetricsError(f"{where}: key mismatch: {sorted(delta)}")


def _closed_strings(value: Any, where: str) -> list[str]:
    if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value):
        raise MetricsError(f"{where}: must be an array of strings")
    return value


def _nonnegative_int(value: Any, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MetricsError(f"{where}: must be a nonnegative integer")
    return value


def _no_floats(value: Any, where: str) -> None:
    if isinstance(value, float):
        raise MetricsError(f"{where}: floating-point values are forbidden")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise MetricsError(f"{where}: non-string object key")
            _no_floats(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _no_floats(item, f"{where}[{index}]")


def _git(*args: str, cwd: Path = ROOT) -> str:
    run = subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if run.returncode:
        raise MetricsError(
            f"git {' '.join(args)} failed ({run.returncode}): {run.stderr.strip()}")
    return run.stdout


def _commit_exists(commit: str) -> None:
    if not HEX40.fullmatch(commit):
        raise MetricsError(f"invalid commit id: {commit!r}")
    _git("cat-file", "-e", f"{commit}^{{commit}}")


def _parse_time(value: object, where: str) -> datetime:
    if not isinstance(value, str):
        raise MetricsError(f"{where}: timestamp is not a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MetricsError(f"{where}: invalid RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise MetricsError(f"{where}: timestamp lacks timezone")
    return parsed


def resolve_ref(ref: Any, run_dir: Path, tested_root: Path,
                where: str) -> tuple[Path, dict[str, Any]]:
    if not isinstance(ref, dict):
        raise MetricsError(f"{where}: artifact reference is not an object")
    _exact_keys(ref, REF_KEYS, where)
    if ref["scope"] not in {"repo", "run"}:
        raise MetricsError(f"{where}: invalid scope")
    rel = ref["path"]
    if not isinstance(rel, str) or not rel:
        raise MetricsError(f"{where}: invalid path")
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != rel:
        raise MetricsError(f"{where}: unsafe or non-canonical path {rel!r}")
    root = tested_root if ref["scope"] == "repo" else run_dir
    path = root.joinpath(*pure.parts)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise MetricsError(f"{where}: missing or escaping artifact {rel}") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise MetricsError(f"{where}: artifact is not a regular file")
    if not isinstance(ref["sha256"], str) or not HEX64.fullmatch(ref["sha256"]):
        raise MetricsError(f"{where}: invalid SHA-256")
    actual = sha256(resolved)
    if actual != ref["sha256"]:
        raise MetricsError(
            f"{where}: SHA-256 mismatch ({actual} != {ref['sha256']})")
    return resolved, ref


def _debt_rows(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if doc.get("schema") != "abl-phase4-closure-debt/1":
        raise MetricsError("closure-debt schema mismatch")
    if doc.get("valid") is not True or doc.get("errors"):
        raise MetricsError("closure-debt snapshot is not valid")
    rows = doc.get("rows")
    if not isinstance(rows, list) or len(rows) != 107:
        raise MetricsError("closure-debt snapshot must contain 107 rows")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or row_id in result:
            raise MetricsError("closure-debt row IDs are missing or duplicate")
        result[row_id] = row
    return result


def _selected(doc: dict[str, Any]) -> tuple[str, list[str]]:
    selected = ((doc.get("scheduler") or {}).get("selected_campaigns") or [])
    if len(selected) != 1:
        raise MetricsError("closure-debt scheduler must select exactly one campaign")
    campaign = selected[0]
    campaign_id = campaign.get("campaign_id")
    rows = campaign.get("rows")
    if not isinstance(campaign_id, str) or not isinstance(rows, list) or not rows:
        raise MetricsError("selected campaign identity is malformed")
    if len(rows) > 3 or not all(isinstance(row, str) for row in rows):
        raise MetricsError("selected campaign exceeds the three-row WIP limit")
    return campaign_id, rows


def _movie_ready_scheduler_handoff(
        previous_after: dict[str, Any], current_before: dict[str, Any],
        previous_progress: dict[str, Any]) -> bool:
    """Admit only a policy-driven scheduler change over identical closure debt."""
    try:
        old_campaign, old_rows = _selected(previous_after)
        new_campaign, new_rows = _selected(current_before)
    except MetricsError:
        return False
    if not old_campaign.startswith("movie-ready:") or \
            not new_campaign.startswith("movie-ready:"):
        return False
    old_payload = json.loads(json.dumps(previous_after))
    new_payload = json.loads(json.dumps(current_before))
    old_payload.pop("scheduler", None)
    new_payload.pop("scheduler", None)
    if old_payload != new_payload or \
            previous_progress.get("campaign_id") != old_campaign or \
            previous_progress.get("row_ids") != old_rows or \
            previous_progress.get("demotions"):
        return False
    no_reduction = not (
        previous_progress.get("row_transitions")
        or previous_progress.get("dimension_transitions")
    )
    return not no_reduction or set(old_rows).isdisjoint(new_rows)


def _transitions(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    before_rows = _debt_rows(before)
    after_rows = _debt_rows(after)
    if set(before_rows) != set(after_rows):
        raise MetricsError("closure-debt row universe changed")
    row_transitions: list[list[str]] = []
    dimension_transitions: list[list[str]] = []
    demotions: list[list[str]] = []
    for row_id in sorted(before_rows):
        old_row, new_row = before_rows[row_id], after_rows[row_id]
        old_complete = old_row.get("completion_state") in {
            "campaign_complete", "reviewed_absent",
        }
        new_complete = new_row.get("completion_state") in {
            "campaign_complete", "reviewed_absent",
        }
        if not old_complete and new_complete:
            row_transitions.append([row_id, str(old_row.get("completion_state")),
                                    str(new_row.get("completion_state"))])
        elif old_complete and not new_complete:
            demotions.append([row_id, "row", str(old_row.get("completion_state")),
                              str(new_row.get("completion_state"))])
        old_dims = old_row.get("dimensions") or {}
        new_dims = new_row.get("dimensions") or {}
        if set(old_dims) != set(new_dims):
            raise MetricsError(f"{row_id}: dimension universe changed")
        for dim in sorted(old_dims):
            old_state = old_dims[dim].get("state")
            new_state = new_dims[dim].get("state")
            if old_state in {"gap", "partial"} and new_state == "met":
                dimension_transitions.append(
                    [row_id, dim, str(old_state), str(new_state)])
            elif old_state == "met" and new_state != "met":
                demotions.append([row_id, dim, str(old_state), str(new_state)])
    return {
        "rows": row_transitions,
        "dimensions": dimension_transitions,
        "demotions": demotions,
    }


def _event_document(
        path: Path, expected_iteration: int | None = None,
        expected_base: str | None = None,
        expected_tested: str | None = None,
) -> tuple[list[dict[str, Any]], str, str]:
    doc = load_json(path)
    _exact_keys(doc, {"schema", "iteration", "events"}, str(path))
    if doc.get("schema") != "abl-phase4-controller-events/1":
        raise MetricsError("controller event schema mismatch")
    if not isinstance(doc["iteration"], int) or isinstance(doc["iteration"], bool) or \
            doc["iteration"] < 1:
        raise MetricsError("controller event iteration is invalid")
    if expected_iteration is not None and doc["iteration"] != expected_iteration:
        raise MetricsError("controller event iteration disagrees with manifest")
    events = doc.get("events")
    if not isinstance(events, list) or len(events) < 2:
        raise MetricsError("controller event stream is incomplete")
    sequences: list[int] = []
    for event in events:
        _exact_keys(event, {"sequence", "at", "type", "payload"},
                    "controller event")
        if not isinstance(event["sequence"], int) or isinstance(event["sequence"], bool):
            raise MetricsError("controller event sequence must be integer")
        sequences.append(event["sequence"])
        _parse_time(event["at"], "controller event")
        if not isinstance(event["type"], str) or not isinstance(event["payload"], dict):
            raise MetricsError("controller event is malformed")
        payload = event["payload"]
        if event["type"] == "iteration_started":
            _exact_keys(payload, {"base_commit"}, "iteration-start payload")
            if expected_base is not None and payload["base_commit"] != expected_base:
                raise MetricsError("iteration-start payload disagrees with manifest")
        elif event["type"] == "executor_finished":
            _exact_keys(
                payload, {"status", "candidate_commit"},
                "executor-finished payload")
            if payload["status"] not in {
                    "closed", "open_autonomous", "blocked_external"} or \
                    not isinstance(payload["candidate_commit"], str) or \
                    not HEX40.fullmatch(payload["candidate_commit"]):
                raise MetricsError("executor-finished payload is invalid")
            if expected_tested is not None and \
                    payload["candidate_commit"] != expected_tested:
                raise MetricsError("executor-finished payload disagrees with manifest")
        elif event["type"] in {"iteration_reports_started", "iteration_completed"}:
            _exact_keys(payload, {"tested_commit"}, f"{event['type']} payload")
            if not isinstance(payload["tested_commit"], str) or \
                    not HEX40.fullmatch(payload["tested_commit"]):
                raise MetricsError(f"{event['type']} payload is invalid")
            if expected_tested is not None and \
                    payload["tested_commit"] != expected_tested:
                raise MetricsError(f"{event['type']} payload disagrees with manifest")
        elif event["type"] != "infrastructure_failure":
            raise MetricsError(f"unknown controller event type: {event['type']}")
    if sequences != list(range(len(events))):
        raise MetricsError("controller event sequence is not contiguous")
    parsed_times = [
        _parse_time(event["at"], "controller event ordering")
        for event in events
    ]
    if parsed_times != sorted(parsed_times):
        raise MetricsError("controller event timestamps are not monotonic")
    if events[0]["type"] != "iteration_started" or \
            events[-1]["type"] not in {
                "iteration_completed", "infrastructure_failure",
            }:
        raise MetricsError("controller stream lacks terminal events")
    if not isinstance(events[0]["payload"].get("base_commit"), str) or not \
            HEX40.fullmatch(events[0]["payload"]["base_commit"]):
        raise MetricsError("iteration-start payload lacks a base commit")
    event_types = [event["type"] for event in events]
    if events[-1]["type"] == "iteration_completed" and event_types != [
            "iteration_started", "executor_finished",
            "iteration_reports_started", "iteration_completed"]:
        raise MetricsError("completed controller lifecycle is incomplete or duplicated")
    if events[-1]["type"] == "infrastructure_failure":
        allowed_order = [
            "iteration_started", "executor_finished",
            "iteration_reports_started", "infrastructure_failure",
        ]
        positions = [allowed_order.index(value) for value in event_types]
        if positions != sorted(set(positions)) or \
                event_types[0] != "iteration_started" or \
                event_types[-1] != "infrastructure_failure":
            raise MetricsError(
                "infrastructure controller lifecycle is incomplete or duplicated")
    if events[-1]["type"] == "iteration_completed" and expected_tested is not None and \
            events[-1]["payload"].get("tested_commit") != expected_tested:
        raise MetricsError("iteration-completed payload disagrees with manifest")
    if events[-1]["type"] == "infrastructure_failure":
        payload = events[-1]["payload"]
        _exact_keys(payload, {"code", "cleanup"}, "infrastructure failure payload")
        if not isinstance(payload["code"], str) or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{2,63}", payload["code"]):
            raise MetricsError("infrastructure failure code is invalid")
        if not isinstance(payload["cleanup"], list) or not payload["cleanup"] or \
                not all(isinstance(item, str) and item for item in payload["cleanup"]):
            raise MetricsError("infrastructure failure cleanup is absent")
    return events, events[0]["at"], events[-1]["at"]


def _canonical_check_output(value: str) -> str:
    """Remove only explicitly non-semantic timing noise from fixed checks."""
    return re.sub(
        r" in \d+(?:\.\d+)?s(?: \(\d+:\d{2}:\d{2}\))?(?=\n|$)",
        " in <seconds>s", value)


def _validate_fixed_check_output(
        command: list[str], output: str, exit_code: int, where: str) -> None:
    """Reject a reproducible command result whose semantic body says failure."""
    if re.search(
            r"(?im)^(?:FAIL(?:ED)?|ERROR|FATAL)(?:\b|:)|"
            r"\b(?:failures?|errors?)\s*[:=]\s*[1-9]\d*\b|"
            r"\b[1-9]\d*\s+(?:failed|failures?|errors?)\b",
            output):
        raise MetricsError(f"{where}: command output reports failure")
    if command[1:3] == ["-m", "pytest"]:
        if exit_code != 0 or not re.search(r"(?m)\b\d+ passed\b", output):
            raise MetricsError(f"{where}: pytest success marker is absent")
        return
    if command[-1:] == ["tools/phase4_gate.py"]:
        expected_gate = (
            "[phase4-gate] CLOSED" if exit_code == 0 else "[phase4-gate] OPEN")
        if expected_gate not in output:
            raise MetricsError(f"{where}: Phase-4 gate outcome marker is absent")
        return
    markers = EXPECTED_REPORT_OUTPUTS.get(tuple(command[1:]))
    if markers is None:
        raise MetricsError(f"{where}: fixed command has no semantic output contract")
    missing = [marker for marker in markers if marker not in output]
    if missing:
        raise MetricsError(
            f"{where}: semantic success marker is absent: {missing}")


def _closed_report(path: Path, schema: str, tested_commit: str,
                   run_dir: Path, tested_root: Path,
                   rerun_cache: dict[tuple[str, ...], tuple[int, str]] | None = None,
                   reporter_sha256: str | None = None) -> dict[str, Any]:
    doc = load_json(path)
    extras: set[str]
    if schema == "abl-phase4-command-log/1":
        extras = {"logs"}
    elif schema == "abl-phase4-knowledge-report/1":
        extras = {"joined"}
    elif schema == "abl-phase4-clean-checkout-report/1":
        extras = {"status_before", "status_after"}
    else:
        extras = set()
    _exact_keys(doc, REPORT_KEYS | extras, str(path))
    if doc["schema"] != schema:
        raise MetricsError(f"{path}: report schema mismatch")
    if doc["tested_commit"] != tested_commit:
        raise MetricsError(f"{path}: report tested commit mismatch")
    _parse_time(doc["generated_at"], f"{path}: generated_at")
    checks = doc["checks"]
    if not isinstance(checks, list):
        raise MetricsError(f"{path}: checks are not an array")
    derived_errors: list[str] = []
    if schema != "abl-phase4-command-log/1":
        expected = EXPECTED_REPORT_COMMANDS.get(schema)
        actual = tuple(
            (tuple(check.get("command") or ()),
             tuple(check.get("accepted_exit_codes") or ()))
            for check in checks if isinstance(check, dict)
        )
        if expected is None or actual != expected:
            raise MetricsError(f"{path}: report command set is not the fixed contract")
        reporter = tested_root / "tools" / "phase4_method_reports.py"
        if reporter_sha256 is None or not reporter.is_file() or \
                sha256(reporter) != reporter_sha256:
            raise MetricsError(f"{path}: report producer source is not pinned")
    for index, check in enumerate(checks):
        where = f"{path}: checks[{index}]"
        if not isinstance(check, dict):
            raise MetricsError(f"{where}: not an object")
        _exact_keys(check, CHECK_KEYS, where)
        command = check["command"]
        if not isinstance(command, list) or not command or not all(
                isinstance(item, str) and item for item in command):
            raise MetricsError(f"{where}: invalid command")
        started = _parse_time(check["started_at"], f"{where}: started_at")
        finished = _parse_time(check["finished_at"], f"{where}: finished_at")
        if finished < started:
            raise MetricsError(f"{where}: finish precedes start")
        exit_code = check["exit_code"]
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise MetricsError(f"{where}: invalid exit code")
        accepted_codes = check["accepted_exit_codes"]
        if not isinstance(accepted_codes, list) or not accepted_codes or \
                not all(isinstance(code, int) and not isinstance(code, bool)
                        for code in accepted_codes) or \
                accepted_codes != sorted(set(accepted_codes)):
            raise MetricsError(f"{where}: invalid accepted exit codes")
        derived_ok = exit_code in accepted_codes
        if check["ok"] is not derived_ok:
            raise MetricsError(f"{where}: authored ok disagrees with exit code")
        output = check["output"]
        if not isinstance(output, str) or not isinstance(check["output_tail"], str):
            raise MetricsError(f"{where}: output fields are invalid")
        if "Traceback (most recent call last)" in output:
            raise MetricsError(f"{where}: command crashed despite an admitted exit code")
        if schema != "abl-phase4-command-log/1":
            _validate_fixed_check_output(command, output, exit_code, where)
        if check["output_tail"] != output[-4000:]:
            raise MetricsError(f"{where}: output tail is not derived")
        digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
        if check["output_sha256"] != digest:
            raise MetricsError(f"{where}: output SHA-256 is not derived")
        if schema != "abl-phase4-command-log/1":
            cache = rerun_cache if rerun_cache is not None else {}
            command_key = tuple(command)
            if command_key not in cache:
                rerun = subprocess.run(
                    command, cwd=tested_root, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                )
                cache[command_key] = (rerun.returncode, rerun.stdout)
            rerun_code, rerun_output = cache[command_key]
            if rerun_code != exit_code:
                raise MetricsError(
                    f"{where}: retained result does not reproduce independently")
            if _canonical_check_output(rerun_output) != \
                    _canonical_check_output(output):
                raise MetricsError(
                    f"{where}: retained output body does not reproduce independently")
        if not derived_ok:
            derived_errors.append(f"{' '.join(command)}: exit {exit_code}")
    if doc["errors"] != derived_errors or doc["complete"] != (not derived_errors):
        raise MetricsError(f"{path}: authored completeness disagrees with checks")
    if not doc["complete"]:
        raise MetricsError(f"{path}: report is incomplete")
    if schema == "abl-phase4-command-log/1":
        logs = doc["logs"]
        if not isinstance(logs, list) or not logs:
            raise MetricsError(f"{path}: no retained command logs")
        roles: set[str] = set()
        for index, entry in enumerate(logs):
            where = f"{path}: logs[{index}]"
            if not isinstance(entry, dict):
                raise MetricsError(f"{where}: not an object")
            _exact_keys(entry, {"role", "artifact", "size"}, where)
            if entry["role"] not in {"executor", "verifier"} or \
                    entry["role"] in roles:
                raise MetricsError(f"{where}: invalid or duplicate role")
            roles.add(entry["role"])
            log_path, _ = resolve_ref(
                entry["artifact"], run_dir, tested_root, f"{where}: artifact")
            if entry["size"] != log_path.stat().st_size:
                raise MetricsError(f"{where}: authored size disagrees")
        if "executor" not in roles:
            raise MetricsError(f"{path}: executor log is missing")
    if schema == "abl-phase4-knowledge-report/1":
        derived_joined = bool(checks) and all(check["ok"] for check in checks)
        if doc["joined"] is not derived_joined:
            raise MetricsError(f"{path}: knowledge join is not derived")
    if schema == "abl-phase4-clean-checkout-report/1":
        for key in ("status_before", "status_after"):
            if not isinstance(doc[key], list) or not all(
                    isinstance(item, str) for item in doc[key]):
                raise MetricsError(f"{path}: {key} is invalid")
        actual_status = subprocess.run(
            ["git", "-C", str(tested_root), "status", "--porcelain=v1",
             "--untracked-files=all"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if actual_status.returncode or actual_status.stdout:
            raise MetricsError(f"{path}: tested checkout is not independently clean")
    return doc


def _progress(path: Path, iteration: int, campaign_id: str, rows: list[str],
              transitions: dict[str, list[Any]], before_hash: str,
              after_hash: str) -> dict[str, Any]:
    doc = load_json(path)
    expected = {
        "schema", "iteration", "campaign_id", "row_ids",
        "debt_before_sha256", "debt_after_sha256",
        "row_transitions", "dimension_transitions", "demotions",
    }
    _exact_keys(doc, expected, str(path))
    if doc.get("schema") != "abl-ratchet-phase4-progress/2":
        raise MetricsError("progress receipt schema mismatch")
    expected_values = {
        "iteration": iteration,
        "campaign_id": campaign_id,
        "row_ids": rows,
        "debt_before_sha256": before_hash,
        "debt_after_sha256": after_hash,
        "row_transitions": transitions["rows"],
        "dimension_transitions": transitions["dimensions"],
        "demotions": transitions["demotions"],
    }
    for key, value in expected_values.items():
        if doc.get(key) != value:
            raise MetricsError(f"progress receipt disagrees on {key}")
    return doc


def _canonical_live_key(receipt: dict[str, Any]) -> str:
    experiment = receipt.get("experiment")
    if not isinstance(experiment, dict):
        raise MetricsError("live receipt lacks experiment object")
    required = {
        "executor_role", "anchor", "execution", "domain", "observer_plan_sha256",
        "perturbation_plan_sha256", "control_plan_sha256",
        "duckstation_source_sha256", "duckstation_executable_sha256",
        "api_surface_sha256", "adapter_source_sha256",
    }
    _exact_keys(experiment, required, "live experiment")
    if experiment["executor_role"] not in {"investigator", "fresh_verifier"}:
        raise MetricsError("live executor role is invalid")
    anchor = experiment["anchor"]
    if not isinstance(anchor, dict):
        raise MetricsError("live anchor is malformed")
    anchor_keys = {
        "kind", "media_sha256", "settings_sha256", "movie_sha256",
        "state_sha256", "start",
    }
    _exact_keys(anchor, anchor_keys, "live anchor")
    if anchor["kind"] not in {
        "cold_boot", "cold_boot_movie", "save_state", "movie_start_state",
    }:
        raise MetricsError("live anchor kind is invalid")
    for key in ("media_sha256", "settings_sha256"):
        if not isinstance(anchor[key], str) or not HEX64.fullmatch(anchor[key]):
            raise MetricsError(f"live anchor {key} is invalid")
    optional = {"movie_sha256": anchor["movie_sha256"],
                "state_sha256": anchor["state_sha256"]}
    for key, value in optional.items():
        if value is not None and (
                not isinstance(value, str) or not HEX64.fullmatch(value)):
            raise MetricsError(f"live anchor {key} is invalid")
    kind_requirements = {
        "cold_boot": (None, None),
        "cold_boot_movie": ("hash", None),
        "save_state": (None, "hash"),
        "movie_start_state": ("hash", "hash"),
    }
    movie_req, state_req = kind_requirements[anchor["kind"]]
    if (movie_req == "hash") != (anchor["movie_sha256"] is not None) or \
            (state_req == "hash") != (anchor["state_sha256"] is not None):
        raise MetricsError("live anchor kind/hash combination is invalid")
    _typed_clock(anchor["start"], point=True, where="live anchor start")
    execution = experiment["execution"]
    _exact_keys(execution, {"bound", "capture_window"}, "live execution")
    _typed_clock(execution["bound"], point=False, where="live bound")
    _typed_clock(execution["capture_window"], point=False,
                 where="live capture window")
    bound = execution["bound"]
    capture = execution["capture_window"]
    if capture["clock"] != bound["clock"] or capture["start"] < bound["start"] or \
            capture["stop"] > bound["stop"]:
        raise MetricsError("live capture window is outside its execution bound")
    if experiment["domain"] not in {
        "ram", "register", "dma", "gpu", "spu", "interface", "native_control",
    }:
        raise MetricsError("live domain is invalid")
    for key in required - {
        "executor_role", "anchor", "execution", "domain",
    }:
        if not isinstance(experiment[key], str) or \
                not HEX64.fullmatch(experiment[key]):
            raise MetricsError(f"live experiment {key} is invalid")
    key_object = {key: experiment[key] for key in sorted(required - {"executor_role"})}
    return hashlib.sha256(canonical_bytes(key_object)).hexdigest()


def _semantic_live_key(
        receipt: dict[str, Any], control: dict[str, Any],
        observer: dict[str, Any],
        perturbation: dict[str, Any]) -> str:
    """Identify behavior without allowing opaque assertion hashes to salt reruns."""
    experiment = receipt["experiment"]
    key_object = {
        "anchor": experiment["anchor"],
        "execution": experiment["execution"],
        "domain": experiment["domain"],
        "observer_plan": observer,
        "perturbation_plan": perturbation,
        "control_role": control["role"],
        "duckstation_source_sha256": experiment["duckstation_source_sha256"],
        "duckstation_executable_sha256":
            experiment["duckstation_executable_sha256"],
        "api_surface_sha256": experiment["api_surface_sha256"],
    }
    return hashlib.sha256(canonical_bytes(key_object)).hexdigest()


def _typed_clock(value: Any, *, point: bool, where: str) -> None:
    expected = {"clock", "value"} if point else {
        "clock", "start", "stop", "stop_inclusive",
    }
    if not isinstance(value, dict):
        raise MetricsError(f"{where}: not an object")
    _exact_keys(value, expected, where)
    if value["clock"] not in {
        "emulator_frame", "movie_frame", "cpu_cycle", "instruction",
    }:
        raise MetricsError(f"{where}: invalid clock")
    numeric = ("value",) if point else ("start", "stop")
    for key in numeric:
        if not isinstance(value[key], int) or isinstance(value[key], bool) or \
                value[key] < 0 or value[key] > MAX_CLOCK_VALUE:
            raise MetricsError(f"{where}: {key} must be a nonnegative integer")
    if not point:
        if value["stop"] < value["start"] or not isinstance(value["stop_inclusive"], bool):
            raise MetricsError(f"{where}: invalid range")


def _validate_observer_plan(doc: dict[str, Any], where: str) -> None:
    if not isinstance(doc, dict):
        raise MetricsError(f"{where}: observer plan is not an object")
    schema = doc.get("schema")
    expected_keys = {"schema", "operations", "result_limits"}
    if schema == "abl-phase4-observer-plan/2":
        expected_keys.add("direct_command_plan")
    _exact_keys(doc, expected_keys, where)
    if schema not in {
            "abl-phase4-observer-plan/1",
            "abl-phase4-observer-plan/2"}:
        raise MetricsError(f"{where}: observer-plan schema mismatch")
    operations = doc["operations"]
    if not isinstance(operations, list) or not operations:
        raise MetricsError(f"{where}: observer operations are empty")
    for sequence, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise MetricsError(f"{where}: operation {sequence} is not an object")
        _exact_keys(operation, {"sequence", "method", "args"},
                    f"{where}: operation {sequence}")
        if operation["sequence"] != sequence:
            raise MetricsError(f"{where}: observer sequence is not contiguous")
        if operation["method"] not in OBSERVER_METHODS:
            raise MetricsError(f"{where}: observer method is not closed")
        if not isinstance(operation["args"], dict):
            raise MetricsError(f"{where}: observer args are not an object")
        _no_floats(operation["args"], f"{where}: observer args")
        method = operation["method"]
        args = operation["args"]
        arg_keys = {
            "debugger.readMemory": {"address", "size"},
            "debugger.getRegisters": set(),
            "debugger.addBreakpoint": {
                "address", "type", "enabled", "temporary",
            },
            "accessLog.addWatch": {
                "address", "length", "type", "label", "max_events",
                "stop_on_hit",
            },
            "execTrace.run": {"frames"},
            "functionTrace.start": {
                "functions", "all_symbols", "capture_memory", "max_events",
            },
            "provenanceLog.start": {"max_events", "clear"},
            "transferLog.start": set(),
            "gpu.causality.start": set(),
            "spu.trace.start": {"clear"},
            "movie.traceToFrame": {
                "path", "frame", "start", "end", "ranges", "filter",
            },
        }
        _exact_keys(args, arg_keys[method], f"{where}: {method} args")
        if method == "debugger.readMemory":
            address = _nonnegative_int(
                args["address"], f"{where}: read address")
            size = _nonnegative_int(
                args["size"], f"{where}: read size")
            if address > 0xFFFFFFFF or size < 1 or size > 0x200000:
                raise MetricsError(f"{where}: readMemory args are out of range")
        elif method == "debugger.addBreakpoint":
            address = _nonnegative_int(
                args["address"], f"{where}: breakpoint address")
            if address > 0xFFFFFFFF or address & 3 or \
                    args["type"] != "execute" or \
                    args["enabled"] is not True or \
                    args["temporary"] is not False:
                raise MetricsError(
                    f"{where}: debugger.addBreakpoint args are invalid")
        elif method == "accessLog.addWatch":
            address = _nonnegative_int(args["address"], f"{where}: watch address")
            length = _nonnegative_int(args["length"], f"{where}: watch length")
            maximum = _nonnegative_int(
                args["max_events"], f"{where}: watch max_events")
            if address > 0xFFFFFFFF or length < 1 or length > 0x200000 or \
                    maximum < 1 or maximum > 1_000_000 or \
                    args["type"] not in {"read", "write", "readwrite"} or \
                    not isinstance(args["label"], str) or not args["label"] or \
                    not isinstance(args["stop_on_hit"], bool):
                raise MetricsError(f"{where}: accessLog.addWatch args are invalid")
        elif method == "execTrace.run":
            frames = _nonnegative_int(args["frames"], f"{where}: trace frames")
            if frames < 1 or frames > 1_000_000:
                raise MetricsError(f"{where}: execTrace.run args are invalid")
        elif method == "provenanceLog.start":
            maximum = _nonnegative_int(
                args["max_events"], f"{where}: provenance max_events")
            if maximum < 1 or maximum > 1_000_000 or \
                    not isinstance(args["clear"], bool):
                raise MetricsError(f"{where}: provenanceLog.start args are invalid")
        elif method == "functionTrace.start":
            maximum = _nonnegative_int(
                args["max_events"], f"{where}: function max_events")
            if not isinstance(args["functions"], list) or \
                    not all(isinstance(item, (str, int)) and
                            not isinstance(item, bool)
                            for item in args["functions"]) or \
                    not isinstance(args["all_symbols"], bool) or \
                    not isinstance(args["capture_memory"], bool) or \
                    maximum < 1 or maximum > 1_000_000 or \
                    (not args["functions"] and not args["all_symbols"]):
                raise MetricsError(f"{where}: functionTrace.start args are invalid")
        elif method == "spu.trace.start":
            if not isinstance(args["clear"], bool):
                raise MetricsError(f"{where}: spu.trace.start args are invalid")
        elif method == "movie.traceToFrame":
            if not isinstance(args["path"], str) or not args["path"] or \
                    any(not isinstance(args[key], int) or isinstance(args[key], bool)
                        or args[key] < 0 or args[key] > MAX_CLOCK_VALUE
                        for key in ("frame", "start", "end")) or \
                    args["start"] > args["end"] or args["end"] > args["frame"] or \
                    not isinstance(args["ranges"], list) or \
                    len(args["ranges"]) > 16 or \
                    not isinstance(args["filter"], dict):
                raise MetricsError(f"{where}: movie.traceToFrame args are invalid")
            for index, range_doc in enumerate(args["ranges"]):
                if not isinstance(range_doc, dict):
                    raise MetricsError(f"{where}: trace range {index} is invalid")
                _exact_keys(
                    range_doc, {"start", "end"},
                    f"{where}: trace range {index}")
                start = _nonnegative_int(
                    range_doc["start"], f"{where}: trace range start")
                end = _nonnegative_int(
                    range_doc["end"], f"{where}: trace range end")
                if start > end or end > 0xFFFFFFFF:
                    raise MetricsError(f"{where}: trace range is out of range")
            _exact_keys(args["filter"], {"pc_min", "pc_max"},
                        f"{where}: trace filter")
            pc_min = _nonnegative_int(
                args["filter"]["pc_min"], f"{where}: trace pc_min")
            pc_max = _nonnegative_int(
                args["filter"]["pc_max"], f"{where}: trace pc_max")
            if pc_min > pc_max or pc_max > 0xFFFFFFFF:
                raise MetricsError(f"{where}: trace filter is out of range")
    if schema == "abl-phase4-observer-plan/2":
        direct_plan = doc["direct_command_plan"]
        direct_schema = (
            direct_plan.get("schema")
            if isinstance(direct_plan, dict) else None
        )
        if direct_schema == "abl-phase4-duckstation-exact-pc-plan/1":
            if len(operations) != 1 or operations[0] != {
                    "sequence": 0, "method": "transferLog.start", "args": {}}:
                raise MetricsError(
                    f"{where}: direct exact-PC observer must be "
                    "transferLog.start")
            try:
                import phase4_duckstation_exact_pc_batch as direct_adapter
            except ImportError as exc:
                raise MetricsError(
                    f"{where}: exact-PC adapter is unavailable") from exc
        elif direct_schema == \
                "abl-phase4-duckstation-two-pc-first-hit-plan/1":
            try:
                import phase4_duckstation_two_pc_first_hit as direct_adapter
            except ImportError as exc:
                raise MetricsError(
                    f"{where}: two-PC first-hit adapter is unavailable") from exc
            expected_operations = [
                {
                    "sequence": index,
                    "method": "debugger.addBreakpoint",
                    "args": stop["params"],
                }
                for index, stop in enumerate(
                    direct_plan.get("breakpoint_sequence") or [])
            ]
            if operations != expected_operations:
                raise MetricsError(
                    f"{where}: managed first-hit observer differs from its "
                    "two breakpoint plan")
        else:
            raise MetricsError(
                f"{where}: direct command plan schema is unsupported")
        direct_errors = direct_adapter.validate_plan(direct_plan)
        if direct_errors:
            raise MetricsError(
                f"{where}: direct command plan is invalid: "
                f"{'; '.join(direct_errors)}")
    limits = doc["result_limits"]
    if not isinstance(limits, dict):
        raise MetricsError(f"{where}: result limits are not an object")
    _exact_keys(limits, {"max_records", "max_bytes", "max_pages"},
                f"{where}: result limits")
    for key, value in limits.items():
        parsed = _nonnegative_int(value, f"{where}: {key}")
        if parsed < 1 or parsed > MAX_RESULT_LIMITS[key]:
            raise MetricsError(f"{where}: {key} must be positive")
    if schema == "abl-phase4-observer-plan/2":
        direct_plan = doc["direct_command_plan"]
        if direct_plan["schema"] == \
                "abl-phase4-duckstation-exact-pc-plan/1":
            pagination = direct_plan["transfer_pagination"]
            expected_limits = {
                "max_records": pagination["max_records"],
                "max_bytes": pagination["max_bytes"],
                "max_pages": pagination["max_pages"],
            }
        else:
            import phase4_duckstation_two_pc_first_hit as first_hit_adapter
            expected_limits = first_hit_adapter.observer_result_limits(
                direct_plan)
        if limits != expected_limits:
            raise MetricsError(
                f"{where}: result limits differ from direct-plan bounds")


def _validate_movie_trace_event(
        params: dict[str, Any], result: dict[str, Any], where: str,
) -> None:
    """Validate one retained native phase-neutral coverage command/result."""
    _exact_keys(
        params, {"path", "frame", "ranges", "pc_min", "pc_max"},
        f"{where}: params")
    if not isinstance(params["path"], str) or not params["path"] or \
            any(not isinstance(params[key], int) or isinstance(params[key], bool)
                or params[key] < 0 or params[key] > MAX_CLOCK_VALUE
                for key in ("frame", "pc_min", "pc_max")) or \
            params["pc_min"] > params["pc_max"] or \
            params["pc_max"] > 0xFFFFFFFF or \
            not isinstance(params["ranges"], list) or \
            not 1 <= len(params["ranges"]) <= 16:
        raise MetricsError(f"{where}: movie.traceToFrame params are invalid")
    for index, range_doc in enumerate(params["ranges"]):
        if not isinstance(range_doc, dict):
            raise MetricsError(f"{where}: trace range {index} is invalid")
        _exact_keys(
            range_doc, {"start", "end", "label", "max_pcs"},
            f"{where}: trace range {index}")
        start = _nonnegative_int(
            range_doc["start"], f"{where}: trace range start")
        end = _nonnegative_int(
            range_doc["end"], f"{where}: trace range end")
        maximum = _nonnegative_int(
            range_doc["max_pcs"], f"{where}: trace range max_pcs")
        if start > end or end > 0xFFFFFFFF or maximum < 1 or \
                maximum > 1_000_000 or not isinstance(
                    range_doc["label"], str) or not range_doc["label"]:
            raise MetricsError(f"{where}: trace range is invalid")

    _exact_keys(result, {
        "target_frame", "trace_mode", "configured_execution_mode",
        "comparison_execution_mode", "control", "instrumented",
        "comparison", "coverage", "status",
    }, f"{where}: result")
    if result["target_frame"] != params["frame"] or \
            result["trace_mode"] != "passive_cached_block_coverage" or \
            result["comparison_execution_mode"] != "CachedInterpreter" or \
            not isinstance(result["configured_execution_mode"], str) or \
            not result["configured_execution_mode"]:
        raise MetricsError(f"{where}: trace mode/target is invalid")
    comparison = result["comparison"]
    _exact_keys(comparison, {
        "cycle_neutral", "same_ram", "same_registers", "same_cycle",
        "same_frame",
    }, f"{where}: result comparison")
    endpoint_keys = {
        "cycle", "frame", "movie_frame", "pc", "ram_sha256",
        "registers_sha256", "sp",
    }
    for key in ("control", "instrumented"):
        if not isinstance(result[key], dict):
            raise MetricsError(f"{where}: {key} endpoint is absent")
        _exact_keys(result[key], endpoint_keys, f"{where}: {key} endpoint")
        for counter in ("cycle", "frame", "movie_frame"):
            _nonnegative_int(
                result[key][counter], f"{where}: {key}.{counter}")
        for digest in ("ram_sha256", "registers_sha256"):
            if not isinstance(result[key][digest], str) or not HEX64.fullmatch(
                    result[key][digest]):
                raise MetricsError(f"{where}: {key}.{digest} is invalid")
        for register in ("pc", "sp"):
            if not isinstance(result[key][register], str) or not re.fullmatch(
                    r"0x[0-9a-f]{8}", result[key][register]):
                raise MetricsError(f"{where}: {key}.{register} is invalid")
    control = result["control"]
    instrumented = result["instrumented"]
    derived_comparison = {
        "same_ram": control["ram_sha256"] == instrumented["ram_sha256"],
        "same_registers": (
            control["registers_sha256"] ==
            instrumented["registers_sha256"]),
        "same_cycle": control["cycle"] == instrumented["cycle"],
        "same_frame": (
            control["frame"] == instrumented["frame"] and
            control["movie_frame"] == instrumented["movie_frame"]),
    }
    derived_comparison["cycle_neutral"] = all(derived_comparison.values())
    if comparison != derived_comparison:
        raise MetricsError(
            f"{where}: native comparison contradicts retained endpoints")
    if not isinstance(result["status"], dict) or not result["status"]:
        raise MetricsError(f"{where}: status endpoint is absent")
    coverage = result["coverage"]
    if not isinstance(coverage, list) or len(coverage) != len(params["ranges"]):
        raise MetricsError(f"{where}: coverage cardinality is invalid")
    for index, (observed, requested) in enumerate(
            zip(coverage, params["ranges"], strict=True)):
        if not isinstance(observed, dict):
            raise MetricsError(f"{where}: coverage {index} is invalid")
        _exact_keys(
            observed, {"range", "label", "coverage"},
            f"{where}: coverage {index}")
        expected_range = {
            "start": f"0x{requested['start']:08x}",
            "end": f"0x{requested['end']:08x}",
        }
        if observed["range"] != expected_range or \
                observed["label"] != requested["label"]:
            raise MetricsError(f"{where}: coverage range/label drifted")
        body = observed["coverage"]
        _exact_keys(body, {
            "watch_id", "total_hits", "distinct_pc_count", "truncated",
            "pcs", "counts_by_pc",
        }, f"{where}: coverage {index} result")
        total = _nonnegative_int(
            body["total_hits"], f"{where}: coverage {index} hits")
        distinct = _nonnegative_int(
            body["distinct_pc_count"],
            f"{where}: coverage {index} distinct PCs")
        watch_id = _nonnegative_int(
            body["watch_id"], f"{where}: coverage {index} watch ID")
        if body["truncated"] is not False or \
                not isinstance(body["pcs"], list) or \
                not isinstance(body["counts_by_pc"], list) or \
                watch_id < 1 or \
                distinct != len(body["pcs"]) or \
                distinct != len(body["counts_by_pc"]):
            raise MetricsError(
                f"{where}: coverage {index} is truncated/inconsistent")
        counts = 0
        observed_pcs: list[str] = []
        for count_index, count_row in enumerate(body["counts_by_pc"]):
            if not isinstance(count_row, dict):
                raise MetricsError(
                    f"{where}: coverage {index} count {count_index} is invalid")
            _exact_keys(
                count_row, {"pc", "count"},
                f"{where}: coverage {index} count {count_index}")
            if not isinstance(count_row["pc"], str) or not re.fullmatch(
                    r"0x[0-9a-f]{8}", count_row["pc"]):
                raise MetricsError(
                    f"{where}: coverage {index} PC is invalid")
            counts += _nonnegative_int(
                count_row["count"],
                f"{where}: coverage {index} count")
            if count_row["count"] < 1 or \
                    int(count_row["pc"], 16) < requested["start"] or \
                    int(count_row["pc"], 16) > requested["end"]:
                raise MetricsError(
                    f"{where}: coverage {index} count escapes its range")
            observed_pcs.append(count_row["pc"])
        if body["pcs"] != observed_pcs or counts != total:
            raise MetricsError(
                f"{where}: coverage {index} totals are not derived")


def _validate_perturbation_plan(doc: dict[str, Any], where: str) -> None:
    _exact_keys(doc, {"schema", "kind", "operations"}, where)
    if doc["schema"] != "abl-phase4-perturbation-plan/1" or \
            doc["kind"] not in {"none", "operations"}:
        raise MetricsError(f"{where}: perturbation-plan schema/kind mismatch")
    operations = doc["operations"]
    if not isinstance(operations, list):
        raise MetricsError(f"{where}: perturbation operations are not an array")
    if (doc["kind"] == "none") != (operations == []):
        raise MetricsError(f"{where}: perturbation kind disagrees with operations")
    if len(operations) > 128:
        raise MetricsError(f"{where}: perturbation operation limit exceeded")
    schemas = {
        "memory_write": {
            "sequence", "kind", "address", "width_bits", "before", "after",
        },
        "register_write": {
            "sequence", "kind", "register_index", "before", "after",
        },
        "input_edit": {
            "sequence", "kind", "port", "control_kind", "control_index",
            "start_frame", "stop_frame", "value",
        },
        "code_write": {
            "sequence", "kind", "address", "original_word", "replacement_word",
        },
        "disc_overlay": {
            "sequence", "kind", "lba_start", "sector_count",
            "base_extent_sha256", "replacement_extent_sha256",
        },
    }
    integer_keys = {
        "address", "width_bits", "before", "after", "register_index", "port",
        "control_index", "start_frame", "stop_frame", "value", "original_word",
        "replacement_word", "lba_start", "sector_count",
    }
    for sequence, operation in enumerate(operations):
        if not isinstance(operation, dict) or operation.get("kind") not in schemas:
            raise MetricsError(f"{where}: invalid perturbation operation")
        kind = operation["kind"]
        _exact_keys(operation, schemas[kind], f"{where}: operation {sequence}")
        if operation["sequence"] != sequence:
            raise MetricsError(f"{where}: perturbation sequence is not contiguous")
        for key in integer_keys & set(operation):
            _nonnegative_int(operation[key], f"{where}: operation {sequence}.{key}")
        if "width_bits" in operation and operation["width_bits"] not in {8, 16, 32}:
            raise MetricsError(f"{where}: invalid write width")
        if "address" in operation and operation["address"] > 0xFFFFFFFF:
            raise MetricsError(f"{where}: address exceeds the PS1 address width")
        if kind == "memory_write":
            limit = 1 << operation["width_bits"]
            if operation["before"] >= limit or operation["after"] >= limit:
                raise MetricsError(f"{where}: memory-write value exceeds its width")
        if kind in {"register_write", "code_write"}:
            for key in ({"before", "after"} if kind == "register_write"
                        else {"original_word", "replacement_word"}):
                if operation[key] > 0xFFFFFFFF:
                    raise MetricsError(f"{where}: {key} exceeds 32 bits")
        if kind == "disc_overlay" and (
                operation["lba_start"] > 0x7FFFFFFF or
                operation["sector_count"] < 1 or
                operation["sector_count"] > 0x7FFFFFFF):
            raise MetricsError(f"{where}: disc overlay range is invalid")
        if "register_index" in operation and operation["register_index"] > 31:
            raise MetricsError(f"{where}: invalid register index")
        if "port" in operation and operation["port"] not in {0, 1}:
            raise MetricsError(f"{where}: invalid controller port")
        if "control_kind" in operation and operation["control_kind"] not in {
                "digital_bit", "axis"}:
            raise MetricsError(f"{where}: invalid control kind")
        if kind == "input_edit":
            max_index = 15 if operation["control_kind"] == "digital_bit" else 7
            max_value = 1 if operation["control_kind"] == "digital_bit" else 255
            if operation["control_index"] > max_index or \
                    operation["value"] > max_value or \
                    operation["start_frame"] > MAX_CLOCK_VALUE or \
                    operation["stop_frame"] > MAX_CLOCK_VALUE:
                raise MetricsError(f"{where}: input edit exceeds controller bounds")
        if "stop_frame" in operation and \
                operation["stop_frame"] < operation["start_frame"]:
            raise MetricsError(f"{where}: invalid input-edit range")
        for key in ("base_extent_sha256", "replacement_extent_sha256"):
            if key in operation and not (
                    isinstance(operation[key], str) and
                    HEX64.fullmatch(operation[key])):
                raise MetricsError(f"{where}: invalid extent hash")


def _validate_control_plan(doc: dict[str, Any], where: str) -> None:
    _exact_keys(doc, {
        "schema", "role", "paired_run_basis_sha256", "anchor_sha256",
        "only_difference_plan_sha256", "assertion_plan_sha256",
    }, where)
    if doc["schema"] != "abl-phase4-control-plan/1" or doc["role"] not in {
            "baseline", "positive", "negative"}:
        raise MetricsError(f"{where}: control-plan schema/role mismatch")
    for key in set(doc) - {"schema", "role"}:
        if not isinstance(doc[key], str) or not HEX64.fullmatch(doc[key]):
            raise MetricsError(f"{where}: invalid {key}")


RESULT_SCHEMAS = {
    "abl-phase4-live-raw-results/1": {
        "schema", "complete", "errors", "counters", "sessions", "results",
    },
    "abl-phase4-live-pagination/1": {
        "schema", "complete", "errors", "truncated", "pages_complete", "pages",
    },
    "abl-phase4-live-media-capabilities/1": {
        "schema", "complete", "errors", "mounted_serial",
        "pristine_media_sha256", "duckstation_source_sha256",
        "duckstation_executable_sha256", "api_surface_sha256", "capabilities",
    },
    "abl-phase4-live-command-events/1": {
        "schema", "complete", "errors", "events",
    },
    "abl-phase4-owned-pid-cleanup/1": {
        "schema", "complete", "errors", "owned_pid", "owned_pid_stopped",
        "config_dir", "actions",
    },
}


def _validate_result_doc(
        doc: dict[str, Any], schema: str, where: str,
        *, allow_empty_pagination: bool = False) -> None:
    _exact_keys(doc, RESULT_SCHEMAS[schema], where)
    if doc.get("schema") != schema:
        raise MetricsError(f"{where}: schema mismatch")
    if doc.get("complete") is not True:
        raise MetricsError(f"{where}: result is incomplete")
    if _closed_strings(doc.get("errors"), f"{where}: errors"):
        raise MetricsError(f"{where}: result records errors")
    _no_floats(doc, where)
    list_fields = {
        "abl-phase4-live-raw-results/1": ("results",),
        "abl-phase4-live-pagination/1": ("pages",),
        "abl-phase4-live-command-events/1": ("events",),
        "abl-phase4-owned-pid-cleanup/1": ("actions",),
    }.get(schema, ())
    for field in list_fields:
        if not isinstance(doc[field], list):
            raise MetricsError(f"{where}: {field} is not an array")
    if schema == "abl-phase4-live-raw-results/1":
        sessions = doc["sessions"]
        results = doc["results"]
        if not isinstance(sessions, list) or not sessions or not results:
            raise MetricsError(f"{where}: sessions/results are empty")
        if len(results) > 128:
            raise MetricsError(f"{where}: atomic job limit exceeded")
        session_ids: set[str] = set()
        for index, session in enumerate(sessions):
            _exact_keys(session, {"server_session_id", "launch_sequence"},
                        f"{where}: sessions[{index}]")
            if not isinstance(session["server_session_id"], str) or not \
                    session["server_session_id"] or \
                    session["server_session_id"] in session_ids or \
                    session["launch_sequence"] != index:
                raise MetricsError(f"{where}: invalid/duplicate server session")
            session_ids.add(session["server_session_id"])
        job_keys: set[tuple[str, str]] = set()
        for index, result in enumerate(results):
            _exact_keys(result, {
                "job_id", "server_session_id", "status",
                "replay_start", "replay_stop", "observer_start",
                "observer_stop", "instruction_start", "instruction_stop",
            }, f"{where}: results[{index}]")
            if not isinstance(result["job_id"], str) or not result["job_id"] or \
                    result["server_session_id"] not in session_ids or \
                    result["status"] != "completed":
                raise MetricsError(f"{where}: raw job is not completed/joined")
            job_key = (result["server_session_id"], result["job_id"])
            if job_key in job_keys:
                raise MetricsError(f"{where}: duplicate raw job identity")
            job_keys.add(job_key)
            for field in (
                    "replay_start", "replay_stop", "observer_start",
                    "observer_stop", "instruction_start", "instruction_stop"):
                value = _nonnegative_int(
                    result[field], f"{where}: results[{index}].{field}")
                if value > MAX_CLOCK_VALUE:
                    raise MetricsError(
                        f"{where}: raw job counter exceeds the typed clock bound")
            if any(result[stop] < result[start] for start, stop in (
                    ("replay_start", "replay_stop"),
                    ("observer_start", "observer_stop"),
                    ("instruction_start", "instruction_stop"))):
                raise MetricsError(f"{where}: raw job counters run backwards")
    elif schema == "abl-phase4-live-pagination/1":
        if not doc["pages"] and not allow_empty_pagination:
            raise MetricsError(f"{where}: no retained pagination record")
        for index, page in enumerate(doc["pages"]):
            _exact_keys(page, {"page", "record_count"},
                        f"{where}: pages[{index}]")
            if page["page"] != index:
                raise MetricsError(f"{where}: pagination is not contiguous")
            _nonnegative_int(
                page["record_count"], f"{where}: pages[{index}].record_count")
    elif schema == "abl-phase4-live-command-events/1":
        if not doc["events"]:
            raise MetricsError(f"{where}: command event stream is empty")
        methods: list[str] = []
        identity_methods: list[str] = []
        for index, event in enumerate(doc["events"]):
            if not isinstance(event, dict):
                raise MetricsError(f"{where}: events[{index}] is not an object")
            direct = "socket_timeout_ms" in event
            event_keys = {
                "sequence", "server_session_id", "method", "params",
                "result_sha256", "result",
            }
            if direct:
                event_keys.add("socket_timeout_ms")
            _exact_keys(
                event, event_keys,
                        f"{where}: events[{index}]")
            if event["sequence"] != index or not isinstance(event["method"], str) or \
                    not isinstance(event["server_session_id"], str) or not \
                    event["server_session_id"] or \
                    not isinstance(event["result_sha256"], str) or not \
                    HEX64.fullmatch(event["result_sha256"]):
                raise MetricsError(f"{where}: command event is invalid")
            if event["result_sha256"] != hashlib.sha256(
                    canonical_bytes(event["result"])).hexdigest():
                raise MetricsError(f"{where}: command result hash is not derived")
            if not isinstance(event["params"], dict) or \
                    not isinstance(event["result"], dict):
                raise MetricsError(f"{where}: command params/result are not objects")
            method = event["method"]
            if direct:
                timeout = _nonnegative_int(
                    event["socket_timeout_ms"],
                    f"{where}: event {index} socket timeout")
                if timeout < 1 or timeout > 60000 or \
                        method not in DIRECT_EXACT_PC_COMMAND_METHODS:
                    raise MetricsError(
                        f"{where}: direct command method/timeout is invalid")
            if method in REQUIRED_LIVE_COMMAND_METHODS:
                _exact_keys(
                    event["params"], set(),
                    f"{where}: {method} params")
                if not direct:
                    identity_methods.append(method)
            elif method == "scenario.runBatch":
                _exact_keys(
                    event["params"], {"plan_sha256"},
                    f"{where}: scenario.runBatch params")
                _exact_keys(
                    event["result"], {"batch_id", "job_ids"},
                    f"{where}: scenario.runBatch result")
                if not isinstance(event["params"]["plan_sha256"], str) or not \
                        HEX64.fullmatch(event["params"]["plan_sha256"]) or \
                        not isinstance(event["result"]["batch_id"], str) or not \
                        event["result"]["batch_id"] or \
                        not isinstance(event["result"]["job_ids"], list) or \
                        not 1 <= len(event["result"]["job_ids"]) <= 128 or \
                        len(set(event["result"]["job_ids"])) != \
                        len(event["result"]["job_ids"]) or \
                        not all(isinstance(item, str) and item
                                for item in event["result"]["job_ids"]):
                    raise MetricsError(f"{where}: scenario.runBatch event is invalid")
            elif method == "scenario.getBatch":
                _exact_keys(
                    event["params"], {"batch_id", "include_results"},
                    f"{where}: scenario.getBatch params")
                _exact_keys(
                    event["result"], {"batch_id", "status", "job_ids"},
                    f"{where}: scenario.getBatch result")
                if event["result"]["batch_id"] != event["params"]["batch_id"] or \
                        event["result"]["status"] not in {
                            "queued", "running", "completed", "cancelled",
                            "failed"} or \
                        not isinstance(event["params"]["include_results"], bool) or \
                        not isinstance(event["result"]["job_ids"], list):
                    raise MetricsError(f"{where}: scenario.getBatch event is invalid")
            elif method == "movie.traceToFrame":
                _validate_movie_trace_event(
                    event["params"], event["result"],
                    f"{where}: event {index}")
            elif direct and method == "debugger.runUntilAddress":
                _exact_keys(
                    event["params"], {"address"},
                    f"{where}: debugger.runUntilAddress params")
                if not isinstance(event["params"]["address"], str) or not \
                        re.fullmatch(
                            r"0x[0-9A-Fa-f]{8}",
                            event["params"]["address"]):
                    raise MetricsError(
                        f"{where}: runUntilAddress parameter is invalid")
            elif direct and method in {
                    "debugger.getRegisters", "debugger.pause",
                    "debugger.listBreakpoints", "debugger.resume",
                    "transferLog.clear",
                    "transferLog.start", "transferLog.stop"}:
                _exact_keys(
                    event["params"], set(),
                    f"{where}: {method} params")
            elif direct and method == "debugger.addBreakpoint":
                _exact_keys(
                    event["params"],
                    {"address", "type", "enabled", "temporary"},
                    f"{where}: debugger.addBreakpoint params")
                address = _nonnegative_int(
                    event["params"]["address"],
                    f"{where}: debugger.addBreakpoint address")
                if address > 0xFFFFFFFF or address & 3 or \
                        event["params"]["type"] != "execute" or \
                        event["params"]["enabled"] is not True or \
                        event["params"]["temporary"] is not False:
                    raise MetricsError(
                        f"{where}: debugger.addBreakpoint params are invalid")
            elif direct and method == "debugger.removeBreakpoint":
                _exact_keys(
                    event["params"], {"id"},
                    f"{where}: debugger.removeBreakpoint params")
                if not isinstance(event["params"]["id"], str) or \
                        not event["params"]["id"].startswith("bp_"):
                    raise MetricsError(
                        f"{where}: debugger.removeBreakpoint id is invalid")
            elif direct and method == "transferLog.get":
                _exact_keys(
                    event["params"], {"offset", "limit"},
                    f"{where}: transferLog.get params")
                offset = _nonnegative_int(
                    event["params"]["offset"],
                    f"{where}: transferLog.get offset")
                limit = _nonnegative_int(
                    event["params"]["limit"],
                    f"{where}: transferLog.get limit")
                if offset > 1_000_000 or not 1 <= limit <= 10_000:
                    raise MetricsError(
                        f"{where}: transferLog.get bounds are invalid")
            elif direct and method == "capture.atomic":
                _no_floats(
                    event["params"],
                    f"{where}: capture.atomic params")
            else:
                raise MetricsError(f"{where}: command method is not closed")
            methods.append(event["method"])
        identity_counts = {
            method: identity_methods.count(method)
            for method in REQUIRED_LIVE_COMMAND_METHODS
        }
        if any(count != 1 for count in identity_counts.values()):
            raise MetricsError(
                f"{where}: identity/capability events must occur exactly once: "
                f"{identity_counts}")
        missing_atomic = REQUIRED_ATOMIC_COMMAND_METHODS - set(methods)
        if missing_atomic:
            raise MetricsError(
                f"{where}: atomic execution events missing: {sorted(missing_atomic)}")
    elif schema == "abl-phase4-owned-pid-cleanup/1":
        if not isinstance(doc["owned_pid"], int) or \
                isinstance(doc["owned_pid"], bool) or doc["owned_pid"] < 2:
            raise MetricsError(f"{where}: owned PID is invalid")
        if not doc["actions"] or not all(
                isinstance(item, dict) and
                set(item) == {"sequence", "kind", "pid"} and
                item["sequence"] == index and
                item["kind"] in {"stop_owned_pid", "confirm_pid_stopped"} and
                item["pid"] == doc["owned_pid"]
                for index, item in enumerate(doc["actions"])):
            raise MetricsError(f"{where}: cleanup actions are not typed/complete")
        if {item["kind"] for item in doc["actions"]} != {
                "stop_owned_pid", "confirm_pid_stopped"}:
            raise MetricsError(f"{where}: cleanup lacks stop confirmation")


def _validate_preservation_manifest(
        path: Path, refs: list[tuple[Path, dict[str, Any]]], where: str) -> int:
    doc = load_json(path)
    _exact_keys(doc, {"schema", "complete", "errors", "entries"}, where)
    if doc["schema"] != "abl-phase4-method-external-preservation/1" or \
            doc["complete"] is not True or \
            _closed_strings(doc["errors"], f"{where}: errors"):
        raise MetricsError(f"{where}: preservation manifest is not closed")
    entries = doc["entries"]
    if not isinstance(entries, list):
        raise MetricsError(f"{where}: preservation entries are not an array")
    indexed: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MetricsError(f"{where}: entry {index} is not an object")
        _exact_keys(entry, {
            "sha256", "size", "media_class", "preservation_required",
        }, f"{where}: entry {index}")
        digest = entry["sha256"]
        if not isinstance(digest, str) or not HEX64.fullmatch(digest) or \
                digest in indexed:
            raise MetricsError(f"{where}: invalid/duplicate preservation hash")
        _nonnegative_int(entry["size"], f"{where}: entry {index}.size")
        if entry["media_class"] not in {
                "pristine", "non_pristine", "derived_pristine_evidence",
                "tool_source", "runtime_receipt"}:
            raise MetricsError(f"{where}: invalid media class")
        if entry["preservation_required"] is not True:
            raise MetricsError(f"{where}: preservation is not required")
        indexed[digest] = entry
    total = 0
    for artifact_path, ref in refs:
        entry = indexed.get(ref["sha256"])
        if entry is None:
            raise MetricsError(
                f"{where}: referenced artifact absent from preservation set")
        if entry["size"] != artifact_path.stat().st_size:
            raise MetricsError(f"{where}: preserved size disagrees with bytes")
        total += entry["size"]
    return total


def _planned_live_join(
        receipt: dict[str, Any], before_ledger: dict[str, Any],
        selected_rows: list[str], where: str) -> None:
    escalation_id = receipt["escalation_id"]
    missing_fact_id = receipt["missing_fact_id"]
    if not isinstance(escalation_id, str) or not escalation_id or \
            not isinstance(missing_fact_id, str) or not missing_fact_id:
        raise MetricsError(f"{where}: escalation/missing-fact IDs are invalid")
    entries = before_ledger.get("entries")
    if not isinstance(entries, list):
        raise MetricsError(f"{where}: before-ledger entries are malformed")
    matches = [
        entry for entry in entries
        if entry.get("id") == escalation_id and entry.get("state") == "planned"
        and entry.get("missing_fact_id") == missing_fact_id
        and entry.get("target_row") in selected_rows
    ]
    if len(matches) != 1:
        raise MetricsError(
            f"{where}: live work lacks a unique pre-planned escalation/missing-fact join")


def _validate_duckstation_authority(
        media: dict[str, Any], tested_root: Path, where: str) -> None:
    """Join a live claim to repository-pinned media and DuckStation identities."""
    manifest_path = tested_root / "analysis" / "phase3_duckstation_rpc_manifest.json"
    if not manifest_path.is_file():
        raise MetricsError(f"{where}: DuckStation authority manifest is absent")
    manifest = load_json(manifest_path)
    source = manifest.get("source")
    binaries = manifest.get("binaries")
    methods = manifest.get("methods")
    if not isinstance(source, dict) or not isinstance(binaries, dict) or \
            not isinstance(methods, dict):
        raise MetricsError(f"{where}: DuckStation authority manifest is malformed")
    source_digest = hashlib.sha256(canonical_bytes(source)).hexdigest()
    binary_digests = {
        value.get("sha256") for value in binaries.values()
        if isinstance(value, dict)
    }
    api_digest = hashlib.sha256(canonical_bytes(methods)).hexdigest()
    if media.get("pristine_media_sha256") != PRISTINE_MEDIA_SHA256:
        raise MetricsError(f"{where}: media hash is not the retail authority pin")
    if media.get("duckstation_source_sha256") != source_digest:
        raise MetricsError(f"{where}: DuckStation source identity is not manifest-pinned")
    if media.get("duckstation_executable_sha256") not in binary_digests:
        raise MetricsError(f"{where}: running DuckStation binary is not manifest-pinned")
    if media.get("api_surface_sha256") != api_digest:
        raise MetricsError(f"{where}: API surface identity is not manifest-derived")
    declared_methods = set(methods.get("committed") or ()) | \
        set(methods.get("dirty_only") or ())
    receipt_methods = set((media.get("capabilities") or {}).get(
        "method_schemas") or ())
    if not receipt_methods <= declared_methods:
        raise MetricsError(f"{where}: receipt claims methods outside the authority manifest")


def _validate_anchor_fixtures(
        anchor: dict[str, Any], tested_root: Path, where: str) -> None:
    fixture_path = tested_root / "analysis" / "phase0_2_external_fixture_set.json"
    required = {
        anchor[key] for key in ("movie_sha256", "state_sha256")
        if anchor[key] is not None
    }
    if not required:
        return
    if not fixture_path.is_file():
        raise MetricsError(f"{where}: central anchor fixture manifest is absent")
    fixtures = load_json(fixture_path).get("entries")
    if not isinstance(fixtures, dict):
        raise MetricsError(f"{where}: central anchor fixture manifest is malformed")
    for digest in required:
        matches = [
            (logical, declaration)
            for logical, declaration in fixtures.items()
            if isinstance(logical, str) and isinstance(declaration, dict) and
            declaration.get("sha256") == digest and
            declaration.get("media_class") in {"pristine", "pristine_serial"} and
            declaration.get("preservation_required") is True
        ]
        if not matches:
            raise MetricsError(
                f"{where}: movie/state anchor is not centrally declared pristine "
                "evidence")
        verified = False
        for logical, declaration in matches:
            path = tested_root / logical
            if path.is_file() and not path.is_symlink() and \
                    path.stat().st_size == declaration.get("size") and \
                    sha256(path) == digest:
                verified = True
                break
        if not verified:
            raise MetricsError(
                f"{where}: centrally declared movie/state anchor is not provisioned")


def _validate_direct_exact_pc_stream(
        observer: dict[str, Any], command_events: dict[str, Any],
        raw: dict[str, Any], pagination: dict[str, Any],
        experiment: dict[str, Any], media: dict[str, Any],
        adapter_path: str, terminal_gets: list[dict[str, Any]],
        tested_root: Path, where: str) -> dict[str, Any] | None:
    """Re-run the exact-PC adapter against retained direct result bodies.

    The retained RPC bodies are not trusted as a transcript.  The tracked adapter
    must consume them in its exact typed order and independently re-derive the
    bounded stop, register, pagination, and terminal-capture result.
    """
    direct_events = [
        event for event in command_events["events"]
        if "socket_timeout_ms" in event
    ]
    if observer["schema"] == "abl-phase4-observer-plan/1":
        if direct_events:
            raise MetricsError(
                f"{where}: historical observer plan cannot admit direct commands")
        return None
    if observer["schema"] != "abl-phase4-observer-plan/2":
        raise MetricsError(f"{where}: unsupported direct observer schema")
    if observer["direct_command_plan"].get("schema") != \
            "abl-phase4-duckstation-exact-pc-plan/1":
        return None
    if adapter_path != "tools/phase4_duckstation_exact_pc_batch.py":
        raise MetricsError(
            f"{where}: direct exact-PC observer requires the tracked exact adapter")
    if experiment["domain"] != "dma":
        raise MetricsError(f"{where}: exact-PC transfer observer is not DMA-typed")
    if not direct_events:
        raise MetricsError(f"{where}: direct exact-PC command stream is absent")
    if not terminal_gets or any(
            event["sequence"] <= max(item["sequence"] for item in terminal_gets)
            for event in direct_events):
        raise MetricsError(
            f"{where}: direct exact-PC commands did not follow the atomic anchor")

    plan = observer["direct_command_plan"]
    identity = plan["identity_join"]
    manifest_path = tested_root / "analysis/phase3_duckstation_rpc_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise MetricsError(f"{where}: current RPC manifest is absent")
    manifest = load_json(manifest_path)
    source = manifest.get("source")
    binaries = manifest.get("binaries")
    if not isinstance(source, dict) or not isinstance(binaries, dict):
        raise MetricsError(f"{where}: current RPC manifest is malformed")
    binary = binaries.get("build-release/bin/duckstation-qt")
    expected_identity = {
        "rpc_manifest_sha256": sha256(manifest_path),
        "source_revision": source.get("revision"),
        "source_dirty_state_hash": source.get("dirty_state_hash"),
        "dispatcher_sha256": source.get("dispatcher_sha256"),
        "binary_sha256": (
            binary.get("sha256") if isinstance(binary, dict) else None),
        "media_serial": "SCUS-94288",
        "media_sha256": experiment["anchor"]["media_sha256"],
    }
    if identity != expected_identity:
        raise MetricsError(
            f"{where}: direct command identity differs from current authority")
    if identity["binary_sha256"] != \
            experiment["duckstation_executable_sha256"] or \
            identity["media_sha256"] != PRISTINE_MEDIA_SHA256:
        raise MetricsError(
            f"{where}: direct command binary/media identity is contradictory")
    method_schemas = media["capabilities"]["method_schemas"]
    try:
        import phase4_duckstation_exact_pc_batch as exact_pc_adapter
    except ImportError as exc:
        raise MetricsError(f"{where}: exact-PC adapter is unavailable") from exc
    missing_methods = set(exact_pc_adapter.REQUIRED_METHODS) - set(method_schemas)
    if missing_methods:
        raise MetricsError(
            f"{where}: capabilities omit exact-PC methods: "
            f"{sorted(missing_methods)}")

    bound = experiment["execution"]["bound"]
    capture = experiment["execution"]["capture_window"]
    if bound["clock"] != "emulator_frame" or \
            capture["clock"] != "emulator_frame" or \
            plan["execution_limit"]["clock"] != "emulator_frame" or \
            capture["stop"] - capture["start"] != \
            plan["execution_limit"]["max_frame_delta"]:
        raise MetricsError(
            f"{where}: direct command frame bound differs from typed execution")
    results = raw["results"]
    if len(results) != 1:
        raise MetricsError(
            f"{where}: exact-PC receipt requires one atomic anchor job")
    anchor_job = results[0]
    if anchor_job["replay_stop"] != capture["start"] or \
            anchor_job["observer_start"] != capture["start"] or \
            anchor_job["observer_stop"] != capture["start"]:
        raise MetricsError(
            f"{where}: atomic job does not end at the paused capture anchor")

    server_session_id = raw["sessions"][0]["server_session_id"]
    cursor = 0

    def retained_rpc(
            observed_session: str, method: str, params: dict[str, Any],
            socket_timeout_ms: int) -> dict[str, Any]:
        nonlocal cursor
        if cursor >= len(direct_events):
            raise RuntimeError("retained direct command stream ended early")
        event = direct_events[cursor]
        cursor += 1
        if observed_session != server_session_id or \
                event["server_session_id"] != server_session_id or \
                event["method"] != method or event["params"] != params or \
                event["socket_timeout_ms"] != socket_timeout_ms:
            raise RuntimeError(
                "retained direct command differs from the typed adapter request")
        return event["result"]

    try:
        derived = exact_pc_adapter.execute_exact_pc_window(
            retained_rpc, plan, server_session_id, identity,
            sleep=lambda _seconds: None)
    except exact_pc_adapter.ExactPcFalsifiedError as exc:
        if cursor != len(direct_events):
            raise MetricsError(
                f"{where}: falsified direct command stream has extras") from exc
        reason = str(exc)
        if ("finite emulator-frame bound" in reason or
                "finite status-poll bound" in reason) and (
                direct_events[-1]["method"] != "debugger.pause" or
                direct_events[-1]["result"].get("paused") is not True):
            raise MetricsError(
                f"{where}: bounded falsifier lacks retained pause") from exc
        if pagination["pages"] != [] or \
                pagination["pages_complete"] is not True or \
                pagination["truncated"] is not False:
            raise MetricsError(
                f"{where}: falsified direct command stream claims pages") from exc
        return {
            "schema": exact_pc_adapter.RESULT_SCHEMA,
            "complete": True,
            "errors": [],
            "outcome": "falsified",
            "reason": reason,
            "command_event_count": len(direct_events),
        }
    except (RuntimeError, ValueError) as exc:
        raise MetricsError(
            f"{where}: retained exact-PC stream failed adapter replay: {exc}") from exc
    if cursor != len(direct_events):
        raise MetricsError(f"{where}: retained direct command stream has extras")
    derived_events = derived["command_events"]["events"]
    normalized_retained = [
        {**event, "sequence": index}
        for index, event in enumerate(direct_events)
    ]
    if derived_events != normalized_retained:
        raise MetricsError(
            f"{where}: direct command stream is not adapter-derived")
    if derived["execution"]["anchor_frame"] != capture["start"] or \
            derived["execution"]["frame_ceiling"] != capture["stop"] or \
            derived["execution"]["terminal_stop_frame"] > capture["stop"]:
        raise MetricsError(
            f"{where}: direct execution escapes the typed capture window")
    transfer_pages = derived["transfer"]["pages"]
    expected_pages = [
        {"page": index, "record_count": page["returned"]}
        for index, page in enumerate(transfer_pages)
    ]
    if pagination["pages"] != expected_pages or \
            pagination["pages_complete"] is not True or \
            pagination["truncated"] is not False:
        raise MetricsError(
            f"{where}: receipt pagination differs from direct transfer pages")
    return derived


def _validate_direct_two_pc_first_hit_stream(
        observer: dict[str, Any], command_events: dict[str, Any],
        raw: dict[str, Any], pagination: dict[str, Any],
        experiment: dict[str, Any], media: dict[str, Any],
        adapter_path: str, terminal_gets: list[dict[str, Any]],
        tested_root: Path, where: str) -> dict[str, Any] | None:
    """Replay a retained managed-breakpoint stream through its tracked adapter."""
    if observer["schema"] != "abl-phase4-observer-plan/2" or \
            observer["direct_command_plan"].get("schema") != \
            "abl-phase4-duckstation-two-pc-first-hit-plan/1":
        return None
    direct_events = [
        event for event in command_events["events"]
        if "socket_timeout_ms" in event
    ]
    if adapter_path != "tools/phase4_duckstation_two_pc_first_hit.py":
        raise MetricsError(
            f"{where}: managed first-hit observer requires the tracked "
            "two-PC adapter")
    if experiment["domain"] != "interface":
        raise MetricsError(
            f"{where}: managed first-hit observer is not interface-typed")
    if not direct_events:
        raise MetricsError(
            f"{where}: managed first-hit command stream is absent")
    if not terminal_gets or any(
            event["sequence"] <= max(item["sequence"] for item in terminal_gets)
            for event in direct_events):
        raise MetricsError(
            f"{where}: managed first-hit commands did not follow the atomic "
            "anchor")

    plan = observer["direct_command_plan"]
    identity = plan["identity_join"]
    manifest_path = tested_root / "analysis/phase3_duckstation_rpc_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise MetricsError(f"{where}: current RPC manifest is absent")
    manifest = load_json(manifest_path)
    source = manifest.get("source")
    binaries = manifest.get("binaries")
    if not isinstance(source, dict) or not isinstance(binaries, dict):
        raise MetricsError(f"{where}: current RPC manifest is malformed")
    binary = binaries.get("build-release/bin/duckstation-qt")
    expected_identity = {
        "rpc_manifest_sha256": sha256(manifest_path),
        "source_revision": source.get("revision"),
        "source_dirty_state_hash": source.get("dirty_state_hash"),
        "dispatcher_sha256": source.get("dispatcher_sha256"),
        "binary_sha256": (
            binary.get("sha256") if isinstance(binary, dict) else None),
        "media_serial": "SCUS-94288",
        "media_sha256": experiment["anchor"]["media_sha256"],
    }
    if identity != expected_identity:
        raise MetricsError(
            f"{where}: managed first-hit identity differs from current authority")
    if identity["binary_sha256"] != \
            experiment["duckstation_executable_sha256"] or \
            identity["media_sha256"] != PRISTINE_MEDIA_SHA256:
        raise MetricsError(
            f"{where}: managed first-hit binary/media identity is contradictory")

    try:
        import phase4_duckstation_two_pc_first_hit as first_hit_adapter
    except ImportError as exc:
        raise MetricsError(
            f"{where}: two-PC first-hit adapter is unavailable") from exc
    method_schemas = media["capabilities"]["method_schemas"]
    missing_methods = set(first_hit_adapter.REQUIRED_METHODS) - \
        set(method_schemas)
    if missing_methods:
        raise MetricsError(
            f"{where}: capabilities omit first-hit methods: "
            f"{sorted(missing_methods)}")

    bound = experiment["execution"]["bound"]
    capture = experiment["execution"]["capture_window"]
    if bound["clock"] != "emulator_frame" or \
            capture["clock"] != "emulator_frame" or \
            plan["execution_limit"]["clock"] != "emulator_frame" or \
            capture["stop"] - capture["start"] != 64 or \
            plan["execution_limit"]["max_frame_delta"] != 64:
        raise MetricsError(
            f"{where}: managed first-hit frame bound is not the exact "
            "64-frame predeclaration")
    results = raw["results"]
    if len(results) != 1:
        raise MetricsError(
            f"{where}: first-hit receipt requires one atomic anchor job")
    anchor_job = results[0]
    if anchor_job["replay_stop"] != capture["start"] or \
            anchor_job["observer_start"] != capture["start"] or \
            anchor_job["observer_stop"] != capture["start"]:
        raise MetricsError(
            f"{where}: atomic job does not end at the paused first-hit anchor")
    if pagination["pages"] != [] or \
            pagination["pages_complete"] is not True or \
            pagination["truncated"] is not False:
        raise MetricsError(
            f"{where}: managed first-hit receipt must retain closed empty "
            "pagination")

    server_session_id = raw["sessions"][0]["server_session_id"]
    cursor = 0

    def retained_rpc(
            observed_session: str, method: str, params: dict[str, Any],
            socket_timeout_ms: int) -> dict[str, Any]:
        nonlocal cursor
        if cursor >= len(direct_events):
            raise RuntimeError("retained first-hit command stream ended early")
        event = direct_events[cursor]
        cursor += 1
        if observed_session != server_session_id or \
                event["server_session_id"] != server_session_id or \
                event["method"] != method or event["params"] != params or \
                event["socket_timeout_ms"] != socket_timeout_ms:
            raise RuntimeError(
                "retained first-hit command differs from the typed adapter "
                "request")
        return event["result"]

    try:
        derived = first_hit_adapter.execute_first_hit(
            retained_rpc, plan, server_session_id, identity,
            sleep=lambda _seconds: None)
    except first_hit_adapter.FirstHitFalsifiedError as exc:
        if cursor != len(direct_events):
            raise MetricsError(
                f"{where}: falsified first-hit command stream has extras") from exc
        reason = str(exc)
        last = direct_events[-1]
        if reason in {
                "first-hit failure cleanup could not prove an empty breakpoint set",
                "first-hit failure cleanup left managed breakpoints armed"} or \
                last["method"] != "debugger.listBreakpoints" or \
                last["result"].get("breakpoints") != []:
            raise MetricsError(
                f"{where}: falsified first-hit stream lacks complete owned "
                "breakpoint cleanup") from exc
        return {
            "schema": first_hit_adapter.RESULT_SCHEMA,
            "complete": True,
            "errors": [],
            "outcome": "falsified",
            "reason": reason,
            "command_event_count": len(direct_events),
        }
    except (RuntimeError, ValueError) as exc:
        raise MetricsError(
            f"{where}: retained first-hit stream failed adapter replay: "
            f"{exc}") from exc
    if cursor != len(direct_events):
        raise MetricsError(f"{where}: retained first-hit command stream has extras")
    normalized_retained = [
        {**event, "sequence": index}
        for index, event in enumerate(direct_events)
    ]
    if derived["command_events"]["events"] != normalized_retained:
        raise MetricsError(
            f"{where}: first-hit command stream is not adapter-derived")
    execution = derived["execution"]
    if execution["anchor_frame"] != capture["start"] or \
            execution["frame_ceiling"] != capture["stop"] or \
            execution["first_hit_frame"] > capture["stop"]:
        raise MetricsError(
            f"{where}: first-hit execution escapes the typed capture window")
    added_ids = [
        event["result"].get("id") for event in direct_events
        if event["method"] == "debugger.addBreakpoint"
    ]
    if len(added_ids) != 2 or len(set(added_ids)) != 2 or \
            any(not isinstance(identifier, str) or
                not identifier.startswith("bp_")
                for identifier in added_ids) or \
            derived["cleanup"] != {
                "owned_breakpoint_ids": added_ids,
                "remaining_breakpoints": 0,
            }:
        raise MetricsError(
            f"{where}: first-hit owned-breakpoint cleanup is incomplete")
    return derived


def _validate_live_receipt(
        path: Path, doc: dict[str, Any], run_dir: Path, tested_root: Path,
        before_ledger: dict[str, Any], after_ledger: dict[str, Any],
        selected_rows: list[str],
        verifier: dict[str, Any] | None, legacy_index: dict[str, Any],
        where: str) -> dict[str, Any]:
    _exact_keys(doc, LIVE_RECEIPT_KEYS, where)
    if doc["schema"] != LIVE_SCHEMA or doc["complete"] is not True or \
            _closed_strings(doc["errors"], f"{where}: errors"):
        raise MetricsError(f"{where}: live receipt is not closed")
    if not isinstance(doc["precise"], bool):
        raise MetricsError(f"{where}: precise is not boolean")
    key = _canonical_live_key(doc)
    if doc["experiment"]["executor_role"] == "investigator":
        _planned_live_join(doc, before_ledger, selected_rows, where)
        planned = next(
            entry for entry in before_ledger["entries"]
            if entry.get("id") == doc["escalation_id"])
        row_id = planned["target_row"]
        anchor = doc["experiment"]["anchor"]
        overlaps = [
            entry for entry in legacy_index["entries"]
            if entry["target_row"] == row_id and
            (entry["media_sha256"] is None or
             entry["media_sha256"] == anchor["media_sha256"]) and
            (entry["movie_sha256"] is None or
             entry["movie_sha256"] == anchor["movie_sha256"]) and
            (entry["state_sha256"] is None or
             entry["state_sha256"] == anchor["state_sha256"]) and
            (
                entry.get("normalization", "conservative_deny") ==
                "conservative_deny" or
                entry.get("domain") == doc["experiment"]["domain"]
            )
        ]
        if overlaps:
            raise MetricsError(
                f"{where}: investigator run overlaps conservative pre-v2 deny "
                f"entries {[item.get('escalation_id', '<unknown>') for item in overlaps]}")
    elif verifier is None or sha256(path) not in \
            verifier["verified_live_receipt_sha256s"]:
        raise MetricsError(
            f"{where}: fresh-verifier receipt is not hash-joined to verifier decision")
    evidence = doc["evidence"]
    if not isinstance(evidence, dict):
        raise MetricsError(f"{where}: evidence is not an object")
    _exact_keys(evidence, LIVE_EVIDENCE_KEYS, f"{where}: evidence")
    adapter_ref = evidence["adapter_source"]
    if not isinstance(adapter_ref, dict) or adapter_ref.get("scope") != "repo" or \
            not isinstance(adapter_ref.get("path"), str) or \
            not LIVE_ADAPTER_PATH.fullmatch(adapter_ref["path"]):
        raise MetricsError(
            f"{where}: live adapter must be a repository-pinned Phase-4 runner")
    tracked_adapter = subprocess.run(
        ["git", "-C", str(tested_root), "ls-files", "--error-unmatch",
         adapter_ref["path"]],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if tracked_adapter.returncode:
        raise MetricsError(f"{where}: live adapter is not tracked at tested commit")
    resolved: dict[str, tuple[Path, dict[str, Any]]] = {}
    for name, ref in evidence.items():
        resolved[name] = resolve_ref(
            ref, run_dir, tested_root, f"{where}: evidence.{name}")
    if resolved["settings_snapshot"][1]["sha256"] != \
            doc["experiment"]["anchor"]["settings_sha256"]:
        raise MetricsError(f"{where}: settings snapshot does not match live anchor")
    _validate_anchor_fixtures(doc["experiment"]["anchor"], tested_root, where)
    observer = load_json(resolved["observer_plan"][0])
    perturbation = load_json(resolved["perturbation_plan"][0])
    control = load_json(resolved["control_plan"][0])
    _validate_observer_plan(observer, f"{where}: observer plan")
    _validate_perturbation_plan(perturbation, f"{where}: perturbation plan")
    _validate_control_plan(control, f"{where}: control plan")
    anchor_hash = hashlib.sha256(
        canonical_bytes(doc["experiment"]["anchor"])).hexdigest()
    if control["anchor_sha256"] != anchor_hash:
        raise MetricsError(f"{where}: control anchor hash is not derived")
    if control["only_difference_plan_sha256"] != \
            resolved["perturbation_plan"][1]["sha256"]:
        raise MetricsError(f"{where}: control difference is not the perturbation plan")
    basis_object = {
        key: value for key, value in doc["experiment"].items()
        if key not in {"executor_role", "control_plan_sha256"}
    }
    if control["paired_run_basis_sha256"] != hashlib.sha256(
            canonical_bytes(basis_object)).hexdigest():
        raise MetricsError(f"{where}: paired-run basis hash is not derived")
    expected_hashes = {
        "observer_plan_sha256": resolved["observer_plan"][1]["sha256"],
        "perturbation_plan_sha256": resolved["perturbation_plan"][1]["sha256"],
        "control_plan_sha256": resolved["control_plan"][1]["sha256"],
        "adapter_source_sha256": resolved["adapter_source"][1]["sha256"],
    }
    for field, expected in expected_hashes.items():
        if doc["experiment"][field] != expected:
            raise MetricsError(f"{where}: experiment {field} disagrees with evidence")
    raw = load_json(resolved["raw_results"][0])
    _validate_result_doc(
        raw,
        "abl-phase4-live-raw-results/1", f"{where}: raw results")
    pagination = load_json(resolved["pagination"][0])
    _validate_result_doc(
        pagination, "abl-phase4-live-pagination/1", f"{where}: pagination",
        allow_empty_pagination=(
            observer["schema"] == "abl-phase4-observer-plan/2"))
    if pagination.get("truncated") is not False or \
            pagination.get("pages_complete") is not True:
        raise MetricsError(f"{where}: pagination is truncated/incomplete")
    media = load_json(resolved["media_capabilities"][0])
    _validate_result_doc(
        media, "abl-phase4-live-media-capabilities/1",
        f"{where}: media/capabilities")
    if media.get("mounted_serial") != "SCUS-94288" or \
            media.get("pristine_media_sha256") != \
            doc["experiment"]["anchor"]["media_sha256"]:
        raise MetricsError(f"{where}: mounted media is not pinned pristine authority")
    _validate_duckstation_authority(media, tested_root, where)
    for field in (
        "duckstation_source_sha256", "duckstation_executable_sha256",
        "api_surface_sha256",
    ):
        if media.get(field) != doc["experiment"][field]:
            raise MetricsError(f"{where}: {field} disagrees with capabilities")
    capabilities = media["capabilities"]
    _exact_keys(capabilities, {"api_version", "method_schemas"},
                f"{where}: capabilities")
    if not isinstance(capabilities["api_version"], str) or not \
            capabilities["api_version"]:
        raise MetricsError(f"{where}: API version is absent")
    method_schemas = capabilities["method_schemas"]
    if not isinstance(method_schemas, dict) or not method_schemas:
        raise MetricsError(f"{where}: method schemas are absent")
    for method, digest in method_schemas.items():
        if not isinstance(method, str) or not isinstance(digest, str) or not \
                HEX64.fullmatch(digest):
            raise MetricsError(f"{where}: method schema pin is invalid")
    command_events = load_json(resolved["command_events"][0])
    _validate_result_doc(
        command_events, "abl-phase4-live-command-events/1",
        f"{where}: command events")
    event_methods = {item["method"] for item in command_events["events"]}
    used_methods = {item["method"] for item in observer["operations"]}
    missing_methods = (
        used_methods | REQUIRED_LIVE_COMMAND_METHODS |
        REQUIRED_ATOMIC_COMMAND_METHODS | event_methods) - set(method_schemas)
    if missing_methods:
        raise MetricsError(
            f"{where}: capabilities omit used methods: {sorted(missing_methods)}")
    sessions = raw["sessions"]
    results = raw["results"]
    session_ids = {item["server_session_id"] for item in sessions}
    if len(session_ids) != 1:
        raise MetricsError(
            f"{where}: one live receipt must describe one owned server session")
    if any(event["server_session_id"] not in session_ids
           for event in command_events["events"]):
        raise MetricsError(
            f"{where}: command event is not joined to the owned server session")
    atomic_plan_sha256 = hashlib.sha256(canonical_bytes({
        "anchor": doc["experiment"]["anchor"],
        "execution": doc["experiment"]["execution"],
        "observer_plan_sha256": resolved["observer_plan"][1]["sha256"],
        "perturbation_plan_sha256": resolved["perturbation_plan"][1]["sha256"],
        "control_plan_sha256": resolved["control_plan"][1]["sha256"],
    })).hexdigest()
    run_events = [
        event for event in command_events["events"]
        if event["method"] == "scenario.runBatch"
    ]
    get_events = [
        event for event in command_events["events"]
        if event["method"] == "scenario.getBatch"
    ]
    if len(run_events) != 1 or not get_events:
        raise MetricsError(
            f"{where}: raw jobs lack a unique atomic batch execution")
    run_event = run_events[0]
    if any(event["sequence"] <= run_event["sequence"] for event in get_events):
        raise MetricsError(
            f"{where}: scenario.getBatch precedes its scenario.runBatch")
    identity_events = [
        event for event in command_events["events"]
        if event["method"] in REQUIRED_LIVE_COMMAND_METHODS and
        "socket_timeout_ms" not in event
    ]
    if any(event["sequence"] >= run_event["sequence"]
           for event in identity_events):
        raise MetricsError(
            f"{where}: media/capability identity was not established before execution")
    if run_event["params"]["plan_sha256"] != atomic_plan_sha256:
        raise MetricsError(f"{where}: atomic batch plan hash is not derived")
    raw_job_ids = [item["job_id"] for item in results]
    if run_event["result"]["job_ids"] != raw_job_ids:
        raise MetricsError(f"{where}: atomic batch jobs disagree with raw results")
    terminal_gets = [
        event for event in get_events
        if event["params"]["batch_id"] == run_event["result"]["batch_id"] and
        event["params"]["include_results"] is True and
        event["result"]["batch_id"] == run_event["result"]["batch_id"] and
        event["result"]["status"] == "completed" and
        event["result"]["job_ids"] == raw_job_ids
    ]
    if not terminal_gets:
        raise MetricsError(
            f"{where}: atomic batch has no completed result-bearing poll")
    _validate_direct_exact_pc_stream(
        observer, command_events, raw, pagination, doc["experiment"], media,
        adapter_ref["path"], terminal_gets, tested_root,
        f"{where}: direct exact-PC")
    _validate_direct_two_pc_first_hit_stream(
        observer, command_events, raw, pagination, doc["experiment"], media,
        adapter_ref["path"], terminal_gets, tested_root,
        f"{where}: direct two-PC first-hit")
    direct_operations = [
        operation for operation in observer["operations"]
        if operation["method"] == "movie.traceToFrame"
    ]
    direct_events = [
        event for event in command_events["events"]
        if event["method"] == "movie.traceToFrame"
    ]
    if len(direct_operations) != len(direct_events):
        raise MetricsError(
            f"{where}: direct observer operations lack exact command events")
    for operation, event in zip(direct_operations, direct_events, strict=True):
        args = operation["args"]
        expected_params = {
            "path": args["path"],
            "frame": args["frame"],
            "ranges": [
                {
                    "start": row["start"],
                    "end": row["end"],
                    "label": (
                        f"pc_{row['start']:08x}"
                    ),
                    "max_pcs": 1,
                }
                for row in args["ranges"]
            ],
            "pc_min": args["filter"]["pc_min"],
            "pc_max": args["filter"]["pc_max"],
        }
        if event["params"] != expected_params:
            raise MetricsError(
                f"{where}: direct observer command differs from its typed plan")
        if event["sequence"] <= max(
                terminal["sequence"] for terminal in terminal_gets):
            raise MetricsError(
                f"{where}: direct observer did not follow the atomic control")
    bound = doc["experiment"]["execution"]["bound"]
    capture = doc["experiment"]["execution"]["capture_window"]
    for result in results:
        if bound["clock"] in {"emulator_frame", "movie_frame"}:
            if result["replay_start"] < bound["start"] or \
                    result["replay_stop"] > bound["stop"] or \
                    result["observer_start"] < capture["start"] or \
                    result["observer_stop"] > capture["stop"]:
                raise MetricsError(
                    f"{where}: raw frame counters escape typed execution/capture")
        elif bound["clock"] == "instruction" and (
                result["instruction_start"] < bound["start"] or
                result["instruction_stop"] > bound["stop"]):
            raise MetricsError(
                f"{where}: raw instruction counters escape typed execution bound")
    by_method = {
        item["method"]: item["result"] for item in command_events["events"]
        if item["method"] in REQUIRED_LIVE_COMMAND_METHODS and
        "socket_timeout_ms" not in item
    }
    expected_identity_results = {
        "debugger.capabilities": {
            "source_sha256": media["duckstation_source_sha256"],
            "executable_sha256": media["duckstation_executable_sha256"],
            "api_surface_sha256": media["api_surface_sha256"],
            "method_schemas": media["capabilities"]["method_schemas"],
        },
        "debugger.status": {"game_serial": "SCUS-94288"},
        "emulator.getMediaInfo": {
            "serial": "SCUS-94288",
            "sha256": PRISTINE_MEDIA_SHA256,
        },
    }
    for method, expected_result in expected_identity_results.items():
        if by_method.get(method) != expected_result:
            raise MetricsError(
                f"{where}: normalized {method} result is absent or contradictory")
    cleanup = load_json(resolved["owned_pid_cleanup"][0])
    _validate_result_doc(
        cleanup, "abl-phase4-owned-pid-cleanup/1", f"{where}: cleanup")
    if cleanup.get("owned_pid_stopped") is not True or \
            not isinstance(cleanup.get("config_dir"), str) or \
            not cleanup["config_dir"].startswith("/"):
        raise MetricsError(f"{where}: owned-PID cleanup is not proven")
    config = Path(cleanup["config_dir"]).resolve(strict=False)
    normal_profiles = {
        (Path.home() / ".config" / "duckstation").resolve(strict=False),
        (Path.home() / ".local" / "share" / "duckstation").resolve(strict=False),
        (Path(os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config"))) /
         "duckstation").resolve(strict=False),
        (Path(os.environ.get(
            "XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) /
         "duckstation").resolve(strict=False),
    }
    if any(config == profile or profile in config.parents
           for profile in normal_profiles):
        raise MetricsError(f"{where}: normal DuckStation profile is forbidden")
    if any(item["method"] in PRECISE_OBSERVER_METHODS
           for item in observer["operations"]) and doc["precise"] is not True:
        raise MetricsError(f"{where}: precise observer is mislabeled as passive")
    preserved_refs = [
        item for name, item in resolved.items()
        if name != "external_preservation_manifest"
    ]
    external_bytes = _validate_preservation_manifest(
        resolved["external_preservation_manifest"][0], preserved_refs,
        f"{where}: external preservation")
    prelude_key = None
    prelude_receipt_sha256 = None
    if doc["precise"]:
        if doc["prelude_receipt"] is None:
            raise MetricsError(f"{where}: precise run lacks prelude receipt")
        prelude_path, prelude_ref = resolve_ref(
            doc["prelude_receipt"], run_dir, tested_root, f"{where}: prelude")
        prelude_receipt_sha256 = prelude_ref["sha256"]
        prelude = load_json(prelude_path)
        if prelude.get("schema") != LIVE_SCHEMA or prelude.get("precise") is not False:
            raise MetricsError(f"{where}: prelude is not a passive v2 receipt")
        prelude_key = _canonical_live_key(prelude)
        current = doc["experiment"]
        prior = prelude["experiment"]
        for field in ("anchor", "domain"):
            if current[field] != prior[field]:
                raise MetricsError(f"{where}: precise/prelude {field} differs")
        current_window = current["execution"]["capture_window"]
        prior_window = prior["execution"]["capture_window"]
        strictly_smaller = (
            current_window["clock"] == prior_window["clock"] and
            current_window["start"] >= prior_window["start"] and
            current_window["stop"] <= prior_window["stop"] and
            (current_window["start"] > prior_window["start"] or
             current_window["stop"] < prior_window["stop"])
        )
        if not strictly_smaller:
            exceptions = [] if verifier is None else verifier.get(
                "method_exceptions", [])
            receipt_hash = sha256(path)
            valid_exception = any(
                isinstance(item, dict) and
                item.get("code") == "PRECISE_WINDOW_UNAVOIDABLE" and
                item.get("live_receipt_sha256") == receipt_hash and
                isinstance(item.get("boundary_mismatch"), dict)
                for item in exceptions
            )
            if not valid_exception:
                raise MetricsError(
                    f"{where}: precise window is not strictly smaller than prelude")
    elif doc["prelude_receipt"] is not None:
        raise MetricsError(f"{where}: non-precise receipt names a prelude")
    counters = {
        "server_session_id": sessions[0]["server_session_id"],
        "launches": len(sessions),
        "atomic_jobs": len(results),
        "replay_frames": sum(
            item["replay_stop"] - item["replay_start"] for item in results),
        "observer_frames": sum(
            item["observer_stop"] - item["observer_start"] for item in results),
        "instructions": sum(
            item["instruction_stop"] - item["instruction_start"]
            for item in results),
    }
    authored_counters = raw.get("counters")
    if not isinstance(authored_counters, dict):
        raise MetricsError(f"{where}: raw counters are absent")
    expected_counter_keys = {
        "server_session_id", "launches", "atomic_jobs", "replay_frames",
        "observer_frames", "instructions",
    }
    _exact_keys(authored_counters, expected_counter_keys, f"{where}: raw counters")
    if authored_counters != counters:
        raise MetricsError(f"{where}: raw counters are not derived from jobs/sessions")
    if doc["experiment"]["executor_role"] == "investigator":
        after_entries = after_ledger.get("entries")
        if not isinstance(after_entries, list) or len([
                item for item in after_entries
                if item.get("id") == doc["escalation_id"] and
                item.get("missing_fact_id") == doc["missing_fact_id"] and
                item.get("target_row") in selected_rows and
                item.get("state") in {"executed", "closed"}
        ]) != 1:
            raise MetricsError(f"{where}: planned live escalation was not executed")
    if verifier is None or sha256(path) not in \
            verifier["verified_live_receipt_sha256s"]:
        raise MetricsError(
            f"{where}: investigator live receipt lacks independent verifier join")
    return {
        "key": key,
        "semantic_key": _semantic_live_key(
            doc, control, observer, perturbation),
        "prelude_key": prelude_key,
        "prelude_receipt_sha256": prelude_receipt_sha256,
        "precise": doc["precise"],
        "external_bytes": external_bytes,
        "counters": counters,
        "escalation_id": doc["escalation_id"],
        "missing_fact_id": doc["missing_fact_id"],
        "receipt_sha256": sha256(path),
    }


def _validate_offline_receipt(
        doc: dict[str, Any], run_dir: Path, tested_root: Path,
        where: str) -> dict[str, Any]:
    _exact_keys(doc, {
        "schema", "complete", "errors", "reader", "command", "execution", "query",
        "external_inputs", "outputs", "external_preservation_manifest",
    }, where)
    if doc["schema"] != OFFLINE_SCHEMA or doc["complete"] is not True or \
            _closed_strings(doc["errors"], f"{where}: errors"):
        raise MetricsError(f"{where}: offline receipt is not closed")
    if not isinstance(doc["query"], dict) or not doc["query"]:
        raise MetricsError(f"{where}: canonical query is missing")
    _no_floats(doc["query"], f"{where}: query")
    reader_path, _ = resolve_ref(
        doc["reader"], run_dir, tested_root, f"{where}: reader")
    try:
        reader_rel = reader_path.relative_to(tested_root).as_posix()
    except ValueError as exc:
        raise MetricsError(
            f"{where}: offline reader is not repository-scoped") from exc
    if not re.fullmatch(r"tools/phase4_[a-z0-9_]+\.py", reader_rel):
        raise MetricsError(
            f"{where}: offline reader is not a tracked Phase-4 tool")
    tracked = subprocess.run(
        ["git", "-C", str(tested_root), "ls-files", "--error-unmatch",
         reader_rel],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if tracked.returncode:
        raise MetricsError(f"{where}: offline reader is untracked")
    command = doc["command"]
    if not isinstance(command, list) or not 2 <= len(command) <= 64 or \
            command[0] not in {"python3", sys.executable} or \
            command[1] != reader_rel or \
            not all(isinstance(item, str) and item and "\x00" not in item
                    and len(item) <= 2048 for item in command):
        raise MetricsError(
            f"{where}: offline command is not closed over the pinned reader")
    execution = doc["execution"]
    if not isinstance(execution, dict):
        raise MetricsError(f"{where}: execution receipt is not an object")
    _exact_keys(
        execution, {"exit_code", "stdout", "stdout_sha256"},
        f"{where}: execution")
    if execution["exit_code"] != 0 or not isinstance(execution["stdout"], str) or \
            not isinstance(execution["stdout_sha256"], str) or not \
            HEX64.fullmatch(execution["stdout_sha256"]) or \
            execution["stdout_sha256"] != hashlib.sha256(
                execution["stdout"].encode("utf-8")).hexdigest():
        raise MetricsError(f"{where}: execution receipt is not a derived success")
    refs: list[tuple[Path, dict[str, Any]]] = []
    input_refs: list[tuple[Path, dict[str, Any]]] = []
    named: dict[str, tuple[str, Path, dict[str, Any]]] = {}
    for name in ("external_inputs", "outputs"):
        if not isinstance(doc[name], list) or not doc[name]:
            raise MetricsError(f"{where}: {name} is not an array")
        for index, ref in enumerate(doc[name]):
            resolved = resolve_ref(
                ref, run_dir, tested_root, f"{where}: {name}[{index}]")
            refs.append(resolved)
            token = f"@{ref['scope']}/{ref['path']}"
            if token in named:
                raise MetricsError(f"{where}: artifact token is duplicated")
            if name == "outputs" and ref["scope"] != "run":
                raise MetricsError(f"{where}: offline outputs must be run-scoped")
            named[token] = (name, resolved[0], ref)
            if name == "external_inputs":
                input_refs.append(resolved)
    command_tokens = {item for item in command[2:] if item.startswith("@")}
    if command_tokens != set(named) | {"@query"}:
        raise MetricsError(
            f"{where}: command must name the canonical query and every retained "
            "input/output token")
    for argument in command[2:]:
        if argument.startswith("@"):
            if argument != "@query" and argument not in named:
                raise MetricsError(f"{where}: command names an unknown artifact")
            continue
        pure = PurePosixPath(argument)
        if pure.is_absolute() or ".." in pure.parts:
            raise MetricsError(f"{where}: command contains an unbounded path")
    manifest, _ = resolve_ref(
        doc["external_preservation_manifest"], run_dir, tested_root,
        f"{where}: preservation manifest")
    external_bytes = _validate_preservation_manifest(
        manifest, refs, f"{where}: external preservation")
    preservation = load_json(manifest)
    preservation_by_hash = {
        entry["sha256"]: entry for entry in preservation["entries"]
    }
    for _path, ref in input_refs:
        entry = preservation_by_hash[ref["sha256"]]
        if entry["media_class"] not in {
                "pristine", "derived_pristine_evidence"}:
            raise MetricsError(
                f"{where}: offline input is not pristine-authority evidence")
    with tempfile.TemporaryDirectory(prefix="phase4-offline-replay-") as tmp:
        scratch = Path(tmp)
        replacements: dict[str, str] = {}
        replacements["@query"] = canonical_bytes(doc["query"]).decode("utf-8")
        output_replays: list[tuple[Path, Path]] = []
        for token, (kind, retained, ref) in named.items():
            if kind == "external_inputs":
                replacements[token] = str(retained)
            else:
                replayed = scratch / "outputs" / ref["path"]
                replayed.parent.mkdir(parents=True, exist_ok=True)
                replacements[token] = str(replayed)
                output_replays.append((retained, replayed))
        replay_command = [
            sys.executable, str(reader_path),
            *(replacements.get(item, item) for item in command[2:]),
        ]
        replay = subprocess.run(
            replay_command, cwd=tested_root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=300,
            env={**os.environ, "ABL_PHASE4_OFFLINE_RECEIPT_REPLAY": "1"},
        )
        if replay.returncode != execution["exit_code"] or \
                replay.stdout != execution["stdout"]:
            raise MetricsError(
                f"{where}: offline command does not reproduce independently")
        for retained, replayed in output_replays:
            if not replayed.is_file() or replayed.is_symlink() or \
                    sha256(replayed) != sha256(retained):
                raise MetricsError(
                    f"{where}: offline output does not reproduce byte-identically")
    return {
        "key": hashlib.sha256(canonical_bytes({
            "reader_sha256": sha256(reader_path),
            "command": command,
            "query": doc["query"],
        })).hexdigest(),
        "external_bytes": sum(path.stat().st_size for path, _ref in input_refs),
        "external_inputs": {
            ref["sha256"]: path.stat().st_size for path, ref in input_refs
        },
        "receipt_sha256": None,
    }


def _receipt_list(refs: Any, schema: str, run_dir: Path, tested_root: Path,
                  where: str, *, before_ledger: dict[str, Any],
                  after_ledger: dict[str, Any],
                  selected_rows: list[str],
                  verifier: dict[str, Any] | None,
                  legacy_index: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(refs, list):
        raise MetricsError(f"{where}: must be an array")
    out: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        path, _ = resolve_ref(ref, run_dir, tested_root, f"{where}[{index}]")
        doc = load_json(path)
        item_where = f"{where}[{index}]"
        if schema == LIVE_SCHEMA:
            item = _validate_live_receipt(
                path, doc, run_dir, tested_root, before_ledger, after_ledger,
                selected_rows, verifier, legacy_index, item_where)
            item["executor_role"] = doc["experiment"]["executor_role"]
        else:
            item = _validate_offline_receipt(
                doc, run_dir, tested_root, item_where)
        item["receipt_sha256"] = sha256(path)
        out.append(item)
    return out


def _admit_iteration_live_receipts(
        receipts: list[dict[str, Any]], seen_live_keys: set[str],
        seen_escalation_ids: set[str]) -> list[str]:
    """Admit one iteration's predeclared live receipt set.

    One escalation may deliberately cover several anchors and the passive
    preludes required by its precise observers.  Reusing that escalation in a
    later iteration remains forbidden, as does repeating a semantic experiment
    under another receipt identity.
    """
    duplicates: list[str] = []
    current_escalations: set[str] = set()
    for receipt in receipts:
        if receipt["executor_role"] != "investigator":
            continue
        key = receipt["semantic_key"]
        if key in seen_live_keys:
            duplicates.append(key)
        seen_live_keys.add(key)
        current_escalations.add(receipt["escalation_id"])
    if duplicates:
        raise MetricsError(
            f"duplicate investigator live experiments: "
            f"{sorted(set(duplicates))}")
    reused = current_escalations & seen_escalation_ids
    if reused:
        raise MetricsError(
            f"investigator escalation was reused: {sorted(reused)}")
    seen_escalation_ids.update(current_escalations)
    # Duplicates are fail-closed above. Return the computed (therefore empty)
    # list so the per-iteration manifest can retain the derived result without
    # depending on a function-local variable.
    return sorted(set(duplicates))


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _generator_outputs(base_commit: str, tested_commit: str) -> set[str]:
    outputs: set[str] = set()
    for commit in (base_commit, tested_commit):
        try:
            raw = _git("show", f"{commit}:config/phase4_inventory.yaml")
            doc = yaml.safe_load(raw)
        except Exception:
            continue
        for entry in doc.get("generators") or []:
            if isinstance(entry, dict):
                for value in entry.get("outputs") or []:
                    if isinstance(value, str) and value.startswith("analysis/"):
                        outputs.add(value)
    return outputs


def classify_commits(base: str, tested: str) -> dict[str, Any]:
    commits = [line for line in _git(
        "rev-list", "--reverse", "--no-merges", f"{base}..{tested}",
    ).splitlines() if line]
    generated = _generator_outputs(base, tested)
    raw: list[dict[str, Any]] = []
    totals = {
        "semantic_source": 0, "generator_guard": 0,
        "joined_hash_gate": 0, "prose_only": 0,
    }
    for commit in commits:
        names: list[str] = []
        diff = _git(
            "diff-tree", "--no-commit-id", "--name-status", "-r", commit,
        )
        for line in diff.splitlines():
            fields = line.split("\t")
            if not fields:
                continue
            status = fields[0]
            if status.startswith("R") and len(fields) == 3:
                names.extend(fields[1:])
            elif len(fields) >= 2:
                names.append(fields[-1])
        names = [PurePosixPath(name).as_posix() for name in names]
        categories: list[str] = []
        if any(_matches(name, SEMANTIC_SOURCE) for name in names):
            categories.append("semantic_source")
            totals["semantic_source"] += 1
        if any(_matches(name, GENERATOR_GUARD) or name in generated for name in names):
            categories.append("generator_guard")
            totals["generator_guard"] += 1
        if names and all(name.endswith(".md") for name in names):
            categories.append("prose_only")
            totals["prose_only"] += 1
        elif names and all(name in JOINED_ONLY for name in names):
            categories.append("joined_hash_gate")
            totals["joined_hash_gate"] += 1
        recognized = all(
            name.endswith(".md") or name in JOINED_ONLY or name in generated or
            _matches(name, SEMANTIC_SOURCE) or _matches(name, GENERATOR_GUARD)
            for name in names
        )
        if not recognized:
            unknown = [
                name for name in names
                if not (name.endswith(".md") or name in JOINED_ONLY or
                        name in generated or _matches(name, SEMANTIC_SOURCE) or
                        _matches(name, GENERATOR_GUARD))
            ]
            raise MetricsError(
                f"{commit}: unclassified changed paths: {unknown}")
        raw.append({"commit": commit, "paths": names, "categories": categories})
    return {"totals": totals, "commits": raw}


def _repo_at_commit(commit: str, current_tested: str) -> tuple[Path, Any]:
    del current_tested
    current_head = _git("rev-parse", "HEAD").strip()
    if commit == current_head:
        return ROOT, None
    temp = tempfile.TemporaryDirectory(prefix="abl-phase4-metrics-")
    checkout = Path(temp.name) / "checkout"
    _git("worktree", "add", "--detach", str(checkout), commit)
    return checkout, temp


def reproduce_debt(path: Path, commit: str, current_tested: str) -> None:
    checkout, temp = _repo_at_commit(commit, current_tested)
    try:
        retained = load_json(path)
        selected = ((retained.get("scheduler") or {}).get(
            "selected_campaigns") or [])
        selection_args: list[str] = []
        if len(selected) == 1 and str(
                selected[0].get("campaign_id") or "").startswith("movie-ready:"):
            selection_args = [
                "--selection-policy", "movie-ready",
                "--selected-batch-id", selected[0]["campaign_id"],
            ]
            for row_id in selected[0].get("rows") or []:
                selection_args.extend(["--selected-row", row_id])
        with tempfile.TemporaryDirectory(prefix="abl-phase4-debt-") as scratch:
            generated = Path(scratch) / "debt.json"
            command = [
                sys.executable, "tools/phase4_closure_debt.py",
                "--snapshot", str(generated), *selection_args,
            ]
            run = subprocess.run(
                command, cwd=checkout, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            if run.returncode and selection_args:
                run = subprocess.run(
                    [*command, "--selection-continuation"],
                    cwd=checkout, text=True, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT)
            if run.returncode:
                raise MetricsError(
                    f"debt regeneration failed at {commit}: {run.stdout[-2000:]}")
            if generated.read_bytes() != path.read_bytes():
                raise MetricsError(
                    f"debt snapshot does not reproduce byte-identically at {commit}")
    finally:
        if temp is not None:
            checkout = Path(temp.name) / "checkout"
            _git("worktree", "remove", "--force", str(checkout))
            temp.cleanup()


def _derive_knowledge_join(
        tested_root: Path, campaign_id: str,
        transitions: dict[str, list[Any]], after: dict[str, Any],
        knowledge_report: dict[str, Any], vault_report: dict[str, Any]) -> dict[str, Any]:
    if not transitions["rows"] and not transitions["dimensions"]:
        return {"complete": True, "authoritative_paths": [], "claims": []}
    if knowledge_report.get("joined") is not True or \
            vault_report.get("complete") is not True:
        raise MetricsError("promoted evidence lacks clean knowledge/vault reports")
    inventory_path = tested_root / "analysis" / "phase4_campaign_inventory.json"
    if not inventory_path.is_file():
        raise MetricsError("promoted evidence lacks the generator inventory")
    inventory = load_json(inventory_path)
    generators = inventory.get("generators")
    if not isinstance(generators, dict):
        raise MetricsError("campaign inventory generator map is malformed")
    output_owners: dict[str, set[str]] = {}
    for generator, declaration in generators.items():
        if not isinstance(generator, str) or not isinstance(declaration, dict) or \
                declaration.get("tracked") is not True:
            continue
        generator_path = tested_root / generator
        if not generator_path.is_file() or declaration.get("sha256") != \
                sha256(generator_path):
            raise MetricsError(f"generator inventory is stale for {generator}")
        for output in declaration.get("outputs") or []:
            if isinstance(output, dict) and isinstance(output.get("path"), str):
                output_owners.setdefault(output["path"], set()).add(generator)
    declared_tests = set(inventory.get("tests") or ())
    registry_path = tested_root / "config" / "phase4_campaigns.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    campaigns = {
        item.get("id"): item
        for item in registry.get("child_campaigns") or []
        if isinstance(item, dict)
    }
    campaign = campaigns.get(campaign_id)
    if campaign is None:
        raise MetricsError("promoted campaign is absent from campaign registry")
    selected_rows = set(campaign.get("rows") or [])
    transition_rows = {
        item[0] for kind in ("rows", "dimensions", "demotions")
        for item in transitions[kind]
    }
    if not selected_rows or not transition_rows <= selected_rows:
        raise MetricsError("knowledge join includes an out-of-campaign transition")
    after_rows = _debt_rows(after)
    required_dimensions = {
        transition[1] for transition in transitions["dimensions"]
    }
    if transitions["rows"]:
        for row_id, _, _ in transitions["rows"]:
            row = after_rows[row_id]
            required_dimensions.update(
                name for name, value in row["dimensions"].items()
                if value.get("state") == "met")
    authoritative: set[str] = set()
    claims_out: list[dict[str, Any]] = []
    promotion_guard_nodes: set[str] = set()
    promotion_guards_by_artifact: dict[str, set[str]] = {}
    claims = campaign.get("dimension_claims")
    if not isinstance(claims, dict):
        raise MetricsError("promoted campaign lacks dimension claims")
    for dimension in sorted(required_dimensions):
        claim = claims.get(dimension)
        if not isinstance(claim, dict) or claim.get("claim") != "met":
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks a met machine claim")
        evidence = claim.get("evidence")
        paths = claim.get("authoritative_paths")
        bindings = claim.get("knowledge_bindings")
        if not isinstance(evidence, list) or not evidence or \
                not isinstance(paths, list) or not paths:
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks assertions/paths")
        if not isinstance(bindings, list) or not bindings:
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks structured knowledge "
                "bindings")
        if not isinstance(claim.get("residuals"), list):
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks residual handling")
        for residual in claim["residuals"]:
            if not isinstance(residual, dict) or \
                    residual.get("intersects_dimension") is not False:
                raise MetricsError(
                    f"promoted {campaign_id}/{dimension} has intersecting residual")
        resolved_paths: list[str] = []
        for rel in paths:
            if not isinstance(rel, str):
                raise MetricsError("authoritative path is not a string")
            pure = PurePosixPath(rel)
            if pure.is_absolute() or ".." in pure.parts or str(pure) != rel:
                raise MetricsError(f"unsafe authoritative path: {rel!r}")
            path = tested_root.joinpath(*pure.parts)
            if not path.is_file():
                raise MetricsError(f"authoritative path is absent: {rel}")
            tracked = subprocess.run(
                ["git", "-C", str(tested_root), "ls-files", "--error-unmatch", rel],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if tracked.returncode:
                raise MetricsError(f"authoritative path is untracked: {rel}")
            authoritative.add(rel)
            resolved_paths.append(rel)
        machine_paths = [
            rel for rel in resolved_paths
            if rel.startswith((
                "analysis/", "config/", "src/main/", "src_re/", "symbols/",
                "asm/", "tools/", "tests/",
            )) and not rel.endswith(".md")
        ]
        if not machine_paths:
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks a machine authority")
        if not any(rel.startswith(("src/main/", "src_re/", "symbols/", "asm/",
                                   "config/")) for rel in resolved_paths):
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks semantic source/schema")
        guard_paths = {
            rel for rel in resolved_paths
            if rel.startswith("tests/") and rel in declared_tests
        }
        if not guard_paths:
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} lacks an inventoried guard")
        binding_by_artifact: dict[str, dict[str, Any]] = {}
        for binding_index, binding in enumerate(bindings):
            binding_where = (
                f"{campaign_id}/{dimension} knowledge_bindings[{binding_index}]")
            if not isinstance(binding, dict):
                raise MetricsError(f"{binding_where}: binding is not an object")
            _exact_keys(binding, {
                "artifact", "producer", "semantic_sources", "guard_nodes",
            }, binding_where)
            artifact = binding["artifact"]
            if not isinstance(artifact, str) or artifact in binding_by_artifact:
                raise MetricsError(
                    f"{binding_where}: artifact is invalid or duplicated")
            producer = binding["producer"]
            if producer not in output_owners.get(artifact, set()) or \
                    producer not in resolved_paths:
                raise MetricsError(
                    f"{binding_where}: producer is not the inventoried output owner")
            sources = binding["semantic_sources"]
            if not isinstance(sources, list) or not sources:
                raise MetricsError(f"{binding_where}: semantic sources are absent")
            for source_index, source in enumerate(sources):
                source_where = f"{binding_where}.semantic_sources[{source_index}]"
                if not isinstance(source, dict):
                    raise MetricsError(f"{source_where}: source is not an object")
                _exact_keys(
                    source, {"path", "sha256", "artifact_json_path"},
                    source_where)
                source_path = source["path"]
                if source_path not in resolved_paths or not isinstance(
                        source_path, str) or not source_path.startswith((
                            "src/main/", "src_re/", "symbols/", "asm/", "config/",
                        )):
                    raise MetricsError(
                        f"{source_where}: source is not a declared semantic authority")
                if source["sha256"] != sha256(tested_root / source_path):
                    raise MetricsError(f"{source_where}: semantic source pin is stale")
                if not isinstance(source["artifact_json_path"], str) or not \
                        source["artifact_json_path"]:
                    raise MetricsError(
                        f"{source_where}: artifact provenance path is absent")
                provenance: Any = load_json(tested_root / artifact)
                for part in source["artifact_json_path"].split("."):
                    if isinstance(provenance, list) and part.isdigit() and \
                            int(part) < len(provenance):
                        provenance = provenance[int(part)]
                    elif isinstance(provenance, dict) and part in provenance:
                        provenance = provenance[part]
                    else:
                        raise MetricsError(
                            f"{source_where}: artifact provenance path is absent")
                if provenance != source["sha256"]:
                    raise MetricsError(
                        f"{source_where}: artifact does not pin the semantic source")
            nodes = binding["guard_nodes"]
            if not isinstance(nodes, list) or not nodes or not all(
                    isinstance(node, str) and "::" in node for node in nodes):
                raise MetricsError(f"{binding_where}: exact guard nodes are absent")
            for node in nodes:
                test_path = node.split("::", 1)[0]
                if test_path not in guard_paths:
                    raise MetricsError(
                        f"{binding_where}: guard node is not an authoritative "
                        "inventoried test")
                promotion_guard_nodes.add(node)
                promotion_guards_by_artifact.setdefault(artifact, set()).add(node)
            binding_by_artifact[artifact] = binding
        asserted_artifacts = {
            assertion.get("artifact") for assertion in evidence
            if isinstance(assertion, dict)
        }
        if set(binding_by_artifact) != asserted_artifacts:
            raise MetricsError(
                f"promoted {campaign_id}/{dimension} knowledge bindings do not "
                "exactly cover asserted artifacts")
        for index, assertion in enumerate(evidence):
            where = f"{campaign_id}/{dimension} evidence[{index}]"
            if not isinstance(assertion, dict):
                raise MetricsError(f"{where}: assertion is not machine-readable")
            _exact_keys(assertion, {
                "artifact", "sha256", "json_path", "op", "expected",
            }, where)
            artifact = assertion["artifact"]
            if artifact not in resolved_paths or not artifact.startswith(
                    ("analysis/", "config/")):
                raise MetricsError(f"{where}: artifact is not authoritative")
            artifact_path = tested_root / artifact
            owners = output_owners.get(artifact, set())
            if not owners or not (owners & set(resolved_paths)):
                raise MetricsError(
                    f"{where}: artifact lacks a pinned generator in authoritative paths")
            if not isinstance(assertion["sha256"], str) or \
                    assertion["sha256"] != sha256(artifact_path):
                raise MetricsError(f"{where}: artifact pin is stale")
            if assertion["op"] not in {"eq", "len_eq"} or not isinstance(
                    assertion["json_path"], str) or not assertion["json_path"]:
                raise MetricsError(f"{where}: assertion operator/path is invalid")
            value: Any = load_json(artifact_path)
            for part in assertion["json_path"].split("."):
                if isinstance(value, list) and part.isdigit():
                    position = int(part)
                    if position >= len(value):
                        raise MetricsError(f"{where}: JSON index is absent")
                    value = value[position]
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    raise MetricsError(f"{where}: JSON path is absent")
            observed = len(value) if assertion["op"] == "len_eq" and \
                isinstance(value, (list, dict, str)) else value
            if observed != assertion["expected"]:
                raise MetricsError(f"{where}: assertion does not reproduce")
        claims_out.append({
            "dimension": dimension,
            "assertion_count": len(evidence),
            "authoritative_paths": resolved_paths,
            "knowledge_binding_count": len(bindings),
        })
    guard_validation: dict[str, Any] | None = None
    if promotion_guard_nodes:
        nodes = sorted(promotion_guard_nodes)
        collect_command = [
            sys.executable, "-m", "pytest", "--collect-only", "-q", *nodes,
        ]
        collect = subprocess.run(
            collect_command, cwd=tested_root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if collect.returncode or not re.search(
                r"\b\d+ tests? collected\b", collect.stdout):
            raise MetricsError(
                "promoted evidence guard nodes do not collect exactly")
        run_command = [sys.executable, "-m", "pytest", "-q", *nodes]
        guarded = subprocess.run(
            run_command, cwd=tested_root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if guarded.returncode or not re.search(
                r"\b\d+ passed\b", guarded.stdout):
            raise MetricsError("promoted evidence guard nodes do not pass")
        falsifier_hashes: dict[str, str] = {}
        status_before = subprocess.run(
            ["git", "-C", str(tested_root), "status", "--porcelain=v1"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if status_before.returncode:
            raise MetricsError("cannot establish promotion-guard checkout status")
        for artifact, artifact_nodes in sorted(
                promotion_guards_by_artifact.items()):
            artifact_path = tested_root / artifact
            original = artifact_path.read_bytes()
            try:
                artifact_path.write_bytes(original + b" ")
                falsifier = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q",
                     *sorted(artifact_nodes)],
                    cwd=tested_root, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    env={**os.environ,
                         "ABL_PHASE4_PROMOTION_GUARD_FALSIFICATION": artifact},
                )
            finally:
                artifact_path.write_bytes(original)
            if falsifier.returncode == 0:
                raise MetricsError(
                    f"promoted guard does not reject artifact drift: {artifact}")
            falsifier_hashes[artifact] = hashlib.sha256(
                falsifier.stdout.encode("utf-8")).hexdigest()
        status_after = subprocess.run(
            ["git", "-C", str(tested_root), "status", "--porcelain=v1"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if status_after.returncode or status_after.stdout != status_before.stdout:
            raise MetricsError(
                "promotion-guard falsification did not restore checkout state")
        guard_validation = {
            "nodes": nodes,
            "collect_output_sha256": hashlib.sha256(
                collect.stdout.encode("utf-8")).hexdigest(),
            "run_output_sha256": hashlib.sha256(
                guarded.stdout.encode("utf-8")).hexdigest(),
            "artifact_drift_falsifier_output_sha256": falsifier_hashes,
        }
    notes = set(authoritative)
    campaign_note = campaign.get("note")
    if isinstance(campaign_note, str):
        notes.add(campaign_note)
    if not any(path.startswith("ObsidianVault/Canon/") for path in notes):
        raise MetricsError("promoted campaign lacks a linked Canon path")
    if not any(path.startswith("ObsidianVault/Experiments/") for path in notes):
        raise MetricsError("promoted campaign lacks a linked Experiment path")
    mods_disposition = campaign.get("mods_disposition")
    has_mods_note = any(path.startswith("ObsidianVault/Mods/") for path in notes)
    if not has_mods_note and mods_disposition != "not_applicable":
        raise MetricsError(
            "promoted campaign lacks Mods path or mods_disposition:not_applicable")
    return {
        "complete": True,
        "authoritative_paths": sorted(authoritative),
        "claims": claims_out,
        "guard_validation": guard_validation,
        "mods_disposition": mods_disposition,
        "has_mods_note": has_mods_note,
    }


def _decision_artifact(
        value: str, run_dir: Path, tested_root: Path, where: str) -> Path:
    match = re.fullmatch(r"(repo|run):([^@]+)@([0-9a-f]{64})", value)
    if match is None:
        raise MetricsError(f"{where}: must be a closed scope:path@sha256 reference")
    path, _ = resolve_ref(
        {"scope": match.group(1), "path": match.group(2),
         "sha256": match.group(3)},
        run_dir, tested_root, where)
    if path.stat().st_size < 1:
        raise MetricsError(f"{where}: referenced evidence is empty")
    return path


def _validate_verifier_decision(
        doc: dict[str, Any], tested_commit: str, where: str,
        run_dir: Path | None = None,
        tested_root: Path | None = None) -> dict[str, Any]:
    _exact_keys(doc, {
        "phase", "status", "summary", "gaps", "gap_codes",
        "falsifier_results", "verified_live_receipt_sha256s",
        "method_exceptions", "evidence", "validation",
        "required_input", "candidate_commit",
    }, where)
    if doc["phase"] != 4 or doc["status"] not in {
            "closed", "open_autonomous", "blocked_external"}:
        raise MetricsError(f"{where}: verifier phase/status is invalid")
    for key in (
            "gaps", "gap_codes", "verified_live_receipt_sha256s",
            "evidence", "validation"):
        _closed_strings(doc[key], f"{where}: {key}")
    if len(doc["gaps"]) != len(doc["gap_codes"]) or not all(
            re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", code)
            for code in doc["gap_codes"]):
        raise MetricsError(f"{where}: stable gap-code mapping is invalid")
    falsifiers = doc["falsifier_results"]
    if not isinstance(falsifiers, list):
        raise MetricsError(f"{where}: falsifier results are not an array")
    falsifier_ids: set[str] = set()
    for index, item in enumerate(falsifiers):
        if not isinstance(item, dict):
            raise MetricsError(f"{where}: falsifier result is not an object")
        _exact_keys(item, {"id", "outcome", "evidence"},
                    f"{where}: falsifier result")
        if not isinstance(item["id"], str) or not item["id"] or \
                item["id"] in falsifier_ids or \
                item["outcome"] not in {"survived", "falsified", "not_run"} or \
                not isinstance(item["evidence"], str) or not item["evidence"].strip():
            raise MetricsError(f"{where}: falsifier result is invalid")
        if run_dir is not None and tested_root is not None:
            artifact = _decision_artifact(
                item["evidence"], run_dir, tested_root,
                f"{where}: falsifier[{index}].evidence")
            receipt = load_json(artifact)
            _exact_keys(receipt, {
                "schema", "id", "candidate_commit", "command", "exit_code",
                "outcome", "output", "output_sha256",
            }, f"{where}: falsifier[{index}] receipt")
            if receipt["schema"] != "abl-phase4-verifier-falsifier/1" or \
                    receipt["id"] != item["id"] or \
                    receipt["candidate_commit"] != tested_commit or \
                    receipt["outcome"] != item["outcome"] or \
                    not isinstance(receipt["command"], list) or \
                    not receipt["command"] or \
                    not all(isinstance(value, str) and value
                            for value in receipt["command"]) or \
                    not isinstance(receipt["exit_code"], int) or \
                    isinstance(receipt["exit_code"], bool) or \
                    not isinstance(receipt["output"], str) or \
                    (receipt["outcome"] == "survived" and
                     (receipt["exit_code"] != 0 or not receipt["output"].strip())) or \
                    receipt["output_sha256"] != hashlib.sha256(
                        receipt["output"].encode("utf-8")).hexdigest():
                raise MetricsError(
                    f"{where}: falsifier[{index}] receipt is not derived")
        falsifier_ids.add(item["id"])
    for digest in doc["verified_live_receipt_sha256s"]:
        if not HEX64.fullmatch(digest):
            raise MetricsError(f"{where}: invalid verified live-receipt hash")
    if not isinstance(doc["method_exceptions"], list):
        raise MetricsError(f"{where}: method exceptions are not an array")
    for item in doc["method_exceptions"]:
        if not isinstance(item, dict):
            raise MetricsError(f"{where}: method exception is not an object")
        _exact_keys(item, {
            "code", "live_receipt_sha256", "boundary_mismatch",
        }, f"{where}: method exception")
        if item["code"] != "PRECISE_WINDOW_UNAVOIDABLE" or not \
                isinstance(item["live_receipt_sha256"], str) or not \
                HEX64.fullmatch(item["live_receipt_sha256"]) or not \
                isinstance(item["boundary_mismatch"], dict) or not \
                item["boundary_mismatch"]:
            raise MetricsError(f"{where}: method exception is invalid")
    for key in ("summary", "required_input", "candidate_commit"):
        if not isinstance(doc[key], str):
            raise MetricsError(f"{where}: {key} is not a string")
    if not doc["summary"].strip():
        raise MetricsError(f"{where}: verifier summary is empty")
    if doc["candidate_commit"] != tested_commit:
        raise MetricsError(f"{where}: verifier decision commit mismatch")
    if doc["status"] == "closed" and (
            doc["gaps"] or doc["required_input"]):
        raise MetricsError(f"{where}: closed verifier carries gaps/input")
    if run_dir is not None and tested_root is not None:
        for key in ("evidence", "validation"):
            for index, value in enumerate(doc[key]):
                _decision_artifact(
                    value, run_dir, tested_root,
                    f"{where}: {key}[{index}]")
    if not doc["gaps"]:
        if run_dir is None or tested_root is None:
            raise MetricsError(
                f"{where}: gap-free verifier evidence cannot be checked without roots")
        if doc["status"] not in {"closed", "open_autonomous"} or \
                doc["required_input"] or not doc["evidence"] or \
                not doc["validation"] or len(falsifiers) < 2 or \
                any(item["outcome"] != "survived" for item in falsifiers):
            raise MetricsError(
                f"{where}: gap-free verifier lacks independent evidence/validation")
    return doc


def _validate_legacy_index(path: Path) -> dict[str, Any]:
    doc = load_json(path)
    _exact_keys(doc, {
        "schema", "generated", "source", "entries", "counts",
        "complete", "errors",
    }, str(path))
    if doc["schema"] != LEGACY_SCHEMA or \
            doc["complete"] is not True or \
            _closed_strings(doc["errors"], f"{path}: errors"):
        raise MetricsError("legacy live index is not closed")
    source = doc["source"]
    if not isinstance(source, dict):
        raise MetricsError("legacy live index source is malformed")
    _exact_keys(
        source, {"path", "baseline_sha256", "projection", "legacy_ids"},
        "legacy index source")
    source_path = ROOT / source["path"]
    if not source_path.is_file() or not isinstance(
            source["baseline_sha256"], str) or not HEX64.fullmatch(
                source["baseline_sha256"]):
        raise MetricsError("legacy live index source baseline is invalid")
    if source["projection"] != LEGACY_SOURCE_PROJECTION:
        raise MetricsError("legacy live index source projection is invalid")
    if not isinstance(source["legacy_ids"], list) or not all(
            isinstance(item, str) for item in source["legacy_ids"]):
        raise MetricsError("legacy live index ID cutoff is invalid")
    current_source = load_json(source_path)
    source_entries = {
        entry.get("id"): entry
        for entry in current_source.get("entries") or []
        if isinstance(entry, dict)
    }
    entries = doc["entries"]
    if not isinstance(entries, list) or not entries:
        raise MetricsError("legacy live index is empty")
    ids: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise MetricsError("legacy live index entry is not an object")
        _exact_keys(entry, {
            "escalation_id", "target_row", "state", "normalization",
            "media_sha256", "movie_sha256", "state_sha256", "domain",
            "window", "observer_methods", "external_receipt_sha256s",
            "source_entry_sha256",
        }, f"legacy entry {index}")
        if entry["escalation_id"] in ids or not isinstance(
                entry["escalation_id"], str):
            raise MetricsError("legacy live index IDs are invalid/duplicate")
        ids.add(entry["escalation_id"])
        raw = source_entries.get(entry["escalation_id"])
        if raw is None or hashlib.sha256(canonical_bytes(
                _legacy_source_projection(raw))).hexdigest() != \
                entry["source_entry_sha256"]:
            raise MetricsError(
                f"legacy entry {index} no longer matches its retained source entry")
        if entry["normalization"] not in {"normalized", "conservative_deny"}:
            raise MetricsError("legacy live normalization is invalid")
        if not isinstance(entry["observer_methods"], list) or not all(
                isinstance(method, str) and method
                for method in entry["observer_methods"]) or \
                not isinstance(entry["external_receipt_sha256s"], list):
            raise MetricsError("legacy live observer normalization is invalid")
        if entry["normalization"] == "normalized":
            try:
                import phase4_method_legacy_live_index as legacy_generator
            except ImportError as exc:
                raise MetricsError(
                    "legacy live generator is unavailable") from exc
            derived = legacy_generator.normalized_observer_basis(raw)
            expected_normalized = {
                "normalization": entry["normalization"],
                "domain": entry["domain"],
                "observer_methods": entry["observer_methods"],
                "external_receipt_sha256s":
                    entry["external_receipt_sha256s"],
            }
            if derived != expected_normalized or entry["window"] is not None:
                raise MetricsError(
                    "legacy live normalized observer basis is not derived")
        elif entry["domain"] is not None or entry["window"] is not None or \
                entry["observer_methods"] or \
                entry["external_receipt_sha256s"]:
            raise MetricsError(
                "legacy conservative deny contains authored normalization")
        for key in (
            "media_sha256", "movie_sha256", "state_sha256",
            "source_entry_sha256",
        ):
            value = entry[key]
            if value is not None and not (
                    isinstance(value, str) and HEX64.fullmatch(value)):
                raise MetricsError(f"legacy entry {index} has invalid {key}")
        if any(
                not isinstance(value, str) or not HEX64.fullmatch(value)
                for value in entry["external_receipt_sha256s"]):
            raise MetricsError(
                f"legacy entry {index} has invalid external receipt identity")
    counts = doc["counts"]
    expected = {
        "entries": len(entries),
        "normalized": sum(
            item["normalization"] == "normalized" for item in entries),
        "conservative_deny": sum(
            item["normalization"] == "conservative_deny" for item in entries),
    }
    if counts != expected:
        raise MetricsError("legacy live index counts are authored/stale")
    if source["legacy_ids"] != [item["escalation_id"] for item in entries]:
        raise MetricsError("legacy live index cutoff/order disagrees with entries")
    return doc


def _legacy_source_projection(raw: dict[str, Any]) -> dict[str, Any]:
    """Independently reproduce the closed legacy-generator projection."""
    return {
        key: value for key, value in raw.items()
        if key != "derived_post_run_audit"
    }


def validate_manifest(path: Path, run_dir: Path,
                      previous: dict[str, Any] | None,
                      seen_live_keys: set[str],
                      seen_escalation_ids: set[str],
                      reporter_sha256: str,
                      legacy_index: dict[str, Any]) -> dict[str, Any]:
    doc = load_json(path)
    _exact_keys(doc, MANIFEST_KEYS, str(path))
    if doc.get("schema") != SCHEMA:
        raise MetricsError(f"{path}: method-metrics schema mismatch")
    iteration = doc.get("iteration")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
        raise MetricsError(f"{path}: invalid iteration")
    if previous is not None and iteration != previous["iteration"] + 1:
        raise MetricsError("method iteration numbers are not contiguous")
    if not isinstance(doc.get("campaign_id"), str) or not doc["campaign_id"]:
        raise MetricsError("manifest campaign ID is invalid")
    if not isinstance(doc.get("row_ids"), list) or not doc["row_ids"] or \
            len(doc["row_ids"]) > 3 or \
            not all(isinstance(row, str) for row in doc["row_ids"]):
        raise MetricsError("manifest row set is invalid")
    for key in ("base_commit", "tested_commit"):
        _commit_exists(doc[key])
    if previous is not None and doc["base_commit"] != previous["tested_commit"]:
        raise MetricsError("base/tested commit chain is broken")

    tested_root, cleanup = _repo_at_commit(doc["tested_commit"], doc["tested_commit"])
    try:
        validator_path, _ = resolve_ref(
            doc["validator"], run_dir, tested_root, "validator")
        if validator_path.relative_to(tested_root) != Path(
                "tools/phase4_method_metrics.py"):
            raise MetricsError("manifest pins the wrong validator path")
        evidence = doc.get("evidence")
        if not isinstance(evidence, dict):
            raise MetricsError("manifest evidence is not an object")
        _exact_keys(evidence, EVIDENCE_KEYS, "manifest evidence")
        before_path, before_ref = resolve_ref(
            evidence["debt_before"], run_dir, tested_root, "debt_before")
        after_path, after_ref = resolve_ref(
            evidence["debt_after"], run_dir, tested_root, "debt_after")
        before, after = load_json(before_path), load_json(after_path)
        campaign_id, row_ids = _selected(before)
        if campaign_id != doc["campaign_id"] or row_ids != doc["row_ids"]:
            raise MetricsError("manifest target differs from debt scheduler")
        if previous is not None and before_ref["sha256"] != \
                previous["debt_after_sha256"]:
            previous_after_path, _ = resolve_ref(
                previous["evidence"]["debt_after"], run_dir, tested_root,
                "previous debt_after")
            previous_progress_path, _ = resolve_ref(
                previous["evidence"]["progress_receipt"], run_dir, tested_root,
                "previous progress_receipt")
            if not _movie_ready_scheduler_handoff(
                    load_json(previous_after_path), before,
                    load_json(previous_progress_path)):
                raise MetricsError("debt hash chain is broken")
        reproduce_debt(before_path, doc["base_commit"], doc["tested_commit"])
        reproduce_debt(after_path, doc["tested_commit"], doc["tested_commit"])
        transitions = _transitions(before, after)
        changed_rows = {
            item[0] for kind in ("rows", "dimensions", "demotions")
            for item in transitions[kind]
        }
        outside_scope = changed_rows - set(row_ids)
        if outside_scope:
            raise MetricsError(
                f"debt transitions escape selected campaign rows: "
                f"{sorted(outside_scope)}")
        progress_path, _ = resolve_ref(
            evidence["progress_receipt"], run_dir, tested_root,
            "progress_receipt")
        _progress(
            progress_path, iteration, campaign_id, row_ids, transitions,
            before_ref["sha256"], after_ref["sha256"])
        before_ledger_path, _ = resolve_ref(
            evidence["escalation_ledger_before"], run_dir, tested_root,
            "escalation_ledger_before")
        after_ledger_path, _ = resolve_ref(
            evidence["escalation_ledger_after"], run_dir, tested_root,
            "escalation_ledger_after")
        before_ledger = load_json(before_ledger_path)
        after_ledger = load_json(after_ledger_path)
        for ledger in (before_ledger, after_ledger):
            if ledger.get("schema") != "abl-phase4-live-escalations/1":
                raise MetricsError("escalation ledger schema mismatch")
        verifier: dict[str, Any] | None = None
        verifier_path = None
        if evidence["verifier_decision"] is not None:
            verifier_path, _ = resolve_ref(
                evidence["verifier_decision"], run_dir, tested_root,
                "verifier_decision")
            verifier = _validate_verifier_decision(
                load_json(verifier_path), doc["tested_commit"],
                "verifier_decision", run_dir, tested_root)
        offline = _receipt_list(
            evidence["offline_query_receipts"],
            OFFLINE_SCHEMA, run_dir, tested_root,
            "offline_query_receipts", before_ledger=before_ledger,
            after_ledger=after_ledger,
            selected_rows=row_ids, verifier=verifier,
            legacy_index=legacy_index)
        live = _receipt_list(
            evidence["live_run_receipts"],
            LIVE_SCHEMA, run_dir, tested_root,
            "live_run_receipts", before_ledger=before_ledger,
            after_ledger=after_ledger,
            selected_rows=row_ids, verifier=verifier,
            legacy_index=legacy_index)
        live_by_hash = {item["receipt_sha256"]: item for item in live}
        for receipt in live:
            if not receipt["precise"]:
                continue
            prelude = live_by_hash.get(receipt["prelude_receipt_sha256"])
            if prelude is None or prelude["precise"] or \
                    prelude["key"] != receipt["prelude_key"]:
                raise MetricsError(
                    "precise live receipt's passive prelude is not independently "
                    "retained and fully validated in this iteration")
        duplicates = _admit_iteration_live_receipts(
            live, seen_live_keys, seen_escalation_ids)
        events_path, _ = resolve_ref(
            evidence["controller_events"], run_dir, tested_root,
            "controller_events")
        events, started, finished = _event_document(
            events_path, iteration, doc["base_commit"], doc["tested_commit"])
        if doc["started_at"] != started or doc["finished_at"] != finished:
            raise MetricsError("manifest timestamps differ from controller events")
        started_dt = _parse_time(started, "started_at")
        finished_dt = _parse_time(finished, "finished_at")
        if finished_dt < started_dt:
            raise MetricsError("iteration finish precedes start")
        command_path, _ = resolve_ref(
            evidence["command_log"], run_dir, tested_root, "command_log")
        validation_path, _ = resolve_ref(
            evidence["validation_report"], run_dir, tested_root,
            "validation_report")
        knowledge_path, _ = resolve_ref(
            evidence["knowledge_report"], run_dir, tested_root,
            "knowledge_report")
        vault_path, _ = resolve_ref(
            evidence["vault_report"], run_dir, tested_root, "vault_report")
        clean_path, _ = resolve_ref(
            evidence["clean_checkout_report"], run_dir, tested_root,
            "clean_checkout_report")
        rerun_cache: dict[tuple[str, ...], tuple[int, str]] = {}
        command_report = _closed_report(
            command_path, "abl-phase4-command-log/1", doc["tested_commit"],
            run_dir, tested_root, rerun_cache, reporter_sha256)
        validation_report = _closed_report(
            validation_path, "abl-phase4-validation-report/1",
            doc["tested_commit"], run_dir, tested_root, rerun_cache,
            reporter_sha256)
        knowledge = _closed_report(
            knowledge_path, "abl-phase4-knowledge-report/1",
            doc["tested_commit"], run_dir, tested_root, rerun_cache,
            reporter_sha256)
        vault = _closed_report(
            vault_path, "abl-phase4-vault-report/1", doc["tested_commit"],
            run_dir, tested_root, rerun_cache, reporter_sha256)
        clean = _closed_report(
            clean_path, "abl-phase4-clean-checkout-report/1",
            doc["tested_commit"], run_dir, tested_root, rerun_cache,
            reporter_sha256)
        for report in (
                command_report, validation_report, knowledge, vault, clean):
            generated = _parse_time(
                report["generated_at"], "iteration report generated_at")
            if generated < started_dt or generated > finished_dt:
                raise MetricsError(
                    "iteration report generation is outside controller event bounds")
        if clean.get("status_before") or clean.get("status_after"):
            raise MetricsError("clean-checkout report records a dirty tree")
        verifier_gap_free = bool(
            verifier is not None and verifier["gaps"] == [] and
            verifier["required_input"] == "" and
            verifier["falsifier_results"] and
            all(item["outcome"] == "survived"
                for item in verifier["falsifier_results"]))
        has_transition = bool(transitions["rows"] or transitions["dimensions"])
        if has_transition and not verifier_gap_free:
            raise MetricsError(
                "debt promotion lacks a gap-free fresh verifier; promoted state "
                "cannot enter the next chain")
        knowledge_join = _derive_knowledge_join(
            tested_root, campaign_id, transitions, after, knowledge, vault)
        accepted = has_transition
        classes = classify_commits(doc["base_commit"], doc["tested_commit"])
        terminal = events[-1]["type"]
        infrastructure = terminal == "infrastructure_failure"
        if infrastructure:
            if doc["base_commit"] != doc["tested_commit"] or \
                    before_ref["sha256"] != after_ref["sha256"] or \
                    verifier_path is not None:
                raise MetricsError("infrastructure terminal changed semantic evidence")
            iteration_class = "infrastructure_failure"
        elif not accepted and classes["commits"] and all(
                set(row["categories"]) <= {"joined_hash_gate", "prose_only"}
                for row in classes["commits"]):
            iteration_class = "repair_only"
        else:
            iteration_class = "semantic"
        return {
            "iteration": iteration,
            "campaign_id": campaign_id,
            "row_ids": row_ids,
            "base_commit": doc["base_commit"],
            "tested_commit": doc["tested_commit"],
            "manifest_sha256": sha256(path),
            "debt_after_sha256": after_ref["sha256"],
            "transitions": transitions,
            "transition_ids": (
                [f"row:{item[0]}" for item in transitions["rows"]] +
                [f"dimension:{item[0]}/{item[1]}"
                 for item in transitions["dimensions"]]
            ),
            "terminal_met_ids": sorted(
                [f"row:{row_id}" for row_id, row in _debt_rows(after).items()
                 if row.get("completion_state") in {
                     "campaign_complete", "reviewed_absent"}] +
                [f"dimension:{row_id}/{dimension}"
                 for row_id, row in _debt_rows(after).items()
                 for dimension, value in (row.get("dimensions") or {}).items()
                 if value.get("state") == "met"]
            ),
            "accepted": accepted,
            "verifier_gap_free": verifier_gap_free,
            "verifier_gap_codes": (
                [] if verifier is None else verifier["gap_codes"]),
            "falsifier_results": (
                [] if verifier is None else verifier["falsifier_results"]),
            "wall_seconds": (finished_dt - started_dt).total_seconds(),
            "offline_query_count": len({item["key"] for item in offline}),
            "external_bytes_reused": sum({
                digest: size
                for item in offline
                for digest, size in item["external_inputs"].items()
            }.values()),
            "live_run_count": len(live),
            "duckstation_launches": sum(
                item["counters"]["launches"] for item in live),
            "atomic_jobs": sum(
                item["counters"]["atomic_jobs"] for item in live),
            "replay_frames": sum(
                item["counters"]["replay_frames"] for item in live),
            "observer_frames": sum(
                item["counters"]["observer_frames"] for item in live),
            "instructions": sum(
                item["counters"]["instructions"] for item in live),
            "duplicate_experiment_keys": duplicates,
            "experiment_keys": [item["key"] for item in live],
            "source_receipt_hashes": [
                item["receipt_sha256"] for item in offline + live],
            "knowledge_join": knowledge_join,
            "commit_classification": classes,
            "iteration_class": iteration_class,
        }
    finally:
        if cleanup is not None:
            cleanup.cleanup()


def validate_trial(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    trial_path = run_dir / "method-metrics" / "trial-root.json"
    trial = load_json(trial_path)
    _exact_keys(
        trial,
        {"schema", "base_commit", "debt_before_sha256",
         "validator_sha256", "reporter_sha256", "legacy_index", "created_at"},
        str(trial_path),
    )
    if trial.get("schema") != TRIAL_SCHEMA:
        raise MetricsError("trial-root schema mismatch")
    _commit_exists(trial["base_commit"])
    for key in ("debt_before_sha256", "validator_sha256", "reporter_sha256"):
        if not isinstance(trial.get(key), str) or not HEX64.fullmatch(trial[key]):
            raise MetricsError(f"trial root {key} is invalid")
    if sha256(Path(__file__).resolve()) != trial["validator_sha256"]:
        raise MetricsError("current validator differs from trial-root pin")
    reporter = ROOT / "tools" / "phase4_method_reports.py"
    if not reporter.is_file() or sha256(reporter) != trial["reporter_sha256"]:
        raise MetricsError("current report producer differs from trial-root pin")
    _parse_time(trial["created_at"], "trial-root created_at")
    legacy_path, _ = resolve_ref(
        trial["legacy_index"], run_dir, ROOT, "trial-root legacy index")
    legacy_index = _validate_legacy_index(legacy_path)
    paths = sorted(
        (run_dir / "method-metrics").glob("iteration-*.json"),
        key=lambda path: int(path.stem.split("-")[-1]),
    )
    failure_paths = sorted(
        (run_dir / "method-metrics").glob("terminal-failure-*.json"))
    if len(failure_paths) > 1:
        raise MetricsError("method trial has multiple unchained terminal failures")
    if not paths and not failure_paths:
        raise MetricsError("method trial has no terminal iteration manifests")
    referenced_event_paths: set[Path] = set()
    for manifest_path in paths:
        manifest_doc = load_json(manifest_path)
        event_path, _ = resolve_ref(
            manifest_doc["evidence"]["controller_events"],
            run_dir, ROOT, f"{manifest_path}: controller events")
        referenced_event_paths.add(event_path.resolve())
    for failure_path in failure_paths:
        failure_doc = load_json(failure_path)
        event_path, _ = resolve_ref(
            failure_doc["controller_events"], run_dir, ROOT,
            f"{failure_path}: controller events")
        referenced_event_paths.add(event_path.resolve())
    discovered_event_paths = {
        path.resolve() for path in run_dir.glob(
            "iteration-*-controller-events.json")
    }
    if discovered_event_paths != referenced_event_paths:
        raise MetricsError(
            "orphan or missing controller-event stream exists outside terminal chain")
    rows: list[dict[str, Any]] = []
    previous = None
    seen_live_keys: set[str] = set()
    seen_escalation_ids: set[str] = set()
    for expected, path in enumerate(paths, 1):
        if int(path.stem.split("-")[-1]) != expected:
            raise MetricsError("method manifest filenames are not contiguous")
        row = validate_manifest(
            path, run_dir, previous, seen_live_keys, seen_escalation_ids,
            trial["reporter_sha256"], legacy_index)
        if previous is None:
            if row["base_commit"] != trial["base_commit"]:
                raise MetricsError("first iteration base differs from trial root")
            before_doc = load_json(resolve_ref(
                load_json(path)["evidence"]["debt_before"], run_dir, ROOT,
                "first debt_before")[0])
            # The trial root pins bytes, not a trusted scalar.
            first_ref = load_json(path)["evidence"]["debt_before"]
            if first_ref["sha256"] != trial["debt_before_sha256"]:
                raise MetricsError("first debt differs from trial-root pin")
            _debt_rows(before_doc)
        rows.append(row)
        previous = row
    terminal_failure = None
    if failure_paths:
        terminal_failure = _validate_terminal_failure(
            failure_paths[0], run_dir, len(paths) + 1,
            trial["base_commit"] if previous is None else previous["tested_commit"])
    tested_rows = [
        row for row in rows if row["iteration_class"] != "infrastructure_failure"]
    if len(tested_rows) > 6:
        raise MetricsError(
            "method trial continued beyond the mandatory six-tested-iteration reassessment")
    promotion_events = sum(bool(row["accepted"]) for row in rows)
    gap_free = sum(bool(row["verifier_gap_free"]) for row in rows)
    repair_only = sum(row["iteration_class"] == "repair_only" for row in rows)
    duplicates = sorted({
        key for row in rows for key in row["duplicate_experiment_keys"]})
    accepted_transition_ids = {
        transition
        for row in rows if row["accepted"]
        for transition in row["transition_ids"]
    }
    terminal_met = set(rows[-1]["terminal_met_ids"]) if rows else set()
    retained = sorted(accepted_transition_ids & terminal_met)
    retained_rows = [item for item in retained if item.startswith("row:")]
    retained_dimensions = [
        item for item in retained if item.startswith("dimension:")]
    first_promotions: dict[str, int] = {}
    for row in rows:
        for transition in row["transition_ids"]:
            if row["accepted"] and transition not in first_promotions:
                first_promotions[transition] = row["iteration"]
    retained_first_iterations = sorted({
        first_promotions[item] for item in retained if item in first_promotions
    })
    contributing_iterations = len(retained_first_iterations)
    consecutive_no_reduction = 0
    for row in reversed(tested_rows):
        if row["accepted"]:
            break
        consecutive_no_reduction += 1
    tested_iterations = len(tested_rows)
    threshold_checks = {
        "six_tested_iterations": tested_iterations == 6,
        "three_retained_promotion_iterations": contributing_iterations >= 3,
        "three_distinct_retained_transitions": len(retained) >= 3,
        "four_gap_free_first_decisions": gap_free >= 4,
        "zero_duplicate_investigator_runs": not duplicates,
        "at_most_one_repair_only_iteration": repair_only <= 1,
        "all_promotions_knowledge_joined": all(
            not row["accepted"] or row["knowledge_join"]["complete"]
            for row in rows),
    }
    trial_success = (
        terminal_failure is None and tested_iterations == 6 and
        all(threshold_checks.values()))
    return {
        "schema": SUMMARY_SCHEMA,
        "trial_root_sha256": sha256(trial_path),
        "validator_sha256": sha256(Path(__file__).resolve()),
        "tested_iterations": tested_iterations,
        "terminal_iterations": len(rows),
        "terminal_failure": terminal_failure,
        "promotion_events": promotion_events,
        "retained_transition_ids": retained,
        "net_retained_rows": len(retained_rows),
        "net_retained_dimensions": len(retained_dimensions),
        "retained_promotion_iterations": contributing_iterations,
        "gap_free_first_decisions": gap_free,
        "repair_only_iterations": repair_only,
        "duplicate_investigator_experiment_keys": duplicates,
        "offline_query_count": sum(
            row["offline_query_count"] for row in rows),
        "external_bytes_reused": sum(
            row["external_bytes_reused"] for row in rows),
        "duckstation_launches": sum(
            row["duckstation_launches"] for row in rows),
        "atomic_jobs": sum(row["atomic_jobs"] for row in rows),
        "replay_frames": sum(row["replay_frames"] for row in rows),
        "observer_frames": sum(row["observer_frames"] for row in rows),
        "instructions": sum(row["instructions"] for row in rows),
        "consecutive_no_reduction_iterations": consecutive_no_reduction,
        "threshold_checks": threshold_checks,
        "trial_success": trial_success,
        "reassessment_required": (
            terminal_failure is not None or tested_iterations == 6 or
            consecutive_no_reduction >= 2),
        "iterations": rows,
    }


def _validate_terminal_failure(
        path: Path, run_dir: Path, expected_iteration: int,
        expected_base: str) -> dict[str, Any]:
    doc = load_json(path)
    _exact_keys(doc, {
        "schema", "iteration", "base_commit", "actual_commit", "code",
        "status", "controller_events", "created_at",
    }, str(path))
    if doc["schema"] != TERMINAL_FAILURE_SCHEMA or \
            doc["iteration"] != expected_iteration or \
            doc["base_commit"] != expected_base:
        raise MetricsError("terminal-failure chain identity is invalid")
    for key in ("base_commit", "actual_commit"):
        _commit_exists(doc[key])
    if not isinstance(doc["code"], str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_]{2,63}", doc["code"]):
        raise MetricsError("terminal-failure code is invalid")
    if not isinstance(doc["status"], list) or not all(
            isinstance(item, str) for item in doc["status"]):
        raise MetricsError("terminal-failure status is invalid")
    events_path, _ = resolve_ref(
        doc["controller_events"], run_dir, ROOT, "terminal failure events")
    events, _started, finished = _event_document(
        events_path, expected_iteration, expected_base, doc["actual_commit"])
    if events[-1]["type"] != "infrastructure_failure" or \
            events[-1]["payload"]["code"] != doc["code"] or \
            doc["created_at"] != finished:
        raise MetricsError("terminal failure is not joined to its controller event")
    if doc["actual_commit"] != doc["base_commit"]:
        raise MetricsError(
            "terminal failure cannot classify an unrelated/changed commit as infrastructure")
    return {
        "iteration": doc["iteration"],
        "code": doc["code"],
        "base_commit": doc["base_commit"],
        "actual_commit": doc["actual_commit"],
        "status": doc["status"],
        "manifest_sha256": sha256(path),
    }


def self_check() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    required = (
        SCHEMA, TRIAL_SCHEMA, SUMMARY_SCHEMA, LIVE_SCHEMA, OFFLINE_SCHEMA,
        TERMINAL_FAILURE_SCHEMA,
        LEGACY_SCHEMA, LEGACY_SOURCE_PROJECTION,
        "abl-phase4-method-external-preservation/1",
        "SEMANTIC_SOURCE", "GENERATOR_GUARD", "JOINED_ONLY",
        "duplicate JSON key", "debt snapshot does not reproduce",
        "three_retained_promotion_iterations",
        "pre-planned escalation/missing-fact join",
    )
    missing = [value for value in required if value not in source]
    if missing:
        raise MetricsError(f"validator self-check missing: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_check:
            self_check()
            print(f"PASS: validator source sha256={sha256(Path(__file__))}")
            return 0
        if not args.run_dir or not (args.check or args.summary):
            parser.error("--run-dir and --check/--summary are required")
        summary = validate_trial(args.run_dir)
        if args.summary:
            print(json.dumps(summary, indent=2, ensure_ascii=False))
        threshold_failed = (
            summary["terminal_failure"] is not None or (
                summary["tested_iterations"] == 6 and
                not summary["trial_success"]))
        if args.check and threshold_failed:
            failed = [
                name for name, passed in summary["threshold_checks"].items()
                if not passed
            ]
            raise MetricsError(
                "method trial is not acceptable: " +
                (f"terminal failure {summary['terminal_failure']['code']}"
                 if summary["terminal_failure"] is not None
                 else f"six-iteration threshold failures {failed}"))
        if args.check:
            print(
                "PASS: "
                f"{summary['terminal_iterations']} terminal iterations, "
                f"{summary['promotion_events']} accepted promotions, "
                f"{len(summary['duplicate_investigator_experiment_keys'])} duplicates")
        return 0
    except MetricsError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
