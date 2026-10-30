#!/usr/bin/env python3
"""Regenerate the Phase-4 A04 kick campaign from pristine retail evidence.

The retained proof joins hash-pinned resident bytes to a from-boot movie
counterfactual, all-gameplay-anchor input breadth, paired contact controls over
every active actor class present in those anchors, recovery/pause/respawn
lifecycle checks, and instruction-attributed execution/access traces.
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
        verified_media_identity, write_live_evidence,
    )
except ModuleNotFoundError:
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_kick.json"
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
LIVE_ACTOR_TABLE = 0x80090748
ACTOR_TABLE_CAPACITY = 64
RECORD_BASE = 0x8009FE04
KICK_OWNER = 0x80048138
PROXIMITY_OWNER = 0x8004ABF4

SHOULDER_MASK = 0x0300
SQUARE_MASK = 0x8000
KICK_START = -16
KICK_ANIMATION = 1
KICK_RESPONSE = 30
NEUTRAL_RESPONSE = 15
FLOOR_DISTANCE_EXCLUSIVE = 1024
CONTACT_Y_BIAS = 7360

SETTLE_FRAMES = 2
CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
EXCEPTION_LABEL = "stage14_riverbed_flight"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8135
MOVIE_EDIT_END = 8161
MOVIE_SQUARE_START = 8140
MOVIE_SQUARE_END = 8144
MOVIE_OBSERVE_FRAME = 8148

REGIONS = {
    "kick_arm": (0x80048F40, 0x80048FC0),
    "proximity_owner": (0x8004ABF4, 0x8004B6AC),
    "kick_contact_classification": (0x8004B400, 0x8004B660),
    "actor_animation_kick_path": (0x800566FC, 0x80056928),
}

EXPECTED_WORDS = {
    "decoded_action_load": (0x80048F44, 0x94632488),
    "shoulder_mask": (0x80048F4C, 0x30620300),
    "shoulder_required": (0x80048F50, 0x10400019),
    "square_mask": (0x80048F54, 0x30628000),
    "square_required": (0x80048F58, 0x1040004A),
    "previous_pad_load": (0x80048F64, 0x84422380),
    "fresh_square_mask": (0x80048F6C, 0x30428000),
    "fresh_square_required": (0x80048F70, 0x14400011),
    "timer_gate_load": (0x80048F78, 0x8622007A),
    "negative_timer_blocks": (0x80048F80, 0x0440000D),
    "floor_load": (0x80048F88, 0x8E220048),
    "floor_distance": (0x80048F94, 0x00431023),
    "floor_threshold": (0x80048F98, 0x28420400),
    "player_gate_load": (0x80048FA4, 0x8E22005C),
    "player_gate_required_zero": (0x80048FAC, 0x14400002),
    "timer_start_constant": (0x80048FB0, 0x2402FFF0),
    "timer_arm_writer": (0x80048FB4, 0xA622007A),
    "timer_negative_increment": (0x80048EB8, 0xA4820000),
    "timer_positive_decrement": (0x80048ED4, 0xA4820000),
    "timer_positive_12_writer": (0x80048F3C, 0xA4820000),
    "contact_actor_table_first_load": (0x8004AC00, 0x8E310748),
    "contact_timer_read": (0x8004B43C, 0x8442657A),
    "contact_timer_sign_branch": (0x8004B444, 0x04410004),
    "contact_kick_true": (0x8004B450, 0x24120001),
    "contact_flags_load": (0x8004B458, 0x9622005C),
    "response_only_mask": (0x8004B468, 0x30420080),
    "kick_response_branch": (0x8004B5AC, 0x12400028),
    "kick_state_30_constant": (0x8004B5C8, 0x2402001E),
    "kick_state_30_writer": (0x8004B5D8, 0xA622006C),
    "player_kick_response_writer": (0x8004B644, 0xA4226588),
    "neutral_or_resistant_state_writer": (0x8004B650, 0xA622006C),
    "kick_animation_timer_read": (0x80056700, 0x8442657A),
    "kick_animation_sign_branch": (0x80056708, 0x04410005),
    "kick_animation_constant": (0x80056710, 0x24020001),
    "kick_animation_writer": (0x80056718, 0xA4226588),
    "kick_start_compare": (0x80056914, 0x2402FFF0),
    "kick_phase_reset_writer": (0x80056924, 0xAC206544),
    "scene_load_clear": (0x80046D00, 0xA420657A),
    "action_reset_clear": (0x8004838C, 0xA420657A),
    "transition_clear": (0x8004A738, 0xA420657A),
    "respawn_clear": (0x8005B280, 0xA420657A),
    "plant_cannon_clear": (0x8005C1FC, 0xA420657A),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "prev_x", "offset": 0x10, "type": "s32"},
    {"name": "prev_y", "offset": 0x14, "type": "s32"},
    {"name": "prev_z", "offset": 0x18, "type": "s32"},
    {"name": "heading", "offset": 0x20, "type": "u32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "animation_phase", "offset": 0x44, "type": "u32"},
    {"name": "floor_y", "offset": 0x48, "type": "s32"},
    {"name": "action_gate_5c", "offset": 0x5C, "type": "u32"},
    {"name": "kick_timer", "offset": 0x7A, "type": "s16"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "health", "offset": 0x94, "type": "s16"},
    {"name": "lives", "offset": 0xA0, "type": "u8"},
    {"name": "special_mode", "offset": 0xA3, "type": "u8"},
]

EXPECTED_ACTIVE_CLASSES = {
    "6:4007", "9:4010", "9:4011", "9:4012", "9:4013",
    "10:4002", "10:4004", "10:4006", "14:4085", "15:4052",
    "15:4053", "17:4102", "17:c101", "19:4041", "22:4045",
    "22:4454", "30:4145", "34:4004", "36:4055", "37:4010",
    "38:4180", "38:4181", "39:4005", "11:4030", "11:4031",
    "21:4881", "28:4881", "30:4984",
}


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


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine kick word mismatch at 0x{address:08x}: "
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
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "regions": regions, "instruction_words": words,
        "law": {
            "action_word": f"0x{ACTION_WORD:08X}",
            "previous_pad": f"0x{PREVIOUS_PAD:08X}",
            "shoulder_mask": SHOULDER_MASK, "square_mask": SQUARE_MASK,
            "fresh_square_required": True,
            "timer_start": KICK_START,
            "timer_recovery_per_player_update": 1,
            "floor_distance_exclusive": FLOOR_DISTANCE_EXCLUSIVE,
            "player_gate_5c_required": 0,
            "kick_animation": KICK_ANIMATION,
            "ordinary_actor_response": KICK_RESPONSE,
            "neutral_actor_response": NEUTRAL_RESPONSE,
            "contact_geometry": (
                "actor animation-frame bounds at actor+0x74 + "
                "16*(actor+0x44), transformed through resident 12-bit LUT"),
            "contact_classification": {
                "flags_0x20": "separate actor path",
                "flags_0x800": "ordinary proximity path suppressed",
                "flags_0x80": "response 15; ordinary state-30 branch suppressed",
                "otherwise": "negative kick timer selects state 30; neutral contact selects state 15 and player damage",
            },
            "ordinary_owner": "resident player update 0x80048138..0x800498AB",
            "contact_owner": "resident proximity updater 0x8004ABF4..0x8004B6AB",
            "animation_owner": "resident actor skinned update 0x800563D4",
        },
        "writer_inventory": [
            {"address": "0x80046D00", "role": "scene-load clear"},
            {"address": "0x8004838C", "role": "resident action reset clear"},
            {"address": "0x80048EB8", "role": "negative recovery +1"},
            {"address": "0x80048ED4", "role": "positive recovery -1"},
            {"address": "0x80048F3C", "role": "shared positive-12 action writer"},
            {"address": "0x80048FB4", "role": "kick arm := -16"},
            {"address": "0x8004A738", "role": "resident transition clear"},
            {"address": "0x8005B280", "role": "native respawn clear"},
            {"address": "0x8005C1FC", "role": "plant/cannon action clear"},
        ],
        "source_status": {
            "player": "asm/hand_written/80048138_player_vertical_update.s (byte-matched build unit)",
            "contact": "asm/hand_written/8004abf4_proximity_updater.s (byte-matched build unit)",
            "animation": "asm/hand_written/800563d4_actor_skinned_update.s (byte-matched build unit)",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    for key, expected, message in (
        ("shoulder_mask", SHOULDER_MASK, "kick shoulder mask is not L2|R2 0x0300"),
        ("square_mask", SQUARE_MASK, "kick action mask is not Square 0x8000"),
        ("timer_start", KICK_START, "kick timer does not arm at -16"),
        ("floor_distance_exclusive", FLOOR_DISTANCE_EXCLUSIVE,
         "kick floor distance is not the exclusive 1024-unit bound"),
        ("kick_animation", KICK_ANIMATION, "kick animation is not 1"),
        ("ordinary_actor_response", KICK_RESPONSE,
         "ordinary kick contact response is not state 30"),
    ):
        if law.get(key) != expected:
            gaps.append(message)
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive kick instruction census is incomplete")
    if len(census.get("writer_inventory") or []) != 9:
        gaps.append("kick timer writer inventory is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(row["hex"])


def _read_u32(client: Any, address: int) -> int:
    return int.from_bytes(_read_memory(client, address, 4), "little")


def _read_s16(client: Any, address: int) -> int:
    return struct.unpack("<h", _read_memory(client, address, 2))[0]


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
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _actor_snapshot(client: Any, pointer: int) -> dict[str, Any]:
    data = _read_memory(client, pointer, 0x84)
    return {
        "pointer": f"0x{pointer:08X}",
        "id": struct.unpack_from("<I", data, 0)[0],
        "x": struct.unpack_from("<i", data, 4)[0],
        "y": struct.unpack_from("<i", data, 8)[0],
        "z": struct.unpack_from("<i", data, 12)[0],
        "heading": struct.unpack_from("<I", data, 0x14)[0],
        "animation_phase": struct.unpack_from("<I", data, 0x44)[0],
        "flags": struct.unpack_from("<H", data, 0x5C)[0],
        "state": struct.unpack_from("<h", data, 0x6C)[0],
        "hp_or_response": struct.unpack_from("<h", data, 0x6E)[0],
        "animation_geometry": struct.unpack_from("<I", data, 0x74)[0],
        "record_sha256": _sha256_bytes(data),
    }


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
    expected = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
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


def _fire_chord(client: Any, shoulder: str = "l2",
                *, sample_frames: int = 8) -> dict[str, Any]:
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {shoulder: True}})
    client.call("emulator.advanceFrames", {"frames": 4})
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {shoulder: True, "square": True}})
    samples = []
    for _ in range(sample_frames):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
    client.call("emulator.clearControllerState", {"port": 0})
    return {"shoulder": shoulder, "samples": samples,
            "minimum_timer": min(row["fields"]["kick_timer"] for row in samples)}


def _live_actor_entries(client: Any) -> list[dict[str, Any]]:
    pointers = struct.unpack(
        f"<{ACTOR_TABLE_CAPACITY}I",
        _read_memory(client, LIVE_ACTOR_TABLE, ACTOR_TABLE_CAPACITY * 4))
    entries = []
    for index, pointer in enumerate(pointers):
        if pointer == 0:
            break
        row = _actor_snapshot(client, pointer)
        row["table_index"] = index
        entries.append(row)
    return entries


def _s16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _contact_center(client: Any, pointer: int) -> dict[str, Any]:
    actor = _actor_snapshot(client, pointer)
    phase = actor["animation_phase"]
    geometry = actor["animation_geometry"] + phase * 16
    frame = _read_memory(client, geometry, 16)
    off_x, off_y, off_z = struct.unpack_from("<hhh", frame, 0)
    angle = actor["heading"] & 0xFFF
    lut = _read_memory(client, 0x80074970, 0x2000)
    cos_q = _s16(struct.unpack_from(
        "<H", lut, ((angle + 3072) & 0xFFF) * 2)[0]) >> 2
    sin_q = _s16(struct.unpack_from(
        "<H", lut, ((angle + 2048) & 0xFFF) * 2)[0]) >> 2
    rotated_x = (off_x * cos_q + off_z * sin_q) >> 12
    rotated_z = (off_z * cos_q - off_x * sin_q) >> 12
    xyz = (actor["x"] + rotated_x,
           actor["y"] + off_y + CONTACT_Y_BIAS,
           actor["z"] + rotated_z)
    return {
        "actor": actor, "frame_address": f"0x{geometry:08X}",
        "frame_offsets": [off_x, off_y, off_z],
        "angle": angle, "cos_q": cos_q, "sin_q": sin_q,
        "player_contact_center": list(xyz),
    }


def _classify_flags(flags: int) -> str:
    if flags & 0x20:
        return "separate_actor_path_0x20"
    if flags & 0x800:
        return "ordinary_contact_suppressed_0x800"
    if flags & 0x80:
        return "response_only_0x80"
    return "ordinary_kick_eligible"


def _run_native_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR

    positives = {}
    for shoulder in ("l2", "r2"):
        _load_anchor(client, path)
        before = _snapshot(client)
        fired = _fire_chord(client, shoulder)
        positives[shoulder] = {"before": before, **fired}
        if fired["minimum_timer"] != KICK_START or not any(
                row["fields"]["animation"] == KICK_ANIMATION
                for row in fired["samples"]):
            raise SystemExit(f"native {shoulder}+Square did not kick: {fired}")

    negatives = {}
    for name, initial, second in (
        ("square_without_shoulder", {"square": True}, None),
        ("shoulder_without_square", {"l2": True}, None),
        ("square_preheld_then_shoulder", {"square": True},
         {"square": True, "l2": True}),
    ):
        _load_anchor(client, path)
        before = _snapshot(client)
        client.call("emulator.setControllerState", {"port": 0, "buttons": initial})
        client.call("emulator.advanceFrames", {"frames": 4})
        if second:
            client.call("emulator.setControllerState", {"port": 0, "buttons": second})
        samples = []
        for _ in range(8):
            client.call("emulator.advanceFrames", {"frames": 1})
            samples.append(_snapshot(client))
        client.call("emulator.clearControllerState", {"port": 0})
        negatives[name] = {"before": before, "samples": samples}
        if any(row["fields"]["kick_timer"] < 0 for row in samples):
            raise SystemExit(f"negative kick control armed: {name}")

    for distance, expected in ((1023, KICK_START), (1024, 0)):
        _load_anchor(client, path)
        before = _snapshot(client)
        y = before["fields"]["floor_y"] - distance
        writes = [
            _checked_write(client, "debugger.writeU32", PLAYER_BASE + off,
                           y & 0xFFFFFFFF) for off in (0x04, 0x14)]
        fired = _fire_chord(client, "l2", sample_frames=4)
        row = {"distance": distance, "before": before, "writes": writes, **fired}
        negatives[f"floor_distance_{distance}"] = row
        if fired["minimum_timer"] != expected:
            raise SystemExit(f"kick floor boundary failed: {row}")

    _load_anchor(client, path)
    blocked_before = _snapshot(client)
    gate_write = _checked_write(
        client, "debugger.writeU32", PLAYER_BASE + 0x5C, 1)
    blocked = _fire_chord(client, "l2")
    negatives["player_gate_5c_nonzero"] = {
        "before": blocked_before, "write": gate_write, **blocked}
    if blocked["minimum_timer"] < 0:
        raise SystemExit("player+0x5C nonzero did not block kick")

    _load_anchor(client, path)
    first = _fire_chord(client, "l2", sample_frames=3)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"l2": True}})
    client.call("emulator.advanceFrames", {"frames": 4})
    retry_before = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"l2": True, "square": True}})
    retry = []
    for _ in range(4):
        client.call("emulator.advanceFrames", {"frames": 1})
        retry.append(_snapshot(client))
    client.call("emulator.clearControllerState", {"port": 0})
    busy = {"first": first, "retry_before": retry_before, "retry_samples": retry}
    if retry_before["fields"]["kick_timer"] >= 0 or any(
            row["fields"]["kick_timer"] == KICK_START for row in retry):
        raise SystemExit(f"negative timer rearmed unexpectedly: {busy}")

    return {"positive_chords": positives, "negative_controls": negatives,
            "negative_timer_retry": busy}


def _run_recovery(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    fired = _fire_chord(client, "l2", sample_frames=2)
    samples = list(fired["samples"])
    for _ in range(48):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
        if samples[-1]["fields"]["kick_timer"] == 0:
            break
    transitions = []
    for row in samples:
        value = row["fields"]["kick_timer"]
        if not transitions or transitions[-1] != value:
            transitions.append(value)
    # A controller poll and the resident player update do not necessarily fall
    # in the same emulator frame.  Retain that pre-arm zero in ``samples`` for
    # timing audit, but the recovery law begins at the observed -16 writer.
    transitions = transitions[transitions.index(KICK_START):]
    if transitions != list(range(KICK_START, 1)):
        raise SystemExit(f"kick recovery is not -16..0 by +1: {transitions}")
    recovered = samples[-1]
    fresh = _fire_chord(client, "r2")
    if fresh["minimum_timer"] != KICK_START:
        raise SystemExit("fresh kick did not arm after recovery")
    return {"samples": samples, "distinct_timer_transitions": transitions,
            "recovered": recovered, "fresh_after_recovery": fresh}


def _run_input_breadth(client: Any,
                       anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    for index, (label, save) in enumerate(anchors, 1):
        _load_anchor(client, ROOT / save)
        before = _snapshot(client)
        fired = _fire_chord(client, "l2")
        results[label] = {"save": save, "before": before, **fired}
        print(f"[kick] input {index:02d}/{len(anchors)} {label}: "
              f"min_timer={fired['minimum_timer']}")
    applicable = [label for label in results if label != EXCEPTION_LABEL]
    armed = sorted(label for label in applicable
                   if results[label]["minimum_timer"] == KICK_START)
    animated = sorted(label for label in applicable if any(
        row["fields"]["animation"] == KICK_ANIMATION
        for row in results[label]["samples"]))
    exception = results[EXCEPTION_LABEL]
    summary = {
        "anchors_compared": len(results),
        "applicable_anchors": len(applicable),
        "applicable_labels": applicable,
        "armed_labels": armed, "animation_1_labels": animated,
        "exception_label": EXCEPTION_LABEL,
        "exception_minimum_timer": exception["minimum_timer"],
        "exception_animation": exception["samples"][-1]["fields"]["animation"],
        "exception_grounded": exception["samples"][-1]["fields"]["grounded"],
    }
    if len(results) != 19 or len(armed) != 18 or len(animated) != 18 or \
            summary["exception_minimum_timer"] != 0 or \
            summary["exception_animation"] != 4 or \
            summary["exception_grounded"] != 0:
        raise SystemExit(f"kick gameplay breadth failed: {summary}")
    return {"summary": summary, "anchors": results}


def _enumerate_active_classes(client: Any,
                              anchors: list[tuple[str, str]]) -> dict[str, Any]:
    by_anchor, representatives = {}, {}
    for label, save in anchors:
        _load_anchor(client, ROOT / save)
        entries = _live_actor_entries(client)
        rows = []
        for row in entries:
            key = f"{row['id']}:{row['flags']:04x}"
            compact = {
                "table_index": row["table_index"], "pointer": row["pointer"],
                "id": row["id"], "flags": row["flags"],
                "classification": _classify_flags(row["flags"]),
            }
            rows.append(compact)
            representatives.setdefault(key, {
                "anchor": label, "save": save, **compact})
        by_anchor[label] = {"save": save, "active_count": len(rows),
                            "entries": rows}
    if set(representatives) != EXPECTED_ACTIVE_CLASSES:
        raise SystemExit(
            "active kick class set changed: "
            f"missing={sorted(EXPECTED_ACTIVE_CLASSES - set(representatives))} "
            f"extra={sorted(set(representatives) - EXPECTED_ACTIVE_CLASSES)}")
    return {"anchors": by_anchor, "representatives": representatives}


def _direct_contact_trial(client: Any, representative: dict[str, Any],
                          timer: int) -> dict[str, Any]:
    _load_anchor(client, ROOT / representative["save"])
    pointers = struct.unpack(
        f"<{ACTOR_TABLE_CAPACITY}I",
        _read_memory(client, LIVE_ACTOR_TABLE, ACTOR_TABLE_CAPACITY * 4))
    pointer = pointers[representative["table_index"]]
    actor = _actor_snapshot(client, pointer)
    if actor["id"] != representative["id"] or \
            actor["flags"] != representative["flags"]:
        raise SystemExit(f"active class representative changed on reload: {representative} {actor}")
    center = _contact_center(client, pointer)
    xyz = tuple(center["player_contact_center"])
    writes = _set_player_position(client, xyz)
    for method, address, value in (
        ("debugger.writeU32", PLAYER_BASE + 0x20, 0),
        ("debugger.writeU32", PLAYER_BASE + 0x30, 0),
        ("debugger.writeU32", PLAYER_BASE + 0x5C, 0),
        ("debugger.writeU16", PLAYER_BASE + 0x7A, timer & 0xFFFF),
        ("debugger.writeU16", PLAYER_BASE + 0x88, 22),
        ("debugger.writeU16", PLAYER_BASE + 0x94, 4),
        ("debugger.writeU16", pointer + 0x6C, 0),
    ):
        writes.append(_checked_write(client, method, address, value))
    before_player = _snapshot(client)
    before_actor = _actor_snapshot(client, pointer)
    client.call("debugger.pause", {})
    call = client.call("debugger.callFunction", {
        "address": f"0x{PROXIMITY_OWNER:08X}", "timeout": 10000}, timeout=30)
    after_player = _snapshot(client)
    after_actor = _actor_snapshot(client, pointer)
    return {
        "timer": timer, "geometry": center, "writes": writes,
        "before": {"player": before_player, "actor": before_actor},
        "call": call,
        "after": {"player": after_player, "actor": after_actor},
    }


def _run_contact_matrix(client: Any,
                        anchors: list[tuple[str, str]]) -> dict[str, Any]:
    census = _enumerate_active_classes(client, anchors)
    trials, summary = {}, {
        "active_classes": len(census["representatives"]),
        "ordinary_kick_eligible": [], "response_only_0x80": [],
        "separate_actor_path_0x20": [],
        "ordinary_contact_suppressed_0x800": [],
        "static_live_classification_matches": [],
    }
    for index, key in enumerate(sorted(census["representatives"]), 1):
        representative = census["representatives"][key]
        neutral = _direct_contact_trial(client, representative, 0)
        kick = _direct_contact_trial(client, representative, KICK_START)
        classification = representative["classification"]
        trials[key] = {"representative": representative,
                       "neutral": neutral, "kick": kick}
        summary[classification].append(key)
        neutral_actor = neutral["after"]["actor"]
        kick_actor = kick["after"]["actor"]
        neutral_health = neutral["after"]["player"]["fields"]["health"]
        kick_health = kick["after"]["player"]["fields"]["health"]
        matched = False
        if classification == "ordinary_kick_eligible":
            matched = (neutral_actor["state"] == NEUTRAL_RESPONSE and
                       neutral_health == 3 and
                       kick_actor["state"] == KICK_RESPONSE and
                       kick_health == 4 and
                       kick["after"]["player"]["fields"]["animation"] == 30)
        elif classification == "response_only_0x80":
            matched = kick_actor["state"] == NEUTRAL_RESPONSE and kick_health == 4
        else:
            matched = kick_actor["state"] != KICK_RESPONSE
        if matched:
            summary["static_live_classification_matches"].append(key)
        print(f"[kick] class {index:02d}/{len(census['representatives'])} "
              f"{key} {classification}: neutral={neutral_actor['state']} "
              f"kick={kick_actor['state']} hp={kick_health}")
    for key in summary:
        if isinstance(summary[key], list):
            summary[key] = sorted(summary[key])
    if len(summary["ordinary_kick_eligible"]) != 20 or \
            len(summary["response_only_0x80"]) != 3 or \
            len(summary["separate_actor_path_0x20"]) != 2 or \
            len(summary["ordinary_contact_suppressed_0x800"]) != 3 or \
            len(summary["static_live_classification_matches"]) != 28:
        raise SystemExit(f"kick contact class matrix failed: {summary}")
    summary["scope_boundary"] = (
        "active pointer-table classes at the 19 retained save moments; this is "
        "not a full authored enemy roster and does not promote family-specific "
        "AI, boss/overlay contact, respawn, permanence, or berry immunity")
    return {"active_census": census, "summary": summary, "trials": trials}


def _run_pause_control(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    fired = _fire_chord(client, "l2", sample_frames=2)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused_start = _snapshot(client)
    client.call("emulator.advanceFrames", {"frames": 30})
    paused_neutral = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    resumed = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    frozen_names = ["x", "y", "z", "kick_timer", "animation"]
    frozen = [name for name in frozen_names
              if paused_start["fields"][name] == paused_neutral["fields"][name]]
    result = {"fired": fired, "paused_start": paused_start,
              "paused_after_neutral": paused_neutral, "resumed": resumed,
              "frozen_fields": frozen}
    if paused_start["pause_flag"] != 1 or paused_neutral["pause_flag"] != 1 or \
            frozen != frozen_names or resumed["pause_flag"] != 0 or \
            resumed["fields"]["kick_timer"] <= paused_neutral["fields"]["kick_timer"]:
        raise SystemExit(f"kick pause/resume failed: {result}")
    return result


def _run_respawn_control(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    rid, actor_x, actor_y, actor_z = struct.unpack(
        "<Iiii", _read_memory(client, RECORD_BASE, 16))
    writes = [
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0),
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x7A, 11),
    ]
    writes.extend(_set_player_position(client, (actor_x, actor_y, actor_z)))
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
        raise SystemExit("native respawn did not complete during kick lifecycle control")
    post = _fire_chord(client, "r2")
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "perturbation": "health:=0; kick_timer:=11; position+mirror:=first actor; fresh kick after native respawn",
        "actor": {"id": rid, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes, "before": before, "flow": flow,
        "respawn": respawn, "post_respawn_kick": post,
    }
    if before["fields"]["kick_timer"] != 11 or \
            respawn["fields"]["kick_timer"] != 0 or \
            respawn["scene"] != before["scene"] or \
            post["minimum_timer"] != KICK_START:
        raise SystemExit(f"kick timer did not reset/rearm across native respawn: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id", "regs")}


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    target = _live_actor_entries(client)[0]
    pointer = int(target["pointer"], 16)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    specifications = [
        {"address": f"0x{ACTION_WORD:08X}", "length": 2, "type": "read",
         "label": "decoded_action_read", "max_events": 64,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x80048138", "max": "0x800498AB"}}},
        {"address": f"0x{PREVIOUS_PAD:08X}", "length": 2, "type": "read",
         "label": "previous_pad_read", "max_events": 64,
         "stop_on_hit": False},
        {"address": f"0x{PLAYER_BASE + 0x7A:08X}", "length": 2,
         "type": "readwrite", "label": "kick_timer", "max_events": 128,
         "stop_on_hit": False},
        {"address": f"0x{PLAYER_BASE + 0x88:08X}", "length": 2,
         "type": "write", "label": "player_animation", "max_events": 128,
         "stop_on_hit": False},
        {"address": f"0x{pointer + 0x5C:08X}", "length": 2,
         "type": "readwrite", "label": "target_flags", "max_events": 64,
         "stop_on_hit": False},
        {"address": f"0x{pointer + 0x6C:08X}", "length": 2,
         "type": "readwrite", "label": "target_response", "max_events": 64,
         "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    exec_specs = [
        ("shoulder_mask", 0x80048F4C, ["v0", "v1", "s1"]),
        ("timer_arm", 0x80048FB4, ["v0", "s1"]),
        ("timer_recovery", 0x80048EB8, ["v0", "v1", "a0"]),
        ("kick_animation", 0x80056718, ["v0"]),
        ("kick_phase_reset", 0x80056924, ["v1"]),
        ("contact_timer_read", 0x8004B43C, ["v0", "s1", "s2"]),
        ("target_state_30", 0x8004B5D8, ["v0", "s1", "s2"]),
        ("player_response_30", 0x8004B644, ["v0", "a0", "s1", "s2"]),
    ]
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture,
        "label": label, "max_events": 64})
        for label, pc, capture in exec_specs]
    # The resident player update is less frequent than an emulator frame.  Keep
    # Square asserted long enough to cross one attributed 0x80048F4C poll.
    fired = _fire_chord(client, "l2", sample_frames=8)
    if fired["minimum_timer"] != KICK_START:
        raise SystemExit(f"traced native chord did not arm kick: {fired}")
    # Actors continue updating during the input chord; reconstruct the contact
    # center from the current phase instead of reusing a pre-input coordinate.
    center = _contact_center(client, pointer)
    writes = _set_player_position(
        client, tuple(center["player_contact_center"]))
    access = client.call("accessLog.run", {"frames": 12})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 32}) for watch in watches]
    executions = {}
    for (label, _pc, _capture), watch in zip(exec_specs, exec_watches):
        executions[label] = client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 64})
    events = [_trim_event(row) for row in access.get("events") or []]
    result = {
        "target": target, "geometry": center, "fired": fired,
        "position_writes": writes, "specifications": specifications,
        "watches": watches, "events": events, "total": access.get("total"),
        "truncated": access.get("truncated", False),
        "summaries": summaries, "execution": executions,
        "target_after": _actor_snapshot(client, pointer),
        "player_after": _snapshot(client),
    }
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    if result["truncated"] or any(row.get("truncated") for row in summaries):
        raise SystemExit("kick access trace truncated")
    if any(row.get("truncated") for row in executions.values()) or any(
            not (row.get("events") or []) for row in executions.values()):
        raise SystemExit(f"kick execution trace missing/truncated: {executions}")
    state_event = executions["target_state_30"]["events"][0]
    if int(state_event["regs"]["v0"], 16) != KICK_RESPONSE or \
            result["player_after"]["fields"]["health"] != 4:
        raise SystemExit(f"native traced kick contact failed: {result}")
    return result


def _verify_base_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / BASE_MOVIE
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(BASE_MOVIE)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot movie lacks an exact central pin: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("LEVEL01 kick control is not a v3 from-boot movie")
    frames = movie.get("frames") or []
    if MOVIE_EDIT_END > len(frames):
        raise SystemExit("kick edit window exceeds base movie")
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((frames[index].get("ports") or {}).get("0") or {})
        if pad.get("up") is not True or any(pad.get(button) for button in (
                "l2", "r2", "cross", "circle", "square", "triangle",
                "start", "select")):
            raise SystemExit(f"kick movie window is no longer action-neutral Up at {index}")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _run_cold_boot_movie(client: Any) -> dict[str, Any]:
    movie, pin = _verify_base_movie()
    path = str((ROOT / BASE_MOVIE).resolve())
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    registry_ids = []
    try:
        loaded = client.call("movie.load", {"path": path})
        control_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        control_before = _snapshot(client)
        control_before_movie = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_OBSERVE_FRAME, "max_frames": 100}, timeout=900)
        control_after = _snapshot(client)
        control_after_movie = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})

        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(movie["frames"])})
        branch_id = branch["movieId"]
        registry_ids.append(branch_id)
        edits = []
        for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
            pad = dict(movie["frames"][index]["ports"]["0"])
            pad["l2"] = True
            pad["square"] = MOVIE_SQUARE_START <= index < MOVIE_SQUARE_END
            edits.append(client.call("movie.editFrame", {
                "movieId": branch_id, "frame": index, "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch_id})
        edited_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        edited_before = _snapshot(client)
        edited_before_movie = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_OBSERVE_FRAME, "max_frames": 100}, timeout=900)
        edited_after = _snapshot(client)
        edited_after_movie = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})
    finally:
        try:
            client.call("movie.stopPlayback", {})
        except Exception:
            pass
        for movie_id in reversed(registry_ids):
            try:
                client.call("movie.remove", {"movieId": movie_id})
            except Exception:
                pass
        try:
            client.call("movie.clear", {})
        except Exception:
            pass
    before_fields = list(control_before["fields"])
    differences = [name for name in before_fields
                   if control_before["fields"][name] != edited_before["fields"][name]]
    result = {
        "base_movie": pin,
        "base_movie_metadata": {
            "format": movie.get("format"), "version": movie.get("version"),
            "frame_count": len(movie["frames"]),
            "start_state": movie.get("start_state")},
        "edit_recipe": {
            "shoulder_added": "l2", "square_added": "fresh press",
            "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "square_start": MOVIE_SQUARE_START,
            "square_end_exclusive": MOVIE_SQUARE_END,
            "observe_frame": MOVIE_OBSERVE_FRAME,
            "edited_frame_count": len(edits),
            "source_window_predicate": "Up true; shoulders, action peers, and menu buttons false",
        },
        "control": {
            "loaded": loaded, "started": control_started,
            "before": control_before, "before_movie": control_before_movie,
            "after": control_after, "after_movie": control_after_movie},
        "edited": {
            "branch": branch, "activated": activated, "started": edited_started,
            "before": edited_before, "before_movie": edited_before_movie,
            "after": edited_after, "after_movie": edited_after_movie},
        "pre_edit_field_differences": differences,
        "pre_edit_block_equal": (
            control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"]),
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
        "pre_edit_emulator_frame_equal": control_before["frame"] == edited_before["frame"],
    }
    statuses = (control_started, control_before_movie, control_after_movie,
                edited_started, edited_before_movie, edited_after_movie)
    if any(status.get("reproducible") is not True or
           status.get("truncated") is not False for status in statuses):
        raise SystemExit(f"kick cold-boot movie was not reproducible: {result}")
    if differences or not result["pre_edit_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["pre_edit_emulator_frame_equal"] or \
            control_after["fields"]["kick_timer"] != 0 or \
            edited_after["fields"]["kick_timer"] >= 0 or \
            edited_after["fields"]["animation"] != KICK_ANIMATION:
        raise SystemExit(f"kick cold-boot counterfactual failed: {result}")
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
        raise SystemExit(f"static kick census failed: {gaps}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    saves = [save for _label, save in anchors]

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.readMemory", "debugger.readStruct", "debugger.writeU16",
        "debugger.writeU32", "debugger.callFunction", "debugger.pause",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "accessLog.addWatch", "accessLog.run",
        "accessLog.summary", "accessLog.clear", "execTrace.addWatch",
        "execTrace.get", "execTrace.clear", "movie.load", "movie.store",
        "movie.branch", "movie.editFrame", "movie.activate",
        "movie.startPlayback", "movie.advanceToFrame", "movie.stopPlayback",
        "movie.status", "movie.remove", "movie.clear",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    controls = _run_native_controls(client)
    recovery = _run_recovery(client)
    breadth = _run_input_breadth(client, anchors)
    contacts = _run_contact_matrix(client, anchors)
    pause = _run_pause_control(client)
    respawn = _run_respawn_control(client)
    trace = _run_writer_trace(client)
    cold_boot = _run_cold_boot_movie(client)

    client.call("emulator.clearControllerState", {"port": 0})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    run_provenance = finish_run(
        args, generator="tools/phase4_kick.py",
        anchor={
            "type": "from-boot L2+fresh-Square counterfactual plus strict-pristine save-state input/contact/lifecycle sweep",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections,
            "selection": {**selection, "accepted": selection["accepted"][:19],
                          "rejected": [], "anchors_requested": 19,
                          "anchors_accepted": 19, "anchors_rejected": 0},
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "player_update_cadence": "timer transitions are deduplicated by value and attributed to 0x80048EB8; constants apply per native player update",
            "cold_boot_edit": cold_boot["edit_recipe"],
            "contact_trials": "fresh state for every timer=0 / timer=-16 paired call; exact animation-geometry contact center reconstructed after each load",
        },
    )
    document = {
        "_comment": (
            "Phase-4 A04 pristine kick evidence. Retail bytes bind the "
            "L2|R2 plus fresh-Square gate, -16..0 timer, animation, contact "
            "geometry and flag law. Live evidence retains cold boot, 19-anchor "
            "input breadth, 28 active contact classes, lifecycle and writer attribution."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {
            "cold_boot": cold_boot, "native_controls": controls,
            "recovery": recovery, "input_breadth": breadth,
            "contact_matrix": contacts, "pause_resume": pause,
            "death_respawn": respawn, "writer_trace": trace,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[kick] retained cold-boot + {len(anchors)} anchors + "
          f"{contacts['summary']['active_classes']} active classes: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_kick.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
