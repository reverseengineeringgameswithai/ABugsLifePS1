#!/usr/bin/env python3
"""Rebuild and measure the F01 player_vertical_update C near-match.

The comparison is deliberately symmetric.  A word emitted beyond the retail
extent or absent from the compiler output is a differing word; a size mismatch
can therefore never be hidden by truncating both sides to their common prefix.

Usage:
  python3 tools/phase4_f01_source_closure.py --write
  python3 tools/phase4_f01_source_closure.py --check
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import subprocess
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from substrate_common import (  # noqa: E402
    MASPSX,
    compile_at,
    compiler_dir,
    load_segments,
    load_toolchain_manifest,
    original_exe,
    resolve_declaration_profile,
    tool,
    va_to_off,
)

SOURCE = ROOT / "src_re" / "player_vertical_update_80048138.c"
OUTPUT = ROOT / "analysis" / "phase4_f01_source_closure.json"
TARGET_START = 0x80048138
TARGET_END = 0x800498AC
TARGET_SIZE = TARGET_END - TARGET_START
IMAGE_SHA256 = "1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20"
COMPILER_ID = "gcc2.7.2-psx"
CC1_FLAGS = ["-O2", "-G0", "-mcpu=3000", "-fno-builtin"]
MASPSX_ARGS = ["--dont-expand-li", "--expand-div"]
REGIONS = [
    ("controller_history_and_spin", 0x80048138, 0x800483B0),
    ("movement_parameters_and_status_input", 0x800483B0, 0x80048514),
    ("timers_and_special_vertical_modes", 0x80048514, 0x80048B20),
    ("jump_dive_and_landing", 0x80048B20, 0x80048E9C),
    ("horizontal_steering_and_projection", 0x80048E9C, 0x80049544),
    ("collision_fall_recovery_and_epilogue", 0x80049544, 0x800498AC),
]

GP_EXPECTED = {
    0x502: {"address": 0x8008229A, "width_bytes": 2, "access_count": 4},
    0x618: {"address": 0x800823B0, "width_bytes": 2, "access_count": 6},
    0x63C: {"address": 0x800823D4, "width_bytes": 4, "access_count": 2},
    0x69C: {"address": 0x80082434, "width_bytes": 4, "access_count": 2},
    0x73C: {"address": 0x800824D4, "width_bytes": 4, "access_count": 3},
}

FRAME_WITNESSES = [
    (0x80048138, "frame_size", -0x100),
    (0x8004813C, "save_s1", 0xDC),
    (0x80048160, "save_ra", 0xFC),
    (0x80048164, "save_fp", 0xF8),
    (0x80048168, "save_s6", 0xF0),
    (0x8004816C, "save_s4", 0xE8),
    (0x80048170, "save_s3", 0xE4),
    (0x80048174, "save_s2", 0xE0),
    (0x80048178, "save_s0", 0xD8),
    (0x80048158, "local_sp30", 0x30),
    (0x80048180, "local_sp38", 0x38),
    (0x800481B8, "local_sp40", 0x40),
    (0x800481C0, "local_sp48", 0x48),
    (0x800481BC, "local_sp50", 0x50),
    (0x8004817C, "local_sp58", 0x58),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def word_at(data: bytes, index: int) -> int | None:
    offset = index * 4
    if offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def fmt_word(value: int | None) -> str | None:
    return None if value is None else f"0x{value:08X}"


def compile_candidate(profile_name: str, *, small_data: bool = False) -> bytes:
    profile = resolve_declaration_profile(profile_name)
    include_dirs = [
        ROOT / "build" / "substrate",
        ROOT / "asm" / "hand_written",
        *profile["include_dirs"],
    ]
    compiled = compile_at(
        SOURCE,
        TARGET_START,
        compiler_id=COMPILER_ID,
        cc1_flags=CC1_FLAGS,
        maspsx_args=MASPSX_ARGS,
        include_dirs=include_dirs,
        externs={},
        small_data=small_data,
        gp=0x80081D98,
        cpp_args=profile["cpp_args"],
        section_layout=None,
    )
    if not isinstance(compiled, bytes):
        raise RuntimeError("single-text compile unexpectedly returned split sections")
    return compiled


def decode_gp_accesses(compiled: bytes) -> list[dict]:
    opcodes = {
        0x20: ("lb", "load", 1),
        0x21: ("lh", "load", 2),
        0x23: ("lw", "load", 4),
        0x24: ("lbu", "load", 1),
        0x25: ("lhu", "load", 2),
        0x28: ("sb", "store", 1),
        0x29: ("sh", "store", 2),
        0x2B: ("sw", "store", 4),
    }
    rows = []
    for index in range(len(compiled) // 4):
        word = word_at(compiled, index)
        assert word is not None
        opcode = word >> 26
        base = (word >> 21) & 0x1F
        if base != 28 or opcode not in opcodes:
            continue
        mnemonic, access, width = opcodes[opcode]
        immediate = word & 0xFFFF
        if immediate & 0x8000:
            immediate -= 0x10000
        rows.append({
            "pc": f"0x{TARGET_START + index * 4:08X}",
            "word": fmt_word(word),
            "mnemonic": mnemonic,
            "access": access,
            "width_bytes": width,
            "gp_offset": f"0x{immediate & 0xFFFF:03X}",
            "address": f"0x{0x80081D98 + immediate:08X}",
        })
    return rows


def declaration_probes(selected_compiler_dir: Path) -> dict:
    variants = {
        "extern_reference": "extern s16 g_800823b0;",
        "extern_with_sdata_attribute": (
            'extern s16 g_800823b0 __attribute__((section(".sdata")));'
        ),
        "translation_unit_definition": "s16 g_800823b0 = 1;",
        "translation_unit_sdata_definition": (
            's16 g_800823b0 __attribute__((section(".sdata"))) = 1;'
        ),
    }
    rows = []
    with tempfile.TemporaryDirectory(prefix="abl_f01_decl_probe_") as raw:
        td = Path(raw)
        for name, declaration in variants.items():
            source = td / f"{name}.c"
            preprocessed = td / f"{name}.i"
            assembly = td / f"{name}.s"
            gas_assembly = td / f"{name}_gas.s"
            obj = td / f"{name}.o"
            source.write_text(
                "typedef short s16;\n"
                f"{declaration}\n"
                "s16 probe(void) { return g_800823b0; }\n"
            )
            cpp = subprocess.run(
                [str(selected_compiler_dir / "cpp"), str(source), str(preprocessed)],
                capture_output=True,
                text=True,
            )
            if cpp.returncode != 0:
                raise RuntimeError(f"declaration probe cpp failed: {cpp.stderr}")
            cc1 = subprocess.run(
                [
                    str(selected_compiler_dir / "cc1"),
                    *CC1_FLAGS,
                    "-quiet",
                    str(preprocessed),
                    "-o",
                    str(assembly),
                ],
                capture_output=True,
                text=True,
            )
            if cc1.returncode != 0:
                raise RuntimeError(f"declaration probe cc1 failed: {cc1.stderr}")
            lines = assembly.read_text().splitlines()
            start = next(i for i, line in enumerate(lines) if line.strip() == "probe:")
            end = next(
                i for i in range(start, len(lines))
                if lines[i].strip().startswith(".end")
            )
            body = "\n".join(line.strip() for line in lines[start:end + 1]) + "\n"
            maspsx = subprocess.run(
                ["python3", str(MASPSX), *MASPSX_ARGS],
                input=assembly.read_text(),
                capture_output=True,
                text=True,
            )
            if maspsx.returncode != 0:
                raise RuntimeError(f"declaration probe maspsx failed: {maspsx.stderr}")
            gas_assembly.write_text(maspsx.stdout)
            assembler = subprocess.run(
                [
                    tool("as"), "-march=mips1", "-mabi=32", "-EL",
                    "-no-pad-sections", "-G0", "-o", str(obj), str(gas_assembly),
                ],
                capture_output=True,
                text=True,
            )
            if assembler.returncode != 0:
                raise RuntimeError(f"declaration probe as failed: {assembler.stderr}")
            disassembly = subprocess.run(
                [tool("objdump"), "-dr", str(obj)],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            relocations = sorted(set(re.findall(r"R_MIPS_[A-Z0-9]+", disassembly)))
            rows.append({
                "variant": name,
                "cc1_probe_body_sha256": sha256_bytes(body.encode("ascii")),
                "cc1_symbolic_load": "lh\t$2,g_800823b0" in body,
                "cc1_explicit_gp_operand": "$28" in body,
                "g0_relocations": relocations,
                "gprel16_emitted": "R_MIPS_GPREL16" in relocations,
            })
    return {
        "probe_definition": (
            "minimal C read of the same signed halfword, compiled with the pinned "
            "cc1 flags and assembled with -G0"
        ),
        "variants": rows,
        "conclusion": (
            "extern/definition and .sdata provenance do not select $gp under the "
            "pinned GNU-as -G0 tail; every variant emits HI16/LO16 and no GPREL16"
        ),
    }


def build_receipt() -> dict:
    seg = load_segments()
    # The segment manifest's historical `image: SCUS_942.88` points at the
    # repository-root convenience copy.  Phase-0 policy makes the pinned
    # REBUILD input the authoritative pristine base, so override only this path
    # before calling the canonical hash-checking loader.
    seg = {**seg, "image": "REBUILD/files/SCUS_942.88"}
    image = original_exe(seg)
    observed_image_sha256 = sha256_bytes(image)
    if observed_image_sha256 != IMAGE_SHA256:
        raise RuntimeError(
            f"pristine image sha256 {observed_image_sha256} != {IMAGE_SHA256}"
        )

    profile = resolve_declaration_profile("cleanroom_unprototyped")
    compiled = compile_candidate(profile["name"])

    image_offset = va_to_off(seg, TARGET_START)
    retail = image[image_offset:image_offset + TARGET_SIZE]
    if len(retail) != TARGET_SIZE:
        raise RuntimeError(f"retail slice is {len(retail)} bytes, expected {TARGET_SIZE}")

    target_words = TARGET_SIZE // 4
    compiled_words = len(compiled) // 4
    compared_words = max(target_words, compiled_words)
    differences = []
    for index in range(compared_words):
        retail_word = word_at(retail, index)
        compiled_word = word_at(compiled, index)
        if retail_word != compiled_word:
            differences.append({
                "address": f"0x{TARGET_START + 4 * index:08X}",
                "retail_word": fmt_word(retail_word),
                "compiled_word": fmt_word(compiled_word),
            })

    region_rows = []
    for name, start, end in REGIONS:
        first = (start - TARGET_START) // 4
        count = (end - start) // 4
        diff_count = sum(
            word_at(retail, first + i) != word_at(compiled, first + i)
            for i in range(count)
        )
        region_rows.append({
            "name": name,
            "start": f"0x{start:08X}",
            "end_exclusive": f"0x{end:08X}",
            "word_count": count,
            "differing_words": diff_count,
            "equal_words": count - diff_count,
        })
    closed_prefix = 0
    for row in region_rows:
        if row["differing_words"] != 0:
            break
        closed_prefix += 1
    for index, row in enumerate(region_rows):
        if index < closed_prefix:
            row["status"] = "closed"
            row["gate_scored"] = True
            row["closed"] = True
            row["words_remaining"] = 0
        elif index == closed_prefix:
            row["status"] = "active_open"
            row["gate_scored"] = True
            row["closed"] = False
            row["words_remaining"] = row["differing_words"]
        else:
            row["status"] = "not_attempted_gate_blocked"
            row["gate_scored"] = False
            row["closed"] = False
            row["words_remaining"] = None
    if compiled_words > target_words:
        region_rows.append({
            "name": "compiled_tail_outside_target",
            "start": f"0x{TARGET_END:08X}",
            "end_exclusive": f"0x{TARGET_START + len(compiled):08X}",
            "word_count": compiled_words - target_words,
            "differing_words": compiled_words - target_words,
            "equal_words": 0,
            "status": "outside_retail_extent",
        })

    manifest = load_toolchain_manifest()
    compiler = next(c for c in manifest["compilers"] if c["id"] == COMPILER_ID)
    selected_compiler_dir = compiler_dir(COMPILER_ID)
    observed_cc1_sha256 = sha256_file(selected_compiler_dir / "cc1")
    observed_cpp_sha256 = sha256_file(selected_compiler_dir / "cpp")
    if observed_cc1_sha256 != compiler["cc1_sha256"]:
        raise RuntimeError("selected cc1 does not match its toolchain-manifest pin")
    if observed_cpp_sha256 != compiler["cpp_sha256"]:
        raise RuntimeError("selected cpp does not match its toolchain-manifest pin")
    profile_rows = []
    for profile_name in ("source", "cleanroom_prototyped", "cleanroom_unprototyped"):
        profile_bytes = compiled if profile_name == profile["name"] else compile_candidate(
            profile_name
        )
        profile_rows.append({
            "profile": profile_name,
            "compiled_size_bytes": len(profile_bytes),
            "compiled_sha256": sha256_bytes(profile_bytes),
        })

    try:
        compile_candidate(profile["name"], small_data=True)
    except RuntimeError as error:
        small_data_error = str(error)
        small_data_probe = {
            "outcome": "link_error",
            "gprel16_overflow": "R_MIPS_GPREL16" in small_data_error,
            "small_data_section_too_large": "small-data section too large" in small_data_error,
            "contract_changed": False,
            "note": (
                "The probe is diagnostic only. The retained compile remains -G0; "
                "global -G8 over-selects distant 0x800A/0x800B objects and cannot link."
            ),
        }
    else:
        small_data_probe = {
            "outcome": "unexpected_success",
            "gprel16_overflow": False,
            "small_data_section_too_large": False,
            "contract_changed": False,
        }

    gp_accesses = decode_gp_accesses(compiled)
    gp_counts = Counter(int(row["gp_offset"], 16) for row in gp_accesses)
    gp_summary = []
    for offset, expected in GP_EXPECTED.items():
        matching = [row for row in gp_accesses if int(row["gp_offset"], 16) == offset]
        observed_widths = sorted(set(row["width_bytes"] for row in matching))
        gp_summary.append({
            "gp_offset": f"0x{offset:03X}",
            "address": f"0x{expected['address']:08X}",
            "expected_width_bytes": expected["width_bytes"],
            "observed_width_bytes": observed_widths,
            "expected_access_count": expected["access_count"],
            "observed_access_count": gp_counts[offset],
            "matches": (
                observed_widths == [expected["width_bytes"]]
                and gp_counts[offset] == expected["access_count"]
            ),
        })
    unexpected_gp_offsets = sorted(set(gp_counts) - set(GP_EXPECTED))
    if not all(row["matches"] for row in gp_summary) or unexpected_gp_offsets:
        raise RuntimeError("compiled $gp access set does not match the frozen 17-access set")

    exact_prefix_words = 0
    while (
        exact_prefix_words < min(target_words, compiled_words)
        and word_at(retail, exact_prefix_words) == word_at(compiled, exact_prefix_words)
    ):
        exact_prefix_words += 1
    frame_witnesses = []
    for pc, role, frame_value in FRAME_WITNESSES:
        index = (pc - TARGET_START) // 4
        retail_word = word_at(retail, index)
        compiled_word = word_at(compiled, index)
        frame_witnesses.append({
            "pc": f"0x{pc:08X}",
            "role": role,
            "frame_value": frame_value,
            "retail_word": fmt_word(retail_word),
            "compiled_word": fmt_word(compiled_word),
            "equal": retail_word == compiled_word,
        })
    if not all(row["equal"] for row in frame_witnesses):
        raise RuntimeError("retail frame-map witness diverged")

    exact_match = not differences and len(compiled) == TARGET_SIZE
    near_miss = (
        not exact_match
        and len(compiled) == TARGET_SIZE
        and len(differences) <= 16
    )
    result = "MATCH" if exact_match else "NEAR_MISS" if near_miss else "NO_GO"
    active_region = region_rows[closed_prefix] if closed_prefix < len(region_rows) else None
    active_differences = 0 if active_region is None else active_region["differing_words"]
    return {
        "schema": "abl-phase4-f01-source-closure/2",
        "result": result,
        "execution_freeze": {
            "issued_baseline_commit": "7ea89416dfaff1d4e9d8498ee806d24b23e41e6f",
            "freeze_commit": "10339263c1e89a37817c55ba84e393883fc46c5e",
            "issued_baseline_status_short_line_count": 116,
            "issued_baseline_status_short_sha256": (
                "dbb9bee516c80b08983dd3cb4cafdfb799a939818771c90a899407c0d31b1616"
            ),
            "status_note": (
                "Hash and count cover the exact git status --short captured before "
                "work; the 116 paths are pre-existing operator WIP and are excluded "
                "from this work order's commit."
            ),
            "pre_outcome_contents": (
                "baseline identity, status digest, observed-vs-pinned compiler "
                "contract, and the immutable six-region table only"
            ),
        },
        "target": {
            "name": "player_vertical_update",
            "start": f"0x{TARGET_START:08X}",
            "end_exclusive": f"0x{TARGET_END:08X}",
            "size_bytes": TARGET_SIZE,
            "word_count": target_words,
            "retail_slice_sha256": sha256_bytes(retail),
        },
        "inputs": {
            "image": "REBUILD/files/SCUS_942.88",
            "image_sha256": observed_image_sha256,
            "source": SOURCE.relative_to(ROOT).as_posix(),
            "source_sha256": sha256_file(SOURCE),
        },
        "compiler_contract": {
            "compiler_id": COMPILER_ID,
            "gcc_version": compiler["gcc_version"],
            "cc1_sha256_pin": compiler["cc1_sha256"],
            "cc1_sha256_observed": observed_cc1_sha256,
            "cpp_sha256_pin": compiler["cpp_sha256"],
            "cpp_sha256_observed": observed_cpp_sha256,
            "maspsx_commit_pin": manifest["assembler_shim"]["commit"],
            "maspsx_entry_sha256_observed": sha256_file(MASPSX),
            "cc1_flags": CC1_FLAGS,
            "maspsx_args": MASPSX_ARGS,
            "declaration_profile": profile["name"],
            "small_data": False,
            "placement_va": f"0x{TARGET_START:08X}",
        },
        "classification": {
            "exact_match_definition": (
                "compiled size is exactly 6004 bytes and every compared word is equal"
            ),
            "near_miss_definition": (
                "compiled size is exactly 6004 bytes and at most 16 word positions differ"
            ),
            "exact_match": exact_match,
            "near_miss": near_miss,
            "no_go": result == "NO_GO",
        },
        "region_gate": {
            "order_frozen": True,
            "regions_closed": closed_prefix,
            "region_count": len(REGIONS),
            "regions": [
                {
                    "number": index + 1,
                    "name": row["name"],
                    "start": row["start"],
                    "end_exclusive": row["end_exclusive"],
                    "closed": row["closed"],
                    "words_remaining": row["words_remaining"],
                    "status": row["status"],
                }
                for index, row in enumerate(region_rows[:len(REGIONS)])
            ],
            "first_open_region": (
                None
                if active_region is None
                else {
                    "number": closed_prefix + 1,
                    "name": active_region["name"],
                    "start": active_region["start"],
                    "end_exclusive": active_region["end_exclusive"],
                    "words_remaining": active_differences,
                }
            ),
            "active_region_number": None if active_region is None else closed_prefix + 1,
            "active_region_name": None if active_region is None else active_region["name"],
            "words_remaining_in_active_region": (
                active_differences
            ),
            "progress_statement": (
                f"{closed_prefix} of {len(REGIONS)} regions closed; "
                + (
                    "no active region"
                    if active_region is None
                    else (
                        f"{active_differences} words remaining in "
                        f"region {closed_prefix + 1}"
                    )
                )
            ),
            "later_region_work_authorized": active_region is None,
            "stop_rule": (
                "region 1 did not close after the ordered Phase 0 probes and local "
                "C-source scheduling pass; regions 2-6 remain unattempted"
            ),
        },
        "phase0_findings": {
            "frame_and_register_map": {
                "status": "cleared",
                "retail_frame_size_bytes": 0x100,
                "compiled_frame_size_bytes": 0x100,
                "exact_prefix_word_count": exact_prefix_words,
                "exact_prefix_end_exclusive": (
                    f"0x{TARGET_START + exact_prefix_words * 4:08X}"
                ),
                "witnesses": frame_witnesses,
            },
            "mixed_gp_relative_addressing": {
                "status": "cleared",
                "gp_value": "0x80081D98",
                "expected_access_count": 17,
                "observed_access_count": len(gp_accesses),
                "region_1_observed_access_count": sum(
                    int(row["pc"], 16) < REGIONS[0][2] for row in gp_accesses
                ),
                "summary": gp_summary,
                "accesses": gp_accesses,
                "implementation": (
                    "C lvalues based on the ABI $gp register; no inline or hand ASM"
                ),
            },
            "ordered_hypothesis_tests": {
                "definition_vs_extern_and_sdata": declaration_probes(
                    selected_compiler_dir
                ),
                "declaration_profile": {
                    "profiles": profile_rows,
                    "all_outputs_identical": len({
                        row["compiled_sha256"] for row in profile_rows
                    }) == 1,
                    "conclusion": (
                        "source, cleanroom_prototyped, and cleanroom_unprototyped "
                        "produce byte-identical output"
                    ),
                },
                "nonzero_g": small_data_probe,
            },
        },
        "measurement": {
            "definition": (
                "little-endian 4-byte words at placement VA; compare through the "
                "longer extent, so absent retail/compiled words count as differences"
            ),
            "compiled_size_bytes": len(compiled),
            "compiled_word_count": compiled_words,
            "compiled_sha256": sha256_bytes(compiled),
            "size_delta_bytes": len(compiled) - TARGET_SIZE,
            "compared_word_positions": compared_words,
            "equal_word_positions": compared_words - len(differences),
            "differing_word_positions": len(differences),
            "retail_extent_differing_word_positions": sum(
                1 for row in differences
                if int(row["address"], 16) < TARGET_END
            ),
            "compiled_only_word_positions": max(0, compiled_words - target_words),
            "retail_only_word_positions": max(0, target_words - compiled_words),
            "differences": differences,
        },
        "regions": region_rows,
        "hand_asm_regions": [],
        "hand_asm_statement": (
            "None. The hash-pinned exact handwritten transcription remains separate "
            "and is not an input to this C compile."
        ),
        "semantic_limitations": [
            (
                "The source is a compiler-scored decompilation seed, not a claim of "
                "behavioral equivalence; the region gate remains at 0 of 6 closed."
            ),
            (
                "m2c marked the collision-result switch irregular and inferred an "
                "unsigned temporary whose generated comparison against zero is always "
                "false; both remain named source-recovery work, not established retail C."
            ),
            (
                "Fields +0x86, +0x96, and +0x97 have known access widths but no "
                "semantics established by this receipt, so the C names them only by offset."
            ),
        ],
        "attempt_history": [
            {
                "stage": "normalized_m2c_seed",
                "outcome": "compiler_error",
                "evidence_status": "unretained_executor_observation",
                "independently_reproducible": False,
                "supports_current_result": False,
                "note": (
                    "The intermediate seed and compiler output were not retained or "
                    "hash-pinned. This observation records workflow only and supplies "
                    "no evidence for the current verdict."
                ),
            },
            {
                "stage": "width_and_address_repair",
                "outcome": "compiled_near_miss",
                "evidence_status": "unretained_executor_observation",
                "independently_reproducible": False,
                "supports_current_result": False,
                "note": (
                    "No exact size, diff, or improvement figure is retained because the "
                    "intermediate source and output were not banked."
                ),
            },
            {
                "stage": "callee_save_role_and_frame_shape_repair",
                "outcome": "NEAR_MISS",
                "evidence_status": "retained_and_hash_pinned",
                "independently_reproducible": True,
                "supports_current_result": False,
                "compiled_size_bytes": 6012,
                "differing_word_positions": 1447,
                "source_sha256": (
                    "d6c1f29a7702e3c05e947a1574565e21f756c887f8d0aefb9b269737199d56cf"
                ),
                "compiled_sha256": (
                    "19afcde822c8261de8d38ed63970d32e6e0f184fb3cc6640b6ae4392a83e1e6a"
                ),
            },
            {
                "stage": "v2_phase0_and_region_1_gate",
                "outcome": result,
                "evidence_status": "retained_and_hash_pinned",
                "independently_reproducible": True,
                "supports_current_result": True,
                "compiled_size_bytes": len(compiled),
                "differing_word_positions": len(differences),
                "regions_closed": closed_prefix,
                "active_region_differing_words": (
                    active_differences
                ),
                "source_sha256": sha256_file(SOURCE),
                "compiled_sha256": sha256_bytes(compiled),
            },
        ],
        "compiler_walls": [
            {
                "class": "extent_and_cfg_shape",
                "binding_subproblem": (
                    "region_1_source_expression_order_and_register_lifetime"
                ),
                "wall_shape": "technique_shaped",
                "evidence": (
                    f"The C now reproduces the first {exact_prefix_words} words, exact "
                    "retail frame/save/local offsets, and all 17 mixed-$gp accesses. "
                    f"Region 1 still has {active_differences} positional "
                    "word differences because the remaining history-loop and spin-reset "
                    "expressions schedule/register-allocate differently. This is a limit "
                    "of the present source-recovery/search technique, not evidence that "
                    "the binary structurally forbids a C-origin proof."
                ),
            },
        ],
        "no_go": {
            "binding_wall": "extent_and_cfg_shape",
            "binding_subproblem": (
                "region_1_source_expression_order_and_register_lifetime"
            ),
            "wall_shape": "technique_shaped",
            "later_regions_attempted": False,
            "reason": (
                "The frozen gate forbids region 2 work until region 1 reaches zero; "
                f"region 1 remains at {active_differences} differing words."
            ),
        },
        "dc_permute": {
            "used": False,
            "reason": (
                f"Not eligible: compiled size is {len(compiled)} rather than 6004 bytes "
                f"and the active region has {active_differences} differences."
            ),
        },
        "source_closure_eligible_for_promotion": result == "MATCH",
        "status_statement": (
            "F01 source_closure remains partial; v2 stops NO-GO at region 1 and does "
            "not promote the dimension."
        ),
        "reproduction": {
            "write": "python3 tools/phase4_f01_source_closure.py --write",
            "check": "python3 tools/phase4_f01_source_closure.py --check",
        },
    }


def render(receipt: dict) -> str:
    return json.dumps(receipt, indent=1, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    expected = render(build_receipt())
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected)
        try:
            display_output = output.relative_to(ROOT)
        except ValueError:
            display_output = output
        print(f"[phase4-f01-source-closure] wrote {display_output}")
        return 0

    if not output.exists():
        print(f"[phase4-f01-source-closure] missing {output}", file=sys.stderr)
        return 1
    observed = output.read_text()
    if observed != expected:
        print(
            "[phase4-f01-source-closure] STALE: rerun with --write",
            file=sys.stderr,
        )
        return 1
    receipt = json.loads(observed)
    print(
        "[phase4-f01-source-closure] PASS: "
        f"{receipt['result']} {receipt['region_gate']['progress_statement']}; "
        f"size delta {receipt['measurement']['size_delta_bytes']:+d} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
