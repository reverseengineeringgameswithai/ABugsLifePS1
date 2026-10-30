#!/usr/bin/env python3
"""Regenerate the Phase-4 E07 event/mover-VM campaign.

The retained artifact joins a hash-pinned complete resident bytecode decode to
every pristine level overlay and to isolated retail-media runtime controls.  It
does not infer a fixed meaning for Region A: each overlay/target intersection is
classified independently, and runtime rows record the scene-qualified image.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any

try:
    from build_identity import load_baselines, verify_staged_input
    import gen_vm_disasm
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_event_vm
    from tools.build_identity import load_baselines, verify_staged_input
    from tools import gen_vm_disasm
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, select_pristine_save_anchors,
        verified_media_identity, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_event_vm.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FUNCTIONS = ROOT / "analysis/functions.json"
OVERLAY_MAP = ROOT / "analysis/phase3_overlay_map.json"
BASELINE = ROOT / "analysis/phase2_stage_baseline.json"
BASE_MOVIE = "movies/go_to_end/LEVEL01.movie.json"

EXE_HEADER = 0x800
EXE_BASE = 0x80010000
INTERPRETER = 0x8004C13C
FETCH_PC = 0x8004C1F4
SELECTOR_ROUTINE = 0x80049C30
SELECTOR_LOAD = 0x80049C78
PROGRAM_TABLE = 0x80077AF8
PROGRAM_MIN = 0x8007745C
PROGRAM_MAX = 0x80077AF8
CALL_STUBS = [0x8004C5D4 + index * 0x10 for index in range(9)]
OVERLAY_CALL_TARGETS = [0x800B3D78, 0x800B3B70, 0x800B3BD4,
                        0x800B3DC8, 0x800B3F00]
REGION_A = 0x800B39A0

ACTOR_BASE = 0x8009FD80
ACTOR_STRIDE = 0x84
ACTOR_CAPACITY = 64
SCENE_WORD = 0x80082504
PAUSE_FLAG = 0x8008224E
PLAYER_BASE = 0x800A6500
SCRATCH_ACTOR = 0x1F800000
SCRATCH_SOURCE = 0x1F800100
SETTLE_FRAMES = 2
TRACE_FRAMES = 12
MOVIE_TRACE_START = 8550
MOVIE_TRACE_END = 8620

EXPECTED_WORDS = {
    "interpreter_entry": (0x8004C13C, 0x27BDFF50),
    "actor_source_load": (0x8004C178, 0x8E150080),
    "actor_ip_load": (0x8004C17C, 0x8E110070),
    "opcode_fetch": (0x8004C1EC, 0x96220000),
    "opcode_domain_check": (0x8004C200, 0x2C62001A),
    "opcode_table_load": (0x8004C218, 0x8C22B2F4),
    "selector_byte_load": (0x80049C78, 0x9122000D),
    "selector_scale": (0x80049C80, 0x00021080),
    "selector_table_load": (0x80049C8C, 0x8C227AF8),
    "actor_ip_store": (0x80049C94, 0xAD020070),
    "actor_pool_high": (0x8004D248, 0x3C12800A),
    "actor_pool_low": (0x8004D24C, 0x2652FD80),
    "actor_pool_stride": (0x8004D410, 0x26520084),
    "actor_pool_capacity": (0x8004D41C, 0x2A820040),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _word(exe: bytes, address: int) -> int:
    return struct.unpack_from("<I", exe, EXE_HEADER + address - EXE_BASE)[0]


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


def _write_memory(client: Any, address: int, data: bytes) -> dict[str, Any]:
    row = client.call("debugger.writeMemory", {
        "address": f"0x{address:08X}", "hex": data.hex()})
    if row.get("written") != len(data):
        raise SystemExit(f"short debugger write at 0x{address:08X}: {row}")
    return row


def _checked_write(client: Any, method: str, address: int, value: int) -> dict[str, Any]:
    row = client.call(method, {"address": f"0x{address:08X}", "value": value})
    expected = {"debugger.writeU8": 1, "debugger.writeU16": 2,
                "debugger.writeU32": 4}[method]
    if row.get("written") != expected:
        raise SystemExit(f"short debugger scalar write: {row}")
    return row


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


def _program_for_ip(vm: dict[str, Any], ip: int) -> dict[str, Any] | None:
    for program in vm["programs"]:
        if int(program["entry"], 16) <= ip < int(program["end"], 16):
            return {"id": program["id"], "entry": program["entry"],
                    "selectors": program["selectors"]}
    return None


def _actor_snapshot(client: Any, vm: dict[str, Any]) -> dict[str, Any]:
    raw = _read_memory(client, ACTOR_BASE, ACTOR_CAPACITY * ACTOR_STRIDE)
    records = []
    for slot in range(ACTOR_CAPACITY):
        row = raw[slot * ACTOR_STRIDE:(slot + 1) * ACTOR_STRIDE]
        actor_id = struct.unpack_from("<I", row, 0)[0]
        if actor_id == 0:
            continue
        source = struct.unpack_from("<I", row, 0x80)[0]
        ip = struct.unpack_from("<I", row, 0x70)[0]
        source_row: dict[str, Any]
        if 0x80010000 <= source <= 0x801FFFF0:
            source_data = _read_memory(client, source, 0x14)
            source_row = {
                "valid": True, "selector": source_data[0x0D],
                "kind": source_data[0x0C],
                "sha256": _sha256_bytes(source_data),
            }
        else:
            source_row = {"valid": False, "selector": None, "kind": None}
        records.append({
            "slot": slot, "address": f"0x{ACTOR_BASE + slot * ACTOR_STRIDE:08X}",
            "id": actor_id,
            "position": list(struct.unpack_from("<iii", row, 4)),
            "flags": struct.unpack_from("<H", row, 0x5C)[0],
            "wait": struct.unpack_from("<h", row, 0x60)[0],
            "ip": f"0x{ip:08X}", "program": _program_for_ip(vm, ip),
            "source_pointer": f"0x{source:08X}", "source": source_row,
        })
    selectors = [row["source"]["selector"] for row in records
                 if row["source"]["valid"]]
    return {
        "base": f"0x{ACTOR_BASE:08X}", "stride": ACTOR_STRIDE,
        "capacity": ACTOR_CAPACITY, "live_count": len(records),
        "raw_sha256": _sha256_bytes(raw), "records": records,
        "selector_histogram": {str(key): value for key, value in sorted(
            Counter(selectors).items())},
        "invalid_source_slots": [row["slot"] for row in records
                                 if not row["source"]["valid"]],
    }


def _trace_get(client: Any, watch: dict[str, Any], limit: int = 10000) -> dict[str, Any]:
    return client.call("execTrace.get", {
        "watch_id": watch["watch_id"], "offset": 0, "limit": limit})


def _trace_vm(client: Any, frames: int = TRACE_FRAMES) -> dict[str, Any]:
    client.call("execTrace.clear", {})
    fetch = client.call("execTrace.addWatch", {
        "pc": f"0x{FETCH_PC:08X}", "capture": ["v0", "s0", "s1", "s3"],
        "label": "vm_fetch", "max_events": 10000})
    calls = [client.call("execTrace.addWatch", {
        "pc": f"0x{pc:08X}", "capture": ["s0", "s1", "a0", "ra"],
        "label": f"call_slot_{slot}", "max_events": 256})
        for slot, pc in enumerate(CALL_STUBS, 1)]
    client.call("execTrace.run", {"frames": frames})
    fetch_rows = _trace_get(client, fetch)
    call_rows = {str(slot): _trace_get(client, watch, 256)
                 for slot, watch in enumerate(calls, 1)}
    client.call("execTrace.clear", {})
    opcodes = Counter()
    examples = {}
    invalid = []
    for event in fetch_rows["events"]:
        raw = int(event["regs"]["v0"], 16) & 0xFFFF
        signed = raw - 0x10000 if raw >= 0x8000 else raw
        index = signed + 1
        if not 0 <= index < 26:
            invalid.append({"raw": raw, "index": index, "event": event})
            continue
        opcodes[index] += 1
        examples.setdefault(str(index), event)
    if fetch_rows.get("truncated") or invalid:
        raise SystemExit(f"VM fetch trace overflow/invalid opcode: {fetch_rows} {invalid}")
    for slot, rows in call_rows.items():
        if rows.get("truncated"):
            raise SystemExit(f"VM CALL trace overflow in slot {slot}")
    return {
        "frames": frames, "fetch_watch": fetch,
        "fetch_total": fetch_rows["total"],
        "opcode_histogram": {str(key): value for key, value in sorted(opcodes.items())},
        "opcode_first_examples": examples,
        "call_slot_hits": {slot: rows["total"] for slot, rows in call_rows.items()},
        "call_first_examples": {slot: rows["events"][:1]
                                for slot, rows in call_rows.items() if rows["events"]},
        "truncated": False,
    }


def _overlay_path(name: str) -> tuple[str, Path]:
    match = re.fullmatch(r"LEVEL(\d{2})_(LEVEL1?)\.BIN", name)
    if not match:
        raise ValueError(name)
    rel = f"LEVEL{match.group(1)}/{match.group(2)}.BIN"
    return rel, ROOT / "REBUILD/files" / rel


def _overlay_runtime_identity(client: Any, scene: int,
                              overlays: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for name, row in overlays.items():
        if row["stub"] or scene not in row["scenes"]:
            continue
        runtime = _read_memory(client, REGION_A, row["size"])
        entry_runtime = _read_memory(
            client, REGION_A + 4, row["entry_code_length"])
        exact_targets = []
        for target in row["call_targets"]:
            if not target["exact_function_start"]:
                continue
            address = int(target["target"], 16)
            sample = _read_memory(client, address, target["sample_length"])
            exact_targets.append({
                "target": target["target"],
                "expected_sha256": target["sample_sha256"],
                "runtime_sha256": _sha256_bytes(sample),
                "matches": _sha256_bytes(sample) == target["sample_sha256"],
            })
        candidates.append({
            "overlay": name, "expected_sha256": row["sha256"],
            "runtime_sha256": _sha256_bytes(runtime),
            "matches": _sha256_bytes(runtime) == row["sha256"],
            "entry_code_expected_sha256": row["entry_code_sha256"],
            "entry_code_runtime_sha256": _sha256_bytes(entry_runtime),
            "entry_code_matches": _sha256_bytes(entry_runtime) == row["entry_code_sha256"],
            "exact_call_targets": exact_targets,
        })
    return {"scene": scene, "candidates": candidates,
            "exact_matches": [row["overlay"] for row in candidates if row["matches"]],
            "entry_code_matches": [row["overlay"] for row in candidates
                                   if row["entry_code_matches"]],
            "exact_call_target_matches": [
                {"overlay": row["overlay"], "target": target["target"]}
                for row in candidates for target in row["exact_call_targets"]
                if target["matches"]
            ]}


def _overlay_census(functions: dict[str, Any], overlay_map: dict[str, Any]) -> dict[str, Any]:
    baselines = load_baselines()
    function_index: dict[tuple[str, int], dict[str, Any]] = {}
    for row in functions["functions"]:
        if row.get("space") == "overlay":
            function_index[(row.get("overlay"), int(row["start"], 16))] = row
    rows = {}
    for rel, pin in sorted(baselines["staged_inputs"].items()):
        match = re.fullmatch(r"LEVEL(\d{2})/(LEVEL1?)\.BIN", rel)
        if not match:
            continue
        name = f"LEVEL{match.group(1)}_{match.group(2)}.BIN"
        path = ROOT / "REBUILD/files" / rel
        data = path.read_bytes()
        verify_staged_input(rel, data)
        map_row = (overlay_map.get("map") or {}).get(name, {})
        tag = name[:-4]
        targets = []
        for target in OVERLAY_CALL_TARGETS:
            offset = target - REGION_A
            exact = function_index.get((tag, target))
            in_image = 0 <= offset < len(data)
            sample = data[offset:min(offset + 32, len(data))] if in_image else b""
            targets.append({
                "target": f"0x{target:08X}", "in_image": in_image,
                "sample_length": len(sample),
                "sample_sha256": _sha256_bytes(sample) if sample else None,
                "exact_function_start": exact is not None,
                "function": ({key: exact.get(key) for key in (
                    "name", "start", "end", "confidence", "classification")}
                    if exact else None),
            })
        rows[name] = {
            "rel": f"REBUILD/files/{rel}", "size": len(data),
            "sha256": _sha256_bytes(data), "stub": len(data) <= 4,
            "entry_code_length": min(max(len(data) - 4, 0), 64),
            "entry_code_sha256": (_sha256_bytes(data[4:min(len(data), 68)])
                                  if len(data) > 4 else None),
            "scenes": map_row.get("scenes_that_load_it", []),
            "call_targets": targets,
        }
    exact = [
        {"overlay": name, **target}
        for name, row in rows.items() for target in row["call_targets"]
        if target["exact_function_start"]
    ]
    return {
        "region": "Region A shared swap buffer",
        "base": f"0x{REGION_A:08X}",
        "images": len(rows), "non_stub_images": sum(not row["stub"] for row in rows.values()),
        "rows": rows, "exact_function_bindings": exact,
        "exact_function_bindings_count": len(exact),
        "safety": "Every overlay CALL target is meaningful only for a scene-qualified loaded image.",
    }


def build_static_census(exe: bytes | None = None) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe is None else exe
    verify_staged_input(EXE_REL, exe)
    vm = gen_vm_disasm.build_document(exe)
    words = {}
    for name, (address, expected) in EXPECTED_WORDS.items():
        actual = _word(exe, address)
        if actual != expected:
            raise SystemExit(
                f"pristine E07 word mismatch at 0x{address:08X}: "
                f"0x{actual:08X} != 0x{expected:08X}")
        words[name] = {"address": f"0x{address:08X}", "word": f"0x{actual:08X}"}
    instructions = [instruction for program in vm["programs"]
                    for instruction in program["instructions"]]
    opcode_counts = Counter(row["idx"] for row in instructions if row.get("idx") is not None)
    call_counts = Counter(row["call_slot"] for row in instructions if row.get("call_slot"))
    functions = json.loads(FUNCTIONS.read_text())
    overlay_map = json.loads(OVERLAY_MAP.read_text())
    return {
        "executable": {"path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
                       "sha256": _sha256_bytes(exe), "pristine_pin_verified": True},
        "instruction_words": words,
        "vm": vm,
        "instruction_count": len(instructions),
        "opcode_occurrences": {str(key): value for key, value in sorted(opcode_counts.items())},
        "call_slot_occurrences": {str(key): value for key, value in sorted(call_counts.items())},
        "overlays": _overlay_census(functions, overlay_map),
        "fixture_sha256": {
            "analysis/functions.json": _sha256(FUNCTIONS),
            "analysis/phase3_overlay_map.json": _sha256(OVERLAY_MAP),
            "analysis/vm_programs.json": _sha256(ROOT / "analysis/vm_programs.json"),
        },
        "mod_contract": {
            "valid_selector_domain": [0, 39],
            "source_selector_field": "source record +0x0D u8",
            "actor_source_field": "actor +0x80 pointer",
            "actor_ip_field": "actor +0x70 pointer",
            "retail_bounds_check": False,
            "first_out_of_domain_control": {"selector": 40, "loaded_word": "0x03020100"},
            "overlay_rule": "Condition CALL slots 3,4,5,6,9 on the loaded Region-A image; a bare VA has no stable verb.",
        },
    }


def static_census_gaps(static: dict[str, Any]) -> list[str]:
    vm = static.get("vm") or {}
    overlays = static.get("overlays") or {}
    gaps = []
    if vm.get("selector_count") != 40 or vm.get("unique_program_count") != 40:
        gaps.append("selector table is not 40 slots / 40 unique starts")
    if {row.get("confidence") for row in vm.get("opcode_semantics", [])} != {"CONFIRMED"}:
        gaps.append("not all 26 opcode handlers are confirmed")
    if set(map(int, static.get("opcode_occurrences", {}))) != set(range(26)):
        gaps.append("program decode does not exercise every opcode index")
    if set(map(int, static.get("call_slot_occurrences", {}))) != set(range(1, 10)):
        gaps.append("program decode does not exercise every CALL slot")
    if overlays.get("images") != 20 or overlays.get("non_stub_images") != 19:
        gaps.append("overlay census is not 20 pinned images / 19 non-stubs")
    if overlays.get("exact_function_bindings_count") != 9:
        gaps.append("overlay CALL frontier does not retain nine exact function bindings")
    if static.get("mod_contract", {}).get("retail_bounds_check") is not False:
        gaps.append("retail selector absence control is missing")
    return gaps


def _run_breadth(client: Any, anchors: list[tuple[str, str]],
                 vm: dict[str, Any], overlays: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for label, save in anchors:
        loaded = _load_anchor(client, save)
        scene = _read_u32(client, SCENE_WORD)
        before = _actor_snapshot(client, vm)
        trace = _trace_vm(client)
        after = _actor_snapshot(client, vm)
        rows.append({
            "label": label, "save": save, "load": loaded, "scene": scene,
            "before": before, "trace": trace, "after": after,
            "overlay_identity": _overlay_runtime_identity(client, scene, overlays),
        })
    observed_selectors = sorted({int(selector) for row in rows
                                 for selector in row["before"]["selector_histogram"]})
    observed_opcodes = sorted({int(index) for row in rows
                               for index in row["trace"]["opcode_histogram"]})
    call_slots = sorted({int(slot) for row in rows
                         for slot, hits in row["trace"]["call_slot_hits"].items()
                         if hits})
    idle_windows = [row["label"] for row in rows if not row["trace"]["fetch_total"]]
    invalid_program_rows = [
        row["label"] for row in rows
        if any(record["source"]["valid"] and record["program"] is None
               for record in row["before"]["records"])
    ]
    traced_contexts = len(rows) - len(idle_windows)
    # A fixed window with no fetch is retained as an idle observation, not an
    # absence claim: actor waits can exceed TRACE_FRAMES and special stages may
    # have no live mover.  The independent source/IP census still has to map all
    # valid-source actors into the decoded program bank, and natural execution
    # must occur in broad (not single-scene) coverage.
    if len(rows) != 19 or traced_contexts < 5 or invalid_program_rows:
        raise SystemExit(
            f"E07 breadth failed: traced={traced_contexts}, "
            f"idle={idle_windows}, invalid_program_rows={invalid_program_rows}")
    if any(selector > 39 for selector in observed_selectors):
        raise SystemExit(f"live authored selector outside static domain: {observed_selectors}")
    return {"trials": rows, "summary": {
        "anchors": len(rows), "scenes": sorted({row["scene"] for row in rows}),
        "observed_selectors": observed_selectors,
        "observed_opcodes": observed_opcodes, "observed_call_slots": call_slots,
        "traced_contexts": traced_contexts, "idle_trace_windows": idle_windows,
        "fetch_events": sum(row["trace"]["fetch_total"] for row in rows),
        "actor_live_count_range": [min(row["before"]["live_count"] for row in rows),
                                   max(row["before"]["live_count"] for row in rows)],
    }}


def _selector_controls(client: Any) -> dict[str, Any]:
    results = {}
    for selector, expected in ((0, 0x8007745C), (39, 0x80077AC0), (40, 0x03020100)):
        _load_anchor(client, "level01.sav")
        actor = bytearray(ACTOR_STRIDE)
        source = bytearray(0x20)
        struct.pack_into("<I", actor, 0x80, SCRATCH_SOURCE)
        source[0x0C] = 1
        source[0x0D] = selector
        writes = [_write_memory(client, SCRATCH_ACTOR, actor),
                  _write_memory(client, SCRATCH_SOURCE, source)]
        call = client.call("debugger.callFunction", {
            "address": f"0x{SELECTOR_ROUTINE:08X}", "a0": SCRATCH_ACTOR,
            "a1": 0, "a2": 0, "a3": 0, "timeout": 5000})
        actual = _read_u32(client, SCRATCH_ACTOR + 0x70)
        results[str(selector)] = {
            "selector": selector, "writes": writes, "call": call,
            "actual_actor_ip": f"0x{actual:08X}",
            "expected_actor_ip": f"0x{expected:08X}",
            "in_valid_program_region": PROGRAM_MIN <= actual < PROGRAM_MAX,
        }
        if actual != expected:
            raise SystemExit(f"selector control {selector} changed: {results[str(selector)]}")
    if results["40"]["in_valid_program_region"]:
        raise SystemExit("out-of-domain selector unexpectedly resolved into the program bank")
    return {
        "trials": results,
        "conclusion": "Retail accepts the source byte without bounds checking; MOD emitters must enforce 0..39.",
    }


def _movie_cleanup(client: Any) -> None:
    try:
        client.call("movie.stopPlayback", {})
    except Exception:
        pass
    try:
        client.call("movie.clear", {})
    except Exception:
        pass


def _base_movie_pin() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    pin = entries.get(BASE_MOVIE)
    path = ROOT / BASE_MOVIE
    if not pin or pin.get("media_class") != "pristine_serial" or not path.is_file() or \
            path.stat().st_size != pin.get("size") or _sha256(path) != pin.get("sha256"):
        raise SystemExit(f"cold-boot E07 movie is not centrally pinned: {pin}")
    movie = json.loads(path.read_text())
    if movie.get("format") != "DuckStationInputMovie" or movie.get("version") != 3 or \
            (movie.get("start_state") or {}).get("from_boot") is not True or \
            len(movie.get("frames") or []) <= MOVIE_TRACE_END:
        raise SystemExit("cold-boot E07 movie is not a usable v3 from-boot fixture")
    return {"path": BASE_MOVIE, "sha256": pin["sha256"], "size": pin["size"],
            "media_class": pin["media_class"], "frames": len(movie["frames"])}


def _run_cold_boot(client: Any, vm: dict[str, Any]) -> dict[str, Any]:
    pin = _base_movie_pin()
    client.call("debugger.pause", {})
    _movie_cleanup(client)
    try:
        loaded = client.call("movie.load", {"path": str((ROOT / BASE_MOVIE).resolve())})
        started = client.call("movie.startPlayback", {"load_start_state": True})
        client.call("movie.advanceToFrame", {"frame": MOVIE_TRACE_START,
                                               "max_frames": 9000}, timeout=900)
        before = _actor_snapshot(client, vm)
        client.call("execTrace.clear", {})
        watch = client.call("execTrace.addWatch", {
            "pc": f"0x{FETCH_PC:08X}", "capture": ["v0", "s0", "s1"],
            "label": "cold_boot_vm_fetch", "max_events": 10000})
        client.call("movie.advanceToFrame", {"frame": MOVIE_TRACE_END,
                                               "max_frames": 100}, timeout=900)
        trace = _trace_get(client, watch)
        client.call("execTrace.clear", {})
        after = _actor_snapshot(client, vm)
        status = client.call("movie.status", {})
    finally:
        _movie_cleanup(client)
    if started.get("reproducible") is not True or status.get("reproducible") is not True or \
            status.get("truncated") is not False or trace.get("truncated") or not trace["total"] or \
            _read_u32(client, SCENE_WORD) != 1:
        raise SystemExit("cold-boot E07 trace did not reproduce the LEVEL01 VM")
    return {"movie": pin, "load": loaded, "started": started,
            "trace_window": [MOVIE_TRACE_START, MOVIE_TRACE_END],
            "before": before, "after": after,
            "fetch_total": trace["total"], "first_event": trace["events"][:1],
            "status": status, "scene": 1}


def _run_pause(client: Any, vm: dict[str, Any]) -> dict[str, Any]:
    _load_anchor(client, "level01.sav")
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"start": True}})
    client.call("emulator.advanceFrames", {"frames": 3})
    client.call("emulator.clearControllerState", {"port": 0})
    paused = {"pause_flag": _read_u16(client, PAUSE_FLAG), "actors": _actor_snapshot(client, vm)}
    client.call("emulator.advanceFrames", {"frames": 30})
    frozen = {"pause_flag": _read_u16(client, PAUSE_FLAG), "actors": _actor_snapshot(client, vm)}
    client.call("emulator.setControllerState", {"port": 0, "buttons": {"cross": True}})
    client.call("emulator.advanceFrames", {"frames": 8})
    client.call("emulator.clearControllerState", {"port": 0})
    resumed = {"pause_flag": _read_u16(client, PAUSE_FLAG), "actors": _actor_snapshot(client, vm)}
    trace = _trace_vm(client, 60)
    progressed = _actor_snapshot(client, vm)
    if paused["pause_flag"] != 1 or frozen["pause_flag"] != 1 or \
            paused["actors"]["raw_sha256"] != frozen["actors"]["raw_sha256"] or \
            resumed["pause_flag"] != 0 or \
            (not trace["fetch_total"] and
             progressed["raw_sha256"] == frozen["actors"]["raw_sha256"]):
        raise SystemExit(
            "E07 pause/resume control failed: "
            f"flags={paused['pause_flag']},{frozen['pause_flag']},{resumed['pause_flag']} "
            f"frozen_equal={paused['actors']['raw_sha256'] == frozen['actors']['raw_sha256']} "
            f"post_fetch={trace['fetch_total']} "
            f"progressed={progressed['raw_sha256'] != frozen['actors']['raw_sha256']}")
    return {"paused": paused, "frozen": frozen, "resumed": resumed,
            "post_resume_trace": trace, "post_trace_actors": progressed}


def _set_player_position(client: Any, xyz: tuple[int, int, int]) -> list[dict[str, Any]]:
    return [_checked_write(client, "debugger.writeU32", PLAYER_BASE + offset,
                           value & 0xFFFFFFFF)
            for offset, value in zip((0, 4, 8), xyz)]


def _run_respawn(client: Any, vm: dict[str, Any]) -> dict[str, Any]:
    _load_anchor(client, "level01.sav")
    first = _actor_snapshot(client, vm)["records"][0]
    writes = [
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x94, 0),
        _checked_write(client, "debugger.writeU16", PLAYER_BASE + 0x86, 5),
        _checked_write(client, "debugger.writeU8", PLAYER_BASE + 0x96, 3),
        *_set_player_position(client, tuple(first["position"])),
    ]
    before = {"lives": _read_u8(client, PLAYER_BASE + 0xA0),
              "scene": _read_u32(client, SCENE_WORD),
              "actors": _actor_snapshot(client, vm)}
    flow, respawn = [], None
    for elapsed in range(60, 481, 60):
        client.call("emulator.advanceFrames", {"frames": 60})
        row = {"elapsed": elapsed, "lives": _read_u8(client, PLAYER_BASE + 0xA0),
               "health": struct.unpack("<h", _read_memory(client, 0x800A7E2A, 2))[0],
               "scene": _read_u32(client, SCENE_WORD)}
        flow.append(row)
        if row["lives"] == before["lives"] - 1 and row["health"] == 4:
            respawn = row
            break
    if respawn is None:
        raise SystemExit(f"native E07 respawn did not complete: {flow}")
    after = _actor_snapshot(client, vm)
    trace = _trace_vm(client, 12)
    if not trace["fetch_total"] or after["live_count"] == 0 or respawn["scene"] != before["scene"]:
        raise SystemExit("E07 VM did not rearm after native respawn")
    return {"collision_actor": first, "writes": writes, "before": before,
            "flow": flow, "respawn": respawn, "after": after,
            "post_respawn_trace": trace}


def _stable_actor_sources(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"slot": row["slot"], "id": row["id"],
             "source_pointer": row["source_pointer"],
             "selector": row["source"]["selector"]}
            for row in snapshot["records"]]


def _run_scene_reuse(client: Any, vm: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for save in ("level01.sav", "level02.sav", "level01.sav"):
        _load_anchor(client, save)
        snap = _actor_snapshot(client, vm)
        rows.append({"save": save, "scene": _read_u32(client, SCENE_WORD),
                     "actor_sources": _stable_actor_sources(snap),
                     "trace": _trace_vm(client, 6)})
    if rows[0]["scene"] != rows[2]["scene"] or \
            rows[0]["actor_sources"] != rows[2]["actor_sources"] or \
            rows[0]["actor_sources"] == rows[1]["actor_sources"]:
        raise SystemExit("E07 LEVEL01->02->01 scene rebuild control failed")
    return {"loads": rows, "level01_rebuilt_identically": True,
            "level02_distinct": True}


def _fixture_pins(selection: dict[str, Any], saves: list[str]) -> dict[str, str]:
    by_save = {row["save"]: row["sha256"] for row in selection["accepted"]}
    return {save: by_save[save] for save in saves}


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    static = build_static_census()
    gaps = static_census_gaps(static)
    if gaps:
        raise SystemExit(f"static E07 census failed: {gaps}")
    baseline = json.loads(BASELINE.read_text())
    all_anchors, selection = select_pristine_save_anchors(baseline)
    anchors = all_anchors[:19]
    if len(anchors) != 19 or anchors[-1][0] != "bonus3_grasshoppers":
        raise SystemExit("strict-pristine E07 anchors no longer cover 19 gameplay contexts")
    saves = [save for _label, save in anchors]
    selection = {**selection, "accepted": selection["accepted"][:19], "rejected": [],
                 "anchors_requested": 19, "anchors_accepted": 19, "anchors_rejected": 0}

    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeMemory", "debugger.writeU8",
        "debugger.writeU16", "debugger.writeU32", "debugger.callFunction",
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.loadState",
        "emulator.setControllerState", "emulator.clearControllerState",
        "emulator.advanceFrames", "execTrace.addWatch", "execTrace.get",
        "execTrace.run", "execTrace.clear", "movie.load", "movie.startPlayback",
        "movie.advanceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required if not _method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E07 methods: {missing}")
    inspections = [inspect_state_before_load(client, ROOT / save, media_identity)
                   for save in saves]

    cold_boot = _run_cold_boot(client, static["vm"])
    breadth = _run_breadth(client, anchors, static["vm"], static["overlays"]["rows"])
    selectors = _selector_controls(client)
    pause = _run_pause(client, static["vm"])
    respawn = _run_respawn(client, static["vm"])
    scene_reuse = _run_scene_reuse(client, static["vm"])

    provenance = finish_run(
        args, generator="tools/phase4_event_vm.py",
        anchor={
            "type": "cold-boot VM fetch plus strict-pristine gameplay breadth, selector bounds, pause, respawn and scene-reuse controls",
            "saves": saves, "fixture_sha256": _fixture_pins(selection, saves),
            "state_inspections": inspections, "selection": selection,
            "cold_boot_movie": cold_boot["movie"], "media_identity": media_identity,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "settle_frames": SETTLE_FRAMES, "trace_frames": TRACE_FRAMES,
            "cold_boot_trace_window": [MOVIE_TRACE_START, MOVIE_TRACE_END],
        })
    document = {
        "_comment": "Phase-4 E07 event/mover-VM evidence from hash-pinned pristine executable/overlays and isolated retail-media controls.",
        "generated": date.today().isoformat(), "static_census": static,
        "live": {"cold_boot": cold_boot, "breadth": breadth,
                 "selector_controls": selectors, "pause_resume": pause,
                 "death_respawn": respawn, "scene_reuse": scene_reuse},
        "source_dependencies": {
            "tools/gen_vm_disasm.py": _sha256(ROOT / "tools/gen_vm_disasm.py"),
            "src_re/enemy_ai_programs.c": _sha256(ROOT / "src_re/enemy_ai_programs.c"),
        },
        "run_provenance": provenance,
    }
    write_live_evidence(OUTPUT, document)
    print(f"[event-vm] retained E07 campaign: {OUTPUT}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_required_live_args(parser)
    args = parser.parse_args()
    try:
        return _run(args)
    except BaseException:
        try:
            finish_run(args, generator="tools/phase4_event_vm.py",
                       anchor={"type": "aborted before retained E07 evidence"}, timing={})
        except BaseException as cleanup_error:
            print(f"owned E07 instance cleanup also failed: {cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
