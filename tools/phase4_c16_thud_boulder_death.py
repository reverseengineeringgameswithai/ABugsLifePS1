#!/usr/bin/env python3
"""Bind one Thud arena boulder contact to C16 final-life selection.

The centrally pinned pristine Thud movie already contains a cycle-neutral,
row-attributed health 3 -> 2 contact.  This generator replays that boundary,
changes only true health from 3 to 0 at a shared pre-contact origin, and stops
at the exact overlay-to-resident call and architectural return.  It proves one
boss-arena final-life path without promoting a scripted/special death class or
claiming complete Thud, arena, or lifecycle policy.
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
    import phase4_thud_arena as arena
    import phase4_thud_defeat as thud
    from live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_c16_thud_boulder_death
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_thud_arena as arena
    from tools import phase4_thud_defeat as thud
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_c16_thud_boulder_death.json"
SCENE_GRAPH = ROOT / "analysis/phase3_scene_asset_graph.json"
ARENA_EVIDENCE = ROOT / "analysis/phase4_thud_arena.json"

ROW = 4
PREPARE_TARGET = 1465
OUTCOME_TARGET = 1471
EXPECTED_CALL = thud.ARENA_DAMAGE_CALL
EXPECTED_RETURN = EXPECTED_CALL + 8
EXPECTED_CALL_WORD = 0x0C0129C0


def _sha256(path: Path) -> str:
    return base._sha256(path)


def build_fixture_census() -> dict[str, Any]:
    return thud.build_fixture_census()


def build_context_identity() -> dict[str, Any]:
    scene = (json.loads(SCENE_GRAPH.read_text()).get("scenes") or {}).get(
        "scene_14") or {}
    retained = json.loads(ARENA_EVIDENCE.read_text())
    natural = next(
        (row for row in retained.get("natural_contacts") or []
         if row.get("row") == ROW), {})
    pre, post = natural.get("pre") or {}, natural.get("post") or {}
    pre_row = pre.get("selected_row") or {}
    post_row = post.get("selected_row") or {}
    result = {
        "scene_graph": {
            key: scene.get(key) for key in (
                "scene_id", "asset_entry", "disc_dir", "overlays",
                "phase2_stage_labels")
        },
        "retained_arena_evidence": {
            "path": ARENA_EVIDENCE.relative_to(ROOT).as_posix(),
            "sha256": _sha256(ARENA_EVIDENCE),
            "schema": retained.get("schema"),
            "campaign_state": retained.get("campaign_state"),
            "all_contact_rows": (retained.get("summary") or {}).get(
                "all_contact_rows"),
            "row": natural.get("row"),
            "targets": [natural.get("pre_target"), natural.get("post_target")],
            "health": [pre.get("player_health"), post.get("player_health")],
            "inside_threshold": [
                pre_row.get("inside"), post_row.get("inside")],
            "threshold": post_row.get("threshold"),
            "squared_distance": post_row.get("squared_distance"),
            "speed": [pre_row.get("speed"), post_row.get("speed")],
            "ramp": [pre_row.get("ramp"), post_row.get("ramp")],
            "trace_cycle_neutral": all(
                (((natural.get("passive_traces") or {}).get(side) or {}).get(
                    "comparison") or {}).get("cycle_neutral") is True
                for side in ("pre", "post")),
        },
        "classification": (
            "Pristine scene 14 / Stage 09 Bug Bar boss-arena context. The "
            "retained row evidence, not the movie filename, establishes the "
            "row-4 rolling-arena contact."),
    }
    expected = {
        "scene_graph": {
            "scene_id": 14, "asset_entry": "level08\\level5b",
            "disc_dir": "level08",
            "overlays": {"LEVEL08_LEVEL": 6, "LEVEL08_LEVEL1": 6},
            "phase2_stage_labels": ["stage09_bug_bar"],
        },
        "retained_arena_evidence": {
            "path": "analysis/phase4_thud_arena.json",
            "sha256": _sha256(ARENA_EVIDENCE),
            "schema": "abl-phase4-thud-arena/1",
            "campaign_state": "active_partial",
            "all_contact_rows": [0, 1, 2, 3, 4, 5],
            "row": 4, "targets": [1470, 1471], "health": [3, 2],
            "inside_threshold": [False, True], "threshold": 490000,
            "squared_distance": 420045, "speed": [-110, 110],
            "ramp": [104, 0], "trace_cycle_neutral": True,
        },
        "classification": result["classification"],
    }
    if result != expected:
        raise SystemExit(f"Thud C16 context identity drifted: {result}")
    return result


def _snapshot(client: Any, *, full_identity: bool = False) -> dict[str, Any]:
    result = arena._snapshot(client, ROW, full_identity=full_identity)
    result["lives"] = struct.unpack(
        "<B", base._read_memory(client, thud.LIVES, 1))[0]
    return result


def _prepare(client: Any, movie_path: Path, *, mutate: bool) -> dict[str, Any]:
    thud._advance_movie_to(client, movie_path, PREPARE_TARGET)
    before = _snapshot(client, full_identity=True)
    before_ram = base._main_ram(client)
    mutation = None
    if mutate:
        write = client.call("debugger.writeU16", {
            "address": f"0x{thud.HEALTH:08X}", "value": 0})
        after = _snapshot(client, full_identity=True)
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
        stable = ("emulator_frame", "cycle", "movie_frame", "scene", "lives")
        if before["player_health"] != 3 or after["player_health"] != 0 or \
                any(before[key] != after[key] for key in stable) or \
                differences != [{
                    "address": "0x800a6594", "before": 3, "after": 0}] or \
                write.get("written") != 2:
            raise SystemExit(f"Thud health mutation was not isolated: {mutation}")
    return {"origin": before, "mutation": mutation}


def _capture_invocation(
        client: Any, movie_path: Path, *, mutate: bool) -> dict[str, Any]:
    prepared = _prepare(client, movie_path, mutate=mutate)
    client.call("debugger.runUntilAddress", {
        "address": f"0x{thud.PLAYER_TRANSITION_ENTRY:08X}"})
    base._wait_for_pause(client, "Thud row-4 damage entry")
    registers = {
        str(key).lower(): value for key, value in
        client.call("debugger.getRegisters", {})["registers_hex"].items()}
    pc, ra = int(registers["pc"], 16), int(registers["ra"], 16)
    call = (ra - 8) & 0xFFFFFFFF
    word = struct.unpack(
        "<I", base._read_memory(client, call, 4))[0]
    before_call = _snapshot(client, full_identity=True)
    client.call("debugger.runUntilAddress", {"address": f"0x{ra:08X}"})
    base._wait_for_pause(client, "Thud row-4 damage return")
    after_return = _snapshot(client, full_identity=True)
    entry = {
        "pc": f"0x{pc:08x}", "ra": f"0x{ra:08x}",
        "link_call_address": f"0x{call:08x}",
        "instruction_word": f"0x{word:08x}",
        "resolved_target": f"0x{thud.PLAYER_TRANSITION_ENTRY:08x}",
        "arguments": {name: registers[name]
                      for name in ("a0", "a1", "a2", "a3")},
        "loop_terminal_register": registers["s2"],
        "inside_rows": [
            row["row"] for row in before_call["rows"] if row["inside"]],
    }
    expected = (0, -1, 2) if mutate else (3, 2, 0)
    bound = bool(
        pc == thud.PLAYER_TRANSITION_ENTRY and
        call == EXPECTED_CALL and ra == EXPECTED_RETURN and
        word == EXPECTED_CALL_WORD and int(registers["a3"], 16) == 0 and
        int(registers["s2"], 16) == thud.ARENA_TRANSFORM_ROW_COUNT and
        entry["inside_rows"] == [ROW] and
        (before_call["scene"], before_call["player_health"],
         before_call["lives"], before_call["master_state"]) ==
        (14, expected[0], 0, 0) and
        (after_return["scene"], after_return["player_health"],
         after_return["lives"], after_return["master_state"]) ==
        (14, expected[1], 0, expected[2]) and
        str(after_return["pc"]).lower() == f"0x{ra:08x}")
    result = {
        "control": "one_field_final_life" if mutate else "natural_nonfatal",
        "prepared": prepared, "entry": entry,
        "before_call": before_call, "after_return": after_return,
        "returned_to": f"0x{ra:08x}", "row_contact_causally_bound": bound,
    }
    if not bound:
        raise SystemExit(f"Thud row-4 invocation was not causal: {result}")
    return result


def _advance_current(client: Any, target: int) -> dict[str, Any]:
    advance = client.call("movie.advanceToFrame", {
        "frame": target, "max_frames": target - PREPARE_TARGET + 4})
    snapshot = _snapshot(client, full_identity=True)
    if snapshot["movie_frame"] != target or \
            snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"Thud outcome boundary {target} drifted: {snapshot}")
    return {"advance": advance, "snapshot": snapshot}


def _matched_outcomes(client: Any, movie_path: Path) -> dict[str, Any]:
    natural_origin = _prepare(client, movie_path, mutate=False)
    natural = _advance_current(client, OUTCOME_TARGET)
    fatal_origin = _prepare(client, movie_path, mutate=True)
    fatal = _advance_current(client, OUTCOME_TARGET)
    a, b = natural_origin["origin"], fatal_origin["origin"]
    stable = (
        "emulator_frame", "cycle", "movie_frame", "pc", "sp", "scene",
        "master_state", "player_health", "lives", "main_ram_sha256",
        "registers_sha256")
    n, f = natural["snapshot"], fatal["snapshot"]
    if any(a[key] != b[key] for key in stable) or \
            (n["scene"], n["player_health"], n["lives"],
             n["master_state"]) != (14, 2, 0, 0) or \
            (f["scene"], f["player_health"], f["lives"],
             f["master_state"]) != (14, -1, 0, 2) or \
            any((row.get("row"), row.get("speed"), row.get("ramp")) !=
                (ROW, 110, 0) for row in
                (n.get("selected_row") or {}, f.get("selected_row") or {})):
        raise SystemExit(f"Thud matched outcomes drifted: {natural} {fatal}")
    return {
        "shared_origin": natural_origin["origin"],
        "one_field_control": fatal_origin["mutation"],
        "natural_nonfatal": natural, "final_life_death": fatal,
    }


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    matched = document.get("matched_outcomes") or {}
    natural = ((matched.get("natural_nonfatal") or {}).get("snapshot") or {})
    fatal = ((matched.get("final_life_death") or {}).get("snapshot") or {})
    calls = document.get("exact_invocations") or {}
    return {
        "movies_replayed": 1,
        "arena_row": ROW,
        "natural_health_delta": natural.get("player_health", 0) - 3,
        "mutation_main_ram_difference_count": (
            (matched.get("one_field_control") or {}).get(
                "main_ram_difference_count")),
        "fatal_health_lives_master": [
            fatal.get("player_health"), fatal.get("lives"),
            fatal.get("master_state")],
        "natural_and_fatal_row_calls_bound": all(
            (calls.get(key) or {}).get("row_contact_causally_bound") is True
            for key in ("natural", "fatal")),
        "boss_arena_final_life_paths_bounded": 1,
        "death_class_promoted": 0,
        "c16_d18_or_f09_completed": 0,
    }


def _source_dependencies() -> dict[str, str]:
    paths = (
        "tools/phase4_c16_bonus_death.py",
        "tools/phase4_e08_operator_contacts.py",
        "tools/phase4_thud_arena.py",
        "tools/phase4_thud_defeat.py",
        "analysis/phase3_scene_asset_graph.json",
        "analysis/phase4_thud_arena.json",
    )
    return {path: _sha256(ROOT / path) for path in paths}


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for label, builder, key in (
            ("fixture", build_fixture_census, "fixture_census"),
            ("context", build_context_identity, "context_identity")):
        try:
            recomputed = builder()
        except (OSError, KeyError, ValueError, SystemExit) as error:
            recomputed = None
            gaps.append(f"Thud boulder {label} recomputation failed: {error}")
        if recomputed is not None and document.get(key) != recomputed:
            gaps.append(f"Thud boulder {label} census changed")
    if document.get("source_dependencies") != _source_dependencies():
        gaps.append("Thud boulder source dependencies changed")
    matched = document.get("matched_outcomes") or {}
    mutation = matched.get("one_field_control") or {}
    natural = ((matched.get("natural_nonfatal") or {}).get("snapshot") or {})
    fatal = ((matched.get("final_life_death") or {}).get("snapshot") or {})
    if mutation.get("main_ram_differences") != [{
            "address": "0x800a6594", "before": 3, "after": 0}]:
        gaps.append("Thud boulder one-field mutation changed")
    if (natural.get("scene"), natural.get("player_health"),
            natural.get("lives"), natural.get("master_state")) != \
            (14, 2, 0, 0) or \
            (fatal.get("scene"), fatal.get("player_health"),
             fatal.get("lives"), fatal.get("master_state")) != \
            (14, -1, 0, 2):
        gaps.append("Thud boulder matched outcome changed")
    calls = document.get("exact_invocations") or {}
    for key, health in (("natural", (3, 2, 0)), ("fatal", (0, -1, 2))):
        row = calls.get(key) or {}
        entry = row.get("entry") or {}
        if row.get("row_contact_causally_bound") is not True or \
                entry.get("link_call_address") != "0x800b4ae0" or \
                entry.get("instruction_word") != "0x0c0129c0" or \
                entry.get("loop_terminal_register") != "0x00000006" or \
                entry.get("inside_rows") != [4] or \
                (row.get("before_call") or {}).get(
                    "player_health") != health[0] or \
                (row.get("after_return") or {}).get(
                    "player_health") != health[1] or \
                (row.get("after_return") or {}).get(
                    "master_state") != health[2]:
            gaps.append(f"{key} Thud boulder invocation changed")
    summary = derive_summary(document)
    if document.get("summary") != summary or summary != {
            "movies_replayed": 1, "arena_row": 4,
            "natural_health_delta": -1,
            "mutation_main_ram_difference_count": 1,
            "fatal_health_lives_master": [-1, 0, 2],
            "natural_and_fatal_row_calls_bound": True,
            "boss_arena_final_life_paths_bounded": 1,
            "death_class_promoted": 0,
            "c16_d18_or_f09_completed": 0}:
        gaps.append("Thud boulder derived summary changed")
    gaps.extend(retained_pristine_save_gaps(document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thud boulder process cleanup changed")
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
    media = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU16", "debugger.getRegisters",
        "debugger.runUntilAddress", "debugger.clearBreakpoints",
        "emulator.getMediaInfo", "emulator.getStateInfo",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.stopPlayback", "movie.status", "movie.clear",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks Thud C16 methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / thud.SAVE_REL, media)
    movie_path = ROOT / thud.MOVIE_REL
    natural_call = _capture_invocation(client, movie_path, mutate=False)
    fatal_call = _capture_invocation(client, movie_path, mutate=True)
    outcomes = _matched_outcomes(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_c16_thud_boulder_death.py",
        anchor={
            "type": "existing state-anchored Thud row-4 contact recording",
            "save": thud.SAVE_REL, "movie": thud.MOVIE_REL,
            "fixture_sha256": {
                thud.SAVE_REL: thud.SAVE_SHA256,
                thud.MOVIE_REL: thud.MOVIE_SHA256},
            "state_inspections": [inspection], "media_identity": media,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "shared_origin_target": PREPARE_TARGET,
            "outcome_target": OUTCOME_TARGET,
            "trace_mode": (
                "fresh exact entry-to-architectural-return captures plus "
                "fresh matched uninstrumented movie advances"),
            "causal_capture": (
                "change only true health 3->0 before the retained row-4 "
                "contact; require the next 0x8004A700 entry to return to "
                "overlay call 0x800B4AE0+8 with row 4 as the sole live "
                "in-threshold row"),
        })
    document = {
        "_comment": (
            "Active C16 breadth: one natural Thud row-4 contact made fatal "
            "on the final playable life by a one-field health control. This "
            "does not promote a death class or complete C16/D18/F09."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-c16-thud-boulder-death/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "context_identity": context,
        "exact_invocations": {"natural": natural_call, "fatal": fatal_call},
        "matched_outcomes": outcomes,
        "bounded_interpretation": {
            "observation": (
                "The pristine replay naturally invokes resident damage from "
                "overlay call 0x800B4AE0 with row 4 as the sole live "
                "in-threshold row and changes health 3->2."),
            "inference": (
                "Scene routing and the independently retained arena census "
                "establish Stage-09 boss-arena row-4 context."),
            "causal_confirmation": (
                "Changing only true health 3->0 at the shared movie origin "
                "makes the same row-4 call return with health -1/master 2 "
                "while final-life lives remains 0."),
            "forbidden_claim": (
                "Do not call this a scripted, special, or exceptional death; "
                "do not infer every arena row, retry, Thud phase, or C16 path."),
        },
        "bounded_open_frontier": {
            "death_classes": (
                "Scripted, special, and exceptional deaths remain open."),
            "boss_scope": (
                "This extends C16 into one Thud arena contact only; boss and "
                "arena policy remain owned by active D18/F09 work."),
            "frontend_card": (
                "Explicit native Save/Load, alternate title/menu choices, "
                "no-card, and corrupt-card behavior remain open."),
            "next_experiment": (
                "Inventory an existing scripted/setpiece or exceptional "
                "death lead and bind its exact producer before requesting a "
                "new fixture."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained C16 Thud boulder evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[c16-thud-boulder] row-4 contact bound to final-life selection")
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
                args, generator="tools/phase4_c16_thud_boulder_death.py",
                anchor={"type": "aborted before retained Thud C16 evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(f"owned Thud C16 cleanup also failed: {cleanup_error}",
                  file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
