#!/usr/bin/env python3
"""Regenerate the Phase-4 E02 collision/floor-plane campaign.

Only centrally pinned pristine inputs are accepted.  Static work is performed
against the retail executable and staged LEVEL*.RAW files; live work requires
an isolated external-debugger instance mounted on the hash-verified retail CUE.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
from typing import Any

try:
    from build_identity import verify_staged_input
    import decode_level_raw as decoder
    import edit_collision_sector as collision_editor
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
    import phase4_run_locomotion as locomotion
    import recompress_level_raw as recompressor
except ModuleNotFoundError:  # imported as tools.phase4_collision in tests
    from tools.build_identity import verify_staged_input
    from tools import decode_level_raw as decoder
    from tools import edit_collision_sector as collision_editor
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
    from tools import phase4_run_locomotion as locomotion
    from tools import recompress_level_raw as recompressor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_collision.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

PLAYER_BASE = 0x800A6500
PLAYER_GATE = PLAYER_BASE + 0x82
PLAYER_SECTOR = 0x80090560
SECTOR_COUNT = 0x800822A0
SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30
CANDIDATE_COUNT = 0x80082314
CANDIDATE_POINTERS = 0x8009C230
CANDIDATE_POINTERS_END = 0x8009C870
CANDIDATE_SECTORS = 0x80091718
TRANSITION_LEVER = 0x800823A0

SETTLE_FRAMES = 2
CONTROL_FRAMES = 12
TRACE_FRAMES = 60
SECTOR_GRID_LIMIT = 700
POINTER_STORAGE_SLOTS = (CANDIDATE_POINTERS_END - CANDIDATE_POINTERS) // 4
FLIGHT_LABEL = "stage14_riverbed_flight"
CONTROL_SAVE = "level01.sav"
EXIT_SAVE = "level01_end_of_stage.sav"

FUNCTION_REGIONS = {
    "sector_table_builder": (0x80030F60, 0x800313A8),
    "grid_builder": (0x800313A8, 0x80031EFC),
    "resolver_accumulate": (0x800345CC, 0x80035280),
    "swept_resolver": (0x80035280, 0x80035F24),
    "resolver_probe": (0x80035F24, 0x8003633C),
    "player_integrator": (0x8003633C, 0x80036CEC),
    "player_y_commit": (0x80036CEC, 0x80036E70),
    "player_candidate_probe": (0x80036E70, 0x800370C8),
    "player_probe_pass": (0x800370C8, 0x80037320),
    "entity_candidate_builder": (0x80037320, 0x800376A0),
    "ground_height_query": (0x80037A38, 0x80037DAC),
    "point_in_polygon": (0x80038090, 0x80038E48),
    "region_code_query": (0x80038F38, 0x80038F84),
}

EXPECTED_WORDS = {
    "sector_table_region_copy": (0x80030F60, 0x8522001E),
    "grid_builder_entry": (0x800313A8, 0x27BDFF30),
    "resolver_accumulate_entry": (0x800345CC, 0x27BDFEF0),
    "swept_resolver_entry": (0x80035280, 0x27BDFEE8),
    "resolver_probe_entry": (0x80035F24, 0x27BDFFB8),
    "integrator_entry": (0x8003633C, 0x27BDFF78),
    "resolver_probe_call": (0x80036C50, 0x0C00D7C9),
    "resolver_accumulate_call": (0x80036C68, 0x0C00D173),
    "resolved_x_commit": (0x80036CE8, 0xAEE20000),
    "resolved_y_commit": (0x80036CEC, 0xAEE30004),
    "resolved_z_commit": (0x80036CF0, 0xAEE40008),
    "probe_bias_restore_y": (0x80036D54, 0xAEE40004),
    "entity_candidate_builder_entry": (0x80037320, 0x27BDFFA8),
    "point_test_call": (0x80037640, 0x0C00E024),
    "ground_height_entry": (0x80037A38, 0x27BDFFB0),
    "point_in_polygon_entry": (0x80038090, 0x27BDFFE0),
    "region_gate_read": (0x80038F38, 0x90A30000),
    "region_gate_branch": (0x80038F40, 0x1462000E),
    "region_code_read": (0x80038F78, 0x84227E76),
}

SECTOR_FIELDS = [
    {"name": "origin_x", "offset": 0x00, "type": "s32"},
    {"name": "origin_y", "offset": 0x04, "type": "s32"},
    {"name": "origin_z", "offset": 0x08, "type": "s32"},
    {"name": "block_ptr", "offset": 0x10, "type": "u32"},
    {"name": "min_x", "offset": 0x14, "type": "s32"},
    {"name": "min_z", "offset": 0x1C, "type": "s32"},
    {"name": "extent_x", "offset": 0x24, "type": "s32"},
    {"name": "extent_z", "offset": 0x28, "type": "s32"},
    {"name": "flag", "offset": 0x2C, "type": "u16"},
    {"name": "region_code", "offset": 0x2E, "type": "s16"},
]

PLANE_FIELDS = [
    {"name": "normal_x", "offset": 0x00, "type": "s16"},
    {"name": "normal_y", "offset": 0x02, "type": "s16"},
    {"name": "normal_z", "offset": 0x04, "type": "s16"},
    {"name": "ref_x", "offset": 0x06, "type": "s16"},
    {"name": "ref_y", "offset": 0x08, "type": "s16"},
    {"name": "ref_z", "offset": 0x0A, "type": "s16"},
    {"name": "dv1_x", "offset": 0x0C, "type": "s16"},
    {"name": "dv2_x", "offset": 0x0E, "type": "s16"},
    {"name": "dv1_z", "offset": 0x10, "type": "s16"},
    {"name": "dv2_z", "offset": 0x12, "type": "s16"},
    {"name": "dv3_x", "offset": 0x14, "type": "s16"},
    {"name": "dv3_z", "offset": 0x16, "type": "s16"},
    {"name": "footprint_min_x", "offset": 0x18, "type": "s16"},
    {"name": "footprint_extent_x", "offset": 0x1A, "type": "s16"},
    {"name": "unused_1c", "offset": 0x1C, "type": "s16"},
    {"name": "footprint_min_z_hi", "offset": 0x1E, "type": "s8"},
    {"name": "footprint_extent_z_hi", "offset": 0x1F, "type": "s8"},
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _va_offset(address: int) -> int:
    return EXE_HEADER + address - EXE_BASE


def _word(exe: bytes, address: int) -> int:
    return struct.unpack_from("<I", exe, _va_offset(address))[0]


def _function_census(exe: bytes) -> dict[str, Any]:
    function_doc = json.loads((ROOT / "analysis/functions.json").read_text())
    by_start = {int(row["start"], 16): row for row in function_doc["functions"]}
    regions = {}
    for name, (start, end) in FUNCTION_REGIONS.items():
        data = exe[_va_offset(start):_va_offset(end)]
        row = by_start[start]
        regions[name] = {
            "start": f"0x{start:08X}", "end_exclusive": f"0x{end:08X}",
            "length": len(data), "sha256": _sha256_bytes(data),
            "registry_name": row["name"], "match": row.get("match"),
            "space": row.get("space"), "classification": row.get("classification"),
        }
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"static collision opcode drift at {address:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    return {"regions": regions, "instruction_words": words}


def _asset_census() -> dict[str, Any]:
    provenance = json.loads(
        (ROOT / "analysis/phase3_asset_provenance.json").read_text())
    selected = sorted(rel for rel, row in provenance["assets"].items()
                      if "collision" in (row.get("roles") or []))
    rows = []
    for rel in selected:
        path = ROOT / "REBUILD/files" / rel
        raw = path.read_bytes()
        verify_staged_input(rel, raw)
        chunks = collision_editor.split_chunks(raw)
        marker_rows = []
        for index, (_offset, declared_size, _compressed_size, chunk) in enumerate(chunks):
            decoded = bytes(decoder.decompress_chunk(chunk))
            marker = struct.unpack_from("<H", decoded)[0] if len(decoded) >= 2 else None
            if marker not in (0x0103, 0x0104):
                continue
            rebuilt = recompressor.compress_chunk(decoded, chunk[8:0x0E])
            replay = bytes(decoder.decompress_chunk(rebuilt))
            marker_rows.append({
                "chunk_index": index, "marker": marker,
                "declared_decompressed_size": declared_size,
                "decompressed_size": len(decoded),
                "decompressed_sha256": _sha256_bytes(decoded),
                "semantic_recompression_equal": replay == decoded,
                "literal_recompressed_size": len(rebuilt),
            })
        rows.append({
            "path": f"REBUILD/files/{rel}", "relative_input": rel,
            "size": len(raw), "sha256": _sha256_bytes(raw),
            "chunk_count": len(chunks), "collision_markers": marker_rows,
        })
    return {
        "provenance_source": "analysis/phase3_asset_provenance.json",
        "classified_assets": len(rows),
        "assets_with_collision_marker": sum(
            any(marker["marker"] == 0x0103 for marker in row["collision_markers"])
            for row in rows),
        "collision_chunks_roundtripped": sum(
            len(row["collision_markers"]) for row in rows),
        "rows": rows,
    }


def build_static_census(executable: bytes | None = None) -> dict[str, Any]:
    exe = executable if executable is not None else EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    functions = _function_census(exe)
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
            "sha256": _sha256_bytes(exe),
            "pin_source": "tools/build_baselines.json:staged_inputs.SCUS_942.88",
        },
        "regions": functions["regions"],
        "instruction_words": functions["instruction_words"],
        "assets": _asset_census(),
        "typed_contract": {
            "sector_table": {"base": f"0x{SECTOR_TABLE:08X}",
                             "count_address": f"0x{SECTOR_COUNT:08X}",
                             "stride": SECTOR_STRIDE, "fields": SECTOR_FIELDS},
            "candidate_list": {
                "count_address": f"0x{CANDIDATE_COUNT:08X}",
                "pointer_base": f"0x{CANDIDATE_POINTERS:08X}",
                "sector_base": f"0x{CANDIDATE_SECTORS:08X}",
                "pointer_storage_end": f"0x{CANDIDATE_POINTERS_END:08X}",
                "pointer_storage_slots": POINTER_STORAGE_SLOTS,
                "writer_pc": "0x800368E8", "writer_has_bounds_check": False,
            },
            "plane_record": {"size": 0x20, "fields": PLANE_FIELDS,
                             "floor_normal_predicate": "normal_y < 0"},
            "grid_sector_scan_limit": SECTOR_GRID_LIMIT,
        },
        "source_status": {
            "matching_c": (
                "src/main/80038f38_sector_region_code_query.c is matching C; "
                "no matching-C claim is made for the larger resolver chain."),
            "asm": (
                "The sector/grid builders, resolver passes, player integrator, "
                "candidate builders, point test, and Y commit are byte-matched ASM units."),
            "semantic_c": (
                "src_re/collision_source_converter_80030f60.c, "
                "src_re/collision_plane_resolver_800345cc.c, and "
                "src_re/movement_integrator_8003633c.c are documentation-grade."),
        },
    }


def static_census_gaps(census: dict[str, Any]) -> list[str]:
    gaps = []
    assets = census.get("assets") or {}
    if assets.get("classified_assets") != 24:
        gaps.append("collision-classified asset census is not exactly 24")
    if assets.get("assets_with_collision_marker") != 14:
        gaps.append("collision marker 0x0103 is not present in exactly 14 staged assets")
    if assets.get("collision_chunks_roundtripped") != 28:
        gaps.append("0x0103/0x0104 semantic round-trip census is not exactly 28 chunks")
    for row in assets.get("rows") or []:
        if any(marker.get("semantic_recompression_equal") is not True
               for marker in row.get("collision_markers") or []):
            gaps.append(f"asset semantic recompression mismatch: {row.get('relative_input')}")
    if len(census.get("instruction_words") or {}) != len(EXPECTED_WORDS):
        gaps.append("decisive collision instruction census is incomplete")
    if len(census.get("regions") or {}) != len(FUNCTION_REGIONS):
        gaps.append("collision function frontier is incomplete")
    if any(row.get("match") not in {"asm", "c"}
           for row in (census.get("regions") or {}).values()):
        gaps.append("collision function frontier contains a non-matching build unit")
    contract = census.get("typed_contract") or {}
    if contract.get("grid_sector_scan_limit") != 700 or \
            (contract.get("candidate_list") or {}).get("pointer_storage_slots") != 400 or \
            (contract.get("candidate_list") or {}).get("writer_has_bounds_check") is not False:
        gaps.append("collision capacity/failure contract drifted")
    return gaps


def _method_present(capabilities: dict[str, Any], name: str) -> bool:
    return name in (capabilities.get("methods") or {})


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    return bytes.fromhex(row["hex"])


def _read_int(client: Any, address: int, kind: str) -> int:
    formats = {"u8": (1, "<B"), "s8": (1, "<b"),
               "u16": (2, "<H"), "s16": (2, "<h"),
               "u32": (4, "<I"), "s32": (4, "<i")}
    length, fmt = formats[kind]
    return struct.unpack(fmt, _read_memory(client, address, length))[0]


def _struct(client: Any, base: int, fields: list[dict[str, Any]]) -> dict[str, Any]:
    result = client.call("debugger.readStruct", {
        "base": f"0x{base:08X}", "fields": fields})
    values = {}
    for row in result.get("fields") or []:
        if row.get("valid") is not True:
            raise SystemExit(f"invalid structured collision read: {row}")
        values[row["name"]] = row["value"]
    if len(values) != len(fields):
        raise SystemExit(f"short structured collision read at {base:#x}: {result}")
    return values


def _checked_write(client: Any, kind: str, address: int, value: int) -> dict[str, Any]:
    sizes = {"U8": 1, "U16": 2, "U32": 4}
    method = f"debugger.write{kind}"
    result = client.call(method, {
        "address": f"0x{address:08X}", "value": value})
    if result.get("written") != sizes[kind]:
        raise SystemExit(f"collision perturbation did not apply: {method}: {result}")
    return {"method": method, "address": f"0x{address:08X}",
            "value": value, "rpc": result}


def _load_anchor(client: Any, path: Path) -> dict[str, Any]:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str(path.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False,
    })
    if loaded.get("loaded") is not True:
        raise SystemExit(f"collision anchor load failed: {path}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return loaded


def _compact_player(client: Any) -> dict[str, Any]:
    snap = locomotion._snapshot(client)
    return {"frame": snap["frame"], "cycle": snap["cycle"],
            "scene": snap["scene"], "working_actions": snap["working_actions"],
            "player_block_sha256": snap["player_block_sha256"],
            "fields": snap["fields"]}


def _sector_table(client: Any, *, retain_rows: bool = True) -> dict[str, Any]:
    count = _read_int(client, SECTOR_COUNT, "u32")
    if not 0 < count <= SECTOR_GRID_LIMIT:
        raise SystemExit(f"runtime collision sector count is unsafe: {count}")
    result = client.call("debugger.readArray", {
        "base": f"0x{SECTOR_TABLE:08X}", "count": count,
        "stride": SECTOR_STRIDE, "fields": SECTOR_FIELDS})
    rows = []
    for index, record in enumerate(result.get("records") or []):
        fields = {row["name"]: row["value"] for row in record.get("fields") or []
                  if row.get("valid") is True}
        if len(fields) != len(SECTOR_FIELDS):
            raise SystemExit(f"short runtime sector row {index}: {record}")
        rows.append({"index": index, **fields})
    if len(rows) != count:
        raise SystemExit(f"short runtime sector table: {len(rows)}/{count}")
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    histogram: dict[str, int] = {}
    for row in rows:
        key = str(row["region_code"])
        histogram[key] = histogram.get(key, 0) + 1
    return {"count": count, "sha256": _sha256_bytes(encoded),
            "region_code_histogram": histogram,
            "nonzero_region_rows": [row for row in rows if row["region_code"] != 0],
            "rows": rows if retain_rows else []}


def _wait_for_pause(client: Any, target: int, timeout: float = 15.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    status = client.call("debugger.status", {})
    while time.monotonic() < deadline:
        if status.get("paused") is True and int(str(status.get("pc")), 16) == target:
            return status
        time.sleep(0.01)
        status = client.call("debugger.status", {})
    client.call("debugger.pause", {})
    raise SystemExit(f"timed out waiting for collision PC {target:#x}: {status}")


def _run_until(client: Any, target: int) -> dict[str, Any]:
    client.call("debugger.runUntilAddress", {"address": f"0x{target:08X}"})
    return _wait_for_pause(client, target)


def _candidate_snapshot(client: Any, path: Path) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "cross": True}})
    caller = _run_until(client, 0x800495C8)
    boundary = _run_until(client, 0x80036BC8)
    count = _read_int(client, CANDIDATE_COUNT, "u32")
    if not 0 < count < POINTER_STORAGE_SLOTS:
        raise SystemExit(f"unsafe/empty player candidate count at resolver boundary: {count}")
    pointers_row = client.call("debugger.readArray", {
        "base": f"0x{CANDIDATE_POINTERS:08X}", "count": count, "stride": 4,
        "fields": [{"name": "pointer", "offset": 0, "type": "u32"}]})
    sectors_row = client.call("debugger.readArray", {
        "base": f"0x{CANDIDATE_SECTORS:08X}", "count": count, "stride": 2,
        "fields": [{"name": "sector", "offset": 0, "type": "u16"}]})
    pointers = [row["fields"][0]["value"] for row in pointers_row["records"]]
    sectors = [row["fields"][0]["value"] for row in sectors_row["records"]]
    unique = {}
    for pointer, sector in zip(pointers, sectors):
        if pointer not in unique:
            plane = _struct(client, pointer, PLANE_FIELDS)
            nx, ny, nz = plane["normal_x"], plane["normal_y"], plane["normal_z"]
            unique[pointer] = {
                "pointer": f"0x{pointer:08X}", "sector": sector, **plane,
                "normal_length_squared": nx * nx + ny * ny + nz * nz,
                "orientation": "floor_or_slope" if ny < 0 else "other_orientation",
            }
    client.call("emulator.clearControllerState", {"port": 0})
    return {
        "load": loaded, "caller_boundary": caller, "resolver_boundary": boundary,
        "count": count, "pointers": [f"0x{value:08X}" for value in pointers],
        "sectors": sectors, "unique_planes": list(unique.values()),
        "floor_or_slope_planes": sum(
            row["orientation"] == "floor_or_slope" for row in unique.values()),
        "other_orientation_planes": sum(
            row["orientation"] == "other_orientation" for row in unique.values()),
    }


def _branch(client: Any, path: Path, *, buttons: dict[str, bool] | None = None,
            frames: int = CONTROL_FRAMES) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    before = _compact_player(client)
    if buttons:
        client.call("emulator.setControllerState", {"port": 0, "buttons": buttons})
    client.call("emulator.advanceFrames", {"frames": frames})
    after = _compact_player(client)
    client.call("emulator.clearControllerState", {"port": 0})
    return {"load": loaded, "buttons": buttons or {}, "frames": frames,
            "before": before, "after": after}


def _run_breadth(client: Any, anchors: list[tuple[str, str]]) -> dict[str, Any]:
    results = {}
    for label, save in anchors:
        path = ROOT / save
        _load_anchor(client, path)
        table = _sector_table(client)
        current = _read_int(client, PLAYER_SECTOR, "s32")
        candidate = None if label == FLIGHT_LABEL else _candidate_snapshot(client, path)
        neutral = _branch(client, path)
        moving = _branch(client, path, buttons={"up": True, "cross": True}, frames=24)
        results[label] = {
            "save": save, "current_sector": current, "sector_table": table,
            "candidate_boundary": candidate, "neutral": neutral, "up_cross": moving,
            "position_delta": {
                axis: moving["after"]["fields"][axis] - neutral["after"]["fields"][axis]
                for axis in ("x", "y", "z")},
        }
        print(f"[collision-breadth] {label}: sectors={table['count']} "
              f"candidates={candidate['count'] if candidate else 'N/A'}")
    applicable = [row for row in results.values() if row["candidate_boundary"]]
    all_planes = [plane for row in applicable
                  for plane in row["candidate_boundary"]["unique_planes"]]
    return {
        "anchors": results,
        "summary": {
            "anchors_compared": len(results),
            "applicable_candidate_anchors": len(applicable),
            "exceptional_labels": [FLIGHT_LABEL],
            "sector_counts": {label: row["sector_table"]["count"]
                              for label, row in results.items()},
            "distinct_sector_table_hashes": sorted({
                row["sector_table"]["sha256"] for row in results.values()}),
            "candidate_count_min": min(row["candidate_boundary"]["count"]
                                       for row in applicable),
            "candidate_count_max": max(row["candidate_boundary"]["count"]
                                       for row in applicable),
            "floor_or_slope_plane_samples": sum(
                plane["orientation"] == "floor_or_slope" for plane in all_planes),
            "other_orientation_plane_samples": sum(
                plane["orientation"] == "other_orientation" for plane in all_planes),
            "nonzero_region_codes": sorted({
                item["region_code"] for row in results.values()
                for item in row["sector_table"]["nonzero_region_rows"]}),
            "movement_delta_labels": sorted(
                label for label, row in results.items()
                if any(row["position_delta"].values())),
        },
    }


def _mutated_branch(client: Any, path: Path, writes: list[tuple[str, int, int]]) -> dict[str, Any]:
    loaded = _load_anchor(client, path)
    applied = [_checked_write(client, kind, address, value)
               for kind, address, value in writes]
    before = _compact_player(client)
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": CONTROL_FRAMES})
    after = _compact_player(client)
    client.call("emulator.clearControllerState", {"port": 0})
    return {"load": loaded, "writes": applied, "frames": CONTROL_FRAMES,
            "buttons": {"up": True}, "before": before, "after": after}


def _run_geometry_controls(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_SAVE
    baseline = _branch(client, path, buttons={"up": True})
    _load_anchor(client, path)
    current = _read_int(client, PLAYER_SECTOR, "s32")
    active_y_addr = SECTOR_TABLE + current * SECTOR_STRIDE + 4
    active_y = _read_int(client, active_y_addr, "s32")
    active = _mutated_branch(
        client, path, [("U32", active_y_addr, (active_y + 2048) & 0xFFFFFFFF)])

    candidates = _candidate_snapshot(client, path)
    candidate_sectors = set(candidates["sectors"])
    distant_index = next(index for index in range(700)
                         if index != current and index not in candidate_sectors)
    _load_anchor(client, path)
    count = _read_int(client, SECTOR_COUNT, "u32")
    if distant_index >= count:
        raise SystemExit("no non-candidate runtime sector available for negative control")
    distant_y_addr = SECTOR_TABLE + distant_index * SECTOR_STRIDE + 4
    distant_y = _read_int(client, distant_y_addr, "s32")
    distant = _mutated_branch(
        client, path, [("U32", distant_y_addr, (distant_y + 2048) & 0xFFFFFFFF)])

    floor_planes = [row for row in candidates["unique_planes"]
                    if row["sector"] == current and row["normal_y"] < 0]
    if not floor_planes:
        raise SystemExit("no current-sector floor planes available for causal control")
    plane_writes = []
    for row in floor_planes:
        pointer = int(row["pointer"], 16)
        plane_writes.append(("U16", pointer + 8, (row["ref_y"] + 64) & 0xFFFF))
    planes = _mutated_branch(client, path, plane_writes)

    active_y_delta = active["after"]["fields"]["y"] - baseline["after"]["fields"]["y"]
    active_floor_delta = (active["after"]["fields"]["floor_y"] -
                          baseline["after"]["fields"]["floor_y"])
    distant_fields_equal = all(
        distant["after"]["fields"][key] == baseline["after"]["fields"][key]
        for key in ("x", "y", "z", "floor_y", "grounded"))
    plane_y_delta = planes["after"]["fields"]["y"] - baseline["after"]["fields"]["y"]
    plane_floor_delta = (planes["after"]["fields"]["floor_y"] -
                         baseline["after"]["fields"]["floor_y"])
    result = {
        "baseline": baseline,
        "active_sector_origin_shift": {
            "sector": current, "original_origin_y": active_y,
            "world_delta": 2048, "branch": active,
            "player_y_delta_vs_baseline": active_y_delta,
            "floor_y_delta_vs_baseline": active_floor_delta,
        },
        "distant_sector_origin_shift": {
            "sector": distant_index, "original_origin_y": distant_y,
            "world_delta": 2048, "branch": distant,
            "post_fields_equal_baseline": distant_fields_equal,
        },
        "current_sector_plane_ref_shift": {
            "sector": current, "local_ref_y_delta": 64,
            "mutated_plane_count": len(floor_planes), "planes": floor_planes,
            "branch": planes, "player_y_delta_vs_baseline": plane_y_delta,
            "floor_y_delta_vs_baseline": plane_floor_delta,
        },
    }
    if active_y_delta < 1500 or active_floor_delta < 1500 or \
            active["after"]["fields"]["grounded"] == 0:
        raise SystemExit(f"active-sector causal control failed: {result}")
    if not distant_fields_equal:
        raise SystemExit(f"distant-sector negative control changed player output: {result}")
    if plane_y_delta < 1500 or plane_floor_delta < 1500 or \
            planes["after"]["fields"]["grounded"] == 0:
        raise SystemExit(f"floor-plane causal control failed: {result}")
    return result


def _run_resolver_trace(client: Any) -> dict[str, Any]:
    path = ROOT / CONTROL_SAVE
    _load_anchor(client, path)
    client.call("execTrace.clear", {})
    specs = [
        ("player_integrator", 0x8003633C, ["a0", "a1", "ra"],
         {"registers": {"a0": f"0x{PLAYER_BASE:08X}"}}),
        ("candidate_boundary", 0x80036BC8, ["a0", "a1", "ra"], None),
        ("resolver_probe", 0x80035F24, ["a0", "a1", "a2", "a3", "ra"], None),
        ("resolver_accumulate", 0x800345CC, ["a0", "a1", "a2", "a3", "ra"], None),
        ("swept_resolver", 0x80035280, ["a0", "a1", "a2", "a3", "ra"], None),
        ("resolved_y_commit", 0x80036CEC, ["v1", "s7", "ra"], None),
        ("region_code_query", 0x80038F38, ["a0", "a1", "ra"], None),
    ]
    watches = []
    for label, pc, capture, filter_row in specs:
        request = {"pc": f"0x{pc:08X}", "capture": capture,
                   "label": label, "max_events": 256}
        if filter_row:
            request["filter"] = filter_row
        watches.append(client.call("execTrace.addWatch", request))
    client.call("emulator.setControllerState", {
        "port": 0, "buttons": {"up": True, "cross": True}})
    execution = client.call("execTrace.run", {"frames": TRACE_FRAMES})
    client.call("emulator.clearControllerState", {"port": 0})
    by_label = {}
    for spec, watch in zip(specs, watches):
        by_label[spec[0]] = client.call("execTrace.get", {
            "watch_id": watch["watch_id"], "offset": 0, "limit": 256})
    client.call("execTrace.clear", {})
    required = ("player_integrator", "candidate_boundary", "resolved_y_commit",
                "region_code_query")
    if execution.get("truncated") or any(
            by_label[label].get("truncated") or not by_label[label].get("events")
            for label in required):
        raise SystemExit(f"decisive collision resolver trace incomplete: {by_label}")
    if not (by_label["resolver_accumulate"].get("events") or
            by_label["swept_resolver"].get("events") or
            by_label["resolver_probe"].get("events")):
        raise SystemExit(f"no collision resolver helper executed: {by_label}")
    return {"save": CONTROL_SAVE, "buttons": {"up": True, "cross": True},
            "frames": TRACE_FRAMES, "watches": watches,
            "execution": execution, "by_label": by_label}


def _run_region_exit(client: Any) -> dict[str, Any]:
    path = ROOT / EXIT_SAVE
    loaded = _load_anchor(client, path)
    before = {"player": _compact_player(client),
              "sector": _read_int(client, PLAYER_SECTOR, "s32"),
              "transition_lever": _read_int(client, TRANSITION_LEVER, "u32")}
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    stop = client.call("emulator.advanceUntil", {
        "condition": {"kind": "memory", "address": f"0x{PLAYER_SECTOR:08X}",
                      "type": "s32", "op": "eq", "value": 177},
        "max_frames": 180, "observe": True}, timeout=300)
    client.call("emulator.clearControllerState", {"port": 0})
    if stop.get("reason") != "condition" or stop.get("final_value") != 177:
        raise SystemExit(f"natural LEVEL01 exit sector was not reached: {stop}")
    table = _sector_table(client)
    sector = table["rows"][177]
    gate_observed = _read_int(client, PLAYER_GATE, "u8")
    gate_one = _checked_write(client, "U8", PLAYER_GATE, 1)
    positive = client.call("debugger.callFunction", {
        "address": "0x80038F38", "a0": 0, "a1": PLAYER_GATE,
        "timeout": 10000}, timeout=30)
    gate_write = _checked_write(client, "U8", PLAYER_GATE, 0)
    negative = client.call("debugger.callFunction", {
        "address": "0x80038F38", "a0": 0, "a1": PLAYER_GATE,
        "timeout": 10000}, timeout=30)
    after = {"player": _compact_player(client),
             "sector": _read_int(client, PLAYER_SECTOR, "s32"),
             "transition_lever": _read_int(client, TRANSITION_LEVER, "u32")}
    result = {
        "load": loaded, "before": before, "advance_until": stop,
        "sector_177": sector, "gate_observed_at_pause": gate_observed,
        "gate_one_write": gate_one,
        "positive_query": positive, "gate_zero_write": gate_write,
        "negative_gate_query": negative, "after": after,
    }
    if sector["region_code"] != 2 or \
            positive.get("v0") != 2 or negative.get("v0") != 0 or \
            after["transition_lever"] != 1:
        raise SystemExit(f"region-code positive/negative control failed: {result}")
    return result


def _run_pause_lifecycle(client: Any) -> dict[str, Any]:
    path = ROOT / "level02.sav"
    loaded = _load_anchor(client, path)
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    before = _compact_player(client)
    candidate_count_before = _read_int(client, CANDIDATE_COUNT, "u32")
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    paused = _compact_player(client)
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"up": True}})
    client.call("emulator.advanceFrames", {"frames": 60})
    resumed = _compact_player(client)
    client.call("emulator.clearControllerState", {"port": 0})
    frozen = [key for key in ("x", "y", "z", "floor_y", "grounded")
              if before["fields"][key] == paused["fields"][key]]
    result = {"load": loaded, "before": before, "paused_after_up": paused,
              "resumed_after_up": resumed, "frozen_fields": frozen,
              "candidate_count_at_paused_frame_boundary": candidate_count_before}
    if len(frozen) != 5 or resumed["fields"]["x"] == paused["fields"]["x"] and \
            resumed["fields"]["z"] == paused["fields"]["z"]:
        raise SystemExit(f"collision pause lifecycle failed: {result}")
    return result


def _run_table_reuse(client: Any) -> dict[str, Any]:
    tables = []
    for save in ("level01.sav", "level02.sav", "level01.sav"):
        _load_anchor(client, ROOT / save)
        tables.append({"save": save, "table": _sector_table(client)})
    result = {"sequence": tables,
              "level01_reloaded_equal": tables[0]["table"]["sha256"] == tables[2]["table"]["sha256"],
              "level01_level02_different": tables[0]["table"]["sha256"] != tables[1]["table"]["sha256"]}
    if not result["level01_reloaded_equal"] or not result["level01_level02_different"]:
        raise SystemExit(f"collision table reuse/retirement failed: {result}")
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
        raise SystemExit(f"static collision census failed: {gaps}")
    stage_baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, all_selection = select_pristine_save_anchors(stage_baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("strict-pristine collision anchors no longer cover 19 gameplay contexts")
    saves = [save for _label, save in anchors] + [EXIT_SAVE]
    accepted = [row for row in all_selection["accepted"] if row["save"] in saves]
    selection = {**all_selection, "accepted": accepted, "rejected": [],
                 "anchors_requested": len(saves), "anchors_accepted": len(accepted),
                 "anchors_rejected": 0}
    if len(accepted) != len(saves):
        raise SystemExit("collision fixture selection does not cover every loaded save")

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status", "debugger.pause",
        "debugger.readMemory", "debugger.readStruct", "debugger.readArray",
        "debugger.writeU8", "debugger.writeU16", "debugger.writeU32",
        "debugger.runUntilAddress", "debugger.callFunction",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "emulator.advanceUntil",
        "execTrace.addWatch", "execTrace.run", "execTrace.get", "execTrace.clear",
        "movie.load", "movie.store", "movie.branch", "movie.editFrame",
        "movie.activate", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.remove", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks collision methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    breadth = _run_breadth(client, anchors)
    controls = _run_geometry_controls(client)
    resolver_trace = _run_resolver_trace(client)
    region_exit = _run_region_exit(client)
    pause = _run_pause_lifecycle(client)
    respawn = locomotion._run_respawn_control(client)
    table_reuse = _run_table_reuse(client)
    cold_boot = locomotion._run_cold_boot_movie(client)

    client.call("emulator.clearControllerState", {"port": 0})
    client.call("execTrace.clear", {})
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass
    provenance = finish_run(
        args, generator="tools/phase4_collision.py",
        anchor={
            "type": "cold-boot movie plus strict-pristine all-stage collision breadth, lifecycle, and causal controls",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES, "control_frames": CONTROL_FRAMES,
            "trace_frames": TRACE_FRAMES,
            "breadth_input": {"port": 0, "buttons": {"up": True, "cross": True}},
            "cold_boot_edit": cold_boot["edit_recipe"],
        },
    )
    document = {
        "_comment": (
            "Phase-4 E02 collision/floor-plane evidence regenerated from pristine "
            "executable/assets/media: typed tables and planes, 19 gameplay anchors, "
            "causal active/distant/plane controls, lifecycle, resolver trace, and the "
            "natural LEVEL01 region-code exit."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {
            "cold_boot": cold_boot, "breadth": breadth,
            "geometry_controls": controls, "resolver_trace": resolver_trace,
            "region_exit": region_exit, "pause_resume": pause,
            "death_respawn": respawn, "table_reuse": table_reuse,
        },
        "source_dependencies": {
            "tools/phase4_run_locomotion.py": _sha256(ROOT / "tools/phase4_run_locomotion.py"),
            "tools/native_collision_mesh_codec.py": _sha256(ROOT / "tools/native_collision_mesh_codec.py"),
            "tools/decode_level_raw.py": _sha256(ROOT / "tools/decode_level_raw.py"),
            "tools/recompress_level_raw.py": _sha256(ROOT / "tools/recompress_level_raw.py"),
        },
        "run_provenance": provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[collision] retained E02 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_collision.py",
                       anchor={"type": "aborted before retained collision evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned collision-instance failure cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
