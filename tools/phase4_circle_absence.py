#!/usr/bin/env python3
"""Prove the default Circle input absence from pristine static and live evidence.

The Phase-1 A20 row is deliberately narrow: with the native default controller
profile, raw Circle has no gameplay action.  This generator does not claim that
Circle can never do anything.  It proves the exact opposite boundary too: the
native profile table can remap Circle to a real action.

Static mode is always recomputed from the hash-pinned pristine executable.  Live
mode compares a neutral branch with a Circle-held branch from every strict-
pristine Phase-2 stage/lifecycle anchor, then runs profile 0 and profile 1 decoder
controls with instruction-attributed writes to the decoded action word.

Launch a fresh owned instance first, then run:

  python3 tools/phase4_circle_absence.py --config-dir /tmp/<fresh> \
    --port <dedicated> --token <ephemeral> --instance-state recreated

The generator verifies mounted media and every state before load, keeps disc
validation enabled, clears injected input/instrumentation, and stops only the PID
owned by the supplied config directory.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    from build_identity import verify_staged_input
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_circle_absence in tests
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_circle_absence.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

DECODER_START = 0x80051294
DECODER_END = 0x80051358
PROFILE_TABLE = 0x80078C28
PROFILE_COUNT = 8
PROFILE_STRIDE = 6
PROFILE_SELECTOR = 0x8009EC7D
RAW_PAD = 0x80082412
ACTION_WORD = 0x80082488
RAW_CIRCLE = 0x2000
ACTION_BITS = (0x4000, 0x8000, 0x1000)

CONTROL_ANCHOR = "level01.sav"
SETTLE_FRAMES = 2
HOLD_FRAMES = 30
RELEASE_FRAMES = 2

BLOCKS = {
    "player": (0x800A6500, 0xC0),
    "camera": (0x80095358, 0x60),
}
FIELDS = {
    "scene_id": (0x80082504, "u32"),
    "player_x": (0x800A6500, "s32"),
    "player_y": (0x800A6504, "s32"),
    "player_z": (0x800A6508, "s32"),
    "air_state": (0x800A6580, "u8"),
    "grounded": (0x800A6582, "u8"),
    "kick_timer": (0x800A657A, "s16"),
    "lives": (0x800A65A0, "u8"),
    "grain": (0x800A65A1, "u8"),
    "equipped_berry": (0x800A6597, "u8"),
    "power_word": (0x800A6590, "u8"),
}

# These words are not an inferred disassembly.  They are exact little-endian
# words at named addresses in the pinned retail executable and are mutation-
# tested by the safe suite.
EXPECTED_WORDS = {
    "profile_selector_load": (0x800512A0, 0x9042EC7D),
    "raw_pad_load": (0x800512A8, 0x94A52412),
    "profile_index_mask_0x7f": (0x800512AC, 0x3042007F),
    "profile_table_load": (0x800512C4, 0x94228C28),
    "raw_low_bits_mask_0x0fff": (0x800512C8, 0x30A60FFF),
    "decoded_base_store": (0x800512D0, 0xA4262488),
    "first_action_or_0x4000": (0x800512E0, 0x34C24000),
    "first_action_store": (0x800512E8, 0xA4222488),
    "second_action_or_0x8000": (0x80051310, 0x34428000),
    "second_action_store": (0x80051318, 0xA4222488),
    "third_action_or_0x1000": (0x80051340, 0x34421000),
    "third_action_store": (0x80051348, 0xA4222488),
    "profile_reset_store_zero": (0x8004FAF0, 0xA020EC7D),
    "profile_secondary_read": (0x80055338, 0x9042EC7D),
    "profile_high_flag_mask": (0x80055340, 0x30420080),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _va_offset(va: int) -> int:
    offset = EXE_HEADER + va - EXE_BASE
    if offset < EXE_HEADER:
        raise ValueError(f"VA precedes executable payload: 0x{va:08x}")
    return offset


def _read_word(exe: bytes, va: int) -> int:
    return struct.unpack_from("<I", exe, _va_offset(va))[0]


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    """Recompute the byte-exact decoder and native profile-table proof."""
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    instruction_words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _read_word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine decoder word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        instruction_words[name] = {
            "address": f"0x{address:08X}",
            "word": f"0x{actual:08X}",
        }

    decoder = exe[_va_offset(DECODER_START):_va_offset(DECODER_END)]
    table_bytes = exe[
        _va_offset(PROFILE_TABLE):
        _va_offset(PROFILE_TABLE) + PROFILE_COUNT * PROFILE_STRIDE]
    profiles = {}
    for profile in range(PROFILE_COUNT):
        raw_masks = list(struct.unpack_from("<HHH", table_bytes,
                                            profile * PROFILE_STRIDE))
        circle_action_bits = sum(
            action for raw, action in zip(raw_masks, ACTION_BITS)
            if raw & RAW_CIRCLE)
        profiles[str(profile)] = {
            "raw_masks": raw_masks,
            "raw_masks_hex": [f"0x{value:04X}" for value in raw_masks],
            "circle_action_bits": circle_action_bits,
            "circle_action_bits_hex": f"0x{circle_action_bits:04X}",
        }

    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}",
            "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "decoder": {
            "function_start": f"0x{DECODER_START:08X}",
            "function_end_exclusive": f"0x{DECODER_END:08X}",
            "byte_length": len(decoder),
            "sha256": _sha256_bytes(decoder),
            "instruction_words": instruction_words,
            "raw_low_bits_mask": 0x0FFF,
            "profile_selector_mask": 0x7F,
            "raw_circle_bit": RAW_CIRCLE,
            "action_output_bits": list(ACTION_BITS),
        },
        "profile_table": {
            "address": f"0x{PROFILE_TABLE:08X}",
            "profile_count": PROFILE_COUNT,
            "stride": PROFILE_STRIDE,
            "sha256": _sha256_bytes(table_bytes),
            "profiles": profiles,
        },
        "default_profile": {
            "selector_value": 0,
            "raw_masks": profiles["0"]["raw_masks"],
            "circle_action_bits": profiles["0"]["circle_action_bits"],
            "reset_writer": "0x8004FAF0 sb zero,0xEC7D(at)",
        },
        "remap_boundary": {
            "positive_profile": 1,
            "raw_masks": profiles["1"]["raw_masks"],
            "circle_action_bits": profiles["1"]["circle_action_bits"],
            "selector_readers": ["0x800512A0", "0x80055338"],
            "resident_selector_writers": ["0x8004FAF0"],
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    gaps = []
    default = census.get("default_profile") or {}
    remap = census.get("remap_boundary") or {}
    decoder = census.get("decoder") or {}
    table = census.get("profile_table") or {}
    if default.get("circle_action_bits") != 0:
        gaps.append("default profile maps raw Circle to an action bit")
    if remap.get("circle_action_bits") != 0x8000:
        gaps.append("profile 1 no longer maps raw Circle to Square action")
    if decoder.get("raw_low_bits_mask") & RAW_CIRCLE:
        gaps.append("raw Circle survives the decoder low-bit passthrough")
    if table.get("profile_count") != PROFILE_COUNT:
        gaps.append("native profile table count changed")
    if len((decoder.get("instruction_words") or {})) != len(EXPECTED_WORDS):
        gaps.append("not all decisive decoder instructions were retained")
    return gaps


def _typed_value(raw: bytes, kind: str) -> int:
    widths = {"u8": (1, False), "u16": (2, False), "s16": (2, True),
              "u32": (4, False), "s32": (4, True)}
    size, signed = widths[kind]
    return int.from_bytes(raw[:size], "little", signed=signed)


def _rpc_read(client: Any, address: int, length: int) -> bytes:
    result = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(result["hex"])


def _read_u16(client: Any, address: int) -> int:
    return _typed_value(_rpc_read(client, address, 2), "u16")


def _snapshot(client: Any) -> dict[str, Any]:
    blocks = {}
    for name, (address, length) in BLOCKS.items():
        data = _rpc_read(client, address, length)
        blocks[name] = {
            "address": f"0x{address:08X}",
            "length": length,
            "sha256": _sha256_bytes(data),
        }
    fields = {
        name: _typed_value(_rpc_read(client, address, {
            "u8": 1, "s16": 2, "u32": 4, "s32": 4}[kind]), kind)
        for name, (address, kind) in FIELDS.items()
    }
    return {"blocks": blocks, "fields": fields}


def _snapshot_differences(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    differences = []
    for name in BLOCKS:
        if left["blocks"][name]["sha256"] != right["blocks"][name]["sha256"]:
            differences.append(f"block:{name}")
    for name in FIELDS:
        if left["fields"][name] != right["fields"][name]:
            differences.append(f"field:{name}")
    return differences


def _load_anchor(client: Any, path: Path, profile: int) -> dict[str, Any]:
    loaded = client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False,
    })
    if loaded.get("loaded") is not True:
        raise SystemExit(f"state load failed for {path}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    written = client.call("debugger.writeU8", {
        "address": f"0x{PROFILE_SELECTOR:08X}", "value": profile})
    if written.get("written") != 1:
        raise SystemExit(f"profile selector write did not apply: {written}")
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return {"load": loaded, "profile_write": written}


def _branch(client: Any, path: Path, *, circle: bool) -> dict[str, Any]:
    setup = _load_anchor(client, path, 0)
    if circle:
        controller = client.call("emulator.setControllerState", {
            "port": 0, "buttons": {"circle": True}})
    else:
        controller = client.call("emulator.getControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": HOLD_FRAMES})
    during = {
        "raw_pad": _read_u16(client, RAW_PAD),
        "decoded_action_word": _read_u16(client, ACTION_WORD),
        "profile_selector": _typed_value(
            _rpc_read(client, PROFILE_SELECTOR, 1), "u8"),
        "controller": controller,
        "emulator": client.call("debugger.status", {}),
    }
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": RELEASE_FRAMES})
    return {"setup": setup, "during_hold": during,
            "after_release": _snapshot(client)}


def _decoder_control(client: Any, path: Path, profile: int) -> dict[str, Any]:
    _load_anchor(client, path, profile)
    client.call("accessLog.clear", {})
    watch = client.call("accessLog.addWatch", {
        "address": f"0x{ACTION_WORD:08X}", "length": 2, "type": "write",
        "label": f"profile_{profile}_decoded_action_word",
        "max_events": 128, "stop_on_hit": False,
    })
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"circle": True}})
    trace = client.call("accessLog.run", {"frames": 3})
    raw_pad = _read_u16(client, RAW_PAD)
    decoded = _read_u16(client, ACTION_WORD)
    selector = _typed_value(_rpc_read(client, PROFILE_SELECTOR, 1), "u8")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("accessLog.clear", {})
    events = []
    for event in trace.get("events") or []:
        instruction_pc = event.get("instruction_pc") or event.get("pc")
        if str(instruction_pc).lower() in {
                "0x800512d0", "0x800512e8", "0x80051318", "0x80051348"}:
            events.append({key: event.get(key) for key in (
                "frame", "cycle", "reported_pc", "instruction_pc", "pc",
                "instruction_word", "instruction", "width", "value",
                "new_value")})
    return {
        "profile": profile,
        "raw_pad": raw_pad,
        "decoded_action_word": decoded,
        "decoded_action_bits": decoded & 0xF000,
        "profile_selector": selector,
        "watch_id": watch.get("watch_id"),
        "watch_hit_count": trace.get("hit_count", trace.get("total")),
        "retained_events": len(trace.get("events") or []),
        "truncated": trace.get("truncated", False),
        "decoder_write_events": events,
    }


def _fixture_pins(selection: dict[str, Any]) -> dict[str, str]:
    return {row["save"]: row["sha256"] for row in selection["accepted"]}


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    methods = capabilities.get("methods") or {}
    return name in methods if isinstance(methods, dict) else name in methods


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    static_gaps = static_census_gaps(static)
    if static_gaps:
        raise SystemExit(f"static Circle census failed: {static_gaps}")

    baseline = json.loads(
        (ROOT / "analysis/phase2_stage_baseline.json").read_text())
    anchors, selection = select_pristine_save_anchors(baseline)
    if CONTROL_ANCHOR not in {save for _, save in anchors}:
        raise SystemExit(f"control anchor is not strict pristine: {CONTROL_ANCHOR}")

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.capabilities", "debugger.readMemory", "debugger.writeU8",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "accessLog.addWatch", "accessLog.run",
        "accessLog.clear",
    }
    missing_methods = sorted(
        method for method in required_methods
        if not _method_present(capabilities, method))
    if missing_methods:
        raise SystemExit(f"running debugger lacks required methods: {missing_methods}")

    inspections = []
    for _label, save in anchors:
        inspections.append(inspect_state_before_load(
            client, ROOT / save, media_identity))

    results = {}
    for index, (label, save) in enumerate(anchors, 1):
        path = ROOT / save
        neutral = _branch(client, path, circle=False)
        circle = _branch(client, path, circle=True)
        differences = _snapshot_differences(
            neutral["after_release"], circle["after_release"])
        results[label] = {
            "save": save,
            "neutral": neutral,
            "circle": circle,
            "outcome_differences": differences,
            "raw_circle_observed": bool(
                circle["during_hold"]["raw_pad"] & RAW_CIRCLE),
            "decoded_action_words_equal": (
                neutral["during_hold"]["decoded_action_word"] ==
                circle["during_hold"]["decoded_action_word"]),
            "profile_zero_observed": (
                neutral["during_hold"]["profile_selector"] == 0 and
                circle["during_hold"]["profile_selector"] == 0),
        }
        print(f"[circle] {index:02d}/{len(anchors)} {label}: "
              f"diffs={differences or 'none'} raw_circle="
              f"{results[label]['raw_circle_observed']} decoded_equal="
              f"{results[label]['decoded_action_words_equal']}")

    control_path = ROOT / CONTROL_ANCHOR
    negative_control = _decoder_control(client, control_path, 0)
    positive_control = _decoder_control(client, control_path, 1)
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("accessLog.clear", {})

    summary = {
        "anchors_requested": selection["anchors_requested"],
        "anchors_compared": len(results),
        "phase_matched_equal_anchors": sum(
            not row["outcome_differences"] for row in results.values()),
        "raw_circle_observed_anchors": sum(
            row["raw_circle_observed"] for row in results.values()),
        "decoded_equivalent_anchors": sum(
            row["decoded_action_words_equal"] for row in results.values()),
        "profile_zero_anchors": sum(
            row["profile_zero_observed"] for row in results.values()),
        "differing_labels": sorted(
            label for label, row in results.items()
            if row["outcome_differences"]),
        "raw_circle_missing_labels": sorted(
            label for label, row in results.items()
            if not row["raw_circle_observed"]),
        "decoded_difference_labels": sorted(
            label for label, row in results.items()
            if not row["decoded_action_words_equal"]),
    }
    expected_count = len(results)
    if any(summary[key] != expected_count for key in (
            "phase_matched_equal_anchors", "raw_circle_observed_anchors",
            "decoded_equivalent_anchors", "profile_zero_anchors")):
        raise SystemExit(f"Circle breadth evidence diverged: {summary}")
    if negative_control["decoded_action_bits"] != 0:
        raise SystemExit(f"profile-0 negative control decoded an action: {negative_control}")
    if positive_control["decoded_action_bits"] != 0x8000:
        raise SystemExit(f"profile-1 positive control missed Square action: {positive_control}")
    if negative_control["truncated"] or positive_control["truncated"]:
        raise SystemExit("decoder access trace truncated")

    run_provenance = finish_run(
        args, generator="tools/phase4_circle_absence.py",
        anchor={
            "type": "hash-verified pristine save-state breadth sweep",
            "saves": [save for _label, save in anchors],
            "fixture_sha256": _fixture_pins(selection),
            "state_inspections": inspections,
            "selection": selection,
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100,
            "cd_read_speedup": 1,
            "cd_seek_speedup": 1,
            "rewind": False,
            "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "hold_frames": HOLD_FRAMES,
            "release_frames": RELEASE_FRAMES,
            "input": {"port": 0, "buttons": {"circle": True}},
        },
    )

    document = {
        "_comment": (
            "Phase-4 A20 proof. Static bytes show that the default profile omits "
            "raw Circle while native remap profile 1 maps it to Square. Live "
            "phase-matched controls compare default-profile Circle against neutral "
            "input across every strict-pristine Phase-2 stage/lifecycle anchor. "
            "Regenerate with tools/phase4_circle_absence.py in a fresh owned instance."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "summary": summary,
            "anchor_results": results,
            "negative_control": negative_control,
            "positive_control": positive_control,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[circle] retained {len(results)} phase-matched anchors; "
          "profile0=0x0000 profile1=0x8000; output={OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        # A failed experiment must not strand its isolated emulator.  The
        # shared helper proves config ownership and stops only that exact PID.
        try:
            finish_run(
                args, generator="tools/phase4_circle_absence.py",
                anchor={"type": "aborted before retained evidence"},
                timing={},
            )
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
