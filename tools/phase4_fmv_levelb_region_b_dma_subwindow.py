#!/usr/bin/env python3
"""Reconstruct the exact-PC subwindow for the next E15 Region-B DMA run."""
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
import phase4_common as common


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/phase4_fmv_levelb_region_b_dma_subwindow.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_levelb_region_b_dma_subwindow.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
MEMORY_REL = "BITS/MEMORY.BIN"
MEMORY_PATH = ROOT / "REBUILD/files" / MEMORY_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
CDREAD = 0x80070698

FUNCTIONS = {
    "resource_selector_zero_path": (0x8003D2F8, 0x8003D318),
    "universal_file_loader": (0x80046330, 0x80046538),
    "file_lookup_cdsearchfile": (0x80045FC4, 0x800460E4),
    "selected_transfer_subwindow": (0x80046078, 0x800460C8),
    "other_cdread_wrapper": (0x8006FFB0, 0x8007001C),
}

EXPECTED_FUNCTION_SHA256 = {
    "resource_selector_zero_path":
        "d23c1e881ffe8d666969334095c15d26fee7a772d60f1a492d8c873104d9b9fc",
    "universal_file_loader":
        "060b385746f65e02f70cc95cbeedff8fbb0cc6c951b238294526e248701a9e28",
    "file_lookup_cdsearchfile":
        "37b4f2f8ea955f11a4e8d6d86a067b65bc5a1061c48f868ed4f10bb71e73502a",
    "selected_transfer_subwindow":
        "bb3fe5cd00ed4f8df9d787cf3d5ac9db5b2174a941a0ca6ce816909d21808a31",
    "other_cdread_wrapper":
        "9cd6d313e1e9db05085b221dd37f659cce45da8d28d626dcc6e0168c7229cd57",
}

EXPECTED_WORDS = {
    0x800503CC: 0x0C00F3CB,
    0x800503D0: 0x00002021,
    0x8003D2F8: 0x1680000D,
    0x8003D308: 0x3C05800B,
    0x8003D30C: 0x24A55788,
    0x8003D310: 0x0C0118CC,
    0x80046340: 0x00A0F021,
    0x8004641C: 0x0C0117F1,
    0x80046420: 0x03C02821,
    0x80045FD4: 0x00A09821,
    0x80046050: 0x001132C0,
    0x80046054: 0x0206102A,
    0x80046058: 0x10400005,
    0x8004605C: 0x02702821,
    0x80046068: 0x0C017DE7,
    0x8004606C: 0x00D03023,
    0x80046070: 0x02202021,
    0x80046074: 0x02602821,
    0x80046078: 0x0C01C1A6,
    0x8004607C: 0x36460080,
    0x80046080: 0x14400003,
    0x80046088: 0x08011831,
    0x80046090: 0x0C01C1E7,
    0x80046098: 0x1C40FFFD,
    0x800460A8: 0x10400005,
    0x800460B8: 0x0C017DE7,
    0x800460C0: 0x02001021,
    0x800460C4: 0x8FBF0038,
    0x8006FFEC: 0x0C01C1A6,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            value = common.load_json(OUTPUT).get("generated")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return date.today().isoformat()


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
    rows = []
    for pc in range(start, end, 4):
        word = _word(data, pc)
        target = _jal_target(pc, word)
        if target is not None:
            rows.append({
                "pc": f"0x{pc:08X}",
                "target": f"0x{target:08X}",
                "word": f"0x{word:08X}",
                "mnemonic": exe_read.disasm_one(pc, word),
            })
    return rows


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
        "bytes": len(body),
        "sha256": digest,
        "direct_calls": _direct_calls(data, start, end),
    }


def _all_cdread_calls(data: bytes) -> list[dict[str, str]]:
    rows = []
    for offset in range(EXE_HEADER, len(data) - 3, 4):
        pc = EXE_BASE + offset - EXE_HEADER
        word = struct.unpack_from("<I", data, offset)[0]
        if _jal_target(pc, word) == CDREAD:
            rows.append({
                "pc": f"0x{pc:08X}",
                "word": f"0x{word:08X}",
                "classification": (
                    "selected_memory_bin_file_helper"
                    if pc == 0x80046078
                    else "separate_resident_cdread_wrapper"
                ),
            })
    return rows


def _work_packet() -> dict[str, Any]:
    spec = CONFIG["work_packet"]
    path = RUN_ROOT / spec["relative_path"]
    _require(
        path.is_file()
        and common.sha256(path) == spec["sha256"]
        and path.stat().st_size == spec["bytes"],
        "iteration work packet identity drifted",
    )
    packet = common.load_json(path)
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIG["campaign_id"]
        and packet.get("row_ids") == [CONFIG["row_id"]]
        and packet.get("first_unmet_dimension") == CONFIG["dimension"]
        and packet.get("next_lane") == "static"
        and "latest safe exact late-arm boundary" in packet.get("claim", "")
        and "fails to preserve destination 0x800B5788" in
        packet.get("falsifier", ""),
        "iteration work packet semantic boundary drifted",
    )
    return {
        "sha256": spec["sha256"],
        "selected_campaign": packet["campaign_id"],
        "rows": packet["row_ids"],
        "first_unmet_dimension": packet["first_unmet_dimension"],
        "claim": packet["claim"],
        "falsifier": packet["falsifier"],
        "evidence_domain": packet["evidence_domain"],
        "predicted_authoritative_machine_layer":
            packet["predicted_authoritative_machine_layer"],
    }


def _prior_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    loaded: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(
            path.is_file() and common.sha256(path) == spec["sha256"],
            f"{name} evidence identity drifted",
        )
        loaded[name] = common.load_json(path)
        hashes[spec["path"]] = spec["sha256"]

    replacement = loaded["replacement_ownership"]
    _require(
        replacement.get("schema")
        == "abl-phase4-fmv-region-b-replacement-ownership/2"
        and replacement["completed_level_b_anchor"]["return_pc"]
        == "0x80050324"
        and replacement["completed_level_b_replacement_policy"]
        ["common_resource_policy"] == {
            "byte_owner": "E16_streaming_overlays",
            "destination": "0x800B5788",
            "path": r"bits\memory.bin",
            "resource_dispatch_selector": 0,
            "scene_setup_non_skip_transitions": [0, 128],
            "transition_owner": "resident_scene_flow_dispatcher",
        }
        and replacement["falsifier"]["outcome"] == "survived",
        "completed-Level-B replacement ownership drifted",
    )
    natural = loaded["natural_level_b"]
    _require(
        natural.get("valid") is True
        and natural["observation"]["common_exit"]["ordered"] is True
        and natural["observation"]["common_exit"]["callback_teardown"]["frame"]
        == CONFIG["expected"]["teardown_frame"],
        "natural Level-B teardown anchor drifted",
    )
    rejected = loaded["rejected_late_dma"]
    _require(
        rejected["falsifier"]["method_outcome"] == "rejected"
        and rejected["observation"]["precise"]["receipt_present"] is False
        and rejected["observation"]["precise"]["dma_events_admitted"] == 0
        and rejected["claim_boundary"]["next_lane"] == "static",
        "rejected late-DMA method boundary drifted",
    )
    return loaded, hashes


def _reused_offline() -> dict[str, Any]:
    spec = CONFIG["reused_offline_query"]
    root = Path(spec["run_root"]).resolve()
    path = (root / spec["receipt"]["relative_path"]).resolve()
    _require(
        root in path.parents
        and path.is_file()
        and common.sha256(path) == spec["receipt"]["sha256"],
        "reused offline receipt identity drifted",
    )
    receipt = common.load_json(path)
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0
        and any(
            row.get("sha256") == spec["external_index_sha256"]
            for row in receipt.get("external_inputs") or []
        ),
        "reused offline receipt is not closed over the retained index",
    )
    return {
        "receipt_sha256": spec["receipt"]["sha256"],
        "external_index_sha256": spec["external_index_sha256"],
        "counted_as_iteration_2_query": False,
        "answer": (
            "The retained derived-pristine index has no exact DMA/CD/"
            "Region-B event or instruction attribution for this route. "
            "No duplicate offline query was opened."
        ),
    }


def _semantic_sources() -> dict[str, str]:
    required = {
        "src/main/8005038c_scene_setup_and_load.c": [
            "resource_id_dat_load_dispatcher(0);",
        ],
        "src/main/8003f5b8_load_memory_bin.c": [
            "universal_file_loader",
            "g_800b5788",
        ],
        "src_re/fmv_levelb_region_b_dma_subwindow.c": [
            "not matching source",
            "0x80046078",
            "0x800460C4",
            "36,448-byte",
            "18",
            "Both copies are CPU operations, not CD-ROM DMA events",
            "does not prove that the native read",
            "succeeds or identify any DMA event",
        ],
    }
    hashes = {}
    for rel, fragments in required.items():
        path = ROOT / rel
        text = path.read_text()
        _require(
            all(fragment in text for fragment in fragments),
            f"semantic source contract drifted: {rel}",
        )
        hashes[rel] = common.sha256(path)
    return hashes


def build(
    *,
    exe_data: bytes | None = None,
    memory_data: bytes | None = None,
    verify_identity: bool = True,
) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    memory = MEMORY_PATH.read_bytes() if memory_data is None else memory_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(MEMORY_REL, memory)

    packet = _work_packet()
    _, prior_hashes = _prior_evidence()
    offline = _reused_offline()
    sources = _semantic_sources()
    expected = CONFIG["expected"]

    _require(
        len(memory) == expected["memory_bin_bytes"],
        "pristine MEMORY.BIN byte extent drifted",
    )
    sectors = (len(memory) + expected["sector_bytes"] - 1) // (
        expected["sector_bytes"]
    )
    padded_bytes = sectors * expected["sector_bytes"]
    _require(
        sectors == expected["sector_count"]
        and padded_bytes == expected["padded_transfer_bytes"],
        "MEMORY.BIN transfer geometry drifted",
    )

    instructions = {
        f"0x{pc:08X}": _instruction(exe, pc, word)
        for pc, word in EXPECTED_WORDS.items()
    }
    functions = {name: _function(exe, name) for name in FUNCTIONS}
    all_cdread = _all_cdread_calls(exe)
    _require(
        all_cdread == [
            {
                "pc": "0x80046078",
                "word": "0x0C01C1A6",
                "classification": "selected_memory_bin_file_helper",
            },
            {
                "pc": "0x8006FFEC",
                "word": "0x0C01C1A6",
                "classification": "separate_resident_cdread_wrapper",
            },
        ],
        "global CdRead direct-call census drifted",
    )
    subwindow_calls = functions["selected_transfer_subwindow"]["direct_calls"]
    _require(
        subwindow_calls == [
            {
                "pc": "0x80046078",
                "target": "0x80070698",
                "word": "0x0C01C1A6",
                "mnemonic": "jal 0x80070698",
            },
            {
                "pc": "0x80046090",
                "target": "0x8007079C",
                "word": "0x0C01C1E7",
                "mnemonic": "jal 0x8007079c",
            },
            {
                "pc": "0x800460B8",
                "target": "0x8005F79C",
                "word": "0x0C017DE7",
                "mnemonic": "jal 0x8005f79c",
            },
        ],
        "selected transfer subwindow call frontier drifted",
    )
    _require(
        not any(
            _word(exe, pc) >> 26 == 0
            and (_word(exe, pc) & 0x3F) == 9
            for start, end in FUNCTIONS.values()
            for pc in range(start, end, 4)
        ),
        "selected function set gained an indirect call",
    )

    source_dependencies = {
        **sources,
        "asm/hand_written/800502c4_sub_800502c4.s":
            common.sha256(
                ROOT / "asm/hand_written/800502c4_sub_800502c4.s"
            ),
        "asm/hand_written/8004fca0_scene_flow_dispatcher.s":
            common.sha256(
                ROOT /
                "asm/hand_written/8004fca0_scene_flow_dispatcher.s"
            ),
        "asm/hand_written/8003cf2c_resource_id_dat_load_dispatcher.s":
            common.sha256(
                ROOT /
                "asm/hand_written/8003cf2c_resource_id_dat_load_dispatcher.s"
            ),
        "asm/hand_written/80046330_universal_file_loader.s":
            common.sha256(
                ROOT /
                "asm/hand_written/80046330_universal_file_loader.s"
            ),
        "asm/hand_written/80045fc4_file_lookup_cdsearchfile.s":
            common.sha256(
                ROOT /
                "asm/hand_written/80045fc4_file_lookup_cdsearchfile.s"
            ),
        "config/phase4_fmv_levelb_region_b_dma_subwindow.yaml":
            common.sha256(CONFIG_PATH),
        "tools/phase4_fmv_levelb_region_b_dma_subwindow.py":
            common.sha256(Path(__file__)),
    }

    return {
        "_comment": (
            "Generated from hash-verified pristine retail executable and "
            "MEMORY.BIN bytes plus retained low-level E15 evidence. No "
            "copyrighted input bytes are retained."
        ),
        "schema": "abl-phase4-fmv-levelb-region-b-dma-subwindow/1",
        "generated": _stable_generated(),
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "lane": CONFIG["lane"],
        "work_packet": packet,
        "offline_reuse": offline,
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "sha256": _sha256_bytes(exe),
                "bytes": len(exe),
                "identity_verified": verify_identity,
            },
            "memory_bin": {
                "path": f"REBUILD/files/{MEMORY_REL}",
                "sha256": _sha256_bytes(memory),
                "bytes": len(memory),
                "identity_verified": verify_identity,
                "media_class": "pristine_authority",
            },
            "prior_evidence": prior_hashes,
        },
        "natural_anchor": {
            "completed_level_b_return_pc": "0x80050324",
            "common_teardown_frame": expected["teardown_frame"],
            "resource_selector": 0,
            "resource_path": r"bits\memory.bin",
            "destination": expected["region_b_base"],
        },
        "transfer_geometry": {
            "file_bytes": len(memory),
            "sector_bytes": expected["sector_bytes"],
            "sector_count": sectors,
            "padded_transfer_bytes": padded_bytes,
            "sector_tail_overlap_bytes": padded_bytes - len(memory),
            "pre_cdread_tail_save": {
                "pc": "0x80046068",
                "destination": "0x8009B890",
                "source": "0x800B5788+36448",
                "bytes": padded_bytes - len(memory),
            },
            "post_cdread_tail_restore": {
                "pc": "0x800460B8",
                "destination": "0x800B5788+36448",
                "source": "0x8009B890",
                "bytes": padded_bytes - len(memory),
            },
            "tail_copies_are_dma": False,
        },
        "destination_liveness": [
            {
                "pc": "0x800503CC",
                "fact": "scene setup calls resource selector zero",
                "delay_slot": instructions["0x800503D0"],
            },
            {
                "pc": "0x8003D308",
                "fact": "selector zero materializes a1=0x800B5788",
                "low_half": instructions["0x8003D30C"],
                "callee": instructions["0x8003D310"],
            },
            {
                "pc": "0x80046340",
                "fact": "universal_file_loader preserves a1 in fp",
                "instruction": instructions["0x80046340"],
            },
            {
                "pc": "0x8004641C",
                "fact": "file helper call restores a1 from fp",
                "delay_slot": instructions["0x80046420"],
            },
            {
                "pc": "0x80045FD4",
                "fact": "file helper preserves a1 in s3",
                "instruction": instructions["0x80045FD4"],
            },
            {
                "pc": "0x80046074",
                "fact": "CdRead a1 is restored from s3",
                "instruction": instructions["0x80046074"],
            },
        ],
        "static_functions": functions,
        "static_instructions": instructions,
        "cdread_direct_call_census": {
            "target": "0x80070698",
            "all_resident_calls": all_cdread,
            "selected_path_calls": ["0x80046078"],
            "unclassified_calls": [],
        },
        "exact_pc_subwindow": {
            "start": {
                "pc": expected["pre_submit_pc"],
                "boundary": "before_instruction",
                "instruction": instructions["0x80046078"],
                "register_assertions": {
                    "a0": sectors,
                    "a1": expected["region_b_base"],
                },
                "actions_after_stop_before_resume": [
                    "transferLog.clear",
                    "transferLog.start",
                ],
            },
            "stop": {
                "pc": expected["common_post_transfer_pc"],
                "boundary": "before_instruction",
                "instruction": instructions["0x800460C4"],
                "reached_by": [
                    "failed CdRead submission",
                    "completed CdReadSync path",
                ],
            },
            "direct_calls_between_stops": subwindow_calls,
            "cdread_submissions_between_stops": 1,
            "later_universal_loader_retry_excluded": True,
            "prior_fmv_transfer_history_excluded_by_clear": True,
            "transfer_log_capacity": expected["transfer_log_capacity"],
            "finite": True,
            "causality_scope": (
                "one CdRead submission, its CdReadSync wait and optional "
                "post-read CPU tail restore"
            ),
        },
        "falsifier": {
            "outcome": "survived",
            "checks": {
                "work_packet_identity_exact": True,
                "pristine_executable_identity_exact": verify_identity,
                "pristine_memory_bin_identity_exact": verify_identity,
                "retained_offline_query_reused_not_repeated": True,
                "natural_teardown_frame_exact": True,
                "replacement_owner_predecessor_contract_survived": True,
                "memory_bin_sector_count_exact": True,
                "sector_tail_save_restore_classified": True,
                "destination_liveness_complete": True,
                "selected_cdread_call_unique": True,
                "global_cdread_calls_classified": True,
                "indirect_calls_in_selected_function_set_zero": True,
                "common_stop_reached_by_success_and_failure": True,
                "later_loader_retry_outside_subwindow": True,
            },
        },
        "claim_boundary": CONFIG["claim_boundary"],
        "source_dependencies": source_dependencies,
        "summary": {
            "selected_cdread_calls": 1,
            "global_cdread_calls": len(all_cdread),
            "unclassified_cdread_calls": 0,
            "transfer_sectors": sectors,
            "sector_tail_overlap_bytes": padded_bytes - len(memory),
            "exact_pc_stops": 2,
            "new_offline_queries": 0,
            "new_live_receipts": 0,
            "dimension_promoted": False,
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
    _require(
        OUTPUT.read_text() == payload,
        f"stale generated artifact: {OUTPUT}",
    )
    print(
        "PASS: completed-Level-B Region-B DMA exact-PC subwindow "
        "(one 18-sector submission; no DMA result or dimension promoted)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
