#!/usr/bin/env python3
"""Validate and execute one bounded, managed two-PC first-hit boundary.

The adapter begins at an already paused, identity-verified anchor.  It owns
exactly two ordinary execute breakpoints, proves that both are armed before
one resume, accepts only the first paused target with its target-specific
register identity, removes both owned breakpoint IDs, and retains normalized
command results.  Anchor setup and live-receipt emission remain the
responsibility of a future predeclared runner.
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


PLAN_SCHEMA = "abl-phase4-duckstation-two-pc-first-hit-plan/1"
RESULT_SCHEMA = "abl-phase4-duckstation-two-pc-first-hit-result/1"
REQUIRED_METHODS = (
    "debugger.status",
    "debugger.pause",
    "debugger.listBreakpoints",
    "debugger.addBreakpoint",
    "debugger.resume",
    "debugger.getRegisters",
    "debugger.removeBreakpoint",
    "capture.atomic",
)
MAX_STATUS_POLLS = 4096
MAX_FRAME_DELTA = 4096
MAX_RETAINED_BYTES = 16 * 1024 * 1024

RpcCall = Callable[[str, str, dict[str, Any], int], dict[str, Any]]
Sleep = Callable[[float], None]


class FirstHitFalsifiedError(RuntimeError):
    """A complete typed result contradicted the first-hit contract."""


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
    raise FirstHitFalsifiedError(f"{label} is not a 32-bit integer")


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


def _sha(value: object, label: str, errors: list[str]) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        errors.append(f"{label} is not a lowercase SHA-256")


def validate_plan(plan: object) -> list[str]:
    """Return all closed-schema errors without changing external state."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["two-PC first-hit plan must be an object"]
    expected_keys = {
        "schema",
        "campaign_id",
        "row_ids",
        "identity_join",
        "anchor_contract",
        "breakpoint_sequence",
        "resume",
        "execution_limit",
        "cleanup",
        "terminal_capture",
    }
    if set(plan) != expected_keys:
        errors.append("two-PC first-hit plan keys differ from the closed schema")
    if plan.get("schema") != PLAN_SCHEMA:
        errors.append("two-PC first-hit plan schema is invalid")
    if not isinstance(plan.get("campaign_id"), str) or not plan.get("campaign_id"):
        errors.append("two-PC first-hit campaign_id is invalid")
    rows = plan.get("row_ids")
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 3
        or any(not isinstance(row, str) or not row for row in rows)
        or len(set(rows)) != len(rows)
    ):
        errors.append("two-PC first-hit plan requires one to three unique rows")

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
    for name in {
        "rpc_manifest_sha256",
        "dispatcher_sha256",
        "binary_sha256",
        "media_sha256",
    }:
        _sha(identity.get(name), f"identity_join {name}", errors)
    for name in {"source_revision", "source_dirty_state_hash"}:
        value = identity.get(name)
        if (
            not isinstance(value, str)
            or len(value) != 40
            or any(character not in "0123456789abcdef" for character in value)
        ):
            errors.append(f"identity_join {name} is not a Git object ID")
    if identity.get("media_serial") != "SCUS-94288":
        errors.append("identity_join media_serial is not pristine SCUS-94288")

    anchor = plan.get("anchor_contract")
    if anchor != {
        "required_status": "valid_paused",
        "initial_breakpoints": [],
    }:
        errors.append("anchor_contract must require a paused empty breakpoint set")

    sequence = plan.get("breakpoint_sequence")
    if not isinstance(sequence, list) or len(sequence) != 2:
        errors.append("breakpoint_sequence must contain exactly two stops")
        sequence = []
    addresses: list[int] = []
    for index, stop in enumerate(sequence):
        if not isinstance(stop, dict) or set(stop) != {
            "sequence",
            "method",
            "params",
            "boundary",
            "required_registers",
        }:
            errors.append(f"breakpoint_sequence[{index}] is not closed")
            continue
        if stop.get("sequence") != index:
            errors.append("breakpoint_sequence indexes must be contiguous")
        if stop.get("method") != "debugger.addBreakpoint":
            errors.append("first-hit stops must use debugger.addBreakpoint")
        params = stop.get("params")
        if not isinstance(params, dict) or set(params) != {
            "address",
            "type",
            "enabled",
            "temporary",
        }:
            errors.append(f"breakpoint_sequence[{index}] params are not closed")
            params = {}
        address = _plan_u32(
            params.get("address"),
            f"breakpoint_sequence[{index}] address",
            errors,
        )
        if address is not None:
            addresses.append(address)
        if (
            params.get("type") != "execute"
            or params.get("enabled") is not True
            or params.get("temporary") is not False
        ):
            errors.append("first-hit stops must be managed enabled execute stops")
        if stop.get("boundary") != "before_instruction":
            errors.append("first-hit stops must be pre-instruction boundaries")
        registers = stop.get("required_registers")
        if not isinstance(registers, dict) or set(registers) != {"pc", "a0", "a1"}:
            errors.append(
                f"breakpoint_sequence[{index}] required_registers are not closed"
            )
            registers = {}
        required_pc = _plan_u32(
            registers.get("pc"),
            f"breakpoint_sequence[{index}] required pc",
            errors,
        )
        _plan_u32(
            registers.get("a0"),
            f"breakpoint_sequence[{index}] required a0",
            errors,
            aligned=False,
        )
        _plan_u32(
            registers.get("a1"),
            f"breakpoint_sequence[{index}] required a1",
            errors,
            aligned=False,
        )
        if address is not None and required_pc is not None and address != required_pc:
            errors.append("breakpoint address differs from its required pc")
    if len(addresses) == 2 and len(set(addresses)) != 2:
        errors.append("the two first-hit addresses must be distinct")

    if plan.get("resume") != {
        "method": "debugger.resume",
        "params": {},
        "winner_policy": "first_paused_target",
    }:
        errors.append("resume contract is not the closed first-hit policy")

    limit = plan.get("execution_limit")
    if not isinstance(limit, dict) or set(limit) != {
        "clock",
        "max_frame_delta",
        "max_status_polls",
        "poll_interval_ms",
        "socket_timeout_ms",
    }:
        errors.append("execution_limit keys differ from the closed schema")
        limit = {}
    if limit.get("clock") != "emulator_frame":
        errors.append("execution_limit clock must be emulator_frame")
    frame_delta = limit.get("max_frame_delta")
    if not _is_int(frame_delta) or not 1 <= frame_delta <= MAX_FRAME_DELTA:
        errors.append(
            f"execution_limit max_frame_delta must be 1..{MAX_FRAME_DELTA}"
        )
    polls = limit.get("max_status_polls")
    if not _is_int(polls) or not 1 <= polls <= MAX_STATUS_POLLS:
        errors.append(
            f"execution_limit max_status_polls must be 1..{MAX_STATUS_POLLS}"
        )
    poll_ms = limit.get("poll_interval_ms")
    if not _is_int(poll_ms) or not 1 <= poll_ms <= 1000:
        errors.append("execution_limit poll_interval_ms must be 1..1000")
    timeout_ms = limit.get("socket_timeout_ms")
    if not _is_int(timeout_ms) or not 1 <= timeout_ms <= 60000:
        errors.append("execution_limit socket_timeout_ms must be 1..60000")

    if plan.get("cleanup") != {
        "method": "debugger.removeBreakpoint",
        "remove_all_owned": True,
        "require_empty_after": True,
    }:
        errors.append("cleanup must remove every owned breakpoint and prove empty")

    capture = plan.get("terminal_capture")
    if (
        not isinstance(capture, dict)
        or set(capture) != {"method", "params"}
        or capture.get("method") != "capture.atomic"
    ):
        errors.append("terminal_capture must be a bounded capture.atomic call")
        capture = {}
    params = capture.get("params")
    if not isinstance(params, dict) or set(params) != {
        "trigger",
        "include_registers",
        "trace_limit",
    }:
        errors.append("terminal_capture params differ from the closed schema")
        params = {}
    if (
        not isinstance(params.get("trigger"), str)
        or not params.get("trigger")
        or len(params["trigger"]) > 128
    ):
        errors.append("terminal_capture trigger is invalid")
    if params.get("include_registers") is not True:
        errors.append("terminal_capture must include registers")
    trace_limit = params.get("trace_limit")
    if not _is_int(trace_limit) or not 1 <= trace_limit <= 10000:
        errors.append("terminal_capture trace_limit must be 1..10000")
    return sorted(set(errors))


def require_valid_plan(plan: object) -> dict[str, Any]:
    errors = validate_plan(plan)
    if errors:
        raise ValueError("; ".join(errors))
    assert isinstance(plan, dict)
    return plan


def observer_result_limits(plan: object) -> dict[str, int]:
    """Derive the closed receipt limits for one managed first-hit stream."""
    normalized = require_valid_plan(plan)
    # Twelve fixed calls surround the bounded status-poll loop.  Failure
    # cleanup can add a pause, two removals, and one final empty-list proof,
    # but those replace the normal register/post-hit/capture suffix rather
    # than exceeding this conservative ceiling.
    return {
        "max_records": normalized["execution_limit"]["max_status_polls"] + 12,
        "max_bytes": MAX_RETAINED_BYTES,
        "max_pages": 1,
    }


def _status_frame(status: dict[str, Any]) -> int:
    value = status.get("frame")
    if not _is_int(value):
        value = status.get("frame_number")
    if not _is_int(value) or value < 0:
        raise FirstHitFalsifiedError(
            "debugger.status lacks a finite emulator frame"
        )
    return int(value)


def _status_pc(status: dict[str, Any]) -> int:
    return _u32(status.get("pc"), "debugger.status pc")


def _register_value(registers: dict[str, Any], name: str) -> int:
    values = registers.get("registers")
    if isinstance(values, dict) and name in values:
        return _u32(values[name], f"register {name}")
    values = registers.get("registers_hex")
    if isinstance(values, dict) and name in values:
        return _u32(values[name], f"register {name}")
    raise FirstHitFalsifiedError(f"debugger.getRegisters lacks {name}")


def _breakpoints(result: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows = result.get("breakpoints")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise FirstHitFalsifiedError(f"{label} lacks a breakpoint list")
    return rows


def execute_first_hit(
    rpc_call: RpcCall,
    plan: object,
    server_session_id: str,
    verified_identity: object,
    *,
    sleep: Sleep = time.sleep,
) -> dict[str, Any]:
    """Execute one bounded first-hit sequence against one owned session."""
    normalized = require_valid_plan(plan)
    if not isinstance(server_session_id, str) or not server_session_id:
        raise ValueError("server_session_id must be a non-empty string")
    if verified_identity != normalized["identity_join"]:
        raise ValueError("verified identity context differs from the first-hit plan")

    events: list[dict[str, Any]] = []
    owned: list[str] = []
    limit = normalized["execution_limit"]

    def call(method: str, params: dict[str, Any]) -> dict[str, Any]:
        result = rpc_call(
            server_session_id,
            method,
            params,
            limit["socket_timeout_ms"],
        )
        if not isinstance(result, dict):
            raise FirstHitFalsifiedError(f"{method} returned a non-object result")
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

    def fail_pause() -> None:
        try:
            call("debugger.pause", {})
        except Exception:
            pass

    try:
        initial = call("debugger.status", {})
        if initial.get("valid") is not True or initial.get("paused") is not True:
            raise FirstHitFalsifiedError(
                "first-hit adapter requires a valid paused anchor"
            )
        initial_frame = _status_frame(initial)
        frame_ceiling = initial_frame + limit["max_frame_delta"]
        if _breakpoints(call("debugger.listBreakpoints", {}), "initial list"):
            raise FirstHitFalsifiedError(
                "first-hit anchor contains pre-existing breakpoints"
            )

        expected_by_pc: dict[int, dict[str, Any]] = {}
        for stop in normalized["breakpoint_sequence"]:
            params = stop["params"]
            result = call(stop["method"], params)
            identifier = result.get("id")
            breakpoint = result.get("breakpoint")
            address = _u32(params["address"], "breakpoint address")
            if (
                not isinstance(identifier, str)
                or not identifier.startswith("bp_")
                or identifier in owned
                or not isinstance(breakpoint, dict)
                or breakpoint.get("id") != identifier
                or _u32(breakpoint.get("address"), "added breakpoint address")
                != address
                or breakpoint.get("type") != "execute"
                or breakpoint.get("enabled") is not True
                or breakpoint.get("temporary") is not False
                or breakpoint.get("conditional") is not False
                or breakpoint.get("hit_count") != 0
                or breakpoint.get("trigger_count") != 0
            ):
                raise FirstHitFalsifiedError(
                    "debugger.addBreakpoint did not retain the managed stop"
                )
            owned.append(identifier)
            expected_by_pc[address] = stop

        armed_rows = _breakpoints(
            call("debugger.listBreakpoints", {}), "armed list"
        )
        if (
            [row.get("id") for row in armed_rows] != owned
            or [_u32(row.get("address"), "armed breakpoint address")
                for row in armed_rows] != list(expected_by_pc)
            or any(
                row.get("enabled") is not True
                or row.get("type") != "execute"
                or row.get("temporary") is not False
                or row.get("hit_count") != 0
                or row.get("trigger_count") != 0
                for row in armed_rows
            )
        ):
            raise FirstHitFalsifiedError(
                "both managed first-hit stops were not listed before resume"
            )

        resumed = call(normalized["resume"]["method"], {})
        if (
            resumed.get("valid") is not True
            or resumed.get("paused") is not False
        ):
            raise FirstHitFalsifiedError("debugger.resume did not start execution")

        winner_status: dict[str, Any] | None = None
        for _ in range(limit["max_status_polls"]):
            status = call("debugger.status", {})
            frame = _status_frame(status)
            if frame < initial_frame or frame > frame_ceiling:
                fail_pause()
                raise FirstHitFalsifiedError(
                    "first-hit search escaped the finite emulator-frame bound"
                )
            if status.get("paused") is True:
                if status.get("valid") is not True:
                    raise FirstHitFalsifiedError(
                        "first-hit search paused without a valid system"
                    )
                pc = _status_pc(status)
                if pc not in expected_by_pc:
                    raise FirstHitFalsifiedError(
                        f"first-hit search paused at unexpected PC 0x{pc:08X}"
                    )
                winner_status = status
                break
            sleep(limit["poll_interval_ms"] / 1000.0)
        if winner_status is None:
            fail_pause()
            raise FirstHitFalsifiedError(
                "first-hit search exhausted its finite status-poll bound"
            )

        winner_pc = _status_pc(winner_status)
        registers = call("debugger.getRegisters", {})
        observed = {
            name: _register_value(registers, name)
            for name in ("pc", "a0", "a1")
        }
        required = expected_by_pc[winner_pc]["required_registers"]
        expected = {
            name: _u32(required[name], f"required register {name}")
            for name in ("pc", "a0", "a1")
        }
        if observed != expected:
            raise FirstHitFalsifiedError(
                "first-hit register identity differs from the typed target"
            )

        hit_rows = _breakpoints(
            call("debugger.listBreakpoints", {}), "post-hit list"
        )
        by_id = {row.get("id"): row for row in hit_rows}
        if set(by_id) != set(owned):
            raise FirstHitFalsifiedError(
                "post-hit breakpoint ownership differs from the armed set"
            )
        winner_id = next(
            identifier
            for identifier, row in by_id.items()
            if _u32(row.get("address"), "post-hit address") == winner_pc
        )
        for identifier in owned:
            row = by_id[identifier]
            hit_count = row.get("hit_count")
            trigger_count = row.get("trigger_count")
            if not _is_int(hit_count) or not _is_int(trigger_count):
                raise FirstHitFalsifiedError(
                    "post-hit counters are not finite integers"
                )
            if identifier == winner_id:
                if hit_count != 1 or trigger_count != 1:
                    raise FirstHitFalsifiedError(
                        "winning breakpoint did not retain exactly one first hit"
                    )
            elif hit_count != 0 or trigger_count != 0:
                raise FirstHitFalsifiedError(
                    "non-winning breakpoint fired before cleanup"
                )

        removed: list[str] = []
        for identifier in list(owned):
            result = call("debugger.removeBreakpoint", {"id": identifier})
            if result != {"id": identifier, "removed": True}:
                raise FirstHitFalsifiedError(
                    "debugger.removeBreakpoint did not confirm owned cleanup"
                )
            removed.append(identifier)
        owned.clear()
        if _breakpoints(call("debugger.listBreakpoints", {}), "cleanup list"):
            raise FirstHitFalsifiedError(
                "breakpoints remain after owned first-hit cleanup"
            )

        capture_spec = normalized["terminal_capture"]
        capture = call(capture_spec["method"], capture_spec["params"])
        cpu = capture.get("cpu")
        status = cpu.get("status") if isinstance(cpu, dict) else None
        if (
            capture.get("atomic") is not True
            or capture.get("trigger") != capture_spec["params"]["trigger"]
            or capture.get("frame") != _status_frame(winner_status)
            or not _is_int(capture.get("cycle"))
            or capture["cycle"] < 0
            or not isinstance(status, dict)
            or status.get("valid") is not True
            or status.get("paused") is not True
            or _status_pc(status) != winner_pc
            or not isinstance(cpu.get("registers"), dict)
        ):
            raise FirstHitFalsifiedError(
                "capture.atomic returned incomplete first-hit identity"
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
                "first_hit_frame": _status_frame(winner_status),
            },
            "first_hit": {
                "pc": f"0x{winner_pc:08X}",
                "winner_breakpoint_id": winner_id,
                "registers": {
                    name: f"0x{value:08X}"
                    for name, value in observed.items()
                },
            },
            "cleanup": {
                "owned_breakpoint_ids": removed,
                "remaining_breakpoints": 0,
            },
            "terminal_capture": capture,
            "command_events": {
                "complete": True,
                "errors": [],
                "events": events,
            },
        }
    finally:
        if owned:
            fail_pause()
            for identifier in list(owned):
                try:
                    call("debugger.removeBreakpoint", {"id": identifier})
                    owned.remove(identifier)
                except Exception:
                    pass
            try:
                remaining = _breakpoints(
                    call("debugger.listBreakpoints", {}),
                    "failure cleanup list",
                )
            except Exception as exc:
                raise FirstHitFalsifiedError(
                    "first-hit failure cleanup could not prove an empty "
                    "breakpoint set"
                ) from exc
            if remaining:
                raise FirstHitFalsifiedError(
                    "first-hit failure cleanup left managed breakpoints armed"
                )
            owned.clear()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    loaded = yaml.safe_load(args.plan.read_text())
    plan = (
        loaded["first_hit_plan"]
        if isinstance(loaded, dict) and "first_hit_plan" in loaded
        else loaded
    )
    errors = validate_plan(plan)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.validate_only:
        parser.error(
            "live execution requires a future predeclared anchor/receipt runner; "
            "this adapter currently exposes its typed library only"
        )
    print(
        "PASS: two-PC first-hit plan "
        f"({len(REQUIRED_METHODS)} required methods)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
