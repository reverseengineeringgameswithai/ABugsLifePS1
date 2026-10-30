#!/usr/bin/env python3
"""Collect the first natural E15 LEVEL01-B call and bounded lifecycle.

This collector deliberately changes method from the rejected frame-zero
precise-observer run.  It first uses ``movie.traceToFrame`` to binary-search
the first cumulative hit of resident caller 0x8005031C.  Every localization
query contains its own uninstrumented/passive cached-interpreter comparison.
Only after the last absent target does it arm exact instruction observers for
the short selector/completion/teardown window.  A timing-identical all-neutral
movie derivative supplies the native negative control.

Raw receipts and transient derived movies must remain outside the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

import phase4_common as common
import phase4_fmv_levelb_phase_neutral_live as prior


SOURCE_MOVIE_FRAMES = 15230
PADDING_FRAMES = 3000
DERIVED_MOVIE_FRAMES = SOURCE_MOVIE_FRAMES + PADDING_FRAMES
POST_CALL_FRAMES = 1800
# The rejected diagnostic run retained no result, but its RPC-duration sequence
# bounded 14,278 as an untrusted lower lead.  This collector queries and proves
# that absence again before using it as the binary-search lower boundary.
LOCALIZATION_LOWER_TARGET = 14278

COMPLETED_LEVEL_B_CALL = 0x8005031C
LOADER = 0x8003E7C0
ST_CLEAR_RING = 0x8007094C
CALLBACK_TEARDOWN = 0x800709AC
COMMON_EXIT_CALLBACK_CALL = 0x800B74A4
SELECTED_LIMIT = 0x80131EEE
COMPLETION_REQUEST = 0x800CAC10
STR_BACKLOC = 0x80088FFC
DECODE_STOP_LATCH = 0x800B9A54

EXACT_CALL_RANGE = [{
    "start": f"0x{COMPLETED_LEVEL_B_CALL:08X}",
    "end": f"0x{COMPLETED_LEVEL_B_CALL:08X}",
    "label": "completed_level_b_call",
    "max_pcs": 4,
}]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _non_neutral(pad: dict) -> bool:
    for key, value in pad.items():
        if key in {"lx", "ly", "rx", "ry"}:
            if int(value) != 128:
                return True
        elif bool(value):
            return True
    return False


def _write_extended_movie(path: Path, *, neutralize: bool) -> dict:
    movie = json.loads(prior.MOVIE.read_text())
    frames = movie.get("frames") or []
    _require(
        movie.get("format") == "DuckStationInputMovie" and
        movie.get("version") == 3 and
        len(frames) == SOURCE_MOVIE_FRAMES and
        (movie.get("start_state") or {}).get("from_boot") is True,
        "source full-level movie metadata drifted")
    source_prefix = json.dumps(
        frames, separators=(",", ":"), sort_keys=True).encode()
    changed: list[int] = []
    if neutralize:
        for row in frames:
            ports = row.get("ports") or {}
            pad = ports.get("0") or {}
            if _non_neutral(pad):
                changed.append(int(row["frame"]))
                ports["0"] = {}
    derived_prefix = json.dumps(
        frames, separators=(",", ":"), sort_keys=True).encode()
    if not neutralize:
        _require(
            derived_prefix == source_prefix,
            "positive source prefix changed while extending the movie")
    for frame in range(SOURCE_MOVIE_FRAMES, DERIVED_MOVIE_FRAMES):
        frames.append({"frame": frame, "ports": {"0": {}}})
    payload = json.dumps(
        movie, separators=(",", ":"), sort_keys=True).encode() + b"\n"
    path.write_bytes(payload)
    return {
        "source_path": str(prior.MOVIE),
        "source_sha256": common.sha256(prior.MOVIE),
        "source_bytes": prior.MOVIE.stat().st_size,
        "source_frame_count": SOURCE_MOVIE_FRAMES,
        "derived_sha256": common.sha256(path),
        "derived_bytes": path.stat().st_size,
        "derived_frame_count": len(frames),
        "padding_frames": PADDING_FRAMES,
        "source_prefix_sha256": _sha256_bytes(source_prefix),
        "derived_prefix_sha256": _sha256_bytes(derived_prefix),
        "source_prefix_semantically_identical": not neutralize,
        "changed_frame_count": len(changed),
        "first_changed_frame": changed[0] if changed else None,
        "last_changed_frame": changed[-1] if changed else None,
        "changed_frames_sha256": _sha256_bytes(
            json.dumps(changed, separators=(",", ":")).encode()),
        "changed_field":
            "all non-neutral port-0 buttons/axes -> neutral"
            if neutralize else "none",
        "anchor": "from_boot",
        "transient_storage":
            "temporary /var/tmp directory removed before collector exit",
    }


def _trace_exact_pc(
        client: Any, path: Path, target: int, label: str) -> dict:
    trace = prior._compact_trace(client.call("movie.traceToFrame", {
        "path": str(path),
        "frame": target,
        "ranges": EXACT_CALL_RANGE,
    }, timeout=1800))
    comparison = trace.get("comparison") or {}
    _require(
        comparison.get("cycle_neutral") is True and
        all(comparison.get(key) is True for key in (
            "same_ram", "same_registers", "same_cycle", "same_frame")),
        f"{label} target {target}: passive trace was not cycle-neutral")
    coverage = trace.get("coverage") or []
    _require(
        len(coverage) == 1 and coverage[0].get("truncated") is False,
        f"{label} target {target}: exact-PC coverage is absent or truncated")
    status = client.call("movie.status", {})
    _require(
        status.get("reproducible") is True and
        status.get("truncated") is False and
        status.get("playback_index") == target and
        status.get("frame_count") == DERIVED_MOVIE_FRAMES and
        (status.get("start_state") or {}).get("from_boot") is True,
        f"{label} target {target}: recorded boot anchor was not retained")
    pcs = {str(pc).lower() for pc in coverage[0].get("pcs") or []}
    return {
        "target_frame": target,
        "contains_call": f"0x{COMPLETED_LEVEL_B_CALL:08x}" in pcs,
        "movie_status": status,
        "trace": trace,
    }


def _localize_first_target(client: Any, path: Path) -> dict:
    queries: list[dict] = []
    low = LOCALIZATION_LOWER_TARGET
    high = SOURCE_MOVIE_FRAMES
    high_query = _trace_exact_pc(client, path, high, "localize_high")
    queries.append(high_query)
    _require(
        high_query["contains_call"],
        "full recorded prefix no longer reaches completed-level-B caller")
    low_query = _trace_exact_pc(client, path, low, "localize_low")
    queries.append(low_query)
    _require(
        not low_query["contains_call"],
        "diagnostic lower lead already contains completed-level-B caller")
    while high - low > 1:
        middle = (low + high) // 2
        query = _trace_exact_pc(
            client, path, middle, f"localize_{middle}")
        queries.append(query)
        if query["contains_call"]:
            high = middle
        else:
            low = middle
    return {
        "last_absent_target": low,
        "first_present_target": high,
        "queried_lower_target": LOCALIZATION_LOWER_TARGET,
        "lower_target_source":
            "untrusted rejected-run duration lead, re-proved absent here",
        "query_count": len(queries),
        "queries": queries,
    }


def _registers(client: Any) -> dict[str, str]:
    return {
        str(key).lower(): str(value).lower()
        for key, value in client.call(
            "debugger.getRegisters", {})["registers_hex"].items()
    }


def _atomic(client: Any, trigger: str) -> dict:
    return client.call("capture.atomic", {
        "trigger": trigger,
        "include_registers": True,
        "trace_limit": 128,
        "memory_dumps": [
            {"label": "str_backloc",
             "address": f"0x{STR_BACKLOC:08X}", "length": 4},
            {"label": "fmv_bin_head",
             "address": "0x800B5788", "length": 0x100},
            {"label": "completion_request",
             "address": f"0x{COMPLETION_REQUEST:08X}", "length": 4},
            {"label": "selected_frame_limit",
             "address": f"0x{SELECTED_LIMIT:08X}", "length": 2},
            {"label": "decode_stop_latch",
             "address": f"0x{DECODE_STOP_LATCH:08X}", "length": 1},
            {"label": "fmv_running_latch",
             "address": "0x80082250", "length": 4},
            {"label": "shell_substate",
             "address": "0x8008243C", "length": 4},
            {"label": "scene", "address": "0x80082504", "length": 4},
        ],
    })


def _arm_exact_window(client: Any) -> dict:
    function = client.call("functionTrace.start", {
        "functions": [
            f"0x{LOADER:08X}", f"0x{ST_CLEAR_RING:08X}",
            f"0x{CALLBACK_TEARDOWN:08X}"],
        "capture_memory": False,
        "max_events": 64,
    })
    access = {}
    for label, address, length, maximum in (
            ("selected_frame_limit", SELECTED_LIMIT, 2, 16),
            # Loading FMV.BIN overwrites the future completion cell before
            # the player publishes its later one.  Keep the complete bounded
            # ring so loader traffic cannot evict 0x800B6B48.
            ("completion_request", COMPLETION_REQUEST, 4, 4096),
            ("str_backloc", STR_BACKLOC, 4, 1024),
            ("decode_stop_latch", DECODE_STOP_LATCH, 1, 32)):
        access[label] = client.call("accessLog.addWatch", {
            "address": f"0x{address:08X}",
            "length": length,
            "type": "write",
            "label": label,
            "max_events": maximum,
        })
    execution = client.call("execTrace.addWatch", {
        "pc": f"0x{COMPLETED_LEVEL_B_CALL:08X}",
        "label": "completed_level_b_call",
        "capture": ["a0", "a1", "v0", "v1", "ra", "sp"],
        "max_events": 8,
    })
    return {
        "function": function,
        "access": access,
        "execution": execution,
    }


def _read_exact_window(client: Any, armed: dict) -> dict:
    access = {}
    for label, watch in armed["access"].items():
        access[label] = client.call("accessLog.get", {
            "watch_id": watch["watch_id"],
            "offset": 0,
            "limit": 4096,
        })
    return {
        "functions": client.call(
            "functionTrace.get", {"offset": 0, "limit": 256}),
        "execution": client.call("execTrace.get", {
            "watch_id": armed["execution"]["watch_id"],
            "offset": 0,
            "limit": 64,
        }),
        "access": access,
    }


def _clear_observers(client: Any) -> list[dict]:
    outcomes = []
    for method, params in (
            ("debugger.clearBreakpoints", {}),
            ("accessLog.clear", {}),
            ("execTrace.clear", {}),
            ("functionTrace.stop", {}),
            ("functionTrace.clear", {}),
            ("movie.stopPlayback", {}),
            ("movie.clear", {}),
            ("emulator.clearControllerState", {"port": 0}),
            ("emulator.setTurbo", {"enabled": False}),
            ("emulator.setFastForward", {"enabled": False})):
        try:
            outcomes.append({
                "method": method,
                "ok": True,
                "result": client.call(method, params),
            })
        except Exception as exc:
            outcomes.append({
                "method": method,
                "ok": False,
                "error": str(exc),
            })
    return outcomes


def _run_positive(
        client: Any, path: Path, last_absent_target: int) -> dict:
    prelude = _trace_exact_pc(
        client, path, last_absent_target, "positive_exact_prelude")
    _require(
        not prelude["contains_call"],
        "positive exact prelude already contains the target caller")
    breakpoint = client.call("debugger.addBreakpoint", {
        "address": f"0x{COMPLETED_LEVEL_B_CALL:08X}",
        "type": "execute",
        "enabled": True,
        "temporary": False,
    })
    client.drain_events()
    client.call("debugger.resume", {})
    event = client.wait_event(
        lambda row: row.get("event") in ("breakpointHit", "paused"),
        timeout=120.0)
    _require(event is not None, "first caller breakpoint did not fire")
    call_status = client.call("debugger.status", {})
    registers = _registers(client)
    _require(
        call_status.get("paused") is True and
        int(registers["pc"], 16) == COMPLETED_LEVEL_B_CALL,
        f"first caller did not pause at 0x{COMPLETED_LEVEL_B_CALL:08x}")
    client.call("debugger.removeBreakpoint", {"id": breakpoint["id"]})
    call_capture = _atomic(client, "e15_levelb_first_caller")
    armed = _arm_exact_window(client)

    loader_breakpoint = client.call("debugger.addBreakpoint", {
        "address": f"0x{LOADER:08X}",
        "type": "execute",
        "enabled": True,
        "temporary": False,
    })
    client.drain_events()
    client.call("debugger.resume", {})
    loader_event = client.wait_event(
        lambda row: row.get("event") in ("breakpointHit", "paused"),
        timeout=120.0)
    _require(loader_event is not None, "loader entry breakpoint did not fire")
    loader_status = client.call("debugger.status", {})
    loader_registers = _registers(client)
    _require(
        loader_status.get("paused") is True and
        int(loader_registers["pc"], 16) == LOADER,
        f"loader did not pause at 0x{LOADER:08x}")
    client.call(
        "debugger.removeBreakpoint", {"id": loader_breakpoint["id"]})
    loader_capture = _atomic(client, "e15_levelb_loader_entry")

    teardown_breakpoint = client.call("debugger.addBreakpoint", {
        "address": f"0x{COMMON_EXIT_CALLBACK_CALL:08X}",
        "type": "execute",
        "enabled": True,
        "temporary": False,
    })
    client.drain_events()
    client.call("debugger.resume", {})
    teardown_event = client.wait_event(
        lambda row: row.get("event") in ("breakpointHit", "paused"),
        timeout=300.0)
    _require(
        teardown_event is not None,
        "common callback-teardown callsite breakpoint did not fire")
    teardown_status = client.call("debugger.status", {})
    teardown_registers = _registers(client)
    _require(
        teardown_status.get("paused") is True and
        int(teardown_registers["pc"], 16) == COMMON_EXIT_CALLBACK_CALL,
        "common callback-teardown breakpoint paused at the wrong PC")
    teardown_capture = _atomic(
        client, "e15_levelb_common_callback_call")
    client.call(
        "debugger.removeBreakpoint", {"id": teardown_breakpoint["id"]})

    elapsed_frames = (
        int(teardown_status["frame"]) - int(call_status["frame"]))
    _require(
        0 <= elapsed_frames < POST_CALL_FRAMES,
        f"teardown elapsed-frame bound drifted: {elapsed_frames}")
    run = client.call("emulator.advanceFrames", {
        "frames": POST_CALL_FRAMES - elapsed_frames,
    }, timeout=1200)
    endpoint_capture = _atomic(
        client, "e15_levelb_after_bounded_lifecycle")
    traces = _read_exact_window(client, armed)
    movie_status = client.call("movie.status", {})
    cleanup = _clear_observers(client)
    return {
        "prelude": prelude,
        "breakpoint": breakpoint,
        "breakpoint_event": event,
        "first_call": {
            "status": call_status,
            "registers": registers,
            "atomic_capture": call_capture,
        },
        "loader_entry": {
            "breakpoint": loader_breakpoint,
            "breakpoint_event": loader_event,
            "status": loader_status,
            "registers": loader_registers,
            "atomic_capture": loader_capture,
        },
        "common_callback_call": {
            "breakpoint": teardown_breakpoint,
            "breakpoint_event": teardown_event,
            "status": teardown_status,
            "registers": teardown_registers,
            "atomic_capture": teardown_capture,
        },
        "elapsed_frames_to_common_callback": elapsed_frames,
        "armed": armed,
        "run": run,
        "endpoint_capture": endpoint_capture,
        "traces": traces,
        "movie_status": movie_status,
        "cleanup": cleanup,
    }


def _run_neutral(
        client: Any, path: Path, last_absent_target: int) -> dict:
    prelude = _trace_exact_pc(
        client, path, last_absent_target, "neutral_exact_prelude")
    _require(
        not prelude["contains_call"],
        "neutral prelude unexpectedly contains completed-level-B caller")
    armed = _arm_exact_window(client)
    run = client.call("emulator.advanceFrames", {
        "frames": POST_CALL_FRAMES,
    }, timeout=1200)
    endpoint_capture = _atomic(
        client, "e15_levelb_neutral_bounded_window")
    traces = _read_exact_window(client, armed)
    movie_status = client.call("movie.status", {})
    cleanup = _clear_observers(client)
    return {
        "prelude": prelude,
        "armed": armed,
        "run": run,
        "endpoint_capture": endpoint_capture,
        "traces": traces,
        "movie_status": movie_status,
        "cleanup": cleanup,
    }


def _events(window: dict, label: str) -> list[dict]:
    return (
        ((window.get("traces") or {}).get("access") or {})
        .get(label, {}).get("events") or []
    )


def _function_events(window: dict) -> list[dict]:
    result = ((window.get("traces") or {}).get("functions") or {})
    return result.get("events") or result.get("functions") or []


def _validate_observation(
        localization: dict, positive: dict, neutral: dict) -> dict:
    registers = positive["first_call"]["registers"]
    loader_registers = positive["loader_entry"]["registers"]
    selected = _events(positive, "selected_frame_limit")
    completion = _events(positive, "completion_request")
    stop_latch = _events(positive, "decode_stop_latch")
    functions = _function_events(positive)
    positive_exec = (
        positive["traces"]["execution"].get("events") or [])
    neutral_exec = neutral["traces"]["execution"].get("events") or []
    neutral_functions = _function_events(neutral)

    selected_485 = [
        row for row in selected
        if row.get("instruction_pc", "").lower() == "0x800b6dc0" and
        row.get("new_value") == 485
    ]
    frame_order_completion_one = [
        row for row in completion
        if row.get("instruction_pc", "").lower() == "0x800b6b24" and
        row.get("new_value") == 1
    ]
    loader_entries = [
        row for row in functions
        if row.get("type") == "entry" and
        row.get("function", row.get("address", "")).lower() ==
        "0x8003e7c0"
    ]
    st_clear_entries = [
        row for row in functions
        if row.get("type") == "entry" and
        row.get("function", row.get("address", "")).lower() ==
        "0x8007094c" and
        row.get("caller", "").lower() == "0x800b749c"
    ]
    teardown_entries = [
        row for row in functions
        if row.get("type") == "entry" and
        row.get("function", row.get("address", "")).lower() ==
        "0x800709ac" and
        row.get("caller", "").lower() == "0x800b74a4"
    ]
    _require(
        not positive["traces"]["access"]["completion_request"].get(
            "truncated", False),
        "positive completion-request access trace was truncated")
    _require(
        localization["first_present_target"] ==
        localization["last_absent_target"] + 1,
        "binary localization did not converge to adjacent targets")
    _require(
        int(registers["a0"], 16) == 0 and
        int(registers["a1"], 16) == 0 and
        int(registers["s0"], 16) == 1,
        "pre-delay caller registers are not a0=0/a1=0/progress=1: "
        f"{registers}")
    _require(
        int(loader_registers["pc"], 16) == LOADER and
        int(loader_registers["a0"], 16) == 11 and
        int(loader_registers["a1"], 16) == 0xFFFFFFFF,
        "post-load-delay/JAL-delay loader registers are not a0=11/a1=-1: "
        f"{loader_registers}")
    _require(
        len(positive_exec) >= 1,
        "positive exact caller watch retained no event")
    _require(
        selected_485,
        "positive lifecycle retained no selected-limit 485 write")
    _require(
        frame_order_completion_one,
        "positive lifecycle retained no 0x800B6B24 completion-one write: " +
        json.dumps({
            "completion_events": completion[:32],
            "function_events": functions[:32],
            "run": positive.get("run"),
            "endpoint_memory":
                (positive.get("endpoint_capture") or {}).get("memory"),
            "movie_status": positive.get("movie_status"),
        }, sort_keys=True))
    _require(
        not [
            row for row in stop_latch
            if row.get("instruction_pc", "").lower().startswith("0x800b")
        ],
        "positive lifecycle wrote the decoded-record stop latch")
    _require(
        loader_entries and
        loader_entries[0].get("caller", "").lower() == "0x8005031c",
        "positive lifecycle retained no level-B-table fmv_bin_load entry")
    _require(
        st_clear_entries and teardown_entries,
        "positive lifecycle retained no balanced common teardown entries")
    _require(
        selected_485[0]["cycle"] <
        frame_order_completion_one[0]["cycle"] <
        st_clear_entries[0]["cycle"] < teardown_entries[0]["cycle"],
        "selected-limit/completion/common-teardown ordering drifted")
    _require(
        not neutral_exec,
        "neutral branch unexpectedly reached completed-level-B caller")
    neutral_loader_entries = [
        row for row in neutral_functions
        if row.get("type") == "entry" and
        row.get("function", row.get("address", "")).lower() ==
        "0x8003e7c0"
    ]
    neutral_levelb_loader_entries = [
        row for row in neutral_loader_entries
        if row.get("caller", "").lower() == "0x8005031c"
    ]
    neutral_selected_485 = [
        row for row in _events(neutral, "selected_frame_limit")
        if row.get("instruction_pc", "").lower() == "0x800b6dc0" and
        row.get("new_value") == 485
    ]
    _require(
        not neutral_levelb_loader_entries and not neutral_selected_485,
        "neutral branch unexpectedly entered the completed-level-B loader "
        "interface or published selector-11 limit 485")
    return {
        "first_present_target": localization["first_present_target"],
        "last_absent_target": localization["last_absent_target"],
        "first_call": {
            "frame": positive["first_call"]["status"]["frame"],
            "cycle": positive["first_call"]["status"]["cycle"],
            "pc": registers["pc"],
            "a0": registers["a0"],
            "a1": registers["a1"],
            "s0_progress_id": registers["s0"],
            "ra": registers["ra"],
            "sp": registers["sp"],
        },
        "loader_entry_registers": {
            "frame": positive["loader_entry"]["status"]["frame"],
            "cycle": positive["loader_entry"]["status"]["cycle"],
            "pc": loader_registers["pc"],
            "a0": loader_registers["a0"],
            "a1": loader_registers["a1"],
            "ra": loader_registers["ra"],
            "sp": loader_registers["sp"],
        },
        "selected_limit_485_events": selected_485,
        "frame_order_completion_one_events": frame_order_completion_one,
        "decoded_stop_latch_game_write_count": len([
            row for row in stop_latch
            if row.get("instruction_pc", "").lower().startswith("0x800b")
        ]),
        "positive_caller_events": len(positive_exec),
        "neutral_caller_events": len(neutral_exec),
        "positive_loader_entries": len(loader_entries),
        "neutral_loader_entries": len(neutral_loader_entries),
        "neutral_generic_loader_events": neutral_loader_entries,
        "neutral_levelb_loader_entries": len(neutral_levelb_loader_entries),
        "neutral_selected_limit_485_events": neutral_selected_485,
        "loader_function_entry": loader_entries[0],
        "common_exit_st_clear_ring": st_clear_entries[0],
        "common_exit_callback_teardown": teardown_entries[0],
        "ordered_limit_completion_teardown": True,
    }


def collect(port: int, token: str) -> dict:
    for label, path, digest in (
            ("movie", prior.MOVIE, prior.EXPECTED["movie_sha256"]),
            ("cue", prior.CUE, prior.EXPECTED["cue_sha256"]),
            ("bin", prior.BIN, prior.EXPECTED["bin_sha256"])):
        _require(
            path.is_file() and common.sha256(path) == digest,
            f"{label} fixture identity drifted")
    module = prior._load_client()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(1800)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status",
        "debugger.getRegisters", "debugger.addBreakpoint",
        "debugger.removeBreakpoint", "debugger.resume",
        "debugger.clearBreakpoints", "emulator.getMediaInfo",
        "emulator.advanceFrames", "capture.atomic",
        "movie.traceToFrame", "movie.status", "movie.stopPlayback",
        "movie.clear", "accessLog.addWatch", "accessLog.get",
        "accessLog.clear", "execTrace.addWatch", "execTrace.get",
        "execTrace.clear", "functionTrace.start", "functionTrace.get",
        "functionTrace.stop", "functionTrace.clear",
        "scenario.runBatch", "scenario.loadStateAndRun",
        "scenario.bootAndRun", "provenanceLog.start",
        "provenanceLog.get",
    }
    missing = sorted(
        method for method in required
        if not prior._method_present(capabilities, method))
    _require(not missing, f"running debugger lacks methods: {missing}")
    _require(
        (capabilities.get("api") or {}).get("version") == "2.1.0" and
        (capabilities.get("api") or {}).get("schema_version") ==
        "2026-07-18" and
        (capabilities.get("binary") or {}).get("sha256") ==
        prior.EXPECTED["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        prior.EXPECTED["source_revision"] and
        (capabilities.get("source") or {}).get("dirty") is True and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        prior.EXPECTED["dirty_state_hash"],
        "debugger capability identity drifted")
    status = client.call("debugger.status", {})
    media = client.call("emulator.getMediaInfo", {})
    _require(
        status.get("valid") is True and
        status.get("game_serial") == "SCUS-94288" and
        Path(str(status.get("game_path") or "")).resolve() ==
        prior.CUE.resolve(),
        f"debugger status media identity drifted: {status}")
    _require(
        media.get("has_media") is True and
        media.get("game_serial") == "SCUS-94288" and
        Path(str(media.get("path") or "")).resolve() ==
        prior.CUE.resolve(),
        f"mounted media identity drifted: {media}")
    media["verified_cue_sha256"] = common.sha256(prior.CUE)
    media["verified_track_sha256"] = common.sha256(prior.BIN)

    cleanup: list[dict] = []
    try:
        with tempfile.TemporaryDirectory(
                prefix="abl-p4-e15-levelb-first-call-",
                dir="/var/tmp") as temporary:
            original_path = Path(temporary) / (
                "LEVEL01.extended.movie.json")
            neutral_path = Path(temporary) / (
                "LEVEL01.extended-neutral.movie.json")
            original_recipe = _write_extended_movie(
                original_path, neutralize=False)
            neutral_recipe = _write_extended_movie(
                neutral_path, neutralize=True)
            localization = _localize_first_target(
                client, original_path)
            positive = _run_positive(
                client, original_path,
                localization["last_absent_target"])
            neutral = _run_neutral(
                client, neutral_path,
                localization["last_absent_target"])
            observation = _validate_observation(
                localization, positive, neutral)
    finally:
        cleanup = _clear_observers(client)

    _require(
        all(row.get("ok") is True for row in cleanup),
        "final instrumentation/controller cleanup failed")
    return {
        "schema": "abl-phase4-fmv-levelb-first-call-live/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": {
            "localization":
                "binary search with internally controlled movie.traceToFrame",
            "exact_window":
                "last-absent passive prelude, exact execute stop, bounded "
                "function/access/exec observers",
            "post_call_frames": POST_CALL_FRAMES,
            "fallback_reason":
                "scenario.runBatch cannot stage a cycle-neutral recorded-"
                "anchor prelude followed by exact instruction observers",
        },
        "capabilities": capabilities,
        "initial_status": status,
        "mounted_media": media,
        "fixtures": {
            "movie": {
                "absolute_path": str(prior.MOVIE),
                "sha256": common.sha256(prior.MOVIE),
                "bytes": prior.MOVIE.stat().st_size,
            },
            "cue": {
                "absolute_path": str(prior.CUE),
                "sha256": common.sha256(prior.CUE),
                "bytes": prior.CUE.stat().st_size,
            },
            "bin": {
                "absolute_path": str(prior.BIN),
                "sha256": common.sha256(prior.BIN),
                "bytes": prior.BIN.stat().st_size,
            },
        },
        "original_derivative": original_recipe,
        "neutral_derivative": neutral_recipe,
        "localization": localization,
        "positive": positive,
        "neutral": neutral,
        "observation": observation,
        "cleanup": cleanup,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--config-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.config_dir.is_absolute():
        raise SystemExit("--config-dir must be absolute")
    output = args.output.resolve()
    if common.ROOT == output or common.ROOT in output.parents:
        raise SystemExit("raw live output must remain outside Git")
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = collect(args.port, args.token)
    document["isolated_instance"] = {
        "config_dir": str(args.config_dir),
        "port": args.port,
        "host": "127.0.0.1",
        "transport": "ws",
        "profile_recreated": True,
        "token_retained": False,
    }
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(
        "PASS: first natural LEVEL01-B call and lifecycle -> "
        f"{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
