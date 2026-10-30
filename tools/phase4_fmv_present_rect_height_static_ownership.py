#!/usr/bin/env python3
"""Reconstruct the E15 presentation-RECT height owner from pristine bytes."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from build_identity import verify_staged_input
import exe_read
import phase4_common as common


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/phase4_fmv_present_rect_height_static_ownership.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_present_rect_height_static_ownership.json"
CONFIG = common.load_yaml(CONFIG_PATH)
RUN_ROOT = Path(CONFIG["run_root"]).resolve()

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
FMV_BASE = 0x800B5788
FMV_CODE_END = 0x800B9A4C

EXPECTED_FMV_WORDS = {
    0x800B6A84: 0x00808821,  # addu s1,a0,zero
    0x800B6BE0: 0x94849A5C,  # lhu a0,cached_frame_height
    0x800B6BE8: 0xA624001E,  # sh a0,rect[1].h(s1)
    0x800B6BEC: 0xA6240016,  # sh a0,rect[0].h(s1)
    0x800B6BF0: 0xA624002A,  # sh a0,present.h(s1)
    0x800B6C2C: 0x00808021,  # addu s0,a0,zero
    0x800B6C34: 0x0C02DA9F,  # jal 0x800b6a7c
    0x800B7098: 0x3C10800D,  # lui s0,0x800d
    0x800B709C: 0x2610ABE0,  # addiu s0,s0,-21536
    0x800B70A0: 0x0C02DB09,  # jal 0x800b6c24
    0x800B70A4: 0x02002021,  # addu a0,s0,zero
    0x800B70D4: 0x02009821,  # addu s3,s0,zero
    0x800B7280: 0x0C02DB09,  # jal 0x800b6c24
    0x800B7284: 0x02602021,  # addu a0,s3,zero
    0x800B6874: 0x3C10800D,  # lui s0,0x800d
    0x800B6878: 0x2610AC04,  # addiu s0,s0,-21500
    0x800B6884: 0x0C018A30,  # jal LoadImage
    0x800B6888: 0x02002021,  # addu a0,s0,zero
}

EXPECTED_EXE_WORDS = {
    0x800628E8: 0x02002821,  # addu a1,s0,zero
    0x800628F0: 0x8C42FBC0,  # lw v0,gpu_driver
    0x800628F8: 0x8C440020,  # lw a0,32(v0) == driver[8]
    0x800628FC: 0x8C420008,  # lw v0,8(v0) == driver[2]
    0x80062904: 0x0040F809,  # jalr v0
    0x800646C0: 0x00809821,  # addu s3,a0,zero
    0x800646C8: 0x00A08021,  # addu s0,a1,zero
    0x800647C0: 0x02002021,  # addu a0,s0,zero
    0x800647C4: 0x0260F809,  # jalr s3
    0x800647DC: 0xAC530000,  # sw s3,queued callback
    0x800647E4: 0xAC30FCC0,  # sw s0,queued RECT
    0x80064928: 0xAC3365D8,  # sw s3,ring callback
    0x800640D4: 0x00808821,  # addu s1,a0,zero
    0x80064130: 0x86250006,  # lh a1,6(s1)
    0x80064144: 0x8442FBCE,  # lh v0,gpu height bound
    0x80064164: 0x00002021,  # addu a0,zero,zero
    0x80064178: 0xA6240006,  # sh a0,6(s1)
}

FUNCTIONS = {
    "fmv_present_upload": (FMV_PATH, 0x800B6634, 0x800B6A7C, FMV_BASE, 0),
    "fmv_decode_commit_dimensions": (
        FMV_PATH, 0x800B6A7C, 0x800B6C24, FMV_BASE, 0),
    "fmv_decode_one_record": (
        FMV_PATH, 0x800B6C24, 0x800B6CA4, FMV_BASE, 0),
    "LoadImage": (EXE_PATH, 0x800628C0, 0x80062924, EXE_BASE, EXE_HEADER),
    "_dws": (EXE_PATH, 0x800640CC, 0x80064308, EXE_BASE, EXE_HEADER),
    "gpu_present_drawotag_vsync": (
        EXE_PATH, 0x800646B8, 0x80064998, EXE_BASE, EXE_HEADER),
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _word(data: bytes, address: int, *, base: int, header: int) -> int:
    offset = header + address - base
    _require(
        header <= offset <= len(data) - 4,
        f"instruction address out of range: 0x{address:08X}",
    )
    return struct.unpack_from("<I", data, offset)[0]


def _instruction(
    data: bytes, address: int, expected: int, *, base: int, header: int
) -> dict[str, Any]:
    actual = _word(data, address, base=base, header=header)
    _require(
        actual == expected,
        f"opcode drift at 0x{address:08X}: 0x{actual:08X} != 0x{expected:08X}",
    )
    return {
        "pc": f"0x{address:08X}",
        "word": f"0x{actual:08X}",
        "mnemonic": exe_read.disasm_one(address, actual),
    }


def _slice(
    data: bytes, start: int, end: int, *, base: int, header: int
) -> bytes:
    begin = header + start - base
    finish = header + end - base
    _require(header <= begin < finish <= len(data), "function slice out of range")
    return data[begin:finish]


def _function(
    name: str, data: bytes, start: int, end: int, *, base: int, header: int
) -> dict[str, Any]:
    body = _slice(data, start, end, base=base, header=header)
    return {
        "name": name,
        "start": f"0x{start:08X}",
        "end": f"0x{end:08X}",
        "size": len(body),
        "sha256": _sha256_bytes(body),
    }


def _jal_target(pc: int, word: int) -> int | None:
    if word >> 26 != 3:
        return None
    return ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def _direct_callers(fmv: bytes, target: int) -> list[dict[str, Any]]:
    rows = []
    for pc in range(FMV_BASE, FMV_CODE_END, 4):
        word = _word(fmv, pc, base=FMV_BASE, header=0)
        if _jal_target(pc, word) == target:
            rows.append(_instruction(
                fmv, pc, word, base=FMV_BASE, header=0))
    return rows


def _load_run_artifact(spec: dict[str, Any], label: str) -> tuple[Path, dict]:
    path = RUN_ROOT / spec["relative_path"]
    _require(path.is_file(), f"missing {label}: {path}")
    _require(_sha256(path) == spec["sha256"], f"{label} hash drifted")
    return path, json.loads(path.read_text())


def _offline_localization() -> dict[str, Any]:
    spec = CONFIG["offline_query"]
    receipt_path, receipt = _load_run_artifact(spec["receipt"], "offline receipt")
    output_path, output = _load_run_artifact(spec["output"], "offline output")
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
    external = receipt.get("external_inputs") or []
    _require(
        len(external) == 1
        and external[0].get("sha256") == spec["external_index_sha256"],
        "offline input identity drifted",
    )
    _require(
        output.get("schema") == "abl-phase4-offline-json-search-result/1"
        and output.get("source", {}).get("sha256")
        == spec["external_index_sha256"],
        "offline output source drifted",
    )
    terms = output.get("terms") or {}
    _require(
        set(terms) == set(spec["expected_zero_terms"])
        and all(row == {
            "count": 0, "paths": [], "paths_truncated": False
        } for row in terms.values()),
        "offline zero-result boundary drifted",
    )
    return {
        "receipt": {
            "path": str(receipt_path),
            "sha256": spec["receipt"]["sha256"],
            "reader_sha256": receipt["reader"]["sha256"],
            "command": receipt["command"],
            "exit_code": receipt["execution"]["exit_code"],
            "stdout_sha256": receipt["execution"]["stdout_sha256"],
        },
        "external_index": {
            "sha256": spec["external_index_sha256"],
            "bytes": output["source"]["bytes"],
            "domains": ["block_flow", "ram", "registers", "vram", "spu"],
        },
        "output": {
            "path": str(output_path),
            "sha256": spec["output"]["sha256"],
            "zero_match_terms": sorted(terms),
        },
        "finding": (
            "The retained frame-boundary index contains no exact symbol/address "
            "lead for either writer, so pristine static code owns localization."
        ),
    }


def _prior_evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    loaded = {}
    hashes = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(path.is_file() and _sha256(path) == spec["sha256"],
                 f"{name} identity drifted")
        loaded[name] = json.loads(path.read_text())
        hashes[spec["path"]] = spec["sha256"]
    prior = loaded["saturated_writer_result"]
    _require(
        prior["falsifier"]["outcome"] == "falsified"
        and prior["observation"]["precise"]["native"]["writer_pc_counts"]
        == {"0x80064178": 28, "0x800b6bf0": 3, "0x800b6f18": 1}
        and prior["claim_boundary"]["complete_writer_sequence_closed"] is False,
        "prior saturated writer boundary drifted",
    )
    static = loaded["static_owners"]
    _require(
        static["player_typed_state"]["structures"]["double_buffer"]["base"]
        == "0x800CABE0"
        and static["player_typed_state"]["structures"]["present_rect"]["base"]
        == "0x800CAC04",
        "prior typed player boundary drifted",
    )
    return static, prior, hashes


def _validate_sources() -> dict[str, Any]:
    segments = common.load_yaml(ROOT / "config/segments.yml")["attempted"]
    expected = {
        (0x800628C0, 0x80062924): "src/main/800628c0_LoadImage.c",
        (0x800640CC, 0x80064308): "asm/hand_written/800640cc__dws.s",
        (0x800646B8, 0x80064998):
            "asm/hand_written/800646b8_gpu_present_drawotag_vsync.s",
    }
    found = {
        (int(row["start"]), int(row["end"])): row["source"]
        for row in segments
        if (int(row["start"]), int(row["end"])) in expected
    }
    _require(found == expected, "segment source ownership drifted")
    pins = {}
    for line in (ROOT / "tools/repro_inputs.sha256").read_text().splitlines():
        if "  asm/hand_written/800640cc__dws.s" in line or \
                "  asm/hand_written/800646b8_gpu_present_drawotag_vsync.s" in line:
            digest, path = line.split(None, 1)
            pins[path] = digest
    _require(pins == {
        "asm/hand_written/800640cc__dws.s":
            "dc4822038c0499b55b1e62adc358cab072db1623c757c5f95838e7d2cbeb1c26",
        "asm/hand_written/800646b8_gpu_present_drawotag_vsync.s":
            "8faa5ba6e1e80da0b9e6b5d27f1eb39a402aaa202d43407cbbd15b79c2068f50",
    }, "external ASM preservation pins drifted")
    symbols = {}
    for line in (ROOT / "symbols/re_symbols.sym").read_text().splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0] in {
            "800628C0", "800640CC", "800646B8"
        }:
            symbols[f"0x{parts[0]}"] = parts[1]
    _require(symbols == {
        "0x800628C0": "LoadImage",
        "0x800640CC": "_dws",
        "0x800646B8": "gpu_present_drawotag_vsync",
    }, "resident symbols drifted")
    return {
        "segments": [
            {"start": f"0x{start:08X}", "end": f"0x{end:08X}",
             "source": source}
            for (start, end), source in sorted(found.items())
        ],
        "matching_c": {
            "path": "src/main/800628c0_LoadImage.c",
            "sha256": _sha256(ROOT / "src/main/800628c0_LoadImage.c"),
        },
        "external_asm_pins": pins,
        "symbols": symbols,
        "status": {
            "LoadImage": "matching_c",
            "_dws": "hash_pinned_external_asm",
            "gpu_present_drawotag_vsync": "hash_pinned_external_asm",
            "fmv_player": "documentation_grade_semantic_c",
        },
    }


def build(
    *, exe_data: bytes | None = None, fmv_data: bytes | None = None,
    verify_identity: bool = True,
) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(FMV_REL, fmv)

    offline = _offline_localization()
    _, prior, evidence_hashes = _prior_evidence()
    fmv_instructions = {
        f"0x{address:08X}": _instruction(
            fmv, address, word, base=FMV_BASE, header=0)
        for address, word in EXPECTED_FMV_WORDS.items()
    }
    exe_instructions = {
        f"0x{address:08X}": _instruction(
            exe, address, word, base=EXE_BASE, header=EXE_HEADER)
        for address, word in EXPECTED_EXE_WORDS.items()
    }
    callers_commit = _direct_callers(fmv, 0x800B6A7C)
    callers_helper = _direct_callers(fmv, 0x800B6C24)
    _require(
        [row["pc"] for row in callers_commit] == ["0x800B6C34"]
        and [row["pc"] for row in callers_helper]
        == ["0x800B70A0", "0x800B7280"],
        "FMV direct-caller census drifted",
    )

    function_rows = {}
    for name, (path, start, end, base, header) in FUNCTIONS.items():
        data = fmv if path == FMV_PATH else exe
        function_rows[name] = _function(
            name, data, start, end, base=base, header=header)

    vtable = [
        _word(exe, 0x8007FB80 + 4 * index,
              base=EXE_BASE, header=EXE_HEADER)
        for index in range(10)
    ]
    expected_vtable = [
        0x8001BF04, 0x80064694, 0x800646B8, 0x80063E70,
        0x8006458C, 0x800645C8, 0x80064618, 0x80064308,
        0x800640CC, 0x80064998,
    ]
    _require(vtable == expected_vtable, "resident libgpu vtable drifted")
    driver_pointer = _word(
        exe, 0x8007FBC0, base=EXE_BASE, header=EXE_HEADER)
    _require(driver_pointer == 0x8007FB80, "resident libgpu driver pointer drifted")

    sources = _validate_sources()
    pc_counts = prior["observation"]["precise"]["native"]["writer_pc_counts"]
    classifications = {
        "0x800b6f18": "FMV.BIN direct initializer, constant 240",
        "0x800b6bf0":
            "FMV.BIN cached-height publish through base 0x800CABE0 + 0x2A",
        "0x80064178":
            "resident PsyQ _dws clamp of the supplied RECT height",
    }
    _require(
        pc_counts == {"0x80064178": 28, "0x800b6bf0": 3, "0x800b6f18": 1},
        "retained writer PC count drifted",
    )
    _require(set(pc_counts) == set(classifications),
             "retained writer PC remains unclassified")

    return {
        "_comment": (
            "Generated from hash-verified pristine bytes, one closed retained "
            "offline query and the bounded saturated runtime result. No "
            "copyrighted input bytes are retained."
        ),
        "schema": "abl-phase4-fmv-present-rect-height-static-ownership/1",
        "generated": "2026-07-28",
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "lane": CONFIG["lane"],
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "sha256": _sha256_bytes(exe),
                "size": len(exe),
                "identity_verified": verify_identity,
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}",
                "sha256": _sha256_bytes(fmv),
                "size": len(fmv),
                "identity_verified": verify_identity,
            },
            "config": {
                "path": str(CONFIG_PATH.relative_to(ROOT)),
                "sha256": _sha256(CONFIG_PATH),
            },
            "prior_evidence": evidence_hashes,
        },
        "offline_localization": offline,
        "functions": function_rows,
        "overlay_cached_height_publish": {
            "player_boundary_base": "0x800CABE0",
            "base_materialization": [
                fmv_instructions["0x800B7098"],
                fmv_instructions["0x800B709C"],
            ],
            "first_helper_call": {
                "call": fmv_instructions["0x800B70A0"],
                "argument_delay_slot": fmv_instructions["0x800B70A4"],
            },
            "loop_base_preservation": fmv_instructions["0x800B70D4"],
            "second_helper_call": {
                "call": fmv_instructions["0x800B7280"],
                "argument_delay_slot": fmv_instructions["0x800B7284"],
            },
            "helper_argument_preservation": fmv_instructions["0x800B6C2C"],
            "helper_to_commit_call": fmv_instructions["0x800B6C34"],
            "commit_base_binding": fmv_instructions["0x800B6A84"],
            "cached_height_load": {
                **fmv_instructions["0x800B6BE0"],
                "source_address": "0x800B9A5C",
                "source_type": "u32 containing zero-extended u16",
                "loaded_view": "u16",
            },
            "height_stores": [
                {**fmv_instructions["0x800B6BE8"],
                 "offset": "0x1E", "destination": "0x800CABFE",
                 "field": "rect_bank_1_h"},
                {**fmv_instructions["0x800B6BEC"],
                 "offset": "0x16", "destination": "0x800CABF6",
                 "field": "rect_bank_0_h"},
                {**fmv_instructions["0x800B6BF0"],
                 "offset": "0x2A", "destination": "0x800CAC0A",
                 "field": "present_rect_h"},
            ],
            "direct_callers": {
                "0x800B6A7C": callers_commit,
                "0x800B6C24": callers_helper,
                "unclassified": [],
            },
        },
        "resident_sdk_normalization": {
            "present_rect_materialization": [
                fmv_instructions["0x800B6874"],
                fmv_instructions["0x800B6878"],
            ],
            "LoadImage_call": {
                "call": fmv_instructions["0x800B6884"],
                "argument_delay_slot": fmv_instructions["0x800B6888"],
                "rect_address": "0x800CAC04",
            },
            "LoadImage_dispatch": {
                "rect_forward": exe_instructions["0x800628E8"],
                "driver_pointer_load": exe_instructions["0x800628F0"],
                "driver_pointer_address": "0x8007FBC0",
                "driver_pointer_value": "0x8007FB80",
                "callback_argument_load": exe_instructions["0x800628F8"],
                "wrapper_load": exe_instructions["0x800628FC"],
                "indirect_call": exe_instructions["0x80062904"],
                "vtable": [
                    {"index": index, "value": f"0x{value:08X}"}
                    for index, value in enumerate(vtable)
                ],
                "driver_2": "0x800646B8",
                "driver_8": "0x800640CC",
            },
            "queue_wrapper": {
                "callback_binding": exe_instructions["0x800646C0"],
                "rect_binding": exe_instructions["0x800646C8"],
                "direct_path_rect_argument": exe_instructions["0x800647C0"],
                "direct_path_call": exe_instructions["0x800647C4"],
                "single_entry_callback_store": exe_instructions["0x800647DC"],
                "single_entry_rect_store": exe_instructions["0x800647E4"],
                "ring_callback_store": exe_instructions["0x80064928"],
            },
            "_dws_clamp": {
                "rect_binding": exe_instructions["0x800640D4"],
                "height_load": exe_instructions["0x80064130"],
                "upper_bound_load": exe_instructions["0x80064144"],
                "negative_clamp": exe_instructions["0x80064164"],
                "height_store": {
                    **exe_instructions["0x80064178"],
                    "field": "RECT.h",
                    "classification": "downstream SDK bounds normalization",
                },
            },
        },
        "runtime_writer_join": {
            "retained_event_capacity": 32,
            "capacity_reached": True,
            "complete_sequence_closed": False,
            "writer_pc_counts": pc_counts,
            "pc_classification": classifications,
            "unclassified_writer_pcs": [],
            "first_240_to_128_store": "0x800B6BF0",
            "interpretation": (
                "The transition is the FMV cached-height publish. The repeated "
                "resident store belongs to the downstream libgpu RECT clamp; "
                "event saturation still forbids a complete sequence claim."
            ),
        },
        "source_status": sources,
        "falsifier": {
            "claim": CONFIG["claim_boundary"]["exact_claim"],
            "outcome": "survived",
            "checks": {
                "both_player_callers_pass_exact_boundary_base": True,
                "helper_preserves_argument_into_commit_function": True,
                "source_and_three_destinations_exact": True,
                "direct_caller_census_exhaustive": True,
                "LoadImage_driver_table_resolves_dws": True,
                "all_retained_writer_pcs_owned": True,
            },
        },
        "claim_boundary": CONFIG["claim_boundary"],
        "summary": {
            "offline_exact_term_matches": 0,
            "overlay_functions_reconstructed": 3,
            "resident_functions_reconstructed": 3,
            "overlay_direct_callers": 3,
            "height_destinations": 3,
            "retained_writer_pcs_classified": len(classifications),
            "unclassified_writer_pcs": 0,
            "promoted_dimensions": 0,
        },
        "source_dependencies": {
            "config/segments.yml": _sha256(ROOT / "config/segments.yml"),
            "symbols/re_symbols.sym": _sha256(ROOT / "symbols/re_symbols.sym"),
            "tools/repro_inputs.sha256":
                _sha256(ROOT / "tools/repro_inputs.sha256"),
            "src/main/800628c0_LoadImage.c":
                _sha256(ROOT / "src/main/800628c0_LoadImage.c"),
            "src_re/fmv_present_rect_height_ownership.c":
                _sha256(ROOT / "src_re/fmv_present_rect_height_ownership.c"),
            "tools/phase4_fmv_present_rect_height_static_ownership.py":
                _sha256(Path(__file__)),
        },
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
        "phase4 FMV present-RECT static ownership: PASS "
        "(3/3 retained writer PCs classified; 0 dimension promotions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
