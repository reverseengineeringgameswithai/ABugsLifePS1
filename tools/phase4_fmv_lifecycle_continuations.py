#!/usr/bin/env python3
"""Reconstruct every resident continuation after synchronous E15 playback."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from build_identity import verify_staged_input
import phase4_fmv_interface_frontier as frontier


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_lifecycle_continuations.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
SOURCE_MANIFEST = ROOT / "tools/repro_inputs.sha256"
SEMANTIC_SOURCE = ROOT / "src_re/fmv_lifecycle_continuations.c"
CONFIG = ROOT / "config/phase4_fmv_lifecycle_continuations.yaml"
SEGMENTS = ROOT / "config/segments.yml"
MATCHING_LOADER_SOURCE = ROOT / "src/main/8003e7c0_fmv_bin_load.c"
MATCHING_POST_PLAYER_SOURCE = ROOT / "src/main/80039854_boot_subsystem_init.c"
MATCHING_CD_EVENT_CALLBACK_SOURCE = ROOT / "src/main/80045d5c_gp_set_one.c"
CD_SUBSYSTEM_INIT_SOURCE = (
    ROOT / "asm/hand_written/80045d6c_cd_subsystem_init.s")
INTERFACE_ARTIFACT = ROOT / "analysis/phase4_fmv_interface_frontier.json"
STATIC_OWNER_ARTIFACT = ROOT / "analysis/phase4_fmv_static_owners.json"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _hex(value: int) -> str:
    return f"0x{value:08X}"


# Windows begin at the instruction after fmv_bin_load's delay slot.  They end
# at the next independently owned transition or the enclosing function's true
# end.  Hashing every byte makes this a stronger boundary than a chosen-opcode
# summary and catches a new store, branch or call in the interior.
CONTINUATIONS = (
    {
        "id": "boot_dlogo",
        "call": 0x8004FB5C,
        "start": 0x8004FB64,
        "end": 0x8004FB68,
        "sha256": "016559e0e3772403783ed7ae47e4806435395520dadbfe85af27f151ff8127cb",
        "owner": "main_shell_state_machine",
        "family": "boot_repeated_playback",
        "outcome": "loads selector zero for the next synchronous title movie",
    },
    {
        "id": "boot_title",
        "call": 0x8004FB68,
        "start": 0x8004FB70,
        "end": 0x8004FB74,
        "sha256": "f008ec3a16bf6254489d1dfe29ab75ffe8a06a4dbe0c0004f68b9f35e3b1edae",
        "owner": "main_shell_state_machine",
        "family": "boot_repeated_playback",
        "outcome": "loads selector 45 for the next synchronous intro movie",
    },
    {
        "id": "boot_intro",
        "call": 0x8004FB74,
        "start": 0x8004FB7C,
        "end": 0x8004FC3C,
        "sha256": "a0d72e4cb3049bdad58062e33ce0bc6a967405d28a2a5d4a032fc7a0e2b21b39",
        "owner": "main_shell_state_machine",
        "family": "boot_to_frontend",
        "outcome": "initializes scene flow and reaches the guarded six-target shell dispatch",
    },
    {
        "id": "bonus_clip_sequence",
        "call": 0x8004FFD4,
        "start": 0x8004FFDC,
        "end": 0x80050004,
        "sha256": "0bb1f3abeeae712704abe25265df894d2ed433757217ed96f52b277c5de14f42",
        "owner": "scene_flow_dispatcher",
        "family": "bonus_iteration",
        "outcome": "publishes the scene-flow return state and continues the bonus cursor loop",
    },
    {
        "id": "game_over_lose",
        "call": 0x800500D8,
        "start": 0x800500E0,
        "end": 0x800500F4,
        "sha256": "782344e336768eb1c919f633ab4b73908bb0e7a4db0d55eb38b4d09876356d98",
        "owner": "scene_flow_dispatcher",
        "family": "game_over_to_scene",
        "outcome": "calls scene_setup_and_load with a0=5 and delay-slot a1=64",
    },
    {
        "id": "finale_lev15c",
        "call": 0x80050284,
        "start": 0x8005028C,
        "end": 0x8005029C,
        "sha256": "84d14d0ffe287e1eaca6cfdef78ce7dc4e315ceed849edfc75cc55b28e1fd5bd",
        "owner": "scene_flow_dispatcher",
        "family": "finale_to_level_transition",
        "outcome": "calls level_transition_orchestrator with a0=0",
    },
    {
        "id": "completed_level_b",
        "call": 0x8005031C,
        "start": 0x80050324,
        "end": 0x8005036C,
        "sha256": "38ce7971afec42c89fedb004d45765ff63b392b2fbe71a9b9f4d4f5f36ccd5f9",
        "owner": "fmv_sequence_completion_check",
        "family": "level_b_progress_scan",
        "outcome": "sums 16 progress bytes and selects finale D only when the total is 112",
    },
    {
        "id": "all_levels_complete_lev15d",
        "call": 0x8005036C,
        "start": 0x80050374,
        "end": 0x8005038C,
        "sha256": "e57464f3afc65a84594b9977d3c704995b8694c2facb81716a9b4c48ce0bc324",
        "owner": "fmv_sequence_completion_check",
        "family": "finale_to_shell",
        "outcome": "publishes scene-flow transition value one and returns",
    },
    {
        "id": "level_a_reset_handoff",
        "call": 0x8005B788,
        "start": 0x8005B790,
        "end": 0x8005BC64,
        "sha256": "1205b9e134100eb87fa27ba06f49162b22c42436d04879b0015a5445c4133a44",
        "owner": "gameplay_state_reset_cursor_seed",
        "family": "level_a_reset_and_scene_load",
        "outcome": "clears transition state and executes the complete reset/scene-load continuation",
    },
)

PLAYER_WINDOWS = (
    ("completion_writers", 0x800B6B10, 0x800B6B4C,
     "bb21d7adbbe08910c516c862ff1663861b95bfd8b278fa79b9e5821f7208637b"),
    ("decode_record_absent", 0x800B6C24, 0x800B6CA4,
     "9d91718d072e2af77e13cff008ed3a935655e8facd4bb53f50ff0febd2c5d074"),
    ("decode_poll_timeout", 0x800B6CA4, 0x800B6D68,
     "06e83c28563ab998976b036f6e23c52c840352bee19c39efdd58322a7383e205"),
    ("player_exit_routing", 0x800B7294, 0x800B7464,
     "20d1fe33db6097d322899629549b88041a664ac948f6f5a76156c7c94df32853"),
    ("pause_stop_and_teardown", 0x800B7464, 0x800B752C,
     "49d06700299671580639874e4d3181f30f6394980756fab57d14a274127aac8a"),
)

LOADER_START = 0x8003E7C0
LOADER_END = 0x8003E83C
LOADER_SHA256 = "a9de53707b6fd702ed41d5010d3ac264bbd4145c12a6363475a003ccae9f68e3"
LOADER_CALLS = (
    {
        "role": "pre_player_display_reset",
        "pc": 0x8003E7D4,
        "target": 0x80039478,
        "conditional": False,
    },
    {
        "role": "optional_transition_pre_hook",
        "pc": 0x8003E7E4,
        "target": 0x8005B440,
        "conditional": True,
    },
    {
        "role": "fmv_bin_reload",
        "pc": 0x8003E7FC,
        "target": 0x80046330,
        "conditional": False,
    },
    {
        "role": "optional_transition_post_hook",
        "pc": 0x8003E80C,
        "target": 0x8005B4E4,
        "conditional": True,
    },
    {
        "role": "synchronous_fmv_player",
        "pc": 0x8003E814,
        "target": 0x800B6250,
        "conditional": False,
    },
    {
        "role": "post_player_display_reinitialization",
        "pc": 0x8003E81C,
        "target": 0x80039854,
        "conditional": False,
    },
)

LOADER_KEY_WORDS = {
    0x8003E7C8: 0x00808821,  # selector -> s1
    0x8003E7D8: 0x00A08021,  # hook enable -> s0
    0x8003E7DC: 0x12000003,  # skip pre hook when disabled
    0x8003E7EC: 0x3C048002,  # "fmv\\fmv.bin" pointer high
    0x8003E7F0: 0x2484AE6C,  # "fmv\\fmv.bin" pointer low
    0x8003E7F4: 0x3C05800B,  # Region-B destination high
    0x8003E7F8: 0x24A55788,  # Region-B destination low
    0x8003E804: 0x12000003,  # skip post hook when disabled
    0x8003E818: 0x02202021,  # selector -> player a0 in delay slot
}

CD_EVENT_CALLBACK_START = 0x80045D5C
CD_EVENT_CALLBACK_END = 0x80045D6C
CD_EVENT_CALLBACK_SHA256 = (
    "3d015ec5134457e676b69047323c2db3ee7b9ab902b25d4e88530e56c45fdd2c")
CD_EVENT_CALLBACK_WORDS = {
    0x80045D5C: 0x24020001,
    0x80045D60: 0xAF8206EC,
    0x80045D64: 0x03E00008,
    0x80045D68: 0x00000000,
}
CD_EVENT_REGISTRATION_START = 0x80045E38
CD_EVENT_REGISTRATION_END = 0x80045E64
CD_EVENT_REGISTRATION_SHA256 = (
    "6d81bdc9029f8fdc1d9c4cd052d3164a805aa8c92aaacc19cb15480d6736de76")
CD_EVENT_REGISTRATION_WORDS = {
    0x80045E38: 0x3C04F000,
    0x80045E3C: 0x34840003,
    0x80045E40: 0x34058000,
    0x80045E44: 0x3C078004,
    0x80045E48: 0x24E75D5C,
    0x80045E4C: 0x0C0197CF,
    0x80045E50: 0x24061000,
    0x80045E54: 0x00402021,
    0x80045E58: 0xAF840570,
    0x80045E5C: 0x0C0197DF,
    0x80045E60: 0x00000000,
}
CD_EVENT_FIELD_ADDRESS = 0x80082484
CD_EVENT_FIELD_GP_OFFSET = 0x06EC
CD_EVENT_HANDLE_ADDRESS = 0x80082308
FMV_EVENT_CONSUMER_START = 0x800B741C
FMV_EVENT_CONSUMER_END = 0x800B7474
FMV_EVENT_CONSUMER_SHA256 = (
    "86e1a7105affd7ff1cdf0266897d0ec7c607b519091216d1869ab778f508da9a")
FMV_EVENT_CONSUMER_WORDS = {
    0x800B741C: 0x3C028008,
    0x800B7420: 0x8C422484,
    0x800B7428: 0x1054000E,
    0x800B7464: 0x2404000B,
    0x800B746C: 0x0C01B63A,
}
FMV_EVENT_SENTINEL_WORD = {0x800B70D8: 0x24140001}


def _manifest_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in SOURCE_MANIFEST.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            pins[fields[1]] = fields[0]
    return pins


def _source_row(owner: str, pins: dict[str, str]) -> dict[str, Any]:
    start, end, source = frontier.CALLER_REGIONS[owner]
    expected = pins.get(source)
    if expected is None:
        raise SystemExit(f"continuation owner lacks central source pin: {source}")
    actual = _sha256(ROOT / source)
    if actual != expected:
        raise SystemExit(f"continuation owner source pin drifted: {source}")
    return {
        "owner": owner,
        "range": [_hex(start), _hex(end)],
        "source": source,
        "sha256": actual,
        "expected_sha256": expected,
        "source_status": "handwritten_asm_external_hash_pinned",
    }


def _direct_calls(exe: bytes, start: int, end: int) -> list[dict[str, Any]]:
    rows = []
    for pc in range(start, end, 4):
        word = frontier._word(
            exe, pc, base=frontier.EXE_BASE, header=frontier.EXE_HEADER)
        target = frontier._jal_target(pc, word)
        if target is not None:
            rows.append({
                "pc": _hex(pc),
                "target": _hex(target),
                "instruction": frontier._instruction(
                    exe, pc, base=frontier.EXE_BASE,
                    header=frontier.EXE_HEADER),
            })
    return rows


def _matching_source_map() -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(SEGMENTS.read_text())
    matches = [
        row for row in document.get("attempted", [])
        if row.get("source") == "src/main/8003e7c0_fmv_bin_load.c"
    ]
    if matches != [{
            "start": LOADER_START,
            "end": LOADER_END,
            "source": "src/main/8003e7c0_fmv_bin_load.c",
    }]:
        raise SystemExit("matching FMV loader source map drifted")
    return {
        "path": "src/main/8003e7c0_fmv_bin_load.c",
        "sha256": _sha256(MATCHING_LOADER_SOURCE),
        "segments_path": "config/segments.yml",
        "segments_sha256": _sha256(SEGMENTS),
        "range": [_hex(LOADER_START), _hex(LOADER_END)],
        "source_status": "matching_c",
    }


def _matching_cd_event_source_map(pins: dict[str, str]) -> dict[str, Any]:
    import yaml

    document = yaml.safe_load(SEGMENTS.read_text())
    callback_matches = [
        row for row in document.get("attempted", [])
        if row.get("source") == "src/main/80045d5c_gp_set_one.c"
    ]
    if callback_matches != [{
            "start": CD_EVENT_CALLBACK_START,
            "end": CD_EVENT_CALLBACK_END,
            "source": "src/main/80045d5c_gp_set_one.c",
            "small_data": True,
    }]:
        raise SystemExit("matching CD event callback source map drifted")
    init_matches = [
        row for row in document.get("attempted", [])
        if row.get("source") ==
        "asm/hand_written/80045d6c_cd_subsystem_init.s"
    ]
    if init_matches != [{
            "start": CD_EVENT_CALLBACK_END,
            "end": 0x80045FC4,
            "source": "asm/hand_written/80045d6c_cd_subsystem_init.s",
    }]:
        raise SystemExit("CD subsystem init source map drifted")
    init_path = "asm/hand_written/80045d6c_cd_subsystem_init.s"
    init_expected = pins.get(init_path)
    init_actual = _sha256(CD_SUBSYSTEM_INIT_SOURCE)
    if init_expected is None or init_actual != init_expected:
        raise SystemExit("CD subsystem init central source pin drifted")
    return {
        "callback": {
            "path": "src/main/80045d5c_gp_set_one.c",
            "sha256": _sha256(MATCHING_CD_EVENT_CALLBACK_SOURCE),
            "range": [
                _hex(CD_EVENT_CALLBACK_START), _hex(CD_EVENT_CALLBACK_END)],
            "source_status": "matching_c",
        },
        "registration_owner": {
            "path": init_path,
            "sha256": init_actual,
            "expected_sha256": init_expected,
            "range": [_hex(CD_EVENT_CALLBACK_END), "0x80045FC4"],
            "source_status": "handwritten_asm_external_hash_pinned",
        },
    }


def _assert_words(data: bytes, expected: dict[int, int], *,
                  base: int, header: int, label: str) -> None:
    for pc, word in expected.items():
        observed = frontier._word(data, pc, base=base, header=header)
        if observed != word:
            raise SystemExit(f"{label} key word drifted: {_hex(pc)}")


def _native_cd_event_route(
        exe: bytes, fmv: bytes, pins: dict[str, str]) -> dict[str, Any]:
    callback = frontier._slice(
        exe, CD_EVENT_CALLBACK_START, CD_EVENT_CALLBACK_END,
        base=frontier.EXE_BASE, header=frontier.EXE_HEADER)
    if _sha256_bytes(callback) != CD_EVENT_CALLBACK_SHA256:
        raise SystemExit("native CD event callback window drifted")
    _assert_words(
        exe, CD_EVENT_CALLBACK_WORDS, base=frontier.EXE_BASE,
        header=frontier.EXE_HEADER, label="native CD event callback")

    registration = frontier._slice(
        exe, CD_EVENT_REGISTRATION_START, CD_EVENT_REGISTRATION_END,
        base=frontier.EXE_BASE, header=frontier.EXE_HEADER)
    if _sha256_bytes(registration) != CD_EVENT_REGISTRATION_SHA256:
        raise SystemExit("native CD event registration window drifted")
    _assert_words(
        exe, CD_EVENT_REGISTRATION_WORDS, base=frontier.EXE_BASE,
        header=frontier.EXE_HEADER, label="native CD event registration")

    consumer = frontier._slice(
        fmv, FMV_EVENT_CONSUMER_START, FMV_EVENT_CONSUMER_END,
        base=frontier.FMV_BASE, header=0)
    if _sha256_bytes(consumer) != FMV_EVENT_CONSUMER_SHA256:
        raise SystemExit("FMV native CD event consumer window drifted")
    _assert_words(
        fmv, FMV_EVENT_CONSUMER_WORDS | FMV_EVENT_SENTINEL_WORD,
        base=frontier.FMV_BASE, header=0,
        label="FMV native CD event consumer")

    resident_gp_xrefs = []
    for pc in range(frontier.EXE_BASE, frontier.EXE_END, 4):
        word = frontier._word(
            exe, pc, base=frontier.EXE_BASE, header=frontier.EXE_HEADER)
        if ((word >> 21) & 0x1F) != 28 or (
                word & 0xFFFF) != CD_EVENT_FIELD_GP_OFFSET:
            continue
        opcode = (word >> 26) & 0x3F
        if opcode not in (0x23, 0x2B):
            raise SystemExit(f"unclassified gp+0x06ec access at {_hex(pc)}")
        resident_gp_xrefs.append({
            "pc": _hex(pc),
            "operation": "load" if opcode == 0x23 else "store",
            "word": _hex(word),
        })
    expected_gp_xrefs = [
        ("0x80045B80", "load", "0x8F8206EC"),
        ("0x80045BA0", "store", "0xAF8006EC"),
        ("0x80045D60", "store", "0xAF8206EC"),
        ("0x8004621C", "store", "0xAF8006EC"),
        ("0x800462EC", "load", "0x8F8206EC"),
        ("0x8004640C", "store", "0xAF8006EC"),
        ("0x800464E4", "load", "0x8F8206EC"),
    ]
    if [(row["pc"], row["operation"], row["word"])
            for row in resident_gp_xrefs] != expected_gp_xrefs:
        raise SystemExit("resident gp+0x06ec xref census drifted")

    return {
        "registration": {
            "owner": "cd_subsystem_init",
            "window": {
                "start": _hex(CD_EVENT_REGISTRATION_START),
                "end": _hex(CD_EVENT_REGISTRATION_END),
                "size": len(registration),
                "sha256": CD_EVENT_REGISTRATION_SHA256,
            },
            "event_class": "0xF0000003",
            "event_spec": "0x00008000",
            "callback": _hex(CD_EVENT_CALLBACK_START),
            "mode": "0x00001000",
            "open_event": "0x80065F3C",
            "enable_event": "0x80065F7C",
            "event_handle_address": _hex(CD_EVENT_HANDLE_ADDRESS),
        },
        "callback": {
            "window": {
                "start": _hex(CD_EVENT_CALLBACK_START),
                "end": _hex(CD_EVENT_CALLBACK_END),
                "size": len(callback),
                "sha256": CD_EVENT_CALLBACK_SHA256,
            },
            "store": {
                "pc": "0x80045D60",
                "address": _hex(CD_EVENT_FIELD_ADDRESS),
                "gp_offset": "0x000006EC",
                "type": "u32",
                "value": 1,
            },
        },
        "resident_field_xrefs": resident_gp_xrefs,
        "player_consumer": {
            "window": {
                "start": _hex(FMV_EVENT_CONSUMER_START),
                "end": _hex(FMV_EVENT_CONSUMER_END),
                "size": len(consumer),
                "sha256": FMV_EVENT_CONSUMER_SHA256,
            },
            "load": {
                "pc": "0x800B7420",
                "address": _hex(CD_EVENT_FIELD_ADDRESS),
                "type": "u32",
            },
            "sentinel": {"pc": "0x800B70D8", "value": 1},
            "exit_branch": {
                "pc": "0x800B7428",
                "taken_when": "loaded value equals 1",
                "target": "0x800B7464",
            },
            "common_teardown": {
                "cd_control_site": "0x800B7464",
                "command": "0x0B",
                "cd_control_call": "0x800B746C",
            },
        },
        "planned_same_anchor_control_basis": {
            "site": "0x800B7420",
            "negative_word": "0x8C422484",
            "positive_word": "0x24020001",
            "only_difference": (
                "replace the field load with addiu v0,zero,1 while preserving "
                "the exact comparison, branch target and teardown code"),
            "proves_if_observed": (
                "the player-consumer value-1 interface reaches the native "
                "Pause/common-teardown path before caller-owned replacement"),
            "does_not_prove": (
                "native event delivery, delivery frequency, media-failure "
                "classification, or user-visible failure outcome"),
        },
        "sources": _matching_cd_event_source_map(pins),
        "static_edges": [
            "OpenEvent registration -> callback 0x80045D5C",
            "callback -> u32 store 1 at 0x80082484",
            "FMV load 0x80082484 -> equality branch on sentinel 1",
            "taken branch -> CdControl(0x0B) common teardown",
        ],
        "unclassified_static_edges": 0,
        "runtime_event_delivery_claimed": False,
        "native_failure_outcome_claimed": False,
    }


def _loader_lifecycle(exe: bytes) -> dict[str, Any]:
    payload = frontier._slice(
        exe, LOADER_START, LOADER_END, base=frontier.EXE_BASE,
        header=frontier.EXE_HEADER)
    if _sha256_bytes(payload) != LOADER_SHA256:
        raise SystemExit("FMV loader lifecycle window drifted")
    for pc, expected in LOADER_KEY_WORDS.items():
        observed = frontier._word(
            exe, pc, base=frontier.EXE_BASE, header=frontier.EXE_HEADER)
        if observed != expected:
            raise SystemExit(f"FMV loader lifecycle key word drifted: {_hex(pc)}")

    direct_calls = _direct_calls(exe, LOADER_START, LOADER_END)
    observed_edges = [
        (int(row["pc"], 16), int(row["target"], 16))
        for row in direct_calls
    ]
    expected_edges = [(row["pc"], row["target"]) for row in LOADER_CALLS]
    if observed_edges != expected_edges:
        raise SystemExit("FMV loader lifecycle call sequence drifted")

    source = _matching_source_map()
    calls = []
    for observed, expected in zip(direct_calls, LOADER_CALLS):
        calls.append({
            **observed,
            "role": expected["role"],
            "conditional": expected["conditional"],
        })
    return {
        "owner": {
            "start": _hex(LOADER_START),
            "end": _hex(LOADER_END),
            "size": LOADER_END - LOADER_START,
            "sha256": LOADER_SHA256,
            "source": source,
        },
        "arguments": {
            "selector": {
                "entry_register": "a0",
                "saved_register": "s1",
                "save_pc": "0x8003E7C8",
                "player_delay_slot": "0x8003E818",
            },
            "transition_hook_enable": {
                "entry_register": "a1",
                "saved_register": "s0",
                "save_pc": "0x8003E7D8",
                "domain_at_all_direct_callers": [0, -1],
            },
        },
        "ordered_calls": calls,
        "region_b_reload": {
            "unconditional_call": "0x8003E7FC",
            "loader": "0x80046330",
            "path_pointer": "0x8001AE6C",
            "path": r"fmv\fmv.bin",
            "destination": "0x800B5788",
            "occurs_once_per_fmv_bin_load_invocation": True,
            "repeat_calls_recopy_identical_overlay_bytes": True,
        },
        "post_player": {
            "player_call": "0x8003E814",
            "display_reinitialization_call": "0x8003E81C",
            "display_reinitialization_source": {
                "path": "src/main/80039854_boot_subsystem_init.c",
                "sha256": _sha256(MATCHING_POST_PLAYER_SOURCE),
                "source_status": "matching_c",
            },
            "loader_returns_after_display_reinitialization": True,
        },
        "retirement_partition": {
            "common_player_teardown_ends_transient_fmv_use": True,
            "fmv_loader_contains_explicit_region_b_unload": False,
            "fmv_loader_contains_explicit_region_b_clear": False,
            "post_return_replacement_owner": "resident caller continuation or later Region-B loader",
            "all_post_return_owners_classified": True,
            "endpoint_nonresidency_does_not_identify_overwrite_instruction": True,
        },
        "summary": {
            "ordered_direct_calls": len(calls),
            "unconditional_reload_calls": 1,
            "conditional_transition_hooks": 2,
            "unclassified_loader_edges": 0,
            "unclassified_repeat_reload_retirement_owners": 0,
        },
    }


def build(*, exe_data: bytes | None = None, fmv_data: bytes | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = frontier.FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(frontier.FMV_REL, fmv)

    expected_calls = [row[0] for row in frontier.CONSUMERS]
    observed_calls = frontier._jal_sites(
        exe, 0x8003E7C0, base=frontier.EXE_BASE,
        header=frontier.EXE_HEADER, end=frontier.EXE_END)
    if observed_calls != expected_calls:
        raise SystemExit("FMV lifecycle continuation call census drifted")

    loader_lifecycle = _loader_lifecycle(exe)
    pins = _manifest_pins()
    owner_rows = {
        owner: _source_row(owner, pins)
        for owner in sorted({row["owner"] for row in CONTINUATIONS})
    }
    continuation_rows = []
    for spec in CONTINUATIONS:
        payload = frontier._slice(
            exe, spec["start"], spec["end"], base=frontier.EXE_BASE,
            header=frontier.EXE_HEADER)
        actual_hash = _sha256_bytes(payload)
        if actual_hash != spec["sha256"]:
            raise SystemExit(
                f"FMV lifecycle continuation window drifted: {spec['id']}")
        owner = owner_rows[spec["owner"]]
        if not (int(owner["range"][0], 16) <= spec["call"] <
                spec["start"] < spec["end"] <= int(owner["range"][1], 16)):
            raise SystemExit(
                f"FMV lifecycle continuation escaped its owner: {spec['id']}")
        continuation_rows.append({
            "id": spec["id"],
            "loader_call": _hex(spec["call"]),
            "return_pc": _hex(spec["start"]),
            "window": {
                "start": _hex(spec["start"]),
                "end": _hex(spec["end"]),
                "size": spec["end"] - spec["start"],
                "sha256": actual_hash,
            },
            "owner": spec["owner"],
            "family": spec["family"],
            "static_outcome": spec["outcome"],
            "direct_calls": _direct_calls(exe, spec["start"], spec["end"]),
        })

    interface = json.loads(INTERFACE_ARTIFACT.read_text())
    interface_calls = [
        row["call"]["pc"]
        for row in interface["resident_consumers"]["calls"]
    ]
    if interface_calls != [_hex(pc) for pc in expected_calls]:
        raise SystemExit("FMV interface artifact consumer join drifted")
    exceptional = interface["exceptional_frontier"]
    if [row["id"] for row in exceptional["paths"]] != [
            "file_open_failure", "decode_record_absent",
            "decode_poll_timeout", "cd_submit_retry"]:
        raise SystemExit("FMV exceptional continuation join drifted")
    if not interface["callback_lifecycle"]["teardown"][
            "all_player_exit_edges_converge"]:
        raise SystemExit("FMV common teardown convergence join drifted")

    static_owners = json.loads(STATIC_OWNER_ARTIFACT.read_text())
    completion = static_owners["completion_ownership"]
    if [(row["role"], row["instruction"]["pc"])
            for row in completion["xrefs"]] != [
        ("frame_order_regression_set", "0x800B6B24"),
        ("selected_limit_set", "0x800B6B48"),
        ("stream_start_clear", "0x800B6DD0"),
        ("player_loop_exit_read", "0x800B743C"),
    ]:
        raise SystemExit("FMV completion ownership join drifted")

    player_windows = []
    for identifier, start, end, expected_hash in PLAYER_WINDOWS:
        payload = frontier._slice(
            fmv, start, end, base=frontier.FMV_BASE, header=0)
        actual_hash = _sha256_bytes(payload)
        if actual_hash != expected_hash:
            raise SystemExit(
                f"FMV transient player continuation window drifted: {identifier}")
        player_windows.append({
            "id": identifier,
            "start": _hex(start),
            "end": _hex(end),
            "size": end - start,
            "sha256": actual_hash,
        })
    native_cd_event_route = _native_cd_event_route(exe, fmv, pins)

    source_dependencies = {
        "analysis/phase4_fmv_interface_frontier.json": _sha256(INTERFACE_ARTIFACT),
        "analysis/phase4_fmv_static_owners.json": _sha256(STATIC_OWNER_ARTIFACT),
        "config/segments.yml": _sha256(SEGMENTS),
        "config/phase4_fmv_lifecycle_continuations.yaml": _sha256(CONFIG),
        "src/main/80039854_boot_subsystem_init.c":
            _sha256(MATCHING_POST_PLAYER_SOURCE),
        "src/main/8003e7c0_fmv_bin_load.c":
            _sha256(MATCHING_LOADER_SOURCE),
        "src/main/80045d5c_gp_set_one.c":
            _sha256(MATCHING_CD_EVENT_CALLBACK_SOURCE),
        "asm/hand_written/80045d6c_cd_subsystem_init.s":
            _sha256(CD_SUBSYSTEM_INIT_SOURCE),
        "src_re/fmv_lifecycle_continuations.c": _sha256(SEMANTIC_SOURCE),
        "tools/repro_inputs.sha256": _sha256(SOURCE_MANIFEST),
    }
    for row in owner_rows.values():
        source_dependencies[row["source"]] = row["sha256"]

    return {
        "schema": "abl-phase4-fmv-lifecycle-continuations/1",
        "generated": "2026-07-27",
        "row": "E15_fmv",
        "campaign": "fmv_playback",
        "lane": "static",
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "size": len(exe),
                "sha256": _sha256_bytes(exe),
                "identity_verified": verify_identity,
                "classification": "pristine_authority",
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{frontier.FMV_REL}",
                "size": len(fmv),
                "sha256": _sha256_bytes(fmv),
                "identity_verified": verify_identity,
                "classification": "pristine_authority",
            },
            "interface_frontier": {
                "path": "analysis/phase4_fmv_interface_frontier.json",
                "sha256": _sha256(INTERFACE_ARTIFACT),
            },
        },
        "continuations": continuation_rows,
        "loader_lifecycle": loader_lifecycle,
        "transient_player_continuations": {
            "completion_ownership": completion,
            "native_cd_event_route": native_cd_event_route,
            "exit_edges": [
                "0x800B7294", "0x800B7428", "0x800B7430",
                "0x800B7444", "0x800B745C",
            ],
            "common_teardown": {
                "start": "0x800B7464",
                "cd_pause_command": {"site": "0x800B7464", "value": "0x0B"},
                "st_clear_ring_call": "0x800B749C",
                "callback_teardown_call": "0x800B74A4",
                "return": "0x800B7524",
                "all_player_exit_edges_converge": True,
            },
            "exceptional_paths": exceptional["paths"],
            "windows": player_windows,
            "static_routing_closed": True,
            "native_outcomes_claimed": False,
        },
        "owner_sources": list(owner_rows.values()),
        "static_partition": {
            "closed": [
                "all nine resident fmv_bin_load return PCs",
                "sequential boot repeat ownership",
                "unconditional per-invocation FMV.BIN reload",
                "post-player display reinitialization and caller-owned Region-B replacement",
                "bonus-loop return-state writer",
                "game-over scene continuation",
                "level C and D finale continuations",
                "completed-level-B progress scan",
                "full level-A reset and scene-load continuation",
                "native CD event registration-to-player exit routing",
            ],
            "non_intersecting_residuals": {
                "E15_lifecycle_runtime": [
                    "native event delivery and frequency",
                    "Pause/stop command result and user-visible failure outcome",
                    "decode timeout and malformed-stream outcomes",
                ],
                "E15_campaign_breadth": [
                    "unobserved manifest selectors and remaining level variants",
                ],
                "C17_E14_adjacent_policy": [
                    "movie-viewer selection, return policy, unlock and persistence",
                ],
                "E12_adjacent_policy": ["FMV audio presentation policy"],
            },
            "runtime_outcomes_claimed": False,
            "viewer_policy_claimed": False,
        },
        "summary": {
            "direct_loader_calls": len(observed_calls),
            "classified_continuations": len(continuation_rows),
            "unclassified_continuations": 0,
            "owner_sources": len(owner_rows),
            "families": len({row["family"] for row in continuation_rows}),
            "window_bytes": sum(row["window"]["size"] for row in continuation_rows),
            "direct_calls_inside_windows": sum(
                len(row["direct_calls"]) for row in continuation_rows),
            "transient_player_windows": len(player_windows),
            "exceptional_path_categories": len(exceptional["paths"]),
            "loader_direct_calls": loader_lifecycle[
                "summary"]["ordered_direct_calls"],
            "unclassified_repeat_reload_retirement_owners":
                loader_lifecycle["summary"][
                    "unclassified_repeat_reload_retirement_owners"],
            "native_cd_event_static_edges":
                len(native_cd_event_route["static_edges"]),
            "resident_cd_event_field_gp_xrefs":
                len(native_cd_event_route["resident_field_xrefs"]),
            "unclassified_native_cd_event_static_edges":
                native_cd_event_route["unclassified_static_edges"],
        },
        "dimension_boundary": {
            "dimension": "lifecycle",
            "claim": "partial",
            "closed_sub_boundary": "resident_post_fmv_continuation_ownership",
            "closed_sub_boundaries": [
                "resident_post_fmv_continuation_ownership",
                "per_invocation_reload_and_retirement_ownership",
                "native_cd_event_to_pause_teardown_routing",
            ],
            "confidence": "confirmed",
            "next_missing_fact": (
                "one same-anchor native control that observes the exact "
                "value-1 consumer interface reach CdControl(0x0B) and common "
                "teardown before caller-owned Region-B replacement"),
        },
        "claims": {
            "confirmed": [
                "Every direct resident FMV consumer has one byte-exact return continuation inside a hash-pinned pristine owner.",
                "The three boot movies form one sequential synchronous owner before the shell dispatch.",
                "Level and game-over continuations have exact transition callees, arguments, stores or progress-scan predicates.",
                "The level-A continuation remains inside its true owner through all 20 post-FMV direct calls.",
                "Every fmv_bin_load invocation unconditionally recopies FMV.BIN to Region B before the synchronous player call.",
                "The loader does not explicitly unload or clear Region B; after common teardown and display reinitialization, replacement belongs to the classified resident caller continuation or a later Region-B loader.",
                "cd_subsystem_init registers callback 0x80045D5C for exact event class 0xF0000003/spec 0x8000; the callback stores value 1 at 0x80082484, and the FMV player routes that exact value to CdControl(0x0B) and common teardown.",
            ],
            "not_claimed": [
                "Static routing does not establish native event delivery or frequency, the Pause command result, or a user-visible media-failure outcome.",
                "Bonus playback does not establish movie-viewer selection, return, unlock or persistence policy.",
                "This static sub-boundary does not promote the complete lifecycle dimension.",
            ],
        },
        "source_dependencies": dict(sorted(source_dependencies.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4_fmv_lifecycle_continuations.json is stale")
    if not args.write and not args.check:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
