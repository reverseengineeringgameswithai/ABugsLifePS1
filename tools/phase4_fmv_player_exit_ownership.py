#!/usr/bin/env python3
"""Reconstruct E15's complete in-player exit and CD-command ownership."""
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
CONFIG_PATH = ROOT / "config/phase4_fmv_player_exit_ownership.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_player_exit_ownership.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
FMV_BASE = 0x800B5788
FMV_CODE_END = 0x800B9A4C
PLAYER_START = 0x800B6D68
PLAYER_END = 0x800B752C

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
INPUT_POLL_START = 0x8003A2DC
INPUT_POLL_END = 0x8003A314

STOP_ENTRY = 0x800B6E38
PAUSE_ARGUMENT_ENTRY = 0x800B7464
COMMON_ARGUMENT_ENTRY = 0x800B7468
COMMON_TEARDOWN_END = 0x800B752C
CD_CONTROL = 0x8006D8E8

EXPECTED_FMV_WORDS = {
    0x800B6E38: 0x24040008,  # a0 = CdlStop
    0x800B6E3C: 0x0C01B63A,  # CdControl(CdlStop, 0, 0)
    0x800B6E40: 0x00003021,
    0x800B6E44: 0x0802DD1A,  # join common a1/a2 setup
    0x800B6E48: 0x2404000B,  # delay slot: a0 = CdlPause
    0x800B70A8: 0x00121C00,  # signed selected-limit normalization
    0x800B70B0: 0x8C429A4C,  # decoded frame index
    0x800B70B4: 0x00031C03,
    0x800B70B8: 0x0043102A,
    0x800B70BC: 0x104000EA,  # initial limit already reached
    0x800B70C0: 0x2404000B,
    0x800B70C4: 0x2417000C,  # exact skip-count sentinel
    0x800B70D8: 0x24140001,  # shared value-one sentinel
    0x800B70E0: 0x0C00E8B7,  # resident controller poll
    0x800B70F8: 0x26310001,  # active skip countdown increment
    0x800B728C: 0x90429A54,  # u8 decode-stop latch
    0x800B7294: 0x10540073,  # latch == one -> pause teardown
    0x800B7404: 0x94422412,  # resident decoded controller state
    0x800B740C: 0x30424008,  # Start/select-class mask
    0x800B7410: 0x10400002,  # no masked input -> no countdown seed
    0x800B7418: 0x24110001,  # seed countdown at one
    0x800B7420: 0x8C422484,  # resident CD-event field
    0x800B7428: 0x1054000E,  # event == one -> pause teardown
    0x800B7430: 0x1237000C,  # countdown == twelve -> pause teardown
    0x800B743C: 0x8C42AC10,  # completion request
    0x800B7444: 0x1054FE7C,  # completion == one -> Stop
    0x800B7450: 0x8C429A4C,  # decoded frame index
    0x800B7458: 0x0052102A,  # decoded index < signed selected limit
    0x800B745C: 0x1440FF20,  # true -> next outer iteration
    0x800B7464: 0x2404000B,  # a0 = CdlPause
    0x800B7468: 0x00002821,  # a1 = 0
    0x800B746C: 0x0C01B63A,  # CdControl(command, 0, 0)
    0x800B7470: 0x00003021,  # a2 = 0
    0x800B749C: 0x0C01C253,  # StClearRing
    0x800B74A4: 0x0C01C26B,  # callback teardown
    0x800B7520: 0x27BD0908,  # balanced frame restore
    0x800B7524: 0x03E00008,  # conventional return
}

EXPECTED_EXE_WORDS = {
    0x8003A2DC: 0x27BDFFE8,
    0x8003A2E4: 0x94422412,  # read prior controller state
    0x8003A2F0: 0xA42222E4,  # retain prior state
    0x8003A2F4: 0x0C00E70D,  # poll decoded controller port
    0x8003A2F8: 0x24040001,
    0x8003A300: 0xA4222412,  # publish current controller state
    0x8003A30C: 0x03E00008,
}

EXPECTED_FUNCTION_SHA256 = {
    "fmv_player":
        "a4848c83be180bc58eed123b6f80d656b9240b15eab890a1d2debd306c1afe0f",
    "resident_input_poll":
        "94a3f1f1ebd18ababb0737e979db922c93c9a4a275a470d85ff9a98f316e6979",
    "stop_then_pause":
        "90fc806e5f4121c7ceca1cb5788491a5ff37ede8a675e3473445662b8317aad2",
    "pause_and_common_teardown":
        "49d06700299671580639874e4d3181f30f6394980756fab57d14a274127aac8a",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _slice(
    data: bytes, start: int, end: int, *, base: int, header: int
) -> bytes:
    begin = header + start - base
    finish = header + end - base
    _require(
        header <= begin < finish <= len(data),
        f"invalid slice 0x{start:08X}..0x{end:08X}",
    )
    return data[begin:finish]


def _word(
    data: bytes, address: int, *, base: int, header: int
) -> int:
    return struct.unpack(
        "<I", _slice(data, address, address + 4, base=base, header=header)
    )[0]


def _instruction(
    data: bytes, address: int, expected: int, *, base: int, header: int
) -> dict[str, str]:
    word = _word(data, address, base=base, header=header)
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


def _function(
    name: str, data: bytes, start: int, end: int, *,
    base: int, header: int
) -> dict[str, Any]:
    body = _slice(data, start, end, base=base, header=header)
    digest = _sha256_bytes(body)
    _require(
        digest == EXPECTED_FUNCTION_SHA256[name],
        f"{name} function slice drifted",
    )
    return {
        "name": name,
        "start": f"0x{start:08X}",
        "end": f"0x{end:08X}",
        "size": len(body),
        "sha256": digest,
    }


def _branch_target(pc: int, word: int) -> int:
    immediate = word & 0xFFFF
    if immediate & 0x8000:
        immediate -= 0x10000
    return pc + 4 + immediate * 4


def _direct_target(pc: int, word: int) -> int | None:
    opcode = word >> 26
    if opcode in {1, 4, 5, 6, 7}:
        return _branch_target(pc, word)
    if opcode == 2:
        return ((pc + 4) & 0xF0000000) | (
            (word & 0x03FFFFFF) << 2
        )
    return None


def _incoming_edges(
    fmv: bytes, targets: set[int]
) -> list[dict[str, str]]:
    rows = []
    for pc in range(FMV_BASE, FMV_CODE_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        target = _direct_target(pc, word)
        if target in targets:
            rows.append({
                "pc": f"0x{pc:08X}",
                "target": f"0x{target:08X}",
                "word": f"0x{word:08X}",
                "mnemonic": exe_read.disasm_one(pc, word),
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
    expected_output_path = (
        "iteration-1-receipts/outputs/"
        "fmv-player-exit-index-search.json"
    )
    _require(
        receipt.get("external_inputs") == [{
            "path": "iteration-1-receipts/inputs/"
                    "fmv-lifecycle-v2.index.json",
            "scope": "run",
            "sha256": spec["external_index_sha256"],
        }],
        "offline external input drifted",
    )
    _require(
        receipt.get("outputs") == [{
            "path": expected_output_path,
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
    expected_entries = {
        (spec["external_index_sha256"], 16060589),
        (spec["output"]["sha256"], 2038),
    }
    actual_entries = {
        (row.get("sha256"), row.get("size"))
        for row in preservation.get("entries", [])
        if row.get("media_class") == "derived_pristine_evidence"
        and row.get("preservation_required") is True
    }
    _require(
        preservation.get("complete") is True
        and preservation.get("errors") == []
        and actual_entries == expected_entries,
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
            "exit-PC, controller-mask, CD-command, or ownership leads. "
            "Pristine static bytes therefore own this instruction-level "
            "question."
        ),
    }


def _prior_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    loaded: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(path.is_file(), f"missing prior evidence: {path}")
        _require(_sha256(path) == spec["sha256"],
                 f"{name} identity drifted")
        loaded[name] = json.loads(path.read_text())
        hashes[spec["path"]] = spec["sha256"]
    lifecycle = loaded["lifecycle_continuations"][
        "transient_player_continuations"
    ]
    _require(
        lifecycle["exit_edges"] == [
            "0x800B7294", "0x800B7428", "0x800B7430",
            "0x800B7444", "0x800B745C",
        ]
        and lifecycle["static_routing_closed"] is True
        and lifecycle["native_outcomes_claimed"] is False,
        "prior lifecycle exit boundary drifted",
    )
    completion = lifecycle["completion_ownership"]
    _require(
        completion["summary"] == {
            "clear_writers": 1,
            "readers": 1,
            "set_writers": 2,
            "total_xrefs": 4,
            "writers": 3,
        }
        and [row["instruction"]["pc"] for row in completion["xrefs"]]
        == ["0x800B6B24", "0x800B6B48", "0x800B6DD0", "0x800B743C"],
        "completion-request producer frontier drifted",
    )
    cd_route = lifecycle["native_cd_event_route"]
    _require(
        cd_route["callback"]["store"] == {
            "address": "0x80082484",
            "gp_offset": "0x000006EC",
            "pc": "0x80045D60",
            "type": "u32",
            "value": 1,
        }
        and cd_route["runtime_event_delivery_claimed"] is False,
        "resident CD-event producer boundary drifted",
    )
    runtime = loaded["fmv_runtime"]
    _require(
        runtime["live"]["input_edit"]["changed_frames"]
        == list(range(334, 343))
        and runtime["live"]["input_edit"]["changed_field"]
        == "ports.0.start true -> false",
        "retained Start/no-Start control boundary drifted",
    )
    return loaded, hashes


def _semantic_sources() -> dict[str, str]:
    required = {
        "src_re/fmv_player_streaming.c": [
            "FMV post-helper exit ownership",
            "0x800B740C",
            "CdlStop(8)",
            "CdlPause(11)",
            "not the frontend pause shell",
        ],
        "src_re/fmv_lifecycle_continuations.c": [
            "Five exact post-helper predicates",
            "0x800B7430",
            "command 8 before command 11",
            "delivery frequency",
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
    *, fmv_data: bytes | None = None, exe_data: bytes | None = None,
    verify_identity: bool = True,
) -> dict[str, Any]:
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(FMV_REL, fmv)
        verify_staged_input(EXE_REL, exe)

    offline = _offline_localization()
    prior, prior_hashes = _prior_evidence()
    semantic_sources = _semantic_sources()

    fmv_ops = {
        f"0x{address:08X}": _instruction(
            fmv, address, word, base=FMV_BASE, header=0
        )
        for address, word in EXPECTED_FMV_WORDS.items()
    }
    exe_ops = {
        f"0x{address:08X}": _instruction(
            exe, address, word, base=EXE_BASE, header=EXE_HEADER
        )
        for address, word in EXPECTED_EXE_WORDS.items()
    }

    encoded_edges = _incoming_edges(
        fmv, {STOP_ENTRY, PAUSE_ARGUMENT_ENTRY, COMMON_ARGUMENT_ENTRY}
    )
    expected_edges = [
        ("0x800B6E44", "0x800B7468"),
        ("0x800B70BC", "0x800B7468"),
        ("0x800B7294", "0x800B7464"),
        ("0x800B7428", "0x800B7464"),
        ("0x800B7430", "0x800B7464"),
        ("0x800B7444", "0x800B6E38"),
    ]
    _require(
        [(row["pc"], row["target"]) for row in encoded_edges]
        == expected_edges,
        "encoded exit-entry edge census drifted",
    )
    _require(
        _branch_target(0x800B745C, EXPECTED_FMV_WORDS[0x800B745C])
        == 0x800B70E0,
        "decoded-limit loop branch target drifted",
    )

    functions = {
        "fmv_player": _function(
            "fmv_player", fmv, PLAYER_START, PLAYER_END,
            base=FMV_BASE, header=0,
        ),
        "resident_input_poll": _function(
            "resident_input_poll", exe, INPUT_POLL_START, INPUT_POLL_END,
            base=EXE_BASE, header=EXE_HEADER,
        ),
        "stop_then_pause": _function(
            "stop_then_pause", fmv, STOP_ENTRY, 0x800B6E4C,
            base=FMV_BASE, header=0,
        ),
        "pause_and_common_teardown": _function(
            "pause_and_common_teardown", fmv,
            PAUSE_ARGUMENT_ENTRY, COMMON_TEARDOWN_END,
            base=FMV_BASE, header=0,
        ),
    }

    lifecycle = prior["lifecycle_continuations"][
        "transient_player_continuations"
    ]
    completion_xrefs = lifecycle["completion_ownership"]["xrefs"]
    cd_route = lifecycle["native_cd_event_route"]
    runtime = prior["fmv_runtime"]["live"]
    claim = CONFIG["claim_boundary"]

    source_dependencies = {
        **semantic_sources,
        "config/phase4_fmv_player_exit_ownership.yaml":
            _sha256(CONFIG_PATH),
        "tools/phase4_fmv_player_exit_ownership.py":
            _sha256(Path(__file__)),
        "tools/phase4_offline_receipt_query.py":
            _sha256(ROOT / "tools/phase4_offline_receipt_query.py"),
    }

    producers = [
        {
            "id": "decode_stop_latch",
            "load": fmv_ops["0x800B728C"],
            "comparison": fmv_ops["0x800B7294"],
            "source_address": "0x800B9A54",
            "source_type": "u8",
            "source_writer": "0x800B6C84",
            "taken_target": "0x800B7464",
            "command_route": ["CdlPause(11)", "common_teardown"],
        },
        {
            "id": "resident_cd_event",
            "load": fmv_ops["0x800B7420"],
            "comparison": fmv_ops["0x800B7428"],
            "source_address": "0x80082484",
            "source_type": "u32",
            "source_writer": cd_route["callback"]["store"]["pc"],
            "taken_target": "0x800B7464",
            "command_route": ["CdlPause(11)", "common_teardown"],
        },
        {
            "id": "controller_skip_countdown",
            "poll_call": fmv_ops["0x800B70E0"],
            "load": fmv_ops["0x800B7404"],
            "mask": fmv_ops["0x800B740C"],
            "seed": fmv_ops["0x800B7418"],
            "increment": fmv_ops["0x800B70F8"],
            "comparison": fmv_ops["0x800B7430"],
            "source_address": "0x80082412",
            "source_type": "u16",
            "mask_value": "0x4008",
            "seed_value": 1,
            "exit_sentinel": 12,
            "taken_target": "0x800B7464",
            "command_route": ["CdlPause(11)", "common_teardown"],
        },
        {
            "id": "completion_request",
            "load": fmv_ops["0x800B743C"],
            "comparison": fmv_ops["0x800B7444"],
            "source_address": "0x800CAC10",
            "source_type": "u32",
            "source_xrefs": completion_xrefs,
            "taken_target": "0x800B6E38",
            "command_route": [
                "CdlStop(8)", "CdlPause(11)", "common_teardown"
            ],
        },
        {
            "id": "decoded_index_selected_limit",
            "load": fmv_ops["0x800B7450"],
            "comparison": fmv_ops["0x800B7458"],
            "branch": fmv_ops["0x800B745C"],
            "decoded_index_address": "0x800B9A4C",
            "selected_limit_register": "s2",
            "selected_limit_source": "signed a1 stored at 0x80131EEE",
            "true_target": "0x800B70E0",
            "false_fallthrough": "0x800B7464",
            "false_command_route": ["CdlPause(11)", "common_teardown"],
        },
    ]

    return {
        "_comment": (
            "Generated from hash-verified pristine retail bytes, a closed "
            "derived-pristine offline query, and hash-pinned prior evidence. "
            "No copyrighted input bytes are retained."
        ),
        "schema": "abl-phase4-fmv-player-exit-ownership/1",
        "generated": "2026-07-28",
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "lane": CONFIG["lane"],
        "inputs": {
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}",
                "sha256": _sha256_bytes(fmv),
                "size": len(fmv),
                "identity_verified": verify_identity,
            },
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "sha256": _sha256_bytes(exe),
                "size": len(exe),
                "identity_verified": verify_identity,
            },
            "config": {
                "path": str(CONFIG_PATH.relative_to(ROOT)),
                "sha256": _sha256(CONFIG_PATH),
            },
            "prior_evidence": prior_hashes,
        },
        "offline_localization": offline,
        "functions": functions,
        "exit_entry_frontier": {
            "scan_scope": [
                f"0x{FMV_BASE:08X}", f"0x{FMV_CODE_END:08X}"
            ],
            "entry_targets": [
                f"0x{STOP_ENTRY:08X}",
                f"0x{PAUSE_ARGUMENT_ENTRY:08X}",
                f"0x{COMMON_ARGUMENT_ENTRY:08X}",
            ],
            "encoded_edges": encoded_edges,
            "expected_encoded_edges": len(expected_edges),
            "fallthrough_edges": [{
                "pc": "0x800B745C",
                "predicate": "decoded_frame_index_not_less_than_selected_limit",
                "delay_slot": "0x800B7460",
                "target": "0x800B7464",
            }],
            "unclassified_encoded_edges": [],
            "unclassified_fallthrough_edges": [],
        },
        "post_helper_predicates": producers,
        "controller_producer_chain": {
            "resident_function": functions["resident_input_poll"],
            "prior_state_load": exe_ops["0x8003A2E4"],
            "prior_state_store": exe_ops["0x8003A2F0"],
            "port_poll": exe_ops["0x8003A2F4"],
            "port": exe_ops["0x8003A2F8"],
            "current_state_store": exe_ops["0x8003A300"],
            "player_poll_call": fmv_ops["0x800B70E0"],
            "player_mask": fmv_ops["0x800B740C"],
            "countdown_seed": fmv_ops["0x800B7418"],
            "countdown_increment": fmv_ops["0x800B70F8"],
            "countdown_compare": fmv_ops["0x800B7430"],
            "classification": (
                "resident_controller_state_to_twelve_step_skip_sentinel"
            ),
        },
        "cd_command_partition": {
            "completion_only_stop": {
                "entry": fmv_ops["0x800B6E38"],
                "call": fmv_ops["0x800B6E3C"],
                "command": 8,
                "command_name": "CdlStop",
                "join_jump": fmv_ops["0x800B6E44"],
                "join_delay_slot": fmv_ops["0x800B6E48"],
            },
            "shared_pause": {
                "entry": fmv_ops["0x800B7464"],
                "argument_join": fmv_ops["0x800B7468"],
                "call": fmv_ops["0x800B746C"],
                "zero_a2": fmv_ops["0x800B7470"],
                "command": 11,
                "command_name": "CdlPause",
                "classification": "stream_teardown_not_frontend_pause_shell",
            },
            "common_teardown": {
                "start": "0x800B7474",
                "st_clear_ring_call": fmv_ops["0x800B749C"],
                "callback_teardown_call": fmv_ops["0x800B74A4"],
                "stack_restore": fmv_ops["0x800B7520"],
                "return": fmv_ops["0x800B7524"],
            },
            "cd_control_target": f"0x{CD_CONTROL:08X}",
        },
        "runtime_control_join": {
            "source_artifact":
                "analysis/phase4_fmv.json",
            "changed_field": runtime["input_edit"]["changed_field"],
            "changed_frames": runtime["input_edit"]["changed_frames"],
            "positive_boundary": (
                "The retained LEV1A Start-only edit proves that Start can "
                "change the native FMV lifecycle at this anchor."
            ),
            "negative_boundary": (
                "The same retained control does not identify every static "
                "mask bit, countdown step, CD command, or other selector."
            ),
            "static_to_runtime_inference": (
                "Static ownership identifies the only in-player producer "
                "chain compatible with that Start control; no new runtime "
                "outcome is claimed."
            ),
        },
        "source_status": {
            "fmv_player": "pristine_binary_plus_semantic_c_not_matching_source",
            "resident_input_poll": "pristine_binary",
            "semantic_sources": semantic_sources,
        },
        "falsifier": {
            "outcome": "survived",
            "checks": {
                "offline_index_does_not_preanswer_exact_terms": True,
                "encoded_exit_entry_frontier_is_complete": True,
                "five_post_helper_predicates_are_classified": True,
                "controller_mask_is_0x4008": True,
                "controller_exit_sentinel_is_twelve": True,
                "completion_alone_routes_through_stop": True,
                "all_exit_routes_join_shared_pause_and_teardown": True,
                "runtime_outcomes_not_inflated_from_static_routing": True,
            },
            "explicit_falsifier": claim["falsifier"],
        },
        "claim_boundary": claim,
        "source_dependencies": source_dependencies,
        "summary": {
            "post_helper_predicates": len(producers),
            "encoded_exit_entry_edges": len(encoded_edges),
            "unclassified_exit_edges": 0,
            "controller_mask": "0x4008",
            "controller_exit_sentinel": 12,
            "completion_stop_command": 8,
            "shared_pause_command": 11,
            "dimension_promoted": False,
            "next_lane": claim["next_lane"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()

    document = build()
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
        print(
            "PASS: wrote E15 player-exit ownership "
            f"({document['summary']['post_helper_predicates']} predicates, "
            f"{document['summary']['encoded_exit_entry_edges']} encoded "
            "entry edges)"
        )
        return 0
    if not OUTPUT.is_file():
        raise SystemExit(f"missing generated artifact: {OUTPUT}")
    if OUTPUT.read_text() != rendered:
        raise SystemExit(f"generated artifact drifted: {OUTPUT}")
    print(
        "PASS: E15 player-exit ownership "
        f"({document['summary']['post_helper_predicates']} predicates, "
        f"{document['summary']['encoded_exit_entry_edges']} encoded entry "
        "edges, 0 unclassified)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
