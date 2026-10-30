#!/usr/bin/env python3
"""Replay existing E10 hazard leads and route only measured E08 outcomes.

The filenames are discovery metadata, never semantic ownership.  Each retained
result comes from a complete v3 movie replay whose paired state was inspected
against the mounted hash-pinned pristine disc before load.  Passive cached-block
coverage is compared with an uninstrumented replay at the same cycle, frame,
register and RAM boundary.
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
    import phase4_e08_operator_contacts as contacts
    from live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )
except ModuleNotFoundError:  # imported as tools.phase4_e08_hazard_outcomes
    from tools.build_identity import verify_staged_input
    from tools import phase4_e08_operator_contacts as contacts
    from tools.live_session_provenance import (
        FIXTURE_SET, add_required_live_args, finish_run,
        inspect_state_before_load, verified_media_identity,
        verify_declared_save_fixture, write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_e08_hazard_outcomes.json"
PROPS = ROOT / "analysis/phase4_props_movers.json"
OUTCOME_JOIN = ROOT / "analysis/phase4_e08_outcome_join.json"
OPERATOR_CONTACTS = ROOT / "analysis/phase4_e08_operator_contacts.json"
RESPAWN_WRITERS = ROOT / "analysis/phase4_respawn_writer_catalog.json"
EXE_REL = "SCUS_942.88"
EXE = ROOT / "REBUILD/files" / EXE_REL
EXE_LOAD = 0x80010000
EXE_HEADER = 0x800

SCENE = 0x80082504
SAFE_FIELDS = {
    "x": (0x800A6550, 4),
    "y": (0x800A6554, 4),
    "z": (0x800A6558, 4),
    "heading": (0x800A6578, 2),
}
LEVEL06_INITIALIZER = 0x800B3AEC
LEVEL06_INITIALIZER_END = 0x800B3B94
LEVEL06_RETURN = 0x8005B19C
LEVEL06_CALL = 0x8005B194
LEVEL06_CALL_WORD = 0x0C02CEBB
LEVEL06_PRE_FRAME = 487
LEVEL06_TRIGGER_FRAME = 488
LEVEL06_EXPECTED_SAFE = {
    "x": 35329, "y": -85228, "z": -154696, "heading": 3063,
}
RESPAWN_HANDLER = {"start": "0x8005B12C", "end": "0x8005B440",
                   "label": "respawn_transition_state_handler",
                   "max_pcs": 200000}
LEVEL06_INITIALIZER_RANGE = {
    "start": f"0x{LEVEL06_INITIALIZER:08X}",
    "end": f"0x{LEVEL06_INITIALIZER_END:08X}",
    "label": "level06_fixed_safe_tuple_initializer", "max_pcs": 200000,
}
LEVEL06_CAUSAL_BRANCHES = (
    ("control", None, None),
    ("suppress_x_store", 0x800B3B00, 0x00000000),
    ("suppress_y_store", 0x800B3B24, 0x00000000),
    ("suppress_z_store", 0x800B3B3C, 0x00000000),
    ("heading_constant_plus_one", 0x800B3B28, 0x24020BF8),
)

FIXTURES = (
    ("E10_acorn_lead", "hazard_acorn_LEVEL11"),
    ("E10_falling_rocks_lead", "hazard_falling_rocks_LEVEL02"),
    ("E10_falling_spikes_lead", "hazard_fallingspikes_LEVEL05"),
    ("E10_goo_lead", "hazard_goo_LEVEL07"),
    ("E10_ground_bird_lead", "hazard_ground_bird_LEVEL04"),
    ("E10_pit_LEVEL02_lead", "hazard_pit_LEVEL02"),
    ("E10_pit_LEVEL05_lead", "hazard_pit_LEVEL05"),
    ("E10_pit_LEVEL07_lead", "hazard_pit_LEVEL07"),
)

MOVIE_DIR = "movies/Phase4/E10"
TRACE_RANGES = (
    *contacts.TRACE_RANGES,
    {"start": "0x800A0000", "end": "0x80100000",
     "label": "region_a_hazard_and_event_overlay", "max_pcs": 200000},
)


def _fixture_paths(stem: str) -> tuple[str, str]:
    return (f"{MOVIE_DIR}/{stem}.movie.json",
            f"{MOVIE_DIR}/{stem}.movie.sav")


def build_fixture_census() -> dict[str, Any]:
    entries = json.loads(FIXTURE_SET.read_text()).get("entries") or {}
    rows = []
    for lead, stem in FIXTURES:
        movie_rel, save_rel = _fixture_paths(stem)
        movie_path, save_path = ROOT / movie_rel, ROOT / save_rel
        movie_pin = entries.get(movie_rel)
        save = verify_declared_save_fixture(
            save_path, allowed_media_classes={"pristine"})
        if not isinstance(movie_pin, dict) or \
                movie_pin.get("media_class") != "pristine_serial" or \
                movie_pin.get("size") != movie_path.stat().st_size or \
                movie_pin.get("sha256") != contacts._sha256(movie_path):
            raise SystemExit(f"E10 hazard movie pin drifted: {movie_rel}")
        movie = json.loads(movie_path.read_text())
        start = movie.get("start_state") or {}
        if movie.get("version") != 3 or \
                movie.get("game_serial") != "SCUS-94288" or \
                start.get("game_serial") != "SCUS-94288" or \
                start.get("from_boot") is not False or \
                start.get("reproducible_only_from_state") is not True or \
                start.get("file_size") != save["size"] or \
                not movie.get("frames"):
            raise SystemExit(f"E10 hazard movie metadata drifted: {movie_rel}")
        rows.append({
            "lead": lead,
            "row_lead": "E10_hazards",
            "fixture_role": "hazard discovery lead only",
            "movie": {
                "path": movie_rel, "sha256": movie_pin["sha256"],
                "size": movie_pin["size"],
                "media_class": movie_pin["media_class"],
                "version": movie["version"], "frames": len(movie["frames"]),
                "initial_frame": movie["initial_frame"],
            },
            "save": save,
            "classification_boundary": (
                "the operator filename names a trigger lead only; typed state, "
                "outcome and code coverage determine every retained claim"),
        })
    return {
        "manifest": FIXTURE_SET.relative_to(ROOT).as_posix(),
        "count": len(rows), "pairs": rows,
    }


def _exe_slice(executable: bytes, address: int, length: int) -> bytes:
    offset = EXE_HEADER + address - EXE_LOAD
    result = executable[offset:offset + length]
    if len(result) != length:
        raise SystemExit(f"short executable slice at 0x{address:08X}")
    return result


def build_level06_respawn_static_policy() -> dict[str, Any]:
    """Bind the scene selector and LEVEL06 body to pristine staged bytes."""
    executable = EXE.read_bytes()
    verify_staged_input(EXE_REL, executable)
    catalog = json.loads(RESPAWN_WRITERS.read_text())
    writer = catalog["writer_functions"]["LEVEL06/LEVEL.BIN"]
    level = (ROOT / writer["path"]).read_bytes()
    verify_staged_input("LEVEL06/LEVEL.BIN", level)
    offset = int(writer["file_offset"], 16)
    body = level[offset:offset + writer["size"]]
    if hashlib.sha256(body).hexdigest() != writer["sha256"] or \
            int(writer["runtime_start"], 16) != LEVEL06_INITIALIZER or \
            int(writer["runtime_end"], 16) != LEVEL06_INITIALIZER_END:
        raise SystemExit("LEVEL06 fixed-initializer catalog identity drifted")

    jump_table = struct.unpack(
        "<8I", _exe_slice(executable, 0x8001B828, 32))
    expected_table = (
        0x8005B174, 0x8005B184, 0x8005B1BC, 0x8005B194,
        0x8005B1BC, 0x8005B1A4, 0x8005B1BC, 0x8005B1B4,
    )
    call_word = struct.unpack(
        "<I", _exe_slice(executable, LEVEL06_CALL, 4))[0]
    if jump_table != expected_table or call_word != LEVEL06_CALL_WORD:
        raise SystemExit("resident respawn scene selector drifted")
    scene_policy = []
    targets = {
        3: (0x8005B174, 0x800B3C54),
        4: (0x8005B184, 0x800B3C5C),
        5: (0x8005B1BC, None),
        6: (0x8005B194, 0x800B3AEC),
        7: (0x8005B1BC, None),
        8: (0x8005B1A4, 0x800B3AE8),
        9: (0x8005B1BC, None),
        10: (0x8005B1B4, 0x800B3ADC),
    }
    for scene, (dispatch_target, initializer) in targets.items():
        scene_policy.append({
            "scene": scene,
            "jump_table_target": f"0x{dispatch_target:08x}",
            "initializer": (
                f"0x{initializer:08x}" if initializer is not None else None),
            "fixed_initializer_selected": initializer in {
                LEVEL06_INITIALIZER, 0x800B3AE8},
            "denial_or_common_tail": initializer is None,
        })
    return {
        "executable": {
            "path": f"REBUILD/files/{EXE_REL}",
            "sha256": hashlib.sha256(executable).hexdigest(),
        },
        "catalog": {
            "path": RESPAWN_WRITERS.relative_to(ROOT).as_posix(),
            "sha256": contacts._sha256(RESPAWN_WRITERS),
            "level06_writer": writer,
        },
        "resident_selector": {
            "handler_entry": "0x8005b134",
            "scene_domain": {"inclusive_min": 3, "inclusive_max": 10},
            "outside_domain_target": "0x8005b1bc",
            "jump_table": {
                "address": "0x8001b828", "entries": [
                    f"0x{value:08x}" for value in jump_table],
                "sha256": hashlib.sha256(
                    _exe_slice(executable, 0x8001B828, 32)).hexdigest(),
            },
            "scene_policy": scene_policy,
            "level06_call": {
                "scene": 6, "address": f"0x{LEVEL06_CALL:08x}",
                "instruction_word": f"0x{call_word:08x}",
                "target": f"0x{LEVEL06_INITIALIZER:08x}",
            },
            "handler_prefix": {
                "address": "0x8005b134", "length": 144,
                "sha256": hashlib.sha256(
                    _exe_slice(executable, 0x8005B134, 144)).hexdigest(),
            },
        },
        "interpretation": (
            "The resident handler subtracts 3 from scene, bounds the result "
            "to eight jump-table entries, selects LEVEL06 only for scene 6, "
            "and routes scenes 5/7/9 plus all out-of-domain values directly "
            "to the common tail. Loaded-overlay identity remains a separate "
            "runtime predicate."),
    }


def _read_int(client: Any, address: int, width: int, *, signed: bool) -> int:
    return int.from_bytes(
        contacts.read_memory(client, address, width), "little", signed=signed)


def _main_ram(client: Any) -> bytes:
    return b"".join(
        contacts.read_memory(client, 0x80000000 + offset, 0x10000)
        for offset in range(0, 0x200000, 0x10000))


def _checkpoint_snapshot(client: Any, *, full_ram: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    registers = client.call("debugger.getRegisters", {})["registers_hex"]
    registers = {str(key).lower(): value for key, value in registers.items()}
    player = contacts.read_memory(client, contacts.PLAYER_BASE, contacts.PLAYER_SIZE)
    result = {
        "frame": status["frame"], "cycle": status["cycle"],
        "pc": registers["pc"].lower(), "sp": registers["sp"].lower(),
        "ra": registers["ra"].lower(),
        "scene": _read_int(client, SCENE, 4, signed=False),
        "health": struct.unpack_from("<h", player, 0x94)[0],
        "lives": player[0xA0],
        "live_xyz": list(struct.unpack_from("<iii", player, 0)),
        "safe": {
            name: _read_int(client, address, width, signed=name != "heading")
            for name, (address, width) in SAFE_FIELDS.items()
        },
    }
    if full_ram:
        result["main_ram_sha256"] = hashlib.sha256(_main_ram(client)).hexdigest()
    return result


def _wait_for_pause(client: Any, label: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while True:
        status = client.call("debugger.status", {})
        if status.get("paused") is True:
            return status
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for {label}")
        time.sleep(0.01)


def _inspect_transient_state(client: Any, state_path: Path) -> dict[str, Any]:
    row = client.call("emulator.getStateInfo", {"path": str(state_path.resolve())})
    if row.get("valid") is not True or row.get("version") != 84 or \
            row.get("serial") != "SCUS-94288" or \
            Path(row.get("media_path") or "").name != \
            "Disney-Pixar A Bug's Life (v1.0).cue":
        raise SystemExit(f"transient LEVEL06 entry state failed inspection: {row}")
    return {
        "valid": row["valid"], "version": row["version"],
        "serial": row["serial"], "media_path": row["media_path"],
        "size": state_path.stat().st_size,
        "sha256": contacts._sha256(state_path),
    }


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


def _locate_first_outcome(
        client: Any, movie_path: Path, frame_count: int, slot: int,
        initial_actor: dict[str, Any]) -> dict[str, Any]:
    """Locate a stable final actor outcome from fresh cycle-neutral replays."""
    lo, hi = 1, frame_count
    probes = []
    while lo < hi:
        mid = (lo + hi) // 2
        replay = contacts._trace_state_at_frame(
            client, movie_path, mid, ranges=(contacts.TRACE_RANGES[0],))
        actor = replay["snapshot"]["actors"][slot]
        matched = contacts._decisive_outcome(initial_actor, actor)
        probes.append({
            "movie_frame": mid, "matched": matched,
            "emulator_frame": replay["snapshot"]["frame"],
            "cycle": replay["snapshot"]["cycle"],
        })
        if matched:
            hi = mid
        else:
            lo = mid + 1
    before = contacts._trace_state_at_frame(
        client, movie_path, lo - 1, ranges=(contacts.TRACE_RANGES[0],))
    after = contacts._trace_state_at_frame(
        client, movie_path, lo, ranges=(contacts.TRACE_RANGES[0],))
    before_actor = before["snapshot"]["actors"][slot]
    after_actor = after["snapshot"]["actors"][slot]
    if contacts._decisive_outcome(initial_actor, before_actor) or \
            not contacts._decisive_outcome(initial_actor, after_actor):
        raise SystemExit(
            f"E10 actor outcome was not a stable first boundary: "
            f"slot={slot} frame={lo}")
    return {
        "movie_frame": lo, "probes": probes,
        "before": {
            "emulator_frame": before["snapshot"]["frame"],
            "cycle": before["snapshot"]["cycle"],
            "actor": before_actor, "player": before["snapshot"]["player"],
        },
        "after": {
            "emulator_frame": after["snapshot"]["frame"],
            "cycle": after["snapshot"]["cycle"],
            "actor": after_actor, "player": after["snapshot"]["player"],
        },
        "search_rule": (
            "fresh recorded-anchor replay for every probe; no per-frame "
            "instrumentation or state mutation"),
    }


def _run_movie(client: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    movie = fixture["movie"]
    movie_path = ROOT / movie["path"]
    start = contacts._trace_state_at_frame(
        client, movie_path, 0, ranges=(contacts.TRACE_RANGES[0],))
    initial = start["snapshot"]
    sources = contacts._source_identity(client, initial)
    full = contacts._trace_state_at_frame(
        client, movie_path, movie["frames"], ranges=TRACE_RANGES)
    final = full["snapshot"]
    outcome_slots = {
        slot for slot in range(contacts.ACTOR_CAPACITY)
        if contacts._decisive_outcome(
            initial["actors"][slot], final["actors"][slot])
    }
    controlled = sorted({
        sources[slot]["type_word"] for slot in outcome_slots if slot in sources
    })
    boundaries = []
    for slot in sorted(outcome_slots):
        if slot not in sources:
            raise SystemExit(
                f"E10 outcome actor slot {slot} lacked start-state source identity")
        boundaries.append({
            "slot": slot, "source_identity": sources[slot],
            **_locate_first_outcome(
                client, movie_path, movie["frames"], slot,
                initial["actors"][slot]),
        })
    contacts._cleanup_movie(client)
    print(
        f"[e08-hazard-outcomes] {fixture['lead']} 0->{movie['frames']} "
        f"outcome_slots={sorted(outcome_slots)}")
    return {
        "lead": fixture["lead"], "row_lead": fixture["row_lead"],
        "fixture": fixture,
        "initial": {
            "frame": initial["frame"], "cycle": initial["cycle"],
            "player": initial["player"], "actor_sources": sources,
            "cycle_neutral_trace": start["trace"],
        },
        "final": {
            "frame": final["frame"], "cycle": final["cycle"],
            "player": final["player"],
            "ram_sha256": full["trace"]["control"]["ram_sha256"],
            "movie_status": full["movie_status"],
        },
        "player_delta": _player_delta(initial["player"], final["player"]),
        "native_outcome_boundaries": boundaries,
        "controlled_type_words": controlled,
        "typed_outcome_observed": bool(controlled),
        "cycle_neutral_trace": full["trace"],
        "classification_boundary": (
            "this is a measured natural replay outcome only; it does not assign "
            "E08/E10 ownership, a hazard kind, species or persistence law"),
    }


def _capture_level06_respawn_activation(
        client: Any, fixture: dict[str, Any],
        static_policy: dict[str, Any]) -> dict[str, Any]:
    """Turn the existing scene-6 death lead into bounded C15 activation proof."""
    movie_path = ROOT / fixture["movie"]["path"]
    ranges = (LEVEL06_INITIALIZER_RANGE, RESPAWN_HANDLER)
    before_trace = contacts._trace_state_at_frame(
        client, movie_path, LEVEL06_PRE_FRAME, ranges=ranges)
    before = _checkpoint_snapshot(client, full_ram=True)
    after_trace = contacts._trace_state_at_frame(
        client, movie_path, LEVEL06_TRIGGER_FRAME, ranges=ranges)
    after = _checkpoint_snapshot(client, full_ram=True)
    contacts._cleanup_movie(client)

    # Reproduce the exact pre-trigger endpoint, then stop at the native call.
    contacts._trace_state_at_frame(
        client, movie_path, LEVEL06_PRE_FRAME, ranges=ranges)
    client.call("debugger.runUntilAddress", {
        "address": f"0x{LEVEL06_INITIALIZER:08X}"})
    _wait_for_pause(client, "LEVEL06 fixed initializer entry")
    entry = _checkpoint_snapshot(client, full_ram=True)
    registers = client.call("debugger.getRegisters", {})["registers_hex"]
    registers = {str(key).lower(): value.lower()
                 for key, value in registers.items()}
    call_word = _read_int(client, LEVEL06_CALL, 4, signed=False)
    writer = static_policy["catalog"]["level06_writer"]
    runtime = contacts.read_memory(client, LEVEL06_INITIALIZER, writer["size"])
    runtime_identity = {
        "address": f"0x{LEVEL06_INITIALIZER:08x}",
        "length": len(runtime),
        "sha256": hashlib.sha256(runtime).hexdigest(),
        "pinned_sha256": writer["sha256"],
        "exact_pristine_match": hashlib.sha256(runtime).hexdigest() == writer["sha256"],
    }

    with tempfile.TemporaryDirectory(
            prefix="abl-phase4-level06-initializer-") as temp_dir_text:
        state_path = Path(temp_dir_text) / "initializer-entry.sav"
        saved = client.call("emulator.saveState", {
            "path": str(state_path.resolve())})
        transient = _inspect_transient_state(client, state_path)
        if saved.get("saved") is not True:
            raise SystemExit(f"failed to save transient initializer entry: {saved}")

        # accessLog changes execution mode and supplies attribution only.
        client.call("accessLog.clear", {})
        watches = {}
        for name, (address, width) in SAFE_FIELDS.items():
            watches[name] = client.call("accessLog.addWatch", {
                "address": f"0x{address:08X}", "length": width,
                "type": "write", "label": f"safe_{name}",
                "max_events": 32})
        client.call("debugger.runUntilAddress", {
            "address": f"0x{LEVEL06_RETURN:08X}"})
        _wait_for_pause(client, "LEVEL06 fixed initializer return")
        page = client.call("accessLog.get", {"offset": 0, "limit": 128})
        client.call("accessLog.clear", {})
        labels = {row["watch_id"]: name for name, row in watches.items()}
        events = [{**row, "field": labels.get(row.get("watch_id"))}
                  for row in page.get("events") or []]
        attribution = {
            "execution_mode_boundary": (
                "accessLog forces interpreter execution and attributes direct "
                "stores only; the passive trace pair supplies timing authority."),
            "events": events,
            "total": page.get("total"),
            "returned": len(events),
            "truncated": page.get("truncated", False),
            "after_return": _checkpoint_snapshot(client, full_ram=True),
        }

        branches = []
        expected_words = {
            0x800B3B00: 0xAC236550,
            0x800B3B24: 0xAC226554,
            0x800B3B3C: 0xAC246558,
            0x800B3B28: 0x24020BF7,
        }
        for label, patch_address, patch_value in LEVEL06_CAUSAL_BRANCHES:
            inspection = _inspect_transient_state(client, state_path)
            loaded = client.call("emulator.loadState", {
                "path": str(state_path.resolve()), "pause_after_load": True,
                "validate_disc": True, "auto_select_disc": False,
            })
            if loaded.get("loaded") is not True:
                raise SystemExit(
                    f"failed to reload transient initializer entry: {loaded}")
            media = verified_media_identity(
                client, client.call("debugger.status", {}))
            origin = _checkpoint_snapshot(client, full_ram=True)
            mutation = None
            if patch_address is not None and patch_value is not None:
                old_word = _read_int(client, patch_address, 4, signed=False)
                if old_word != expected_words[patch_address]:
                    raise SystemExit(
                        f"LEVEL06 branch source drifted at 0x{patch_address:08X}")
                write = client.call("debugger.writeU32", {
                    "address": f"0x{patch_address:08X}", "value": patch_value})
                new_word = _read_int(client, patch_address, 4, signed=False)
                if write.get("written") != 4 or \
                        write.get("code_invalidated") is not True or \
                        new_word != patch_value:
                    raise SystemExit(f"LEVEL06 branch patch failed: {write}")
                mutation = {
                    "address": f"0x{patch_address:08x}",
                    "before_word": f"0x{old_word:08x}",
                    "after_word": f"0x{new_word:08x}",
                    "written": write["written"],
                    "code_invalidated": write["code_invalidated"],
                    "scope": (
                        "one runtime instruction in a transient same-origin "
                        "branch; no disc or retained fixture was modified"),
                }
            client.call("debugger.runUntilAddress", {
                "address": f"0x{LEVEL06_RETURN:08X}"})
            _wait_for_pause(client, f"LEVEL06 {label} return")
            branches.append({
                "label": label, "state_inspection": inspection,
                "mounted_media_pristine_verified":
                    (media.get("hash_verification") or {}).get(
                        "pristine_verified") is True,
                "origin": origin, "mutation": mutation,
                "after_return": _checkpoint_snapshot(client, full_ram=True),
            })
        transient_recipe = {
            **transient,
            "origin": "saved at the natural LEVEL06 initializer entry",
            "storage": "temporary directory deleted before artifact retention",
            "deleted_before_retention": True,
            "loads": len(branches),
        }

    entry_call = {
        "pc": entry["pc"], "ra": entry["ra"],
        "link_call_address": f"0x{LEVEL06_CALL:08x}",
        "instruction_word": f"0x{call_word:08x}",
        "resolved_target": f"0x{LEVEL06_INITIALIZER:08x}",
        "selector_registers": {
            name: registers[name] for name in ("v0", "v1", "a0", "a1")},
        "snapshot": entry,
    }
    result = {
        "fixture": fixture,
        "static_policy": static_policy,
        "passive_boundary": {
            "before_movie_frame": LEVEL06_PRE_FRAME,
            "after_movie_frame": LEVEL06_TRIGGER_FRAME,
            "before": {"snapshot": before,
                       "cycle_neutral_trace": before_trace["trace"]},
            "after": {"snapshot": after,
                      "cycle_neutral_trace": after_trace["trace"]},
        },
        "exact_entry": entry_call,
        "runtime_identity": runtime_identity,
        "writer_attribution": attribution,
        "causal_branches": branches,
        "transient_state_recipe": transient_recipe,
        "bounded_interpretation": {
            "observation": (
                "The pristine scene-6 replay first executes all 42 LEVEL06 "
                "initializer instructions between movie frames 487 and 488; "
                "the exact native call and four safe-field stores are retained."),
            "inference": (
                "The resident scene selector activates the residency-matched "
                "LEVEL06 fixed initializer for this ordinary respawn."),
            "causal_confirmation": (
                "Three same-entry single-store suppressions retain the prior "
                "X/Y/Z independently, while a one-unit heading-constant change "
                "changes heading by one; all branches return at the same "
                "cycle/frame/PC/SP boundary as control."),
            "forbidden_claim": (
                "Do not infer a hazard species, a player-visible checkpoint, "
                "LEVEL08 activation, all-scene coverage, persistence, or "
                "indirect-writer completeness from this scene-6 path."),
        },
    }
    gaps = _level06_activation_gaps(result)
    if gaps:
        raise SystemExit(f"LEVEL06 respawn activation failed: {gaps}")
    return result


def _level06_activation_gaps(result: dict[str, Any]) -> list[str]:
    gaps = []
    policy = result.get("static_policy") or {}
    resident = policy.get("resident_selector") or {}
    scene_rows = {row.get("scene"): row
                  for row in resident.get("scene_policy") or []}
    if (resident.get("level06_call") or {}).get("instruction_word") != \
            f"0x{LEVEL06_CALL_WORD:08x}" or \
            (scene_rows.get(6) or {}).get("initializer") != \
            f"0x{LEVEL06_INITIALIZER:08x}" or any(
                (scene_rows.get(scene) or {}).get("denial_or_common_tail") is not True
                for scene in (5, 7, 9)):
        gaps.append("LEVEL06 resident scene trigger/denial policy changed")
    passive = result.get("passive_boundary") or {}
    before = (passive.get("before") or {}).get("snapshot") or {}
    after = (passive.get("after") or {}).get("snapshot") or {}

    def coverage(side: str, label: str) -> dict[str, Any]:
        trace = (passive.get(side) or {}).get("cycle_neutral_trace") or {}
        return next((row for row in trace.get("coverage") or []
                     if row.get("label") == label), {})

    for side in ("before", "after"):
        trace = (passive.get(side) or {}).get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"LEVEL06 {side} passive trace changed")
    pre_init = coverage("before", "level06_fixed_safe_tuple_initializer")
    post_init = coverage("after", "level06_fixed_safe_tuple_initializer")
    if pre_init.get("total_hits") != 0 or \
            pre_init.get("distinct_pc_count") != 0:
        gaps.append("LEVEL06 pre-trigger denial boundary changed")
    if post_init.get("total_hits") != 42 or \
            post_init.get("distinct_pc_count") != 42:
        gaps.append("LEVEL06 first activation coverage changed")
    if before.get("scene") != 6 or after.get("scene") != 6 or \
            (before.get("health"), before.get("lives")) != (4, 4) or \
            (after.get("health"), after.get("lives")) != (4, 3) or \
            after.get("safe") != LEVEL06_EXPECTED_SAFE:
        gaps.append("LEVEL06 natural respawn boundary state changed")

    exact = result.get("exact_entry") or {}
    entry = exact.get("snapshot") or {}
    if exact.get("pc") != f"0x{LEVEL06_INITIALIZER:08x}" or \
            exact.get("ra") != f"0x{LEVEL06_RETURN:08x}" or \
            exact.get("link_call_address") != f"0x{LEVEL06_CALL:08x}" or \
            exact.get("instruction_word") != f"0x{LEVEL06_CALL_WORD:08x}" or \
            entry.get("safe") != before.get("safe") or \
            (exact.get("selector_registers") or {}).get("v1") != "0x00000003":
        gaps.append("LEVEL06 exact native entry/caller changed")
    runtime = result.get("runtime_identity") or {}
    if runtime.get("exact_pristine_match") is not True or \
            runtime.get("sha256") != runtime.get("pinned_sha256"):
        gaps.append("LEVEL06 runtime overlay identity changed")

    attribution = result.get("writer_attribution") or {}
    events = attribution.get("events") or []
    expected_events = {
        "x": (0x800B3B00, 0xAC236550, 35329, 4),
        "y": (0x800B3B24, 0xAC226554, -85228, 4),
        "heading": (0x800B3B30, 0xA4226578, 3063, 2),
        "z": (0x800B3B3C, 0xAC246558, -154696, 4),
    }
    if attribution.get("total") != 4 or len(events) != 4 or \
            attribution.get("truncated") is not False:
        gaps.append("LEVEL06 complete writer log changed")
    for field, (pc, word, value, width) in expected_events.items():
        row = next((item for item in events if item.get("field") == field), None)
        mask = (1 << (width * 8)) - 1
        if not row or str(row.get("instruction_pc", "")).lower() != \
                f"0x{pc:08x}" or row.get("instruction_word") != \
                f"0x{word:08x}" or row.get("new_value") != (value & mask):
            gaps.append(f"LEVEL06 {field} writer attribution changed")
    if (attribution.get("after_return") or {}).get("safe") != \
            LEVEL06_EXPECTED_SAFE:
        gaps.append("LEVEL06 attributed return tuple changed")

    branches = result.get("causal_branches") or []
    if [row.get("label") for row in branches] != [
            row[0] for row in LEVEL06_CAUSAL_BRANCHES]:
        gaps.append("LEVEL06 causal branch set changed")
        return gaps
    origins = [row.get("origin") or {} for row in branches]
    origin_fingerprints = [
        (row.get("main_ram_sha256"), row.get("cycle"), row.get("frame"),
         row.get("pc"), row.get("sp"), row.get("ra")) for row in origins]
    if len(set(origin_fingerprints)) != 1 or \
            any(row.get("safe") != before.get("safe") for row in origins):
        gaps.append("LEVEL06 causal branches lost their same-entry origin")
    endpoints = [row.get("after_return") or {} for row in branches]
    endpoint_timing = [
        (row.get("cycle"), row.get("frame"), row.get("pc"), row.get("sp"))
        for row in endpoints]
    if len(set(endpoint_timing)) != 1 or \
            any(row.get("mounted_media_pristine_verified") is not True
                for row in branches):
        gaps.append("LEVEL06 causal endpoint/media identity changed")
    control_safe = endpoints[0].get("safe") or {}
    expected_safe = [
        LEVEL06_EXPECTED_SAFE,
        {**LEVEL06_EXPECTED_SAFE, "x": before.get("safe", {}).get("x")},
        {**LEVEL06_EXPECTED_SAFE, "y": before.get("safe", {}).get("y")},
        {**LEVEL06_EXPECTED_SAFE, "z": before.get("safe", {}).get("z")},
        {**LEVEL06_EXPECTED_SAFE, "heading": 3064},
    ]
    if control_safe != LEVEL06_EXPECTED_SAFE or \
            any(row.get("safe") != expected
                for row, expected in zip(endpoints, expected_safe)):
        gaps.append("LEVEL06 single-instruction causal field effects changed")
    for index, branch in enumerate(branches):
        mutation = branch.get("mutation")
        if index == 0 and mutation is not None:
            gaps.append("LEVEL06 control unexpectedly mutated code")
        if index > 0 and (not mutation or mutation.get("written") != 4 or
                          mutation.get("code_invalidated") is not True):
            gaps.append(f"LEVEL06 {branch.get('label')} mutation guard changed")
    transient = result.get("transient_state_recipe") or {}
    if transient.get("deleted_before_retention") is not True or \
            transient.get("loads") != len(branches) or \
            any((row.get("state_inspection") or {}).get("sha256") !=
                transient.get("sha256") for row in branches):
        gaps.append("LEVEL06 transient state lifecycle changed")
    return gaps


def _prior_frontier() -> tuple[set[str], set[str]]:
    join = json.loads(OUTCOME_JOIN.read_text())
    operator = json.loads(OPERATOR_CONTACTS.read_text())
    controlled = {
        value.lower() for value in
        join["unclassified_type_words_with_native_contact_controls"]
    } | {
        value.lower() for value in
        operator["summary"]["newly_controlled_unclassified_type_words"]
    }
    remaining = {
        value.lower() for value in
        operator["summary"]["remaining_uncontrolled_type_words"]
    }
    if len(controlled) != 19 or len(remaining) != 28 or controlled & remaining:
        raise SystemExit("retained 19/28 E08 frontier drifted")
    return controlled, remaining


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps = []
    activation = document.get("shared_c15_level06_respawn_activation")
    if not isinstance(activation, dict):
        gaps.append("shared C15 LEVEL06 activation evidence missing")
    else:
        gaps.extend(_level06_activation_gaps(activation))
    replays = document.get("replays") or []
    if len(replays) != len(FIXTURES):
        gaps.append("E10 hazard replay count changed")
    controlled = set()
    health_or_lives = 0
    for replay in replays:
        initial = (replay.get("initial") or {}).get("player") or {}
        final = (replay.get("final") or {}).get("player") or {}
        if initial and final and replay.get("player_delta") != _player_delta(initial, final):
            gaps.append(f"{replay.get('lead')}: player delta changed")
        health_or_lives += int(
            (replay.get("player_delta") or {}).get("health_or_lives_changed") is True)
        derived = set()
        for boundary in replay.get("native_outcome_boundaries") or []:
            before = (boundary.get("before") or {}).get("actor") or {}
            after = (boundary.get("after") or {}).get("actor") or {}
            identity = boundary.get("source_identity") or {}
            if not before or not after or \
                    contacts._decisive_outcome(before, before) or \
                    not contacts._decisive_outcome(before, after):
                gaps.append(f"{replay.get('lead')}: actor outcome boundary changed")
            if boundary.get("movie_frame", 0) <= 0 or \
                    (boundary.get("after") or {}).get("cycle", 0) <= \
                    (boundary.get("before") or {}).get("cycle", 0):
                gaps.append(f"{replay.get('lead')}: actor trigger timing changed")
            if identity.get("type_word"):
                derived.add(identity["type_word"])
        retained = set(replay.get("controlled_type_words") or [])
        if derived != retained or replay.get("typed_outcome_observed") is not bool(retained):
            gaps.append(f"{replay.get('lead')}: typed outcome derivation changed")
        controlled.update(value.lower() for value in retained)
        trace = replay.get("cycle_neutral_trace") or {}
        if (trace.get("comparison") or {}).get("cycle_neutral") is not True or \
                any(row.get("truncated") for row in trace.get("coverage") or []):
            gaps.append(f"{replay.get('lead')}: cycle-neutral trace changed")
        if (replay.get("final") or {}).get("ram_sha256") != \
                (trace.get("control") or {}).get("ram_sha256"):
            gaps.append(f"{replay.get('lead')}: final RAM/control identity changed")

    previous, remaining = _prior_frontier()
    props = json.loads(PROPS.read_text())
    unclassified = {
        row["type_word"].lower()
        for row in props["live"]["source_actor_clusters"]["behavior_classes"]
        if row["owner_classification"].startswith("unclassified")
    }
    new = controlled & remaining
    aggregate = previous | new
    still_remaining = remaining - new
    outside = controlled - unclassified
    summary = document.get("summary") or {}
    if sorted(controlled) != summary.get("controlled_type_words") or \
            sorted(new) != summary.get("newly_controlled_unclassified_type_words") or \
            sorted(outside) != summary.get("controlled_type_words_outside_unclassified_frontier") or \
            len(aggregate) != summary.get("unclassified_with_native_outcome_controls") or \
            len(still_remaining) != summary.get("unclassified_without_native_outcome_control") or \
            sorted(still_remaining) != summary.get("remaining_uncontrolled_type_words") or \
            health_or_lives != summary.get("replays_with_health_or_lives_change") or \
            summary.get("row_or_class_owners_promoted") != 0:
        gaps.append("aggregate E08 hazard-outcome partition changed")
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned live process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixtures = build_fixture_census()
    level06_static_policy = build_level06_respawn_static_policy()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media_identity = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "debugger.status", "debugger.capabilities", "debugger.pause",
        "debugger.readMemory", "debugger.writeU32", "debugger.getRegisters",
        "debugger.runUntilAddress", "emulator.getMediaInfo",
        "emulator.getStateInfo", "emulator.saveState", "emulator.loadState",
        "movie.load", "movie.startPlayback", "movie.advanceToFrame",
        "movie.traceToFrame", "movie.stopPlayback", "movie.status", "movie.clear",
        "accessLog.addWatch", "accessLog.get", "accessLog.clear",
    }
    missing = sorted(
        method for method in required
        if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(f"running debugger lacks E08 hazard methods: {missing}")
    client.call("debugger.pause", {})
    inspections = [
        inspect_state_before_load(client, ROOT / row["save"]["path"], media_identity)
        for row in fixtures["pairs"]
    ]
    replays = [_run_movie(client, row) for row in fixtures["pairs"]]
    ground_bird = next(
        row for row in fixtures["pairs"] if row["lead"] == "E10_ground_bird_lead")
    level06_activation = _capture_level06_respawn_activation(
        client, ground_bird, level06_static_policy)
    final_media = verified_media_identity(client, client.call("debugger.status", {}))

    controlled = {
        value.lower() for replay in replays
        for value in replay["controlled_type_words"]
    }
    previous, remaining = _prior_frontier()
    props = json.loads(PROPS.read_text())
    unclassified = {
        row["type_word"].lower()
        for row in props["live"]["source_actor_clusters"]["behavior_classes"]
        if row["owner_classification"].startswith("unclassified")
    }
    new = controlled & remaining
    aggregate = previous | new
    still_remaining = remaining - new
    outside = controlled - unclassified
    health_or_lives = sum(
        replay["player_delta"]["health_or_lives_changed"] is True
        for replay in replays)

    provenance = finish_run(
        args, generator="tools/phase4_e08_hazard_outcomes.py",
        anchor={
            "type": "eight existing state-anchored E10 hazard lead movies",
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
            "typed_sampling": (
                "cycle-neutral anchor-to-target branches; stable final actor "
                "outcomes located by fresh binary-search replays"),
            "coverage_control": (
                "movie.traceToFrame uninstrumented versus passive cached-block replay"),
            "shared_c15_activation": (
                "scene-6 targets 487/488 plus exact initializer entry/return; "
                "accessLog is attribution-only and transient same-entry code "
                "branches are deleted before retention"),
        })
    document = {
        "_comment": (
            "Measured actor/player outcomes from existing E10 hazard leads. "
            "Filenames remain discovery metadata and assign no semantic owner."),
        "generated": date.today().isoformat(),
        "schema": "abl-phase4-e08-hazard-outcomes/2",
        "fixture_census": fixtures,
        "replays": replays,
        "shared_c15_level06_respawn_activation": level06_activation,
        "summary": {
            "movies_replayed": len(replays),
            "replays_with_health_or_lives_change": health_or_lives,
            "controlled_type_words": sorted(controlled),
            "newly_controlled_unclassified_type_words": sorted(new),
            "controlled_type_words_outside_unclassified_frontier": sorted(outside),
            "unclassified_with_native_outcome_controls": len(aggregate),
            "unclassified_without_native_outcome_control": len(still_remaining),
            "remaining_uncontrolled_type_words": sorted(still_remaining),
            "row_or_class_owners_promoted": 0,
        },
        "bounded_interpretation": {
            "observation": (
                "Eight complete cycle-neutral replays retain typed actor outcomes, "
                "player deltas and resident/Region-A coverage where observed."),
            "inference": (
                "A typed stable actor boundary can extend the E08 outcome frontier; "
                "a player-only boundary remains evidence for the later E10 campaign."),
            "causal_confirmation": (
                "The operator movies are natural positive leads for E08. The "
                "shared C15 join separately uses same-entry transient instruction "
                "controls to bind LEVEL06's four fixed safe fields; it assigns "
                "no hazard kind."),
            "forbidden_claim": (
                "Do not assign E08/E10 ownership, hazard kind, species, interaction "
                "writer or persistence from a filename or player-only outcome."),
        },
        "source_dependencies": {
            "tools/phase4_e08_operator_contacts.py": contacts._sha256(
                ROOT / "tools/phase4_e08_operator_contacts.py"),
            "analysis/phase4_props_movers.json": contacts._sha256(PROPS),
            "analysis/phase4_e08_outcome_join.json": contacts._sha256(OUTCOME_JOIN),
            "analysis/phase4_e08_operator_contacts.json": contacts._sha256(
                OPERATOR_CONTACTS),
            "analysis/phase4_respawn_writer_catalog.json": contacts._sha256(
                RESPAWN_WRITERS),
        },
        "run_provenance": provenance,
    }
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained E08 hazard evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print(
        f"[e08-hazard-outcomes] {len(new)} new E08 controls; "
        f"{len(still_remaining)} of 47 unclassified type words remain uncontrolled; "
        f"health/lives changed in {health_or_lives}/{len(replays)} replays")
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
                args, generator="tools/phase4_e08_hazard_outcomes.py",
                anchor={"type": "aborted before retained E08 hazard evidence"},
                timing={})
        except BaseException as cleanup_error:
            print(
                f"owned E08 hazard cleanup also failed: {cleanup_error}",
                file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
