#!/usr/bin/env python3
"""Reproduce one final-life death in the pristine Stage-15 boss context.

The operator filename is only a discovery lead.  This generator verifies the
centrally pinned v1 movie/state pair, inspects the save before load, proves live
scene 15, bounds its save-restored Region-A identity, locates the first fatal-health
movie frame, and captures the native caller whose invocation changes health
from nonfatal to negative.  Passive ``movie.traceToFrame`` evidence separately
proves cycle/register/RAM/frame neutrality and the resident game-over law.
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
    import phase4_e08_operator_contacts as contacts
    import phase4_lives_death_breadth as breadth
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_c16_boss_death
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_lives_death_breadth as breadth
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_c16_boss_death.json"
MOVIE_REL = "hopper_boss.movie.json"
SAVE_REL = "hopper_boss.movie.sav"
SCENE_GRAPH = ROOT / "analysis/phase3_scene_asset_graph.json"
ACTOR_CENSUS = ROOT / "analysis/phase1_kind_actor_census.json"
MECHANICS = ROOT / "analysis/mechanics_baseline.yaml"
E07_ARTIFACT = ROOT / "analysis/phase4_event_vm.json"
SCENE = 0x80082504
HEALTH = 0x800A6594
LIVES = 0x800A65A0
MASTER_STATE = 0x800823A0
EXPECTED_SCENE = 15


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length or row.get("valid_bytes") != length:
        raise SystemExit(
            f"short debugger read at 0x{address:08X}: "
            f"{row.get('valid_bytes')}/{length}")
    return data


def _scalar_snapshot(client: Any) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    return {
        "emulator_frame": status["frame"],
        "cycle": status["cycle"],
        "pc": status["pc"],
        "scene": struct.unpack("<I", _read_memory(client, SCENE, 4))[0],
        "health": struct.unpack("<h", _read_memory(client, HEALTH, 2))[0],
        "lives": _read_memory(client, LIVES, 1)[0],
        "master_state": struct.unpack(
            "<H", _read_memory(client, MASTER_STATE, 2))[0],
    }


def _trace_state_at_frame(
        client: Any, movie_path: Path, target: int,
        *, ranges: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    """Control-check one v1 replay boundary, including its legacy EOF rule.

    The current runtime consumes all ``frame_count`` v1 samples when asked for
    target ``frame_count`` but reports the last zero-based sample and leaves the
    movie active.  V3 files stop and reset at EOF.  Keep that difference local
    to this v1 fixture instead of weakening the shared v3 helper.
    """
    trace = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": target,
        "ranges": list(ranges)}, timeout=900)
    trace = contacts._compact_trace(trace)
    if trace["comparison"].get("cycle_neutral") is not True or \
            any(row["truncated"] for row in trace["coverage"]):
        raise SystemExit(
            f"C16 boss-context trace was not cycle-neutral at {target}: "
            f"{trace['comparison']}")
    snapshot = contacts._typed_snapshot(client)
    status = client.call("movie.status", {})
    legacy_v1_advanced = target > 0
    at_v1_eof = target == status.get("frame_count")
    expected_movie_frame = target - 1 if legacy_v1_advanced else 0
    if status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            trace["instrumented"].get("movie_frame") != expected_movie_frame or \
            (legacy_v1_advanced and (
                status.get("playing") is not True or
                status.get("playback_index") != expected_movie_frame)):
        raise SystemExit(
            f"C16 boss-context trace lost its v1 movie anchor: target={target} "
            f"instrumented={trace['instrumented']} status={status}")
    return {
        "snapshot": snapshot, "movie_status": status, "trace": trace,
        "v1_eof_rule": {
            "applied": at_v1_eof,
            "legacy_zero_based_reporting_applied": legacy_v1_advanced,
            "requested_target": target,
            "reported_movie_frame": trace["instrumented"].get("movie_frame"),
            "reported_playback_index": status.get("playback_index"),
            "playing": status.get("playing"),
            "interpretation": (
                "all source samples consumed; legacy v1 remains active at the "
                "last zero-based input sample" if at_v1_eof else
                "legacy v1 reports the last consumed zero-based input sample"),
        },
    }


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_path = ROOT / MOVIE_REL
    save_path = ROOT / SAVE_REL
    movie_pin = entries.get(MOVIE_REL)
    save = verify_declared_save_fixture(
        save_path, allowed_media_classes={"pristine"})
    if not isinstance(movie_pin, dict) or \
            movie_pin.get("media_class") != "pristine_serial" or \
            movie_pin.get("size") != movie_path.stat().st_size or \
            movie_pin.get("sha256") != _sha256(movie_path):
        raise SystemExit(f"C16 boss-context movie pin drifted: {MOVIE_REL}")
    movie = json.loads(movie_path.read_text())
    start = movie.get("start_state") or {}
    frames = movie.get("frames") or []
    expected_buttons = {
        "circle", "cross", "down", "l1", "l2", "l3", "left", "r1",
        "r2", "r3", "right", "select", "square", "start", "triangle", "up",
    }
    frame_keys = {
        key for frame in frames for port in (frame.get("ports") or {}).values()
        for key in port
    }
    if movie.get("version") != 1 or \
            movie.get("game_serial") != "SCUS-94288" or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            Path(start.get("path", "")).name != Path(SAVE_REL).name or \
            start.get("file_size") != save["size"] or not frames or \
            frame_keys != expected_buttons:
        raise SystemExit(f"C16 boss-context movie metadata drifted: {MOVIE_REL}")
    non_neutral = sum(
        any(value is True for port in (frame.get("ports") or {}).values()
            for value in port.values()) for frame in frames)
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "lead": "centrally declared D20/F15 Hopper-showdown recording",
        "movie": {
            "path": MOVIE_REL, "sha256": movie_pin["sha256"],
            "size": movie_pin["size"], "media_class": movie_pin["media_class"],
            "version": movie["version"], "frames": len(frames),
            "initial_frame": movie.get("initial_frame"),
            "recorded_input_scope": "16 digital buttons; v1 has no analog axes",
            "non_neutral_frames": non_neutral,
        },
        "save": save,
        "classification_boundary": (
            "the filename and central D20/F15 routing are leads; live scene, "
            "overlay, typed health/lives and caller execution determine claims"),
    }


def build_boss_context_identity() -> dict[str, Any]:
    import yaml

    graph = json.loads(SCENE_GRAPH.read_text())
    scene = (graph.get("scenes") or {}).get("scene_15") or {}
    actor = json.loads(ACTOR_CENSUS.read_text())
    probe = (actor.get("addendum_probes") or {}).get(SAVE_REL) or {}
    mechanics = yaml.safe_load(MECHANICS.read_text())
    rows = {row["id"]: row for row in mechanics.get("rows") or []}
    fixture_entry = (json.loads(FIXTURE_SET.read_text()).get("entries") or {}).get(
        MOVIE_REL) or {}
    selected = {}
    for row_id in ("D20_hopper", "F15_canyon_showdown"):
        row = rows.get(row_id) or {}
        selected[row_id] = {
            "name": row.get("name"), "stages": row.get("stages"),
            "status": row.get("status"),
            "movie_declared": MOVIE_REL in (row.get("fixture_have") or []),
        }
    required_routes = {"mechanics:D20_hopper", "mechanics:F15_canyon_showdown"}
    consumers = set(fixture_entry.get("consumers") or [])
    result = {
        "scene_graph": scene,
        "phase1_actor_probe": probe,
        "baseline_fixture_routes": selected,
        "central_movie_required_routes": sorted(required_routes & consumers),
        "central_movie_preservation_required": fixture_entry.get(
            "preservation_required"),
        "classification": (
            "confirmed Stage-15/Canyon-Showdown boss context only; live "
            "Region-A bytes remain save-restored and are not promoted to an "
            "exact staged overlay identity; this does not identify Hopper as "
            "the damage producer or complete D20/F15"),
    }
    if scene != {
            "scene_id": 15, "asset_entry": "level05\\level5c",
            "disc_dir": "level05", "asset_prefix": "level5c",
            "loading_screen": "gfx\\level5c.raw",
            "overlays": {"LEVEL05_LEVEL": 8, "LEVEL05_LEVEL1": 6},
            "phase2_stage_labels": ["stage15_canyon_showdown"]}:
        raise SystemExit("Stage-15 scene/overlay identity drifted")
    if probe.get("save_sha256") != \
            "003209bfe7566234b337620236b6bf00f8ec560dfd1c48a26886ecb565fb97b7" or \
            probe.get("owner_level") != "stage15_canyon_showdown" or \
            probe.get("matches_owner_census") is not True:
        raise SystemExit("Stage-15 actor-census corroboration drifted")
    if any(not row["movie_declared"] for row in selected.values()) or \
            result["central_movie_required_routes"] != sorted(required_routes) or \
            result["central_movie_preservation_required"] is not True:
        raise SystemExit("boss-context fixture routing drifted")
    return result


def _coverage(trace: dict[str, Any], label: str) -> dict[str, Any]:
    rows = [row for row in trace.get("coverage") or []
            if row.get("label") == label]
    return rows[0] if len(rows) == 1 else {}


def _all_pcs(trace: dict[str, Any]) -> set[str]:
    return {
        str(pc).lower() for row in trace.get("coverage") or []
        for pc in row.get("pcs") or []
    }


def _wait_for_pause(client: Any, label: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while True:
        status = client.call("debugger.status", {})
        if status.get("paused") is True:
            return status
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for {label}")
        time.sleep(0.01)


def _capture_entry_caller(
        client: Any, movie_path: Path, movie_target: int) -> dict[str, Any]:
    """Stop at the next transition entry after a v1 target boundary."""
    _trace_state_at_frame(
        client, movie_path, movie_target - 1,
        ranges=(breadth.TRACE_RANGES[0],))
    client.call("debugger.runUntilAddress", {"address": "0x8004A700"})
    status = _wait_for_pause(client, "transition-entry breakpoint")
    registers = client.call("debugger.getRegisters", {})["registers_hex"]
    registers = {str(key).lower(): value for key, value in registers.items()}
    pc = int(registers["pc"], 16)
    ra = int(registers["ra"], 16)
    call_address = (ra - 8) & 0xFFFFFFFF
    word = struct.unpack("<I", _read_memory(client, call_address, 4))[0]
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
        target_register = breadth.MIPS_GPR_NAMES[rs]
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
        "valid": valid, "pc": f"0x{pc:08x}", "ra": f"0x{ra:08x}",
        "link_call_address": f"0x{call_address:08x}",
        "instruction_word": f"0x{word:08x}", "call_kind": call_kind,
        "target_register": target_register,
        "target_register_value": (
            registers[target_register] if target_register else None),
        "resolved_target": f"0x{call_target:08x}",
        "arguments": {
            name: registers[name] for name in ("a0", "a1", "a2", "a3")},
        "code_slice": {
            "address": f"0x{sample_address:08x}", "length": len(sample),
            "sha256": hashlib.sha256(sample).hexdigest(),
        },
        "capture_boundary": (
            f"v1 target {movie_target - 1} consumes input through index "
            f"{movie_target - 2}; the next native entry is the target-{movie_target} "
            "fatal invocation"),
    }


def _capture_fatal_invocation(
        client: Any, movie_path: Path, movie_frame: int) -> dict[str, Any]:
    capture = _capture_entry_caller(client, movie_path, movie_frame)
    before = _scalar_snapshot(client)
    return_address = int(capture["ra"], 16)
    client.call("debugger.runUntilAddress", {
        "address": f"0x{return_address:08X}"})
    status = _wait_for_pause(client, "fatal invocation return")
    after = _scalar_snapshot(client)
    result = {
        "entry": capture, "before_call": before, "after_return": after,
        "returned_to": f"0x{return_address:08x}",
        "method_boundary": (
            "instrumented replay pauses at the next 0x8004A700 entry after "
            "movie frame N-1, then runs exactly to its architectural return; "
            "passive traceToFrame supplies separate cycle-neutral identity"),
    }
    result["caused_fatal_health"] = derive_fatal_invocation_causal(result)
    if result["caused_fatal_health"] is not True or \
            int(status.get("pc", "0"), 16) != return_address:
        raise SystemExit(f"transition invocation was not the fatal call: {result}")
    return result


def derive_fatal_invocation_causal(invocation: dict[str, Any]) -> bool:
    capture = invocation.get("entry") or {}
    before = invocation.get("before_call") or {}
    after = invocation.get("after_return") or {}
    return bool(
        breadth.derive_entry_capture_valid(capture) and
        before.get("health", -1) >= 0 and after.get("health", 0) < 0 and
        before.get("lives") == after.get("lives") == 0 and
        before.get("scene") == after.get("scene") == EXPECTED_SCENE and
        after.get("pc") == invocation.get("returned_to") == capture.get("ra"))


def derive_fatal_attribution(
        boundary: dict[str, Any], static: dict[str, Any]) -> dict[str, Any]:
    invocation = boundary.get("fatal_invocation") or {}
    capture = invocation.get("entry") or {}
    address = str(capture.get("link_call_address", "")).lower()
    authority = list(
        ((static.get("resident_executable") or {}).get("direct_calls") or []))
    runtime_matches = {
        (row.get("address"), row.get("overlay"))
        for row in ((boundary.get("runtime_overlay_identity") or {}).get(
            "runtime_direct_call_matches") or [])
    }
    for row in ((static.get("scene_overlays") or {}).get("direct_calls") or []):
        if (row.get("address"), row.get("overlay")) in runtime_matches:
            authority.append(row)
    matches = [row for row in authority
               if str(row.get("address", "")).lower() == address]
    owner = matches[0] if len(matches) == 1 else None
    before_trace = (boundary.get("before") or {}).get("cycle_neutral_trace") or {}
    after_trace = (boundary.get("after") or {}).get("cycle_neutral_trace") or {}
    producer_label = None
    if address:
        call_address = int(address, 16)
        for row in breadth.TRIGGER_TRACE_RANGES:
            if int(row["start"], 16) <= call_address <= int(row["end"], 16):
                producer_label = row["label"]
                break
    before_damage = _coverage(before_trace, "damage_and_death_initiator")
    after_damage = _coverage(after_trace, "damage_and_death_initiator")
    before_producer = _coverage(before_trace, producer_label) if producer_label else {}
    after_producer = _coverage(after_trace, producer_label) if producer_label else {}
    passive_execution = bool(
        address in _all_pcs(after_trace) and
        "0x8004a700" in _all_pcs(after_trace) and
        after_damage.get("total_hits", 0) > before_damage.get("total_hits", 0) and
        after_producer.get("total_hits", 0) > before_producer.get("total_hits", 0))
    producer_path_id = (
        owner.get("producer_path_id") if owner else
        (f"runtime_{capture.get('call_kind')}_{address}"
         if breadth.derive_entry_capture_valid(capture) else None))
    exact = bool(
        derive_fatal_invocation_causal(invocation) and passive_execution and
        (boundary.get("before") or {}).get("scene") ==
        (boundary.get("after") or {}).get("scene") == EXPECTED_SCENE)
    return {
        "exact": exact, "producer_path_id": producer_path_id,
        "link_call_address": capture.get("link_call_address"),
        "call_kind": capture.get("call_kind"),
        "static_direct_call_match": owner is not None,
        "function": owner.get("function") if owner else
        "runtime register-linked caller",
        "mode": owner.get("mode") if owner else None,
        "boundary": owner.get("boundary") if owner else
        "entry-time link register resolves to 0x8004A700",
        "overlay": owner.get("overlay") if owner else None,
        "producer_trace_label": producer_label,
        "passive_call_and_target_execution": passive_execution,
        "damage_hit_delta": (
            after_damage.get("total_hits", 0) - before_damage.get("total_hits", 0)),
        "producer_hit_delta": (
            after_producer.get("total_hits", 0) -
            before_producer.get("total_hits", 0)),
        "scene_15": (
            (boundary.get("before") or {}).get("scene") ==
            (boundary.get("after") or {}).get("scene") == EXPECTED_SCENE),
        "damage_actor_or_hopper_promoted": False,
    }


def _locate_first_fatal_boundary(
        client: Any, movie_path: Path, frame_count: int,
        static: dict[str, Any]) -> dict[str, Any]:
    lo, hi = 1, frame_count
    probes = []
    while lo < hi:
        mid = (lo + hi) // 2
        replay = _trace_state_at_frame(
            client, movie_path, mid, ranges=(breadth.TRACE_RANGES[0],))
        player = replay["snapshot"]["player"]
        matched = player["health"] < 0
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
    before_row = _trace_state_at_frame(
        client, movie_path, lo - 1, ranges=breadth.TRIGGER_TRACE_RANGES)
    before_scene = struct.unpack("<I", _read_memory(client, SCENE, 4))[0]
    after_row = _trace_state_at_frame(
        client, movie_path, lo, ranges=breadth.TRIGGER_TRACE_RANGES)
    after_scene = struct.unpack("<I", _read_memory(client, SCENE, 4))[0]
    before_player = before_row["snapshot"]["player"]
    after_player = after_row["snapshot"]["player"]
    if before_player["health"] < 0 or after_player["health"] >= 0 or \
            before_player["lives"] != 0 or after_player["lives"] != 0 or \
            before_scene != after_scene or after_scene != EXPECTED_SCENE:
        raise SystemExit(
            f"no stable Stage-15 fatal boundary at movie frame {lo}: "
            f"{before_player} -> {after_player}, scenes {before_scene}/{after_scene}")
    runtime_overlay = breadth._runtime_overlay_identity(
        client, after_scene, static)
    invocation = _capture_fatal_invocation(client, movie_path, lo)
    boundary = {
        "movie_frame": lo, "probes": probes,
        "before": {
            "emulator_frame": before_row["snapshot"]["frame"],
            "cycle": before_row["snapshot"]["cycle"],
            "scene": before_scene, "player": before_player,
            "cycle_neutral_trace": before_row["trace"],
        },
        "after": {
            "emulator_frame": after_row["snapshot"]["frame"],
            "cycle": after_row["snapshot"]["cycle"],
            "scene": after_scene, "player": after_player,
            "cycle_neutral_trace": after_row["trace"],
        },
        "runtime_overlay_identity": runtime_overlay,
        "fatal_invocation": invocation,
        "search_rule": (
            "fresh pinned replay for every probe; first stable health<0 frame "
            "is bracketed by passive cycle-neutral traces, then a separate "
            "instrumented replay proves the next transition invocation returns "
            "with negative health"),
    }
    boundary["attribution"] = derive_fatal_attribution(boundary, static)
    if boundary["attribution"]["exact"] is not True:
        raise SystemExit(
            f"fatal boundary lacked exact producer attribution: "
            f"{boundary['attribution']}")
    return boundary


def _player_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    fields = ("health", "lives", "state", "grounded", "animation",
              "velocity_y", "position")
    return {
        "changed_fields": {
            field: {"before": before[field], "after": after[field]}
            for field in fields if before[field] != after[field]
        },
        "health_or_lives_changed": any(
            before[field] != after[field] for field in ("health", "lives")),
    }


def _run_movie(
        client: Any, fixture: dict[str, Any], temp_dir: Path,
        static: dict[str, Any]) -> dict[str, Any]:
    movie = fixture["movie"]
    movie_path = ROOT / movie["path"]
    initial_row = _trace_state_at_frame(
        client, movie_path, 0, ranges=breadth.TRACE_RANGES)
    source_end_row = _trace_state_at_frame(
        client, movie_path, movie["frames"], ranges=breadth.TRACE_RANGES)
    initial = initial_row["snapshot"]
    source_end = source_end_row["snapshot"]
    source_end_scene = struct.unpack("<I", _read_memory(client, SCENE, 4))[0]
    preliminary = {
        "initial": {"player": initial["player"], "scene": EXPECTED_SCENE},
        "source_end": {"player": source_end["player"], "scene": source_end_scene},
        "cycle_neutral_trace": source_end_row["trace"],
    }
    final_row = source_end_row
    final = source_end
    final_scene = source_end_scene
    extension_recipe = None
    law = breadth.derive_law_evidence(preliminary)
    if law["classification"] == "final_life_game_over_selected" and \
            law["required_pcs_present"] is not True:
        extended_path, extension_recipe = breadth._write_neutral_suffix_movie(
            {"lead": "hopper_boss_context", **fixture}, temp_dir)
        final_row = _trace_state_at_frame(
            client, extended_path, extension_recipe["derived_frame_count"],
            ranges=breadth.TRACE_RANGES)
        final = final_row["snapshot"]
        final_scene = struct.unpack("<I", _read_memory(client, SCENE, 4))[0]
    fatal = _locate_first_fatal_boundary(
        client, movie_path, movie["frames"], static)
    contacts._cleanup_movie(client)
    replay = {
        "fixture": fixture,
        "initial": {
            "frame": initial["frame"], "cycle": initial["cycle"],
            "scene": EXPECTED_SCENE, "player": initial["player"],
            "cycle_neutral_trace": initial_row["trace"],
        },
        "source_end": {
            "frame": source_end["frame"], "cycle": source_end["cycle"],
            "scene": source_end_scene, "player": source_end["player"],
            "ram_sha256": source_end_row["trace"]["control"]["ram_sha256"],
            "movie_status": source_end_row["movie_status"],
        },
        "final": {
            "frame": final["frame"], "cycle": final["cycle"],
            "scene": final_scene, "player": final["player"],
            "ram_sha256": final_row["trace"]["control"]["ram_sha256"],
            "movie_status": final_row["movie_status"],
        },
        "extension_recipe": extension_recipe,
        "first_fatal_boundary": fatal,
        "player_delta": _player_delta(initial["player"], source_end["player"]),
        "cycle_neutral_trace": final_row["trace"],
        "classification_boundary": (
            "live scene/overlay identity classifies a Stage-15 boss context; "
            "exact caller evidence classifies the damage producer, never the filename"),
    }
    replay["law_evidence"] = breadth.derive_law_evidence(replay)
    return replay


def derive_summary(replay: dict[str, Any]) -> dict[str, Any]:
    fatal = replay.get("first_fatal_boundary") or {}
    attribution = fatal.get("attribution") or {}
    runtime = fatal.get("runtime_overlay_identity") or {}
    return {
        "movies_replayed": 1,
        "boss_context_death_paths": int(
            (replay.get("initial") or {}).get("scene") == EXPECTED_SCENE and
            (replay.get("law_evidence") or {}).get("classification") ==
            "final_life_game_over_selected"),
        "first_fatal_movie_frame": fatal.get("movie_frame"),
        "producer_path_id": attribution.get("producer_path_id"),
        "producer_link_call_address": attribution.get("link_call_address"),
        "fatal_invocation_causally_confirmed": (
            derive_fatal_invocation_causal(
                fatal.get("fatal_invocation") or {})),
        "resident_game_over_law_complete": (
            (replay.get("law_evidence") or {}).get(
                "required_pcs_present") is True),
        "cycle_neutral": (
            (replay.get("cycle_neutral_trace") or {}).get(
                "comparison", {}).get("cycle_neutral") is True),
        "runtime_overlay_exact_matches": runtime.get("exact_matches") or [],
        "hopper_or_damage_actor_promoted": 0,
    }


def _source_dependencies() -> dict[str, str]:
    return {
        "tools/phase4_lives_death_breadth.py": _sha256(
            ROOT / "tools/phase4_lives_death_breadth.py"),
        "tools/phase4_e08_operator_contacts.py": _sha256(
            ROOT / "tools/phase4_e08_operator_contacts.py"),
        "analysis/phase4_event_vm.json": _sha256(E07_ARTIFACT),
        "analysis/phase3_scene_asset_graph.json": _sha256(SCENE_GRAPH),
        "analysis/phase1_kind_actor_census.json": _sha256(ACTOR_CENSUS),
        "analysis/mechanics_baseline.yaml": _sha256(MECHANICS),
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    try:
        fixture = build_fixture_census()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        fixture = None
        gaps.append(f"boss-context fixture census failed: {error}")
    if fixture is not None and document.get("fixture_census") != fixture:
        gaps.append("boss-context fixture census changed")
    try:
        context = build_boss_context_identity()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        context = None
        gaps.append(f"boss-context identity failed: {error}")
    if context is not None and document.get("boss_context_identity") != context:
        gaps.append("boss-context identity changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("boss-context source dependencies changed")
    replay = document.get("replay") or {}
    initial = replay.get("initial") or {}
    source_end = replay.get("source_end") or {}
    final = replay.get("final") or {}
    if initial.get("scene") != EXPECTED_SCENE or \
            (initial.get("player") or {}).get("health") != 2 or \
            (initial.get("player") or {}).get("lives") != 0:
        gaps.append("boss-context initial typed state changed")
    if source_end.get("scene") != EXPECTED_SCENE or \
            (source_end.get("player") or {}).get("health") != -1 or \
            (source_end.get("player") or {}).get("lives") != 0:
        gaps.append("boss-context source-end fatal state changed")
    if replay.get("player_delta") != _player_delta(
            initial.get("player") or {}, source_end.get("player") or {}):
        gaps.append("boss-context typed player delta changed")
    law = breadth.derive_law_evidence(replay)
    if replay.get("law_evidence") != law or \
            law.get("classification") != "final_life_game_over_selected" or \
            law.get("required_pcs_present") is not True:
        gaps.append("boss-context resident game-over law changed")
    trace = replay.get("cycle_neutral_trace") or {}
    if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in trace.get("coverage") or []):
        gaps.append("boss-context cycle-neutral coverage changed")
    if final.get("ram_sha256") != (trace.get("control") or {}).get("ram_sha256"):
        gaps.append("boss-context final RAM/control identity changed")
    fatal = replay.get("first_fatal_boundary") or {}
    before = fatal.get("before") or {}
    after = fatal.get("after") or {}
    if fatal.get("movie_frame", 0) <= 0 or \
            (before.get("player") or {}).get("health", -1) < 0 or \
            (after.get("player") or {}).get("health", 0) >= 0 or \
            before.get("scene") != after.get("scene") or \
            after.get("scene") != EXPECTED_SCENE:
        gaps.append("first fatal-health boundary changed")
    invocation = fatal.get("fatal_invocation") or {}
    capture = invocation.get("entry") or {}
    causal = derive_fatal_invocation_causal(invocation)
    if capture.get("valid") is not breadth.derive_entry_capture_valid(capture) or \
            invocation.get("caused_fatal_health") is not causal or causal is not True:
        gaps.append("fatal invocation causal capture changed")
    static = document.get("trigger_static_census") or {}
    try:
        rebuilt_static = breadth.build_trigger_static_census()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        rebuilt_static = None
        gaps.append(f"transition-initiator census failed: {error}")
    if rebuilt_static is not None and static != rebuilt_static:
        gaps.append("transition-initiator census changed")
    attribution = derive_fatal_attribution(fatal, static)
    if fatal.get("attribution") != attribution or \
            attribution.get("exact") is not True or \
            attribution.get("damage_actor_or_hopper_promoted") is not False:
        gaps.append("fatal producer attribution changed")
    runtime = fatal.get("runtime_overlay_identity") or {}
    candidates = runtime.get("candidates") or []
    if runtime.get("scene") != EXPECTED_SCENE or \
            runtime.get("exact_matches") != [] or \
            {row.get("overlay") for row in candidates} != {
                "LEVEL05_LEVEL.BIN", "LEVEL05_LEVEL1.BIN"} or \
            any(row.get("exact_match") for row in candidates):
        gaps.append("save-restored Region-A identity boundary changed")
    for side in (before, after):
        side_trace = side.get("cycle_neutral_trace") or {}
        if (side_trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in side_trace.get("coverage") or []):
            gaps.append("fatal boundary passive coverage changed")
            break
    summary = derive_summary(replay)
    if document.get("summary") != summary or \
            summary.get("boss_context_death_paths") != 1 or \
            summary.get("fatal_invocation_causally_confirmed") is not True or \
            summary.get("resident_game_over_law_complete") is not True or \
            summary.get("hopper_or_damage_actor_promoted") != 0:
        gaps.append("boss-context summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned live process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = build_fixture_census()
    context = build_boss_context_identity()
    static = breadth.build_trigger_static_census()
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
        "emulator.getStateInfo", "movie.load", "movie.startPlayback",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C16 boss-death methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / SAVE_REL, media_identity)
    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-c16-boss-death-") as temp_dir_text:
        replay = _run_movie(client, fixture, Path(temp_dir_text), static)
    final_media = verified_media_identity(client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_c16_boss_death.py",
        anchor={
            "type": "existing state-anchored Stage-15 boss-context death lead",
            "save": SAVE_REL, "movie": MOVIE_REL,
            "fixture_sha256": {SAVE_REL: fixture["save"]["sha256"]},
            "state_inspections": [inspection],
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_format": "v1 digital-only; analog axes absent by format",
            "movie_end_rule": (
                "consume all 2,983 source samples; current v1 runtime reports "
                "last zero-based frame/index 2,982 and remains playing at EOF"),
            "trace_mode": (
                "movie.traceToFrame cached-interpreter control/coverage pairs"),
            "causal_capture": (
                "first fatal frame N: replay N-1, stop at next 0x8004A700, "
                "run to architectural return and read typed state"),
        })
    document = {
        "_comment": (
            "Active C16 breadth: one final-life death in the verified Stage-15 "
            "boss context. The exact producer is derived from live caller "
            "execution; Hopper damage causation and D20/F15 completion are not claimed."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-boss-death/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "boss_context_identity": context,
        "trigger_static_census": static,
        "replay": replay,
        "summary": derive_summary(replay),
        "bounded_interpretation": {
            "observation": (
                "The pristine v1 recording begins in live scene 15 at health/lives "
                "2/0, crosses one exact fatal-health frame, and reaches the resident "
                "final-life selector with cycle-neutral passive coverage."),
            "inference": (
                "Live scene 15 plus the authoritative scene graph and F15/D20 "
                "fixture routing classify a Canyon-Showdown boss context. The "
                "save-restored Region-A bytes match neither staged LEVEL05 image."),
            "causal_confirmation": (
                "A separate replay stops at the next transition-initiator entry "
                "after the fatal boundary and runs that invocation to its return; "
                "health changes from nonfatal to negative while lives and scene stay fixed."),
            "forbidden_claim": (
                "Do not infer from the filename/context that Hopper or any actor "
                "caused the damage, complete D20/F15, or generalize to other boss, "
                "scripted, bonus, special or exceptional deaths."),
        },
        "bounded_open_frontier": {
            "producer_owner": (
                "The exact native caller path is retained; actor/hazard species and "
                "boss attack ownership remain in D20/E10."),
            "overlay_residency": (
                "The runtime Region-A hashes differ from both staged LEVEL05 "
                "candidates; scene identity is not upgraded to exact live file identity."),
            "death_classes": (
                "Other bosses, scripted, bonus, special and exceptional deaths remain open."),
            "frontend_card": (
                "Explicit Save/Load, alternate title/menu choices, no-card and "
                "corrupt-card behavior remain open."),
            "next_experiment": (
                "Reuse an existing bonus or scripted-death lead and bind its fatal "
                "producer without assigning ownership from its filename."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 boss-death evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(
        "[c16-boss-death] Stage-15 final-life path joined to "
        f"{document['summary']['producer_path_id']} at "
        f"{document['summary']['producer_link_call_address']}; C16 remains active")
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
                args, generator="tools/phase4_c16_boss_death.py",
                anchor={"type": "aborted before retained C16 boss-death evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned C16 boss-death cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
