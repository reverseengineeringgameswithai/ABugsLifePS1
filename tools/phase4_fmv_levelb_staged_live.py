#!/usr/bin/env python3
"""Collect the native LEVEL01-B FMV lifecycle from a pristine save anchor.

This is a documented batch fallback: the current ``scenario.runBatch`` recipe
surface cannot combine a save-state trigger with the native held/press/wait
sequence needed to cross the save UI.  The collector does not replay a full
movie.  It loads the same centrally declared save twice, re-arms all
instrumentation after each load, and compares the native input recipe with a
same-duration neutral control.
Raw output must remain outside the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import phase4_common as common


STATE = Path("~/Downloads/ABL/level01_end_of_stage.sav")
CUE = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).cue")
BIN = Path(
    "~/Downloads/ABL/"
    "Disney-Pixar A Bug's Life (v1.0).bin")
CLIENT = Path.home() / (
    "duckstation/scripts/debugger-client/duckstation_debug_client.py")

EXPECTED = {
    "state_sha256":
        "42047329754c56f6daaf413e192ba8e88ca40889714bbc9f57216f3462ed739f",
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

LOADER = 0x8003E7C0
COMPLETED_LEVEL_B_CALL = 0x8005031C
ST_CLEAR_RING = 0x8007094C
CALLBACK_TEARDOWN = 0x800709AC
COMMON_EXIT_ST_CLEAR_CALL = 0x800B749C
COMMON_EXIT_CALLBACK_CALL = 0x800B74A4
SCENE = 0x80082504
ACTION_SEQUENCE = (
    ("hold", "up", 1500),
    ("press", "cross", 10),
    ("wait", None, 400),
    ("press", "square", 10),
    ("wait", None, 1200),
    ("press", "square", 10),
    ("wait", None, 1000),
    ("press", "square", 10),
    ("wait", None, 1000),
)
CONTROL_FRAMES = sum(row[2] for row in ACTION_SEQUENCE)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load_client() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase4_fmv_levelb_client", CLIENT)
    _require(spec is not None and spec.loader is not None,
             f"cannot load debugger client: {CLIENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _method_present(capabilities: dict, method: str) -> bool:
    return method in (capabilities.get("methods") or {})


def _registers(client: Any) -> dict[str, str]:
    return {
        str(key).lower(): value
        for key, value in client.call(
            "debugger.getRegisters", {})["registers_hex"].items()
    }


def _read_u32(client: Any, address: int) -> int:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": 4})
    data = bytes.fromhex(row["hex"])
    _require(len(data) == 4, f"short read at 0x{address:08x}")
    return int.from_bytes(data, "little")


def _snapshot(client: Any, label: str) -> dict:
    status = client.call("debugger.status", {})
    registers = _registers(client)
    return {
        "label": label,
        "frame": status["frame"],
        "cycle": status["cycle"],
        "pc": registers["pc"].lower(),
        "sp": registers["sp"].lower(),
        "scene": _read_u32(client, SCENE),
    }


def _clear_observers(client: Any) -> list[dict]:
    outcomes = []
    for method, params in (
            ("debugger.clearBreakpoints", {}),
            ("accessLog.clear", {}),
            ("execTrace.clear", {}),
            ("functionTrace.stop", {}),
            ("functionTrace.clear", {}),
            ("emulator.clearControllerState", {"port": 0}),
            ("emulator.setTurbo", {"enabled": False}),
            ("emulator.setFastForward", {"enabled": False})):
        try:
            outcomes.append({
                "method": method, "ok": True,
                "result": client.call(method, params)})
        except Exception as exc:  # Cleanup is retained even for optional traces.
            outcomes.append({
                "method": method, "ok": False, "error": str(exc)})
    return outcomes


def _load_anchor(client: Any, label: str) -> tuple[dict, dict]:
    client.call("debugger.pause", {})
    _clear_observers(client)
    loaded = client.call("emulator.loadState", {
        "path": str(STATE), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False}, timeout=120)
    _require(loaded.get("loaded") is True,
             f"{label}: save did not load: {loaded}")
    # Loading invalidates non-halting watches; instrumentation is deliberately
    # armed only after this boundary.
    return loaded, _snapshot(client, label)


def _arm_levelb_observers(client: Any) -> list[dict]:
    return [
        client.call("functionTrace.start", {
            "functions": [
                f"0x{LOADER:08X}", f"0x{ST_CLEAR_RING:08X}",
                f"0x{CALLBACK_TEARDOWN:08X}"],
            "capture_memory": False, "max_events": 64}),
        client.call("accessLog.addWatch", {
            "address": "0x80131EEE", "length": 2, "type": "write",
            "label": "selected_frame_limit", "max_events": 8}),
        client.call("accessLog.addWatch", {
            "address": "0x800CAC10", "length": 4, "type": "write",
            "label": "completion_request", "max_events": 8}),
        client.call("execTrace.addWatch", {
            "pc": f"0x{COMPLETED_LEVEL_B_CALL:08X}",
            "label": "completed_level_b_call",
            "capture": ["a0", "a1", "v0", "v1", "ra", "sp"],
            "max_events": 4}),
    ]


def _advance_frames(client: Any, frames: int) -> dict:
    status = client.call("debugger.status", {})
    start = status.get("frame")
    _require(isinstance(start, int),
             f"debugger returned no frame before advance: {status}")
    return client.call("emulator.advanceToFrame", {
        "frame": start + frames, "max_frames": frames + 10}, timeout=900)


def _run_native_actions(client: Any) -> list[dict]:
    outcomes = []
    for kind, button, frames in ACTION_SEQUENCE:
        if kind == "hold":
            client.call("emulator.setControllerState", {
                "port": 0, "buttons": {button: True}})
            result = _advance_frames(client, frames)
            client.call("emulator.clearControllerState", {"port": 0})
        elif kind == "press":
            result = client.call("emulator.pressButton", {
                "button": button, "frames": frames, "port": 0,
                "release_after": True}, timeout=900)
        else:
            result = _advance_frames(client, frames)
        outcomes.append({
            "kind": kind, "button": button, "frames": frames,
            "result": result})
    return outcomes


def _capture(client: Any, trigger: str) -> dict:
    return client.call("capture.atomic", {
        "trigger": trigger,
        "include_registers": True,
        "trace_limit": 64,
        "memory_dumps": [
            {"label": "music_progress_id",
             "address": "0x8008245C", "length": 2},
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


def collect(port: int, token: str) -> dict:
    fixture_rows = {
        "state": (STATE, EXPECTED["state_sha256"]),
        "cue": (CUE, EXPECTED["cue_sha256"]),
        "bin": (BIN, EXPECTED["bin_sha256"]),
    }
    for label, (path, digest) in fixture_rows.items():
        _require(
            path.is_file() and common.sha256(path) == digest,
            f"{label} fixture identity drifted")

    module = _load_client()
    client = module.DebuggerClient("127.0.0.1", port, "ws")
    client.authenticate(token)
    client.transport.sock.settimeout(900)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status",
        "debugger.getRegisters", "debugger.readMemory",
        "debugger.clearBreakpoints", "debugger.pause",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "emulator.loadState", "emulator.advanceToFrame",
        "emulator.pressButton",
        "emulator.setControllerState", "emulator.clearControllerState",
        "accessLog.addWatch", "accessLog.clear",
        "execTrace.addWatch", "execTrace.clear", "capture.atomic",
        "functionTrace.start", "functionTrace.stop", "functionTrace.clear",
        "provenanceLog.start", "provenanceLog.get",
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

    client.call("provenanceLog.start", {"clear": True})
    positive_loaded, positive_anchor = _load_anchor(
        client, "positive_anchor")
    positive_watches = _arm_levelb_observers(client)
    positive_actions = _run_native_actions(client)
    positive_capture = _capture(
        client, "e15_levelb_native_recipe_positive")
    positive_cleanup = _clear_observers(client)

    negative_loaded, negative_anchor = _load_anchor(
        client, "neutral_anchor")
    _require(
        {
            key: positive_anchor[key]
            for key in ("frame", "cycle", "pc", "sp", "scene")
        } == {
            key: negative_anchor[key]
            for key in ("frame", "cycle", "pc", "sp", "scene")
        },
        "positive and neutral state anchors differ")
    negative_watches = _arm_levelb_observers(client)
    start_frame = negative_anchor["frame"]
    negative_run = client.call("emulator.advanceToFrame", {
        "frame": start_frame + CONTROL_FRAMES,
        "max_frames": CONTROL_FRAMES + 10}, timeout=900)
    negative_capture = _capture(
        client, "e15_levelb_neutral_after_1500_frames")
    final_media = client.call("emulator.getMediaInfo", {})
    provenance = client.call(
        "provenanceLog.get", {"offset": 0, "limit": 512})
    final_cleanup = _clear_observers(client)

    return {
        "schema": "abl-phase4-fmv-levelb-staged-live/1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "method": {
            "kind": "same_save_native_recipe_function_trace",
            "reason": (
                "scenario.runBatch cannot express the save-state held/press/"
                "wait input recipe; all bounded observers are armed only "
                "after each load"),
            "positive_actions": [
                {"kind": kind, "button": button, "frames": frames}
                for kind, button, frames in ACTION_SEQUENCE],
            "neutral_control_frames": CONTROL_FRAMES,
        },
        "fixtures": {
            label: {
                "absolute_path": str(path), "sha256": digest,
                "bytes": path.stat().st_size}
            for label, (path, digest) in fixture_rows.items()
        },
        "capabilities": capabilities,
        "mounted_media": media,
        "final_media": final_media,
        "state_inspection": state_info,
        "positive": {
            "loaded": positive_loaded,
            "anchor": positive_anchor,
            "watches": positive_watches,
            "actions": positive_actions,
            "capture": positive_capture,
            "cleanup": positive_cleanup,
        },
        "neutral_control": {
            "loaded": negative_loaded,
            "anchor": negative_anchor,
            "watches": negative_watches,
            "run": negative_run,
            "capture": negative_capture,
            "cleanup": final_cleanup,
        },
        "provenance": provenance,
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
    print(f"PASS: staged LEVEL01-B lifecycle trace -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
