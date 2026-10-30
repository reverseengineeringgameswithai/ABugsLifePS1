#!/usr/bin/env python3
"""Reconstruct caller-owned Region-B replacement after LOSE and Level-B."""
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
CONFIG_PATH = ROOT / "config/phase4_fmv_region_b_replacement_ownership.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_region_b_replacement_ownership.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

REGION_B_BASE = 0x800B5788
MEMORY_BIN_STRING = 0x8001ADFC

FUNCTIONS = {
    "post_lose_return": (0x800500E0, 0x800500F4),
    "scene_flow_dispatcher": (0x8004FCA0, 0x800502C4),
    "completed_level_b_owner": (0x800502C4, 0x8005038C),
    "post_level_b_return": (0x80050324, 0x8005038C),
    "scene_setup_and_load": (0x8005038C, 0x800503FC),
    "display_buffers_init": (0x80039478, 0x80039780),
    "resource_id_dat_load_dispatcher": (0x8003CF2C, 0x8003D404),
    "resource_selector_zero_path": (0x8003D2F8, 0x8003D318),
    "universal_file_loader": (0x80046330, 0x80046538),
    "file_lookup_cdsearchfile": (0x80045FC4, 0x800460E4),
}

EXPECTED_FUNCTION_SHA256 = {
    "post_lose_return":
        "782344e336768eb1c919f633ab4b73908bb0e7a4db0d55eb38b4d09876356d98",
    "scene_flow_dispatcher":
        "02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f",
    "completed_level_b_owner":
        "0b1c9bf09173c00de24df8d5c827b534b2d1ebe3a82dba7fb55b5595ac7d22fb",
    "post_level_b_return":
        "4b87da9553f17509c2cfaf78def96096fe23ef07771bf84af2e0449b90c3ec0e",
    "scene_setup_and_load":
        "6c12e5e6c9416b4e7aa2223c3ead0d3478ad65faa97c82098b223e494e61fddb",
    "display_buffers_init":
        "deb8ac88b80f0b5d9b5085fc84fad979fea6cabe1448ec8d4bd1d6b27c854d2b",
    "resource_id_dat_load_dispatcher":
        "2437e010eaf1c6439794913dbcd1cfba07d7455a86834ad59007fcd323491921",
    "resource_selector_zero_path":
        "d23c1e881ffe8d666969334095c15d26fee7a772d60f1a492d8c873104d9b9fc",
    "universal_file_loader":
        "060b385746f65e02f70cc95cbeedff8fbb0cc6c951b238294526e248701a9e28",
    "file_lookup_cdsearchfile":
        "37b4f2f8ea955f11a4e8d6d86a067b65bc5a1061c48f868ed4f10bb71e73502a",
}

EXPECTED_WORDS = {
    0x800500E0: 0x24040005,
    0x800500E4: 0x0C0140E3,
    0x800500E8: 0x24050040,
    0x80050134: 0x1602001C,
    0x8005013C: 0x0C0140B1,
    0x80050144: 0x3C038008,
    0x8005019C: 0xAF90064C,
    0x8005023C: 0x3C02800A,
    0x80050248: 0x04410014,
    0x8005024C: 0x24040006,
    0x80050250: 0x08013F58,
    0x8005029C: 0x0C0140E3,
    0x800502A0: 0x24050080,
    0x80050324: 0x00002021,
    0x8005034C: 0x1482000A,
    0x80050354: 0x24040029,
    0x8005036C: 0x0C00F9F0,
    0x80050378: 0xAF82064C,
    0x80050384: 0x03E00008,
    0x8004FD60: 0x3C02800A,
    0x8004FD6C: 0x0441000C,
    0x8004FD70: 0x24040003,
    0x8004FD74: 0x0C0140E3,
    0x8004FD78: 0x00002821,
    0x800503B0: 0x10A20008,
    0x800503C4: 0x0C00E51E,
    0x800503CC: 0x0C00F3CB,
    0x800503D0: 0x00002021,
    0x8003CF34: 0x0080A021,
    0x8003D2F8: 0x1680000D,
    0x8003D300: 0x3C048002,
    0x8003D304: 0x2484ADFC,
    0x8003D308: 0x3C05800B,
    0x8003D30C: 0x24A55788,
    0x8003D310: 0x0C0118CC,
    0x80046340: 0x00A0F021,
    0x8004641C: 0x0C0117F1,
    0x80046420: 0x03C02821,
    0x80045FD4: 0x00A09821,
    0x80046074: 0x02602821,
    0x80046078: 0x0C01C1A6,
    0x8004607C: 0x36460080,
}

EXPECTED_DISPLAY_CALL_TARGETS = [
    0x80062790, 0x80062790, 0x800625FC, 0x80060EC0, 0x80060F78,
    0x80062B04, 0x80060EC0, 0x80060F78, 0x80062B04, 0x800651D0,
    0x80062EC8, 0x80062BFC, 0x800625FC, 0x800651D0, 0x80062EC8,
    0x80062BFC, 0x800625FC, 0x80063508, 0x80063508,
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _slice(data: bytes, start: int, end: int) -> bytes:
    begin = EXE_HEADER + start - EXE_BASE
    finish = EXE_HEADER + end - EXE_BASE
    _require(
        EXE_HEADER <= begin < finish <= len(data),
        f"invalid executable slice 0x{start:08X}..0x{end:08X}",
    )
    return data[begin:finish]


def _word(data: bytes, address: int) -> int:
    return struct.unpack("<I", _slice(data, address, address + 4))[0]


def _instruction(data: bytes, address: int, expected: int) -> dict[str, str]:
    word = _word(data, address)
    _require(
        word == expected,
        f"opcode drift at 0x{address:08X}: "
        f"0x{word:08X} != 0x{expected:08X}",
    )
    return {
        "pc": f"0x{address:08X}",
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(address, word),
    }


def _jal_target(pc: int, word: int) -> int | None:
    if word >> 26 != 3:
        return None
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def _direct_calls(
    data: bytes, start: int, end: int
) -> list[dict[str, str]]:
    calls = []
    for pc in range(start, end, 4):
        word = _word(data, pc)
        target = _jal_target(pc, word)
        if target is not None:
            calls.append({
                "pc": f"0x{pc:08X}",
                "target": f"0x{target:08X}",
                "word": f"0x{word:08X}",
                "mnemonic": exe_read.disasm_one(pc, word),
            })
    return calls


def _function(data: bytes, name: str) -> dict[str, Any]:
    start, end = FUNCTIONS[name]
    body = _slice(data, start, end)
    digest = _sha256_bytes(body)
    _require(
        digest == EXPECTED_FUNCTION_SHA256[name],
        f"{name} function slice drifted",
    )
    return {
        "start": f"0x{start:08X}",
        "end": f"0x{end:08X}",
        "size": len(body),
        "sha256": digest,
        "direct_calls": _direct_calls(data, start, end),
    }


def _region_b_materializations(
    data: bytes, ranges: list[tuple[int, int]]
) -> list[dict[str, str]]:
    rows = []
    for start, end in ranges:
        for pc in range(start, end - 4, 4):
            first = _word(data, pc)
            second = _word(data, pc + 4)
            if first >> 26 != 15:
                continue
            register = (first >> 16) & 0x1F
            opcode = second >> 26
            if (
                opcode not in {9, 13}
                or ((second >> 21) & 0x1F) != register
                or ((second >> 16) & 0x1F) != register
            ):
                continue
            high = (first & 0xFFFF) << 16
            low = second & 0xFFFF
            if opcode == 9 and low & 0x8000:
                low -= 0x10000
            value = (high + low if opcode == 9 else high | low) & 0xFFFFFFFF
            if value == REGION_B_BASE:
                rows.append({
                    "lui_pc": f"0x{pc:08X}",
                    "low_pc": f"0x{pc + 4:08X}",
                    "register": register,
                    "value": f"0x{value:08X}",
                })
    return rows


def _load_run_json(
    spec: dict[str, Any], label: str
) -> tuple[Path, dict[str, Any]]:
    path = RUN_ROOT / spec["relative_path"]
    _require(path.is_file(), f"missing {label}: {path}")
    _require(_sha256(path) == spec["sha256"], f"{label} hash drifted")
    return path, json.loads(path.read_text())


def _offline_localization() -> dict[str, Any]:
    spec = CONFIG["offline_query"]
    _, receipt = _load_run_json(spec["receipt"], "offline receipt")
    _, output = _load_run_json(spec["output"], "offline output")
    _, preservation = _load_run_json(
        spec["preservation"], "offline preservation manifest"
    )
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0,
        "offline receipt is not closed",
    )
    _require(
        receipt.get("reader", {}).get("path")
        == "tools/phase4_offline_receipt_query.py"
        and receipt.get("reader", {}).get("sha256")
        == _sha256(ROOT / "tools/phase4_offline_receipt_query.py"),
        "offline reader identity drifted",
    )
    _require(
        receipt.get("external_inputs") == [{
            "path": "iteration-2-receipts/inputs/"
                    "fmv-lifecycle-v2.index.json",
            "scope": "run",
            "sha256": spec["external_index_sha256"],
        }],
        "offline external input drifted",
    )
    _require(
        receipt.get("outputs") == [{
            "path": spec["output"]["relative_path"],
            "scope": "run",
            "sha256": spec["output"]["sha256"],
        }],
        "offline retained output drifted",
    )
    terms = output.get("terms") or {}
    _require(
        output.get("schema") == "abl-phase4-offline-json-search-result/1"
        and output.get("source", {}).get("sha256")
        == spec["external_index_sha256"]
        and set(terms) == set(spec["expected_zero_terms"])
        and all(row == {
            "count": 0, "paths": [], "paths_truncated": False
        } for row in terms.values()),
        "offline zero-result boundary drifted",
    )
    actual_entries = {
        (row.get("sha256"), row.get("size"))
        for row in preservation.get("entries", [])
        if row.get("media_class") == "derived_pristine_evidence"
        and row.get("preservation_required") is True
    }
    _require(
        preservation.get("complete") is True
        and preservation.get("errors") == []
        and actual_entries == {
            (spec["external_index_sha256"], 16060589),
            (spec["output"]["sha256"], spec["output"]["bytes"]),
        },
        "offline preservation contract drifted",
    )
    return {
        "receipt_sha256": spec["receipt"]["sha256"],
        "output_sha256": spec["output"]["sha256"],
        "preservation_sha256": spec["preservation"]["sha256"],
        "external_index_sha256": spec["external_index_sha256"],
        "external_index_bytes": output["source"]["bytes"],
        "zero_match_terms": sorted(terms),
        "reader": receipt["reader"],
        "command": receipt["command"],
        "exit_code": receipt["execution"]["exit_code"],
        "stdout_sha256": receipt["execution"]["stdout_sha256"],
        "finding": (
            "The retained frame-boundary index contains none of the exact "
            "completed-Level-B, Region-B replacement, transition-owner, "
            "movie-viewer or persistence leads. Pristine static bytes "
            "therefore own the selected instruction/ownership question."
        ),
    }


def _prior_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    loaded: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(path.is_file(), f"missing prior evidence: {path}")
        _require(_sha256(path) == spec["sha256"], f"{name} hash drifted")
        loaded[name] = json.loads(path.read_text())
        hashes[spec["path"]] = spec["sha256"]

    natural = loaded["lose_lifecycle"]["observations"]["natural_lose"]
    _require(
        natural["loader"]["entry"]["arguments"][:2]
        == ["0x0000002e", "0x00000000"]
        and natural["loader"]["entry"]["caller"] == "0x800500d8"
        and natural["loader"]["return"]["pc"] == "0x800500e0"
        and natural["endpoint"]["movie_reproducible"] is True,
        "natural LOSE anchor drifted",
    )
    continuation = next(
        row for row in loaded["lifecycle_continuations"]["continuations"]
        if row["id"] == "game_over_lose"
    )
    _require(
        continuation["return_pc"] == "0x800500E0"
        and continuation["window"]["sha256"]
        == EXPECTED_FUNCTION_SHA256["post_lose_return"]
        and continuation["direct_calls"] == [{
            "instruction": {
                "mnemonic": "jal 0x8005038c",
                "pc": "0x800500E4",
                "word": "0x0C0140E3",
            },
            "pc": "0x800500E4",
            "target": "0x8005038C",
        }],
        "LOSE continuation boundary drifted",
    )

    level_b = loaded["levelb_first_call"]
    observation = level_b["observation"]
    _require(
        level_b.get("schema") == "abl-phase4-fmv-levelb-first-call/1"
        and level_b.get("valid") is True
        and observation["first_call"] == {
            "cycle": 8142856967,
            "frame": 14382,
            "pc": "0x8005031c",
            "pre_delay_arguments": {
                "a0": "0x00000000",
                "a1": "0x00000000",
                "progress_id_s0": "0x00000001",
            },
        }
        and observation["loader_entry"]["selector"] == 11
        and observation["loader_entry"]["mode_signed"] == -1
        and observation["common_exit"]["ordered"] is True,
        "natural completed-Level-B anchor drifted",
    )
    level_b_continuation = next(
        row for row in loaded["lifecycle_continuations"]["continuations"]
        if row["id"] == "completed_level_b"
    )
    _require(
        level_b_continuation == {
            "direct_calls": [],
            "family": "level_b_progress_scan",
            "id": "completed_level_b",
            "loader_call": "0x8005031C",
            "owner": "fmv_sequence_completion_check",
            "return_pc": "0x80050324",
            "static_outcome": (
                "sums 16 progress bytes and selects finale D only when "
                "the total is 112"
            ),
            "window": {
                "end": "0x8005036C",
                "sha256": (
                    "38ce7971afec42c89fedb004d45765ff63b392b2fbe"
                    "71a9b9f4d4f5f36ccd5f9"
                ),
                "size": 72,
                "start": "0x80050324",
            },
        },
        "completed-Level-B continuation boundary drifted",
    )
    return loaded, hashes


def _semantic_sources() -> dict[str, str]:
    required = {
        "src/main/8005038c_scene_setup_and_load.c": [
            "display_buffers_init();",
            "resource_id_dat_load_dispatcher(0);",
        ],
        "src/main/8003f5b8_load_memory_bin.c": [
            "universal_file_loader",
            "g_800b5788",
        ],
        "src_re/fmv_lifecycle_continuations.c": [
            "Natural LOSE Region-B replacement ownership",
            "Completed-Level-B Region-B replacement ownership",
            "bits\\\\memory.bin",
            "0x800B5788",
            "E16",
            "C16",
            "0x8004FD74",
            "0x8005029C",
            "C17",
            "does not prove the first CD/DMA write cycle",
        ],
    }
    result = {}
    for rel, fragments in required.items():
        text = (ROOT / rel).read_text()
        _require(
            all(fragment in text for fragment in fragments),
            f"semantic source contract drifted: {rel}",
        )
        result[rel] = _sha256(ROOT / rel)
    return result


def build(
    *, exe_data: bytes | None = None, verify_identity: bool = True
) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)

    offline = _offline_localization()
    prior, prior_hashes = _prior_evidence()
    semantic_sources = _semantic_sources()
    instructions = {
        f"0x{address:08X}": _instruction(exe, address, expected)
        for address, expected in EXPECTED_WORDS.items()
    }
    functions = {
        name: _function(exe, name)
        for name in FUNCTIONS
    }

    _require(
        [int(row["target"], 16) for row in
         functions["display_buffers_init"]["direct_calls"]]
        == EXPECTED_DISPLAY_CALL_TARGETS,
        "display initializer call frontier drifted",
    )
    lose_materializations = _region_b_materializations(
        exe,
        [
            FUNCTIONS["post_lose_return"],
            FUNCTIONS["scene_setup_and_load"],
            FUNCTIONS["display_buffers_init"],
            (0x8003CF2C, 0x8003D318),
        ],
    )
    _require(
        lose_materializations == [{
            "lui_pc": "0x8003D308",
            "low_pc": "0x8003D30C",
            "register": 5,
            "value": "0x800B5788",
        }],
        "LOSE Region-B materialization census drifted",
    )
    level_b_materializations = _region_b_materializations(
        exe,
        [
            FUNCTIONS["post_level_b_return"],
            FUNCTIONS["scene_flow_dispatcher"],
            FUNCTIONS["scene_setup_and_load"],
            FUNCTIONS["display_buffers_init"],
            (0x8003CF2C, 0x8003D318),
        ],
    )
    _require(
        level_b_materializations == lose_materializations,
        "completed-Level-B Region-B materialization census drifted",
    )
    level_b_calls = functions["post_level_b_return"]["direct_calls"]
    _require(
        level_b_calls == [{
            "pc": "0x8005036C",
            "target": "0x8003E7C0",
            "word": "0x0C00F9F0",
            "mnemonic": "jal 0x8003e7c0",
        }],
        "post-Level-B call frontier drifted",
    )
    scene_flow_calls = functions["scene_flow_dispatcher"]["direct_calls"]
    scene_setup_calls = [
        row for row in scene_flow_calls
        if row["target"] == "0x8005038C"
    ]
    _require(
        scene_setup_calls == [
            {
                "pc": "0x8004FD74",
                "target": "0x8005038C",
                "word": "0x0C0140E3",
                "mnemonic": "jal 0x8005038c",
            },
            {
                "pc": "0x800500E4",
                "target": "0x8005038C",
                "word": "0x0C0140E3",
                "mnemonic": "jal 0x8005038c",
            },
            {
                "pc": "0x8005029C",
                "target": "0x8005038C",
                "word": "0x0C0140E3",
                "mnemonic": "jal 0x8005038c",
            },
        ],
        "scene-flow scene-setup call frontier drifted",
    )
    string_bytes = _slice(
        exe, MEMORY_BIN_STRING, MEMORY_BIN_STRING + len(b"bits\\memory.bin\0")
    )
    _require(
        string_bytes == b"bits\\memory.bin\0",
        "memory.bin resource string drifted",
    )

    claim = CONFIG["claim_boundary"]
    source_dependencies = {
        **semantic_sources,
        "asm/hand_written/80039478_display_buffers_init.s":
            _sha256(ROOT / "asm/hand_written/80039478_display_buffers_init.s"),
        "asm/hand_written/8004fca0_scene_flow_dispatcher.s":
            _sha256(ROOT / "asm/hand_written/8004fca0_scene_flow_dispatcher.s"),
        "asm/hand_written/800502c4_sub_800502c4.s":
            _sha256(ROOT / "asm/hand_written/800502c4_sub_800502c4.s"),
        "asm/hand_written/8003cf2c_resource_id_dat_load_dispatcher.s":
            _sha256(ROOT / "asm/hand_written/8003cf2c_resource_id_dat_load_dispatcher.s"),
        "asm/hand_written/80046330_universal_file_loader.s":
            _sha256(ROOT / "asm/hand_written/80046330_universal_file_loader.s"),
        "asm/hand_written/80045fc4_file_lookup_cdsearchfile.s":
            _sha256(ROOT / "asm/hand_written/80045fc4_file_lookup_cdsearchfile.s"),
        "config/phase4_fmv_region_b_replacement_ownership.yaml":
            _sha256(CONFIG_PATH),
        "tools/phase4_fmv_region_b_replacement_ownership.py":
            _sha256(Path(__file__)),
        "tools/phase4_offline_receipt_query.py":
            _sha256(ROOT / "tools/phase4_offline_receipt_query.py"),
    }

    return {
        "_comment": (
            "Generated from hash-verified pristine retail executable bytes, "
            "a closed derived-pristine offline query, and hash-pinned prior "
            "natural-LOSE/completed-Level-B evidence. No copyrighted input "
            "bytes are retained."
        ),
        "schema": "abl-phase4-fmv-region-b-replacement-ownership/2",
        "generated": "2026-07-28",
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "lane": CONFIG["lane"],
        "work_packet": {
            "selected_campaign": "fmv_playback",
            "coupled_rows": ["E15_fmv"],
            "first_unmet_dimension": "lifecycle",
            "claim": (
                "After the retained natural LOSE and completed-Level-B "
                "returns, the first caller-owned Region-B replacement "
                "requests both reach selector-zero bits\\memory.bin through "
                "the resident resource loader. E16 owns replacement bytes; "
                "C16 owns the LOSE choice and resident scene flow owns the "
                "completed-level conditional transition."
            ),
            "falsifier": (
                "Any earlier Region-B materialization or writer, nonzero "
                "resource selector, different file/destination, omitted "
                "scene-flow branch, direct save/viewer mutation, or "
                "unclassified transition edge falsifies the claim."
            ),
            "evidence_domain": "derived index plus pristine executable/C/ASM",
            "predicted_authoritative_layer":
                "generated ownership artifact and semantic C",
        },
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "sha256": _sha256_bytes(exe),
                "size": len(exe),
                "identity_verified": verify_identity,
            },
            "prior_evidence": prior_hashes,
        },
        "offline_localization": offline,
        "natural_anchor": {
            "selector": 46,
            "transition_hook_enabled": 0,
            "caller": "0x800500D8",
            "return_pc": "0x800500E0",
            "movie_reproducible": True,
            "source_artifact":
                "analysis/phase4_fmv_lose_lifecycle.json",
        },
        "completed_level_b_anchor": {
            "selector": 11,
            "transition_hook_enabled": -1,
            "caller": "0x8005031C",
            "return_pc": "0x80050324",
            "first_movie_frame": 14382,
            "scene_flow_entry_state_s0": 1,
            "completion_writer": "0x800B6B24",
            "common_exit_ordered": True,
            "source_artifact":
                "analysis/phase4_fmv_levelb_first_call.json",
        },
        "static_functions": functions,
        "static_instructions": instructions,
        "region_b_materialization_census": {
            "natural_lose_ordered_ranges": [
                "post_lose_return", "scene_setup_and_load",
                "display_buffers_init",
                "resource_dispatch_prefix_through_selector_zero_load",
            ],
            "completed_level_b_ordered_ranges": [
                "post_level_b_return", "scene_flow_dispatcher",
                "scene_setup_and_load", "display_buffers_init",
                "resource_dispatch_prefix_through_selector_zero_load",
            ],
            "natural_lose_matches": lose_materializations,
            "completed_level_b_matches": level_b_materializations,
            "unclassified_matches": [],
        },
        "replacement_chain": [
            {
                "stage": "C16_game_over_return",
                "pc": "0x800500E4",
                "operation": "scene_setup_and_load(5, 64)",
            },
            {
                "stage": "resident_scene_setup",
                "pc": "0x800503C4",
                "operation": "display_buffers_init()",
                "region_b_materializations": 0,
                "direct_call_targets":
                    [row["target"] for row in
                     functions["display_buffers_init"]["direct_calls"]],
            },
            {
                "stage": "resident_scene_setup",
                "pc": "0x800503CC",
                "operation": "resource_id_dat_load_dispatcher(0)",
            },
            {
                "stage": "E16_resource_dispatch",
                "pc": "0x8003D310",
                "selector": 0,
                "path": "bits\\memory.bin",
                "path_address": "0x8001ADFC",
                "destination": "0x800B5788",
                "operation": "universal_file_loader(path, destination)",
            },
            {
                "stage": "resident_file_loader",
                "pc": "0x8004641C",
                "operation":
                    "file_lookup_cdsearchfile(path, preserved_destination)",
            },
            {
                "stage": "resident_cd_transfer",
                "pc": "0x80046078",
                "operation": "CdRead(sectors, 0x800B5788, mode|0x80)",
                "destination_instruction": instructions["0x80046074"],
            },
        ],
        "completed_level_b_replacement_policy": {
            "player_return": {
                "pc": "0x80050324",
                "owner": "fmv_sequence_completion_check",
                "progress_bytes_read": 16,
                "all_complete_sum": 112,
                "ordinary_scene_flow_value": 0,
                "all_complete_scene_flow_value": 1,
                "optional_call": {
                    "pc": "0x8005036C",
                    "selector": 41,
                    "classification":
                        "same FMV.BIN reload, not Region-B replacement",
                },
                "region_b_materializations": 0,
            },
            "natural_scene_flow_join": {
                "caller_guard": instructions["0x80050134"],
                "caller": instructions["0x8005013C"],
                "return_pc": "0x80050144",
                "basis": (
                    "The retained s0=1 entry is the state-one call guarded "
                    "at 0x80050134. The completed owner publishes only "
                    "scene-flow values zero or one, so the immediate "
                    "state-five call at 0x80050214 is not selected."
                ),
            },
            "conditional_transition_requests": [
                {
                    "condition": "pending scene-flow request is negative",
                    "branch": instructions["0x8004FD6C"],
                    "call": instructions["0x8004FD74"],
                    "scene": 3,
                    "transition": 0,
                    "transition_argument":
                        instructions["0x8004FD78"],
                },
                {
                    "condition":
                        "pending scene-flow request is nonnegative",
                    "branch": instructions["0x80050248"],
                    "call": instructions["0x8005029C"],
                    "scene": 6,
                    "transition": 128,
                    "scene_argument": instructions["0x8005024C"],
                    "transition_argument":
                        instructions["0x800502A0"],
                },
            ],
            "common_resource_policy": {
                "scene_setup_non_skip_transitions": [0, 128],
                "resource_dispatch_selector": 0,
                "path": "bits\\memory.bin",
                "destination": "0x800B5788",
                "byte_owner": "E16_streaming_overlays",
                "transition_owner": "resident_scene_flow_dispatcher",
            },
            "persistence_partition": {
                "ordinary_progress_scan_calls_save_serializer": False,
                "ordinary_progress_scan_writes_movie_viewer_unlock": False,
                "all_complete_sets_scene_flag_at": "0x8009B888",
                "c17_movie_viewer_unlock_field": "0x8009B889",
                "c17_unlock_field_written": False,
                "e14_serialization_policy_claimed": False,
                "classification": (
                    "The selected code reads the 16-byte progress table and "
                    "publishes transition state. The all-complete branch "
                    "sets an adjacent scene flag; whether that flag is "
                    "serialized remains E14/C17 debt."
                ),
            },
        },
        "ownership": {
            "replacement_byte_owner": "E16_streaming_overlays",
            "lose_transition_choice_owner":
                "C16_death_lives_game_over",
            "completed_level_b_transition_choice_owner":
                "resident_scene_flow_dispatcher",
            "E14_frontend_save_intersects_selected_path": False,
            "C17_movie_viewer_unlock_intersects_selected_path": False,
            "classification": (
                "C16 selects scene 5/transition 64 for LOSE. Completed-Level-B "
                "returns to one scene-flow owner with scene 3/transition 0 or "
                "scene 6/transition 128. Every branch reaches E16 selector "
                "zero and requests bits\\memory.bin into Region B."
            ),
            "first_byte_cycle_claimed": False,
        },
        "falsifier": {
            "outcome": "survived",
            "checks": {
                "natural_anchor_exact": True,
                "post_return_call_exact": True,
                "display_frontier_excludes_region_b_and_loaders": True,
                "selector_zero_exact": True,
                "first_region_b_materialization_unique": True,
                "memory_bin_path_exact": True,
                "universal_loader_destination_preserved": True,
                "cdread_destination_exact": True,
                "completed_level_b_anchor_exact": True,
                "natural_state_one_scene_flow_join_exact": True,
                "completed_level_b_post_return_calls_classified": True,
                "completed_level_b_region_b_materializations_zero": True,
                "conditional_scene_setup_frontier_complete": True,
                "both_scene_setup_transitions_execute_resource_selector_zero":
                    True,
                "c17_unlock_field_not_written": True,
                "e14_serialization_not_inferred": True,
                "unclassified_transition_edges_zero": True,
            },
        },
        "claim_boundary": claim,
        "source_dependencies": source_dependencies,
        "summary": {
            "closed_sub_boundaries": 2,
            "region_b_materializations_per_chain":
                len(lose_materializations),
            "unclassified_region_b_materializations": 0,
            "display_direct_calls": len(EXPECTED_DISPLAY_CALL_TARGETS),
            "level_b_conditional_transition_requests": 2,
            "offline_zero_match_terms":
                len(offline["zero_match_terms"]),
            "dimension_promoted": claim["dimension_promoted"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(payload)
        print(f"WROTE {OUTPUT.relative_to(ROOT)}")
        return 0
    _require(OUTPUT.is_file(), f"missing generated artifact: {OUTPUT}")
    _require(OUTPUT.read_text() == payload, f"stale generated artifact: {OUTPUT}")
    print(
        "PASS: FMV LOSE/completed-Level-B Region-B replacement ownership "
        "(E16 bytes, distinct transition owners, lifecycle not promoted)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
