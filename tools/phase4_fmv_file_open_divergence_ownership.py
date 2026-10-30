#!/usr/bin/env python3
"""Reclassify and statically bound the falsified E15 control's endpoint."""
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
OUTPUT = ROOT / "analysis/phase4_fmv_file_open_divergence_ownership.json"
CONFIG = ROOT / "config/phase4_fmv_file_open_divergence_ownership.yaml"
FMV_REL = "FMV/FMV.BIN"
FMV_PATH = ROOT / "REBUILD/files" / FMV_REL
FMV_BASE = 0x800B5788

EXPECTED_WORDS = {
    0x800B6678: 0x8442AC08,  # read presentation width
    0x800B6680: 0x8463AC0A,  # read presentation height
    0x800B6878: 0x2610AC04,  # materialize presentation RECT
    0x800B6884: 0x0C018A30,  # LoadImage(&present_rect, block)
    0x800B6988: 0x8442AC08,  # read presentation width
    0x800B69DC: 0x8463AC0A,  # read presentation height
    0x800B6DC0: 0xA4321EEE,  # actual selected-frame-limit writer
    0x800B6EBC: 0x84A51EEC,  # load signed display mode
    0x800B6EC0: 0x241000F0,  # presentation height = 240
    0x800B6F18: 0xA430AC0A,  # store presentation height
    0x800B6F1C: 0x00051080,  # display_mode * 4
    0x800B6F20: 0x00451021,  # display_mode * 5
    0x800B6F24: 0x00021140,  # display_mode * 160
    0x800B6F28: 0x000528C0,  # display_mode * 8
    0x800B6F40: 0xA425AC08,  # store presentation width
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact(spec: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = ROOT / spec["path"]
    _require(path.is_file(), f"missing input artifact: {path}")
    _require(common.sha256(path) == spec["sha256"],
             f"input artifact drifted: {path}")
    return path, common.load_json(path)


def _source(spec: dict[str, Any]) -> Path:
    path = ROOT / spec["path"]
    _require(path.is_file(), f"missing source: {path}")
    _require(common.sha256(path) == spec["sha256"],
             f"source drifted: {path}")
    return path


def _word(data: bytes, pc: int) -> int:
    offset = pc - FMV_BASE
    _require(0 <= offset <= len(data) - 4,
             f"FMV instruction is out of range: 0x{pc:08X}")
    return struct.unpack_from("<I", data, offset)[0]


def _instruction(data: bytes, pc: int) -> dict[str, str]:
    word = _word(data, pc)
    return {
        "pc": f"0x{pc:08X}",
        "word": f"0x{word:08X}",
        "mnemonic": exe_read.disasm_one(pc, word),
    }


def _field(owners: dict[str, Any], name: str) -> dict[str, Any]:
    rows = [
        row for row in owners["player_typed_state"]["fields"]
        if row["name"] == name
    ]
    _require(len(rows) == 1, f"typed field is not unique: {name}")
    return rows[0]


def _capture(job: dict[str, Any], label: str) -> dict[str, Any]:
    rows = [
        row for row in job["result"]["capture"]["memory"]
        if row["label"] == label
    ]
    _require(len(rows) == 1, f"capture label is not unique: {label}")
    row = rows[0]
    _require(row["valid_bytes"] == row["length"],
             f"capture is incomplete: {label}")
    return row


def _decode_rect(hex_le: str) -> dict[str, int]:
    raw = bytes.fromhex(hex_le)
    _require(len(raw) == 4, "presentation RECT capture is not four bytes")
    width, height = struct.unpack("<hh", raw)
    return {"width": width, "height": height}


def _run_artifact(run_root: Path, relative_path: str, expected_sha256: str,
                  label: str) -> tuple[Path, dict[str, Any]]:
    path = run_root / relative_path
    _require(path.is_file(), f"{label} is missing")
    _require(common.sha256(path) == expected_sha256,
             f"{label} identity drifted")
    return path, common.load_json(path)


def build(*, fmv_data: bytes | None = None,
          verify_identity: bool = True) -> dict[str, Any]:
    config = common.load_yaml(CONFIG)
    _require(
        config.get("schema")
        == "abl-phase4-fmv-file-open-divergence-ownership-source/1"
        and config.get("campaign_id") == "fmv_playback"
        and config.get("row_id") == "E15_fmv"
        and config.get("dimension") == "lifecycle"
        and config.get("lane") == "static"
        and config.get("next_lane") == "live"
        and config.get("dimension_promoted") is False,
        "divergence-ownership source boundary drifted",
    )
    fmv = FMV_PATH.read_bytes() if fmv_data is None else fmv_data
    if verify_identity:
        verify_staged_input(FMV_REL, fmv)
    instructions = []
    for pc, expected in EXPECTED_WORDS.items():
        actual = _word(fmv, pc)
        _require(
            actual == expected,
            f"FMV divergence owner opcode drifted at 0x{pc:08X}: "
            f"expected 0x{expected:08X}, observed 0x{actual:08X}",
        )
        instructions.append(_instruction(fmv, pc))

    result_path, retained = _artifact(config["retained_result"])
    owners_path, owners = _artifact(config["static_owners"])
    schema_path = _source(config["typed_schema"])
    semantic_path = _source(config["semantic_source"])
    load_image_path = _source(config["load_image_source"])
    _require(retained["falsifier"]["outcome"] == "falsified",
             "retained diagnostic-route falsifier drifted")
    _require(
        owners["player_typed_state"]["summary"]["unclassified_xrefs"] == 0,
             "typed-state xref census is not closed")

    width = _field(owners, "present_rect_w")
    height = _field(owners, "present_rect_h")
    limit = _field(owners, "selected_frame_limit")
    _require(
        width["address"] == "0x800CAC08"
        and [row["instruction"]["pc"] for row in width["xrefs"]]
        == ["0x800B6678", "0x800B6988", "0x800B6F40"]
        and height["address"] == "0x800CAC0A"
        and [row["instruction"]["pc"] for row in height["xrefs"]]
        == ["0x800B6680", "0x800B69DC", "0x800B6F18"]
        and limit["address"] == "0x80131EEE"
        and [row["instruction"]["pc"] for row in limit["xrefs"]]
        == ["0x800B6B2C", "0x800B6DC0"],
        "typed width/height/selected-limit xref ownership drifted",
    )
    schema = common.load_yaml(schema_path)
    typed = schema["typed_state"]
    _require(
        typed["selected_frame_limit"]["address"] == 0x80131EEE
        and typed["player_boundary"]["structures"]["present_rect"]
        == {
            "base": 0x800CAC04,
            "size": 8,
            "fields": ["s16_x", "s16_y", "s16_w", "s16_h"],
        },
        "authoritative FMV typed schema drifted",
    )

    batch_spec = config["precise_batch_result"]
    run_root = Path(config["run_root"]).resolve()
    batch_path, batch = _run_artifact(
        run_root, batch_spec["relative_path"], batch_spec["sha256"],
        "precise batch result",
    )
    _require(batch_path.stat().st_size == batch_spec["bytes"],
             "precise batch result size drifted")
    jobs = batch["result"]["jobs"]
    _require(
        [row["id"] for row in jobs]
        == [
            "file_open_failure_forced_positive",
            "file_open_failure_native_negative",
        ],
        "precise job order drifted",
    )
    capture_spec = config["historical_capture"]
    captures = [
        _capture(row, capture_spec["label"]) for row in jobs
    ]
    _require(
        all(
            row["address"].lower()
            == f"0x{capture_spec['address']:08x}"
            and row["length"] == capture_spec["length"]
            for row in captures
        ),
        "historical capture address/length drifted",
    )
    positive_hex = captures[0]["hex"]
    native_hex = captures[1]["hex"]
    _require(
        positive_hex == capture_spec["positive_hex_le"]
        and native_hex == capture_spec["native_hex_le"],
        "historical endpoint bytes drifted",
    )
    positive_rect = _decode_rect(positive_hex)
    native_rect = _decode_rect(native_hex)
    _require(
        positive_rect == {"width": 24, "height": 240}
        and native_rect == {"width": 24, "height": 128},
        "historical endpoint no longer decodes as the presentation RECT",
    )
    endpoints = [
        {
            "job_id": row["id"],
            "frame": row["result"]["capture"]["frame"],
            "cycle": row["result"]["capture"]["cycle"],
            "pc": row["result"]["capture"]["cpu"]["registers"][
                "registers_hex"
            ]["pc"],
            "movie_reproducible": row["result"]["capture"]["movie"][
                "reproducible"
            ],
        }
        for row in jobs
    ]
    _require(
        endpoints[0]["frame"] == endpoints[1]["frame"] == 4475
        and endpoints[0]["cycle"] == endpoints[1]["cycle"] == 2533180622
        and endpoints[0]["pc"] == "0x80070cac"
        and endpoints[1]["pc"] == "0x800b97b8",
        "historical endpoint phase boundary drifted",
    )

    offline_spec = config["offline_index_query"]
    receipt_path, receipt = _run_artifact(
        run_root,
        offline_spec["receipt_relative_path"],
        offline_spec["receipt_sha256"],
        "offline index query receipt",
    )
    output_path, offline = _run_artifact(
        run_root,
        offline_spec["output_relative_path"],
        offline_spec["output_sha256"],
        "offline index query output",
    )
    _require(
        receipt["schema"] == "abl-phase4-offline-query/1"
        and receipt["complete"] is True
        and receipt["errors"] == []
        and receipt["execution"]["exit_code"] == 0
        and receipt["outputs"] == [{
            "path": offline_spec["output_relative_path"],
            "scope": "run",
            "sha256": offline_spec["output_sha256"],
        }]
        and receipt["external_inputs"][0]["sha256"]
        == offline_spec["external_index_sha256"],
        "offline index query receipt is not closed or joined",
    )
    _require(
        offline["schema"] == "abl-phase4-offline-json-search-result/1"
        and offline["source"]["sha256"]
        == offline_spec["external_index_sha256"]
        and all(
            offline["terms"][term]
            == {"count": 0, "paths": [], "paths_truncated": False}
            for term in offline_spec["absent_terms"]
        ),
        "derived index unexpectedly answers the exact RECT ownership question",
    )

    return {
        "_comment": (
            "Generated from hash-verified pristine FMV.BIN, the exhaustive "
            "typed-state census and the closed live result. The retained "
            "memory-dump label is provenance only; 0x800CAC08 is not the "
            "selected-frame-limit field."
        ),
        "schema": "abl-phase4-fmv-file-open-divergence-ownership/1",
        "campaign": "fmv_playback",
        "row": "E15_fmv",
        "dimension_boundary": {
            "dimension": "lifecycle",
            "claim": "partial",
            "dimension_promoted": False,
            "closed_sub_boundary":
                config["claim_boundary"]["closed_sub_boundary"],
            "next_lane": "live",
            "next_missing_fact_id": config["next_missing_fact_id"],
        },
        "inputs": {
            "fmv_bin": {
                "path": f"REBUILD/files/{FMV_REL}",
                "sha256": _sha256_bytes(fmv),
                "identity_verified": verify_identity,
            },
            "config": {
                "path": CONFIG.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(CONFIG),
            },
            "retained_result": {
                "path": result_path.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(result_path),
            },
            "static_owners": {
                "path": owners_path.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(owners_path),
            },
            "typed_schema": {
                "path": schema_path.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(schema_path),
            },
            "semantic_source": {
                "path": semantic_path.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(semantic_path),
                "status": "documentation_grade_semantic_c",
            },
            "load_image_source": {
                "path": load_image_path.relative_to(ROOT).as_posix(),
                "sha256": common.sha256(load_image_path),
                "status": "matching_c",
            },
            "precise_batch_result": batch_spec,
            "offline_index_query": {
                "receipt": {
                    "relative_path": receipt_path.relative_to(
                        run_root
                    ).as_posix(),
                    "sha256": common.sha256(receipt_path),
                },
                "output": {
                    "relative_path": output_path.relative_to(
                        run_root
                    ).as_posix(),
                    "sha256": common.sha256(output_path),
                },
                "external_index_sha256":
                    offline_spec["external_index_sha256"],
                "exact_terms_found": 0,
                "exact_address_or_owner_named": False,
            },
        },
        "retained_capture": {
            "historical_label": capture_spec["label"],
            "historical_label_is_semantic": False,
            "address": "0x800CAC08",
            "length": 4,
            "positive": {
                "hex_le": positive_hex,
                "decoded": positive_rect,
            },
            "native_negative": {
                "hex_le": native_hex,
                "decoded": native_rect,
            },
            "unchanged_width": 24,
            "divergent_field": "present_rect_h",
            "selected_frame_limit_difference_claimed": False,
            "endpoint_phase": endpoints,
        },
        "typed_reclassification": {
            "captured_range": {
                "start": "0x800CAC08",
                "end": "0x800CAC0C",
                "fields": [
                    {"name": "present_rect_w", "address": "0x800CAC08",
                     "type": "s16"},
                    {"name": "present_rect_h", "address": "0x800CAC0A",
                     "type": "s16"},
                ],
            },
            "actual_selected_frame_limit": {
                "address": "0x80131EEE",
                "type": "s16",
                "captured_by_retained_control": False,
                "writer": "0x800B6DC0",
            },
            "static_initializer": {
                "height_constant": 240,
                "height_store": "0x800B6F18",
                "width_expression": "signed_display_mode * 8",
                "width_store": "0x800B6F40",
                "display_mode_3_width": 24,
            },
            "direct_xrefs": {
                "present_rect_w": width["xrefs"],
                "present_rect_h": height["xrefs"],
                "selected_frame_limit": limit["xrefs"],
            },
        },
        "runtime_writer_frontier": {
            "classified_direct_height_writers": ["0x800B6F18"],
            "classified_direct_height_writer_value": 240,
            "present_rect_pointer_escape": {
                "materialization": "0x800B6878",
                "call": "0x800B6884",
                "callee": "0x800628C0",
                "callee_name": "LoadImage",
                "matching_wrapper_writes_rect": False,
                "downstream_gpu_driver_write_effect_statically_closed": False,
            },
            "native_height_128_writer_attributed": False,
            "positive_height_240_equals_static_initializer": True,
            "static_exhaustion_result":
                "endpoint_semantics_closed_runtime_writer_open",
            "offline_index_result":
                "exact_field_address_and_owner_absent",
            "missing_domain":
                "instruction_or_DMA_attributed writes to 0x800CAC0A in the "
                "bounded post-initialization window",
        },
        "falsifier": {
            "claim": (
                "Static reconstruction must both reclassify the four bytes "
                "and identify the exact owner of the native height-128 value."
            ),
            "outcome": "falsified",
            "survived": {
                "capture_address_and_length": True,
                "little_endian_rect_decode": True,
                "typed_state_and_xref_reclassification": True,
                "only_retained_code_perturbation": "0x800B6DE8",
            },
            "failed": {
                "exact_native_height_writer_attributed": False,
                "reason":
                    "the only direct pristine height writer stores 240; the "
                    "retained equal-frame/equal-cycle endpoints stop at "
                    "different PCs and no instruction/DMA writer evidence "
                    "was captured",
            },
        },
        "claim_boundary": {
            "endpoint_semantics_closed": True,
            "runtime_writer_closed": False,
            "selected_frame_limit_interpretation_superseded": True,
            "dimension_promoted": False,
            "not_claimed": config["claim_boundary"]["not_claimed"],
        },
        "exact_instructions": instructions,
        "summary": {
            "captured_fields_reclassified": 2,
            "selected_frame_limit_fields_captured": 0,
            "classified_direct_height_writers": 1,
            "unattributed_runtime_height_values": 1,
            "promoted_dimensions": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = build()
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(payload)
    if args.check:
        _require(OUTPUT.is_file(), f"missing generated artifact: {OUTPUT}")
        _require(OUTPUT.read_text() == payload,
                 "generated divergence-ownership artifact is stale")
    if not args.write and not args.check:
        print(payload, end="")
    print(
        "phase4 FMV file-open divergence ownership: PASS "
        "(RECT endpoint reclassified; runtime height writer remains open)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
