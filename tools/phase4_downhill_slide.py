#!/usr/bin/env python3
"""Regenerate the Phase-4 A06 downhill-slide campaign from pristine evidence.

The static census binds the high-slam landing initializer, shared state-5
continuation, the timer-12 carry latch, exact 767/768 component boundary,
low-friction constants, steering, animation, contact class, and reset paths.
Live mode retains the pinned Training slide movie, a cold-boot LEVEL01 branch,
all gameplay anchors, control-checked execution coverage, actor-class contact,
pause, and native death/respawn evidence.
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
OUTPUT = ROOT / "analysis/phase4_downhill_slide.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_FN = (0x80048138, 0x800498AC)
SLIDE_SETUP = (0x800484A4, 0x800484C4)
STATE_AND_LANDING = (0x80048B60, 0x80048E0C)
SLIDE_LATCH = (0x80048E9C, 0x80048F40)
ANIMATION_OWNER = (0x800563D4, 0x80056F18)
PROXIMITY_OWNER = (0x8004ABF4, 0x8004B6AC)

PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
ACTION_WORD = 0x80082488
PREVIOUS_PAD = 0x80082380
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
LIVE_ACTOR_TABLE = 0x80090748
ACTOR_TABLE_CAPACITY = 64
RECORD_BASE = 0x8009FE04

CROSS_MASK = 0x4000
SLIDE_TIMER = 12
SLIDE_POST_DECREMENT = 11
SLIDE_COMPONENT_MIN = 768
SLIDE_FORWARD_DECAY = 2
SLIDE_LATERAL_DECAY = 8
SLIDE_TARGET_COMPONENT = 0
SLIDE_STATE = 5
LANDING_STATE = 1
GROUND_STATE = 0
AIRBORNE_RELEASE_STATE = 6
SLIDE_ANIMATION = 28
LANDING_AUX = -6144
CONTACT_Y_BIAS = 7360
SETTLE_FRAMES = 2
DOUBLE_CROSS_RELEASE_FRAMES = 6

CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
EXCEPTION_LABEL = "stage14_riverbed_flight"
SLIDE_MOVIE = "movies/Phase_Helpers/buttslide_carry_handstand.movie.json"
SLIDE_SAVE = "movies/Phase_Helpers/buttslide_carry_handstand.movie.sav"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"

STEER_EDIT_START = 451
STEER_EDIT_END = 492
STEER_BEFORE = 450
STEER_OBSERVE = 492
COLD_EDIT_START = 8475
COLD_EDIT_END = 8482
COLD_BEFORE = 8474
COLD_OBSERVE = 8480

EXPECTED_ACTIVE_CLASSES = {
    "6:4007", "9:4010", "9:4011", "9:4012", "9:4013",
    "10:4002", "10:4004", "10:4006", "14:4085", "15:4052",
    "15:4053", "17:4102", "17:c101", "19:4041", "22:4045",
    "22:4454", "30:4145", "34:4004", "36:4055", "37:4010",
    "38:4180", "38:4181", "39:4005", "11:4030", "11:4031",
    "21:4881", "28:4881", "30:4984",
}

REGIONS = {
    "player_owner": PLAYER_FN,
    "slide_physics_setup": SLIDE_SETUP,
    "state_and_landing": STATE_AND_LANDING,
    "slide_latch": SLIDE_LATCH,
    "animation_owner": ANIMATION_OWNER,
    "proximity_owner": PROXIMITY_OWNER,
}

EXPECTED_WORDS = {
    "timer_12_setup_reader": (0x800484A4, 0x8623007A),
    "timer_12_setup_constant": (0x800484A8, 0x2402000C),
    "timer_12_setup_branch": (0x800484AC, 0x14620005),
    "forward_decay_2": (0x800484B4, 0x24160002),
    "lateral_decay_8": (0x800484B8, 0x24090008),
    "lateral_decay_publish": (0x800484BC, 0xAFA90040),
    "target_component_zero": (0x800484C0, 0x0000A821),
    "decoded_action_load": (0x80048B60, 0x94422488),
    "cross_mask": (0x80048B68, 0x30424000),
    "held_state_branch_grounded_read": (0x80048CD8, 0x86220082),
    "held_grounded_state_5_constant": (0x80048CE4, 0x24020005),
    "released_grounded_read": (0x80048D00, 0x86220082),
    "released_ground_state_writer": (0x80048D10, 0xA6200080),
    "released_state_5_compare": (0x80048D58, 0x24020005),
    "released_airborne_state_6_constant": (0x80048D60, 0x24020006),
    "shared_state_writer": (0x80048D64, 0xA6220080),
    "landing_was_grounded_reader": (0x80048DD8, 0x8FA90048),
    "landing_aux_writer": (0x80048DF8, 0xA6220084),
    "landing_timer_12_constant": (0x80048DFC, 0x2402000C),
    "landing_timer_writer": (0x80048E00, 0xA622007A),
    "landing_state_1_constant": (0x80048E04, 0x24020001),
    "landing_state_writer": (0x80048E0C, 0xA6220080),
    "positive_timer_decrement": (0x80048ED4, 0xA4820000),
    "post_decrement_11_reader": (0x80048ED8, 0x84830000),
    "post_decrement_11_constant": (0x80048EDC, 0x2402000B),
    "latch_cross_action_load": (0x80048EEC, 0x94422488),
    "latch_cross_mask": (0x80048EF4, 0x30424000),
    "forward_component_load": (0x80048F04, 0x8C426538),
    "component_768_compare": (0x80048F0C, 0x28420300),
    "timer_12_rearm_constant": (0x80048F14, 0x2402000C),
    "lateral_component_load": (0x80048F1C, 0x8C42653C),
    "lateral_absolute_compare": (0x80048F30, 0x28420300),
    "timer_12_rearm_writer": (0x80048F3C, 0xA4820000),
    "animation_timer_reader": (0x8005684C, 0x8442657A),
    "animation_timer_12_compare": (0x80056854, 0x14440003),
    "animation_28_constant": (0x80056858, 0x2402001C),
    "animation_28_writer": (0x80056860, 0xA4226588),
    "contact_slide_timer_reader": (0x8004B170, 0x8463657A),
    "contact_slide_timer_compare": (0x8004B178, 0x10620003),
    "generic_attack_timer_reader": (0x8004B43C, 0x8442657A),
    "generic_attack_negative_branch": (0x8004B444, 0x04410004),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "prev_x", "offset": 0x10, "type": "s32"},
    {"name": "prev_y", "offset": 0x14, "type": "s32"},
    {"name": "prev_z", "offset": 0x18, "type": "s32"},
    {"name": "heading", "offset": 0x20, "type": "u32"},
    {"name": "input_heading", "offset": 0x28, "type": "u32"},
    {"name": "velocity_x", "offset": 0x2C, "type": "s32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "velocity_z", "offset": 0x34, "type": "s32"},
    {"name": "forward_component", "offset": 0x38, "type": "s32"},
    {"name": "lateral_component", "offset": 0x3C, "type": "s32"},
    {"name": "anim_pair_a", "offset": 0x42, "type": "u16"},
    {"name": "anim_pair_b", "offset": 0x46, "type": "u16"},
    {"name": "floor_y", "offset": 0x48, "type": "s32"},
    {"name": "action_timer", "offset": 0x7A, "type": "s16"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "u16"},
    {"name": "vertical_aux", "offset": 0x84, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "action_gate_5c", "offset": 0x5C, "type": "u32"},
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
                f"pristine downhill-slide word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {
            "address": f"0x{address:08X}", "word": f"0x{actual:08X}"}
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
        "regions": regions,
        "instruction_words": words,
        "law": {
            "action_word": f"0x{ACTION_WORD:08X}",
            "cross_mask": CROSS_MASK,
            "native_entry": (
                "a state-4 ground contact writes vertical_aux=-6144, "
                "action_timer=12 and shared state=1; the next held-Cross "
                "grounded update selects shared state 5"),
            "landing_aux": LANDING_AUX,
            "slide_timer": SLIDE_TIMER,
            "post_decrement_rearm_value": SLIDE_POST_DECREMENT,
            "component_threshold_inclusive_min": SLIDE_COMPONENT_MIN,
            "rearm_predicate": (
                "Cross held AND (forward_component >= 768 OR "
                "abs(lateral_component) >= 768)"),
            "active_forward_decay_per_player_update": SLIDE_FORWARD_DECAY,
            "active_lateral_decay_per_player_update": SLIDE_LATERAL_DECAY,
            "active_target_component": SLIDE_TARGET_COMPONENT,
            "active_animation": SLIDE_ANIMATION,
            "held_grounded_state": SLIDE_STATE,
            "released_grounded_state": GROUND_STATE,
            "released_airborne_state": AIRBORNE_RELEASE_STATE,
            "slope_predicate": None,
            "terrain_boundary": (
                "no floor or slope read occurs in the timer-12 rearm slice; "
                "the collision-integrated terrain changes position, floor_y, "
                "and carried components before later player updates"),
            "damage_class": (
                "positive timer 12 is not the negative-timer generic kick "
                "class and does not select target offensive response -20/30; "
                "ordinary actor-specific contact can still damage the player"),
            "capacity": "one context-reused resident player timer/state tuple; no A06-private pool or allocation",
        },
        "source_status": {
            "asm": "byte-matched hand-written player build unit plus pinned resident animation/proximity bytes",
            "semantic_c": "documentation-grade src_re slices; not build input",
            "matching_c": "none for the bounded slide slices; authoritative execution remains pristine bytes",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    checks = (
        ("cross_mask", CROSS_MASK, "slide input mask is not Cross 0x4000"),
        ("landing_aux", LANDING_AUX, "landing aux is not -6144"),
        ("slide_timer", SLIDE_TIMER, "slide latch is not 12"),
        ("component_threshold_inclusive_min", SLIDE_COMPONENT_MIN,
         "slide component threshold is not inclusive 768"),
        ("active_forward_decay_per_player_update", SLIDE_FORWARD_DECAY,
         "slide forward decay is not 2"),
        ("active_lateral_decay_per_player_update", SLIDE_LATERAL_DECAY,
         "slide lateral decay is not 8"),
        ("active_animation", SLIDE_ANIMATION,
         "slide animation is not 28"),
    )
    for key, expected, message in checks:
        if law.get(key) != expected:
            gaps.append(message)
    if law.get("slope_predicate", "missing") is not None:
        gaps.append("a nonexistent explicit slope predicate was asserted")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive downhill-slide instruction census is incomplete")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(row["hex"])


def _read_int(client: Any, address: int, length: int,
              *, signed: bool = False) -> int:
    return int.from_bytes(_read_memory(client, address, length), "little",
                          signed=signed)


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
        "working_actions": _read_int(client, ACTION_WORD, 2),
        "previous_pad": _read_int(client, PREVIOUS_PAD, 2),
        "pause_flag": _read_int(client, PAUSE_FLAG, 2),
        "scene": _read_int(client, SCENE_WORD, 4),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    names = (
        "x", "y", "z", "heading", "velocity_x", "velocity_y",
        "velocity_z", "forward_component", "lateral_component",
        "anim_pair_a", "anim_pair_b", "floor_y", "action_timer", "state",
        "grounded", "vertical_aux", "animation", "health", "lives")
    return {
        "fields": {name: row["fields"][name] for name in names},
        "working_actions": row["working_actions"],
        "player_block_sha256": row["player_block_sha256"],
        "pause_flag": row["pause_flag"], "scene": row["scene"],
        "frame": row["frame"], "cycle": row["cycle"], "pc": row["pc"],
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


def _checked_write(client: Any, method: str, address: int,
                   value: int) -> dict[str, Any]:
    row = client.call(method, {
        "address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    if row.get("written") != expected:
        raise SystemExit(f"debugger write did not apply: {method}: {row}")
    return row


def _verify_movie(rel: str, *, from_boot: bool) -> tuple[dict, dict]:
    path = ROOT / rel
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(rel)
    if not pin or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"movie lacks exact central pristine pin: {rel}: {pin}")
    movie = json.loads(path.read_text())
    start = movie.get("start_state") or {}
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or \
            bool(start.get("from_boot")) != from_boot:
        raise SystemExit(f"unexpected movie anchor: {rel}")
    return movie, {"path": rel, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _movie_cleanup(client: Any) -> None:
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass


def _movie_start(client: Any, rel: str) -> tuple[dict, dict]:
    _movie_cleanup(client)
    loaded = client.call("movie.load", {
        "path": str((ROOT / rel).resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": True})
    if started.get("reproducible") is not True or \
            started.get("truncated") is not False:
        raise SystemExit(f"movie did not start reproducibly: {rel}: {started}")
    return loaded, started


def _run_native_movie_oracle(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie(SLIDE_MOVIE, from_boot=False)
    loaded, started = _movie_start(client, SLIDE_MOVIE)
    checkpoints = {}
    for frame in (300, 356, 378, 400, 406, 410, 430, 450,
                  492, 500, 600, 710, 714):
        client.call("movie.advanceToFrame", {
            "frame": frame, "max_frames": 800}, timeout=900)
        checkpoints[str(frame)] = {
            "player": _compact(_snapshot(client)),
            "movie": client.call("movie.status", {})}
    _movie_cleanup(client)
    f300 = checkpoints["300"]["player"]["fields"]
    f378 = checkpoints["378"]["player"]["fields"]
    f400 = checkpoints["400"]["player"]["fields"]
    f406 = checkpoints["406"]["player"]["fields"]
    f410 = checkpoints["410"]["player"]["fields"]
    f500 = checkpoints["500"]["player"]["fields"]
    f714 = checkpoints["714"]["player"]["fields"]
    statuses = [started, *(row["movie"] for row in checkpoints.values())]
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses) or \
            (f300["state"], f300["grounded"]) != (0, 257) or \
            (f378["state"], f378["vertical_aux"]) != (4, 9) or \
            (f400["anim_pair_a"], f400["anim_pair_b"]) != (11, 12) or \
            (f406["state"], f406["action_timer"], f406["animation"]) != \
            (1, 12, 28) or \
            (f410["state"], f410["action_timer"], f410["animation"]) != \
            (5, 12, 28) or \
            (f500["state"], f500["action_timer"], f500["animation"]) != \
            (5, 12, 28) or \
            max(f500["forward_component"], abs(f500["lateral_component"])) < 768 or \
            f714["state"] != 0:
        raise SystemExit(f"native downhill-slide movie changed: {checkpoints}")
    return {
        "base_movie": pin,
        "metadata": {"format": movie.get("format"),
                     "version": movie.get("version"),
                     "frame_count": len(movie.get("frames") or []),
                     "start_state": movie.get("start_state")},
        "loaded": loaded, "started": started, "checkpoints": checkpoints,
        "state_5_alone_is_not_signature": (
            "the retained signature also requires timer 12/animation 28 and "
            "eligible carried component; raw pair 11/12 is animation phase data"),
    }


def _run_component_boundary(client: Any) -> dict[str, Any]:
    cases = {
        "forward_767": (767, 0, 11, 6),
        "forward_768": (768, 0, 12, 28),
        "lateral_767": (0, 767, 11, 6),
        "lateral_768": (0, 768, 12, 28),
        "lateral_minus_768": (0, -768, 12, 28),
    }
    results, canonical_before = {}, None
    for label, (forward, lateral, timer, animation) in cases.items():
        loaded, started = _movie_start(client, SLIDE_MOVIE)
        client.call("movie.advanceToFrame", {
            "frame": 500, "max_frames": 600}, timeout=900)
        before = _snapshot(client)
        if canonical_before is None:
            canonical_before = before
        writes = [
            _checked_write(client, "debugger.writeU32",
                           PLAYER_BASE + 0x38, forward & 0xFFFFFFFF),
            _checked_write(client, "debugger.writeU32",
                           PLAYER_BASE + 0x3C, lateral & 0xFFFFFFFF),
        ]
        written = _snapshot(client)
        client.call("movie.advanceToFrame", {
            "frame": 502, "max_frames": 10}, timeout=900)
        after = _snapshot(client)
        status = client.call("movie.status", {})
        _movie_cleanup(client)
        if before["fields"] != canonical_before["fields"] or \
                before["player_block_sha256"] != \
                canonical_before["player_block_sha256"] or \
                before["cycle"] != canonical_before["cycle"] or \
                status.get("reproducible") is not True or \
                status.get("truncated") is not False or \
                after["fields"]["action_timer"] != timer or \
                after["fields"]["animation"] != animation or \
                after["fields"]["state"] != SLIDE_STATE:
            raise SystemExit(f"slide component boundary failed: {label}: {after}")
        results[label] = {
            "forward": forward, "lateral": lateral,
            "loaded": loaded, "started": started,
            "before": _compact(before), "writes": writes,
            "written": _compact(written), "after": _compact(after),
            "movie": status,
        }
    return {"cases": results, "pre_edit_fields_block_cycle_equal": True,
            "inclusive_boundary": 768}


def _run_movie_direction_branch(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie(SLIDE_MOVIE, from_boot=False)
    frames = movie.get("frames") or []
    for index in range(STEER_EDIT_START, STEER_EDIT_END):
        pad = frames[index]["ports"]["0"]
        if pad.get("cross") is not True or pad.get("left") is not True:
            raise SystemExit(f"steering window changed at frame {index}")
    registry_ids = []
    try:
        loaded, started = _movie_start(client, SLIDE_MOVIE)
        client.call("movie.advanceToFrame", {
            "frame": STEER_BEFORE, "max_frames": 600}, timeout=900)
        control_before = _snapshot(client)
        before_status = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": STEER_OBSERVE, "max_frames": 100}, timeout=900)
        control_after = _snapshot(client)
        control_status = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})
        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(frames)})
        registry_ids.append(branch["movieId"])
        edits = []
        for index in range(STEER_EDIT_START, STEER_EDIT_END):
            pad = dict(frames[index]["ports"]["0"])
            pad["left"] = False
            edits.append(client.call("movie.editFrame", {
                "movieId": branch["movieId"], "frame": index,
                "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch["movieId"]})
        edited_started = client.call("movie.startPlayback", {
            "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": STEER_BEFORE, "max_frames": 600}, timeout=900)
        edited_before = _snapshot(client)
        edited_before_status = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": STEER_OBSERVE, "max_frames": 100}, timeout=900)
        edited_after = _snapshot(client)
        edited_status = client.call("movie.status", {})
    finally:
        _movie_cleanup(client)
        for movie_id in reversed(registry_ids):
            try:
                client.call("movie.remove", {"movieId": movie_id})
            except Exception:
                pass
        _movie_cleanup(client)
    result = {
        "base_movie": pin,
        "edit_recipe": {"button_removed": "left",
                        "start_frame": STEER_EDIT_START,
                        "end_frame_exclusive": STEER_EDIT_END,
                        "observe_frame": STEER_OBSERVE,
                        "edited_frame_count": len(edits)},
        "control": {"loaded": loaded, "started": started,
                    "before": _compact(control_before),
                    "before_movie": before_status,
                    "after": _compact(control_after),
                    "after_movie": control_status},
        "edited": {"branch": branch, "activated": activated,
                   "started": edited_started,
                   "before": _compact(edited_before),
                   "before_movie": edited_before_status,
                   "after": _compact(edited_after),
                   "after_movie": edited_status},
        "pre_edit_fields_equal": control_before["fields"] == edited_before["fields"],
        "pre_edit_block_equal": control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"],
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
    }
    statuses = (started, before_status, control_status, edited_started,
                edited_before_status, edited_status)
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses) or \
            not all((result["pre_edit_fields_equal"],
                     result["pre_edit_block_equal"],
                     result["pre_edit_cycle_equal"])) or \
            control_after["fields"]["action_timer"] != 12 or \
            edited_after["fields"]["action_timer"] != 12 or \
            control_after["fields"]["state"] != 5 or \
            edited_after["fields"]["state"] != 5 or \
            control_after["fields"]["heading"] == edited_after["fields"]["heading"] or \
            (control_after["fields"]["x"], control_after["fields"]["z"]) == \
            (edited_after["fields"]["x"], edited_after["fields"]["z"]):
        raise SystemExit(f"slide steering branch failed: {result}")
    return result


def _run_cold_boot(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie(BASE_MOVIE, from_boot=True)
    frames = movie.get("frames") or []
    for index in range(COLD_EDIT_START, COLD_EDIT_END):
        if frames[index]["ports"]["0"].get("cross") is not False:
            raise SystemExit(f"cold release window changed at frame {index}")
    registry_ids = []
    try:
        loaded, started = _movie_start(client, BASE_MOVIE)
        client.call("movie.advanceToFrame", {
            "frame": COLD_BEFORE, "max_frames": 8500}, timeout=900)
        control_before = _snapshot(client)
        before_status = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": COLD_OBSERVE, "max_frames": 20}, timeout=900)
        control_after = _snapshot(client)
        control_status = client.call("movie.status", {})
        client.call("movie.stopPlayback", {})
        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(frames)})
        registry_ids.append(branch["movieId"])
        edits = []
        for index in range(COLD_EDIT_START, COLD_EDIT_END):
            pad = dict(frames[index]["ports"]["0"])
            pad["cross"] = True
            edits.append(client.call("movie.editFrame", {
                "movieId": branch["movieId"], "frame": index,
                "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch["movieId"]})
        edited_started = client.call("movie.startPlayback", {
            "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": COLD_BEFORE, "max_frames": 8500}, timeout=900)
        edited_before = _snapshot(client)
        edited_before_status = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": COLD_OBSERVE, "max_frames": 20}, timeout=900)
        edited_after = _snapshot(client)
        edited_status = client.call("movie.status", {})
    finally:
        _movie_cleanup(client)
        for movie_id in reversed(registry_ids):
            try:
                client.call("movie.remove", {"movieId": movie_id})
            except Exception:
                pass
        _movie_cleanup(client)
    result = {
        "base_movie": pin,
        "edit_recipe": {"button_added": "cross",
                        "start_frame": COLD_EDIT_START,
                        "end_frame_exclusive": COLD_EDIT_END,
                        "observe_frame": COLD_OBSERVE,
                        "edited_frame_count": len(edits)},
        "control": {"loaded": loaded, "started": started,
                    "before": _compact(control_before),
                    "before_movie": before_status,
                    "after": _compact(control_after),
                    "after_movie": control_status},
        "edited": {"branch": branch, "activated": activated,
                   "started": edited_started,
                   "before": _compact(edited_before),
                   "before_movie": edited_before_status,
                   "after": _compact(edited_after),
                   "after_movie": edited_status},
        "pre_edit_fields_equal": control_before["fields"] == edited_before["fields"],
        "pre_edit_block_equal": control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"],
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
    }
    statuses = (started, before_status, control_status, edited_started,
                edited_before_status, edited_status)
    cf, ef = control_after["fields"], edited_after["fields"]
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses) or \
            not all((result["pre_edit_fields_equal"],
                     result["pre_edit_block_equal"],
                     result["pre_edit_cycle_equal"])) or \
            (cf["state"], cf["action_timer"], cf["animation"]) != (0, 10, 6) or \
            (ef["state"], ef["action_timer"], ef["animation"]) != (5, 12, 28):
        raise SystemExit(f"cold-boot held-Cross continuation failed: {result}")
    return result


def _perform_slam_landing(client: Any, *, limit: int = 120) -> dict[str, Any]:
    before = _snapshot(client)
    _set_buttons(client, {"cross": True})
    client.call("emulator.advanceFrames", {"frames": 12})
    _set_buttons(client, {})
    client.call("emulator.advanceFrames", {
        "frames": DOUBLE_CROSS_RELEASE_FRAMES})
    released = _snapshot(client)
    _set_buttons(client, {"cross": True})
    transitions, last_key = [], None
    state4 = landing = state5 = None
    for index in range(limit):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _snapshot(client)
        fields = row["fields"]
        key = (fields["state"], fields["grounded"], fields["vertical_aux"],
               fields["action_timer"], fields["animation"])
        if key != last_key:
            transitions.append({"emulator_frame_offset": index + 1,
                                **_compact(row)})
            last_key = key
        if state4 is None and fields["state"] == 4:
            state4 = _compact(row)
        # The initializer writes 12, then the same player update decrements it
        # to 11.  Eligible carry re-arms 12 before the first retained sample;
        # stationary/slow landings retain 11 instead.
        if landing is None and fields["state"] == 1 and \
                fields["action_timer"] in (11, 12) and \
                fields["vertical_aux"] < 0:
            landing = _compact(row)
        if landing is not None and fields["state"] == 5:
            state5 = _compact(row)
            break
    _set_buttons(client, {})
    return {"before": _compact(before), "released": _compact(released),
            "transitions": transitions, "state4": state4,
            "landing_initializer": landing, "state5": state5,
            "after": _compact(_snapshot(client))}


def _run_shared_state_negative(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / CONTROL_ANCHOR)
    before = _snapshot(client)
    _set_buttons(client, {"cross": True})
    transitions, state5 = [], None
    last_state = None
    for index in range(100):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _snapshot(client)
        state = row["fields"]["state"]
        if state != last_state:
            transitions.append({"emulator_frame_offset": index + 1,
                                **_compact(row)})
            last_state = state
        if state == 5:
            state5 = row
            break
    _set_buttons(client, {})
    if state5 is None or state5["fields"]["action_timer"] != 0 or \
            state5["fields"]["animation"] == SLIDE_ANIMATION:
        raise SystemExit(f"shared state-5 negative changed: {transitions}")
    return {"anchor": CONTROL_ANCHOR, "before": _compact(before),
            "transitions": transitions, "state5": _compact(state5),
            "conclusion": "held ordinary jump landing reaches shared state 5 without the timer-12 slide latch"}


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results, completed = {}, []
    for index, (label, save) in enumerate(anchors, 1):
        _load_anchor(client, ROOT / save)
        row = _perform_slam_landing(client)
        results[label] = {"save": save, **row}
        if label != EXCEPTION_LABEL and all(
                row[name] is not None
                for name in ("state4", "landing_initializer", "state5")):
            completed.append(label)
        end = row["state5"] or row["after"]
        fields = end["fields"]
        print(f"[slide] {index:02d}/{len(anchors)} {label}: "
              f"state={fields['state']} timer={fields['action_timer']} "
              f"animation={fields['animation']}")
    exception = results[EXCEPTION_LABEL]["after"]["fields"]
    summary = {
        "anchors_compared": len(results),
        "applicable_anchors": 18,
        "native_state4_landing_state5_labels": sorted(completed),
        "exception_label": EXCEPTION_LABEL,
        "exception_state": exception["state"],
        "exception_animation": exception["animation"],
        "exception_action_timer": exception["action_timer"],
    }
    if len(results) != 19 or len(completed) != 18 or \
            (exception["state"], exception["animation"],
             exception["action_timer"]) != (0, 4, 0):
        raise SystemExit(f"downhill-slide breadth failed: {summary}")
    return {"summary": summary, "anchors": results}


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id", "regs")}


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _movie_start(client, SLIDE_MOVIE)
    client.call("movie.advanceToFrame", {
        "frame": 390, "max_frames": 500}, timeout=900)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    specifications = [
        {"address": f"0x{ACTION_WORD:08X}", "length": 2, "type": "read",
         "label": "decoded_action_reads", "max_events": 256,
         "stop_on_hit": False,
         "filter": {"pc": {"min": "0x80048138", "max": "0x800498AB"}}},
        {"address": "0x800A6538", "length": 8, "type": "readwrite",
         "label": "carried_components", "max_events": 512,
         "stop_on_hit": False},
        {"address": "0x800A657A", "length": 2, "type": "readwrite",
         "label": "slide_timer", "max_events": 512, "stop_on_hit": False},
        {"address": "0x800A6580", "length": 6, "type": "write",
         "label": "state_ground_aux", "max_events": 256,
         "stop_on_hit": False},
        {"address": "0x800A6588", "length": 2, "type": "write",
         "label": "animation", "max_events": 256, "stop_on_hit": False},
        {"address": "0x800A6520", "length": 4, "type": "write",
         "label": "heading", "max_events": 256, "stop_on_hit": False},
        {"address": "0x800A6500", "length": 12, "type": "write",
         "label": "position", "max_events": 512, "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    exec_specs = [
        ("slide_setup", 0x800484B4, ["s5", "s6", "sp"]),
        ("state_5_select", 0x80048CE4, ["v0", "v1", "s1"]),
        ("landing_aux", 0x80048DF8, ["v0", "s1"]),
        ("landing_timer", 0x80048E00, ["v0", "s1"]),
        ("timer_threshold", 0x80048F0C, ["v0"]),
        ("timer_rearm", 0x80048F3C, ["v0", "a0"]),
        ("animation_28", 0x80056860, ["v0"]),
    ]
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture, "label": label,
        "max_events": 128}) for label, pc, capture in exec_specs]
    access = client.call("accessLog.run", {"frames": 120})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 32}) for watch in watches]
    executions = {}
    for (label, _pc, _capture), watch in zip(exec_specs, exec_watches):
        executions[label] = client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 128})
    status = client.call("movie.status", {})
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    _movie_cleanup(client)
    events = [_trim_event(row) for row in access.get("events") or []]
    result = {
        "specifications": specifications, "watches": watches,
        "events": events, "total": access.get("total"),
        "truncated": access.get("truncated", False),
        "summaries": summaries, "execution": executions,
        "movie": status,
    }
    if result["truncated"] or any(row.get("truncated") for row in summaries) or \
            any(row.get("truncated") or not (row.get("events") or [])
                for row in executions.values()) or \
            status.get("reproducible") is not True or \
            status.get("truncated") is not False:
        raise SystemExit(f"downhill-slide writer trace incomplete: {result}")
    return result


def _run_control_checked_trace(client: Any) -> dict[str, Any]:
    result = client.call("movie.traceToFrame", {
        "path": str((ROOT / SLIDE_MOVIE).resolve()), "frame": 510,
        "ranges": [
            {"start": "0x800484A4", "end": "0x80048F3F"},
            {"start": "0x800563D4", "end": "0x80056863"},
        ]}, timeout=900)
    comparison = result.get("comparison") or {}
    if not all(comparison.get(key) is True for key in (
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers")):
        raise SystemExit(f"movie trace changed execution: {comparison}")
    coverage = result.get("coverage") or []
    if len(coverage) != 2 or any(
            (row.get("coverage") or {}).get("truncated") is not False
            for row in coverage):
        raise SystemExit(f"slide coverage absent/truncated: {coverage}")
    pcs = [{row["pc"] for row in item["coverage"]["counts_by_pc"]}
           for item in coverage]
    if not {"0x800484a4", "0x800484b4", "0x80048ce4",
            "0x80048df8", "0x80048e00", "0x80048f3c"} <= pcs[0] or \
            not {"0x8005684c", "0x80056860"} <= pcs[1]:
        raise SystemExit(f"decisive downhill-slide PCs absent: {pcs}")
    return result


def _run_pause(client: Any) -> dict[str, Any]:
    _movie_start(client, SLIDE_MOVIE)
    client.call("movie.advanceToFrame", {
        "frame": 500, "max_frames": 600}, timeout=900)
    client.call("movie.stopPlayback", {})
    before = _snapshot(client)
    _set_buttons(client, {"cross": True, "start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {})
    paused = _snapshot(client)
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = _snapshot(client)
    _set_buttons(client, {"cross": True, "start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {"cross": True})
    client.call("emulator.advanceFrames", {"frames": 4})
    resumed = _snapshot(client)
    _set_buttons(client, {})
    _movie_cleanup(client)
    names = ["x", "y", "z", "heading", "velocity_x", "velocity_y",
             "velocity_z", "forward_component", "lateral_component",
             "action_timer", "state", "grounded", "vertical_aux",
             "animation"]
    frozen_fields = [name for name in names
                     if paused["fields"][name] == frozen["fields"][name]]
    result = {"before": _compact(before), "paused": _compact(paused),
              "frozen": _compact(frozen), "resumed": _compact(resumed),
              "frozen_fields": frozen_fields}
    if paused["pause_flag"] != 1 or frozen["pause_flag"] != 1 or \
            frozen_fields != names or resumed["pause_flag"] != 0 or \
            resumed["fields"]["state"] != 5:
        raise SystemExit(f"downhill-slide pause/resume failed: {result}")
    return result


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


def _set_player_position(client: Any,
                         xyz: tuple[int, int, int]) -> list[dict[str, Any]]:
    return [_checked_write(client, "debugger.writeU32", PLAYER_BASE + offset,
                           value & 0xFFFFFFFF)
            for offset, value in zip((0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                                     (*xyz, *xyz))]


def _classify_flags(flags: int) -> str:
    if flags & 0x20:
        return "separate_actor_path_0x20"
    if flags & 0x800:
        return "ordinary_contact_suppressed_0x800"
    if flags & 0x80:
        return "response_only_0x80"
    return "ordinary_contact"


def _enumerate_active_classes(client: Any,
                              anchors: list[tuple[str, str]]) -> dict[str, Any]:
    by_anchor, representatives = {}, {}
    for label, save in anchors:
        _load_anchor(client, ROOT / save)
        rows = []
        for row in _live_actor_entries(client):
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
            "active slide contact class set changed: "
            f"missing={sorted(EXPECTED_ACTIVE_CLASSES - set(representatives))} "
            f"extra={sorted(set(representatives) - EXPECTED_ACTIVE_CLASSES)}")
    return {"anchors": by_anchor, "representatives": representatives}


def _slide_contact_trial(client: Any,
                         representative: dict[str, Any]) -> dict[str, Any]:
    _load_anchor(client, ROOT / representative["save"])
    entries = _live_actor_entries(client)
    pointer = int(entries[representative["table_index"]]["pointer"], 16)
    actor = _actor_snapshot(client, pointer)
    if actor["id"] != representative["id"] or \
            actor["flags"] != representative["flags"]:
        raise SystemExit(f"active class representative changed: {representative} {actor}")
    center = _contact_center(client, pointer)
    writes = _set_player_position(client, tuple(center["player_contact_center"]))
    for method, address, value in (
        ("debugger.writeU32", PLAYER_BASE + 0x20, 0),
        ("debugger.writeU32", PLAYER_BASE + 0x30, 0),
        ("debugger.writeU32", PLAYER_BASE + 0x5C, 0),
        ("debugger.writeU16", PLAYER_BASE + 0x7A, 12),
        ("debugger.writeU16", PLAYER_BASE + 0x80, 5),
        ("debugger.writeU16", PLAYER_BASE + 0x82, 257),
        ("debugger.writeU16", PLAYER_BASE + 0x84, (-4096) & 0xFFFF),
        ("debugger.writeU16", PLAYER_BASE + 0x88, 28),
        ("debugger.writeU16", PLAYER_BASE + 0x94, 4),
        ("debugger.writeU16", pointer + 0x6C, 0),
    ):
        writes.append(_checked_write(client, method, address, value))
    before_player = _snapshot(client)
    before_actor = _actor_snapshot(client, pointer)
    client.call("debugger.pause", {})
    call = client.call("debugger.callFunction", {
        "address": f"0x{PROXIMITY_OWNER[0]:08X}", "timeout": 10000},
        timeout=30)
    after_player = _snapshot(client)
    after_actor = _actor_snapshot(client, pointer)
    return {
        "geometry": center, "writes": writes,
        "before": {"player": _compact(before_player), "actor": before_actor},
        "call": call,
        "after": {"player": _compact(after_player), "actor": after_actor},
    }


def _run_contact_matrix(client: Any,
                        anchors: list[tuple[str, str]]) -> dict[str, Any]:
    census = _enumerate_active_classes(client, anchors)
    trials = {}
    for index, (key, representative) in enumerate(
            census["representatives"].items(), 1):
        trial = _slide_contact_trial(client, representative)
        trials[key] = {"representative": representative, **trial}
        after_player = trial["after"]["player"]["fields"]
        after_actor = trial["after"]["actor"]
        print(f"[slide-contact] {index:02d}/{len(EXPECTED_ACTIVE_CLASSES)} "
              f"{key}: hp={after_player['health']} actor={after_actor['state']}")
    offensive = sorted(key for key, row in trials.items()
                       if row["after"]["actor"]["state"] in (-20, 30))
    damaged = sorted(key for key, row in trials.items()
                     if row["after"]["player"]["fields"]["health"] == 3)
    neutral_response = sorted(key for key, row in trials.items()
                              if row["after"]["actor"]["state"] == 15)
    preserved = sorted(key for key, row in trials.items()
                       if row["after"]["player"]["fields"]["health"] == 4)
    summary = {
        "active_classes": len(trials),
        "offensive_target_response_classes": offensive,
        "ordinary_contact_damaged_player_classes": damaged,
        "player_health_preserved_classes": preserved,
        "neutral_actor_response_15_classes": neutral_response,
        "scope_boundary": (
            "distinct active pointer-table id/flag classes at the 19 retained "
            "save moments; family AI/HP/death and boss-special contacts remain separate"),
    }
    if len(trials) != 28 or offensive or len(damaged) != 8 or \
            len(preserved) != 20 or len(neutral_response) != 10 or any(
                row["after"]["player"]["fields"]["state"] != 5 or
                row["after"]["player"]["fields"]["animation"] != 28
                for row in trials.values()):
        raise SystemExit(f"slide contact classification failed: {summary}")
    return {"active_census": census, "summary": summary, "trials": trials}


def _run_respawn(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / LIFECYCLE_ANCHOR)
    rid, x, y, z = struct.unpack("<Iiii", _read_memory(client, RECORD_BASE, 16))
    writes = [_checked_write(client, "debugger.writeU16",
                             PLAYER_BASE + 0x94, 0)]
    writes.extend(_set_player_position(client, (x, y, z)))
    trigger_flow = []
    for _ in range(30):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _snapshot(client)
        trigger_flow.append(_compact(row))
        if row["fields"]["health"] < 0:
            break
    if trigger_flow[-1]["fields"]["health"] >= 0:
        raise SystemExit("native fatal contact did not begin")
    for method, address, value in (
        ("debugger.writeU16", PLAYER_BASE + 0x7A, 12),
        ("debugger.writeU16", PLAYER_BASE + 0x80, 5),
        ("debugger.writeU16", PLAYER_BASE + 0x88, 28),
    ):
        writes.append(_checked_write(client, method, address, value))
    marked = _snapshot(client)
    flow, respawn = [], None
    for _ in range(10):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(_compact(row))
        if row["fields"]["lives"] == marked["fields"]["lives"] - 1 and \
                row["fields"]["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit("native downhill-slide lifecycle respawn did not complete")
    for _ in range(3):
        client.call("emulator.advanceFrames", {"frames": 60})
    fresh = _perform_slam_landing(client)
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "perturbation": (
            "health:=0 at first actor record; after fatal contact mark "
            "timer/state/animation 12/5/28; native respawn; fresh double Cross held through landing"),
        "actor": {"id": rid, "x": x, "y": y, "z": z},
        "writes": writes, "trigger_flow": trigger_flow,
        "marked": _compact(marked), "flow": flow,
        "respawn": _compact(respawn), "fresh_slide_entry": fresh,
    }
    if (marked["fields"]["action_timer"], marked["fields"]["state"],
            marked["fields"]["animation"]) != (12, 5, 28) or \
            respawn["fields"]["action_timer"] != 0 or \
            respawn["fields"]["state"] != 0 or \
            fresh["landing_initializer"] is None or fresh["state5"] is None or \
            fresh["state5"]["fields"]["lives"] != respawn["fields"]["lives"]:
        raise SystemExit(f"downhill-slide respawn reset/re-entry failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static downhill-slide census failed: {static_census_gaps(static)}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    slide_declaration = verify_declared_save_fixture(
        ROOT / SLIDE_SAVE, allowed_media_classes={"pristine"})
    selection = {**selection,
                 "accepted": [*selection["accepted"][:19], {
                     "label": "training_downhill_slide",
                     "save": SLIDE_SAVE, **slide_declaration}],
                 "rejected": [], "anchors_requested": 20,
                 "anchors_accepted": 20, "anchors_rejected": 0}
    saves = [save for _label, save in anchors] + [SLIDE_SAVE]

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required_methods = {
        "debugger.readMemory", "debugger.readStruct", "debugger.writeU16",
        "debugger.writeU32", "debugger.pause", "debugger.callFunction",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "accessLog.addWatch", "accessLog.run",
        "accessLog.summary", "accessLog.clear", "execTrace.addWatch",
        "execTrace.get", "execTrace.clear", "movie.load", "movie.store",
        "movie.branch", "movie.editFrame", "movie.activate",
        "movie.startPlayback", "movie.advanceToFrame", "movie.stopPlayback",
        "movie.status", "movie.remove", "movie.clear", "movie.traceToFrame",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    native = _run_native_movie_oracle(client)
    boundary = _run_component_boundary(client)
    steering = _run_movie_direction_branch(client)
    cold_boot = _run_cold_boot(client)
    shared_state = _run_shared_state_negative(client)
    breadth = _run_breadth(client, anchors)
    trace = _run_control_checked_trace(client)
    writer_trace = _run_writer_trace(client)
    pause = _run_pause(client)
    contacts = _run_contact_matrix(client, anchors)
    respawn = _run_respawn(client)
    _set_buttons(client, {})
    _movie_cleanup(client)

    run_provenance = finish_run(
        args, generator="tools/phase4_downhill_slide.py",
        anchor={
            "type": "cold-boot held-Cross branch, pinned Training slide movie, strict-pristine gameplay breadth/lifecycle, and active actor-class contact matrix",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "slide_movie": native["base_movie"],
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "native_double_cross_emulator_frames": {
                "first_hold": 12, "release": DOUBLE_CROSS_RELEASE_FRAMES,
                "held_through_landing_max": 120},
            "slide_law_cadence": "timer/component/friction laws are per resident player update, not emulator frame",
            "component_boundary_movie_frames": [500, 502],
            "steering_edit": steering["edit_recipe"],
            "cold_boot_edit": cold_boot["edit_recipe"],
            "trace": "movie.traceToFrame cached-interpreter control/instrumented full-RAM and register equivalence plus attributed access/exec watches",
        })
    document = {
        "_comment": (
            "Phase-4 A06 pristine downhill-slide evidence. Retail bytes bind "
            "the high-slam landing initializer, timer-12 component latch, "
            "carry-only friction, steering, state termination, animation and "
            "non-offensive contact class. Retained live evidence supplies "
            "cold boot, exact 767/768 controls, gameplay breadth, lifecycle, "
            "actor-class contact and control-checked execution coverage."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "native_movie_oracle": native,
            "component_boundary": boundary,
            "steering_counterfactual": steering,
            "cold_boot": cold_boot,
            "shared_state_5_negative": shared_state,
            "breadth": breadth,
            "control_checked_trace": trace,
            "writer_trace": writer_trace,
            "pause_resume": pause,
            "contact_matrix": contacts,
            "death_respawn": respawn,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[slide] retained A06 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_downhill_slide.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
