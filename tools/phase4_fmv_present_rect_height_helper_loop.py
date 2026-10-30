#!/usr/bin/env python3
"""Reconstruct the E15 decode-helper ABI and outer-loop call partition."""
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
CONFIG_PATH = (
    ROOT / "config/phase4_fmv_present_rect_height_helper_loop.yaml"
)
OUTPUT = ROOT / "analysis/phase4_fmv_present_rect_height_helper_loop.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_BASE = 0x800B5788
FMV_CODE_END = 0x800B9A4C
EXE_BASE = 0x80010000
EXE_HEADER = 0x800

COMMIT_START = 0x800B6A7C
COMMIT_END = 0x800B6C24
HELPER_START = 0x800B6C24
HELPER_END = 0x800B6CA4
PLAYER_START = 0x800B6D68
PLAYER_END = 0x800B752C
ST_GET_NEXT_START = 0x80070C9C
ST_GET_NEXT_END = 0x80070D60

EXPECTED_FMV_WORDS = {
    0x800B6A7C: 0x27BDFFD0,  # commit prologue
    0x800B6A84: 0x00808821,  # move s1,a0
    0x800B6A94: 0x27A40018,  # a0 = &stack_record
    0x800B6A98: 0x0C01C327,  # jal StGetNext
    0x800B6A9C: 0x27A5001C,  # a1 = &stack_header
    0x800B6AA8: 0x1600FFFB,  # bounded retry back to StGetNext call
    0x800B6B8C: 0x00003021,  # a2 = 0
    0x800B6B90: 0x00003821,  # a3 = 0
    0x800B6C1C: 0x03E00008,  # commit conventional return
    0x800B6C24: 0x27BDFFE0,  # helper prologue
    0x800B6C2C: 0x00808021,  # move s0,a0
    0x800B6C34: 0x0C02DA9F,  # sole jal commit
    0x800B6C3C: 0x00408821,  # retain commit result
    0x800B6C48: 0x8E020008,  # active index
    0x800B6C54: 0xAE020008,  # toggle active index
    0x800B6C60: 0x8C450000,  # select block[active_index]
    0x800B6C84: 0xA0229A54,  # no-record stop latch
    0x800B6C9C: 0x03E00008,  # helper conventional return
    0x800B7098: 0x3C10800D,  # boundary base upper
    0x800B709C: 0x2610ABE0,  # boundary base lower
    0x800B70A0: 0x0C02DB09,  # initialization helper call
    0x800B70A4: 0x02002021,  # a0 = s0 in delay slot
    0x800B70D4: 0x02009821,  # preserve boundary in s3
    0x800B70E0: 0x0C00E8B7,  # outer loop top
    0x800B7280: 0x0C02DB09,  # outer-loop helper call
    0x800B7284: 0x02602021,  # a0 = s3 in delay slot
    0x800B745C: 0x1440FF20,  # outer-loop back edge
}

EXPECTED_EXE_WORDS = {
    0x80070C9C: 0x00803821,  # StGetNext overwrites incoming a3
    0x80070CB4: 0x00623021,  # StGetNext overwrites incoming a2
    0x80070CC8: 0x00A04021,  # preserve explicit a1 in t0
    0x80070D50: 0xACE40000,  # publish through explicit a0
    0x80070D54: 0xAD060000,  # publish through explicit a1
    0x80070D58: 0x03E00008,  # conventional return
}

EXPECTED_FUNCTION_SHA256 = {
    "fmv_decode_commit_dimensions":
        "2529f62e28c9ccd986e93c57fca8aa18adf345553eac570113077b14d22949ee",
    "fmv_decode_one_record":
        "9d91718d072e2af77e13cff008ed3a935655e8facd4bb53f50ff0febd2c5d074",
    "fmv_player":
        "a4848c83be180bc58eed123b6f80d656b9240b15eab890a1d2debd306c1afe0f",
    "StGetNext":
        "df38b6d6615d67a04728ce1da6a087c6493f6d4c928be5740e3129ff9dde7082",
}

REGISTER_NAMES = {
    4: "a0",
    5: "a1",
    6: "a2",
    7: "a3",
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
) -> dict[str, Any]:
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


def _uses_defs(word: int) -> tuple[set[int], set[int]]:
    """Return architectural GPR reads/writes for the MIPS-I opcodes in scope."""
    opcode = word >> 26
    rs = (word >> 21) & 31
    rt = (word >> 16) & 31
    rd = (word >> 11) & 31
    uses: set[int] = set()
    defs: set[int] = set()
    if opcode == 0:
        funct = word & 0x3F
        if funct in {0, 2, 3}:  # immediate shifts
            uses.add(rt)
            defs.add(rd)
        elif funct in {4, 6, 7}:  # variable shifts
            uses.update({rs, rt})
            defs.add(rd)
        elif funct == 8:  # jr
            uses.add(rs)
        elif funct == 9:  # jalr
            uses.add(rs)
            defs.add(rd)
        elif funct in {16, 18}:  # mfhi/mflo
            defs.add(rd)
        elif funct in {17, 19}:  # mthi/mtlo
            uses.add(rs)
        elif funct in {24, 25, 26, 27}:  # mult/div
            uses.update({rs, rt})
        elif funct not in {12, 13}:  # syscall/break
            uses.update({rs, rt})
            defs.add(rd)
    elif opcode == 1:
        uses.add(rs)
        if rt in {16, 17}:  # bltzal/bgezal
            defs.add(31)
    elif opcode == 2:
        pass
    elif opcode == 3:
        defs.add(31)
    elif opcode in {4, 5}:
        uses.update({rs, rt})
    elif opcode in {6, 7}:
        uses.add(rs)
    elif opcode == 15:  # lui
        defs.add(rt)
    elif opcode in {8, 9, 10, 11, 12, 13, 14}:
        uses.add(rs)
        defs.add(rt)
    elif opcode in {
        32, 33, 34, 35, 36, 37, 38, 48, 49, 50, 51, 54, 55,
    }:
        uses.add(rs)
        defs.add(rt)
    elif opcode in {40, 41, 42, 43, 46, 56, 57, 58, 59, 62}:
        uses.update({rs, rt})
    uses.discard(0)
    defs.discard(0)
    return uses, defs


def _first_argument_accesses(
    data: bytes, start: int, end: int, *, base: int, header: int
) -> dict[str, dict[str, Any] | None]:
    result: dict[str, dict[str, Any] | None] = {
        name: None for name in REGISTER_NAMES.values()
    }
    for pc in range(start, end, 4):
        word = _word(data, pc, base=base, header=header)
        uses, defs = _uses_defs(word)
        for register, name in REGISTER_NAMES.items():
            if result[name] is not None:
                continue
            if register in uses or register in defs:
                result[name] = {
                    "access": (
                        "read_write"
                        if register in uses and register in defs
                        else "read"
                        if register in uses
                        else "definition"
                    ),
                    "instruction": {
                        "pc": f"0x{pc:08X}",
                        "word": f"0x{word:08X}",
                        "mnemonic": exe_read.disasm_one(pc, word),
                    },
                }
    return result


def _jal_target(pc: int, word: int) -> int | None:
    if word >> 26 != 3:
        return None
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def _direct_callers(fmv: bytes, target: int) -> list[dict[str, Any]]:
    rows = []
    for pc in range(FMV_BASE, FMV_CODE_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        if _jal_target(pc, word) == target:
            rows.append({
                "pc": f"0x{pc:08X}",
                "word": f"0x{word:08X}",
                "mnemonic": exe_read.disasm_one(pc, word),
            })
    return rows


def _jalr_sites(fmv: bytes) -> list[dict[str, Any]]:
    rows = []
    for pc in range(FMV_BASE, FMV_CODE_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        if word & 0xFC00003F == 0x00000009:
            rows.append({
                "pc": f"0x{pc:08X}",
                "word": f"0x{word:08X}",
                "mnemonic": exe_read.disasm_one(pc, word),
            })
    return rows


def _raw_target_references(fmv: bytes, targets: tuple[int, ...]) -> list[str]:
    target_bytes = {struct.pack("<I", target) for target in targets}
    return [
        f"0x{FMV_BASE + offset:08X}"
        for offset in range(0, FMV_CODE_END - FMV_BASE, 4)
        if fmv[offset:offset + 4] in target_bytes
    ]


def _branch_target(pc: int, word: int) -> int:
    immediate = word & 0xFFFF
    if immediate & 0x8000:
        immediate -= 0x10000
    return pc + 4 + immediate * 4


def _helper_back_edges(fmv: bytes) -> list[dict[str, str]]:
    rows = []
    for pc in range(HELPER_START, HELPER_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        opcode = word >> 26
        target = None
        if opcode in {1, 4, 5, 6, 7}:
            target = _branch_target(pc, word)
        elif opcode == 2:
            target = ((pc + 4) & 0xF0000000) | (
                (word & 0x03FFFFFF) << 2
            )
        if target is not None and target < pc:
            rows.append({
                "pc": f"0x{pc:08X}",
                "target": f"0x{target:08X}",
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
            "path": "iteration-1-receipts/inputs/"
                    "fmv-lifecycle-v2.index.json",
            "scope": "run",
            "sha256": spec["external_index_sha256"],
        }],
        "offline external input drifted",
    )
    _require(
        receipt.get("outputs") == [{
            "path": "iteration-1-receipts/outputs/"
                    "fmv-helper-loop-index-search.json",
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
        (spec["output"]["sha256"], 1610),
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
            "helper, call-instruction, argument-class, or synthetic-unwind "
            "leads; pristine static bytes therefore own this question."
        ),
    }


def _prior_evidence(
    trace_data: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    loaded = {}
    hashes = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(path.is_file(), f"missing prior evidence: {path}")
        _require(_sha256(path) == spec["sha256"],
                 f"{name} identity drifted")
        loaded[name] = json.loads(path.read_text())
        hashes[spec["path"]] = spec["sha256"]
    if trace_data is not None:
        loaded["function_trace_result"] = trace_data
    return loaded, hashes


def _validate_trace(trace: dict[str, Any]) -> dict[str, Any]:
    native = trace["observation"]["precise"]["native"]
    classes = native["argument_classes"]
    _require(
        trace["falsifier"]["outcome"] == "falsified"
        and native["call_count"] == 11
        and native["function_events"] == 22
        and native["configured_max_events"] == 32
        and native["headroom_events"] == 10
        and native["call_instruction"] == "0x800b6c34"
        and native["return_address"] == "0x800b6c3c"
        and native["synthetic_exit_indexes"] == [2]
        and [row["call_count"] for row in classes] == [1, 1, 9]
        and all(row["arguments"][0] == "0x800cabe0" for row in classes),
        "retained function-trace partition drifted",
    )
    _require(
        trace["observation"]["precise"]["repeat"]["argument_classes"] == classes
        and trace["observation"]["precise"]["repeat"]["call_count"] == 11,
        "paired trace repeat drifted",
    )
    return {
        "call_instruction": "0x800B6C34",
        "return_address": "0x800B6C3C",
        "calls": 11,
        "function_events": 22,
        "headroom_events": 10,
        "synthetic_exit_indexes": [2],
        "argument_classes": classes,
        "static_call_site_partition": [
            {
                "class_index": 0,
                "owner": "player_initialization_call_0x800B70A0",
                "calls": 1,
            },
            {
                "class_indexes": [1, 2],
                "owner": "player_outer_loop_call_0x800B7280",
                "calls": 10,
            },
        ],
        "interpretation": (
            "The ordered trace begins with the one pre-loop helper call and "
            "continues with ten outer-loop calls. Its final a1-a3 residue "
            "class happens nine times; that is not a static loop bound."
        ),
    }


def _validate_schemas() -> dict[str, Any]:
    fmv_path = ROOT / "config/phase4_fmv.yaml"
    record_path = ROOT / "config/record_types.yaml"
    fmv = common.load_yaml(fmv_path)
    records = common.load_yaml(record_path)
    helper = fmv["typed_state"]["decode_helper_ownership"]
    _require(
        fmv["schema"] == "abl-phase4-fmv/11"
        and helper["commit_function"] == [COMMIT_START, COMMIT_END]
        and helper["helper_function"] == [HELPER_START, HELPER_END]
        and helper["semantic_entry_arguments"] == ["a0"]
        and helper["retained_trace_partition"] == {
            "player_initialization_calls": 1,
            "player_outer_loop_calls": 10,
            "incidental_argument_class_counts": [1, 1, 9],
            "fixed_nine_loop_bound": False,
        },
        "FMV helper schema drifted",
    )
    record_ids = [row["id"] for row in records["records"]]
    fmv_record_ids = [
        record_id for record_id in record_ids
        if "fmv" in record_id or "decode" in record_id
    ]
    _require(
        fmv_record_ids == [],
        "incidental FMV register class leaked into record types",
    )
    return {
        "phase4_fmv": {
            "path": "config/phase4_fmv.yaml",
            "sha256": _sha256(fmv_path),
            "schema": fmv["schema"],
            "helper_contract": helper,
        },
        "record_types": {
            "path": "config/record_types.yaml",
            "sha256": _sha256(record_path),
            "fmv_or_decode_record_ids": fmv_record_ids,
            "decision": (
                "No record was added because a1-a3 are dead on entry, not "
                "decoded-record fields."
            ),
        },
    }


def _validate_semantic_sources() -> dict[str, str]:
    paths = [
        "src_re/fmv_present_rect_height_ownership.c",
        "src_re/fmv_player_streaming.c",
    ]
    required = {
        paths[0]: [
            "0x800B6C24 is a single-call wrapper, not a loop",
            "a1/a2/a3 values in",
            "must not be",
            "added to config/record_types.yaml",
        ],
        paths[1]: [
            "The wrapper is not itself a loop",
            "0x800B745C  outer player back edge",
            "not three record types",
        ],
    }
    result = {}
    for rel in paths:
        text = (ROOT / rel).read_text()
        _require(
            all(fragment in text for fragment in required[rel]),
            f"semantic source contract drifted: {rel}",
        )
        result[rel] = _sha256(ROOT / rel)
    return result


def build(
    *, fmv_data: bytes | None = None, exe_data: bytes | None = None,
    trace_data: dict[str, Any] | None = None, verify_identity: bool = True,
) -> dict[str, Any]:
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(FMV_REL, fmv)
        verify_staged_input(EXE_REL, exe)

    offline = _offline_localization()
    prior, prior_hashes = _prior_evidence(trace_data)
    trace_join = _validate_trace(prior["function_trace_result"])
    schemas = _validate_schemas()
    semantic_sources = _validate_semantic_sources()

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
    commit_accesses = _first_argument_accesses(
        fmv, COMMIT_START, COMMIT_END, base=FMV_BASE, header=0
    )
    helper_accesses = _first_argument_accesses(
        fmv, HELPER_START, HELPER_END, base=FMV_BASE, header=0
    )
    st_get_next_accesses = _first_argument_accesses(
        exe, ST_GET_NEXT_START, ST_GET_NEXT_END,
        base=EXE_BASE, header=EXE_HEADER,
    )
    _require(
        {
            name: (
                row["access"],
                row["instruction"]["pc"],
            )
            for name, row in commit_accesses.items()
            if row is not None
        } == {
            "a0": ("read", "0x800B6A84"),
            "a1": ("definition", "0x800B6A9C"),
            "a2": ("definition", "0x800B6B8C"),
            "a3": ("definition", "0x800B6B90"),
        },
        "commit entry argument use-before-definition drifted",
    )
    _require(
        helper_accesses["a0"]["access"] == "read"
        and helper_accesses["a0"]["instruction"]["pc"] == "0x800B6C2C"
        and helper_accesses["a1"]["access"] == "definition"
        and helper_accesses["a1"]["instruction"]["pc"] == "0x800B6C60"
        and helper_accesses["a2"] is None
        and helper_accesses["a3"] is None,
        "helper argument access frontier drifted",
    )
    _require(
        st_get_next_accesses["a2"]["access"] == "definition"
        and st_get_next_accesses["a2"]["instruction"]["pc"] == "0x80070CB4"
        and st_get_next_accesses["a3"]["access"] == "definition"
        and st_get_next_accesses["a3"]["instruction"]["pc"] == "0x80070C9C",
        "StGetNext inherited argument access drifted",
    )

    commit_callers = _direct_callers(fmv, COMMIT_START)
    helper_callers = _direct_callers(fmv, HELPER_START)
    jalr = _jalr_sites(fmv)
    target_refs = _raw_target_references(
        fmv, (COMMIT_START, HELPER_START)
    )
    helper_back_edges = _helper_back_edges(fmv)
    _require(
        [row["pc"] for row in commit_callers] == ["0x800B6C34"],
        "commit direct caller census drifted",
    )
    _require(
        [row["pc"] for row in helper_callers]
        == ["0x800B70A0", "0x800B7280"],
        "helper direct caller census drifted",
    )
    _require(jalr == [], "FMV indirect caller frontier drifted")
    _require(target_refs == [], "helper target became address-taken")
    _require(helper_back_edges == [], "0x800B6C24 gained a loop back edge")

    back_target = _branch_target(
        0x800B745C,
        _word(fmv, 0x800B745C, base=FMV_BASE, header=0),
    )
    _require(
        back_target == 0x800B70E0 and back_target > 0x800B70A0,
        "outer loop can revisit initialization helper call",
    )

    source_dependencies = {
        **semantic_sources,
        "config/phase4_fmv.yaml":
            schemas["phase4_fmv"]["sha256"],
        "config/record_types.yaml":
            schemas["record_types"]["sha256"],
        "tools/phase4_fmv_present_rect_height_helper_loop.py":
            _sha256(Path(__file__)),
        "tools/phase4_offline_receipt_query.py":
            _sha256(ROOT / "tools/phase4_offline_receipt_query.py"),
        "asm/hand_written/80070c9c_StGetNext.s":
            _sha256(ROOT / "asm/hand_written/80070c9c_StGetNext.s"),
        "tools/repro_inputs.sha256":
            _sha256(ROOT / "tools/repro_inputs.sha256"),
    }
    repro_line = (
        "3ee73d63990afa5b1d21049fb2945969cbdd3cbd863e8cc4048f062bd9335b94"
        "  asm/hand_written/80070c9c_StGetNext.s"
    )
    _require(
        repro_line in (ROOT / "tools/repro_inputs.sha256").read_text(),
        "StGetNext preservation pin drifted",
    )

    functions = {
        "fmv_decode_commit_dimensions": _function(
            "fmv_decode_commit_dimensions", fmv,
            COMMIT_START, COMMIT_END, base=FMV_BASE, header=0,
        ),
        "fmv_decode_one_record": _function(
            "fmv_decode_one_record", fmv,
            HELPER_START, HELPER_END, base=FMV_BASE, header=0,
        ),
        "fmv_player": _function(
            "fmv_player", fmv,
            PLAYER_START, PLAYER_END, base=FMV_BASE, header=0,
        ),
        "StGetNext": _function(
            "StGetNext", exe,
            ST_GET_NEXT_START, ST_GET_NEXT_END,
            base=EXE_BASE, header=EXE_HEADER,
        ),
    }

    return {
        "_comment": (
            "Generated from hash-verified pristine retail bytes, a closed "
            "derived-pristine offline query, and a retained bounded function "
            "trace. No copyrighted input bytes are retained."
        ),
        "schema": "abl-phase4-fmv-present-rect-height-helper-loop/1",
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
        "caller_frontier": {
            "scope": [f"0x{FMV_BASE:08X}", f"0x{FMV_CODE_END:08X}"],
            "commit_direct_callers": commit_callers,
            "helper_direct_callers": helper_callers,
            "jalr_sites": jalr,
            "raw_target_references": target_refs,
            "unclassified_callers": [],
        },
        "helper_single_call_ownership": {
            "entry": fmv_ops["0x800B6C24"],
            "boundary_argument_binding": fmv_ops["0x800B6C2C"],
            "commit_call": fmv_ops["0x800B6C34"],
            "commit_result_binding": fmv_ops["0x800B6C3C"],
            "active_index_read": fmv_ops["0x800B6C48"],
            "active_index_toggle": fmv_ops["0x800B6C54"],
            "selected_block_read": fmv_ops["0x800B6C60"],
            "no_record_latch_store": fmv_ops["0x800B6C84"],
            "guest_return": fmv_ops["0x800B6C9C"],
            "back_edges": helper_back_edges,
            "commit_calls_per_invocation": 1,
            "classification": "single_call_wrapper_not_loop",
        },
        "commit_entry_abi": {
            "computed_first_accesses": commit_accesses,
            "helper_computed_first_accesses": helper_accesses,
            "semantic_arguments": {
                "a0": {
                    "binding": fmv_ops["0x800B6A84"],
                    "value_from_both_player_calls": "0x800CABE0",
                    "role": "fmv_player_boundary_pointer",
                },
            },
            "dead_on_entry_arguments": {
                "a1": {
                    "first_definition": fmv_ops["0x800B6A9C"],
                    "computed_first_access": commit_accesses["a1"],
                },
                "a2": {
                    "first_definition": fmv_ops["0x800B6B8C"],
                    "computed_first_access": commit_accesses["a2"],
                    "StGetNext_first_definition":
                        exe_ops["0x80070CB4"],
                    "StGetNext_computed_first_access":
                        st_get_next_accesses["a2"],
                },
                "a3": {
                    "first_definition": fmv_ops["0x800B6B90"],
                    "computed_first_access": commit_accesses["a3"],
                    "StGetNext_entry_definition":
                        exe_ops["0x80070C9C"],
                    "StGetNext_computed_first_access":
                        st_get_next_accesses["a3"],
                },
            },
            "StGetNext_call": {
                "output_a0_definition": fmv_ops["0x800B6A94"],
                "call": fmv_ops["0x800B6A98"],
                "output_a1_definition": fmv_ops["0x800B6A9C"],
                "explicit_a1_preservation": exe_ops["0x80070CC8"],
                "a0_output_store": exe_ops["0x80070D50"],
                "a1_output_store": exe_ops["0x80070D54"],
                "guest_return": exe_ops["0x80070D58"],
                "external_asm_sha256": source_dependencies[
                    "asm/hand_written/80070c9c_StGetNext.s"
                ],
                "preservation_pin": repro_line.split()[0],
            },
            "internal_retry_back_edge": {
                **fmv_ops["0x800B6AA8"],
                "target": "0x800B6A98",
                "budget": "0x007FFFFF",
                "classification":
                    "StGetNext_poll_not_helper_invocation_loop",
            },
            "guest_return": fmv_ops["0x800B6C1C"],
            "classification": "single_semantic_argument_a0",
        },
        "player_call_partition": {
            "boundary_materialization": [
                fmv_ops["0x800B7098"],
                fmv_ops["0x800B709C"],
            ],
            "initialization_call": {
                "call": fmv_ops["0x800B70A0"],
                "argument_delay_slot": fmv_ops["0x800B70A4"],
                "calls_per_player_invocation": 1,
            },
            "boundary_preservation": fmv_ops["0x800B70D4"],
            "outer_loop_top": fmv_ops["0x800B70E0"],
            "outer_loop_call": {
                "call": fmv_ops["0x800B7280"],
                "argument_delay_slot": fmv_ops["0x800B7284"],
                "calls_per_outer_loop_iteration": 1,
            },
            "outer_loop_back_edge": {
                **fmv_ops["0x800B745C"],
                "target": "0x800B70E0",
                "can_revisit_initialization_call": False,
            },
            "fixed_iteration_bound": None,
            "classification":
                "one_initialization_call_then_outer_loop_calls",
        },
        "retained_trace_join": trace_join,
        "schema_decisions": schemas,
        "source_status": {
            "semantic_c": semantic_sources,
            "StGetNext": "hash_pinned_external_asm",
            "fmv_overlay": "documentation_grade_semantic_c",
            "matching_c_claimed": False,
        },
        "falsifier": {
            "packet_claim": {
                "claim": CONFIG["claim_boundary"]["packet_claim"],
                "outcome": "falsified",
                "reasons": [
                    "0x800B6C24_has_no_back_edge",
                    "repeated_calls_are_owned_by_outer_player_loop",
                    "nine_is_bounded_trace_class_count_not_static_bound",
                ],
            },
            "corrected_claim": {
                "claim": CONFIG["claim_boundary"]["corrected_claim"],
                "outcome": "survived",
                "checks": {
                    "offline_index_answer_absent": True,
                    "complete_fmv_caller_frontier_has_no_indirect_calls": True,
                    "helper_calls_commit_once_per_invocation": True,
                    "initialization_call_not_revisited_by_back_edge": True,
                    "only_a0_semantic_on_commit_entry": True,
                    "retained_trace_partitions_one_plus_ten": True,
                    "both_functions_have_conventional_guest_returns": True,
                    "synthetic_first_exit_kept_as_observer_provenance": True,
                    "incidental_classes_excluded_from_record_schema": True,
                },
            },
        },
        "claim_boundary": CONFIG["claim_boundary"],
        "summary": {
            "offline_exact_term_matches": 0,
            "direct_commit_callers": len(commit_callers),
            "direct_helper_callers": len(helper_callers),
            "indirect_fmv_calls": len(jalr),
            "helper_back_edges": len(helper_back_edges),
            "semantic_entry_arguments": 1,
            "dead_on_entry_argument_registers": 3,
            "retained_initialization_calls": 1,
            "retained_outer_loop_calls": 10,
            "promoted_dimensions": 0,
        },
        "source_dependencies": source_dependencies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.write and not args.check:
        parser.error("choose --write and/or --check")
    document = build()
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(payload)
    if args.check:
        _require(OUTPUT.is_file(), f"missing generated artifact: {OUTPUT}")
        _require(OUTPUT.read_text() == payload, "generated artifact is stale")
    print(
        "phase4 FMV helper ownership: PASS "
        "(1 init + 10 outer-loop calls; packet helper-loop claim falsified)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
