#!/usr/bin/env python3
"""Regenerate the Phase-4 A02 slow-walk campaign from pristine evidence.

The campaign has two independent resident boundaries: player movement masks the
decoded L2/R2 bits and selects a lower component cap, while the actor animation
driver selects animation 29 from the same mask.  Static mode always re-reads the
hash-pinned retail executable.  Live mode supplies:

* a cold-boot, timing-matched branch of the pinned LEVEL01 input movie;
* R2/run controls across all 19 gameplay stage and bonus anchors;
* L2 equivalence, shoulder-only, release/re-entry, pause/resume, and
  death/respawn controls; and
* instruction-attributed input readers and state writers with bounded traces.

The input-movie branch is session-local: only R2 is added to an existing
60-frame Up window.  No edited movie, save, capture, or disc is written.
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
except ModuleNotFoundError:  # imported as tools.phase4_slow_walk in tests
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_slow_walk.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_FN = (0x80048138, 0x800498AC)
SLOW_GATE = (0x80048488, 0x800484A4)
VELOCITY_CAP = (0x800493C0, 0x80049444)
ANIMATION_GATE = (0x800566CC, 0x800566FC)
ACTION_WORD = 0x80082488
PAUSE_FLAG = 0x8008224E
PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
RECORD_BASE = 0x8009FE04

SLOW_MASK = 0x0300
L2_MASK = 0x0100
R2_MASK = 0x0200
UP_MASK = 0x0010
RUN_COMPONENT_CAP = 1792
WALK_COMPONENT_CAP = 768
RUN_ANIMATION = 0
WALK_ANIMATION = 29

SETTLE_FRAMES = 2
HOLD_FRAMES = 60
CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
EXCEPTION_LABEL = "stage14_riverbed_flight"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_EDIT_START = 8103
MOVIE_EDIT_END = 8163

EXPECTED_WORDS = {
    "default_component_cap_1792": (0x80048150, 0x24150700),
    "working_action_load": (0x8004848C, 0x94842488),
    "slow_mask_0x0300": (0x80048494, 0x30820300),
    "slow_gate_branch": (0x80048498, 0x10400002),
    "slow_component_cap_768": (0x800484A0, 0x24150300),
    "positive_component_clamp": (0x8004942C, 0x02A09021),
    "negative_component_clamp_test": (0x80049430, 0x0243102A),
    "speed_field_writer": (0x800494AC, 0xAE330038),
    "animation_action_load": (0x800566D0, 0x94422488),
    "animation_slow_mask_0x0300": (0x800566D8, 0x30420300),
    "animation_branch": (0x800566DC, 0x10400005),
    "animation_29_value": (0x800566E0, 0x2402001D),
    "animation_29_writer": (0x800566E8, 0xA4226588),
    "animation_zero_writer": (0x800566F8, 0xA4206588),
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
    {"name": "horizontal_speed", "offset": 0x38, "type": "s32"},
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
    start, end = bounds
    return exe[_va_offset(start):_va_offset(end)]


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine slow-walk word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "player_update": PLAYER_FN,
        "slow_gate": SLOW_GATE,
        "velocity_cap": VELOCITY_CAP,
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
            "path": f"REBUILD/files/{EXE_REL}",
            "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "regions": regions,
        "instruction_words": words,
        "law": {
            "decoded_action_word": f"0x{ACTION_WORD:08X}",
            "shoulder_mask": SLOW_MASK,
            "shoulder_bits": [L2_MASK, R2_MASK],
            "default_component_cap": RUN_COMPONENT_CAP,
            "slow_component_cap": WALK_COMPONENT_CAP,
            "run_animation": RUN_ANIMATION,
            "slow_animation": WALK_ANIMATION,
            "movement_owner": "0x80048138..0x800498AB",
            "animation_owner": "0x800563D4..0x800570F7",
            "overlays": "none; both consumers and state are resident",
        },
        "source_status": {
            "player_asm": "asm/hand_written/80048138_player_vertical_update.s (byte-matched build unit)",
            "player_semantic_c": "src_re/player_update_80048138.c (documentation-grade, not build input)",
            "animation_asm": "asm/nonmatchings/resident/800563d4.s (byte-exact recovered assembly, nonmatching C)",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    gaps = []
    law = census.get("law") or {}
    if law.get("shoulder_mask") != SLOW_MASK:
        gaps.append("slow-walk shoulder mask is not 0x0300")
    if law.get("default_component_cap") != RUN_COMPONENT_CAP:
        gaps.append("default movement component cap is not 1792")
    if law.get("slow_component_cap") != WALK_COMPONENT_CAP:
        gaps.append("slow movement component cap is not 768")
    if law.get("slow_animation") != WALK_ANIMATION:
        gaps.append("slow-walk animation is not 29")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive instruction census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    methods = capabilities.get("methods") or {}
    return name in methods


def _read_memory(client: Any, address: int, length: int) -> bytes:
    result = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(result["hex"])


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
    block = _read_memory(client, PLAYER_BASE, PLAYER_SIZE)
    status = client.call("debugger.status", {})
    return {
        "fields": fields,
        "player_block_sha256": _sha256_bytes(block),
        "working_actions": _read_u16(client, ACTION_WORD),
        "pause_flag": _read_u16(client, PAUSE_FLAG),
        "scene": int.from_bytes(_read_memory(client, 0x80082504, 4), "little"),
        "frame": status.get("frame"),
        "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _field_differences(left: dict[str, Any], right: dict[str, Any],
                       names: list[str] | None = None) -> list[str]:
    names = names or list(left["fields"])
    return [name for name in names
            if left["fields"].get(name) != right["fields"].get(name)]


def _load_anchor(client: Any, path: Path) -> dict[str, Any]:
    # Injected holds survive loadState; clear on both sides of the load.
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


def _held_branch(client: Any, path: Path, buttons: dict[str, bool],
                 frames: int = HOLD_FRAMES) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _snapshot(client)
    controller = client.call("emulator.setControllerState", {
        "port": 0, "buttons": buttons})
    client.call("emulator.advanceFrames", {"frames": frames})
    after = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    return {"load": loaded, "buttons": buttons, "frames": frames,
            "controller": controller, "before": before, "after": after,
            "displacement_x": after["fields"]["x"] - before["fields"]["x"],
            "displacement_z": after["fields"]["z"] - before["fields"]["z"]}


def _run_breadth(client: Any, anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    for index, (label, save) in enumerate(anchors, 1):
        path = ROOT / save
        run = _held_branch(client, path, {"up": True})
        walk = _held_branch(client, path, {"up": True, "r2": True})
        outcome_names = [
            "x", "y", "z", "heading", "input_heading", "velocity_x",
            "velocity_y", "velocity_z", "horizontal_speed", "state",
            "grounded", "animation", "health", "lives",
        ]
        result = {
            "save": save,
            "run": run,
            "walk": walk,
            "walk_has_r2_and_up": (
                walk["after"]["working_actions"] & (R2_MASK | UP_MASK)) ==
                (R2_MASK | UP_MASK),
            "run_animation": run["after"]["fields"]["animation"],
            "walk_animation": walk["after"]["fields"]["animation"],
            "outcome_differences": _field_differences(
                run["after"], walk["after"], outcome_names),
        }
        results[label] = result
        print(f"[slow-walk] {index:02d}/{len(anchors)} {label}: "
              f"run_anim={result['run_animation']} "
              f"walk_anim={result['walk_animation']} "
              f"run_speed={run['after']['fields']['horizontal_speed']} "
              f"walk_speed={walk['after']['fields']['horizontal_speed']}")
    applicable = [label for label in results if label != EXCEPTION_LABEL]
    summary = {
        "anchors_compared": len(results),
        "applicable_anchors": len(applicable),
        "applicable_labels": applicable,
        "walk_animation_29_labels": sorted(
            label for label in applicable
            if results[label]["walk_animation"] == WALK_ANIMATION),
        "run_animation_not_29_labels": sorted(
            label for label in applicable
            if results[label]["run_animation"] != WALK_ANIMATION),
        "r2_up_observed_labels": sorted(
            label for label in applicable
            if results[label]["walk_has_r2_and_up"]),
        "exception_label": EXCEPTION_LABEL,
        "exception_outcome_differences": results[EXCEPTION_LABEL]["outcome_differences"],
        "exception_run_animation": results[EXCEPTION_LABEL]["run_animation"],
        "exception_walk_animation": results[EXCEPTION_LABEL]["walk_animation"],
    }
    if len(results) != 19 or len(applicable) != 18:
        raise SystemExit(f"unexpected Phase-4 action breadth: {summary}")
    for key in ("walk_animation_29_labels", "run_animation_not_29_labels",
                "r2_up_observed_labels"):
        if len(summary[key]) != len(applicable):
            raise SystemExit(f"slow-walk breadth predicate failed ({key}): {summary}")
    if summary["exception_outcome_differences"]:
        raise SystemExit(f"flight exceptional control diverged: {summary}")
    return {"summary": summary, "anchors": results}


def _run_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_ANCHOR
    r2 = _held_branch(client, path, {"up": True, "r2": True})
    l2 = _held_branch(client, path, {"up": True, "l2": True})
    shoulder_only = _held_branch(client, path, {"r2": True})
    equivalence_fields = [
        "x", "y", "z", "heading", "input_heading", "velocity_x",
        "velocity_y", "velocity_z", "horizontal_speed", "state",
        "grounded", "animation", "health", "lives",
    ]

    _load_anchor(client, path)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": True}})
    client.call("emulator.advanceFrames", {"frames": 30})
    first_walk = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": False}})
    client.call("emulator.advanceFrames", {"frames": 20})
    released = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": True}})
    client.call("emulator.advanceFrames", {"frames": 30})
    second_walk = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})

    controls = {
        "r2_positive": r2,
        "l2_positive": l2,
        "shoulder_without_direction": shoulder_only,
        "l2_r2_outcome_differences": _field_differences(
            l2["after"], r2["after"], equivalence_fields),
        "release_and_reentry": {
            "first_walk": first_walk,
            "released_to_run": released,
            "second_walk": second_walk,
        },
    }
    if controls["l2_r2_outcome_differences"]:
        raise SystemExit(f"L2/R2 slow-walk controls differ: {controls}")
    if shoulder_only["after"]["fields"]["animation"] == WALK_ANIMATION:
        raise SystemExit("R2 without movement selected walk animation 29")
    if (shoulder_only["displacement_x"], shoulder_only["displacement_z"]) != (0, 0):
        raise SystemExit("R2 without movement displaced the player")
    if first_walk["fields"]["animation"] != WALK_ANIMATION or \
            released["fields"]["animation"] != RUN_ANIMATION or \
            second_walk["fields"]["animation"] != WALK_ANIMATION:
        raise SystemExit(f"release/re-entry animation law failed: {controls}")
    return controls


def _run_pause_control(client: Any) -> dict[str, Any]:
    path = ROOT / LIFECYCLE_ANCHOR
    _load_anchor(client, path)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused_start = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    paused_after_input = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    # Deliberately merge movement into the held resume edge, matching the
    # established Phase-2 lifecycle oracle's debounce recipe.
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    resumed = _snapshot(client)
    client.call("emulator.clearControllerState", {"port": 0})
    frozen = [name for name in ("x", "y", "z", "horizontal_speed", "animation")
              if paused_start["fields"][name] == paused_after_input["fields"][name]]
    result = {
        "paused_start": paused_start,
        "paused_after_r2_up": paused_after_input,
        "resumed_after_r2_up": resumed,
        "frozen_fields": frozen,
        "resume_displacement": (
            abs(resumed["fields"]["x"] - paused_after_input["fields"]["x"]) +
            abs(resumed["fields"]["z"] - paused_after_input["fields"]["z"])),
    }
    if paused_start["pause_flag"] != 1 or paused_after_input["pause_flag"] != 1:
        raise SystemExit(f"pause flag did not remain set: {result}")
    if len(frozen) != 5:
        raise SystemExit(f"slow-walk input changed frozen player fields: {result}")
    if resumed["pause_flag"] != 0 or \
            resumed["fields"]["animation"] != WALK_ANIMATION or \
            result["resume_displacement"] <= 500:
        raise SystemExit(f"slow walk did not resume after pause: {result}")
    return result


def _checked_write(client: Any, method: str, address: int, value: int) -> dict[str, Any]:
    result = client.call(method, {"address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU8": 1, "debugger.writeU16": 2,
                "debugger.writeU32": 4}[method]
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
        "port": 0, "buttons": {"up": True, "r2": True}})
    flow = []
    respawn = None
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
        "perturbation": "health:=0; position+mirror:=first actor; hold R2+Up",
        "actor": {"id": rid, "x": actor_x, "y": actor_y, "z": actor_z},
        "writes": writes,
        "before": before,
        "flow": flow,
        "respawn": respawn,
        "post_respawn_walk": post_respawn,
    }
    if respawn is None or post_respawn is None:
        raise SystemExit(f"death/respawn slow-walk control did not complete: {result}")
    if respawn["scene"] != before["scene"] or \
            respawn["fields"]["animation"] != WALK_ANIMATION or \
            post_respawn["fields"]["animation"] != WALK_ANIMATION or \
            (post_respawn["working_actions"] & (R2_MASK | UP_MASK)) != (R2_MASK | UP_MASK):
        raise SystemExit(f"slow walk did not survive native respawn lifecycle: {result}")
    return result


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id")}


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    client.call("accessLog.clear", {})
    specifications = [
        {"address": "0x80082488", "length": 2, "type": "read",
         "label": "working_buttons_player", "max_events": 256,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x80048138", "max": "0x800498AB"}}},
        {"address": "0x80082488", "length": 2, "type": "read",
         "label": "working_buttons_animation", "max_events": 128,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x800563D4", "max": "0x800570F7"}}},
        {"address": "0x800A6538", "length": 4, "type": "write",
         "label": "horizontal_speed_writer", "max_events": 128,
         "stop_on_hit": False},
        {"address": "0x800A6588", "length": 2, "type": "write",
         "label": "animation_writer", "max_events": 128,
         "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", spec) for spec in specifications]
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "r2": True}})
    trace = client.call("accessLog.run", {"frames": 12})
    client.call("emulator.clearControllerState", {"port": 0})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 20}) for watch in watches]
    client.call("accessLog.clear", {})
    events = [_trim_event(event) for event in trace.get("events") or []]
    result = {
        "specifications": specifications,
        "watches": watches,
        "events": events,
        "summaries": summaries,
        "total": trace.get("total"),
        "truncated": trace.get("truncated", False),
    }
    pcs = {str(event.get("instruction_pc")).lower() for event in events}
    values = {event.get("value") for event in events
              if event.get("address") == "0x80082488"}
    animation_writes = [event for event in events
                        if str(event.get("instruction_pc")).lower() == "0x800566e8"]
    speed_writes = [event for event in events
                    if str(event.get("instruction_pc")).lower() == "0x800494ac"]
    if result["truncated"] or any(row.get("truncated") for row in summaries):
        raise SystemExit(f"slow-walk writer trace truncated: {result}")
    if not {"0x8004848c", "0x800566d0", "0x800494ac", "0x800566e8"} <= pcs:
        raise SystemExit(f"decisive slow-walk readers/writers absent: {result}")
    if (R2_MASK | UP_MASK) not in values:
        raise SystemExit(f"trace did not observe decoded R2+Up: {result}")
    if not animation_writes or animation_writes[0].get("new_value") != WALK_ANIMATION:
        raise SystemExit(f"animation writer did not publish 29: {result}")
    if not speed_writes:
        raise SystemExit(f"horizontal-speed writer was not attributed: {result}")
    return result


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
    if MOVIE_EDIT_END > len(frames):
        raise SystemExit("slow-walk edit window exceeds the control movie")
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
        control_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
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
            pad["r2"] = True
            edit_responses.append(client.call("movie.editFrame", {
                "movieId": branch_id, "frame": index, "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch_id})
        edited_started = client.call(
            "movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_START, "max_frames": 9000}, timeout=900)
        edited_before = _snapshot(client)
        edited_before_movie = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": MOVIE_EDIT_END, "max_frames": 100}, timeout=900)
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
    before_differences = _field_differences(
        control_before, edited_before, before_fields)
    result = {
        "base_movie": pin,
        "base_movie_metadata": {
            "format": movie_doc.get("format"),
            "version": movie_doc.get("version"),
            "frame_count": len(movie_doc["frames"]),
            "start_state": movie_doc.get("start_state"),
        },
        "edit_recipe": {
            "button_added": "r2",
            "start_frame": MOVIE_EDIT_START,
            "end_frame_exclusive": MOVIE_EDIT_END,
            "edited_frame_count": len(edit_responses),
            "source_window_predicate": "Up true; L2/R2/action/menu buttons false",
        },
        "control": {
            "loaded": loaded, "started": control_started,
            "before": control_before, "before_movie": control_before_movie,
            "after": control_after, "after_movie": control_after_movie,
        },
        "edited": {
            "branch": branch, "activated": activated, "started": edited_started,
            "before": edited_before, "before_movie": edited_before_movie,
            "after": edited_after, "after_movie": edited_after_movie,
        },
        "pre_edit_field_differences": before_differences,
        "pre_edit_block_equal": (
            control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"]),
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
        "pre_edit_emulator_frame_equal": (
            control_before["frame"] == edited_before["frame"]),
        "post_edit_field_differences": _field_differences(
            control_after, edited_after, before_fields),
    }
    statuses = (control_started, control_before_movie, control_after_movie,
                edited_started, edited_before_movie, edited_after_movie)
    if any(status.get("reproducible") is not True or
           status.get("truncated") is not False for status in statuses):
        raise SystemExit(f"cold-boot movie was not reproducible or was truncated: {result}")
    if before_differences or not result["pre_edit_block_equal"] or \
            not result["pre_edit_cycle_equal"] or \
            not result["pre_edit_emulator_frame_equal"]:
        raise SystemExit(f"cold-boot branches diverged before the edit window: {result}")
    if control_after["scene"] != 1 or edited_after["scene"] != 1 or \
            control_after["fields"]["animation"] == WALK_ANIMATION or \
            edited_after["fields"]["animation"] != WALK_ANIMATION or \
            len(edit_responses) != MOVIE_EDIT_END - MOVIE_EDIT_START:
        raise SystemExit(f"cold-boot slow-walk control failed: {result}")
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
        raise SystemExit(f"static slow-walk census failed: {gaps}")

    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or [label for label, _save in anchors][-1] != \
            "bonus3_grasshoppers":
        raise SystemExit("the first 19 strict-pristine anchors are no longer gameplay breadth")
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
    breadth = _run_breadth(client, anchors)
    controls = _run_controls(client)
    pause = _run_pause_control(client)
    respawn = _run_respawn_control(client)
    trace = _run_writer_trace(client)
    cold_boot = _run_cold_boot_movie(client)

    client.call("emulator.clearControllerState", {"port": 0})
    client.call("accessLog.clear", {})
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass

    run_provenance = finish_run(
        args, generator="tools/phase4_slow_walk.py",
        anchor={
            "type": "cold-boot edited-input control plus strict-pristine save-state breadth/lifecycle sweep",
            "saves": saves,
            "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections,
            "selection": {
                **selection,
                "accepted": selection["accepted"][:19],
                "rejected": [],
                "anchors_requested": 19,
                "anchors_accepted": 19,
                "anchors_rejected": 0,
            },
            "cold_boot_movie": cold_boot["base_movie"],
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
            "breadth_inputs": {
                "run": {"port": 0, "buttons": {"up": True}},
                "walk": {"port": 0, "buttons": {"up": True, "r2": True}},
            },
            "cold_boot_edit": cold_boot["edit_recipe"],
        },
    )

    document = {
        "_comment": (
            "Phase-4 A02 slow-walk campaign evidence. Static retail bytes bind "
            "the L2/R2 mask to the player component cap and animation 29. A "
            "from-boot movie branch, 19-anchor breadth sweep, lifecycle controls, "
            "and instruction-attributed trace reproduce the boundaries. Regenerate "
            "with tools/phase4_slow_walk.py in a fresh owned instance."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "cold_boot": cold_boot,
            "breadth": breadth,
            "controls": controls,
            "pause_resume": pause,
            "death_respawn": respawn,
            "writer_trace": trace,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[slow-walk] retained cold-boot + {len(anchors)} anchor campaign: {OUTPUT}")
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
                args, generator="tools/phase4_slow_walk.py",
                anchor={"type": "aborted before retained evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
