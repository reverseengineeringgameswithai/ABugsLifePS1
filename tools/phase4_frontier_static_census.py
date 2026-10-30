#!/usr/bin/env python3
"""Compile the two static censuses a semantic-frontier query cannot assert itself.

`tools/phase4_frontier_extractor.py` projects the static index into a checker
query.  Two of the checker's Item-2 demands cannot be answered from the index at
all, and until now the query answered both by DECLARATION:

* the ``callbacks`` category had zero records, because the index has no
  callback field -- an absence of data reported as an absence of surface; and
* ``census_complete`` was a per-image boolean the seed simply set, false by
  default for twenty of the twenty-one images because nobody had decided them.

This tool replaces both declarations with a derived, hash-bound receipt built by
`tools/phase4_callback_probe.c`, which is recompiled with warnings-as-errors and
re-run here rather than quoted from a retained attestation.

THE TWO SECTIONS ARE DIFFERENT UNIVERSES AND ARE NEVER SUBSTITUTED.

``function_pointer_census``
    Positive-only.  It reports every code address materialised by an adjacent
    lui/addiu or lui/ori pair and how the value leaves that site.  It finds
    registration sites; it does not bound the set of them.  A pointer built
    across a basic block, loaded out of data, or copied through a third
    register is invisible to it, so every callback group derived from it is
    emitted INCOMPLETE.  Its silence is not evidence.

``image_census``
    A census over its universe.  Every byte of every image is either claimed by
    an indexed extent or falls in an enumerated gap, and every load and store
    inside a gap is reported WITH ITS BASE PROVENANCE -- including the ones
    whose base could not be proved.  An unresolved base leaves the gap
    undecided and the image not census-complete.  That is the fail-closed
    direction: a positive-only sweep that found nothing would otherwise read
    exactly like a swept-and-clean image.

Usage
  tools/phase4_frontier_static_census.py \
      --output analysis/phase4_frontier_static_census.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
PROBE_SOURCE = ROOT / "tools/phase4_callback_probe.c"
GATE_PATH = ROOT / "analysis/phase4_static_asm_prerequisites.json"
F01_HARD_TRUTH_PATH = ROOT / "analysis/phase4_f01_static_hard_truth.json"
GAP_SEMANTICS_PATH = ROOT / "analysis/phase4_f01_gap_semantics.json"
SCHEMA = "abl-phase4-frontier-static-census/1"
EXECUTABLE_TYPES = {"code", "thunk"}
# The two state windows F01 declares.  They are inputs to the GAP SWEEP only:
# a gap byte that reaches one of them is a falsifier for the direct static
# writer census, which is exactly what this sweep exists to look for.
DEFAULT_WINDOWS = ((0x800823A0, 0x800823A2), (0x80082470, 0x80082472))
GP_VALUE = 0x80081D98


class CensusError(RuntimeError):
    """The census failed closed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def hex32(value: int) -> str:
    return f"0x{value:08X}"


def load_index() -> tuple[dict[str, Any], str]:
    if not INDEX_PATH.is_file():
        raise CensusError(f"missing static index: {INDEX_PATH}")
    raw = INDEX_PATH.read_bytes()
    index = json.loads(raw)
    if not index.get("valid"):
        raise CensusError("static index reports valid=false; regenerate it first")
    return index, sha256_bytes(raw)


def compile_probe(destination: Path) -> None:
    command = [
        os.environ.get("CC", "cc"),
        "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
        str(PROBE_SOURCE), "-o", str(destination),
    ]
    subprocess.run(command, check=True)


def resident_range(image_id: str, raw: bytes, base: int, size: int,
                   header_rule_bytes: int) -> dict[str, Any]:
    """Split the FILE universe from the RESIDENT loaded universe.

    A pinned image file is not the same thing as the bytes the console loads.
    A PS-X EXE carries a 2,048-byte header whose own fields state the load base
    and text size; every level overlay carries a 4-byte header.  Those bytes are
    file metadata: never fetched, never executed, never a data operand.

    Treating them as part of the image census made the header show up as a
    2,048-byte *unclassified gap* in `SCUS_942_88` -- an accounting error of kind,
    not of size, because "unclassified" means "resident bytes nobody has owned"
    and these are not resident at all.

    The prefix is DERIVED from the bytes, cross-checked against the index's
    declared `header_rule.bytes`, and any disagreement is reported rather than
    silently resolved.  The index declares `bytes: 0` for `SCUS_942_88`, which is
    wrong; that disagreement is a finding and is carried into the receipt.
    """
    declared = int(header_rule_bytes or 0)
    if raw[:8] == b"PS-X EXE":
        if len(raw) < 0x800:
            raise CensusError(f"{image_id}: PS-X EXE shorter than its header")
        text_base, text_size = struct.unpack_from("<II", raw, 0x18)
        if text_base & 3 or text_size & 3 or 0x800 + text_size > len(raw):
            raise CensusError(f"{image_id}: PS-X EXE declares an invalid load range")
        if base + 0x800 != text_base:
            raise CensusError(
                f"{image_id}: index file_va_base {hex(base)} does not place the "
                f"PS-X EXE text at its declared {hex(text_base)}")
        prefix, source = 0x800, "ps_x_exe_header"
        start, end = text_base, text_base + text_size
    else:
        prefix, source = declared, "index_header_rule"
        start, end = base + prefix, base + size
    return {
        "nonresident_prefix_bytes": prefix,
        "nonresident_prefix_source": source,
        "header_rule_bytes_declared_by_index": declared,
        "header_rule_agrees_with_bytes": prefix == declared,
        "resident_start": start,
        "resident_end": end,
        "resident_bytes": end - start,
    }


def build_manifest(index: dict[str, Any],
                   windows: tuple[tuple[int, int], ...]) -> tuple[str, dict[str, Any]]:
    """Manifest lines plus the per-image extent bookkeeping Python needs.

    The image bytes are hash-checked against the index's pin HERE, before the
    probe reads them.  A probe run against an image the index does not describe
    would produce a receipt that looks fine and means nothing.
    """
    lines: list[str] = []
    for start, end in windows:
        lines.append(f"window\t{start:08x}\t{end:08x}")
    lines.append(f"gp\t{GP_VALUE:08x}")
    by_image: dict[str, dict[str, Any]] = {}
    extents: dict[str, list[tuple[int, int, str]]] = {}
    for record in index["records"]:
        image_id = record["image_id"]
        extents.setdefault(image_id, []).append(
            (parse_int(record["entry"]), parse_int(record["end"]),
             str(record.get("range_type"))))
    for image in index["images"]:
        image_id = image["image_id"]
        path = ROOT / image["path"]
        if not path.is_file():
            raise CensusError(f"image file absent: {image['path']}")
        raw = path.read_bytes()
        size = int(image["expected_size"])
        if len(raw) != size:
            raise CensusError(
                f"{image_id}: size {len(raw)} != pinned {size}")
        digest = sha256_bytes(raw)
        if digest != image["expected_sha256"]:
            raise CensusError(f"{image_id}: sha256 does not match the index pin")
        base = parse_int(image["file_va_base"])
        resident = resident_range(image_id, raw, base, size,
                                  (image.get("header_rule") or {}).get("bytes", 0))
        lines.append(f"image\t{image_id}\t{path}\t{base:08x}\t{size}")
        lines.append(f"resident\t{image_id}\t{resident['resident_start']:08x}"
                     f"\t{resident['resident_end']:08x}")
        rows = sorted(extents.get(image_id, ()))
        outside = [(a, b, t) for a, b, t in rows
                   if a < resident["resident_start"] or b > resident["resident_end"]]
        if outside:
            raise CensusError(
                f"{image_id}: {len(outside)} indexed extent(s) fall outside the "
                f"resident range, starting at {hex(outside[0][0])}")
        for start, end, range_type in rows:
            lines.append(f"extent\t{image_id}\t{start:08x}\t{end:08x}\t{range_type}")
        by_image[image_id] = {
            "id": image_id, "path": image["path"], "sha256": digest,
            "base": base, "size": size, "extents": rows, **resident,
        }
    return "\n".join(lines) + "\n", by_image


def run_probe(manifest: str) -> list[list[str]]:
    with tempfile.TemporaryDirectory(prefix="phase4-frontier-census-") as raw_temp:
        temp = Path(raw_temp)
        manifest_path = temp / "manifest.tsv"
        manifest_path.write_text(manifest, encoding="utf-8")
        binary = temp / "phase4_callback_probe"
        compile_probe(binary)
        result = subprocess.run([str(binary), str(manifest_path)],
                                check=True, text=True, stdout=subprocess.PIPE)
    return [line.split("\t") for line in result.stdout.splitlines() if line]


def partition(image: dict[str, Any]) -> tuple[int, list[tuple[int, int]], int]:
    """Claimed bytes, enumerated gaps, and overlapping bytes over the RESIDENT range.

    The nonresident header prefix is not a gap -- it is not part of this
    universe at all -- so the complement is taken inside the resident range.
    """
    base, limit = image["resident_start"], image["resident_end"]
    claimed = 0
    overlap = 0
    gaps: list[tuple[int, int]] = []
    cursor = base
    for start, end, _ in image["extents"]:
        if start < cursor:
            overlap += min(end, cursor) - start
        if start > cursor:
            gaps.append((cursor, min(start, limit)))
        if end > cursor:
            claimed += end - max(start, cursor)
            cursor = end
    if cursor < limit:
        gaps.append((cursor, limit))
    return claimed, [(a, b) for a, b in gaps if b > a], overlap


def _merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if end <= start:
            continue
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def _subtract(whole: tuple[int, int], covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
    remaining: list[tuple[int, int]] = []
    cursor = whole[0]
    for start, end in _merge(covered):
        if end <= whole[0] or start >= whole[1]:
            continue
        start, end = max(start, whole[0]), min(end, whole[1])
        if start > cursor:
            remaining.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < whole[1]:
        remaining.append((cursor, whole[1]))
    return remaining


def gap_boundary_edges(word_at: dict[int, int], reachable: set[int],
                       independent_entries: set[int],
                       generator: Any) -> dict[int, list[dict[str, Any]]]:
    """EVERY successor of a reachable instruction that leaves the claimed extents.

    ⚠️ Counting only branch, jump, call and known-`jr` TARGETS is not a
    direct-edge result.  Two boundary edges have no target field at all and were
    invisible:

    * ordinary FALLTHROUGH -- the last word of an extent that is not an
      unconditional terminator falls into whatever follows it; and
    * the CALL RETURN continuation -- `jal`/`jalr` resumes at pc+8, which may sit
      past the end of the extent the call was made from.

    Both are enumerated here by kind, so "no direct edge enters any gap" is a
    statement about all of them rather than about the ones that carry an address.
    """
    landing: dict[int, list[dict[str, Any]]] = {}
    # ⚠️ A DELAY SLOT has no fallthrough of its own -- IN THE DELAY CONTEXT.
    # The word after a jump runs before control transfers, and where control
    # goes next is decided by the transfer, not by the slot: after `j`/`jr` it
    # does not continue linearly at all, and after `jal`/`jalr` it resumes at
    # the call's pc+8, which `call_return` already records. Emitting a
    # fallthrough from every slot reported 67 edges into gaps where the real
    # figure is far smaller.
    #
    # ⚠️⚠️ But the delay-slot property is a property of an EXECUTION CONTEXT,
    # not of an address. The same address can ALSO be entered independently --
    # as a branch/jump/jr target, a not-taken continuation, a call return, or
    # an extent entry -- and in that context the instruction executes on its
    # own and control continues linearly to pc+4. A global address-only
    # exclusion suppressed that successor everywhere, so an address that is
    # both a delay slot and an independent entry lost its real fallthrough.
    # `independent_entries` is the set of addresses the CFG walk recorded as
    # entered by an explicit edge (extent entries plus every followed
    # successor); fallthrough is suppressed only for an address whose ONLY
    # established execution context is the delay slot.
    delay_slots = {pc + 4 for pc in reachable
                   if generator.control_flow(word_at[pc], pc)[0] is not None}

    def record(target: int | None, source: int, kind: str) -> None:
        if target is None or target in word_at:
            return          # stays inside claimed executable bytes
        landing.setdefault(target, []).append(
            {"target": hex32(target), "source": hex32(source), "kind": kind})

    for pc in sorted(reachable):
        word = word_at[pc]
        kind, target = generator.control_flow(word, pc)
        if kind is None:
            if pc not in delay_slots or pc in independent_entries:
                record(pc + 4, pc, "fallthrough")
            continue
        if kind == "branch":
            for value in generator.branch_successors(word, pc, target):
                record(value, pc, "branch")
        elif kind == "jump":
            record(target, pc, "jump")
        elif kind == "call":
            record(target, pc, "call")
            record(pc + 8, pc, "call_return")
        elif kind == "indirect_call":
            record(pc + 8, pc, "indirect_call_return")
        elif kind == "indirect_jump":
            for value in generator.JR_TARGETS.get(pc, ()):  # known targets only
                record(value, pc, "resolved_indirect_jump")
        # `return` leaves through $ra and has no static successor here
    return landing


def classify_gap_ownership(index: dict[str, Any], by_image: dict[str, Any],
                           gaps: dict[str, list[tuple[int, int]]],
                           ) -> tuple[dict[tuple[str, int, int], dict[str, Any]], dict[str, Any]]:
    """Decide what each unclaimed BYTE is, before interpreting the words in it.

    ⚠️ A word in a gap that decodes as `lw` is an INSTRUCTION-SHAPED WORD, not a
    confirmed memory reference.  Counting those as undecided references states a
    deficit in the wrong category: the prior question is who owns the bytes.

    ⚠️⚠️ OWNERSHIP IS RECORDED PER BYTE, NEVER PER GAP.  A whole-gap boolean was
    the previous shape and it overstated the result badly: `read_as_data` proves
    something about the words an access actually touches, so marking a
    13,536-byte region "has evidence" on the strength of 184 covered words left
    3,200 words unowned while the headline said the region was accounted for.
    Every class below contributes BYTE INTERVALS, they are unioned, and the
    complement is reported exactly.

    * `zero_filled` -- maximal runs of 0x00.  A measurement.  It says only that
      those bytes contain no load/store encoding, NOT that they are data: a zero
      word is a valid `sll zero,zero,0`.
    * `decoded_jump_table` -- intersection with a table decoded by
      `tools/phase3_jr_tables.py`, whose artifact the index pins by hash.
    * `read_as_data` -- `[address, address+width)` of each statically resolved
      access from analysed code that lands inside the gap.
    * `targeted_by_a_proved_indirect_jump` -- the four bytes at a `jr` target
      whose set the shared gate proved complete.  It proves an instruction
      STARTS there and nothing about how far the island runs.
    """
    import phase4_static_frontier as generator   # shared edge semantics

    tables: list[tuple[int, int]] = []
    jr_path = ROOT / "analysis/phase3_jr_tables.json"
    if jr_path.is_file():
        for _, record in (json.loads(jr_path.read_bytes()).get("decoded") or {}).items():
            base = parse_int(record["table"])
            tables.append((base, base + 4 * int(record["entries"])))

    # ⚠️ The gate stores jump islands under `entries` and every other kind under
    # `targets`; reading one and not the other reported 38 distinct targets
    # instead of 450 and would have silently under-owned every gap.
    indirect_targets: dict[int, list[str]] = {}
    if GATE_PATH.is_file():
        for site in json.loads(GATE_PATH.read_bytes())["indirect_control"]["jr_sites"]:
            resolution = site.get("resolution") or {}
            if not resolution.get("target_set_complete"):
                continue
            values = [parse_int(value) for value in (resolution.get("targets") or [])]
            values += [parse_int(entry["target"])
                       for entry in (resolution.get("entries") or [])]
            for value in set(values):
                indirect_targets.setdefault(value, []).append(site["pc"])

    # Islands the index decoded from a proved indirect-jump target landing in
    # unclaimed bytes, each with its own stopping proof and none of them widening
    # a neighbouring extent.
    islands: dict[str, list[tuple[int, int]]] = {}
    for island in index.get("target_root_islands") or []:
        islands.setdefault(island["image"], []).append(
            (parse_int(island["start"]), parse_int(island["end"])))

    accesses: dict[str, list[tuple[int, int]]] = {}
    for record in index["records"]:
        for access in record.get("memory_accesses") or []:
            address = access.get("address")
            if address:
                start = parse_int(address)
                accesses.setdefault(record["image_id"], []).append(
                    (start, start + int(access.get("width") or 4)))

    # ---- content-verified trig ownership: BOTH evidence legs required ------
    # A mathematical-looking byte sequence alone does not establish how the
    # program uses it, and a dynamic-index read alone does not identify the
    # resident content. The C receipt independently supplies both. It is
    # accepted only when its exact reader-PC/range set is identical to the
    # range annotations carried by this index, and only the receipt's two
    # pre-existing gap intervals are eligible for ownership -- never the whole
    # table extents.
    if not F01_HARD_TRUTH_PATH.is_file():
        raise CensusError("missing F01 static hard-truth receipt")
    f01_raw = F01_HARD_TRUTH_PATH.read_bytes()
    f01_sha = sha256_bytes(f01_raw)
    expected_f01_sha = (index.get("source_dependencies") or {}).get(
        str(F01_HARD_TRUTH_PATH.relative_to(ROOT)))
    if expected_f01_sha != f01_sha:
        raise CensusError("static index does not pin the current F01 hard-truth receipt")
    f01 = json.loads(f01_raw)
    if not (f01.get("verdicts") or {}).get("trig_semantic_disposition_supported"):
        raise CensusError("F01 hard-truth receipt does not support trig ownership")
    receipt_readers: dict[tuple[str, int], tuple[int, int, str]] = {}
    trig_gap_spans: dict[str, list[tuple[int, int]]] = {}
    trig_tables_meta: list[dict[str, Any]] = []
    for table in (f01.get("c_probe") or {}).get("trigonometric_tables") or []:
        image_id = str(table["image"])
        content = table.get("content_comparison") or {}
        gap = table.get("gap") or {}
        if content.get("mismatched_entries") != 0 or gap.get("mismatched_entries") != 0:
            raise CensusError(f"{table.get('id')}: trig content comparison is not exact")
        span = (parse_int(gap["start"]), parse_int(gap["end"]))
        if span not in set(gaps.get(image_id) or []):
            raise CensusError(
                f"{table.get('id')}: {hex32(span[0])}..{hex32(span[1])} is not "
                "one exact pre-existing gap; refusing to widen or split an extent")
        trig_gap_spans.setdefault(image_id, []).append(span)
        for reader in table.get("readers") or []:
            key = (image_id, parse_int(reader["pc"]))
            if key in receipt_readers:
                raise CensusError(f"duplicate trig reader {key}")
            low, high = map(parse_int, reader["effective_address_range"])
            receipt_readers[key] = (low, high, str(table["id"]))
        trig_tables_meta.append({
            "id": table["id"], "image": image_id,
            "full_table": [table["base"], table["end"]],
            "gap": [gap["start"], gap["end"]],
            "gap_bytes": int(gap["byte_count"]),
            "entry_count": int(table["entry_count"]),
            "stride_bytes": int(table["stride_bytes"]),
            "amplitude": int(table["amplitude"]),
            "formula": table["formula"],
            "full_content_mismatches": int(content["mismatched_entries"]),
            "gap_content_mismatches": int(gap["mismatched_entries"]),
            "reader_count": len(table.get("readers") or []),
        })
    indexed_readers: dict[tuple[str, int], tuple[int, int, str]] = {}
    for record in index["records"]:
        for access in record.get("memory_accesses") or []:
            resolved = access.get("resolved_address_range")
            if not resolved:
                continue
            key = (record["image_id"], parse_int(access["pc"]))
            indexed_readers[key] = (
                parse_int(resolved["start"]), parse_int(resolved["end"]),
                str(resolved["table"]))
    receipt_only = set(receipt_readers) - set(indexed_readers)
    index_only = set(indexed_readers) - set(receipt_readers)
    value_mismatches = sorted(
        key for key in set(receipt_readers) & set(indexed_readers)
        if receipt_readers[key] != indexed_readers[key])
    if receipt_only or index_only or value_mismatches:
        raise CensusError(
            "F01 trig reader reconciliation failed: "
            f"receipt-only {sorted(receipt_only)}, index-only {sorted(index_only)}, "
            f"range/table mismatches {value_mismatches}")

    # ---- partial-gap semantics receipt: three tiers, none conflated ---------
    # The 2026-08-07 campaign receipt contributes byte INTERVALS (clipped to
    # each current gap -- it can never widen anything) at three explicitly
    # different evidence tiers: the sine tail is CONTENT-verified (exact
    # re-derivation), the atan table is INSTRUCTION-derived (the reader's own
    # twelve indexing/fold words verified; its analytic content model is
    # approximate and says so), and the entry-pointer runs are STRUCTURAL
    # (membership in the exact census entry set, false-positive model stated).
    if not GAP_SEMANTICS_PATH.is_file():
        raise CensusError("missing F01 gap-semantics receipt")
    gs_raw = GAP_SEMANTICS_PATH.read_bytes()
    expected_gs_sha = (index.get("source_dependencies") or {}).get(
        str(GAP_SEMANTICS_PATH.relative_to(ROOT)))
    if expected_gs_sha != sha256_bytes(gs_raw):
        raise CensusError("static index does not pin the current gap-semantics receipt")
    gs = json.loads(gs_raw)
    if not (gs.get("verdicts") or {}).get("atan_instructions_verified"):
        raise CensusError("gap-semantics receipt: atan instructions unverified")
    if not (gs.get("verdicts") or {}).get("sine_tail_exact"):
        raise CensusError("gap-semantics receipt: sine tail not exact")
    if (gs.get("verdicts") or {}).get("atan_content_model_exact") is not False:
        raise CensusError("gap-semantics receipt shape changed: re-review the "
                          "atan content-model disclosure before consuming it")
    gs_claims = gs["claims"]
    gs_intervals: dict[str, list[tuple[int, int]]] = {
        "content_verified_trig_tail": [tuple(
            parse_int(x) for x in gs_claims["content_verified_trig_tail"]["interval"])],
        "reader_indexed_atan_table": [tuple(
            parse_int(x) for x in gs_claims["reader_indexed_atan_table"]["interval"])],
        "function_entry_pointer_run": [
            (parse_int(a), parse_int(b))
            for a, b in gs_claims["function_entry_pointer_runs"]["intervals"]],
    }

    # ---- arm the SAME verified jr universe the index's CFG follows ----------
    # The walk below used to run with an empty JR_TARGETS map, so its
    # `resolved_indirect_jump` boundary kind was structurally dead and its
    # reachable set was smaller than the index's. Both loaders fail closed on
    # an image-hash mismatch, exactly as they do inside the index generator,
    # and their provenance is carried in the receipt rather than assumed.
    resident_meta = next((row for row in index["images"]
                          if row.get("role") == "resident"), None)
    resident_sha = (resident_meta or {}).get("sha256") or ""
    generator.load_jr_targets(generator.JR_ARTIFACT_PATH, resident_sha)
    gate_import = generator.load_gate_jr_targets(generator.GATE_ARTIFACT_PATH,
                                                 resident_sha)
    jr_provenance = {
        "phase3_jr_tables": {
            "source": generator.JR_PROVENANCE.get("source"),
            "verified": generator.JR_PROVENANCE.get("verified"),
            "sites": generator.JR_PROVENANCE.get("sites"),
            "artifact_sha256": generator.JR_PROVENANCE.get("artifact_sha256"),
        },
        "gate_only_jr_sites": {
            "source": gate_import.get("source"),
            "verified": gate_import.get("verified"),
            "sites": gate_import.get("sites"),
            "sites_added": gate_import.get("sites_added"),
            "artifact_sha256": gate_import.get("artifact_sha256"),
            "phase3_sites_not_in_gate": gate_import.get("phase3_sites_not_in_gate"),
        },
    }

    result: dict[tuple[str, int, int], dict[str, Any]] = {}
    edge_kinds: dict[str, int] = {}
    for image_id, rows in gaps.items():
        if not rows:
            continue
        image = by_image[image_id]
        raw = (ROOT / image["path"]).read_bytes()
        base = image["base"]
        word_at: dict[int, int] = {}
        entries: list[int] = []
        for start, end, range_type in image["extents"]:
            if range_type not in EXECUTABLE_TYPES:
                continue
            entries.append(start)
            for pc in range(start, end, 4):
                word_at[pc] = int.from_bytes(raw[pc - base:pc - base + 4], "little")
        reachable, block_starts, _ = generator.image_direct_cfg(
            word_at, sorted(entries))
        landing = gap_boundary_edges(word_at, reachable, block_starts, generator)
        image_accesses = accesses.get(image_id, ())

        for start, end in rows:
            blob = raw[start - base:end - base]
            classes: dict[str, list[tuple[int, int]]] = {}

            # ⚠️ WORD-granular, and only aligned whole-zero words. A byte-level
            # zero run is noise inside code -- most MIPS instructions contain
            # zero bytes, so `addiu rt,rs,0` alone contributed "evidence" for 5
            # scattered bytes of a 20-byte executable island. A zero WORD is
            # `sll zero,zero,0` and provably carries no load/store encoding;
            # that is the whole of what this class asserts.
            runs: list[tuple[int, int]] = []
            for offset in range(0, (end - start) // 4 * 4, 4):
                if (start + offset) % 4:
                    continue
                if blob[offset:offset + 4] == b"\x00\x00\x00\x00":
                    runs.append((start + offset, start + offset + 4))
            if runs:
                classes["zero_filled"] = _merge(runs)

            overlap = [(max(start, low), min(end, high)) for low, high in tables
                       if min(end, high) > max(start, low)]
            if overlap:
                classes["decoded_jump_table"] = overlap

            data = [(max(start, low), min(end, high)) for low, high in image_accesses
                    if min(end, high) > max(start, low)]
            if data:
                classes["read_as_data"] = data

            trig = [(max(start, low), min(end, high))
                    for low, high in trig_gap_spans.get(image_id, ())
                    if min(end, high) > max(start, low)]
            if trig:
                classes["content_verified_trigonometric_table"] = trig

            # gap-semantics claims apply to the RESIDENT image only and are
            # CLIPPED to this gap -- a claim outside every gap contributes
            # nothing and can never widen or split an extent.
            if image_id == "SCUS_942_88":
                for gs_name, gs_spans in gs_intervals.items():
                    clipped = [(max(start, low), min(end, high))
                               for low, high in gs_spans
                               if min(end, high) > max(start, low)]
                    if clipped:
                        classes[gs_name] = clipped

            landed = sorted(value for value in indirect_targets if start <= value < end)
            if landed:
                classes["targeted_by_a_proved_indirect_jump"] = [
                    (value, min(value + 4, end)) for value in landed]

            island_spans = [(max(start, low), min(end, high))
                            for low, high in islands.get(image_id, ())
                            if min(end, high) > max(start, low)]
            if island_spans:
                classes["decoded_target_root_island"] = island_spans

            edges = [row for target, rows_ in landing.items() if start <= target < end
                     for row in rows_]
            for row in edges:
                edge_kinds[row["kind"]] = edge_kinds.get(row["kind"], 0) + 1

            covered = _merge([span for spans in classes.values() for span in spans])
            # `zero_filled` says a byte holds no load/store encoding; it is not a
            # claim about what the byte IS. The semantic total excludes it so a
            # run of padding can never read as an owned region.
            semantic = _merge([span for name, spans in classes.items()
                               if name != "zero_filled" for span in spans])
            unevidenced = _subtract((start, end), covered)
            # ⚠️ THE DISPOSITION IS EXPLICIT so "some evidence" can never be read
            # as "owned". `partial` is the answer for most of the corpus and it
            # is the answer this census refuses to round up.
            if not covered:
                disposition = "none"
            elif not unevidenced:
                disposition = "complete"
            else:
                disposition = "partial"
            result[(image_id, start, end)] = {
                "disposition": disposition,
                "image": image_id, "start": hex32(start), "end": hex32(end),
                "byte_count": end - start,
                "ownership_classes": sorted(classes),
                "bytes_by_class": {name: sum(b - a for a, b in _merge(spans))
                                   for name, spans in sorted(classes.items())},
                "bytes_with_any_evidence": sum(b - a for a, b in covered),
                "bytes_with_semantic_evidence": sum(b - a for a, b in semantic),
                "bytes_with_no_evidence": sum(b - a for a, b in unevidenced),
                "unevidenced_ranges": [{"start": hex32(a), "end": hex32(b),
                                        "byte_count": b - a} for a, b in unevidenced],
                "incoming_boundary_edges": sorted(
                    edges, key=lambda row: (row["source"], row["kind"])),
                "incoming_boundary_edge_count": len(edges),
                "proved_indirect_jump_sites": sorted(
                    {pc for value in landed for pc in indirect_targets[value]}),
            }
    return result, {
        "images_checked": sorted(gaps),
        "jump_tables_consulted": len(tables),
        "proved_indirect_jump_targets_consulted": len(indirect_targets),
        "indirect_target_source": "analysis/phase4_static_asm_prerequisites.json",
        "boundary_edge_kinds_enumerated": [
            "fallthrough", "branch", "jump", "call", "call_return",
            "indirect_call_return", "resolved_indirect_jump"],
        "boundary_edges_into_gaps_by_kind": dict(sorted(edge_kinds.items())),
        "boundary_edge_universe": (
            "instructions reachable from every indexed executable extent entry "
            "(target-root island records included) by direct branch/jump/call "
            "edges, post-call fall-through, and the verified jr targets armed "
            "below -- the same universe as the index's CFG. All seven successor "
            "kinds are enumerated. Fallthrough from a delay-slot address is "
            "suppressed ONLY when the delay slot is that address's sole "
            "established execution context; an address that is also entered "
            "independently (branch/jump/jr target, not-taken continuation, "
            "call return, extent entry) keeps its linear successor."),
        "cfg_jr_sources_armed": jr_provenance,
        "content_verified_trigonometric_table": {
            "source": str(F01_HARD_TRUTH_PATH.relative_to(ROOT)),
            "source_sha256": f01_sha,
            "basis": ("complete-table mathematical byte comparison with zero "
                      "mismatches PLUS instruction-derived reader ranges; either "
                      "leg alone is insufficient"),
            "extent_rule": ("only the two exact gap intervals from the receipt "
                            "are covered; full-table extents are descriptive and "
                            "do not widen any indexed extent"),
            "reader_reconciliation": "exact (image,pc,range,table) set both directions",
            "receipt_only_readers": [],
            "index_only_readers": [],
            "range_or_table_mismatches": [],
            "reader_count": len(receipt_readers),
            "tables": trig_tables_meta,
        },
        "note": ("the index's CFG imports BOTH verified jr sources -- "
                 "analysis/phase3_jr_tables.json and the gate-only jr sites "
                 "from analysis/phase4_static_asm_prerequisites.json -- and "
                 "promotes decoded target-root islands to census records, so a "
                 "proved indirect-jump target now lands in claimed bytes "
                 "unless its island decode fails; a failed decode leaves the "
                 "gap and is visible here"),
    }


def compile_census(windows: tuple[tuple[int, int], ...]) -> dict[str, Any]:
    index, index_sha = load_index()
    manifest, by_image = build_manifest(index, windows)
    rows = run_probe(manifest)

    pointers: list[dict[str, Any]] = []
    gap_refs: dict[str, list[dict[str, Any]]] = {}
    probe_gaps: dict[str, list[tuple[int, int]]] = {}
    for fields in rows:
        tag = fields[0]
        if tag == "fnptr":
            (_, image_id, def_pc, value, owner_image, owner_entry, consumer,
             register, offset, call_target, consumer_pc, is_entry) = fields
            pointers.append({
                "image": image_id,
                "materialised_at": hex32(int(def_pc, 16)),
                "value": hex32(int(value, 16)),
                "target_image": owner_image,
                "target_function": hex32(int(owner_entry, 16)),
                "target_is_function_entry": is_entry == "1",
                "consumer": consumer,
                "consumer_pc": hex32(int(consumer_pc, 16)),
                "slot_base_register": int(register),
                "slot_offset": int(offset),
                "registrar_callee": (None if call_target == "-"
                                     else hex32(int(call_target, 16))),
            })
        elif tag == "gapref":
            (_, image_id, pc, mnemonic, width, kind, register, offset,
             provenance, effective, window_hit) = fields
            gap_refs.setdefault(image_id, []).append({
                "image": image_id, "pc": hex32(int(pc, 16)),
                "mnemonic": mnemonic, "width": int(width), "kind": kind,
                "base_register": int(register), "offset": int(offset),
                "base_provenance": provenance,
                "effective_address": (hex32(int(effective, 16))
                                      if provenance != "unresolved" else None),
                "reaches_window": window_hit == "1",
            })
        elif tag == "gap":
            probe_gaps.setdefault(fields[1], []).append(
                (int(fields[2], 16), int(fields[3], 16)))

    gap_rows: dict[str, list[tuple[int, int]]] = {}
    for image_id in sorted(by_image):
        _, rows, _ = partition(by_image[image_id])
        gap_rows[image_id] = rows
    ownership, ownership_meta = classify_gap_ownership(index, by_image, gap_rows)

    images: list[dict[str, Any]] = []
    falsifiers: list[dict[str, Any]] = []
    for image_id in sorted(by_image):
        image = by_image[image_id]
        claimed, gaps, overlap = partition(image)
        # The probe walks the complement itself.  Requiring the two independent
        # partitions to agree EXACTLY is the point: a gap either side computed
        # alone would be a number nobody re-derived.
        if probe_gaps.get(image_id, []) != gaps:
            raise CensusError(
                f"{image_id}: probe and index disagree about the extent complement")
        refs = gap_refs.get(image_id, [])
        unresolved = [row for row in refs if row["base_provenance"] == "unresolved"]
        reaching = [row for row in refs if row["reaches_window"]]
        falsifiers.extend(reaching)
        gap_bytes = sum(end - start for start, end in gaps)
        partition_complete = claimed + gap_bytes == image["resident_bytes"] and overlap == 0
        gaps_decided = not unresolved
        images.append({
            "id": image_id,
            "path": image["path"],
            "sha256": image["sha256"],
            "base": hex32(image["base"]),
            "size": image["size"],
            # FILE universe vs RESIDENT universe, never collapsed into one number.
            "file_bytes": image["size"],
            "nonresident_prefix_bytes": image["nonresident_prefix_bytes"],
            "nonresident_prefix_source": image["nonresident_prefix_source"],
            "header_rule_bytes_declared_by_index":
                image["header_rule_bytes_declared_by_index"],
            "header_rule_agrees_with_bytes": image["header_rule_agrees_with_bytes"],
            "resident_start": hex32(image["resident_start"]),
            "resident_end": hex32(image["resident_end"]),
            "resident_bytes": image["resident_bytes"],
            "extent_count": len(image["extents"]),
            "claimed_bytes": claimed,
            "overlapping_bytes": overlap,
            "gap_count": len(gaps),
            "gap_bytes": gap_bytes,
            "gaps": [{"start": hex32(a), "end": hex32(b), "byte_count": b - a}
                     for a, b in gaps],
            # ⚠️ NAMED for what they are. These are words inside unclaimed bytes
            # whose ENCODING is a load or store; nothing here establishes that
            # any of them is executed. Calling them "memory references" put a
            # deficit in the wrong category.
            "instruction_shaped_words_in_gaps": len(refs),
            "instruction_shaped_words_with_a_proved_base": len(refs) - len(unresolved),
            "instruction_shaped_words_with_an_unprovable_base": len(unresolved),
            "instruction_shaped_words_reaching_a_window": len(reaching),
            "gap_ownership": [ownership[(image_id, a, b)] for a, b in gaps],
            "gap_bytes_with_no_evidence": sum(
                ownership[(image_id, a, b)]["bytes_with_no_evidence"] for a, b in gaps),
            "gap_bytes_with_semantic_evidence": sum(
                ownership[(image_id, a, b)]["bytes_with_semantic_evidence"]
                for a, b in gaps),
            "byte_partition_complete": partition_complete,
            "gap_words_all_attributed": gaps_decided,
            # census_complete is DERIVED, never declared.  All three conjuncts
            # are necessary: a complete partition with an undecided gap
            # reference is a census whose remainder nobody has read.
            "census_complete": bool(partition_complete and gaps_decided
                                    and not reaching),
        })

    # A materialised address that lands INSIDE a code extent but not ON a
    # function entry is not a function pointer -- it is a data address in a
    # range the index calls code, and every one of them here is a buffer handed
    # to memcpy/memset.  They are excluded from the callback surface and listed
    # separately rather than dropped, because an exclusion nobody can see is
    # indistinguishable from a scan that never ran.
    entry_rows = [row for row in pointers if row["target_is_function_entry"]]
    interior_rows = [row for row in pointers if not row["target_is_function_entry"]]

    consumers: dict[str, int] = {}
    for row in entry_rows:
        consumers[row["consumer"]] = consumers.get(row["consumer"], 0) + 1
    slots: dict[str, dict[str, Any]] = {}
    for row in entry_rows:
        if row["consumer"] == "store":
            key = (f"slot:{row['image']}:r{row['slot_base_register']}"
                   f"{row['slot_offset']:+d}")
        elif row["consumer"] == "argument":
            key = f"registrar:{row['image']}:{row['registrar_callee']}"
        else:
            key = f"{row['consumer']}:{row['image']}:{row['consumer_pc']}"
        group = slots.setdefault(key, {
            "id": key, "consumer": row["consumer"], "sites": [], "targets": []})
        group["sites"].append(row["consumer_pc"])
        target = f"{row['target_image']}:{row['target_function']}"
        if target not in group["targets"]:
            group["targets"].append(target)
    for group in slots.values():
        group["sites"].sort()
        group["targets"].sort()

    # ---- exact-set cross-check against the shared static-ASM gate ------------
    # The gate partitions the SAME resident universe from a DIFFERENT extent
    # source (repaired extents, not static-index records). Once the nonresident
    # header is out of the way the two are directly comparable, so the gaps are
    # differenced as SETS in both directions. A difference is not an error --
    # the two extent sources are allowed to disagree -- but every differing
    # region must be NAMED, because an unexplained one means an extent moved.
    reconciliation: dict[str, Any] = {"available": False}
    if GATE_PATH.is_file():
        gate = json.loads(GATE_PATH.read_bytes())
        image_id = gate["scope"]["image"]
        row = next((r for r in images if r["id"] == image_id), None)
        partition_block = gate["image_partition"]
        if row is not None:
            gate_gaps = {(parse_int(g["start"]), parse_int(g["end"]))
                         for g in partition_block["gaps"]}
            mine = {(parse_int(g["start"]), parse_int(g["end"])) for g in row["gaps"]}
            # ⚠️ Endpoints are not identity. Two different images can occupy the
            # same load range, and comparing only the range would let a changed
            # image reconcile as "the same universe" -- the gap sets would then
            # differ for a reason nobody could attribute. The gate pins the
            # sha256 of the image it probed; require it to be the same file.
            gate_inputs = gate.get("inputs") or {}
            gate_image_path = (gate_inputs.get("paths") or {}).get("image")
            gate_image_sha = (gate_inputs.get("sha256") or {}).get(gate_image_path)
            same_range = (
                parse_int(partition_block["load_base"]) == parse_int(row["resident_start"])
                and parse_int(partition_block["text_end"]) == parse_int(row["resident_end"]))
            same_identity = bool(gate_image_sha) and gate_image_sha == row["sha256"]
            same_universe = bool(same_range and same_identity)
            reconciliation = {
                "available": True,
                "gate_receipt": "analysis/phase4_static_asm_prerequisites.json",
                "gate_receipt_sha256": sha256_bytes(GATE_PATH.read_bytes()),
                "image": image_id,
                "same_resident_universe": same_universe,
                "same_resident_range": same_range,
                "same_image_identity": same_identity,
                "gate_image_path": gate_image_path,
                "gate_image_sha256": gate_image_sha,
                "census_image_sha256": row["sha256"],
                "gate_extent_source": "analysis/functions_resident_repaired.txt",
                "census_extent_source": "analysis/phase4_static_frontier_index.json",
                "reconciliation": "exact_set_both_directions",
                "identical_gaps": len(mine & gate_gaps),
                "census_only_gaps": [
                    {"start": hex32(a), "end": hex32(b), "byte_count": b - a}
                    for a, b in sorted(mine - gate_gaps)],
                "gate_only_gaps": [
                    {"start": hex32(a), "end": hex32(b), "byte_count": b - a}
                    for a, b in sorted(gate_gaps - mine)],
                "meaning": (
                    "Two independently built partitions of the same resident range "
                    "OF THE SAME IMAGE FILE -- range endpoints and sha256 both "
                    "checked, because equal endpoints alone would let a changed "
                    "image reconcile. Every differing region is attributable to the "
                    "extent source and none to the universe."),
            }

    census_complete_images = [row["id"] for row in images if row["census_complete"]]
    return {
        "schema": SCHEMA,
        "inputs": {
            "static_index": "analysis/phase4_static_frontier_index.json",
            "static_index_sha256": index_sha,
            "probe_source": "tools/phase4_callback_probe.c",
            "probe_source_sha256": sha256_bytes(PROBE_SOURCE.read_bytes()),
            "f01_static_hard_truth": str(F01_HARD_TRUTH_PATH.relative_to(ROOT)),
            "f01_static_hard_truth_sha256": sha256_bytes(
                F01_HARD_TRUTH_PATH.read_bytes()),
            "f01_gap_semantics": str(GAP_SEMANTICS_PATH.relative_to(ROOT)),
            "f01_gap_semantics_sha256": sha256_bytes(
                GAP_SEMANTICS_PATH.read_bytes()),
            # The compiler identity is deliberately NOT recorded.  It would make
            # the receipt reproduce only on one toolchain, and what has to be
            # pinned is the source the probe was built from.
            "windows": [{"start": hex32(a), "end": hex32(b)} for a, b in windows],
            "gp": hex32(GP_VALUE),
        },
        "function_pointer_census": {
            "universe": ("every aligned word of every hash-verified image; a code "
                         "address materialised by an ADJACENT lui/addiu or lui/ori "
                         "pair, tracked only within a basic block and only across "
                         "a delay slot"),
            "completeness": "positive_only",
            "silence_is_not_evidence": True,
            "materialisations_in_code_extents": len(pointers),
            "function_pointer_sites": len(entry_rows),
            "by_consumer": dict(sorted(consumers.items())),
            "distinct_target_functions": len(
                {(row["target_image"], row["target_function"]) for row in entry_rows}),
            # ⚠️ The signal that this probe finds FUNCTION POINTERS rather than
            # arbitrary constants is measured over the UNFILTERED population --
            # every materialisation landing anywhere inside a code extent -- and
            # is the fraction of them landing exactly on a function ENTRY. Noise
            # lands at random offsets. Stating it over the kept rows instead
            # would be vacuous: that set is DEFINED by the property.
            "entry_landing_rate_over_all_code_extent_materialisations": {
                "landed_on_an_entry": len(entry_rows),
                "landed_in_a_code_extent": len(pointers),
                "note": ("the denominator is every materialisation inside a code "
                         "extent, not the kept subset"),
            },
            "registration_groups": [slots[key] for key in sorted(slots)],
            "sites": sorted(entry_rows, key=lambda row: (row["image"],
                                                         row["materialised_at"],
                                                         row["consumer_pc"])),
            "excluded_interior_code_addresses": sorted(
                interior_rows, key=lambda row: (row["image"],
                                                row["materialised_at"],
                                                row["consumer_pc"])),
        },
        "image_census": {
            "universe": "every byte of every image the static index pins",
            "completeness": "census",
            "universe_note": (
                "The partition and the gap sweep run over the RESIDENT range only. "
                "A pinned image FILE is not the set of bytes the console loads: a "
                "PS-X EXE carries a 2,048-byte header and every level overlay a "
                "4-byte one. Those bytes are file metadata and are reported as "
                "nonresident_prefix_bytes, NOT as an unclassified gap -- calling "
                "them unclassified would be an error of kind, since unclassified "
                "means `resident bytes nobody has owned`."),
            "census_complete_means": (
                "every RESIDENT byte of the image is claimed by an indexed extent "
                "or falls in an enumerated gap; every INSTRUCTION-SHAPED WORD "
                "decoded inside those gaps has a proved base; and none of them "
                "reaches a declared window. It does NOT mean the accesses INSIDE "
                "the extents are all resolved -- that is mechanical completeness "
                "-- and it does NOT assert semantic ownership of any byte."),
            "instruction_shaped_word_caveat": (
                "A word inside an unclaimed region whose ENCODING is a load or "
                "store is not a confirmed memory reference. Nothing here shows it "
                "is executed, and no direct branch, jump or call edge from "
                "reachable code enters any gap in any image. The prior question "
                "is who OWNS the region, which is why gap_ownership is recorded "
                "per gap with its evidence class and why this count is named for "
                "the encoding rather than for a reference."),
            "ownership_classes": {
                "not_directly_reachable": (
                    "no direct edge from reachable code enters the region. "
                    "NECESSARY BUT NOT SUFFICIENT -- an undecoded indirect jump "
                    "could still land here, so this alone never owns a region."),
                "zero_filled": "measured: every byte is 0x00",
                "decoded_jump_table": "overlaps a table decoded by tools/phase3_jr_tables.py",
                "read_as_data": (
                    "statically resolved accesses from analysed code land inside "
                    "it; the covered-WORD count ships beside the region size so "
                    "partial coverage is never read as whole-region ownership"),
                "content_verified_trigonometric_table": (
                    "the complete mathematical table byte-compares with zero "
                    "mismatches AND a C instruction proof resolves the named "
                    "readers' bounded effective-address ranges into this exact "
                    "pre-existing gap. Either fact alone is insufficient; the "
                    "class never widens an extent"),
                "content_verified_trig_tail": (
                    "the tail of the ALREADY content-verified sine table "
                    "overlapping a third gap: the established formula is "
                    "re-derived over the overlap by the gap-semantics probe "
                    "with zero mismatches, clipped to the current gap"),
                "reader_indexed_atan_table": (
                    "the atan lookup table of atan2_heading: base, entry "
                    "width and index domain 0..1024 are INSTRUCTION-derived "
                    "(all twelve indexing/fold words verified by the "
                    "gap-semantics probe). Its analytic content model is "
                    "APPROXIMATE -- a fixed 189-entry subset sits exactly +1 "
                    "over llround(atan), generator unknown -- so this class "
                    "is one tier below content_verified and says so"),
                "function_entry_pointer_run": (
                    "a run of >= 3 consecutive aligned words, each exactly a "
                    "census code/thunk entry of the resident image; the "
                    "false-positive model (~1e-8 per run) is stated in the "
                    "gap-semantics receipt. STRUCTURAL evidence: it "
                    "identifies a pointer table without naming its consumer"),
                "targeted_by_a_proved_indirect_jump": (
                    "a jr site whose target set the shared gate proved complete "
                    "lands inside it -- 4 bytes, since it proves an instruction "
                    "STARTS there and nothing about how far the island runs"),
                "decoded_target_root_island": (
                    "the index decoded an executable island from that proved "
                    "target with an explicit stopping proof, without widening "
                    "any neighbouring extent. Since 2026-08-06 every decoded "
                    "island is ALSO a first-class census record, so its bytes "
                    "are claimed and this class is expected empty; a non-empty "
                    "value would mean an island overlaps an unclaimed gap, "
                    "which is a defect to investigate, not evidence"),
            },
            "disposition_means": {
                "none": "no evidence class covers any byte of the gap",
                "partial": "some bytes are covered and some are not -- this is "
                           "NOT an owned gap and must never be counted as one",
                "complete": "every byte is covered by at least one class",
            },
            "comparable_universe": (
                "analysis/phase4_static_asm_prerequisites.json partitions the same "
                "resident loaded-text range for SCUS_942_88 (0x80010000..0x80082800, "
                "468,992 bytes) but against REPAIRED extents rather than static "
                "index records, so the two gap totals are comparable and any "
                "difference is attributable to the extent source rather than to the "
                "universe."),
            "images": images,
            "resident_partition_reconciliation": reconciliation,
            "census_complete_images": census_complete_images,
            "census_incomplete_images": [row["id"] for row in images
                                         if not row["census_complete"]],
            "total_gap_bytes": sum(row["gap_bytes"] for row in images),
            "total_instruction_shaped_words_in_gaps": sum(
                row["instruction_shaped_words_in_gaps"] for row in images),
            "total_instruction_shaped_words_with_an_unprovable_base": sum(
                row["instruction_shaped_words_with_an_unprovable_base"] for row in images),
            "gap_ownership_evidence": ownership_meta,
            # ⚠️ BYTE-EXACT, never a whole-gap boolean. A gap that carries some
            # evidence is not an owned gap: the 13,536-byte region below has
            # evidence for a few hundred of its 13,536 bytes.
            "gap_count": sum(1 for _ in ownership),
            "gap_bytes_with_any_evidence": sum(
                row["bytes_with_any_evidence"] for row in ownership.values()),
            "gap_bytes_with_semantic_evidence": sum(
                row["bytes_with_semantic_evidence"] for row in ownership.values()),
            "gap_bytes_with_no_evidence": sum(
                row["bytes_with_no_evidence"] for row in ownership.values()),
            "gaps_by_disposition": {
                name: sum(1 for row in ownership.values()
                          if row["disposition"] == name)
                for name in ("none", "partial", "complete")},
            "gap_bytes_by_disposition": {
                name: sum(row["byte_count"] for row in ownership.values()
                          if row["disposition"] == name)
                for name in ("none", "partial", "complete")},
            "gap_bytes_by_class": {
                name: sum(row["bytes_by_class"].get(name, 0)
                          for row in ownership.values())
                for name in sorted({key for row in ownership.values()
                                    for key in row["bytes_by_class"]})},
            "classes_overlap": (
                "byte intervals from different classes intersect, so the "
                "per-class totals are NOT exclusive buckets and must not be "
                "summed; gap_bytes_with_any_evidence is the union"),
            "largest_unevidenced_ranges": sorted(
                ({"image": row["image"], **span}
                 for row in ownership.values() for span in row["unevidenced_ranges"]),
                key=lambda span: -span["byte_count"])[:12],
        },
        "verdicts": {
            "all_images_census_complete": len(census_complete_images) == len(images),
            "function_pointer_census_complete": False,
            "window_reaching_gap_references": len(falsifiers),
            # ⚠️ The zero above is a bounded negative over the DECIDABLE part of
            # the gap sweep. It travels with its denominator on purpose: a gap
            # reference whose base could not be proved is not evidence of a miss,
            # and quoting the zero without this number would read as a clean
            # sweep of every byte.
            "instruction_shaped_gap_words_with_an_unprovable_base": sum(
                row["instruction_shaped_words_with_an_unprovable_base"]
                for row in images),
            "instruction_shaped_gap_words_total": sum(
                row["instruction_shaped_words_in_gaps"] for row in images),
            "gaps_entered_by_a_direct_boundary_edge": sum(
                1 for row in ownership.values()
                if row["incoming_boundary_edge_count"]),
            "boundary_edges_into_gaps": sum(
                row["incoming_boundary_edge_count"] for row in ownership.values()),
            "named_falsifier_found": bool(falsifiers),
        },
        "falsifiers": falsifiers,
        "authority": {
            "changes_campaign_registry": False,
            "promotes_dimension": False,
            "closes_item_2": False,
            "widens_the_direct_static_writer_census": False,
        },
    }


def render(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true",
                        help="require the retained receipt to equal regenerated bytes")
    args = parser.parse_args()
    if ROOT not in args.output.resolve().parents:
        raise CensusError("output must stay inside the repository")
    payload = render(compile_census(DEFAULT_WINDOWS))
    if args.check:
        if not args.output.is_file():
            raise CensusError(f"retained receipt missing: {args.output}")
        if args.output.read_bytes() != payload:
            raise CensusError(f"retained receipt is stale: {args.output}")
        print(f"[phase4-frontier-static-census] {args.output}: fresh")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    document = json.loads(payload)
    print(f"[phase4-frontier-static-census] wrote {args.output}")
    fpc = document["function_pointer_census"]
    print(f"  function pointers {fpc['function_pointer_sites']} "
          f"({fpc['by_consumer']}) | groups {len(fpc['registration_groups'])} | "
          f"excluded interior addresses {len(fpc['excluded_interior_code_addresses'])}")
    census = document["image_census"]
    print(f"  images census-complete {len(census['census_complete_images'])}"
          f"/{len(census['images'])} | gap bytes {census['total_gap_bytes']} | "
          "instruction-shaped gap words without a proved base "
          f"{census['total_instruction_shaped_words_with_an_unprovable_base']}")
    print(f"  gaps by disposition {census['gaps_by_disposition']} | "
          f"bytes {census['gap_bytes_by_disposition']}")
    print(f"  gap bytes: {census['gap_bytes_with_any_evidence']} evidenced "
          f"({census['gap_bytes_with_semantic_evidence']} semantically) | "
          f"{census['gap_bytes_with_no_evidence']} with NO evidence")
    print(f"  boundary edges into gaps "
          f"{document['verdicts']['boundary_edges_into_gaps']} across "
          f"{document['verdicts']['gaps_entered_by_a_direct_boundary_edge']} gaps "
          f"| kinds {census['gap_ownership_evidence']['boundary_edges_into_gaps_by_kind']}")
    print(f"  window-reaching gap words "
          f"{document['verdicts']['window_reaching_gap_references']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CensusError as exc:
        raise SystemExit(f"[phase4-frontier-static-census] ERROR: {exc}") from exc
