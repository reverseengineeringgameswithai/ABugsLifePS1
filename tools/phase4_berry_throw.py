#!/usr/bin/env python3
"""Regenerate the Phase-4 A08 berry-throw campaign from pristine retail evidence.

The proof joins hash-pinned resident input/dispatch/projectile bytes to a
from-boot Square counterfactual, exact gate and selector controls, all-gameplay
anchor breadth, straight and homing lifecycles, pause/respawn behavior, and
instruction-attributed native execution.
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
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_berry_throw.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
ACTION_WORD = 0x80082488
PREVIOUS_PAD = 0x80082380
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
POOL_BASE = 0x800B0D18
POOL_STRIDE = 0x38
POOL_CAPACITY = 64
POOL_CURSOR = 0x8008234C
TYPE_TABLE = 0x8007941C
LIVE_ACTOR_RECORD = 0x8009FE04

SQUARE_MASK = 0x8000
THROW_WINDUP = 18
THROW_DISPATCH_AT = 10
GRAVITY = 128
SELECTOR_TYPES = {0: 2, 1: 5, 2: 8, 3: 11, 4: 45}
HOMING_TRANSITIONS = {8: 16, 45: 48}
TYPE_NAMES = {
    2: "red", 5: "blue", 8: "homing_primary", 11: "gold",
    16: "homing_projectile", 45: "mega_primary", 48: "mega_projectile",
}
CONTROL_ANCHOR = "red_berry.sav"
ARC_ANCHOR = "red_berry_thrown.sav"
HOMING_ANCHORS = {2: "homing_berry.sav", 4: "mega_homing_berry.sav"}
RESPAWN_ANCHOR = "level02.sav"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8550
MOVIE_EDIT_END = 8621
MOVIE_SQUARE_START = 8558
MOVIE_SQUARE_END = 8562
MOVIE_OBSERVE_FRAME = 8620
SETTLE_FRAMES = 2

REGIONS = {
    "throw_gate": (0x80048FB8, 0x8004909C),
    "aim_helper": (0x80046D24, 0x800470AC),
    "throw_dispatch": (0x800470AC, 0x80047284),
    "contact_spawn": (0x8005A0E0, 0x8005A308),
    "projectile_update": (0x8005A308, 0x8005B12C),
    "projectile_cleanup": (0x8005953C, 0x80059E44),
}

EXPECTED_WORDS = {
    "decoded_action_load": (0x80048FBC, 0x84422488),
    "square_mask": (0x80048FC4, 0x30428000),
    "square_required": (0x80048FC8, 0x1040002E),
    "previous_pad_load": (0x80048FD4, 0x84422380),
    "fresh_square_mask": (0x80048FDC, 0x30428000),
    "fresh_square_required": (0x80048FE0, 0x14400028),
    "windup_load": (0x80048FE8, 0x86220086),
    "windup_lt_7": (0x80048FF0, 0x28420007),
    "in_flight_load": (0x80048FFC, 0x92220096),
    "in_flight_lt_4": (0x80049004, 0x2C420004),
    "special_mode_load": (0x80049010, 0x922200A3),
    "shared_timer_load": (0x80049024, 0x8442657A),
    "animation_load": (0x80049034, 0x86230088),
    "gate_9e_lt_12": (0x8004904C, 0x2842000C),
    "vertical_aux_load": (0x80049070, 0x86220084),
    "windup_18_writer": (0x80049080, 0xA6220086),
    "dispatch_at_10": (0x80049088, 0x2402000A),
    "dispatch_call": (0x80049094, 0x0C011C2B),
    "equipped_selector_load": (0x80047170, 0x92030097),
    "selector_lt_5": (0x80047178, 0x2C620005),
    "red_type_2": (0x800471A4, 0x24110002),
    "blue_type_5": (0x800471B0, 0x24110005),
    "homing_type_8": (0x800471B8, 0x24110008),
    "gold_type_11": (0x800471C4, 0x2411000B),
    "mega_type_45": (0x800471C8, 0x2411002D),
    "homing_vertical_minus_2048": (0x800471CC, 0x2408F800),
    "in_flight_increment": (0x800471DC, 0xA2020096),
    "gravity_128": (0x80047220, 0x24020080),
    "type_stack_store": (0x80047228, 0xAFB1001C),
    "spawn_call": (0x8004724C, 0x0C016838),
    "throw_sfx_2": (0x80047254, 0x24040002),
    "sfx_call": (0x80047258, 0x0C014113),
    "allocator_wrap_64": (0x8005A114, 0x28420040),
    "allocator_occupied_mask": (0x8005A150, 0x30420080),
    "respawn_in_flight_clear": (0x8005B304, 0xA0206596),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "heading", "offset": 0x20, "type": "u32"},
    {"name": "shared_timer", "offset": 0x7A, "type": "s16"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "s16"},
    {"name": "vertical_aux", "offset": 0x84, "type": "s16"},
    {"name": "throw_windup", "offset": 0x86, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "health", "offset": 0x94, "type": "s16"},
    {"name": "berries_in_flight", "offset": 0x96, "type": "u8"},
    {"name": "equipped_berry", "offset": 0x97, "type": "u8"},
    {"name": "gate_9e", "offset": 0x9E, "type": "u16"},
    {"name": "lives", "offset": 0xA0, "type": "u8"},
    {"name": "special_mode", "offset": 0xA3, "type": "u8"},
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _va_offset(address: int) -> int:
    return EXE_HEADER + address - EXE_BASE


def _word(exe: bytes, address: int) -> int:
    return struct.unpack_from("<I", exe, _va_offset(address))[0]


def _region(exe: bytes, bounds: tuple[int, int]) -> bytes:
    return exe[_va_offset(bounds[0]):_va_offset(bounds[1])]


def _type_descriptor(exe: bytes, type_id: int) -> dict[str, Any]:
    data = exe[_va_offset(TYPE_TABLE + type_id * 20):
               _va_offset(TYPE_TABLE + (type_id + 1) * 20)]
    return {
        "type": type_id, "name": TYPE_NAMES[type_id], "raw_hex": data.hex(),
        "record_fields": {
            "field_20": struct.unpack_from("<H", data, 0)[0],
            "lifetime_ttl": struct.unpack_from("<H", data, 2)[0],
            "model_or_asset": struct.unpack_from("<h", data, 4)[0],
            # The allocator copies descriptor +7 to record +0x30 and +6 to
            # record +0x31; retain record-relative names here.
            "field_30": data[7], "field_31": data[6],
            "field_28": struct.unpack_from("<H", data, 8)[0],
            "field_2a": struct.unpack_from("<H", data, 10)[0],
            "field_2c": struct.unpack_from("<H", data, 12)[0],
            "orientation_mode": struct.unpack_from("<b", data, 14)[0],
            "field_2f": data[15], "flags": data[16],
            "field_34": data[17], "field_35": data[18],
            "field_36": data[19],
        },
    }


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine berry word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in REGIONS.items():
        data = _region(exe, bounds)
        regions[name] = {
            "start": f"0x{bounds[0]:08X}",
            "end_exclusive": f"0x{bounds[1]:08X}",
            "length": len(data), "sha256": _sha256_bytes(data),
        }
    table = [_word(exe, 0x8001B1C0 + index * 4) for index in range(5)]
    expected_table = [0x8004719C, 0x800471A8, 0x800471B4,
                      0x800471BC, 0x800471C8]
    if table != expected_table:
        raise SystemExit(f"pristine berry jump table changed: {table}")
    descriptors = {str(type_id): _type_descriptor(exe, type_id)
                   for type_id in TYPE_NAMES}
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "regions": regions, "instruction_words": words,
        "selector_jump_table": {
            "address": "0x8001B1C0",
            "entries": [f"0x{value:08X}" for value in table],
            "selector_to_type": {str(k): v for k, v in SELECTOR_TYPES.items()},
        },
        "type_descriptors": descriptors,
        "law": {
            "square_mask": SQUARE_MASK, "fresh_press_required": True,
            "windup_arm": THROW_WINDUP,
            "dispatch_value": THROW_DISPATCH_AT,
            "windup_arm_max_exclusive": 7,
            "in_flight_max_exclusive": 4,
            "gate_9e_max_exclusive": 12,
            "shared_timer_required": 0,
            "vertical_aux_required": 0,
            "special_mode_required": 0,
            "blocked_animations": [8, 10, 13, 17],
            "straight_selectors_using_aim_helper": [0, 1, 3],
            "fixed_heading_selectors": [2, 4],
            "fixed_vertical_velocity": -2048,
            "gravity_per_projectile_update": GRAVITY,
            "initial_horizontal_velocity": "3 * (signed 12-bit LUT sample >> 4)",
            "spawn_y_offset": -12800,
            "throw_sfx": 2,
            "pool": {"base": "0x800B0D18", "stride": 56,
                     "capacity": 64, "cursor": "0x8008234C",
                     "allocation": "round-robin free-slot search; no full-pool escape"},
            "homing_transitions": {str(k): v for k, v in HOMING_TRANSITIONS.items()},
            "homing_target_table": "0x80090748",
            "homing_target_filter": "flags bit 0x1 set and flags 0xA0 clear; nearest squared XZ distance",
        },
        "writer_inventory": [
            {"address": "0x80049080", "role": "throw windup := 18"},
            {"address": "0x800471DC", "role": "in-flight increment after valid selector"},
            {"address": "0x800595C8..0x80059930", "role": "type-specific projectile retirement decrements"},
            {"address": "0x8005B304", "role": "native respawn in-flight clear"},
            {"address": "0x80057424", "role": "gameplay contact-pool/cursor reset"},
        ],
        "source_status": {
            "input": "asm/hand_written/80048138_player_vertical_update.s (byte-matched build unit)",
            "dispatch": "asm/hand_written/800470ac_berry_throw_dispatch.s (byte-matched build unit)",
            "spawn": "asm/hand_written/8005a0f0_contact_object_spawn.s plus full-entry pristine prologue",
            "update": "asm/hand_written/8005a308_berry_projectile_update.s (byte-matched build unit)",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    for key, expected, message in (
        ("square_mask", SQUARE_MASK, "berry action mask is not Square 0x8000"),
        ("windup_arm", 18, "berry windup does not arm at 18"),
        ("dispatch_value", 10, "berry dispatch does not occur at windup 10"),
        ("in_flight_max_exclusive", 4, "berry in-flight gate is not exclusive 4"),
        ("gravity_per_projectile_update", 128, "berry gravity is not 128 per native update"),
    ):
        if law.get(key) != expected:
            gaps.append(message)
    if census.get("selector_jump_table", {}).get("selector_to_type") != {
            str(k): v for k, v in SELECTOR_TYPES.items()}:
        gaps.append("selector/type map is incomplete")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive berry instruction census is incomplete")
    if set((census.get("type_descriptors") or {})) != {str(v) for v in TYPE_NAMES}:
        gaps.append("native primary/secondary descriptor census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(row["hex"])


def _read_u8(client: Any, address: int) -> int:
    return _read_memory(client, address, 1)[0]


def _read_u32(client: Any, address: int) -> int:
    return int.from_bytes(_read_memory(client, address, 4), "little")


def _snapshot(client: Any) -> dict[str, Any]:
    result = client.call("debugger.readStruct", {
        "base": f"0x{PLAYER_BASE:08X}", "fields": PLAYER_FIELDS})
    fields = {}
    for row in result.get("fields") or []:
        if row.get("valid") is not True:
            raise SystemExit(f"invalid player field read: {row}")
        fields[row["name"]] = row["value"]
    status = client.call("debugger.status", {})
    return {
        "fields": fields,
        "player_block_sha256": _sha256_bytes(
            _read_memory(client, PLAYER_BASE, PLAYER_SIZE)),
        "working_actions": int.from_bytes(
            _read_memory(client, ACTION_WORD, 2), "little"),
        "previous_pad": int.from_bytes(
            _read_memory(client, PREVIOUS_PAD, 2), "little"),
        "pause_flag": int.from_bytes(
            _read_memory(client, PAUSE_FLAG, 2), "little"),
        "scene": _read_u32(client, SCENE_WORD),
        "pool_cursor": _read_u32(client, POOL_CURSOR),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _record_from_data(pointer: int, data: bytes) -> dict[str, Any]:
    if not (POOL_BASE <= pointer < POOL_BASE + POOL_CAPACITY * POOL_STRIDE) or \
            (pointer - POOL_BASE) % POOL_STRIDE:
        raise SystemExit(f"spawn returned non-pool pointer 0x{pointer:08X}")
    return {
        "pointer": f"0x{pointer:08X}",
        "slot": (pointer - POOL_BASE) // POOL_STRIDE,
        "position": list(struct.unpack_from("<iii", data, 0)),
        "velocity": list(struct.unpack_from("<iii", data, 0x0C)),
        "gravity": struct.unpack_from("<h", data, 0x18)[0],
        "field_20": struct.unpack_from("<H", data, 0x20)[0],
        "lifetime_ttl": struct.unpack_from("<H", data, 0x22)[0],
        "model_or_asset": struct.unpack_from("<h", data, 0x24)[0],
        "field_28": struct.unpack_from("<H", data, 0x28)[0],
        "field_2a": struct.unpack_from("<H", data, 0x2A)[0],
        "field_2c": struct.unpack_from("<H", data, 0x2C)[0],
        "orientation": struct.unpack_from("<b", data, 0x2E)[0],
        "field_2f": data[0x2F], "field_30": data[0x30],
        "field_31": data[0x31], "flags": data[0x33],
        "field_34": data[0x34], "field_35": data[0x35],
        "field_36": data[0x36], "record_sha256": _sha256_bytes(data),
    }


def _record_snapshot(client: Any, pointer: int) -> dict[str, Any]:
    return _record_from_data(pointer, _read_memory(client, pointer, POOL_STRIDE))


def _descriptor_type(record: dict[str, Any], static: dict[str, Any]) -> int | None:
    keys = ("field_20", "model_or_asset", "field_28", "field_2a",
            "field_2c", "field_2f", "field_30", "field_31", "flags",
            "field_34", "field_35", "field_36")
    for raw, descriptor in static["type_descriptors"].items():
        fields = descriptor["record_fields"]
        if all(record[key] == fields[key] for key in keys):
            return int(raw)
    return None


def _active_descriptor_records(client: Any, static: dict[str, Any],
                               wanted: set[int]) -> list[dict[str, Any]]:
    data = _read_memory(client, POOL_BASE, POOL_CAPACITY * POOL_STRIDE)
    rows = []
    for slot in range(POOL_CAPACITY):
        start = slot * POOL_STRIDE
        record = _record_from_data(
            POOL_BASE + start, data[start:start + POOL_STRIDE])
        type_id = _descriptor_type(record, static)
        if type_id in wanted and record["lifetime_ttl"] > 0:
            rows.append({"type": type_id, "record": record})
    return rows


def _load_anchor(client: Any, path: Path) -> dict[str, Any]:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False,
    })
    if loaded.get("loaded") is not True:
        raise SystemExit(f"state load failed: {path}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return loaded


def _checked_write(client: Any, method: str, address: int,
                   value: int) -> dict[str, Any]:
    row = client.call(method, {"address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU8": 1, "debugger.writeU16": 2,
                "debugger.writeU32": 4}[method]
    if row.get("written") != expected:
        raise SystemExit(f"debugger write did not apply: {method}: {row}")
    return row


def _set_player_position(client: Any, xyz: tuple[int, int, int]) -> list[dict]:
    writes = []
    for offset, value in zip((0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                             (*xyz, *xyz)):
        writes.append(_checked_write(
            client, "debugger.writeU32", PLAYER_BASE + offset,
            value & 0xFFFFFFFF))
    return writes


def _trace_get(client: Any, watch: dict[str, Any], limit: int = 64) -> dict[str, Any]:
    return client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": limit})


def _throw(client: Any, *, require_spawn: bool = True,
           extra_neutral: int = 64) -> dict[str, Any]:
    client.call("execTrace.clear", {})
    specs = [
        ("arm", 0x80049080, ["v0", "s1"]),
        ("dispatch", 0x80049094, ["a0", "s1"]),
        ("aim", 0x80046D24, ["a0", "a1", "a2", "a3"]),
        ("type_store", 0x80047228, ["s1"]),
        ("spawn_return", 0x80047254, ["v0", "s1"]),
        ("sfx", 0x8005044C, ["a0", "a1"]),
    ]
    watches = {label: client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture,
        "label": label, "max_events": 64})
        for label, pc, capture in specs}
    before = _snapshot(client)
    attempts = 0
    for attempts in range(1, 7):
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": {"square": True}})
        client.call("emulator.advanceFrames", {"frames": 4})
        client.call("emulator.clearControllerState", {"port": 0})
        client.call("emulator.advanceFrames", {"frames": 12})
        if _trace_get(client, watches["spawn_return"])["events"]:
            break
    if not _trace_get(client, watches["spawn_return"])["events"] and extra_neutral:
        client.call("emulator.advanceFrames", {"frames": extra_neutral})
    traces = {label: _trace_get(client, watch) for label, watch in watches.items()}
    after = _snapshot(client)
    events = traces["spawn_return"]["events"]
    result = {"before": before, "after": after, "attempts": attempts,
              "execution": traces}
    if events:
        pointer = int(events[0]["regs"]["v0"], 16)
        result["spawn_pointer"] = f"0x{pointer:08X}"
        result["spawn_record"] = _record_snapshot(client, pointer)
    if require_spawn:
        if len(events) != 1 or any(row.get("truncated") for row in traces.values()):
            raise SystemExit(f"berry throw did not produce one non-truncated spawn: {result}")
        type_events = traces["type_store"]["events"]
        sfx2 = [row for row in traces["sfx"]["events"]
                if int(row["regs"]["a0"], 16) == 2]
        if len(type_events) != 1 or not sfx2:
            raise SystemExit(f"berry throw lacked type/SFX attribution: {result}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("execTrace.clear", {})
    return result


def _run_gate_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR

    def trial(label: str, writes: list[tuple[str, int, int]]) -> dict[str, Any]:
        _load_anchor(client, path)
        applied = [_checked_write(client, method, PLAYER_BASE + offset, value)
                   for method, offset, value in writes]
        client.call("execTrace.clear", {})
        watch = client.call("execTrace.addWatch", {
            "pc": "0x80049080", "capture": ["v0", "s1"],
            "label": label, "max_events": 8})
        before = _snapshot(client)
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": {"square": True}})
        client.call("emulator.advanceFrames", {"frames": 12})
        after = _snapshot(client)
        trace = _trace_get(client, watch, 8)
        client.call("emulator.clearControllerState", {"port": 0})
        return {"writes": applied, "before": before, "after": after,
                "arm_trace": trace}

    cases = {
        "in_flight_3_allows": trial("in_flight_3_allows", [
            ("debugger.writeU8", 0x96, 3)]),
        "in_flight_4_blocks": trial("in_flight_4_blocks", [
            ("debugger.writeU8", 0x96, 4)]),
        "special_mode_blocks": trial("special_mode_blocks", [
            ("debugger.writeU8", 0xA3, 1)]),
        "shared_timer_blocks": trial("shared_timer_blocks", [
            ("debugger.writeU16", 0x7A, 12)]),
        "vertical_aux_blocks": trial("vertical_aux_blocks", [
            ("debugger.writeU16", 0x84, 1)]),
        "gate_9e_11_allows": trial("gate_9e_11_allows", [
            ("debugger.writeU16", 0x9E, 11)]),
        "gate_9e_12_blocks": trial("gate_9e_12_blocks", [
            ("debugger.writeU16", 0x9E, 12)]),
    }
    _load_anchor(client, path)
    writes = [_checked_write(client, "debugger.writeU8", PLAYER_BASE + 0xA3, 1)]
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"square": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    blocked_held = _snapshot(client)
    writes.append(_checked_write(client, "debugger.writeU8", PLAYER_BASE + 0xA3, 0))
    client.call("emulator.advanceFrames", {"frames": 12})
    still_held = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": 4})
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"square": True}})
    client.call("emulator.advanceFrames", {"frames": 12})
    fresh_after_release = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    cases["fresh_edge"] = {
        "writes": writes, "blocked_while_first_held": blocked_held,
        "blocker_cleared_while_still_held": still_held,
        "fresh_after_release": fresh_after_release,
    }

    # Windup and animation are written earlier in the same native controller
    # update, so save-state pokes at those fields are not stable causal inputs.
    # Their exact gates remain opcode-pinned above; live controls perturb only
    # fields that survive to the decision point.
    allow = ("in_flight_3_allows", "gate_9e_11_allows")
    block = tuple(key for key in cases if key not in allow and key != "fresh_edge")
    if any(not cases[key]["arm_trace"]["events"] or
           cases[key]["after"]["fields"]["throw_windup"] <= 0
           for key in allow):
        raise SystemExit(f"berry positive gate boundary failed: {cases}")
    if any(cases[key]["arm_trace"]["events"] or
           cases[key]["after"]["fields"]["throw_windup"] == THROW_WINDUP
           for key in block):
        raise SystemExit(f"berry negative gate boundary failed: {cases}")
    edge = cases["fresh_edge"]
    if edge["blocked_while_first_held"]["fields"]["throw_windup"] != 0 or \
            edge["blocker_cleared_while_still_held"]["fields"]["throw_windup"] != 0 or \
            edge["fresh_after_release"]["fields"]["throw_windup"] <= 0:
        raise SystemExit(f"berry fresh-edge control failed: {edge}")
    return {"cases": cases, "allow_cases": list(allow),
            "block_cases": list(block)}


def _run_selector_matrix(client: Any, static: dict[str, Any]) -> dict[str, Any]:
    trials = {}
    for selector, expected_type in SELECTOR_TYPES.items():
        _load_anchor(client, ROOT / ARC_ANCHOR)
        write = _checked_write(
            client, "debugger.writeU8", PLAYER_BASE + 0x97, selector)
        result = _throw(client)
        type_event = result["execution"]["type_store"]["events"][0]
        actual_type = int(type_event["regs"]["s1"], 16)
        descriptor_type = _descriptor_type(result["spawn_record"], static)
        aim_hits = result["execution"]["aim"]["total"]
        trials[str(selector)] = {
            "selector_write": write, "expected_type": expected_type,
            "actual_type": actual_type, "descriptor_type": descriptor_type,
            "aim_helper_hits": aim_hits, **result,
        }
        if actual_type != expected_type or descriptor_type != expected_type or \
                (aim_hits > 0) != (selector in (0, 1, 3)):
            raise SystemExit(f"berry selector trial failed: {trials[str(selector)]}")
    return {"anchor": ARC_ANCHOR, "trials": trials,
            "selector_type_pairs": [[int(key), row["actual_type"]]
                                    for key, row in trials.items()]}


def _run_arc_and_lifecycle(client: Any, static: dict[str, Any]) -> dict[str, Any]:
    _load_anchor(client, ROOT / ARC_ANCHOR)
    _checked_write(client, "debugger.writeU8", PLAYER_BASE + 0x97, 0)
    thrown = _throw(client)
    pointer = int(thrown["spawn_pointer"], 16)
    samples = [thrown["spawn_record"]]
    for _ in range(80):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _record_snapshot(client, pointer)
        if (row["position"], row["velocity"], row["lifetime_ttl"]) != (
                samples[-1]["position"], samples[-1]["velocity"],
                samples[-1]["lifetime_ttl"]):
            samples.append(row)
        if len(samples) >= 12:
            break
    laws = []
    for before, after in zip(samples, samples[1:]):
        laws.append({
            "delta_position": [after["position"][i] - before["position"][i]
                               for i in range(3)],
            "delta_velocity_y": after["velocity"][1] - before["velocity"][1],
            "ttl_delta": after["lifetime_ttl"] - before["lifetime_ttl"],
        })
    if len(samples) < 8 or any(
            row["delta_position"][0] != samples[i]["velocity"][0] or
            row["delta_position"][2] != samples[i]["velocity"][2] or
            row["delta_velocity_y"] != GRAVITY or
            row["delta_position"][1] != samples[i]["velocity"][1] or
            row["ttl_delta"] != -1
            for i, row in enumerate(laws)):
        raise SystemExit(f"straight berry integration law failed: {samples} {laws}")

    flow = []
    retired = None
    for frame in range(1, 401):
        client.call("emulator.advanceFrames", {"frames": 1})
        if frame % 10 == 0:
            flow.append({"elapsed_frames": frame,
                         "record": _record_snapshot(client, pointer),
                         "player": _snapshot(client)})
        record = _record_snapshot(client, pointer)
        if record["lifetime_ttl"] == 0 and \
                _snapshot(client)["fields"]["berries_in_flight"] == 0:
            retired = {"elapsed_frames": frame, "record": record,
                       "player": _snapshot(client)}
            break
    if retired is None:
        raise SystemExit("straight berry did not retire and release in-flight ownership")
    return {"throw": thrown, "samples": samples,
            "per_update_deltas": laws, "retirement_flow": flow,
            "retired": retired}


def _run_homing_transitions(client: Any, static: dict[str, Any]) -> dict[str, Any]:
    results = {}
    for selector, primary in ((2, 8), (4, 45)):
        _load_anchor(client, ROOT / HOMING_ANCHORS[selector])
        _checked_write(client, "debugger.writeU8", PLAYER_BASE + 0x97, selector)
        client.call("execTrace.clear", {})
        acquisition = client.call("execTrace.addWatch", {
            "pc": "0x8005743C", "capture": ["a0", "a1"],
            "label": "homing_acquisition", "max_events": 64})
        thrown = _throw(client)
        # _throw clears its own watches, so re-arm the acquisition owner after
        # the primary spawn, as required after every instrumentation reset.
        client.call("execTrace.clear", {})
        acquisition = client.call("execTrace.addWatch", {
            "pc": "0x8005743C", "capture": ["a0", "a1"],
            "label": "homing_acquisition", "max_events": 64})
        secondary_return_pc = {2: 0x80057584, 4: 0x80057540}[selector]
        secondary_return = client.call("execTrace.addWatch", {
            "pc": f"0x{secondary_return_pc:08X}", "capture": ["v0", "s0", "s2"],
            "label": "secondary_spawn_return", "max_events": 16})
        pointer = int(thrown["spawn_pointer"], 16)
        primary_record = _record_snapshot(client, pointer)
        secondary_type = HOMING_TRANSITIONS[primary]
        timeline = [{"elapsed_frames": 0, "primary": primary_record,
                     "in_flight": _read_u8(client, PLAYER_BASE + 0x96)}]
        secondary_spawn = None
        retired = None
        for frame in range(1, 401):
            client.call("emulator.advanceFrames", {"frames": 1})
            record = _record_snapshot(client, pointer)
            secondary_trace = _trace_get(client, secondary_return, 16)
            if secondary_trace["events"] and secondary_spawn is None:
                event = secondary_trace["events"][0]
                secondary_pointer = int(event["regs"]["v0"], 16)
                secondary_spawn = {
                    "elapsed_frames": frame, "type": secondary_type,
                    "return_pc": f"0x{secondary_return_pc:08X}",
                    "event": event,
                    "record_after_native_update": _record_snapshot(
                        client, secondary_pointer),
                }
            if secondary_spawn is not None or frame % 20 == 0:
                timeline.append({"elapsed_frames": frame, "primary": record,
                                 "in_flight": _read_u8(
                                     client, PLAYER_BASE + 0x96)})
            if record["lifetime_ttl"] == 0 and \
                    _read_u8(client, PLAYER_BASE + 0x96) == 0:
                retired = {"elapsed_frames": frame, "record": record,
                           "in_flight": 0}
                break
        trace = _trace_get(client, acquisition)
        secondary_trace = _trace_get(client, secondary_return, 16)
        result = {"selector": selector, "primary_type": primary,
                  "secondary_type": HOMING_TRANSITIONS[primary],
                  "throw": thrown, "timeline": timeline,
                  "secondary_spawn": secondary_spawn, "retired": retired,
                  "acquisition_trace": trace,
                  "secondary_spawn_trace": secondary_trace}
        if _descriptor_type(primary_record, static) != primary or \
                secondary_spawn is None or \
                retired is None or not trace["events"] or trace["truncated"]:
            raise SystemExit(f"homing primary/secondary lifecycle failed: {result}")
        results[str(selector)] = result
        client.call("execTrace.clear", {})
    return results


def _run_pause(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / ARC_ANCHOR)
    _checked_write(client, "debugger.writeU8", PLAYER_BASE + 0x97, 0)
    thrown = _throw(client)
    pointer = int(thrown["spawn_pointer"], 16)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused = {"player": _snapshot(client),
              "record": _record_snapshot(client, pointer)}
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = {"player": _snapshot(client),
              "record": _record_snapshot(client, pointer)}
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    client.call("emulator.clearControllerState", {"port": 0})
    resumed = {"player": _snapshot(client),
               "record": _record_snapshot(client, pointer)}
    if paused["player"]["pause_flag"] != 1 or \
            frozen["player"]["pause_flag"] != 1 or \
            paused["record"]["record_sha256"] != frozen["record"]["record_sha256"] or \
            resumed["player"]["pause_flag"] != 0 or \
            resumed["record"]["record_sha256"] == frozen["record"]["record_sha256"]:
        raise SystemExit(f"berry pause/resume failed: {paused} {frozen} {resumed}")
    return {"throw": thrown, "paused": paused, "frozen": frozen,
            "resumed": resumed}


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = []
    for label, save in anchors:
        _load_anchor(client, ROOT / save)
        result = _throw(client, require_spawn=False, extra_neutral=96)
        rows.append({"label": label, "save": save, **result})
    spawned = [row["label"] for row in rows
               if row["execution"]["spawn_return"]["events"]]
    blocked = [row["label"] for row in rows if row["label"] not in spawned]
    bonus2 = next(row for row in rows if row["label"] == "bonus2_mushrooms")
    if len(rows) != 19 or len(spawned) != 18 or blocked != ["bonus2_mushrooms"] or \
            bonus2["execution"]["arm"]["events"]:
        raise SystemExit(f"berry gameplay breadth changed: {spawned} {blocked}")
    return {"trials": rows, "summary": {
        "anchors_compared": len(rows), "spawned_labels": spawned,
        "blocked_labels": blocked,
        "bonus2_initial_animation": bonus2["before"]["fields"]["animation"],
        "bonus2_final_animation": bonus2["after"]["fields"]["animation"],
        "bonus2_final_windup": bonus2["after"]["fields"]["throw_windup"],
        "riverbed_flight_spawned": "stage14_riverbed_flight" in spawned,
    }}


def _run_respawn(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / RESPAWN_ANCHOR)
    thrown = _throw(client)
    actor_id, x, y, z = struct.unpack(
        "<Iiii", _read_memory(client, LIVE_ACTOR_RECORD, 16))
    writes = [
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0),
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x86, 5),
        _checked_write(client, "debugger.writeU8", PLAYER_BASE + 0x96, 3),
    ]
    writes.extend(_set_player_position(client, (x, y, z)))
    before = _snapshot(client)
    flow, respawn = [], None
    for _ in range(8):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        if row["fields"]["lives"] == before["fields"]["lives"] - 1 and \
                row["fields"]["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit("native respawn did not complete during berry lifecycle control")
    fresh = _throw(client)
    result = {"anchor": RESPAWN_ANCHOR, "initial_throw": thrown,
              "actor": {"id": actor_id, "x": x, "y": y, "z": z},
              "writes": writes, "before": before, "flow": flow,
              "respawn": respawn, "fresh_post_respawn_throw": fresh}
    if before["fields"]["berries_in_flight"] != 3 or \
            respawn["fields"]["berries_in_flight"] != 0 or \
            respawn["fields"]["throw_windup"] != 0 or \
            respawn["scene"] != before["scene"]:
        raise SystemExit(f"berry state did not reset/rearm across respawn: {result}")
    return result


def _verify_base_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / BASE_MOVIE
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(BASE_MOVIE)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot berry movie lacks an exact central pin: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("LEVEL01 berry control is not a v3 from-boot movie")
    frames = movie.get("frames") or []
    if MOVIE_EDIT_END > len(frames):
        raise SystemExit("berry edit window exceeds base movie")
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((frames[index].get("ports") or {}).get("0") or {})
        if any(pad.get(button) for button in (
                "l2", "r2", "cross", "circle", "square", "triangle",
                "start", "select")):
            raise SystemExit(f"berry movie window is no longer action-neutral at {index}")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _movie_cleanup(client: Any, registry_ids: list[str] | None = None) -> None:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    for movie_id in reversed(registry_ids or []):
        try:
            client.call("movie.remove", {"movieId": movie_id})
        except Exception:
            pass
    try:
        client.call("movie.clear", {})
    except Exception:
        pass


def _run_cold_boot(client: Any, static: dict[str, Any]) -> dict[str, Any]:
    movie, pin = _verify_base_movie()
    path = str((ROOT / BASE_MOVIE).resolve())
    # Launcher readiness only proves that RPC is available; the emulated CPU may
    # still be running.  Begin both counterfactual arms from the same explicit
    # paused condition so no host-scheduling frames can slip between movie reset
    # and advanceToFrame.
    client.call("debugger.pause", {})
    _movie_cleanup(client)
    registry_ids = []
    try:
        loaded = client.call("movie.load", {"path": path})
        client.call("debugger.pause", {})
        control_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        control_before = _snapshot(client)
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_OBSERVE_FRAME, "max_frames": 100}, timeout=900)
        control_after = _snapshot(client)
        control_status = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})

        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(movie["frames"])})
        registry_ids.append(branch["movieId"])
        edits = []
        for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
            pad = dict(movie["frames"][index]["ports"]["0"])
            pad["square"] = MOVIE_SQUARE_START <= index < MOVIE_SQUARE_END
            edits.append(client.call("movie.editFrame", {
                "movieId": branch["movieId"], "frame": index,
                "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch["movieId"]})
        client.call("debugger.pause", {})
        edited_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        edited_before = _snapshot(client)
        client.call("execTrace.clear", {})
        watches = {label: client.call("execTrace.addWatch", {
            "pc": f"0x{pc:08X}", "capture": capture,
            "label": label, "max_events": 16})
            for label, pc, capture in (
                ("arm", 0x80049080, ["v0", "s1"]),
                ("dispatch", 0x80049094, ["a0", "s1"]),
                ("type_store", 0x80047228, ["s1"]),
                ("spawn_return", 0x80047254, ["v0", "s1"]),
                ("sfx", 0x8005044C, ["a0", "a1"]))}
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_OBSERVE_FRAME, "max_frames": 100}, timeout=900)
        edited_after = _snapshot(client)
        edited_status = client.call("movie.status", {})
        execution = {label: _trace_get(client, watch, 16)
                     for label, watch in watches.items()}
        client.call("movie.stopPlayback", {})
    finally:
        _movie_cleanup(client, registry_ids)
    differences = [name for name in control_before["fields"]
                   if control_before["fields"][name] != edited_before["fields"][name]]
    spawn_events = execution["spawn_return"]["events"]
    spawn_record = None
    if spawn_events:
        spawn_record = _record_snapshot(
            client, int(spawn_events[0]["regs"]["v0"], 16))
    result = {
        "base_movie": pin,
        "base_movie_metadata": {
            "format": movie.get("format"), "version": movie.get("version"),
            "frame_count": len(movie["frames"]),
            "start_state": movie.get("start_state")},
        "edit_recipe": {
            "button_added": "fresh Square", "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "square_start": MOVIE_SQUARE_START,
            "square_end_exclusive": MOVIE_SQUARE_END,
            "observe_frame": MOVIE_OBSERVE_FRAME,
            "edited_frame_count": len(edits),
            "source_window_predicate": "no shoulder/action/menu buttons",
        },
        "control": {"loaded": loaded, "started": control_started,
                    "before": control_before, "after": control_after,
                    "movie_status": control_status},
        "edited": {"branch": branch, "activated": activated,
                   "started": edited_started, "before": edited_before,
                   "after": edited_after, "movie_status": edited_status,
                   "execution": execution, "spawn_record": spawn_record},
        "pre_edit_field_differences": differences,
        "pre_edit_block_equal": control_before["player_block_sha256"] ==
                                edited_before["player_block_sha256"],
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
        "pre_edit_emulator_frame_equal": control_before["frame"] == edited_before["frame"],
    }
    statuses = (control_started, control_status, edited_started, edited_status)
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses) or \
            differences or not result["pre_edit_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["pre_edit_emulator_frame_equal"] or \
            control_after["fields"]["berries_in_flight"] != 0 or \
            len(spawn_events) != 1 or \
            int(execution["type_store"]["events"][0]["regs"]["s1"], 16) != 2 or \
            _descriptor_type(spawn_record, static) != 2:
        raise SystemExit(f"berry cold-boot counterfactual failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    gaps = static_census_gaps(static)
    if gaps:
        raise SystemExit(f"static berry census failed: {gaps}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    saves = [save for _label, save in anchors]
    selection = {**selection, "accepted": selection["accepted"][:19]}
    for extra in (CONTROL_ANCHOR, ARC_ANCHOR, *HOMING_ANCHORS.values()):
        declaration = verify_declared_save_fixture(
            ROOT / extra, allowed_media_classes={"pristine"})
        selection["accepted"].append({"label": f"berry_{extra}",
                                      "save": extra, **declaration})
        saves.append(extra)
    selection = {**selection, "accepted": selection["accepted"],
                 "rejected": [], "anchors_requested": 23,
                 "anchors_accepted": 23, "anchors_rejected": 0}

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.readMemory", "debugger.readStruct", "debugger.writeU8",
        "debugger.writeU16", "debugger.writeU32", "debugger.pause",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "execTrace.addWatch", "execTrace.get",
        "execTrace.clear", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status",
        "movie.remove", "movie.clear",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")

    # The from-boot counterfactual is independent evidence and must run before
    # any save-state load.  Apart from preserving the cold-boot/save-state
    # distinction, this prevents prior runtime experiments from influencing the
    # absolute checkpoint reached by movie playback.
    cold_boot = _run_cold_boot(client, static)
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    gates = _run_gate_controls(client)
    selectors = _run_selector_matrix(client, static)
    arc = _run_arc_and_lifecycle(client, static)
    homing = _run_homing_transitions(client, static)
    pause = _run_pause(client)
    breadth = _run_breadth(client, anchors)
    respawn = _run_respawn(client)

    client.call("emulator.clearControllerState", {"port": 0})
    client.call("execTrace.clear", {})
    _movie_cleanup(client)
    run_provenance = finish_run(
        args, generator="tools/phase4_berry_throw.py",
        anchor={
            "type": "from-boot fresh-Square counterfactual plus strict-pristine selector/gate/trajectory/lifecycle and gameplay-breadth sweep",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "input_pulse": "Square 4 emulator frames then neutral 12; dispatch observed by native PC, not assumed from frame count",
            "projectile_cadence": "position, velocity, gravity and TTL laws are per native projectile update, not emulator frame",
            "cold_boot_edit": cold_boot["edit_recipe"],
        })
    document = {
        "_comment": (
            "Phase-4 A08 pristine berry-throw evidence. Retail bytes bind the "
            "fresh-Square/gate law, five selector classes, aim split, spawn ABI, "
            "pool ownership, straight integration, homing transitions, audio and "
            "retirement. Live evidence retains cold boot, 19 anchors, lifecycle "
            "and instruction attribution."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {
            "cold_boot": cold_boot, "gate_controls": gates,
            "selector_matrix": selectors,
            "straight_arc_and_retirement": arc,
            "homing_transitions": homing, "pause_resume": pause,
            "breadth": breadth, "death_respawn": respawn,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[berry] retained A08 cold-boot + {len(anchors)} anchors + "
          f"{len(SELECTOR_TYPES)} native selector classes: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_berry_throw.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
