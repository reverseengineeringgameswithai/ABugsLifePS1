#!/usr/bin/env python3
"""Regenerate the Phase-4 A16 swing-attachment campaign from pristine evidence.

Static mode is deliberately available through ``build_static_census`` for the
safe test suite.  A retained live run uses only centrally declared, strict-
pristine save states plus the pinned from-boot LEVEL01 movie.  It covers the
natural input boundary, every active swing record in the two distinct gameplay
layouts, pendulum writers, release, pause, camera coupling, pool initialization,
native respawn reset, and the scene-wide applicability census.
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
except ModuleNotFoundError:  # imported as tools.phase4_swinging in tests
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_swinging.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_BASE = 0x800A6500
PLAYER_SIZE = 0xB0
ATTACHMENT_INDEX = PLAYER_BASE + 0x8C
ACTION_WORD = 0x80082488
PREVIOUS_PAD = 0x80082380
PAUSE_FLAG = 0x8008224E
SCENE_WORD = 0x80082504
CAMERA_SCRATCH = 0x1F800374
LIVE_ACTOR_TABLE = 0x80090748
CONTACT_Y_BIAS = 7360

POOL_BASE = 0x8009C870
POOL_CAPACITY = 8
POOL_STRIDE = 0x344
ACTIVE_COUNT_OFFSET = 0x00
CLAIM_OFFSET = 0x04
DYNAMIC_VELOCITY_OFFSET = 0x0C
RELATIVE_OFFSET = 0x14
SELECTED_NODE_OFFSET = 0x20
ANCHOR_OFFSET = 0x24
CAMERA_GATE_OFFSET = 0x34
NODE_ONE_OFFSET = 0x54

ACQUIRE_FN = (0x80041AC4, 0x80042428)
DETACH_FN = (0x80041A74, 0x80041AC4)
RESET_FN = (0x8003F5FC, 0x8003F620)
ANCHOR_HELPER_FN = (0x80042DCC, 0x80042E94)
PLAYER_GATE = (0x800488D8, 0x80048A74)
CAMERA_BRANCH = (0x8004E0A8, 0x8004E104)

SETTLE_FRAMES = 2
NATURAL_HOLD_FRAMES = 120
CROSS_MASK = 0x4000
ATTACHED_STATE = 5
ATTACHED_ANIMATION = 4
RELEASE_ANIMATION = 3
RELEASE_MARKER = -30
PROXIMITY_SQUARED_MAX = 0xFFFF
ANCHOR_Y_BIAS = 15000
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
COLD_BOOT_FRAME = 8000
APPROACH_SAVE = "in_front_of_swing.sav"
ATTACHED_SAVE = "on_swing.sav"
TREE_SAVE = "level_11.sav"

EXPECTED_ACTIVE_COUNTS = {
    "stage01_anthill": [16, 12, 16],
    "stage11_the_tree": [16, 22, 16, 22, 16, 16, 19],
    "bonus2_mushrooms": [16, 12, 16],
}

EXPECTED_WORDS = {
    "reset_last_record_offset": (0x8003F5FC, 0x240216DC),
    "reset_active_count_writer": (0x8003F608, 0xA420C870),
    "detach_record_minus_30": (0x80041AA8, 0x2402FFE2),
    "detach_record_writer": (0x80041AB4, 0xA422C874),
    "detach_attachment_clear": (0x80041AB8, 0xA4800000),
    "acquire_threshold_0xffff": (0x80041CE8, 0x3402FFFF),
    "acquire_threshold_compare": (0x80041CEC, 0x0049102A),
    "attachment_index_writer": (0x80041CF8, 0xA6220000),
    "record_claim_writer": (0x80041D00, 0xA6C20000),
    "pool_stride_836": (0x80041EEC, 0x26730344),
    "pool_capacity_8": (0x80041F08, 0x2A820008),
    "velocity_x_writer": (0x800423C8, 0xAC23652C),
    "velocity_y_writer": (0x800423DC, 0xAC236530),
    "velocity_z_writer": (0x800423F0, 0xAC226534),
    "player_attachment_reader": (0x800488D8, 0x8622008C),
    "attached_state_writer": (0x80048930, 0xA6220080),
    "attached_aux_clear": (0x80048934, 0xA6200084),
    "attached_timer_clear": (0x8004893C, 0xA620007A),
    "camera_attachment_reader": (0x8004E0AC, 0x8442658C),
}

PLAYER_FIELDS = [
    {"name": "x", "offset": 0x00, "type": "s32"},
    {"name": "y", "offset": 0x04, "type": "s32"},
    {"name": "z", "offset": 0x08, "type": "s32"},
    {"name": "heading", "offset": 0x20, "type": "u32"},
    {"name": "velocity_x", "offset": 0x2C, "type": "s32"},
    {"name": "velocity_y", "offset": 0x30, "type": "s32"},
    {"name": "velocity_z", "offset": 0x34, "type": "s32"},
    {"name": "state", "offset": 0x80, "type": "s16"},
    {"name": "grounded", "offset": 0x82, "type": "s16"},
    {"name": "vertical_aux", "offset": 0x84, "type": "s16"},
    {"name": "animation", "offset": 0x88, "type": "s16"},
    {"name": "attachment_index", "offset": 0x8C, "type": "s16"},
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
                f"pristine swinging word mismatch at 0x{address:08x}: "
                f"actual=0x{actual:08x} expected=0x{expected:08x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in {
        "pool_reset": RESET_FN,
        "detach_helper": DETACH_FN,
        "acquire_and_pendulum": ACQUIRE_FN,
        "attached_anchor_helper": ANCHOR_HELPER_FN,
        "player_attachment_gate": PLAYER_GATE,
        "camera_attachment_branch": CAMERA_BRANCH,
    }.items():
        data = _region(exe, bounds)
        regions[name] = {
            "start": f"0x{bounds[0]:08X}", "end_exclusive": f"0x{bounds[1]:08X}",
            "size": len(data), "sha256": _sha256_bytes(data),
        }
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}",
                       "sha256": _sha256_bytes(exe)},
        "instruction_words": words,
        "regions": regions,
        "law": {
            "pool_base": f"0x{POOL_BASE:08X}",
            "pool_capacity": POOL_CAPACITY,
            "record_stride": POOL_STRIDE,
            "attachment_index_address": f"0x{ATTACHMENT_INDEX:08X}",
            "attachment_index_domain": "0 detached; 1..8 selects pool slot 0..7",
            "claim_lifecycle": "0 available; 1 attached; -30 native release cooldown",
            "nearest_node_squared_max": PROXIMITY_SQUARED_MAX,
            "anchor_y_bias": ANCHOR_Y_BIAS,
            "native_velocity_copy": {
                "record_offsets": ["0x0C:s16", "0x0E:s16", "0x10:s16"],
                "player_offsets": ["0x2C:s32", "0x30:s32", "0x34:s32"],
                "writers": ["0x800423C8", "0x800423DC", "0x800423F0"],
            },
            "natural_gate": (
                "attachment index 0, player state 1/2/6, an active unclaimed "
                "record inside its camera gate, and nearest rope node distance^2 <= 0xFFFF"),
            "release_gate": "fresh decoded Cross while attached",
        },
        "source_status": {
            "matching_c": (
                "0x80041A74 detach helper, 0x8003F5FC pool reset, and "
                "0x80042DCC attached-anchor helper are matching C"),
            "asm": (
                "0x80041AC4..0x80042427 acquisition/pendulum and the "
                "0x80048138 player owner are byte-matched handwritten assembly"),
            "semantic_name_correction": (
                "legacy vec_normalize_len_1ac4/get_current_actor_xyz names are weak; "
                "runtime evidence identifies swing acquisition and attached-anchor roles"),
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    law = census.get("law") or {}
    gaps = []
    for key, expected, message in (
        ("pool_capacity", 8, "swing pool capacity is not 8"),
        ("record_stride", 836, "swing record stride is not 836"),
        ("nearest_node_squared_max", 0xFFFF,
         "swing nearest-node threshold is not 0xFFFF"),
        ("anchor_y_bias", 15000, "swing anchor Y bias is not 15000"),
    ):
        if law.get(key) != expected:
            gaps.append(message)
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive swing instruction census is incomplete")
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


def _checked_write(client: Any, method: str, address: int,
                   value: int) -> dict[str, Any]:
    width = {"debugger.writeU16": 2, "debugger.writeU32": 4}[method]
    mask = (1 << (8 * width)) - 1
    row = client.call(method, {
        "address": f"0x{address:08X}", "value": value & mask})
    if row.get("written") != width:
        raise SystemExit(f"short debugger write: {method} {address:#x}: {row}")
    observed = _read_int(client, address, width)
    if observed != value & mask:
        raise SystemExit(
            f"debugger write did not round-trip: {address:#x}: {observed:#x}")
    return {"method": method, "address": f"0x{address:08X}",
            "value": value & mask, "readback": observed}


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
        "camera_xyz": list(struct.unpack(
            "<iii", _read_memory(client, CAMERA_SCRATCH, 12))),
        "frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"),
    }


def _pool_record(client: Any, slot: int) -> dict[str, Any]:
    base = POOL_BASE + slot * POOL_STRIDE
    data = _read_memory(client, base, POOL_STRIDE)
    return {
        "slot": slot, "address": f"0x{base:08X}",
        "active_count": struct.unpack_from("<h", data, ACTIVE_COUNT_OFFSET)[0],
        "claim": struct.unpack_from("<h", data, CLAIM_OFFSET)[0],
        "dynamic_velocity": list(struct.unpack_from(
            "<hhh", data, DYNAMIC_VELOCITY_OFFSET)),
        "relative_xyz": list(struct.unpack_from("<iii", data, RELATIVE_OFFSET)),
        "selected_node": struct.unpack_from("<i", data, SELECTED_NODE_OFFSET)[0],
        "anchor_xyz": list(struct.unpack_from("<iii", data, ANCHOR_OFFSET)),
        "camera_gate_x_z_radius": [
            struct.unpack_from("<i", data, CAMERA_GATE_OFFSET)[0],
            struct.unpack_from("<i", data, CAMERA_GATE_OFFSET + 8)[0],
            struct.unpack_from("<i", data, CAMERA_GATE_OFFSET + 12)[0],
        ],
        "node_one_xyz": list(struct.unpack_from("<iii", data, NODE_ONE_OFFSET)),
        "record_sha256": _sha256_bytes(data),
    }


def _pool_snapshot(client: Any) -> dict[str, Any]:
    records = [_pool_record(client, slot) for slot in range(POOL_CAPACITY)]
    active = [row for row in records if row["active_count"] > 0]
    return {
        "attachment_index": _read_int(client, ATTACHMENT_INDEX, 2, signed=True),
        "records": records,
        "active_slots": [row["slot"] for row in active],
        "active_counts": [row["active_count"] for row in active],
        "active_anchors": [row["anchor_xyz"] for row in active],
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


def _held_branch(client: Any, save: str, buttons: dict[str, bool],
                 frames: int = NATURAL_HOLD_FRAMES) -> dict[str, Any]:
    loaded = _load_anchor(client, ROOT / save)
    before = _snapshot(client)
    before_pool = _pool_snapshot(client)
    _set_buttons(client, buttons)
    client.call("emulator.advanceFrames", {"frames": frames})
    after = _snapshot(client)
    after_pool = _pool_snapshot(client)
    _set_buttons(client, {})
    return {"load": loaded, "buttons": buttons, "frames": frames,
            "before": before, "before_pool": before_pool,
            "after": after, "after_pool": after_pool}


def _run_natural_controls(client: Any) -> dict[str, Any]:
    cases = {
        "no_input": _held_branch(client, APPROACH_SAVE, {}),
        "cross_only": _held_branch(client, APPROACH_SAVE, {"cross": True}),
        "up_only": _held_branch(client, APPROACH_SAVE, {"up": True}),
        "up_cross": _held_branch(
            client, APPROACH_SAVE, {"up": True, "cross": True}),
    }
    attached = cases["up_cross"]["after"]["fields"]
    negatives = [cases[name]["after"]["fields"]["attachment_index"]
                 for name in ("no_input", "cross_only", "up_only")]
    summary = {
        "negative_attachment_indices": negatives,
        "positive_attachment_index": attached["attachment_index"],
        "positive_state": attached["state"],
        "positive_grounded": attached["grounded"],
        "positive_animation": attached["animation"],
    }
    if negatives != [0, 0, 0] or attached["attachment_index"] != 2 or \
            (attached["state"], attached["grounded"],
             attached["animation"]) != (ATTACHED_STATE, 0, ATTACHED_ANIMATION):
        raise SystemExit(f"natural swing controls failed: {summary}")
    return {"summary": summary, "cases": cases}


def _run_breadth(client: Any,
                 anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = {}
    for index, (label, save) in enumerate(anchors, 1):
        _load_anchor(client, ROOT / save)
        pool = _pool_snapshot(client)
        rows[label] = {"save": save, "scene": _snapshot(client)["scene"],
                       "pool": pool}
        print(f"[swing-breadth] {index:02d}/{len(anchors)} {label}: "
              f"counts={pool['active_counts']}")
    actual = {label: rows[label]["pool"]["active_counts"]
              for label in EXPECTED_ACTIVE_COUNTS}
    non_applicable = sorted(
        label for label, row in rows.items()
        if not row["pool"]["active_counts"])
    summary = {
        "anchors_compared": len(rows),
        "applicable_labels": sorted(EXPECTED_ACTIVE_COUNTS),
        "non_applicable_labels": non_applicable,
        "active_record_counts": actual,
        "distinct_layout_record_total": (
            len(actual["stage01_anthill"]) + len(actual["stage11_the_tree"])),
        "bonus2_reuses_stage01_layout": (
            rows["bonus2_mushrooms"]["pool"]["active_anchors"] ==
            rows["stage01_anthill"]["pool"]["active_anchors"]),
    }
    if len(rows) != 19 or actual != EXPECTED_ACTIVE_COUNTS or \
            len(non_applicable) != 16 or \
            not summary["bonus2_reuses_stage01_layout"]:
        raise SystemExit(f"swing breadth census failed: {summary}")
    return {"summary": summary, "anchors": rows}


def _prepare_direct_acquisition(client: Any, slot: int) -> list[dict[str, Any]]:
    target = _pool_record(client, slot)
    if target["active_count"] <= 1:
        raise SystemExit(f"target swing record has no selectable node: {target}")
    writes = []
    for other in range(POOL_CAPACITY):
        record = _pool_record(client, other)
        claim = 0 if other == slot else (1 if record["active_count"] > 0 else 0)
        writes.append(_checked_write(
            client, "debugger.writeU16",
            POOL_BASE + other * POOL_STRIDE + CLAIM_OFFSET, claim))
    writes.append(_checked_write(
        client, "debugger.writeU16", ATTACHMENT_INDEX, 0))
    anchor = target["anchor_xyz"]
    node = target["node_one_xyz"]
    xyz = (anchor[0] + node[0],
           anchor[1] + ANCHOR_Y_BIAS + node[1],
           anchor[2] + node[2])
    for offset, value in zip((0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                             (*xyz, *xyz)):
        writes.append(_checked_write(
            client, "debugger.writeU32", PLAYER_BASE + offset, value))
    gate = target["camera_gate_x_z_radius"]
    for offset, value in ((0, gate[0]), (4, anchor[1]), (8, gate[1])):
        writes.append(_checked_write(
            client, "debugger.writeU32", CAMERA_SCRATCH + offset, value))
    return writes


def _run_direct_capacity(client: Any) -> dict[str, Any]:
    trials = []
    layouts = (("stage01_anthill", "level01.sav", 3),
               ("stage11_the_tree", TREE_SAVE, 7))
    for label, save, active_count in layouts:
        for slot in range(active_count):
            _load_anchor(client, ROOT / save)
            writes = _prepare_direct_acquisition(client, slot)
            before = {"player": _snapshot(client),
                      "record": _pool_record(client, slot)}
            client.call("debugger.pause", {})
            call = client.call("debugger.callFunction", {
                "address": f"0x{ACQUIRE_FN[0]:08X}", "a0": 0, "a1": 0,
                "timeout": 10000}, timeout=30)
            after = {"player": _snapshot(client),
                     "record": _pool_record(client, slot)}
            result = {
                "layout": label, "save": save, "slot": slot,
                "writes": writes, "before": before, "call": call,
                "after": after,
            }
            if after["player"]["fields"]["attachment_index"] != slot + 1 or \
                    after["record"]["claim"] != 1:
                raise SystemExit(f"direct swing acquisition failed: {result}")
            trials.append(result)
            print(f"[swing-capacity] {label} slot {slot}: attached={slot + 1}")
    return {
        "summary": {
            "declared_capacity": POOL_CAPACITY,
            "distinct_active_slots_exercised": len(trials),
            "stage01_slots": 3, "stage11_slots": 7,
            "all_selected_target_slot": all(
                row["after"]["player"]["fields"]["attachment_index"] ==
                row["slot"] + 1 for row in trials),
        },
        "trials": trials,
    }


def _selected_record(client: Any) -> dict[str, Any] | None:
    index = _read_int(client, ATTACHMENT_INDEX, 2, signed=True)
    return _pool_record(client, index - 1) if 1 <= index <= POOL_CAPACITY else None


def _run_pendulum(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / ATTACHED_SAVE)
    samples = []
    for emulator_frame in range(0, 26, 2):
        player = _snapshot(client)
        record = _selected_record(client)
        samples.append({"emulator_frame_offset": emulator_frame,
                        "player": player, "record": record})
        if emulator_frame < 24:
            client.call("emulator.advanceFrames", {"frames": 2})
    velocity_matches = [
        row["record"] is not None and
        row["record"]["dynamic_velocity"] == [
            row["player"]["fields"]["velocity_x"],
            row["player"]["fields"]["velocity_y"],
            row["player"]["fields"]["velocity_z"]]
        for row in samples
    ]
    ys = [row["player"]["fields"]["y"] for row in samples]
    summary = {
        "samples": len(samples),
        "attachment_indices": sorted(set(
            row["player"]["fields"]["attachment_index"] for row in samples)),
        "player_y_span": max(ys) - min(ys),
        "record_velocity_equals_player_velocity_samples": sum(velocity_matches),
        "all_record_velocity_copies_match": all(velocity_matches),
    }
    if summary["attachment_indices"] != [2] or \
            summary["player_y_span"] <= 0 or not all(velocity_matches):
        raise SystemExit(f"pendulum law failed: {summary}")
    return {"summary": summary, "samples": samples}


def _trim_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "reported_pc", "instruction_pc", "pc",
        "instruction_word", "instruction", "address", "type", "width",
        "value", "new_value", "watch_id", "regs")}


def _run_writer_trace(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / ATTACHED_SAVE)
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    specifications = [
        {"address": f"0x{PLAYER_BASE + offset:08X}", "length": 4,
         "type": "write", "label": f"player_velocity_{axis}",
         "max_events": 64, "stop_on_hit": False}
        for offset, axis in ((0x2C, "x"), (0x30, "y"), (0x34, "z"))
    ]
    watches = [client.call("accessLog.addWatch", row)
               for row in specifications]
    exec_specs = [
        ("attachment_read", 0x80041F18, ["v0"]),
        ("velocity_x_write", 0x800423C8, ["v1"]),
        ("velocity_y_write", 0x800423DC, ["v1"]),
        ("velocity_z_write", 0x800423F0, ["v0"]),
        ("camera_attachment_read", 0x8004E0AC, ["v0"]),
    ]
    exec_watches = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": capture, "label": label,
        "max_events": 64}) for label, pc, capture in exec_specs]
    access = client.call("accessLog.run", {"frames": 24})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 16}) for watch in watches]
    execution = {label: client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 64})
        for (label, _pc, _capture), watch in zip(exec_specs, exec_watches)}
    client.call("accessLog.clear", {})
    client.call("execTrace.clear", {})
    events = [_trim_event(row) for row in access.get("events") or []]
    observed_pcs = sorted(set(str(row.get("instruction_pc")).lower()
                              for row in events))
    result = {
        "specifications": specifications, "watches": watches,
        "events": events, "total": access.get("total"),
        "truncated": access.get("truncated", False),
        "summaries": summaries, "execution": execution,
        "observed_instruction_pcs": observed_pcs,
    }
    required = {"0x800423c8", "0x800423dc", "0x800423f0"}
    if result["truncated"] or not required <= set(observed_pcs) or any(
            row.get("truncated") or not (row.get("events") or [])
            for row in execution.values()):
        raise SystemExit(f"swing writer trace incomplete: {result}")
    return result


def _run_release(client: Any) -> dict[str, Any]:
    idle = _held_branch(client, ATTACHED_SAVE, {}, frames=24)
    loaded = _load_anchor(client, ROOT / ATTACHED_SAVE)
    before = _snapshot(client)
    before_pool = _pool_snapshot(client)
    before_index = before["fields"]["attachment_index"]
    claim_address = POOL_BASE + (before_index - 1) * POOL_STRIDE + CLAIM_OFFSET
    client.call("accessLog.clear", {})
    specifications = [
        {"address": f"0x{ATTACHMENT_INDEX:08X}", "length": 2,
         "type": "write", "label": "attachment_clear", "max_events": 32,
         "stop_on_hit": False},
        {"address": f"0x{claim_address:08X}", "length": 2,
         "type": "write", "label": "release_marker", "max_events": 32,
         "stop_on_hit": False},
    ]
    watches = [client.call("accessLog.addWatch", row) for row in specifications]
    _set_buttons(client, {"cross": True})
    access = client.call("accessLog.run", {"frames": 12})
    after = _snapshot(client)
    after_pool = _pool_snapshot(client)
    _set_buttons(client, {})
    summaries = [client.call("accessLog.summary", {
        "watch_id": watch["watch_id"], "top": 16}) for watch in watches]
    client.call("accessLog.clear", {})
    events = [_trim_event(row) for row in access.get("events") or []]
    released = {
        "load": loaded, "buttons": {"cross": True}, "frames": 12,
        "before": before, "before_pool": before_pool,
        "after": after, "after_pool": after_pool,
        "trace": {"specifications": specifications, "watches": watches,
                  "events": events, "total": access.get("total"),
                  "truncated": access.get("truncated", False),
                  "summaries": summaries},
    }
    selected_before = before_pool["records"][before_index - 1]
    selected_after = after_pool["records"][before_index - 1]
    marker_events = [row for row in events
                     if str(row.get("instruction_pc")).lower() == "0x80041ab4"]
    clear_events = [row for row in events
                    if str(row.get("instruction_pc")).lower() == "0x80041ab8"]
    summary = {
        "idle_attachment_index": idle["after"]["fields"]["attachment_index"],
        "release_attachment_index": after["fields"]["attachment_index"],
        "release_state": after["fields"]["state"],
        "release_animation": after["fields"]["animation"],
        "record_claim_before": selected_before["claim"],
        "record_claim_after": selected_after["claim"],
        "native_minus_30_events": len(marker_events),
        "native_attachment_clear_events": len(clear_events),
        "native_minus_30_new_value": (
            marker_events[0].get("new_value") if marker_events else None),
    }
    if summary["idle_attachment_index"] != 2 or \
            summary["release_attachment_index"] != 0 or \
            summary["release_state"] == ATTACHED_STATE or \
            summary["record_claim_before"] != 1 or \
            not RELEASE_MARKER <= summary["record_claim_after"] < 0 or \
            len(marker_events) != 1 or len(clear_events) != 1 or \
            released["trace"]["truncated"]:
        raise SystemExit(f"swing release failed: {summary}")
    return {"summary": summary, "idle": idle, "fresh_cross": released}


def _run_pause(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / ATTACHED_SAVE)
    before = _snapshot(client)
    _set_buttons(client, {"start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {})
    paused = _snapshot(client)
    paused_pool = _pool_snapshot(client)
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = _snapshot(client)
    frozen_pool = _pool_snapshot(client)
    _set_buttons(client, {"start": True})
    client.call("emulator.advanceFrames", {"frames": 3})
    _set_buttons(client, {})
    client.call("emulator.advanceFrames", {"frames": 6})
    resumed = _snapshot(client)
    names = ["x", "y", "z", "velocity_x", "velocity_y", "velocity_z",
             "state", "grounded", "animation", "attachment_index"]
    frozen_fields = [name for name in names
                     if paused["fields"][name] == frozen["fields"][name]]
    result = {
        "before": before, "paused": paused, "frozen": frozen,
        "resumed": resumed, "paused_pool": paused_pool,
        "frozen_pool": frozen_pool, "frozen_fields": frozen_fields,
        "pool_frozen": paused_pool == frozen_pool,
    }
    if paused["pause_flag"] != 1 or frozen["pause_flag"] != 1 or \
            frozen_fields != names or not result["pool_frozen"] or \
            resumed["pause_flag"] != 0 or \
            resumed["fields"]["attachment_index"] != 2:
        raise SystemExit(f"swing pause/resume failed: {result}")
    return result


def _camera_branch(client: Any, *, clear_attachment: bool) -> dict[str, Any]:
    _load_anchor(client, ROOT / ATTACHED_SAVE)
    write = None
    if clear_attachment:
        write = _checked_write(
            client, "debugger.writeU16", ATTACHMENT_INDEX, 0)
    before = _snapshot(client)
    client.call("execTrace.clear", {})
    watch = client.call("execTrace.addWatch", {
        "pc": "0x8004E0AC", "capture": ["v0"],
        "label": "camera_attachment_read", "max_events": 64})
    client.call("emulator.advanceFrames", {"frames": 12})
    after = _snapshot(client)
    execution = client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 64})
    client.call("execTrace.clear", {})
    return {"clear_attachment": clear_attachment, "write": write,
            "before": before, "after": after, "execution": execution,
            "camera_delta": [after["camera_xyz"][i] - before["camera_xyz"][i]
                             for i in range(3)]}


def _run_camera(client: Any) -> dict[str, Any]:
    attached = _camera_branch(client, clear_attachment=False)
    detached = _camera_branch(client, clear_attachment=True)
    result = {
        "attached": attached, "attachment_cleared": detached,
        "camera_deltas_differ": attached["camera_delta"] != detached["camera_delta"],
    }
    if attached["execution"].get("truncated") or \
            detached["execution"].get("truncated") or \
            not (attached["execution"].get("events") or []) or \
            not (detached["execution"].get("events") or []) or \
            not result["camera_deltas_differ"]:
        raise SystemExit(f"swing camera dependency failed: {result}")
    return result


def _verify_movie() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(FIXTURE_SET.read_text())
    pin = (manifest.get("entries") or {}).get(BASE_MOVIE)
    path = ROOT / BASE_MOVIE
    if not isinstance(pin, dict) or pin.get("media_class") != "pristine_serial" or \
            not path.is_file() or path.stat().st_size != pin.get("size") or \
            _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot movie lacks exact central pin: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or \
            movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True:
        raise SystemExit("LEVEL01 is not a v3 from-boot movie")
    return movie, {"path": BASE_MOVIE, "sha256": pin["sha256"],
                   "size": pin["size"], "media_class": pin["media_class"]}


def _movie_cleanup(client: Any) -> None:
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass


def _run_cold_boot(client: Any) -> dict[str, Any]:
    movie, pin = _verify_movie()
    _movie_cleanup(client)
    loaded = client.call("movie.load", {
        "path": str((ROOT / BASE_MOVIE).resolve())})
    started = client.call("movie.startPlayback", {"load_start_state": True})
    client.call("movie.advanceToFrame", {
        "frame": COLD_BOOT_FRAME, "max_frames": COLD_BOOT_FRAME + 100},
        timeout=900)
    player = _snapshot(client)
    pool = _pool_snapshot(client)
    status = client.call("movie.status", {})
    _movie_cleanup(client)
    result = {
        "base_movie": pin,
        "metadata": {"format": movie.get("format"),
                     "version": movie.get("version"),
                     "frame_count": len(movie.get("frames") or []),
                     "from_boot": True},
        "loaded": loaded, "started": started, "checkpoint": COLD_BOOT_FRAME,
        "player": player, "pool": pool, "movie": status,
    }
    if any(row.get("reproducible") is not True or row.get("truncated") is not False
           for row in (started, status)) or player["scene"] != 1 or \
            pool["active_counts"] != EXPECTED_ACTIVE_COUNTS["stage01_anthill"] or \
            pool["attachment_index"] != 0:
        raise SystemExit(f"cold-boot swing pool census failed: {result}")
    return result


def _set_player_position(client: Any,
                         xyz: tuple[int, int, int]) -> list[dict[str, Any]]:
    return [_checked_write(client, "debugger.writeU32", PLAYER_BASE + offset,
                           value) for offset, value in zip(
                               (0x00, 0x04, 0x08, 0x10, 0x14, 0x18),
                               (*xyz, *xyz))]


def _s16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _contact_center(client: Any, pointer: int) -> dict[str, Any]:
    data = _read_memory(client, pointer, 0x84)
    actor = {
        "id": struct.unpack_from("<I", data, 0)[0],
        "x": struct.unpack_from("<i", data, 4)[0],
        "y": struct.unpack_from("<i", data, 8)[0],
        "z": struct.unpack_from("<i", data, 12)[0],
        "heading": struct.unpack_from("<I", data, 0x14)[0],
        "animation_phase": struct.unpack_from("<I", data, 0x44)[0],
        "flags": struct.unpack_from("<H", data, 0x5C)[0],
        "state": struct.unpack_from("<h", data, 0x6C)[0],
        "animation_geometry": struct.unpack_from("<I", data, 0x74)[0],
    }
    geometry = actor["animation_geometry"] + actor["animation_phase"] * 16
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
    return {"actor": actor, "frame_address": f"0x{geometry:08X}",
            "frame_offsets": [off_x, off_y, off_z],
            "player_contact_center": list(xyz)}


def _run_respawn(client: Any) -> dict[str, Any]:
    _load_anchor(client, ROOT / ATTACHED_SAVE)
    contact_pointer = _read_int(client, LIVE_ACTOR_TABLE, 4)
    if contact_pointer == 0:
        raise SystemExit("attached lifecycle anchor has no live actor")
    contact = _contact_center(client, contact_pointer)
    before = _snapshot(client)
    writes = [_checked_write(
        client, "debugger.writeU16", PLAYER_BASE + 0x94, 0)]
    writes.extend(_set_player_position(
        client, tuple(contact["player_contact_center"])))
    trigger = []
    fatal = None
    for _ in range(30):
        client.call("emulator.advanceFrames", {"frames": 1})
        row = _snapshot(client)
        trigger.append(row)
        if row["fields"]["health"] < 0:
            fatal = row
            break
    if fatal is None:
        raise SystemExit("native fatal contact did not begin for swing lifecycle")
    flow, respawn = [], None
    for _ in range(10):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = _snapshot(client)
        flow.append(row)
        if row["fields"]["lives"] == before["fields"]["lives"] - 1 and \
                row["fields"]["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit("native swing lifecycle respawn did not complete")
    result = {
        "anchor": ATTACHED_SAVE,
        "perturbation": (
            "from the naturally attached pristine state, set health:=0 and "
            "position:=first actor; observe native damage detach and same-scene respawn"),
        "contact": contact, "writes": writes, "before": before,
        "trigger": trigger,
        "fatal": fatal, "flow": flow, "respawn": respawn,
    }
    if before["fields"]["attachment_index"] != 2 or \
            fatal["fields"]["attachment_index"] != 0 or \
            respawn["fields"]["attachment_index"] != 0 or \
            respawn["scene"] != before["scene"]:
        raise SystemExit(f"swing respawn reset failed: {result}")
    return result


def _run_transition_reset(client: Any) -> dict[str, Any]:
    sequence = []
    for label, save in (("attached_stage01", ATTACHED_SAVE),
                        ("stage02_no_pool", "level02.sav"),
                        ("stage11_seven_records", TREE_SAVE),
                        ("stage12_no_pool", "level_12.sav")):
        loaded = _load_anchor(client, ROOT / save)
        sequence.append({"label": label, "save": save, "load": loaded,
                         "player": _snapshot(client),
                         "pool": _pool_snapshot(client)})
    counts = [row["pool"]["active_counts"] for row in sequence]
    attachments = [row["player"]["fields"]["attachment_index"]
                   for row in sequence]
    result = {"sequence": sequence, "active_counts": counts,
              "attachment_indices": attachments}
    if counts != [[16, 12, 16], [], [16, 22, 16, 22, 16, 16, 19], []] or \
            attachments != [2, 0, 0, 0]:
        raise SystemExit(f"swing transition/reset census failed: {result}")
    return result


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    if static_census_gaps(static):
        raise SystemExit(f"static swing census failed: {static_census_gaps(static)}")
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("first 19 strict-pristine anchors no longer cover gameplay")

    extra_saves = [APPROACH_SAVE, ATTACHED_SAVE]
    extra_declarations = []
    for save in extra_saves:
        declaration = verify_declared_save_fixture(
            ROOT / save, allowed_media_classes={"pristine"})
        extra_declarations.append({"label": save.removesuffix(".sav"),
                                   "save": save, **declaration})
    accepted = [*selection["accepted"][:19], *extra_declarations]
    selection = {**selection, "accepted": accepted, "rejected": [],
                 "anchors_requested": len(accepted),
                 "anchors_accepted": len(accepted), "anchors_rejected": 0}
    saves = list(dict.fromkeys([save for _label, save in anchors] + extra_saves))

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
        "execTrace.get", "execTrace.clear", "movie.load",
        "movie.startPlayback", "movie.advanceToFrame", "movie.stopPlayback",
        "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required_methods
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks required methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    cold_boot = _run_cold_boot(client)
    natural = _run_natural_controls(client)
    breadth = _run_breadth(client, anchors)
    capacity = _run_direct_capacity(client)
    pendulum = _run_pendulum(client)
    trace = _run_writer_trace(client)
    release = _run_release(client)
    pause = _run_pause(client)
    camera = _run_camera(client)
    transition = _run_transition_reset(client)
    respawn = _run_respawn(client)
    _set_buttons(client, {})
    _movie_cleanup(client)

    run_provenance = finish_run(
        args, generator="tools/phase4_swinging.py",
        anchor={
            "type": (
                "pinned from-boot Stage-1 pool census, strict-pristine natural "
                "approach/attached controls, gameplay breadth, and lifecycle"),
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "natural_hold_emulator_frames": NATURAL_HOLD_FRAMES,
            "pendulum_sample_cadence": "every 2 emulator frames over 24 frames",
            "writer_trace_emulator_frames": 24,
            "cold_boot_checkpoint": COLD_BOOT_FRAME,
            "direct_controls": (
                "paused callFunction at 0x80041AC4 after one-record-available "
                "camera/node/player setup; state reloaded before every slot"),
        })
    document = {
        "_comment": (
            "Phase-4 A16 pristine swing-attachment evidence. Retail bytes bind "
            "the pool, acquisition, pendulum, release, camera and reset owners; "
            "retained live evidence supplies natural controls, all active slots, "
            "stage breadth, cold boot, pause, transition and respawn lifecycle."),
        "generated": date.today().isoformat(),
        "static_census": static,
        "live": {
            "cold_boot": cold_boot,
            "natural_controls": natural,
            "breadth": breadth,
            "direct_capacity": capacity,
            "pendulum": pendulum,
            "writer_trace": trace,
            "release": release,
            "pause_resume": pause,
            "camera_dependency": camera,
            "transition_reset": transition,
            "death_respawn": respawn,
        },
        "run_provenance": run_provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[swing] retained A16 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_swinging.py",
                       anchor={"type": "aborted before retained evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
