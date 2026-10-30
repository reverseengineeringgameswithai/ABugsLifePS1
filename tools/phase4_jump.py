#!/usr/bin/env python3
"""Regenerate the Phase-4 A03 jump-controller campaign from pristine evidence.

Static mode re-reads the hash-pinned retail executable.  Live mode retains a
timing-matched cold-boot counterfactual, the hold/release curve, native
super-jump and coyote controls, gameplay breadth, lifecycle controls, and
instruction-attributed readers/writers.  Save states are accepted only through
the central strict-pristine fixture inventory; they supplement rather than
replace the cold boot.
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
OUTPUT = ROOT / "analysis/phase4_jump.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_FN = (0x80048138, 0x800498AC)
JUMP_BRANCH = (0x80048B2C, 0x80048D94)
TAKEOFF_BRANCH = (0x80048B60, 0x80048C00)
RELEASE_GRAVITY = (0x80048D14, 0x80048D94)
ACTION_WORD = 0x80082488
COYOTE_GUARD = 0x80082434
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
RECORD_BASE = 0x8009FE04

CROSS_MASK = 0x4000
SUPER_FLAG = 0x0020
NORMAL_IMPULSE = -3072
SUPER_IMPULSE = -3776
GRAVITY_STEP = 256
TERMINAL_VELOCITY = 4096
RELEASE_THRESHOLD = -800
RELEASE_BIAS = 384
RELEASE_FINAL_BIAS = -256
COYOTE_DISTANCE_EXCLUSIVE = 1024
RISE_STATE = 1
RELEASED_STATE = 2
RISE_ANIMATION = 3
FLIGHT_ANIMATION = 4

SETTLE_FRAMES = 2
CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
EXCEPTION_LABEL = "stage14_riverbed_flight"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8011
MOVIE_EDIT_END = 8039
MOVIE_OBSERVE_FRAME = 8025

EXPECTED_WORDS = {
    "power_flags_load": (0x80048184, 0x96220090),
    "super_flag_mask": (0x8004818C, 0x30420020),
    "normal_impulse": (0x80048194, 0x2413F400),
    "super_impulse": (0x80048198, 0x2413F140),
    "special_mode_load": (0x80048B2C, 0x922400A3),
    "flight_mode_14": (0x80048B30, 0x2402000E),
    "flight_jump_bypass": (0x80048B34, 0x10820096),
    "action_word_load": (0x80048B60, 0x94422488),
    "cross_mask": (0x80048B68, 0x30424000),
    "coyote_distance": (0x80048BAC, 0x28420400),
    "coyote_guard_load": (0x80048BB8, 0x8F82069C),
    "impulse_select": (0x80048BD8, 0x0260A021),
    "takeoff_state_writer": (0x80048BDC, 0xA6220080),
    "takeoff_grounded_clear": (0x80048BE8, 0xA6200082),
    "takeoff_animation_writer": (0x80048BF4, 0xA6230088),
    "release_state_read": (0x80048D14, 0x86230080),
    "release_bias": (0x80048D34, 0x001417C2),
    "release_state_writer": (0x80048D50, 0xA6220080),
    "gravity_step": (0x80048D78, 0x26940100),
    "terminal_velocity": (0x80048D88, 0x24141000),
    "velocity_commit": (0x80048D8C, 0xAE340030),
    "collision_integrator_call": (0x800495C8, 0x0C00D8CF),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "floor_y", "offset": 0x48, "type": "s32"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "power_flags", "offset": 0x90, "type": "u16"},
    {"name": "health", "offset": 0x94, "type": "s16"},
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


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine jump word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "player_vertical_update": PLAYER_FN,
        "jump_branch": JUMP_BRANCH,
        "takeoff_branch": TAKEOFF_BRANCH,
        "release_gravity": RELEASE_GRAVITY,
    }.items():
        data = _region(exe, bounds)
        regions[name] = {
            "start": f"0x{bounds[0]:08X}",
            "end_exclusive": f"0x{bounds[1]:08X}",
            "length": len(data),
            "sha256": _sha256_bytes(data),
        }
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "regions": regions,
        "instruction_words": words,
        "law": {
            "action_word": f"0x{ACTION_WORD:08X}",
            "cross_mask": CROSS_MASK,
            "normal_impulse": NORMAL_IMPULSE,
            "super_impulse": SUPER_IMPULSE,
            "super_flag": SUPER_FLAG,
            "gravity_step_per_player_update": GRAVITY_STEP,
            "terminal_velocity": TERMINAL_VELOCITY,
            "release_threshold": RELEASE_THRESHOLD,
            "release_bias_before_halving": RELEASE_BIAS,
            "release_bias_after_halving": RELEASE_FINAL_BIAS,
            "coyote_distance_exclusive": COYOTE_DISTANCE_EXCLUSIVE,
            "coyote_guard": f"0x{COYOTE_GUARD:08X}",
            "takeoff_state": RISE_STATE,
            "released_state": RELEASED_STATE,
            "rise_animation": RISE_ANIMATION,
            "ordinary_owner": "resident 0x80048138..0x800498AB",
            "collision_owner": "resident movement/collision integrator 0x8003633C",
            "overlays": "none for the ordinary jump controller",
        },
        "source_status": {
            "asm": "asm/hand_written/80048138_player_vertical_update.s (byte-matched build unit)",
            "semantic_c": "src_re/player_update_80048138.c (documentation-grade, not build input)",
            "matching_c": "none; authoritative implementation remains the byte-matched assembly",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    for key, expected, message in (
        ("cross_mask", CROSS_MASK, "jump input mask is not Cross 0x4000"),
        ("normal_impulse", NORMAL_IMPULSE, "normal takeoff impulse is not -3072"),
        ("super_impulse", SUPER_IMPULSE, "super takeoff impulse is not -3776"),
        ("gravity_step_per_player_update", GRAVITY_STEP, "gravity step is not 256"),
        ("terminal_velocity", TERMINAL_VELOCITY, "terminal velocity is not 4096"),
        ("coyote_distance_exclusive", COYOTE_DISTANCE_EXCLUSIVE,
         "coyote threshold is not the exclusive 1024-unit bound"),
    ):
        if law.get(key) != expected:
            gaps.append(message)
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive jump instruction census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(row["hex"])


def _read_u16(client: Any, address: int) -> int:
    return int.from_bytes(_read_memory(client, address, 2), "little")


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
        "working_actions": _read_u16(client, ACTION_WORD),
        "pause_flag": _read_u16(client, PAUSE_FLAG),
        "scene": int.from_bytes(_read_memory(client, SCENE_WORD, 4), "little"),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _field_differences(left: dict[str, Any], right: dict[str, Any],
                       names: list[str] | None = None) -> list[str]:
    names = names or list(left["fields"])
    return [name for name in names
            if left["fields"].get(name) != right["fields"].get(name)]


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


def _jump_branch(client: Any, path: Path, *, hold_frames: int = 4,
                 post_release_frames: int = 80,
                 modifier: str = "normal") -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _snapshot(client)
    writes = []
    if modifier == "super_flag_0x20":
        value = before["fields"]["power_flags"] | SUPER_FLAG
        writes.append(_checked_write(client, "debugger.writeU16",
                                     PLAYER_BASE + 0x90, value))
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    samples = []
    for _ in range(hold_frames):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
    client.call("emulator.clearControllerState", {"port": 0})
    for _ in range(post_release_frames):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
        if samples[-1]["fields"]["grounded"] != 0 and any(
                row["fields"]["grounded"] == 0 for row in samples):
            # One extra native player update interval exposes the state reset.
            client.call("emulator.advanceFrames", {"frames": 6})
            samples.append(_snapshot(client))
            break
    ys = [row["fields"]["y"] for row in samples]
    update_rows = []
    previous = before
    for row in samples:
        if row["fields"]["velocity_y"] != previous["fields"]["velocity_y"] or \
                row["fields"]["state"] != previous["fields"]["state"]:
            update_rows.append(row)
        previous = row
    result = {
        "load": loaded, "modifier": modifier, "writes": writes,
        "held_emulator_frames": hold_frames,
        "released_emulator_frames": len(samples) - hold_frames,
        "before": before, "samples": samples,
        "player_update_observations": update_rows,
        "apex_y": min(ys), "height": before["fields"]["y"] - min(ys),
        "became_airborne": any(row["fields"]["grounded"] == 0 for row in samples),
        "returned_grounded": samples[-1]["fields"]["grounded"] != 0,
        "state_sequence": [row["fields"]["state"] for row in update_rows],
        "animation_sequence": [row["fields"]["animation"] for row in update_rows],
    }
    return result


def _run_curve_and_modifiers(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR
    curve = [_jump_branch(client, path, hold_frames=frames)
             for frames in (1, 2, 4, 8, 12, 20)]
    heights = [row["height"] for row in curve]
    if heights != sorted(heights) or len(set(heights)) < 5:
        raise SystemExit(f"jump height did not grow with held Cross: {heights}")
    normal = _jump_branch(client, path, hold_frames=2)
    super_jump = _jump_branch(
        client, path, hold_frames=2, modifier="super_flag_0x20")
    if super_jump["height"] <= normal["height"] or \
            not (super_jump["samples"][0]["fields"]["power_flags"] & SUPER_FLAG):
        raise SystemExit("native super-jump flag did not strengthen takeoff")
    return {"hold_release_curve": curve, "height_curve": heights,
            "normal": normal, "super_flag_0x20": super_jump}


def _run_coyote_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR

    def branch(distance: int, guard: int) -> dict[str, Any]:
        _load_anchor(client, path)
        before = _snapshot(client)
        floor_y = before["fields"]["floor_y"]
        writes = [
            _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x82, 0),
            _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x80, 0),
            _checked_write(client, "debugger.writeU32", PLAYER_BASE + 0x30, 0),
            _checked_write(client, "debugger.writeU32", PLAYER_BASE + 0x04,
                           (floor_y - distance) & 0xFFFFFFFF),
            _checked_write(client, "debugger.writeU32", COYOTE_GUARD, guard),
        ]
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": {"cross": True}})
        samples = []
        for _ in range(6):
            client.call("emulator.advanceFrames", {"frames": 1})
            samples.append(_snapshot(client))
            fields = samples[-1]["fields"]
            if fields["state"] != 0 or fields["velocity_y"] != 0 or \
                    fields["y"] != floor_y - distance:
                break
        after = samples[-1]
        client.call("emulator.clearControllerState", {"port": 0})
        return {"distance": distance, "guard": guard, "writes": writes,
                "before": before, "samples": samples, "after": after}

    inside = branch(512, 0)
    boundary = branch(COYOTE_DISTANCE_EXCLUSIVE, 0)
    guarded = branch(512, 1)
    if inside["after"]["fields"]["state"] != RISE_STATE or \
            inside["after"]["fields"]["grounded"] != 0:
        raise SystemExit(f"inside-threshold coyote positive failed: {inside}")
    if boundary["after"]["fields"]["state"] == RISE_STATE or \
            guarded["after"]["fields"]["state"] == RISE_STATE:
        raise SystemExit(
            "coyote threshold/guard negative control failed: "
            f"boundary_state={boundary['after']['fields']['state']} "
            f"guarded_state={guarded['after']['fields']['state']}")
    return {"inside_512_guard_clear": inside,
            "boundary_1024_guard_clear": boundary,
            "inside_512_guard_set": guarded}


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    for index, (label, save) in enumerate(anchors, 1):
        path = ROOT / save
        neutral = _jump_branch(client, path, hold_frames=0,
                               post_release_frames=16)
        cross = _jump_branch(client, path, hold_frames=4,
                             post_release_frames=52)
        result = {
            "save": save, "neutral": neutral, "cross": cross,
            "cross_observed": any(
                row["working_actions"] & CROSS_MASK for row in cross["samples"]),
        }
        if label == EXCEPTION_LABEL:
            names = ["x", "y", "z", "velocity_y", "state", "grounded", "animation"]
            result["outcome_differences"] = _field_differences(
                neutral["samples"][15], cross["samples"][15], names)
        results[label] = result
        print(f"[jump] {index:02d}/{len(anchors)} {label}: "
              f"height={cross['height']} air={cross['became_airborne']} "
              f"anim={cross['samples'][0]['fields']['animation']}")
    applicable = [label for label in results if label != EXCEPTION_LABEL]
    airborne = sorted(label for label in applicable
                      if results[label]["cross"]["became_airborne"])
    landed = sorted(label for label in applicable
                    if results[label]["cross"]["returned_grounded"])
    rise_anim = sorted(label for label in applicable if any(
        row["fields"]["animation"] == RISE_ANIMATION
        for row in results[label]["cross"]["samples"]))
    summary = {
        "anchors_compared": len(results),
        "applicable_anchors": len(applicable),
        "applicable_labels": applicable,
        "airborne_labels": airborne,
        "returned_grounded_labels": landed,
        "rise_animation_3_labels": rise_anim,
        "exception_label": EXCEPTION_LABEL,
        "exception_outcome_differences":
            results[EXCEPTION_LABEL]["outcome_differences"],
        "exception_animation": results[EXCEPTION_LABEL]["cross"][
            "samples"][15]["fields"]["animation"],
        "exception_special_mode_observed": results[EXCEPTION_LABEL]["cross"][
            "samples"][15]["fields"]["special_mode"],
        "exception_state": results[EXCEPTION_LABEL]["cross"][
            "samples"][15]["fields"]["state"],
    }
    if len(results) != 19 or len(applicable) != 18:
        raise SystemExit(f"unexpected jump breadth: {summary}")
    for key in ("airborne_labels", "returned_grounded_labels",
                "rise_animation_3_labels"):
        if len(summary[key]) != 18:
            raise SystemExit(f"jump breadth predicate failed ({key}): {summary}")
    if set(summary["exception_outcome_differences"]) != {
            "x", "y", "z", "velocity_y"} or \
            summary["exception_animation"] != FLIGHT_ANIMATION or \
            summary["exception_state"] != 0:
        raise SystemExit(f"flight exceptional path changed boundary: {summary}")
    return {"summary": summary, "anchors": results}


def _run_pause_control(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
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
    frozen_names = ["x", "y", "z", "velocity_y", "state", "grounded", "animation"]
    frozen = [name for name in frozen_names
              if paused_start["fields"][name] == paused_neutral["fields"][name]]
    result = {"paused_start": paused_start, "paused_after_neutral": paused_neutral,
              "cross_confirmed_resume_and_jump": resumed,
              "frozen_fields": frozen}
    if paused_start["pause_flag"] != 1 or paused_neutral["pause_flag"] != 1 or \
            frozen != frozen_names or resumed["pause_flag"] != 0 or \
            resumed["fields"]["grounded"] != 0 or \
            resumed["fields"]["state"] != RISE_STATE:
        raise SystemExit(f"jump pause/resume failed: {result}")
    return result


def _run_respawn_control(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    rid, actor_x, actor_y, actor_z = struct.unpack(
        "<Iiii", _read_memory(client, RECORD_BASE, 16))
    writes = [_checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0)]
    for address, value in (
        (PLAYER_BASE + 0x00, actor_x), (PLAYER_BASE + 0x10, actor_x),
        (PLAYER_BASE + 0x04, actor_y), (PLAYER_BASE + 0x14, actor_y),
        (PLAYER_BASE + 0x08, actor_z), (PLAYER_BASE + 0x18, actor_z),
    ):
        writes.append(_checked_write(
            client, "debugger.writeU32", address, value & 0xFFFFFFFF))
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
        raise SystemExit("native respawn did not complete")
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    post = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "perturbation": "health:=0; position+mirror:=first actor; jump after native respawn",
        "actor": {"id": rid, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes, "before": before, "flow": flow,
        "respawn": respawn, "post_respawn_jump": post,
    }
    if respawn["scene"] != before["scene"] or \
            post["fields"]["grounded"] != 0 or \
            post["fields"]["state"] != RISE_STATE:
        raise SystemExit(f"jump did not reinitialize after native respawn: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    row = {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id", "regs")}
    return row


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    specifications = [
        {"address": "0x80082488", "length": 2, "type": "read",
         "label": "cross_action_read", "max_events": 64,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x80048138", "max": "0x800498AB"}}},
        {"address": "0x800A6580", "length": 2, "type": "write",
         "label": "jump_state_writer", "max_events": 64, "stop_on_hit": False},
        {"address": "0x800A6582", "length": 2, "type": "write",
         "label": "grounded_writer", "max_events": 64, "stop_on_hit": False},
        {"address": "0x800A6530", "length": 4, "type": "write",
         "label": "velocity_y_writer", "max_events": 64, "stop_on_hit": False},
        {"address": "0x800A6504", "length": 4, "type": "write",
         "label": "position_y_writer", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A6588", "length": 2, "type": "write",
         "label": "animation_writer", "max_events": 64, "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    exec_specs = [
        ("cross_read", 0x80048B60, ["v0", "v1", "s1", "s3", "s4"]),
        ("takeoff", 0x80048BDC, ["v0", "s1", "s3", "s4"]),
        ("release", 0x80048D14, ["v0", "v1", "s1", "s4"]),
        ("velocity_commit", 0x80048D8C, ["s1", "s4"]),
        ("collision_call", 0x800495C8, ["s1", "s4", "a0"]),
    ]
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture, "label": label,
        "max_events": 32}) for label, pc, capture in exec_specs]
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 4})
    client.call("emulator.clearControllerState", {"port": 0})
    access = client.call("accessLog.run", {"frames": 40})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 32}) for watch in watches]
    executions = {}
    for (label, _pc, _capture), watch in zip(exec_specs, exec_watches):
        executions[label] = client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 32})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = [_trim_event(row) for row in access.get("events") or []]
    result = {
        "specifications": specifications, "watches": watches,
        "events": events, "total": access.get("total"),
        "truncated": access.get("truncated", False),
        "summaries": summaries, "execution": executions,
    }
    pcs = {str(row.get("instruction_pc")).lower() for row in events}
    required_access = {"0x80048b60", "0x80048bdc", "0x80048be8",
                       "0x80048bf4", "0x80048d50", "0x80048d8c",
                       "0x80036cec"}
    if result["truncated"] or any(row.get("truncated") for row in summaries):
        raise SystemExit("jump writer trace truncated")
    if not required_access <= pcs:
        raise SystemExit(f"decisive jump reader/writer PCs absent: {sorted(pcs)}")
    if any(row.get("truncated") for row in executions.values()) or any(
            not (row.get("events") or []) for row in executions.values()):
        raise SystemExit(f"jump execution trace missing/truncated: {executions}")
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
        raise SystemExit("LEVEL01 jump control is not a v3 from-boot movie")
    frames = movie.get("frames") or []
    if MOVIE_OBSERVE_FRAME >= len(frames):
        raise SystemExit("jump observation frame exceeds base movie")
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((frames[index].get("ports") or {}).get("0") or {})
        if pad.get("cross") is not True or any(pad.get(button) for button in (
                "l2", "r2", "circle", "square", "triangle", "start",
                "select")):
            raise SystemExit(
                f"jump movie window no longer has isolated Cross among action/menu peers: {index}")
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
        control_started = client.call("movie.startPlayback", {
            "load_start_state": True})
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
            pad["cross"] = False
            edits.append(client.call("movie.editFrame", {
                "movieId": branch_id, "frame": index,
                "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch_id})
        edited_started = client.call("movie.startPlayback", {
            "load_start_state": True})
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
    result = {
        "base_movie": pin,
        "base_movie_metadata": {
            "format": movie.get("format"), "version": movie.get("version"),
            "frame_count": len(movie["frames"]),
            "start_state": movie.get("start_state")},
        "edit_recipe": {
            "button_removed": "cross", "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "observe_frame": MOVIE_OBSERVE_FRAME,
            "edited_frame_count": len(edits),
            "source_window_predicate": "Cross true; shoulders, action peers, and menu buttons false; original direction/analog preserved",
        },
        "control_cross": {
            "loaded": loaded, "started": control_started,
            "before": control_before, "before_movie": control_before_movie,
            "after": control_after, "after_movie": control_after_movie},
        "edited_neutral": {
            "branch": branch, "activated": activated, "started": edited_started,
            "before": edited_before, "before_movie": edited_before_movie,
            "after": edited_after, "after_movie": edited_after_movie},
        "pre_edit_field_differences": _field_differences(
            control_before, edited_before),
        "pre_edit_block_equal": control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"],
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
        "pre_edit_emulator_frame_equal": control_before["frame"] == edited_before["frame"],
        "post_edit_field_differences": _field_differences(
            control_after, edited_after),
    }
    statuses = (control_started, control_before_movie, control_after_movie,
                edited_started, edited_before_movie, edited_after_movie)
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses):
        raise SystemExit(f"cold-boot movie not reproducible: {result}")
    if result["pre_edit_field_differences"] or \
            not result["pre_edit_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["pre_edit_emulator_frame_equal"]:
        raise SystemExit(f"cold-boot branches diverged before edit: {result}")
    if control_after["scene"] != 1 or edited_after["scene"] != 1 or \
            control_after["fields"]["y"] >= edited_after["fields"]["y"] or \
            control_after["fields"]["state"] != RISE_STATE or \
            control_after["fields"]["grounded"] != 0 or \
            control_after["fields"]["animation"] != RISE_ANIMATION or \
            edited_after["fields"]["state"] != 0 or \
            edited_after["fields"]["grounded"] == 0 or \
            not result["post_edit_field_differences"] or \
            len(edits) != MOVIE_EDIT_END - MOVIE_EDIT_START:
        raise SystemExit(f"cold-boot Cross/neutral control failed: {result}")
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
        raise SystemExit(f"static jump census failed: {gaps}")
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
        "debugger.writeU32", "emulator.getMediaInfo", "emulator.getStateInfo",
        "emulator.loadState", "emulator.setControllerState",
        "emulator.clearControllerState", "emulator.advanceFrames",
        "accessLog.addWatch", "accessLog.run", "accessLog.summary",
        "accessLog.clear", "execTrace.addWatch", "execTrace.get",
        "execTrace.clear", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status",
        "movie.remove", "movie.clear",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")

    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]
    controls = _run_curve_and_modifiers(client)
    coyote = _run_coyote_controls(client)
    breadth = _run_breadth(client, anchors)
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
        args, generator="tools/phase4_jump.py",
        anchor={
            "type": "cold-boot Cross-removal counterfactual plus strict-pristine save-state breadth/lifecycle sweep",
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
            "player_update_cadence": "retained exec trace records native update frames/cycles; law constants apply per player update, never per emulator frame",
            "curve_hold_emulator_frames": [1, 2, 4, 8, 12, 20],
            "cold_boot_edit": cold_boot["edit_recipe"],
        },
    )
    document = {
        "_comment": (
            "Phase-4 A03 pristine jump-controller evidence. Retail bytes bind "
            "Cross, takeoff constants, coyote eligibility, release cut, gravity, "
            "and collision handoff. Retained live evidence reproduces cold boot, "
            "hold/release height, native modifier, breadth, lifecycle, and writer "
            "attribution. Regenerate in a fresh owned instance."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "cold_boot": cold_boot, "controls": controls,
            "coyote_controls": coyote, "breadth": breadth,
            "pause_resume": pause, "death_respawn": respawn,
            "writer_trace": trace,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[jump] retained cold-boot + {len(anchors)} anchor campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_jump.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
