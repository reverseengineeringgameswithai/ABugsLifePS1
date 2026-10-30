#!/usr/bin/env python3
"""Join existing natural damage leads to the resident C16 death law.

The operator filenames remain discovery metadata.  This generator admits only
centrally pinned pristine movie/state pairs, inspects every state before load,
and uses cycle-neutral ``movie.traceToFrame`` control/coverage pairs to decide
whether each complete replay reaches nonfatal damage, final-life game over, or
ordinary respawn.  It does not assign an E10 hazard kind or owner.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
from typing import Any

try:
    from build_identity import verify_staged_input
    import phase4_e08_hazard_outcomes as hazards
    import phase4_e08_operator_contacts as contacts
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_lives_death_breadth
    from tools.build_identity import verify_staged_input
    from tools import phase4_e08_hazard_outcomes as hazards
    from tools import phase4_e08_operator_contacts as contacts
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_lives_death_breadth.json"
C16_ARTIFACT = ROOT / "analysis/phase4_lives_gameover.json"
E10_ARTIFACT = ROOT / "analysis/phase4_e08_hazard_outcomes.json"
E07_ARTIFACT = ROOT / "analysis/phase4_event_vm.json"
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800
REGION_A = 0x800B39A0
REGION_A_END = 0x800B5788
TRANSITION_INITIATOR_JAL = 0x0C0129C0
MIPS_GPR_NAMES = (
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
)

SCENE = 0x80082504
TRACE_RANGES = (
    {"start": "0x8004A700", "end": "0x8004AA34",
     "label": "damage_and_death_initiator", "max_pcs": 200000},
    {"start": "0x8004FCA0", "end": "0x800502C4",
     "label": "scene_flow_dispatcher", "max_pcs": 200000},
    {"start": "0x8005B12C", "end": "0x8005B440",
     "label": "respawn_transition_state_handler", "max_pcs": 200000},
)

TRIGGER_TRACE_RANGES = (
    TRACE_RANGES[0],
    TRACE_RANGES[2],
    {"start": "0x80048138", "end": "0x800498AC",
     "label": "player_vertical_update", "max_pcs": 200000},
    {"start": "0x8004ABF4", "end": "0x8004B6DC",
     "label": "proximity_updater", "max_pcs": 200000},
    {"start": "0x800586B0", "end": "0x80058AF8",
     "label": "contact_pickup_walker", "max_pcs": 200000},
    {"start": "0x8005C918", "end": "0x8005CA24",
     "label": "seed_plant_mine_handler", "max_pcs": 200000},
    {"start": f"0x{REGION_A:08X}", "end": f"0x{REGION_A_END:08X}",
     "label": "region_a_scene_overlay", "max_pcs": 200000},
)

RESIDENT_DIRECT_CALLS = {
    0x800496B0: {
        "producer_path_id": "player_region_code_1_exit",
        "function": "player_vertical_update",
        "mode": 1,
        "boundary": "region-code 1 branch",
    },
    0x80049740: {
        "producer_path_id": "player_region_code_4_hazard",
        "function": "player_vertical_update",
        "mode": 0,
        "boundary": "region-code 4 branch with player +0x7E/+0x92 clear",
    },
    0x80049868: {
        "producer_path_id": "player_bottomless_fall",
        "function": "player_vertical_update",
        "mode": 2,
        "boundary": "live Y exceeds floor/reference Y +8192",
    },
    0x8004B4A0: {
        "producer_path_id": "proximity_contact",
        "function": "proximity_updater",
        "mode": 0,
        "boundary": "proximity updater accepted its native contact gates",
    },
    0x80058A48: {
        "producer_path_id": "contact_pool_damage",
        "function": "contact_pickup_walker",
        "mode": 0,
        "boundary": "contact walker accumulated its native damage response",
    },
    0x8005C9F8: {
        "producer_path_id": "seed_plant_mine_contact",
        "function": "seed_plant_mine_handler",
        "mode": 0,
        "boundary": "seed/plant/mine record flag 0x0040",
    },
}

DECISIVE_PCS = {
    "fatal_health_write": "0x8004a888",
    "final_life_reader": "0x800500bc",
    "game_over_movie_selector": "0x800500d4",
    "ordinary_respawn_call": "0x800500f4",
    "respawn_health_restore": "0x8005b30c",
    "respawn_lives_decrement": "0x8005b348",
}
NEUTRAL_SUFFIX_FRAMES = 240


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_u32(client: Any, address: int) -> int:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": 4})
    data = bytes.fromhex(row["hex"])
    if len(data) != 4:
        raise SystemExit(f"short debugger read at 0x{address:08X}")
    return struct.unpack("<I", data)[0]


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length or row.get("valid_bytes") != length:
        raise SystemExit(
            f"short debugger read at 0x{address:08X}: "
            f"{row.get('valid_bytes')}/{length}")
    return data


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _scan_direct_calls(data: bytes, base: int) -> list[int]:
    return [
        base + offset for offset in range(0, len(data) - 3, 4)
        if struct.unpack_from("<I", data, offset)[0] == TRANSITION_INITIATOR_JAL
    ]


def build_trigger_static_census() -> dict[str, Any]:
    """Enumerate every exact direct call to the C16 transition initiator."""
    executable = EXE.read_bytes()
    verify_staged_input(EXE_REL, executable)
    resident = _scan_direct_calls(executable[EXE_HEADER:], EXE_LOAD)
    if set(resident) != set(RESIDENT_DIRECT_CALLS):
        raise SystemExit(
            "resident transition-initiator caller census drifted: "
            f"{[f'0x{pc:08X}' for pc in resident]}")

    event_vm = json.loads(E07_ARTIFACT.read_text())
    overlay_rows = (((event_vm.get("static_census") or {}).get("overlays") or {})
                    .get("rows") or {})
    overlay_calls = []
    for name, row in sorted(overlay_rows.items()):
        if row.get("stub"):
            continue
        rel = str(row["rel"]).removeprefix("REBUILD/files/")
        path = ROOT / "REBUILD/files" / rel
        data = path.read_bytes()
        verify_staged_input(rel, data)
        if _sha256_bytes(data) != row.get("sha256"):
            raise SystemExit(f"E07 overlay census drifted for {name}")
        for address in _scan_direct_calls(data, REGION_A):
            offset = address - REGION_A
            lo = max(0, offset - 16)
            hi = min(len(data), offset + 20)
            overlay_calls.append({
                "address": f"0x{address:08x}",
                "producer_path_id": (
                    f"scene_overlay_{name.lower().removesuffix('.bin')}"),
                "function": "scene-qualified Region-A overlay",
                "mode": None,
                "boundary": "overlay-private policy; decode remains row-owned",
                "overlay": name,
                "path": f"REBUILD/files/{rel}",
                "sha256": row["sha256"],
                "scenes": row.get("scenes") or [],
                "code_slice": {
                    "address": f"0x{REGION_A + lo:08x}",
                    "length": hi - lo,
                    "sha256": _sha256_bytes(data[lo:hi]),
                },
            })
    expected_overlay_calls = {
        ("LEVEL04_LEVEL1.BIN", "0x800b4ae0"),
        ("LEVEL06_LEVEL.BIN", "0x800b3e94"),
    }
    observed_overlay_calls = {
        (row["overlay"], row["address"]) for row in overlay_calls}
    if observed_overlay_calls != expected_overlay_calls:
        raise SystemExit(
            f"overlay transition-initiator caller census drifted: "
            f"{sorted(observed_overlay_calls)}")

    resident_rows = [
        {"address": f"0x{address:08x}", "instruction_word": "0x0c0129c0",
         "residency": "resident", **RESIDENT_DIRECT_CALLS[address]}
        for address in resident
    ]
    return {
        "target": "0x8004a700",
        "jal_instruction_word": "0x0c0129c0",
        "resident_executable": {
            "path": f"REBUILD/files/{EXE_REL}",
            "sha256": _sha256(EXE),
            "direct_calls": resident_rows,
        },
        "scene_overlays": {
            "authority": "analysis/phase4_event_vm.json static overlay census",
            "base": f"0x{REGION_A:08x}",
            "direct_calls": overlay_calls,
        },
        "direct_call_count": len(resident_rows) + len(overlay_calls),
    }


def _runtime_overlay_identity(
        client: Any, scene: int, static: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    direct_calls = (static.get("scene_overlays") or {}).get("direct_calls") or []
    event_vm = json.loads(E07_ARTIFACT.read_text())
    rows = (((event_vm.get("static_census") or {}).get("overlays") or {})
            .get("rows") or {})
    for name, row in sorted(rows.items()):
        if row.get("stub") or scene not in (row.get("scenes") or []):
            continue
        runtime = _read_memory(client, REGION_A, int(row["size"]))
        candidates.append({
            "overlay": name,
            "expected_sha256": row["sha256"],
            "runtime_sha256": _sha256_bytes(runtime),
            "exact_match": _sha256_bytes(runtime) == row["sha256"],
        })
    runtime_calls = []
    for call in direct_calls:
        address = int(call["address"], 16)
        code = call["code_slice"]
        sample = _read_memory(client, int(code["address"], 16), code["length"])
        word = _read_u32(client, address)
        runtime_calls.append({
            "address": call["address"],
            "overlay": call["overlay"],
            "declared_scene_match": scene in call["scenes"],
            "runtime_word": f"0x{word:08x}",
            "word_matches": word == TRANSITION_INITIATOR_JAL,
            "expected_slice_sha256": code["sha256"],
            "runtime_slice_sha256": _sha256_bytes(sample),
            "slice_matches": _sha256_bytes(sample) == code["sha256"],
        })
    return {
        "scene": scene,
        "candidates": candidates,
        "exact_matches": [row["overlay"] for row in candidates
                          if row["exact_match"]],
        "runtime_direct_calls": runtime_calls,
        "runtime_direct_call_matches": [
            {"address": row["address"], "overlay": row["overlay"]}
            for row in runtime_calls
            if row["word_matches"] and row["slice_matches"]
        ],
    }


def _capture_entry_caller(
        client: Any, movie_path: Path, movie_frame: int) -> dict[str, Any]:
    """Replay to just before first entry and retain the architectural link."""
    contacts._trace_state_at_frame(
        client, movie_path, movie_frame - 1, ranges=(TRACE_RANGES[0],))
    client.call("debugger.runUntilAddress", {"address": "0x8004A700"})
    deadline = time.monotonic() + 30
    while True:
        status = client.call("debugger.status", {})
        if status.get("paused") is True:
            break
        if time.monotonic() >= deadline:
            raise SystemExit("timed out waiting for transition-entry breakpoint")
        time.sleep(0.01)
    registers = client.call("debugger.getRegisters", {})["registers_hex"]
    registers = {str(key).lower(): value for key, value in registers.items()}
    pc = int(registers["pc"], 16)
    ra = int(registers["ra"], 16)
    call_address = (ra - 8) & 0xFFFFFFFF
    word = _read_u32(client, call_address)
    opcode = word >> 26
    rs = (word >> 21) & 0x1F
    rd = (word >> 11) & 0x1F
    if opcode == 3:
        call_kind = "jal"
        call_target = ((call_address + 4) & 0xF0000000) | \
            ((word & 0x03FFFFFF) << 2)
        target_register = None
    elif opcode == 0 and (word & 0x3F) == 9:
        call_kind = "jalr"
        target_register = MIPS_GPR_NAMES[rs]
        call_target = int(registers[target_register], 16)
    else:
        call_kind = "not_link_call"
        target_register = None
        call_target = 0
    sample_address = max(0x80000000, call_address - 16)
    sample = _read_memory(client, sample_address, 36)
    valid = bool(
        pc == 0x8004A700 and call_target == 0x8004A700 and
        call_kind in {"jal", "jalr"} and
        (call_kind != "jalr" or rd == 31) and
        status.get("paused") is True and
        int(status.get("pc", "0"), 16) == 0x8004A700)
    return {
        "valid": valid,
        "pc": f"0x{pc:08x}",
        "ra": f"0x{ra:08x}",
        "link_call_address": f"0x{call_address:08x}",
        "instruction_word": f"0x{word:08x}",
        "call_kind": call_kind,
        "target_register": target_register,
        "target_register_value": (
            registers[target_register] if target_register else None),
        "resolved_target": f"0x{call_target:08x}",
        "arguments": {
            name: registers[name] for name in ("a0", "a1", "a2", "a3")},
        "code_slice": {
            "address": f"0x{sample_address:08x}",
            "length": len(sample),
            "sha256": _sha256_bytes(sample),
        },
        "capture_boundary": (
            "instrumented pinned replay stopped before the first target "
            "instruction; passive traceToFrame evidence separately supplies "
            "cycle-neutral execution identity"),
    }


def _coverage_pcs(replay: dict[str, Any], label: str) -> set[str]:
    rows = (replay.get("cycle_neutral_trace") or {}).get("coverage") or []
    matches = [row for row in rows if row.get("label") == label]
    if len(matches) != 1:
        return set()
    return {str(pc).lower() for pc in matches[0].get("pcs") or []}


def derive_entry_capture_valid(capture: dict[str, Any]) -> bool:
    try:
        pc = int(capture["pc"], 16)
        ra = int(capture["ra"], 16)
        address = int(capture["link_call_address"], 16)
        word = int(capture["instruction_word"], 16)
        target = int(capture["resolved_target"], 16)
    except (KeyError, TypeError, ValueError):
        return False
    if pc != 0x8004A700 or target != pc or address != (ra - 8) & 0xFFFFFFFF:
        return False
    opcode = word >> 26
    if capture.get("call_kind") == "jal":
        decoded = ((address + 4) & 0xF0000000) | \
            ((word & 0x03FFFFFF) << 2)
        return opcode == 3 and decoded == target
    if capture.get("call_kind") == "jalr":
        rs = (word >> 21) & 0x1F
        rd = (word >> 11) & 0x1F
        try:
            register_value = int(capture["target_register_value"], 16)
        except (KeyError, TypeError, ValueError):
            return False
        return bool(
            opcode == 0 and (word & 0x3F) == 9 and rd == 31 and
            capture.get("target_register") == MIPS_GPR_NAMES[rs] and
            register_value == target)
    return False


def _all_coverage_pcs(trace: dict[str, Any]) -> set[str]:
    return {
        str(pc).lower()
        for row in trace.get("coverage") or []
        for pc in row.get("pcs") or []
    }


def _trigger_changed(
        initial_player: dict[str, Any], player: dict[str, Any]) -> bool:
    return any(initial_player[field] != player[field]
               for field in ("health", "lives"))


def derive_trigger_attribution(
        boundary: dict[str, Any], static: dict[str, Any]) -> dict[str, Any]:
    """Join first initiator entry and its typed outcome to one direct caller."""
    before = boundary.get("before") or {}
    after = boundary.get("after") or {}
    outcome = boundary.get("health_lives_outcome") or {}
    outcome_before = outcome.get("before") or {}
    outcome_after = outcome.get("after") or {}
    before_player = outcome_before.get("player") or {}
    after_player = outcome_after.get("player") or {}
    initial_player = boundary.get("initial_player") or {}
    before_trace = before.get("cycle_neutral_trace") or {}
    after_trace = after.get("cycle_neutral_trace") or {}
    before_pcs = _all_coverage_pcs(before_trace)
    after_pcs = _all_coverage_pcs(after_trace)
    newly_reached = after_pcs - before_pcs
    outcome_pcs = _all_coverage_pcs(
        outcome_after.get("cycle_neutral_trace") or {})
    newly_reached_by_outcome = outcome_pcs - before_pcs
    capture = boundary.get("entry_register_capture") or {}

    authority = list(
        ((static.get("resident_executable") or {}).get("direct_calls") or []))
    overlay_matches = {
        (row.get("address"), row.get("overlay"))
        for row in ((boundary.get("runtime_overlay_identity") or {}).get(
            "runtime_direct_call_matches") or [])
    }
    for row in ((static.get("scene_overlays") or {}).get("direct_calls") or []):
        if (row.get("address"), row.get("overlay")) in overlay_matches:
            authority.append(row)
    capture_address = str(capture.get("link_call_address", "")).lower()
    calls = [row for row in authority
             if str(row.get("address", "")).lower() == capture_address]
    unique_call = calls[0] if len(calls) == 1 else None
    producer_path_id = (
        unique_call.get("producer_path_id") if unique_call else
        (f"runtime_{capture.get('call_kind')}_{capture_address}"
         if derive_entry_capture_valid(capture) else None))
    health_lives_boundary = bool(
        initial_player and before_player and after_player and
        not _trigger_changed(initial_player, before_player) and
        _trigger_changed(initial_player, after_player))
    exact = bool(
        health_lives_boundary and derive_entry_capture_valid(capture) and
        "0x8004a700" in newly_reached and
        (DECISIVE_PCS["fatal_health_write"] in newly_reached_by_outcome or
         DECISIVE_PCS["respawn_lives_decrement"] in
         newly_reached_by_outcome) and
        before.get("scene") == after.get("scene") ==
        outcome_before.get("scene") == outcome_after.get("scene"))
    return {
        "exact": exact,
        "producer_path_id": producer_path_id,
        "link_call_address": capture.get("link_call_address"),
        "call_kind": capture.get("call_kind"),
        "static_direct_call_match": unique_call is not None,
        "function": (unique_call.get("function") if unique_call else
                     "runtime register-linked caller"),
        "mode": unique_call.get("mode") if unique_call else None,
        "boundary": (unique_call.get("boundary") if unique_call else
                     "entry-time link register resolves to 0x8004A700"),
        "overlay": unique_call.get("overlay") if unique_call else None,
        "health_lives_boundary": health_lives_boundary,
        "static_call_candidates": [row.get("address") for row in calls],
        "call_target_newly_reached": "0x8004a700" in newly_reached,
        "health_write_reached_by_typed_outcome": (
            DECISIVE_PCS["fatal_health_write"] in newly_reached_by_outcome),
        "lives_decrement_reached_by_typed_outcome": (
            DECISIVE_PCS["respawn_lives_decrement"] in
            newly_reached_by_outcome),
        "same_scene": (
            before.get("scene") == after.get("scene") ==
            outcome_before.get("scene") == outcome_after.get("scene")),
        "newly_reached_pc_count": len(newly_reached),
        "trigger_to_outcome_movie_frames": (
            outcome.get("movie_frame", 0) - boundary.get("movie_frame", 0)),
    }


def _locate_first_trigger_boundary(
        client: Any, movie_path: Path, frame_count: int,
        initial_player: dict[str, Any], static: dict[str, Any]) -> dict[str, Any]:
    """Binary-search first cumulative target execution from fresh anchors."""
    lo, hi = 1, frame_count
    probes = []
    while lo < hi:
        mid = (lo + hi) // 2
        replay = contacts._trace_state_at_frame(
            client, movie_path, mid, ranges=(TRACE_RANGES[0],))
        player = replay["snapshot"]["player"]
        matched = "0x8004a700" in _all_coverage_pcs(replay["trace"])
        probes.append({
            "movie_frame": mid, "matched": matched,
            "emulator_frame": replay["snapshot"]["frame"],
            "cycle": replay["snapshot"]["cycle"],
            "health": player["health"], "lives": player["lives"],
        })
        if matched:
            hi = mid
        else:
            lo = mid + 1

    before = contacts._trace_state_at_frame(
        client, movie_path, lo - 1, ranges=TRIGGER_TRACE_RANGES)
    before_scene = _read_u32(client, SCENE)
    after = contacts._trace_state_at_frame(
        client, movie_path, lo, ranges=TRIGGER_TRACE_RANGES)
    after_scene = _read_u32(client, SCENE)
    if "0x8004a700" in _all_coverage_pcs(before["trace"]) or \
            "0x8004a700" not in _all_coverage_pcs(after["trace"]):
        raise SystemExit(f"transition initiator was not first reached at {lo}")
    overlay_identity = _runtime_overlay_identity(client, after_scene, static)
    outcome_probes = []
    outcome_lo, outcome_hi = lo, frame_count
    outcome_ranges = (TRACE_RANGES[0], TRACE_RANGES[2])
    outcome_effect_pcs = {
        DECISIVE_PCS["fatal_health_write"],
        DECISIVE_PCS["respawn_lives_decrement"],
    }
    while outcome_lo < outcome_hi:
        movie_frame = (outcome_lo + outcome_hi) // 2
        current = contacts._trace_state_at_frame(
            client, movie_path, movie_frame, ranges=outcome_ranges)
        player = current["snapshot"]["player"]
        matched = bool(
            outcome_effect_pcs & _all_coverage_pcs(current["trace"]))
        outcome_probes.append({
            "movie_frame": movie_frame, "matched": matched,
            "emulator_frame": current["snapshot"]["frame"],
            "cycle": current["snapshot"]["cycle"],
            "health": player["health"], "lives": player["lives"],
        })
        if matched:
            outcome_hi = movie_frame
        else:
            outcome_lo = movie_frame + 1
    outcome_before_row = contacts._trace_state_at_frame(
        client, movie_path, outcome_lo - 1, ranges=TRIGGER_TRACE_RANGES)
    outcome_before_scene = _read_u32(client, SCENE)
    outcome_after_row = contacts._trace_state_at_frame(
        client, movie_path, outcome_lo, ranges=TRIGGER_TRACE_RANGES)
    outcome_after_scene = _read_u32(client, SCENE)
    outcome_before_player = outcome_before_row["snapshot"]["player"]
    outcome_after_player = outcome_after_row["snapshot"]["player"]
    if _trigger_changed(initial_player, outcome_before_player) or not \
            _trigger_changed(initial_player, outcome_after_player):
        raise SystemExit(
            f"transition initiator at {lo} had no stable typed effect boundary "
            f"at {outcome_lo}")
    outcome = {
        "movie_frame": outcome_lo,
        "probes": outcome_probes,
        "effect_pc_search": sorted(outcome_effect_pcs),
        "before": {
            "emulator_frame": outcome_before_row["snapshot"]["frame"],
            "cycle": outcome_before_row["snapshot"]["cycle"],
            "scene": outcome_before_scene,
            "player": outcome_before_player,
            "cycle_neutral_trace": outcome_before_row["trace"],
        },
        "after": {
            "emulator_frame": outcome_after_row["snapshot"]["frame"],
            "cycle": outcome_after_row["snapshot"]["cycle"],
            "scene": outcome_after_scene,
            "player": outcome_after_player,
            "cycle_neutral_trace": outcome_after_row["trace"],
        },
    }
    entry_capture = _capture_entry_caller(client, movie_path, lo)
    boundary = {
        "movie_frame": lo,
        "initial_player": initial_player,
        "probes": probes,
        "before": {
            "emulator_frame": before["snapshot"]["frame"],
            "cycle": before["snapshot"]["cycle"],
            "scene": before_scene,
            "player": before["snapshot"]["player"],
            "cycle_neutral_trace": before["trace"],
        },
        "after": {
            "emulator_frame": after["snapshot"]["frame"],
            "cycle": after["snapshot"]["cycle"],
            "scene": after_scene,
            "player": after["snapshot"]["player"],
            "cycle_neutral_trace": after["trace"],
        },
        "runtime_overlay_identity": overlay_identity,
        "entry_register_capture": entry_capture,
        "health_lives_outcome": outcome,
        "search_rule": (
            "fresh pinned recorded-anchor replay for every probe; cumulative "
            "execution of 0x8004A700 is monotonic even when fatal health is "
            "later restored; the retained before/after pair separately requires "
            "a subsequent first typed health/lives change, its health-store PC, "
            "and passive cycle-neutral caller coverage"),
    }
    boundary["attribution"] = derive_trigger_attribution(boundary, static)
    if boundary["attribution"]["exact"] is not True:
        raise SystemExit(
            f"first health/lives boundary lacked one exact direct caller at "
            f"movie frame {lo}: {boundary['attribution']}")
    return boundary


def _player_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    fields = ("health", "lives", "state", "grounded", "animation",
              "velocity_y", "position")
    changed = {field: {"before": before[field], "after": after[field]}
               for field in fields if before[field] != after[field]}
    return {
        "changed_fields": changed,
        "health_or_lives_changed": any(
            before[field] != after[field] for field in ("health", "lives")),
    }


def derive_law_evidence(replay: dict[str, Any]) -> dict[str, Any]:
    """Derive the bounded C16 result only from retained typed state and PCs."""
    before = (replay.get("initial") or {}).get("player") or {}
    outcome = replay.get("source_end") or replay.get("final") or {}
    after = outcome.get("player") or {}
    if not before or not after:
        return {"classification": "invalid", "required_pcs_present": False}
    scene_pcs = _coverage_pcs(replay, "scene_flow_dispatcher")
    respawn_pcs = _coverage_pcs(replay, "respawn_transition_state_handler")
    damage_pcs = _coverage_pcs(replay, "damage_and_death_initiator")
    if after["lives"] == before["lives"] - 1:
        classification = "ordinary_respawn_completed"
        required = {
            DECISIVE_PCS["ordinary_respawn_call"],
            DECISIVE_PCS["respawn_health_restore"],
            DECISIVE_PCS["respawn_lives_decrement"],
        }
        present = ({DECISIVE_PCS["ordinary_respawn_call"]} <= scene_pcs and
                   required - {DECISIVE_PCS["ordinary_respawn_call"]} <=
                   respawn_pcs and after["health"] == 4)
    elif after["health"] < 0 and before["lives"] == after["lives"] == 0:
        classification = "final_life_game_over_selected"
        required = {
            DECISIVE_PCS["fatal_health_write"],
            DECISIVE_PCS["final_life_reader"],
            DECISIVE_PCS["game_over_movie_selector"],
        }
        present = (DECISIVE_PCS["fatal_health_write"] in damage_pcs and
                   required - {DECISIVE_PCS["fatal_health_write"]} <= scene_pcs and
                   DECISIVE_PCS["ordinary_respawn_call"] not in scene_pcs)
    elif after["health"] < before["health"]:
        classification = "nonfatal_damage_boundary"
        required = set()
        present = (DECISIVE_PCS["ordinary_respawn_call"] not in scene_pcs and
                   DECISIVE_PCS["respawn_lives_decrement"] not in respawn_pcs)
    else:
        classification = "no_c16_health_or_lives_outcome"
        required = set()
        present = False
    return {
        "classification": classification,
        "required_pcs": sorted(required),
        "required_pcs_present": present,
        "same_scene_at_retained_boundary": (
            (replay.get("initial") or {}).get("scene") ==
            outcome.get("scene")),
    }


def derive_summary(replays: list[dict[str, Any]]) -> dict[str, Any]:
    classifications = Counter(
        derive_law_evidence(replay)["classification"] for replay in replays)
    death_paths = [
        replay for replay in replays
        if derive_law_evidence(replay)["classification"] in {
            "ordinary_respawn_completed", "final_life_game_over_selected"}
    ]
    trigger_rows = [
        ((replay.get("first_transition_trigger") or {}).get(
            "attribution") or {})
        for replay in replays
    ]
    producer_paths = Counter(
        row["producer_path_id"] for row in trigger_rows
        if row.get("exact") is True and row.get("producer_path_id"))
    return {
        "movies_replayed": len(replays),
        "classification_counts": dict(sorted(classifications.items())),
        "death_paths_joined_to_exact_resident_law": len(death_paths),
        "ordinary_respawn_paths": classifications["ordinary_respawn_completed"],
        "final_life_game_over_paths": classifications[
            "final_life_game_over_selected"],
        "nonfatal_damage_paths": classifications["nonfatal_damage_boundary"],
        "death_scenes": sorted({
            replay["initial"]["scene"] for replay in death_paths}),
        "all_traces_cycle_neutral": all(
            (replay.get("cycle_neutral_trace") or {}).get("comparison", {}).get(
                "cycle_neutral") is True for replay in replays),
        "all_death_law_requirements_present": all(
            derive_law_evidence(replay)["required_pcs_present"] is True
            for replay in death_paths),
        "exact_first_trigger_paths": sum(
            row.get("exact") is True for row in trigger_rows),
        "trigger_producer_path_counts": dict(sorted(producer_paths.items())),
        "hazard_kinds_or_owners_promoted": 0,
    }


def _write_neutral_suffix_movie(
        fixture: dict[str, Any], temp_dir: Path) -> tuple[Path, dict[str, Any]]:
    movie_path = ROOT / fixture["movie"]["path"]
    movie = json.loads(movie_path.read_text())
    source_count = len(movie["frames"])
    neutral = json.loads(json.dumps(movie["frames"][-1]))
    for value in (neutral.get("ports") or {}).values():
        if isinstance(value, dict):
            for key in list(value):
                value[key] = 128 if key in {"lx", "ly", "rx", "ry"} else False
    for index in range(NEUTRAL_SUFFIX_FRAMES):
        row = json.loads(json.dumps(neutral))
        row["frame"] = source_count + index
        movie["frames"].append(row)
    save_path = (ROOT / fixture["save"]["path"]).resolve()
    movie["start_state"]["path"] = str(save_path)
    movie["start_state"]["file_size"] = save_path.stat().st_size
    output = temp_dir / f"{fixture['lead']}-neutral-suffix.movie.json"
    output.write_text(json.dumps(movie, separators=(",", ":")) + "\n")
    return output, {
        "source_sha256": fixture["movie"]["sha256"],
        "source_frame_count": source_count,
        "derived_frame_count": len(movie["frames"]),
        "appended_neutral_frames": NEUTRAL_SUFFIX_FRAMES,
        "anchor": fixture["save"]["path"],
        "transient_storage": (
            "temporary directory; derivative deleted before evidence retention"),
    }


def _run_movie(
        client: Any, fixture: dict[str, Any], temp_dir: Path,
        static: dict[str, Any]) -> dict[str, Any]:
    movie = fixture["movie"]
    movie_path = ROOT / movie["path"]
    initial_row = contacts._trace_state_at_frame(
        client, movie_path, 0, ranges=TRACE_RANGES)
    initial = initial_row["snapshot"]
    initial_scene = _read_u32(client, SCENE)
    source_end_row = contacts._trace_state_at_frame(
        client, movie_path, movie["frames"], ranges=TRACE_RANGES)
    source_end = source_end_row["snapshot"]
    source_end_scene = _read_u32(client, SCENE)
    final_row = source_end_row
    final = source_end
    final_scene = source_end_scene
    extension_recipe = None
    preliminary = {
        "initial": {"player": initial["player"], "scene": initial_scene},
        "source_end": {"player": source_end["player"], "scene": source_end_scene},
        "cycle_neutral_trace": source_end_row["trace"],
    }
    preliminary_law = derive_law_evidence(preliminary)
    if preliminary_law["classification"] == "final_life_game_over_selected" and \
            preliminary_law["required_pcs_present"] is not True:
        extended_path, extension_recipe = _write_neutral_suffix_movie(
            fixture, temp_dir)
        final_row = contacts._trace_state_at_frame(
            client, extended_path, extension_recipe["derived_frame_count"],
            ranges=TRACE_RANGES)
        final = final_row["snapshot"]
        final_scene = _read_u32(client, SCENE)
    first_boundary = _locate_first_trigger_boundary(
        client, movie_path, movie["frames"], initial["player"], static)
    contacts._cleanup_movie(client)
    replay = {
        "lead": fixture["lead"],
        "row_lead": fixture["row_lead"],
        "fixture": fixture,
        "initial": {
            "frame": initial["frame"], "cycle": initial["cycle"],
            "scene": initial_scene, "player": initial["player"],
            "cycle_neutral_trace": initial_row["trace"],
        },
        "final": {
            "frame": final["frame"], "cycle": final["cycle"],
            "scene": final_scene, "player": final["player"],
            "ram_sha256": final_row["trace"]["control"]["ram_sha256"],
            "movie_status": final_row["movie_status"],
        },
        "source_end": {
            "frame": source_end["frame"], "cycle": source_end["cycle"],
            "scene": source_end_scene, "player": source_end["player"],
            "ram_sha256": source_end_row["trace"]["control"]["ram_sha256"],
            "movie_status": source_end_row["movie_status"],
        },
        "extension_recipe": extension_recipe,
        "first_transition_trigger": first_boundary,
        "player_delta": _player_delta(initial["player"], source_end["player"]),
        "cycle_neutral_trace": final_row["trace"],
        "classification_boundary": (
            "the operator filename is a discovery lead only; typed health/lives, "
            "scene and exact resident-PC coverage determine this C16 join"),
    }
    replay["law_evidence"] = derive_law_evidence(replay)
    print(
        f"[c16-death-breadth] {fixture['lead']} scene={initial_scene} "
        f"classification={replay['law_evidence']['classification']} "
        f"producer={first_boundary['attribution']['producer_path_id']}@"
        f"{first_boundary['attribution']['link_call_address']}")
    return replay


def source_dependency_gaps(document: dict[str, Any]) -> list[str]:
    expected = {
        "tools/phase4_e08_hazard_outcomes.py": _sha256(
            ROOT / "tools/phase4_e08_hazard_outcomes.py"),
        "tools/phase4_e08_operator_contacts.py": _sha256(
            ROOT / "tools/phase4_e08_operator_contacts.py"),
        "analysis/phase4_e08_hazard_outcomes.json": _sha256(E10_ARTIFACT),
        "analysis/phase4_lives_gameover.json": _sha256(C16_ARTIFACT),
        "analysis/phase4_event_vm.json": _sha256(E07_ARTIFACT),
    }
    return [] if document.get("source_dependencies") == expected else [
        "C16 death-breadth source dependencies changed"]


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = source_dependency_gaps(document)
    replays = document.get("replays") or []
    if len(replays) != len(hazards.FIXTURES):
        gaps.append("C16 death-breadth replay count changed")
    static = document.get("trigger_static_census") or {}
    try:
        rebuilt_static = build_trigger_static_census()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        rebuilt_static = None
        gaps.append(f"transition-initiator direct-call census failed: {error}")
    if rebuilt_static is not None and static != rebuilt_static:
        gaps.append("transition-initiator direct-call census changed")
    for replay in replays:
        initial = (replay.get("initial") or {}).get("player") or {}
        outcome = replay.get("source_end") or replay.get("final") or {}
        final = outcome.get("player") or {}
        lead = replay.get("lead", "<missing>")
        if not initial or not final or replay.get("player_delta") != _player_delta(
                initial, final):
            gaps.append(f"{lead}: typed player delta changed")
        derived = derive_law_evidence(replay)
        if replay.get("law_evidence") != derived:
            gaps.append(f"{lead}: resident-law derivation changed")
        trace = replay.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"{lead}: cycle-neutral coverage changed")
        if (replay.get("final") or {}).get("ram_sha256") != \
                (trace.get("control") or {}).get("ram_sha256"):
            gaps.append(f"{lead}: final RAM/control identity changed")
        status = (replay.get("final") or {}).get("movie_status") or {}
        recipe = replay.get("extension_recipe") or {}
        expected_frames = recipe.get("derived_frame_count") or \
            ((replay.get("fixture") or {}).get("movie") or {}).get("frames")
        if status.get("reproducible") is not True or \
                status.get("truncated") is not False or \
                status.get("frame_count") != expected_frames or \
                status.get("playing") is not False:
            gaps.append(f"{lead}: complete movie boundary changed")
        if derived["classification"] in {
                "ordinary_respawn_completed", "final_life_game_over_selected"} \
                and derived["required_pcs_present"] is not True:
            gaps.append(f"{lead}: exact resident death law is incomplete")
        trigger = replay.get("first_transition_trigger") or {}
        capture = trigger.get("entry_register_capture") or {}
        if capture.get("valid") is not derive_entry_capture_valid(capture):
            gaps.append(f"{lead}: entry link-register derivation changed")
        attribution = derive_trigger_attribution(trigger, static)
        if trigger.get("attribution") != attribution:
            gaps.append(f"{lead}: trigger attribution derivation changed")
        if attribution.get("exact") is not True:
            gaps.append(f"{lead}: exact first trigger producer is incomplete")
        before = trigger.get("before") or {}
        after = trigger.get("after") or {}
        if trigger.get("movie_frame", 0) <= 0 or \
                after.get("cycle", 0) <= before.get("cycle", 0) or \
                after.get("emulator_frame", 0) <= before.get(
                    "emulator_frame", 0):
            gaps.append(f"{lead}: trigger timing boundary changed")
        for side in (before, after):
            side_trace = side.get("cycle_neutral_trace") or {}
            if (side_trace.get("comparison") or {}).get(
                    "cycle_neutral") is not True or any(
                        row.get("truncated")
                        for row in side_trace.get("coverage") or []):
                gaps.append(f"{lead}: trigger caller coverage changed")
        outcome = trigger.get("health_lives_outcome") or {}
        outcome_before = outcome.get("before") or {}
        outcome_after = outcome.get("after") or {}
        if outcome.get("movie_frame", 0) < trigger.get("movie_frame", 0) or \
                outcome_after.get("cycle", 0) <= outcome_before.get("cycle", 0):
            gaps.append(f"{lead}: typed trigger outcome timing changed")
        for side in (outcome_before, outcome_after):
            side_trace = side.get("cycle_neutral_trace") or {}
            if (side_trace.get("comparison") or {}).get(
                    "cycle_neutral") is not True or any(
                        row.get("truncated")
                        for row in side_trace.get("coverage") or []):
                gaps.append(f"{lead}: typed trigger outcome coverage changed")
    if document.get("summary") != derive_summary(replays):
        gaps.append("C16 death-breadth summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned live process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixtures = hazards.build_fixture_census()
    trigger_static_census = build_trigger_static_census()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.runUntilAddress",
        "debugger.getRegisters", "emulator.getMediaInfo",
        "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.traceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C16 breadth methods: {missing}")
    client.call("debugger.pause", {})
    inspections = [
        inspect_state_before_load(client, ROOT / row["save"]["path"],
                                  media_identity)
        for row in fixtures["pairs"]
    ]
    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-c16-death-breadth-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        replays = [
            _run_movie(client, row, temp_dir, trigger_static_census)
            for row in fixtures["pairs"]
        ]
    final_media = verified_media_identity(client, client.call("debugger.status", {}))
    source_dependencies = {
        "tools/phase4_e08_hazard_outcomes.py": _sha256(
            ROOT / "tools/phase4_e08_hazard_outcomes.py"),
        "tools/phase4_e08_operator_contacts.py": _sha256(
            ROOT / "tools/phase4_e08_operator_contacts.py"),
        "analysis/phase4_e08_hazard_outcomes.json": _sha256(E10_ARTIFACT),
        "analysis/phase4_lives_gameover.json": _sha256(C16_ARTIFACT),
        "analysis/phase4_event_vm.json": _sha256(E07_ARTIFACT),
    }
    provenance = finish_run(
        args, generator="tools/phase4_lives_death_breadth.py",
        anchor={
            "type": "eight existing state-anchored E10 natural damage leads",
            "saves": [row["save"]["path"] for row in fixtures["pairs"]],
            "fixture_sha256": {
                row["save"]["path"]: row["save"]["sha256"]
                for row in fixtures["pairs"]
            },
            "state_inspections": inspections,
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_end_rule": "consume every recorded frame",
            "trace_mode": (
                "movie.traceToFrame cached-interpreter control/coverage pairs"),
            "classification_rule": (
                "typed health/lives/scene plus exact caller/target/store and "
                "resident death-law PC coverage; filenames assign no owner"),
        })
    document = {
        "_comment": (
            "C16 supporting breadth from complete natural E10 leads. Hazard "
            "filenames remain discovery metadata and confer no E10 ownership."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-death-breadth/2",
        "campaign_state": "active_partial",
        "fixture_census": fixtures,
        "resident_law": {
            "trace_ranges": list(TRACE_RANGES),
            "decisive_pcs": DECISIVE_PCS,
            "authority": "analysis/phase4_lives_gameover.json",
        },
        "trigger_static_census": trigger_static_census,
        "replays": replays,
        "summary": derive_summary(replays),
        "bounded_interpretation": {
            "observation": (
                "Complete natural replays expose typed health/lives boundaries "
                "and exact first producer-call/target/store plus resident "
                "scene-flow/respawn coverage across multiple scenes."),
            "inference": (
                "Each retained path reaches the resident transition initiator "
                "from one statically enumerated native producer boundary. Paths "
                "with the exact death-law PCs share C16's final-life or ordinary-"
                "respawn law; the E10 hazard kind and actor owner remain unknown."),
            "causal_confirmation": (
                "The one-frame health/lives divergence executes one newly reached "
                "enumerated direct call, 0x8004A700 and its health store. Every "
                "pass is byte/register/cycle/frame equal to its uninstrumented "
                "replay; the joined control is execution identity, not a filename."),
            "forbidden_claim": (
                "Do not assign a hazard kind, scripted/special classification, "
                "E10 actor owner, overlay-private predicate, persistence law, or "
                "C16 completion from these natural leads."),
        },
        "bounded_open_frontier": {
            "trigger_ownership": (
                "E10 must still identify the hazard kind and actor/script owner; "
                "this pass closes only the exact native producer-call boundary."),
            "frontend_card": (
                "Continue alternatives, corrupt/no-card behavior and native card "
                "effects remain open."),
            "stage_breadth": (
                "The retained scenes widen C16 but do not cover every campaign, "
                "bonus, boss, scripted or exceptional death path."),
            "next_experiment": (
                "Use the existing frontend movie/card fixtures to separate "
                "Continue refusal/alternatives and serialized effects."),
        },
        "source_dependencies": source_dependencies,
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 breadth evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(
        "[c16-death-breadth] "
        f"{document['summary']['death_paths_joined_to_exact_resident_law']} "
        "natural death paths joined; campaign remains active_partial")
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
                args, generator="tools/phase4_lives_death_breadth.py",
                anchor={"type": "aborted before retained C16 breadth evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned C16 breadth cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
