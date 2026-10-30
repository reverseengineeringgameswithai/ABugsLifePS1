#!/usr/bin/env python3
"""Bind one Bonus-3 contact death to the resident C16 lifecycle law.

The operator filename and Phase-1 row are context leads, not damage-owner
authority.  This generator verifies the centrally pinned v3 movie/state pair,
inspects the state before load, replays the natural health 1 -> 0 contact, then
changes only true health from 1 to 0 at the exact pre-contact movie boundary.
The same native invocation must produce health -1/master-state 2 and ordinary
respawn must restore health 4 while decrementing lives 5 -> 4.  Separate
cached-interpreter coverage passes prove the mutated replay remains cycle/RAM/
register/frame neutral; a bounded breakpoint replay attributes only the exact
resident caller and architectural return.
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
except ModuleNotFoundError:  # imported as tools.phase4_c16_bonus_death
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_lives_death_breadth as breadth
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, retained_pristine_save_gaps,
        verified_media_identity, verify_declared_save_fixture,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_c16_bonus_death.json"
MOVIE_REL = "movies/Bonus_Level_03.movie.json"
SAVE_REL = "movies/Bonus_Level_03.movie.sav"
STAGE_BASELINE = ROOT / "analysis/phase2_stage_baseline.json"
ROW_COVERAGE = ROOT / "analysis/phase2_row_coverage.json"
MECHANICS = ROOT / "analysis/mechanics_baseline.yaml"
E07_ARTIFACT = ROOT / "analysis/phase4_event_vm.json"

SCENE = 0x80082504
MASTER_STATE = 0x800823A0
HEALTH = 0x800A6594
LIVES = 0x800A65A0
EXPECTED_SCENE = 3
PRE_HIT_FRAME = 210
HIT_FRAME = 211
RESPAWN_FRAME = 331
TRANSITION_ENTRY = 0x8004A700
EXPECTED_CALL = 0x8004B4A0
EXPECTED_CALL_WORD = 0x0C0129C0

COVERAGE_RANGES = (
    breadth.TRACE_RANGES[0],
    breadth.TRACE_RANGES[1],
    breadth.TRACE_RANGES[2],
    next(row for row in breadth.TRIGGER_TRACE_RANGES
         if row["label"] == "proximity_updater"),
)
REQUIRED_PCS = {
    "proximity_call": "0x8004b4a0",
    "transition_entry": "0x8004a700",
    "fatal_health_write": "0x8004a888",
    "ordinary_respawn_call": "0x800500f4",
    "respawn_health_restore": "0x8005b30c",
    "respawn_lives_decrement": "0x8005b348",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_memory(client: Any, address: int, length: int) -> bytes:
    row = client.call("debugger.readMemory", {
        "address": f"0x{address:08X}", "length": length})
    data = bytes.fromhex(row["hex"])
    if len(data) != length or row.get("valid_bytes") != length:
        raise SystemExit(
            f"short debugger read at 0x{address:08X}: "
            f"{row.get('valid_bytes')}/{length}")
    return data


def _main_ram(client: Any) -> bytes:
    # Current source caps debugger.readMemory at 1 MiB per request.
    return (
        _read_memory(client, 0x80000000, 1 << 20) +
        _read_memory(client, 0x80100000, 1 << 20)
    )


def _register_sha256(client: Any) -> str:
    registers = client.call("debugger.getRegisters", {})["registers_hex"]
    canonical = json.dumps(registers, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _snapshot(client: Any, *, include_full_ram: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    result = {
        "emulator_frame": status["frame"], "cycle": status["cycle"],
        "pc": status["pc"], "sp": status["sp"],
        "paused": status["paused"],
        "scene": struct.unpack("<I", _read_memory(client, SCENE, 4))[0],
        "master_state": struct.unpack(
            "<H", _read_memory(client, MASTER_STATE, 2))[0],
        "health": struct.unpack("<h", _read_memory(client, HEALTH, 2))[0],
        "lives": _read_memory(client, LIVES, 1)[0],
        "movie_frame": movie.get("playback_index"),
        "movie_playing": movie.get("playing"),
        "movie_reproducible": movie.get("reproducible"),
        "movie_truncated": movie.get("truncated"),
    }
    if include_full_ram:
        ram = _main_ram(client)
        result["main_ram_sha256"] = hashlib.sha256(ram).hexdigest()
        result["registers_sha256"] = _register_sha256(client)
    return result


def _semantic_signature(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: snapshot[key] for key in (
        "emulator_frame", "cycle", "pc", "sp", "scene", "master_state",
        "health", "lives", "movie_frame", "movie_playing",
        "movie_reproducible", "movie_truncated", "main_ram_sha256",
        "registers_sha256")}


def _machine_signature(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Exact machine boundary independent of suffix-movie frame numbering."""
    return {key: snapshot[key] for key in (
        "emulator_frame", "cycle", "pc", "sp", "scene", "master_state",
        "health", "lives", "main_ram_sha256", "registers_sha256")}


def _suffix_direct_relation(
        suffix: dict[str, Any], direct: dict[str, Any]) -> dict[str, Any]:
    return {
        "emulator_frame_equal": suffix.get("emulator_frame") ==
            direct.get("emulator_frame"),
        "pc_sp_equal": (suffix.get("pc"), suffix.get("sp")) ==
            (direct.get("pc"), direct.get("sp")),
        "typed_lifecycle_equal": tuple(suffix.get(key) for key in (
            "scene", "master_state", "health", "lives")) ==
            tuple(direct.get(key) for key in (
                "scene", "master_state", "health", "lives")),
        "registers_sha256_equal": suffix.get("registers_sha256") ==
            direct.get("registers_sha256"),
        "cycle_delta_suffix_minus_direct": (
            suffix.get("cycle", 0) - direct.get("cycle", 0)),
        "main_ram_sha256_equal": suffix.get("main_ram_sha256") ==
            direct.get("main_ram_sha256"),
        "boundary": (
            "The transient save/reload suffix is an independent internally "
            "control-checked anchor. Two fresh isolated iteration-1 replays "
            "reproduce the same bounded terminal relation: registers, PC/SP, "
            "emulator frame and typed C16 outcome match, while save/reload "
            "cycle accounting is exactly one cycle earlier and the full-RAM "
            "digest remains distinct. Both exact terminal hashes are retained."),
    }


def _cleanup(client: Any) -> None:
    try:
        client.call("debugger.clearBreakpoints", {})
    except Exception:
        pass
    contacts._cleanup_movie(client)


def _start_movie(client: Any, movie_path: Path) -> dict[str, Any]:
    _cleanup(client)
    loaded = client.call("movie.load", {"path": str(movie_path.resolve())})
    started = client.call(
        "movie.startPlayback", {"start_frame": 0, "load_start_state": True})
    if loaded.get("frame_count") != 5020 or \
            started.get("reproducible") is not True or \
            started.get("truncated") is not False:
        raise SystemExit(f"Bonus-3 movie did not start reproducibly: {started}")
    return {"loaded": loaded, "started": started}


def _advance_to(client: Any, frame: int, *, max_frames: int) -> dict[str, Any]:
    result = client.call("movie.advanceToFrame", {
        "frame": frame, "max_frames": max_frames}, timeout=900)
    status = client.call("movie.status", {})
    if status.get("reproducible") is not True or \
            status.get("truncated") is not False or \
            status.get("playback_index") != frame:
        raise SystemExit(f"Bonus-3 movie lost frame {frame}: {status}")
    return result


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    movie_path, save_path = ROOT / MOVIE_REL, ROOT / SAVE_REL
    movie_pin = entries.get(MOVIE_REL)
    save = verify_declared_save_fixture(
        save_path, allowed_media_classes={"pristine"})
    if not isinstance(movie_pin, dict) or \
            movie_pin.get("media_class") not in {"pristine", "pristine_serial"} or \
            movie_pin.get("size") != movie_path.stat().st_size or \
            movie_pin.get("sha256") != _sha256(movie_path):
        raise SystemExit(f"Bonus-3 movie pin drifted: {MOVIE_REL}")
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
        "triangle", "up", "lx", "ly", "rx", "ry",
    }
    if movie.get("version") != 3 or \
            movie.get("game_serial") != "SCUS-94288" or \
            movie.get("initial_frame") != 49294 or len(frames) != 5020 or \
            start.get("game_serial") != "SCUS-94288" or \
            start.get("from_boot") is not False or \
            start.get("reproducible_only_from_state") is not True or \
            Path(start.get("path", "")).name != Path(SAVE_REL).name or \
            start.get("file_size") != save["size"] or keys != expected_keys:
        raise SystemExit("Bonus-3 movie metadata or recorded input scope drifted")
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "lead": "centrally declared Bonus-3 operator movie/state pair",
        "movie": {
            "path": MOVIE_REL, "sha256": movie_pin["sha256"],
            "size": movie_pin["size"],
            "media_class": movie_pin["media_class"], "version": 3,
            "frames": len(frames), "initial_frame": movie["initial_frame"],
            "recorded_input_scope": (
                "all 16 digital buttons; optional v3 analog axes lx/ly/rx/ry"),
        },
        "save": save,
        "classification_boundary": (
            "The F18 filename/route establishes a Bonus-3 context lead only; "
            "typed state and executed code determine the C16 claim."),
    }


def build_bonus_context_identity() -> dict[str, Any]:
    import yaml

    stage = (json.loads(STAGE_BASELINE.read_text()).get("stages") or {}).get(
        "bonus3_grasshoppers") or {}
    coverage = (json.loads(ROW_COVERAGE.read_text()).get("rows") or {}).get(
        "F18_bonus3_grasshoppers") or {}
    mechanics = yaml.safe_load(MECHANICS.read_text())
    row = next((item for item in mechanics.get("rows") or []
                if item.get("id") == "F18_bonus3_grasshoppers"), {})
    fixture_entry = (
        json.loads(FIXTURE_SET.read_text()).get("entries") or {}).get(
            MOVIE_REL) or {}
    result = {
        "phase2_stage_anchor": {
            "role": stage.get("role"), "save": stage.get("save"),
            "save_sha256": stage.get("save_sha256"),
            "scene_id": (stage.get("anchor") or {}).get("scene_id"),
            "lives": (stage.get("anchor") or {}).get("lives"),
            "enemy_quota": (stage.get("anchor") or {}).get("enemy_quota"),
        },
        "phase2_row_route": coverage,
        "baseline_row": {
            "id": row.get("id"), "name": row.get("name"),
            "stages": row.get("stages"), "status": row.get("status"),
            "movie_declared": MOVIE_REL in (row.get("fixture_have") or []),
            "save_declared": SAVE_REL in (row.get("fixture_have") or []),
        },
        "central_required_routes": sorted(
            set(fixture_entry.get("consumers") or {}) & {
                "mechanics:F18_bonus3_grasshoppers",
                "mechanics:C18_bonus_entry",
            }),
        "classification": (
            "confirmed Bonus-3 context only; no named grasshopper, actor slot, "
            "attack, F18 rule, reward, or permanent-kill ownership is promoted"),
    }
    expected = {
        "role": "identity_bonus", "save": SAVE_REL,
        "save_sha256": "0dd145be44878df0424eee7942c9f645d4b0961e1bfe0a831e6acf0538d6b522",
        "scene_id": EXPECTED_SCENE, "lives": 5, "enemy_quota": 50,
    }
    if result["phase2_stage_anchor"] != expected or \
            coverage.get("status") != "pristine_trigger" or \
            set(coverage.get("pristine_fixtures") or []) != {
                MOVIE_REL, SAVE_REL} or \
            result["baseline_row"] != {
                "id": "F18_bonus3_grasshoppers",
                "name": "Bonus 3: consecutive grasshopper kills, no missed blue berry",
                "stages": "bonus", "status": "partial",
                "movie_declared": True, "save_declared": True} or \
            result["central_required_routes"] != [
                "mechanics:C18_bonus_entry",
                "mechanics:F18_bonus3_grasshoppers"]:
        raise SystemExit(f"Bonus-3 context routing drifted: {result}")
    return result


def _natural_trace(
        client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    trace = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": [breadth.TRACE_RANGES[0], COVERAGE_RANGES[-1]]},
        timeout=900)
    compact = contacts._compact_trace(trace)
    snapshot = _snapshot(client)
    if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in compact.get("coverage") or []):
        raise SystemExit(f"natural Bonus-3 trace was not cycle neutral: {compact}")
    return {"snapshot": snapshot, "cycle_neutral_trace": compact}


def _run_natural_control(client: Any, movie_path: Path) -> dict[str, Any]:
    before = _natural_trace(client, movie_path, PRE_HIT_FRAME)
    after = _natural_trace(client, movie_path, HIT_FRAME)
    before_typed, after_typed = before["snapshot"], after["snapshot"]
    pcs = {
        str(pc).lower() for row in after["cycle_neutral_trace"]["coverage"]
        for pc in row.get("pcs") or []}
    result = {
        "before": before, "after": after,
        "derived_delta": {
            "health": after_typed["health"] - before_typed["health"],
            "lives": after_typed["lives"] - before_typed["lives"],
            "scene_equal": before_typed["scene"] == after_typed["scene"],
            "call_and_target_present": {
                REQUIRED_PCS["proximity_call"],
                REQUIRED_PCS["transition_entry"]}.issubset(pcs),
        },
    }
    if (before_typed["scene"], before_typed["health"],
            before_typed["lives"], before_typed["master_state"]) != (
                EXPECTED_SCENE, 1, 5, 0) or \
            (after_typed["scene"], after_typed["health"],
             after_typed["lives"], after_typed["master_state"]) != (
                EXPECTED_SCENE, 0, 5, 0) or \
            result["derived_delta"] != {
                "health": -1, "lives": 0, "scene_equal": True,
                "call_and_target_present": True}:
        raise SystemExit(f"natural Bonus-3 health boundary drifted: {result}")
    return result


def _prepare_mutation(
        client: Any, movie_path: Path) -> tuple[dict[str, Any], bytes,
                                                dict[str, Any], bytes]:
    _start_movie(client, movie_path)
    _advance_to(client, PRE_HIT_FRAME, max_frames=PRE_HIT_FRAME + 10)
    before = _snapshot(client, include_full_ram=True)
    before_ram = _main_ram(client)
    write = client.call("debugger.writeU16", {
        "address": f"0x{HEALTH:08X}", "value": 0})
    after = _snapshot(client, include_full_ram=True)
    after_ram = _main_ram(client)
    differences = [
        {"address": f"0x{0x80000000 + index:08x}",
         "before": before_ram[index], "after": after_ram[index]}
        for index in range(len(before_ram))
        if before_ram[index] != after_ram[index]
    ]
    if before["health"] != 1 or after["health"] != 0 or \
            before["scene"] != after["scene"] or \
            before["lives"] != after["lives"] or \
            before["emulator_frame"] != after["emulator_frame"] or \
            before["cycle"] != after["cycle"] or \
            differences != [{
                "address": "0x800a6594", "before": 1, "after": 0}] or \
            write.get("written") != 2:
        raise SystemExit(
            f"Bonus-3 one-field mutation was not isolated: {differences}")
    mutation = {
        "method": "debugger.writeU16",
        "address": f"0x{HEALTH:08x}", "value": 0,
        "response": write, "main_ram_differences": differences,
        "main_ram_difference_count": len(differences),
    }
    return before, before_ram, mutation, after_ram


def _run_mutated_behavior(
        client: Any, movie_path: Path) -> dict[str, Any]:
    before, _before_ram, mutation, _after_ram = _prepare_mutation(
        client, movie_path)
    written = _snapshot(client, include_full_ram=True)
    _advance_to(client, HIT_FRAME, max_frames=2)
    fatal = _snapshot(client, include_full_ram=True)
    _advance_to(client, RESPAWN_FRAME, max_frames=RESPAWN_FRAME - HIT_FRAME + 5)
    respawn = _snapshot(client, include_full_ram=True)
    result = {
        "pre_hit": before, "mutation": mutation,
        "post_write": written, "fatal_boundary": fatal,
        "completed_respawn": respawn,
        "terminal_signature": _semantic_signature(respawn),
    }
    if (fatal["scene"], fatal["health"], fatal["lives"],
            fatal["master_state"], fatal["movie_frame"]) != (
                EXPECTED_SCENE, -1, 5, 2, HIT_FRAME) or \
            (respawn["scene"], respawn["health"], respawn["lives"],
             respawn["master_state"], respawn["movie_frame"]) != (
                EXPECTED_SCENE, 4, 4, 0, RESPAWN_FRAME):
        raise SystemExit(f"Bonus-3 mutated lifecycle drifted: {result}")
    return result


def _create_mutated_suffix(
        client: Any, movie_path: Path, temp_dir: Path,
        expected_pre: dict[str, Any], expected_mutation: dict[str, Any]
        ) -> tuple[Path, dict[str, Any]]:
    before, _before_ram, mutation, _after_ram = _prepare_mutation(
        client, movie_path)
    if _semantic_signature(before) != _semantic_signature(expected_pre) or \
            mutation["main_ram_differences"] != \
            expected_mutation["main_ram_differences"]:
        raise SystemExit("Bonus-3 suffix derivation lost its exact mutation anchor")
    mutated = _snapshot(client, include_full_ram=True)
    state_path = temp_dir / "bonus3-health0-prehit.sav"
    saved = client.call("emulator.saveState", {"path": str(state_path.resolve())})
    state_info = client.call(
        "emulator.getStateInfo", {"path": str(state_path.resolve())})
    if saved.get("saved") is not True or state_info.get("valid") is not True or \
            state_info.get("serial") != "SCUS-94288" or \
            Path(state_info.get("media_path") or "").name != \
            "Disney-Pixar A Bug's Life (v1.0).cue":
        raise SystemExit(
            f"Bonus-3 transient suffix state failed inspection: {saved}/{state_info}")

    source = json.loads(movie_path.read_text())
    derivative = copy.deepcopy(source)
    frames = copy.deepcopy(source["frames"][PRE_HIT_FRAME:])
    for index, row in enumerate(frames):
        row["frame"] = index
    derivative["frames"] = frames
    derivative["initial_frame"] = mutated["emulator_frame"]
    derivative["start_state"] = {
        "path": str(state_path.resolve()), "loaded_before_recording": True,
        "from_boot": False, "game_serial": "SCUS-94288",
        "game_title": source.get("game_title"),
        "frame": mutated["emulator_frame"], "pc": mutated["pc"],
        "sp": mutated["sp"], "file_size": state_path.stat().st_size,
        "sha256": _sha256(state_path),
        "reproducible_only_from_state": True,
    }
    movie_out = temp_dir / "bonus3-health0-prehit.movie.json"
    movie_out.write_text(json.dumps(derivative, separators=(",", ":")) + "\n")
    canonical = copy.deepcopy(derivative)
    canonical["start_state"]["path"] = "<transient-derived-state>"
    canonical_hash = hashlib.sha256(
        (json.dumps(canonical, sort_keys=True, separators=(",", ":")) + "\n")
        .encode()).hexdigest()
    recipe = {
        "source_movie": MOVIE_REL, "source_movie_sha256": _sha256(movie_path),
        "source_state": SAVE_REL, "source_state_sha256": _sha256(ROOT / SAVE_REL),
        "source_frame": PRE_HIT_FRAME,
        "suffix_frame_count": len(frames),
        "suffix_boundaries": {
            "pre_hit": 0, "fatal_hit": HIT_FRAME - PRE_HIT_FRAME,
            "ordinary_respawn": RESPAWN_FRAME - PRE_HIT_FRAME},
        "mutation": mutation,
        "derived_state": {
            "sha256": _sha256(state_path), "size": state_path.stat().st_size,
            "version": state_info.get("version"),
            "serial": state_info.get("serial"),
            "main_ram_sha256": mutated["main_ram_sha256"]},
        "derived_movie": {
            "sha256": canonical_hash, "size": movie_out.stat().st_size,
            "hash_normalization": (
                "canonical JSON with start_state.path replaced by "
                "<transient-derived-state>")},
        "transient_storage": (
            "temporary directory; derivative state/movie deleted before retention"),
    }
    return movie_out, recipe


def _trace_suffix(
        client: Any, movie_path: Path, target: int) -> dict[str, Any]:
    trace = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": target,
        "ranges": list(COVERAGE_RANGES)}, timeout=900)
    compact = contacts._compact_trace(trace)
    snapshot = _snapshot(client, include_full_ram=True)
    if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in compact.get("coverage") or []):
        raise SystemExit(f"Bonus-3 suffix trace was not cycle neutral: {compact}")
    return {"suffix_movie_frame": target, "snapshot": snapshot,
            "cycle_neutral_trace": compact}


def _wait_for_pause(client: Any, label: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while True:
        status = client.call("debugger.status", {})
        if status.get("paused") is True:
            return status
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for {label}")
        time.sleep(0.01)


def _capture_fatal_invocation(
        client: Any, movie_path: Path,
        expected_pre: dict[str, Any]) -> dict[str, Any]:
    before, _before_ram, mutation, _after_ram = _prepare_mutation(
        client, movie_path)
    if _semantic_signature(before) != _semantic_signature(expected_pre):
        raise SystemExit("fatal invocation replay lost its exact pre-hit anchor")
    client.call("debugger.runUntilAddress", {
        "address": f"0x{TRANSITION_ENTRY:08X}"})
    _wait_for_pause(client, "Bonus-3 fatal transition entry")
    registers = {
        str(key).lower(): value for key, value in
        client.call("debugger.getRegisters", {})["registers_hex"].items()}
    pc, ra = int(registers["pc"], 16), int(registers["ra"], 16)
    call_address = (ra - 8) & 0xFFFFFFFF
    word = struct.unpack("<I", _read_memory(client, call_address, 4))[0]
    before_call = _snapshot(client)
    code = _read_memory(client, call_address - 8, 24)
    client.call("debugger.runUntilAddress", {"address": f"0x{ra:08X}"})
    _wait_for_pause(client, "Bonus-3 fatal invocation return")
    after_return = _snapshot(client)
    result = {
        "entry": {
            "pc": f"0x{pc:08x}", "ra": f"0x{ra:08x}",
            "link_call_address": f"0x{call_address:08x}",
            "instruction_word": f"0x{word:08x}", "call_kind": "jal",
            "resolved_target": f"0x{TRANSITION_ENTRY:08x}",
            "arguments": {
                name: registers[name] for name in ("a0", "a1", "a2", "a3")},
            "code_slice": {
                "address": f"0x{call_address - 8:08x}", "length": len(code),
                "sha256": hashlib.sha256(code).hexdigest()},
        },
        "mutation": mutation,
        "before_call": before_call, "after_return": after_return,
        "returned_to": f"0x{ra:08x}",
    }
    result["caused_fatal_transition"] = bool(
        pc == TRANSITION_ENTRY and call_address == EXPECTED_CALL and
        word == EXPECTED_CALL_WORD and
        (before_call["scene"], before_call["health"], before_call["lives"],
         before_call["master_state"]) == (EXPECTED_SCENE, 0, 5, 0) and
        (after_return["scene"], after_return["health"],
         after_return["lives"], after_return["master_state"]) == (
            EXPECTED_SCENE, -1, 5, 2) and
        after_return["pc"].lower() == result["returned_to"])
    if result["caused_fatal_transition"] is not True:
        raise SystemExit(f"Bonus-3 fatal invocation was not causal: {result}")
    return result


def _required_pc_coverage(passes: list[dict[str, Any]]) -> dict[str, Any]:
    pcs = {
        str(pc).lower() for retained in passes
        for row in ((retained.get("cycle_neutral_trace") or {}).get(
            "coverage") or [])
        for pc in row.get("pcs") or []}
    return {
        "observed": {name: pc in pcs for name, pc in REQUIRED_PCS.items()},
        "all_present": set(REQUIRED_PCS.values()).issubset(pcs),
    }


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    natural = document.get("natural_control") or {}
    behavior = document.get("causal_health_control") or {}
    invocation = document.get("fatal_invocation") or {}
    traces = document.get("cycle_neutral_suffix_traces") or []
    coverage = _required_pc_coverage(traces)
    before = ((natural.get("before") or {}).get("snapshot") or {})
    after = ((natural.get("after") or {}).get("snapshot") or {})
    fatal = behavior.get("fatal_boundary") or {}
    respawn = behavior.get("completed_respawn") or {}
    return {
        "movies_replayed": 1,
        "bonus_contexts_bounded": int(
            (document.get("bonus_context_identity") or {}).get(
                "classification", "").startswith("confirmed Bonus-3 context")),
        "natural_health_delta": after.get("health", 0) - before.get("health", 0),
        "mutation_main_ram_difference_count": (
            (behavior.get("mutation") or {}).get(
                "main_ram_difference_count")),
        "fatal_health": fatal.get("health"),
        "respawn_health_lives": [respawn.get("health"), respawn.get("lives")],
        "producer_path_id": (
            "proximity_contact" if
            (invocation.get("entry") or {}).get("link_call_address") ==
            "0x8004b4a0" else None),
        "fatal_invocation_causally_confirmed": (
            invocation.get("caused_fatal_transition") is True),
        "coverage_required_pcs": coverage,
        "all_coverage_passes_cycle_ram_register_frame_neutral": all(
            ((row.get("cycle_neutral_trace") or {}).get(
                "comparison") or {}).get("cycle_neutral") is True and
            not any(item.get("truncated") for item in
                    (row.get("cycle_neutral_trace") or {}).get("coverage") or [])
            for row in traces),
        "named_enemy_or_f18_promoted": 0,
    }


def _source_dependencies() -> dict[str, str]:
    return {
        "tools/phase4_lives_death_breadth.py": _sha256(
            ROOT / "tools/phase4_lives_death_breadth.py"),
        "tools/phase4_e08_operator_contacts.py": _sha256(
            ROOT / "tools/phase4_e08_operator_contacts.py"),
        "analysis/phase4_event_vm.json": _sha256(E07_ARTIFACT),
        "analysis/phase2_stage_baseline.json": _sha256(STAGE_BASELINE),
        "analysis/phase2_row_coverage.json": _sha256(ROW_COVERAGE),
        "analysis/mechanics_baseline.yaml": _sha256(MECHANICS),
        "analysis/phase0_2_external_fixture_set.json": _sha256(FIXTURE_SET),
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    try:
        fixture = build_fixture_census()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        fixture = None
        gaps.append(f"Bonus-3 fixture census failed: {error}")
    if fixture is not None and document.get("fixture_census") != fixture:
        gaps.append("Bonus-3 fixture census changed")
    try:
        context = build_bonus_context_identity()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        context = None
        gaps.append(f"Bonus-3 context identity failed: {error}")
    if context is not None and document.get("bonus_context_identity") != context:
        gaps.append("Bonus-3 context identity changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Bonus-3 source dependencies changed")
    try:
        static = breadth.build_trigger_static_census()
    except (OSError, KeyError, ValueError, SystemExit) as error:
        static = None
        gaps.append(f"transition-initiator census failed: {error}")
    if static is not None and document.get("trigger_static_census") != static:
        gaps.append("transition-initiator census changed")
    natural = document.get("natural_control") or {}
    before = ((natural.get("before") or {}).get("snapshot") or {})
    after = ((natural.get("after") or {}).get("snapshot") or {})
    if (before.get("scene"), before.get("health"), before.get("lives"),
            before.get("master_state"), before.get("movie_frame")) != (
                EXPECTED_SCENE, 1, 5, 0, PRE_HIT_FRAME) or \
            (after.get("scene"), after.get("health"), after.get("lives"),
             after.get("master_state"), after.get("movie_frame")) != (
                EXPECTED_SCENE, 0, 5, 0, HIT_FRAME):
        gaps.append("natural Bonus-3 health boundary changed")
    for side in (natural.get("before") or {}, natural.get("after") or {}):
        trace = side.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append("natural Bonus-3 trace neutrality changed")
            break
    behavior = document.get("causal_health_control") or {}
    mutation = behavior.get("mutation") or {}
    fatal = behavior.get("fatal_boundary") or {}
    respawn = behavior.get("completed_respawn") or {}
    if mutation.get("main_ram_differences") != [{
            "address": "0x800a6594", "before": 1, "after": 0}] or \
            (fatal.get("health"), fatal.get("lives"),
             fatal.get("master_state"), fatal.get("movie_frame")) != (
                -1, 5, 2, HIT_FRAME) or \
            (respawn.get("health"), respawn.get("lives"),
             respawn.get("master_state"), respawn.get("movie_frame")) != (
                4, 4, 0, RESPAWN_FRAME):
        gaps.append("causal Bonus-3 lifecycle changed")
    recipe = document.get("transient_suffix_recipe") or {}
    if recipe.get("source_frame") != PRE_HIT_FRAME or \
            recipe.get("suffix_boundaries") != {
                "pre_hit": 0, "fatal_hit": 1, "ordinary_respawn": 121} or \
            (recipe.get("mutation") or {}).get("main_ram_differences") != [{
                "address": "0x800a6594", "before": 1, "after": 0}] or \
            (recipe.get("derived_state") or {}).get("serial") != "SCUS-94288":
        gaps.append("Bonus-3 transient suffix recipe changed")
    derived_movie = recipe.get("derived_movie") or {}
    if len(str(derived_movie.get("sha256") or "")) != 64 or \
            derived_movie.get("hash_normalization") != (
                "canonical JSON with start_state.path replaced by "
                "<transient-derived-state>"):
        gaps.append("Bonus-3 transient movie hash normalization changed")
    warmup = document.get("discarded_execution_mode_warmup") or {}
    warm_trace = warmup.get("cycle_neutral_trace") or {}
    if warmup.get("suffix_movie_frame") != 0 or \
            (warm_trace.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in warm_trace.get("coverage") or []):
        gaps.append("Bonus-3 discarded execution-mode warm-up changed")
    traces = document.get("cycle_neutral_suffix_traces") or []
    if [row.get("suffix_movie_frame") for row in traces] != [0, 1, 121]:
        gaps.append("Bonus-3 suffix trace boundaries changed")
    else:
        typed = [row.get("snapshot") or {} for row in traces]
        if [(row.get("scene"), row.get("health"), row.get("lives"),
             row.get("master_state")) for row in typed] != [
                (EXPECTED_SCENE, 0, 5, 0),
                (EXPECTED_SCENE, -1, 5, 2),
                (EXPECTED_SCENE, 4, 4, 0)]:
            gaps.append("Bonus-3 suffix typed lifecycle changed")
        relation = _suffix_direct_relation(typed[-1], respawn)
        if document.get("suffix_direct_terminal_relation") != relation or \
                relation.get("emulator_frame_equal") is not True or \
                relation.get("pc_sp_equal") is not True or \
                relation.get("typed_lifecycle_equal") is not True or \
                relation.get("registers_sha256_equal") is not True or \
                relation.get("cycle_delta_suffix_minus_direct") != -1 or \
                relation.get("main_ram_sha256_equal") is not False:
            gaps.append("Bonus-3 exact suffix/direct terminal relation changed")
    for row in traces:
        trace = row.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(item.get("truncated") for item in trace.get("coverage") or []):
            gaps.append("Bonus-3 suffix trace neutrality changed")
            break
    required = _required_pc_coverage(traces)
    if required["all_present"] is not True:
        gaps.append("Bonus-3 decisive resident PC coverage changed")
    invocation = document.get("fatal_invocation") or {}
    entry = invocation.get("entry") or {}
    if invocation.get("caused_fatal_transition") is not True or \
            entry.get("link_call_address") != "0x8004b4a0" or \
            entry.get("instruction_word") != "0x0c0129c0" or \
            (invocation.get("before_call") or {}).get("health") != 0 or \
            (invocation.get("after_return") or {}).get("health") != -1:
        gaps.append("Bonus-3 fatal invocation attribution changed")
    summary = derive_summary(document)
    if document.get("summary") != summary or \
            summary.get("bonus_contexts_bounded") != 1 or \
            summary.get("natural_health_delta") != -1 or \
            summary.get("mutation_main_ram_difference_count") != 1 or \
            summary.get("respawn_health_lives") != [4, 4] or \
            summary.get("producer_path_id") != "proximity_contact" or \
            summary.get("fatal_invocation_causally_confirmed") is not True or \
            summary.get("named_enemy_or_f18_promoted") != 0:
        gaps.append("Bonus-3 derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Bonus-3 process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = build_fixture_census()
    context = build_bonus_context_identity()
    static = breadth.build_trigger_static_census()
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
        "emulator.getMediaInfo", "emulator.getStateInfo", "emulator.saveState",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks C16 bonus-death methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / SAVE_REL, media_identity)
    movie_path = ROOT / MOVIE_REL
    natural = _run_natural_control(client, movie_path)
    behavior = _run_mutated_behavior(client, movie_path)
    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-c16-bonus-death-") as temp_dir_text:
        suffix_path, suffix_recipe = _create_mutated_suffix(
            client, movie_path, Path(temp_dir_text), behavior["pre_hit"],
            behavior["mutation"])
        # Discard the first backend-transition call exactly as the E15 live
        # generator does, then retain fresh internally control-checked traces.
        coverage_warmup = _trace_suffix(client, suffix_path, 0)
        suffix_traces = [
            _trace_suffix(client, suffix_path, target)
            for target in (0, 1, RESPAWN_FRAME - PRE_HIT_FRAME)
        ]
        suffix_direct_relation = _suffix_direct_relation(
            suffix_traces[-1]["snapshot"], behavior["completed_respawn"])
        if suffix_direct_relation != {
                "emulator_frame_equal": True,
                "pc_sp_equal": True,
                "typed_lifecycle_equal": True,
                "registers_sha256_equal": True,
                "cycle_delta_suffix_minus_direct": -1,
                "main_ram_sha256_equal": False,
                "boundary": suffix_direct_relation["boundary"]}:
            raise SystemExit(
                "Bonus-3 suffix/direct terminal relation changed: "
                f"{suffix_direct_relation}")
    invocation = _capture_fatal_invocation(
        client, movie_path, behavior["pre_hit"])
    _cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_c16_bonus_death.py",
        anchor={
            "type": "existing state-anchored Bonus-3 contact/death lead",
            "save": SAVE_REL, "movie": MOVIE_REL,
            "fixture_sha256": {SAVE_REL: fixture["save"]["sha256"]},
            "state_inspections": [inspection],
            "media_identity": media_identity,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "movie_format": (
                "v3 all digital buttons; optional analog axes recorded"),
            "boundaries": {
                "pre_hit": PRE_HIT_FRAME, "hit": HIT_FRAME,
                "ordinary_respawn": RESPAWN_FRAME},
            "trace_mode": (
                "natural movie.traceToFrame pairs plus a transient one-byte "
                "mutated suffix replayed by internally control-checked "
                "movie.traceToFrame cached-interpreter passes"),
            "causal_capture": (
                "write only true-health 1->0 at movie frame 210; stop at next "
                "0x8004A700 and run exactly to architectural return"),
        })
    document = {
        "_comment": (
            "Active C16 breadth: one Bonus-3 context contact death. A natural "
            "health 1->0 control and one-byte health 1->0 perturbation bind the "
            "same native proximity call to fatal health, resident ordinary "
            "respawn and life decrement without assigning a named enemy or F18."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-bonus-death/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "bonus_context_identity": context,
        "trigger_static_census": static,
        "natural_control": natural,
        "causal_health_control": behavior,
        "transient_suffix_recipe": suffix_recipe,
        "discarded_execution_mode_warmup": coverage_warmup,
        "cycle_neutral_suffix_traces": suffix_traces,
        "suffix_direct_terminal_relation": suffix_direct_relation,
        "fatal_invocation": invocation,
        "bounded_interpretation": {
            "observation": (
                "The pristine v3 replay is scene 3/lives 5 and naturally changes "
                "true health 1->0 at movie frame 211 while executing resident "
                "proximity and damage/death code."),
            "inference": (
                "Phase-2 fixture routing and the pinned start state establish a "
                "Bonus-3 context. The filename does not identify the damage actor."),
            "causal_confirmation": (
                "At the identical frame-210 RAM/cycle boundary, changing only "
                "0x800A6594 from 1 to 0 makes JAL 0x8004B4A0->0x8004A700 "
                "return with health -1/master 2; the native path then restores "
                "health 4 and decrements lives 5->4."),
            "forbidden_claim": (
                "Do not infer grasshopper/species/attack ownership, complete F18, "
                "generalize to all bonus deaths, or close C16 from this control."),
        },
        "bounded_open_frontier": {
            "producer_owner": (
                "The resident producer is exact proximity_contact; actor/source "
                "identity and attack policy remain independently owned."),
            "death_classes": (
                "Other bonus contexts plus scripted, special and exceptional "
                "deaths and boss-actor causation remain open."),
            "frontend_card": (
                "Explicit Save/Load, alternate title/menu choices, no-card and "
                "corrupt-card behavior remain open."),
            "next_experiment": (
                "Reuse an existing scripted/special or exceptional death lead "
                "and bind its exact producer and resident transition law."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 Bonus-3 evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(
        "[c16-bonus-death] Bonus-3 one-field control joined to "
        "proximity_contact and ordinary respawn; C16 remains active")
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
                args, generator="tools/phase4_c16_bonus_death.py",
                anchor={"type": "aborted before retained C16 Bonus-3 evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned C16 Bonus-3 cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
