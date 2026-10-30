#!/usr/bin/env python3
"""Re-localize E15's completed-Level-B replacement before frame 15816."""
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
CONFIG_PATH = ROOT / "config/phase4_fmv_levelb_transition_relocalization.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_levelb_transition_relocalization.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

FUNCTIONS = {
    "scene_flow_dispatcher": (0x8004FCA0, 0x800502C4),
    "scene_setup_and_load": (0x8005038C, 0x800503FC),
    "resource_selector_zero_path": (0x8003D2F8, 0x8003D318),
}
EXPECTED_FUNCTION_SHA256 = {
    "scene_flow_dispatcher":
        "02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f",
    "scene_setup_and_load":
        "6c12e5e6c9416b4e7aa2223c3ead0d3478ad65faa97c82098b223e494e61fddb",
    "resource_selector_zero_path":
        "d23c1e881ffe8d666969334095c15d26fee7a772d60f1a492d8c873104d9b9fc",
}
EXPECTED_WORDS = {
    0x8004FD6C: 0x0441000C,
    0x8004FD70: 0x24040003,
    0x8004FD74: 0x0C0140E3,
    0x8004FD78: 0x00002821,
    0x8004FDF8: 0x14400128,
    0x8004FDFC: 0x24040006,
    0x8004FEA4: 0x3C028008,
    0x80050124: 0x0441005D,
    0x80050128: 0x24040006,
    0x80050248: 0x04410014,
    0x8005024C: 0x24040006,
    0x8005029C: 0x0C0140E3,
    0x800502A0: 0x24050080,
    0x800503B0: 0x10A20008,
    0x800503CC: 0x0C00F3CB,
    0x800503D0: 0x00002021,
    0x8003D2F8: 0x1680000D,
    0x8003D300: 0x3C048002,
    0x8003D304: 0x2484ADFC,
    0x8003D308: 0x3C05800B,
    0x8003D30C: 0x24A55788,
    0x8003D310: 0x0C0118CC,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return common.sha256(path)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_generated() -> str:
    if OUTPUT.is_file():
        try:
            generated = common.load_json(OUTPUT).get("generated")
            if isinstance(generated, str) and generated:
                return generated
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


def _word(data: bytes, pc: int) -> int:
    return struct.unpack("<I", _slice(data, pc, pc + 4))[0]


def _jal_target(pc: int, word: int) -> int | None:
    if word >> 26 != 3:
        return None
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def _branch_target(pc: int, word: int) -> int | None:
    if word >> 26 not in {1, 4, 5, 6, 7}:
        return None
    immediate = word & 0xFFFF
    if immediate & 0x8000:
        immediate -= 0x10000
    return pc + 4 + immediate * 4


def _instruction(data: bytes, pc: int) -> dict[str, str]:
    expected = EXPECTED_WORDS[pc]
    word = _word(data, pc)
    _require(
        word == expected,
        f"opcode drift at 0x{pc:08X}: 0x{word:08X} != 0x{expected:08X}",
    )
    return {
        "pc": f"0x{pc:08X}",
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(pc, word),
    }


def _direct_calls(data: bytes, start: int, end: int) -> list[dict[str, str]]:
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
        f"{name} function identity drifted",
    )
    return {
        "start": f"0x{start:08X}",
        "end": f"0x{end:08X}",
        "bytes": len(body),
        "sha256": digest,
        "direct_calls": _direct_calls(data, start, end),
    }


def _artifact(spec: dict[str, Any], *, run: bool = False) -> tuple[Path, dict[str, Any]]:
    base = RUN_ROOT if run else ROOT
    relative = spec.get("relative_path") if run else spec.get("path")
    path = base / relative
    _require(
        path.is_file() and _sha256(path) == spec["sha256"],
        f"artifact identity drifted: {relative}",
    )
    return path, common.load_json(path)


def _work_packet() -> tuple[dict[str, Any], dict[str, str]]:
    path, packet = _artifact(CONFIG["work_packet"], run=True)
    _require(path.stat().st_size == CONFIG["work_packet"]["bytes"],
             "work packet byte size drifted")
    predicted = packet.get("predicted_authoritative_machine_layer", {})
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIG["campaign_id"]
        and packet.get("row_ids") == [CONFIG["row_id"]]
        and packet.get("first_unmet_dimension") == CONFIG["dimension"]
        and packet.get("next_lane") == CONFIG["lane"]
        and "0x8004FD74 and 0x8005029C" in packet.get("exact_claim", "")
        and "retained exact-PC falsifier" in
        packet.get("explicit_falsifier", "")
        and predicted.get("artifact") ==
        "analysis/phase4_fmv_levelb_transition_relocalization.json",
        "work packet semantic boundary drifted",
    )
    token = f"run:{CONFIG['work_packet']['relative_path']}"
    return packet, {token: CONFIG["work_packet"]["sha256"]}


def _offline_anchor() -> tuple[dict[str, Any], dict[str, str]]:
    source = CONFIG["offline_anchor_query"]
    receipt_path, receipt = _artifact(source["receipt"], run=True)
    output_path, output = _artifact(source["output"], run=True)
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0
        and receipt.get("reader") == {
            "path": source["reader_path"],
            "scope": "repo",
            "sha256": source["reader_sha256"],
        }
        and receipt.get("external_inputs", [{}])[0].get("sha256")
        == source["input_sha256"]
        and receipt.get("outputs", [{}])[0].get("sha256")
        == source["output"]["sha256"]
        and receipt.get("query") == output.get("query"),
        "offline anchor receipt is not closed",
    )
    expected = CONFIG["expected"]["anchor"]
    result = output.get("result", {})
    anchor = result.get("anchor", {})
    memory = result.get("memory", {})
    _require(
        output.get("schema")
        == "abl-phase4-offline-atomic-anchor-projection/1"
        and output.get("source", {}).get("sha256") == source["input_sha256"]
        and anchor.get("frame") == expected["frame"]
        and anchor.get("cycle") == expected["cycle"]
        and anchor.get("pc", "").upper() == expected["pc"].upper()
        and anchor.get("paused") is True
        and memory.get("address") == "0x800B5788"
        and memory.get("length") == 256
        and memory.get("sha256") == expected["region_b_head_sha256"]
        and memory.get("retired_memory_sha256")
        == expected["retired_fmv_head_sha256"]
        and memory.get("retired_memory_absent") is True
        and memory.get("payload_retained") is False,
        "offline anchor projection drifted",
    )
    return output, {
        f"run:{source['receipt']['relative_path']}":
            source["receipt"]["sha256"],
        f"run:{source['output']['relative_path']}":
            source["output"]["sha256"],
    }


def _prior_evidence() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    loaded = {}
    hashes = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path, document = _artifact(spec)
        loaded[name] = document
        hashes[spec["path"]] = spec["sha256"]
    replacement = loaded["replacement_ownership"]
    subwindow = loaded["exact_pc_subwindow"]
    exact_result = loaded["exact_pc_falsifier"]
    transition_requests = (
        replacement.get("completed_level_b_replacement_policy", {})
        .get("conditional_transition_requests", [])
    )
    _require(
        replacement.get("falsifier", {}).get("outcome") == "survived"
        and replacement.get("completed_level_b_anchor", {}).get("return_pc")
        == "0x80050324"
        and replacement.get("completed_level_b_replacement_policy", {})
        .get("common_resource_policy", {}).get("path") == r"bits\memory.bin"
        and [
            {
                "call": row.get("call"),
                "scene": row.get("scene"),
                "transition": row.get("transition"),
            }
            for row in transition_requests
        ] == [
            {
                "call": replacement["static_instructions"]["0x8004FD74"],
                "scene": 3,
                "transition": 0,
            },
            {
                "call": replacement["static_instructions"]["0x8005029C"],
                "scene": 6,
                "transition": 128,
            },
        ],
        "replacement ownership predecessor contract drifted",
    )
    _require(
        subwindow.get("falsifier", {}).get("outcome") == "survived"
        and subwindow.get("exact_pc_subwindow", {}).get("start", {})
        .get("pc") == "0x80046078"
        and subwindow.get("exact_pc_subwindow", {}).get("stop", {})
        .get("pc") == "0x800460C4"
        and subwindow.get("claim_boundary", {}).get("dimension_promoted")
        is False,
        "exact-PC static subwindow drifted",
    )
    _require(
        exact_result.get("valid") is True
        and exact_result.get("falsifier", {}).get("outcome")
        == "falsified_repeated"
        and exact_result.get("observation", {}).get("exact_pc_repeat_equal")
        is True
        and exact_result.get("claim_boundary", {}).get("exact_pc_stop_observed")
        is False
        and exact_result.get("claim_boundary", {}).get("dimension_promoted")
        is False,
        "retained exact-PC falsifier drifted",
    )
    return loaded, hashes


def _semantic_sources() -> dict[str, str]:
    required = {
        "src/main/8005038c_scene_setup_and_load.c": [
            "if (scene_id != -1)",
            "resource_id_dat_load_dispatcher(0);",
        ],
        "src_re/fmv_lifecycle_continuations.c": [
            "0x8004FD74",
            "0x8005029C",
            r"bits\\memory.bin",
            "0x800B5788",
        ],
        "src_re/fmv_levelb_transition_relocalization.c": [
            "0x8004FEA4",
            "0x8004FD74",
            "0x8005029C",
            "first-hit stop",
            "not establish a DMA event",
        ],
    }
    result = {}
    for relative, fragments in required.items():
        path = ROOT / relative
        text = path.read_text()
        _require(
            all(fragment in text for fragment in fragments),
            f"semantic source contract drifted: {relative}",
        )
        result[relative] = _sha256(path)
    return result


def _external_asm() -> dict[str, str]:
    relative = "asm/hand_written/8004fca0_scene_flow_dispatcher.s"
    path = ROOT / relative
    expected = "80c4643d6584bb0706a6905b939a76225dc0fa92d6c9eebf526337969d349098"
    manifest = (ROOT / "tools/repro_inputs.sha256").read_text()
    _require(
        path.is_file() and _sha256(path) == expected
        and f"{expected}  {relative}" in manifest,
        "scene-flow external ASM pin drifted",
    )
    return {relative: expected}


def _incoming_nonnegative_edges(
        data: bytes, start: int, end: int
) -> list[dict[str, Any]]:
    rows = []
    for pc in range(start, end, 4):
        word = _word(data, pc)
        if _branch_target(pc, word) != 0x8005029C:
            continue
        delay = _word(data, pc + 4)
        rows.append({
            "pc": f"0x{pc:08X}",
            "instruction": exe_read.disasm_one(pc, word),
            "word": f"0x{word:08X}",
            "target": "0x8005029C",
            "delay_pc": f"0x{pc + 4:08X}",
            "delay_instruction": exe_read.disasm_one(pc + 4, delay),
            "delay_word": f"0x{delay:08X}",
            "a0": 6,
        })
    _require(
        [row["pc"] for row in rows]
        == ["0x8004FDF8", "0x80050124", "0x80050248"]
        and all(row["delay_word"] == "0x24040006" for row in rows),
        "nonnegative scene-setup predecessor frontier drifted",
    )
    return rows


def build(*, exe_data: bytes | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)

    packet, packet_hashes = _work_packet()
    offline, offline_hashes = _offline_anchor()
    prior, prior_hashes = _prior_evidence()
    semantic_sources = _semantic_sources()
    external_asm = _external_asm()
    instructions = {
        f"0x{pc:08X}": _instruction(exe, pc)
        for pc in EXPECTED_WORDS
    }
    functions = {
        name: _function(exe, name)
        for name in FUNCTIONS
    }

    scene_calls = [
        row for row in functions["scene_flow_dispatcher"]["direct_calls"]
        if row["target"] == CONFIG["expected"]["scene_setup_target"]
    ]
    _require(
        [row["pc"] for row in scene_calls]
        == ["0x8004FD74", "0x800500E4", "0x8005029C"],
        "scene-setup direct-call census drifted",
    )
    completed_boundaries = [
        row for row in scene_calls
        if row["pc"] in {"0x8004FD74", "0x8005029C"}
    ]
    _require(
        [row["pc"] for row in completed_boundaries]
        == ["0x8004FD74", "0x8005029C"],
        "completed-Level-B earlier boundary set drifted",
    )
    setup_calls = functions["scene_setup_and_load"]["direct_calls"]
    _require(
        [row["pc"] for row in setup_calls]
        == ["0x800503C4", "0x800503CC", "0x800503D4"]
        and setup_calls[1]["target"] == "0x8003CF2C",
        "scene-setup resource call frontier drifted",
    )
    selector_calls = functions["resource_selector_zero_path"]["direct_calls"]
    _require(
        selector_calls == [{
            "pc": "0x8003D310",
            "target": "0x80046330",
            "word": "0x0C0118CC",
            "mnemonic": "jal 0x80046330",
        }],
        "selector-zero universal-loader call drifted",
    )

    anchor = offline["result"]["anchor"]
    memory = offline["result"]["memory"]
    expected_boundaries = CONFIG["expected"]["earlier_boundaries"]
    boundary_rows = [
        {
            **expected,
            "call": instructions[expected["pc"]],
            "target": CONFIG["expected"]["scene_setup_target"],
            "pre_instruction": True,
            "resource_skip_sentinel_excluded": expected["a1"] != -1,
        }
        for expected in expected_boundaries
    ]
    source_dependencies = {
        "config/phase4_fmv_levelb_transition_relocalization.yaml":
            _sha256(CONFIG_PATH),
        CONFIG["offline_anchor_query"]["reader_path"]:
            CONFIG["offline_anchor_query"]["reader_sha256"],
        **prior_hashes,
        **semantic_sources,
        **external_asm,
    }
    return {
        "schema": "abl-phase4-fmv-levelb-transition-relocalization/1",
        "generated": _stable_generated(),
        "_comment": (
            "Generated from a closed derived-pristine atomic-anchor query, "
            "hash-verified pristine executable bytes and hash-pinned semantic/"
            "external ASM sources. No captured or copyrighted payload is retained."
        ),
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "work_packet": {
            "sha256": CONFIG["work_packet"]["sha256"],
            "exact_claim": packet["exact_claim"],
            "explicit_falsifier": packet["explicit_falsifier"],
            "evidence_domain": packet["evidence_domain"],
        },
        "offline_localization": {
            "receipt_sha256":
                CONFIG["offline_anchor_query"]["receipt"]["sha256"],
            "output_sha256":
                CONFIG["offline_anchor_query"]["output"]["sha256"],
            "input_sha256": CONFIG["offline_anchor_query"]["input_sha256"],
            "reader_sha256":
                CONFIG["offline_anchor_query"]["reader_sha256"],
            "new_query_completed": True,
            "retained_input_bytes": offline["source"]["bytes"],
            "payload_retained_in_repo": False,
        },
        "observed_anchor": {
            "frame": anchor["frame"],
            "cycle": anchor["cycle"],
            "pc": CONFIG["expected"]["anchor"]["pc"],
            "sp": anchor["sp"],
            "selected_registers": anchor["selected_registers"],
            "region_b_head_sha256": memory["sha256"],
            "retired_fmv_head_sha256": memory["retired_memory_sha256"],
            "retired_fmv_head_absent": memory["retired_memory_absent"],
            "observation": (
                "The paused frame-15816 anchor is in the resident scene-flow "
                "wait block at 0x8004FEA4 and Region B no longer has the "
                "retired FMV.BIN head identity."
            ),
            "non_claim": (
                "The anchor projection does not identify a DMA event, transfer "
                "cycle, sector sequence or the selected earlier callsite."
            ),
        },
        "static_functions": functions,
        "static_instructions": instructions,
        "earlier_transition_boundaries": boundary_rows,
        "nonnegative_boundary_predecessors":
            _incoming_nonnegative_edges(
                exe, *FUNCTIONS["scene_flow_dispatcher"]),
        "negative_boundary_predecessor": {
            "condition": instructions["0x8004FD6C"],
            "a0_delay": instructions["0x8004FD70"],
            "call": instructions["0x8004FD74"],
            "a1_delay": instructions["0x8004FD78"],
        },
        "common_resource_chain": [
            {
                "pc": "0x800503B0",
                "operation": "skip resource initialization only when a1 == -1",
                "selected_transition_values": [0, 128],
                "selected_values_skip": False,
            },
            {
                "pc": "0x800503CC",
                "operation": "resource_id_dat_load_dispatcher(0)",
                "instruction": instructions["0x800503CC"],
                "selector_delay": instructions["0x800503D0"],
            },
            {
                "pc": "0x8003D310",
                "operation":
                    r"universal_file_loader(bits\memory.bin, 0x800B5788)",
                "instruction": instructions["0x8003D310"],
                "path_materialization": [
                    instructions["0x8003D300"],
                    instructions["0x8003D304"],
                ],
                "destination_materialization": [
                    instructions["0x8003D308"],
                    instructions["0x8003D30C"],
                ],
            },
            {
                "pc": "0x80046078",
                "operation": "retired later CdRead submission boundary",
                "source_artifact":
                    "analysis/phase4_fmv_levelb_region_b_dma_subwindow.json",
            },
        ],
        "relocalization": {
            "old_anchor": {
                "frame": 15816,
                "start_pc": "0x80046078",
                "outcome": "falsified_repeated",
                "retired": True,
            },
            "reason": (
                "The retained anchor is already paused in the scene-flow wait "
                "block with the FMV head retired. Static control flow places "
                "both branch-specific scene-setup calls before the common "
                "resource selector and CdRead boundary."
            ),
            "earlier_first_hit_set": [
                row["pc"] for row in boundary_rows
            ],
            "first_hit_set_complete": True,
            "next_observer_method": (
                "A future typed adapter must stop at the first hit of either "
                "0x8004FD74 or 0x8005029C from an earlier anchor, inspect the "
                "call arguments, and only then derive a narrower successor."
            ),
            "new_live_escalation_authorized": False,
        },
        "evidence_boundary": {
            "observation": (
                "Frame 15816 / cycle 8954497636 is paused at 0x8004FEA4; "
                "Region-B head SHA-256 is not the FMV.BIN head."
            ),
            "static_confirmation": (
                "The complete completed-Level-B replacement predecessor set is "
                "0x8004FD74 and 0x8005029C; both call scene_setup_and_load with "
                "a non--1 transition and therefore reach selector-zero resource "
                "loading before 0x80046078."
            ),
            "inference": (
                "The frame-15816 start was too late for a pre-submit exact-PC "
                "stop. The exact natural branch and its frame remain unclaimed."
            ),
            "causal_confirmation": None,
        },
        "falsifier": {
            "outcome": "survived",
            "checks": {
                "work_packet_identity_exact": True,
                "offline_receipt_closed_and_replayable": True,
                "anchor_frame_cycle_pc_exact": True,
                "anchor_pristine_media_exact": True,
                "anchor_region_b_payload_not_retained": True,
                "retired_fmv_head_absent": True,
                "retained_exact_pc_falsifier_preserved": True,
                "scene_flow_function_identity_exact": True,
                "completed_boundary_set_exactly_two": True,
                "negative_boundary_arguments_exact": True,
                "nonnegative_predecessor_edges_complete": True,
                "nonnegative_boundary_arguments_exact": True,
                "scene_setup_target_exact": True,
                "resource_skip_sentinel_excluded": True,
                "selector_zero_path_and_destination_exact": True,
                "external_scene_flow_asm_pin_exact": True,
                "unclassified_predecessors_zero": True,
                "new_live_escalation_absent": True,
                "dimension_promotion_absent": True,
            },
        },
        "claim_boundary": CONFIG["claim_boundary"],
        "source_dependencies": source_dependencies,
        "external_dependencies": {
            **packet_hashes,
            **offline_hashes,
        },
        "summary": {
            "new_offline_queries": 1,
            "external_input_bytes_reused": offline["source"]["bytes"],
            "earlier_boundary_count": len(boundary_rows),
            "unclassified_predecessors": 0,
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
        "PASS: E15 frame-15816 transition re-localized to two earlier "
        "scene-setup boundaries (no DMA claim or dimension promotion)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
