#!/usr/bin/env python3
"""Bind a natural Thumper-owned attack to one C16 ordinary-death lifecycle.

This generator consumes the centrally pinned pristine-serial
``thumper_boss_2`` movie/state pair.  It first brackets a natural health 4 -> 3
hit with passive, internally controlled tracing.  It then changes only true
health from 4 to 0 at the exact pre-hit movie boundary and proves that the same
native invocation produces fatal health and the ordinary resident respawn.

The actor claim is not inferred from the filename: both the natural and fatal
invocations must enter 0x8004A700 with ``s1`` pointing at a live pool record
whose id, callback, and authored-record backlink identify Thumper.
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
    import phase4_c16_bonus_death as base
    import phase4_e08_operator_contacts as contacts
    import phase4_lives_death_breadth as breadth
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_c16_thumper_death
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
OUTPUT = ROOT / "analysis/phase4_c16_thumper_death.json"
MOVIE_REL = "thumper_boss_2.movie.json"
SAVE_REL = "thumper_boss_2.movie.sav"
MOVIE_SHA256 = "c5e26e960e10627963d3f419e38868384439c5477d525f1972c0c87288d2bad5"
SAVE_SHA256 = "991d50d2af1513e3fd746711b8e70936d7674aab44ece21d3262e6bac0efe282"
SCENE_GRAPH = ROOT / "analysis/phase3_scene_asset_graph.json"
ROW_COVERAGE = ROOT / "analysis/phase2_row_coverage.json"
MECHANICS = ROOT / "analysis/mechanics_baseline.yaml"
THUMPER_SOURCE = ROOT / "src_re/thumper_boss.c"

SCENE = 0x80082504
HEALTH = 0x800A6594
EXPECTED_SCENE = 2
PRE_HIT_FRAME = 2422
HIT_FRAME = 2423
RESPAWN_FRAME = 2550
TRANSITION_ENTRY = 0x8004A700
EXPECTED_CALL = 0x8004B4A0
EXPECTED_CALL_WORD = 0x0C0129C0

ACTOR_POOL_BASE = 0x8009FD80
ACTOR_STRIDE = 0x84
ACTOR_CAPACITY = 64
THUMPER_ACTOR = 0x8009FE04
THUMPER_ID = 16
THUMPER_CALLBACK = 0x8004A0F4
THUMPER_BACKLINK = 0x80094A54
MOSQUITO_ACTOR = THUMPER_ACTOR + ACTOR_STRIDE
MOSQUITO_ID = 10
MOSQUITO_CALLBACK = 0x8004A180

COVERAGE_RANGES = (
    breadth.TRACE_RANGES[0],
    breadth.TRACE_RANGES[1],
    breadth.TRACE_RANGES[2],
    next(row for row in breadth.TRIGGER_TRACE_RANGES
         if row["label"] == "proximity_updater"),
)


def _sha256(path: Path) -> str:
    return base._sha256(path)


def _start_movie(client: Any, movie_path: Path) -> dict[str, Any]:
    base._cleanup(client)
    loaded = client.call("movie.load", {"path": str(movie_path.resolve())})
    started = client.call(
        "movie.startPlayback", {"start_frame": 0, "load_start_state": True})
    if loaded.get("frame_count") != 3092 or \
            started.get("reproducible") is not True or \
            started.get("truncated") is not False:
        raise SystemExit(f"Thumper movie did not start reproducibly: {started}")
    return {"loaded": loaded, "started": started}


def _advance_to(client: Any, frame: int, *, max_frames: int) -> dict[str, Any]:
    result = client.call("movie.advanceToFrame", {
        "frame": frame, "max_frames": max_frames}, timeout=900)
    status = client.call("movie.status", {})
    if status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            status.get("playback_index") != frame:
        raise SystemExit(f"Thumper movie lost frame {frame}: {status}")
    return result


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_path, save_path = ROOT / MOVIE_REL, ROOT / SAVE_REL
    movie_pin = entries.get(MOVIE_REL) or {}
    save = verify_declared_save_fixture(
        save_path, allowed_media_classes={"pristine"})
    movie = json.loads(movie_path.read_text())
    start = movie.get("start_state") or {}
    frames = movie.get("frames") or []
    keys = {
        key for frame in frames for port in (frame.get("ports") or {}).values()
        for key in port
    }
    expected_keys = {
        "circle", "cross", "down", "l1", "l2", "l3", "left",
        "r1", "r2", "r3", "right", "select", "square", "start",
        "triangle", "up",
    }
    if movie_pin.get("sha256") != MOVIE_SHA256 or \
            movie_pin.get("size") != movie_path.stat().st_size or \
            movie_pin.get("media_class") != "pristine_serial" or \
            _sha256(movie_path) != MOVIE_SHA256 or \
            save.get("sha256") != SAVE_SHA256 or \
            movie.get("version") != 2 or \
            movie.get("game_serial") != "SCUS-94288" or \
            movie.get("initial_frame") != 57593 or len(frames) != 3092 or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            Path(start.get("path", "")).name != Path(SAVE_REL).name or \
            start.get("file_size") != save["size"] or keys != expected_keys:
        raise SystemExit("Thumper movie/state pin or metadata drifted")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "inventory_scope": (
            "selected only after recursively enumerating movies/Phase4 and "
            "the broader operator movies tree; rejected candidates remain "
            "transient experiment evidence"),
        "movie": {
            "path": MOVIE_REL, "sha256": MOVIE_SHA256,
            "size": movie_pin["size"], "media_class": "pristine_serial",
            "version": 2, "frames": 3092, "initial_frame": 57593,
            "recorded_input_scope": "all 16 digital buttons; no analog axes",
        },
        "save": save,
        "classification_boundary": (
            "Filename and serial are leads only; inspected save media, replayed "
            "typed state, exact call registers, and live actor bytes carry the "
            "claim."),
    }


def build_context_identity() -> dict[str, Any]:
    import yaml

    scene = (json.loads(SCENE_GRAPH.read_text()).get("scenes") or {}).get(
        "scene_02") or {}
    coverage = (json.loads(ROW_COVERAGE.read_text()).get("rows") or {}).get(
        "D16_thumper") or {}
    mechanics = yaml.safe_load(MECHANICS.read_text())
    row = next((item for item in mechanics.get("rows") or []
                if item.get("id") == "D16_thumper"), {})
    c16 = next((item for item in mechanics.get("rows") or []
                if item.get("id") == "C16_lives_gameover"), {})
    fixture = (json.loads(FIXTURE_SET.read_text()).get("entries") or {}).get(
        MOVIE_REL) or {}
    result = {
        "scene_graph": {
            "scene_id": scene.get("scene_id"),
            "asset_entry": scene.get("asset_entry"),
            "disc_dir": scene.get("disc_dir"),
            "overlays": scene.get("overlays"),
            "phase2_stage_labels": scene.get("phase2_stage_labels"),
        },
        "phase2_row_route": coverage,
        "mechanics_routes": {
            "d16_status": row.get("status"),
            "d16_movie_declared": MOVIE_REL in (row.get("fixture_have") or []),
            "d16_save_declared": SAVE_REL in (row.get("fixture_have") or []),
            "c16_status": c16.get("status"),
            "c16_movie_declared": MOVIE_REL in (c16.get("fixture_have") or []),
            "c16_save_declared": SAVE_REL in (c16.get("fixture_have") or []),
        },
        "required_mechanics_consumers": sorted(
            set(fixture.get("consumers") or []) & {
                "mechanics:C16_lives_gameover", "mechanics:D16_thumper"}),
        "classification": (
            "scene 2 / stage03 Council Chamber and D16 Thumper context; actor "
            "ownership is established independently at the damage call"),
    }
    expected_scene = {
        "scene_id": 2, "asset_entry": "level03\\level1b",
        "disc_dir": "level03",
        "overlays": {"LEVEL03_LEVEL": 8, "LEVEL03_LEVEL1": 4},
        "phase2_stage_labels": ["stage03_council_chamber"],
    }
    if result["scene_graph"] != expected_scene or \
            coverage.get("status") != "pristine_trigger" or \
            MOVIE_REL not in (coverage.get("pristine_fixtures") or []) or \
            result["mechanics_routes"] != {
                "d16_status": "partial", "d16_movie_declared": True,
                "d16_save_declared": True, "c16_status": "partial",
                "c16_movie_declared": True, "c16_save_declared": True} or \
            result["required_mechanics_consumers"] != [
                "mechanics:C16_lives_gameover", "mechanics:D16_thumper"]:
        raise SystemExit(f"Thumper context routing drifted: {result}")
    return result


def _trace_boundary(client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    trace = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": [COVERAGE_RANGES[0], COVERAGE_RANGES[-1]]}, timeout=900)
    compact = contacts._compact_trace(trace)
    snapshot = base._snapshot(client, include_full_ram=True)
    if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in compact.get("coverage") or []):
        raise SystemExit(f"Thumper natural trace was not neutral: {compact}")
    return {"snapshot": snapshot, "cycle_neutral_trace": compact}


def _run_natural_control(client: Any, movie_path: Path) -> dict[str, Any]:
    before = _trace_boundary(client, movie_path, PRE_HIT_FRAME)
    after = _trace_boundary(client, movie_path, HIT_FRAME)
    a, b = before["snapshot"], after["snapshot"]
    pcs = {
        str(pc).lower() for row in after["cycle_neutral_trace"]["coverage"]
        for pc in row.get("pcs") or []}
    result = {
        "before": before, "after": after,
        "derived_delta": {
            "health": b["health"] - a["health"],
            "lives": b["lives"] - a["lives"],
            "scene_equal": a["scene"] == b["scene"],
            "proximity_call_present": "0x8004b4a0" in pcs,
            "health_write_present": "0x8004a888" in pcs,
        },
    }
    if (a["scene"], a["health"], a["lives"], a["master_state"],
            a["movie_frame"]) != (2, 4, 4, 0, PRE_HIT_FRAME) or \
            (b["scene"], b["health"], b["lives"], b["master_state"],
             b["movie_frame"]) != (2, 3, 4, 0, HIT_FRAME) or \
            result["derived_delta"] != {
                "health": -1, "lives": 0, "scene_equal": True,
                "proximity_call_present": True, "health_write_present": True}:
        raise SystemExit(f"natural Thumper hit boundary drifted: {result}")
    return result


def _prepare(client: Any, movie_path: Path, *, mutate: bool) -> dict[str, Any]:
    _start_movie(client, movie_path)
    _advance_to(client, PRE_HIT_FRAME, max_frames=PRE_HIT_FRAME + 10)
    before = base._snapshot(client, include_full_ram=True)
    before_ram = base._main_ram(client)
    mutation = None
    if mutate:
        write = client.call("debugger.writeU16", {
            "address": f"0x{HEALTH:08X}", "value": 0})
        after = base._snapshot(client, include_full_ram=True)
        after_ram = base._main_ram(client)
        differences = [
            {"address": f"0x{0x80000000 + index:08x}",
             "before": before_ram[index], "after": after_ram[index]}
            for index in range(len(before_ram))
            if before_ram[index] != after_ram[index]
        ]
        mutation = {
            "method": "debugger.writeU16", "address": "0x800a6594",
            "value": 0, "response": write,
            "main_ram_differences": differences,
            "main_ram_difference_count": len(differences),
            "post_write": after,
        }
        if before["health"] != 4 or after["health"] != 0 or \
                before["scene"] != after["scene"] or \
                before["lives"] != after["lives"] or \
                before["emulator_frame"] != after["emulator_frame"] or \
                before["cycle"] != after["cycle"] or \
                differences != [{
                    "address": "0x800a6594", "before": 4, "after": 0}] or \
                write.get("written") != 2:
            raise SystemExit(f"Thumper health mutation was not isolated: {mutation}")
    return {"pre_hit": before, "mutation": mutation}


def _actor_record(client: Any, address: int) -> dict[str, Any]:
    data = base._read_memory(client, address, ACTOR_STRIDE)
    return {
        "address": f"0x{address:08x}",
        "pool_slot": (address - ACTOR_POOL_BASE) // ACTOR_STRIDE,
        "id": struct.unpack_from("<I", data, 0)[0],
        "xyz": list(struct.unpack_from("<iii", data, 0x04)),
        "flags": f"0x{struct.unpack_from('<H', data, 0x5C)[0]:04x}",
        "hp": struct.unpack_from("<h", data, 0x6E)[0],
        "vm_ip": f"0x{struct.unpack_from('<I', data, 0x70)[0]:08x}",
        "callback": f"0x{struct.unpack_from('<I', data, 0x7C)[0]:08x}",
        "authored_record_backlink":
            f"0x{struct.unpack_from('<I', data, 0x80)[0]:08x}",
        "record_sha256": hashlib.sha256(data).hexdigest(),
    }


def _capture_invocation(
        client: Any, movie_path: Path, *, mutate: bool) -> dict[str, Any]:
    prepared = _prepare(client, movie_path, mutate=mutate)
    client.call("debugger.runUntilAddress", {
        "address": f"0x{TRANSITION_ENTRY:08X}"})
    base._wait_for_pause(client, "Thumper damage entry")
    registers = {
        str(key).lower(): value for key, value in
        client.call("debugger.getRegisters", {})["registers_hex"].items()}
    pc, ra = int(registers["pc"], 16), int(registers["ra"], 16)
    call_address = (ra - 8) & 0xFFFFFFFF
    word = struct.unpack("<I", base._read_memory(client, call_address, 4))[0]
    s1 = int(registers["s1"], 16)
    actor = _actor_record(client, s1)
    neighbor = _actor_record(client, MOSQUITO_ACTOR)
    authored = base._read_memory(client, THUMPER_BACKLINK, 0x1C)
    before_call = base._snapshot(client, include_full_ram=True)
    client.call("debugger.runUntilAddress", {"address": f"0x{ra:08X}"})
    base._wait_for_pause(client, "Thumper damage return")
    after_return = base._snapshot(client, include_full_ram=True)
    result = {
        "control": "one_field_fatal" if mutate else "natural_nonfatal",
        "entry": {
            "pc": f"0x{pc:08x}", "ra": f"0x{ra:08x}",
            "link_call_address": f"0x{call_address:08x}",
            "instruction_word": f"0x{word:08x}",
            "resolved_target": f"0x{TRANSITION_ENTRY:08x}",
            "arguments": {name: registers[name]
                          for name in ("a0", "a1", "a2", "a3")},
            "s1_actor_pointer": f"0x{s1:08x}",
        },
        "actor_owner": actor,
        "neighbor_control": neighbor,
        "authored_record": {
            "address": f"0x{THUMPER_BACKLINK:08x}", "length": len(authored),
            "sha256": hashlib.sha256(authored).hexdigest(),
            "low_id": struct.unpack_from("<H", authored, 0)[0] & 0xFF,
        },
        "pre_hit": prepared["pre_hit"],
        "mutation": prepared["mutation"],
        "before_call": before_call,
        "after_return": after_return,
        "returned_to": f"0x{ra:08x}",
    }
    expected_health = (0, -1, 2) if mutate else (4, 3, 0)
    result["actor_causally_bound"] = bool(
        pc == TRANSITION_ENTRY and call_address == EXPECTED_CALL and
        word == EXPECTED_CALL_WORD and s1 == THUMPER_ACTOR and
        actor["pool_slot"] == 1 and actor["id"] == THUMPER_ID and
        actor["callback"] == f"0x{THUMPER_CALLBACK:08x}" and
        actor["authored_record_backlink"] == f"0x{THUMPER_BACKLINK:08x}" and
        neighbor["pool_slot"] == 2 and neighbor["id"] == MOSQUITO_ID and
        neighbor["callback"] == f"0x{MOSQUITO_CALLBACK:08x}" and
        (before_call["scene"], before_call["health"], before_call["lives"],
         before_call["master_state"]) == (
            EXPECTED_SCENE, expected_health[0], 4, 0) and
        (after_return["scene"], after_return["health"], after_return["lives"],
         after_return["master_state"]) == (
            EXPECTED_SCENE, expected_health[1], 4, expected_health[2]) and
        after_return["pc"].lower() == result["returned_to"])
    if result["actor_causally_bound"] is not True:
        raise SystemExit(f"Thumper actor invocation was not causal: {result}")
    return result


def _run_fatal_lifecycle(client: Any, movie_path: Path) -> dict[str, Any]:
    prepared = _prepare(client, movie_path, mutate=True)
    _advance_to(client, HIT_FRAME, max_frames=2)
    fatal = base._snapshot(client, include_full_ram=True)
    _advance_to(client, RESPAWN_FRAME,
                max_frames=RESPAWN_FRAME - HIT_FRAME + 5)
    respawn = base._snapshot(client, include_full_ram=True)
    result = {
        "pre_hit": prepared["pre_hit"], "mutation": prepared["mutation"],
        "fatal_boundary": fatal, "ordinary_respawn": respawn,
    }
    if (fatal["scene"], fatal["health"], fatal["lives"],
            fatal["master_state"], fatal["movie_frame"]) != (
                2, -1, 4, 2, HIT_FRAME) or \
            (respawn["scene"], respawn["health"], respawn["lives"],
             respawn["master_state"], respawn["movie_frame"]) != (
                2, 4, 3, 0, RESPAWN_FRAME):
        raise SystemExit(f"Thumper fatal lifecycle drifted: {result}")
    return result


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    natural = document.get("natural_control") or {}
    a = ((natural.get("before") or {}).get("snapshot") or {})
    b = ((natural.get("after") or {}).get("snapshot") or {})
    fatal = document.get("one_field_fatal_lifecycle") or {}
    respawn = fatal.get("ordinary_respawn") or {}
    invocations = document.get("exact_invocations") or {}
    return {
        "movies_replayed": 1,
        "natural_health_delta": b.get("health", 0) - a.get("health", 0),
        "mutation_main_ram_difference_count": (
            (fatal.get("mutation") or {}).get("main_ram_difference_count")),
        "fatal_health": (fatal.get("fatal_boundary") or {}).get("health"),
        "ordinary_respawn_health_lives": [
            respawn.get("health"), respawn.get("lives")],
        "producer_path_id": "proximity_contact",
        "actor_owner_id": (
            (invocations.get("fatal") or {}).get("actor_owner") or {}).get("id"),
        "actor_owner_address": (
            ((invocations.get("fatal") or {}).get("actor_owner") or {}).get(
                "address")),
        "natural_and_fatal_actor_bound": all(
            (invocations.get(key) or {}).get("actor_causally_bound") is True
            for key in ("natural", "fatal")),
        "boss_actor_causation_bounded": 1,
        "d16_or_f03_completed": 0,
    }


def _source_dependencies() -> dict[str, str]:
    paths = [
        "tools/phase4_c16_bonus_death.py",
        "tools/phase4_lives_death_breadth.py",
        "tools/phase4_e08_operator_contacts.py",
        "analysis/phase3_scene_asset_graph.json",
        "analysis/phase2_row_coverage.json",
        "analysis/mechanics_baseline.yaml",
        "src_re/thumper_boss.c",
    ]
    return {path: _sha256(ROOT / path) for path in paths}


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for label, builder, key in (
            ("fixture", build_fixture_census, "fixture_census"),
            ("context", build_context_identity, "thumper_context_identity")):
        try:
            recomputed = builder()
        except (OSError, KeyError, ValueError, SystemExit) as error:
            recomputed = None
            gaps.append(f"Thumper {label} recomputation failed: {error}")
        if recomputed is not None and document.get(key) != recomputed:
            gaps.append(f"Thumper {label} census changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Thumper source dependencies changed")
    natural = document.get("natural_control") or {}
    before = ((natural.get("before") or {}).get("snapshot") or {})
    after = ((natural.get("after") or {}).get("snapshot") or {})
    if (before.get("scene"), before.get("health"), before.get("lives"),
            before.get("master_state"), before.get("movie_frame")) != (
                2, 4, 4, 0, PRE_HIT_FRAME) or \
            (after.get("scene"), after.get("health"), after.get("lives"),
             after.get("master_state"), after.get("movie_frame")) != (
                2, 3, 4, 0, HIT_FRAME):
        gaps.append("natural Thumper damage boundary changed")
    for side in (natural.get("before") or {}, natural.get("after") or {}):
        trace = side.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append("natural Thumper trace neutrality changed")
            break
    lifecycle = document.get("one_field_fatal_lifecycle") or {}
    mutation = lifecycle.get("mutation") or {}
    fatal = lifecycle.get("fatal_boundary") or {}
    respawn = lifecycle.get("ordinary_respawn") or {}
    if mutation.get("main_ram_differences") != [{
            "address": "0x800a6594", "before": 4, "after": 0}] or \
            (fatal.get("scene"), fatal.get("health"), fatal.get("lives"),
             fatal.get("master_state"), fatal.get("movie_frame")) != (
                2, -1, 4, 2, HIT_FRAME) or \
            (respawn.get("scene"), respawn.get("health"), respawn.get("lives"),
             respawn.get("master_state"), respawn.get("movie_frame")) != (
                2, 4, 3, 0, RESPAWN_FRAME):
        gaps.append("one-field Thumper fatal lifecycle changed")
    invocations = document.get("exact_invocations") or {}
    for key, expected in (("natural", (4, 3, 0)), ("fatal", (0, -1, 2))):
        row = invocations.get(key) or {}
        entry, actor = row.get("entry") or {}, row.get("actor_owner") or {}
        if row.get("actor_causally_bound") is not True or \
                entry.get("link_call_address") != "0x8004b4a0" or \
                entry.get("instruction_word") != "0x0c0129c0" or \
                entry.get("s1_actor_pointer") != "0x8009fe04" or \
                (actor.get("pool_slot"), actor.get("id"), actor.get("callback"),
                 actor.get("authored_record_backlink")) != (
                    1, 16, "0x8004a0f4", "0x80094a54") or \
                (row.get("before_call") or {}).get("health") != expected[0] or \
                (row.get("after_return") or {}).get("health") != expected[1] or \
                (row.get("after_return") or {}).get("master_state") != expected[2]:
            gaps.append(f"{key} Thumper actor attribution changed")
    summary = derive_summary(document)
    if document.get("summary") != summary or \
            summary.get("natural_health_delta") != -1 or \
            summary.get("mutation_main_ram_difference_count") != 1 or \
            summary.get("ordinary_respawn_health_lives") != [4, 3] or \
            summary.get("actor_owner_id") != 16 or \
            summary.get("natural_and_fatal_actor_bound") is not True or \
            summary.get("d16_or_f03_completed") != 0:
        gaps.append("Thumper derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thumper process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = build_fixture_census()
    context = build_context_identity()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU16", "debugger.getRegisters",
        "debugger.runUntilAddress", "debugger.clearBreakpoints",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks Thumper methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / SAVE_REL, media_identity)
    movie_path = ROOT / MOVIE_REL
    natural = _run_natural_control(client, movie_path)
    natural_invocation = _capture_invocation(client, movie_path, mutate=False)
    fatal_invocation = _capture_invocation(client, movie_path, mutate=True)
    lifecycle = _run_fatal_lifecycle(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_c16_thumper_death.py",
        anchor={
            "type": "existing state-anchored Thumper boss attack lead",
            "save": SAVE_REL, "movie": MOVIE_REL,
            "fixture_sha256": {
                SAVE_REL: SAVE_SHA256, MOVIE_REL: MOVIE_SHA256},
            "state_inspections": [inspection],
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_format": "v2 all digital buttons",
            "boundaries": {
                "pre_hit": PRE_HIT_FRAME, "hit": HIT_FRAME,
                "ordinary_respawn": RESPAWN_FRAME},
            "trace_mode": (
                "fresh passive movie.traceToFrame boundaries plus fresh exact "
                "entry-to-architectural-return invocation captures"),
            "causal_capture": (
                "change only true health 4->0 at frame 2422; stop at the next "
                "0x8004A700 and require s1 to name the same actor as the natural hit"),
        })
    document = {
        "_comment": (
            "Active C16 breadth: one natural Thumper-owned attack made fatal by "
            "a one-field starting-health control, then joined to ordinary resident "
            "respawn. This is boss-actor causation, not D16/F03 completion."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-thumper-death/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "thumper_context_identity": context,
        "natural_control": natural,
        "exact_invocations": {
            "natural": natural_invocation, "fatal": fatal_invocation},
        "one_field_fatal_lifecycle": lifecycle,
        "bounded_interpretation": {
            "observation": (
                "The pristine replay naturally changes health 4->3 at frame 2423. "
                "Both the natural and fatal controls enter the same resident damage "
                "routine from the same call with s1=0x8009FE04."),
            "inference": (
                "The scene graph and D16 route establish Council Chamber boss context."),
            "causal_confirmation": (
                "At each exact call, s1 names pool slot 1/id 16/callback 0x8004A0F4/"
                "backlink 0x80094A54; the neighboring slot is separately id 10. "
                "Changing only health 4->0 makes that invocation return at health -1/"
                "master 2 and the native path respawns at health 4/lives 3."),
            "forbidden_claim": (
                "Do not infer Thumper's whole attack policy, complete D16/F03, or "
                "generalize this ordinary proximity death to scripted, special, or "
                "exceptional death classes."),
        },
        "bounded_open_frontier": {
            "death_classes": (
                "Scripted, special and exceptional deaths plus other bonus contexts "
                "remain open."),
            "boss_scope": (
                "One actor-owned Thumper proximity hit is bounded; phases, complete "
                "defeat transition, arena policy and other boss damage paths remain open."),
            "frontend_card": (
                "Explicit native Save/Load, alternate title/menu choices, no-card and "
                "corrupt-card behavior remain open."),
            "next_experiment": (
                "Inventory an existing scripted/setpiece or exceptional death lead and "
                "bind its exact producer before requesting a new fixture."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 Thumper evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[c16-thumper-death] actor-owned hit joined to ordinary C16 respawn")
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
                args, generator="tools/phase4_c16_thumper_death.py",
                anchor={"type": "aborted before retained C16 Thumper evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(f"owned C16 Thumper cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
