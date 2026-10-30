#!/usr/bin/env python3
"""Regenerate the Phase-4 A05 abdomen-slam campaign from pristine evidence.

The static census binds the retail double-Cross controller, exact height
boundary, slam countdown, impact window, rebound, actor response, and Bonus-1
streak.  Live mode retains cold-boot and save-state input controls, all gameplay
anchors, a control-checked native movie trace, the five-stomp chain, a paired
timer counterfactual, pause, death/respawn, and the Riverbed Flight exception.
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
OUTPUT = ROOT / "analysis/phase4_abdomen_bounce.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_FN = (0x80048138, 0x800498AC)
SLAM_BRANCH = (0x80048B60, 0x80048D94)
PROXIMITY_FN = (0x8004ABF4, 0x8004B6AC)
STOMP_BRANCH = (0x8004B2AC, 0x8004B3D4)

PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
ACTION_WORD = 0x80082488
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
BONUS_STREAK = 0x8008223C
BONUS_LATCH = 0x800823A0
BONUS_FLAGS = 0x8009B889
ACTOR_TABLE = 0x80090748
RECORD_BASE = 0x8009FE04

CROSS_MASK = 0x4000
NEAR_FLOOR_MAX = 8192
HIGH_SLAM_MIN = 8193
SLAM_TIMER_START = 10
IMPACT_TIMER = 1
NEAR_FLOOR_STATE = 3
HIGH_SLAM_STATE = 4
REBOUND_STATE = 5
REBOUND_IMPULSE = -1536
ACTOR_RESPONSE = -20
ACTOR_RESPONSE_IMPULSE = 4096
EXCEPTION_LABEL = "stage14_riverbed_flight"
SETTLE_FRAMES = 2

CONTROL_ANCHOR = "level01.sav"
LIFECYCLE_ANCHOR = "level02.sav"
OPERATOR_ANCHOR = "buttslam_after_running_og.sav"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
BONUS_MOVIE = "movies/Bonus_Level_01.movie.json"
BONUS_SAVE = "movies/Bonus_Level_01.movie.sav"
COLD_EDIT_START = 8380
COLD_EDIT_END = 8409
COLD_OBSERVE = 8384

EXPECTED_WORDS = {
    "action_word_load": (0x80048B60, 0x94422488),
    "cross_mask": (0x80048B68, 0x30424000),
    "state_reader": (0x80048C6C, 0x86230080),
    "released_state_gate": (0x80048C74, 0x1462003C),
    "floor_distance_subtract": (0x80048C88, 0x00431023),
    "distance_8193_compare": (0x80048C8C, 0x28422001),
    "near_floor_branch": (0x80048C90, 0x14400034),
    "timer_start_constant": (0x80048CA4, 0x2402000A),
    "timer_start_writer": (0x80048CA8, 0xA6220084),
    "high_slam_state_writer": (0x80048CBC, 0xA6230080),
    "animation_7_writer": (0x80048CC8, 0xA6220088),
    "animation_2_writer": (0x80048CD4, 0xA6220088),
    "near_floor_state_writer": (0x80048D64, 0xA6220080),
    "timer_reader": (0x80048D90, 0x86240084),
    "stomp_impact_window": (0x8004B2AC, 0x96C2000A),
    "timer_zero_branch": (0x8004B324, 0x1440000D),
    "rebound_velocity_writer": (0x8004B338, 0xAEC2FFB6),
    "rebound_state_writer": (0x8004B340, 0xA6C20006),
    "grounded_clear_writer": (0x8004B348, 0xA6C00008),
    "rebound_animation_writer": (0x8004B34C, 0xA6C2000E),
    "miss_streak_reset": (0x8004B350, 0xAF8004A4),
    "bonus_branch": (0x8004B35C, 0x3C05800A),
    "bonus_increment": (0x8004B3A8, 0xAF8304A4),
    "bonus_success_reset": (0x8004B3D0, 0xAF8004A4),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "floor_y", "offset": 0x48, "type": "s32"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "u16"},
    {"name": "slam_aux", "offset": 0x84, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
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
                f"pristine abdomen-slam word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "player_owner": PLAYER_FN, "slam_branch": SLAM_BRANCH,
        "proximity_owner": PROXIMITY_FN, "stomp_branch": STOMP_BRANCH,
    }.items():
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
            "input_sequence": "state 2 (released jump) plus a new decoded Cross",
            "near_floor_distance_inclusive_max": NEAR_FLOOR_MAX,
            "high_slam_distance_inclusive_min": HIGH_SLAM_MIN,
            "near_floor_state": NEAR_FLOOR_STATE,
            "high_slam_state": HIGH_SLAM_STATE,
            "high_slam_timer_start": SLAM_TIMER_START,
            "impact_window_unsigned_values": [0, IMPACT_TIMER],
            "timer_active_contact_value": IMPACT_TIMER,
            "timer_zero_rebound_impulse": REBOUND_IMPULSE,
            "timer_zero_rebound_state": REBOUND_STATE,
            "actor_response_state": ACTOR_RESPONSE,
            "actor_response_impulses": [ACTOR_RESPONSE_IMPULSE,
                                         ACTOR_RESPONSE_IMPULSE],
            "bonus_streak_address": f"0x{BONUS_STREAK:08X}",
            "bonus_target_count": 5,
            "contact_geometry": (
                "resident proximity owner applies strict squared-distance "
                "gates using actor center offsets and current 16-byte "
                "animation-frame bounds at actor+0x74+16*(actor+0x44), "
                "rotated by the 12-bit heading table, with a 250-unit margin"),
            "ordinary_owner": "resident player vertical update 0x80048138..0x800498AB",
            "contact_owner": "resident proximity updater 0x8004ABF4..0x8004B6AB",
        },
        "source_status": {
            "asm": "byte-matched hand-written player/proximity build units",
            "semantic_c": "documentation-grade src_re slices; not build input",
            "matching_c": "none; authoritative execution remains byte-matched assembly",
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    checks = (
        ("cross_mask", CROSS_MASK, "slam input mask is not Cross 0x4000"),
        ("near_floor_distance_inclusive_max", NEAR_FLOOR_MAX,
         "near-floor maximum is not 8192"),
        ("high_slam_distance_inclusive_min", HIGH_SLAM_MIN,
         "high-slam minimum is not 8193"),
        ("high_slam_timer_start", SLAM_TIMER_START,
         "high-slam timer start is not 10"),
        ("timer_zero_rebound_impulse", REBOUND_IMPULSE,
         "expired-contact rebound is not -1536"),
        ("actor_response_state", ACTOR_RESPONSE,
         "target response is not -20"),
    )
    for key, expected, message in checks:
        if law.get(key) != expected:
            gaps.append(message)
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive abdomen-slam instruction census is incomplete")
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
        "pause_flag": _read_int(client, PAUSE_FLAG, 2),
        "scene": _read_int(client, SCENE_WORD, 4),
        "bonus_streak": _read_int(client, BONUS_STREAK, 4),
        "bonus_latch": _read_int(client, BONUS_LATCH, 2, signed=True),
        "bonus_flags": _read_int(client, BONUS_FLAGS, 1),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _actor_snapshot(client: Any, pointer: int) -> dict[str, Any]:
    return {
        "pointer": f"0x{pointer:08X}",
        "id": _read_int(client, pointer, 4),
        "x": _read_int(client, pointer + 4, 4, signed=True),
        "y": _read_int(client, pointer + 8, 4, signed=True),
        "z": _read_int(client, pointer + 12, 4, signed=True),
        "flags": _read_int(client, pointer + 0x5C, 2),
        "response_state": _read_int(client, pointer + 0x6C, 2, signed=True),
        "response_54": _read_int(client, pointer + 0x54, 2, signed=True),
        "response_58": _read_int(client, pointer + 0x58, 2, signed=True),
        "block_sha256": _sha256_bytes(_read_memory(client, pointer, 0x80)),
    }


def _spider_actors(client: Any) -> list[dict[str, Any]]:
    rows = []
    for slot in range(64):
        pointer = _read_int(client, ACTOR_TABLE + slot * 4, 4)
        if pointer and _read_int(client, pointer, 4) == 9:
            rows.append({"slot": slot, **_actor_snapshot(client, pointer)})
    return rows


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


def _checked_write(client: Any, method: str, address: int,
                   value: int) -> dict[str, Any]:
    row = client.call(method, {"address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    if row.get("written") != expected:
        raise SystemExit(f"debugger write did not apply: {method}: {row}")
    return row


def _perform_double_tap(client: Any) -> dict[str, Any]:
    before = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 12})
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": 4})
    released = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    samples = []
    for _ in range(8):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
        if samples[-1]["fields"]["state"] not in (1, 2):
            break
    client.call("emulator.clearControllerState", {"port": 0})
    return {"before": before, "released": released,
            "second_press_samples": samples, "after": samples[-1]}


def _double_tap(client: Any, path: Path) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    return {"load": loaded, **_perform_double_tap(client)}


def _run_operator_oracle(client: Any) -> dict[str, Any]:
    loaded = _load_anchor(client, ROOT / OPERATOR_ANCHOR)
    start = _snapshot(client)
    samples = [start]
    for _ in range(16):
        client.call("emulator.advanceFrames", {"frames": 1})
        samples.append(_snapshot(client))
        if samples[-1]["fields"]["grounded"] != 0:
            break
    if (start["fields"]["state"], start["fields"]["slam_aux"],
            start["fields"]["animation"]) != (4, 1, 7):
        raise SystemExit(f"operator abdomen-slam anchor changed: {start}")
    return {"load": loaded, "start": start, "samples_to_contact": samples}


def _run_distance_boundary(client: Any) -> dict[str, Any]:
    results = {}
    for distance in (NEAR_FLOOR_MAX, HIGH_SLAM_MIN):
        _load_anchor(client, ROOT / CONTROL_ANCHOR)
        before = _snapshot(client)
        floor_y = before["fields"]["floor_y"]
        writes = [
            _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x80, 2),
            _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x82, 0),
            _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x84, 0),
            _checked_write(client, "debugger.writeU32", PLAYER_BASE + 0x30, 0),
            _checked_write(client, "debugger.writeU32", PLAYER_BASE + 0x04,
                           (floor_y - distance) & 0xFFFFFFFF),
        ]
        client.call("emulator.setControllerState", {
            "port": 0, "buttons": {"cross": True}})
        samples = []
        for _ in range(8):
            client.call("emulator.advanceFrames", {"frames": 1})
            samples.append(_snapshot(client))
            if samples[-1]["fields"]["state"] != 2:
                break
        client.call("emulator.clearControllerState", {"port": 0})
        results[str(distance)] = {"distance": distance, "before": before,
                                  "writes": writes, "samples": samples,
                                  "after": samples[-1]}
    low = results[str(NEAR_FLOOR_MAX)]["after"]["fields"]
    high = results[str(HIGH_SLAM_MIN)]["after"]["fields"]
    if (low["state"], low["slam_aux"]) != (3, 0) or \
            (high["state"], high["slam_aux"]) != (4, 9):
        raise SystemExit(f"abdomen-slam distance boundary failed: {results}")
    return results


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    for index, (label, save) in enumerate(anchors, 1):
        row = _double_tap(client, ROOT / save)
        results[label] = {"save": save, **row}
        fields = row["after"]["fields"]
        print(f"[abdomen] {index:02d}/{len(anchors)} {label}: "
              f"state={fields['state']} timer={fields['slam_aux']} "
              f"animation={fields['animation']}")
    ordinary = [label for label in results if label != EXCEPTION_LABEL]
    high = sorted(label for label in ordinary
                  if results[label]["after"]["fields"]["state"] == 4
                  and results[label]["after"]["fields"]["slam_aux"] == 9)
    exception = results[EXCEPTION_LABEL]["after"]["fields"]
    summary = {
        "anchors_compared": len(results),
        "applicable_anchors": len(ordinary),
        "high_slam_state_4_timer_9_labels": high,
        "exception_label": EXCEPTION_LABEL,
        "exception_state": exception["state"],
        "exception_animation": exception["animation"],
        "exception_slam_aux": exception["slam_aux"],
    }
    if len(results) != 19 or len(high) != 18 or \
            (exception["state"], exception["animation"],
             exception["slam_aux"]) != (0, 4, 0):
        raise SystemExit(f"abdomen-slam breadth failed: {summary}")
    return {"summary": summary, "anchors": results}


def _verify_movie(rel: str, *, from_boot: bool) -> tuple[dict, dict]:
    path = ROOT / rel
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(rel)
    expected_class = "pristine_serial"
    if not pin or pin.get("media_class") != expected_class or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"movie lacks exact central pin: {rel}: {pin}")
    movie = json.loads(path.read_text())
    start = movie.get("start_state") or {}
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or bool(start.get("from_boot")) != from_boot:
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
    loaded = client.call("movie.load", {"path": str((ROOT / rel).resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": True})
    if started.get("reproducible") is not True or \
            started.get("truncated") is not False:
        raise SystemExit(f"movie did not start reproducibly: {rel}: {started}")
    return loaded, started


def _run_bonus_chain(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie(BONUS_MOVIE, from_boot=False)
    loaded, started = _movie_start(client, BONUS_MOVIE)
    checkpoints = {}
    for frame in (104, 122, 124, 128, 130, 140, 250, 500, 750, 1000, 1250):
        client.call("movie.advanceToFrame", {
            "frame": frame, "max_frames": 2000}, timeout=900)
        row = {"player": _snapshot(client),
               "movie": client.call("movie.status", {})}
        if frame in (124, 128):
            row["spiders"] = _spider_actors(client)
        checkpoints[str(frame)] = row
    _movie_cleanup(client)
    c104 = checkpoints["104"]["player"]["fields"]
    c124 = checkpoints["124"]["player"]
    c128 = checkpoints["128"]["player"]
    c750 = checkpoints["750"]["player"]
    c1250 = checkpoints["1250"]["player"]
    before_spider = next(row for row in checkpoints["124"]["spiders"]
                         if row["pointer"] == "0x800A0014")
    after_spider = next(row for row in checkpoints["128"]["spiders"]
                        if row["pointer"] == "0x800A0014")
    if (c104["state"], c104["slam_aux"]) != (4, 9) or \
            c124["bonus_streak"] != 0 or c128["bonus_streak"] != 1 or \
            c124["fields"]["health"] != c128["fields"]["health"] or \
            (after_spider["response_state"], after_spider["response_54"],
             after_spider["response_58"]) != (-20, 4096, 4096) or \
            before_spider["response_state"] != 0 or \
            c750["bonus_streak"] != 4 or c750["scene"] != 0x11 or \
            (c1250["scene"], c1250["bonus_streak"],
             c1250["bonus_latch"], c1250["bonus_flags"] & 2) != (0x10, 0, 6, 2):
        raise SystemExit(f"five-stomp Bonus-1 chain failed: {checkpoints}")
    return {
        "base_movie": pin,
        "metadata": {"format": movie.get("format"),
                     "version": movie.get("version"),
                     "frame_count": len(movie.get("frames") or []),
                     "start_state": movie.get("start_state")},
        "loaded": loaded, "started": started, "checkpoints": checkpoints,
        "target_response": {"before": before_spider, "after": after_spider,
                            "player_health_before": c124["fields"]["health"],
                            "player_health_after": c128["fields"]["health"]},
    }


def _run_control_checked_trace(client: Any) -> dict[str, Any]:
    result = client.call("movie.traceToFrame", {
        "path": str((ROOT / BONUS_MOVIE).resolve()), "frame": 140,
        "ranges": [
            {"start": "0x80048B2C", "end": "0x80048D93"},
            {"start": "0x8004B2AC", "end": "0x8004B3D3"},
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
        raise SystemExit(f"movie coverage absent/truncated: {coverage}")
    pcs = [{row["pc"] for row in item["coverage"]["counts_by_pc"]}
           for item in coverage]
    if not {"0x80048c6c", "0x80048ca8", "0x80048cbc"} <= pcs[0] or \
            not {"0x8004b2ac", "0x8004b31c", "0x8004b324",
                 "0x8004b35c", "0x8004b3a8"} <= pcs[1]:
        raise SystemExit(f"decisive abdomen-slam PCs absent: {pcs}")
    return result


def _run_timer_counterfactual(client: Any) -> dict[str, Any]:
    def replay_to(frame: int) -> tuple[dict, dict]:
        loaded, started = _movie_start(client, BONUS_MOVIE)
        client.call("movie.advanceToFrame", {
            "frame": frame, "max_frames": 500}, timeout=900)
        return {"loaded": loaded, "started": started,
                "movie": client.call("movie.status", {}),
                "player": _snapshot(client),
                "spiders": _spider_actors(client)}, started

    control_before, _ = replay_to(124)
    client.call("movie.advanceToFrame", {
        "frame": 128, "max_frames": 20}, timeout=900)
    control_after = {"movie": client.call("movie.status", {}),
                     "player": _snapshot(client),
                     "spiders": _spider_actors(client)}
    _movie_cleanup(client)

    edited_before, _ = replay_to(124)
    write = _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x84, 0)
    client.call("movie.advanceToFrame", {
        "frame": 128, "max_frames": 20}, timeout=900)
    edited_after = {"movie": client.call("movie.status", {}),
                    "player": _snapshot(client),
                    "spiders": _spider_actors(client)}
    _movie_cleanup(client)

    pre_control = control_before["player"]
    pre_edited = edited_before["player"]
    control = control_after["player"]
    edited = edited_after["player"]
    result = {
        "edit": "at movie frame 124 write player+0x84 u16 1 -> 0",
        "write": write, "control_before": control_before,
        "control_after": control_after, "edited_before": edited_before,
        "edited_after": edited_after,
        "pre_edit_fields_equal": pre_control["fields"] == pre_edited["fields"],
        "pre_edit_block_equal": pre_control["player_block_sha256"] ==
            pre_edited["player_block_sha256"],
        "pre_edit_cycle_equal": pre_control["cycle"] == pre_edited["cycle"],
    }
    if not all((result["pre_edit_fields_equal"], result["pre_edit_block_equal"],
                result["pre_edit_cycle_equal"])) or \
            pre_control["fields"]["slam_aux"] != 1 or \
            (control["bonus_streak"], control["fields"]["state"]) != (1, 4) or \
            (edited["bonus_streak"], edited["fields"]["state"],
             edited["fields"]["slam_aux"]) != (0, 5, 0) or \
            edited["fields"]["velocity_y"] >= 0:
        raise SystemExit(f"slam timer counterfactual failed: {result}")
    return result


def _run_cold_boot(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie(BASE_MOVIE, from_boot=True)
    frames = movie.get("frames") or []
    for index in range(COLD_EDIT_START, COLD_EDIT_END):
        if ((frames[index].get("ports") or {}).get("0") or {}).get("cross") is not True:
            raise SystemExit(f"cold-boot second-Cross window changed at {index}")
    registry_ids = []
    try:
        loaded, started = _movie_start(client, BASE_MOVIE)
        client.call("movie.advanceToFrame", {
            "frame": COLD_EDIT_START, "max_frames": 9000}, timeout=900)
        control_before = _snapshot(client)
        before_status = client.call("movie.status", {})
        control_samples = {}
        for frame in (COLD_OBSERVE, 8390, 8400, 8406, 8408):
            client.call("movie.advanceToFrame", {
                "frame": frame, "max_frames": 100}, timeout=900)
            control_samples[str(frame)] = {
                "player": _snapshot(client),
                "movie": client.call("movie.status", {})}
        client.call("movie.stopPlayback", {})
        base = client.call("movie.store", {})
        registry_ids.append(base["movieId"])
        branch = client.call("movie.branch", {
            "movieId": base["movieId"], "fromFrame": len(frames)})
        branch_id = branch["movieId"]
        registry_ids.append(branch_id)
        edits = []
        for index in range(COLD_EDIT_START, COLD_EDIT_END):
            pad = dict(frames[index]["ports"]["0"])
            pad["cross"] = False
            edits.append(client.call("movie.editFrame", {
                "movieId": branch_id, "frame": index, "input": {"0": pad}}))
        activated = client.call("movie.activate", {"movieId": branch_id})
        edited_started = client.call("movie.startPlayback", {
            "load_start_state": True})
        client.call("movie.advanceToFrame", {
            "frame": COLD_EDIT_START, "max_frames": 9000}, timeout=900)
        edited_before = _snapshot(client)
        edited_before_status = client.call("movie.status", {})
        client.call("movie.advanceToFrame", {
            "frame": COLD_OBSERVE, "max_frames": 100}, timeout=900)
        edited_after = _snapshot(client)
        edited_after_status = client.call("movie.status", {})
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
        "edit_recipe": {"button_removed": "cross",
                        "start_frame": COLD_EDIT_START,
                        "end_frame_exclusive": COLD_EDIT_END,
                        "observe_frame": COLD_OBSERVE,
                        "edited_frame_count": len(edits)},
        "control": {"loaded": loaded, "started": started,
                    "before": control_before, "before_movie": before_status,
                    "samples": control_samples},
        "edited": {"branch": branch, "activated": activated,
                   "started": edited_started, "before": edited_before,
                   "before_movie": edited_before_status,
                   "after": edited_after, "after_movie": edited_after_status},
        "pre_edit_fields_equal": control_before["fields"] == edited_before["fields"],
        "pre_edit_block_equal": control_before["player_block_sha256"] ==
            edited_before["player_block_sha256"],
        "pre_edit_cycle_equal": control_before["cycle"] == edited_before["cycle"],
    }
    control = control_samples[str(COLD_OBSERVE)]["player"]
    miss = control_samples["8408"]["player"]
    statuses = [started, before_status, *
                (row["movie"] for row in control_samples.values()),
                edited_started, edited_before_status, edited_after_status]
    if any(row.get("reproducible") is not True or
           row.get("truncated") is not False for row in statuses) or \
            not all((result["pre_edit_fields_equal"], result["pre_edit_block_equal"],
                     result["pre_edit_cycle_equal"])) or \
            (control["fields"]["state"], control["fields"]["slam_aux"]) != (4, 8) or \
            edited_after["fields"]["state"] != 2 or \
            any(row["player"]["bonus_streak"] != 0
                for row in control_samples.values()) or \
            miss["fields"]["grounded"] == 0:
        raise SystemExit(f"cold-boot second-Cross/miss control failed: {result}")
    return result


def _run_pause(client: Any) -> dict[str, Any]:
    action = _double_tap(client, ROOT / LIFECYCLE_ANCHOR)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused = _snapshot(client)
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = _snapshot(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    client.call("emulator.clearControllerState", {"port": 0})
    resumed = _snapshot(client)
    names = ["x", "y", "z", "velocity_y", "state", "grounded",
             "slam_aux", "animation"]
    frozen_fields = [name for name in names
                     if paused["fields"][name] == frozen["fields"][name]]
    result = {"action": action, "paused": paused, "frozen": frozen,
              "resumed": resumed, "frozen_fields": frozen_fields}
    if paused["pause_flag"] != 1 or frozen["pause_flag"] != 1 or \
            frozen_fields != names or resumed["pause_flag"] != 0 or \
            resumed["fields"]["slam_aux"] >= frozen["fields"]["slam_aux"]:
        raise SystemExit(f"abdomen-slam pause/resume failed: {result}")
    return result


def _set_player_position(client: Any, xyz: tuple[int, int, int]) -> list[dict]:
    return [_checked_write(client, "debugger.writeU32", PLAYER_BASE + offset,
                           value & 0xFFFFFFFF)
            for offset, value in zip((0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                                     (*xyz, *xyz))]


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
        trigger_flow.append(row)
        if row["fields"]["health"] < 0:
            break
    if trigger_flow[-1]["fields"]["health"] >= 0:
        raise SystemExit("native fatal contact did not begin")
    writes.append(_checked_write(client, "debugger.writeU16",
                                 PLAYER_BASE + 0x84, 7))
    marked = _snapshot(client)
    flow, respawn = [], None
    for _ in range(10):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        if row["fields"]["lives"] == marked["fields"]["lives"] - 1 and \
                row["fields"]["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit("native abdomen-slam lifecycle respawn did not complete")
    post_respawn_settle = []
    for _ in range(3):
        client.call("emulator.advanceFrames", {"frames": 60})
        post_respawn_settle.append(_snapshot(client))
    fresh = _perform_double_tap(client)
    result = {
        "anchor": LIFECYCLE_ANCHOR,
        "perturbation": "health:=0 at first actor center; after fatal contact, slam_aux:=7; native respawn; fresh double Cross",
        "actor": {"id": rid, "x": x, "y": y, "z": z},
        "writes": writes, "trigger_flow": trigger_flow, "marked": marked,
        "flow": flow, "respawn": respawn,
        "post_respawn_settle": post_respawn_settle,
        "fresh_double_cross": fresh,
    }
    if marked["fields"]["slam_aux"] != 7 or \
            respawn["fields"]["slam_aux"] != 0 or \
            respawn["scene"] != marked["scene"] or \
            fresh["after"]["fields"]["lives"] != respawn["fields"]["lives"] or \
            (fresh["after"]["fields"]["state"],
             fresh["after"]["fields"]["slam_aux"]) != (4, 9):
        raise SystemExit(f"abdomen-slam respawn reset/re-entry failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static abdomen-slam census failed: {static_census_gaps(static)}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")
    operator_declaration = verify_declared_save_fixture(
        ROOT / OPERATOR_ANCHOR, allowed_media_classes={"pristine"})
    selection = {**selection,
                 "accepted": [*selection["accepted"][:19], {
                     "label": "operator_abdomen_slam",
                     "save": OPERATOR_ANCHOR, **operator_declaration}],
                 "rejected": [], "anchors_requested": 20,
                 "anchors_accepted": 20, "anchors_rejected": 0}
    saves = [save for _label, save in anchors] + [OPERATOR_ANCHOR]

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
        "movie.load", "movie.store", "movie.branch", "movie.editFrame",
        "movie.activate", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.remove", "movie.clear",
        "movie.traceToFrame",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    operator = _run_operator_oracle(client)
    boundary = _run_distance_boundary(client)
    breadth = _run_breadth(client, anchors)
    trace = _run_control_checked_trace(client)
    chain = _run_bonus_chain(client)
    counterfactual = _run_timer_counterfactual(client)
    cold_boot = _run_cold_boot(client)
    pause = _run_pause(client)
    respawn = _run_respawn(client)
    client.call("emulator.clearControllerState", {"port": 0})
    _movie_cleanup(client)

    run_provenance = finish_run(
        args, generator="tools/phase4_abdomen_bounce.py",
        anchor={
            "type": "cold-boot second-Cross counterfactual, strict-pristine gameplay breadth/lifecycle, and Bonus-1 five-stomp movie",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["base_movie"],
            "bonus_movie": chain["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "double_cross_emulator_frames": {
                "first_hold": 12, "release": 4, "second_press_max": 8},
            "native_cadence": "timer 10 is written and first retained post-update sample is 9; laws are per player update, not emulator frame",
            "cold_boot_edit": cold_boot["edit_recipe"],
            "trace": "movie.traceToFrame cached-interpreter control/instrumented full-RAM and register equivalence",
        })
    document = {
        "_comment": (
            "Phase-4 A05 pristine abdomen-slam evidence. Retail bytes bind the "
            "double-Cross state split, timer, hit response, rebound, and Bonus-1 "
            "streak. Retained live evidence supplies cold boot, exact boundary, "
            "gameplay breadth, five native stomps, causal timer edit, lifecycle, "
            "and control-checked execution coverage."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "operator_oracle": operator,
            "distance_boundary": boundary,
            "breadth": breadth,
            "control_checked_trace": trace,
            "bonus1_five_stomp_chain": chain,
            "timer_counterfactual": counterfactual,
            "cold_boot": cold_boot,
            "pause_resume": pause,
            "death_respawn": respawn,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[abdomen] retained A05 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_abdomen_bounce.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
