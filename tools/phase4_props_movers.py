#!/usr/bin/env python3
"""Regenerate the active Phase-4 E08 props/movers catalog campaign.

This campaign deliberately separates three original-game surfaces which older
notes conflated: fixed pass-1 instances, pass-3 cull groups, and the scene-owned
64-record actor/mover pool.  Static mode enumerates every row from every pinned
staged LEVEL*.DAT.  Live mode joins that catalog to a cold boot, strict-pristine
whole-game anchors, phase-matched render perturbations, pause, and scene rebuild.

The retained result is intentionally an *active* campaign artifact.  It does
not promote switches, gates, authored interaction policy, or persistence until
those consumer-specific paths receive native positive and negative controls.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    from build_identity import load_baselines, verify_staged_input
    import dat_reloc
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_props_movers
    from tools.build_identity import load_baselines, verify_staged_input
    from tools import dat_reloc
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_props_movers.json"
BASELINE = ROOT / "analysis/phase2_stage_baseline.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

DAT_BASE_PTR = 0x80082498
PASS1_PTR = 0x800824AC
PASS3_PTR = 0x80082508
PASS3_BITMAP_HI = 0x800902C7
PASS3_VISIBLE_LIST = 0x80096EA8
SCENE_WORD = 0x80082504
PAUSE_FLAG = 0x8008224E
PLAYER_BASE = 0x800A6500
SECTOR_COUNT = 0x800822A0
SECTOR_TABLE = 0x800A7E48
SECTOR_STRIDE = 0x30

ACTOR_BASE = 0x8009FD80
ACTOR_STRIDE = 0x84
ACTOR_CAPACITY = 64
SOURCE_RECORD_SIZE = 0x1C
MOVER_UPDATE = 0x8004B940
MOVER_UPDATER = 0x8004D224

ROW_STRIDE = 0x14
MAX_TABLE_ROWS = 2048
EXPECTED_STATIC_COUNTS = {
    "files": 21, "pass1_rows": 9097, "pass3_rows": 1684,
    "external_source_rows": 2, "external_payload_rows": 114,
}
SETTLE_FRAMES = 2
RENDER_BRANCH_FRAMES = 20
MOVER_FRAMES = 4
EXPECTED_ACTOR_OBSERVATIONS = 605
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"
MOVIE_START = 8550
MOVIE_END = 8580
PASS1_CONTROL_SAVE = "acorn.sav"
PASS1_TARGET_INDEX = 214
PASS1_DONOR_INDEX = 117
PASS3_CONTROL_SAVE = "level01.sav"
FOCUSED_CONTROL_SAVES = ("wooden_fence.sav", "offering_stone_and_ramp.sav")

# These are the only actor IDs whose downstream row owner is already confirmed
# by current machine/Canon evidence.  Every other source signature stays a
# candidate cluster; the generator must not resurrect legacy species names.
KNOWN_DOWNSTREAM_ACTOR_OWNERS = {
    11: "seeds_plants_traversal_powers:A09/A13-A15",
    14: "bosses_special_objectives:F13_dot_guide",
    16: "bosses_special_objectives:D16_thumper",
    36: "bosses_special_objectives:D18_thud",
}

FUNCTION_REGIONS = {
    "dat_parser_relocator": (0x8001CDC0, 0x8001D3CC),
    "pass1_culler": (0x800140A0, 0x80014360),
    "pass3_culler": (0x80014360, 0x80014504),
    "mover_initializer": (0x80049C30, 0x80049E88),
    "mover_actor_update": (0x8004B940, 0x8004C10C),
    "mover_updater": (0x8004D224, 0x8004D698),
}

EXPECTED_WORDS = {
    "dat_parser_entry": (0x8001CDC0, 0x27BDFFD0),
    "pass1_culler_entry": (0x800140A0, 0x23BDFFE0),
    "pass1_flags_read": (0x80014170, 0x848B000E),
    "pass3_culler_entry": (0x80014360, 0x23BDFFE0),
    "pass3_bitmap_address": (0x800143D8, 0x3718238C),
    "mover_initializer_entry": (0x80049C30, 0x00804021),
    "mover_selector_load": (0x80049C78, 0x9122000D),
    "mover_actor_update_entry": (0x8004B940, 0x27BDFFB0),
    "mover_updater_entry": (0x8004D224, 0x27BDFFA0),
    "actor_pool_high": (0x8004D248, 0x3C12800A),
    "actor_pool_stride": (0x8004D410, 0x26520084),
    "actor_pool_capacity": (0x8004D41C, 0x2A820040),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _va_offset(address: int) -> int:
    return EXE_HEADER + address - EXE_BASE


def _word(exe: bytes, address: int) -> int:
    return struct.unpack_from("<I", exe, _va_offset(address))[0]


def _method_present(capabilities: dict[str, Any], method: str) -> bool:
    methods = capabilities.get("methods") or []
    return any((row.get("name") if isinstance(row, dict) else row) == method
               for row in methods)


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return data


def _read_u8(client: Any, address: int) -> int:
    return _read_memory(client, address, 1)[0]


def _read_u16(client: Any, address: int) -> int:
    return struct.unpack("<H", _read_memory(client, address, 2))[0]


def _read_u32(client: Any, address: int) -> int:
    return struct.unpack("<I", _read_memory(client, address, 4))[0]


def _write_u8(client: Any, address: int, value: int) -> dict[str, Any]:
    row = client.call("debugger.writeU8", {
        "address": f"0x{address:08X}", "value": value & 0xFF})
    if row.get("written") != 1:
        raise SystemExit(f"short debugger write at 0x{address:08X}: {row}")
    return row


def _write_u32(client: Any, address: int, value: int) -> dict[str, Any]:
    row = client.call("debugger.writeU32", {
        "address": f"0x{address:08X}", "value": value & 0xFFFFFFFF})
    if row.get("written") != 4:
        raise SystemExit(f"short debugger write at 0x{address:08X}: {row}")
    return row


def _parse_file_table(data: bytes, base: int, *, table: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(MAX_TABLE_ROWS):
        offset = base + index * ROW_STRIDE
        if offset + ROW_STRIDE > len(data):
            raise SystemExit(f"{table} table escaped file before sentinel at 0x{offset:X}")
        flags = struct.unpack_from("<H", data, offset + 0x0E)[0]
        if flags & 0x8000:
            return rows
        x, y, z = struct.unpack_from("<iii", data, offset)
        extent = struct.unpack_from("<h", data, offset + 0x0C)[0]
        source = struct.unpack_from("<I", data, offset + 0x10)[0]
        payload_field = source + (0x1C if flags & 0x08 else 0x14)
        source_valid = 0 <= source <= len(data) - 0x24
        payload_valid = source_valid and 0 <= payload_field <= len(data) - 4
        payload = struct.unpack_from("<I", data, payload_field)[0] if payload_valid else None
        payload_in_file = payload is not None and 0 <= payload < len(data)
        source_head = data[source:source + 0x24] if source_valid else b""
        payload_head = data[payload:min(payload + 0x40, len(data))] \
            if payload_in_file else b""
        rows.append({
            "index": index, "file_offset": f"0x{offset:X}",
            "position_file_units": [x, y, z],
            "position_world_units": [x << 5, y << 5, z << 5],
            "extent": extent, "flags": f"0x{flags:04X}",
            "source_offset": f"0x{source:X}", "source_in_file": source_valid,
            "source_class": (
                "in_file" if source_valid else
                "external_relative_negative" if source >= 0x80000000 else
                "external_positive"),
            "source_head_sha256": _sha256_bytes(source_head) if source_head else None,
            "payload_pointer_field": f"0x{payload_field:X}" if source_valid else None,
            "payload_offset": f"0x{payload:X}" if payload is not None else None,
            "payload_in_file": payload_in_file,
            "payload_class": (
                "unresolved_external_source" if payload is None else
                "in_file" if payload_in_file else
                "null" if payload == 0 else
                "external_relative_negative" if payload >= 0x80000000 else
                "external_positive"),
            "payload_head_sha256": _sha256_bytes(payload_head) if payload_head else None,
        })
    raise SystemExit(f"{table} table exceeded {MAX_TABLE_ROWS} rows without sentinel")


def _file_catalog(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    rel = path.relative_to(ROOT / "REBUILD/files").as_posix()
    verify_staged_input(rel, data)
    model = dat_reloc.DAT(data)
    trail, _records = model.trailing_base()
    cursor = trail + 0x0E
    while struct.unpack_from("<h", data, cursor)[0] >= 0:
        cursor += ROW_STRIDE
    pass1_count = (cursor - (trail + 0x0E)) // ROW_STRIDE
    p2 = trail + ROW_STRIDE * (pass1_count + 1)
    # The retail parser performs this arithmetic in 32-bit registers.  A -1
    # pass-2 sentinel therefore selects p2+4 as the pass-3 base; preserving the
    # wrap is necessary for 15 of the 21 pristine DATs.
    pass2_count = struct.unpack_from("<I", data, p2)[0]
    p3 = (p2 + ((pass2_count << 2) & 0xFFFFFFFF) + 8) & 0xFFFFFFFF
    meta = {"trail": trail, "p2": p2, "p3": p3}
    pass1 = _parse_file_table(data, meta["trail"], table=f"{rel}:pass1")
    pass3 = _parse_file_table(data, meta["p3"], table=f"{rel}:pass3")
    return {
        "input": f"REBUILD/files/{rel}", "size": len(data),
        "sha256": _sha256_bytes(data),
        "bases": {key: f"0x{value:X}" for key, value in meta.items()},
        "pass1": {"count": len(pass1), "rows": pass1},
        "pass3": {"count": len(pass3), "rows": pass3},
    }


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe is None else exe
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine E08 word mismatch at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        words[name] = {"address": f"0x{address:08X}", "word": f"0x{actual:08X}"}
    regions = {
        name: {"start": f"0x{start:08X}", "end": f"0x{end:08X}",
               "size": end - start,
               "sha256": _sha256_bytes(exe[_va_offset(start):_va_offset(end)])}
        for name, (start, end) in FUNCTION_REGIONS.items()
    }
    files = [_file_catalog(path) for path in sorted(
        (ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.DAT"))]
    all_pass1 = [row for file_row in files for row in file_row["pass1"]["rows"]]
    all_pass3 = [row for file_row in files for row in file_row["pass3"]["rows"]]
    summary = {
        "files": len(files),
        "pass1_rows": len(all_pass1), "pass3_rows": len(all_pass3),
        "pass1_counts": [row["pass1"]["count"] for row in files],
        "pass3_counts": [row["pass3"]["count"] for row in files],
        "pass1_distinct_source_heads": len({
            row["source_head_sha256"] for row in all_pass1
            if row["source_head_sha256"]}),
        "pass3_distinct_source_heads": len({
            row["source_head_sha256"] for row in all_pass3
            if row["source_head_sha256"]}),
        "pass1_distinct_payload_heads": len({
            row["payload_head_sha256"] for row in all_pass1
            if row["payload_head_sha256"]}),
        "pass3_distinct_payload_heads": len({
            row["payload_head_sha256"] for row in all_pass3
            if row["payload_head_sha256"]}),
        "external_source_rows": [
            f"{file_row['input']}:{table}:{row['index']}"
            for file_row in files for table in ("pass1", "pass3")
            for row in file_row[table]["rows"] if not row["source_in_file"]],
        "external_payload_rows": [
            f"{file_row['input']}:{table}:{row['index']}"
            for file_row in files for table in ("pass1", "pass3")
            for row in file_row[table]["rows"] if not row["payload_in_file"]],
        "source_classes": dict(sorted(Counter(
            row["source_class"] for row in all_pass1 + all_pass3).items())),
        "payload_classes": dict(sorted(Counter(
            row["payload_class"] for row in all_pass1 + all_pass3).items())),
    }
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}",
                       "sha256": _sha256_bytes(exe), "size": len(exe)},
        "instruction_words": words, "regions": regions,
        "catalog": {"files": files, "summary": summary},
        "typed_contract": {
            "table_stride": ROW_STRIDE,
            "pass1_role": "instance placement and per-frame source/model handoff",
            "pass3_role": "bitmap-gated cull group; XYZ is cull anchor, not draw position",
            "actor_pool": {"base": f"0x{ACTOR_BASE:08X}",
                           "stride": ACTOR_STRIDE, "capacity": ACTOR_CAPACITY},
            "residency": "tables and actor sources are scene-owned; resident code and fixed buffers are reused",
        },
    }


def static_census_gaps(doc: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    summary = doc["catalog"]["summary"]
    observed = {
        "files": summary["files"],
        "pass1_rows": summary["pass1_rows"],
        "pass3_rows": summary["pass3_rows"],
        "external_source_rows": len(summary["external_source_rows"]),
        "external_payload_rows": len(summary["external_payload_rows"]),
    }
    if observed != EXPECTED_STATIC_COUNTS:
        gaps.append(f"pinned DAT census drifted: {observed}")
    if summary["source_classes"] != {
            "external_positive": 1, "external_relative_negative": 1,
            "in_file": 10779}:
        gaps.append("source-pointer classification drifted")
    if summary["payload_classes"] != {
            "external_relative_negative": 112, "in_file": 10667,
            "unresolved_external_source": 2}:
        gaps.append("payload-pointer classification drifted")
    if doc["typed_contract"]["actor_pool"] != {
            "base": "0x8009FD80", "stride": 0x84, "capacity": 64}:
        gaps.append("fixed actor/mover pool contract drifted")
    if set(doc["regions"]) != set(FUNCTION_REGIONS):
        gaps.append("static parser/culler/mover frontier is incomplete")
    return gaps


def _load_anchor(client: Any, save: str) -> dict[str, Any]:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str((ROOT / save).resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    if loaded.get("loaded") is not True:
        raise SystemExit(f"failed to load {save}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return loaded


def _parse_runtime_table(client: Any, address: int, *, table: str) -> dict[str, Any]:
    raw = _read_memory(client, address, MAX_TABLE_ROWS * ROW_STRIDE)
    rows = []
    for index in range(MAX_TABLE_ROWS):
        offset = index * ROW_STRIDE
        flags = struct.unpack_from("<H", raw, offset + 0x0E)[0]
        if flags & 0x8000:
            used = raw[:offset + ROW_STRIDE]
            return {"address": f"0x{address:08X}", "count": len(rows),
                    "sha256_with_sentinel": _sha256_bytes(used), "rows": rows}
        x, y, z = struct.unpack_from("<iii", raw, offset)
        rows.append({
            "index": index, "address": f"0x{address + offset:08X}",
            "position": [x, y, z],
            "extent": struct.unpack_from("<h", raw, offset + 0x0C)[0],
            "flags": f"0x{flags:04X}",
            "source_pointer": f"0x{struct.unpack_from('<I', raw, offset + 0x10)[0]:08X}",
        })
    raise SystemExit(f"runtime {table} table exceeded {MAX_TABLE_ROWS} rows")


def _source_record_snapshot(client: Any, address: int) -> dict[str, Any]:
    """Decode the initializer-consumed fields without retaining source bytes."""
    if not 0x80000000 <= address <= 0x80200000 - SOURCE_RECORD_SIZE:
        raise SystemExit(f"actor source pointer escaped RAM: 0x{address:08X}")
    raw = _read_memory(client, address, SOURCE_RECORD_SIZE)
    actor_id = raw[0x0C]
    selector = raw[0x0D]
    source_flags = struct.unpack_from("<H", raw, 0x12)[0]
    # +0x0E and +0x18..+0x1B are runtime-mutated by the native updater.  The
    # stable clustering signature therefore covers only the fields consumed by
    # initializer 0x80049C30 plus the still-unknown authored parameter word.
    authored_signature = bytes((
        actor_id, selector, raw[0x0F], raw[0x10], raw[0x11],
        raw[0x12], raw[0x13],
    )) + raw[0x14:0x18]
    return {
        "address": f"0x{address:08X}",
        "record_sha256": _sha256_bytes(raw),
        "position_file_units": list(struct.unpack_from("<iii", raw, 0)),
        "actor_id": actor_id,
        "program_selector": selector,
        "runtime_byte_0e": raw[0x0E],
        "config_byte_0f": raw[0x0F],
        "initial_hp": raw[0x10],
        "initial_wait": raw[0x11],
        "source_flags": source_flags,
        "authored_parameter_sha256": _sha256_bytes(raw[0x14:0x18]),
        "runtime_tail_sha256": _sha256_bytes(raw[0x18:0x1C]),
        "authored_signature_sha256": _sha256_bytes(authored_signature),
    }


def _actor_snapshot(client: Any) -> dict[str, Any]:
    raw = _read_memory(client, ACTOR_BASE, ACTOR_CAPACITY * ACTOR_STRIDE)
    records = []
    for slot in range(ACTOR_CAPACITY):
        row = raw[slot * ACTOR_STRIDE:(slot + 1) * ACTOR_STRIDE]
        actor_id = struct.unpack_from("<I", row, 0)[0]
        if not actor_id:
            continue
        source_pointer = struct.unpack_from("<I", row, 0x80)[0]
        source = _source_record_snapshot(client, source_pointer)
        if source["actor_id"] != actor_id:
            raise SystemExit(
                f"actor/source id mismatch in slot {slot}: "
                f"{actor_id} != {source['actor_id']}")
        records.append({
            "slot": slot, "address": f"0x{ACTOR_BASE + slot * ACTOR_STRIDE:08X}",
            "id": actor_id, "position": list(struct.unpack_from("<iii", row, 4)),
            "velocity": list(struct.unpack_from("<iii", row, 0x10)),
            "target": list(struct.unpack_from("<iii", row, 0x34)),
            "flags": struct.unpack_from("<H", row, 0x5C)[0],
            "wait": struct.unpack_from("<h", row, 0x60)[0],
            "instruction_pointer": f"0x{struct.unpack_from('<I', row, 0x70)[0]:08X}",
            "callback": f"0x{struct.unpack_from('<I', row, 0x7C)[0]:08X}",
            "source_pointer": f"0x{source_pointer:08X}",
            "source": source,
        })
    return {"base": f"0x{ACTOR_BASE:08X}", "stride": ACTOR_STRIDE,
            "capacity": ACTOR_CAPACITY, "live_count": len(records),
            "raw_sha256": _sha256_bytes(raw), "records": records}


def _world_snapshot(client: Any) -> dict[str, Any]:
    dat_base = _read_u32(client, DAT_BASE_PTR)
    pass1 = _read_u32(client, PASS1_PTR)
    pass3 = _read_u32(client, PASS3_PTR)
    if not all(0x80010000 <= value < 0x80200000
               for value in (dat_base, pass1, pass3)):
        raise SystemExit(f"invalid live DAT pointers: {dat_base:X}/{pass1:X}/{pass3:X}")
    count = _read_u32(client, SECTOR_COUNT)
    if not 0 < count <= 700:
        raise SystemExit(f"invalid collision sector count {count}")
    collision = _read_memory(client, SECTOR_TABLE, count * SECTOR_STRIDE)
    runtime_pass3 = _parse_runtime_table(client, pass3, table="pass3")
    visible_raw = struct.unpack(
        f"<{runtime_pass3['count']}I",
        _read_memory(client, PASS3_VISIBLE_LIST, runtime_pass3["count"] * 4))
    visible_indices = []
    for value in visible_raw:
        pointer = value & ~1
        if not (pass3 <= pointer < pass3 + runtime_pass3["count"] * ROW_STRIDE):
            continue
        delta = pointer - pass3
        if delta % ROW_STRIDE:
            continue
        index = delta // ROW_STRIDE
        if index not in visible_indices:
            visible_indices.append(index)
    return {
        "scene": _read_u32(client, SCENE_WORD),
        "dat_base": f"0x{dat_base:08X}",
        "pass1": _parse_runtime_table(client, pass1, table="pass1"),
        "pass3": runtime_pass3,
        "pass3_visible_indices": visible_indices,
        "pass3_bitmap_sha256": _sha256_bytes(
            _read_memory(client, PASS3_BITMAP_HI - 255, 256)),
        "collision": {"count": count, "sha256": _sha256_bytes(collision)},
        "player": {"position": list(struct.unpack(
            "<iii", _read_memory(client, PLAYER_BASE, 12)))},
        "actors": _actor_snapshot(client),
    }


def _compact_world(snapshot: dict[str, Any], *, actor_records: bool = False) \
        -> dict[str, Any]:
    """Retain proof-bearing hashes/counts without duplicating 10k table rows."""
    actors = {key: snapshot["actors"][key]
              for key in ("base", "stride", "capacity", "live_count", "raw_sha256")}
    if actor_records:
        actors["records"] = snapshot["actors"]["records"]
    compact = {
        "scene": snapshot["scene"], "dat_base": snapshot["dat_base"],
        "pass1": {key: snapshot["pass1"][key]
                  for key in ("address", "count", "sha256_with_sentinel")},
        "pass3": {key: snapshot["pass3"][key]
                  for key in ("address", "count", "sha256_with_sentinel")},
        "pass3_visible_indices": snapshot["pass3_visible_indices"],
        "pass3_bitmap_sha256": snapshot["pass3_bitmap_sha256"],
        "collision": snapshot["collision"], "player": snapshot["player"],
        "actors": actors,
    }
    if "pause_flag" in snapshot:
        compact["pause_flag"] = snapshot["pause_flag"]
    return compact


def _trace_movers(client: Any, frames: int = MOVER_FRAMES) -> dict[str, Any]:
    client.call("execTrace.clear", {})
    watch = client.call("execTrace.addWatch", {
        "pc": f"0x{MOVER_UPDATE:08X}", "capture": ["a0", "ra"],
        "label": "mover_actor_update", "max_events": 4096})
    client.call("execTrace.run", {"frames": frames})
    trace = client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": 4096})
    client.call("execTrace.clear", {})
    if trace.get("truncated"):
        raise SystemExit("mover trace truncated")
    addresses = [int(event["regs"]["a0"], 16) for event in trace["events"]]
    slots = sorted({(address - ACTOR_BASE) // ACTOR_STRIDE for address in addresses
                    if ACTOR_BASE <= address < ACTOR_BASE + ACTOR_CAPACITY * ACTOR_STRIDE
                    and (address - ACTOR_BASE) % ACTOR_STRIDE == 0})
    return {"frames": frames, "watch": watch, "returned": trace["total"],
            "truncated": trace.get("truncated", False),
            "actor_slots": slots, "first_events": trace["events"][:8]}


def _run_breadth(client: Any, anchors: list[tuple[str, str]]) -> dict[str, Any]:
    trials = []
    for label, save in anchors:
        loaded = _load_anchor(client, save)
        before = _world_snapshot(client)
        trace = _trace_movers(client)
        after = _world_snapshot(client)
        before_pos = {row["slot"]: row["position"] for row in before["actors"]["records"]}
        after_pos = {row["slot"]: row["position"] for row in after["actors"]["records"]}
        moved = sorted(slot for slot in before_pos.keys() & after_pos.keys()
                       if before_pos[slot] != after_pos[slot])
        trials.append({"label": label, "save": save, "load": loaded,
                       "before": _compact_world(before, actor_records=True),
                       "trace": trace,
                       "after": _compact_world(after, actor_records=True),
                       "moved_actor_slots": moved})
    summary = {
        "anchors": len(trials),
        "scenes": sorted({row["before"]["scene"] for row in trials}),
        "pass1_counts": {row["label"]: row["before"]["pass1"]["count"]
                         for row in trials},
        "pass3_counts": {row["label"]: row["before"]["pass3"]["count"]
                         for row in trials},
        "distinct_pass1_hashes": sorted({
            row["before"]["pass1"]["sha256_with_sentinel"] for row in trials}),
        "distinct_pass3_hashes": sorted({
            row["before"]["pass3"]["sha256_with_sentinel"] for row in trials}),
        "actor_counts": {row["label"]: row["before"]["actors"]["live_count"]
                         for row in trials},
        "actor_ids": sorted({actor["id"] for row in trials
                             for actor in row["before"]["actors"]["records"]}),
        "mover_trace_events": sum(row["trace"]["returned"] for row in trials),
        "mover_traced_labels": [row["label"] for row in trials
                                if row["trace"]["returned"]],
        "naturally_moving_labels": [row["label"] for row in trials
                                    if row["moved_actor_slots"]],
    }
    if summary["anchors"] != 19 or len(summary["scenes"]) != 16 or \
            len(summary["actor_ids"]) != 41 or not summary["mover_trace_events"]:
        raise SystemExit(f"E08 whole-game live breadth drifted: {summary}")
    return {"trials": trials, "summary": summary}


def _source_actor_clusters(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate every observed actor by its stable authored source signature."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    observations = []
    for trial in trials:
        moved = set(trial["moved_actor_slots"])
        for actor in trial["before"]["actors"]["records"]:
            source = actor["source"]
            observation = {
                "label": trial["label"], "scene": trial["before"]["scene"],
                "slot": actor["slot"], "actor_id": actor["id"],
                "moved": actor["slot"] in moved, "flags": actor["flags"],
                "callback": actor["callback"],
                "instruction_pointer": actor["instruction_pointer"],
                "source_pointer": actor["source_pointer"], "source": source,
            }
            observations.append(observation)
            grouped.setdefault(source["authored_signature_sha256"], []).append(
                observation)

    clusters = []
    for signature, rows in sorted(grouped.items()):
        first = rows[0]
        source = first["source"]
        actor_id = source["actor_id"]
        clusters.append({
            "authored_signature_sha256": signature,
            "actor_id": actor_id,
            "program_selector": source["program_selector"],
            "config_byte_0f": source["config_byte_0f"],
            "initial_hp": source["initial_hp"],
            "initial_wait": source["initial_wait"],
            "source_flags": source["source_flags"],
            "authored_parameter_sha256": source["authored_parameter_sha256"],
            "observations": len(rows),
            "labels": sorted({row["label"] for row in rows}),
            "scenes": sorted({row["scene"] for row in rows}),
            "source_pointers": sorted({row["source_pointer"] for row in rows}),
            "callbacks": sorted({row["callback"] for row in rows}),
            "instruction_pointers": sorted(
                {row["instruction_pointer"] for row in rows}),
            "runtime_actor_flags": sorted({row["flags"] for row in rows}),
            "runtime_record_hashes": sorted(
                {row["source"]["record_sha256"] for row in rows}),
            "moved_observations": sum(row["moved"] for row in rows),
            "confirmed_downstream_owner": KNOWN_DOWNSTREAM_ACTOR_OWNERS.get(
                actor_id),
            "owner_classification": (
                "confirmed_downstream" if actor_id in KNOWN_DOWNSTREAM_ACTOR_OWNERS
                else "unclassified_e08_or_downstream_candidate"),
        })

    behavior_groups: dict[int, list[dict[str, Any]]] = {}
    for row in observations:
        source = row["source"]
        type_word = (source["program_selector"] << 8) | source["actor_id"]
        behavior_groups.setdefault(type_word, []).append(row)
    behavior_classes = []
    for type_word, rows in sorted(behavior_groups.items()):
        first = rows[0]
        source = first["source"]
        actor_id = source["actor_id"]
        behavior_classes.append({
            "type_word": f"0x{type_word:04X}",
            "actor_id": actor_id,
            "program_selector": source["program_selector"],
            "observations": len(rows),
            "labels": sorted({row["label"] for row in rows}),
            "scenes": sorted({row["scene"] for row in rows}),
            "authored_signatures": sorted({
                row["source"]["authored_signature_sha256"] for row in rows}),
            "source_flags": sorted({row["source"]["source_flags"] for row in rows}),
            "config_bytes_0f": sorted({
                row["source"]["config_byte_0f"] for row in rows}),
            "initial_hp_values": sorted({
                row["source"]["initial_hp"] for row in rows}),
            "initial_wait_values": sorted({
                row["source"]["initial_wait"] for row in rows}),
            "authored_parameter_hashes": sorted({
                row["source"]["authored_parameter_sha256"] for row in rows}),
            "callbacks": sorted({row["callback"] for row in rows}),
            "runtime_actor_flags": sorted({row["flags"] for row in rows}),
            "moved_observations": sum(row["moved"] for row in rows),
            "confirmed_downstream_owner": KNOWN_DOWNSTREAM_ACTOR_OWNERS.get(
                actor_id),
            "owner_classification": (
                "confirmed_downstream" if actor_id in KNOWN_DOWNSTREAM_ACTOR_OWNERS
                else "unclassified_e08_or_downstream_candidate"),
        })

    actor_ids = sorted({row["actor_id"] for row in observations})
    selectors = sorted({row["source"]["program_selector"] for row in observations})
    callbacks = sorted({row["callback"] for row in observations
                        if row["callback"] != "0x00000000"})
    unclassified_variants = [row for row in clusters
                             if row["owner_classification"].startswith(
                                 "unclassified")]
    unclassified_classes = [row for row in behavior_classes
                            if row["owner_classification"].startswith(
                                "unclassified")]
    if len(observations) != EXPECTED_ACTOR_OBSERVATIONS or \
            len(behavior_classes) != 54 or actor_ids != list(range(1, 42)) or \
            not selectors or not callbacks:
        raise SystemExit(
            "E08 actor/source clustering lost retained breadth: "
            f"observations={len(observations)} ids={actor_ids} "
            f"selectors={selectors} callbacks={callbacks}")
    return {
        "summary": {
            "observations": len(observations),
            "behavior_classes": len(behavior_classes),
            "authored_variants": len(clusters),
            "actor_ids": actor_ids, "program_selectors": selectors,
            "nonzero_callbacks": callbacks,
            "confirmed_downstream_actor_ids": sorted(KNOWN_DOWNSTREAM_ACTOR_OWNERS),
            "unclassified_behavior_classes": len(unclassified_classes),
            "unclassified_authored_variants": len(unclassified_variants),
            "all_actor_source_ids_match": True,
        },
        "behavior_classes": behavior_classes,
        "authored_variants": clusters,
    }


def _run_focused_controls(client: Any, saves: tuple[str, ...]) -> dict[str, Any]:
    """Inspect filename-led E08 saves without treating their names as proof."""
    controls = []
    for save in saves:
        loaded = _load_anchor(client, save)
        before = _world_snapshot(client)
        trace = _trace_movers(client, 20)
        after = _world_snapshot(client)
        controls.append({
            "save": save, "load": loaded,
            "before": _compact_world(before, actor_records=True),
            "trace": trace, "after": _compact_world(after, actor_records=True),
            "interpretation": (
                "focused visual lead only; native trigger semantics require "
                "an observed state/outcome delta"),
        })
    return {"controls": controls, "count": len(controls)}


def _frame_payload(client: Any) -> dict[str, Any]:
    row = client.call("gpu.frameSnapshot", {"buffer": "displayed", "format": "raw16"})
    encoded = next((row.get(key) for key in ("data", "base64", "image", "png")
                    if isinstance(row.get(key), str)), None)
    if encoded is None:
        raise SystemExit(f"gpu.frameSnapshot returned no payload: {row.keys()}")
    data = base64.b64decode(encoded)
    return {"sha256": _sha256_bytes(data), "data": data,
            "width": row.get("width"), "height": row.get("height"),
            "format": row.get("format"), "buffer": row.get("buffer")}


def _frame_diff(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    if len(left["data"]) != len(right["data"]):
        raise SystemExit("phase-matched frame payload sizes differ")
    if len(left["data"]) % 2:
        raise SystemExit("raw16 frame payload has odd size")
    pixels = len(left["data"]) // 2
    changed = sum(left["data"][i:i + 2] != right["data"][i:i + 2]
                  for i in range(0, len(left["data"]), 2))
    return {"pixels": pixels, "changed_pixels": changed,
            "changed_fraction": changed / pixels if pixels else 0,
            "left_sha256": left["sha256"], "right_sha256": right["sha256"]}


def _branch_snapshot(client: Any, save: str, edit=None) -> dict[str, Any]:
    loaded = _load_anchor(client, save)
    before = _world_snapshot(client)
    writes = edit(client, before) if edit else []
    client.call("emulator.advanceFrames", {"frames": RENDER_BRANCH_FRAMES})
    client.call("debugger.pause", {})
    after = _world_snapshot(client)
    frame = _frame_payload(client)
    frame.pop("data")
    return {"load": loaded, "before": before, "writes": writes,
            "after": after, "frame": frame}


def _render_branch(client: Any, save: str, edit=None) -> tuple[dict[str, Any], dict[str, Any]]:
    loaded = _load_anchor(client, save)
    before = _world_snapshot(client)
    writes = edit(client, before) if edit else []
    client.call("emulator.advanceFrames", {"frames": RENDER_BRANCH_FRAMES})
    client.call("debugger.pause", {})
    after = _world_snapshot(client)
    frame = _frame_payload(client)
    compact = {"load": loaded, "before": _compact_world(before), "writes": writes,
               "after": _compact_world(after),
               "frame": {key: value for key, value in frame.items()
                         if key != "data"}}
    return compact, frame


def _phase_matched_render_controls(client: Any) -> dict[str, Any]:
    p1_control, p1_control_frame = _render_branch(client, PASS1_CONTROL_SAVE)

    def swap_pass1(c, world):
        base = int(world["pass1"]["address"], 16)
        target = base + PASS1_TARGET_INDEX * ROW_STRIDE + 0x10
        donor = base + PASS1_DONOR_INDEX * ROW_STRIDE + 0x10
        target_value = _read_u32(c, target)
        donor_value = _read_u32(c, donor)
        return [{"target": f"0x{target:08X}", "old": f"0x{target_value:08X}",
                 "donor": f"0x{donor:08X}", "new": f"0x{donor_value:08X}",
                 "write": _write_u32(c, target, donor_value)}]

    p1_edit, p1_edit_frame = _render_branch(client, PASS1_CONTROL_SAVE, swap_pass1)
    p1_diff = _frame_diff(p1_control_frame, p1_edit_frame)

    p3_control, p3_control_frame = _render_branch(client, PASS3_CONTROL_SAVE)

    def clear_pass3_bitmap(c, world):
        byte_count = (world["pass3"]["count"] + 7) // 8
        writes = []
        for offset in range(byte_count):
            address = PASS3_BITMAP_HI - offset
            old = _read_u8(c, address)
            writes.append({"bitmap_address": f"0x{address:08X}",
                           "old": old, "new": 0,
                           "write": _write_u8(c, address, 0)})
        return writes

    p3_disabled, p3_disabled_frame = _render_branch(
        client, PASS3_CONTROL_SAVE, clear_pass3_bitmap)
    p3_disabled_diff = _frame_diff(p3_control_frame, p3_disabled_frame)

    def nudge_pass3_anchor(c, world):
        base = int(world["pass3"]["address"], 16)
        if not world["pass3_visible_indices"]:
            raise SystemExit("pass-3 negative control has no visible record")
        target_index = world["pass3_visible_indices"][0]
        record = base + target_index * ROW_STRIDE
        xyz = list(world["pass3"]["rows"][target_index]["position"])
        xyz[0] += 32
        return [{"record": target_index,
                 "address": f"0x{record:08X}",
                 "old_position": world["pass3"]["rows"][target_index]["position"],
                 "new_position": xyz,
                 "writes": [_write_u32(c, record + i * 4, value)
                            for i, value in enumerate(xyz)]}]

    p3_nudged, p3_nudged_frame = _render_branch(
        client, PASS3_CONTROL_SAVE, nudge_pass3_anchor)
    p3_nudged_diff = _frame_diff(p3_control_frame, p3_nudged_frame)

    if not p1_diff["changed_pixels"] or not p3_disabled_diff["changed_pixels"]:
        raise SystemExit(
            f"E08 positive render controls produced no visual delta: "
            f"pass1={p1_diff} pass3={p3_disabled_diff}")
    for name, control, edited in (
            ("pass1", p1_control, p1_edit),
            ("pass3_disabled", p3_control, p3_disabled),
            ("pass3_nudged", p3_control, p3_nudged)):
        if control["after"]["collision"] != edited["after"]["collision"] or \
                control["after"]["player"] != edited["after"]["player"]:
            raise SystemExit(f"E08 {name} render-only control changed collision/player state")
    target_index = p3_nudged["writes"][0]["record"]
    if target_index not in p3_control["after"]["pass3_visible_indices"] or \
            target_index not in p3_nudged["after"]["pass3_visible_indices"] or \
            p3_nudged_diff["changed_pixels"] != 0:
        raise SystemExit(
            "E08 pass3 cull-preserving anchor negative failed: "
            f"record={target_index} diff={p3_nudged_diff} "
            f"control_visible={p3_control['after']['pass3_visible_indices']} "
            f"edited_visible={p3_nudged['after']['pass3_visible_indices']}")
    return {
        "pass1_payload_swap": {"control": p1_control, "edited": p1_edit,
                               "frame_diff": p1_diff},
        "pass3_bitmap_disable": {"control": p3_control, "edited": p3_disabled,
                                 "frame_diff": p3_disabled_diff},
        "pass3_anchor_nudge_negative": {"control": p3_control,
                                         "edited": p3_nudged,
                                         "frame_diff": p3_nudged_diff},
    }


def _run_pause(client: Any) -> dict[str, Any]:
    _load_anchor(client, "level01.sav")
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused = _world_snapshot(client)
    paused["pause_flag"] = _read_u16(client, PAUSE_FLAG)
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = _world_snapshot(client)
    frozen["pause_flag"] = _read_u16(client, PAUSE_FLAG)
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    client.call("emulator.clearControllerState", {"port": 0})
    resumed = _world_snapshot(client)
    resumed["pause_flag"] = _read_u16(client, PAUSE_FLAG)
    trace = _trace_movers(client, 20)
    progressed = _world_snapshot(client)
    if paused["pause_flag"] != 1 or frozen["pause_flag"] != 1 or \
            paused["actors"]["raw_sha256"] != frozen["actors"]["raw_sha256"] or \
            resumed["pause_flag"] != 0 or not trace["returned"]:
        raise SystemExit("E08 pause/resume actor-mover control failed")
    return {"paused": _compact_world(paused), "frozen": _compact_world(frozen),
            "resumed": _compact_world(resumed), "post_resume_trace": trace,
            "progressed": _compact_world(progressed)}


def _stable_world(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene": snapshot["scene"],
        "pass1_hash": snapshot["pass1"]["sha256_with_sentinel"],
        "pass3_hash": snapshot["pass3"]["sha256_with_sentinel"],
        "pass1_count": snapshot["pass1"]["count"],
        "pass3_count": snapshot["pass3"]["count"],
        "actor_sources": [{"slot": row["slot"], "id": row["id"],
                           "source_pointer": row["source_pointer"]}
                          for row in snapshot["actors"]["records"]],
    }


def _run_scene_reuse(client: Any) -> dict[str, Any]:
    rows = []
    for save in ("level01.sav", "level02.sav", "level01.sav"):
        loaded = _load_anchor(client, save)
        rows.append({"save": save, "load": loaded,
                     "world": _stable_world(_world_snapshot(client))})
    if rows[0]["world"] != rows[2]["world"] or \
            rows[0]["world"] == rows[1]["world"]:
        raise SystemExit("E08 LEVEL01->LEVEL02->LEVEL01 scene ownership did not rebuild")
    return {"loads": rows, "level01_rebuilt_identically": True,
            "level02_distinct": True}


def _movie_cleanup(client: Any) -> None:
    for method in ("movie.stopPlayback", "movie.clear"):
        try:
            client.call(method, {})
        except Exception:
            pass


def _base_movie_pin() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(BASE_MOVIE)
    path = ROOT / BASE_MOVIE
    movie = json.loads(path.read_text()) if path.is_file() else {}
    if not pin or pin.get("media_class") != "pristine_serial" or \
            pin.get("sha256") != _sha256(path) or \
            movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True or \
            len(movie.get("frames") or []) <= MOVIE_END:
        raise SystemExit("E08 cold-boot movie is missing, stale, or not v3 from-boot")
    return {"path": BASE_MOVIE, "sha256": pin["sha256"], "size": pin["size"],
            "media_class": pin["media_class"], "frames": len(movie["frames"])}


def _run_cold_boot(client: Any) -> dict[str, Any]:
    pin = _base_movie_pin()
    client.call("debugger.pause", {})
    _movie_cleanup(client)
    try:
        loaded = client.call("movie.load", {"path": str((ROOT / BASE_MOVIE).resolve())})
        started = client.call("movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {"frame": MOVIE_START,
                                               "max_frames": 9000}, timeout=900)
        before = _world_snapshot(client)
        client.call("movie.advanceToFrame", {"frame": MOVIE_END,
                                               "max_frames": 100}, timeout=900)
        after = _world_snapshot(client)
        status = client.call("movie.status", {})
    finally:
        _movie_cleanup(client)
    if started.get("reproducible") is not True or status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            before["scene"] != 1 or after["scene"] != 1:
        raise SystemExit(
            "E08 cold-boot pass-table/mover oracle did not reproduce: "
            f"started_reproducible={started.get('reproducible')} "
            f"status_reproducible={status.get('reproducible')} "
            f"truncated={status.get('truncated')} "
            f"scenes={before['scene']}/{after['scene']} "
            f"playback_index={status.get('playback_index')}")
    return {"movie": pin, "load": loaded, "started": started,
            "window": [MOVIE_START, MOVIE_END],
            "before": _compact_world(before),
            "after": _compact_world(after), "status": status}


def _selection_with_extras(baseline: dict[str, Any], extras: list[str]) \
        -> tuple[list[tuple[str, str]], dict[str, Any]]:
    anchors, selection = select_pristine_save_anchors(baseline)
    anchors = anchors[:19]
    accepted = selection["accepted"][:19]
    seen = {save for _label, save in anchors}
    for save in extras:
        if save in seen:
            continue
        declaration = verify_declared_save_fixture(
            ROOT / save, allowed_media_classes={"pristine"})
        anchors.append((f"control_{Path(save).stem}", save))
        accepted.append({"label": f"control_{Path(save).stem}", "save": save,
                         **declaration})
        seen.add(save)
    return anchors, {
        **selection, "accepted": accepted, "rejected": [],
        "anchors_requested": len(accepted), "anchors_accepted": len(accepted),
        "anchors_rejected": 0,
    }


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    gaps = static_census_gaps(static)
    if gaps:
        raise SystemExit(f"static E08 catalog failed: {gaps}")
    baseline = json.loads(BASELINE.read_text())
    all_anchors, selection = _selection_with_extras(
        baseline, [PASS1_CONTROL_SAVE, *FOCUSED_CONTROL_SAVES])
    breadth_anchors = all_anchors[:19]
    saves = [save for _label, save in all_anchors]

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU8", "debugger.writeU32",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "execTrace.addWatch", "execTrace.get",
        "execTrace.run", "execTrace.clear", "gpu.frameSnapshot",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E08 methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    cold_boot = _run_cold_boot(client)
    breadth = _run_breadth(client, breadth_anchors)
    source_actor_clusters = _source_actor_clusters(breadth["trials"])
    focused_controls = _run_focused_controls(client, FOCUSED_CONTROL_SAVES)
    render = _phase_matched_render_controls(client)
    pause = _run_pause(client)
    scene_reuse = _run_scene_reuse(client)

    provenance = finish_run(
        args, generator="tools/phase4_props_movers.py",
        anchor={
            "type": "cold-boot and strict-pristine pass-table/mover catalog with authored source clusters, focused controls, phase-matched render controls, pause and scene reuse",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["movie"], "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES, "mover_trace_frames": MOVER_FRAMES,
            "cold_boot_window": [MOVIE_START, MOVIE_END],
            "render_branch_frames": RENDER_BRANCH_FRAMES,
        })
    document = {
        "_comment": "Active Phase-4 E08 evidence: exhaustive pinned DAT catalog plus isolated pristine actor/source clustering and pass-table/render/mover/lifecycle controls. Switch/gate policy remains open.",
        "generated": date.today().isoformat(), "campaign_state": "active_partial",
        "static_census": static,
        "live": {"cold_boot": cold_boot, "breadth": breadth,
                 "source_actor_clusters": source_actor_clusters,
                 "focused_controls": focused_controls,
                 "render_controls": render, "pause_resume": pause,
                 "scene_reuse": scene_reuse},
        "bounded_open_frontier": {
            "interaction_rules": "Classify the remaining authored source signatures by observed native contact, switch, gate and mover outcomes; pointer identity and filenames are not semantic proof.",
            "persistence_reset": "Trace native switch/gate state through denial/success, death, checkpoint, reload and save/load.",
            "terrain_baked_boundary": "E01/E02/E11 retain terrain payload, collision and dynamic-geometry ownership; pass-table absence alone is not an absence proof.",
            "next_experiment": "Select one native trigger per retained unclassified authored signature, then capture outcome writers and overlay-qualified callbacks through denial/success and lifecycle controls.",
        },
        "source_dependencies": {
            "tools/dat_reloc.py": _sha256(ROOT / "tools/dat_reloc.py"),
            "src_re/prop_decor_catalog.c": _sha256(ROOT / "src_re/prop_decor_catalog.c"),
            "src_re/pass3_backdrop_cull_80014360.c": _sha256(
                ROOT / "src_re/pass3_backdrop_cull_80014360.c"),
        },
        "run_provenance": provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[props-movers] retained active E08 campaign evidence: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_props_movers.py",
                       anchor={"type": "aborted before retained E08 evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned E08 instance cleanup also failed: {cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
