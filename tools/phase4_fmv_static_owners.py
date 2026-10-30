#!/usr/bin/env python3
"""Reconstruct E15 selector dispatch and resident owners from pristine bytes.

This generator is deliberately static. It reads the hash-pinned staged SCUS,
MEMORY.BIN and FMV.BIN plus retained evidence identities, emits bounded
address/opcode/table metadata, and never launches DuckStation or consumes an
operator recording.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from build_identity import verify_staged_input
import exe_read
import fmv_frame_table


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_static_owners.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
MEMORY_REL = "BITS/MEMORY.BIN"
MEMORY_PATH = ROOT / "REBUILD/files" / MEMORY_REL
JALR_PATH = ROOT / "analysis/phase3_jalr_callbacks.json"
LEGACY_FMV_PATH = ROOT / "analysis/phase4_fmv.json"
LEGACY_FMV_SHA256 = "ae6b6baf0bec3c0e77649c714560c7425a3d0a8e95ab86cbc54d7cc9ab294a40"
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
EXE_TEXT_SIZE = 0x72800
FMV_BASE = 0x800B5788
FMV_CODE_END = 0x800B9A4C

DISPATCH_START = 0x800B6250
DISPATCH_END = 0x800B6634
SELECTOR_LIMIT_PC = 0x800B62A4
SELECTOR_JUMP_TABLE = 0x800B5AA4
NO_STREAM_TARGET = 0x800B6574
STREAM_START_CALL_PC = 0x800B656C
STREAM_START_TARGET = 0x800B6D68
RESIDENT_LOADER = 0x8003E7C0
PLAYER_END = 0x800B752C
COMPLETION_REQUEST = 0x800CAC10

PLAYER_FIELD_XREFS = {
    0x800B9A4C: [0x800B6B00, 0x800B6B08, 0x800B70B0, 0x800B7154,
                 0x800B71B4, 0x800B73D8, 0x800B7450],
    0x800B9A50: [0x800B6B14],
    0x800B9A54: [0x800B6C84, 0x800B728C],
    0x800B9A58: [0x800B6B54, 0x800B6BB8, 0x800B6BD0],
    0x800B9A5C: [0x800B6B6C, 0x800B6BC0, 0x800B6BE0],
    0x800CABD4: [0x800B6890, 0x800B6900, 0x800B6A5C, 0x800B6DC8],
    0x800CABE0: [0x800B6E80, 0x800B74CC],
    0x800CABE4: [0x800B6EA0, 0x800B74DC],
    0x800CABE8: [0x800B6EA8, 0x800B71D8],
    0x800CABEC: [0x800B6690, 0x800B6880, 0x800B6A08, 0x800B6EC8,
                 0x800B74EC],
    0x800CABF0: [0x800B6960, 0x800B6A40, 0x800B6F58, 0x800B72F4,
                 0x800B7350],
    0x800CABF2: [0x800B6A54, 0x800B6EE4, 0x800B72E8, 0x800B735C],
    0x800CABF4: [0x800B68BC, 0x800B696C, 0x800B6F30, 0x800B7300,
                 0x800B7368],
    0x800CABF6: [0x800B6EEC, 0x800B7310, 0x800B7374],
    0x800CABF8: [0x800B6F60],
    0x800CABFA: [0x800B6F00],
    0x800CABFC: [0x800B6F38],
    0x800CABFE: [0x800B6F08],
    0x800CAC00: [0x800B68A4, 0x800B6948, 0x800B6A28, 0x800B6ED4,
                 0x800B72D0],
    0x800CAC04: [0x800B6F68],
    0x800CAC06: [0x800B6A64, 0x800B6F10],
    0x800CAC08: [0x800B6678, 0x800B6988, 0x800B6F40],
    0x800CAC0A: [0x800B6680, 0x800B69DC, 0x800B6F18],
    0x800CAC0C: [0x800B6A34, 0x800B6EDC],
    0x800CAC10: [0x800B6B24, 0x800B6B48, 0x800B6DD0, 0x800B743C],
    0x800CAC18: [0x800B6E24],
    0x800CAC20: [0x800B66A4, 0x800B6D8C, 0x800B7144, 0x800B71D0],
    0x80131EE8: [0x800B6278, 0x800B6288, 0x800B6E64, 0x800B6E78,
                 0x800B6E90, 0x800B6F88],
    0x80131EEC: [0x800B663C, 0x800B68AC, 0x800B6930, 0x800B6990,
                 0x800B6BC8, 0x800B6DB8, 0x800B6E98, 0x800B6EBC,
                 0x800B6FB4, 0x800B6FDC, 0x800B71E0, 0x800B7200,
                 0x800B72BC, 0x800B7388],
    0x80131EEE: [0x800B6B2C, 0x800B6DC0],
}

PLAYER_FIELD_META = {
    0x800B9A4C: ("decoded_frame_index", "s32", "nonnegative decoder output; signed comparisons are exact"),
    0x800B9A50: ("previous_decoded_frame_index", "s32", "prior decoded-frame index copied before the current index is published; write-only in the exact FMV code extent"),
    0x800B9A54: ("decode_stop_latch", "u8", "0 continues; the sole writer publishes 1 on callback failure/retirement"),
    0x800B9A58: ("cached_frame_width", "u32", "zero-extended u16 decoder width; refreshed when the incoming dimensions change"),
    0x800B9A5C: ("cached_frame_height", "u32", "zero-extended u16 decoder height; its low halfword feeds the presentation rectangles"),
    0x800CABD4: ("presentation_active_latch", "u32", "boolean 0 or 1 from all exact writers"),
    0x800CABE0: ("allocated_block_0", "nullable pointer32", "allocation result; freed once in player teardown"),
    0x800CABE4: ("allocated_block_1", "nullable pointer32", "allocation result; freed once in player teardown"),
    0x800CABE8: ("active_block_index", "u32", "boolean 0 or 1; alias helper 0x800B6C24 toggles field +8"),
    0x800CABEC: ("allocated_presentation_block", "nullable pointer32", "allocation result; consumed by presentation helpers and freed once"),
    0x800CABF0: ("rect_bank_0_x", "s16", "signed RECT coordinate; slot 0 or 1 selected through an 8-byte stride"),
    0x800CABF2: ("rect_bank_0_y", "s16", "signed RECT coordinate; slot 0 or 1 selected through an 8-byte stride"),
    0x800CABF4: ("rect_bank_0_w", "s16", "signed RECT extent; slot 0 or 1 selected through an 8-byte stride"),
    0x800CABF6: ("rect_bank_0_h", "s16", "signed RECT extent; slot 0 or 1 selected through an 8-byte stride"),
    0x800CABF8: ("rect_bank_1_x", "s16", "second 8-byte RECT slot"),
    0x800CABFA: ("rect_bank_1_y", "s16", "second 8-byte RECT slot"),
    0x800CABFC: ("rect_bank_1_w", "s16", "second 8-byte RECT slot"),
    0x800CABFE: ("rect_bank_1_h", "s16", "second 8-byte RECT slot"),
    0x800CAC00: ("active_rect_index", "u32", "boolean 0 or 1; converted to an 8-byte RECT offset"),
    0x800CAC04: ("present_rect_x", "s16", "signed presentation RECT coordinate"),
    0x800CAC06: ("present_rect_y", "s16", "signed presentation RECT coordinate"),
    0x800CAC08: ("present_rect_w", "s16", "signed presentation RECT extent"),
    0x800CAC0A: ("present_rect_h", "s16", "signed presentation RECT extent"),
    0x800CAC0C: ("rect_ready_latch", "u32", "boolean 0 or 1 from both exact writers"),
    0x800CAC10: ("completion_request", "u32", "boolean 0 or 1; player exits only on exact value 1"),
    0x800CAC18: ("stream_open_result", "opaque u32", "return value retained by the player; no direct overlay reader"),
    0x800CAC20: ("presentation_counter", "u32", "0..7 select exact cases; values >=8 take the terminal/default path"),
    0x80131EE8: ("workspace_pointer", "pointer32", "fixed pristine value 0x800CAEE8 installed by selector dispatch"),
    0x80131EEC: ("display_mode", "s16", "caller supplied; exact value 3 selects the special geometry branch"),
    0x80131EEE: ("selected_frame_limit", "s16", "pristine manifest values 156..3162"),
}

# Direct absolute state accesses are exhaustive only inside these declared
# regions. Keeping the ranges separate from the field whitelist makes a new or
# previously omitted address fail closed instead of silently preserving an
# authored all_xrefs_verified claim.
PLAYER_STATE_RANGES = (
    (0x800B9A4C, 0x800B9A60, "decode_commit_scalars"),
    (0x800CABD4, 0x800CAC24, "player_boundary"),
    (0x80131EE8, 0x80131EF0, "selector_parameters"),
)

EXPECTED_COMPLETION_XREFS = {
    0x800B6B24: ("frame_order_regression_set", "write", "0xAC22AC10"),
    0x800B6B48: ("selected_limit_set", "write", "0xAC22AC10"),
    0x800B6DD0: ("stream_start_clear", "write", "0xAC20AC10"),
    0x800B743C: ("player_loop_exit_read", "read", "0x8C42AC10"),
}

LEVEL_A_TABLE = 0x8007A08B
LEVEL_B_TABLE = 0x80077FE3
MUSIC_ID_FIELD = 0x8008245C
BONUS_FLAGS_FIELD = 0x8009B889
BONUS_CURSOR_FIELD = 0x8009B88A

EXPECTED_CALL_SITES = {
    0x8004FB5C: ("boot_dlogo", "constant", 1, 0),
    0x8004FB68: ("boot_title", "constant", 0, 0),
    0x8004FB74: ("boot_intro", "constant", 45, 0),
    0x8004FFD4: ("bonus_clip_sequence", "cursor_plus_42", None, -1),
    0x800500D8: ("game_over_lose", "constant", 46, 0),
    0x80050284: ("finale_lev15c", "constant", 40, 0),
    0x8005031C: ("completed_level_b", "level_b_table", None, -1),
    0x8005036C: ("all_levels_complete_lev15d", "constant", 41, -1),
    0x8005B788: ("level_a_reset_handoff", "level_a_table", None, 0),
}

CALLER_REGIONS = {
    "main_shell_state_machine": (0x8004FA40, 0x8004FC3C),
    "scene_flow_dispatcher": (0x8004FCA0, 0x800502C4),
    "fmv_sequence_completion_check": (0x800502C4, 0x8005038C),
    "gameplay_state_reset_cursor_seed": (0x8005B714, 0x8005BC64),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _slice(data: bytes, address: int, size: int, *, base: int, header: int) -> bytes:
    offset = header + address - base
    if offset < header or offset + size > len(data):
        raise SystemExit(f"invalid slice 0x{address:08X}+0x{size:X}")
    return data[offset:offset + size]


def _word(data: bytes, address: int, *, base: int, header: int) -> int:
    return struct.unpack("<I", _slice(data, address, 4, base=base, header=header))[0]


def _hex(address: int) -> str:
    return f"0x{address:08X}"


def _instruction(data: bytes, address: int, *, base: int, header: int) -> dict[str, Any]:
    word = _word(data, address, base=base, header=header)
    return {
        "pc": _hex(address),
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(address, word),
    }


def _manifest_cases(fmv: bytes) -> tuple[list[dict[str, Any]], dict[int, int]]:
    movies = fmv_frame_table.manifest_movies(fmv)
    frame_rows = fmv_frame_table.frame_table(fmv)
    if len(movies) != 40 or len(frame_rows) != 40:
        raise SystemExit("FMV manifest/frame-table count is not 40/40")
    case_addresses = [0x800B62C8, 0x800B62D8, 0x800B62F4]
    case_addresses.extend(0x800B6310 + (index - 3) * 0x10
                          for index in range(3, 40))
    rows: list[dict[str, Any]] = []
    target_to_index: dict[int, int] = {}
    for index, ((offset, count), movie, case) in enumerate(
            zip(frame_rows, movies, case_addresses)):
        instruction = struct.unpack_from("<I", fmv, offset)[0]
        if instruction != 0x24050000 | count:
            raise SystemExit(f"frame-limit opcode drifted for manifest row {index}")
        rows.append({
            "manifest_index": index,
            "path": movie.replace("\\", "/"),
            "frame_count": count,
            "case_target": _hex(case),
            "frame_limit_pc": _hex(FMV_BASE + offset),
            "frame_limit_word": f"0x{instruction:08X}",
        })
        target_to_index[case] = index
    return rows, target_to_index


def _selector_dispatch(fmv: bytes, manifest: list[dict[str, Any]],
                       target_to_index: dict[int, int]) -> dict[str, Any]:
    limit = _instruction(fmv, SELECTOR_LIMIT_PC, base=FMV_BASE, header=0)
    if limit["word"] != "0x2E02002F":
        raise SystemExit("FMV selector upper-bound instruction drifted")
    table = _slice(fmv, SELECTOR_JUMP_TABLE, 47 * 4, base=FMV_BASE, header=0)
    targets = struct.unpack("<47I", table)
    selectors = []
    for selector, target in enumerate(targets):
        row: dict[str, Any] = {"selector": selector, "target": _hex(target)}
        if target == NO_STREAM_TARGET:
            row.update({"action": "no_stream", "manifest_index": None,
                        "path": None, "frame_count": None})
        elif target in target_to_index:
            manifest_row = manifest[target_to_index[target]]
            row.update({
                "action": "select_stream",
                "manifest_index": manifest_row["manifest_index"],
                "path": manifest_row["path"],
                "frame_count": manifest_row["frame_count"],
            })
        else:
            raise SystemExit(
                f"selector {selector} has unknown target 0x{target:08X}")
        selectors.append(row)
    stream_call = _instruction(
        fmv, STREAM_START_CALL_PC, base=FMV_BASE, header=0)
    expected_jal = 0x0C000000 | ((STREAM_START_TARGET >> 2) & 0x03FFFFFF)
    if int(stream_call["word"], 16) != expected_jal:
        raise SystemExit("FMV stream-start call drifted")
    return {
        "function": {
            "start": _hex(DISPATCH_START), "end": _hex(DISPATCH_END),
            "size": DISPATCH_END - DISPATCH_START,
            "sha256": _sha256_bytes(_slice(
                fmv, DISPATCH_START, DISPATCH_END - DISPATCH_START,
                base=FMV_BASE, header=0)),
        },
        "selector_domain": {
            "minimum": 0, "maximum": 46,
            "limit_instruction": limit,
            "out_of_range_target": _hex(NO_STREAM_TARGET),
        },
        "jump_table": {
            "address": _hex(SELECTOR_JUMP_TABLE),
            "entries": 47,
            "sha256": _sha256_bytes(table),
        },
        "stream_start_call": stream_call,
        "stream_start_target": _hex(STREAM_START_TARGET),
        "selectors": selectors,
    }


def _level_table(exe: bytes, *, name: str, address: int,
                 selector_rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = _slice(exe, address, 16, base=EXE_BASE, header=EXE_HEADER)
    rows = []
    for music_id, selector in enumerate(raw):
        resolved = selector_rows[selector] if selector < len(selector_rows) else None
        if music_id == 0 and name == "level_b":
            rows.append({
                "music_id": 0, "selector": selector, "action": "branch_skips_call",
                "path": None, "frame_count": None,
            })
        elif resolved is None or resolved["action"] != "select_stream":
            raise SystemExit(
                f"{name} table ID {music_id} has non-stream selector {selector}")
        else:
            rows.append({
                "music_id": music_id, "selector": selector,
                "action": "select_stream", "path": resolved["path"],
                "frame_count": resolved["frame_count"],
            })
    return {
        "name": name,
        "address": _hex(address),
        "index_field": _hex(MUSIC_ID_FIELD),
        "index_width": "s16 loaded then used as a byte-table index",
        "entries": rows,
        "sha256": _sha256_bytes(raw),
    }


def _resident_calls(exe: bytes) -> dict[str, Any]:
    expected_jal = 0x0C000000 | ((RESIDENT_LOADER >> 2) & 0x03FFFFFF)
    sites = []
    text = exe[EXE_HEADER:EXE_HEADER + EXE_TEXT_SIZE]
    for offset in range(0, len(text) - 3, 4):
        if struct.unpack_from("<I", text, offset)[0] == expected_jal:
            sites.append(EXE_BASE + offset)
    if set(sites) != set(EXPECTED_CALL_SITES):
        raise SystemExit(
            "resident fmv_bin_load JAL census drifted: "
            f"expected {[ _hex(v) for v in sorted(EXPECTED_CALL_SITES) ]}, "
            f"observed {[ _hex(v) for v in sites ]}")
    rows = []
    for site in sites:
        owner, source_kind, selector, hook_argument = EXPECTED_CALL_SITES[site]
        rows.append({
            "owner": owner,
            "call": _instruction(exe, site, base=EXE_BASE, header=EXE_HEADER),
            "delay_slot": _instruction(
                exe, site + 4, base=EXE_BASE, header=EXE_HEADER),
            "selector_source": source_kind,
            "constant_selector": selector,
            "hook_argument_a1": hook_argument,
        })
    regions = {}
    for name, (start, end) in CALLER_REGIONS.items():
        raw = _slice(exe, start, end - start, base=EXE_BASE, header=EXE_HEADER)
        regions[name] = {
            "start": _hex(start), "end": _hex(end), "size": end - start,
            "sha256": _sha256_bytes(raw),
        }
    return {
        "callee": _hex(RESIDENT_LOADER),
        "direct_jal_word": f"0x{expected_jal:08X}",
        "exhaustive_direct_call_count": len(rows),
        "calls": rows,
        "caller_regions": regions,
    }


def _bonus_cursor(exe: bytes, selectors: list[dict[str, Any]]) -> dict[str, Any]:
    reader = _instruction(exe, 0x8004FFAC, base=EXE_BASE, header=EXE_HEADER)
    writer = _instruction(exe, 0x8004FFD0, base=EXE_BASE, header=EXE_HEADER)
    if reader["word"] != "0x90C6B88A" or writer["word"] != "0xA026B88A":
        raise SystemExit("bonus clip cursor reader/writer drifted")
    outcomes = []
    for old_cursor in range(256):
        new_cursor = (old_cursor + 1) & 0xFF
        selector = new_cursor + 41
        selected = selectors[selector] if selector < len(selectors) else None
        outcomes.append({
            "old_cursor": old_cursor, "new_cursor": new_cursor,
            "selector": selector,
            "action": selected["action"] if selected else "out_of_range_no_stream",
            "path": selected["path"] if selected else None,
        })
    return {
        "address": _hex(BONUS_CURSOR_FIELD),
        "width": "u8",
        "readers": [reader],
        "writers": [writer],
        "expression": "selector = (((old_cursor + 1) & 0xFF) + 41)",
        "outcomes": outcomes,
        "streaming_old_cursor_values": [
            row["old_cursor"] for row in outcomes if row["path"] is not None],
        "bonus_flags_interaction": {
            "address": _hex(BONUS_FLAGS_FIELD),
            "operation": "replace byte with 17 * (old_value & 0x0F)",
            "read_pc": _hex(0x8004FFB0),
            "write_pc": _hex(0x8004FFC8),
        },
        "boundary": (
            "The byte has exactly one resident reader and writer in the static "
            "xref census. Its user-facing/movie-viewer meaning and any external "
            "initialization remain unclaimed."),
    }


def _direct_calls(data: bytes, start: int, end: int, *, base: int,
                  header: int) -> list[dict[str, Any]]:
    rows = []
    for pc in range(start, end, 4):
        word = _word(data, pc, base=base, header=header)
        if word >> 26 != 3:
            continue
        target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        rows.append({
            "call": _instruction(data, pc, base=base, header=header),
            "target": _hex(target),
            "target_residency": (
                "FMV.BIN" if FMV_BASE <= target < FMV_BASE + len(data)
                else "resident"),
        })
    return rows


MEMORY_OPS = {
    0x20: ("lb", "read", "u8", True),
    0x21: ("lh", "read", "u16", True),
    0x23: ("lw", "read", "u32", None),
    0x24: ("lbu", "read", "u8", False),
    0x25: ("lhu", "read", "u16", False),
    0x28: ("sb", "write", "u8", None),
    0x29: ("sh", "write", "u16", None),
    0x2B: ("sw", "write", "u32", None),
}


def _written_registers(word: int) -> set[int]:
    op = word >> 26
    if op == 0:
        function = word & 0x3F
        if function in (8, 12, 13):
            return set()
        return {(word >> 11) & 0x1F}
    if op == 3:
        return {31}
    if op in (2, 4, 5, 6, 7, 0x28, 0x29, 0x2A, 0x2B, 0x2E):
        return set()
    return {(word >> 16) & 0x1F}


def _resolved_memory_base(instructions: list[tuple[int, int]], index: int,
                          register: int) -> tuple[int, int | None] | None:
    """Resolve the compiler's local LUI or LUI+ADDU absolute-address idiom."""
    current = register
    for prior in range(index - 1, max(-1, index - 10), -1):
        _pc, word = instructions[prior]
        if current not in _written_registers(word):
            continue
        op = word >> 26
        if op == 0x0F and ((word >> 16) & 0x1F) == current:
            return (word & 0xFFFF) << 16, None
        if op == 0 and (word & 0x3F) in (0x20, 0x21):
            destination = (word >> 11) & 0x1F
            left = (word >> 21) & 0x1F
            right = (word >> 16) & 0x1F
            if destination != current or current not in (left, right):
                return None
            index_register = right if left == current else left
            for earlier in range(prior - 1, max(-1, prior - 8), -1):
                _earlier_pc, earlier_word = instructions[earlier]
                if current not in _written_registers(earlier_word):
                    continue
                if earlier_word >> 26 == 0x0F and \
                        ((earlier_word >> 16) & 0x1F) == current:
                    return (earlier_word & 0xFFFF) << 16, index_register
                return None
        return None
    return None


def _player_typed_state(fmv: bytes) -> dict[str, Any]:
    instructions = [
        (pc, _word(fmv, pc, base=FMV_BASE, header=0))
        for pc in range(FMV_BASE, FMV_CODE_END, 4)
    ]
    observed: dict[int, list[dict[str, Any]]] = {
        address: [] for address in PLAYER_FIELD_XREFS
    }
    unclassified = []
    for index, (pc, word) in enumerate(instructions):
        operation = MEMORY_OPS.get(word >> 26)
        if operation is None:
            continue
        base_register = (word >> 21) & 0x1F
        resolved = _resolved_memory_base(instructions, index, base_register)
        if resolved is None:
            continue
        base, index_register = resolved
        immediate = word & 0xFFFF
        immediate = immediate - 0x10000 if immediate & 0x8000 else immediate
        address = (base + immediate) & 0xFFFFFFFF
        region = next((name for start, end, name in PLAYER_STATE_RANGES
                       if start <= address < end), None)
        if region is None:
            continue
        mnemonic, access, width, signed = operation
        row = {
            "instruction": _instruction(
                fmv, pc, base=FMV_BASE, header=0),
            "access": access,
            "width": width,
            "signed_load": signed,
            "index_register": (
                None if index_register is None else index_register),
            "scope": (
                "player" if STREAM_START_TARGET <= pc < PLAYER_END
                else "other_fmv_code"),
        }
        if address not in observed:
            unclassified.append({
                "address": _hex(address), "region": region, **row})
        else:
            observed[address].append(row)

    if unclassified:
        rows = ", ".join(
            f"{row['address']}@{row['instruction']['pc']}"
            for row in unclassified)
        raise SystemExit(f"FMV unclassified typed-state xref(s): {rows}")

    fields = []
    for address, expected_pcs in PLAYER_FIELD_XREFS.items():
        rows = observed[address]
        actual_pcs = [int(row["instruction"]["pc"], 16) for row in rows]
        if actual_pcs != expected_pcs:
            raise SystemExit(
                f"FMV typed-state xref drift at {_hex(address)}: "
                f"expected {[ _hex(pc) for pc in expected_pcs ]}, "
                f"observed {[ _hex(pc) for pc in actual_pcs ]}")
        name, storage_type, valid_domain = PLAYER_FIELD_META[address]
        fields.append({
            "name": name,
            "address": _hex(address),
            "storage_type": storage_type,
            "residency": "FMV.BIN Region B",
            "valid_domain": valid_domain,
            "xrefs": rows,
            "xref_count": len(rows),
            "player_xref_count": sum(row["scope"] == "player" for row in rows),
        })

    alias_instructions = {
        0x800B6878: ("0x800CAC04", "present_rect pointer"),
        0x800B6928: ("0x800CAC04", "present_rect pointer"),
        0x800B6950: ("0x800CAC04", "present_rect pointer"),
        0x800B6E0C: ("0x800CABD0", "opaque libcd result buffer pointer"),
        0x800B7038: ("0x800CABD0", "CdControl(CdlGetlocP) result buffer pointer"),
        0x800B709C: ("0x800CABE0", "two-pointer plus active-index block"),
    }
    aliases = []
    for pc, (address, role) in alias_instructions.items():
        instruction = _instruction(fmv, pc, base=FMV_BASE, header=0)
        if not instruction["mnemonic"].startswith("addiu "):
            raise SystemExit(f"FMV typed-state alias instruction drift at {_hex(pc)}")
        aliases.append({"instruction": instruction, "address": address, "role": role})

    entry_abi = [
        {"source": "a1", "storage": "s2 then 0x80131EEE",
         "type": "s16", "role": "selected frame limit"},
        {"source": "a2", "storage": "0x80131EEC",
         "type": "s16", "role": "display mode"},
        {"source": "a3", "storage": "stack +0x08C0",
         "type": "u16", "role": "presentation width input"},
        {"source": "caller stack +0x10", "storage": "s8",
         "type": "u16", "role": "presentation height input"},
        {"source": "caller stack +0x14", "storage": "t0",
         "type": "u16", "role": "presentation auxiliary input"},
    ]
    return {
        "code_scope": {
            "start": _hex(FMV_BASE), "end": _hex(FMV_CODE_END),
            "sha256": _sha256_bytes(_slice(
                fmv, FMV_BASE, FMV_CODE_END - FMV_BASE,
                base=FMV_BASE, header=0)),
            "boundary": (
                "Executable FMV code ends at the jr-ra function ending at "
                "0x800B9A48; 0x800B9A4C begins the first typed state word."),
        },
        "player_function": {
            "start": _hex(STREAM_START_TARGET), "end": _hex(PLAYER_END),
            "entry_abi": entry_abi,
        },
        "fields": fields,
        "pointer_aliases": aliases,
        "structures": {
            "double_buffer": {
                "base": "0x800CABE0", "size": 12,
                "layout": ["pointer32 block[2]", "u32 active_index"],
                "alias_helper": "0x800B6C24..0x800B6CA4",
                "exact_behavior": (
                    "The helper reads field +8, toggles it as a boolean, "
                    "selects block[active_index], and publishes stop latch 1 "
                    "when its callback path returns no record."),
            },
            "rect_bank": {
                "base": "0x800CABF0", "slots": 2, "stride": 8,
                "fields": ["s16 x", "s16 y", "s16 w", "s16 h"],
            },
            "present_rect": {
                "base": "0x800CAC04", "size": 8,
                "fields": ["s16 x", "s16 y", "s16 w", "s16 h"],
            },
        },
        "resident_dependencies": [
            {"address": "0x80082218", "type": "s16", "player_read": "0x800B7088",
             "owner": "resident audio/presentation policy"},
            {"address": "0x80082412", "type": "u16", "player_read": "0x800B7404",
             "local_use": "mask 0x4008", "owner": "resident decoded input"},
            {"address": "0x80082484", "type": "u32", "player_read": "0x800B7420",
             "local_use": "exact value 1 requests exit", "owner": "resident shell"},
        ],
        "lifecycle": {
            "initialization": (
                "Selector dispatch installs workspace 0x800CAEE8. Player entry "
                "stores the signed mode/limit, clears completion, active index, "
                "rect-ready state and initializes both RECT slots."),
            "reuse": (
                "0x800B6C24 toggles only active_index and selects exactly one of "
                "two allocated block pointers."),
            "retirement": (
                "Player teardown stops CD/audio callbacks, frees the three "
                "allocation-result pointers at 0x800CABE0/0x800CABE4/0x800CABEC, "
                "then returns before Region B may be replaced."),
            "residency_rule": (
                "Every address in this table is valid only while the exact "
                "FMV.BIN head identity is resident."),
        },
        "summary": {
            "region_b_address_rows": len(fields),
            "absolute_xrefs": sum(len(row["xrefs"]) for row in fields),
            "player_xrefs": sum(row["player_xref_count"] for row in fields),
            "pointer_aliases": len(aliases),
            "enumerated_state_ranges": len(PLAYER_STATE_RANGES),
            "unclassified_xrefs": len(unclassified),
            "all_xrefs_verified": True,
        },
        "boundary": (
            "This exhaustively types direct absolute accesses within the three "
            "declared decode/player/selector state ranges, including widths, "
            "signed views, valid branches, initialization/reuse/retirement and "
            "local resident dependencies. Internal MDEC tables and SDK-private "
            "callback records outside those ranges remain source/interface "
            "owners and are not presented as MOD state."),
    }


def _player_frontier(fmv: bytes) -> dict[str, Any]:
    calls = _direct_calls(
        fmv, STREAM_START_TARGET, PLAYER_END, base=FMV_BASE, header=0)
    jalr = []
    for pc in range(STREAM_START_TARGET, PLAYER_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        if word >> 26 == 0 and word & 0x3F == 9:
            jalr.append(_instruction(fmv, pc, base=FMV_BASE, header=0))
    if len(calls) != 50 or len({row["target"] for row in calls}) != 30:
        raise SystemExit("FMV player direct-call frontier drifted")
    if jalr:
        raise SystemExit("FMV player gained an indirect call")
    if _instruction(fmv, 0x800B70D8, base=FMV_BASE, header=0)["word"] != \
            "0x24140001":
        raise SystemExit("FMV player completion sentinel drifted")
    if _instruction(fmv, 0x800B7444, base=FMV_BASE, header=0)["word"] != \
            "0x1054FE7C":
        raise SystemExit("FMV completion exit branch drifted")
    function_bytes = _slice(
        fmv, STREAM_START_TARGET, PLAYER_END - STREAM_START_TARGET,
        base=FMV_BASE, header=0)
    teardown = _slice(
        fmv, 0x800B7464, PLAYER_END - 0x800B7464,
        base=FMV_BASE, header=0)
    return {
        "function": {
            "start": _hex(STREAM_START_TARGET), "end": _hex(PLAYER_END),
            "size": len(function_bytes), "sha256": _sha256_bytes(function_bytes),
        },
        "direct_calls": calls,
        "direct_call_count": len(calls),
        "unique_direct_targets": len({row["target"] for row in calls}),
        "indirect_calls": jalr,
        "completion_exit": {
            "sentinel_one": _instruction(
                fmv, 0x800B70D8, base=FMV_BASE, header=0),
            "request_read": _instruction(
                fmv, 0x800B743C, base=FMV_BASE, header=0),
            "branch_to_stop": _instruction(
                fmv, 0x800B7444, base=FMV_BASE, header=0),
            "stop_target": _hex(0x800B6E38),
            "teardown": {
                "start": _hex(0x800B7464), "end": _hex(PLAYER_END),
                "sha256": _sha256_bytes(teardown),
            },
        },
    }


def _completion_ownership(fmv: bytes) -> dict[str, Any]:
    rows = []
    for offset in range(0, len(fmv) - 3, 4):
        word = struct.unpack_from("<I", fmv, offset)[0]
        opcode = word >> 26
        if word & 0xFFFF != (COMPLETION_REQUEST & 0xFFFF) or \
                opcode not in {0x23, 0x2B}:
            continue
        pc = FMV_BASE + offset
        role = EXPECTED_COMPLETION_XREFS.get(pc)
        if role is None or f"0x{word:08X}" != role[2]:
            raise SystemExit(f"unexpected completion-request xref at 0x{pc:08X}")
        base_register = (word >> 21) & 0x1F
        prior = _word(fmv, pc - 4, base=FMV_BASE, header=0)
        if prior != (0x3C000000 | (base_register << 16) | 0x800D):
            raise SystemExit(f"completion-request xref lacks exact LUI at 0x{pc:08X}")
        rows.append({
            "role": role[0], "access": role[1],
            "address": _hex(COMPLETION_REQUEST),
            "lui": _instruction(fmv, pc - 4, base=FMV_BASE, header=0),
            "instruction": _instruction(fmv, pc, base=FMV_BASE, header=0),
        })
    if {int(row["instruction"]["pc"], 16) for row in rows} != \
            set(EXPECTED_COMPLETION_XREFS):
        raise SystemExit("completion-request xref census is incomplete")
    return {
        "address": _hex(COMPLETION_REQUEST), "width": "u32",
        "residency": "FMV.BIN",
        "xrefs": rows,
        "summary": {
            "total_xrefs": len(rows),
            "writers": sum(row["access"] == "write" for row in rows),
            "readers": sum(row["access"] == "read" for row in rows),
            "set_writers": 2,
            "clear_writers": 1,
        },
        "contexts": {
            "setters_sha256": _sha256_bytes(_slice(
                fmv, 0x800B6AF8, 0x800B6B4C - 0x800B6AF8,
                base=FMV_BASE, header=0)),
            "initialization_sha256": _sha256_bytes(_slice(
                fmv, 0x800B6DB4, 0x800B6DD4 - 0x800B6DB4,
                base=FMV_BASE, header=0)),
            "consumer_sha256": _sha256_bytes(_slice(
                fmv, 0x800B7430, 0x800B744C - 0x800B7430,
                base=FMV_BASE, header=0)),
        },
    }


def _loader_materialization_proof(code_images: dict[str, bytes],
                                  exe: bytes,
                                  jalr_doc: dict[str, Any]) -> dict[str, Any]:
    pointer = struct.pack("<I", RESIDENT_LOADER)
    literal_counts: dict[str, int] = {}
    standard_materializations: list[dict[str, Any]] = []
    for rel, data in sorted(code_images.items()):
        literal_counts[f"REBUILD/files/{rel}"] = data.count(pointer)
        for offset in range(0, len(data) - 7, 4):
            upper, lower = struct.unpack_from("<II", data, offset)
            register = (upper >> 16) & 0x1F
            if upper >> 26 != 0x0F or register == 0 or \
                    ((lower >> 16) & 0x1F) != register:
                continue
            immediate = lower & 0xFFFF
            signed = immediate - 0x10000 if immediate & 0x8000 else immediate
            addiu_value = (((upper & 0xFFFF) << 16) + signed) & 0xFFFFFFFF
            ori_value = ((upper & 0xFFFF) << 16) | immediate
            form = None
            if lower >> 26 == 0x09 and addiu_value == RESIDENT_LOADER:
                form = "lui/addiu"
            elif lower >> 26 == 0x0D and ori_value == RESIDENT_LOADER:
                form = "lui/ori"
            if form:
                standard_materializations.append({
                    "path": f"REBUILD/files/{rel}", "offset": offset,
                    "form": form, "register": register,
                })
    if any(literal_counts.values()) or standard_materializations:
        raise SystemExit("fmv_bin_load became address-taken or computed in pristine code")

    unresolved = {
        pc: row for pc, row in (jalr_doc.get("sites") or {}).items()
        if row.get("class") == "unresolved"
    }
    expected_unresolved = {
        "0x80060C78", "0x800647C4", "0x8006684C", "0x800668C4"}
    if set(unresolved) != expected_unresolved:
        raise SystemExit("resident unresolved JALR set drifted")
    exact = {
        0x80060C74: "0x240A00B0",
        0x80060C78: "0x0140F809",
        0x800646C0: "0x00809821",
        0x800647C4: "0x0260F809",
        0x80066848: "0x240A00B0",
        0x8006684C: "0x0140F809",
        0x800668C0: "0x240A00B0",
        0x800668C4: "0x0140F809",
    }
    for pc, expected in exact.items():
        if _instruction(exe, pc, base=EXE_BASE, header=EXE_HEADER)["word"] != expected:
            raise SystemExit(f"unresolved JALR def-use instruction drift at {_hex(pc)}")
    def_use = [
        {"site": "0x80060C78", "target_source": "t2 = 0x000000B0",
         "classification": "PSYQ BIOS-vector call; not RAM code"},
        {"site": "0x800647C4", "target_source": "s3 = entry a0 at 0x800646C0",
         "classification": (
             "caller-supplied GPU callback; loader cannot be supplied by any "
             "literal or standard computed materialization in the complete "
             "pristine resident/level/MEMORY/FMV code-owner set")},
        {"site": "0x8006684C", "target_source": "t2 = 0x000000B0",
         "classification": "PSYQ BIOS-vector call; not RAM code"},
        {"site": "0x800668C4", "target_source": "t2 = 0x000000B0",
         "classification": "PSYQ BIOS-vector call; not RAM code"},
    ]
    return {
        "code_owner_images": [
            {"path": f"REBUILD/files/{rel}", "bytes": len(data),
             "sha256": _sha256_bytes(data)}
            for rel, data in sorted(code_images.items())
        ],
        "literal_pointer_counts": literal_counts,
        "standard_materializations": standard_materializations,
        "supported_materialization_forms": [
            "little-endian aligned or unaligned u32 pointer literal",
            "aligned LUI plus ADDIU in the same destination register",
            "aligned LUI plus ORI in the same destination register",
        ],
        "unresolved_jalr_def_use": def_use,
        "result": "no pristine code owner can supply 0x8003E7C0 to jalr",
    }


def _selector_reachability(exe: bytes, fmv: bytes, memory: bytes,
                           code_images: dict[str, bytes],
                           direct: dict[str, Any], level_a: dict[str, Any],
                           level_b: dict[str, Any], cursor: dict[str, Any],
                           selectors: list[dict[str, Any]]) -> dict[str, Any]:
    reachable = {
        row["constant_selector"] for row in direct["calls"]
        if row["constant_selector"] is not None
    }
    for table in (level_a, level_b):
        reachable.update(
            row["selector"] for row in table["entries"]
            if row["action"] == "select_stream")
    reachable.update(
        row["selector"] for row in cursor["outcomes"]
        if row["path"] is not None)
    stream_selectors = {
        row["selector"] for row in selectors
        if row["action"] == "select_stream"
    }
    unreachable_stream = sorted(stream_selectors - reachable)
    if unreachable_stream != [2]:
        raise SystemExit(
            f"unexpected unreachable stream selector set: {unreachable_stream}")

    jalr_doc = json.loads(JALR_PATH.read_text())
    if jalr_doc.get("jalr_sites") != 139 or \
            sum((jalr_doc.get("classification") or {}).values()) != 139:
        raise SystemExit("Phase-3 resident JALR census is incomplete")
    installed = jalr_doc.get("installed_handlers") or {}
    if any(str(row.get("value")).lower() == _hex(RESIDENT_LOADER).lower()
           for row in installed.values()):
        raise SystemExit("fmv_bin_load appears in a retained installed callback slot")
    materialization_proof = _loader_materialization_proof(
        code_images, exe, jalr_doc)
    return {
        "reachable_stream_selectors": sorted(reachable & stream_selectors),
        "reviewed_unreachable_stream_selectors": unreachable_stream,
        "selector_2": {
            "path": selectors[2]["path"],
            "frame_count": selectors[2]["frame_count"],
            "classification": "unreachable_pristine_manifest_row",
            "basis": (
                "No direct loader argument source reaches 2; the resident loader "
                "address is absent as data and as a standard computed constant "
                "from every pristine resident, level, MEMORY and FMV code owner; "
                "all four formerly unresolved resident JALR target definitions "
                "exclude it; and no retained installed slot equals the loader. "
                "This is a static reachability boundary, not a movie-viewer "
                "behavior claim."),
        },
        "direct_loader_address_taken": False,
        "address_materializations": materialization_proof["literal_pointer_counts"],
        "computed_target_exclusion": materialization_proof,
        "resident_indirect_call_census": {
            "artifact": "analysis/phase3_jalr_callbacks.json",
            "sha256": _sha256(JALR_PATH),
            "jalr_sites": jalr_doc["jalr_sites"],
            "classification": jalr_doc["classification"],
            "installed_fmv_bin_load_targets": 0,
            "boundary": (
                "Installed handler values are one retained pristine anchor. The "
                "complete staged code-owner materialization scan, exact def-use "
                "of all four formerly unresolved sites and closed direct argument "
                "census carry the static selector-2 absence conclusion."),
        },
    }


def _historical_oracle_acceptance(legacy: dict[str, Any], *,
                                  verify_hash: bool) -> dict[str, Any]:
    if verify_hash and _sha256(LEGACY_FMV_PATH) != LEGACY_FMV_SHA256:
        raise SystemExit("historical E15 live receipt hash drifted")
    try:
        provenance = legacy["run_provenance"]
        state = provenance["anchor"]["state_inspections"][0]
        media = provenance["anchor"]["media_identity"]
        start_trace = legacy["live"]["natural_start_skip"]["pre_trigger"] \
            ["cycle_neutral_trace"]["comparison"]
        control_trace = legacy["live"]["start_removed_control"]["pre_trigger"] \
            ["cycle_neutral_trace"]["comparison"]
        start_anchor = legacy["live"]["natural_start_skip"]["pre_trigger"] \
            ["cycle_neutral_trace"]["control"]
        control_anchor = legacy["live"]["start_removed_control"]["pre_trigger"] \
            ["cycle_neutral_trace"]["control"]
        input_edit = legacy["live"]["input_edit"]
        coverage = legacy["live"]["start_removed_control"]["final"] \
            ["cycle_neutral_trace"]["coverage"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SystemExit(f"historical E15 live receipt is structurally incomplete: {exc}")
    checks = {
        "schema_v1": legacy.get("schema") == "abl-phase4-fmv/1",
        "receipt_date": legacy.get("generated") == "2026-07-16",
        "state_valid": state.get("valid") is True,
        "state_serial": state.get("serial") == "SCUS-94288",
        "state_media_pristine": state.get("state_media_hash_verification", {}).get(
            "pristine_verified") is True,
        "mounted_media_pristine": media.get("hash_verification", {}).get(
            "pristine_verified") is True,
        "same_anchor_positive": all(start_trace.get(key) is True for key in (
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers")),
        "same_anchor_negative": all(control_trace.get(key) is True for key in (
            "cycle_neutral", "same_cycle", "same_frame", "same_ram",
            "same_registers")),
        "same_anchor_controls_identical": start_anchor == control_anchor and all(
            start_anchor.get(key) == value for key, value in {
                "cycle": 2585837573,
                "movie_frame": 333,
                "pc": "0x80070d00",
                "ram_sha256": "1044d5b7d0bb6dc5a563a18c98e497e66f7919152d3ddcf1b093e2f4a01224e5",
                "registers_sha256": "754f0d34004d6508c9410c0c667bcf2726cb94bcb12241db10630a0622b63117",
            }.items()),
        "single_variable_start_edit": (
            input_edit.get("changed_frames") == list(range(334, 343))
            and input_edit.get("changed_field") == "ports.0.start true -> false"
            and input_edit.get("source_frame_count") == 541
            and input_edit.get("derived_frame_count") == 541),
        "native_control_divergence": (
            legacy["live"]["natural_start_skip"]["post_trigger"]
            ["cycle_neutral_trace"]["control"].get("pc") == "0x80065340"
            and legacy["live"]["start_removed_control"]["post_trigger"]
            ["cycle_neutral_trace"]["control"].get("pc") == "0x800b98f0"),
        "bounded_untruncated_coverage": bool(coverage) and all(
            row.get("total_hits", 0) > 0 and row.get("truncated") is False
            for row in coverage),
        "cold_boot_anchor": legacy.get("fixture_census", {}).get(
            "cold_boot_movie", {}).get("from_boot") is True,
        "binary_identity": bool(provenance.get("duckstation", {}).get(
            "binary_sha256")),
        "rpc_capability_identity": provenance.get("rpc_manifest", {}).get(
            "source", {}).get("method_count") == 203,
        "owned_cleanup": provenance.get("cleanup", {}).get(
            "owned_pid_stopped") is True,
    }
    if not all(checks.values()):
        raise SystemExit(
            "historical E15 live receipt acceptance check failed: "
            + ", ".join(key for key, value in checks.items() if not value))
    return {
        "classification": "closed_exact_historical_receipt_exception",
        "artifact": "analysis/phase4_fmv.json",
        "sha256": LEGACY_FMV_SHA256,
        "checks": checks,
        "reason": (
            "The exact 2026-07-16 receipt predates the Phase-4 escalation/batch "
            "adapter requirement but already retains pristine mounted/save media, "
            "binary/RPC identity, same-anchor positive and negative controls, "
            "bounded untruncated traces, a from-boot oracle, and owned-PID cleanup."),
        "non_extensible_rule": (
            "Only this exact artifact SHA-256 is accepted. Every new E15 live run "
            "requires a predeclared phase4_live_escalations entry and a validated "
            "phase4_duckstation_batch plan; this exception cannot accept drifted "
            "or future client-driven receipts."),
    }


def build(*, exe_data: bytes | None = None, fmv_data: bytes | None = None,
          memory_data: bytes | None = None, legacy_doc: dict[str, Any] | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    memory = MEMORY_PATH.read_bytes() if memory_data is None else memory_data
    legacy = json.loads(LEGACY_FMV_PATH.read_text()) \
        if legacy_doc is None else legacy_doc
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(FMV_REL, fmv)
        verify_staged_input(MEMORY_REL, memory)
    code_paths = [EXE_REL, FMV_REL, MEMORY_REL]
    code_paths.extend(str(path.relative_to(ROOT / "REBUILD/files"))
                      for path in sorted((ROOT / "REBUILD/files").glob(
                          "LEVEL*/LEVEL*.BIN")))
    if len(code_paths) != 23:
        raise SystemExit(f"unexpected pristine code-owner image count: {len(code_paths)}")
    code_images = {}
    for rel in code_paths:
        if rel == EXE_REL:
            data = exe
        elif rel == FMV_REL:
            data = fmv
        elif rel == MEMORY_REL:
            data = memory
        else:
            data = (ROOT / "REBUILD/files" / rel).read_bytes()
        if verify_identity:
            verify_staged_input(rel, data)
        code_images[rel] = data
    manifest, target_to_index = _manifest_cases(fmv)
    dispatch = _selector_dispatch(fmv, manifest, target_to_index)
    level_a = _level_table(
        exe, name="level_a", address=LEVEL_A_TABLE,
        selector_rows=dispatch["selectors"])
    level_b = _level_table(
        exe, name="level_b", address=LEVEL_B_TABLE,
        selector_rows=dispatch["selectors"])
    direct = _resident_calls(exe)
    cursor = _bonus_cursor(exe, dispatch["selectors"])
    reachability = _selector_reachability(
        exe, fmv, memory, code_images, direct, level_a, level_b, cursor,
        dispatch["selectors"])
    completion = _completion_ownership(fmv)
    player = _player_frontier(fmv)
    typed_state = _player_typed_state(fmv)
    historical = _historical_oracle_acceptance(
        legacy, verify_hash=verify_identity and legacy_doc is None)
    return {
        "schema": "abl-phase4-fmv-static-owners/3",
        "generated": "2026-07-19",
        "row": "E15_fmv",
        "lane": "static",
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}", "size": len(exe),
                "sha256": _sha256_bytes(exe), "identity_verified": verify_identity,
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}", "size": len(fmv),
                "sha256": _sha256_bytes(fmv), "identity_verified": verify_identity,
            },
            "memory_bin": {
                "path": f"REBUILD/files/{MEMORY_REL}", "size": len(memory),
                "sha256": _sha256_bytes(memory), "identity_verified": verify_identity,
            },
        },
        "manifest_cases": manifest,
        "overlay_dispatch": dispatch,
        "resident_direct_calls": direct,
        "selector_tables": {"level_a": level_a, "level_b": level_b},
        "bonus_clip_cursor": cursor,
        "selector_reachability": reachability,
        "completion_ownership": completion,
        "player_frontier": player,
        "player_typed_state": typed_state,
        "historical_oracle_acceptance": historical,
        "summary": {
            "manifest_rows": len(manifest),
            "selector_entries": len(dispatch["selectors"]),
            "stream_selectors": sum(
                row["action"] == "select_stream" for row in dispatch["selectors"]),
            "no_stream_selectors": sum(
                row["action"] == "no_stream" for row in dispatch["selectors"]),
            "direct_resident_call_sites": direct["exhaustive_direct_call_count"],
            "level_a_ids_resolved": 15,
            "level_b_ids_resolved": 15,
            "directly_unowned_stream_selectors": [2],
            "reviewed_unreachable_stream_selectors": [2],
            "selector_2_reachable_from_pristine_callers": False,
            "completion_request_xrefs": completion["summary"]["total_xrefs"],
            "player_direct_calls": player["direct_call_count"],
            "player_unique_targets": player["unique_direct_targets"],
            "typed_region_b_address_rows": typed_state["summary"][
                "region_b_address_rows"],
            "typed_absolute_xrefs": typed_state["summary"]["absolute_xrefs"],
        },
        "claims": {
            "confirmed": [
                "All 47 in-range selector targets and all 40 manifest cases are byte-derived.",
                "All nine direct resident JAL sites to fmv_bin_load are exhaustively enumerated.",
                "music IDs 1..15 resolve every LEV1A..LEV15A and LEV1B..LEV15B selector.",
                "The cursor path selects ALT1, ALT2, ALT3, INTRO, or LOSE only for old cursor 0..4; old 255 wraps to LEV15D.",
                "Selector 2 is a reviewed unreachable manifest row across all pristine direct argument sources and the address-not-taken/indirect-call boundary.",
                "The completion request has exactly three writers and one reader; the reader branches to the player stop/teardown path when it observes one.",
                "All direct absolute accesses in the declared player-boundary Region-B state ranges have exact widths, signed views, valid branch domains, xrefs, aliases and lifecycle rules.",
            ],
            "not_claimed": [
                "Selector 2 reachability absence does not prove a player-facing movie viewer exists or assign C17 frontend semantics.",
                "Static selector reachability does not prove natural playback, completion, pause/stop, reset, or error behavior.",
                "Typed player-boundary state does not close SDK-private libpress/MDEC record layouts or their callback ABI.",
            ],
        },
        "evidence_dependencies": {
            "analysis/phase3_jalr_callbacks.json": _sha256(JALR_PATH),
            "analysis/phase4_fmv.json": _sha256(LEGACY_FMV_PATH),
        },
        "source_dependencies": {
            "config/phase4_fmv.yaml": _sha256(ROOT / "config/phase4_fmv.yaml"),
            "src_re/fmv_player_streaming.c": _sha256(
                ROOT / "src_re/fmv_player_streaming.c"),
            "src_re/fmv_selector_dispatch.c": _sha256(
                ROOT / "src_re/fmv_selector_dispatch.c"),
            "tools/fmv_frame_table.py": _sha256(ROOT / "tools/fmv_frame_table.py"),
            "tools/phase4_fmv_static_owners.py": _sha256(Path(__file__)),
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
            raise SystemExit("phase4 FMV static-owner artifact is stale")
    print(
        "[phase4-fmv-static] 47 selectors, 40 cases, 9 direct callers, "
        "15 level-A and 15 level-B IDs verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
