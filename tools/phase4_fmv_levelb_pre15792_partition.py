#!/usr/bin/env python3
"""Bank E15's pre-frame-15792 caller, predecessor, and state partition."""
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
CONFIG_PATH = ROOT / "config/phase4_fmv_levelb_pre15792_partition.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_levelb_pre15792_partition.json"
SEMANTIC_SOURCE = ROOT / "src_re/fmv_levelb_pre15792_partition.c"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
SCENE_FLOW = (0x8004FCA0, 0x800502C4)
SCENE_SETUP = (0x8005038C, 0x800503FC)
REQUEST_ACCEPTOR = (0x8005B4E4, 0x8005B70C)
RESET_WRAPPER = (0x8005B70C, 0x8005BC64)
SCENE_SETUP_TARGET = 0x8005038C
PENDING_SCENE_REQUEST = 0x8009EDCC
LEVEL_ACTIVE = 0x800822F8
DECODED_INPUT_CURRENT = 0x80082412

EXPECTED_FUNCTION_SHA256 = {
    SCENE_FLOW:
        "02fc946a4c8757792f646d23e5cabdac5e0cf4755211b733cc75aa15b2f0592f",
    SCENE_SETUP:
        "6c12e5e6c9416b4e7aa2223c3ead0d3478ad65faa97c82098b223e494e61fddb",
    REQUEST_ACCEPTOR:
        "526b6fdd387e91fe7bb6497a847028c8a994014e1538a69c720bce6ffd4ec57c",
    RESET_WRAPPER:
        "b9572f907ef527be7d1a01f761d05eebfa924ccc718206b3ca1f9c613d93986b",
}
EXPECTED_ASM_SHA256 = {
    "asm/hand_written/8004fca0_scene_flow_dispatcher.s":
        "80c4643d6584bb0706a6905b939a76225dc0fa92d6c9eebf526337969d349098",
    "asm/hand_written/8005b4e4_sub_8005b4e4.s":
        "1b5d116a21da3b9eb77a0657770a97c0e828f43065ba49f4561b37af539d1bae",
    "asm/hand_written/8005b4ec_sub_8005b4ec.s":
        "9c16bc83bdef7910b7a022cfa8ddae9235d8597e76acd356e21b47244d892524",
    "asm/hand_written/8005b70c_sub_8005b70c.s":
        "3d3ad4a7b5ebbe97bfd3bec791e2110d6b7d0f4e22ebca1a3d0654e948f275fd",
    "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s":
        "07b436d13edd1628b61702d27030a1b02af23212758f8e99b352f2831f1c15ca",
}
EXPECTED_PENDING_XREFS = {
    0x8004D858: ("read", "sub_8004d6a8"),
    0x8004ED88: ("read", "gameplay_state_machine"),
    0x8004F1D8: ("read", "gameplay_state_machine"),
    0x8004F63C: ("read", "gameplay_frame_render"),
    0x8004FA68: ("write", "main_shell_state_machine"),
    0x8004FA90: ("write", "main_shell_state_machine"),
    0x8004FAA0: ("write", "main_shell_state_machine"),
    0x8004FBB4: ("read", "main_shell_state_machine"),
    0x8004FD64: ("read", "scene_flow_dispatcher"),
    0x8005011C: ("read", "scene_flow_dispatcher"),
    0x80050240: ("read", "scene_flow_dispatcher"),
    0x8005B4E8: ("read", "pending_request_wrapper"),
    0x8005B61C: ("read", "scene_flow_helper"),
}
EXPECTED_PREDECESSORS = {
    0x8004FDF8: {
        "class": "pending_request_acceptance_return_nonzero",
        "state_source": (
            "transitive u32 boolean returned by 0x8005B70C after the "
            "0x8005B4E4 request-acceptance call"
        ),
        "control_position": "before_wait_loop",
    },
    0x80050124: {
        "class": "pending_scene_request_nonnegative_after_wait",
        "state_source": "s32 resident field 0x8009EDCC loaded at 0x8005011C",
        "control_position": "after_wait_loop",
    },
    0x80050248: {
        "class": "pending_scene_request_nonnegative_loop_tail",
        "state_source": "s32 resident field 0x8009EDCC loaded at 0x80050240",
        "control_position": "loop_tail",
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return common.sha256(path)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _upper_hex(value: str) -> str:
    return "0x" + value.removeprefix("0x").removeprefix("0X").upper()


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


def _word(data: bytes, pc: int) -> int:
    return struct.unpack("<I", _slice(data, pc, pc + 4))[0]


def _instruction(data: bytes, pc: int) -> dict[str, str]:
    word = _word(data, pc)
    return {
        "pc": f"0x{pc:08X}",
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(pc, word),
    }


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


def _written_gpr(word: int) -> int | None:
    """Return the GPR written by the resident instruction subset."""
    opcode = word >> 26
    if opcode == 0:
        function = word & 0x3F
        if function == 0x09:  # jalr
            return (word >> 11) & 0x1F
        if function in {
            0x00, 0x02, 0x03, 0x04, 0x06, 0x07,
            0x10, 0x12,
            0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
            0x2A, 0x2B,
        }:
            return (word >> 11) & 0x1F
        return None
    if opcode == 0x03:  # jal
        return 31
    if opcode == 0x01 and (word >> 16) & 0x1F in {0x10, 0x11}:  # *al
        return 31
    if opcode in {
        0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
        0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26,
    }:
        return (word >> 16) & 0x1F
    return None


def _register_definitions(
    data: bytes, start: int, end: int, register: int
) -> list[dict[str, str]]:
    return [
        _instruction(data, pc)
        for pc in range(start, end, 4)
        if _written_gpr(_word(data, pc)) == register
    ]


def _function_identity(data: bytes, bounds: tuple[int, int]) -> dict[str, Any]:
    start, end = bounds
    body = _slice(data, start, end)
    digest = _sha256_bytes(body)
    _require(
        digest == EXPECTED_FUNCTION_SHA256[bounds],
        f"function identity drifted at 0x{start:08X}",
    )
    calls = []
    for pc in range(start, end, 4):
        target = _jal_target(pc, _word(data, pc))
        if target is not None:
            calls.append({
                **_instruction(data, pc),
                "target": f"0x{target:08X}",
            })
    return {
        "start": f"0x{start:08X}",
        "end": f"0x{end:08X}",
        "bytes": len(body),
        "sha256": digest,
        "direct_calls": calls,
    }


def _pending_xrefs(data: bytes) -> list[dict[str, Any]]:
    """Enumerate compiler-standard adjacent LUI plus direct LW/SW xrefs."""
    lower = PENDING_SCENE_REQUEST & 0xFFFF
    # Signed -4660 is paired with LUI 0x800A, not the unadjusted 0x8009.
    upper = ((PENDING_SCENE_REQUEST + 0x8000) >> 16) & 0xFFFF
    found: list[int] = []
    for pc in range(EXE_BASE + 4, EXE_BASE + len(data) - EXE_HEADER, 4):
        word = _word(data, pc)
        opcode = word >> 26
        if opcode not in {0x23, 0x2B} or word & 0xFFFF != lower:
            continue
        base_register = (word >> 21) & 0x1F
        previous = _word(data, pc - 4)
        if (
            previous >> 26 == 0x0F
            and (previous >> 16) & 0x1F == base_register
            and previous & 0xFFFF == upper
        ):
            found.append(pc)
    _require(
        found == list(EXPECTED_PENDING_XREFS),
        "pending_scene_request direct xref census drifted",
    )
    rows = []
    for pc in found:
        access, owner = EXPECTED_PENDING_XREFS[pc]
        rows.append({
            "access": access,
            "owner": owner,
            "address": "0x8009EDCC",
            "instruction": _instruction(data, pc),
            "address_materialization": _instruction(data, pc - 4),
        })
    return rows


def _scene_setup_partition(data: bytes) -> dict[str, Any]:
    scene = _function_identity(data, SCENE_FLOW)
    calls = [
        row for row in scene["direct_calls"]
        if row["target"] == "0x8005038C"
    ]
    _require(
        [row["pc"] for row in calls]
        == ["0x8004FD74", "0x800500E4", "0x8005029C"],
        "scene-setup caller census drifted",
    )
    predecessors = []
    for pc in range(*SCENE_FLOW, 4):
        if _branch_target(pc, _word(data, pc)) != 0x8005029C:
            continue
        _require(pc in EXPECTED_PREDECESSORS, "unclassified candidate predecessor")
        predecessors.append({
            **EXPECTED_PREDECESSORS[pc],
            "branch": _instruction(data, pc),
            "delay": _instruction(data, pc + 4),
            "target": "0x8005029C",
        })
    _require(
        [row["branch"]["pc"] for row in predecessors]
        == [f"0x{pc:08X}" for pc in EXPECTED_PREDECESSORS],
        "candidate predecessor frontier drifted",
    )
    return {
        "all_scene_setup_callers": [
            {
                **row,
                "classification": (
                    "completed_level_b_candidate"
                    if row["pc"] in {"0x8004FD74", "0x8005029C"}
                    else "natural_lose_nonintersecting_residual"
                ),
            }
            for row in calls
        ],
        "completed_level_b_candidates": [
            {
                "pc": "0x8004FD74",
                "scene": 3,
                "transition": 0,
                "predecessors": [{
                    "class": "pending_scene_request_negative",
                    "state_source":
                        "s32 resident field 0x8009EDCC loaded at 0x8004FD64",
                    "control_position": "before_wait_loop",
                    "branch": _instruction(data, 0x8004FD6C),
                    "delay": _instruction(data, 0x8004FD70),
                }],
            },
            {
                "pc": "0x8005029C",
                "scene": 6,
                "transition": 128,
                "predecessors": predecessors,
            },
        ],
        "candidate_count": 2,
        "predecessor_count": 4,
        "nonintersecting_residuals": [{
            "pc": "0x800500E4",
            "owner": "natural LOSE continuation",
            "reason": "scene_setup_and_load(5, 64), not completed-Level-B",
        }],
        "unclassified_callers": 0,
        "unclassified_predecessors": 0,
    }


def _transitive_return_gate(data: bytes) -> dict[str, Any]:
    acceptor = _function_identity(data, REQUEST_ACCEPTOR)
    wrapper = _function_identity(data, RESET_WRAPPER)
    acceptor_calls = [
        row for row in wrapper["direct_calls"]
        if row["target"] == "0x8005B4E4"
    ]
    _require(
        [row["pc"] for row in acceptor_calls] == ["0x8005B848"],
        "request-acceptor call frontier drifted",
    )

    s5_defs = _register_definitions(
        data, REQUEST_ACCEPTOR[0], 0x8005B6C8, 21
    )
    _require(
        [row["pc"] for row in s5_defs]
        == ["0x8005B4F4", "0x8005B63C"],
        "request-acceptance result definition frontier drifted",
    )
    s0_defs = _register_definitions(
        data, REQUEST_ACCEPTOR[0], 0x8005B6C8, 16
    )
    _require(
        [row["pc"] for row in s0_defs]
        == ["0x8005B52C", "0x8005B54C", "0x8005B5E8", "0x8005B640"],
        "request-acceptance one-shot definition frontier drifted",
    )
    saved_result_defs = _register_definitions(
        data, 0x8005B850, 0x8005BC44, 17
    )
    _require(
        [row["pc"] for row in saved_result_defs] == ["0x8005B850"],
        "saved request-acceptance result was redefined",
    )

    pcs = (
        0x8004FDF0,
        0x8004FDF8,
        0x8005B4E4,
        0x8005B4E8,
        0x8005B4F4,
        0x8005B524,
        0x8005B52C,
        0x8005B54C,
        0x8005B5F8,
        0x8005B5FC,
        0x8005B604,
        0x8005B608,
        0x8005B610,
        0x8005B618,
        0x8005B61C,
        0x8005B624,
        0x8005B63C,
        0x8005B640,
        0x8005B6C8,
        0x8005B840,
        0x8005B844,
        0x8005B848,
        0x8005B850,
        0x8005BC40,
    )
    instructions = {
        f"0x{pc:08X}": _instruction(data, pc)
        for pc in pcs
    }
    _require(
        [row["word"] for row in instructions.values()] == [
            "0x0C016DC3",
            "0x14400128",
            "0x3C02800A",
            "0x8C42EDCC",
            "0x0000A821",
            "0x14A00004",
            "0x00008021",
            "0x24100001",
            "0x3C028008",
            "0x94422412",
            "0x30420001",
            "0x1040000E",
            "0x1600000C",
            "0x3C02800A",
            "0x8C42EDCC",
            "0x04400007",
            "0x24150001",
            "0x24100001",
            "0x02A01021",
            "0x3C058008",
            "0x8CA522F8",
            "0x0C016D39",
            "0x00408821",
            "0x02201021",
        ],
        "transitive request-acceptance instruction identity drifted",
    )
    _require(
        _jal_target(0x8004FDF0, _word(data, 0x8004FDF0)) == 0x8005B70C
        and _branch_target(0x8004FDF8, _word(data, 0x8004FDF8))
        == 0x8005029C
        and _jal_target(0x8005B848, _word(data, 0x8005B848))
        == 0x8005B4E4,
        "transitive request-acceptance call/branch chain drifted",
    )
    return {
        "classification": "pending_request_acceptance_return_contract",
        "scene_flow_consumer": {
            "call": instructions["0x8004FDF0"],
            "branch": instructions["0x8004FDF8"],
            "branch_target": "0x8005029C",
        },
        "wrapper": {
            "function": wrapper,
            "acceptor_call": instructions["0x8005B848"],
            "level_active_argument_load": {
                "address": "0x800822F8",
                "type": "u32",
                "instructions": [
                    instructions["0x8005B840"],
                    instructions["0x8005B844"],
                ],
            },
            "saved_result_definition": instructions["0x8005B850"],
            "saved_result_definitions_before_return": saved_result_defs,
            "return_copy": instructions["0x8005BC40"],
            "saved_result_redefinitions": 0,
        },
        "acceptor": {
            "function": acceptor,
            "result_type": "u32_boolean",
            "result_initialization": instructions["0x8005B4F4"],
            "result_set": instructions["0x8005B63C"],
            "result_definitions_before_return_copy": s5_defs,
            "result_return_copy": instructions["0x8005B6C8"],
            "result_set_count": 1,
            "result_domain": [0, 1],
            "required_predicates": [
                {
                    "name": "decoded_input_bit_zero_present",
                    "address": "0x80082412",
                    "type": "u16",
                    "mask": "0x0001",
                    "load": instructions["0x8005B5FC"],
                    "mask_instruction": instructions["0x8005B604"],
                    "reject_branch": instructions["0x8005B608"],
                },
                {
                    "name": "local_one_shot_clear",
                    "register": "s0",
                    "level_active_branch": instructions["0x8005B524"],
                    "clear_definition": instructions["0x8005B52C"],
                    "initial_set_definition": instructions["0x8005B54C"],
                    "reject_branch": instructions["0x8005B610"],
                    "all_definitions_before_result_copy": s0_defs,
                },
                {
                    "name": "pending_scene_request_nonnegative",
                    "address": "0x8009EDCC",
                    "type": "s32",
                    "materialization": instructions["0x8005B618"],
                    "load": instructions["0x8005B61C"],
                    "reject_branch": instructions["0x8005B624"],
                },
            ],
        },
        "def_use_chain": [
            "0x8005B63C:s5=1",
            "0x8005B6C8:v0=s5",
            "0x8005B850:s1=v0",
            "0x8005BC40:v0=s1",
            "0x8004FDF8:branch_if_v0_nonzero",
            "0x8005029C:scene_setup_and_load(6,128)",
        ],
        "unclassified_result_definitions": 0,
        "natural_execution_claimed": False,
    }


def _run_artifact(spec: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = RUN_ROOT / spec["relative_path"]
    _require(
        path.is_file() and _sha256(path) == spec["sha256"],
        f"run artifact identity drifted: {spec['relative_path']}",
    )
    return path, common.load_json(path)


def _repo_artifact(spec: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = ROOT / spec["path"]
    _require(
        path.is_file() and _sha256(path) == spec["sha256"],
        f"repo artifact identity drifted: {spec['path']}",
    )
    return path, common.load_json(path)


def _closed_query(
    spec: dict[str, Any], *, expected_schema: str
) -> tuple[dict[str, Any], dict[str, str]]:
    receipt_path, receipt = _run_artifact(spec["receipt"])
    output_path, output = _run_artifact(spec["output"])
    _require(
        receipt.get("schema") == "abl-phase4-offline-query/1"
        and receipt.get("complete") is True
        and receipt.get("errors") == []
        and receipt.get("execution", {}).get("exit_code") == 0
        and receipt.get("reader") == {
            "path": spec["reader_path"],
            "scope": "repo",
            "sha256": spec["reader_sha256"],
        }
        and receipt.get("external_inputs", [{}])[0].get("sha256")
        == spec["input_sha256"]
        and receipt.get("outputs", [{}])[0].get("sha256")
        == spec["output"]["sha256"]
        and output.get("schema") == expected_schema
        and output.get("source", {}).get("sha256") == spec["input_sha256"],
        "offline receipt is not closed and joined",
    )
    return output, {
        f"run:{spec['receipt']['relative_path']}": _sha256(receipt_path),
        f"run:{spec['output']['relative_path']}": _sha256(output_path),
    }


def _offline_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    index, index_hashes = _closed_query(
        CONFIG["offline_index_query"],
        expected_schema="abl-phase4-offline-json-search-result/1",
    )
    terms = index.get("terms") or {}
    _require(
        all(
            terms.get(term, {}).get("count") == 0
            for term in (
                "0x8004fd74",
                "0x8005029c",
                "0x8005031c",
                "0x800b5788",
                "completed-Level-B",
                "Region-B",
                "15763",
                "15792",
                "15816",
            )
        )
        and terms.get("0x8004fea4", {}).get("count") == 708,
        "retained index coverage answer drifted",
    )
    staged, staged_hashes = _closed_query(
        CONFIG["staged_anchor_query"],
        expected_schema="abl-phase4-offline-staged-prelude-projection/1",
    )
    expected = CONFIG["expected"]["staged_anchor"]
    boundary = staged.get("result", {}).get("boundary", {})
    _require(
        staged.get("result", {}).get("paired_cpu_boundary_equal") is True
        and staged.get("result", {}).get("payload_retained") is False
        and boundary.get("frame") == expected["frame"]
        and boundary.get("cycle") == expected["cycle"]
        and boundary.get("pc", "").upper() == expected["pc"].upper()
        and boundary.get("sp", "").upper() == expected["sp"].upper()
        and len(staged.get("result", {}).get("jobs") or []) == 2
        and staged.get("result", {}).get("media", {}).get("verified") is True,
        "paired staged boundary drifted",
    )
    return {
        "index": index,
        "staged": staged,
    }, {**index_hashes, **staged_hashes}


def _prior_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    transition_path, transition = _repo_artifact(
        CONFIG["prior_evidence"]["transition_relocalization"]
    )
    result_path, result = _repo_artifact(
        CONFIG["prior_evidence"]["two_pc_result"]
    )
    _require(
        transition.get("falsifier", {}).get("outcome") == "survived"
        and transition.get("relocalization", {}).get("earlier_first_hit_set")
        == ["0x8004FD74", "0x8005029C"]
        and transition.get("relocalization", {}).get("first_hit_set_complete")
        is True
        and result.get("valid") is True
        and result.get("falsifier", {}).get("outcome") == "falsified"
        and result.get("observation", {}).get("candidate_pc_hits") == 0
        and result.get("observation", {}).get("native_anchor", {}).get("frame")
        == 15792
        and result.get("claim_boundary", {}).get("dimension_promoted") is False,
        "prior transition/no-hit evidence drifted",
    )
    return {
        "transition": transition,
        "two_pc_result": result,
    }, {
        str(transition_path.relative_to(ROOT)): _sha256(transition_path),
        str(result_path.relative_to(ROOT)): _sha256(result_path),
    }


def _machine_sources() -> dict[str, str]:
    text = SEMANTIC_SOURCE.read_text()
    _require(
        all(fragment in text for fragment in (
            "0x8009EDCC",
            "0x80082250",
            "0x800822F8",
            "0x80082412",
            "0x8004FD74",
            "0x8004FDF8 -> 0x8005029C",
            "0x80050124 -> 0x8005029C",
            "0x80050248 -> 0x8005029C",
            "0x8005B63C",
            "0x8005B6C8",
            "0x8005B850",
            "0x8005BC40",
            "does not prove",
        )),
        "semantic C partition drifted",
    )
    repro = (ROOT / "tools/repro_inputs.sha256").read_text()
    for relative, digest in EXPECTED_ASM_SHA256.items():
        _require(
            _sha256(ROOT / relative) == digest
            and f"{digest}  {relative}" in repro,
            f"external ASM pin drifted: {relative}",
        )
    contract = CONFIG["return_gate_contract"]
    _require(
        contract["scene_flow_call"] == 0x8004FDF0
        and contract["scene_flow_branch"] == 0x8004FDF8
        and contract["branch_target"] == 0x8005029C
        and contract["wrapper"] == [0x8005B70C, 0x8005BC64]
        and contract["acceptance_callee"] == [0x8005B4E4, 0x8005B70C]
        and contract["result"]["initialization"] == 0x8005B4F4
        and contract["result"]["only_set_to_one"] == 0x8005B63C
        and contract["result"]["callee_return_copy"] == 0x8005B6C8
        and contract["wrapper_result_save"] == 0x8005B850
        and contract["wrapper_return_copy"] == 0x8005BC40,
        "authoritative FMV return-gate schema drifted",
    )
    return {
        "src_re/fmv_levelb_pre15792_partition.c": _sha256(SEMANTIC_SOURCE),
        **EXPECTED_ASM_SHA256,
    }


def build(
    *, exe_data: bytes | None = None, verify_identity: bool = True
) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)

    offline, external_hashes = _offline_evidence()
    prior, prior_hashes = _prior_evidence()
    machine_sources = _machine_sources()
    scene_flow = _function_identity(exe, SCENE_FLOW)
    scene_setup = _function_identity(exe, SCENE_SETUP)
    partition = _scene_setup_partition(exe)
    return_gate = _transitive_return_gate(exe)
    xrefs = _pending_xrefs(exe)
    staged = offline["staged"]["result"]["boundary"]
    excluded = CONFIG["expected"]["excluded_window"]
    wait_instructions = {
        f"0x{pc:08X}": _instruction(exe, pc)
        for pc in (
            0x8004FE98,
            0x8004FE9C,
            0x8004FEA0,
            0x8004FEA4,
            0x8004FEA8,
            0x8004FEB0,
        )
    }
    _require(
        [row["word"] for row in wait_instructions.values()]
        == [
            "0x24030001",
            "0x3C018008",
            "0xAC232250",
            "0x3C028008",
            "0x8C422250",
            "0x1043FFFC",
        ],
        "wait-loop instruction identity drifted",
    )

    checks = {
        "offline_index_receipt_closed": True,
        "index_has_no_row_specific_exact_edge": True,
        "staged_anchor_receipt_closed": True,
        "paired_frame_15720_cpu_boundary_equal": True,
        "staged_anchor_payload_absent": True,
        "frame_15792_no_hit_falsifier_preserved": True,
        "scene_flow_function_identity_exact": True,
        "scene_setup_function_identity_exact": True,
        "scene_setup_caller_census_complete": True,
        "completed_candidate_set_exactly_two": True,
        "candidate_predecessor_set_exactly_four": True,
        "early_helper_result_predecessor_typed": True,
        "early_helper_result_transitive_contract_closed": True,
        "request_acceptance_result_set_exactly_once": True,
        "request_acceptance_predicates_complete": True,
        "request_acceptance_result_propagation_complete": True,
        "request_acceptance_saved_result_not_redefined": True,
        "pending_request_predecessors_typed": True,
        "pending_request_direct_xrefs_complete": True,
        "pending_request_direct_xrefs_unclassified_zero": True,
        "wait_loop_state_field_typed": True,
        "natural_lose_residual_nonintersecting": True,
        "selector_zero_replacement_chain_preserved": True,
        "machine_sources_hash_pinned": True,
        "new_live_escalation_absent": True,
        "dimension_promotion_absent": True,
    }
    return {
        "schema": "abl-phase4-fmv-levelb-pre15792-partition/1",
        "generated": _stable_generated(),
        "_comment": (
            "Generated from two closed derived-pristine offline queries, "
            "hash-verified pristine executable bytes, and hash-pinned static "
            "machine sources. No captured or copyrighted payload is retained."
        ),
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "offline_localization": {
            "derived_index": {
                "sha256": CONFIG["offline_index_query"]["input_sha256"],
                "bytes": CONFIG["offline_index_query"]["input_bytes"],
                "receipt_sha256":
                    CONFIG["offline_index_query"]["receipt"]["sha256"],
                "answer": (
                    "No exact E15 candidate, completed-Level-B, Region-B, or "
                    "late-frame lead is retained; the index cannot answer the "
                    "natural first-hit timing question."
                ),
                "candidate_exact_hits": 0,
                "wait_pc_exact_hits": 708,
            },
            "staged_current_toolchain_boundary": {
                "source_sha256":
                    CONFIG["staged_anchor_query"]["input_sha256"],
                "source_bytes": CONFIG["staged_anchor_query"]["input_bytes"],
                "receipt_sha256":
                    CONFIG["staged_anchor_query"]["receipt"]["sha256"],
                "frame": staged["frame"],
                "cycle": staged["cycle"],
                "pc": _upper_hex(staged["pc"]),
                "sp": _upper_hex(staged["sp"]),
                "paired_equal": True,
                "payload_retained": False,
                "interpretation": (
                    "At frame 15720 both retained pristine cold-boot jobs are "
                    "at the shared frame-sync wait-loop control position. "
                    "This is not an instruction hit, an FMV lifetime latch, "
                    "or a Region-B memory observation."
                ),
            },
            "excluded_later_window": {
                **excluded,
                "candidate_pcs": ["0x8004FD74", "0x8005029C"],
                "outcome": "falsified",
                "source_artifact":
                    "analysis/phase4_fmv_levelb_two_pc_first_hit_result.json",
            },
        },
        "typed_state": {
            "pending_scene_request": {
                **CONFIG["expected"]["pending_scene_request"],
                "address": "0x8009EDCC",
                "direct_xref_contract":
                    "compiler_standard_adjacent_lui_load_store",
                "direct_xrefs": xrefs,
                "direct_xref_count": len(xrefs),
                "direct_read_count":
                    sum(row["access"] == "read" for row in xrefs),
                "direct_write_count":
                    sum(row["access"] == "write" for row in xrefs),
                "unclassified_direct_xrefs": 0,
                "alias_residual": (
                    "Non-adjacent pointer aliases are outside this direct-xref "
                    "contract and remain explicitly unclaimed."
                ),
            },
            "frame_sync_wait_latch": {
                **CONFIG["expected"]["frame_sync_wait_latch"],
                "address": "0x80082250",
                "instructions": wait_instructions,
                "control_pc": "0x8004FEA4",
                "ownership_artifact":
                    "analysis/phase4_fmv_frame_sync_wait_ownership.json",
                "boundary": (
                    "The retained historical fmv_running_latch label is an "
                    "alias only; this shared interrupt handshake does not "
                    "bracket FMV retirement."
                ),
            },
        },
        "static_functions": {
            "scene_flow_dispatcher": scene_flow,
            "scene_setup_and_load": scene_setup,
            "pending_request_acceptor": return_gate["acceptor"]["function"],
            "gameplay_state_reset_cursor_seed_entry":
                return_gate["wrapper"]["function"],
        },
        "static_partition": partition,
        "transitive_return_gate": return_gate,
        "control_position_partition": {
            "anchor": {
                "frame": staged["frame"],
                "cycle": staged["cycle"],
                "pc": _upper_hex(staged["pc"]),
            },
            "before_wait_predecessor_classes": [
                "pending_scene_request_negative",
                "pending_request_acceptance_return_nonzero",
            ],
            "after_wait_predecessor_classes": [
                "pending_scene_request_nonnegative_after_wait",
                "pending_scene_request_nonnegative_loop_tail",
            ],
            "boundary_limit": (
                "Static control flow places predecessor classes on either "
                "side of the shared frame-sync wait, but the retained frame "
                "boundary does not establish dynamic execution. It does not "
                "prove whether a before-wait candidate already retired or a "
                "later candidate will execute."
            ),
            "exact_candidate_set_before_frame_15792": [
                "0x8004FD74",
                "0x8005029C",
            ],
            "candidate_set_complete": True,
            "natural_branch_selected": False,
            "exact_retirement_frame": None,
        },
        "resource_replacement_join": {
            "source_artifact":
                "analysis/phase4_fmv_levelb_transition_relocalization.json",
            "source_sha256":
                CONFIG["prior_evidence"]["transition_relocalization"]["sha256"],
            "path": r"bits\memory.bin",
            "destination": "0x800B5788",
            "selector": 0,
            "transition_values": [0, 128],
            "resource_skip_sentinel": -1,
            "selected_values_skip": False,
            "byte_owner": "E16_streaming_overlays",
            "transition_owner": "resident_scene_flow_dispatcher",
        },
        "evidence_boundary": {
            "observation": (
                "Paired current-toolchain pristine jobs are at frame 15720, "
                "cycle 8900142073, PC 0x8004FEA4."
            ),
            "static_confirmation": CONFIG["claim"]["exact"],
            "inference": (
                "The exact first-hit event is earlier than the falsified "
                "15792..15856 observer, but the shared frame-sync position at "
                "frame 15720 is not an FMV lifetime discriminator and does "
                "not choose which side of that anchor contains it."
            ),
            "causal_confirmation": None,
        },
        "falsifier": {
            "claim": CONFIG["claim"]["falsifier"],
            "outcome": "survived",
            "checks": checks,
        },
        "claim_boundary": CONFIG["claim_boundary"],
        "source_dependencies": {
            "config/phase4_fmv_levelb_pre15792_partition.yaml":
                _sha256(CONFIG_PATH),
            CONFIG["offline_index_query"]["reader_path"]:
                CONFIG["offline_index_query"]["reader_sha256"],
            CONFIG["staged_anchor_query"]["reader_path"]:
                CONFIG["staged_anchor_query"]["reader_sha256"],
            **prior_hashes,
            **machine_sources,
        },
        "external_dependencies": external_hashes,
        "summary": {
            "offline_queries_consumed_by_artifact": 2,
            "external_unique_input_hashes_reused": 2,
            "external_input_bytes_reused":
                CONFIG["offline_index_query"]["input_bytes"]
                + CONFIG["staged_anchor_query"]["input_bytes"],
            "completed_candidate_calls": 2,
            "classified_candidate_predecessors": 4,
            "closed_transitive_return_gates": 1,
            "unclassified_result_definitions": 0,
            "pending_request_direct_xrefs": len(xrefs),
            "unclassified_direct_xrefs": 0,
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
    try:
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
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "PASS: E15 pre-15792 caller/predecessor/state partition closed "
        "(no branch, DMA, or dimension promotion)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
