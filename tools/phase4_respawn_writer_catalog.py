#!/usr/bin/env python3
"""Catalog direct pristine Region-A writers of the C15 safe-respawn tuple.

This is deliberately a static breadth census.  It enumerates every centrally
hash-pinned ``LEVEL*/LEVEL.BIN`` staged input, resolves conservative local MIPS
constants, and records only direct stores whose effective address is one of the
three safe-position words or the safe heading.  A zero result does not exclude
pointer-mediated writers, and a static writer does not establish runtime
activation or player-visible checkpoint policy.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from typing import Any

try:
    from build_identity import verify_staged_input
except ModuleNotFoundError:  # imported as tools.phase4_respawn_writer_catalog
    from tools.build_identity import verify_staged_input


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_respawn_writer_catalog.json"
STAGED_ROOT = ROOT / "REBUILD/files"
REGION_A_LOAD = 0x800B39A0
TARGETS = {
    0x800A6550: ("safe_anchor_x", 4),
    0x800A6554: ("safe_anchor_y", 4),
    0x800A6558: ("safe_anchor_z", 4),
    0x800A6578: ("safe_anchor_heading", 2),
}
REGISTER_NAMES = (
    "zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
    "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
    "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
    "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra",
)

# These are expected discoveries, not the scan input.  The scanner derives the
# complete list from all staged files and fails if a site disappears or a new
# direct writer appears without review.
EXPECTED_WRITES = {
    "LEVEL03/LEVEL.BIN": (
        (0x800B3D24, 0x800A6550, 4, 0xAC830000),
        (0x800B3D34, 0x800A6554, 4, 0xAC256554),
        (0x800B3D40, 0x800A6558, 4, 0xAC226558),
        (0x800B3D54, 0x800A6554, 4, 0xAC226554),
    ),
    "LEVEL04/LEVEL.BIN": (
        (0x800B3C94, 0x800A6550, 4, 0xACA3FFC0),
        (0x800B3C9C, 0x800A6558, 4, 0xAC226558),
        (0x800B3CA8, 0x800A6554, 4, 0xAC246554),
        (0x800B3CB0, 0x800A6578, 2, 0xA4226578),
        (0x800B3CC4, 0x800A6554, 4, 0xAC226554),
    ),
    "LEVEL06/LEVEL.BIN": (
        (0x800B3B00, 0x800A6550, 4, 0xAC236550),
        (0x800B3B24, 0x800A6554, 4, 0xAC226554),
        (0x800B3B30, 0x800A6578, 2, 0xA4226578),
        (0x800B3B3C, 0x800A6558, 4, 0xAC246558),
    ),
    "LEVEL08/LEVEL.BIN": (
        (0x800B3B08, 0x800A6550, 4, 0xAC256550),
        (0x800B3B10, 0x800A6554, 4, 0xAC246554),
        (0x800B3B18, 0x800A6558, 4, 0xAC236558),
        (0x800B3B20, 0x800A6578, 2, 0xA4226578),
    ),
    "LEVEL10/LEVEL.BIN": (
        (0x800B3BAC, 0x800A6550, 4, 0xAC830000),
        (0x800B3BBC, 0x800A6554, 4, 0xAC256554),
        (0x800B3BC8, 0x800A6558, 4, 0xAC226558),
        (0x800B3BDC, 0x800A6554, 4, 0xAC226554),
    ),
}

WRITER_FUNCTIONS = {
    "LEVEL03/LEVEL.BIN": {
        "runtime_range": (0x800B3C54, 0x800B3D78),
        "classification": "status_gated_nearest_row_with_ground_query",
        "evidence_scope": "live_causal_and_static",
    },
    "LEVEL04/LEVEL.BIN": {
        "runtime_range": (0x800B3C5C, 0x800B3CD8),
        "classification": "status_gated_fixed_tuple_with_ground_query",
        "evidence_scope": "live_attributed_and_static",
    },
    "LEVEL06/LEVEL.BIN": {
        "runtime_range": (0x800B3AEC, 0x800B3B94),
        "classification": "fixed_safe_tuple_initialization",
        "evidence_scope": "static_only",
    },
    "LEVEL08/LEVEL.BIN": {
        "runtime_range": (0x800B3AE8, 0x800B3B54),
        "classification": "fixed_safe_and_live_tuple_initialization",
        "evidence_scope": "static_only",
    },
    "LEVEL10/LEVEL.BIN": {
        "runtime_range": (0x800B3ADC, 0x800B3C1C),
        "classification": "status_gated_nearest_row_with_ground_query",
        "evidence_scope": "live_attributed_and_static",
    },
}

C15_ARTIFACT = ROOT / "analysis/phase4_checkpoint_respawn.json"
C15_ARTIFACT_SHA256 = (
    "fc71182a5ffeb1acc15a305d4c707ac2f2846ebc173497d48a4bbc3fd1fc0660")
OVERLAY_MAP = ROOT / "analysis/phase3_overlay_map.json"
OVERLAY_MAP_SHA256 = (
    "cf116c3ad4ec1bfb849dba80e22ccaff56faa0de20cb83b56924b4ae445beec7")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _signed(value: int, width: int) -> int:
    bits = width * 8
    sign = 1 << (bits - 1)
    mask = (1 << bits) - 1
    value &= mask
    return value - (1 << bits) if value & sign else value


def _constant_write(registers: dict[int, int], word: int) -> tuple[int, int] | None:
    """Return (destination register, constant) or invalidate with ``None``.

    Only the small constant-building subset needed by this census is evaluated.
    Callers separately invalidate registers written by other instructions.
    """
    opcode = word >> 26
    rs = (word >> 21) & 31
    rt = (word >> 16) & 31
    rd = (word >> 11) & 31
    immediate = word & 0xFFFF
    signed_immediate = immediate if immediate < 0x8000 else immediate - 0x10000
    function = word & 0x3F
    shift = (word >> 6) & 31

    if opcode == 0x0F:  # lui
        return rt, immediate << 16
    if opcode == 0x09:  # addiu
        return rt, ((registers[rs] + signed_immediate) & 0xFFFFFFFF) \
            if rs in registers else None
    if opcode == 0x0D:  # ori
        return rt, ((registers[rs] | immediate) & 0xFFFFFFFF) \
            if rs in registers else None
    if opcode == 0 and function in (0x21, 0x25):  # addu / or
        if rs not in registers or rt not in registers:
            return rd, None
        value = registers[rs] + registers[rt] if function == 0x21 \
            else registers[rs] | registers[rt]
        return rd, value & 0xFFFFFFFF
    if opcode == 0 and function == 0x00:  # sll
        return rd, ((registers[rt] << shift) & 0xFFFFFFFF) \
            if rt in registers else None

    # Ordinary ALU-immediate and load instructions overwrite rt.
    if opcode in {
            0x08, 0x0A, 0x0B, 0x0C, 0x0E,
            0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26,
            0x30, 0x31, 0x32, 0x33, 0x36, 0x37}:
        return rt, None
    # Remaining arithmetic SPECIAL instructions overwrite rd.  Jumps, moves
    # to HI/LO and traps have rd=0 and therefore leave the constant map alone.
    if opcode == 0 and rd:
        return rd, None
    if opcode == 0x03:  # jal writes ra
        return 31, None
    return None


def scan_direct_writes(data: bytes) -> list[dict[str, Any]]:
    registers: dict[int, int] = {0: 0}
    pending_boundary: str | None = None
    rows: list[dict[str, Any]] = []
    store_widths = {0x28: 1, 0x29: 2, 0x2B: 4}
    caller_saved = set(range(2, 16)) | {24, 25, 31}

    for offset in range(0, len(data) - 3, 4):
        word = struct.unpack_from("<I", data, offset)[0]
        opcode = word >> 26
        rs = (word >> 21) & 31
        rt = (word >> 16) & 31
        immediate = word & 0xFFFF
        signed_immediate = immediate if immediate < 0x8000 else immediate - 0x10000

        if opcode in store_widths and rs in registers:
            effective = (registers[rs] + signed_immediate) & 0xFFFFFFFF
            if effective in TARGETS:
                width = store_widths[opcode]
                target_name, expected_width = TARGETS[effective]
                if width != expected_width:
                    raise SystemExit(
                        f"C15 direct writer has wrong width at 0x{REGION_A_LOAD + offset:08X}")
                source = registers.get(rt)
                source_row = None
                if source is not None:
                    source_row = {
                        "raw": f"0x{source & ((1 << (width * 8)) - 1):0{width * 2}X}",
                        "signed": _signed(source, width),
                    }
                rows.append({
                    "runtime_address": f"0x{REGION_A_LOAD + offset:08X}",
                    "file_offset": f"0x{offset:X}",
                    "instruction_word": f"0x{word:08X}",
                    "width": width,
                    "base_register": REGISTER_NAMES[rs],
                    "source_register": REGISTER_NAMES[rt],
                    "target": target_name,
                    "target_address": f"0x{effective:08X}",
                    "constant_source": source_row,
                })

        constant = _constant_write(registers, word)
        if constant is not None:
            destination, value = constant
            if destination:
                if value is None:
                    registers.pop(destination, None)
                else:
                    registers[destination] = value

        # Apply a previous call/return boundary only after its delay slot.
        if pending_boundary == "return":
            registers = {0: 0}
        elif pending_boundary == "call":
            for register in caller_saved:
                registers.pop(register, None)
        pending_boundary = None

        is_jr_ra = opcode == 0 and (word & 0x3F) == 0x08 and rs == 31
        if is_jr_ra:
            pending_boundary = "return"
        elif opcode == 0x03:
            pending_boundary = "call"

    return rows


def _expected_tuple(rows: list[dict[str, Any]]) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (int(row["runtime_address"], 16), int(row["target_address"], 16),
         row["width"], int(row["instruction_word"], 16))
        for row in rows)


def _live_evidence_join() -> dict[str, Any]:
    if _sha256(C15_ARTIFACT) != C15_ARTIFACT_SHA256:
        raise SystemExit("C15 live artifact changed; regenerate/review the writer join")
    document = json.loads(C15_ARTIFACT.read_text())
    static = document["static_census"]
    attribution = {
        row["id"]: row for row in document["live"]["pit_writer_attribution"]}
    if static["overlay_safe_anchor_selector"]["sha256"] != \
            "1fdeb0da151050edbde73a082b5951ae4326ec133979ca5bae2f0198bd8cfbf9":
        raise SystemExit("LEVEL03 live/static writer join drifted")
    if attribution["scene_10_pit"]["access_log"]["total"] != 4 or \
            attribution["scene_10_pit"]["access_log"]["truncated"] is not False:
        raise SystemExit("LEVEL10 writer attribution is incomplete")
    if attribution["scene_4_pit"]["access_log"]["total"] != 5 or \
            attribution["scene_4_pit"]["access_log"]["truncated"] is not False:
        raise SystemExit("LEVEL04 writer attribution is incomplete")
    return {
        "artifact": "analysis/phase4_checkpoint_respawn.json",
        "artifact_sha256": C15_ARTIFACT_SHA256,
        "LEVEL03/LEVEL.BIN": {
            "evidence": (
                "selected-row X +128 changes safe/live X +4096; clearing only "
                "status mask 0x0010 denies all selector stores and retains the "
                "prior safe anchor"),
            "slice_sha256": static["overlay_safe_anchor_selector"]["sha256"],
            "selected_row": document["live"]["reset_owner"]["selector"]["selected"]["index"],
            "denial_selector_hits": document["live"]["reset_owner"]["branches"]
                ["selector_status_bit_cleared"]["post_reset"]
                ["cycle_neutral_trace"]["coverage"][0]["total_hits"],
        },
        "LEVEL04/LEVEL.BIN": {
            "evidence": "complete transition-boundary write attribution",
            "slice_sha256": static["pit_transition_writers"]["scene_4_pit"]["sha256"],
            "access_events": attribution["scene_4_pit"]["access_log"]["total"],
        },
        "LEVEL10/LEVEL.BIN": {
            "evidence": "complete transition-boundary write attribution",
            "slice_sha256": static["pit_transition_writers"]["scene_10_pit"]["sha256"],
            "access_events": attribution["scene_10_pit"]["access_log"]["total"],
        },
    }


def _resident_entry_call_sites() -> dict[str, list[str]]:
    """Return static resident callers of reused Region-A entry addresses.

    These are address-level candidates only.  The resident executable cannot
    identify which level overlay is loaded when a reused entry is called.
    """
    if _sha256(OVERLAY_MAP) != OVERLAY_MAP_SHA256:
        raise SystemExit("Phase-3 overlay map changed; regenerate/review caller join")
    document = json.loads(OVERLAY_MAP.read_text())
    return {
        row["entry"]: row["resident_call_sites"]
        for row in document["region_a_shared_entry_points"]
    }


def build_document() -> dict[str, Any]:
    paths = sorted(STAGED_ROOT.glob("LEVEL*/LEVEL.BIN"))
    if len(paths) != 11:
        raise SystemExit(f"expected 11 staged LEVEL.BIN inputs, found {len(paths)}")

    inputs: list[dict[str, Any]] = []
    writers: dict[str, Any] = {}
    entry_call_sites = _resident_entry_call_sites()
    for path in paths:
        rel = path.relative_to(STAGED_ROOT).as_posix()
        data = path.read_bytes()
        verify_staged_input(rel, data)
        rows = scan_direct_writes(data)
        expected = EXPECTED_WRITES.get(rel, ())
        if _expected_tuple(rows) != expected:
            raise SystemExit(
                f"C15 direct-writer census changed for {rel}: "
                f"{_expected_tuple(rows)} != {expected}")
        inputs.append({
            "path": f"REBUILD/files/{rel}",
            "size": len(data),
            "sha256": _sha256(path),
            "direct_writer_count": len(rows),
        })
        if not rows:
            continue
        spec = WRITER_FUNCTIONS[rel]
        start, end = spec["runtime_range"]
        file_offset = start - REGION_A_LOAD
        function = data[file_offset:file_offset + end - start]
        if len(function) != end - start:
            raise SystemExit(f"C15 writer function range escaped {rel}")
        writers[rel] = {
            "path": f"REBUILD/files/{rel}",
            "file_sha256": _sha256(path),
            "runtime_start": f"0x{start:08X}",
            "runtime_end": f"0x{end:08X}",
            "file_offset": f"0x{file_offset:X}",
            "size": len(function),
            "sha256": _sha256_bytes(function),
            "classification": spec["classification"],
            "evidence_scope": spec["evidence_scope"],
            "static_resident_entry_call_sites": entry_call_sites.get(
                f"0x{start:08X}", []),
            "caller_boundary": (
                "resident JAL targets to a reused Region-A address; loaded-"
                "overlay activation is not established"),
            "direct_writes": rows,
        }

    target_counts = {name: 0 for name, _ in TARGETS.values()}
    for writer in writers.values():
        for row in writer["direct_writes"]:
            target_counts[row["target"]] += 1
    zero_paths = [row["path"] for row in inputs if row["direct_writer_count"] == 0]
    return {
        "_comment": (
            "Static C15 breadth evidence. Direct absolute stores are exhaustive "
            "for the eleven pinned LEVEL.BIN inputs under the declared scanner; "
            "runtime activation and indirect writers remain separate questions."),
        "schema": "abl-phase4-respawn-writer-catalog/1",
        "row": "C15_checkpoints",
        "generator": "tools/phase4_respawn_writer_catalog.py",
        "generator_sha256": _sha256(Path(__file__)),
        "scan_contract": {
            "region_a_load": f"0x{REGION_A_LOAD:08X}",
            "targets": {
                name: {"address": f"0x{address:08X}", "width": width}
                for address, (name, width) in TARGETS.items()
            },
            "method": (
                "conservative local constant propagation over little-endian MIPS "
                "words, reset after jr-ra delay slots and caller-clobbered after "
                "jal delay slots; only resolved direct stores are counted"),
        },
        "staged_inputs": inputs,
        "writer_functions": writers,
        "summary": {
            "staged_input_count": len(inputs),
            "writer_file_count": len(writers),
            "direct_write_count": sum(target_counts.values()),
            "target_write_counts": target_counts,
            "writer_paths": list(writers),
            "zero_direct_writer_paths": zero_paths,
            "new_static_only_variants": [
                "REBUILD/files/LEVEL06/LEVEL.BIN",
                "REBUILD/files/LEVEL08/LEVEL.BIN",
            ],
            "new_static_only_resident_entry_call_sites": [
                {
                    "path": "REBUILD/files/LEVEL06/LEVEL.BIN",
                    "entry": "0x800B3AEC",
                    "resident_call_sites": entry_call_sites["0x800B3AEC"],
                },
                {
                    "path": "REBUILD/files/LEVEL08/LEVEL.BIN",
                    "entry": "0x800B3AE8",
                    "resident_call_sites": entry_call_sites["0x800B3AE8"],
                },
            ],
        },
        "existing_live_evidence_join": _live_evidence_join(),
        "bounded_interpretation": {
            "observation": (
                "Five of eleven pinned LEVEL.BIN inputs contain 21 resolved "
                "direct stores to safe X/Y/Z/heading. LEVEL06 and LEVEL08 add "
                "distinct fixed-tuple initializer functions to the three "
                "previously live-bound writer functions."),
            "inference": (
                "The pristine Region-A family has at least nearest-row, fixed-"
                "ground, fixed-safe initialization, and fixed-safe-plus-live "
                "initialization forms."),
            "causal_confirmation": (
                "Only LEVEL03 has a retained selected-row mutation; LEVEL04 and "
                "LEVEL10 have complete live writer attribution. The two newly "
                "cataloged functions are not causal runtime evidence."),
            "still_unknown": (
                "LEVEL06/LEVEL08 runtime activation and denial policy, authored source "
                "ownership, pointer-mediated writers, overlay variants outside "
                "the staged LEVEL.BIN set, reset/persistence scope, and remaining "
                "death-class/stage breadth."),
        },
        "source_dependencies": {
            "tools/build_baselines.json": _sha256(ROOT / "tools/build_baselines.json"),
            "analysis/phase4_checkpoint_respawn.json": C15_ARTIFACT_SHA256,
            "analysis/phase3_overlay_map.json": OVERLAY_MAP_SHA256,
        },
    }


def main() -> int:
    document = build_document()
    OUTPUT.write_text(json.dumps(document, indent=1) + "\n")
    print(
        "[respawn-writer-catalog] "
        f"{document['summary']['writer_file_count']}/"
        f"{document['summary']['staged_input_count']} files, "
        f"{document['summary']['direct_write_count']} direct writes; "
        "2 new static-only variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
