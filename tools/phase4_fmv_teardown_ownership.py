#!/usr/bin/env python3
"""Reconstruct E15 callback-teardown ownership from pristine static bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from build_identity import verify_staged_input
import exe_read


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/phase4_fmv_teardown_ownership.json"
EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
LIFECYCLE_PATH = ROOT / "analysis/phase4_fmv_callback_lifecycle.json"
PHASE3_CALLBACKS = ROOT / "analysis/phase3_jalr_callbacks.json"
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
EXE_TEXT_SIZE = 0x72800
FMV_BASE = 0x800B5788

TEARDOWN = (0x800709AC, 0x80070A30)
READY_SLOT = 0x800818C8
MODE_FIELD = 0x800818E8
MMIO_POINTER_TABLE = (0x80081C28, 0x80081C38)

EXPECTED_TEARDOWN_WORDS = {
    0x800709AC: 0x27BDFFE8,
    0x800709B0: 0xAFBF0010,
    0x800709B4: 0x0C0197EF,
    0x800709BC: 0x3C038008,
    0x800709C0: 0x8C6318E8,
    0x800709C4: 0x24020001,
    0x800709C8: 0x14620007,
    0x800709D0: 0x0C02E68A,
    0x800709D4: 0x00002021,
    0x800709D8: 0x0C02E685,
    0x800709DC: 0x00002021,
    0x800709E0: 0x0801C27E,
    0x800709E8: 0x0C01B73C,
    0x800709EC: 0x00002021,
    0x800709F0: 0x0C01B634,
    0x800709F4: 0x00002021,
    0x800709F8: 0x3C028008,
    0x800709FC: 0x8C421C28,
    0x80070A04: 0xA0400000,
    0x80070A08: 0x3C028008,
    0x80070A0C: 0x8C421C34,
    0x80070A14: 0xA0400000,
    0x80070A18: 0x0C0197F3,
    0x80070A20: 0x8FBF0010,
    0x80070A24: 0x27BD0018,
    0x80070A28: 0x03E00008,
    0x80070A2C: 0x00000000,
}

EXPECTED_READY_XREFS = {
    0x8006D8D4: ("read", "CdReadyCallback_previous"),
    0x8006D8DC: ("write", "CdReadyCallback_install"),
    0x8006E5BC: ("read", "CD_sync_dispatch"),
    0x8006E844: ("read", "CD_ready_dispatch"),
    0x8006ECB4: ("read", "CD_cw_dispatch"),
    0x8006F010: ("write", "CD_initintr_clear"),
    0x8006F098: ("write", "CD_init_clear"),
    0x8006F600: ("read", "CD_interrupt_dispatch"),
}

EXPECTED_DISPATCH_SITES = {
    0x8006E5BC: 0x8006E5D8,
    0x8006E844: 0x8006E860,
    0x8006ECB4: 0x8006ECD0,
    0x8006F600: 0x8006F61C,
}

EXPECTED_WRAPPER_WORDS = {
    0x8006DCF0: 0x27BDFFE8,
    0x8006DCF4: 0xAFBF0010,
    0x8006DCF8: 0x00802821,
    0x8006DCFC: 0x0C01950D,
    0x8006DD00: 0x24040003,
    0x8006DD04: 0x8FBF0010,
    0x8006DD08: 0x27BD0018,
    0x8006DD0C: 0x03E00008,
    0x8006DD10: 0x00000000,
    0x80065434: 0x3C028008,
    0x80065438: 0x8C420DE0,
    0x80065444: 0x8C420004,
    0x8006544C: 0x0040F809,
}

EXPECTED_FMV_WORDS = {
    0x800B74A4: 0x0C01C26B,
    0x800B74A8: 0x00000000,
    0x800B74AC: 0x0C02E46B,
    0x800B9A14: 0x3C03800D,
    0x800B9A18: 0x2463AECC,
    0x800B9A1C: 0x8C620000,
    0x800B9A20: 0x03E00008,
    0x800B9A24: 0xAC640000,
    0x800B9A28: 0x27BDFFE8,
    0x800B9A30: 0x00802821,
    0x800B9A34: 0x0C01950D,
    0x800B9A38: 0x24040003,
    0x800B9A44: 0x03E00008,
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _slice(data: bytes, address: int, size: int, *, base: int,
           header: int) -> bytes:
    offset = header + address - base
    if offset < header or offset + size > len(data):
        raise SystemExit(f"invalid static slice 0x{address:08X}+0x{size:X}")
    return data[offset:offset + size]


def _word(data: bytes, address: int, *, base: int, header: int) -> int:
    return struct.unpack(
        "<I", _slice(data, address, 4, base=base, header=header))[0]


def _hex(value: int) -> str:
    return f"0x{value:08X}"


def _instruction(data: bytes, address: int, *, base: int,
                 header: int) -> dict[str, str]:
    word = _word(data, address, base=base, header=header)
    return {
        "pc": _hex(address),
        "word": _hex(word),
        "mnemonic": exe_read.disasm_one(address, word),
    }


def _require_words(data: bytes, expected: dict[int, int], *, base: int,
                   header: int, label: str) -> list[dict[str, str]]:
    rows = []
    for address, expected_word in expected.items():
        observed = _word(data, address, base=base, header=header)
        if observed != expected_word:
            raise SystemExit(
                f"{label} opcode drifted at 0x{address:08X}: "
                f"expected 0x{expected_word:08X}, observed 0x{observed:08X}")
        rows.append(_instruction(
            data, address, base=base, header=header))
    return rows


def _direct_slot_xrefs(exe: bytes, address: int) -> list[int]:
    """Find compiler-standard adjacent LUI plus direct LW/SW accesses."""
    upper = (address >> 16) & 0xFFFF
    lower = address & 0xFFFF
    found = []
    for pc in range(EXE_BASE + 4, EXE_BASE + EXE_TEXT_SIZE, 4):
        word = _word(exe, pc, base=EXE_BASE, header=EXE_HEADER)
        op = word >> 26
        if op not in (0x23, 0x2B) or (word & 0xFFFF) != lower:
            continue
        base_register = (word >> 21) & 0x1F
        previous = _word(
            exe, pc - 4, base=EXE_BASE, header=EXE_HEADER)
        if (previous >> 26) != 0x0F:
            continue
        if ((previous >> 16) & 0x1F) != base_register:
            continue
        if (previous & 0xFFFF) != upper:
            continue
        found.append(pc)
    return found


def _ready_slot(exe: bytes) -> dict[str, Any]:
    actual = _direct_slot_xrefs(exe, READY_SLOT)
    if actual != list(EXPECTED_READY_XREFS):
        raise SystemExit(
            "default ready-callback slot xref census drifted: "
            f"expected {[ _hex(x) for x in EXPECTED_READY_XREFS ]}, "
            f"observed {[ _hex(x) for x in actual ]}")
    rows = []
    for pc, (access, owner) in EXPECTED_READY_XREFS.items():
        row: dict[str, Any] = {
            "instruction": _instruction(
                exe, pc, base=EXE_BASE, header=EXE_HEADER),
            "access": access,
            "owner": owner,
        }
        if pc in EXPECTED_DISPATCH_SITES:
            jalr = EXPECTED_DISPATCH_SITES[pc]
            jalr_row = _instruction(
                exe, jalr, base=EXE_BASE, header=EXE_HEADER)
            if jalr_row["word"] != "0x0040F809":
                raise SystemExit(
                    f"default ready-callback dispatch drifted at 0x{jalr:08X}")
            row["guarded_dispatch"] = jalr_row
        rows.append(row)
    return {
        "address": _hex(READY_SLOT),
        "storage": "resident pointer32",
        "swap_function": {
            "range": ["0x8006D8D0", "0x8006D8E8"],
            "previous_value_returned_in": "v0",
            "new_value_source": "a0",
            "load": "0x8006D8D4",
            "store": "0x8006D8DC",
        },
        "xrefs": rows,
        "summary": {
            "total_direct_xrefs": len(rows),
            "reads": sum(row["access"] == "read" for row in rows),
            "writes": sum(row["access"] == "write" for row in rows),
            "guarded_dispatches": len(EXPECTED_DISPATCH_SITES),
            "all_direct_xrefs_classified": True,
        },
    }


def _teardown(exe: bytes, fmv: bytes) -> dict[str, Any]:
    instructions = _require_words(
        exe, EXPECTED_TEARDOWN_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="callback teardown")
    fmv_instructions = _require_words(
        fmv, EXPECTED_FMV_WORDS, base=FMV_BASE, header=0,
        label="FMV teardown caller/backend")
    mode_xrefs = _direct_slot_xrefs(exe, MODE_FIELD)
    if mode_xrefs != [0x800709C0]:
        raise SystemExit(
            "callback teardown mode-field xref census drifted: "
            f"{[ _hex(x) for x in mode_xrefs ]}")
    return {
        "function": {
            "range": [_hex(TEARDOWN[0]), _hex(TEARDOWN[1])],
            "size": TEARDOWN[1] - TEARDOWN[0],
            "critical_section": {
                "enter": {"call": "0x800709B4", "target": "0x80065FBC",
                          "syscall_code": 1},
                "exit": {"call": "0x80070A18", "target": "0x80065FCC",
                         "syscall_code": 2},
            },
            "mode": {
                "address": _hex(MODE_FIELD),
                "read": "0x800709C0",
                "direct_xrefs": [_hex(pc) for pc in mode_xrefs],
                "value_1_backend": "FMV.BIN alternate wrappers",
                "other_values_backend": "resident PsyQ callback APIs",
            },
            "instructions": instructions,
        },
        "caller": {
            "call": "0x800B74A4",
            "return_address": "0x800B74AC",
            "next_call": {"site": "0x800B74AC", "target": "0x800B91AC"},
        },
        "guest_return": {
            "classification": "conventional_balanced_return",
            "stack_allocation": 24,
            "saved_ra": {"store": "0x800709B0", "offset": 16},
            "restored_ra": {"load": "0x80070A20", "offset": 16},
            "stack_restore": "0x80070A24",
            "return_instruction": "0x80070A28",
            "delay_slot": "0x80070A2C",
            "caller_continuation": "0x800B74AC",
            "synthetic_guest_return_instruction": False,
        },
        "backends": {
            "default": {
                "data_clear": {"call": "0x800709E8",
                               "target": "0x8006DCF0", "argument": 0},
                "ready_clear": {"call": "0x800709F0",
                                "target": "0x8006D8D0", "argument": 0},
            },
            "mode_1": {
                "data_clear": {"call": "0x800709D0",
                               "target": "0x800B9A28", "argument": 0},
                "ready_clear": {"call": "0x800709D8",
                                "target": "0x800B9A14", "argument": 0},
                "ready_slot": {
                    "address": "0x800CAECC",
                    "swap_function": ["0x800B9A14", "0x800B9A28"],
                },
            },
        },
        "fmv_instructions": fmv_instructions,
    }


def _mmio_pointer_table(exe: bytes, lifecycle: dict) -> dict[str, Any]:
    start, end = MMIO_POINTER_TABLE
    raw = _slice(
        exe, start, end - start, base=EXE_BASE, header=EXE_HEADER)
    words = list(struct.unpack("<4I", raw))
    expected = [0x1F801800, 0x1F801801, 0x1F801802, 0x1F801803]
    if words != expected:
        raise SystemExit(
            "CD-ROM MMIO pointer table drifted: "
            f"expected {[ _hex(x) for x in expected ]}, "
            f"observed {[ _hex(x) for x in words ]}")
    captured = lifecycle["observations"]["fixed_callback_words"]
    if captured["positive"] != raw.hex() or captured["negative"] != raw.hex():
        raise SystemExit(
            "retained callback-word capture no longer matches pristine "
            "CD-ROM MMIO pointer cells")
    return {
        "range": [_hex(start), _hex(end)],
        "storage": "four resident pointer32 cells",
        "values": [_hex(value) for value in words],
        "targets": [
            {"cell": _hex(start + index * 4), "target": _hex(value),
             "cdrom_register": index}
            for index, value in enumerate(words)
        ],
        "retained_capture": {
            "hex": raw.hex(),
            "positive_matches_pristine_table": True,
            "negative_matches_pristine_table": True,
            "captured_words_are_pointer_cells": True,
            "captured_words_are_callback_storage": False,
            "equal_after_capture_is_expected": True,
        },
        "teardown_target_stores": [
            {
                "pointer_cell": "0x80081C28",
                "load": "0x800709FC",
                "target": "0x1F801800",
                "store": "0x80070A04",
                "width": "u8",
                "value": 0,
            },
            {
                "pointer_cell": "0x80081C34",
                "load": "0x80070A0C",
                "target": "0x1F801803",
                "store": "0x80070A14",
                "width": "u8",
                "value": 0,
            },
        ],
        "boundary": (
            "The retained 16-byte endpoint capture observes the immutable "
            "resident pointer cells, not the volatile MMIO bytes written "
            "through those pointers. Equality cannot falsify either target store."
        ),
    }


def _data_callback(exe: bytes) -> dict[str, Any]:
    instructions = _require_words(
        exe, EXPECTED_WRAPPER_WORDS, base=EXE_BASE, header=EXE_HEADER,
        label="default data-callback wrapper")
    return {
        "function": {
            "range": ["0x8006DCF0", "0x8006DD14"],
            "behavior": "DMACallback(3, a0)",
            "dma_callback_call": "0x8006DCFC",
            "channel_argument": {"site": "0x8006DD00", "value": 3},
        },
        "sdk_dispatch": {
            "entry": "0x80065434",
            "kernel_table_pointer_cell": "0x80080DE0",
            "function_field_offset": 4,
            "jalr": "0x8006544C",
            "storage_boundary": (
                "The game calls the PsyQ DMACallback API. Its callback storage "
                "is kernel-private behind this table dispatch and is not promoted "
                "to game-owned MOD state."
            ),
        },
        "instructions": instructions,
    }


def build(*, exe_data: bytes | None = None, fmv_data: bytes | None = None,
          lifecycle_doc: dict | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    lifecycle = (
        json.loads(LIFECYCLE_PATH.read_text())
        if lifecycle_doc is None else lifecycle_doc)
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
        verify_staged_input(FMV_REL, fmv)
    if lifecycle.get("schema") != "abl-phase4-fmv-callback-lifecycle/1":
        raise SystemExit("unexpected callback-lifecycle schema")
    live_teardown = lifecycle["observations"]["positive_common_exit"][
        "callback_teardown"]
    if live_teardown != {
            "address": "0x800709ac",
            "caller": "0x800b74a4",
            "entry_cycle": 2644274321,
            "exit_cycle": 2644284120,
            "exit_is_synthetic_unwind": True,
            "exit_v0": "0x00000001",
            "return_address": "0x800b74ac"}:
        raise SystemExit("retained callback-teardown live observation drifted")

    teardown = _teardown(exe, fmv)
    ready = _ready_slot(exe)
    mmio = _mmio_pointer_table(exe, lifecycle)
    data = _data_callback(exe)
    return {
        "schema": "abl-phase4-fmv-teardown-ownership/1",
        "generated": "2026-07-24",
        "row": "E15_fmv",
        "lane": "static",
        "inputs": {
            "resident_executable": {
                "path": f"REBUILD/files/{EXE_REL}",
                "size": len(exe),
                "sha256": _sha256_bytes(exe),
                "identity_verified": verify_identity,
            },
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}",
                "size": len(fmv),
                "sha256": _sha256_bytes(fmv),
                "identity_verified": verify_identity,
            },
        },
        "retained_live_join": {
            "artifact": "analysis/phase4_fmv_callback_lifecycle.json",
            "sha256": _sha256(LIFECYCLE_PATH),
            "caller": live_teardown["caller"],
            "return_address": live_teardown["return_address"],
            "function_trace_synthetic_unwind": True,
            "interpretation": (
                "The retained event classification is preserved. Static guest "
                "bytes independently prove a balanced epilogue and contain no "
                "synthetic return instruction; the event must not be rewritten "
                "as a guest control-flow edge."
            ),
        },
        "teardown": teardown,
        "callback_backends": {
            "default": {
                "ready": ready,
                "data": data,
            },
            "mode_1": teardown["backends"]["mode_1"],
        },
        "cdrom_mmio_pointer_table": mmio,
        "reconciliation": {
            "function_trace_flag_preserved": True,
            "guest_return_is_conventional": True,
            "synthetic_unwind_is_guest_return": False,
            "captured_words_are_callback_words": False,
            "captured_words_are_mmio_pointer_cells": True,
            "captured_pointer_equality_falsifies_target_stores": False,
        },
        "summary": {
            "teardown_size": TEARDOWN[1] - TEARDOWN[0],
            "ready_slot_direct_xrefs": ready["summary"]["total_direct_xrefs"],
            "ready_slot_guarded_dispatches": ready["summary"][
                "guarded_dispatches"],
            "mmio_pointer_cells": 4,
            "mmio_target_stores": len(mmio["teardown_target_stores"]),
            "unclassified_ready_slot_xrefs": 0,
            "unresolved_game_owned_teardown_interfaces": 0,
            "unresolved_cross_boundary_interfaces": 5,
        },
        "claims": {
            "confirmed": [
                "The guest teardown has a conventional balanced return to 0x800B74AC.",
                "The default ready callback is a resident pointer slot with every direct read, write, initialization clear and guarded dispatch classified.",
                "The default data callback is cleared through the PsyQ DMACallback channel-3 API; kernel-private storage remains behind the SDK boundary.",
                "Mode 1 uses the FMV.BIN channel-3 wrapper and resident overlay slot 0x800CAECC.",
                "The retained four words are CD-ROM MMIO pointer cells; teardown writes zero to register targets 0 and 3 through two of those cells.",
            ],
            "not_claimed": [
                "The retained functionTrace synthetic-unwind flag is not rewritten or explained as an exact every-cycle event.",
                "Static ownership does not establish pause, repeat, decode-failure or malformed-media outcomes.",
                "Kernel-private DMACallback storage is not promoted to safe game-owned MOD state.",
                "The mode-field direct-read census does not prove which indirect writers make mode 1 reachable at runtime.",
            ],
        },
        "dimension_boundary": {
            "dimension": "original_interfaces",
            "claim": "partial",
            "confidence": "partial",
            "low_level_basis": (
                "Pristine opcodes bind both callback backends, the complete "
                "resident ready-slot xref/dispatch census, the default data SDK "
                "boundary, both MMIO target stores, the pointer-table identity, "
                "and the conventional guest return. This closes the teardown "
                "sub-boundary only; it does not bind every original interface "
                "crossed by the E15 subsystem."
            ),
            "non_intersecting_residuals": [
                "Pause, repeat and error outcomes remain lifecycle and campaign-breadth debt.",
                "Kernel-private DMACallback storage remains outside game-owned MOD state.",
                "Exact functionTrace stack-unwind causality remains observer evidence, not a guest interface.",
            ],
            "intersecting_residuals": [
                "Remaining level/viewer completion and transition writers.",
                "E12 audio-presentation interface.",
                "C17 movie-viewer selection and unlock interface.",
                "E14 frontend persistence interface.",
                "E16 generic overlay/resource-loader interface.",
            ],
        },
        "evidence_dependencies": {
            "analysis/phase4_fmv_callback_lifecycle.json": _sha256(
                LIFECYCLE_PATH),
            "analysis/phase3_jalr_callbacks.json": _sha256(PHASE3_CALLBACKS),
        },
        "source_dependencies": {
            "config/phase4_fmv.yaml": _sha256(
                ROOT / "config/phase4_fmv.yaml"),
            "src/main/800709ac_sub_800709ac.c": _sha256(
                ROOT / "src/main/800709ac_sub_800709ac.c"),
            "src_re/fmv_callback_consumer_frontier.c": _sha256(
                ROOT / "src_re/fmv_callback_consumer_frontier.c"),
            "tools/phase4_fmv_teardown_ownership.py": _sha256(Path(__file__)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    rendered = json.dumps(document, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(rendered)
    if args.check or not args.write:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("phase4 FMV teardown-ownership artifact is stale")
    print(
        "[phase4-fmv-teardown] balanced return; 8 ready-slot xrefs; "
        "2 MMIO target stores; 0 unresolved game-owned interfaces")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
