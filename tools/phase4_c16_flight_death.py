#!/usr/bin/env python3
"""Bind one Riverbed Flight actor contact to the ordinary C16 death law.

The generator starts from the centrally pinned pristine ``level_14.sav``
anchor.  It creates a trigger by moving only the player mirrors beside one live
actor, then compares natural and response-only branches at an identical
boundary.  Transient neutral movies exist only under /tmp so passive coverage
can prove the response-only branch suppresses the resident damage call without
changing the endpoint frame or cycle.
"""
from __future__ import annotations

import argparse
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
    import phase4_c16_bonus_death as base
    import phase4_e08_operator_contacts as contacts
    import phase4_lives_death_breadth as breadth
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_c16_flight_death
    from tools.build_identity import verify_staged_input
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_lives_death_breadth as breadth
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_c16_flight_death.json"
SAVE_REL = "level_14.sav"
SAVE = ROOT / SAVE_REL
SAVE_SHA256 = "6e56d8c4780851f85059b477186b5b1346e23ed7e8eac79a134192e03fef5f50"
SCENE_GRAPH = ROOT / "analysis/phase3_scene_asset_graph.json"
DEATH_MATRIX = ROOT / "analysis/phase2_death_matrix.json"
OUTCOME_JOIN = ROOT / "analysis/phase4_e08_outcome_join.json"
RESPAWN_WRITERS = ROOT / "analysis/phase4_respawn_writer_catalog.json"
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800

SCENE = 0x80082504
MASTER_STATE = 0x800823A0
HEALTH = 0x800A6594
LIVES = 0x800A65A0
PLAYER_XYZ = (0x800A6500, 0x800A6504, 0x800A6508)
PLAYER_PREV_XYZ = (0x800A6510, 0x800A6514, 0x800A6518)

ACTOR_POOL_BASE = 0x8009FD80
ACTOR_STRIDE = 0x84
ACTOR = 0x800A0014
ACTOR_SLOT = 5
ACTOR_ID = 37
ACTOR_CALLBACK = 0x80049E88
ACTOR_SOURCE = 0x80094AC4
ACTOR_FLAGS = ACTOR + 0x5C
RESPONSE_ONLY_BIT = 0x0080
SOURCE_TYPE_WORD = 0x0125

TRANSITION_ENTRY = 0x8004A700
EXPECTED_CALL = 0x8004B4A0
EXPECTED_RETURN = 0x8004B4A8
EXPECTED_CALL_WORD = 0x0C0129C0
ANCHOR_FRAME = 223733
BOUNDARY_FRAME = 223793
OUTCOME_FRAME = 223853
RESPAWN_FRAME = 223973
SETUP_FRAMES = 60
OUTCOME_FRAMES = 60
TRACE_FRAMES = 180

LEVEL08_INITIALIZER = 0x800B3AE8
LEVEL08_INITIALIZER_END = 0x800B3B54
LEVEL08_CALL = 0x8005B1A4
LEVEL08_RETURN = 0x8005B1AC
LEVEL08_CALL_WORD = 0x0C02CEBA
LEVEL08_SAFE = {
    "x": (0x800A6550, 4),
    "y": (0x800A6554, 4),
    "z": (0x800A6558, 4),
    "heading": (0x800A6578, 2),
}
LEVEL08_LIVE = {
    "x": (0x800A6500, 4),
    "y": (0x800A6504, 4),
    "z": (0x800A6508, 4),
}
LEVEL08_EXPECTED_TUPLE = {
    "x": -157682, "y": 5744, "z": -12845, "heading": 352,
}
LEVEL08_INITIALIZER_RANGE = {
    "start": f"0x{LEVEL08_INITIALIZER:08X}",
    # movie.traceToFrame ranges are inclusive; the catalog's runtime_end is
    # exclusive, so stop on the final instruction word rather than admitting
    # the caller's return PC at 0x800B3B54.
    "end": f"0x{LEVEL08_INITIALIZER_END - 4:08X}",
    "label": "level08_fixed_safe_live_initializer", "max_pcs": 200000,
}
LEVEL08_CAUSAL_BRANCHES = (
    ("control", None, None),
    ("x_source_plus_4096", 0x800B3AF0, 0x34A5A80E),
    ("heading_source_plus_one", 0x800B3AFC, 0x24020161),
)

COVERAGE_RANGES = (
    breadth.TRACE_RANGES[0],
    breadth.TRACE_RANGES[1],
    breadth.TRACE_RANGES[2],
    next(row for row in breadth.TRIGGER_TRACE_RANGES
         if row["label"] == "proximity_updater"),
    LEVEL08_INITIALIZER_RANGE,
    next(row for row in breadth.TRIGGER_TRACE_RANGES
         if row["label"] == "region_a_scene_overlay"),
)


def _sha256(path: Path) -> str:
    return base._sha256(path)


def _s32(value: int) -> int:
    return value & 0xFFFFFFFF


def _write_u32(client: Any, address: int, value: int) -> dict[str, Any]:
    result = client.call("debugger.writeU32", {
        "address": f"0x{address:08X}", "value": _s32(value)})
    actual = struct.unpack("<i", base._read_memory(client, address, 4))[0]
    if actual != value:
        raise SystemExit(
            f"Riverbed Flight checked write failed at 0x{address:08X}: {actual}")
    return result


def _actor_record(client: Any) -> dict[str, Any]:
    raw = base._read_memory(client, ACTOR, ACTOR_STRIDE)
    source_pointer = struct.unpack_from("<I", raw, 0x80)[0]
    source = base._read_memory(client, source_pointer, 0x1C)
    actor_id = source[0x0C]
    selector = source[0x0D]
    type_word = (selector << 8) | actor_id
    return {
        "address": f"0x{ACTOR:08x}",
        "pool_slot": (ACTOR - ACTOR_POOL_BASE) // ACTOR_STRIDE,
        "id": struct.unpack_from("<I", raw, 0)[0],
        "xyz": list(struct.unpack_from("<iii", raw, 4)),
        "flags": f"0x{struct.unpack_from('<H', raw, 0x5C)[0]:04x}",
        "callback": f"0x{struct.unpack_from('<I', raw, 0x7C)[0]:08x}",
        "source_pointer": f"0x{source_pointer:08x}",
        "record_sha256": hashlib.sha256(raw).hexdigest(),
        "source": {
            "length": len(source),
            "sha256": hashlib.sha256(source).hexdigest(),
            "type_word": f"0x{type_word:04x}",
            "actor_id_low_byte": actor_id,
            "program_selector_high_byte": selector,
        },
    }


def _snapshot(client: Any, *, full_identity: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    result = {
        "emulator_frame": status["frame"],
        "cycle": status["cycle"],
        "pc": str(status["pc"]).lower(),
        "sp": str(status["sp"]).lower(),
        "scene": struct.unpack("<I", base._read_memory(client, SCENE, 4))[0],
        "master_state": struct.unpack(
            "<H", base._read_memory(client, MASTER_STATE, 2))[0],
        "health": struct.unpack("<h", base._read_memory(client, HEALTH, 2))[0],
        "lives": base._read_memory(client, LIVES, 1)[0],
        "player_xyz": [
            struct.unpack("<i", base._read_memory(client, address, 4))[0]
            for address in PLAYER_XYZ],
        "player_previous_xyz": [
            struct.unpack("<i", base._read_memory(client, address, 4))[0]
            for address in PLAYER_PREV_XYZ],
        "actor": _actor_record(client),
    }
    if full_identity:
        ram = base._main_ram(client)
        result["main_ram_sha256"] = hashlib.sha256(ram).hexdigest()
        result["registers_sha256"] = base._register_sha256(client)
    return result


def build_fixture_census() -> dict[str, Any]:
    save = verify_declared_save_fixture(
        SAVE, allowed_media_classes={"pristine"})
    if save != {
            "path": SAVE_REL, "sha256": SAVE_SHA256, "size": 2069312,
            "media_class": "pristine",
            "manifest": "analysis/phase0_2_external_fixture_set.json"}:
        raise SystemExit(f"Riverbed Flight save pin drifted: {save}")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "inventory_scope": (
            "selected after recursively enumerating movies/Phase4 and the "
            "broader operator movie tree; no dedicated scripted-death movie "
            "was substituted for this existing pristine stage anchor"),
        "save": save,
        "classification_boundary": (
            "The stage filename and serialized game serial are leads only. "
            "Central byte pins, load-free state inspection, pristine mounted "
            "media, live actor bytes, exact call registers and causal control "
            "carry the retained claim."),
    }


def build_context_identity() -> dict[str, Any]:
    scene = (json.loads(SCENE_GRAPH.read_text()).get("scenes") or {}).get(
        "scene_08") or {}
    historical = (json.loads(DEATH_MATRIX.read_text()).get("matrix") or {}).get(
        "stage14_riverbed_flight") or {}
    joined = json.loads(OUTCOME_JOIN.read_text())
    type_row = next(
        (row for row in joined.get("type_words") or []
         if row.get("type_word") == "0x0125"), {})
    result = {
        "scene_graph": {key: scene.get(key) for key in (
            "scene_id", "asset_entry", "disc_dir", "overlays",
            "phase2_stage_labels")},
        "historical_phase2_lead": {
            "anchor": historical.get("anchor"),
            "death_observed": historical.get("death_observed"),
            "record_index": (historical.get("via_record") or {}).get("index"),
            "record_id": (historical.get("via_record") or {}).get("id"),
            "respawn": historical.get("respawn"),
            "qualification": (
                "Phase-2's index was from an older off-by-one pool scan. It is "
                "a discovery lead only; the corrected live slot is 5."),
        },
        "retained_type_word_frontier": {
            "type_word": type_row.get("type_word"),
            "actor_id": type_row.get("actor_id"),
            "program_selector": type_row.get("program_selector"),
            "callbacks": type_row.get("callbacks"),
            "owner_classification": type_row.get("e08_owner_classification"),
        },
    }
    expected_scene = {
        "scene_id": 8, "asset_entry": "level05\\level3b",
        "disc_dir": "level05",
        "overlays": {"LEVEL05_LEVEL": 8, "LEVEL05_LEVEL1": 6},
        "phase2_stage_labels": ["stage14_riverbed_flight"],
    }
    if result["scene_graph"] != expected_scene or \
            result["historical_phase2_lead"]["anchor"] != SAVE_REL or \
            result["historical_phase2_lead"]["death_observed"] is not True or \
            result["historical_phase2_lead"]["record_id"] != ACTOR_ID or \
            result["retained_type_word_frontier"] != {
                "type_word": "0x0125", "actor_id": 37,
                "program_selector": 1, "callbacks": ["0x80049E88"],
                "owner_classification":
                    "unclassified_e08_or_downstream_candidate"}:
        raise SystemExit(f"Riverbed Flight context routing drifted: {result}")
    return result


def _exe_slice(executable: bytes, address: int, length: int) -> bytes:
    offset = EXE_HEADER + address - EXE_LOAD
    result = executable[offset:offset + length]
    if len(result) != length:
        raise SystemExit(f"short executable slice at 0x{address:08X}")
    return result


def build_level08_respawn_static_policy() -> dict[str, Any]:
    """Bind the scene-8 dispatcher and initializer to pristine staged bytes."""
    executable = EXE.read_bytes()
    verify_staged_input(EXE_REL, executable)
    catalog = json.loads(RESPAWN_WRITERS.read_text())
    writer = catalog["writer_functions"]["LEVEL08/LEVEL.BIN"]
    level = (ROOT / writer["path"]).read_bytes()
    verify_staged_input("LEVEL08/LEVEL.BIN", level)
    offset = int(writer["file_offset"], 16)
    body = level[offset:offset + writer["size"]]
    body_sha256 = hashlib.sha256(body).hexdigest()
    if body_sha256 != writer["sha256"] or \
            int(writer["runtime_start"], 16) != LEVEL08_INITIALIZER or \
            int(writer["runtime_end"], 16) != LEVEL08_INITIALIZER_END:
        raise SystemExit("LEVEL08 fixed-initializer catalog identity drifted")
    call_word = struct.unpack(
        "<I", _exe_slice(executable, LEVEL08_CALL, 4))[0]
    if call_word != LEVEL08_CALL_WORD:
        raise SystemExit("resident scene-8 initializer call drifted")
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}",
            "sha256": hashlib.sha256(executable).hexdigest(),
        },
        "catalog": {
            "path": RESPAWN_WRITERS.relative_to(ROOT).as_posix(),
            "sha256": _sha256(RESPAWN_WRITERS),
            "level08_writer": writer,
        },
        "resident_scene8_call": {
            "scene": 8, "address": f"0x{LEVEL08_CALL:08x}",
            "instruction_word": f"0x{call_word:08x}",
            "target": f"0x{LEVEL08_INITIALIZER:08x}",
            "return": f"0x{LEVEL08_RETURN:08x}",
        },
        "staged_initializer": {
            "path": writer["path"], "file_sha256": writer["file_sha256"],
            "file_offset": writer["file_offset"], "size": writer["size"],
            "runtime_range": [writer["runtime_start"], writer["runtime_end"]],
            "sha256": body_sha256, "classification": writer["classification"],
            "direct_writes": writer["direct_writes"],
        },
        "interpretation": (
            "The resident scene-8 jump-table arm calls the reused Region-A "
            "address. Exact loaded-byte identity remains required before the "
            "staged LEVEL08 role is assigned."),
    }


def _level08_snapshot(client: Any, *, full_identity: bool = False
                      ) -> dict[str, Any]:
    result = _snapshot(client, full_identity=full_identity)
    result["safe"] = {
        name: int.from_bytes(
            base._read_memory(client, address, width), "little",
            signed=name != "heading")
        for name, (address, width) in LEVEL08_SAFE.items()
    }
    result["live_xyz"] = [
        int.from_bytes(base._read_memory(client, address, width), "little",
                       signed=True)
        for address, width in LEVEL08_LIVE.values()
    ]
    return result


def _inspect_transient_state(client: Any, state: Path) -> dict[str, Any]:
    info = client.call("emulator.getStateInfo", {"path": str(state.resolve())})
    if info.get("valid") is not True or info.get("version") != 84 or \
            info.get("serial") != "SCUS-94288" or \
            Path(info.get("media_path") or "").name != \
            "Disney-Pixar A Bug's Life (v1.0).cue":
        raise SystemExit(f"transient LEVEL08 entry state invalid: {info}")
    return {
        "valid": info["valid"], "version": info["version"],
        "serial": info["serial"], "media_path": info["media_path"],
        "size": state.stat().st_size, "sha256": _sha256(state),
    }


def _capture_level08_respawn_activation(
        client: Any, static_policy: dict[str, Any],
        natural_trace: dict[str, Any], response_trace: dict[str, Any]
        ) -> dict[str, Any]:
    """Qualify the staged LEVEL08 initializer on the natural scene-8 respawn."""
    prepared = _prepare_boundary(client)
    # Stop on the resident call before entering the overlay.  Passive movie
    # coverage below remains the timing authority for the first respawn;
    # runUntilAddress catches a later natural recurrence after the cached-block
    # pass and supplies an exact call/entry boundary for narrow causality.
    client.call("debugger.runUntilAddress", {
        "address": f"0x{LEVEL08_CALL:08X}"})
    base._wait_for_pause(client, "LEVEL08 resident initializer call")
    call_boundary = _level08_snapshot(client, full_identity=True)
    call_word = struct.unpack(
        "<I", base._read_memory(client, LEVEL08_CALL, 4))[0]
    if call_boundary["pc"] != f"0x{LEVEL08_CALL:08x}" or \
            call_word != LEVEL08_CALL_WORD:
        raise SystemExit(
            f"LEVEL08 first natural call boundary drifted: {call_boundary}")
    client.call("debugger.runUntilAddress", {
        "address": f"0x{LEVEL08_INITIALIZER:08X}"})
    base._wait_for_pause(client, "LEVEL08 fixed initializer entry")
    entry = _level08_snapshot(client, full_identity=True)
    registers = {
        str(key).lower(): str(value).lower() for key, value in
        client.call("debugger.getRegisters", {})["registers_hex"].items()}
    runtime = base._read_memory(
        client, LEVEL08_INITIALIZER,
        static_policy["staged_initializer"]["size"])
    runtime_sha256 = hashlib.sha256(runtime).hexdigest()
    runtime_identity = {
        "address": f"0x{LEVEL08_INITIALIZER:08x}", "length": len(runtime),
        "sha256": runtime_sha256,
        "pinned_sha256": static_policy["staged_initializer"]["sha256"],
        "exact_pristine_match": runtime_sha256 ==
            static_policy["staged_initializer"]["sha256"],
    }

    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-level08-initializer-", dir="/tmp") as temp_text:
        state = Path(temp_text) / "initializer-entry.sav"
        saved = client.call("emulator.saveState", {"path": str(state.resolve())})
        if saved.get("saved") is not True:
            raise SystemExit(f"failed to save LEVEL08 entry state: {saved}")
        transient = _inspect_transient_state(client, state)

        client.call("accessLog.clear", {})
        watches: dict[int, str] = {}
        for prefix, fields in (("safe", LEVEL08_SAFE), ("live", LEVEL08_LIVE)):
            for name, (address, width) in fields.items():
                watch = client.call("accessLog.addWatch", {
                    "address": f"0x{address:08X}", "length": width,
                    "type": "write", "label": f"{prefix}_{name}",
                    "max_events": 32})
                watches[int(watch["watch_id"])] = f"{prefix}_{name}"
        client.call("debugger.runUntilAddress", {
            "address": f"0x{LEVEL08_RETURN:08X}"})
        base._wait_for_pause(client, "LEVEL08 fixed initializer return")
        page = client.call("accessLog.get", {"offset": 0, "limit": 128})
        client.call("accessLog.clear", {})
        events = [
            {**row, "field": watches.get(int(row.get("watch_id", -1)))}
            for row in page.get("events") or []]
        attribution = {
            "execution_mode_boundary": (
                "accessLog forces interpreter execution and attributes the "
                "seven direct writes only; passive traceToFrame evidence is "
                "the timing authority."),
            "events": events, "total": page.get("total"),
            "returned": len(events), "truncated": page.get("truncated", False),
            "after_return": _level08_snapshot(client, full_identity=True),
        }

        expected_words = {
            0x800B3AF0: 0x34A5980E,
            0x800B3AFC: 0x24020160,
        }
        branches = []
        for label, patch_address, patch_value in LEVEL08_CAUSAL_BRANCHES:
            inspection = _inspect_transient_state(client, state)
            loaded = client.call("emulator.loadState", {
                "path": str(state.resolve()), "pause_after_load": True,
                "validate_disc": True, "auto_select_disc": False})
            if loaded.get("loaded") is not True:
                raise SystemExit(f"failed to reload LEVEL08 entry state: {loaded}")
            media = verified_media_identity(
                client, client.call("debugger.status", {}))
            origin = _level08_snapshot(client, full_identity=True)
            mutation = None
            if patch_address is not None and patch_value is not None:
                old_word = struct.unpack(
                    "<I", base._read_memory(client, patch_address, 4))[0]
                if old_word != expected_words[patch_address]:
                    raise SystemExit(
                        f"LEVEL08 branch source drifted at 0x{patch_address:08X}")
                response = client.call("debugger.writeU32", {
                    "address": f"0x{patch_address:08X}", "value": patch_value})
                new_word = struct.unpack(
                    "<I", base._read_memory(client, patch_address, 4))[0]
                if response.get("written") != 4 or \
                        response.get("code_invalidated") is not True or \
                        new_word != patch_value:
                    raise SystemExit(f"LEVEL08 branch patch failed: {response}")
                mutation = {
                    "address": f"0x{patch_address:08x}",
                    "before_word": f"0x{old_word:08x}",
                    "after_word": f"0x{new_word:08x}",
                    "written": response["written"],
                    "code_invalidated": response["code_invalidated"],
                    "scope": (
                        "one runtime source instruction in a transient same-"
                        "origin branch; no disc or retained fixture changed"),
                }
            client.call("debugger.runUntilAddress", {
                "address": f"0x{LEVEL08_RETURN:08X}"})
            base._wait_for_pause(client, f"LEVEL08 {label} return")
            branches.append({
                "label": label, "state_inspection": inspection,
                "mounted_media_pristine_verified":
                    (media.get("hash_verification") or {}).get(
                        "pristine_verified") is True,
                "origin": origin, "mutation": mutation,
                "after_return": _level08_snapshot(client, full_identity=True),
            })
        transient_recipe = {
            **transient,
            "origin": "saved at the natural scene-8 initializer entry",
            "storage": "temporary directory deleted before artifact retention",
            "deleted_before_retention": True, "loads": len(branches),
        }

    result = {
        "fixture": build_fixture_census()["save"],
        "static_policy": static_policy,
        "passive_natural_trace": natural_trace["traces"]["180"][
            "cycle_neutral_trace"],
        "passive_negative_trace": response_trace["traces"]["180"][
            "cycle_neutral_trace"],
        "prepared_natural_trigger": prepared,
        "exact_resident_call": {
            "pc": call_boundary["pc"],
            "instruction_word": f"0x{call_word:08x}",
            "resolved_target": f"0x{LEVEL08_INITIALIZER:08x}",
            "snapshot": call_boundary,
        },
        "exact_entry": {
            "pc": entry["pc"], "ra": registers["ra"],
            "link_call_address": f"0x{LEVEL08_CALL:08x}",
            "instruction_word": f"0x{LEVEL08_CALL_WORD:08x}",
            "resolved_target": f"0x{LEVEL08_INITIALIZER:08x}",
            "snapshot": entry,
        },
        "runtime_identity": runtime_identity,
        "writer_attribution": attribution,
        "causal_branches": branches,
        "transient_state_recipe": transient_recipe,
        "bounded_interpretation": {
            "observation": (
                "The natural scene-8 ordinary respawn executes the exact "
                "resident call and all 27 instructions of the loaded "
                "initializer; seven direct writes install safe XYZ/heading "
                "and live XYZ."),
            "inference": (
                "Exact runtime-byte equality qualifies this loaded Region-A "
                "function as the pinned pristine LEVEL08 initializer."),
            "causal_confirmation": (
                "At the same natural entry, changing only the X source by "
                "+4096 changes safe and live X by +4096; changing only the "
                "heading source by +1 changes only safe heading. All branches "
                "return at the same frame/cycle/PC/SP boundary."),
            "negative_control": (
                "The one-byte actor response-only branch prevents contact "
                "damage, death, respawn-handler execution and initializer "
                "execution at the matched endpoint."),
            "forbidden_claim": (
                "Do not infer authored checkpoint-row provenance, universal "
                "selector policy, persistence, actor species, or all-stage "
                "death breadth from this controlled scene-8 path."),
        },
    }
    gaps = _level08_activation_gaps(result)
    if gaps:
        raise SystemExit(f"LEVEL08 respawn activation failed: {gaps}")
    return result


def _level08_activation_gaps(result: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    policy = result.get("static_policy") or {}
    call = policy.get("resident_scene8_call") or {}
    if call != {
            "scene": 8, "address": "0x8005b1a4",
            "instruction_word": "0x0c02ceba", "target": "0x800b3ae8",
            "return": "0x8005b1ac"}:
        gaps.append("LEVEL08 resident selector call changed")
    if (result.get("runtime_identity") or {}).get(
            "exact_pristine_match") is not True:
        gaps.append("LEVEL08 loaded bytes no longer match pristine staged input")
    exact = result.get("exact_entry") or {}
    resident = result.get("exact_resident_call") or {}
    if (resident.get("pc"), resident.get("instruction_word"),
            resident.get("resolved_target")) != (
                "0x8005b1a4", "0x0c02ceba", "0x800b3ae8") or \
            ((resident.get("snapshot") or {}).get("scene")) != 8:
        gaps.append("LEVEL08 exact later natural resident call changed")
    if (exact.get("pc"), exact.get("ra"), exact.get("link_call_address")) != (
            "0x800b3ae8", "0x8005b1ac", "0x8005b1a4") or \
            ((exact.get("snapshot") or {}).get("scene")) != 8:
        gaps.append("LEVEL08 exact natural entry changed")

    def coverage(trace: dict[str, Any]) -> dict[str, Any]:
        return next((row for row in trace.get("coverage") or []
                     if row.get("label") ==
                     "level08_fixed_safe_live_initializer"), {})

    natural = coverage(result.get("passive_natural_trace") or {})
    negative = coverage(result.get("passive_negative_trace") or {})
    expected_pcs = [f"0x{pc:08x}" for pc in range(
        LEVEL08_INITIALIZER, LEVEL08_INITIALIZER_END, 4)]
    if natural.get("total_hits") != 27 or \
            natural.get("distinct_pc_count") != 27 or \
            natural.get("pcs") != expected_pcs or \
            natural.get("truncated") is not False or \
            negative.get("total_hits") != 0:
        gaps.append("LEVEL08 passive positive/negative activation changed")
    attribution = result.get("writer_attribution") or {}
    events = attribution.get("events") or []
    expected_fields = {
        "safe_x", "safe_y", "safe_z", "safe_heading",
        "live_x", "live_y", "live_z"}
    if attribution.get("total") != 7 or attribution.get("returned") != 7 or \
            attribution.get("truncated") is not False or \
            {row.get("field") for row in events} != expected_fields:
        gaps.append("LEVEL08 complete direct-write attribution changed")
    after = attribution.get("after_return") or {}
    if after.get("safe") != LEVEL08_EXPECTED_TUPLE or \
            after.get("live_xyz") != [
                LEVEL08_EXPECTED_TUPLE[name] for name in ("x", "y", "z")]:
        gaps.append("LEVEL08 fixed safe/live tuple changed")
    branches = {row.get("label"): row for row in
                result.get("causal_branches") or []}
    control = (branches.get("control") or {}).get("after_return") or {}
    x_plus = (branches.get("x_source_plus_4096") or {}).get(
        "after_return") or {}
    heading_plus = (branches.get("heading_source_plus_one") or {}).get(
        "after_return") or {}
    if control.get("safe") != LEVEL08_EXPECTED_TUPLE or \
            x_plus.get("safe") != {
                **LEVEL08_EXPECTED_TUPLE,
                "x": LEVEL08_EXPECTED_TUPLE["x"] + 4096} or \
            x_plus.get("live_xyz") != [
                LEVEL08_EXPECTED_TUPLE["x"] + 4096,
                LEVEL08_EXPECTED_TUPLE["y"], LEVEL08_EXPECTED_TUPLE["z"]] or \
            heading_plus.get("safe") != {
                **LEVEL08_EXPECTED_TUPLE,
                "heading": LEVEL08_EXPECTED_TUPLE["heading"] + 1} or \
            heading_plus.get("live_xyz") != control.get("live_xyz"):
        gaps.append("LEVEL08 source-constant causal branches changed")
    branch_endpoints = [
        tuple((row.get("after_return") or {}).get(key)
              for key in ("emulator_frame", "cycle", "pc", "sp"))
        for row in branches.values()]
    if len(branch_endpoints) != 3 or len(set(branch_endpoints)) != 1 or \
            not all(row.get("mounted_media_pristine_verified") is True
                    for row in branches.values()):
        gaps.append("LEVEL08 causal branch origin/endpoint identity changed")
    return gaps


def _load_anchor(client: Any) -> dict[str, Any]:
    base._cleanup(client)
    loaded = client.call("emulator.loadState", {
        "path": str(SAVE.resolve()), "pause_after_load": True,
        "validate_disc": True, "auto_select_disc": False})
    client.call("emulator.clearControllerState", {"port": 0})
    anchor = _snapshot(client, full_identity=True)
    if (anchor["emulator_frame"], anchor["scene"], anchor["health"],
            anchor["lives"], anchor["master_state"]) != (
                ANCHOR_FRAME, 8, 4, 0, 0):
        raise SystemExit(f"Riverbed Flight anchor drifted: {anchor}")
    actor = anchor["actor"]
    if (actor["pool_slot"], actor["id"], actor["xyz"], actor["callback"],
            actor["source_pointer"], actor["source"]["type_word"]) != (
                5, 37, [-139776, -384, 320288], "0x80049e88",
                "0x80094ac4", "0x0125"):
        raise SystemExit(f"Riverbed Flight actor anchor drifted: {actor}")
    return {"load": loaded, "snapshot": anchor}


def _apply_trigger_setup(client: Any) -> dict[str, Any]:
    actor_xyz = _actor_record(client)["xyz"]
    target = [actor_xyz[0] - 250, actor_xyz[1] - 6000, actor_xyz[2] - 250]
    writes = [
        client.call("debugger.writeU16", {
            "address": f"0x{HEALTH:08X}", "value": 0}),
        client.call("debugger.writeU8", {
            "address": f"0x{LIVES:08X}", "value": 3}),
    ]
    for address, value in zip(PLAYER_XYZ, target):
        writes.append(_write_u32(client, address, value))
    for address, value in zip(PLAYER_PREV_XYZ, target):
        writes.append(_write_u32(client, address, value))
    result = {
        "actor_xyz": actor_xyz, "target_player_xyz": target,
        "writes": [
            {"address": "0x800a6594", "width": "u16", "value": 0},
            {"address": "0x800a65a0", "width": "u8", "value": 3},
            *[
                {"address": f"0x{address:08x}", "width": "u32",
                 "value_signed": value, "value_u32": _s32(value)}
                for address, value in zip(
                    (*PLAYER_XYZ, *PLAYER_PREV_XYZ), (*target, *target))],
        ],
        "responses": writes,
        "classification": (
            "Synthetic trigger setup only: health/lives select ordinary death "
            "and both live/previous XYZ mirrors move together. No actor field, "
            "code byte, scene state, or external fixture is changed."),
    }
    return result


def _prepare_boundary(client: Any, *, early_response_only: bool = False
                      ) -> dict[str, Any]:
    anchor = _load_anchor(client)
    setup = _apply_trigger_setup(client)
    early = None
    if early_response_only:
        before = struct.unpack("<H", base._read_memory(client, ACTOR_FLAGS, 2))[0]
        response = client.call("debugger.writeU16", {
            "address": f"0x{ACTOR_FLAGS:08X}",
            "value": before | RESPONSE_ONLY_BIT})
        early = {"before": f"0x{before:04x}",
                 "after": f"0x{before | RESPONSE_ONLY_BIT:04x}",
                 "response": response}
    client.call("emulator.advanceFrames", {"frames": SETUP_FRAMES})
    boundary = _snapshot(client, full_identity=True)
    if (boundary["emulator_frame"], boundary["scene"], boundary["health"],
            boundary["lives"], boundary["master_state"]) != (
                BOUNDARY_FRAME, 8, 0, 3, 0):
        raise SystemExit(f"Riverbed Flight prepared boundary drifted: {boundary}")
    if not early_response_only and boundary["actor"]["flags"] != "0x4011":
        raise SystemExit(f"Riverbed Flight actor flags drifted: {boundary['actor']}")
    return {"anchor": anchor, "setup": setup,
            "early_response_only": early, "boundary": boundary}


def _write_response_only(client: Any) -> dict[str, Any]:
    before_ram = base._main_ram(client)
    before = struct.unpack("<H", base._read_memory(client, ACTOR_FLAGS, 2))[0]
    response = client.call("debugger.writeU16", {
        "address": f"0x{ACTOR_FLAGS:08X}",
        "value": before | RESPONSE_ONLY_BIT})
    after_ram = base._main_ram(client)
    differences = [
        {"address": f"0x{0x80000000 + index:08x}",
         "before": left, "after": right}
        for index, (left, right) in enumerate(zip(before_ram, after_ram))
        if left != right]
    result = {
        "method": "debugger.writeU16", "address": f"0x{ACTOR_FLAGS:08x}",
        "bit": "0x0080", "before": f"0x{before:04x}",
        "after": f"0x{before | RESPONSE_ONLY_BIT:04x}",
        "response": response, "main_ram_differences": differences,
        "main_ram_difference_count": len(differences),
    }
    if before != 0x4011 or result["after"] != "0x4091" or \
            differences != [{
                "address": "0x800a0070", "before": 0x11, "after": 0x91}]:
        raise SystemExit(f"response-only mutation was not isolated: {result}")
    return result


def _run_matched_outcomes(client: Any) -> dict[str, Any]:
    natural_origin = _prepare_boundary(client)
    client.call("emulator.advanceFrames", {"frames": OUTCOME_FRAMES})
    natural = _snapshot(client, full_identity=True)
    client.call("emulator.advanceFrames", {"frames": TRACE_FRAMES - OUTCOME_FRAMES})
    respawn = _snapshot(client, full_identity=True)

    control_origin = _prepare_boundary(client)
    mutation = _write_response_only(client)
    client.call("emulator.advanceFrames", {"frames": OUTCOME_FRAMES})
    control = _snapshot(client, full_identity=True)
    client.call("emulator.advanceFrames", {"frames": TRACE_FRAMES - OUTCOME_FRAMES})
    control_final = _snapshot(client, full_identity=True)
    endpoint_match = {
        key: natural[key] == control[key]
        for key in ("emulator_frame", "cycle", "pc", "sp")}
    result = {
        "natural_origin": natural_origin,
        "natural_fatal_boundary": natural,
        "natural_ordinary_respawn": respawn,
        "response_only_origin": control_origin,
        "response_only_mutation": mutation,
        "response_only_outcome": control,
        "response_only_final": control_final,
        "outcome_endpoint_identity": endpoint_match,
    }
    if (natural["emulator_frame"], natural["health"], natural["lives"],
            natural["master_state"]) != (OUTCOME_FRAME, -1, 3, 2) or \
            (respawn["emulator_frame"], respawn["scene"], respawn["health"],
             respawn["lives"], respawn["master_state"]) != (
                RESPAWN_FRAME, 8, 4, 2, 0) or \
            (control["emulator_frame"], control["health"], control["lives"],
             control["master_state"]) != (OUTCOME_FRAME, 0, 3, 0) or \
            (control_final["emulator_frame"], control_final["health"],
             control_final["lives"], control_final["master_state"]) != (
                RESPAWN_FRAME, 0, 3, 0) or not all(endpoint_match.values()):
        raise SystemExit(f"Riverbed Flight matched outcomes drifted: {result}")
    return result


def _capture_invocation(client: Any) -> dict[str, Any]:
    prepared = _prepare_boundary(client)
    client.call("debugger.runUntilAddress", {
        "address": f"0x{TRANSITION_ENTRY:08X}"})
    base._wait_for_pause(client, "Riverbed Flight damage entry")
    registers = {
        str(key).lower(): value for key, value in
        client.call("debugger.getRegisters", {})["registers_hex"].items()}
    pc, ra = int(registers["pc"], 16), int(registers["ra"], 16)
    call = (ra - 8) & 0xFFFFFFFF
    word = struct.unpack("<I", base._read_memory(client, call, 4))[0]
    actor = _actor_record(client)
    before = _snapshot(client, full_identity=True)
    client.call("debugger.runUntilAddress", {"address": f"0x{ra:08X}"})
    base._wait_for_pause(client, "Riverbed Flight damage return")
    after = _snapshot(client, full_identity=True)
    result = {
        "prepared": prepared,
        "entry": {
            "pc": f"0x{pc:08x}", "ra": f"0x{ra:08x}",
            "link_call_address": f"0x{call:08x}",
            "instruction_word": f"0x{word:08x}",
            "arguments": {name: registers[name]
                          for name in ("a0", "a1", "a2", "a3")},
            "s1_actor_pointer": registers["s1"].lower(),
        },
        "actor_owner": actor, "before_call": before,
        "after_return": after, "returned_to": f"0x{ra:08x}",
    }
    result["actor_contact_causally_bound"] = bool(
        pc == TRANSITION_ENTRY and call == EXPECTED_CALL and
        ra == EXPECTED_RETURN and word == EXPECTED_CALL_WORD and
        int(registers["a3"], 16) == 0 and
        int(registers["s1"], 16) == ACTOR and
        (actor["pool_slot"], actor["id"], actor["callback"],
         actor["source_pointer"], actor["source"]["type_word"]) == (
            5, 37, "0x80049e88", "0x80094ac4", "0x0125") and
        (before["scene"], before["health"], before["lives"],
         before["master_state"]) == (8, 0, 3, 0) and
        (after["scene"], after["health"], after["lives"],
         after["master_state"]) == (8, -1, 3, 2))
    if result["actor_contact_causally_bound"] is not True:
        raise SystemExit(f"Riverbed Flight invocation drifted: {result}")
    return result


def _coverage(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["label"]: row for row in trace.get("coverage") or []}


def _record_trace_branch(client: Any, temp_dir: Path, *, response_only: bool
                         ) -> dict[str, Any]:
    prepared = _prepare_boundary(client)
    mutation = _write_response_only(client) if response_only else None
    state = temp_dir / ("response-only.sav" if response_only else "natural.sav")
    movie = temp_dir / (
        "response-only.movie.json" if response_only else "natural.movie.json")
    saved = client.call("emulator.saveState", {"path": str(state.resolve())})
    info = client.call("emulator.getStateInfo", {"path": str(state.resolve())})
    if saved.get("saved") is not True or info.get("valid") is not True or \
            info.get("serial") != "SCUS-94288":
        raise SystemExit(f"Riverbed Flight transient state invalid: {saved}/{info}")
    recording = client.call("movie.startRecording", {
        "ports": [0], "start_state": str(state.resolve()),
        "load_start_state": True,
        "notes": "transient neutral C16 Riverbed Flight causal trace"})
    client.call("emulator.clearControllerState", {"port": 0})
    client.call("emulator.advanceFrames", {"frames": TRACE_FRAMES})
    stopped = client.call("movie.stopRecording", {})
    stored = client.call("movie.save", {
        "path": str(movie.resolve()), "overwrite": False})
    if recording.get("recording") is not True or \
            stopped.get("frame_count") != TRACE_FRAMES or \
            stored.get("saved") is not True:
        raise SystemExit(
            f"Riverbed Flight transient movie invalid: {recording}/{stopped}/{stored}")
    traces = {}
    for target in (OUTCOME_FRAMES, TRACE_FRAMES):
        raw = client.call("movie.traceToFrame", {
            "path": str(movie.resolve()), "frame": target,
            "ranges": list(COVERAGE_RANGES)}, timeout=900)
        compact = contacts._compact_trace(raw)
        snapshot = _snapshot(client, full_identity=True)
        if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in compact.get("coverage") or []):
            raise SystemExit(f"Riverbed Flight trace was not neutral: {compact}")
        traces[str(target)] = {
            "snapshot": snapshot, "cycle_neutral_trace": compact}
    return {
        "branch": "response_only" if response_only else "natural",
        "prepared": prepared, "mutation": mutation,
        "recipe": {
            "source_save": SAVE_REL, "source_save_sha256": SAVE_SHA256,
            "start_emulator_frame": BOUNDARY_FRAME,
            "neutral_frames": TRACE_FRAMES, "ports": [0],
            "state_version": info.get("version"),
            "state_serial": info.get("serial"),
            "transient_storage": (
                "temporary directory; generated save/movie deleted before retention"),
        },
        "traces": traces,
    }


def _validate_traces(natural: dict[str, Any], control: dict[str, Any]) -> None:
    natural_60 = _coverage(natural["traces"]["60"]["cycle_neutral_trace"])
    natural_180 = _coverage(natural["traces"]["180"]["cycle_neutral_trace"])
    control_60 = _coverage(control["traces"]["60"]["cycle_neutral_trace"])
    control_180 = _coverage(control["traces"]["180"]["cycle_neutral_trace"])
    pcs = lambda row: {str(pc).lower() for pc in row.get("pcs") or []}
    if not {"0x8004a700", "0x8004a888"}.issubset(
            pcs(natural_60["damage_and_death_initiator"])) or \
            "0x8004b4a0" not in pcs(natural_60["proximity_updater"]) or \
            natural_60["respawn_transition_state_handler"]["total_hits"] != 0 or \
            not {"0x8005b30c", "0x8005b348"}.issubset(
                pcs(natural_180["respawn_transition_state_handler"])) or \
            "0x800500f4" not in pcs(natural_180["scene_flow_dispatcher"]) or \
            control_60["damage_and_death_initiator"]["total_hits"] != 0 or \
            control_180["damage_and_death_initiator"]["total_hits"] != 0 or \
            control_180["respawn_transition_state_handler"]["total_hits"] != 0 or \
            "0x8004b4a0" in pcs(control_180["proximity_updater"]) or \
            natural_180["level08_fixed_safe_live_initializer"][
                "total_hits"] != 27 or \
            natural_180["level08_fixed_safe_live_initializer"][
                "distinct_pc_count"] != 27 or \
            natural_180["level08_fixed_safe_live_initializer"][
                "truncated"] is not False or \
            "0x8005b1a4" not in pcs(
                natural_180["respawn_transition_state_handler"]) or \
            control_180["level08_fixed_safe_live_initializer"][
                "total_hits"] != 0:
        raise SystemExit("Riverbed Flight natural/control coverage predicates drifted")


def _run_failed_early_control(client: Any) -> dict[str, Any]:
    prepared = _prepare_boundary(client, early_response_only=True)
    client.call("emulator.advanceFrames", {"frames": OUTCOME_FRAMES})
    outcome = _snapshot(client, full_identity=True)
    result = {"prepared": prepared, "outcome": outcome,
              "disposition": "rejected_hypothesis"}
    if prepared["boundary"]["actor"]["flags"] != "0x4011" or \
            (outcome["emulator_frame"], outcome["health"], outcome["lives"],
             outcome["master_state"]) != (OUTCOME_FRAME, -1, 3, 2):
        raise SystemExit(f"Riverbed Flight early-control result drifted: {result}")
    return result


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    matched = document.get("matched_outcomes") or {}
    invocation = document.get("exact_invocation") or {}
    natural = matched.get("natural_fatal_boundary") or {}
    respawn = matched.get("natural_ordinary_respawn") or {}
    control = matched.get("response_only_outcome") or {}
    level08 = document.get("shared_c15_level08_respawn_activation") or {}
    return {
        "special_stage_contact_paths_bounded": int(
            invocation.get("actor_contact_causally_bound") is True),
        "scene": natural.get("scene"),
        "actor_pool_slot": (
            invocation.get("actor_owner") or {}).get("pool_slot"),
        "actor_id": (invocation.get("actor_owner") or {}).get("id"),
        "producer_path_id": "proximity_contact",
        "natural_fatal_health": natural.get("health"),
        "ordinary_respawn_health_lives": [
            respawn.get("health"), respawn.get("lives")],
        "response_only_health_lives": [
            control.get("health"), control.get("lives")],
        "response_only_main_ram_difference_count": (
            matched.get("response_only_mutation") or {}).get(
                "main_ram_difference_count"),
        "matched_outcome_frame_cycle_pc_sp": all(
            (matched.get("outcome_endpoint_identity") or {}).values()),
        "level08_respawn_initializer_live_qualified": int(
            (level08.get("runtime_identity") or {}).get(
                "exact_pristine_match") is True and
            not _level08_activation_gaps(level08)),
        "level08_fixed_safe_live_tuple": [
            LEVEL08_EXPECTED_TUPLE[name]
            for name in ("x", "y", "z", "heading")],
        "distinct_special_death_law_promoted": 0,
        "actor_species_promoted": 0,
        "c16_or_f14_completed": 0,
    }


def _source_dependencies() -> dict[str, str]:
    paths = [
        "tools/phase4_c16_bonus_death.py",
        "tools/phase4_e08_operator_contacts.py",
        "tools/phase4_lives_death_breadth.py",
        "analysis/phase2_death_matrix.json",
        "analysis/phase3_scene_asset_graph.json",
        "analysis/phase4_e08_outcome_join.json",
        "analysis/phase4_respawn_writer_catalog.json",
        "analysis/phase0_2_external_fixture_set.json",
    ]
    return {path: _sha256(ROOT / path) for path in paths}


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    try:
        if document.get("fixture_census") != build_fixture_census():
            gaps.append("Riverbed Flight fixture census changed")
        if document.get("context_identity") != build_context_identity():
            gaps.append("Riverbed Flight context identity changed")
        if (document.get("shared_c15_level08_respawn_activation") or {}).get(
                "static_policy") != build_level08_respawn_static_policy():
            gaps.append("LEVEL08 respawn static policy changed")
    except (SystemExit, OSError, json.JSONDecodeError) as exc:
        gaps.append(f"Riverbed Flight static dependency failed: {exc}")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Riverbed Flight source dependency changed")
    matched = document.get("matched_outcomes") or {}
    natural = matched.get("natural_fatal_boundary") or {}
    respawn = matched.get("natural_ordinary_respawn") or {}
    control = matched.get("response_only_outcome") or {}
    mutation = matched.get("response_only_mutation") or {}
    if (natural.get("emulator_frame"), natural.get("scene"),
            natural.get("health"), natural.get("lives"),
            natural.get("master_state")) != (223853, 8, -1, 3, 2) or \
            (respawn.get("emulator_frame"), respawn.get("health"),
             respawn.get("lives"), respawn.get("master_state")) != (
                223973, 4, 2, 0):
        gaps.append("Riverbed Flight natural lifecycle changed")
    if mutation.get("main_ram_differences") != [{
            "address": "0x800a0070", "before": 17, "after": 145}] or \
            (control.get("emulator_frame"), control.get("health"),
             control.get("lives"), control.get("master_state")) != (
                223853, 0, 3, 0) or \
            not all((matched.get("outcome_endpoint_identity") or {}).values()):
        gaps.append("Riverbed Flight response-only control changed")
    invocation = document.get("exact_invocation") or {}
    entry, actor = invocation.get("entry") or {}, invocation.get("actor_owner") or {}
    if invocation.get("actor_contact_causally_bound") is not True or \
            entry.get("link_call_address") != "0x8004b4a0" or \
            entry.get("instruction_word") != "0x0c0129c0" or \
            entry.get("s1_actor_pointer") != "0x800a0014" or \
            (actor.get("pool_slot"), actor.get("id"), actor.get("callback"),
             actor.get("source_pointer")) != (
                5, 37, "0x80049e88", "0x80094ac4"):
        gaps.append("Riverbed Flight exact actor invocation changed")
    traces = document.get("passive_traces") or {}
    try:
        _validate_traces(traces["natural"], traces["response_only"])
    except (KeyError, SystemExit) as exc:
        gaps.append(f"Riverbed Flight passive trace changed: {exc}")
    level08 = document.get("shared_c15_level08_respawn_activation") or {}
    gaps.extend(_level08_activation_gaps(level08))
    failed = document.get("rejected_early_control") or {}
    if ((failed.get("prepared") or {}).get("boundary") or {}).get(
            "actor", {}).get("flags") != "0x4011" or \
            (failed.get("outcome") or {}).get("health") != -1:
        gaps.append("Riverbed Flight rejected early control changed")
    summary = derive_summary(document)
    if document.get("summary") != summary or summary != {
            "special_stage_contact_paths_bounded": 1,
            "scene": 8, "actor_pool_slot": 5, "actor_id": 37,
            "producer_path_id": "proximity_contact",
            "natural_fatal_health": -1,
            "ordinary_respawn_health_lives": [4, 2],
            "response_only_health_lives": [0, 3],
            "response_only_main_ram_difference_count": 1,
            "matched_outcome_frame_cycle_pc_sp": True,
            "level08_respawn_initializer_live_qualified": 1,
            "level08_fixed_safe_live_tuple": [-157682, 5744, -12845, 352],
            "distinct_special_death_law_promoted": 0,
            "actor_species_promoted": 0,
            "c16_or_f14_completed": 0}:
        gaps.append("Riverbed Flight derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Riverbed Flight process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = build_fixture_census()
    context = build_context_identity()
    level08_static_policy = build_level08_respawn_static_policy()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU8", "debugger.writeU16",
        "debugger.writeU32", "debugger.getRegisters",
        "debugger.runUntilAddress", "debugger.clearBreakpoints",
        "accessLog.addWatch", "accessLog.get", "accessLog.clear",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "emulator.loadState", "emulator.saveState", "emulator.advanceFrames",
        "emulator.clearControllerState", "movie.startRecording",
        "movie.stopRecording", "movie.save", "movie.traceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks Riverbed Flight methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, SAVE, media_identity)

    matched = _run_matched_outcomes(client)
    invocation = _capture_invocation(client)
    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-c16-flight-", dir="/tmp") as temp_text:
        temp_dir = Path(temp_text)
        natural_trace = _record_trace_branch(
            client, temp_dir, response_only=False)
        response_trace = _record_trace_branch(
            client, temp_dir, response_only=True)
        _validate_traces(natural_trace, response_trace)
    level08_activation = _capture_level08_respawn_activation(
        client, level08_static_policy, natural_trace, response_trace)
    rejected = _run_failed_early_control(client)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_c16_flight_death.py",
        anchor={
            "type": "existing pristine Riverbed Flight stage anchor",
            "save": SAVE_REL, "fixture_sha256": {SAVE_REL: SAVE_SHA256},
            "state_inspections": [inspection],
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "boundaries": {
                "anchor": ANCHOR_FRAME, "prepared": BOUNDARY_FRAME,
                "outcome": OUTCOME_FRAME, "ordinary_respawn": RESPAWN_FRAME},
            "trace_mode": (
                "fresh transient neutral movies; movie.traceToFrame "
                "uninstrumented versus passive cached-interpreter coverage"),
            "causal_capture": (
                "at identical frame 223793, change only actor state bit 0x0080; "
                "natural and control endpoints must retain frame/cycle/PC/SP; "
                "at the later natural LEVEL08 entry, change only the X or "
                "heading source instruction and compare exact return boundaries"),
        })
    document = {
        "_comment": (
            "Active C16/F14/C15 breadth: one Riverbed Flight actor-owned contact "
            "joins the ordinary resident damage/respawn law and live-qualifies "
            "the pristine LEVEL08 fixed safe/live initializer. This does not "
            "name the actor species, establish a special death law, or complete "
            "any campaign."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-flight-death/2",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "context_identity": context,
        "matched_outcomes": matched,
        "exact_invocation": invocation,
        "passive_traces": {
            "natural": natural_trace, "response_only": response_trace},
        "shared_c15_level08_respawn_activation": level08_activation,
        "rejected_early_control": rejected,
        "bounded_interpretation": {
            "observation": (
                "At scene 8, corrected live pool slot 5/id 37/callback "
                "0x80049E88/backlink 0x80094AC4 owns the next proximity call. "
                "The natural branch reaches health -1/master 2 and the ordinary "
                "resident respawn restores health 4 while lives changes 3->2."),
            "inference": (
                "Scene routing places the observation in Riverbed Flight. Type "
                "word 0x0125 remains unclassified E08/downstream evidence; no "
                "species name is promoted."),
            "causal_confirmation": (
                "Changing only actor state bit 0x0080 at the matched boundary "
                "preserves frame/cycle/PC/SP but removes every damage-range hit, "
                "the 0x8004B4A0 call, death, respawn and LEVEL08 initializer. "
                "Independent same-entry LEVEL08 source controls change only "
                "the expected safe/live X or safe heading result."),
            "failed_hypothesis": (
                "Applying the same bit at the save/setup anchor fails because "
                "the native update overwrites it before contact; that branch "
                "still dies and is not causal evidence."),
            "forbidden_claim": (
                "Do not infer an actor species, scripted owner, distinct special "
                "death class, authored checkpoint-row policy, general F14 "
                "flight/chase policy, or C15/C16/F14 completion."),
        },
        "bounded_open_frontier": {
            "death_classes": (
                "Scripted, setpiece and exceptional death producers remain open; "
                "this special-stage context reuses the ordinary proximity law."),
            "flight_scope": (
                "F14 motion, companion/chase state, objective and transition remain open."),
            "checkpoint_scope": (
                "Authored row provenance, indirect writers, persistence, other "
                "death classes and remaining-stage breadth remain open for C15."),
            "frontend_card": (
                "Explicit native Save/Load, alternate title/menu choices, no-card "
                "and corrupt-card behavior remain open."),
            "next_experiment": (
                "Inventory another existing scripted/setpiece or exceptional "
                "death lead and bind its exact producer before requesting a fixture."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 Flight evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[c16-flight-death] actor contact bound to ordinary C16 law")
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
                args, generator="tools/phase4_c16_flight_death.py",
                anchor={"type": "aborted before retained C16 Flight evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(f"owned C16 Flight cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
