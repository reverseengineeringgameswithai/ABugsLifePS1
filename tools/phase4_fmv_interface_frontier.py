#!/usr/bin/env python3
"""Reconstruct the E15 FMV callback and synchronous-consumer frontier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from build_identity import verify_staged_input
import exe_read


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_interface_frontier.json"
EXE_REL = "SCUS_942.88"
FMV_REL = "FMV/FMV.BIN"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
SOURCE_MANIFEST = ROOT / "tools/repro_inputs.sha256"
PHASE3_CALLBACKS = ROOT / "analysis/phase3_jalr_callbacks.json"
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
EXE_END = 0x80082800
FMV_BASE = 0x800B5788


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _slice(data: bytes, start: int, end: int, *, base: int, header: int) -> bytes:
    first = header + start - base
    last = header + end - base
    if first < header or last > len(data) or first >= last:
        raise SystemExit(f"invalid slice {_hex(start)}..{_hex(end)}")
    return data[first:last]


def _word(data: bytes, pc: int, *, base: int, header: int) -> int:
    return struct.unpack("<I", _slice(data, pc, pc + 4, base=base, header=header))[0]


def _instruction(data: bytes, pc: int, *, base: int, header: int) -> dict[str, Any]:
    word = _word(data, pc, base=base, header=header)
    return {
        "pc": _hex(pc),
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(pc, word),
    }


def _require_words(data: bytes, expected: dict[int, int], *, base: int,
                   header: int, label: str) -> list[dict[str, Any]]:
    rows = []
    for pc, expected_word in sorted(expected.items()):
        actual = _word(data, pc, base=base, header=header)
        if actual != expected_word:
            raise SystemExit(
                f"{label} opcode drifted at {_hex(pc)}: "
                f"expected 0x{expected_word:08X}, observed 0x{actual:08X}")
        rows.append(_instruction(data, pc, base=base, header=header))
    return rows


def _jal_target(pc: int, word: int) -> int | None:
    if word >> 26 != 3:
        return None
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def _jal_sites(data: bytes, target: int, *, base: int, header: int,
               end: int) -> list[int]:
    return [
        pc for pc in range(base, end, 4)
        if _jal_target(pc, _word(data, pc, base=base, header=header)) == target
    ]


EXPECTED_CENSUS = {
    0x8006DCF0: [
        0x80070084, 0x800700A8, 0x80070290, 0x800703A0, 0x80070428,
        0x80070590, 0x80070670, 0x80070744, 0x800708F0, 0x800709E8,
    ],
    0x8006D8D0: [
        0x80039944, 0x80045FA4, 0x8006D658, 0x80070268, 0x80070378,
        0x80070404, 0x80070568, 0x8007064C, 0x8007071C, 0x80070900,
        0x800709F0,
    ],
    0x80070D80: [0x80070934],
    0x80070A30: [0x800716D8],
    0x8007094C: [0x8006D3BC],
}


CALLBACK_FUNCTIONS = {
    "StSetRing": (0x8006D3A4, 0x8006D3D4, "src/main/8006d3a4_StSetRing.c", "semantic_c"),
    "CdReadyCallback": (0x8006D8D0, 0x8006D8E8, "src/main/8006d8d0_CdReadyCallback.c", "matching_c"),
    "CdDataCallback": (0x8006DCF0, 0x8006DD14, "src/main/8006dcf0_CdDataCallback.c", "semantic_c"),
    "CdRead2": (0x80070898, 0x8007092C, "src/main/80070898_CdRead2.c", "semantic_c"),
    "StCdInterrupt2": (0x8007092C, 0x8007094C, "src/main/8007092c_StCdInterrupt2.c", "semantic_c"),
    "StClearRing": (0x8007094C, 0x800709AC, "src/main/8007094c_StClearRing.c", "semantic_c"),
    "callback_teardown": (0x800709AC, 0x80070A30, "src/main/800709ac_sub_800709ac.c", "semantic_c"),
    "str_data_ready_callback": (0x80070A30, 0x80070AC0, "asm/hand_written/80070a30_data_ready_callback.s", "handwritten_asm"),
    "StSetStream": (0x80070B20, 0x80070BA8, "src/main/80070b20_StSetStream.c", "semantic_c"),
    "stream_config_store": (0x80070D60, 0x80070D80, "src/main/80070d60_stream_config_store.c", "semantic_c"),
    "StCdInterrupt": (0x80070D80, 0x800716F0, "asm/hand_written/80070d80_StCdInterrupt.s", "handwritten_asm"),
}


CALLBACK_SOURCE_PARTS = {
    # config/segments.yml splits the body reached after the 0x80070A30 entry.
    # Validate the part as well as the entry source so an exact subrange cannot
    # disappear behind the enclosing function's stable bounds.
    "asm/hand_written/80070a40_fmv_frame_counter_setter.s": "handwritten_asm",
}


EXPECTED_CALLBACK_WORDS = {
    # CdRead2 installs fixed data-ready and ready wrappers.
    0x800708E8: 0x3C048007,
    0x800708EC: 0x24840A30,
    0x800708F0: 0x0C01B73C,
    0x800708F8: 0x3C048007,
    0x800708FC: 0x2484092C,
    0x80070900: 0x0C01B634,
    # Wrapper and interrupt handler delivery.
    0x80070934: 0x0C01C360,
    0x800716D8: 0x0C01C28C,
    # Callback teardown clears both SDK entry points in the critical section.
    0x800709B4: 0x0C0197EF,
    0x800709E8: 0x0C01B73C,
    0x800709EC: 0x00002021,
    0x800709F0: 0x0C01B634,
    0x800709F4: 0x00002021,
    0x80070A18: 0x0C0197F3,
    # Optional libpress callback slot and guarded indirect call.
    0x80070A84: 0x8C8410F0,
    0x80070A98: 0x10800003,
    0x80070AA0: 0x0080F809,
    # StSetStream stores a3 in the optional callback slot.
    0x80070B30: 0x00E08821,
    0x80070B58: 0xAC3110F0,
    # Its fifth stack argument is independently loaded and stored in the second
    # optional slot.  StCdInterrupt guards both delivery sites through it.
    0x80070B38: 0x8FB20030,
    0x80070B88: 0xAC3210F4,
    0x800712C4: 0x8C6310F4,
    0x800712D4: 0x10600003,
    0x800712DC: 0x0060F809,
    0x80071370: 0x8C6310F4,
    0x80071380: 0x10600003,
    0x80071388: 0x0060F809,
}


EXPECTED_PLAYER_WORDS = {
    # Ring and stream setup.  a3 and stack arg5 are both zero.
    0x800B6F9C: 0x0C01B4E9,
    0x800B6FA0: 0x24050020,
    0x800B6FA4: 0x24050001,
    0x800B6FA8: 0x3C060FFF,
    0x800B6FAC: 0x34C6FFFF,
    0x800B6FB8: 0x00003821,
    0x800B6FBC: 0xAFA00010,
    0x800B6FC4: 0x0C01C2C8,
    0x800B6FC8: 0x2C840001,
    # GetlocP and CdRead2 are retried until accepted; mode is 0x1c0.
    0x800B703C: 0x0C01B63A,
    0x800B7044: 0x1040FFFB,
    0x800B704C: 0x0C01C226,
    0x800B7050: 0x240401C0,
    0x800B7054: 0x1040FFFD,
    # All player exits converge on stop/ring/callback teardown.
    0x800B7294: 0x10540073,
    0x800B7428: 0x1054000E,
    0x800B7430: 0x1237000C,
    0x800B7444: 0x1054FE7C,
    0x800B745C: 0x1440FF20,
    0x800B7464: 0x2404000B,
    0x800B749C: 0x0C01C253,
    0x800B74A4: 0x0C01C26B,
    # File-open failure, no-record stop, and finite decode-timeout paths.
    0x800B6DE8: 0x12020018,
    0x800B6E4C: 0x3C04800B,
    0x800B6E50: 0x24845BA4,
    0x800B6C40: 0x1220000E,
    0x800B6C84: 0xA0229A54,
    0x800B6CBC: 0x3C020080,
    0x800B6CE8: 0x14400014,
    0x800B6CF4: 0x24845B80,
    0x800B6CF8: 0x0C01859A,
}


CONSUMERS = [
    (0x8004FB5C, "boot_dlogo", "constant_1", 0, "main_shell_state_machine", 0x8004FB64, "next synchronous boot movie"),
    (0x8004FB68, "boot_title", "constant_0", 0, "main_shell_state_machine", 0x8004FB70, "next synchronous boot movie"),
    (0x8004FB74, "boot_intro", "constant_45", 0, "main_shell_state_machine", 0x8004FB7C, "shell transition selection"),
    (0x8004FFD4, "bonus_clip_sequence", "bonus_cursor_plus_42", -1, "scene_flow_dispatcher", 0x8004FFDC, "publish scene-flow state and continue bonus loop"),
    (0x800500D8, "game_over_lose", "constant_46", 0, "scene_flow_dispatcher", 0x800500E0, "scene_setup_and_load(5, 64)"),
    (0x80050284, "finale_lev15c", "constant_40", 0, "scene_flow_dispatcher", 0x8005028C, "level_transition_orchestrator(0)"),
    (0x8005031C, "completed_level_b", "level_b_table", -1, "fmv_sequence_completion_check", 0x80050324, "resume completion/progress scan"),
    (0x8005036C, "all_levels_complete_lev15d", "constant_41", -1, "fmv_sequence_completion_check", 0x80050374, "publish shell transition value one and return"),
    (0x8005B788, "level_a_reset_handoff", "level_a_table", 0, "gameplay_state_reset_cursor_seed", 0x8005B790, "clear transition fields then resume scene load"),
]


EXPECTED_CONSUMER_WORDS = {
    0x8004FB58: 0x24040001,
    0x8004FB5C: 0x0C00F9F0, 0x8004FB60: 0x00002821,
    0x8004FB64: 0x00002021,
    0x8004FB68: 0x0C00F9F0, 0x8004FB6C: 0x00002821,
    0x8004FB70: 0x2404002D,
    0x8004FB74: 0x0C00F9F0, 0x8004FB78: 0x00002821,
    0x8004FF9C: 0x2405FFFF, 0x8004FFAC: 0x90C6B88A,
    0x8004FFB4: 0x24C60001, 0x8004FFB8: 0x30C400FF,
    0x8004FFD4: 0x0C00F9F0, 0x8004FFD8: 0x24840029,
    0x8004FFDC: 0xAF90064C,
    0x800500D4: 0x2404002E,
    0x800500D8: 0x0C00F9F0, 0x800500DC: 0x00002821,
    0x800500E4: 0x0C0140E3,
    0x80050280: 0x24040028,
    0x80050284: 0x0C00F9F0, 0x80050288: 0x00002821,
    0x8005028C: 0x0C01488B,
    0x80050318: 0x90247FE3,
    0x8005031C: 0x0C00F9F0, 0x80050320: 0x2405FFFF,
    0x80050324: 0x00002021,
    0x80050354: 0x24040029, 0x80050364: 0x2405FFFF,
    0x8005036C: 0x0C00F9F0, 0x80050370: 0xA0620000,
    0x80050378: 0xAF82064C,
    0x8005B784: 0x9024A08B,
    0x8005B788: 0x0C00F9F0, 0x8005B78C: 0x00002821,
    0x8005B794: 0xA4202388, 0x8005B79C: 0xA4202494,
    0x8005B7A4: 0xA4202430, 0x8005B7A8: 0x0C00E51E,
}


EXPECTED_LOADER_WORDS = {
    # a1 is retained as a value in s0, tested only for zero, and passed to
    # fixed pre/post routines.  There is no indirect call through the value.
    0x8003E7D8: 0x00A08021,
    0x8003E7DC: 0x12000003,
    0x8003E7E0: 0x02002021,
    0x8003E7E4: 0x0C016D10,
    0x8003E804: 0x12000003,
    0x8003E808: 0x02002021,
    0x8003E80C: 0x0C016D39,
    # The selector/player dispatch is synchronous and returns before the
    # resident post-playback initialization call.
    0x8003E814: 0x0C02D894,
    0x8003E818: 0x02202021,
    0x8003E81C: 0x0C00E615,
}


CALLER_REGIONS = {
    "main_shell_state_machine": (0x8004FA40, 0x8004FC3C, "asm/hand_written/8004fa40_main_shell_state_machine.s"),
    "scene_flow_set_substate_1": (0x8004FC3C, 0x8004FC50, "asm/hand_written/8004fc3c_sub_8004fc3c.s"),
    "scene_flow_set_substate_11": (0x8004FC50, 0x8004FC64, "asm/hand_written/8004fc50_sub_8004fc50.s"),
    "scene_flow_set_substate_2": (0x8004FC64, 0x8004FC78, "asm/hand_written/8004fc64_sub_8004fc64.s"),
    "scene_flow_set_substate_7": (0x8004FC78, 0x8004FC8C, "asm/hand_written/8004fc78_sub_8004fc78.s"),
    "scene_flow_set_substate_12": (0x8004FC8C, 0x8004FCA0, "asm/hand_written/8004fc8c_sub_8004fc8c.s"),
    "scene_flow_dispatcher": (0x8004FCA0, 0x800502C4, "asm/hand_written/8004fca0_scene_flow_dispatcher.s"),
    "fmv_sequence_completion_check": (0x800502C4, 0x8005038C, "asm/hand_written/800502c4_sub_800502c4.s"),
    "gameplay_state_reset_cursor_seed": (0x8005B714, 0x8005BC64, "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s"),
}


MAIN_SHELL_DISPATCH_WORDS = {
    0x8004FC0C: 0x3C038008,
    0x8004FC10: 0x8C63243C,
    0x8004FC18: 0x2C620006,
    0x8004FC1C: 0x10400028,
    0x8004FC20: 0x00031080,
    0x8004FC24: 0x3C018002,
    0x8004FC28: 0x00220821,
    0x8004FC2C: 0x8C22B3C4,
    0x8004FC34: 0x00400008,
    0x8004FC3C: 0x24020001,
    0x8004FC44: 0xA422245C,
    0x8004FC48: 0x08013F30,
    0x8004FC50: 0x2402000B,
    0x8004FC58: 0xA422245C,
    0x8004FC5C: 0x08013F30,
    0x8004FC64: 0x24020002,
    0x8004FC6C: 0xA422245C,
    0x8004FC70: 0x08013F30,
    0x8004FC78: 0x24020007,
    0x8004FC80: 0xA422245C,
    0x8004FC84: 0x08013F30,
    0x8004FC8C: 0x2402000C,
    0x8004FC94: 0xA422245C,
    0x8004FC98: 0x08013F30,
    0x8004FCA4: 0xAC20243C,
    0x8004FCA8: 0x0C01488B,
    0x8004FCAC: 0x24040001,
    0x8004FCB4: 0xA42223A0,
    0x8004FCB8: 0x08013ECF,
    # The five destination fragments join here, then resolve the stored index
    # through the scene table and publish the resulting scene.
    0x8004FCC0: 0x3C028008,
    0x8004FCF0: 0x8442245C,
    0x8004FCF8: 0x00021080,
    0x8004FCFC: 0x3C018007,
    0x8004FD00: 0x00220821,
    0x8004FD04: 0x8C227FA0,
    0x8004FD08: 0x3C018008,
    0x8004FD0C: 0xAC222504,
}


MAIN_SHELL_DISPATCH_TARGETS = (
    (0, 0x8004FC3C, 1, 1, "scene_flow_set_substate_1"),
    (1, 0x8004FC50, 11, 12, "scene_flow_set_substate_11"),
    (2, 0x8004FC64, 2, 3, "scene_flow_set_substate_2"),
    (3, 0x8004FC78, 7, 4, "scene_flow_set_substate_7"),
    (4, 0x8004FC8C, 12, 13, "scene_flow_set_substate_12"),
    (5, 0x8004FCA0, None, None, "scene_flow_dispatcher"),
)
MAIN_SHELL_DISPATCH_TABLE = 0x8001B3C4
SCENE_TABLE = 0x80077FA0


# The level-A loader call returns at 0x8005B790, but that is not the end of its
# owner.  The same function performs the display/scene/resource/player reset and
# returns only at 0x8005BC64.  Keep every direct edge in that continuation
# explicit so a call can neither disappear nor be introduced behind a stable
# function-slice hash.
LEVEL_A_CONTINUATION_CALLS = {
    0x8005B7A8: (0x80039478, "display_buffers_init"),
    0x8005B7CC: (0x8003F358, "scene_load_init"),
    0x8005B7F0: (0x80054AAC, "loadscreen_color_store"),
    0x8005B7F8: (0x8003F2F0, "wait_for_frame_sync"),
    0x8005B800: (0x80054AD4, "loadscreen_state_update"),
    0x8005B818: (0x80025F54, "loadscreen_glyph_draw"),
    0x8005B820: (0x80026D78, "loadscreen_primitive_queue"),
    0x8005B830: (0x8003CF2C, "resource_id_dat_load_dispatch"),
    0x8005B848: (0x8005B4E4, "post_load_transition_hook"),
    0x8005B978: (0x8005F7AC, "clear_reset_block_16_a"),
    0x8005B98C: (0x8005F7AC, "clear_reset_block_16_b"),
    0x8005B9A0: (0x8005F7AC, "clear_reset_block_160"),
    0x8005BAA4: (0x80046B20, "level_load_player_spawn_write"),
    0x8005BAB4: (0x8004DC0C, "respawn_collision_reset"),
    0x8005BABC: (0x80057404, "gameplay_pool_reset"),
    0x8005BAC4: (0x8005BC64, "plant_slot_respawn_scan"),
    0x8005BACC: (0x80054810, "scene_verb_dispatch"),
    0x8005BAE8: (0x8003E760, "token_descriptor_reskin"),
    0x8005BB08: (0x8005F4EC, "actor_slot_field_reset"),
    0x8005BC38: (0x80046AE8, "music_play_looping"),
}


def _manifest_pins() -> dict[str, str]:
    pins = {}
    for line in SOURCE_MANIFEST.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].startswith("asm/hand_written/"):
            pins[fields[1]] = fields[0]
    return pins


def _validate_sources() -> list[dict[str, Any]]:
    """Validate every cited source, including externally provisioned exact ASM."""
    pins = _manifest_pins()
    specs = {
        source: status
        for _, (_, _, source, status) in CALLBACK_FUNCTIONS.items()
    }
    specs.update(CALLBACK_SOURCE_PARTS)
    specs.update({source: "handwritten_asm" for _, (_, _, source) in CALLER_REGIONS.items()})
    rows = []
    for source, status in sorted(specs.items()):
        path = ROOT / source
        if not path.is_file():
            raise SystemExit(f"declared FMV frontier source is missing: {source}")
        actual = _sha256(path)
        if source.startswith("asm/hand_written/"):
            expected = pins.get(source)
            if expected is None:
                raise SystemExit(f"FMV frontier ASM source lacks a central pin: {source}")
            if actual != expected:
                raise SystemExit(f"FMV frontier ASM source pin drifted: {source}")
            retention = "external_local_media; tools/repro_inputs.sha256; hash-verified provisioning"
        else:
            expected = actual
            retention = "tracked_repository_source"
        rows.append({
            "path": source,
            "sha256": actual,
            "expected_sha256": expected,
            "source_status": status,
            "retention": retention,
            "validated": True,
        })
    return rows


def _function_rows(exe: bytes) -> list[dict[str, Any]]:
    rows = []
    for name, (start, end, source, status) in CALLBACK_FUNCTIONS.items():
        payload = _slice(exe, start, end, base=EXE_BASE, header=EXE_HEADER)
        rows.append({
            "name": name, "start": _hex(start), "end": _hex(end),
            "size": end - start, "sha256": _sha256_bytes(payload),
            "source": source, "source_sha256": _sha256(ROOT / source),
            "source_status": status,
        })
    return rows


def _callback_census(exe: bytes) -> dict[str, Any]:
    rows = {}
    for target, expected in EXPECTED_CENSUS.items():
        actual = _jal_sites(exe, target, base=EXE_BASE, header=EXE_HEADER,
                            end=EXE_END)
        if actual != expected:
            raise SystemExit(
                f"callback JAL census drifted for {_hex(target)}: "
                f"expected {[ _hex(x) for x in expected ]}, "
                f"observed {[ _hex(x) for x in actual ]}")
        rows[_hex(target)] = {
            "direct_call_count": len(actual),
            "call_sites": [_hex(pc) for pc in actual],
        }
    return rows


def _phase3_callback_crosscheck() -> dict[str, Any]:
    document = json.loads(PHASE3_CALLBACKS.read_text())
    expected = {
        "0x80070AA0": {
            "class": "global_slot", "function": "str_data_ready_callback",
            "slot": "0x800910F0",
        },
        "0x800712DC": {
            "class": "global_slot", "function": "StCdInterrupt",
            "slot": "0x800910F4",
        },
        "0x80071388": {
            "class": "global_slot", "function": "StCdInterrupt",
            "slot": "0x800910F4",
        },
    }
    sites = document.get("sites") or {}
    for pc, row in expected.items():
        if sites.get(pc) != row:
            raise SystemExit(f"Phase-3 callback classification drifted at {pc}")
    return {
        "artifact": "analysis/phase3_jalr_callbacks.json",
        "sha256": _sha256(PHASE3_CALLBACKS),
        "sites": expected,
    }


def _callback_lifecycle(exe: bytes, fmv: bytes) -> dict[str, Any]:
    callback_ops = _require_words(
        exe, EXPECTED_CALLBACK_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="callback lifecycle")
    player_ops = _require_words(
        fmv, EXPECTED_PLAYER_WORDS, base=FMV_BASE, header=0,
        label="FMV player lifecycle")
    return {
        "functions": _function_rows(exe),
        "direct_jal_census": _callback_census(exe),
        "setup": {
            "ring_call": "0x800B6F9C", "ring_records": 32,
            "stream_call": "0x800B6FC4",
            "arguments": {
                "a0": "display_mode_equals_3", "a1": 1,
                "a2": "0x0FFFFFFF", "a3_optional_callback": 0,
                "stack_arg5": 0,
            },
            "optional_callback_slots": {
                "frame_ready": {
                    "address": "0x800910F0", "argument": "a3",
                    "store": "0x80070B58", "delivery_sites": ["0x80070AA0"],
                    "enabled_for_e15": False,
                },
                "sector_ready": {
                    "address": "0x800910F4", "argument": "stack_arg5",
                    "argument_load": "0x80070B38", "store": "0x80070B88",
                    "delivery_sites": ["0x800712DC", "0x80071388"],
                    "enabled_for_e15": False,
                },
            },
            "optional_callback_enabled_for_e15": False,
        },
        "installation": {
            "player_cdread2_call": "0x800B704C",
            "mode": "0x000001C0",
            "data_callback_install": {
                "site": "0x800708F0", "api": "CdDataCallback",
                "handler": "0x80070A30",
            },
            "ready_callback_install": {
                "site": "0x80070900", "api": "CdReadyCallback",
                "handler": "0x8007092C",
            },
            "ready_wrapper_target": "0x80070D80",
            "interrupt_delivery_to_data_handler": "0x800716D8",
        },
        "teardown": {
            "common_player_range": "0x800B7464..0x800B752C",
            "ring_clear_call": "0x800B749C",
            "callback_clear_call": "0x800B74A4",
            "critical_section_range": "0x800709AC..0x80070A30",
            "default_backend_clears": ["0x800709E8", "0x800709F0"],
            "alternate_backend_clears": ["0x800709D0", "0x800709D8"],
            "post_clear_flag_pointers": ["0x80081C28", "0x80081C34"],
            "all_player_exit_edges_converge": True,
        },
        "exact_instructions": callback_ops + player_ops,
        "phase3_callback_crosscheck": _phase3_callback_crosscheck(),
    }


def _main_shell_dispatch(exe: bytes) -> dict[str, Any]:
    instructions = _require_words(
        exe, MAIN_SHELL_DISPATCH_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="main-shell dispatch")
    observed_targets = [
        _word(exe, MAIN_SHELL_DISPATCH_TABLE + index * 4,
              base=EXE_BASE, header=EXE_HEADER)
        for index in range(len(MAIN_SHELL_DISPATCH_TARGETS))
    ]
    expected_targets = [row[1] for row in MAIN_SHELL_DISPATCH_TARGETS]
    if observed_targets != expected_targets:
        raise SystemExit(
            "main-shell dispatch table drifted: "
            f"expected {[ _hex(value) for value in expected_targets ]}, "
            f"observed {[ _hex(value) for value in observed_targets ]}")
    entries = []
    for index, target, destination_index, expected_scene, owner in \
            MAIN_SHELL_DISPATCH_TARGETS:
        region = CALLER_REGIONS[owner]
        entry = {
            "index": index,
            "target": _hex(target),
            "owner": owner,
            "target_range": [_hex(region[0]), _hex(region[1])],
            "source": region[2],
            "source_sha256": _sha256(ROOT / region[2]),
        }
        if destination_index is None:
            entry["semantics"] = {
                "shell_substate_store": {"address": "0x8008243C", "value": 0},
                "orchestrator_call": {
                    "site": "0x8004FCA8", "target": "0x8005222C", "a0": 1},
                "master_state_store": "0x8004FCB4",
                "return_join": "0x8004FB3C",
            }
        else:
            observed_scene = _word(
                exe, SCENE_TABLE + destination_index * 4,
                base=EXE_BASE, header=EXE_HEADER)
            if observed_scene != expected_scene:
                raise SystemExit(
                    "main-shell downstream scene table drifted at index "
                    f"{destination_index}: expected {expected_scene}, "
                    f"observed {observed_scene}")
            entry["semantics"] = {
                "destination_index_store": {
                    "address": "0x8008245C", "value": destination_index},
                "resolved_scene": expected_scene,
                "scene_table": _hex(SCENE_TABLE),
                "return_join": "0x8004FCC0",
            }
        entries.append(entry)
    table_payload = _slice(
        exe, MAIN_SHELL_DISPATCH_TABLE,
        MAIN_SHELL_DISPATCH_TABLE + len(expected_targets) * 4,
        base=EXE_BASE, header=EXE_HEADER)
    return {
        "owner_range": ["0x8004FA40", "0x8004FC3C"],
        "selector": {"address": "0x8008243C", "guard": "unsigned_less_than_6"},
        "dispatch_site": "0x8004FC34",
        "table": {
            "address": _hex(MAIN_SHELL_DISPATCH_TABLE),
            "entries": len(entries),
            "sha256": _sha256_bytes(table_payload),
        },
        "targets": entries,
        "downstream_scene_resolution": {
            "shared_join": "0x8004FCC0",
            "destination_index_load": "0x8004FCF0",
            "scene_table": _hex(SCENE_TABLE),
            "scene_table_load": "0x8004FD04",
            "scene_store": {"site": "0x8004FD0C", "address": "0x80082504"},
        },
        "boot_return_dispatch_join": {
            "loader_return_pcs": ["0x8004FB64", "0x8004FB70", "0x8004FB7C"],
            "owner_range": ["0x8004FA40", "0x8004FC3C"],
            "dispatch_site": "0x8004FC34",
            "target_count": len(entries),
        },
        "exact_instructions": instructions,
    }


def _consumer_frontier(exe: bytes) -> dict[str, Any]:
    expected_calls = [row[0] for row in CONSUMERS]
    actual_calls = _jal_sites(
        exe, 0x8003E7C0, base=EXE_BASE, header=EXE_HEADER, end=EXE_END)
    if actual_calls != expected_calls:
        raise SystemExit(
            "FMV consumer JAL census drifted: "
            f"expected {[ _hex(x) for x in expected_calls ]}, "
            f"observed {[ _hex(x) for x in actual_calls ]}")
    instructions = _require_words(
        exe, EXPECTED_CONSUMER_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="FMV consumer")
    loader_instructions = _require_words(
        exe, EXPECTED_LOADER_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="FMV synchronous loader")
    continuation_start, continuation_end = 0x8005B790, 0x8005BC64
    continuation_sites = [
        pc for pc in range(continuation_start, continuation_end, 4)
        if _jal_target(pc, _word(exe, pc, base=EXE_BASE, header=EXE_HEADER))
        is not None
    ]
    if continuation_sites != list(LEVEL_A_CONTINUATION_CALLS):
        raise SystemExit(
            "level-A post-FMV continuation JAL census drifted: "
            f"expected {[ _hex(pc) for pc in LEVEL_A_CONTINUATION_CALLS ]}, "
            f"observed {[ _hex(pc) for pc in continuation_sites ]}")
    continuation_words = {
        pc: 0x0C000000 | ((target >> 2) & 0x03FFFFFF)
        for pc, (target, _) in LEVEL_A_CONTINUATION_CALLS.items()
    }
    continuation_instructions = _require_words(
        exe, continuation_words, base=EXE_BASE, header=EXE_HEADER,
        label="level-A post-FMV continuation")
    rows = []
    for call, owner, selector, hook, region, return_pc, continuation in CONSUMERS:
        rows.append({
            "owner": owner, "call": _instruction(
                exe, call, base=EXE_BASE, header=EXE_HEADER),
            "selector_source": selector, "hook_argument": hook,
            "hook_semantics": "fixed_pre_post_transition_enable",
            "caller_region": region, "return_pc": _hex(return_pc),
            "continuation": continuation,
        })
    regions = {}
    for name, (start, end, source) in CALLER_REGIONS.items():
        payload = _slice(exe, start, end, base=EXE_BASE, header=EXE_HEADER)
        regions[name] = {
            "start": _hex(start), "end": _hex(end), "size": end - start,
            "sha256": _sha256_bytes(payload), "source": source,
            "source_sha256": _sha256(ROOT / source),
            "source_status": "handwritten_asm",
        }
    loader_start, loader_end = 0x8003E7C0, 0x8003E83C
    loader = _slice(exe, loader_start, loader_end, base=EXE_BASE,
                    header=EXE_HEADER)
    shell_dispatch = _main_shell_dispatch(exe)
    return {
        "loader": {
            "start": _hex(loader_start), "end": _hex(loader_end),
            "size": loader_end - loader_start,
            "sha256": _sha256_bytes(loader),
            "source": "src/main/8003e7c0_fmv_bin_load.c",
            "source_status": "semantic_c",
            "call_contract": "synchronous selector dispatch and playback",
            "hook_contract": (
                "a1 is a zero/nonzero enable value passed to fixed pre/post "
                "transition routines; it is not an indirect callback target"),
        },
        "exhaustive_direct_call_count": len(rows),
        "calls": rows,
        "caller_regions": regions,
        "main_shell_dispatch": shell_dispatch,
        "level_a_post_fmv_continuation": {
            "start": _hex(continuation_start),
            "end": _hex(continuation_end),
            "function_start": "0x8005B714",
            "function_end": "0x8005BC64",
            "scene_load_call": "0x8005B7CC",
            "scene_load_target": "0x8003F358",
            "direct_call_count": len(continuation_sites),
            "direct_calls": [
                {
                    "pc": _hex(pc), "target": _hex(target), "role": role,
                    "instruction": _instruction(
                        exe, pc, base=EXE_BASE, header=EXE_HEADER),
                }
                for pc, (target, role) in LEVEL_A_CONTINUATION_CALLS.items()
            ],
            "source": "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s",
            "source_status": "handwritten_asm_external_hash_pinned",
            "source_sha256": _sha256(
                ROOT / "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s"),
        },
        "exact_instructions": (
            loader_instructions + instructions + continuation_instructions
            + shell_dispatch["exact_instructions"]),
        "ownership_partition": {
            "e15_interface": [
                "synchronous loader ABI", "selector source", "hook enable",
                "return continuation address",
            ],
            "adjacent_policy": {
                "C17_movie_viewer": "viewer selection and user-facing policy",
                "E14_persistence": "unlock/save persistence",
                "E16_overlay_loader": "generic Region-B replacement policy",
                "E12_audio": "audio presentation policy",
            },
            "viewer_semantics_inferred": False,
        },
    }


def _exceptional_frontier(fmv: bytes) -> dict[str, Any]:
    return {
        "paths": [
            {
                "id": "file_open_failure", "predicate_pc": "0x800B6DE8",
                "target": "0x800B6E4C", "diagnostic_pointer": "0x800B5BA4",
                "static_outcome": "prints File not found and continues initialization",
            },
            {
                "id": "decode_record_absent", "predicate_pc": "0x800B6C40",
                "target": "0x800B6C7C", "stop_latch_store": "0x800B6C84",
                "static_outcome": "sets u8 decode_stop_latch to one and returns -1",
            },
            {
                "id": "decode_poll_timeout", "budget_setup": "0x800B6CBC",
                "budget": "0x00800000", "diagnostic_call": "0x800B6CF8",
                "diagnostic_pointer": "0x800B5B80",
                "static_outcome": "publishes timeout fallback record fields",
            },
            {
                "id": "cd_submit_retry", "getlocp_branch": "0x800B7044",
                "read2_branch": "0x800B7054",
                "static_outcome": "retries each submission until nonzero",
            },
        ],
        "runtime_frequency_claimed": False,
        "malformed_media_behavior_claimed": False,
        "function_slices": [
            {
                "start": "0x800B6C24", "end": "0x800B6CA4", "size": 128,
                "sha256": _sha256_bytes(_slice(
                    fmv, 0x800B6C24, 0x800B6CA4, base=FMV_BASE, header=0)),
                "source_status": "exact_asm_slice_semantic_c_in_frontier",
            },
            {
                "start": "0x800B6CA4", "end": "0x800B6D68", "size": 196,
                "sha256": _sha256_bytes(_slice(
                    fmv, 0x800B6CA4, 0x800B6D68, base=FMV_BASE, header=0)),
                "source_status": "exact_asm_slice_semantic_c_in_frontier",
            },
        ],
    }


def build(*, exe_data: bytes | None = None, fmv_data: bytes | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(FMV_REL, fmv)
    source_validation = _validate_sources()
    lifecycle = _callback_lifecycle(exe, fmv)
    consumers = _consumer_frontier(exe)
    exceptional = _exceptional_frontier(fmv)
    return {
        "schema": "abl-phase4-fmv-interface-frontier/1",
        "generated": "2026-07-20",
        "row": "E15_fmv",
        "lane": "static",
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
                "sha256": _sha256_bytes(exe),
                "identity_verified": verify_identity,
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}", "size": len(fmv),
                "sha256": _sha256_bytes(fmv),
                "identity_verified": verify_identity,
            },
        },
        "callback_lifecycle": lifecycle,
        "resident_consumers": consumers,
        "exceptional_frontier": exceptional,
        "summary": {
            "callback_functions": len(lifecycle["functions"]),
            "callback_install_sites": 2,
            "callback_clear_sites": 2,
            "player_exit_edges": 5,
            "direct_resident_consumers": consumers["exhaustive_direct_call_count"],
            "consumer_continuations": len(consumers["calls"]),
            "level_a_continuation_direct_calls": consumers[
                "level_a_post_fmv_continuation"]["direct_call_count"],
            "main_shell_dispatch_targets": consumers[
                "main_shell_dispatch"]["table"]["entries"],
            "exceptional_paths": len(exceptional["paths"]),
            "validated_source_files": len(source_validation),
            "unclassified_callbacks": 0,
            "unclassified_direct_consumers": 0,
            "complete_frontier_intersections": 0,
        },
        "claims": {
            "confirmed": [
                "The fixed libcd/libpress callback installation, delivery and teardown chain is exact for E15.",
                "E15 stores zero in the optional StSetStream callback slot before CdRead2 installs the fixed handlers.",
                "E15 also stores zero in StSetStream's independent fifth-argument callback slot, disabling both guarded StCdInterrupt deliveries.",
                "All five player exit edges converge on one ring/callback teardown frontier.",
                "All nine direct synchronous resident consumers and their return continuations are exact.",
                "The level-A return continuation is bounded through the full 0x8005B714..0x8005BC64 owner and all 20 post-FMV direct call edges.",
                "The three boot return continuations remain inside 0x8004FA40..0x8004FC3C and reach the exact six-entry main-shell indirect dispatch with all target fragments and downstream stores partitioned.",
                "The four statically reachable exceptional categories have exact predicates, stores, diagnostics or retry edges.",
            ],
            "not_claimed": [
                "Static callback ownership does not establish runtime frequency, every-cycle attribution or malformed-media outcomes.",
                "The bonus selector interface does not establish movie-viewer or unlock policy.",
                "This artifact does not promote SDK-private record interiors into typed MOD state.",
            ],
        },
        "dimension_boundary": {
            "dimension": "complete_frontier",
            "claim": "met",
            "confidence": "confirmed",
            "low_level_basis": (
                "Exact pristine opcodes, exhaustive direct-call censuses, function "
                "bounds/slice hashes, source paths, callback slots, return "
                "continuations, the six-entry main-shell dispatch and target "
                "partitions, the full level-A transition owner, exhaustive "
                "post-FMV direct calls and exceptional branches leave no unclassified "
                "code owner intersecting E15's playback interface."),
            "non_intersecting_residuals": [
                "Runtime callback cadence, repeated playback, pause/stop and failure outcomes remain lifecycle debt.",
                "Thirty-six manifest entries without live controls remain campaign-breadth debt.",
                "Movie-viewer/unlock/persistence semantics remain C17/E14 policy debt.",
                "SDK-private record interiors remain typed-state/source debt outside E15's direct interface.",
            ],
        },
        "evidence_dependencies": {
            "analysis/phase4_fmv_static_owners.json": _sha256(
                ROOT / "analysis/phase4_fmv_static_owners.json"),
            "analysis/phase3_jalr_callbacks.json": _sha256(PHASE3_CALLBACKS),
        },
        "source_validation": {
            "manifest": "tools/repro_inputs.sha256",
            "manifest_sha256": _sha256(SOURCE_MANIFEST),
            "validated_files": source_validation,
            "all_validated": all(row["validated"] for row in source_validation),
        },
        "source_dependencies": {
            "config/phase4_fmv.yaml": _sha256(ROOT / "config/phase4_fmv.yaml"),
            "analysis/phase3_jalr_callbacks.json": _sha256(PHASE3_CALLBACKS),
            "src_re/fmv_callback_consumer_frontier.c": _sha256(
                ROOT / "src_re/fmv_callback_consumer_frontier.c"),
            "tools/phase4_fmv_interface_frontier.py": _sha256(Path(__file__)),
            "tools/repro_inputs.sha256": _sha256(SOURCE_MANIFEST),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    if args.check or not args.write:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 FMV interface-frontier artifact is stale")
    print(
        "[phase4-fmv-interface] 11 callback functions, 2 optional slots, "
        "2 installs, 2 clears, 9 direct consumers, 6 shell targets, "
        "4 exceptional categories verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
