#!/usr/bin/env python3
"""Regenerate the Phase-4 E06 contact/object-pool campaign.

The generator joins the complete pristine type-0x3f authored-source catalog to
the resident allocator/walker/dispatch frontier, then reproduces pool ownership
and failure behavior in a fresh isolated external-debugger instance.  The final
live control intentionally fills every allocator slot and invokes the retail
no-escape search; it is therefore always last and the owned process is stopped
by ``finish_run`` rather than reused.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    from build_identity import verify_staged_input
    import catalog_type3f
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
    import phase4_berry_throw as berry
except ModuleNotFoundError:  # imported as tools.phase4_contact_pool in tests
    from tools.build_identity import verify_staged_input
    from tools import catalog_type3f
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        select_pristine_save_anchors, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
    from tools import phase4_berry_throw as berry


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_contact_pool.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

POOL_BASE = 0x800B0D18
POOL_STRIDE = 0x38
POOL_CAPACITY = 64
POOL_CURSOR = 0x8008234C
PLAYER_BASE = 0x800A6500
TYPE3F_POINTER = 0x80096E9C
DESCRIPTOR_POINTERS = 0x80096B98
DESCRIPTOR_COUNT = 50
DESCRIPTOR_SIZE = 0x0C
METADATA_B = 0x8007941C
METADATA_A = 0x80079E30
METADATA_ROWS = 129
METADATA_STRIDE = 0x14
SOURCE_DISPATCH_TABLE = 0x8001B42C
SOURCE_DISPATCH_COUNT = 34
RECORD_DISPATCH_TABLE = 0x8001B570
RECORD_DISPATCH_COUNT = 117
ALLOCATOR = 0x80059E44
WALKER = 0x800586B0
SETTLE_FRAMES = 2
CONTROL_SAVE = "level01.sav"
PROJECTILE_SAVE = "red_berry_thrown.sav"

REGIONS = {
    "post_init": (0x80024DDC, 0x80024E04),
    "pickup_projector": (0x800253E8, 0x80025F54),
    "type3f_construct_and_action": (0x80053814, 0x80054810),
    "pickup_action_tail": (0x80054278, 0x80054810),
    "grain_action": (0x80054EAC, 0x80055188),
    "checkpoint_construct": (0x80057620, 0x80057704),
    "contact_walker": (0x800586B0, 0x80058AF8),
    "render_attr_decode": (0x800593E8, 0x8005953C),
    "contact_allocator": (0x80059E44, 0x8005A0E0),
    "contact_object_spawn": (0x8005A0E0, 0x8005A308),
    "projectile_update": (0x8005A308, 0x8005B12C),
}

EXPECTED_WORDS = {
    "source_entry": (0x80053814, 0x27BDFF28),
    "source_record_pointer": (0x8005383C, 0x8CA56E9C),
    "source_dispatch_load": (0x80053CF4, 0x8C22B42C),
    "walker_entry": (0x800586B0, 0x27BDFF98),
    "walker_active_gate": (0x80058730, 0x86420000),
    "walker_dispatch_bound": (0x8005880C, 0x2C620075),
    "allocator_entry": (0x80059E44, 0x27BDFFD0),
    "allocator_fifth_argument": (0x80059E50, 0x8FA70040),
    "allocator_wrap_64": (0x80059E7C, 0x28420040),
    "allocator_occupied_mask": (0x80059EB8, 0x30420080),
    "allocator_active_read": (0x80059ECC, 0x84220D3A),
    "allocator_no_escape_backedge": (0x80059ED4, 0x1440FFE3),
    "allocator_post_init_call": (0x8005A0B4, 0x0C009377),
}

SOURCE_KIND_ROLES = {
    0x10: "FLIK letter F",
    0x11: "FLIK letter L",
    0x12: "FLIK letter I",
    0x13: "FLIK letter K",
    0x14: "grain",
    0x21: "green/homing berry marker",
    0x22: "gold berry marker",
    0x23: "blue/super berry marker",
    0x24: "purple/mega-homing berry marker",
    0x29: "seed-token lane 0",
    0x2A: "seed-token lane 1",
    0x2B: "seed-token lane 2",
    0x2C: "seed-token lane 3",
    0x2D: "seed-token lane 4",
    0x30: "checkpoint/trigger record",
    0x31: "alternate animated checkpoint/trigger record",
}
SOURCE_SUPPORTED_UNSTAGED = {0x20: "clear berry marker"}

SOURCE_TARGET_ROLES = {
    0x80053D04: "FLIK F action",
    0x80053E64: "FLIK L action",
    0x80053FC0: "FLIK I action",
    0x8005411C: "FLIK K action",
    0x80054278: "grain action",
    0x80054288: "clear berry marker action",
    0x80054298: "green/homing marker action",
    0x800542AC: "gold marker action",
    0x800542C0: "blue/super marker action",
    0x800542D4: "purple/mega marker action",
    0x800542F4: "seed-token lane 0 action",
    0x8005433C: "seed-token lane 1 action",
    0x800543B8: "seed-token lane 2 action",
    0x80054434: "seed-token lane 3 action",
    0x800544D0: "seed-token lane 4 action",
    0x80054554: "checkpoint action",
    0x800545A0: "alternate checkpoint action",
    0x800545CC: "default/no authored action",
}


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


def _table(exe: bytes, address: int, count: int) -> list[int]:
    return list(struct.unpack_from(f"<{count}I", exe, _va_offset(address)))


def _metadata_row(index: int, data: bytes) -> dict[str, Any]:
    return {
        "index": index,
        "raw_hex": data.hex(),
        "action_id": struct.unpack_from("<H", data, 0)[0],
        "lifetime_or_active_initial": struct.unpack_from("<H", data, 2)[0],
        "variant_initial": struct.unpack_from("<h", data, 4)[0],
        "field_31": data[6], "field_30": data[7],
        "radius_add": struct.unpack_from("<H", data, 8)[0],
        "field_2a": struct.unpack_from("<H", data, 0x0A)[0],
        "state_initial": struct.unpack_from("<H", data, 0x0C)[0],
        "orientation_mode": struct.unpack_from("<b", data, 0x0E)[0],
        "field_2f": data[0x0F], "flags": data[0x10],
        "field_34": data[0x11], "field_35": data[0x12],
        "field_36": data[0x13],
    }


def _dispatch_table(exe: bytes, address: int, count: int,
                    index_bias: int) -> dict[str, Any]:
    targets = _table(exe, address, count)
    groups: dict[str, list[int]] = {}
    for index, target in enumerate(targets):
        groups.setdefault(f"0x{target:08X}", []).append(index + index_bias)
    return {
        "address": f"0x{address:08X}", "entries": count,
        "index_bias": index_bias,
        "targets": [f"0x{target:08X}" for target in targets],
        "target_groups": groups,
        "sha256": _sha256_bytes(struct.pack(f"<{count}I", *targets)),
    }


def _source_catalog() -> dict[str, Any]:
    files, rows, file_rows = [], [], []
    for path in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.DAT")):
        rel = path.relative_to(ROOT / "REBUILD/files").as_posix()
        data = path.read_bytes()
        verify_staged_input(rel, data)
        summary = catalog_type3f.analyze_file(path)
        files.append({
            "path": f"REBUILD/files/{rel}", "size": len(data),
            "sha256": _sha256_bytes(data),
            "type3f_offsets": summary.type3f_offsets,
            "type3f_counts": summary.type3f_counts,
            "entries": len(summary.rows), "warnings": summary.warnings,
        })
        for row in summary.rows:
            item = asdict(row)
            item["file"] = f"REBUILD/files/{rel}"
            rows.append(item)
            file_rows.append((rel, row.source_kind))
    histogram = Counter(row[1] for row in file_rows)
    by_kind_files = {
        str(kind): sorted({rel for rel, value in file_rows if value == kind})
        for kind in sorted(histogram)
    }
    authored = sorted(histogram)
    classifications = []
    for kind in range(DESCRIPTOR_COUNT):
        if kind in SOURCE_KIND_ROLES and kind in histogram:
            status, role = "pristine_authored_source_kind", SOURCE_KIND_ROLES[kind]
        elif kind in SOURCE_SUPPORTED_UNSTAGED:
            status, role = "dispatch_supported_but_unstaged", SOURCE_SUPPORTED_UNSTAGED[kind]
        else:
            status, role = "descriptor_index_not_authored_as_type3f_source", (
                "not a missing source-kind role; constructor/render consumers have separate owners")
        classifications.append({"index": kind, "status": status, "role": role})
    return {
        "files": files, "files_scanned": len(files),
        "files_with_type3f": sum(bool(row["type3f_counts"]) for row in files),
        "entries": rows, "entry_count": len(rows),
        "authored_kind_histogram": {str(k): histogram[k] for k in authored},
        "authored_kind_files": by_kind_files,
        "authored_kinds": authored,
        "authored_kind_count": len(authored),
        "descriptor_index_classification": classifications,
        "classification_counts": dict(Counter(
            row["status"] for row in classifications)),
    }


def _encoded_allocator_calls(exe: bytes) -> dict[str, Any]:
    jal_word = 0x0C016791
    functions_doc = json.loads((ROOT / "analysis/functions.json").read_text())
    functions = functions_doc["functions"]
    resident = []
    for offset in range(EXE_HEADER, len(exe) - 3, 4):
        if struct.unpack_from("<I", exe, offset)[0] != jal_word:
            continue
        address = EXE_BASE + offset - EXE_HEADER
        owner = next((row for row in functions
                      if row.get("space") == "resident"
                      and int(row["start"], 16) <= address < int(row["end"], 16)), None)
        resident.append({
            "call_pc": f"0x{address:08X}",
            "owner_start": owner.get("start") if owner else None,
            "owner_end": owner.get("end") if owner else None,
            "owner_name": owner.get("name") if owner else None,
        })
    overlays = []
    binaries = []
    for path in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.BIN")):
        rel = path.relative_to(ROOT / "REBUILD/files").as_posix()
        data = path.read_bytes()
        verify_staged_input(rel, data)
        hits = [offset for offset in range(0, len(data) - 3, 4)
                if struct.unpack_from("<I", data, offset)[0] == jal_word]
        binaries.append({"path": f"REBUILD/files/{rel}", "size": len(data),
                         "sha256": _sha256_bytes(data), "hit_offsets": hits})
        overlays.extend({"path": f"REBUILD/files/{rel}", "file_offset": offset}
                        for offset in hits)
    return {
        "jal_word": f"0x{jal_word:08X}",
        "resident": resident, "resident_count": len(resident),
        "overlay_encoded_hits": overlays, "overlay_encoded_hit_count": len(overlays),
        "pinned_overlay_binaries": binaries,
        "scope": "all aligned direct JAL encodings in the pinned retail EXE and staged LEVEL*.BIN inputs",
    }


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    if exe is None:
        exe = EXE_PATH.read_bytes()
    verify_staged_input(EXE_REL, exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine contact-pool word mismatch at 0x{address:08X}: "
                f"actual=0x{actual:08X} expected=0x{expected:08X}")
        words[name] = {"address": f"0x{address:08X}",
                       "word": f"0x{actual:08X}"}
    regions = {}
    for name, bounds in REGIONS.items():
        data = _region(exe, bounds)
        regions[name] = {
            "start": f"0x{bounds[0]:08X}",
            "end_exclusive": f"0x{bounds[1]:08X}",
            "length": len(data), "sha256": _sha256_bytes(data),
        }
    metadata_b = []
    for index in range(METADATA_ROWS):
        start = _va_offset(METADATA_B + index * METADATA_STRIDE)
        metadata_b.append(_metadata_row(index, exe[start:start + METADATA_STRIDE]))
    metadata_a_bytes = _region(
        exe, (METADATA_A, METADATA_A + METADATA_ROWS * METADATA_STRIDE))
    source_dispatch = _dispatch_table(
        exe, SOURCE_DISPATCH_TABLE, SOURCE_DISPATCH_COUNT, 0x10)
    source_dispatch["role_by_target"] = {
        f"0x{target:08X}": role for target, role in SOURCE_TARGET_ROLES.items()}
    record_dispatch = _dispatch_table(
        exe, RECORD_DISPATCH_TABLE, RECORD_DISPATCH_COUNT, 2)
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
                       "sha256": _sha256_bytes(exe)},
        "instruction_words": words, "regions": regions,
        "metadata_b": {
            "address": f"0x{METADATA_B:08X}", "stride": METADATA_STRIDE,
            "rows": metadata_b, "row_count": len(metadata_b),
            "action_id_domain": sorted({row["action_id"] for row in metadata_b}),
            "sha256": _sha256_bytes(b"".join(
                bytes.fromhex(row["raw_hex"]) for row in metadata_b)),
        },
        "metadata_a": {
            "address": f"0x{METADATA_A:08X}", "stride": METADATA_STRIDE,
            "rows_retained": METADATA_ROWS, "sha256": _sha256_bytes(metadata_a_bytes),
        },
        "source_dispatch": source_dispatch,
        "record_dispatch": record_dispatch,
        "source_catalog": _source_catalog(),
        "allocator_call_census": _encoded_allocator_calls(exe),
        "typed_contract": {
            "pool": {"base": f"0x{POOL_BASE:08X}", "stride": POOL_STRIDE,
                     "capacity": POOL_CAPACITY, "cursor": f"0x{POOL_CURSOR:08X}"},
            "allocation": {
                "cursor_order": "preincrement_then_wrap_at_64",
                "free_predicate": "not(flags & 0x80) or field_22 == 0",
                "full_pool_escape": None,
                "metadata_b_index": "fourth ABI argument ctor_type",
                "metadata_a_index": "fifth ABI argument at caller sp+0x10",
            },
            "walk_gate": "signed field_22 > 0 and flags & 0x02",
            "field_22_ownership": (
                "type-specific: projectile subclasses decrement it as TTL; "
                "contact-proximity subclasses use it as an active/contact gate"),
            "source_kind_domain": [0x10, 0x31],
            "source_default_target": "0x800545CC",
            "descriptor_indices": DESCRIPTOR_COUNT,
        },
    }


def static_census_gaps(doc: dict[str, Any]) -> list[str]:
    gaps = []
    catalog = doc["source_catalog"]
    if catalog["files_scanned"] != 21 or catalog["files_with_type3f"] != 19:
        gaps.append("staged type3f catalog is not exactly 21 files / 19 populated")
    if catalog["entry_count"] != 1058 or catalog["authored_kind_count"] != 16:
        gaps.append("authored type3f entry/kind census drifted")
    if catalog["authored_kinds"] != sorted(SOURCE_KIND_ROLES):
        gaps.append("pristine-authored source kind domain is incomplete or changed")
    counts = catalog["classification_counts"]
    if counts != {"descriptor_index_not_authored_as_type3f_source": 33,
                  "pristine_authored_source_kind": 16,
                  "dispatch_supported_but_unstaged": 1}:
        gaps.append("50 descriptor indices were not exhaustively classified")
    source = doc["source_dispatch"]
    if source["entries"] != 34 or len(source["target_groups"]) != 18 or \
            source["target_groups"].get("0x800545CC") != [
                0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C,
                0x1D, 0x1E, 0x1F, 0x25, 0x26, 0x27, 0x28, 0x2E, 0x2F]:
        gaps.append("source action dispatch table is incomplete")
    if doc["record_dispatch"]["entries"] != 117 or \
            len(doc["record_dispatch"]["target_groups"]) != 15:
        gaps.append("record walker dispatch table is incomplete")
    calls = doc["allocator_call_census"]
    if calls["resident_count"] != 76 or any(
            row["owner_start"] is None for row in calls["resident"]):
        gaps.append("resident direct allocator caller census is incomplete")
    contract = doc["typed_contract"]
    if contract["pool"]["capacity"] != 64 or \
            contract["allocation"]["full_pool_escape"] is not None:
        gaps.append("allocator capacity/failure contract drifted")
    if doc["metadata_b"]["row_count"] != 129:
        gaps.append("metadata B table is incomplete")
    return gaps


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


def _read_u32(client: Any, address: int) -> int:
    return struct.unpack("<I", _read_memory(client, address, 4))[0]


def _read_s32(client: Any, address: int) -> int:
    return struct.unpack("<i", _read_memory(client, address, 4))[0]


def _checked_write(client: Any, method: str, address: int, value: int) -> dict:
    row = client.call(method, {"address": f"0x{address:08X}",
                               "value": value & 0xFFFFFFFF})
    sizes = {"debugger.writeU8": 1, "debugger.writeU16": 2,
             "debugger.writeU32": 4}
    if row.get("written") != sizes[method]:
        raise SystemExit(f"short debugger write: {method} {row}")
    return row


def _load_anchor(client: Any, save: str) -> dict:
    client.call("emulator.clearControllerState", {"port": 0})
    loaded = client.call("emulator.loadState", {
        "path": str((ROOT / save).resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    if loaded.get("loaded") is not True:
        raise SystemExit(f"failed to load {save}: {loaded}")
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": SETTLE_FRAMES})
    return loaded


def _record_from_data(slot: int, data: bytes) -> dict[str, Any]:
    return {
        "slot": slot, "pointer": f"0x{POOL_BASE + slot * POOL_STRIDE:08X}",
        "position": list(struct.unpack_from("<iii", data, 0)),
        "velocity_or_render_attrs": list(struct.unpack_from("<iiii", data, 0x0C)),
        "action_id": struct.unpack_from("<H", data, 0x20)[0],
        "lifetime_ttl_or_active_gate": struct.unpack_from("<H", data, 0x22)[0],
        "variant": struct.unpack_from("<h", data, 0x24)[0],
        "secondary_counter": struct.unpack_from("<H", data, 0x26)[0],
        "radius_add": struct.unpack_from("<H", data, 0x28)[0],
        "field_2a": struct.unpack_from("<H", data, 0x2A)[0],
        "state": struct.unpack_from("<H", data, 0x2C)[0],
        "orientation": struct.unpack_from("<b", data, 0x2E)[0],
        "field_2f": data[0x2F], "field_30": data[0x30],
        "field_31": data[0x31], "field_32": data[0x32],
        "flags": data[0x33], "field_34": data[0x34],
        "field_35": data[0x35], "field_36": data[0x36],
        "post_init_state": data[0x37], "raw_hex": data.hex(),
    }


def _pool_snapshot(client: Any) -> dict[str, Any]:
    data = _read_memory(client, POOL_BASE, POOL_CAPACITY * POOL_STRIDE)
    records = [_record_from_data(slot, data[slot * POOL_STRIDE:(slot + 1) * POOL_STRIDE])
               for slot in range(POOL_CAPACITY)]
    live = [row["slot"] for row in records
            if row["lifetime_ttl_or_active_gate"] > 0 and row["flags"] & 0x02]
    occupied = [row["slot"] for row in records
                if row["lifetime_ttl_or_active_gate"] != 0 and row["flags"] & 0x80]
    return {"base": f"0x{POOL_BASE:08X}", "stride": POOL_STRIDE,
            "capacity": POOL_CAPACITY, "cursor": _read_u32(client, POOL_CURSOR),
            "sha256": _sha256_bytes(data), "live_slots": live,
            "allocator_occupied_slots": occupied, "records": records}


def _type3f_snapshot(client: Any) -> dict[str, Any]:
    pointer = _read_u32(client, TYPE3F_POINTER)
    if not 0x80010000 <= pointer < 0x80200000:
        raise SystemExit(f"invalid type3f pointer 0x{pointer:08X}")
    count = struct.unpack("<H", _read_memory(client, pointer, 2))[0]
    if not 0 < count <= 4096:
        raise SystemExit(f"invalid live type3f count {count}")
    data = _read_memory(client, pointer, 4 + count * 0x10)
    rows = []
    for index in range(count):
        start = 4 + index * 0x10
        x, y, z = struct.unpack_from("<iii", data, start)
        rows.append({"index": index, "x": x, "y": y, "z": z,
                     "kind": data[start + 0x0C], "status": data[start + 0x0D],
                     "rest_y": struct.unpack_from("<h", data, start + 0x0E)[0]})
    return {"pointer": f"0x{pointer:08X}", "count": count,
            "sha256": _sha256_bytes(data), "rows": rows,
            "kind_histogram": {str(k): v for k, v in sorted(Counter(
                row["kind"] for row in rows).items())}}


def _descriptor_snapshot(client: Any) -> dict[str, Any]:
    raw = _read_memory(client, DESCRIPTOR_POINTERS, DESCRIPTOR_COUNT * 4)
    pointers = struct.unpack(f"<{DESCRIPTOR_COUNT}I", raw)
    rows = []
    for index, pointer in enumerate(pointers):
        if pointer == 0:
            target = b""
        elif 0x80010000 <= pointer < 0x80200000:
            target = _read_memory(client, pointer, DESCRIPTOR_SIZE)
        else:
            raise SystemExit(f"descriptor {index} has invalid pointer 0x{pointer:08X}")
        rows.append({"index": index, "pointer": f"0x{pointer:08X}",
                     "target_hex": target.hex(),
                     "target_sha256": _sha256_bytes(target)})
    return {"table_sha256": _sha256_bytes(raw), "rows": rows,
            "nonzero_pointers": sum(pointer != 0 for pointer in pointers)}


def _run_breadth(client: Any, anchors: list[tuple[str, str]]) -> dict[str, Any]:
    rows = {}
    for label, save in anchors:
        loaded = _load_anchor(client, save)
        rows[label] = {"save": save, "load": loaded,
                       "type3f": _type3f_snapshot(client),
                       "descriptors": _descriptor_snapshot(client),
                       "pool": _pool_snapshot(client)}
    authored_live = sorted({kind for row in rows.values()
                            for kind in map(int, row["type3f"]["kind_histogram"])})
    summary = {
        "anchors": len(rows),
        "type3f_counts": {label: row["type3f"]["count"] for label, row in rows.items()},
        "distinct_type3f_hashes": sorted({row["type3f"]["sha256"] for row in rows.values()}),
        "distinct_descriptor_table_hashes": sorted({
            row["descriptors"]["table_sha256"] for row in rows.values()}),
        "authored_live_kinds": authored_live,
        "allocator_occupied_min": min(len(row["pool"]["allocator_occupied_slots"])
                                      for row in rows.values()),
        "allocator_occupied_max": max(len(row["pool"]["allocator_occupied_slots"])
                                      for row in rows.values()),
        "pool_headroom_min": POOL_CAPACITY - max(
            len(row["pool"]["allocator_occupied_slots"]) for row in rows.values()),
    }
    if summary["anchors"] != 19 or summary["authored_live_kinds"] != sorted(SOURCE_KIND_ROLES):
        raise SystemExit(f"contact-pool gameplay breadth drifted: {summary}")
    if summary["pool_headroom_min"] <= 0:
        raise SystemExit(f"pristine breadth exhausted the contact pool: {summary}")
    return {"anchors": rows, "summary": summary}


def _stack_argument(client: Any, value: int) -> dict:
    registers = client.call("debugger.getRegisters", {})["registers"]
    return _checked_write(client, "debugger.writeU32", registers["sp"] + 0x10, value)


def _call_allocator(client: Any, ctor_type: int, stack_arg: int,
                    xyz: tuple[int, int, int]) -> tuple[dict, dict]:
    stack_write = _stack_argument(client, stack_arg)
    result = client.call("debugger.callFunction", {
        "address": f"0x{ALLOCATOR:08X}",
        "a0": xyz[0] & 0xFFFFFFFF, "a1": xyz[1] & 0xFFFFFFFF,
        "a2": xyz[2] & 0xFFFFFFFF, "a3": ctor_type,
        "timeout": 10000}, timeout=30)
    pointer = result["v0"]
    if not POOL_BASE <= pointer < POOL_BASE + POOL_CAPACITY * POOL_STRIDE or \
            (pointer - POOL_BASE) % POOL_STRIDE:
        raise SystemExit(f"allocator returned invalid pointer 0x{pointer:08X}")
    slot = (pointer - POOL_BASE) // POOL_STRIDE
    record = _record_from_data(slot, _read_memory(client, pointer, POOL_STRIDE))
    return {"stack_argument_write": stack_write, "call": result}, record


def _player_xyz(client: Any) -> tuple[int, int, int]:
    return tuple(_read_s32(client, PLAYER_BASE + offset) for offset in (0, 4, 8))


def _run_allocator_controls(client: Any) -> dict[str, Any]:
    trials = {}
    _load_anchor(client, CONTROL_SAVE)
    cursor = _read_u32(client, POOL_CURSOR)
    xyz = _player_xyz(client)
    call, record = _call_allocator(
        client, 0x51, 3, (xyz[0] + 0x100000, xyz[1] + 0x100000,
                         xyz[2] + 0x100000))
    trials["ordinary_free"] = {"cursor_before": cursor, "call": call, "record": record,
                               "cursor_after": _read_u32(client, POOL_CURSOR)}

    _load_anchor(client, CONTROL_SAVE)
    cursor = _read_u32(client, POOL_CURSOR)
    first, second = (cursor + 1) % 64, (cursor + 2) % 64
    writes = [
        _checked_write(client, "debugger.writeU16", POOL_BASE + first * POOL_STRIDE + 0x22, 1),
        _checked_write(client, "debugger.writeU8", POOL_BASE + first * POOL_STRIDE + 0x33, 0x80),
        _checked_write(client, "debugger.writeU16", POOL_BASE + second * POOL_STRIDE + 0x22, 0),
        _checked_write(client, "debugger.writeU8", POOL_BASE + second * POOL_STRIDE + 0x33, 0),
    ]
    call, record = _call_allocator(client, 0x51, 3, xyz)
    trials["occupied_skip"] = {"cursor_before": cursor, "occupied_slot": first,
                               "expected_selected_slot": second, "writes": writes,
                               "call": call, "record": record}

    _load_anchor(client, CONTROL_SAVE)
    cursor = _read_u32(client, POOL_CURSOR)
    first = (cursor + 1) % 64
    writes = [
        _checked_write(client, "debugger.writeU32", POOL_BASE + first * POOL_STRIDE, 0x12345678),
        _checked_write(client, "debugger.writeU16", POOL_BASE + first * POOL_STRIDE + 0x22, 0),
        _checked_write(client, "debugger.writeU8", POOL_BASE + first * POOL_STRIDE + 0x33, 0x80),
    ]
    call, record = _call_allocator(client, 0x51, 3, xyz)
    trials["dead_residue_reuse"] = {"cursor_before": cursor,
                                    "expected_selected_slot": first, "writes": writes,
                                    "call": call, "record": record}

    _load_anchor(client, CONTROL_SAVE)
    cursor_write = _checked_write(client, "debugger.writeU32", POOL_CURSOR, 63)
    call, record = _call_allocator(client, 0x51, 3, xyz)
    trials["wrap_63_to_0"] = {"cursor_write": cursor_write, "call": call,
                              "record": record, "cursor_after": _read_u32(client, POOL_CURSOR)}

    if trials["ordinary_free"]["record"]["slot"] != (trials["ordinary_free"]["cursor_before"] + 1) % 64 or \
            trials["occupied_skip"]["record"]["slot"] != second or \
            trials["dead_residue_reuse"]["record"]["slot"] != first or \
            trials["dead_residue_reuse"]["record"]["position"][0] == 0x12345678 or \
            trials["wrap_63_to_0"]["record"]["slot"] != 0 or \
            trials["wrap_63_to_0"]["cursor_after"] != 0:
        raise SystemExit(f"allocator positive/negative controls failed: {trials}")
    return trials


def _run_walker_controls(client: Any) -> dict[str, Any]:
    _load_anchor(client, CONTROL_SAVE)
    xyz = _player_xyz(client)
    far_call, far_before = _call_allocator(
        client, 0x51, 3, (xyz[0] + 0x2000, xyz[1] - 7360, xyz[2]))
    far_walker = client.call("debugger.callFunction", {
        "address": f"0x{WALKER:08X}", "timeout": 10000}, timeout=30)
    far_after = _record_from_data(
        far_before["slot"], _read_memory(client,
            POOL_BASE + far_before["slot"] * POOL_STRIDE, POOL_STRIDE))

    _load_anchor(client, CONTROL_SAVE)
    xyz = _player_xyz(client)
    near_call, near_before = _call_allocator(
        client, 0x51, 3, (xyz[0], xyz[1] - 7360, xyz[2]))
    near_walker = client.call("debugger.callFunction", {
        "address": f"0x{WALKER:08X}", "timeout": 10000}, timeout=30)
    near_after = _record_from_data(
        near_before["slot"], _read_memory(client,
            POOL_BASE + near_before["slot"] * POOL_STRIDE, POOL_STRIDE))

    # The retail walker squares signed 32-bit scaled deltas without an overflow
    # guard.  Keep the ordinary spatial negative inside the non-overflow domain,
    # and retain this deliberately invalid-coordinate trial separately so a MOD
    # cannot mistake "farther" for monotonically safer.
    _load_anchor(client, CONTROL_SAVE)
    xyz = _player_xyz(client)
    overflow_call, overflow_before = _call_allocator(
        client, 0x51, 3, (xyz[0] + 0x100000, xyz[1] + 0x100000,
                         xyz[2] + 0x100000))
    overflow_walker = client.call("debugger.callFunction", {
        "address": f"0x{WALKER:08X}", "timeout": 10000}, timeout=30)
    overflow_after = _record_from_data(
        overflow_before["slot"], _read_memory(client,
            POOL_BASE + overflow_before["slot"] * POOL_STRIDE, POOL_STRIDE))
    result = {
        "far_negative": {"allocator": far_call, "walker": far_walker,
                         "before": far_before, "after": far_after},
        "near_positive": {"allocator": near_call, "walker": near_walker,
                          "before": near_before, "after": near_after},
        "invalid_coordinate_overflow": {
            "allocator": overflow_call, "walker": overflow_walker,
            "delta_each_axis": 0x100000, "before": overflow_before,
            "after": overflow_after,
            "interpretation": "signed squared-distance overflow false-positive; outside pristine authored coordinate domain"},
    }
    comparable = ("lifetime_ttl_or_active_gate", "state", "flags")
    if any(far_before[key] != far_after[key] for key in comparable) or \
            near_before["action_id"] != 0x14 or \
            near_before["lifetime_ttl_or_active_gate"] != 200 or \
            near_after["lifetime_ttl_or_active_gate"] != 1 or \
            near_before["state"] != 22 or near_after["state"] != 16 or \
            overflow_before["lifetime_ttl_or_active_gate"] != 200 or \
            overflow_after["lifetime_ttl_or_active_gate"] != 1:
        raise SystemExit(f"walker distance/action controls failed: {result}")
    return result


def _run_scene_reuse(client: Any) -> dict[str, Any]:
    rows = []
    for save in ("level01.sav", "level02.sav", "level01.sav"):
        _load_anchor(client, save)
        rows.append({"save": save, "pool": _pool_snapshot(client),
                     "type3f": _type3f_snapshot(client),
                     "descriptors": _descriptor_snapshot(client)})
    result = {
        "sequence": rows,
        "level01_type3f_reloaded_equal": rows[0]["type3f"]["sha256"] == rows[2]["type3f"]["sha256"],
        "level01_descriptor_reloaded_equal": rows[0]["descriptors"]["table_sha256"] == rows[2]["descriptors"]["table_sha256"],
        "level01_level02_type3f_different": rows[0]["type3f"]["sha256"] != rows[1]["type3f"]["sha256"],
        "level01_pool_reloaded_equal": rows[0]["pool"]["sha256"] == rows[2]["pool"]["sha256"],
    }
    if not all(result[key] for key in (
            "level01_type3f_reloaded_equal", "level01_descriptor_reloaded_equal",
            "level01_level02_type3f_different", "level01_pool_reloaded_equal")):
        raise SystemExit(f"scene pool/source reuse failed: {result}")
    return result


def _run_full_capacity_last(client: Any) -> dict[str, Any]:
    _load_anchor(client, CONTROL_SAVE)
    before = _pool_snapshot(client)
    data = bytearray(_read_memory(client, POOL_BASE, POOL_CAPACITY * POOL_STRIDE))
    for slot in range(POOL_CAPACITY):
        struct.pack_into("<H", data, slot * POOL_STRIDE + 0x22, 1)
        data[slot * POOL_STRIDE + 0x33] |= 0x80
    write = client.call("debugger.writeMemory", {
        "address": f"0x{POOL_BASE:08X}", "hex": bytes(data).hex(),
        "invalidate_code": False})
    if write.get("written") != len(data):
        raise SystemExit(f"full-pool setup write was short: {write}")
    armed = _pool_snapshot(client)
    if len(armed["allocator_occupied_slots"]) != 64:
        raise SystemExit("full-pool setup did not satisfy the retail occupied predicate")
    stack_write = _stack_argument(client, 3)
    outcome: dict[str, Any]
    try:
        returned = client.call("debugger.callFunction", {
            "address": f"0x{ALLOCATOR:08X}", "a0": 0, "a1": 0,
            "a2": 0, "a3": 0x51, "timeout": 1000}, timeout=10)
        outcome = {"unexpected_return": returned}
    except Exception as exc:
        outcome = {"exception_type": type(exc).__name__, "message": str(exc),
                   "code": getattr(exc, "code", None),
                   "data": getattr(exc, "data", None)}
    if "unexpected_return" in outcome or not outcome.get("message"):
        raise SystemExit(f"full-pool allocator unexpectedly escaped: {outcome}")
    return {"before": before, "bulk_write": write, "armed": armed,
            "stack_argument_write": stack_write, "call_outcome": outcome,
            "control_order": "last live RPC by design; owned process stopped immediately after"}


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    gaps = static_census_gaps(static)
    if gaps:
        raise SystemExit(f"static contact-pool census failed: {gaps}")
    berry_static = berry.build_static_census()
    baseline = json.loads((ROOT / "analysis/phase2_stage_baseline.json").read_text())
    all_anchors, all_selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("strict-pristine contact anchors no longer cover 19 gameplay contexts")
    saves = [save for _label, save in anchors]
    accepted = all_selection["accepted"][:19]
    if PROJECTILE_SAVE not in saves:
        declaration = verify_declared_save_fixture(
            ROOT / PROJECTILE_SAVE, allowed_media_classes={"pristine"})
        accepted.append({"label": "contact_projectile_lifecycle",
                         "save": PROJECTILE_SAVE, **declaration})
        saves.append(PROJECTILE_SAVE)
    selection = {**all_selection, "accepted": accepted, "rejected": [],
                 "anchors_requested": len(accepted),
                 "anchors_accepted": len(accepted), "anchors_rejected": 0}

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.status", "debugger.getRegisters",
        "debugger.readMemory", "debugger.writeMemory", "debugger.writeU8",
        "debugger.writeU16", "debugger.writeU32", "debugger.callFunction",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "execTrace.addWatch", "execTrace.get",
        "execTrace.clear", "movie.load", "movie.store", "movie.branch",
        "movie.editFrame", "movie.activate", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status",
        "movie.remove", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks contact-pool methods: {missing}")

    cold_boot = berry._run_cold_boot(client, berry_static)
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]
    breadth = _run_breadth(client, anchors)
    allocator = _run_allocator_controls(client)
    walker = _run_walker_controls(client)
    projectile_retirement = berry._run_arc_and_lifecycle(client, berry_static)
    pause = berry._run_pause(client)
    death_respawn = berry._run_respawn(client)
    scene_reuse = _run_scene_reuse(client)
    full_capacity = _run_full_capacity_last(client)

    provenance = finish_run(
        args, generator="tools/phase4_contact_pool.py",
        anchor={
            "type": "cold-boot pool allocation plus strict-pristine all-stage source/descriptor/pool breadth and destructive capacity-last control",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["base_movie"],
            "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES,
            "cold_boot_edit": cold_boot["edit_recipe"],
            "direct_calls": "paused guest subroutines with fifth ABI argument at caller sp+0x10",
            "capacity_control": "all 64 occupied, 1000 ms callFunction guest timeout, last RPC",
        })
    document = {
        "_comment": (
            "Phase-4 E06 contact/object-pool evidence regenerated from pristine "
            "executable, staged DAT/BIN inputs and retail media. It separates "
            "50 descriptor indices from the 16 actually authored type3f kinds, "
            "pins complete dispatch/caller tables, and reproduces allocator, "
            "walker, projectile, lifecycle and full-capacity behavior."),
        "generated": date.today().isoformat(), "static_census": static,
        "live": {
            "cold_boot": cold_boot, "breadth": breadth,
            "allocator_controls": allocator, "walker_controls": walker,
            "projectile_retirement": projectile_retirement,
            "pause_resume": pause, "death_respawn": death_respawn,
            "scene_reuse": scene_reuse, "full_capacity_last": full_capacity,
        },
        "source_dependencies": {
            "tools/catalog_type3f.py": _sha256(ROOT / "tools/catalog_type3f.py"),
            "tools/phase4_berry_throw.py": _sha256(ROOT / "tools/phase4_berry_throw.py"),
            "src_re/source3f_dispatch_80053814.c": _sha256(ROOT / "src_re/source3f_dispatch_80053814.c"),
            "src_re/contact_alloc_80059e44.c": _sha256(ROOT / "src_re/contact_alloc_80059e44.c"),
            "src_re/contact_walker_800586b0.c": _sha256(ROOT / "src_re/contact_walker_800586b0.c"),
        },
        "run_provenance": provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[contact-pool] retained E06 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_contact_pool.py",
                       anchor={"type": "aborted before retained contact-pool evidence"},
                       timing={})
        except BaseException as cleanup_error:
            print(f"owned contact-pool instance cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
