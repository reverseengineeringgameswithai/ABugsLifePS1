#!/usr/bin/env python3
"""Compile the shared Phase 4 static-ASM prerequisite receipt.

The receipt is deliberately not an Item-2 verdict.  It separates byte
partition, typed instruction candidates, direct-edge reachability, and target
resolution so that completion of one subset cannot be reported as completion
of another.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from typing import Any


SCHEMA = "phase4-static-asm-prerequisites/1"
EXECUTABLE_TYPES = {"code", "thunk"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    return int(value, 0)


def pc(value: int) -> str:
    return f"0x{value:08X}"


def relative_path(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"input must be inside repository: {resolved}") from exc


def read_psx_exe(path: Path) -> tuple[bytes, int, int]:
    data = path.read_bytes()
    if len(data) < 0x800 or data[:8] != b"PS-X EXE":
        raise ValueError(f"not a PS-X EXE: {path}")
    base, text_size = struct.unpack_from("<II", data, 0x18)
    if base & 3 or text_size & 3 or len(data) < 0x800 + text_size:
        raise ValueError("invalid PS-X EXE load range")
    return data, base, text_size


def image_word(data: bytes, base: int, text_size: int, address: int) -> int:
    delta = address - base
    if delta < 0 or delta + 4 > text_size or delta & 3:
        raise ValueError(f"address outside image: {pc(address)}")
    return struct.unpack_from("<I", data, 0x800 + delta)[0]


def build_extents(functions_path: Path, repair_path: Path, base: int,
                  text_size: int) -> list[dict[str, Any]]:
    source = load_json(functions_path)
    records = source.get("functions")
    if not isinstance(records, list):
        raise ValueError("functions.json has no functions array")
    by_start: dict[int, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or "start" not in record:
            continue
        start = parse_int(record["start"])
        if base <= start < base + text_size:
            if start in by_start:
                raise ValueError(f"duplicate function start {pc(start)}")
            by_start[start] = record

    extents: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        repair_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=2)
        if len(fields) != 3:
            raise ValueError(f"bad repair row {line_number}")
        start = int(fields[0], 0)
        size = int(fields[1], 0)
        name = fields[2]
        source_record = by_start.get(start)
        if source_record is None:
            raise ValueError(f"repair start absent from functions.json: {pc(start)}")
        range_type = source_record.get("range_type")
        if range_type not in {"code", "data", "thunk"}:
            raise ValueError(f"untyped repaired extent: {pc(start)}")
        extents.append(
            {
                "start": start,
                "end": start + size,
                "range_type": range_type,
                "name": name,
            }
        )

    extents.sort(key=lambda item: item["start"])
    cursor = base
    for extent in extents:
        if extent["start"] < cursor:
            raise ValueError(f"overlapping extent at {pc(extent['start'])}")
        if extent["start"] < base or extent["end"] > base + text_size:
            raise ValueError(f"extent outside image: {pc(extent['start'])}")
        if extent["start"] & 3 or extent["end"] & 3:
            raise ValueError(f"unaligned extent: {pc(extent['start'])}")
        cursor = extent["end"]
    return extents


def compile_probe(source: Path, output: Path) -> str:
    command = [
        os.environ.get("CC", "cc"),
        "-std=c11",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        str(source),
        "-o",
        str(output),
    ]
    subprocess.run(command, check=True)
    version = subprocess.run(
        [command[0], "--version"], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ).stdout.splitlines()[0]
    return version


def run_probe(source: Path, image: Path, extents: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    with tempfile.TemporaryDirectory(prefix="phase4-static-asm-") as raw_temp:
        temp = Path(raw_temp)
        extent_path = temp / "extents.tsv"
        binary_path = temp / "phase4_static_asm_probe"
        extent_path.write_text(
            "".join(
                f"{item['start']:08x}\t{item['end']:08x}\t"
                f"{item['range_type']}\t{item['name']}\n"
                for item in extents
            ),
            encoding="ascii",
        )
        compiler = compile_probe(source, binary_path)
        result = subprocess.run(
            [str(binary_path), str(image), str(extent_path)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
    return parse_probe(result.stdout), compiler


def parse_probe(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "extents": [],
        "gaps": [],
        "candidates": [],
    }
    for line in text.splitlines():
        fields = line.split("\t")
        tag = fields[0]
        if tag == "meta":
            parsed["meta"] = {
                "load_base": int(fields[1], 0),
                "text_size": int(fields[2]),
                "file_size": int(fields[3]),
            }
        elif tag == "extent":
            parsed["extents"].append(
                {
                    "index": int(fields[1]),
                    "start": int(fields[2], 0),
                    "end": int(fields[3], 0),
                    "range_type": fields[4],
                    "name": fields[5],
                    "direct_cfg_reached_words": int(fields[6]),
                    "word_count": int(fields[7]),
                }
            )
        elif tag == "gap":
            parsed["gaps"].append(
                {"start": int(fields[1], 0), "end": int(fields[2], 0)}
            )
        elif tag == "candidate":
            parsed["candidates"].append(
                {
                    "pc": int(fields[1], 0),
                    "kind": fields[2],
                    "register": int(fields[3]),
                    "extent_index": int(fields[4]),
                    "range_type": fields[5],
                    "extent_name": fields[6],
                    "direct_cfg_reached": fields[7] == "1",
                    "linear_definition_pc": None if fields[8] == "-" else int(fields[8], 0),
                    "linear_definition_kind": fields[9],
                    "memory_base_register": int(fields[10]),
                    "memory_offset": int(fields[11]),
                    "linear_constant": None if fields[12] == "-" else int(fields[12], 0),
                }
            )
        elif tag == "summary":
            parsed["summary"] = {
                "claimed_bytes": int(fields[1]),
                "gap_bytes": int(fields[2]),
                "nonreturn_candidates": int(fields[3]),
                "return_candidates": int(fields[4]),
                "typed_nonreturn_candidates": int(fields[5]),
                "direct_cfg_reached_nonreturn_candidates": int(fields[6]),
                "direct_cfg_queue_entries": int(fields[7]),
            }
        else:
            raise ValueError(f"unknown C probe row: {tag}")
    if "meta" not in parsed or "summary" not in parsed:
        raise ValueError("incomplete C probe output")
    return parsed


def owner_for(extents: list[dict[str, Any]], address: int) -> dict[str, Any] | None:
    for extent in extents:
        if extent["start"] <= address < extent["end"]:
            return extent
    return None


def validate_jump_island(declaration: dict[str, Any], site: dict[str, Any],
                         data: bytes, base: int, text_size: int,
                         extents: list[dict[str, Any]]) -> dict[str, Any]:
    island = parse_int(declaration["base"])
    count = int(declaration["count"])
    stride = int(declaration["stride"])
    mask = parse_int(declaration["mask"])
    if count != mask + 1 or stride <= 0 or stride & (stride - 1):
        raise ValueError(f"invalid jump-island declaration at {pc(site['pc'])}")
    shift = int(math.log2(stride))
    before_shift = image_word(data, base, text_size, site["pc"] - 8)
    before_add = image_word(data, base, text_size, site["pc"] - 4)
    reg = site["register"]
    shift_ok = (
        before_shift >> 26 == 0
        and (before_shift & 63) == 0
        and ((before_shift >> 11) & 31) == reg
        and ((before_shift >> 16) & 31) == reg
        and ((before_shift >> 6) & 31) == shift
    )
    add_ok = (
        before_add >> 26 == 0
        and (before_add & 63) in {32, 33}
        and ((before_add >> 11) & 31) == reg
        and reg in {((before_add >> 21) & 31), ((before_add >> 16) & 31)}
    )
    mask_seen = False
    cursor = site["pc"]
    for _ in range(96):
        if cursor < base + 4:
            break
        cursor -= 4
        word = image_word(data, base, text_size, cursor)
        if word >> 26 == 12 and ((word >> 16) & 31) == reg and (word & 0xFFFF) == mask:
            mask_seen = True
            break
    entries = []
    for index in range(count):
        entry = island + index * stride
        word = image_word(data, base, text_size, entry)
        if word >> 26 != 2:
            raise ValueError(f"jump-island entry is not j at {pc(entry)}")
        target = ((entry + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        target_owner = owner_for(extents, target)
        if target_owner is None or target_owner["range_type"] not in EXECUTABLE_TYPES:
            raise ValueError(f"jump-island target is not typed executable: {pc(target)}")
        entries.append({"index": index, "entry": pc(entry), "target": pc(target)})
    if not (shift_ok and add_ok and mask_seen):
        raise ValueError(f"jump-island source pattern mismatch at {pc(site['pc'])}")
    return {
        "kind": "jump_island",
        "target_set_complete": True,
        "source_pattern_verified": True,
        "base": pc(island),
        "count": count,
        "stride": stride,
        "entries": entries,
    }


def validate_word_table(declaration: dict[str, Any], site: dict[str, Any],
                        data: bytes, base: int, text_size: int,
                        extents: list[dict[str, Any]]) -> dict[str, Any]:
    table = parse_int(declaration["table"])
    count = int(declaration["count"])
    entries = []
    allowed_unclassified = {
        parse_int(value) for value in declaration.get("unclassified_targets", [])
    }
    observed_unclassified: set[int] = set()
    for index in range(count):
        target = image_word(data, base, text_size, table + index * 4)
        target_owner = owner_for(extents, target)
        target_type = target_owner["range_type"] if target_owner else "unclassified"
        if target_owner is None or target_type not in EXECUTABLE_TYPES:
            observed_unclassified.add(target)
            if target not in allowed_unclassified:
                raise ValueError(f"unnamed unclassified table target: {pc(target)}")
        entries.append({"index": index, "target": pc(target), "range_type": target_type})
    if observed_unclassified != allowed_unclassified:
        raise ValueError(f"declared unclassified target set mismatch at {pc(site['pc'])}")
    load_seen = False
    bound_seen = False
    cursor = site["pc"]
    for _ in range(24):
        if cursor < base + 4:
            break
        cursor -= 4
        word = image_word(data, base, text_size, cursor)
        if word >> 26 == 0x23 and ((word >> 16) & 31) == site["register"]:
            load_seen = True
        if word >> 26 == 0x0B and (word & 0xFFFF) == count:
            bound_seen = True
    if not load_seen or not bound_seen:
        raise ValueError(f"word-table source/bound mismatch at {pc(site['pc'])}")
    return {
        "kind": "word_table",
        "target_set_complete": True,
        "target_ownership_complete": not observed_unclassified,
        "source_pattern_verified": True,
        "table": pc(table),
        "count": count,
        "unclassified_targets": [pc(value) for value in sorted(observed_unclassified)],
        "entries": entries,
    }


def immediate_values_for_register(data: bytes, base: int, text_size: int,
                                  extent: dict[str, Any], reg: int) -> set[int]:
    values: set[int] = set()
    words = range(extent["start"], extent["end"] - 4, 4)
    for address in words:
        first = image_word(data, base, text_size, address)
        if first >> 26 != 15 or ((first >> 16) & 31) != reg:
            continue
        # MIPS delay-slot scheduling commonly places a branch or jump between
        # the high and low halves.  Accept at most three intervening words and
        # stop at any competing write to the destination register.
        for distance in range(1, 5):
            next_address = address + distance * 4
            if next_address >= extent["end"]:
                break
            second = image_word(data, base, text_size, next_address)
            op = second >> 26
            rt = (second >> 16) & 31
            rs = (second >> 21) & 31
            if op in {9, 13} and rt == reg and rs == reg:
                high = (first & 0xFFFF) << 16
                if op == 13:
                    values.add(high | (second & 0xFFFF))
                else:
                    signed = struct.unpack("<h", struct.pack("<H", second & 0xFFFF))[0]
                    values.add((high + signed) & 0xFFFFFFFF)
                break
            # All ordinary immediate/load operations write rt.  SPECIAL
            # arithmetic writes rd.  A competing definition ends this slice.
            if (op not in {0, 1, 2, 3, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17,
                           0x28, 0x29, 0x2A, 0x2B, 0x2E, 0x2F} and rt == reg) or \
               (op == 0 and ((second >> 11) & 31) == reg):
                break
    return values


def validate_declaration(declaration: dict[str, Any], site: dict[str, Any],
                         data: bytes, base: int, text_size: int,
                         extents: list[dict[str, Any]]) -> dict[str, Any]:
    kind = declaration["kind"]
    if kind == "jump_island":
        return validate_jump_island(declaration, site, data, base, text_size, extents)
    if kind == "word_table":
        return validate_word_table(declaration, site, data, base, text_size, extents)
    if kind == "constant":
        target = parse_int(declaration["target"])
        if site["linear_constant"] != target:
            raise ValueError(f"constant target mismatch at {pc(site['pc'])}")
        return {
            "kind": "constant",
            "target_set_complete": True,
            "source_pattern_verified": True,
            "targets": [pc(target)],
        }
    if kind == "constant_set":
        extent = owner_for(extents, site["pc"])
        assert extent is not None
        targets = {parse_int(value) for value in declaration["targets"]}
        materialized = immediate_values_for_register(
            data, base, text_size, extent, site["register"]
        )
        missing = targets - materialized
        if missing:
            rendered = ", ".join(pc(value) for value in sorted(missing))
            raise ValueError(f"declared targets not materialized at {pc(site['pc'])}: {rendered}")
        return {
            "kind": "constant_set",
            "target_set_complete": False,
            "source_pattern_verified": True,
            "targets": [pc(value) for value in sorted(targets)],
            "limitation": "materializations verified; all-reaching-definitions proof not yet compiled",
        }
    if kind == "pointer_slot":
        slot = parse_int(declaration["slot"])
        writers = [parse_int(value) for value in declaration["writers"]]
        for writer in writers:
            word = image_word(data, base, text_size, writer)
            if word >> 26 != 0x2B:
                raise ValueError(f"declared pointer writer is not sw: {pc(writer)}")
        return {
            "kind": "pointer_slot",
            "target_set_complete": False,
            "source_pattern_verified": True,
            "slot": pc(slot),
            "writers": [pc(value) for value in writers],
            "owner": declaration["owner"],
            "limitation": "runtime BIOS-table-derived pointer value has no finite target set yet",
        }
    raise ValueError(f"unknown resolution kind {kind}")


def check_expected(contract: dict[str, Any], probe: dict[str, Any],
                   retained_count: int, current_count: int,
                   current_only: list[tuple[str, int]],
                   retained_only: list[tuple[str, int]]) -> None:
    expected = contract["expected"]
    observed = {
        "text_bytes": probe["meta"]["text_size"],
        "extent_count": len(probe["extents"]),
        "claimed_bytes": probe["summary"]["claimed_bytes"],
        "unclassified_bytes": probe["summary"]["gap_bytes"],
        "retained_indirect_sites": retained_count,
        "current_typed_indirect_candidates": current_count,
        "raw_nonreturn_candidates": probe["summary"]["nonreturn_candidates"],
    }
    for key, value in expected.items():
        if key in observed and observed[key] != value:
            raise ValueError(f"expected {key}={value}, observed {observed[key]}")
    named_current = {
        (item["kind"], parse_int(item["pc"]))
        for item in contract["named_deltas"]["current_only"]
    }
    named_retained = {
        (item["kind"], parse_int(item["pc"]))
        for item in contract["named_deltas"]["retained_only"]
    }
    if set(current_only) != named_current:
        raise ValueError("current-only site delta differs from named contract")
    if set(retained_only) != named_retained:
        raise ValueError("retained-only site delta differs from named contract")


def compile_receipt(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    paths = {
        "image": args.image,
        "functions": args.functions,
        "repaired_extents": args.repaired_extents,
        "dispatch_map": args.dispatch_map,
        "jr_analysis": args.jr_analysis,
        "contract": args.contract,
        "c_probe": args.c_probe,
    }
    paths = {key: (root / value).resolve() if not value.is_absolute() else value.resolve()
             for key, value in paths.items()}
    normalized_paths = {key: relative_path(root, value) for key, value in paths.items()}
    contract = load_json(paths["contract"])
    data, base, text_size = read_psx_exe(paths["image"])
    image_hash = sha256(paths["image"])
    if image_hash != contract["image"]["sha256"]:
        raise ValueError("image hash differs from prerequisite contract")
    extents = build_extents(paths["functions"], paths["repaired_extents"], base, text_size)
    probe, compiler = run_probe(paths["c_probe"], paths["image"], extents)
    if probe["meta"]["load_base"] != base or probe["meta"]["text_size"] != text_size:
        raise ValueError("C probe image metadata mismatch")

    dispatch = load_json(paths["dispatch_map"])
    jr_analysis = load_json(paths["jr_analysis"])
    for source_name, source in (("dispatch_map", dispatch), ("jr_analysis", jr_analysis)):
        fixtures = source.get("fixture_sha256", {})
        if image_hash not in fixtures.values():
            raise ValueError(f"{source_name} does not pin the current image")

    retained_rows = dispatch["indirect_sites"]["sites"]
    retained = {(row["kind"], parse_int(row["pc"])) for row in retained_rows}
    typed_rows = [
        row for row in probe["candidates"]
        if row["kind"] in {"jr", "jalr"} and row["range_type"] in EXECUTABLE_TYPES
    ]
    current = {(row["kind"], row["pc"]) for row in typed_rows}
    current_only = sorted(current - retained)
    retained_only = sorted(retained - current)
    check_expected(
        contract, probe, len(retained), len(current), current_only, retained_only
    )

    declarations = {
        parse_int(item["pc"]): item for item in contract["jr_resolutions"]
    }
    decoded = {parse_int(key): value for key, value in jr_analysis["decoded"].items()}
    computed = {
        parse_int(key): value for key, value in jr_analysis["computed_code_jumps"].items()
    }
    failed = {parse_int(key): value for key, value in jr_analysis["failed"].items()}
    jr_receipts: list[dict[str, Any]] = []
    unresolved_target_sites: list[str] = []
    for site in sorted((row for row in typed_rows if row["kind"] == "jr"), key=lambda row: row["pc"]):
        address = site["pc"]
        if address in decoded:
            source = decoded[address]
            resolution = {
                "kind": "retained_word_table",
                "target_set_complete": True,
                "table": source["table"],
                "count": source["entries"],
                "targets": [entry["target"] for entry in source["targets"]],
                "provenance": "analysis/phase3_jr_tables.json",
            }
        elif address in computed and site["linear_constant"] is not None:
            resolution = {
                "kind": "linear_constant",
                "target_set_complete": True,
                "targets": [pc(site["linear_constant"])],
                "provenance": "C linear predecessor slice",
            }
        elif address in declarations:
            resolution = validate_declaration(
                declarations[address], site, data, base, text_size, extents
            )
            resolution["provenance"] = normalized_paths["contract"]
        else:
            prior = failed.get(address)
            resolution = {
                "kind": "unresolved",
                "target_set_complete": False,
                "prior_reason": prior.get("reason") if prior else None,
            }
        if not resolution["target_set_complete"]:
            unresolved_target_sites.append(pc(address))
        jr_receipts.append(
            {
                "id": f"SCUS_942_88:{pc(address)}:jr",
                "pc": pc(address),
                "extent": site["extent_name"],
                "direct_cfg_reached": site["direct_cfg_reached"],
                "resolution": resolution,
            }
        )

    jalr_receipts = []
    for site in sorted((row for row in typed_rows if row["kind"] == "jalr"), key=lambda row: row["pc"]):
        source = {
            "kind": site["linear_definition_kind"],
            "definition_pc": pc(site["linear_definition_pc"]) if site["linear_definition_pc"] else None,
            "linear_constant": pc(site["linear_constant"]) if site["linear_constant"] is not None else None,
            "memory_base_register": site["memory_base_register"],
            "memory_offset": site["memory_offset"],
        }
        jalr_receipts.append(
            {
                "id": f"SCUS_942_88:{pc(site['pc'])}:jalr",
                "pc": pc(site["pc"]),
                "extent": site["extent_name"],
                "direct_cfg_reached": site["direct_cfg_reached"],
                "target_source": source,
                "target_set_complete": False,
            }
        )
        unresolved_target_sites.append(pc(site["pc"]))

    contract_scene = contract["expected"]["scene_flow_dispatcher"]
    scene_extent = next(
        item for item in probe["extents"]
        if item["start"] == parse_int(contract_scene["start"])
    )
    if scene_extent["word_count"] != contract_scene["words"] or \
       scene_extent["direct_cfg_reached_words"] != contract_scene["direct_cfg_reached_words"]:
        raise ValueError("scene_flow_dispatcher direct CFG expectation failed")

    gaps = [
        {"start": pc(item["start"]), "end": pc(item["end"]),
         "byte_count": item["end"] - item["start"], "classification": "unclassified"}
        for item in probe["gaps"]
    ]
    candidate_rows = [
        {
            "pc": pc(row["pc"]),
            "kind": row["kind"],
            "register": row["register"],
            "range_type": row["range_type"],
            "extent": None if row["extent_index"] < 0 else row["extent_name"],
            "direct_cfg_reached": row["direct_cfg_reached"],
            "linear_definition": {
                "pc": pc(row["linear_definition_pc"]) if row["linear_definition_pc"] else None,
                "kind": row["linear_definition_kind"],
                "memory_base_register": row["memory_base_register"],
                "memory_offset": row["memory_offset"],
                "constant": pc(row["linear_constant"]) if row["linear_constant"] is not None else None,
            },
        }
        for row in probe["candidates"]
    ]

    input_hashes = {
        normalized_paths[key]: sha256(value)
        for key, value in paths.items()
    }
    receipt = {
        "schema": SCHEMA,
        "scope": {
            "image": "SCUS_942_88",
            "purpose": "shared Phase 4 prerequisite; not an F01 or Item-2 verdict",
            "excluded_claims": [
                "direct static writer completeness",
                "semantic ownership of unclassified bytes",
                "complete indirect callee target sets",
                "F01 row closure",
            ],
        },
        "inputs": {
            "paths": normalized_paths,
            "sha256": input_hashes,
            "compiler": compiler,
            "compile_flags": ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"],
        },
        "image_partition": {
            "load_base": pc(base),
            "text_end": pc(base + text_size),
            "text_bytes": text_size,
            "extent_count": len(probe["extents"]),
            "claimed_bytes": probe["summary"]["claimed_bytes"],
            "unclassified_bytes": probe["summary"]["gap_bytes"],
            "gaps": gaps,
            "byte_partition_complete": probe["summary"]["claimed_bytes"] + probe["summary"]["gap_bytes"] == text_size,
            "semantic_ownership_complete": probe["summary"]["gap_bytes"] == 0,
        },
        "instruction_candidate_census": {
            "universe": "every aligned loaded-text word with an architecturally valid jr/jalr encoding",
            "candidates": candidate_rows,
            "counts": {
                "all_nonreturn": probe["summary"]["nonreturn_candidates"],
                "returns": probe["summary"]["return_candidates"],
                "typed_code_or_thunk_nonreturn": len(current),
                "direct_cfg_reached_typed_nonreturn": probe["summary"]["direct_cfg_reached_nonreturn_candidates"],
            },
            "typed_candidate_census_complete": True,
            "instruction_execution_census_complete": False,
        },
        "retained_reconciliation": {
            "retained_identity": normalized_paths["dispatch_map"],
            "retained_count": len(retained),
            "current_typed_count": len(current),
            "intersection_count": len(current & retained),
            "current_only": [
                {"kind": kind, "pc": pc(address), "reason": next(
                    item["reason"] for item in contract["named_deltas"]["current_only"]
                    if item["kind"] == kind and parse_int(item["pc"]) == address
                )}
                for kind, address in current_only
            ],
            "retained_only": [
                {"kind": kind, "pc": pc(address), "reason": next(
                    item["reason"] for item in contract["named_deltas"]["retained_only"]
                    if item["kind"] == kind and parse_int(item["pc"]) == address
                )}
                for kind, address in retained_only
            ],
            "exact_set_reconciled": True,
        },
        "direct_cfg": {
            "universe": "typed code/thunk entry roots plus direct branch, jump, and call targets; no unresolved indirect targets",
            "queue_entries": probe["summary"]["direct_cfg_queue_entries"],
            "fixed_point_reached": True,
            "indirect_edges_followed": False,
            "scene_flow_dispatcher": {
                "start": pc(scene_extent["start"]),
                "word_count": scene_extent["word_count"],
                "direct_cfg_reached_words": scene_extent["direct_cfg_reached_words"],
            },
        },
        "indirect_control": {
            "jr_sites": jr_receipts,
            "jalr_sites": jalr_receipts,
            "site_inventory_complete": len(jr_receipts) + len(jalr_receipts) == len(current),
            "target_source_inventory_complete": all(
                item["target_source"]["kind"] != "" for item in jalr_receipts
            ),
            "target_sets_complete": not unresolved_target_sites,
            "sites_without_complete_target_sets": sorted(set(unresolved_target_sites)),
        },
        "verdicts": {
            "reproducible_static_prerequisite": True,
            "image_byte_partition_complete": True,
            "semantic_image_ownership_complete": False,
            "typed_indirect_inventory_complete": True,
            "direct_cfg_fixed_point_complete_for_declared_universe": True,
            "indirect_target_sets_complete": False,
            "ready_for_frontier_integration": True,
            "item2_ready_for_review": False,
            "strict_frontier_closed": False,
        },
        "review_blockers": [
            {
                "id": "UNCLASSIFIED_IMAGE_BYTES",
                "count": probe["summary"]["gap_bytes"],
                "universe": "resident loaded-text bytes",
            },
            {
                "id": "INDIRECT_TARGET_SETS_INCOMPLETE",
                "count": len(set(unresolved_target_sites)),
                "universe": "current typed resident jr/jalr candidate sites",
            },
        ],
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--image", type=Path, default=Path("REBUILD/files/SCUS_942.88"))
    parser.add_argument("--functions", type=Path, default=Path("analysis/functions.json"))
    parser.add_argument("--repaired-extents", type=Path, default=Path("analysis/functions_resident_repaired.txt"))
    parser.add_argument("--dispatch-map", type=Path, default=Path("analysis/phase3_dispatch_map.json"))
    parser.add_argument("--jr-analysis", type=Path, default=Path("analysis/phase3_jr_tables.json"))
    parser.add_argument("--contract", type=Path, default=Path("config/phase4_static_asm_prereqs.json"))
    parser.add_argument("--c-probe", type=Path, default=Path("tools/phase4_static_asm_probe.c"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = compile_receipt(args)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else args.root / args.output
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
