#!/usr/bin/env python3
"""Regenerate the Phase-4 A01 run-locomotion campaign from pristine evidence.

The campaign bounds the resident analog/D-pad direction helper, heading turn,
horizontal acceleration/deceleration, velocity proposal, collision-consumption,
and ordinary run-animation interfaces.  It deliberately does not claim the
vertical jump state machine, special Riverbed Flight control law, or the full
E02 collision resolver as A01-owned behavior.
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
    import phase4_slow_walk as player_common
except ModuleNotFoundError:  # imported as tools.phase4_run_locomotion in tests
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
    from tools import phase4_slow_walk as player_common


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_run_locomotion.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

INPUT_HELPER = (0x80047EBC, 0x80048138)
HORIZONTAL_CONTROLLER = (0x800490B0, 0x80049544)
INTEGRATOR_COMMIT = (0x80036CD8, 0x80036CF8)
ANIMATION_GATE = (0x800566CC, 0x800566FC)

PLAYER_BASE = 0x800A6500
ACTION_WORD = 0x80082488
PAUSE_FLAG = 0x8008224E
RECORD_BASE = 0x8009FE04

DIRECTION_MASK = 0x00F0
UP_MASK = 0x0010
RIGHT_MASK = 0x0020
DOWN_MASK = 0x0040
LEFT_MASK = 0x0080
ANALOG_DEADZONE_INTERNAL = 6144
ANALOG_MAGNITUDE_CAP = 16384
HEADING_MASK = 0x0FFF
RUN_COMPONENT_TARGET = 1792
FORWARD_BOUND = 2048
LATERAL_FRICTION = 256
FORWARD_FRICTION = 64
INPUT_BOOST = 144
NET_STRAIGHT_ACCEL = INPUT_BOOST - FORWARD_FRICTION
DEFAULT_TURN_STEP = 256
RUN_ANIMATION = 0
IDLE_ANIMATION = 22
FLIGHT_ANIMATION = 4

SETTLE_FRAMES = 2
HOLD_FRAMES = 60
CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
FLIGHT_LABEL = "stage14_riverbed_flight"
BASE_MOVIE = player_common.BASE_MOVIE
MOVIE_EDIT_START = player_common.MOVIE_EDIT_START
MOVIE_EDIT_END = player_common.MOVIE_EDIT_END

EXPECTED_WORDS = {
    "analog_x_deadzone_6144": (0x80047F10, 0x28421800),
    "analog_y_deadzone_6144": (0x80047F3C, 0x28421800),
    "desired_heading_writer_analog": (0x80048044, 0xAC226528),
    "magnitude_cap_16384": (0x80048064, 0x24044000),
    "desired_heading_writer_dpad": (0x80048104, 0xAC226528),
    "magnitude_return_writer": (0x80048120, 0xAE040000),
    "direction_mask": (0x8004911C, 0x306200F0),
    "direction_helper_call": (0x80049140, 0x0C011FAF),
    "magnitude_scale": (0x80049158, 0x0009AB83),
    "stationary_heading_snap": (0x800491A4, 0xAE220020),
    "turn_difference_mask": (0x80049250, 0x30440FFF),
    "turn_step_cap_1024": (0x80049274, 0x03C02021),
    "turn_heading_writer": (0x80049298, 0xAE220020),
    "heading_domain_writer": (0x800492A8, 0xAE220020),
    "lateral_decay_negative": (0x80049348, 0x06410008),
    "forward_decay_negative": (0x8004938C, 0x06610006),
    "input_gate": (0x800493C0, 0x97A90058),
    "component_target_clamp": (0x8004942C, 0x02A09021),
    "forward_bound_load": (0x80049440, 0x8FA90030),
    "forward_component_writer": (0x800494AC, 0xAE330038),
    "lateral_component_writer": (0x800494B0, 0xAE32003C),
    "velocity_x_writer": (0x80049524, 0xAE22002C),
    "velocity_z_writer": (0x80049540, 0xAE220034),
    "integrator_call": (0x800495C8, 0x0C00D8CF),
    "resolved_x_commit": (0x80036CE8, 0xAEE20000),
    "resolved_z_commit": (0x80036CF0, 0xAEE40008),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "heading", "offset": 0x20, "type": "u32"},
    {"name": "input_heading", "offset": 0x28, "type": "u32"},
    {"name": "velocity_x", "offset": 0x2C, "type": "s32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "velocity_z", "offset": 0x34, "type": "s32"},
    {"name": "forward_component", "offset": 0x38, "type": "s32"},
    {"name": "lateral_component", "offset": 0x3C, "type": "s32"},
    {"name": "floor_y", "offset": 0x48, "type": "s32"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "health", "offset": 0x94, "type": "s16"},
    {"name": "lives", "offset": 0xA0, "type": "u8"},
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
                f"pristine run-locomotion word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "input_helper": INPUT_HELPER,
        "horizontal_controller": HORIZONTAL_CONTROLLER,
        "integrator_commit": INTEGRATOR_COMMIT,
        "animation_gate": ANIMATION_GATE,
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
            "decoded_action_word": f"0x{ACTION_WORD:08X}",
            "direction_mask": DIRECTION_MASK,
            "direction_bits": [UP_MASK, RIGHT_MASK, DOWN_MASK, LEFT_MASK],
            "analog_deadzone_internal": ANALOG_DEADZONE_INTERNAL,
            "analog_magnitude_cap": ANALOG_MAGNITUDE_CAP,
            "magnitude_scale_shift": 14,
            "heading_domain_mask": HEADING_MASK,
            "ordinary_component_target": RUN_COMPONENT_TARGET,
            "forward_bound": FORWARD_BOUND,
            "lateral_friction": LATERAL_FRICTION,
            "forward_friction": FORWARD_FRICTION,
            "input_boost": INPUT_BOOST,
            "net_straight_acceleration": NET_STRAIGHT_ACCEL,
            "default_turn_step": DEFAULT_TURN_STEP,
            "run_animation": RUN_ANIMATION,
            "owners": [
                "input direction/magnitude helper 0x80047EBC..0x80048137",
                "player horizontal controller 0x800490B0..0x80049543",
                "movement/collision integrator 0x8003633C",
                "actor animation selector 0x800563D4..0x800570F7",
            ],
        },
        "source_status": {
            "input_helper_asm": "asm/hand_written/80047ebc_sub_80047ebc.s (byte-matched build unit)",
            "player_asm": "asm/hand_written/80048138_player_vertical_update.s (byte-matched build unit)",
            "player_semantic_c": "src_re/player_update_80048138.c (documentation-grade; horizontal body not represented)",
            "integrator_semantic_c": "src_re/movement_integrator_8003633c.c (documentation-grade tail only)",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    exact = {
        "direction_mask": DIRECTION_MASK,
        "analog_deadzone_internal": ANALOG_DEADZONE_INTERNAL,
        "analog_magnitude_cap": ANALOG_MAGNITUDE_CAP,
        "heading_domain_mask": HEADING_MASK,
        "ordinary_component_target": RUN_COMPONENT_TARGET,
        "forward_bound": FORWARD_BOUND,
        "net_straight_acceleration": NET_STRAIGHT_ACCEL,
        "default_turn_step": DEFAULT_TURN_STEP,
    }
    for key, expected in exact.items():
        if law.get(key) != expected:
            gaps.append(f"{key} differs from {expected}")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive instruction census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    result = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(result["hex"])


def _snapshot(client: Any) -> dict[str, Any]:
    result = client.call("debugger.readStruct", {
        "base": f"0x{PLAYER_BASE:08X}", "fields": PLAYER_FIELDS})
    fields = {}
    for row in result.get("fields") or []:
        if row.get("valid") is not True:
            raise SystemExit(f"invalid player field read: {row}")
        fields[row["name"]] = row["value"]
    status = client.call("debugger.status", {})
    block = _read_memory(client, PLAYER_BASE, 0xB0)
    return {
        "fields": fields,
        "player_block_sha256": _sha256_bytes(block),
        "working_actions": int.from_bytes(
            _read_memory(client, ACTION_WORD, 2), "little"),
        "pause_flag": int.from_bytes(
            _read_memory(client, PAUSE_FLAG, 2), "little"),
        "scene": int.from_bytes(
            _read_memory(client, 0x80082504, 4), "little"),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _compact(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame": snapshot["frame"], "cycle": snapshot["cycle"],
        "working_actions": snapshot["working_actions"],
        **snapshot["fields"],
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


def _bulk_branch(client: Any, path: Path, *, buttons: dict[str, bool] | None = None,
                 analog: dict[str, int] | None = None,
                 frames: int = HOLD_FRAMES) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _snapshot(client)
    controller = None
    params: dict[str, Any] = {"port": 0}
    if buttons:
        params["buttons"] = buttons
    if analog:
        params["analog"] = analog
    if len(params) > 1:
        controller = client.call("emulator.setControllerState", params)
    client.call("emulator.advanceFrames", {"frames": frames})
    after = _snapshot(client)
    controller_after = client.call("emulator.getControllerState", {"port": 0})
    client.call("emulator.clearControllerState", {"port": 0})
    return {
        "load": loaded, "buttons": buttons or {}, "analog": analog or {},
        "frames": frames, "controller": controller,
        "controller_after": controller_after,
        "before": before, "after": after,
        "displacement_x": after["fields"]["x"] - before["fields"]["x"],
        "displacement_y": after["fields"]["y"] - before["fields"]["y"],
        "displacement_z": after["fields"]["z"] - before["fields"]["z"],
    }


def _sampled_up_branch(client: Any, path: Path) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _snapshot(client)
    controller = client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    rows = []
    for _ in range(HOLD_FRAMES):
        client.call("emulator.advanceFrames", {"frames": 1})
        rows.append(_compact(_snapshot(client)))
    client.call("emulator.clearControllerState", {"port": 0})

    previous = _compact(before)
    moved, exact, adjusted, vertical = [], [], [], []
    for index, row in enumerate(rows, 1):
        dx, dy, dz = (row[axis] - previous[axis]
                      for axis in ("x", "y", "z"))
        if dx or dz:
            record = {
                "sample": index, "frame": row["frame"],
                "dx": dx, "dy": dy, "dz": dz,
                "velocity_x": row["velocity_x"],
                "velocity_z": row["velocity_z"],
                "error_x": dx - row["velocity_x"],
                "error_z": dz - row["velocity_z"],
            }
            moved.append(record)
            if abs(record["error_x"]) <= 2 and abs(record["error_z"]) <= 2:
                exact.append(record)
            else:
                adjusted.append(record)
        if dy:
            vertical.append({"sample": index, "frame": row["frame"], "dy": dy,
                             "velocity_y": row["velocity_y"],
                             "floor_y": row["floor_y"]})
        previous = row
    after = rows[-1]
    return {
        "load": loaded, "buttons": {"up": True}, "controller": controller,
        "before": before, "samples": rows, "after": after,
        "displacement_x": after["x"] - before["fields"]["x"],
        "displacement_y": after["y"] - before["fields"]["y"],
        "displacement_z": after["z"] - before["fields"]["z"],
        "logic_motion": {
            "moved_ticks": moved, "proposal_exact_ticks": exact,
            "resolver_adjusted_ticks": adjusted,
            "vertical_response_ticks": vertical,
        },
    }


def _run_breadth(client: Any, anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    outcome_names = [
        "x", "y", "z", "heading", "input_heading", "velocity_x",
        "velocity_y", "velocity_z", "forward_component",
        "lateral_component", "floor_y", "state", "grounded", "animation",
        "health", "lives",
    ]
    for index, (label, save) in enumerate(anchors, 1):
        path = ROOT / save
        neutral = _bulk_branch(client, path)
        up = _sampled_up_branch(client, path)
        neutral_after = neutral["after"]
        up_after = {"fields": {key: up["after"][key] for key in PLAYER_FIELDS_BY_NAME}}
        outcome_differences = _field_differences(
            neutral_after, up_after, outcome_names)
        motion = up["logic_motion"]
        up_flags = [
            (row["working_actions"] & DIRECTION_MASK) == UP_MASK
            for row in up["samples"]
        ]
        first_up = next((index for index, value in enumerate(up_flags, 1)
                         if value), None)
        result = {
            "save": save, "neutral": neutral, "up": up,
            "outcome_differences": outcome_differences,
            "up_action_samples": sum(up_flags),
            "up_action_first_sample": first_up,
            "up_action_contiguous_after_latch": (
                first_up is not None and all(up_flags[first_up - 1:])),
            "moved_tick_count": len(motion["moved_ticks"]),
            "proposal_exact_tick_count": len(motion["proposal_exact_ticks"]),
            "resolver_adjusted_tick_count": len(motion["resolver_adjusted_ticks"]),
            "vertical_response_tick_count": len(motion["vertical_response_ticks"]),
            "animation": up["after"]["animation"],
        }
        results[label] = result
        print(f"[run] {index:02d}/{len(anchors)} {label}: "
              f"move={result['moved_tick_count']} "
              f"resolved={result['resolver_adjusted_tick_count']} "
              f"vertical={result['vertical_response_tick_count']} "
              f"anim={result['animation']} diffs={outcome_differences}")

    ordinary = [label for label in results if label != FLIGHT_LABEL]
    summary = {
        "anchors_compared": len(results),
        "ordinary_anchors": len(ordinary),
        "ordinary_labels": ordinary,
        "up_observed_labels": sorted(
            label for label, row in results.items()
            if row["up_action_samples"] >= HOLD_FRAMES - 2 and
            row["up_action_first_sample"] in (1, 2, 3) and
            row["up_action_contiguous_after_latch"]),
        "up_action_sample_counts": {
            label: row["up_action_samples"] for label, row in results.items()},
        "ordinary_moved_labels": sorted(
            label for label in ordinary
            if results[label]["moved_tick_count"] > 0),
        "ordinary_outcome_delta_labels": sorted(
            label for label in ordinary
            if results[label]["outcome_differences"]),
        "ordinary_animation_0_labels": sorted(
            label for label in ordinary if results[label]["animation"] == 0),
        "ordinary_proposal_exact_labels": sorted(
            label for label in ordinary
            if results[label]["proposal_exact_tick_count"] > 0),
        "resolver_adjusted_labels": sorted(
            label for label, row in results.items()
            if row["resolver_adjusted_tick_count"] > 0),
        "vertical_response_labels": sorted(
            label for label, row in results.items()
            if row["vertical_response_tick_count"] > 0),
        "flight_label": FLIGHT_LABEL,
        "flight_animation": results[FLIGHT_LABEL]["animation"],
        "flight_outcome_differences": results[FLIGHT_LABEL]["outcome_differences"],
    }
    if len(results) != 19 or len(ordinary) != 18:
        raise SystemExit(f"unexpected A01 gameplay breadth: {summary}")
    if len(summary["up_observed_labels"]) != 19:
        raise SystemExit(f"A01 breadth input-latch predicate failed: {summary}")
    for key in ("ordinary_moved_labels", "ordinary_outcome_delta_labels",
                "ordinary_proposal_exact_labels"):
        if len(summary[key]) != 18:
            raise SystemExit(f"A01 ordinary breadth predicate failed ({key}): {summary}")
    if len(summary["ordinary_animation_0_labels"]) != 18 or \
            summary["flight_animation"] != FLIGHT_ANIMATION or \
            summary["flight_outcome_differences"]:
        raise SystemExit(f"A01 animation breadth failed: {summary}")
    if not summary["resolver_adjusted_labels"] or \
            not summary["vertical_response_labels"]:
        raise SystemExit(f"A01 did not retain collision/slope responses: {summary}")
    return {"summary": summary, "anchors": results}


PLAYER_FIELDS_BY_NAME = [row["name"] for row in PLAYER_FIELDS]


def _circular_distance(left: int, right: int) -> int:
    delta = (left - right) & HEADING_MASK
    return min(delta, 4096 - delta)


def _sample_frames(client: Any, count: int) -> list[dict[str, Any]]:
    rows = []
    for _ in range(count):
        client.call("emulator.advanceFrames", {"frames": 1})
        rows.append(_compact(_snapshot(client)))
    return rows


def _run_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR
    directions = {}
    for button, mask in (("up", UP_MASK), ("right", RIGHT_MASK),
                         ("down", DOWN_MASK), ("left", LEFT_MASK)):
        row = _bulk_branch(client, path, buttons={button: True})
        row["expected_mask"] = mask
        directions[button] = row
        if row["after"]["working_actions"] & DIRECTION_MASK != mask or \
                abs(row["displacement_x"]) + abs(row["displacement_z"]) <= 500:
            raise SystemExit(f"D-pad direction control failed: {button}: {row}")

    analog_full = _bulk_branch(
        client, path, analog={"lx": 128, "ly": 0})
    analog_half = _bulk_branch(
        client, path, analog={"lx": 128, "ly": 64})
    analog_deadzone = _bulk_branch(
        client, path, analog={"lx": 128, "ly": 120})
    if analog_full["after"]["working_actions"] & DIRECTION_MASK != UP_MASK or \
            analog_half["after"]["working_actions"] & DIRECTION_MASK != UP_MASK:
        raise SystemExit("analog direction did not synthesize native Up")
    if analog_deadzone["after"]["working_actions"] & DIRECTION_MASK or \
            (analog_deadzone["displacement_x"], analog_deadzone["displacement_z"]) != (0, 0):
        raise SystemExit(f"analog deadzone moved the player: {analog_deadzone}")
    if not (0 < abs(analog_half["after"]["fields"]["forward_component"]) <
            abs(analog_full["after"]["fields"]["forward_component"])):
        raise SystemExit("half analog magnitude did not produce an intermediate speed")

    _load_anchor(client, path)
    start = _compact(_snapshot(client))
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    acceleration = _sample_frames(client, 60)
    client.call("emulator.clearControllerState", {"port": 0})
    release = _sample_frames(client, 60)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    reentry = _sample_frames(client, 20)
    client.call("emulator.clearControllerState", {"port": 0})
    changed_speeds = [acceleration[0]["forward_component"]]
    for row in acceleration[1:]:
        if row["forward_component"] != changed_speeds[-1]:
            changed_speeds.append(row["forward_component"])
    accel_release = {
        "start": start, "acceleration": acceleration,
        "release": release, "reentry": reentry,
        "changed_speeds": changed_speeds,
    }
    if start["forward_component"] != 0 or \
            max(abs(value) for value in changed_speeds) < 1700 or \
            release[-1]["forward_component"] != 0 or \
            reentry[-1]["forward_component"] == 0:
        raise SystemExit(f"acceleration/release/re-entry failed: {accel_release}")

    _load_anchor(client, path)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": 30})
    before_turn = _compact(_snapshot(client))
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"right": True}})
    turn_rows = _sample_frames(client, 30)
    client.call("emulator.clearControllerState", {"port": 0})
    heading_steps = []
    previous = before_turn["heading"]
    for index, row in enumerate(turn_rows, 1):
        step = _circular_distance(row["heading"], previous)
        if step:
            heading_steps.append({"sample": index, "step": step,
                                  "heading": row["heading"],
                                  "input_heading": row["input_heading"]})
        previous = row["heading"]
    turn = {"before": before_turn, "samples": turn_rows,
            "heading_steps": heading_steps}
    if len(heading_steps) < 10 or max(row["step"] for row in heading_steps) > \
            DEFAULT_TURN_STEP or turn_rows[-1]["heading"] == before_turn["heading"]:
        raise SystemExit(f"turn controller failed: {turn}")
    return {
        "directions": directions,
        "analog": {"full_up": analog_full, "half_up": analog_half,
                   "deadzone": analog_deadzone},
        "acceleration_release_reentry": accel_release,
        "turn_up_to_right": turn,
    }


def _run_pause_control(client: Any) -> dict[str, Any]:
    path = ROOT / LIFECYCLE_ANCHOR
    _load_anchor(client, path)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused_start = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    paused_after = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    resumed = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    frozen = [name for name in ("x", "y", "z", "forward_component", "animation")
              if paused_start["fields"][name] == paused_after["fields"][name]]
    result = {
        "paused_start": paused_start, "paused_after_up": paused_after,
        "resumed_after_up": resumed, "frozen_fields": frozen,
        "resume_displacement": (
            abs(resumed["fields"]["x"] - paused_after["fields"]["x"]) +
            abs(resumed["fields"]["z"] - paused_after["fields"]["z"])),
    }
    if paused_start["pause_flag"] != 1 or paused_after["pause_flag"] != 1 or \
            len(frozen) != 5 or resumed["pause_flag"] != 0 or \
            resumed["fields"]["animation"] != RUN_ANIMATION or \
            result["resume_displacement"] <= 500:
        raise SystemExit(f"run pause/resume failed: {result}")
    return result


def _checked_write(client: Any, method: str, address: int, value: int) -> dict[str, Any]:
    result = client.call(method, {"address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    if result.get("written") != expected:
        raise SystemExit(f"debugger write did not apply: {method}: {result}")
    return result


def _run_respawn_control(client: Any) -> dict[str, Any]:
    path = ROOT / LIFECYCLE_ANCHOR
    _load_anchor(client, path)
    rid, actor_x, actor_y, actor_z = struct.unpack(
        "<Iiii", _read_memory(client, RECORD_BASE, 16))
    writes = [_checked_write(client, "debugger.writeU16", 0x800A6594, 0)]
    for address, value in (
        (0x800A6500, actor_x), (0x800A6510, actor_x),
        (0x800A6504, actor_y), (0x800A6514, actor_y),
        (0x800A6508, actor_z), (0x800A6518, actor_z),
    ):
        writes.append(_checked_write(
            client, "debugger.writeU32", address, value & 0xFFFFFFFF))
    before = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    flow, respawn = [], None
    for _ in range(8):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        if row["fields"]["lives"] == before["fields"]["lives"] - 1 and \
                row["fields"]["health"] == 4:
            respawn = row
            break
    post_respawn = None
    if respawn is not None:
        client.call("emulator.advanceFrames", {"frames": 60})
        post_respawn = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "perturbation": "health:=0; position+mirror:=first actor; hold Up",
        "actor": {"id": rid, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes, "before": before, "flow": flow,
        "respawn": respawn, "post_respawn_run": post_respawn,
    }
    if respawn is None or post_respawn is None or \
            respawn["scene"] != before["scene"] or \
            respawn["fields"]["animation"] != RUN_ANIMATION or \
            post_respawn["fields"]["animation"] != RUN_ANIMATION or \
            (post_respawn["working_actions"] & DIRECTION_MASK) != UP_MASK:
        raise SystemExit(f"run did not survive native respawn: {result}")
    return result


def _trim_access(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id")}


def _trace_branch(client: Any, *, label: str,
                  controller: dict[str, Any]) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    specifications = [
        {"address": "0x80082488", "length": 2, "type": "read",
         "label": "decoded_action_reads", "max_events": 128,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x80048138", "max": "0x800498AB"}}},
        {"address": "0x800A6528", "length": 4, "type": "write",
         "label": "input_heading", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A6520", "length": 4, "type": "write",
         "label": "heading", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A652C", "length": 4, "type": "write",
         "label": "velocity_x", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A6534", "length": 4, "type": "write",
         "label": "velocity_z", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A6538", "length": 4, "type": "write",
         "label": "forward_component", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A653C", "length": 4, "type": "write",
         "label": "lateral_component", "max_events": 128, "stop_on_hit": False},
        {"address": "0x800A6500", "length": 4, "type": "write",
         "label": "position_x", "max_events": 256, "stop_on_hit": False},
        {"address": "0x800A6508", "length": 4, "type": "write",
         "label": "position_z", "max_events": 256, "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    exec_watch = client.call("execTrace.addWatch", {
        "pc": "0x80049150", "capture": ["v0", "s5", "sp"],
        "label": "scaled_magnitude", "max_events": 64})
    client.call("emulator.setControllerState", {"port": 0, **controller})
    access = client.call("accessLog.run", {"frames": 12})
    client.call("emulator.clearControllerState", {"port": 0})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 32}) for watch in watches]
    execution = client.call("execTrace.get", {
        "watch_id": exec_watch["watch_id"], "offset": 0, "limit": 64})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    return {
        "label": label, "controller": controller,
        "specifications": specifications, "watches": watches,
        "events": [_trim_access(row) for row in access.get("events") or []],
        "total": access.get("total"),
        "truncated": access.get("truncated", False),
        "summaries": summaries, "execution": execution,
    }


def _run_writer_trace(client: Any) -> dict[str, Any]:
    dpad = _trace_branch(client, label="dpad_up",
                         controller={"buttons": {"up": True}})
    half = _trace_branch(client, label="analog_half",
                         controller={"analog": {"lx": 128, "ly": 64}})
    deadzone = _trace_branch(client, label="analog_deadzone",
                             controller={"analog": {"lx": 128, "ly": 120}})
    required = {
        "0x80048044", "0x800491a4", "0x800494ac", "0x80049524",
        "0x800494b0", "0x80049540", "0x80036ce8", "0x80036cf0",
    }
    pcs = {str(row.get("instruction_pc")).lower() for row in dpad["events"]}
    full_regs = [row.get("regs") or {} for row in
                 dpad["execution"].get("events") or []]
    half_regs = [row.get("regs") or {} for row in
                 half["execution"].get("events") or []]
    if any(row["truncated"] or any(summary.get("truncated")
                                   for summary in row["summaries"])
           for row in (dpad, half, deadzone)):
        raise SystemExit("A01 access/exec trace truncated")
    if not required <= pcs:
        raise SystemExit(f"A01 decisive writer/commit PCs absent: {sorted(pcs)}")
    if not full_regs or not all(
            16000 <= int(row["v0"], 16) <= ANALOG_MAGNITUDE_CAP
            for row in full_regs):
        raise SystemExit(f"D-pad/full magnitude trace invalid: {full_regs}")
    if not half_regs or not all(int(row["v0"], 16) == 8192 for row in half_regs):
        raise SystemExit(f"half analog magnitude trace invalid: {half_regs}")
    if deadzone["execution"].get("events"):
        raise SystemExit("deadzone input unexpectedly entered the direction helper")
    return {"dpad_up": dpad, "analog_half": half,
            "analog_deadzone": deadzone}


def _verify_base_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / BASE_MOVIE
    manifest = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = manifest.get(BASE_MOVIE)
    if not pin or pin.get("media_class") != "pristine_serial":
        raise SystemExit(f"cold-boot movie lacks central pristine-serial pin: {pin}")
    if not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot movie bytes differ from central pin: {BASE_MOVIE}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("LEVEL01 control movie is not a v3 from-boot anchor")
    frames = movie.get("frames") or []
    for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
        pad = ((frames[index].get("ports") or {}).get("0") or {})
        if pad.get("up") is not True or any(pad.get(button) for button in (
                "l2", "r2", "cross", "circle", "square", "triangle",
                "start", "select")):
            raise SystemExit(f"movie edit window is no longer Up-only at frame {index}")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _run_cold_boot_movie(client: Any) -> dict[str, Any]:
    movie_doc, pin = _verify_base_movie()
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
            "frame": MOVIE_EDIT_END, "max_frames": 100}, timeout=900)
        control_after = _snapshot(client)
        control_after_movie = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})

        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(movie_doc["frames"])})
        branch_id = branch["movieId"]
        registry_ids.append(branch_id)
        edit_responses = []
        for index in range(MOVIE_EDIT_START, MOVIE_EDIT_END):
            pad = dict(movie_doc["frames"][index]["ports"]["0"])
            pad["up"] = False
            edit_responses.append(client.call("movie.editFrame", {
                "movieId": branch_id, "frame": index, "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch_id})
        neutral_started = client.call("movie.startPlayback", {
            "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        neutral_before = _snapshot(client)
        neutral_before_movie = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_END, "max_frames": 100}, timeout=900)
        neutral_after = _snapshot(client)
        neutral_after_movie = client.call("movie.status", {})
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

    before_differences = _field_differences(control_before, neutral_before)
    result = {
        "base_movie": pin,
        "base_movie_metadata": {
            "format": movie_doc.get("format"), "version": movie_doc.get("version"),
            "frame_count": len(movie_doc["frames"]),
            "start_state": movie_doc.get("start_state"),
        },
        "edit_recipe": {
            "button_removed": "up", "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "edited_frame_count": len(edit_responses),
            "source_window_predicate": "Up true; L2/R2/action/menu buttons false",
        },
        "control_up": {
            "loaded": loaded, "started": control_started,
            "before": control_before, "before_movie": control_before_movie,
            "after": control_after, "after_movie": control_after_movie,
        },
        "edited_neutral": {
            "branch": branch, "activated": activated, "started": neutral_started,
            "before": neutral_before, "before_movie": neutral_before_movie,
            "after": neutral_after, "after_movie": neutral_after_movie,
        },
        "pre_edit_field_differences": before_differences,
        "pre_edit_block_equal": (
            control_before["player_block_sha256"] ==
            neutral_before["player_block_sha256"]),
        "pre_edit_cycle_equal": control_before["cycle"] == neutral_before["cycle"],
        "pre_edit_emulator_frame_equal": control_before["frame"] == neutral_before["frame"],
        "post_edit_field_differences": _field_differences(
            control_after, neutral_after),
    }
    statuses = (control_started, control_before_movie, control_after_movie,
                neutral_started, neutral_before_movie, neutral_after_movie)
    if any(status.get("reproducible") is not True or
           status.get("truncated") is not False for status in statuses):
        raise SystemExit(f"cold-boot movie was not reproducible or was truncated: {result}")
    if before_differences or not result["pre_edit_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["pre_edit_emulator_frame_equal"]:
        raise SystemExit(f"cold-boot branches diverged before edit: {result}")
    if control_after["scene"] != 1 or neutral_after["scene"] != 1 or \
            control_after["fields"]["animation"] != RUN_ANIMATION or \
            control_after["fields"]["forward_component"] == 0 or \
            neutral_after["fields"]["forward_component"] != 0 or \
            not result["post_edit_field_differences"] or \
            len(edit_responses) != MOVIE_EDIT_END - MOVIE_EDIT_START:
        raise SystemExit(f"cold-boot run/neutral control failed: {result}")
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
        raise SystemExit(f"static run-locomotion census failed: {gaps}")
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
        "debugger.capabilities", "debugger.readMemory", "debugger.readStruct",
        "debugger.writeU16", "debugger.writeU32", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.getControllerState",
        "emulator.clearControllerState", "emulator.advanceFrames",
        "accessLog.addWatch", "accessLog.run", "accessLog.summary",
        "accessLog.clear", "execTrace.addWatch", "execTrace.get",
        "execTrace.clear", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status",
        "movie.remove", "movie.clear",
    }
    missing = sorted(name for name in required_methods
                     if not _method_present(capabilities, name))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    breadth = _run_breadth(client, anchors)
    controls = _run_controls(client)
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
        args, generator="tools/phase4_run_locomotion.py",
        anchor={
            "type": "cold-boot edited-input control plus strict-pristine save-state breadth/lifecycle sweep",
            "saves": saves,
            "fixture_sha256": _fixture_pins(selection, saves),
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
            "breadth_input": {"port": 0, "buttons": {"up": True}},
            "cold_boot_edit": cold_boot["edit_recipe"],
        },
    )
    document = {
        "_comment": (
            "Phase-4 A01 run-locomotion campaign evidence. Static pristine bytes, "
            "a cold-boot Up/neutral branch, 19-anchor sampled breadth, analog/D-pad "
            "controls, lifecycle paths, and instruction-attributed traces bound the "
            "resident horizontal controller and collision-consumption interface."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "cold_boot": cold_boot, "breadth": breadth,
            "controls": controls, "pause_resume": pause,
            "death_respawn": respawn, "writer_trace": trace,
        },
        "source_dependencies": {
            "tools/phase4_slow_walk.py": _sha256(ROOT / "tools/phase4_slow_walk.py"),
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[run] retained cold-boot + {len(anchors)} anchor campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(
                args, generator="tools/phase4_run_locomotion.py",
                anchor={"type": "aborted before retained evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
