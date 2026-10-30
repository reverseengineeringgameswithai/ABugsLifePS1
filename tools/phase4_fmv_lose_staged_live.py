#!/usr/bin/env python3
"""Collect the staged C16 LOSE interface trace after a neutral cached replay.

This is a documented fallback for a movie whose frame-zero precise observer
changes the recorded input outcome.  ``movie.traceToFrame`` first reproduces
movie frame 300 with its internal uninstrumented/passive cached-interpreter
control.  Only then are precise access watches and temporary execution stops
armed.  Raw output must remain outside the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any

import phase4_common as common


MOVIE = Path(
    "~/Downloads/ABL/movies/Phase4/"
    "C16_gameover_continue.movie.json")
STATE = Path(
    "~/Downloads/ABL/movies/Phase4/"
    "C16_gameover_continue.movie.sav")
CUE = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).cue")
BIN = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).bin")
CLIENT = Path.home() / (
    "duckstation/scripts/debugger-client/duckstation_debug_client.py")

EXPECTED = {
    "movie_sha256":
        "39fa618a0adccf39e4dc5cf23870456594c630a179af41e8ae732ff7e61b30bf",
    "state_sha256":
        "e9c7a3b6545dffc8bc5455317b43bc58a6a1a6012e393768b64d81e22e1c1592",
    "cue_sha256":
        "463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644",
    "bin_sha256":
        "2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566",
    "binary_sha256":
        "55d589032641ad0904526742f2209c034a710a162ebba3e1bc04b4c5da6075a8",
    "source_revision": "fe0cca16b85e09a304cfde3c39669ce8c0adb8f5",
    "dirty_state_hash":
        "72dd936c8a6f92f6370815da7d9e192c3bcc2371",
}

STAGE_FRAME = 300
LOADER = 0x8003E7C0
ST_CLEAR_RING = 0x8007094C
CALLBACK_TEARDOWN = 0x800709AC
COMMON_EXIT_ST_CLEAR_CALL = 0x800B749C
COMMON_EXIT_CALLBACK_CALL = 0x800B74A4


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_client() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase4_fmv_lose_client", CLIENT)
    _require(spec is not None and spec.loader is not None,
             f"cannot load debugger client: {CLIENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _wait_for_pause(client: Any, label: str) -> dict:
    deadline = time.monotonic() + 60
    while True:
        status = client.call("debugger.status", {})
        if status.get("paused") is True:
            return status
        if time.monotonic() >= deadline:
            raise RuntimeError(f"timed out waiting for {label}")
        time.sleep(0.01)


def _registers(client: Any) -> dict[str, str]:
    return {
        str(key).lower(): value
        for key, value in client.call(
            "debugger.getRegisters", {})["registers_hex"].items()
    }


def _stop_at(client: Any, address: int, label: str) -> dict:
    client.call("debugger.runUntilAddress", {
        "address": f"0x{address:08X}"})
    status = _wait_for_pause(client, label)
    registers = _registers(client)
    _require(int(registers["pc"], 16) == address,
             f"{label}: stopped at {registers['pc']}")
    return {
        "label": label,
        "address": f"0x{address:08x}",
        "frame": status["frame"],
        "cycle": status["cycle"],
        "pc": registers["pc"].lower(),
        "ra": registers["ra"].lower(),
        "caller": f"0x{(int(registers['ra'], 16) - 8) & 0xffffffff:08x}",
        "arguments": [registers[name].lower()
                      for name in ("a0", "a1", "a2", "a3")],
        "sp": registers["sp"].lower(),
    }


def _return_from(client: Any, entry: dict, label: str) -> dict:
    address = int(entry["ra"], 16)
    result = _stop_at(client, address, label)
    registers = _registers(client)
    result["v0"] = registers["v0"].lower()
    result["v1"] = registers["v1"].lower()
    return result


def _method_present(capabilities: dict, method: str) -> bool:
    return method in (capabilities.get("methods") or {})


def collect(port: int, token: str) -> dict:
    fixture_rows = {
        "movie": (MOVIE, EXPECTED["movie_sha256"]),
        "state": (STATE, EXPECTED["state_sha256"]),
        "cue": (CUE, EXPECTED["cue_sha256"]),
        "bin": (BIN, EXPECTED["bin_sha256"]),
    }
    for label, (path, digest) in fixture_rows.items():
        _require(path.is_file() and common.sha256(path) == digest,
                 f"{label} fixture identity drifted")

    module = _load_client()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(900)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status",
        "debugger.getRegisters", "debugger.runUntilAddress",
        "debugger.clearBreakpoints", "emulator.getMediaInfo",
        "emulator.getStateInfo", "movie.traceToFrame", "movie.status",
        "accessLog.addWatch", "accessLog.clear", "capture.atomic",
        "traceCapsule.fingerprint",
    }
    missing = sorted(
        method for method in required
        if not _method_present(capabilities, method))
    _require(not missing, f"running debugger lacks methods: {missing}")
    _require(
        (capabilities.get("api") or {}).get("version") == "2.1.0" and
        (capabilities.get("api") or {}).get("schema_version") ==
        "2026-07-18" and
        (capabilities.get("binary") or {}).get("sha256") ==
        EXPECTED["binary_sha256"] and
        (capabilities.get("source") or {}).get("revision") ==
        EXPECTED["source_revision"] and
        (capabilities.get("source") or {}).get("dirty_state_hash") ==
        EXPECTED["dirty_state_hash"],
        "debugger capability identity drifted")

    media = client.call("emulator.getMediaInfo", {})
    _require(
        media.get("game_serial") == "SCUS-94288" and
        Path(str(media.get("path") or "")).resolve() == CUE.resolve(),
        f"mounted media drifted: {media}")
    state_info = client.call("emulator.getStateInfo", {
        "path": str(STATE)})
    _require(
        state_info.get("valid") is True and
        state_info.get("serial") == "SCUS-94288" and
        state_info.get("file_size") == STATE.stat().st_size,
        f"save-state inspection drifted: {state_info}")

    client.call("debugger.clearBreakpoints", {})
    client.call("accessLog.clear", {})
    stage = client.call("movie.traceToFrame", {
        "path": str(MOVIE),
        "frame": STAGE_FRAME,
        "ranges": [
            {"start": "0x8003e7c0", "end": "0x8003f000",
             "label": "fmv_loader", "max_pcs": 4096},
            {"start": "0x8004f000", "end": "0x80050400",
             "label": "resident_selector", "max_pcs": 4096},
            {"start": "0x800b6d68", "end": "0x800b752c",
             "label": "fmv_player", "max_pcs": 4096},
        ],
    }, timeout=900)
    _require(
        (stage.get("comparison") or {}).get("cycle_neutral") is True,
        f"cached stage comparison was not neutral: {stage}")
    status = client.call("movie.status", {})
    _require(
        status.get("playback_index") == STAGE_FRAME and
        status.get("reproducible") is True and
        status.get("truncated") is False,
        f"cached stage movie status drifted: {status}")
    stage_fingerprint = client.call(
        "traceCapsule.fingerprint", {}, timeout=30)

    watches = [
        client.call("accessLog.addWatch", {
            "address": "0x800CAC10", "length": 4, "type": "write",
            "label": "completion_request", "max_events": 16}),
        client.call("accessLog.addWatch", {
            "address": "0x80131EEE", "length": 2, "type": "write",
            "label": "selected_frame_limit", "max_events": 8}),
    ]

    loader_entry = _stop_at(client, LOADER, "fmv_bin_load entry")
    _require(
        loader_entry["caller"] == "0x800500d8" and
        loader_entry["arguments"][0:2] == [
            "0x0000002e", "0x00000000"],
        f"unexpected LOSE loader entry: {loader_entry}")

    ring_calls = []
    while len(ring_calls) < 4:
        entry = _stop_at(
            client, ST_CLEAR_RING,
            f"StClearRing entry {len(ring_calls) + 1}")
        returned = _return_from(
            client, entry, f"StClearRing return {len(ring_calls) + 1}")
        ring_calls.append({"entry": entry, "return": returned})
        if entry["caller"] == f"0x{COMMON_EXIT_ST_CLEAR_CALL:08x}":
            break
    _require(
        ring_calls[-1]["entry"]["caller"] ==
        f"0x{COMMON_EXIT_ST_CLEAR_CALL:08x}",
        f"common-exit StClearRing was not reached: {ring_calls}")

    callback_entry = _stop_at(
        client, CALLBACK_TEARDOWN, "callback_teardown entry")
    _require(
        callback_entry["caller"] ==
        f"0x{COMMON_EXIT_CALLBACK_CALL:08x}",
        f"unexpected callback teardown caller: {callback_entry}")
    callback_return = _return_from(
        client, callback_entry, "callback_teardown return")
    loader_return = _return_from(
        client, loader_entry, "fmv_bin_load return")
    capture = client.call("capture.atomic", {
        "trigger": "e15_c16_lose_loader_return",
        "include_registers": True,
        "trace_limit": 64,
        "memory_dumps": [
            {"label": "fmv_running_latch",
             "address": "0x80082250", "length": 4},
            {"label": "shell_substate",
             "address": "0x8008243C", "length": 4},
            {"label": "scene", "address": "0x80082504", "length": 4},
            {"label": "fmv_bin_head",
             "address": "0x800B5788", "length": 256},
            {"label": "completion_request",
             "address": "0x800CAC10", "length": 4},
            {"label": "selected_frame_limit",
             "address": "0x80131EEE", "length": 2},
        ],
    })
    final_media = client.call("emulator.getMediaInfo", {})
    client.call("accessLog.clear", {})
    client.call("debugger.clearBreakpoints", {})

    return {
        "schema": "abl-phase4-fmv-lose-staged-live/1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "method": {
            "kind": "staged_cached_control_then_precise_stops",
            "reason": (
                "The frame-zero functionTrace batch changed the movie's "
                "reproducibility. Stage the already consumed input outcome "
                "with movie.traceToFrame, then arm exact observers."),
            "stage_movie_frame": STAGE_FRAME,
        },
        "fixtures": {
            label: {"absolute_path": str(path), "sha256": digest,
                    "bytes": path.stat().st_size}
            for label, (path, digest) in fixture_rows.items()
        },
        "capabilities": capabilities,
        "mounted_media": media,
        "final_media": final_media,
        "state_inspection": state_info,
        "cached_stage": {
            "trace": stage,
            "movie_status": status,
            "fingerprint": stage_fingerprint,
        },
        "watches": watches,
        "observations": {
            "loader": {"entry": loader_entry, "return": loader_return},
            "st_clear_ring_calls": ring_calls,
            "callback_teardown": {
                "entry": callback_entry, "return": callback_return},
            "atomic_after_loader_return": capture,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if common.ROOT == output or common.ROOT in output.parents:
        raise SystemExit("raw staged live output must remain outside Git")
    document = collect(args.port, args.token)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(f"PASS: staged C16 LOSE trace -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
