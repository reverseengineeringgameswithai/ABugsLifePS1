#!/usr/bin/env python3
"""Regenerate the active Phase-4 C15 safe-respawn-anchor campaign.

The existing LEVEL02 pit and Bug Bar contact recordings are discovery leads,
not authority by name.  This generator verifies their central byte pins and
load-free state metadata, replays them on mounted pristine media, removes only
the recorded pit movement burst, and derives transient RAM-only
counterfactuals.
The frame-100 branches separate the continuously maintained player+0x50 anchor
from the later transition reset.  The frame-156 branches identify the exact
overlay selector and scene-local source record that rebuild the anchor before
the resident respawn handler consumes it.  The Bug Bar branches change only a
fatal-state safe-X word and prove the resident handler consumes the continuously
maintained tuple when its overlay does not replace it.  The existing LEVEL05
and LEVEL07 pit recordings then widen that reset boundary to two more live
scene values with matched one-word safe-X controls.  Separate attribution-only
replays bind those two transition writers to exact pristine LEVEL10/LEVEL04
functions without treating interpreter-forced timing as behavioral authority.
No operator movie or save-state bytes are retained.
"""
from __future__ import annotations

import argparse
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from typing import Any

try:
    from build_identity import verify_staged_input
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_checkpoint_respawn
    from tools.build_identity import verify_staged_input
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )

try:
    import phase4_lives_gameover as c16
except ModuleNotFoundError:  # imported as tools.phase4_checkpoint_respawn
    from tools import phase4_lives_gameover as c16


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_checkpoint_respawn.json"
MOVIE_REL = "movies/Phase4/E10/hazard_pit_LEVEL02.movie.json"
SAVE_REL = "movies/Phase4/E10/hazard_pit_LEVEL02.movie.sav"
MOVIE = ROOT / MOVIE_REL
SAVE = ROOT / SAVE_REL
CONTACT_MOVIE_REL = "movies/Phase4/C16_gameover_continue.movie.json"
CONTACT_SAVE_REL = "movies/Phase4/C16_gameover_continue.movie.sav"
CONTACT_MOVIE = ROOT / CONTACT_MOVIE_REL
CONTACT_SAVE = ROOT / CONTACT_SAVE_REL
PIT_BREADTH_CASES = (
    {
        "id": "scene_10_pit",
        "movie_rel": "movies/Phase4/E10/hazard_pit_LEVEL05.movie.json",
        "save_rel": "movies/Phase4/E10/hazard_pit_LEVEL05.movie.sav",
        "frames": 262,
        "scene": 10,
        "pre_reset_frame": 144,
        "reset_frame": 145,
        "pre_health": 0,
        "pre_lives": 1,
        "post_health": 4,
        "post_lives": 0,
    },
    {
        "id": "scene_4_pit",
        "movie_rel": "movies/Phase4/E10/hazard_pit_LEVEL07.movie.json",
        "save_rel": "movies/Phase4/E10/hazard_pit_LEVEL07.movie.sav",
        "frames": 342,
        "scene": 4,
        "pre_reset_frame": 204,
        "reset_frame": 205,
        "pre_health": 4,
        "pre_lives": 6,
        "post_health": 4,
        "post_lives": 5,
    },
)
PIT_WRITER_STATIC = {
    "scene_10_pit": {
        "path": "LEVEL10/LEVEL.BIN",
        "runtime_range": (0x800B3ADC, 0x800B3C1C),
        "file_offset": 0x13C,
        "sha256": "97e72e5e4bf8c1029cabc98cfcef43d5077666edeb39617d012769f01285c4b8",
        "function_bounds": (0x800B3ADC, 0x800B3C18),
        "instructions": {
            "status_load": (0x800B3AEC, 0x94620000),
            "status_gate": (0x800B3AF4, 0x30420010),
            "table_pointer_load": (0x800B3B04, 0x8D086DA4),
            "candidate_x_load": (0x800B3B34, 0x8CA20004),
            "candidate_z_load": (0x800B3B48, 0x8CA2000C),
            "selected_x_load": (0x800B3B9C, 0x8C430004),
            "selected_x_scale": (0x800B3BA8, 0x00031940),
            "safe_x_store": (0x800B3BAC, 0xAC830000),
            "selected_z_load": (0x800B3BB0, 0x8C42000C),
            "temporary_safe_y_store": (0x800B3BBC, 0xAC256554),
            "selected_z_scale": (0x800B3BC0, 0x00021140),
            "safe_z_store": (0x800B3BC8, 0xAC226558),
            "ground_query": (0x800B3BCC, 0x0C00DE8E),
            "ground_y_adjust": (0x800B3BD4, 0x2442FF00),
            "final_safe_y_store": (0x800B3BDC, 0xAC226554),
        },
        "expected_events": (
            ("0x800b3bac", "0x800a6550", 4, "0xfffe6bf4", "0xfffd9060"),
            ("0x800b3bbc", "0x800a6554", 4, "0xffffecd9", "0x7fffffff"),
            ("0x800b3bc8", "0x800a6558", 4, "0x0012759f", "0x00120c60"),
            ("0x800b3bdc", "0x800a6554", 4, "0x7fffffff", "0x00000e2c"),
        ),
        "expected_heading_writes": 0,
        "bounded_role": (
            "status-0x0010-gated nearest-row selector; X/Z are scaled by 32, "
            "Y is ground-query-derived, and heading is preserved"),
    },
    "scene_4_pit": {
        "path": "LEVEL04/LEVEL.BIN",
        "runtime_range": (0x800B3C5C, 0x800B3CD8),
        "file_offset": 0x2BC,
        "sha256": "8494bef9a426a6b2ceea0bb57a634c5520a12abb89c493ce4b88ab3d992764ba",
        "function_bounds": (0x800B3C5C, 0x800B3CD4),
        "instructions": {
            "status_load": (0x800B3C6C, 0x94A20000),
            "status_gate": (0x800B3C74, 0x30420010),
            "safe_x_constant_low": (0x800B3C80, 0x34631B54),
            "safe_z_constant_low": (0x800B3C88, 0x34428835),
            "safe_y_temporary_low": (0x800B3C90, 0x3484FFFF),
            "safe_x_store": (0x800B3C94, 0xACA3FFC0),
            "safe_z_store": (0x800B3C9C, 0xAC226558),
            "temporary_safe_y_store": (0x800B3CA8, 0xAC246554),
            "safe_heading_store": (0x800B3CB0, 0xA4226578),
            "ground_query": (0x800B3CB4, 0x0C00DE8E),
            "ground_y_adjust": (0x800B3CBC, 0x2442FF00),
            "final_safe_y_store": (0x800B3CC4, 0xAC226554),
        },
        "expected_events": (
            ("0x800b3c94", "0x800a6550", 4, "0x000b5e18", "0x000b1b54"),
            ("0x800b3c9c", "0x800a6558", 4, "0x00021f29", "0x00028835"),
            ("0x800b3ca8", "0x800a6554", 4, "0x000012fd", "0x7fffffff"),
            ("0x800b3cb0", "0x800a6578", 2, "0x000007ad", "0x00000800"),
            ("0x800b3cc4", "0x800a6554", 4, "0x7fffffff", "0x00002570"),
        ),
        "expected_heading_writes": 1,
        "bounded_role": (
            "status-0x0010-gated fixed X/Z/heading selector with "
            "ground-query-derived Y"),
    },
}
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800
OVERLAY_REL = "LEVEL03/LEVEL.BIN"
OVERLAY = ROOT / "REBUILD/files" / OVERLAY_REL
OVERLAY_OWNER_RANGE = (0x800B3C54, 0x800B3D78)
OVERLAY_OWNER_FILE_OFFSET = 0x2B4
SCENARIO = ROOT / "tools/scenarios/duckstation/pristine_checkpoint_respawn.yaml"
DENIAL_SCENARIO = ROOT / (
    "tools/scenarios/duckstation/pristine_c15_authored_row_denial.yaml")
CONTACT_SCENARIO = ROOT / (
    "tools/scenarios/duckstation/pristine_contact_respawn_safe_anchor.yaml")
PIT_BREADTH_SCENARIOS = (
    ROOT / "tools/scenarios/duckstation/pristine_scene10_pit_respawn.yaml",
    ROOT / "tools/scenarios/duckstation/pristine_scene4_pit_respawn.yaml",
)

FINAL_FRAME = 358
TAKEOFF_PRE_FRAME = 56
FALL_FRAME = 100
PRE_RESET_FRAME = 156
RESET_FRAME = 157
POST_RESET_FRAME = 160
MOVEMENT_FRAMES = tuple(range(57, 88))
ANCHOR_X_DELTA = 4096
SOURCE_X_DELTA = ANCHOR_X_DELTA >> 5
CONTACT_ANCHOR_FRAME = 350
CONTACT_RESET_FRAME = 355

PLAYER = 0x800A6500
MASTER_STATE = 0x800823A0
SCENE = 0x80082504
RESPAWN_TABLE_POINTER = 0x80096DA4
ANCHOR_STORES = {
    0x80054E70: 0xAC236550,
    0x80054E78: 0xAC246554,
    0x80054E80: 0xAC256558,
}

STATIC_REGIONS = {
    "bottomless_fall_transition": (0x800497F4, 0x80049874),
    "respawn_anchor_update": (0x80054C90, 0x80054EAC),
    "respawn_transition_state_handler": (0x8005B12C, 0x8005B440),
}
STATIC_WORDS = {
    "anchor_x_store": (0x80054E70, 0xAC236550),
    "anchor_y_store": (0x80054E78, 0xAC246554),
    "anchor_z_store": (0x80054E80, 0xAC256558),
    "respawn_anchor_x_load": (0x8005B1DC, 0x8CC66550),
    "respawn_anchor_y_load": (0x8005B1E4, 0x8C636554),
    "respawn_anchor_z_load": (0x8005B1EC, 0x8CE76558),
    "respawn_live_x_store": (0x8005B29C, 0xACA60000),
    "respawn_live_y_store": (0x8005B2A4, 0xAC236504),
    "respawn_live_z_store": (0x8005B2AC, 0xAC276508),
    "respawn_health_restore": (0x8005B30C, 0xA4226594),
    "respawn_lives_decrement": (0x8005B348, 0xA02665A0),
}
OVERLAY_WORDS = {
    "reset_gate_status_load": (0x800B3C64, 0x94620000),
    "reset_gate_status_mask": (0x800B3C6C, 0x30420010),
    "reset_gate_status_denial_branch": (0x800B3C70, 0x10400039),
    "respawn_table_pointer_load": (0x800B3C7C, 0x8D086DA4),
    "candidate_x_load": (0x800B3CAC, 0x8CA20004),
    "candidate_z_load": (0x800B3CC0, 0x8CA2000C),
    "selected_x_load": (0x800B3D14, 0x8C430004),
    "selected_x_scale": (0x800B3D20, 0x00031940),
    "selected_anchor_x_store": (0x800B3D24, 0xAC830000),
    "selected_z_load": (0x800B3D28, 0x8C42000C),
    "selected_z_scale": (0x800B3D38, 0x00021140),
    "selected_anchor_z_store": (0x800B3D40, 0xAC226558),
    "selected_ground_query": (0x800B3D44, 0x0C00DE8E),
    "selected_ground_y_adjust": (0x800B3D4C, 0x2442FF00),
    "selected_anchor_y_store": (0x800B3D54, 0xAC226554),
}
TRACE_RANGES = tuple(
    {"start": f"0x{start:08X}", "end": f"0x{end:08X}",
     "label": name, "max_pcs": 4096}
    for name, (start, end) in STATIC_REGIONS.items()
)
OWNER_TRACE_RANGES = (
    {"start": "0x800B3C54", "end": "0x800B3D78",
     "label": "overlay_safe_anchor_selector", "max_pcs": 4096},
    {"start": "0x8005B12C", "end": "0x8005B440",
     "label": "respawn_transition_state_handler", "max_pcs": 4096},
)
CONTACT_TRACE_RANGES = (
    {"start": "0x80054C90", "end": "0x80054EAC",
     "label": "continuous_safe_anchor_updater", "max_pcs": 4096},
    {"start": "0x8005B12C", "end": "0x8005B440",
     "label": "respawn_transition_state_handler", "max_pcs": 4096},
    {"start": "0x800B0000", "end": "0x800C0000",
     "label": "bug_bar_overlay_window", "max_pcs": 8192},
)
PIT_BREADTH_TRACE_RANGES = (
    {"start": "0x80054C90", "end": "0x80054EAC",
     "label": "continuous_safe_anchor_updater", "max_pcs": 4096},
    {"start": "0x8005B12C", "end": "0x8005B440",
     "label": "respawn_transition_state_handler", "max_pcs": 4096},
    {"start": "0x800B0000", "end": "0x800C0000",
     "label": "scene_overlay_window", "max_pcs": 16384},
)

EXPECTED_SEGMENTS = [
    {"first": 0, "last": 56, "input": {}},
    {"first": 57, "last": 59, "input": {"cross": True}},
    {"first": 60, "last": 65,
     "input": {"cross": True, "right": True, "up": True}},
    {"first": 66, "last": 84, "input": {"right": True, "up": True}},
    {"first": 85, "last": 87, "input": {"up": True}},
    {"first": 88, "last": 357, "input": {}},
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in capabilities.get("methods") or [])


def _exe_slice(exe: bytes, start: int, end: int) -> bytes:
    lo = EXE_HEADER + start - EXE_LOAD
    hi = EXE_HEADER + end - EXE_LOAD
    if lo < EXE_HEADER or hi > len(exe) or hi <= lo:
        raise SystemExit(f"invalid executable range 0x{start:08X}..0x{end:08X}")
    return exe[lo:hi]


def _exe_word(exe: bytes, address: int) -> int:
    return struct.unpack("<I", _exe_slice(exe, address, address + 4))[0]


def _overlay_slice(overlay: bytes, start: int, end: int) -> bytes:
    lo = OVERLAY_OWNER_FILE_OFFSET + start - OVERLAY_OWNER_RANGE[0]
    hi = OVERLAY_OWNER_FILE_OFFSET + end - OVERLAY_OWNER_RANGE[0]
    if lo < 0 or hi > len(overlay) or hi <= lo:
        raise SystemExit(
            f"invalid C15 overlay range 0x{start:08X}..0x{end:08X}")
    return overlay[lo:hi]


def _overlay_word(overlay: bytes, address: int) -> int:
    return struct.unpack("<I", _overlay_slice(
        overlay, address, address + 4))[0]


def _build_pit_writer_static_census() -> dict[str, Any]:
    staged_bins: dict[str, bytes] = {}
    for path in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL.BIN")):
        rel = path.relative_to(ROOT / "REBUILD/files").as_posix()
        data = path.read_bytes()
        verify_staged_input(rel, data)
        staged_bins[rel] = data

    result = {}
    for case_id, spec in PIT_WRITER_STATIC.items():
        data = staged_bins[spec["path"]]
        start, end = spec["runtime_range"]
        offset = spec["file_offset"]
        function = data[offset:offset + end - start]
        if len(function) != end - start or \
                _sha256_bytes(function) != spec["sha256"]:
            raise SystemExit(f"C15 {case_id} transition-writer slice drifted")
        instructions = {}
        for name, (address, expected) in spec["instructions"].items():
            word_offset = offset + address - start
            actual = struct.unpack_from("<I", data, word_offset)[0]
            if actual != expected:
                raise SystemExit(
                    f"C15 {case_id} word drifted at 0x{address:08X}: "
                    f"0x{actual:08X} != 0x{expected:08X}")
            instructions[name] = {
                "address": f"0x{address:08X}",
                "instruction_word": f"0x{actual:08X}",
                "file_offset": f"0x{word_offset:X}",
            }
        matches = []
        for rel, candidate in staged_bins.items():
            found = candidate.find(function)
            while found >= 0:
                matches.append({"path": rel, "file_offset": f"0x{found:X}"})
                found = candidate.find(function, found + 1)
        expected_match = [{
            "path": spec["path"], "file_offset": f"0x{offset:X}"}]
        if matches != expected_match:
            raise SystemExit(
                f"C15 {case_id} transition writer is not uniquely staged: "
                f"{matches}")
        result[case_id] = {
            "path": f"REBUILD/files/{spec['path']}",
            "file_sha256": _sha256(ROOT / "REBUILD/files" / spec["path"]),
            "file_size": len(data),
            "file_offset": f"0x{offset:X}",
            "runtime_start": f"0x{start:08X}",
            "runtime_end": f"0x{end:08X}",
            "size": len(function),
            "sha256": spec["sha256"],
            "unique_staged_matches": matches,
            "instructions": instructions,
            "bounded_role": spec["bounded_role"],
        }
    return result


def build_static_census() -> dict[str, Any]:
    exe = EXE.read_bytes()
    verify_staged_input(EXE_REL, exe)
    overlay = OVERLAY.read_bytes()
    verify_staged_input(OVERLAY_REL, overlay)
    regions = {
        name: {
            "start": f"0x{start:08X}", "end": f"0x{end:08X}",
            "size": end - start,
            "file_offset": f"0x{EXE_HEADER + start - EXE_LOAD:X}",
            "sha256": _sha256_bytes(_exe_slice(exe, start, end)),
        }
        for name, (start, end) in STATIC_REGIONS.items()
    }
    words = {}
    for name, (address, expected) in STATIC_WORDS.items():
        actual = _exe_word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"C15 static word drifted at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        words[name] = {
            "address": f"0x{address:08X}",
            "instruction_word": f"0x{actual:08X}",
            "file_offset": f"0x{EXE_HEADER + address - EXE_LOAD:X}",
        }
    overlay_words = {}
    for name, (address, expected) in OVERLAY_WORDS.items():
        actual = _overlay_word(overlay, address)
        if actual != expected:
            raise SystemExit(
                f"C15 overlay word drifted at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        overlay_words[name] = {
            "address": f"0x{address:08X}",
            "instruction_word": f"0x{actual:08X}",
            "file_offset": (
                f"0x{OVERLAY_OWNER_FILE_OFFSET + address - OVERLAY_OWNER_RANGE[0]:X}"),
        }
    overlay_owner = _overlay_slice(overlay, *OVERLAY_OWNER_RANGE)
    return {
        "resident_executable": {
            "path": f"REBUILD/files/{EXE_REL}", "sha256": _sha256(EXE),
            "size": EXE.stat().st_size,
        },
        "regions": regions,
        "instructions": words,
        "overlay_safe_anchor_selector": {
            "path": f"REBUILD/files/{OVERLAY_REL}",
            "file_sha256": _sha256(OVERLAY), "file_size": len(overlay),
            "runtime_start": f"0x{OVERLAY_OWNER_RANGE[0]:08X}",
            "runtime_end": f"0x{OVERLAY_OWNER_RANGE[1]:08X}",
            "file_offset": f"0x{OVERLAY_OWNER_FILE_OFFSET:X}",
            "size": len(overlay_owner),
            "sha256": _sha256_bytes(overlay_owner),
            "instructions": overlay_words,
            "bounded_role": (
                "When player status bit 0x0010 is set, the function selects the "
                "nearest X/Z row through pointer 0x80096DA4, writes scaled X/Z "
                "to safe-anchor fields, and derives safe Y from ground height."),
        },
        "pit_transition_writers": _build_pit_writer_static_census(),
        "typed_player_state": {
            "live_xyz": {"address": "0x800A6500", "width": "3xs32"},
            "safe_anchor_xyz": {"address": "0x800A6550", "width": "3xs32"},
            "safe_anchor_heading": {"address": "0x800A6578", "width": "s16"},
            "safe_position_status_bit": {
                "address": "0x800A6590", "width": "u16", "mask": "0x0008",
                "boundary": "shared status word; this campaign proves only the updater clear/set operation"},
            "respawn_selector_status_bit": {
                "address": "0x800A6590", "width": "u16", "mask": "0x0010",
                "boundary": "overlay 0x800B3C54 gate; whole-word semantics remain shared"},
            "true_health": {"address": "0x800A6594", "width": "s16"},
            "lives": {"address": "0x800A65A0", "width": "u8"},
        },
        "bounded_static_conclusion": (
            "0x80054C90 conditionally copies live XYZ to player+0x50/+0x54/+0x58; "
            "the pristine LEVEL03/LEVEL.BIN slice at runtime 0x800B3C54 selects "
            "and overwrites that tuple for its status-0x0010 path; 0x8005B134 "
            "then loads the tuple and writes live XYZ. The scene-10 and scene-4 "
            "transition paths use distinct exact pristine LEVEL10 and LEVEL04 "
            "writers, respectively. These exact chains are not generalized to "
            "every overlay or death class."),
    }


def _pad_signature(pad: dict[str, Any]) -> dict[str, Any]:
    axes = {"lx", "ly", "rx", "ry"}
    result = {key: value for key, value in pad.items()
              if key not in axes and bool(value)}
    result.update({key: value for key, value in pad.items()
                   if key in axes and value != 128})
    return dict(sorted(result.items()))


def _input_segments(movie: dict[str, Any]) -> list[dict[str, Any]]:
    frames = movie.get("frames") or []
    if not frames:
        return []
    first = 0
    signature = _pad_signature((frames[0].get("ports") or {}).get("0") or {})
    rows = []
    for index, row in enumerate(frames[1:], 1):
        current = _pad_signature((row.get("ports") or {}).get("0") or {})
        if current != signature:
            rows.append({"first": first, "last": index - 1, "input": signature})
            first, signature = index, current
    rows.append({"first": first, "last": len(frames) - 1, "input": signature})
    return rows


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_pin = entries.get(MOVIE_REL)
    save = verify_declared_save_fixture(SAVE, allowed_media_classes={"pristine"})
    if not isinstance(movie_pin, dict) or \
            movie_pin.get("media_class") != "pristine_serial" or \
            movie_pin.get("sha256") != _sha256(MOVIE) or \
            movie_pin.get("size") != MOVIE.stat().st_size:
        raise SystemExit("C15 LEVEL02 movie central pin drifted")
    movie = json.loads(MOVIE.read_text())
    start = movie.get("start_state") or {}
    segments = _input_segments(movie)
    if movie.get("version") != 3 or movie.get("game_serial") != "SCUS-94288" or \
            len(movie.get("frames") or []) != FINAL_FRAME or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            start.get("file_size") != save["size"] or segments != EXPECTED_SEGMENTS:
        raise SystemExit("C15 LEVEL02 movie metadata or input segments drifted")
    contact = c16.build_fixture_census()
    if c16.MOVIE_REL != CONTACT_MOVIE_REL or c16.SAVE_REL != CONTACT_SAVE_REL:
        raise SystemExit("C15/C16 contact fixture constants diverged")
    pit_breadth = []
    for case in PIT_BREADTH_CASES:
        movie_rel = case["movie_rel"]
        save_rel = case["save_rel"]
        movie_path = ROOT / movie_rel
        save_path = ROOT / save_rel
        pin = entries.get(movie_rel)
        save_pin = verify_declared_save_fixture(
            save_path, allowed_media_classes={"pristine"})
        if not isinstance(pin, dict) or \
                pin.get("media_class") != "pristine_serial" or \
                pin.get("sha256") != _sha256(movie_path) or \
                pin.get("size") != movie_path.stat().st_size:
            raise SystemExit(f"C15 pit-breadth movie central pin drifted: {movie_rel}")
        source = json.loads(movie_path.read_text())
        start = source.get("start_state") or {}
        if source.get("version") != 3 or \
                source.get("game_serial") != "SCUS-94288" or \
                len(source.get("frames") or []) != case["frames"] or \
                start.get("game_serial") != "SCUS-94288" or \
                start.get("from_boot") is not False or \
                start.get("reproducible_only_from_state") is not True or \
                start.get("file_size") != save_pin["size"]:
            raise SystemExit(f"C15 pit-breadth metadata drifted: {movie_rel}")
        pit_breadth.append({
            "id": case["id"],
            "movie": {
                "path": movie_rel,
                "sha256": pin["sha256"],
                "size": pin["size"],
                "media_class": pin["media_class"],
                "version": source["version"],
                "frames": len(source["frames"]),
                "initial_frame": source.get("initial_frame"),
                "input_segments": _input_segments(source),
            },
            "save": save_pin,
            "declared_start_state": {
                "frame": start.get("frame"),
                "pc": start.get("pc"),
                "sp": start.get("sp"),
                "game_serial": start.get("game_serial"),
                "from_boot": start.get("from_boot"),
                "reproducible_only_from_state":
                    start.get("reproducible_only_from_state"),
            },
            "expected_typed_boundary": {
                key: case[key] for key in (
                    "scene", "pre_reset_frame", "reset_frame", "pre_health",
                    "pre_lives", "post_health", "post_lives")
            },
        })
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "movie": {
            "path": MOVIE_REL, "sha256": movie_pin["sha256"],
            "size": movie_pin["size"], "media_class": movie_pin["media_class"],
            "version": movie["version"], "frames": len(movie["frames"]),
            "initial_frame": movie.get("initial_frame"),
            "input_segments": segments,
        },
        "save": save,
        "declared_start_state": {
            "frame": start.get("frame"), "pc": start.get("pc"),
            "sp": start.get("sp"), "game_serial": start.get("game_serial"),
            "from_boot": start.get("from_boot"),
            "reproducible_only_from_state": start.get("reproducible_only_from_state"),
        },
        "contact_death": contact,
        "pit_breadth": pit_breadth,
        "classification_boundary": (
            "The filenames are leads only. Every consumed pair is centrally "
            "pinned, each state is inspected before load, mounted/save media are "
            "pristine, and every conclusion below comes from typed replay outcomes."),
    }


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _read_main_ram(client: Any) -> bytes:
    return b"".join(_read_memory(client, 0x80000000 + offset, 0x10000)
                    for offset in range(0, 0x200000, 0x10000))


def _snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    player = _read_memory(client, PLAYER, 0xA4)
    player_status_word = struct.unpack_from("<H", player, 0x90)[0]
    return {
        "status": {key: status.get(key) for key in
                   ("pc", "sp", "frame", "cycle", "paused", "game_serial")},
        "scene": struct.unpack("<I", _read_memory(client, SCENE, 4))[0],
        "master_state": struct.unpack(
            "<H", _read_memory(client, MASTER_STATE, 2))[0],
        "live_xyz": list(struct.unpack_from("<iii", player, 0x00)),
        "safe_anchor_xyz": list(struct.unpack_from("<iii", player, 0x50)),
        "safe_anchor_heading": struct.unpack_from("<h", player, 0x78)[0],
        "player_status_word": player_status_word,
        "safe_position_status_bit_0x0008": bool(player_status_word & 8),
        "respawn_selector_status_bit_0x0010": bool(player_status_word & 0x10),
        "vertical_velocity": struct.unpack_from("<i", player, 0x30)[0],
        "player_state": struct.unpack_from("<h", player, 0x80)[0],
        "grounded": struct.unpack_from("<h", player, 0x82)[0],
        "true_health": struct.unpack_from("<h", player, 0x94)[0],
        "lives": player[0xA0],
        "anchor_store_words": {
            f"0x{address:08X}": f"0x{struct.unpack('<I', _read_memory(client, address, 4))[0]:08X}"
            for address in ANCHOR_STORES
        },
    }


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    coverage = []
    for row in trace.get("coverage") or []:
        data = row.get("coverage") or {}
        pcs = data.get("pcs") or []
        coverage.append({
            "label": row.get("label"), "range": row.get("range"),
            "total_hits": data.get("total_hits"),
            "distinct_pc_count": data.get("distinct_pc_count"),
            "truncated": data.get("truncated", False), "pcs": pcs,
            "pcs_sha256": _sha256_bytes(
                json.dumps(pcs, separators=(",", ":")).encode()),
        })
    return {
        key: trace.get(key) for key in (
            "target_frame", "trace_mode", "configured_execution_mode",
            "comparison_execution_mode", "control", "instrumented", "comparison")
    } | {"coverage": coverage}


def _trace_snapshot(client: Any, path: Path, frame: int,
                    ranges: tuple[dict[str, Any], ...] = TRACE_RANGES) -> dict[str, Any]:
    trace = _compact_trace(client.call("movie.traceToFrame", {
        "path": str(path.resolve()), "frame": frame, "ranges": list(ranges)},
        timeout=900))
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row["truncated"] for row in trace["coverage"]):
        raise SystemExit(f"C15 trace is not cycle-neutral at movie frame {frame}")
    movie = client.call("movie.status", {})
    if movie.get("reproducible") is not True or movie.get("truncated") is not False:
        raise SystemExit(f"C15 trace lost its movie anchor at frame {frame}: {movie}")
    return {
        "movie_frame": frame,
        "movie_status": {key: movie.get(key) for key in
                         ("reproducible", "truncated", "frame_count",
                          "playback_index", "playing")},
        "snapshot": _snapshot(client), "cycle_neutral_trace": trace,
    }


def _canonical_movie_hash(movie: dict[str, Any], anchor: str) -> str:
    canonical = copy.deepcopy(movie)
    (canonical.get("start_state") or {})["path"] = anchor
    return _sha256_bytes(json.dumps(
        canonical, sort_keys=True, separators=(",", ":")).encode())


def _write_neutral_variant(source: dict[str, Any], path: Path) -> dict[str, Any]:
    movie = copy.deepcopy(source)
    movie["start_state"]["path"] = str(SAVE.resolve())
    movie["start_state"]["file_size"] = SAVE.stat().st_size
    neutral_pad = copy.deepcopy(movie["frames"][0]["ports"]["0"])
    if _pad_signature(neutral_pad):
        raise SystemExit("C15 frame-zero neutral pad is no longer neutral")
    for frame in MOVEMENT_FRAMES:
        if not _pad_signature(movie["frames"][frame]["ports"]["0"]):
            raise SystemExit(f"C15 movement source frame {frame} is neutral")
        movie["frames"][frame]["ports"]["0"] = copy.deepcopy(neutral_pad)
    path.write_text(json.dumps(movie, separators=(",", ":")) + "\n")
    return {
        "source_sha256": _sha256(MOVIE),
        "semantic_sha256": _canonical_movie_hash(movie, SAVE_REL),
        "changed_frames": list(MOVEMENT_FRAMES),
        "changed_field": "only ports.0 input at recorded frames 57..87",
        "replacement": "the exact neutral pad record from source frame 0",
        "transient_storage": "temporary directory; derivative deleted before retention",
    }


def _write_u32(client: Any, address: int, value: int) -> None:
    client.call("debugger.writeU32", {
        "address": f"0x{address:08X}", "value": value & 0xFFFFFFFF})
    actual = struct.unpack("<I", _read_memory(client, address, 4))[0]
    if actual != value & 0xFFFFFFFF:
        raise SystemExit(
            f"C15 checked write failed at 0x{address:08X}: 0x{actual:08X}")


def _write_u16(client: Any, address: int, value: int) -> None:
    client.call("debugger.writeU16", {
        "address": f"0x{address:08X}", "value": value & 0xFFFF})
    actual = struct.unpack("<H", _read_memory(client, address, 2))[0]
    if actual != value & 0xFFFF:
        raise SystemExit(
            f"C15 checked write failed at 0x{address:08X}: 0x{actual:04X}")


def _save_state(client: Any, path: Path) -> dict[str, Any]:
    saved = client.call("emulator.saveState", {"path": str(path.resolve())})
    info = client.call("emulator.getStateInfo", {"path": str(path.resolve())})
    if saved.get("saved") is not True or info.get("valid") is not True or \
            info.get("serial") != "SCUS-94288":
        raise SystemExit(f"C15 transient state failed validation: {saved} / {info}")
    return {
        "size": path.stat().st_size, "sha256": _sha256(path),
        "version": info.get("version"), "serial": info.get("serial"),
    }


def _load_state(client: Any, path: Path) -> None:
    client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})


def _diff_addresses(left: bytes, right: bytes) -> list[str]:
    return [f"0x{0x80000000 + index:08X}"
            for index, (a, b) in enumerate(zip(left, right)) if a != b]


def _write_suffix(source: dict[str, Any], state: Path, state_info: dict[str, Any],
                  path: Path, label: str, snapshot: dict[str, Any],
                  *, source_frame: int = FALL_FRAME) -> dict[str, Any]:
    movie = copy.deepcopy(source)
    movie["frames"] = movie["frames"][source_frame:]
    movie["initial_frame"] = int(movie["initial_frame"]) + source_frame
    movie["start_state"] = {
        "path": str(state.resolve()), "loaded_before_recording": True,
        "from_boot": False, "game_serial": "SCUS-94288",
        "game_title": source.get("game_title"),
        "frame": snapshot["status"]["frame"],
        "pc": snapshot["status"]["pc"], "sp": snapshot["status"]["sp"],
        "file_size": state_info["size"], "sha256": state_info["sha256"],
        "reproducible_only_from_state": True,
    }
    path.write_text(json.dumps(movie, separators=(",", ":")) + "\n")
    return {
        "label": label, "source_first_frame": source_frame,
        "frames": len(movie["frames"]),
        "semantic_sha256": _canonical_movie_hash(movie, label),
        "transient_storage": "temporary directory; derivative deleted before retention",
    }


def _coverage_by_label(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row.get("label"): row for row in
            (trace.get("cycle_neutral_trace") or {}).get("coverage") or []}


def _derive_reset_owner(client: Any, source: dict[str, Any],
                        temp_dir: Path) -> dict[str, Any]:
    pre = _trace_snapshot(
        client, MOVIE, PRE_RESET_FRAME, ranges=OWNER_TRACE_RANGES)
    post = _trace_snapshot(
        client, MOVIE, RESET_FRAME, ranges=OWNER_TRACE_RANGES)
    # traceToFrame leaves the instrumented pass at its target. Return to the
    # exact pre-reset boundary before saving the counterfactual anchor.
    pre_anchor = _trace_snapshot(
        client, MOVIE, PRE_RESET_FRAME, ranges=OWNER_TRACE_RANGES)
    if not _trace_signatures_equal(pre, pre_anchor):
        raise SystemExit("C15 frame-156 owner anchor did not reproduce exactly")
    base_state = temp_dir / "frame156-owner-base.sav"
    base_info = _save_state(client, base_state)
    base_ram = _read_main_ram(client)

    runtime_owner = _read_memory(
        client, OVERLAY_OWNER_RANGE[0],
        OVERLAY_OWNER_RANGE[1] - OVERLAY_OWNER_RANGE[0])
    static_owner = build_static_census()["overlay_safe_anchor_selector"]
    runtime_owner_sha256 = _sha256_bytes(runtime_owner)
    if runtime_owner_sha256 != static_owner["sha256"]:
        raise SystemExit("C15 runtime overlay owner does not match pristine slice")

    pointer = struct.unpack(
        "<I", _read_memory(client, RESPAWN_TABLE_POINTER, 4))[0]
    count = struct.unpack("<H", _read_memory(client, pointer, 2))[0]
    if not 1 <= count <= 256:
        raise SystemExit(f"C15 unsafe respawn-table count: {count}")
    table_bytes = _read_memory(client, pointer, 4 + count * 12 + 4)
    live_x, _, live_z = pre["snapshot"]["live_xyz"]
    query_x, query_z = live_x >> 5, live_z >> 5
    records = []
    for index in range(count):
        x_raw = struct.unpack_from("<i", table_bytes, 4 + index * 12)[0]
        z_raw = struct.unpack_from("<i", table_bytes, 12 + index * 12)[0]
        records.append({
            "index": index, "x_raw": x_raw, "z_raw": z_raw,
            "distance_squared": (
                (query_x - x_raw) ** 2 + (query_z - z_raw) ** 2),
        })
    selected = min(records, key=lambda row: row["distance_squared"])
    source_x_address = pointer + 4 + selected["index"] * 12

    provenance = {
        "overlay_runtime_address": client.call(
            "transferLog.resolve", {"address": "0x800B3C54"}),
        "selected_table_x_address": client.call(
            "transferLog.resolve", {"address": f"0x{source_x_address:08X}"}),
    }

    branches: dict[str, dict[str, Any]] = {}
    start_rams: dict[str, bytes] = {}
    for name, delta_raw in (
            ("owner_control", 0),
            ("selected_x_source_plus_128", SOURCE_X_DELTA)):
        _load_state(client, base_state)
        before = struct.unpack(
            "<i", _read_memory(client, source_x_address, 4))[0]
        if delta_raw:
            _write_u32(client, source_x_address, before + delta_raw)
        start_ram = _read_main_ram(client)
        start_rams[name] = start_ram
        start_snapshot = _snapshot(client)
        state = temp_dir / f"{name}.sav"
        state_info = _save_state(client, state)
        movie_path = temp_dir / f"{name}.movie.json"
        recipe = _write_suffix(
            source, state, state_info, movie_path, name, start_snapshot,
            source_frame=PRE_RESET_FRAME)
        replay = _trace_snapshot(
            client, movie_path, RESET_FRAME - PRE_RESET_FRAME,
            ranges=OWNER_TRACE_RANGES)
        branches[name] = {
            "mutation": {
                "source_address": f"0x{source_x_address:08X}",
                "source_x_raw_delta": delta_raw,
                "expected_scaled_x_delta": delta_raw << 5,
            },
            "source_x_raw_before": before,
            "source_x_raw_after": before + delta_raw,
            "start_main_ram_sha256": _sha256_bytes(start_ram),
            "start_snapshot": start_snapshot,
            "suffix_recipe": recipe,
            "post_reset": replay,
        }

    _load_state(client, base_state)
    status_address = PLAYER + 0x90
    status_before = struct.unpack(
        "<H", _read_memory(client, status_address, 2))[0]
    if status_before & 0x0010 == 0:
        raise SystemExit("C15 frame-156 selector status bit is no longer set")
    status_after = status_before & ~0x0010
    _write_u16(client, status_address, status_after)
    denied_start_ram = _read_main_ram(client)
    start_rams["selector_status_bit_cleared"] = denied_start_ram
    denied_start_snapshot = _snapshot(client)
    denied_state = temp_dir / "selector-status-bit-cleared.sav"
    denied_state_info = _save_state(client, denied_state)
    denied_movie = temp_dir / "selector-status-bit-cleared.movie.json"
    denied_recipe = _write_suffix(
        source, denied_state, denied_state_info, denied_movie,
        "selector_status_bit_cleared", denied_start_snapshot,
        source_frame=PRE_RESET_FRAME)
    denied_replay = _trace_snapshot(
        client, denied_movie, RESET_FRAME - PRE_RESET_FRAME,
        ranges=OWNER_TRACE_RANGES)
    branches["selector_status_bit_cleared"] = {
        "mutation": {
            "status_address": f"0x{status_address:08X}",
            "cleared_mask": "0x0010",
            "status_before": status_before,
            "status_after": status_after,
        },
        "start_main_ram_sha256": _sha256_bytes(denied_start_ram),
        "start_snapshot": denied_start_snapshot,
        "suffix_recipe": denied_recipe,
        "post_reset": denied_replay,
    }

    changed = _diff_addresses(
        start_rams["owner_control"],
        start_rams["selected_x_source_plus_128"])
    denial_changed = _diff_addresses(
        start_rams["owner_control"],
        start_rams["selector_status_bit_cleared"])
    return {
        "boundary": {
            "pre_reset_movie_frame": PRE_RESET_FRAME,
            "reset_movie_frame": RESET_FRAME,
            "pre_reset": pre, "reset": post,
        },
        "runtime_owner": {
            "address_range": ["0x800B3C54", "0x800B3D78"],
            "size": len(runtime_owner),
            "runtime_sha256": runtime_owner_sha256,
            "pristine_file": f"REBUILD/files/{OVERLAY_REL}",
            "pristine_file_offset": f"0x{OVERLAY_OWNER_FILE_OFFSET:X}",
            "pristine_slice_sha256": static_owner["sha256"],
            "transfer_provenance": provenance,
        },
        "selector": {
            "table_pointer_global": "0x80096DA4",
            "runtime_table_pointer": f"0x{pointer:08X}",
            "runtime_table_count": count,
            "runtime_table_sha256": _sha256_bytes(table_bytes),
            "query_player_xz_div32": [query_x, query_z],
            "selected": selected,
            "selected_x_source_address": f"0x{source_x_address:08X}",
            "selected_scaled_x": selected["x_raw"] << 5,
            "selection_rule": (
                "minimum squared X/Z distance after player coordinates and "
                "scene-local runtime row coordinates are compared in the >>5 domain"),
            "source_provenance_boundary": (
                "transferLog.resolve cannot map this save-state-restored table "
                "back to a disc file. The runtime layout, selected row and causal "
                "consumer are confirmed; authored file origin remains open."),
        },
        "branches": branches,
        "single_variable_guard": {
            "changed_byte_addresses": changed,
            "changed_word": f"0x{source_x_address:08X}",
            "allowed_word_range": [
                f"0x{source_x_address:08X}",
                f"0x{source_x_address + 3:08X}"],
        },
        "selector_denial_single_variable_guard": {
            "changed_byte_addresses": denial_changed,
            "changed_word": f"0x{status_address:08X}",
            "allowed_word_range": [
                f"0x{status_address:08X}", f"0x{status_address + 1:08X}"],
        },
        "causal_result": (
            "Changing only the selected row's raw X by +128 changes frame-157 "
            "safe/live X by +4096 under identical suffix input and identical "
            "owner/handler execution coverage. Z and health/lives are unchanged; "
            "Y is recomputed by the owner's ground-height query."),
        "selector_denial_causal_result": (
            "Clearing only player status mask 0x0010 at the exact frame-156 "
            "boundary denies the pristine LEVEL03 authored-row selector. The "
            "resident handler still consumes the previously retained safe anchor; "
            "this confirms one activation/denial input for this scene and boundary, "
            "not the source or policy of the status bit."),
        "transient_storage": (
            "all frame-156 states and suffix movies were deleted before retention"),
    }


def _derive_counterfactuals(client: Any, source: dict[str, Any],
                            temp_dir: Path) -> dict[str, Any]:
    anchor_trace = _trace_snapshot(
        client, MOVIE, FALL_FRAME, ranges=(TRACE_RANGES[0],))
    base_snapshot = anchor_trace["snapshot"]
    base_ram = _read_main_ram(client)
    base_state = temp_dir / "frame100-base.sav"
    base_info = _save_state(client, base_state)

    def branch_state(name: str, *, suppress_writer: bool,
                     anchor_delta: int) -> tuple[Path, dict[str, Any], bytes, dict[str, Any]]:
        _load_state(client, base_state)
        if suppress_writer:
            for address, expected in ANCHOR_STORES.items():
                actual = struct.unpack("<I", _read_memory(client, address, 4))[0]
                if actual != expected:
                    raise SystemExit(
                        f"C15 anchor store drifted before patch: 0x{actual:08X}")
                _write_u32(client, address, 0)
        if anchor_delta:
            before = struct.unpack("<i", _read_memory(client, PLAYER + 0x50, 4))[0]
            _write_u32(client, PLAYER + 0x50, before + anchor_delta)
        ram = _read_main_ram(client)
        snapshot = _snapshot(client)
        path = temp_dir / f"{name}.sav"
        info = _save_state(client, path)
        return path, info, ram, snapshot

    branches: dict[str, dict[str, Any]] = {}
    branch_rows: dict[str, tuple[Path, bytes]] = {}
    for name, suppress, delta in (
            ("anchor_control", False, 0),
            ("anchor_x_plus_4096", False, ANCHOR_X_DELTA),
            ("stores_nopped_control", True, 0),
            ("stores_nopped_anchor_x_plus_4096", True, ANCHOR_X_DELTA)):
        state, info, ram, snapshot = branch_state(
            name, suppress_writer=suppress, anchor_delta=delta)
        movie_path = temp_dir / f"{name}.movie.json"
        recipe = _write_suffix(source, state, info, movie_path, name, snapshot)
        replay = _trace_snapshot(
            client, movie_path, POST_RESET_FRAME - FALL_FRAME,
            ranges=(TRACE_RANGES[2],))
        branches[name] = {
            "mutation": {
                "anchor_x_delta": delta,
                "suppressed_instruction_addresses": [
                    f"0x{address:08X}" for address in ANCHOR_STORES]
                if suppress else [],
            },
            "start_snapshot": snapshot,
            "start_main_ram_sha256": _sha256_bytes(ram),
            "suffix_recipe": recipe, "post_reset": replay,
        }
        branch_rows[name] = (ram, state)

    anchor_diff = _diff_addresses(
        branch_rows["anchor_control"][0],
        branch_rows["anchor_x_plus_4096"][0])
    nopped_anchor_diff = _diff_addresses(
        branch_rows["stores_nopped_control"][0],
        branch_rows["stores_nopped_anchor_x_plus_4096"][0])
    patch_diff = _diff_addresses(
        branch_rows["anchor_control"][0],
        branch_rows["stores_nopped_control"][0])
    return {
        "anchor_movie_frame": FALL_FRAME,
        "anchor_cycle_neutral_trace": anchor_trace["cycle_neutral_trace"],
        "base_snapshot": base_snapshot,
        "base_main_ram_sha256": _sha256_bytes(base_ram),
        "branch_recipes": branches,
        "single_variable_guards": {
            "anchor_only_changed_byte_addresses": anchor_diff,
            "nopped_pair_anchor_only_changed_byte_addresses": nopped_anchor_diff,
            "nopped_control_changed_byte_addresses": patch_diff,
            "anchor_only_changed_words": ["0x800A6550"],
            "nopped_instruction_words": [
                f"0x{address:08X}" for address in ANCHOR_STORES],
        },
        "bounded_result": (
            "The anchor-X-only pair converges by source frame 160. The same "
            "convergence occurs when all three continuous anchor stores are NOPed "
            "in both branches, so the stable LEVEL02 pit postcondition is supplied "
            "by another transition/reset owner. This does not erase the static "
            "0x8005B134 anchor read or prove the result for other death classes."),
        "transient_storage": (
            "all derived states and suffix movies were deleted before retention"),
    }


def _derive_contact_death_control(client: Any, media_identity: dict[str, Any],
                                  temp_dir: Path) -> dict[str, Any]:
    source = json.loads(CONTACT_MOVIE.read_text())
    lives_one_state = temp_dir / "contact-lives-one.sav"
    lives_one_recipe = c16._create_lives_one_state(
        client, lives_one_state, media_identity)
    lives_one_movie = temp_dir / "contact-lives-one.movie.json"
    lives_one_movie_recipe = c16._write_variant(
        source, lives_one_movie, start_state=lives_one_state,
        anchor_label="<transient-one-byte-lives-state>")

    start = _trace_snapshot(
        client, lives_one_movie, 0, ranges=CONTACT_TRACE_RANGES)
    anchor = _trace_snapshot(
        client, lives_one_movie, CONTACT_ANCHOR_FRAME,
        ranges=CONTACT_TRACE_RANGES)
    base_state = temp_dir / "contact-frame350-base.sav"
    base_info = _save_state(client, base_state)
    base_ram = _read_main_ram(client)

    branches: dict[str, dict[str, Any]] = {}
    start_rams: dict[str, bytes] = {}
    for name, delta in (("safe_anchor_control", 0),
                        ("safe_anchor_x_plus_4096", ANCHOR_X_DELTA)):
        _load_state(client, base_state)
        before = struct.unpack(
            "<i", _read_memory(client, PLAYER + 0x50, 4))[0]
        if delta:
            _write_u32(client, PLAYER + 0x50, before + delta)
        start_ram = _read_main_ram(client)
        start_rams[name] = start_ram
        snapshot = _snapshot(client)
        state = temp_dir / f"contact-{name}.sav"
        state_info = _save_state(client, state)
        movie = temp_dir / f"contact-{name}.movie.json"
        recipe = _write_suffix(
            source, state, state_info, movie, name, snapshot,
            source_frame=CONTACT_ANCHOR_FRAME)
        post = _trace_snapshot(
            client, movie, CONTACT_RESET_FRAME - CONTACT_ANCHOR_FRAME,
            ranges=CONTACT_TRACE_RANGES)
        branches[name] = {
            "mutation": {
                "address": "0x800A6550", "width": "s32",
                "safe_anchor_x_delta": delta,
            },
            "safe_anchor_x_before": before,
            "safe_anchor_x_after": before + delta,
            "start_snapshot": snapshot,
            "start_main_ram_sha256": _sha256_bytes(start_ram),
            "suffix_recipe": recipe,
            "first_completed_respawn_boundary": post,
        }

    return {
        "fixture_role": (
            "existing Bug Bar contact-death lead; filename assigns no actor, "
            "enemy or hazard-family semantics"),
        "lives_one_state_recipe": lives_one_recipe,
        "lives_one_movie_recipe": lives_one_movie_recipe,
        "start_boundary": start,
        "fatal_anchor": {
            "source_movie_frame": CONTACT_ANCHOR_FRAME,
            "trace": anchor,
            "base_state": base_info,
            "base_main_ram_sha256": _sha256_bytes(base_ram),
        },
        "branches": branches,
        "single_variable_guard": {
            "changed_byte_addresses": _diff_addresses(
                start_rams["safe_anchor_control"],
                start_rams["safe_anchor_x_plus_4096"]),
            "changed_word": "0x800A6550",
            "allowed_word_range": ["0x800A6550", "0x800A6553"],
        },
        "causal_result": (
            "At the first completed ordinary-respawn boundary, changing only "
            "fatal-state safe X by +4096 changes both safe and live X by exactly "
            "+4096. Y/Z, health/lives and scene are unchanged; both branches "
            "have identical safe-updater, resident-handler and Bug Bar overlay "
            "coverage and independently match their uninstrumented replay."),
        "transient_storage": (
            "the lives-one state, frame-350 states and suffix movies were "
            "deleted before retention"),
    }


def _derive_pit_breadth(client: Any, temp_dir: Path) -> list[dict[str, Any]]:
    """Reproduce two additional pit-reset boundaries and perturb only safe X.

    Passive ``movie.traceToFrame`` pairs carry behavior/timing authority.  Each
    counterfactual starts from the exact pre-reset boundary and changes at most
    the safe-X word, then replays one original input frame.  Runtime overlay
    bytes are retained only as hashes/words; no save or movie derivative leaves
    the temporary directory.
    """
    rows = []
    static_owner_sha = build_static_census()[
        "overlay_safe_anchor_selector"]["sha256"]
    for case in PIT_BREADTH_CASES:
        movie_path = ROOT / case["movie_rel"]
        source = json.loads(movie_path.read_text())
        pre_frame = case["pre_reset_frame"]
        reset_frame = case["reset_frame"]
        pre = _trace_snapshot(
            client, movie_path, pre_frame, ranges=PIT_BREADTH_TRACE_RANGES)
        post = _trace_snapshot(
            client, movie_path, reset_frame, ranges=PIT_BREADTH_TRACE_RANGES)
        # Return to a separately reproduced pre-reset origin before saving it.
        origin = _trace_snapshot(
            client, movie_path, pre_frame, ranges=PIT_BREADTH_TRACE_RANGES)
        if not _trace_signatures_equal(pre, origin):
            raise SystemExit(
                f"C15 {case['id']} pre-reset origin did not reproduce exactly")

        runtime_owner = _read_memory(
            client, OVERLAY_OWNER_RANGE[0],
            OVERLAY_OWNER_RANGE[1] - OVERLAY_OWNER_RANGE[0])
        runtime_words = {
            f"0x{address:08X}":
                f"0x{struct.unpack('<I', _read_memory(client, address, 4))[0]:08X}"
            for address, _ in OVERLAY_WORDS.values()
        }
        base_state = temp_dir / f"{case['id']}-pre-reset.sav"
        base_info = _save_state(client, base_state)
        base_ram = _read_main_ram(client)

        branches: dict[str, dict[str, Any]] = {}
        start_rams: dict[str, bytes] = {}
        for name, delta in (("safe_anchor_control", 0),
                            ("safe_anchor_x_plus_4096", ANCHOR_X_DELTA)):
            _load_state(client, base_state)
            before = struct.unpack(
                "<i", _read_memory(client, PLAYER + 0x50, 4))[0]
            if delta:
                _write_u32(client, PLAYER + 0x50, before + delta)
            start_ram = _read_main_ram(client)
            start_rams[name] = start_ram
            start_snapshot = _snapshot(client)
            state = temp_dir / f"{case['id']}-{name}.sav"
            state_info = _save_state(client, state)
            suffix = temp_dir / f"{case['id']}-{name}.movie.json"
            recipe = _write_suffix(
                source, state, state_info, suffix,
                f"{case['id']}:{name}", start_snapshot,
                source_frame=pre_frame)
            replay = _trace_snapshot(
                client, suffix, reset_frame - pre_frame,
                ranges=PIT_BREADTH_TRACE_RANGES)
            branches[name] = {
                "mutation": {
                    "address": "0x800A6550", "width": "s32",
                    "safe_anchor_x_delta": delta,
                },
                "safe_anchor_x_before": before,
                "safe_anchor_x_after": before + delta,
                "start_snapshot": start_snapshot,
                "start_main_ram_sha256": _sha256_bytes(start_ram),
                "suffix_recipe": recipe,
                "post_reset": replay,
            }

        changed = _diff_addresses(
            start_rams["safe_anchor_control"],
            start_rams["safe_anchor_x_plus_4096"])
        control_snapshot = branches["safe_anchor_control"][
            "post_reset"]["snapshot"]
        changed_snapshot = branches["safe_anchor_x_plus_4096"][
            "post_reset"]["snapshot"]
        x_delta = changed_snapshot["live_xyz"][0] - \
            control_snapshot["live_xyz"][0]
        safe_x_delta = changed_snapshot["safe_anchor_xyz"][0] - \
            control_snapshot["safe_anchor_xyz"][0]
        if (x_delta, safe_x_delta) == (0, 0):
            causal_class = "transition_path_replaced_safe_anchor"
            causal_interpretation = (
                "The one-frame original-input transition replaced the perturbed "
                "safe X before resident consumption; the continuously maintained "
                "safe-XYZ stores did not execute in either branch.")
        elif (x_delta, safe_x_delta) == (ANCHOR_X_DELTA, ANCHOR_X_DELTA):
            causal_class = "resident_handler_consumed_retained_safe_anchor"
            causal_interpretation = (
                "The one-frame original-input transition preserved the exact "
                "+4096 safe/live X result through resident consumption.")
        else:
            causal_class = "unexpected_mixed_safe_anchor_result"
            causal_interpretation = (
                "The one-frame result matched neither tuple replacement nor "
                "proportional resident consumption.")

        rows.append({
            "id": case["id"],
            "fixture": {"movie": case["movie_rel"], "save": case["save_rel"]},
            "expected_boundary": {
                key: case[key] for key in (
                    "scene", "pre_reset_frame", "reset_frame", "pre_health",
                    "pre_lives", "post_health", "post_lives")
            },
            "natural_boundary": {"pre_reset": pre, "reset": post},
            "runtime_overlay_window": {
                "address_range": ["0x800B3C54", "0x800B3D78"],
                "size": len(runtime_owner),
                "sha256": _sha256_bytes(runtime_owner),
                "matches_level03_pristine_slice":
                    _sha256_bytes(runtime_owner) == static_owner_sha,
                "runtime_words_at_level03_selector_addresses": runtime_words,
                "identity_boundary": (
                    "runtime bytes are save/residency-qualified unless the exact "
                    "hash matches the separately pinned pristine LEVEL03 slice"),
            },
            "base_state": base_info,
            "base_main_ram_sha256": _sha256_bytes(base_ram),
            "branches": branches,
            "single_variable_guard": {
                "changed_byte_addresses": changed,
                "changed_word": "0x800A6550",
                "allowed_word_range": ["0x800A6550", "0x800A6553"],
            },
            "causal_result": {
                "classification": causal_class,
                "live_x_delta": x_delta,
                "safe_x_delta": safe_x_delta,
                "interpretation": (
                    f"{causal_interpretation} Filename hazard semantics are not "
                    "used."),
            },
        })
    return rows


def _restart_movie_playback(client: Any, path: Path) -> dict[str, Any]:
    status = client.call("movie.status", {})
    if status.get("playing"):
        client.call("movie.stopPlayback", {})
        status = client.call("movie.status", {})
    if status.get("has_movie"):
        client.call("movie.clear", {})
    loaded = client.call("movie.load", {"path": str(path.resolve())})
    playback = client.call("movie.startPlayback", {
        "start_frame": 0, "load_start_state": True})
    if loaded.get("reproducible") is not True or \
            playback.get("reproducible") is not True or \
            playback.get("truncated") is not False:
        raise SystemExit(f"C15 writer-attribution movie is not reproducible: {path}")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "frame_count": playback.get("frame_count"),
        "reproducible": playback.get("reproducible"),
        "truncated": playback.get("truncated"),
    }


def _compact_access_event(event: dict[str, Any]) -> dict[str, Any]:
    return {key: event.get(key) for key in (
        "frame", "cycle", "instruction_pc", "instruction_word",
        "instruction", "reported_pc", "address", "type", "width",
        "value", "value_hex", "new_value", "new_value_hex")}


def _derive_pit_writer_attribution(
        client: Any, static: dict[str, Any]) -> list[dict[str, Any]]:
    """Name the transition writers without using observer timing as behavior.

    The passive cached-block pairs in ``_derive_pit_breadth`` remain the
    behavioral oracle.  These short interpreter-forced access logs begin only
    after the exact state/movie anchor is restored, cover at most three movie
    frames, and retain complete instruction-attributed stores.
    """
    rows = []
    static_writers = static["pit_transition_writers"]
    for case in PIT_BREADTH_CASES:
        case_id = case["id"]
        spec = PIT_WRITER_STATIC[case_id]
        movie_path = ROOT / case["movie_rel"]
        movie = _restart_movie_playback(client, movie_path)
        pre_advance = client.call("movie.advanceToFrame", {
            "frame": case["pre_reset_frame"]}, timeout=900)
        pre_snapshot = _snapshot(client)

        start, end = spec["runtime_range"]
        runtime = _read_memory(client, start, end - start)
        runtime_sha256 = _sha256_bytes(runtime)
        if runtime_sha256 != static_writers[case_id]["sha256"]:
            raise SystemExit(
                f"C15 {case_id} runtime writer does not match pristine slice")
        bounds_start, bounds_end = spec["function_bounds"]
        bounds = client.call("debugger.functionBounds", {
            "address": spec["expected_events"][0][0]})
        if bounds.get("confidence") != "exact" or \
                bounds.get("mergedRegion") is not False or \
                bounds.get("functionStart") != f"0x{bounds_start:08x}" or \
                bounds.get("functionEnd") != f"0x{bounds_end:08x}":
            raise SystemExit(f"C15 {case_id} runtime function bounds changed: {bounds}")

        client.call("accessLog.clear", {})
        watch_specs = (
            {"address": "0x800A6550", "length": 12, "type": "write",
             "label": "safe_xyz", "max_events": 32, "stop_on_hit": False},
            {"address": "0x800A6578", "length": 2, "type": "write",
             "label": "safe_heading", "max_events": 32, "stop_on_hit": False},
        )
        for watch in watch_specs:
            client.call("accessLog.addWatch", watch)
        capture_target = case["reset_frame"] + 2
        capture = client.call("movie.advanceToFrame", {
            "frame": capture_target}, timeout=900)
        access = client.call("accessLog.get", {
            "offset": 0, "limit": 10000})
        final_movie = client.call("movie.status", {})
        final_snapshot = _snapshot(client)
        client.call("accessLog.clear", {})

        events = [_compact_access_event(event)
                  for event in access.get("events") or []]
        event_signature = [
            (event["instruction_pc"], event["address"], event["width"],
             event["value_hex"], event["new_value_hex"])
            for event in events
        ]
        if event_signature != list(spec["expected_events"]):
            raise SystemExit(
                f"C15 {case_id} transition-writer events changed: "
                f"{event_signature}")
        watches = sorted(({
            key: watch.get(key) for key in (
                "label", "address", "length", "type", "max_events",
                "stop_on_hit", "hit_count")}
            for watch in access.get("watches") or []),
            key=lambda row: row["label"])
        rows.append({
            "id": case_id,
            "movie": movie,
            "pre_reset_target": case["pre_reset_frame"],
            "capture_target": capture_target,
            "pre_advance": {
                key: pre_advance.get(key) for key in (
                    "target_frame", "start_playback_index", "frames_advanced")},
            "pre_snapshot": pre_snapshot,
            "runtime_writer": {
                "address_range": [f"0x{start:08X}", f"0x{end:08X}"],
                "size": len(runtime),
                "sha256": runtime_sha256,
                "pristine_static_identity": static_writers[case_id],
                "function_bounds": bounds,
            },
            "access_log": {
                "watches": watches,
                "events": events,
                "total": access.get("total"),
                "truncated": access.get("truncated"),
                "capture_advance": {
                    "target_frame": capture.get("target_frame"),
                    "start_playback_index": capture.get("start_playback_index"),
                    "frames_advanced": capture.get("frames_advanced"),
                    "status": {
                        key: (capture.get("status") or {}).get(key)
                        for key in ("frame", "cycle", "pc", "sp", "paused",
                                    "game_serial")},
                },
            },
            "post_attribution_snapshot": final_snapshot,
            "final_movie_status": {
                key: final_movie.get(key) for key in (
                    "playing", "reproducible", "truncated", "frame_count",
                    "playback_index")},
            "evidence_boundary": (
                "Access watches force the interpreter. These complete bounded "
                "events attribute exact writes only; the separate passive "
                "cycle-neutral natural/control pairs carry behavior and timing."),
        })
    return rows


def _trace_signatures_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("ram_sha256", "registers_sha256", "cycle", "frame", "pc", "sp")
    a = ((left.get("cycle_neutral_trace") or {}).get("control") or {})
    b = ((right.get("cycle_neutral_trace") or {}).get("control") or {})
    return all(a.get(key) == b.get(key) for key in keys)


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    if document.get("campaign_state") != "active_partial":
        gaps.append("C15 campaign state was promoted without closure")
    fixture = document.get("fixture_census") or {}
    if (fixture.get("movie") or {}).get("input_segments") != EXPECTED_SEGMENTS:
        gaps.append("LEVEL02 exact input segments changed")
    static = document.get("static_census") or {}
    if (static.get("regions") or {}).get("respawn_anchor_update", {}).get("sha256") != \
            "9cef37517d164bbe86f7b4f7a1ba33310fb79a622002e00c2222ef6812d68893":
        gaps.append("anchor-update executable region changed")
    if (static.get("regions") or {}).get("respawn_transition_state_handler", {}).get("sha256") != \
            "53cdfe30cec5af34e63107017d5f4a9d357fefb857fd4a511dc1bad56b32cdaf":
        gaps.append("respawn-handler executable region changed")
    overlay = static.get("overlay_safe_anchor_selector") or {}
    if overlay.get("sha256") != \
            "1fdeb0da151050edbde73a082b5951ae4326ec133979ca5bae2f0198bd8cfbf9":
        gaps.append("overlay safe-anchor selector changed")
    overlay_words = overlay.get("instructions") or {}
    for name in ("selected_anchor_x_store", "selected_anchor_y_store",
                 "selected_anchor_z_store"):
        if name not in overlay_words:
            gaps.append(f"overlay selector lost decisive instruction {name}")
    pit_static = static.get("pit_transition_writers") or {}
    if set(pit_static) != set(PIT_WRITER_STATIC):
        gaps.append("pit transition-writer static census changed")
    for case_id, spec in PIT_WRITER_STATIC.items():
        row = pit_static.get(case_id) or {}
        if row.get("sha256") != spec["sha256"] or \
                row.get("path") != f"REBUILD/files/{spec['path']}" or \
                row.get("file_offset") != f"0x{spec['file_offset']:X}" or \
                row.get("unique_staged_matches") != [{
                    "path": spec["path"],
                    "file_offset": f"0x{spec['file_offset']:X}"}]:
            gaps.append(f"{case_id} pristine writer identity changed")
        instructions = row.get("instructions") or {}
        for name, (address, word) in spec["instructions"].items():
            retained = instructions.get(name) or {}
            if retained.get("address") != f"0x{address:08X}" or \
                    retained.get("instruction_word") != f"0x{word:08X}":
                gaps.append(f"{case_id} decisive writer instruction changed: {name}")

    natural = (document.get("live") or {}).get("natural_replay") or {}
    by_frame = {row.get("movie_frame"): row for row in natural.get("snapshots") or []}
    expected = {
        0: ([507900, 31787, 503976], [507900, 31787, 503976], 3, 5),
        56: ([507900, 31787, 503976], [507900, 31787, 503976], 3, 5),
        100: ([508614, 39723, 516886], [507900, 31787, 503976], 3, 5),
        156: ([508193, 153067, 517418], [507900, 31787, 503976], 3, 5),
        157: ([501696, 30092, 494016], [501696, 30092, 494016], 4, 4),
        160: ([501696, 30215, 494013], [501696, 30092, 494016], 4, 4),
        358: ([501696, 30215, 494013], [501696, 30215, 494013], 4, 4),
    }
    for frame, wanted in expected.items():
        snapshot = (by_frame.get(frame) or {}).get("snapshot") or {}
        actual = (snapshot.get("live_xyz"), snapshot.get("safe_anchor_xyz"),
                  snapshot.get("true_health"), snapshot.get("lives"))
        if actual != wanted:
            gaps.append(f"natural frame {frame} typed outcome changed: {actual}")
        trace = (by_frame.get(frame) or {}).get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"natural frame {frame} trace lost cycle neutrality")
    post_coverage = {
        row.get("label"): row.get("total_hits")
        for row in ((by_frame.get(160) or {}).get("cycle_neutral_trace") or {}).get("coverage") or []
    }
    if any(not post_coverage.get(label) for label in STATIC_REGIONS):
        gaps.append(f"natural post-reset coverage lost a frontier: {post_coverage}")

    neutral = (document.get("live") or {}).get("neutral_input_control") or {}
    if (neutral.get("recipe") or {}).get("changed_frames") != list(MOVEMENT_FRAMES):
        gaps.append("neutral control changed more or fewer input frames")
    neutral_final = (neutral.get("final") or {}).get("snapshot") or {}
    if (neutral_final.get("true_health"), neutral_final.get("lives")) != (3, 5):
        gaps.append("neutral control no longer prevents the pit death")
    neutral_coverage = {
        row.get("label"): row.get("total_hits")
        for row in ((neutral.get("final") or {}).get("cycle_neutral_trace") or {}).get("coverage") or []
    }
    if neutral_coverage.get("bottomless_fall_transition") != 1790 or \
            neutral_coverage.get("respawn_transition_state_handler") != 0:
        gaps.append(
            f"neutral control coverage boundary changed: "
            f"{neutral_coverage}")

    counter = (document.get("live") or {}).get("counterfactuals") or {}
    guards = counter.get("single_variable_guards") or {}
    for key in ("anchor_only_changed_byte_addresses",
                "nopped_pair_anchor_only_changed_byte_addresses"):
        addresses = guards.get(key) or []
        if not addresses or any(
                not 0x800A6550 <= int(address, 16) <= 0x800A6553
                for address in addresses):
            gaps.append(f"{key} is not confined to the anchor-X word")
    branches = counter.get("branch_recipes") or {}
    pairs = (
        ("anchor_control", "anchor_x_plus_4096"),
        ("stores_nopped_control", "stores_nopped_anchor_x_plus_4096"),
    )
    for left_name, right_name in pairs:
        left = (branches.get(left_name) or {}).get("post_reset") or {}
        right = (branches.get(right_name) or {}).get("post_reset") or {}
        if not _trace_signatures_equal(left, right):
            gaps.append(f"counterfactual pair did not converge: {left_name}/{right_name}")
        for row in (left, right):
            snap = row.get("snapshot") or {}
            if snap.get("live_xyz") != [501696, 30215, 494013] or \
                    snap.get("safe_anchor_xyz") != [501696, 30092, 494016]:
                gaps.append(f"counterfactual post-reset outcome changed: {left_name}/{right_name}")
    nopped_words = (branches.get("stores_nopped_anchor_x_plus_4096") or {}) \
        .get("post_reset", {}).get("snapshot", {}).get("anchor_store_words")
    if nopped_words != {f"0x{address:08X}": "0x00000000"
                        for address in ANCHOR_STORES}:
        gaps.append("suppressed writer instructions were not retained through replay")

    owner = (document.get("live") or {}).get("reset_owner") or {}
    boundary = owner.get("boundary") or {}
    pre = (boundary.get("pre_reset") or {}).get("snapshot") or {}
    reset = (boundary.get("reset") or {}).get("snapshot") or {}
    if (boundary.get("pre_reset_movie_frame"),
            boundary.get("reset_movie_frame")) != (156, 157):
        gaps.append("exact reset-owner boundary changed")
    if (pre.get("live_xyz"), pre.get("safe_anchor_xyz"),
            pre.get("true_health"), pre.get("lives")) != (
            [508193, 153067, 517418], [507900, 31787, 503976], 3, 5):
        gaps.append("frame-156 pre-reset state changed")
    if (reset.get("live_xyz"), reset.get("safe_anchor_xyz"),
            reset.get("true_health"), reset.get("lives")) != (
            [501696, 30092, 494016], [501696, 30092, 494016], 4, 4):
        gaps.append("frame-157 reset state changed")
    runtime_owner = owner.get("runtime_owner") or {}
    if runtime_owner.get("runtime_sha256") != overlay.get("sha256") or \
            runtime_owner.get("pristine_slice_sha256") != overlay.get("sha256"):
        gaps.append("runtime reset owner is not the pristine overlay slice")
    transfer = runtime_owner.get("transfer_provenance") or {}
    if (transfer.get("overlay_runtime_address") or {}).get("resolved") is not False or \
            (transfer.get("selected_table_x_address") or {}).get("resolved") is not False:
        gaps.append("save-state transfer provenance boundary changed")
    selector = owner.get("selector") or {}
    if selector.get("runtime_table_count") != 18 or \
            (selector.get("selected") or {}).get("index") != 6 or \
            (selector.get("selected") or {}).get("x_raw") != 15678 or \
            selector.get("selected_scaled_x") != 501696:
        gaps.append("frame-156 nearest-row selection changed")
    source_address = selector.get("selected_x_source_address")
    guard = owner.get("single_variable_guard") or {}
    changed = guard.get("changed_byte_addresses") or []
    if source_address != "0x8015E6D0" or not changed or any(
            not int(source_address, 16) <= int(address, 16) <=
            int(source_address, 16) + 3 for address in changed):
        gaps.append("reset-owner mutation is not confined to selected X source word")
    owner_branches = owner.get("branches") or {}
    control = owner_branches.get("owner_control") or {}
    mutated = owner_branches.get("selected_x_source_plus_128") or {}
    denied = owner_branches.get("selector_status_bit_cleared") or {}
    control_post = (control.get("post_reset") or {}).get("snapshot") or {}
    mutated_post = (mutated.get("post_reset") or {}).get("snapshot") or {}
    if (control_post.get("live_xyz"), control_post.get("safe_anchor_xyz"),
            control_post.get("true_health"), control_post.get("lives")) != (
            [501696, 30092, 494016], [501696, 30092, 494016], 4, 4):
        gaps.append("reset-owner control outcome changed")
    if (mutated_post.get("live_xyz"), mutated_post.get("safe_anchor_xyz"),
            mutated_post.get("true_health"), mutated_post.get("lives")) != (
            [505792, 30120, 494016], [505792, 30120, 494016], 4, 4):
        gaps.append("selected-X source no longer causes the scaled reset outcome")
    source_before = mutated.get("source_x_raw_before")
    source_after = mutated.get("source_x_raw_after")
    if not isinstance(source_before, int) or not isinstance(source_after, int) or \
            source_after - source_before != SOURCE_X_DELTA:
        gaps.append("selected-X source mutation delta changed")
    denial_mutation = denied.get("mutation") or {}
    denial_guard = owner.get("selector_denial_single_variable_guard") or {}
    denial_post = (denied.get("post_reset") or {}).get("snapshot") or {}
    if denial_mutation != {
            "status_address": "0x800A6590", "cleared_mask": "0x0010",
            "status_before": 0x0014, "status_after": 0x0004}:
        gaps.append("selector-denial mutation no longer clears only status bit 0x0010")
    if denial_guard.get("changed_byte_addresses") != ["0x800A6590"] or \
            denial_guard.get("changed_word") != "0x800A6590":
        gaps.append("selector-denial branch is not confined to the status word")
    if (denied.get("start_snapshot") or {}).get(
            "respawn_selector_status_bit_0x0010") is not False:
        gaps.append("selector-denial branch started with status bit 0x0010 set")
    if (denial_post.get("live_xyz"), denial_post.get("safe_anchor_xyz"),
            denial_post.get("true_health"), denial_post.get("lives")) != (
            pre.get("safe_anchor_xyz"), pre.get("safe_anchor_xyz"), 4, 4):
        gaps.append("status-bit denial did not preserve and consume the prior anchor")
    for name, branch in (("owner_control", control),
                         ("selected_x_source_plus_128", mutated)):
        trace = (branch.get("post_reset") or {}).get("cycle_neutral_trace") or {}
        comparison = trace.get("comparison") or {}
        coverage = _coverage_by_label(branch.get("post_reset") or {})
        if comparison.get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in coverage.values()):
            gaps.append(f"{name} owner replay lost cycle neutrality")
        if coverage.get("overlay_safe_anchor_selector", {}).get("total_hits") != 400 or \
                coverage.get("respawn_transition_state_handler", {}).get("total_hits") != 768:
            gaps.append(f"{name} owner/consumer coverage changed")
        pcs = set(coverage.get("overlay_safe_anchor_selector", {}).get("pcs") or [])
        if not {"0x800b3d24", "0x800b3d40", "0x800b3d54"}.issubset(pcs):
            gaps.append(f"{name} lost exact overlay safe-XYZ stores")
        pcs = set(coverage.get("respawn_transition_state_handler", {}).get("pcs") or [])
        if not {"0x8005b1dc", "0x8005b1e4", "0x8005b1ec",
                "0x8005b29c", "0x8005b2a4", "0x8005b2ac"}.issubset(pcs):
            gaps.append(f"{name} lost exact resident safe-to-live chain")
    control_coverage = _coverage_by_label(control.get("post_reset") or {})
    mutated_coverage = _coverage_by_label(mutated.get("post_reset") or {})
    for label in ("overlay_safe_anchor_selector",
                  "respawn_transition_state_handler"):
        left, right = control_coverage.get(label, {}), mutated_coverage.get(label, {})
        if (left.get("total_hits"), left.get("pcs_sha256")) != \
                (right.get("total_hits"), right.get("pcs_sha256")):
            gaps.append(f"owner counterfactual changed execution coverage: {label}")
    denial_trace = (denied.get("post_reset") or {}).get(
        "cycle_neutral_trace") or {}
    denial_coverage = _coverage_by_label(denied.get("post_reset") or {})
    if (denial_trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in denial_coverage.values()):
        gaps.append("selector-denial replay lost cycle neutrality")
    denial_selector_pcs = set(
        (denial_coverage.get("overlay_safe_anchor_selector") or {}).get("pcs") or [])
    if "0x800b3c64" not in denial_selector_pcs or \
            {"0x800b3d24", "0x800b3d40", "0x800b3d54"}.intersection(
                denial_selector_pcs):
        gaps.append("selector-denial branch did not take the exact pre-store gate")
    denial_handler = denial_coverage.get("respawn_transition_state_handler") or {}
    control_handler = control_coverage.get("respawn_transition_state_handler") or {}
    if (denial_handler.get("total_hits"), denial_handler.get("pcs_sha256")) != \
            (control_handler.get("total_hits"), control_handler.get("pcs_sha256")):
        gaps.append("selector denial changed the resident consumer execution path")
    if not {"0x8005b1dc", "0x8005b1e4", "0x8005b1ec",
            "0x8005b29c", "0x8005b2a4", "0x8005b2ac"}.issubset(
                set(denial_handler.get("pcs") or [])):
        gaps.append("selector denial lost the resident safe-to-live chain")

    contact = (document.get("live") or {}).get("contact_death_anchor_control") or {}
    lives_recipe = contact.get("lives_one_state_recipe") or {}
    lives_mutation = lives_recipe.get("mutation") or {}
    if lives_mutation.get("main_ram_difference_count") != 1 or \
            lives_mutation.get("main_ram_difference_addresses") != ["0x800A65A0"] or \
            (lives_mutation.get("before"), lives_mutation.get("after")) != (0, 1):
        gaps.append("contact-death lives-one anchor is not single-variable")
    fatal = ((contact.get("fatal_anchor") or {}).get("trace") or {}).get("snapshot") or {}
    if (fatal.get("scene"), fatal.get("live_xyz"), fatal.get("safe_anchor_xyz"),
            fatal.get("true_health"), fatal.get("lives"),
            fatal.get("respawn_selector_status_bit_0x0010")) != (
            9, [-27693, -116008, -162370], [-23491, -112966, -142999],
            -1, 1, False):
        gaps.append("contact-death fatal safe-anchor boundary changed")
    contact_guard = contact.get("single_variable_guard") or {}
    if contact_guard.get("changed_byte_addresses") != ["0x800A6551"] or \
            contact_guard.get("changed_word") != "0x800A6550":
        gaps.append("contact-death branch is not confined to safe X")
    contact_branches = contact.get("branches") or {}
    contact_control = contact_branches.get("safe_anchor_control") or {}
    contact_mutated = contact_branches.get("safe_anchor_x_plus_4096") or {}
    contact_posts = {
        "safe_anchor_control": contact_control.get(
            "first_completed_respawn_boundary") or {},
        "safe_anchor_x_plus_4096": contact_mutated.get(
            "first_completed_respawn_boundary") or {},
    }
    expected_contact = {
        "safe_anchor_control": [-23491, -112966, -142999],
        "safe_anchor_x_plus_4096": [-19395, -112966, -142999],
    }
    expected_contact_coverage = {
        "continuous_safe_anchor_updater": (
            50, "d027b62985c1da9a7cfff71bbe722222cdf9bd0149dd62cd2535da918924fff7"),
        "respawn_transition_state_handler": (
            974, "951f06d598366cf1434b1b6fdd583e20d78e6def61b5c41c205bdea3b86fe2ab"),
        "bug_bar_overlay_window": (
            670, "48132d08868731793762c236e3b75b939fd8324525504492ffca774ea8162c91"),
    }
    for name, post in contact_posts.items():
        snapshot = post.get("snapshot") or {}
        wanted = expected_contact[name]
        if (snapshot.get("live_xyz"), snapshot.get("safe_anchor_xyz"),
                snapshot.get("true_health"), snapshot.get("lives"),
                snapshot.get("scene")) != (wanted, wanted, 4, 0, 9):
            gaps.append(f"{name} contact-death respawn outcome changed")
        trace = post.get("cycle_neutral_trace") or {}
        coverage = _coverage_by_label(post)
        if (trace.get("target_frame") != 5 or
                (trace.get("comparison") or {}).get("cycle_neutral") is not True or
                any(row.get("truncated") for row in coverage.values())):
            gaps.append(f"{name} contact-death trace lost its exact boundary")
        for label, expected_pair in expected_contact_coverage.items():
            row = coverage.get(label) or {}
            if (row.get("total_hits"), row.get("pcs_sha256")) != expected_pair:
                gaps.append(f"{name} contact-death coverage changed: {label}")
        updater_pcs = set(
            (coverage.get("continuous_safe_anchor_updater") or {}).get("pcs") or [])
        if {"0x80054e70", "0x80054e78", "0x80054e80"}.intersection(updater_pcs):
            gaps.append(f"{name} unexpectedly executed continuous safe stores")
        handler_pcs = set(
            (coverage.get("respawn_transition_state_handler") or {}).get("pcs") or [])
        if not {"0x8005b1dc", "0x8005b1e4", "0x8005b1ec",
                "0x8005b29c", "0x8005b2a4", "0x8005b2ac",
                "0x8005b30c", "0x8005b348"}.issubset(handler_pcs):
            gaps.append(f"{name} lost exact contact-death anchor consumers")
    if contact_control.get("safe_anchor_x_before") != -23491 or \
            contact_mutated.get("safe_anchor_x_before") != -23491 or \
            contact_mutated.get("safe_anchor_x_after") != -19395:
        gaps.append("contact-death safe-X mutation delta changed")
    for label in expected_contact_coverage:
        left = _coverage_by_label(contact_posts["safe_anchor_control"]).get(label) or {}
        right = _coverage_by_label(contact_posts["safe_anchor_x_plus_4096"]).get(label) or {}
        if (left.get("total_hits"), left.get("pcs_sha256")) != \
                (right.get("total_hits"), right.get("pcs_sha256")):
            gaps.append(f"contact-death branch coverage diverged: {label}")

    fixture_breadth = fixture.get("pit_breadth") or []
    if [row.get("id") for row in fixture_breadth] != \
            [case["id"] for case in PIT_BREADTH_CASES]:
        gaps.append("pit-breadth fixture census changed")
    breadth = (document.get("live") or {}).get("pit_breadth") or []
    if [row.get("id") for row in breadth] != \
            [case["id"] for case in PIT_BREADTH_CASES]:
        gaps.append("pit-breadth replay set changed")
    breadth_by_id = {row.get("id"): row for row in breadth}
    decisive_handler_pcs = {
        "0x8005b1dc", "0x8005b1e4", "0x8005b1ec",
        "0x8005b29c", "0x8005b2a4", "0x8005b2ac",
        "0x8005b30c", "0x8005b348",
    }
    for case in PIT_BREADTH_CASES:
        row = breadth_by_id.get(case["id"]) or {}
        boundary = row.get("natural_boundary") or {}
        pre_row = boundary.get("pre_reset") or {}
        post_row = boundary.get("reset") or {}
        pre_snapshot = pre_row.get("snapshot") or {}
        post_snapshot = post_row.get("snapshot") or {}
        if (pre_snapshot.get("scene"), pre_snapshot.get("true_health"),
                pre_snapshot.get("lives")) != (
                case["scene"], case["pre_health"], case["pre_lives"]):
            gaps.append(f"{case['id']} pre-reset typed boundary changed")
        if (post_snapshot.get("scene"), post_snapshot.get("true_health"),
                post_snapshot.get("lives")) != (
                case["scene"], case["post_health"], case["post_lives"]):
            gaps.append(f"{case['id']} reset typed boundary changed")
        for label, replay in (("natural pre", pre_row),
                              ("natural reset", post_row)):
            trace = replay.get("cycle_neutral_trace") or {}
            coverage = _coverage_by_label(replay)
            if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(item.get("truncated") for item in coverage.values()):
                gaps.append(f"{case['id']} {label} lost passive trace neutrality")
        owner = row.get("runtime_overlay_window") or {}
        if owner.get("size") != OVERLAY_OWNER_RANGE[1] - OVERLAY_OWNER_RANGE[0] or \
                len(owner.get("sha256") or "") != 64:
            gaps.append(f"{case['id']} runtime owner identity changed")
        guard = row.get("single_variable_guard") or {}
        changed = guard.get("changed_byte_addresses") or []
        if not changed or any(
                not 0x800A6550 <= int(address, 16) <= 0x800A6553
                for address in changed):
            gaps.append(f"{case['id']} mutation escaped the safe-X word")
        branches = row.get("branches") or {}
        control = branches.get("safe_anchor_control") or {}
        mutation = branches.get("safe_anchor_x_plus_4096") or {}
        control_post = control.get("post_reset") or {}
        mutation_post = mutation.get("post_reset") or {}
        if (control_post.get("snapshot") or {}) != post_snapshot:
            gaps.append(f"{case['id']} suffix control changed the natural reset")
        control_snapshot = control_post.get("snapshot") or {}
        mutation_snapshot = mutation_post.get("snapshot") or {}
        live_delta = (mutation_snapshot.get("live_xyz") or [None])[0]
        safe_delta = (mutation_snapshot.get("safe_anchor_xyz") or [None])[0]
        control_live = (control_snapshot.get("live_xyz") or [None])[0]
        control_safe = (control_snapshot.get("safe_anchor_xyz") or [None])[0]
        if None in (live_delta, safe_delta, control_live, control_safe):
            gaps.append(f"{case['id']} causal endpoint is incomplete")
        else:
            live_delta -= control_live
            safe_delta -= control_safe
            expected_class = (
                "transition_path_replaced_safe_anchor"
                if (live_delta, safe_delta) == (0, 0)
                else "resident_handler_consumed_retained_safe_anchor"
                if (live_delta, safe_delta) ==
                    (ANCHOR_X_DELTA, ANCHOR_X_DELTA)
                else "unexpected_mixed_safe_anchor_result")
            result = row.get("causal_result") or {}
            if result.get("classification") != expected_class or \
                    result.get("live_x_delta") != live_delta or \
                    result.get("safe_x_delta") != safe_delta or \
                    expected_class == "unexpected_mixed_safe_anchor_result":
                gaps.append(f"{case['id']} causal classification changed")
        for name, branch in (("control", control), ("mutation", mutation)):
            replay = branch.get("post_reset") or {}
            trace = replay.get("cycle_neutral_trace") or {}
            coverage = _coverage_by_label(replay)
            handler_pcs = set(
                (coverage.get("respawn_transition_state_handler") or {})
                .get("pcs") or [])
            updater_pcs = set(
                (coverage.get("continuous_safe_anchor_updater") or {})
                .get("pcs") or [])
            if (trace.get("target_frame") != 1 or \
                    (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                    any(item.get("truncated") for item in coverage.values()) or \
                    not decisive_handler_pcs.issubset(handler_pcs) or \
                    {"0x80054e70", "0x80054e78", "0x80054e80"}.intersection(
                        updater_pcs)):
                gaps.append(f"{case['id']} {name} lost the exact respawn chain")
        for label in ("continuous_safe_anchor_updater",
                      "respawn_transition_state_handler",
                      "scene_overlay_window"):
            left = _coverage_by_label(control_post).get(label) or {}
            right = _coverage_by_label(mutation_post).get(label) or {}
            if (left.get("total_hits"), left.get("pcs_sha256")) != \
                    (right.get("total_hits"), right.get("pcs_sha256")):
                gaps.append(f"{case['id']} branch coverage diverged: {label}")

    attribution = (document.get("live") or {}).get("pit_writer_attribution") or []
    if [row.get("id") for row in attribution] != \
            [case["id"] for case in PIT_BREADTH_CASES]:
        gaps.append("pit transition-writer attribution set changed")
    attribution_by_id = {row.get("id"): row for row in attribution}
    passive_by_id = {row.get("id"): row for row in breadth}
    for case in PIT_BREADTH_CASES:
        case_id = case["id"]
        spec = PIT_WRITER_STATIC[case_id]
        row = attribution_by_id.get(case_id) or {}
        runtime = row.get("runtime_writer") or {}
        if runtime.get("sha256") != spec["sha256"] or \
                (runtime.get("pristine_static_identity") or {}).get("sha256") != \
                spec["sha256"]:
            gaps.append(f"{case_id} runtime writer lost pristine identity")
        bounds = runtime.get("function_bounds") or {}
        bounds_start, bounds_end = spec["function_bounds"]
        if bounds.get("confidence") != "exact" or \
                bounds.get("mergedRegion") is not False or \
                bounds.get("functionStart") != f"0x{bounds_start:08x}" or \
                bounds.get("functionEnd") != f"0x{bounds_end:08x}":
            gaps.append(f"{case_id} exact runtime function bounds changed")
        access = row.get("access_log") or {}
        events = access.get("events") or []
        signature = [
            (event.get("instruction_pc"), event.get("address"),
             event.get("width"), event.get("value_hex"),
             event.get("new_value_hex"))
            for event in events
        ]
        if access.get("total") != len(spec["expected_events"]) or \
                access.get("truncated") is not False or \
                signature != list(spec["expected_events"]):
            gaps.append(f"{case_id} transition-writer attribution changed")
        watches = {watch.get("label"): watch
                   for watch in access.get("watches") or []}
        if (watches.get("safe_xyz") or {}).get("hit_count") != 4 or \
                (watches.get("safe_heading") or {}).get("hit_count") != \
                spec["expected_heading_writes"]:
            gaps.append(f"{case_id} transition-writer watch counts changed")
        if row.get("capture_target") != case["reset_frame"] + 2 or \
                (row.get("final_movie_status") or {}).get("reproducible") is not True or \
                (row.get("final_movie_status") or {}).get("truncated") is not False:
            gaps.append(f"{case_id} writer-attribution replay lost its anchor")
        passive_post = (((passive_by_id.get(case_id) or {})
                         .get("natural_boundary") or {}).get("reset") or {}) \
            .get("snapshot") or {}
        attribution_post = row.get("post_attribution_snapshot") or {}
        for key in ("scene", "safe_anchor_xyz", "safe_anchor_heading",
                    "true_health", "lives"):
            if attribution_post.get(key) != passive_post.get(key):
                gaps.append(
                    f"{case_id} attribution endpoint changed passive field {key}")
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned C15 live process was not stopped")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    fixtures = build_fixture_census()
    source_movie = json.loads(MOVIE.read_text())
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.functionBounds",
        "debugger.readMemory", "debugger.writeU8", "debugger.writeU16",
        "debugger.writeU32",
        "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.loadState", "emulator.saveState",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
        "accessLog.addWatch", "accessLog.get", "accessLog.clear",
        "transferLog.resolve",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C15 methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, SAVE, media_identity)
    contact_inspection = inspect_state_before_load(
        client, CONTACT_SAVE, media_identity)
    pit_breadth_inspections = [
        inspect_state_before_load(client, ROOT / case["save_rel"], media_identity)
        for case in PIT_BREADTH_CASES
    ]

    with tempfile.TemporaryDirectory(prefix="abl-phase4-c15-") as temp_text:
        temp_dir = Path(temp_text)
        natural = [
            _trace_snapshot(client, MOVIE, frame)
            for frame in (0, TAKEOFF_PRE_FRAME, FALL_FRAME,
                          PRE_RESET_FRAME, RESET_FRAME,
                          POST_RESET_FRAME, FINAL_FRAME)
        ]
        neutral_movie = temp_dir / "movement-neutral.movie.json"
        neutral_recipe = _write_neutral_variant(source_movie, neutral_movie)
        neutral_final = _trace_snapshot(client, neutral_movie, FINAL_FRAME)
        counterfactuals = _derive_counterfactuals(client, source_movie, temp_dir)
        reset_owner = _derive_reset_owner(client, source_movie, temp_dir)
        contact_death_control = _derive_contact_death_control(
            client, media_identity, temp_dir)
        pit_breadth = _derive_pit_breadth(client, temp_dir)
        pit_writer_attribution = _derive_pit_writer_attribution(client, static)
        final_media = verified_media_identity(
            client, client.call("debugger.status", {}))

        provenance = finish_run(
            args, generator="tools/phase4_checkpoint_respawn.py",
            anchor={
                "type": (
                    "existing state-anchored LEVEL02/LEVEL05/LEVEL07 pit and "
                    "Bug Bar contact discovery leads"),
                "movie": MOVIE_REL, "movie_sha256": fixtures["movie"]["sha256"],
                "saves": [
                    SAVE_REL,
                    CONTACT_SAVE_REL,
                    *[case["save_rel"] for case in PIT_BREADTH_CASES],
                ],
                "pit_save": SAVE_REL,
                "pit_save_sha256": fixtures["save"]["sha256"],
                "state_inspections": [inspection, contact_inspection]
                    + pit_breadth_inspections,
                "contact_movie": CONTACT_MOVIE_REL,
                "contact_movie_sha256": fixtures["contact_death"]["movie"]["sha256"],
                "contact_save": CONTACT_SAVE_REL,
                "contact_save_sha256": fixtures["contact_death"]["save"]["sha256"],
                "fixture_sha256": {
                    SAVE_REL: fixtures["save"]["sha256"],
                    CONTACT_SAVE_REL: fixtures["contact_death"]["save"]["sha256"],
                } | {
                    row["save"]["path"]: row["save"]["sha256"]
                    for row in fixtures["pit_breadth"]
                },
                "media_identity": media_identity,
                "final_media_identity": final_media,
            },
            timing={
                "cpu_overclock_percent": 100, "cd_read_speedup": 1,
                "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
                "natural_sampling": (
                    "movie.traceToFrame uninstrumented versus passive cached-block replay"),
                "counterfactual_sampling": (
                    "frame-100 transient save branches; identical suffix inputs; "
                    "no access log or interpreter-forcing observer"),
                "reset_owner_sampling": (
                    "frame-156 transient save branches; selected source-X word or "
                    "status mask 0x0010 only; identical one-frame suffix input; "
                    "passive cached-block coverage compared bit-exactly against "
                    "an uninstrumented pass"),
                "contact_death_sampling": (
                    "one-byte lives control selects ordinary respawn; a frame-350 "
                    "base supplies same-code safe-X control/+4096 branches; each "
                    "five-frame suffix uses passive cached-block coverage against "
                    "its own uninstrumented pass"),
                "pit_breadth_sampling": (
                    "scene-10 and scene-4 pre/reset pairs use passive cached-block "
                    "coverage; each pre-reset state supplies same-code safe-X "
                    "control/+4096 branches with the exact next recorded frame"),
                "pit_writer_attribution": (
                    "after a fresh load of each declared movie anchor, advance to "
                    "the passive pre-reset target, arm bounded safe-XYZ/heading "
                    "write watches, and advance three movie targets; access logs "
                    "force the interpreter and therefore attribute writes only"),
                "movie_end_rule": "consume all 358 recorded frames",
            })

    document = {
        "_comment": (
            "C15 active evidence. This does not promote an authored checkpoint "
            "mechanic or generalize one pit and one contact respawn to every "
            "death class."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-checkpoint-respawn/2",
        "campaign_state": "active_partial",
        "fixture_census": fixtures,
        "static_census": static,
        "live": {
            "natural_replay": {"snapshots": natural},
            "neutral_input_control": {
                "recipe": neutral_recipe, "final": neutral_final,
            },
            "counterfactuals": counterfactuals,
            "reset_owner": reset_owner,
            "contact_death_anchor_control": contact_death_control,
            "pit_breadth": pit_breadth,
            "pit_writer_attribution": pit_writer_attribution,
        },
        "bounded_interpretation": {
            "observation": (
                "The recorded movement causes a bottomless-fall transition; by "
                "frame 160 health is 4, lives is 4, and live/anchor XYZ have reset."),
            "inference": (
                "player+0x50 is a gated continuously maintained safe anchor, not "
                "evidence of a player-activated checkpoint by itself."),
            "causal_confirmation": (
                "Removing only frames 57..87 prevents the respawn transition "
                "(the broader airborne/fall region still executes). Anchor-X mutation "
                "converges even when the three known continuous stores are NOPed, "
                "bounding a distinct transition/reset owner for this pit path. At "
                "frame 156, changing only the selected scene-local row X by +128 "
                "changes frame-157 safe/live X by +4096 through overlay 0x800B3C54 "
                "and resident handler 0x8005B134. Clearing only status mask 0x0010 "
                "at that boundary denies the row selector while the same resident "
                "handler consumes the prior safe anchor. On the Bug Bar contact path, "
                "changing only fatal-state safe X by +4096 changes the first "
                "completed respawn live/safe X by +4096 through the resident "
                "handler without a selector overwrite. Two more pit recordings "
                "reproduce the same typed one-frame resident reset boundary in "
                "live scenes 10 and 4; their one-word controls distinguish tuple "
                "replacement from retained-anchor consumption. Complete bounded "
                "write events then identify exact pristine LEVEL10 and LEVEL04 "
                "transition functions as their tuple writers without using the "
                "operator filenames as semantics or promoting observer timing."),
            "rejected_hypothesis": (
                "The stable LEVEL02 pit postcondition is not determined solely by "
                "the frame-100 player+0x50 anchor value."),
            "still_unknown": (
                "The source and general activation policy of status mask 0x0010, "
                "denial behavior in other row-selecting variants, other overlay-writer variants, remaining "
                "death classes and stages, lifecycle reset/persistence, and the "
                "player-visible activation/denial policy remain open."),
        },
        "declarative_scenarios": [
            {"path": SCENARIO.relative_to(ROOT).as_posix(),
             "sha256": _sha256(SCENARIO), "assertions": 18},
            {"path": DENIAL_SCENARIO.relative_to(ROOT).as_posix(),
             "sha256": _sha256(DENIAL_SCENARIO), "assertions": 19},
            {"path": CONTACT_SCENARIO.relative_to(ROOT).as_posix(),
             "sha256": _sha256(CONTACT_SCENARIO), "assertions": 18},
            *[
                {"path": path.relative_to(ROOT).as_posix(),
                 "sha256": _sha256(path), "assertions": 15}
                for path in PIT_BREADTH_SCENARIOS
            ],
        ],
        "source_dependencies": {
            "analysis/phase0_2_external_fixture_set.json": _sha256(FIXTURE_SET),
            "asm/hand_written/80054c90_checkpoint_save.s": _sha256(
                ROOT / "asm/hand_written/80054c90_checkpoint_save.s"),
            "asm/hand_written/8005b134_respawn_transition_state_handler.s": _sha256(
                ROOT / "asm/hand_written/8005b134_respawn_transition_state_handler.s"),
            "src_re/player_bottomless_fall_800497f4.c": _sha256(
                ROOT / "src_re/player_bottomless_fall_800497f4.c"),
            "tools/phase4_lives_gameover.py": _sha256(
                ROOT / "tools/phase4_lives_gameover.py"),
            "REBUILD/files/LEVEL10/LEVEL.BIN": _sha256(
                ROOT / "REBUILD/files/LEVEL10/LEVEL.BIN"),
            "REBUILD/files/LEVEL04/LEVEL.BIN": _sha256(
                ROOT / "REBUILD/files/LEVEL04/LEVEL.BIN"),
        },
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C15 evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[checkpoint-respawn] active partial; three pit writers and contact safe-anchor consumption reproduced")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        if (Path(args.config_dir) / "instance.pid").is_file():
            try:
                finish_run(
                    args, generator="tools/phase4_checkpoint_respawn.py",
                    anchor={"type": "aborted before retained C15 evidence"},
                    timing={})
            except BaseException as cleanup_error:
                print(
                    f"owned C15 cleanup also failed: {cleanup_error}",
                    file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
