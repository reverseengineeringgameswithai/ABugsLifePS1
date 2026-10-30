#!/usr/bin/env python3
"""Validate and execute a finite exact-PC stop/arm evidence window.

This adapter is deliberately narrower than the ordinary Phase-4 atomic batch
runner.  It starts from an already paused, identity-verified atomic anchor and
composes direct typed debugger methods so instrumentation can be armed between
two pre-instruction execution stops.  Receipt emission and anchor setup remain
the responsibility of a future, predeclared live plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

import yaml


PLAN_SCHEMA = "abl-phase4-duckstation-exact-pc-plan/1"
RESULT_SCHEMA = "abl-phase4-duckstation-exact-pc-result/1"
REQUIRED_METHODS = (
    "debugger.status",
    "debugger.pause",
    "debugger.runUntilAddress",
    "debugger.getRegisters",
    "transferLog.clear",
    "transferLog.start",
    "transferLog.stop",
    "transferLog.get",
    "capture.atomic",
)
MAX_STATUS_POLLS = 4096
MAX_FRAME_DELTA = 600
MAX_TRANSFER_PAGE_SIZE = 10000
MAX_TRANSFER_PAGES = 10
MAX_TRANSFER_RECORDS = 100000
MAX_RESULT_BYTES = 64 * 1024 * 1024

RpcCall = Callable[[str, str, dict[str, Any], int], dict[str, Any]]
Sleep = Callable[[float], None]


class ExactPcFalsifiedError(RuntimeError):
    """A complete typed RPC result contradicted a planned exact-PC predicate."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _u32(value: object, label: str) -> int:
    if _is_int(value) and 0 <= value <= 0xFFFFFFFF:
        return int(value)
    if isinstance(value, str):
        try:
            parsed = int(value, 0)
        except ValueError:
            parsed = -1
        if 0 <= parsed <= 0xFFFFFFFF:
            return parsed
    raise ExactPcFalsifiedError(f"{label} is not a 32-bit integer")


def _plan_u32(
    value: object,
    label: str,
    errors: list[str],
    *,
    aligned: bool = True,
) -> int | None:
    try:
        parsed = _u32(value, label)
    except RuntimeError as exc:
        errors.append(str(exc))
        return None
    if aligned and parsed & 3:
        errors.append(f"{label} must be four-byte aligned")
    return parsed


def validate_plan(plan: object) -> list[str]:
    """Return every closed-schema error without changing external state."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["exact-PC plan must be an object"]
    expected_keys = {
        "schema",
        "campaign_id",
        "row_ids",
        "identity_join",
        "start_stop",
        "arm_sequence",
        "terminal_stop",
        "execution_limit",
        "transfer_pagination",
        "terminal_capture",
    }
    if set(plan) != expected_keys:
        errors.append("exact-PC plan keys differ from the closed schema")
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("exact-PC plan schema is invalid")
    if not isinstance(plan.get("campaign_id"), str) or not plan.get(
        "campaign_id"
    ):
        errors.append("exact-PC plan campaign_id is invalid")
    row_ids = plan.get("row_ids")
    if (
        not isinstance(row_ids, list)
        or not 1 <= len(row_ids) <= 3
        or any(not isinstance(row, str) or not row for row in row_ids)
        or len(set(row_ids)) != len(row_ids)
    ):
        errors.append("exact-PC plan requires one to three unique row IDs")

    identity = plan.get("identity_join")
    identity_keys = {
        "rpc_manifest_sha256",
        "source_revision",
        "source_dirty_state_hash",
        "dispatcher_sha256",
        "binary_sha256",
        "media_serial",
        "media_sha256",
    }
    if not isinstance(identity, dict) or set(identity) != identity_keys:
        errors.append("identity_join keys differ from the closed schema")
        identity = {}
    for name in identity_keys - {
        "source_revision",
        "source_dirty_state_hash",
        "media_serial",
    }:
        value = identity.get(name)
        if (
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
        ):
            errors.append(f"identity_join {name} is not a lowercase SHA-256")
    revision = identity.get("source_revision")
    if (
        not isinstance(revision, str)
        or len(revision) != 40
        or any(character not in "0123456789abcdef" for character in revision)
    ):
        errors.append("identity_join source_revision is not a Git object ID")
    dirty_state = identity.get("source_dirty_state_hash")
    if (
        not isinstance(dirty_state, str)
        or len(dirty_state) != 40
        or any(
            character not in "0123456789abcdef"
            for character in dirty_state
        )
    ):
        errors.append(
            "identity_join source_dirty_state_hash is not a Git object ID"
        )
    if identity.get("media_serial") != "SCUS-94288":
        errors.append("identity_join media_serial is not pristine SCUS-94288")

    start = plan.get("start_stop")
    if not isinstance(start, dict) or set(start) != {
        "method",
        "address",
        "boundary",
        "required_registers",
    }:
        errors.append("start_stop keys differ from the closed schema")
        start = {}
    if start.get("method") != "debugger.runUntilAddress":
        errors.append("start_stop must use debugger.runUntilAddress")
    start_address = _plan_u32(
        start.get("address"), "start_stop address", errors
    )
    if start.get("boundary") != "before_instruction":
        errors.append("start_stop must be a pre-instruction boundary")
    registers = start.get("required_registers")
    if not isinstance(registers, dict) or set(registers) != {
        "pc",
        "a0",
        "a1",
    }:
        errors.append("start_stop required_registers are not closed")
        registers = {}
    required_pc = _plan_u32(
        registers.get("pc"), "required register pc", errors
    )
    _plan_u32(
        registers.get("a0"), "required register a0", errors, aligned=False
    )
    _plan_u32(
        registers.get("a1"), "required register a1", errors, aligned=False
    )
    if (
        start_address is not None
        and required_pc is not None
        and start_address != required_pc
    ):
        errors.append("start_stop address differs from required pc")

    arm_sequence = plan.get("arm_sequence")
    expected_arm = [
        {"sequence": 0, "method": "transferLog.clear", "params": {}},
        {"sequence": 1, "method": "transferLog.start", "params": {}},
    ]
    if arm_sequence != expected_arm:
        errors.append(
            "arm_sequence must clear then start the transfer log exactly"
        )

    terminal = plan.get("terminal_stop")
    if not isinstance(terminal, dict) or set(terminal) != {
        "method",
        "address",
        "boundary",
    }:
        errors.append("terminal_stop keys differ from the closed schema")
        terminal = {}
    if terminal.get("method") != "debugger.runUntilAddress":
        errors.append("terminal_stop must use debugger.runUntilAddress")
    terminal_address = _plan_u32(
        terminal.get("address"), "terminal_stop address", errors
    )
    if terminal.get("boundary") != "before_instruction":
        errors.append("terminal_stop must be a pre-instruction boundary")
    if (
        start_address is not None
        and terminal_address is not None
        and start_address == terminal_address
    ):
        errors.append("start and terminal PCs must differ")

    limit = plan.get("execution_limit")
    if not isinstance(limit, dict) or set(limit) != {
        "clock",
        "max_frame_delta",
        "max_status_polls_per_stop",
        "poll_interval_ms",
        "socket_timeout_ms",
    }:
        errors.append("execution_limit keys differ from the closed schema")
        limit = {}
    if limit.get("clock") != "emulator_frame":
        errors.append("execution_limit clock must be emulator_frame")
    max_delta = limit.get("max_frame_delta")
    if not _is_int(max_delta) or not 1 <= max_delta <= MAX_FRAME_DELTA:
        errors.append(
            f"execution_limit max_frame_delta must be 1..{MAX_FRAME_DELTA}"
        )
    max_polls = limit.get("max_status_polls_per_stop")
    if not _is_int(max_polls) or not 1 <= max_polls <= MAX_STATUS_POLLS:
        errors.append(
            "execution_limit max_status_polls_per_stop must be "
            f"1..{MAX_STATUS_POLLS}"
        )
    poll_ms = limit.get("poll_interval_ms")
    if not _is_int(poll_ms) or not 1 <= poll_ms <= 1000:
        errors.append("execution_limit poll_interval_ms must be 1..1000")
    timeout_ms = limit.get("socket_timeout_ms")
    if not _is_int(timeout_ms) or not 1 <= timeout_ms <= 60000:
        errors.append("execution_limit socket_timeout_ms must be 1..60000")

    pagination = plan.get("transfer_pagination")
    if not isinstance(pagination, dict) or set(pagination) != {
        "page_size",
        "max_pages",
        "max_records",
        "max_bytes",
        "require_contiguous_indexes",
        "require_truncated",
    }:
        errors.append(
            "transfer_pagination keys differ from the closed schema"
        )
        pagination = {}
    page_size = pagination.get("page_size")
    max_pages = pagination.get("max_pages")
    max_records = pagination.get("max_records")
    max_bytes = pagination.get("max_bytes")
    if (
        not _is_int(page_size)
        or not 1 <= page_size <= MAX_TRANSFER_PAGE_SIZE
    ):
        errors.append(
            "transfer page_size must be "
            f"1..{MAX_TRANSFER_PAGE_SIZE}"
        )
    if (
        not _is_int(max_pages)
        or not 1 <= max_pages <= MAX_TRANSFER_PAGES
    ):
        errors.append(
            f"transfer max_pages must be 1..{MAX_TRANSFER_PAGES}"
        )
    if (
        not _is_int(max_records)
        or not 1 <= max_records <= MAX_TRANSFER_RECORDS
    ):
        errors.append(
            "transfer max_records must be "
            f"1..{MAX_TRANSFER_RECORDS}"
        )
    if not _is_int(max_bytes) or not 1 <= max_bytes <= MAX_RESULT_BYTES:
        errors.append(
            f"transfer max_bytes must be 1..{MAX_RESULT_BYTES}"
        )
    if (
        _is_int(page_size)
        and _is_int(max_pages)
        and _is_int(max_records)
        and page_size * max_pages < max_records
    ):
        errors.append(
            "transfer pagination envelope cannot retain max_records"
        )
    if pagination.get("require_contiguous_indexes") is not True:
        errors.append("transfer event indexes must be required contiguous")
    if pagination.get("require_truncated") is not False:
        errors.append("transfer truncation must be required false")

    capture = plan.get("terminal_capture")
    if (
        not isinstance(capture, dict)
        or set(capture) != {"method", "params"}
        or capture.get("method") != "capture.atomic"
    ):
        errors.append("terminal_capture must be a bounded capture.atomic call")
        capture = {}
    capture_params = capture.get("params")
    if not isinstance(capture_params, dict) or set(capture_params) != {
        "trigger",
        "include_registers",
        "trace_limit",
        "memory_dumps",
    }:
        errors.append("terminal_capture params differ from the closed schema")
        capture_params = {}
    if (
        not isinstance(capture_params.get("trigger"), str)
        or not capture_params.get("trigger")
        or len(capture_params["trigger"]) > 128
    ):
        errors.append("terminal_capture trigger is invalid")
    if capture_params.get("include_registers") is not True:
        errors.append("terminal_capture must include registers")
    trace_limit = capture_params.get("trace_limit")
    if not _is_int(trace_limit) or not 1 <= trace_limit <= 10000:
        errors.append("terminal_capture trace_limit must be 1..10000")
    memory_dumps = capture_params.get("memory_dumps")
    if (
        not isinstance(memory_dumps, list)
        or not 1 <= len(memory_dumps) <= 16
    ):
        errors.append("terminal_capture requires one to sixteen memory dumps")
        memory_dumps = []
    total_capture_bytes = 0
    for index, dump in enumerate(memory_dumps):
        if not isinstance(dump, dict) or set(dump) != {
            "label",
            "address",
            "length",
        }:
            errors.append(
                f"terminal_capture memory_dumps[{index}] is not closed"
            )
            continue
        if (
            not isinstance(dump.get("label"), str)
            or not dump.get("label")
            or len(dump["label"]) > 64
        ):
            errors.append(
                f"terminal_capture memory_dumps[{index}] label is invalid"
            )
        _plan_u32(
            dump.get("address"),
            f"terminal_capture memory_dumps[{index}] address",
            errors,
        )
        length = dump.get("length")
        if not _is_int(length) or not 1 <= length <= 1 << 20:
            errors.append(
                "terminal_capture memory dump length must be 1..1048576"
            )
        else:
            total_capture_bytes += int(length)
    if total_capture_bytes > 4 << 20:
        errors.append("terminal_capture memory dumps exceed 4194304 bytes")
    return sorted(set(errors))


def require_valid_plan(plan: object) -> dict[str, Any]:
    errors = validate_plan(plan)
    if errors:
        raise ValueError("; ".join(errors))
    assert isinstance(plan, dict)
    return plan


def _status_frame(status: dict[str, Any]) -> int:
    value = status.get("frame")
    if not _is_int(value):
        value = status.get("frame_number")
    if not _is_int(value) or value < 0:
        raise ExactPcFalsifiedError(
            "debugger.status lacks a finite emulator frame")
    return int(value)


def _status_pc(status: dict[str, Any]) -> int:
    return _u32(status.get("pc"), "debugger.status pc")


def _register_value(registers: dict[str, Any], name: str) -> int:
    raw = registers.get("registers")
    if isinstance(raw, dict) and name in raw:
        return _u32(raw[name], f"register {name}")
    raw_hex = registers.get("registers_hex")
    if isinstance(raw_hex, dict) and name in raw_hex:
        return _u32(raw_hex[name], f"register {name}")
    raise ExactPcFalsifiedError(f"debugger.getRegisters lacks {name}")


def execute_exact_pc_window(
    rpc_call: RpcCall,
    plan: object,
    server_session_id: str,
    verified_identity: object,
    *,
    sleep: Sleep = time.sleep,
) -> dict[str, Any]:
    """Execute the closed direct-method sequence against one owned session."""
    normalized = require_valid_plan(plan)
    if not isinstance(server_session_id, str) or not server_session_id:
        raise ValueError("server_session_id must be a non-empty string")
    expected_identity = normalized["identity_join"]
    if verified_identity != expected_identity:
        raise ValueError(
            "verified identity context differs from the exact-PC plan"
        )

    events: list[dict[str, Any]] = []
    limit = normalized["execution_limit"]

    def call(method: str, params: dict[str, Any]) -> dict[str, Any]:
        result = rpc_call(
            server_session_id,
            method,
            params,
            limit["socket_timeout_ms"],
        )
        if not isinstance(result, dict):
            raise ExactPcFalsifiedError(
                f"{method} returned a non-object result")
        events.append(
            {
                "sequence": len(events),
                "server_session_id": server_session_id,
                "method": method,
                "params": params,
                "socket_timeout_ms": limit["socket_timeout_ms"],
                "result_sha256": sha256_bytes(canonical_bytes(result)),
                "result": result,
            }
        )
        return result

    initial = call("debugger.status", {})
    if initial.get("valid") is not True or initial.get("paused") is not True:
        raise ExactPcFalsifiedError(
            "exact-PC adapter requires a valid paused atomic anchor"
        )
    initial_frame = _status_frame(initial)
    frame_ceiling = initial_frame + limit["max_frame_delta"]
    armed = False

    def fail_stop() -> None:
        try:
            call("debugger.pause", {})
        except Exception:
            pass

    def wait_for_pc(expected_pc: int, label: str) -> dict[str, Any]:
        for _ in range(limit["max_status_polls_per_stop"]):
            status = call("debugger.status", {})
            frame = _status_frame(status)
            if frame < initial_frame or frame > frame_ceiling:
                fail_stop()
                raise ExactPcFalsifiedError(
                    f"{label} escaped the finite emulator-frame bound"
                )
            if status.get("paused") is True:
                if status.get("valid") is not True:
                    raise ExactPcFalsifiedError(
                        f"{label} paused without a valid loaded system"
                    )
                observed_pc = _status_pc(status)
                if observed_pc != expected_pc:
                    raise ExactPcFalsifiedError(
                        f"{label} paused at 0x{observed_pc:08X}, "
                        f"expected 0x{expected_pc:08X}"
                    )
                return status
            sleep(limit["poll_interval_ms"] / 1000.0)
        fail_stop()
        raise ExactPcFalsifiedError(
            f"{label} exhausted its finite status-poll bound")

    try:
        start_address = _u32(
            normalized["start_stop"]["address"], "start_stop address"
        )
        call(
            "debugger.runUntilAddress",
            {"address": f"0x{start_address:08X}"},
        )
        start_status = wait_for_pc(start_address, "start_stop")
        registers = call("debugger.getRegisters", {})
        required = normalized["start_stop"]["required_registers"]
        observed_registers = {
            name: _register_value(registers, name)
            for name in ("pc", "a0", "a1")
        }
        expected_registers = {
            name: _u32(required[name], f"required register {name}")
            for name in ("pc", "a0", "a1")
        }
        if observed_registers != expected_registers:
            raise ExactPcFalsifiedError(
                "start_stop register identity differs from the typed plan"
            )

        cleared = call("transferLog.clear", {})
        if cleared.get("cleared") is not True:
            raise ExactPcFalsifiedError(
                "transferLog.clear did not confirm clearing")
        started = call("transferLog.start", {})
        if started.get("started") is not True:
            raise ExactPcFalsifiedError(
                "transferLog.start did not confirm arming")
        armed = True

        terminal_address = _u32(
            normalized["terminal_stop"]["address"],
            "terminal_stop address",
        )
        call(
            "debugger.runUntilAddress",
            {"address": f"0x{terminal_address:08X}"},
        )
        terminal_status = wait_for_pc(terminal_address, "terminal_stop")
        stopped = call("transferLog.stop", {})
        if stopped.get("stopped") is not True:
            raise ExactPcFalsifiedError(
                "transferLog.stop did not confirm stopping")
        armed = False

        pagination = normalized["transfer_pagination"]
        offset = 0
        total: int | None = None
        truncated: bool | None = None
        indexes: list[int] = []
        pages: list[dict[str, Any]] = []
        for page_number in range(pagination["max_pages"]):
            result = call(
                "transferLog.get",
                {"offset": offset, "limit": pagination["page_size"]},
            )
            events_page = result.get("events")
            observed_total = result.get("total")
            if (
                not isinstance(events_page, list)
                or not _is_int(observed_total)
                or observed_total < 0
                or observed_total > pagination["max_records"]
                or result.get("truncated")
                is not pagination["require_truncated"]
                or result.get("enabled") is not False
            ):
                raise ExactPcFalsifiedError(
                    "transferLog.get returned incomplete or truncated data"
                )
            if total is None:
                total = int(observed_total)
                truncated = bool(result["truncated"])
            elif total != observed_total or truncated != result["truncated"]:
                raise ExactPcFalsifiedError(
                    "transferLog pagination totals changed between pages"
                )
            if len(events_page) > pagination["page_size"]:
                raise ExactPcFalsifiedError(
                    "transferLog page exceeded its finite page_size"
                )
            page_indexes: list[int] = []
            for event in events_page:
                if not isinstance(event, dict):
                    raise ExactPcFalsifiedError(
                        "transferLog event is not an object")
                index = event.get("index")
                if not _is_int(index) or index <= 0:
                    raise ExactPcFalsifiedError(
                        "transferLog event index is not a positive integer"
                    )
                page_indexes.append(int(index))
            indexes.extend(page_indexes)
            pages.append(
                {
                    "page": page_number,
                    "offset": offset,
                    "returned": len(events_page),
                    "events": events_page,
                }
            )
            offset += len(events_page)
            if offset == total:
                break
            if not events_page:
                raise ExactPcFalsifiedError(
                    "transferLog pagination ended before its reported total"
                )
        if total is None or offset != total:
            raise ExactPcFalsifiedError(
                "transferLog pagination exceeded its finite page envelope"
            )
        if (
            pagination["require_contiguous_indexes"]
            and indexes
            and indexes != list(range(1, len(indexes) + 1))
        ):
            raise ExactPcFalsifiedError(
                "transferLog event indexes are not complete and contiguous"
            )
        retained_bytes = len(canonical_bytes(pages))
        if retained_bytes > pagination["max_bytes"]:
            raise ExactPcFalsifiedError(
                "transferLog pages exceed the typed byte bound")

        capture_spec = normalized["terminal_capture"]
        terminal_capture = call(
            capture_spec["method"], capture_spec["params"]
        )
        capture_cpu = terminal_capture.get("cpu")
        capture_status = (
            capture_cpu.get("status")
            if isinstance(capture_cpu, dict)
            else None
        )
        capture_memory = terminal_capture.get("memory")
        expected_labels = [
            dump["label"]
            for dump in capture_spec["params"]["memory_dumps"]
        ]
        observed_labels = (
            [dump.get("label") for dump in capture_memory]
            if isinstance(capture_memory, list)
            and all(isinstance(dump, dict) for dump in capture_memory)
            else None
        )
        if (
            terminal_capture.get("atomic") is not True
            or terminal_capture.get("trigger")
            != capture_spec["params"]["trigger"]
            or terminal_capture.get("frame")
            != _status_frame(terminal_status)
            or not _is_int(terminal_capture.get("cycle"))
            or terminal_capture["cycle"] < 0
            or not isinstance(capture_status, dict)
            or capture_status.get("valid") is not True
            or capture_status.get("paused") is not True
            or _status_pc(capture_status) != terminal_address
            or not isinstance(capture_cpu.get("registers"), dict)
            or observed_labels != expected_labels
        ):
            raise ExactPcFalsifiedError(
                "capture.atomic returned incomplete terminal identity"
            )
        return {
            "schema": RESULT_SCHEMA,
            "complete": True,
            "errors": [],
            "server_session_id": server_session_id,
            "verified_identity": verified_identity,
            "plan_sha256": sha256_bytes(canonical_bytes(normalized)),
            "execution": {
                "clock": "emulator_frame",
                "anchor_frame": initial_frame,
                "frame_ceiling": frame_ceiling,
                "start_stop_frame": _status_frame(start_status),
                "terminal_stop_frame": _status_frame(terminal_status),
            },
            "stops": {
                "start_pc": f"0x{start_address:08X}",
                "terminal_pc": f"0x{terminal_address:08X}",
                "registers": {
                    name: f"0x{value:08X}"
                    for name, value in observed_registers.items()
                },
            },
            "transfer": {
                "total": total,
                "truncated": truncated,
                "pages": pages,
                "indexes_contiguous": (
                    not indexes
                    or indexes == list(range(1, len(indexes) + 1))
                ),
                "retained_bytes": retained_bytes,
            },
            "terminal_capture": terminal_capture,
            "command_events": {
                "complete": True,
                "errors": [],
                "events": events,
            },
        }
    finally:
        if armed:
            try:
                call("transferLog.stop", {})
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    loaded = yaml.safe_load(args.plan.read_text())
    plan = (
        loaded["exact_pc_plan"]
        if isinstance(loaded, dict) and "exact_pc_plan" in loaded
        else loaded
    )
    errors = validate_plan(plan)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.validate_only:
        parser.error(
            "live execution requires a future predeclared anchor/receipt "
            "runner; this adapter currently exposes its typed library only"
        )
    print(
        "PASS: exact-PC stop/arm plan "
        f"({len(REQUIRED_METHODS)} required methods)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
