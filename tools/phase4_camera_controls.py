#!/usr/bin/env python3
"""Regenerate the Phase-4 A17 manual-camera campaign from pristine evidence.

The retained run binds the resident L1/R1 selector, its typed camera-control
state and smoothing laws, the HUD consumer, gameplay breadth, pause/reset and
same-scene respawn.  Full camera collision/rendering remains E04-owned.
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
OUTPUT = ROOT / "analysis/phase4_camera_controls.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

CAMERA_BASE = 0x80095358
CAMERA_SIZE = 0x60
ACTION_WORD = 0x80082488
MODE_WORD = 0x80082220
ORBIT_BIAS = 0x80082280
NEUTRAL_TRACKING_STEP = 0x800822A8
VERTICAL_TARGET = 0x80082460
PITCH_STEP = 0x80082474
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
PLAYER_BASE = 0x800A6500
ACTOR_RECORD_BASE = 0x8009FE04

L1_MASK = 0x0400
R1_MASK = 0x0800
UP_MASK = 0x0010
DOWN_MASK = 0x0040
LEFT_MASK = 0x0080
RIGHT_MASK = 0x0020
MODE_NEUTRAL = 0
MODE_L1 = 2
MODE_R1 = 3
L1_DISTANCE = 600
R1_DISTANCE = 1400
L1_COLLISION_SQUARED = 160000
R1_COLLISION_SQUARED = 1960000
NEUTRAL_VERTICAL_TARGET = 12288
L1_UP_VERTICAL_TARGET = 32768
L1_DOWN_VERTICAL_TARGET = 4096
R1_VERTICAL_TARGET = 24576
L1_DOWN_ORBIT_BIAS = 12288

SETTLE_FRAMES = 2
HOLD_FRAMES = 64
RELEASE_FRAMES = 128
CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8103
MOVIE_EDIT_END = 8163
MOVIE_PRE_EDIT = MOVIE_EDIT_START - 1

CAMERA_UPDATE = (0x8004DF18, 0x8004EA8C)
CAMERA_RESET = (0x8004DC0C, 0x8004DD98)
HUD_CONSUMER = (0x800526FC, 0x80052B00)
PROFILE_TABLE = (0x80077F40, 0x80077FA0)

EXPECTED_WORDS = {
    "packed_timer_decrement_writer": (0x8004DF5C, 0xA6420022),
    "decoded_action_reader": (0x8004DFD4, 0x94632488),
    "l1_mask": (0x8004DFDC, 0x30620400),
    "l1_mode_writer": (0x8004DFF0, 0xAF820488),
    "l1_timer_or_writer": (0x8004E01C, 0xA6420022),
    "r1_mask": (0x8004E064, 0x30620800),
    "r1_mode_writer": (0x8004E070, 0xAF820488),
    "neutral_mode_writer": (0x8004E09C, 0xAF800488),
    "vertical_target_writer": (0x8004E1CC, 0xAF8206C8),
    "orbit_yaw_writer": (0x8004E240, 0xA6420020),
    "orbit_yaw_clamp_writer": (0x8004E2AC, 0xA6420020),
    "distance_increment_writer": (0x8004E490, 0xA642001E),
    "distance_decrement_writer": (0x8004E4C0, 0xA642001E),
    "pitch_step_clear": (0x8004E968, 0xA78006DC),
}

CAMERA_FIELDS = [
    {"name": "position_x", "offset": 0x00, "type": "s32"},
    {"name": "position_y", "offset": 0x04, "type": "s32"},
    {"name": "position_z", "offset": 0x08, "type": "s32"},
    {"name": "target_x", "offset": 0x0C, "type": "s32"},
    {"name": "target_y", "offset": 0x10, "type": "s32"},
    {"name": "target_z", "offset": 0x14, "type": "s32"},
    {"name": "view_yaw", "offset": 0x18, "type": "s16"},
    {"name": "follow_yaw", "offset": 0x1A, "type": "s16"},
    {"name": "distance", "offset": 0x1E, "type": "s16"},
    {"name": "orbit_yaw", "offset": 0x20, "type": "u16"},
    {"name": "profile_and_suppression", "offset": 0x22, "type": "u16"},
    {"name": "pitch_scale", "offset": 0x24, "type": "s16"},
    {"name": "vertical_angle", "offset": 0x2A, "type": "s16"},
    {"name": "alternate_mode", "offset": 0x2C, "type": "s16"},
    {"name": "height_correction", "offset": 0x2E, "type": "s16"},
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


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine camera word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "camera_reset": CAMERA_RESET,
        "camera_follow_update": CAMERA_UPDATE,
        "manual_mode_hud_consumer": HUD_CONSUMER,
        "camera_profile_table": PROFILE_TABLE,
    }.items():
        data = _region(exe, bounds)
        regions[name] = {
            "start": f"0x{bounds[0]:08X}",
            "end_exclusive": f"0x{bounds[1]:08X}",
            "size": len(data), "sha256": _sha256_bytes(data),
        }
    table = _region(exe, PROFILE_TABLE)
    profiles = []
    for index in range(6):
        minimum, maximum, collision_squared, vertical = struct.unpack_from(
            "<IIII", table, index * 16)
        profiles.append({"index": index, "minimum_distance": minimum,
                         "maximum_distance": maximum,
                         "collision_distance_squared": collision_squared,
                         "vertical_target": vertical})
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}",
                       "sha256": _sha256_bytes(exe)},
        "instruction_words": words, "regions": regions,
        "profile_table": profiles,
        "law": {
            "mode_address": f"0x{MODE_WORD:08X}",
            "mode_domain": {"neutral": 0, "l1_manual": 2, "r1_lock": 3},
            "input_precedence": "L1 branch precedes R1; simultaneous L1+R1 selects mode 2",
            "l1": {"mask": L1_MASK, "distance_target": L1_DISTANCE,
                   "collision_distance_squared": L1_COLLISION_SQUARED,
                   "yaw_correction_max": 80,
                   "vertical_neutral": NEUTRAL_VERTICAL_TARGET,
                   "vertical_up": L1_UP_VERTICAL_TARGET,
                   "vertical_down": L1_DOWN_VERTICAL_TARGET,
                   "down_orbit_bias": L1_DOWN_ORBIT_BIAS,
                   "distance_step": 32, "vertical_step": 1024,
                   "orbit_bias_step": 2304},
            "r1": {"mask": R1_MASK, "distance_target": R1_DISTANCE,
                   "collision_distance_squared": R1_COLLISION_SQUARED,
                   "yaw_correction_max": 0,
                   "vertical_target": R1_VERTICAL_TARGET,
                   "distance_step": 32, "vertical_step": 1024},
            "reset": {"mode": 0, "distance": 900,
                      "profile_and_suppression": 2049,
                      "pitch_scale": 32,
                      "vertical_target": NEUTRAL_VERTICAL_TARGET,
                      "neutral_tracking_step": 20},
            "typed_globals": {
                "orbit_bias": f"0x{ORBIT_BIAS:08X}:s32",
                "vertical_target": f"0x{VERTICAL_TARGET:08X}:s32",
                "neutral_tracking_step": f"0x{NEUTRAL_TRACKING_STEP:08X}:s32",
                "pitch_step": f"0x{PITCH_STEP:08X}:s16",
            },
        },
        "source_status": {
            "matching_c": "No matching C is claimed for the manual camera owner or reset owner.",
            "asm": "0x8004DC0C reset and 0x8004DF18 follow/update are byte-matched handwritten assembly.",
            "semantic_c": "The campaign records execution semantics without promoting a documentation-only C rewrite.",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    if (law.get("mode_domain") or {}) != {
            "neutral": 0, "l1_manual": 2, "r1_lock": 3}:
        gaps.append("manual camera mode domain is incomplete")
    if (law.get("l1") or {}).get("distance_target") != L1_DISTANCE:
        gaps.append("L1 distance target is not 600")
    if (law.get("r1") or {}).get("distance_target") != R1_DISTANCE:
        gaps.append("R1 distance target is not 1400")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive camera instruction census is incomplete")
    if len(census.get("profile_table") or []) != 6:
        gaps.append("camera profile table census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    result = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(result["hex"])


def _read_int(client: Any, address: int, length: int,
              *, signed: bool = False) -> int:
    return int.from_bytes(_read_memory(client, address, length), "little",
                          signed=signed)


def _snapshot(client: Any) -> dict[str, Any]:
    result = client.call("debugger.readStruct", {
        "base": f"0x{CAMERA_BASE:08X}", "fields": CAMERA_FIELDS})
    fields = {}
    for row in result.get("fields") or []:
        if row.get("valid") is not True:
            raise SystemExit(f"invalid camera field: {row}")
        fields[row["name"]] = row["value"]
    data = _read_memory(client, CAMERA_BASE, CAMERA_SIZE)
    status = client.call("debugger.status", {})
    return {
        "fields": fields,
        "camera_block_sha256": _sha256_bytes(data),
        "working_actions": _read_int(client, ACTION_WORD, 2),
        "mode": _read_int(client, MODE_WORD, 4, signed=True),
        "orbit_bias": _read_int(client, ORBIT_BIAS, 4, signed=True),
        "neutral_tracking_step": _read_int(
            client, NEUTRAL_TRACKING_STEP, 4, signed=True),
        "vertical_target": _read_int(client, VERTICAL_TARGET, 4, signed=True),
        "pitch_step": _read_int(client, PITCH_STEP, 2, signed=True),
        "pause_flag": _read_int(client, PAUSE_FLAG, 2),
        "scene": _read_int(client, SCENE_WORD, 4),
        "player_heading": _read_int(client, PLAYER_BASE + 0x20, 4),
        "player_lifecycle": {
            "health": _read_int(client, PLAYER_BASE + 0x94, 2, signed=True),
            "lives": _read_int(client, PLAYER_BASE + 0xA0, 1),
        },
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _load_anchor(client: Any, path: Path) -> dict[str, Any]:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    if loaded.get("loaded") is not True:
        raise SystemExit(f"state load failed: {path}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return loaded


def _set_buttons(client: Any, buttons: dict[str, bool]) -> None:
    client.call("emulator.clearControllerState", {"port": 0})
    if buttons:
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": buttons})


def _sample_frames(client: Any, frames: int) -> list[dict[str, Any]]:
    rows = []
    for _ in range(frames):
        client.call("emulator.advanceFrames", {"frames": 1})
        rows.append(_snapshot(client))
    return rows


def _branch(client: Any, buttons: dict[str, bool],
            *, hold: int = HOLD_FRAMES,
            release: int = RELEASE_FRAMES) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    before = _snapshot(client)
    _set_buttons(client, buttons)
    held = _sample_frames(client, hold)
    _set_buttons(client, {})
    released = _sample_frames(client, release)
    return {"buttons": buttons, "before": before, "held": held,
            "released": released}


def _changed_position(before: dict[str, Any], after: dict[str, Any]) -> bool:
    names = ("position_x", "position_y", "position_z",
             "target_x", "target_y", "target_z")
    return any(before["fields"][name] != after["fields"][name]
               for name in names)


def _run_controls(client: Any) -> dict[str, Any]:
    cases = {
        "neutral": _branch(client, {}, hold=24, release=1),
        "l1": _branch(client, {"l1": True}),
        "r1": _branch(client, {"r1": True}),
        "l1_up": _branch(client, {"l1": True, "up": True}),
        "l1_down": _branch(client, {"l1": True, "down": True}),
        "l1_left": _branch(client, {"l1": True, "left": True}),
        "l1_right": _branch(client, {"l1": True, "right": True}),
        "l1_r1": _branch(client, {"l1": True, "r1": True}),
    }
    final = {name: row["held"][-1] for name, row in cases.items()}
    summaries = {
        name: {
            "held_modes": sorted({sample["mode"] for sample in row["held"]}),
            "held_distance_min": min(sample["fields"]["distance"] for sample in row["held"]),
            "held_distance_max": max(sample["fields"]["distance"] for sample in row["held"]),
            "held_vertical_target_min": min(sample["vertical_target"] for sample in row["held"]),
            "held_vertical_target_max": max(sample["vertical_target"] for sample in row["held"]),
            "held_orbit_bias_max": max(sample["orbit_bias"] for sample in row["held"]),
            "held_orbit_bias_min": min(sample["orbit_bias"] for sample in row["held"]),
            "final_mode": row["held"][-1]["mode"],
            "final_distance": row["held"][-1]["fields"]["distance"],
            "final_vertical_target": row["held"][-1]["vertical_target"],
            "final_orbit_bias": row["held"][-1]["orbit_bias"],
            "final_orbit_yaw": row["held"][-1]["fields"]["orbit_yaw"],
            "final_pitch_step": row["held"][-1]["pitch_step"],
            "camera_changed": _changed_position(row["before"], row["held"][-1]),
            "release_mode": row["released"][-1]["mode"],
            "release_distance": row["released"][-1]["fields"]["distance"],
            "release_vertical_target": row["released"][-1]["vertical_target"],
            "release_orbit_bias": row["released"][-1]["orbit_bias"],
            "release_suppression_timer": (
                row["released"][-1]["fields"]["profile_and_suppression"] >> 8),
        } for name, row in cases.items()
    }
    if summaries["neutral"]["held_modes"] != [0] or \
            summaries["neutral"]["camera_changed"]:
        raise SystemExit(f"neutral camera control moved: {summaries['neutral']}")
    if summaries["l1"]["final_mode"] != MODE_L1 or \
            abs(summaries["l1"]["final_distance"] - L1_DISTANCE) > 32 or \
            not summaries["l1"]["camera_changed"]:
        raise SystemExit(f"L1 camera law failed: {summaries['l1']}")
    if summaries["r1"]["final_mode"] != MODE_R1 or \
            abs(summaries["r1"]["final_distance"] - R1_DISTANCE) > 32 or \
            summaries["r1"]["final_vertical_target"] != R1_VERTICAL_TARGET:
        raise SystemExit(f"R1 camera law failed: {summaries['r1']}")
    if summaries["l1_up"]["final_vertical_target"] != L1_UP_VERTICAL_TARGET or \
            summaries["l1_down"]["final_vertical_target"] != L1_DOWN_VERTICAL_TARGET or \
            abs(summaries["l1_down"]["final_orbit_bias"] -
                L1_DOWN_ORBIT_BIAS) > 2304:
        raise SystemExit(f"L1 directional vertical controls failed: {summaries}")
    if summaries["l1_r1"]["final_mode"] != MODE_L1 or \
            abs(summaries["l1_r1"]["final_distance"] - L1_DISTANCE) > 32:
        raise SystemExit(f"L1/R1 precedence failed: {summaries['l1_r1']}")
    if final["l1_left"]["pitch_step"] <= 0 or \
            final["l1_right"]["pitch_step"] >= 0:
        raise SystemExit("L1 left/right orbit directions failed")
    for name in ("l1", "r1", "l1_up", "l1_down", "l1_left", "l1_right", "l1_r1"):
        row = summaries[name]
        if (row["release_mode"], row["release_distance"],
                row["release_vertical_target"], row["release_orbit_bias"],
                row["release_suppression_timer"]) != (0, 900, 12288, 0, 0):
            raise SystemExit(f"camera release/reset failed: {name}: {row}")
    return {"summary": summaries, "cases": cases}


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = {}
    for index, (label, save) in enumerate(anchors, 1):
        _load_anchor(client, ROOT / save)
        before = _snapshot(client)
        client.call("emulator.advanceFrames", {"frames": 16})
        neutral = _snapshot(client)
        _load_anchor(client, ROOT / save)
        _set_buttons(client, {"l1": True})
        client.call("emulator.advanceFrames", {"frames": 16})
        l1 = _snapshot(client)
        _load_anchor(client, ROOT / save)
        _set_buttons(client, {"r1": True})
        client.call("emulator.advanceFrames", {"frames": 16})
        r1 = _snapshot(client)
        _set_buttons(client, {})
        rows[label] = {"save": save, "before": before, "neutral": neutral,
                       "l1": l1, "r1": r1}
        print(f"[camera-breadth] {index:02d}/{len(anchors)} {label}: "
              f"modes={l1['mode']}/{r1['mode']}")
    l1_modes = sorted({row["l1"]["mode"] for row in rows.values()})
    r1_modes = sorted({row["r1"]["mode"] for row in rows.values()})
    l1_changed_labels = sorted(label for label, row in rows.items()
                               if _changed_position(row["neutral"], row["l1"]))
    r1_changed_labels = sorted(label for label, row in rows.items()
                               if _changed_position(row["neutral"], row["r1"]))
    changed_l1 = len(l1_changed_labels)
    changed_r1 = len(r1_changed_labels)
    standard = sorted(label for label, row in rows.items()
                      if (row["l1"]["mode"], row["r1"]["mode"]) == (2, 3))
    l1_only = sorted(label for label, row in rows.items()
                     if (row["l1"]["mode"], row["r1"]["mode"]) == (2, 0))
    disabled = sorted(label for label, row in rows.items()
                      if (row["l1"]["mode"], row["r1"]["mode"]) == (0, 0))
    r1_mode_without_output_change = sorted(
        label for label, row in rows.items()
        if row["r1"]["mode"] == 3 and label not in r1_changed_labels)
    summary = {"anchors_compared": len(rows), "l1_modes": l1_modes,
               "r1_modes": r1_modes, "l1_camera_changed_anchors": changed_l1,
               "r1_camera_changed_anchors": changed_r1,
               "l1_camera_changed_labels": l1_changed_labels,
               "r1_camera_changed_labels": r1_changed_labels,
               "standard_manual_labels": standard,
               "l1_only_labels": l1_only,
               "manual_disabled_labels": disabled,
               "r1_mode_without_16_frame_output_change_labels":
               r1_mode_without_output_change,
               "labels": list(rows)}
    if len(rows) != 19 or l1_modes != [0, 2] or r1_modes != [0, 3] or \
            len(standard) != 17 or l1_only != ["stage09_bug_bar"] or \
            disabled != ["stage14_riverbed_flight"] or \
            r1_mode_without_output_change != ["bonus2_mushrooms"] or \
            changed_l1 != 18 or changed_r1 != 16:
        raise SystemExit(f"camera gameplay breadth failed: {summary}")
    return {"summary": summary, "anchors": rows}


def _run_pause(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    _set_buttons(client, {"start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {})
    paused_before = _snapshot(client)
    _set_buttons(client, {"l1": True})
    client.call("emulator.advanceFrames", {"frames": 60})
    paused_after = _snapshot(client)
    _set_buttons(client, {"start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {"l1": True})
    client.call("emulator.advanceFrames", {"frames": 60})
    resumed = _snapshot(client)
    _set_buttons(client, {})
    result = {"paused_before": paused_before, "paused_after_l1": paused_after,
              "resumed_after_l1": resumed,
              "camera_frozen": paused_before["camera_block_sha256"] ==
              paused_after["camera_block_sha256"]}
    if paused_before["pause_flag"] != 1 or paused_after["pause_flag"] != 1 or \
            not result["camera_frozen"] or paused_after["mode"] != 0 or \
            resumed["pause_flag"] != 0 or resumed["mode"] != 2:
        raise SystemExit(f"camera pause/resume failed: {result}")
    return result


def _checked_write(client: Any, method: str, address: int,
                   value: int) -> dict[str, Any]:
    width = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    result = client.call(method, {
        "address": f"0x{address:08X}", "value": value & ((1 << width * 8) - 1)})
    if result.get("written") != width:
        raise SystemExit(f"debugger write failed: {method}: {result}")
    return result


def _run_respawn(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    _set_buttons(client, {"l1": True})
    client.call("emulator.advanceFrames", {"frames": 20})
    armed = _snapshot(client)
    _set_buttons(client, {})
    actor_id, actor_x, actor_y, actor_z = struct.unpack(
        "<Iiii", _read_memory(client, ACTOR_RECORD_BASE, 16))
    writes = [_checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0)]
    for address, value in (
        (PLAYER_BASE + 0x00, actor_x), (PLAYER_BASE + 0x10, actor_x),
        (PLAYER_BASE + 0x04, actor_y), (PLAYER_BASE + 0x14, actor_y),
        (PLAYER_BASE + 0x08, actor_z), (PLAYER_BASE + 0x18, actor_z),
    ):
        writes.append(_checked_write(client, "debugger.writeU32", address, value))
    before = _snapshot(client)
    flow, respawn = [], None
    for _ in range(8):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        lives = row["player_lifecycle"]["lives"]
        health = row["player_lifecycle"]["health"]
        if lives == before["player_lifecycle"]["lives"] - 1 and health == 4:
            respawn = {**row, "lives": lives, "health": health}
            break
    reentry = None
    if respawn is not None:
        _set_buttons(client, {"l1": True})
        client.call("emulator.advanceFrames", {"frames": 20})
        reentry = _snapshot(client)
    _set_buttons(client, {})
    result = {"anchor": LIFECYCLE_ANCHOR, "actor": {
        "id": actor_id, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes, "armed": armed, "before": before,
        "flow": flow, "respawn": respawn, "l1_reentry": reentry}
    if armed["mode"] != 2 or respawn is None or reentry is None or \
            respawn["mode"] != 0 or respawn["fields"]["distance"] != 900 or \
            respawn["fields"]["profile_and_suppression"] & 0xFF not in range(6) or \
            reentry["mode"] != 2:
        raise SystemExit(f"camera respawn lifecycle failed: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id")}


def _trace_branch(client: Any, label: str,
                  buttons: dict[str, bool]) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    client.call("accessLog.clear", {})
    specifications = [
        {"address": f"0x{ACTION_WORD:08X}", "length": 2, "type": "read",
         "label": "decoded_action_camera_reads", "max_events": 128,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x8004DF18", "max": "0x8004EA8B"}}},
        {"address": f"0x{MODE_WORD:08X}", "length": 4, "type": "readwrite",
         "label": "manual_mode_writers_and_hud_readers", "max_events": 256,
         "stop_on_hit": False},
        {"address": f"0x{CAMERA_BASE + 0x1E:08X}", "length": 2,
         "type": "write", "label": "distance_writers", "max_events": 128,
         "stop_on_hit": False},
        {"address": f"0x{CAMERA_BASE + 0x20:08X}", "length": 4,
         "type": "write", "label": "orbit_and_timer_writers", "max_events": 256,
         "stop_on_hit": False},
        {"address": f"0x{VERTICAL_TARGET:08X}", "length": 4,
         "type": "write", "label": "vertical_target_writer", "max_events": 128,
         "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    _set_buttons(client, buttons)
    trace = client.call("accessLog.run", {"frames": 16})
    _set_buttons(client, {})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 32}) for watch in watches]
    client.call("accessLog.clear", {})
    events = [_trim_event(row) for row in trace.get("events") or []]
    result = {"label": label, "buttons": buttons,
              "specifications": specifications, "watches": watches,
              "events": events, "summaries": summaries,
              "total": trace.get("total"),
              "truncated": trace.get("truncated", False),
              "observed_instruction_pcs": sorted({
                  str(row.get("instruction_pc")).lower() for row in events})}
    if result["truncated"] or any(row.get("truncated") for row in summaries):
        raise SystemExit(f"camera trace truncated: {result}")
    return result


def _run_writer_trace(client: Any) -> dict[str, Any]:
    l1 = _trace_branch(client, "l1", {"l1": True})
    r1 = _trace_branch(client, "r1", {"r1": True})
    l1_pcs, r1_pcs = set(l1["observed_instruction_pcs"]), set(r1["observed_instruction_pcs"])
    if not {"0x8004dfd4", "0x8004dff0", "0x8004e01c",
            "0x8004e4c0"} <= l1_pcs:
        raise SystemExit(f"L1 decisive writers absent: {l1}")
    if not {"0x8004dfd4", "0x8004e070", "0x8004e1cc",
            "0x8004e490"} <= r1_pcs:
        raise SystemExit(f"R1 decisive writers absent: {r1}")
    return {"l1": l1, "r1": r1}


def _verify_base_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / BASE_MOVIE
    pin = (json.loads(FIXTURE_SET.read_text()).get("entries") or {}).get(BASE_MOVIE)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot movie lacks exact central pin: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("LEVEL01 movie is not a v3 from-boot anchor")
    frames = movie.get("frames") or []
    if MOVIE_EDIT_END > len(frames):
        raise SystemExit("camera movie edit exceeds frame count")
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((frames[index].get("ports") or {}).get("0") or {})
        if pad.get("up") is not True or any(pad.get(button) for button in (
                "l1", "r1", "l2", "cross", "circle", "square", "triangle",
                "start", "select")):
            raise SystemExit(f"camera movie source window is not Up-only: {index}")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _movie_cleanup(client: Any) -> None:
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass


def _run_cold_boot(client: Any) -> dict[str, Any]:
    movie, pin = _verify_base_movie()
    path = str((ROOT / BASE_MOVIE).resolve())
    _movie_cleanup(client)
    registry_ids = []
    try:
        loaded = client.call("movie.load", {"path": path})
        started = client.call("movie.startPlayback", {"load_start_state": True})
        client.call("debugger.pause", {})
        client.call("movie.advanceToFrame", {"frame": MOVIE_PRE_EDIT,
                                              "max_frames": 9000}, timeout=900)
        client.call("debugger.pause", {})
        control_before = _snapshot(client)
        client.call("movie.advanceToFrame", {"frame": MOVIE_EDIT_END,
                                              "max_frames": 100}, timeout=900)
        client.call("debugger.pause", {})
        control_after = _snapshot(client)
        control_status = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})
        stored = client.call("movie.store", {})
        registry_ids.append(stored["movieId"])
        branches = {}
        for button, expected_mode in (("l1", 2), ("r1", 3)):
            branch = client.call("movie.branch", {
                "movieId": stored["movieId"], "fromFrame": len(movie["frames"])})
            branch_id = branch["movieId"]
            registry_ids.append(branch_id)
            edits = []
            for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
                pad = dict(movie["frames"][index]["ports"]["0"])
                pad[button] = True
                edits.append(client.call("movie.editFrame", {
                    "movieId": branch_id, "frame": index,
                    "input": {"0": pad}}))
            activated = client.call("movie.activate", {"movieId": branch_id})
            branch_started = client.call(
                "movie.startPlayback", {"load_start_state": True})
            client.call("debugger.pause", {})
            client.call("movie.advanceToFrame", {"frame": MOVIE_PRE_EDIT,
                                                  "max_frames": 9000}, timeout=900)
            client.call("debugger.pause", {})
            before = _snapshot(client)
            client.call("movie.advanceToFrame", {"frame": MOVIE_EDIT_END,
                                                  "max_frames": 100}, timeout=900)
            client.call("debugger.pause", {})
            after = _snapshot(client)
            status = client.call("movie.status", {})
            client.call("movie.stopPlayback", {})
            branches[button] = {"branch": branch, "activated": activated,
                                "started": branch_started, "edits": edits,
                                "before": before, "after": after, "movie": status,
                                "expected_mode": expected_mode,
                                "pre_edit_camera_equal": before["camera_block_sha256"] ==
                                control_before["camera_block_sha256"]}
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
    result = {"base_movie": pin, "metadata": {
        "format": movie.get("format"), "version": movie.get("version"),
        "frame_count": len(movie["frames"]), "from_boot": True},
        "edit_recipe": {"buttons_added": ["l1", "r1"],
                        "start_frame": MOVIE_EDIT_START,
                        "pre_edit_checkpoint": MOVIE_PRE_EDIT,
                        "end_frame_exclusive": MOVIE_EDIT_END,
                        "edited_frames_per_branch": MOVIE_EDIT_END - MOVIE_EDIT_START},
        "control": {"loaded": loaded, "started": started,
                    "before": control_before, "after": control_after,
                    "movie": control_status}, "branches": branches}
    statuses = [started, control_status]
    for row in branches.values():
        statuses.extend([row["started"], row["movie"]])
    if any(row.get("reproducible") is not True or row.get("truncated") is not False
           for row in statuses):
        raise SystemExit(f"camera cold-boot movie not reproducible: {result}")
    for button, expected in (("l1", 2), ("r1", 3)):
        branch = branches[button]
        if not branch["pre_edit_camera_equal"] or branch["before"]["cycle"] != \
                control_before["cycle"] or branch["after"]["mode"] != expected or \
                not _changed_position(control_after, branch["after"]):
            raise SystemExit(f"camera cold-boot branch failed: {button}: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static camera census failed: {static_census_gaps(static)}")
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
        "debugger.capabilities", "debugger.pause", "debugger.readMemory", "debugger.readStruct",
        "debugger.writeU16", "debugger.writeU32", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "accessLog.addWatch", "accessLog.run",
        "accessLog.summary", "accessLog.clear", "movie.load", "movie.store",
        "movie.branch", "movie.editFrame", "movie.activate",
        "movie.startPlayback", "movie.advanceToFrame", "movie.stopPlayback",
        "movie.status", "movie.remove", "movie.clear",
    }
    missing = sorted(name for name in required_methods
                     if not _method_present(capabilities, name))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    cold_boot = _run_cold_boot(client)
    controls = _run_controls(client)
    breadth = _run_breadth(client, anchors)
    pause = _run_pause(client)
    trace = _run_writer_trace(client)
    respawn = _run_respawn(client)
    _set_buttons(client, {})
    client.call("accessLog.clear", {})
    _movie_cleanup(client)

    run_provenance = finish_run(
        args, generator="tools/phase4_camera_controls.py",
        anchor={
            "type": "from-boot edited L1/R1 controls plus strict-pristine gameplay breadth and lifecycle",
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
            "settle_frames": SETTLE_FRAMES, "hold_frames": HOLD_FRAMES,
            "release_frames": RELEASE_FRAMES,
            "breadth_hold_frames": 16,
            "cold_boot_edit": cold_boot["edit_recipe"],
        })
    document = {
        "_comment": (
            "Phase-4 A17 pristine manual-camera evidence. Retail bytes bind "
            "the reset, L1/R1 selector, typed state, smoothing and HUD reader; "
            "live evidence supplies cold boot, exact controls, 19-anchor breadth, "
            "pause, writer attribution and native same-scene respawn."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {"cold_boot": cold_boot, "controls": controls,
                 "breadth": breadth, "pause_resume": pause,
                 "writer_trace": trace, "death_respawn": respawn},
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[camera] retained A17 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_camera_controls.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
