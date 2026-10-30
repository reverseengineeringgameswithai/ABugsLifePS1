#!/usr/bin/env python3
"""Bind Thud's seven natural reward volleys and countdown-selected variant."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

try:
    import phase4_c16_bonus_death as base
    import phase4_e08_operator_contacts as contacts
    import phase4_thud_defeat as thud
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_thud_volley
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_thud_defeat as thud
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_thud_volley.json"
ORIGIN_TARGET = 970
BRANCH_TARGET = 971
SETTLED_TARGETS = (994, 1336, 1736, 2154, 2548, 2964, 3334, 3754, 4113)
EXPECTED_COUNTERS = (1, 2, 3, 4, 5, 6, 7, 8, 8)
EXPECTED_GRAIN = (0, 0, 0, 4, 8, 12, 14, 14, 14)
EXPECTED_CALLS = (10, 20, 30, 40, 50, 60, 70, 70, 70)
EXPECTED_ACTION9_PICKUPS = (0, 0, 1, 2, 3, 4, 4, 4, 4)
NATURAL_PICKUP_PRE_TARGET = 1432
NATURAL_PICKUP_POST_TARGET = 1433

DECREMENT_STORE = 0x800B3F24
SPECIAL_PATH = 0x800B3F34
GENERAL_PATH = 0x800B3F7C
ALLOCATOR_CALL = 0x800B3FF0
SOUND_CALL = 0x800B3FFC
GRAIN_STORE = 0x80054F9C
ACTION20_TAIL = 0x800589B8
ACTION9_HANDLER = 0x80058864
ACTION9_HEALTH_STORE = 0x80058890
ACTION9_HANDLER_LENGTH = 0x38
ACTION9_HANDLER_SHA256 = (
    "e89382b9e86e29907d3cee300e6c7b706884bd20f352f2ff217c06e6f799f849")
ACTION9_DECISIVE_WORDS = {
    "handler_state_7": (0x80058864, 0x24100007),
    "health_load": (0x80058880, 0x94620000),
    "health_increment": (0x80058888, 0x24420001),
    "health_store": (0x80058890, 0xA4620000),
}
DECISIVE_PCS = (
    DECREMENT_STORE, SPECIAL_PATH, GENERAL_PATH, ALLOCATOR_CALL, SOUND_CALL,
    GRAIN_STORE, ACTION20_TAIL, ACTION9_HANDLER, ACTION9_HEALTH_STORE,
)
TRACE_RANGES = (
    {"label": "thud_reward_volley",
     "start": f"0x{thud.POST_RESTORE_CONTINUATION_ADDRESS:08X}",
     "end": f"0x{thud.POST_RESTORE_CONTINUATION_ADDRESS + thud.POST_RESTORE_CONTINUATION_LENGTH - 4:08X}",
     "max_pcs": 256},
    {"label": "resident_grain_increment",
     "start": f"0x{thud.GRAIN_INCREMENT_SLICE_ADDRESS:08X}",
     "end": f"0x{thud.GRAIN_INCREMENT_SLICE_ADDRESS + thud.GRAIN_INCREMENT_SLICE_LENGTH - 4:08X}",
     "max_pcs": 64},
    {"label": "resident_action20_tail",
     "start": "0x800589B8", "end": "0x800589E4", "max_pcs": 64},
    {"label": "resident_action9_health_leaf",
     "start": "0x80058864", "end": "0x80058898", "max_pcs": 64},
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_int(client: Any, address: int, fmt: str) -> int:
    return struct.unpack("<" + fmt, base._read_memory(
        client, address, struct.calcsize(fmt)))[0]


def _pool_census(client: Any) -> dict[str, Any]:
    data = base._read_memory(
        client, thud.CONTACT_POOL, thud.CONTACT_STRIDE * 64)
    rows = []
    for slot in range(64):
        record = data[slot * thud.CONTACT_STRIDE:(slot + 1) * thud.CONTACT_STRIDE]
        ttl = struct.unpack_from("<H", record, 0x22)[0]
        action = struct.unpack_from("<H", record, 0x20)[0]
        if ttl and action in (9, 20):
            rows.append({
                "slot": slot, "action_id": action, "lifetime_ttl": ttl,
                "position": list(struct.unpack_from("<iii", record, 0x00)),
                "velocity": list(struct.unpack_from("<iii", record, 0x0C)),
                "radius_add": struct.unpack_from("<h", record, 0x28)[0],
                "state": struct.unpack_from("<h", record, 0x2C)[0],
                "flags": record[0x33],
            })
    return {
        "active_action9_count": sum(row["action_id"] == 9 for row in rows),
        "active_action20_count": sum(row["action_id"] == 20 for row in rows),
        "active_action9_or_20": rows,
    }


def _snapshot(client: Any, *, full_identity: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    result = {
        "emulator_frame": status.get("frame"), "cycle": status.get("cycle"),
        "pc": status.get("pc"), "sp": status.get("sp"),
        "movie_frame": movie.get("playback_index"),
        "movie_reproducible": movie.get("reproducible"),
        "movie_truncated": movie.get("truncated"),
        "scene": _read_int(client, thud.SCENE, "I"),
        "phase_counter": _read_int(client, thud.PHASE_COUNTER, "I"),
        "derived_countdown": _read_int(client, thud.GRAIN_PHASE_VALUE, "I"),
        "grain": _read_int(client, thud.GRAIN, "B"),
        "health": _read_int(client, thud.HEALTH, "h"),
        "player_position": [
            _read_int(client, thud.PLAYER + offset, "i")
            for offset in (0, 4, 8)
        ],
        "slot17": thud._contact_snapshot(client, thud.THUD_ATTACK_CONTACT_SLOT),
        "reward_pool": _pool_census(client),
    }
    if full_identity:
        result["main_ram_sha256"] = _sha256_bytes(base._main_ram(client))
        result["registers_sha256"] = base._register_sha256(client)
    return result


def _counts(raw: dict[str, Any]) -> dict[str, int]:
    wanted = {f"0x{pc:08x}" for pc in DECISIVE_PCS}
    result = {pc: 0 for pc in sorted(wanted)}
    for coverage in raw.get("coverage") or []:
        for row in (coverage.get("coverage") or {}).get("counts_by_pc") or []:
            pc = str(row.get("pc", "")).lower()
            if pc in wanted:
                result[pc] += int(row.get("count") or 0)
    return result


def _trace_to(client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    raw = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": list(TRACE_RANGES),
    }, timeout=900)
    compact = contacts._compact_trace(raw)
    if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in compact.get("coverage") or []):
        raise SystemExit(f"Thud volley trace incomplete at {frame}")
    counts = _counts(raw)
    for row in compact.get("coverage") or []:
        start = int(row["range"]["start"], 16)
        end = int(row["range"]["end"], 16)
        row["decisive_counts_by_pc"] = {
            pc: count for pc, count in counts.items()
            if start <= int(pc, 16) <= end
        }
    snapshot = _snapshot(client)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"Thud volley movie drifted at {frame}")
    return {"target_movie_frame": frame, "snapshot": snapshot,
            "cumulative_counts": counts, "cycle_neutral_trace": compact}


def _runtime_identity(client: Any) -> dict[str, Any]:
    address = thud.POST_RESTORE_CONTINUATION_ADDRESS
    length = thud.POST_RESTORE_CONTINUATION_LENGTH
    data = base._read_memory(client, address, length)
    disassembly = client.call("debugger.disassemble", {
        "address": f"0x{address:08X}", "count": length // 4})
    instructions = disassembly.get("instructions") or []
    by_address = {int(str(row.get("address")), 16): row for row in instructions}
    decisive = {
        f"0x{pc:08x}": {key: (by_address.get(pc) or {}).get(key)
                         for key in ("address", "bytes", "mnemonic", "operands", "text")}
        for pc in (DECREMENT_STORE, SPECIAL_PATH, GENERAL_PATH,
                   ALLOCATOR_CALL, SOUND_CALL)
    }
    result = {
        "address": f"0x{address:08x}", "length": length,
        "instruction_count": len(instructions), "sha256": _sha256_bytes(data),
        "classification": (
            "save-owned Region-A runtime; exact save/media identity required; "
            "not staged provenance"),
        "decisive_instructions": decisive,
    }
    if result["sha256"] != thud.POST_RESTORE_CONTINUATION_SHA256 or \
            result["instruction_count"] != length // 4:
        raise SystemExit(f"Thud volley runtime identity drifted: {result}")
    expected = {DECREMENT_STORE: "sw", ALLOCATOR_CALL: "jal", SOUND_CALL: "jal"}
    if {pc: (by_address.get(pc) or {}).get("mnemonic") for pc in expected} != expected:
        raise SystemExit(f"Thud volley decisive instructions drifted: {decisive}")
    return result


def _static_action9_identity() -> dict[str, Any]:
    pins = json.loads((ROOT / "tools/build_baselines.json").read_text())[
        "staged_inputs"]
    path = ROOT / "REBUILD/files/SCUS_942.88"
    pin = pins["SCUS_942.88"]
    executable = path.read_bytes()
    executable_sha256 = _sha256_bytes(executable)
    if (len(executable), executable_sha256) != (
            pin["size"], pin["sha256"]):
        raise SystemExit("pristine executable identity drifted for action-9 census")
    data = thud._exe_slice(executable, ACTION9_HANDLER, ACTION9_HANDLER_LENGTH)
    words = {
        label: {
            "address": f"0x{address:08x}",
            "word": f"0x{struct.unpack_from('<I', data, address - ACTION9_HANDLER)[0]:08x}",
        }
        for label, (address, _) in ACTION9_DECISIVE_WORDS.items()
    }
    expected_words = {
        label: f"0x{expected:08x}"
        for label, (_, expected) in ACTION9_DECISIVE_WORDS.items()
    }
    if _sha256_bytes(data) != ACTION9_HANDLER_SHA256 or \
            {label: row["word"] for label, row in words.items()} != expected_words:
        raise SystemExit(f"pristine action-9 handler bytes drifted: {words}")
    return {
        "executable": {
            "path": path.relative_to(ROOT).as_posix(),
            "size": len(executable),
            "sha256": executable_sha256,
            "pin": pin,
        },
        "address": f"0x{ACTION9_HANDLER:08x}",
        "length": ACTION9_HANDLER_LENGTH,
        "sha256": ACTION9_HANDLER_SHA256,
        "decisive_words": words,
        "classification": (
            "hash-pinned pristine resident executable; byte-exact matching ASM "
            "exists, while src_re contact-walker C remains semantic/documentation-grade"),
    }


def _ram_differences(before: bytes, after: bytes) -> list[dict[str, Any]]:
    return [{"address": f"0x{0x80000000 + offset:08x}",
             "before": old, "after": new}
            for offset, (old, new) in enumerate(zip(before, after)) if old != new]


def _advance_one(client: Any) -> dict[str, Any]:
    client.call("movie.advanceToFrame", {
        "frame": BRANCH_TARGET, "max_frames": BRANCH_TARGET}, timeout=300)
    return _snapshot(client)


def _variant_control(client: Any, movie_path: Path) -> dict[str, Any]:
    control_origin = _trace_to(client, movie_path, ORIGIN_TARGET)
    control_origin["snapshot"] = _snapshot(client, full_identity=True)
    runtime = _runtime_identity(client)
    control_after = _advance_one(client)

    mutation_origin = _trace_to(client, movie_path, ORIGIN_TARGET)
    mutation_origin["snapshot"] = _snapshot(client, full_identity=True)
    before_ram = base._main_ram(client)
    before = _read_int(client, thud.GRAIN_PHASE_VALUE, "I")
    write = client.call("debugger.writeU32", {
        "address": f"0x{thud.GRAIN_PHASE_VALUE:08X}", "value": 6})
    after = _read_int(client, thud.GRAIN_PHASE_VALUE, "I")
    after_ram = base._main_ram(client)
    mutation_after = _advance_one(client)

    comparable = ("emulator_frame", "cycle", "pc", "sp", "movie_frame",
                  "scene", "phase_counter", "derived_countdown", "grain",
                  "main_ram_sha256", "registers_sha256")
    return {
        "control_origin": control_origin, "mutation_origin": mutation_origin,
        "origin_equal": {key: control_origin["snapshot"].get(key) ==
                         mutation_origin["snapshot"].get(key)
                         for key in comparable},
        "single_field": {
            "address": f"0x{thud.GRAIN_PHASE_VALUE:08x}",
            "before": before, "after": after, "rpc": write,
            "write_differences": _ram_differences(before_ram, after_ram)},
        "control_after": control_after, "mutation_after": mutation_after,
        "endpoint_timing_equal": {
            key: control_after.get(key) == mutation_after.get(key)
            for key in ("emulator_frame", "cycle", "movie_frame", "pc", "sp")},
        "endpoint_cycle_delta_mutation_minus_control": (
            mutation_after.get("cycle") - control_after.get("cycle")),
        "runtime_identity": runtime,
        "control_rule": (
            "Both branches reset through cycle-neutral traceToFrame to an "
            "identical pristine target-970 RAM/register/cycle/PC/SP origin. "
            "Only u32 countdown 0x800B4CB4 changes 9->6; the next native "
            "iteration decrements it and selects the equality-to-five path."),
    }


def _source_dependencies() -> dict[str, str]:
    paths = (
        "tools/phase4_thud_defeat.py", "analysis/phase4_thud_defeat.json",
        "analysis/phase0_2_external_fixture_set.json",
        "tools/build_baselines.json",
        "asm/hand_written/800586b0_contact_walker.s",
        "src_re/player_health.c", "src_re/enemy_drops.c",
        "ObsidianVault/Canon/Tables/TABLE_8001B570_contact_action_dispatch.md",
        "tools/scenarios/duckstation/pristine_thud_reward_variant_control.yaml",
        "tools/scenarios/duckstation/pristine_thud_action9_natural_pickup.yaml",
    )
    return {path: thud._sha256(ROOT / path) for path in paths}


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    rows = document.get("settled_boundaries") or []
    final_counts = (rows[-1].get("cumulative_counts") or {}) if rows else {}
    final = (rows[-1].get("snapshot") or {}) if rows else {}
    control = document.get("matched_variant_control") or {}
    pickup_rows = document.get("first_natural_action9_pickup") or []
    pickup_pre = (pickup_rows[0].get("snapshot") or {}) if len(pickup_rows) == 2 else {}
    pickup_post = (pickup_rows[1].get("snapshot") or {}) if len(pickup_rows) == 2 else {}
    return {
        "natural_reward_volleys": final_counts.get(f"0x{SPECIAL_PATH:08x}"),
        "allocations_per_volley": (
            (final_counts.get(f"0x{ALLOCATOR_CALL:08x}") or 0) // 7),
        "total_reward_allocations": final_counts.get(f"0x{ALLOCATOR_CALL:08x}"),
        "general_action20_allocations": final_counts.get(f"0x{GENERAL_PATH:08x}"),
        "special_action9_allocations": final_counts.get(f"0x{SPECIAL_PATH:08x}"),
        "natural_action9_pickups": final_counts.get(f"0x{ACTION9_HANDLER:08x}"),
        "first_natural_action9_pickup_target": (
            pickup_rows[1].get("target_movie_frame") if len(pickup_rows) == 2 else None),
        "first_natural_action9_health_delta": (
            pickup_post.get("health") - pickup_pre.get("health")
            if pickup_pre.get("health") is not None and
            pickup_post.get("health") is not None else None),
        "natural_action20_grain_pickups": final_counts.get(f"0x{GRAIN_STORE:08x}"),
        "final_grain": final.get("grain"),
        "countdown_variant": [
            (control.get("control_after") or {}).get("slot17", {}).get("action_id"),
            (control.get("mutation_after") or {}).get("slot17", {}).get("action_id")],
        "recorded_fight_frequency_bound": True,
        "d18_or_f09_completed": 0,
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("schema") != "abl-phase4-thud-volley/2":
        gaps.append("Thud volley schema changed")
    if document.get("campaign_state") != "active_partial":
        gaps.append("Thud volley campaign state changed")
    rows = document.get("settled_boundaries") or []
    if [row.get("target_movie_frame") for row in rows] != list(SETTLED_TARGETS):
        gaps.append("Thud volley settled targets changed")
    observed = []
    for row in rows:
        snap = row.get("snapshot") or {}
        counts = row.get("cumulative_counts") or {}
        observed.append((snap.get("phase_counter"), snap.get("grain"),
                         counts.get(f"0x{ALLOCATOR_CALL:08x}")))
        trace = row.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []):
            gaps.append(f"Thud volley target {row.get('target_movie_frame')} trace changed")
    if observed != list(zip(EXPECTED_COUNTERS, EXPECTED_GRAIN, EXPECTED_CALLS)):
        gaps.append("Thud volley cumulative boundaries changed")
    if rows:
        counts = rows[-1].get("cumulative_counts") or {}
        expected = {
            f"0x{DECREMENT_STORE:08x}": 70, f"0x{SPECIAL_PATH:08x}": 7,
            f"0x{GENERAL_PATH:08x}": 63, f"0x{ALLOCATOR_CALL:08x}": 70,
            f"0x{SOUND_CALL:08x}": 70, f"0x{GRAIN_STORE:08x}": 14,
            f"0x{ACTION20_TAIL:08x}": 14,
            f"0x{ACTION9_HANDLER:08x}": 4,
            f"0x{ACTION9_HEALTH_STORE:08x}": 4,
        }
        if counts != expected:
            gaps.append("Thud volley final exact execution counts changed")
        final = rows[-1].get("snapshot") or {}
        pool = final.get("reward_pool") or {}
        if (final.get("phase_counter"), final.get("derived_countdown"),
                final.get("grain"), pool.get("active_action9_count"),
                pool.get("active_action20_count")) != (8, 0, 14, 0, 0):
            gaps.append("Thud volley final retirement boundary changed")
    action9_counts = [
        (row.get("cumulative_counts") or {}).get(f"0x{ACTION9_HANDLER:08x}")
        for row in rows
    ]
    if action9_counts != list(EXPECTED_ACTION9_PICKUPS):
        gaps.append("Thud natural action-9 pickup counts changed")
    pickup_rows = document.get("first_natural_action9_pickup") or []
    if [row.get("target_movie_frame") for row in pickup_rows] != [
            NATURAL_PICKUP_PRE_TARGET, NATURAL_PICKUP_POST_TARGET]:
        gaps.append("Thud first natural action-9 pickup boundary changed")
    elif len(pickup_rows) == 2:
        pre, post = pickup_rows
        pre_snap = pre.get("snapshot") or {}
        post_snap = post.get("snapshot") or {}
        pre_count = (pre.get("cumulative_counts") or {}).get(
            f"0x{ACTION9_HANDLER:08x}")
        post_count = (post.get("cumulative_counts") or {}).get(
            f"0x{ACTION9_HANDLER:08x}")
        pre_store_count = (pre.get("cumulative_counts") or {}).get(
            f"0x{ACTION9_HEALTH_STORE:08x}")
        post_store_count = (post.get("cumulative_counts") or {}).get(
            f"0x{ACTION9_HEALTH_STORE:08x}")
        pre_records = [
            row for row in (pre_snap.get("reward_pool") or {}).get(
                "active_action9_or_20", []) if row.get("action_id") == 9]
        post_records = [
            row for row in (post_snap.get("reward_pool") or {}).get(
                "active_action9_or_20", []) if row.get("action_id") == 9]
        if (pre_count, post_count, pre_store_count, post_store_count) != \
                (0, 1, 0, 1) or \
                post_snap.get("health") != pre_snap.get("health", 0) + 1 or \
                len(pre_records) != 1 or len(post_records) != 1 or \
                pre_records[0].get("slot") != post_records[0].get("slot") or \
                post_records[0].get("lifetime_ttl") != 1 or \
                post_records[0].get("state") != 7 or \
                post_records[0].get("position") != [126549, -348, -14770] or \
                post_records[0].get("radius_add") != 100 or \
                post_records[0].get("flags") != 226:
            gaps.append("Thud first natural action-9 pickup outcome changed")
        if any((row.get("cycle_neutral_trace") or {}).get(
                "comparison", {}).get("cycle_neutral") is not True for row in pickup_rows):
            gaps.append("Thud first natural action-9 pickup trace changed")
    control = document.get("matched_variant_control") or {}
    if not control.get("origin_equal") or not all(control.get("origin_equal", {}).values()):
        gaps.append("Thud volley matched origins changed")
    if not control.get("endpoint_timing_equal") or \
            control.get("endpoint_timing_equal") != {
                "emulator_frame": True, "cycle": False,
                "movie_frame": True, "pc": True, "sp": True} or \
            control.get("endpoint_cycle_delta_mutation_minus_control") != -1:
        gaps.append(
            "Thud volley matched endpoint timing changed: "
            f"{control.get('endpoint_timing_equal')}, delta="
            f"{control.get('endpoint_cycle_delta_mutation_minus_control')}")
    single = control.get("single_field") or {}
    if (single.get("address"), single.get("before"), single.get("after"),
            len(single.get("write_differences") or [])) != (
                f"0x{thud.GRAIN_PHASE_VALUE:08x}", 9, 6, 1):
        gaps.append("Thud volley single-field mutation changed")
    c = control.get("control_after") or {}
    m = control.get("mutation_after") or {}
    if (c.get("derived_countdown"), c.get("slot17", {}).get("action_id"),
            c.get("slot17", {}).get("lifetime_ttl")) != (8, 20, 200) or \
            (m.get("derived_countdown"), m.get("slot17", {}).get("action_id"),
             m.get("slot17", {}).get("lifetime_ttl")) != (5, 9, 200):
        gaps.append("Thud volley action variant outcome changed")
    runtime = control.get("runtime_identity") or {}
    if (runtime.get("address"), runtime.get("length"),
            runtime.get("instruction_count"), runtime.get("sha256")) != (
                f"0x{thud.POST_RESTORE_CONTINUATION_ADDRESS:08x}",
                thud.POST_RESTORE_CONTINUATION_LENGTH,
                thud.POST_RESTORE_CONTINUATION_LENGTH // 4,
                thud.POST_RESTORE_CONTINUATION_SHA256):
        gaps.append("Thud volley runtime identity changed")
    static = document.get("static_action9_handler") or {}
    if (static.get("address"), static.get("length"), static.get("sha256")) != (
            f"0x{ACTION9_HANDLER:08x}", ACTION9_HANDLER_LENGTH,
            ACTION9_HANDLER_SHA256):
        gaps.append("Thud action-9 static identity changed")
    words = static.get("decisive_words") or {}
    if {label: (words.get(label) or {}).get("word")
            for label in ACTION9_DECISIVE_WORDS} != {
                label: f"0x{word:08x}"
                for label, (_, word) in ACTION9_DECISIVE_WORDS.items()}:
        gaps.append("Thud action-9 decisive words changed")
    expected_summary = {
        "natural_reward_volleys": 7, "allocations_per_volley": 10,
        "total_reward_allocations": 70, "general_action20_allocations": 63,
        "special_action9_allocations": 7,
        "natural_action9_pickups": 4,
        "first_natural_action9_pickup_target": 1433,
        "first_natural_action9_health_delta": 1,
        "natural_action20_grain_pickups": 14, "final_grain": 14,
        "countdown_variant": [20, 9], "recorded_fight_frequency_bound": True,
        "d18_or_f09_completed": 0,
    }
    if document.get("summary") != derive_summary(document) or \
            document.get("summary") != expected_summary:
        gaps.append("Thud volley derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thud volley process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = thud.build_fixture_census()
    static_action9 = _static_action9_identity()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    media = verified_media_identity(client, client.call("debugger.status", {}))
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.capabilities", "debugger.disassemble", "debugger.getRegisters",
        "debugger.pause", "debugger.readMemory", "debugger.status",
        "debugger.writeU32", "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.advanceToFrame", "movie.clear", "movie.load", "movie.startPlayback",
        "movie.status", "movie.stopPlayback", "movie.traceToFrame",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks Thud volley methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / thud.SAVE_REL, media)
    movie_path = ROOT / thud.MOVIE_REL
    settled = [_trace_to(client, movie_path, target) for target in SETTLED_TARGETS]
    first_natural_pickup = [
        _trace_to(client, movie_path, target)
        for target in (NATURAL_PICKUP_PRE_TARGET, NATURAL_PICKUP_POST_TARGET)
    ]
    matched = _variant_control(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_thud_volley.py",
        anchor={
            "type": "existing state-anchored Thud natural-defeat recording",
            "save": thud.SAVE_REL, "movie": thud.MOVIE_REL,
            "fixture_sha256": {thud.SAVE_REL: thud.SAVE_SHA256,
                               thud.MOVIE_REL: thud.MOVIE_SHA256},
            "state_inspections": [inspection], "media_identity": media,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "passive_trace_targets": list(SETTLED_TARGETS),
            "first_natural_action9_pickup_targets": [
                NATURAL_PICKUP_PRE_TARGET, NATURAL_PICKUP_POST_TARGET],
            "matched_variant_origin_target": ORIGIN_TARGET,
            "matched_variant_endpoint_target": BRANCH_TARGET,
            "trace_mode": (
                "passive cycle-neutral movie.traceToFrame cumulative coverage; "
                "fresh matched one-field countdown branch"),
        })
    document = {
        "_comment": (
            "Active D18/F09 evidence: the pinned pristine recording executes "
            "seven ten-item save-owned reward volleys. Exact execution counts, "
            "four natural action-9 pickups and a matched countdown control bind "
            "the special action-9 branch and health effect; "
            "other attacks and lifecycle breadth remain open."),
        "generated": "2026-07-17", "schema": "abl-phase4-thud-volley/2",
        "campaign_state": "active_partial", "fixture_census": fixture,
        "static_action9_handler": static_action9,
        "settled_boundaries": settled,
        "first_natural_action9_pickup": first_natural_pickup,
        "matched_variant_control": matched,
        "bounded_interpretation": {
            "observation": (
                "Seven natural resets execute 70 save-owned allocator calls: "
                "63 general-path calls, seven countdown-equals-five calls and "
                "14 later resident grain-increment stores. Four natural "
                "action-9 handlers execute the exact health increment store."),
            "inference": (
                "The countdown loop emits nine action-20 grain contacts and one "
                "action-9 health-leaf contact per volley; four health leaves are "
                "naturally collected and each raises true health by one."),
            "causal_confirmation": (
                "At equal pristine target-970 RAM/register/cycle/PC/SP, changing "
                "only countdown 9->6 changes the next allocated slot-17 action "
                "20->9 at the same emulator/movie frame, PC and SP with one "
                "fewer mutation-branch CPU cycle."),
            "forbidden_claim": (
                "Do not infer a universal collection/drop rate, health above the "
                "observed domain, complete Thud attack policy, or D18/F09 completion."),
        },
        "bounded_open_frontier": {
            "closed_here": (
                "Recorded-fight volley count, allocation count, action-9 variant "
                "selection, four natural action-9 health increments and natural "
                "action-20 grain-pickup frequency."),
            "still_open": (
                "Other attack sources/damage curves, complete action-9 spawn and "
                "collection policy, visual ownership, initialization, retry, "
                "persistence, breadth "
                "and failures."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained Thud volley evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[thud-volley] reward volleys, action-9 health pickups and variant bound")
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
                finish_run(args, generator="tools/phase4_thud_volley.py",
                           anchor={"type": "aborted before retained volley evidence"},
                           timing={})
            except BaseException as cleanup_error:
                print(f"owned Thud volley cleanup also failed: {cleanup_error}",
                      file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
