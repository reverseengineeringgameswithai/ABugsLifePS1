#!/usr/bin/env python3
"""Reconstruct E15's upstream event producer and failure-routing frontier."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from build_identity import verify_staged_input
import exe_read
import phase4_common as common


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_failure_frontier.json"
CONFIG = ROOT / "config/phase4_fmv_failure_frontier.yaml"
SEMANTIC_SOURCE = ROOT / "src_re/fmv_failure_frontier.c"
TYPED_FMV_CONFIG = ROOT / "config/phase4_fmv.yaml"
STATIC_OWNERS = ROOT / "analysis/phase4_fmv_static_owners.json"
SOURCE_MANIFEST = ROOT / "tools/repro_inputs.sha256"
DERIVED_INDEX = ROOT / "analysis/phase4_derived_index.json"
EXE_REL = "SCUS_942.88"
FMV_REL = "FMV/FMV.BIN"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
EXE_END = 0x80082800
FMV_BASE = 0x800B5788
FMV_CODE_END = 0x800B9A4C
DELIVER_EVENT = 0x8006C3AC
DECODE_TIMEOUT = 0x800B6CA4


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _slice(data: bytes, start: int, end: int, *, base: int,
           header: int) -> bytes:
    first = header + start - base
    last = header + end - base
    if first < header or last > len(data) or first >= last:
        raise SystemExit(f"invalid slice {_hex(start)}..{_hex(end)}")
    return data[first:last]


def _word(data: bytes, pc: int, *, base: int, header: int) -> int:
    return struct.unpack(
        "<I", _slice(data, pc, pc + 4, base=base, header=header))[0]


def _instruction(data: bytes, pc: int, *, base: int,
                 header: int) -> dict[str, str]:
    word = _word(data, pc, base=base, header=header)
    return {
        "pc": _hex(pc),
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(pc, word),
    }


def _require_words(data: bytes, expected: dict[int, int], *, base: int,
                   header: int, label: str) -> list[dict[str, str]]:
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


def _jal_sites(data: bytes, target: int) -> list[int]:
    return [
        pc for pc in range(EXE_BASE, EXE_END, 4)
        if _jal_target(
            pc, _word(data, pc, base=EXE_BASE, header=EXE_HEADER)) == target
    ]


def _fmv_jal_sites(data: bytes, target: int) -> list[int]:
    return [
        pc for pc in range(FMV_BASE, FMV_CODE_END, 4)
        if _jal_target(
            pc, _word(data, pc, base=FMV_BASE, header=0)) == target
    ]


def _jr_ra_sites(data: bytes, start: int, end: int) -> list[int]:
    return [
        pc for pc in range(start, end, 4)
        if _word(data, pc, base=FMV_BASE, header=0) == 0x03E00008
    ]


def _s0_halfword_stores(data: bytes, start: int, end: int) -> list[dict[str, Any]]:
    rows = []
    for pc in range(start, end, 4):
        word = _word(data, pc, base=FMV_BASE, header=0)
        opcode = word >> 26
        base_register = (word >> 21) & 0x1F
        if opcode == 0x29 and base_register == 16:
            rows.append({
                "instruction": _instruction(
                    data, pc, base=FMV_BASE, header=0),
                "record_offset": word & 0xFFFF,
            })
    return rows


WINDOWS = (
    ("spu_fidma_body", "resident_executable", 0x8006BC80, 0x8006BD38,
     "794092aa4fe91faa71daefabb2c6f237941ddd313ecfc602016b72987fe46b84"),
    ("libcd_default_event_callbacks", "resident_executable",
     0x8006D6B4, 0x8006D72C,
     "30fa216e9b22d48de94af063a8088c7b4520e3118fe97d64a71ebeee2ebc7a2d"),
    ("libcd_getintr", "resident_executable", 0x8006DEB8, 0x8006E440,
     "a402706f33611733cedfdec678c7036bb6cc167e1f4ead113ac7a8e624ed4136"),
    ("decode_poll_timeout", "fmv_bin", 0x800B6CA4, 0x800B6D68,
     "06e83c28563ab998976b036f6e23c52c840352bee19c39efdd58322a7383e205"),
    ("file_open_player_route", "fmv_bin", 0x800B6DD8, 0x800B6E70,
     "1d8493de3bb519036ca52d9d322101ee3b3133dc8b689fdb0bbe386cd45a9adb"),
    ("cd_submit_retry", "fmv_bin", 0x800B7030, 0x800B7068,
     "8973a7cc729d42606f86508c61bdcc2c59d33eab737625a877f56125105ccc37"),
    ("file_open_helper", "fmv_bin", 0x800B8C8C, 0x800B8D88,
     "edd70e028314124c86e5c4d56079f25b6facc99f13f2d5a7420abe4db9834a94"),
)

EVENT_WORDS = {
    0x8006BCFC: 0x3C04F000,
    0x8006BD1C: 0x34840009,
    0x8006BD20: 0x0C01B0EB,
    0x8006BD24: 0x24050020,
    0x8006D6BC: 0x3C04F000,
    0x8006D6C0: 0x34840003,
    0x8006D6C4: 0x0C01B0EB,
    0x8006D6C8: 0x24050020,
    0x8006D6E4: 0x3C04F000,
    0x8006D6E8: 0x34840003,
    0x8006D6EC: 0x0C01B0EB,
    0x8006D6F0: 0x24050040,
    0x8006D70C: 0x3C04F000,
    0x8006D710: 0x34840003,
    0x8006D714: 0x0C01B0EB,
    0x8006D718: 0x24050040,
}

FMV_WORDS = {
    0x800B6CBC: 0x3C020080,
    0x800B6CE8: 0x14400014,
    0x800B6CF8: 0x0C01859A,
    0x800B6D04: 0xAE11002C,
    0x800B6D08: 0x2C420001,
    0x800B6DD8: 0x0C02E323,
    0x800B6DE4: 0x2402FFFF,
    0x800B6DE8: 0x12020018,
    0x800B6E4C: 0x3C04800B,
    0x800B6E50: 0x24845BA4,
    0x800B6E54: 0x0C017DF7,
    0x800B6E5C: 0x3C050002,
    0x800B6E60: 0x3C048013,
    0x800B6E68: 0x0C02DF0D,
    0x800B7044: 0x1040FFFB,
    0x800B704C: 0x0C01C226,
    0x800B7054: 0x1040FFFD,
    0x800B7060: 0x0C01B63A,
    0x800B8CFC: 0x1440000D,
    0x800B8D0C: 0x0C017DF7,
    0x800B8D14: 0x0802E35B,
    0x800B8D24: 0x0C017DF7,
    0x800B8D2C: 0x0802E35B,
}

DECODE_TIMEOUT_WORDS = {
    0x800B6CA4: 0x27BDFFD8,
    0x800B6CB8: 0x8E03002C,
    0x800B6CBC: 0x3C020080,
    0x800B6CC0: 0xAFA20010,
    0x800B6CC4: 0x14600021,
    0x800B6CCC: 0x24110001,
    0x800B6CD8: 0x2442FFFF,
    0x800B6CDC: 0xAFA20010,
    0x800B6CE8: 0x14400014,
    0x800B6CF8: 0x0C01859A,
    0x800B6D00: 0x8E020020,
    0x800B6D04: 0xAE11002C,
    0x800B6D08: 0x2C420001,
    0x800B6D0C: 0xAE020020,
    0x800B6D10: 0x000210C0,
    0x800B6D14: 0x02021021,
    0x800B6D18: 0x94430010,
    0x800B6D1C: 0x8E020020,
    0x800B6D24: 0x000210C0,
    0x800B6D28: 0x02021021,
    0x800B6D2C: 0xA6030024,
    0x800B6D30: 0x94420012,
    0x800B6D38: 0xA6020026,
    0x800B6D3C: 0x8E02002C,
    0x800B6D44: 0x1040FFE2,
    0x800B6D4C: 0xAE00002C,
    0x800B6D60: 0x03E00008,
}

DECODE_TIMEOUT_CALLER_WORDS = {
    0x800B7098: 0x3C10800D,
    0x800B709C: 0x2610ABE0,
    0x800B70D4: 0x02009821,
    0x800B729C: 0x02602021,
    0x800B72A0: 0x0C02DB29,
    0x800B72A4: 0x00002821,
}

DIRECT_EVENT_CALLERS = (
    ("spu_fidma_body", 0x8006BD20, 0xF0000009, 0x20,
     "asm/hand_written/8006bc80_sub_8006bc80.s",
     "handwritten_asm_external_hash_pinned"),
    ("def_cbsync", 0x8006D6C4, 0xF0000003, 0x20,
     "src/main/8006d6b4_def_cbsync.c", "matching_c"),
    ("def_cbready", 0x8006D6EC, 0xF0000003, 0x40,
     "src/main/8006d6dc_def_cbready.c", "matching_c"),
    ("def_cbread", 0x8006D714, 0xF0000003, 0x40,
     "src/main/8006d704_def_cbread.c", "matching_c"),
)

SOURCE_PATHS = (
    "src/main/80045d5c_gp_set_one.c",
    "asm/hand_written/80045d6c_cd_subsystem_init.s",
    "src/main/8006d61c_CdInit.c",
    "src/main/8006d6b4_def_cbsync.c",
    "src/main/8006d6dc_def_cbready.c",
    "src/main/8006d704_def_cbread.c",
    "asm/hand_written/8006bc80_sub_8006bc80.s",
    "asm/hand_written/8006deb8_getintr.s",
    "src_re/fmv_failure_frontier.c",
)


def _manifest_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in SOURCE_MANIFEST.read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            pins[fields[1]] = fields[0]
    return pins


def _source_dependencies() -> dict[str, str]:
    pins = _manifest_pins()
    rows: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        path = ROOT / relative
        digest = _sha256(path)
        if relative.startswith("asm/") and pins.get(relative) != digest:
            raise SystemExit(
                f"FMV failure-frontier source is not manifest-pinned: {relative}")
        rows[relative] = digest
    return rows


def _validated_windows(exe: bytes, fmv: bytes) -> list[dict[str, Any]]:
    rows = []
    for name, image, start, end, expected in WINDOWS:
        data, base, header = (
            (exe, EXE_BASE, EXE_HEADER)
            if image == "resident_executable" else (fmv, FMV_BASE, 0))
        digest = _sha256_bytes(
            _slice(data, start, end, base=base, header=header))
        if digest != expected:
            raise SystemExit(f"FMV failure-frontier window drifted: {name}")
        rows.append({
            "id": name,
            "image": image,
            "start": _hex(start),
            "end": _hex(end),
            "bytes": end - start,
            "sha256": digest,
        })
    return rows


def _decode_timeout_recovery(
        fmv: bytes, config: dict[str, Any]) -> dict[str, Any]:
    source = (config.get("failure_paths") or {}).get(
        "decode_poll_timeout") or {}
    expected_callers = source.get("direct_callers")
    callers = _fmv_jal_sites(fmv, DECODE_TIMEOUT)
    if expected_callers != [0x800B72A0] or callers != expected_callers:
        raise SystemExit(
            "FMV decode-timeout caller census drifted: "
            f"expected {[ _hex(value) for value in expected_callers or [] ]}, "
            f"observed {[ _hex(value) for value in callers ]}")
    function = _slice(
        fmv, DECODE_TIMEOUT, 0x800B6D68,
        base=FMV_BASE, header=0)
    fields = source.get("fields") or {}
    if fields != {
        "active_rect_index": {
            "offset": 0x20, "type": "u32", "domain": [0, 1]},
        "rect_bank": {
            "offset": 0x10, "slots": 2, "stride": 8,
            "layout": ["s16_x", "s16_y", "s16_w", "s16_h"]},
        "present_rect": {
            "offset": 0x24,
            "layout": ["s16_x", "s16_y", "s16_w", "s16_h"]},
        "rect_ready": {
            "offset": 0x2C, "type": "u32", "domain": [0, 1]},
    }:
        raise SystemExit("FMV decode-timeout field contract drifted")
    expected_authorities = [
        {
            "path": "config/phase4_fmv.yaml",
            "yaml_path": "typed_state.player_boundary.structures",
        },
        {
            "path": "analysis/phase4_fmv_static_owners.json",
            "json_path": "player_typed_state.structures",
        },
    ]
    if source.get("layout_authorities") != expected_authorities:
        raise SystemExit("FMV decode-timeout layout authorities drifted")
    typed = common.load_yaml(TYPED_FMV_CONFIG)
    typed_structures = (
        ((typed.get("typed_state") or {}).get("player_boundary") or {})
        .get("structures") or {})
    static = common.load_json(STATIC_OWNERS)
    static_structures = (
        (static.get("player_typed_state") or {}).get("structures") or {})
    expected_typed = {
        "rect_bank": {
            "base": 0x800CABF0,
            "slots": 2,
            "stride": 8,
            "fields": ["s16_x", "s16_y", "s16_w", "s16_h"],
        },
        "present_rect": {
            "base": 0x800CAC04,
            "size": 8,
            "fields": ["s16_x", "s16_y", "s16_w", "s16_h"],
        },
    }
    expected_static = {
        "rect_bank": {
            "base": "0x800CABF0",
            "slots": 2,
            "stride": 8,
            "fields": ["s16 x", "s16 y", "s16 w", "s16 h"],
        },
        "present_rect": {
            "base": "0x800CAC04",
            "size": 8,
            "fields": ["s16 x", "s16 y", "s16 w", "s16 h"],
        },
    }
    if {
            name: typed_structures.get(name)
            for name in expected_typed
    } != expected_typed:
        raise SystemExit("authoritative FMV typed RECT layout drifted")
    if {
            name: static_structures.get(name)
            for name in expected_static
    } != expected_static:
        raise SystemExit("generated FMV static-owner RECT layout drifted")
    coordinate_copies = source.get("coordinate_copies") or {}
    expected_copies = {
        "x": {
            "load": 0x800B6D18,
            "source_record_offset": 0x10,
            "store": 0x800B6D2C,
            "destination_record_offset": 0x24,
        },
        "y": {
            "load": 0x800B6D30,
            "source_record_offset": 0x12,
            "store": 0x800B6D38,
            "destination_record_offset": 0x26,
        },
    }
    if coordinate_copies != expected_copies:
        raise SystemExit("FMV decode-timeout coordinate copy contract drifted")
    returns = _jr_ra_sites(fmv, DECODE_TIMEOUT, 0x800B6D68)
    if returns != [0x800B6D60]:
        raise SystemExit(
            "FMV decode-timeout return census drifted: "
            f"{[ _hex(pc) for pc in returns ]}")
    halfword_stores = _s0_halfword_stores(
        fmv, DECODE_TIMEOUT, 0x800B6D68)
    if [
            (row["instruction"]["pc"], row["record_offset"])
            for row in halfword_stores
    ] != [("0x800B6D2C", 0x24), ("0x800B6D38", 0x26)]:
        raise SystemExit("FMV decode-timeout record halfword stores drifted")
    return {
        "function": {
            "start": _hex(DECODE_TIMEOUT),
            "end": "0x800B6D68",
            "bytes": len(function),
            "sha256": _sha256_bytes(function),
            "conventional_return": _instruction(
                fmv, 0x800B6D60, base=FMV_BASE, header=0),
            "return_sites": [_hex(pc) for pc in returns],
        },
        "direct_callers": [
            {
                "site": _hex(pc),
                "instruction": _instruction(
                    fmv, pc, base=FMV_BASE, header=0),
                "owner": "fmv_player_outer_loop",
            }
            for pc in callers
        ],
        "caller_count": len(callers),
        "record_pointer_chain": {
            "record_base": _hex(source["record_base"]),
            "base_materialization": _instruction(
                fmv, source["record_base_materialization"],
                base=FMV_BASE, header=0),
            "preserve_as_s3": _instruction(
                fmv, source["player_base_preservation"],
                base=FMV_BASE, header=0),
            "move_to_a0": _instruction(
                fmv, source["caller_argument_move"],
                base=FMV_BASE, header=0),
            "call": _instruction(
                fmv, callers[0], base=FMV_BASE, header=0),
            "complete": True,
        },
        "fields": {
            "active_rect_index": {
                "offset": "0x20", "address": "0x800CAC00",
                "type": "u32", "domain": [0, 1],
            },
            "rect_bank": {
                "offset": "0x10", "address": "0x800CABF0",
                "slots": 2, "stride": 8,
                "fields": {
                    "x": "s16 +0x00",
                    "y": "s16 +0x02",
                    "width": "s16 +0x04",
                    "height": "s16 +0x06",
                },
            },
            "present_rect": {
                "offset": "0x24", "address": "0x800CAC04",
                "fields": {
                    "x": "s16 +0x00",
                    "y": "s16 +0x02",
                    "width": "s16 +0x04",
                    "height": "s16 +0x06",
                },
            },
            "rect_ready": {
                "offset": "0x2C", "address": "0x800CAC0C",
                "type": "u32", "domain": [0, 1],
            },
        },
        "field_layout_authorities": {
            "typed_config": {
                "path": str(TYPED_FMV_CONFIG.relative_to(ROOT)),
                "sha256": _sha256(TYPED_FMV_CONFIG),
                "structures": expected_typed,
            },
            "static_owner_artifact": {
                "path": str(STATIC_OWNERS.relative_to(ROOT)),
                "sha256": _sha256(STATIC_OWNERS),
                "structures": expected_static,
            },
            "agree_on_field_order": ["x", "y", "width", "height"],
        },
        "poll": {
            "budget": source["counter"],
            "budget_semantics": source["counter_semantics"],
            "entry_ready_branch": _instruction(
                fmv, source["already_ready_branch"],
                base=FMV_BASE, header=0),
            "decrement": _instruction(
                fmv, 0x800B6CD8, base=FMV_BASE, header=0),
            "counter_store": _instruction(
                fmv, 0x800B6CDC, base=FMV_BASE, header=0),
            "exhausted_branch": _instruction(
                fmv, source["exhausted_branch"],
                base=FMV_BASE, header=0),
            "ready_poll_branch": _instruction(
                fmv, source["poll_branch"],
                base=FMV_BASE, header=0),
        },
        "timeout_transition": {
            "diagnostic_call": _instruction(
                fmv, source["diagnostic_call"],
                base=FMV_BASE, header=0),
            "ready_one_store": _instruction(
                fmv, source["timeout_ready_store"],
                base=FMV_BASE, header=0),
            "active_index_normalization": {
                "instruction": _instruction(
                    fmv, source["active_index_boolean_inverse"],
                    base=FMV_BASE, header=0),
                "expression": "old_active_rect_index == 0",
                "boolean_inverse_under_valid_domain": True,
            },
            "active_index_store": _instruction(
                fmv, source["active_index_store"],
                base=FMV_BASE, header=0),
            "selected_rect_addressing": {
                "expression":
                    "record+0x10+(active_rect_index*8)",
                "slot_count": 2,
                "stride": 8,
            },
            "coordinate_copies": {
                field: {
                    "field": field,
                    "load": _instruction(
                        fmv, spec["load"], base=FMV_BASE, header=0),
                    "store": _instruction(
                        fmv, spec["store"], base=FMV_BASE, header=0),
                    "source_record_offset":
                        f"0x{spec['source_record_offset']:02X}",
                    "destination_record_offset":
                        f"0x{spec['destination_record_offset']:02X}",
                    "source":
                        f"rect_bank[active_rect_index].{field}",
                    "destination": f"present_rect.{field}",
                    "semantic_type": "s16",
                    "transfer": "lhu_to_sh_preserves_raw_16_bits",
                }
                for field, spec in coordinate_copies.items()
            },
            "extent_fields_untouched": {
                "width_destination_record_offset": "0x28",
                "height_destination_record_offset": "0x2A",
                "record_halfword_stores": halfword_stores,
                "width_or_height_store_present": False,
            },
        },
        "convergence": {
            "final_ready_clear": _instruction(
                fmv, source["final_ready_clear"],
                base=FMV_BASE, header=0),
            "all_paths_reach_final_ready_clear": True,
            "other_returns": [],
            "ready_value_at_return": 0,
        },
    }


def _validate_config() -> dict[str, Any]:
    config = common.load_yaml(CONFIG)
    if config.get("schema") != \
            "abl-phase4-fmv-failure-frontier-config/1" or \
            config.get("campaign") != "fmv_playback" or \
            config.get("row") != "E15_fmv" or \
            config.get("dimension") != "lifecycle" or \
            config.get("lane") != "static" or \
            config.get("next_lane") != "live" or \
            config.get("dimension_promoted") is not False:
        raise SystemExit("FMV failure-frontier config boundary drifted")
    control = config.get("selected_control") or {}
    if control.get("escalation_id") != \
            "P4-ITER109-E15-FILE-OPEN-FAILURE-ROUTING" or \
            control.get("missing_fact_id") != \
            "E15/file-open-failure-routing-outcome" or \
            control.get("code_write") != {
                "address": 0x800B6DE8,
                "original_word": 0x12020018,
                "replacement_word": 0x10000018,
            }:
        raise SystemExit("FMV failure-frontier selected control drifted")
    return config


def build(*, exe_data: bytes | None = None, fmv_data: bytes | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(FMV_REL, fmv)
    config = _validate_config()
    windows = _validated_windows(exe, fmv)
    event_ops = _require_words(
        exe, EVENT_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="resident DeliverEvent surface")
    fmv_ops = _require_words(
        fmv, {**FMV_WORDS, **DECODE_TIMEOUT_WORDS,
              **DECODE_TIMEOUT_CALLER_WORDS}, base=FMV_BASE, header=0,
        label="FMV failure frontier")
    timeout_recovery = _decode_timeout_recovery(fmv, config)
    sites = _jal_sites(exe, DELIVER_EVENT)
    expected_sites = [row[1] for row in DIRECT_EVENT_CALLERS]
    if sites != expected_sites:
        raise SystemExit(
            "resident DeliverEvent call census drifted: "
            f"expected {[ _hex(value) for value in expected_sites ]}, "
            f"observed {[ _hex(value) for value in sites ]}")
    event_rows = [
        {
            "owner": owner,
            "site": _hex(site),
            "event_class": _hex(event_class),
            "event_spec": _hex(event_spec),
            "matches_fmv_registration": (
                event_class == 0xF0000003 and event_spec == 0x8000),
            "source": source,
            "source_status": status,
            "source_sha256": _sha256(ROOT / source),
        }
        for owner, site, event_class, event_spec, source, status
        in DIRECT_EVENT_CALLERS
    ]
    index = common.load_json(DERIVED_INDEX)
    index_rows = [
        row for row in index.get("external_indexes") or []
        if "E15_fmv" in (row.get("rows") or [])
    ]
    if len(index_rows) != 1 or index_rows[0].get("sha256") != \
            "e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab":
        raise SystemExit("FMV derived-index identity drifted")
    control = config["selected_control"]
    return {
        "_comment": (
            "Generated from hash-verified pristine retail code. Static routing "
            "does not establish native failure outcomes or BIOS event delivery."),
        "schema": "abl-phase4-fmv-failure-frontier/1",
        "campaign": "fmv_playback",
        "row": "E15_fmv",
        "dimension_boundary": {
            "dimension": "lifecycle",
            "claim": "partial",
            "dimension_promoted": False,
            "closed_sub_boundary":
                "upstream_event_and_failure_path_static_partition",
            "next_lane": "live",
            "next_missing_fact":
                "E15/file-open-failure-routing-outcome",
        },
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "sha256": _sha256_bytes(exe),
                "identity_verified": verify_identity,
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}",
                "sha256": _sha256_bytes(fmv),
                "identity_verified": verify_identity,
            },
            "config": {
                "path": str(CONFIG.relative_to(ROOT)),
                "sha256": _sha256(CONFIG),
            },
            "semantic_source": {
                "path": str(SEMANTIC_SOURCE.relative_to(ROOT)),
                "sha256": _sha256(SEMANTIC_SOURCE),
                "status": "documentation_grade_semantic_c",
            },
            "derived_index": {
                "artifact": str(DERIVED_INDEX.relative_to(ROOT)),
                "artifact_sha256": _sha256(DERIVED_INDEX),
                "external_index": index_rows[0],
            },
        },
        "source_dependencies": _source_dependencies(),
        "windows": windows,
        "native_event_delivery": {
            "registration": {
                "event_class": "0xF0000003",
                "event_spec": "0x00008000",
                "callback": "0x80045D5C",
                "callback_store": "0x80082484",
            },
            "deliver_event": {
                "target": _hex(DELIVER_EVENT),
                "resident_direct_callers": event_rows,
                "resident_direct_call_count": len(event_rows),
                "matching_registered_class_spec": sum(
                    row["matches_fmv_registration"] for row in event_rows),
                "all_resident_direct_callers_classified": True,
            },
            "getintr": {
                "range": ["0x8006DEB8", "0x8006E440"],
                "direct_deliver_event_calls": 0,
                "source": "asm/hand_written/8006deb8_getintr.s",
            },
            "producer_boundary": {
                "classification":
                    "outside_resident_direct_deliver_event_call_surface",
                "candidate_domain": "BIOS_or_interrupt_service",
                "exact_producer_instruction_claimed": False,
                "native_delivery_frequency_claimed": False,
            },
        },
        "failure_paths": {
            "file_open": {
                "helper": {
                    "range": ["0x800B8C8C", "0x800B8D88"],
                    "slot_capacity": 16,
                    "failure_returns": ["0x800B8D14", "0x800B8D2C"],
                    "failure_value": -1,
                },
                "player": {
                    "helper_call": "0x800B6DD8",
                    "predicate": "0x800B6DE8",
                    "failure_target": "0x800B6E4C",
                    "diagnostic_call": "0x800B6E54",
                    "shared_initialization_call": "0x800B6E68",
                    "failure_rejoins_shared_initialization": True,
                },
                "native_runtime_outcome_claimed": False,
            },
            "decode_poll_timeout": {
                **timeout_recovery,
                "native_runtime_outcome_claimed": False,
            },
            "cd_submit_retry": {
                "getlocp": {
                    "command": "0x15",
                    "call": "0x800B703C",
                    "retry_branch": "0x800B7044",
                },
                "read2": {
                    "mode": "0x01C0",
                    "call": "0x800B704C",
                    "retry_branch": "0x800B7054",
                },
                "demute_after_both_succeed": {
                    "command": "0x0C",
                    "call": "0x800B7060",
                },
                "native_retry_counts_claimed": False,
            },
        },
        "selected_control": {
            "escalation_id": control["escalation_id"],
            "missing_fact_id": control["missing_fact_id"],
            "anchor": {
                "movie": control["anchor_movie"],
                "movie_sha256": control["anchor_movie_sha256"],
                "state": control["anchor_state"],
                "state_sha256": control["anchor_state_sha256"],
            },
            "offline_localization": {
                "derived_index_sha256":
                    index_rows[0]["sha256"],
                "overlay_resident_interval":
                    control["overlay_resident_interval"],
                "selected_limit_first_observed_frame": 183,
                "movie_start_input_frame": 334,
            },
            "only_difference": {
                "kind": "code_write",
                "address": _hex(control["code_write"]["address"]),
                "original_word":
                    f"0x{control['code_write']['original_word']:08X}",
                "replacement_word":
                    f"0x{control['code_write']['replacement_word']:08X}",
                "same_failure_target": "0x800B6E4C",
            },
            "passive_window": control["passive_window"],
            "precise_window": control["precise_window"],
            "claim_boundary": control["claim_boundary"],
            "falsifier": control["falsifier"],
            "native_failed_handle_claimed": False,
            "missing_or_malformed_media_claimed": False,
            "user_visible_policy_claimed": False,
        },
        "static_successor": {
            "corrected_claim":
                config["static_successor"]["corrected_claim"],
            "closed_sub_boundary":
                "decode_timeout_recovery_coordinate_state_ownership",
            "dimension_promoted": False,
            "next_lane": "static",
            "not_claimed": config["static_successor"]["not_claimed"],
            "falsifier": {
                "packet_hypothesis": {
                    "claim":
                        config["static_successor"]["packet_hypothesis"],
                    "explicit":
                        config["static_successor"]["packet_falsifier"],
                    "outcome": "falsified",
                    "evidence": {
                        "authoritative_field_order":
                            ["x", "y", "width", "height"],
                        "selected_slot_load_offsets": ["0x10", "0x12"],
                        "presentation_store_offsets": ["0x24", "0x26"],
                        "reason":
                            "instructions copy x/y; width/height remain untouched",
                    },
                },
                "corrected_claim": {
                    "explicit":
                        config["static_successor"]["corrected_falsifier"],
                    "checks": {
                        "sole_direct_caller_classified":
                            timeout_recovery["caller_count"] == 1,
                        "record_pointer_chain_complete":
                            timeout_recovery["record_pointer_chain"]["complete"],
                        "budget_is_decrement_before_test":
                            timeout_recovery["poll"]["budget_semantics"] ==
                            "decrement_before_test",
                        "active_index_is_boolean_inverse":
                            timeout_recovery["timeout_transition"]
                            ["active_index_normalization"]
                            ["boolean_inverse_under_valid_domain"],
                        "coordinate_copy_is_authoritatively_typed":
                            list(timeout_recovery["timeout_transition"]
                                 ["coordinate_copies"]) == ["x", "y"],
                        "width_and_height_are_untouched":
                            not timeout_recovery["timeout_transition"]
                            ["extent_fields_untouched"]
                            ["width_or_height_store_present"],
                        "all_paths_clear_ready_before_return":
                            timeout_recovery["convergence"]
                            ["all_paths_reach_final_ready_clear"],
                    },
                    "outcome": "survived",
                },
            },
        },
        "exact_instructions": event_ops + fmv_ops,
        "summary": {
            "classified_resident_direct_event_callers": len(event_rows),
            "resident_direct_event_matches": 0,
            "classified_failure_path_families": 3,
            "exact_failure_windows": 4,
            "unclassified_static_failure_edges": 0,
            "selected_controls": 1,
            "runtime_outcomes_claimed": 0,
            "decode_timeout_packet_hypotheses_falsified": 1,
            "decode_timeout_state_transitions": 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            print("phase4 FMV failure-frontier artifact is missing or stale")
            return 1
    else:
        print(rendered, end="")
    print(
        "PASS: 4 resident DeliverEvent callers, 3 failure families, "
        "1 selected bounded control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
