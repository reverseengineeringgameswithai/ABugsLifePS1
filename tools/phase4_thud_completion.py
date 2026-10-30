#!/usr/bin/env python3
"""Bind Thud's exact counter-8 completion request and causal scene exit.

The pinned pristine Thud recording naturally reaches counter eight, writes the
resident master-state transition lever, retires the boss and leaves scene 14.
Passive movie traces are the timing authority.  A fresh matched branch NOPs
only the save-owned ``sh v0,0x23a0(at)`` request store; it preserves the fade,
defeat and retirement suffix but prevents the scene exit.  The retained output
contains typed values, instruction metadata and hashes, never fixture or
capture bytes.
"""
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
except ModuleNotFoundError:  # imported as tools.phase4_thud_completion
    from tools import phase4_c16_bonus_death as base
    from tools import phase4_e08_operator_contacts as contacts
    from tools import phase4_thud_defeat as thud
    from tools.live_session_provenance import (
        add_required_live_args, finish_run, inspect_state_before_load,
        retained_pristine_save_gaps, verified_media_identity,
        write_live_evidence,
    )


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_thud_completion.json"

ORIGIN_TARGET = 3739
PASSIVE_TARGETS = (3739, 3742, 3903, 4042)
BRANCH_TARGETS = (3741, 3902, 4041)
FADE_TIMER = 0x80082470
REQUEST_STORE = 0x800B3E84
REQUEST_WORD = 0xA42223A0
FADE_STORE = 0x800B3E90
FADE_WORD = 0xA4222470
COUNTER_STORE = 0x800B3DB0
COUNTER_EIGHT_GATE = 0x800B3DB4
RUNTIME_SLICE_ADDRESS = 0x800B3D9C
RUNTIME_SLICE_LENGTH = 0xFC
RUNTIME_SLICE_SHA256 = (
    "8ecf4b069584326f0ecc30acd387d168b34a355e618d5ff20c2a5c0c3dcfe53e")
TRACE_RANGE = {
    "label": "thud_counter8_completion_request",
    "start": f"0x{RUNTIME_SLICE_ADDRESS:08X}",
    "end": f"0x{RUNTIME_SLICE_ADDRESS + RUNTIME_SLICE_LENGTH - 4:08X}",
    "max_pcs": 256,
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_int(client: Any, address: int, fmt: str) -> int:
    return struct.unpack("<" + fmt, base._read_memory(
        client, address, struct.calcsize(fmt)))[0]


def _snapshot(client: Any, *, full_identity: bool = False) -> dict[str, Any]:
    status = client.call("debugger.status", {})
    movie = client.call("movie.status", {})
    result = {
        "emulator_frame": status.get("frame"),
        "cycle": status.get("cycle"),
        "pc": status.get("pc"),
        "sp": status.get("sp"),
        "movie_frame": movie.get("playback_index"),
        "movie_reproducible": movie.get("reproducible"),
        "movie_truncated": movie.get("truncated"),
        "scene": _read_int(client, thud.SCENE, "I"),
        "master_state": _read_int(client, thud.MASTER_STATE, "H"),
        "fade_timer": _read_int(client, FADE_TIMER, "h"),
        "phase_timer": _read_int(client, thud.PHASE_TIMER, "I"),
        "phase_counter": _read_int(client, thud.PHASE_COUNTER, "I"),
        "actor_hp": _read_int(client, thud.ACTOR_HP, "h"),
        "actor_flags": f"0x{_read_int(client, thud.ACTOR_FLAGS, 'H'):04x}",
        "live_table_0": f"0x{_read_int(client, thud.LIVE_TABLE_0, 'I'):08x}",
        "player_position": [
            _read_int(client, thud.PLAYER + offset, "i")
            for offset in (0, 4, 8)],
        "actor_position": [
            _read_int(client, thud.ACTOR + offset, "i")
            for offset in (4, 8, 12)],
    }
    if full_identity:
        result["main_ram_sha256"] = _sha256_bytes(base._main_ram(client))
        result["registers_sha256"] = base._register_sha256(client)
    return result


def _trace_to(client: Any, movie_path: Path, frame: int) -> dict[str, Any]:
    raw = client.call("movie.traceToFrame", {
        "path": str(movie_path.resolve()), "frame": frame,
        "ranges": [TRACE_RANGE],
    }, timeout=900)
    compact = contacts._compact_trace(raw)
    if (compact.get("comparison") or {}).get("cycle_neutral") is not True or \
            any(row.get("truncated") for row in compact.get("coverage") or []):
        raise SystemExit(f"Thud completion trace incomplete at {frame}")
    snapshot = _snapshot(client)
    if snapshot["movie_reproducible"] is not True or \
            snapshot["movie_truncated"] is not False:
        raise SystemExit(f"Thud completion movie drifted at {frame}")
    return {"target_movie_frame": frame, "snapshot": snapshot,
            "cycle_neutral_trace": compact}


def _passive_boundaries(
        client: Any, movie_path: Path) -> dict[str, dict[str, Any]]:
    labels = ("before_request", "after_request", "retired", "scene_exit")
    return {label: _trace_to(client, movie_path, frame)
            for label, frame in zip(labels, PASSIVE_TARGETS)}


def _reset_origin(
        client: Any, movie_path: Path, *, full_identity: bool) -> dict[str, Any]:
    row = _trace_to(client, movie_path, ORIGIN_TARGET)
    row["snapshot"] = _snapshot(client, full_identity=full_identity)
    return row


def _runtime_identity(client: Any) -> dict[str, Any]:
    data = base._read_memory(
        client, RUNTIME_SLICE_ADDRESS, RUNTIME_SLICE_LENGTH)
    disassembly = client.call("debugger.disassemble", {
        "address": f"0x{RUNTIME_SLICE_ADDRESS:08X}",
        "count": RUNTIME_SLICE_LENGTH // 4,
    })
    instructions = disassembly.get("instructions") or []
    by_address = {int(row["address"], 0): row for row in instructions}
    decisive = {}
    for address in (
            COUNTER_STORE, COUNTER_EIGHT_GATE, REQUEST_STORE, FADE_STORE):
        row = by_address.get(address) or {}
        decisive[f"0x{address:08x}"] = {
            key: row.get(key) for key in (
                "address", "bytes", "mnemonic", "operands", "text")}
    result = {
        "address": f"0x{RUNTIME_SLICE_ADDRESS:08x}",
        "length": RUNTIME_SLICE_LENGTH,
        "instruction_count": len(instructions),
        "sha256": _sha256_bytes(data),
        "classification": (
            "save-owned Region-A runtime; exact save/media identity required; "
            "not staged provenance"),
        "decisive_instructions": decisive,
    }
    if result["sha256"] != RUNTIME_SLICE_SHA256 or \
            result["instruction_count"] != RUNTIME_SLICE_LENGTH // 4:
        raise SystemExit(f"Thud completion runtime identity drifted: {result}")
    expected = {
        f"0x{COUNTER_STORE:08x}": ("ac224cc8", "sw"),
        f"0x{COUNTER_EIGHT_GATE:08x}": ("14430039", "bne"),
        f"0x{REQUEST_STORE:08x}": ("a42223a0", "sh"),
        f"0x{FADE_STORE:08x}": ("a4222470", "sh"),
    }
    observed = {key: (row.get("bytes"), row.get("mnemonic"))
                for key, row in decisive.items()}
    if observed != expected:
        raise SystemExit(f"Thud completion instructions drifted: {observed}")
    return result


def _advance_branch(
        client: Any, targets: tuple[int, ...] = BRANCH_TARGETS
        ) -> list[dict[str, Any]]:
    rows = []
    for frame in targets:
        client.call("movie.advanceToFrame", {
            "frame": frame, "max_frames": frame,
        }, timeout=300)
        rows.append({"target_movie_frame": frame, "snapshot": _snapshot(client)})
    return rows


def _ram_write_differences(before: bytes, after: bytes) -> list[dict[str, Any]]:
    return [{"address": f"0x{0x80000000 + offset:08x}",
             "before": old, "after": new}
            for offset, (old, new) in enumerate(zip(before, after))
            if old != new]


def _matched_request_control(
        client: Any, movie_path: Path) -> dict[str, Any]:
    control_origin = _reset_origin(
        client, movie_path, full_identity=True)
    runtime_identity = _runtime_identity(client)
    control = _advance_branch(client)

    mutation_origin = _reset_origin(
        client, movie_path, full_identity=True)
    before_ram = base._main_ram(client)
    word_before = _read_int(client, REQUEST_STORE, "I")
    write = client.call("debugger.writeU32", {
        "address": f"0x{REQUEST_STORE:08X}", "value": 0})
    word_after = _read_int(client, REQUEST_STORE, "I")
    after_ram = base._main_ram(client)
    after_write = _snapshot(client, full_identity=True)
    mutation = _advance_branch(client)

    comparable = (
        "emulator_frame", "cycle", "pc", "sp", "movie_frame", "scene",
        "master_state", "fade_timer", "phase_timer", "phase_counter",
        "actor_hp", "actor_flags", "live_table_0", "player_position",
        "actor_position", "main_ram_sha256", "registers_sha256")
    origin_equal = {
        key: control_origin["snapshot"].get(key) ==
        mutation_origin["snapshot"].get(key) for key in comparable}
    return {
        "control_origin": control_origin,
        "control": control,
        "mutation_origin": mutation_origin,
        "single_instruction": {
            "address": f"0x{REQUEST_STORE:08x}",
            "before_word": f"0x{word_before:08x}",
            "after_word": f"0x{word_after:08x}",
            "rpc": write,
            "write_differences": _ram_write_differences(
                before_ram, after_ram),
        },
        "after_write": after_write,
        "mutation": mutation,
        "origin_equal": origin_equal,
        "runtime_identity": runtime_identity,
        "control_rule": (
            "Both branches reset through cycle-neutral movie.traceToFrame to "
            "the same pristine frame-3738 RAM/register/cycle/PC/SP boundary. "
            "The mutation changes only the four instruction bytes at "
            "0x800B3E84; both sides then advance to identical movie targets."),
    }


def _writer_attribution(client: Any, movie_path: Path) -> dict[str, Any]:
    origin = _reset_origin(client, movie_path, full_identity=False)
    client.call("accessLog.clear", {})
    watches = [client.call("accessLog.addWatch", spec) for spec in (
        {"address": f"0x{thud.MASTER_STATE:08X}", "length": 2,
         "type": "write", "label": "completion_master_state",
         "max_events": 64},
        {"address": f"0x{FADE_TIMER:08X}", "length": 2,
         "type": "write", "label": "completion_fade_timer",
         "max_events": 64},
    )]
    run = client.call("accessLog.run", {"frames": 3})
    page = client.call("accessLog.get", {"offset": 0, "limit": 256})
    client.call("accessLog.clear", {})
    labels = {row["watch_id"]: row["label"] for row in watches}
    events = [{**row, "watch_label": labels.get(row.get("watch_id"))}
              for row in page.get("events") or []]
    changing = [row for row in events
                if row.get("new_value") is not None and
                row.get("new_value") != row.get("value")]

    def decisive(label: str, pc: int, old: int, new: int) -> dict[str, Any] | None:
        return next((row for row in changing
                     if row.get("watch_label") == label and
                     str(row.get("instruction_pc", "")).lower() ==
                     f"0x{pc:08x}" and row.get("value") == old and
                     row.get("new_value") == new), None)

    result = {
        "execution_mode_boundary": (
            "accessLog forces interpreter execution and supplies writer "
            "attribution only; passive traces and matched branches supply "
            "behavior and timing."),
        "origin": origin,
        "frames_run": 3,
        "accounting": {
            "total": page.get("total"),
            "returned": len(events),
            "truncated": page.get("truncated"),
        },
        "value_changing_events": changing,
        "decisive_writers": {
            "master_state_request": decisive(
                "completion_master_state", REQUEST_STORE, 0, 1),
            "fade_timer_request": decisive(
                "completion_fade_timer", FADE_STORE, 0, 150),
        },
        "final_status": {key: (run.get("status") or {}).get(key)
                         for key in ("pc", "sp", "frame", "cycle")},
    }
    if any(value is None
           for value in result["decisive_writers"].values()) or \
            result["accounting"]["truncated"] is not False:
        raise SystemExit(f"Thud completion writer attribution drifted: {result}")
    return result


def _source_dependencies() -> dict[str, str]:
    paths = (
        "tools/phase4_thud_defeat.py",
        "analysis/phase4_thud_defeat.json",
        "analysis/phase4_thud_arena.json",
        "analysis/phase0_2_external_fixture_set.json",
        "tools/scenarios/duckstation/"
        "pristine_thud_completion_request_control.yaml",
    )
    return {path: thud._sha256(ROOT / path) for path in paths}


def derive_summary(document: dict[str, Any]) -> dict[str, Any]:
    passive = document.get("passive_boundaries") or {}
    control = document.get("matched_request_control") or {}
    before = ((passive.get("before_request") or {}).get("snapshot") or {})
    after = ((passive.get("after_request") or {}).get("snapshot") or {})
    branches = control.get("control") or []
    mutations = control.get("mutation") or []
    natural_exit = (branches[-1].get("snapshot") or {}) if branches else {}
    suppressed_exit = (
        (mutations[-1].get("snapshot") or {}) if mutations else {})
    control_retired = (
        (branches[1].get("snapshot") or {}) if len(branches) > 1 else {})
    mutation_retired = (
        (mutations[1].get("snapshot") or {}) if len(mutations) > 1 else {})
    retirement_keys = ("actor_hp", "actor_flags", "live_table_0",
                       "player_position", "actor_position")
    return {
        "request_instruction_pc": f"0x{REQUEST_STORE:08x}",
        "fade_instruction_pc": f"0x{FADE_STORE:08x}",
        "counter_transition": [before.get("phase_counter"),
                               after.get("phase_counter")],
        "master_state_transition": [before.get("master_state"),
                                    after.get("master_state")],
        "fade_timer_transition": [before.get("fade_timer"),
                                  after.get("fade_timer")],
        "natural_vs_suppressed_scene": [natural_exit.get("scene"),
                                        suppressed_exit.get("scene")],
        "natural_vs_suppressed_master_state": [
            natural_exit.get("master_state"),
            suppressed_exit.get("master_state")],
        "retirement_suffix_equal": all(
            control_retired.get(key) == mutation_retired.get(key)
            for key in retirement_keys),
        "exact_completion_request_bound": True,
        "d18_or_f09_completed": 0,
    }


def evidence_gaps(document: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if document.get("schema") != "abl-phase4-thud-completion/1":
        gaps.append("Thud completion schema changed")
    if document.get("campaign_state") != "active_partial":
        gaps.append("Thud completion campaign state changed")
    passive = document.get("passive_boundaries") or {}
    expected = {
        "before_request": (3739, 3738, 14, 0, 0, 7, 48, "0x4055",
                           "0x8009fd80"),
        "after_request": (3742, 3741, 14, 1, 149, 8, 50, "0x4055",
                          "0x8009fd80"),
        "retired": (3903, 3902, 14, 1, 68, 8, 0, "0x0055",
                    "0x00000000"),
        "scene_exit": (4042, 4041, 0, 1, 0, 8, 0, "0x0055",
                       "0x00000000"),
    }
    for label, wanted in expected.items():
        row = passive.get(label) or {}
        snap = row.get("snapshot") or {}
        observed = (
            row.get("target_movie_frame"), snap.get("movie_frame"),
            snap.get("scene"), snap.get("master_state"),
            snap.get("fade_timer"), snap.get("phase_counter"),
            snap.get("actor_hp"), snap.get("actor_flags"),
            snap.get("live_table_0"))
        if observed != wanted or \
                (((row.get("cycle_neutral_trace") or {}).get("comparison") or
                  {}).get("cycle_neutral") is not True):
            gaps.append(f"Thud passive {label} boundary changed")
    after_trace = ((passive.get("after_request") or {}).get(
        "cycle_neutral_trace") or {})
    pcs = set()
    for coverage in after_trace.get("coverage") or []:
        pcs.update(coverage.get("pcs") or [])
    required_pcs = {f"0x{pc:08x}" for pc in (
        COUNTER_STORE, COUNTER_EIGHT_GATE, REQUEST_STORE, FADE_STORE)}
    if not required_pcs.issubset(pcs):
        gaps.append("Thud passive completion instruction coverage changed")

    attribution = document.get("writer_attribution") or {}
    writers = attribution.get("decisive_writers") or {}
    expected_writers = {
        "master_state_request": (f"0x{REQUEST_STORE:08x}", 0, 1),
        "fade_timer_request": (f"0x{FADE_STORE:08x}", 0, 150),
    }
    for label, wanted in expected_writers.items():
        row = writers.get(label) or {}
        observed = (str(row.get("instruction_pc", "")).lower(),
                    row.get("value"), row.get("new_value"))
        if observed != wanted:
            gaps.append(f"Thud {label} attribution changed")
    if (attribution.get("accounting") or {}).get("truncated") is not False:
        gaps.append("Thud completion writer accounting truncated")

    matched = document.get("matched_request_control") or {}
    runtime = matched.get("runtime_identity") or {}
    if (runtime.get("address"), runtime.get("length"),
            runtime.get("instruction_count"), runtime.get("sha256")) != (
                f"0x{RUNTIME_SLICE_ADDRESS:08x}", RUNTIME_SLICE_LENGTH,
                RUNTIME_SLICE_LENGTH // 4, RUNTIME_SLICE_SHA256):
        gaps.append("Thud completion runtime identity changed")
    if not matched.get("origin_equal") or \
            not all(matched.get("origin_equal", {}).values()):
        gaps.append("Thud completion matched origins changed")
    single = matched.get("single_instruction") or {}
    differences = single.get("write_differences") or []
    if (single.get("address"), single.get("before_word"),
            single.get("after_word"), (single.get("rpc") or {}).get("written"),
            (single.get("rpc") or {}).get("code_invalidated")) != (
                f"0x{REQUEST_STORE:08x}", f"0x{REQUEST_WORD:08x}",
                "0x00000000", 4, True) or len(differences) != 4 or \
            {row.get("address") for row in differences} != {
                f"0x{REQUEST_STORE + offset:08x}" for offset in range(4)}:
        gaps.append("Thud completion one-instruction suppression changed")
    control = matched.get("control") or []
    mutation = matched.get("mutation") or []
    if [row.get("target_movie_frame") for row in control] != \
            list(BRANCH_TARGETS) or \
            [row.get("target_movie_frame") for row in mutation] != \
            list(BRANCH_TARGETS):
        gaps.append("Thud completion branch targets changed")
    if len(control) == 3 and len(mutation) == 3:
        c0, c1, c2 = [row.get("snapshot") or {} for row in control]
        m0, m1, m2 = [row.get("snapshot") or {} for row in mutation]
        if (c0.get("scene"), c0.get("master_state"), c0.get("fade_timer"),
                c0.get("phase_counter")) != (14, 1, 149, 8) or \
                (m0.get("scene"), m0.get("master_state"),
                 m0.get("fade_timer"), m0.get("phase_counter")) != \
                (14, 0, 149, 8):
            gaps.append("Thud completion immediate request control changed")
        retirement = ("actor_hp", "actor_flags", "live_table_0",
                      "player_position", "actor_position")
        if any(c1.get(key) != m1.get(key) for key in retirement) or \
                (c1.get("scene"), m1.get("scene")) != (14, 14):
            gaps.append("Thud completion retirement suffix changed")
        if (c2.get("scene"), c2.get("master_state"),
                m2.get("scene"), m2.get("master_state")) != (0, 1, 14, 0) or \
                any(c2.get(key) != m2.get(key) for key in retirement):
            gaps.append("Thud completion causal scene-exit outcome changed")
    else:
        gaps.append("Thud completion matched branch length changed")

    expected_summary = {
        "request_instruction_pc": "0x800b3e84",
        "fade_instruction_pc": "0x800b3e90",
        "counter_transition": [7, 8],
        "master_state_transition": [0, 1],
        "fade_timer_transition": [0, 149],
        "natural_vs_suppressed_scene": [0, 14],
        "natural_vs_suppressed_master_state": [1, 0],
        "retirement_suffix_equal": True,
        "exact_completion_request_bound": True,
        "d18_or_f09_completed": 0,
    }
    if document.get("summary") != derive_summary(document) or \
            document.get("summary") != expected_summary:
        gaps.append("Thud completion derived summary changed")
    gaps.extend(retained_pristine_save_gaps(
        document, require_selection=False))
    cleanup = (document.get("run_provenance") or {}).get("cleanup") or {}
    if cleanup and cleanup.get("owned_pid_stopped") is not True:
        gaps.append("owned Thud completion process cleanup changed")
    return gaps


def _run(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(Path.home() / "duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    fixture = thud.build_fixture_census()
    client = DebuggerClient("127.0.0.1", args.port, "ws")
    client.authenticate(args.token)
    client.transport.sock.settimeout(900)
    status = client.call("debugger.status", {})
    media = verified_media_identity(client, status)
    capabilities = client.call("debugger.capabilities", {})
    required = {
        "accessLog.addWatch", "accessLog.clear", "accessLog.get",
        "accessLog.run", "debugger.capabilities", "debugger.disassemble",
        "debugger.getRegisters", "debugger.pause", "debugger.readMemory",
        "debugger.status", "debugger.writeU32", "emulator.getMediaInfo",
        "emulator.getStateInfo", "movie.advanceToFrame", "movie.clear",
        "movie.load", "movie.startPlayback", "movie.status",
        "movie.stopPlayback", "movie.traceToFrame",
    }
    missing = sorted(method for method in required
                     if not contacts._method_present(capabilities, method))
    if missing:
        raise SystemExit(
            f"running debugger lacks Thud completion methods: {missing}")
    client.call("debugger.pause", {})
    inspection = inspect_state_before_load(client, ROOT / thud.SAVE_REL, media)
    movie_path = ROOT / thud.MOVIE_REL
    passive = _passive_boundaries(client, movie_path)
    matched = _matched_request_control(client, movie_path)
    attribution = _writer_attribution(client, movie_path)
    base._cleanup(client)
    final_media = verified_media_identity(
        client, client.call("debugger.status", {}))
    provenance = finish_run(
        args, generator="tools/phase4_thud_completion.py",
        anchor={
            "type": "existing state-anchored Thud natural-defeat recording",
            "save": thud.SAVE_REL, "movie": thud.MOVIE_REL,
            "fixture_sha256": {
                thud.SAVE_REL: thud.SAVE_SHA256,
                thud.MOVIE_REL: thud.MOVIE_SHA256,
            },
            "state_inspections": [inspection], "media_identity": media,
            "final_media_identity": final_media,
        },
        timing={
            "cpu_overclock_percent": 100, "cd_read_speedup": 1,
            "cd_seek_speedup": 1, "rewind": False, "run_ahead": False,
            "passive_trace_targets": list(PASSIVE_TARGETS),
            "matched_branch_origin_target": ORIGIN_TARGET,
            "matched_branch_targets": list(BRANCH_TARGETS),
            "trace_mode": (
                "passive cycle-neutral movie.traceToFrame boundaries; "
                "fresh matched single-instruction suppression branches; "
                "interpreter access log retained only for writer attribution"),
        })
    document = {
        "_comment": (
            "Active D18/F09 evidence: counter eight executes exact save-owned "
            "master-state/fade request stores; suppressing only the master-state "
            "store preserves defeat/retirement but prevents scene 14->0. Other "
            "attacks, damage breadth, visual ownership, retry and persistence "
            "remain open, so neither row is promoted complete."),
        "generated": "2026-07-17",
        "schema": "abl-phase4-thud-completion/1",
        "campaign_state": "active_partial",
        "fixture_census": fixture,
        "passive_boundaries": passive,
        "writer_attribution": attribution,
        "matched_request_control": matched,
        "bounded_interpretation": {
            "observation": (
                "The eighth natural reset increments the save-owned phase "
                "counter 7->8, writes master state 0->1 at 0x800B3E84, writes "
                "fade timer 150 at 0x800B3E90, later retires Thud and exits "
                "scene 14 to scene 0."),
            "inference": (
                "The paired master/fade writes are the Bug Bar overlay's "
                "objective-completion request into resident scene flow; scene "
                "0 remains the downstream unload boundary, not the request."),
            "causal_confirmation": (
                "At an identical full-RAM/register/cycle/PC/SP origin, NOPing "
                "only 0x800B3E84 leaves counter eight, fade 150, HP zero, active-"
                "bit retirement, live-slot clear and positions intact, while "
                "scene 14 remains loaded at the natural scene-exit target."),
            "forbidden_claim": (
                "Do not infer that master state 1 has one global meaning, that "
                "fade alone requests exit, or that this one objective boundary "
                "completes D18/F09 attack, lifecycle or breadth packages."),
        },
        "bounded_open_frontier": {
            "closed_here": (
                "Exact counter-8 objective request, paired fade request and "
                "causal resident scene-exit handoff."),
            "still_open": (
                "Other boss attacks, complete damage curve, named arena visual/"
                "GPU ownership, initialization, re-engagement, retry, checkpoint, "
                "persistence, representative breadth and failure paths."),
            "next_experiment": (
                "Use the same recording to bind another distinct Thud attack or "
                "request a narrowly targeted retry/re-engagement fixture only "
                "after the existing movie tree cannot supply that boundary."),
        },
        "source_dependencies": _source_dependencies(),
        "run_provenance": provenance,
    }
    document["summary"] = derive_summary(document)
    gaps = evidence_gaps(document)
    if gaps:
        raise SystemExit(f"retained Thud completion evidence failed: {gaps}")
    write_live_evidence(OUTPUT, document)
    print("[thud-completion] exact counter-8 scene-exit request bound")
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
                finish_run(
                    args, generator="tools/phase4_thud_completion.py",
                    anchor={"type": "aborted before retained completion evidence"},
                    timing={})
            except BaseException as cleanup_error:
                print(
                    "owned Thud completion cleanup also failed: "
                    f"{cleanup_error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
