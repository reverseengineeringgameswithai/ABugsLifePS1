#!/usr/bin/env python3
"""Bank E15's corrected shared frame-sync wait ownership."""
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
CONFIG_PATH = ROOT / "config/phase4_fmv_frame_sync_wait_ownership.yaml"
FMV_SCHEMA_PATH = ROOT / "config/phase4_fmv.yaml"
OUTPUT = ROOT / "analysis/phase4_fmv_frame_sync_wait_ownership.json"
SEMANTIC_SOURCE = ROOT / "src_re/fmv_levelb_pre15792_partition.c"
CONFIG = common.load_yaml(CONFIG_PATH)

EXE_REL = "SCUS_942.88"
EXE_PATH = ROOT / "REBUILD/files" / EXE_REL
EXE_BASE = 0x80010000
EXE_HEADER = 0x800
FRAME_SYNC_WAIT_LATCH = 0x80082250
FRAME_PRESENT = 0x80039A70
SHARED_HELPER = (0x8003F2F0, 0x8003F358)
SCENE_PROTOCOL = (0x8004FE98, 0x8004FEB8)

EXPECTED_SLICE_SHA256 = {
    (0x800185B8, 0x800186EC):
        "1d5568cdc829a6d376d24eb5391b80b316eececbf1c0bbbbe4b91669fa33958e",
    (0x800186F0, 0x8001881C):
        "c1694aaed73dc74d35431911d884f182085fbc8517855859ffc0def93f2b5e71",
    SHARED_HELPER:
        "95cf01e80726c2e0c8c75452790ca81231ce668dcc5f8c539674b7d334d61b4c",
    SCENE_PROTOCOL:
        "79ed7b64565b01a1e9b60eb7acc97ee8dd0717ac3c0a1af842c92d32144c80e5",
}
EXPECTED_XREFS = {
    0x80018638: ("read", "context_save_handler_primary"),
    0x8001864C: ("clear", "context_save_handler_primary"),
    0x80018770: ("read", "context_save_handler_secondary"),
    0x80018784: ("clear", "context_save_handler_secondary"),
    0x8003E848: ("clear", "pad_subsystem_start"),
    0x8003E8D8: ("clear", "pad_subsystem_stop"),
    0x8003F330: ("set_wait", "wait_for_frame_sync_flag"),
    0x8003F338: ("read_wait", "wait_for_frame_sync_flag"),
    0x8004FEA0: ("set_wait", "scene_flow_dispatcher_inline_wait"),
    0x8004FEA8: ("read_wait", "scene_flow_dispatcher_inline_wait"),
}
EXPECTED_HELPER_CALLS = {
    0x80052338: "level_transition_orchestrator",
    0x8005235C: "level_transition_orchestrator",
    0x8005B490: "transition_fade_draw_loop",
    0x8005B644: "animated_overlay_display_loop",
    0x8005B7F8: "gameplay_state_reset_cursor_seed_entry",
}
SOURCE_PATHS = (
    "asm/hand_written/800186f0_context_save_callback.s",
    "asm/hand_written/8003f2f0_sub_8003f2f0.s",
    "asm/hand_written/8004fca0_scene_flow_dispatcher.s",
    "asm/hand_written/8005222c_level_transition_orchestrator.s",
    "asm/hand_written/8005b440_sub_8005b440.s",
    "asm/hand_written/8005b4e4_sub_8005b4e4.s",
    "asm/hand_written/8005b4ec_sub_8005b4ec.s",
    "asm/hand_written/8005b70c_sub_8005b70c.s",
    "asm/hand_written/8005b714_gameplay_state_reset_cursor_seed.s",
    "src/main/8003e83c_vsync_wait_glue.c",
    "src/main/8003e8c4_vsync_wait_glue_e8c4.c",
    "src_re/fmv_levelb_pre15792_partition.c",
    "symbols/re_symbols.sym",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return common.sha256(path)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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


def _slice_identities(data: bytes) -> list[dict[str, Any]]:
    rows = []
    for (start, end), expected in EXPECTED_SLICE_SHA256.items():
        actual = _sha256_bytes(_slice(data, start, end))
        _require(actual == expected, "frame-sync owner slice identity drifted")
        rows.append({
            "start": f"0x{start:08X}",
            "end": f"0x{end:08X}",
            "bytes": end - start,
            "sha256": actual,
        })
    return rows


def _direct_xrefs(data: bytes) -> list[dict[str, Any]]:
    lower = FRAME_SYNC_WAIT_LATCH & 0xFFFF
    upper = ((FRAME_SYNC_WAIT_LATCH + 0x8000) >> 16) & 0xFFFF
    memory_ops = {
        0x20: "read", 0x21: "read", 0x23: "read",
        0x24: "read", 0x25: "read",
        0x28: "write", 0x29: "write", 0x2B: "write",
    }
    found = []
    end = EXE_BASE + len(data) - EXE_HEADER
    for pc in range(EXE_BASE + 4, end, 4):
        word = _word(data, pc)
        opcode = word >> 26
        if opcode not in memory_ops or word & 0xFFFF != lower:
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
        found == list(EXPECTED_XREFS),
        "frame-sync wait direct xref census drifted",
    )
    rows = []
    for pc in found:
        role, owner = EXPECTED_XREFS[pc]
        access = memory_ops[_word(data, pc) >> 26]
        rows.append({
            "pc": f"0x{pc:08X}",
            "access": access,
            "role": role,
            "owner": owner,
            "address": "0x80082250",
            "materialization": _instruction(data, pc - 4),
            "instruction": _instruction(data, pc),
        })
    return rows


def _helper_callers(data: bytes) -> list[dict[str, Any]]:
    found = []
    end = EXE_BASE + len(data) - EXE_HEADER
    for pc in range(EXE_BASE, end, 4):
        if _jal_target(pc, _word(data, pc)) == SHARED_HELPER[0]:
            found.append(pc)
    _require(
        found == list(EXPECTED_HELPER_CALLS),
        "shared frame-sync helper caller census drifted",
    )
    return [{
        "pc": f"0x{pc:08X}",
        "owner": EXPECTED_HELPER_CALLS[pc],
        "instruction": _instruction(data, pc),
    } for pc in found]


def _protocols(data: bytes) -> dict[str, Any]:
    shared_pcs = list(range(0x8003F328, 0x8003F348, 4))
    scene_pcs = list(range(*SCENE_PROTOCOL, 4))
    expected = [
        0x24030001,
        0x3C018008,
        0xAC232250,
        0x3C028008,
        0x8C422250,
        0x00000000,
        0x1043FFFC,
        0x00000000,
    ]
    _require(
        [_word(data, pc) for pc in shared_pcs] == expected,
        "shared frame-sync wait protocol drifted",
    )
    _require(
        [_word(data, pc) for pc in scene_pcs] == expected,
        "scene-flow inline frame-sync wait protocol drifted",
    )
    for read_pc, clear_pc, call_pc in (
        (0x80018638, 0x8001864C, 0x80018650),
        (0x80018770, 0x80018784, 0x80018788),
    ):
        _require(
            _word(data, clear_pc) == 0xAC202250
            and _jal_target(call_pc, _word(data, call_pc)) == FRAME_PRESENT,
            "context handler clear/frame_present protocol drifted",
        )
        _require(
            _word(data, read_pc) in {0x8D082250},
            "context handler frame-sync read drifted",
        )
    _require(
        _word(data, 0x8003E848) == 0xAC202250
        and _word(data, 0x8003E8D8) == 0xAC202250,
        "pad start/stop frame-sync clear drifted",
    )
    return {
        "shared_helper": {
            "range": ["0x8003F2F0", "0x8003F358"],
            "set_wait_pc": "0x8003F330",
            "read_wait_pc": "0x8003F338",
            "loop_branch_pc": "0x8003F340",
            "instructions": [_instruction(data, pc) for pc in shared_pcs],
        },
        "scene_flow_inline": {
            "range": ["0x8004FE98", "0x8004FEB8"],
            "set_wait_pc": "0x8004FEA0",
            "control_pc": "0x8004FEA4",
            "read_wait_pc": "0x8004FEA8",
            "loop_branch_pc": "0x8004FEB0",
            "instructions": [_instruction(data, pc) for pc in scene_pcs],
        },
        "interrupt_clearers": [
            {
                "range": ["0x800185B8", "0x800186EC"],
                "read_pc": "0x80018638",
                "clear_pc": "0x8001864C",
                "frame_present_call": "0x80018650",
            },
            {
                "range": ["0x800186F0", "0x8001881C"],
                "read_pc": "0x80018770",
                "clear_pc": "0x80018784",
                "frame_present_call": "0x80018788",
            },
        ],
        "pad_lifecycle_clearers": [
            {"pc": "0x8003E848", "owner": "pad_subsystem_start"},
            {"pc": "0x8003E8D8", "owner": "pad_subsystem_stop"},
        ],
    }


def _work_packet() -> tuple[dict[str, Any], dict[str, str]]:
    spec = CONFIG["work_packet"]
    path = Path(spec["absolute_path"]).resolve()
    _require(
        path.is_file() and _sha256(path) == spec["sha256"],
        "retained work packet identity drifted",
    )
    packet = common.load_json(path)
    _require(
        packet.get("schema") == "abl-phase4-work-packet/1"
        and packet.get("campaign_id") == CONFIG["campaign_id"]
        and packet.get("row_ids") == [CONFIG["row_id"]]
        and packet.get("first_unmet_dimension") == CONFIG["dimension"]
        and packet.get("next_lane") == CONFIG["lane"]
        and "0x80082250" in packet.get("exact_claim", "")
        and "shared frame-sync" in packet.get("exact_claim", ""),
        "retained work packet semantic boundary drifted",
    )
    return packet, {
        "run:iteration-1-receipts/work-packet.json": spec["sha256"],
    }


def _prior_evidence() -> tuple[dict[str, Any], dict[str, str]]:
    documents = {}
    hashes = {}
    for name, spec in CONFIG["prior_evidence"].items():
        path = ROOT / spec["path"]
        _require(
            path.is_file() and _sha256(path) == spec["sha256"],
            f"prior evidence identity drifted: {name}",
        )
        documents[name] = common.load_json(path)
        hashes[spec["path"]] = spec["sha256"]
    boundary = documents["pre15792_partition"]["offline_localization"][
        "staged_current_toolchain_boundary"
    ]
    _require(
        boundary.get("frame") == 15720
        and boundary.get("cycle") == 8900142073
        and boundary.get("pc") == "0x8004FEA4"
        and boundary.get("paired_equal") is True
        and boundary.get("payload_retained") is False,
        "retained frame-15720 boundary drifted",
    )
    _require(
        documents["transition_relocalization"]["claim_boundary"].get(
            "dimension_promoted"
        ) is False,
        "prior transition boundary was rewritten as a promotion",
    )
    return documents, hashes


def _machine_sources() -> dict[str, str]:
    source = SEMANTIC_SOURCE.read_text()
    _require(
        all(fragment in source for fragment in (
            "FRAME_SYNC_WAIT_LATCH",
            "Shared frame-sync interrupt handshake",
            "not FMV-running state",
            "does not bracket FMV retirement",
            "0x8004FEA4",
        )),
        "semantic C frame-sync ownership drifted",
    )
    schema = common.load_yaml(FMV_SCHEMA_PATH)
    typed = schema.get("typed_state") or {}
    field = typed.get("frame_sync_wait_latch") or {}
    _require(
        "fmv_running_latch" not in typed
        and field.get("address") == FRAME_SYNC_WAIT_LATCH
        and field.get("width") == "u32"
        and field.get("owner") == "shared_frame_sync_interrupt_handshake"
        and field.get("legacy_capture_alias") == "fmv_running_latch"
        and field.get("evidence")
        == "analysis/phase4_fmv_frame_sync_wait_ownership.json",
        "authoritative FMV typed-state correction drifted",
    )
    sources = {
        "config/phase4_fmv.yaml": _sha256(FMV_SCHEMA_PATH),
        **{path: _sha256(ROOT / path) for path in SOURCE_PATHS},
    }
    handler = (ROOT / SOURCE_PATHS[0]).read_text()
    _require(
        "clear it and call the" in handler
        and "0x80039a70" in handler
        and "census name" in handler
        and "mislabel" in handler,
        "context-save handler ownership source drifted",
    )
    for path in SOURCE_PATHS:
        _require((ROOT / path).is_file(), f"missing semantic source: {path}")
    return sources


def build(
    *, exe_data: bytes | None = None, verify_identity: bool = True
) -> dict[str, Any]:
    exe = EXE_PATH.read_bytes() if exe_data is None else exe_data
    if verify_identity:
        verify_staged_input(EXE_REL, exe)
    packet, external_hashes = _work_packet()
    prior, prior_hashes = _prior_evidence()
    xrefs = _direct_xrefs(exe)
    callers = _helper_callers(exe)
    protocols = _protocols(exe)
    source_hashes = _machine_sources()
    field = CONFIG["expected"]["field"]
    checks = {
        "work_packet_exact": True,
        "pristine_resident_identity_exact": True,
        "retained_frame_15720_boundary_preserved": True,
        "direct_xref_census_complete": True,
        "direct_xrefs_unclassified_zero": True,
        "interrupt_clearers_complete": True,
        "pad_lifecycle_clearers_complete": True,
        "shared_helper_protocol_exact": True,
        "scene_flow_inline_protocol_exact": True,
        "shared_helper_caller_census_complete": True,
        "fmv_specific_lifetime_rejected": True,
        "legacy_capture_alias_bounded": True,
        "machine_sources_hash_pinned": True,
        "prior_no_promotion_preserved": True,
        "new_live_escalation_absent": True,
        "dimension_promotion_absent": True,
    }
    return {
        "schema": "abl-phase4-fmv-frame-sync-wait-ownership/1",
        "generated": _stable_generated(),
        "_comment": (
            "Generated from hash-verified pristine resident bytes, tracked "
            "ASM/C/schema sources and retained hash-only runtime provenance. "
            "No captured or copyrighted payload is retained."
        ),
        "campaign": CONFIG["campaign_id"],
        "row": CONFIG["row_id"],
        "dimension": CONFIG["dimension"],
        "work_packet": {
            "sha256": CONFIG["work_packet"]["sha256"],
            "exact_claim": packet["exact_claim"],
            "explicit_falsifier": packet["explicit_falsifier"],
        },
        "typed_state": {
            "canonical_name": "frame_sync_wait_latch",
            **field,
            "address": "0x80082250",
            "direct_xref_contract":
                "compiler_standard_adjacent_lui_direct_load_store",
            "direct_xrefs": xrefs,
            "direct_xref_count": len(xrefs),
            "direct_read_count": sum(row["access"] == "read" for row in xrefs),
            "direct_write_count":
                sum(row["access"] == "write" for row in xrefs),
            "unclassified_direct_xrefs": 0,
            "alias_boundary": (
                "Historical retained live documents keep the "
                "fmv_running_latch capture label for hash-stable provenance. "
                "It is not an authoritative owner or lifetime claim."
            ),
        },
        "pristine_static_ownership": {
            "slice_identities": _slice_identities(exe),
            "protocols": protocols,
            "shared_helper_callers": callers,
            "shared_helper_call_count": len(callers),
            "unclassified_helper_callers": 0,
            "owner_classes": [
                "context_save_interrupt",
                "pad_subsystem_lifecycle",
                "level_transition",
                "display_loop",
                "gameplay_reset",
                "scene_flow_inline_wait",
            ],
            "fmv_exclusive": False,
        },
        "retained_boundary": {
            "frame": 15720,
            "cycle": 8900142073,
            "pc": "0x8004FEA4",
            "paired_equal": True,
            "payload_retained": False,
            "observation": (
                "Both retained pristine jobs are paused at the inline "
                "frame-sync wait control position."
            ),
            "corrected_inference": (
                "The PC and latch value do not locate either scene-setup call "
                "and do not establish whether FMV retirement is before or "
                "after this frame boundary."
            ),
            "natural_branch_selected": False,
            "exact_retirement_frame": None,
        },
        "evidence_boundary": {
            "observation": (
                "The retained paired frame-15720 PC is 0x8004FEA4."
            ),
            "static_confirmation": CONFIG["claim"]["exact"],
            "inference": (
                "A future earlier-boundary experiment must use a distinct "
                "state producer or exact instruction predicate; the shared "
                "frame-sync latch is not an FMV lifecycle discriminator."
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
            "config/phase4_fmv_frame_sync_wait_ownership.yaml":
                _sha256(CONFIG_PATH),
            **prior_hashes,
            **source_hashes,
        },
        "external_dependencies": external_hashes,
        "summary": {
            "direct_xrefs": len(xrefs),
            "direct_reads": sum(row["access"] == "read" for row in xrefs),
            "direct_writes": sum(row["access"] == "write" for row in xrefs),
            "shared_helper_callers": len(callers),
            "owner_classes": 6,
            "unclassified_direct_xrefs": 0,
            "unclassified_helper_callers": 0,
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
        "PASS: E15 0x80082250 shared frame-sync ownership corrected "
        "(10 xrefs, 5 helper calls, no lifecycle promotion)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
