#!/usr/bin/env python3
"""Unified non-mutating catalog for DAT type-0x3f placement entries.

Phase: Option C Phase 1. This tool reads LEVEL*.DAT files, decodes type-0x3f
entries, and writes catalog reports. It never writes DAT/BIN/CUE inputs.
"""

from __future__ import annotations

import argparse
import csv
import glob
import struct
from dataclasses import dataclass, field
from pathlib import Path


TYPE3F = 0x3F
ENTRY_SIZE = 0x10

CSV_COLUMNS = [
    "file",
    "top_level_dat_record_offset",
    "raw_entry_index",
    "entry_offset",
    "x",
    "y",
    "z",
    "source_kind",
    "decoded_identity",
    "movement_safe_status",
    "known_warnings",
    "runtime_x",
    "runtime_y",
    "runtime_z",
    "notes",
]

LEVEL01_EXPECTED = {
    **{i: 0x14 for i in range(0, 50)},
    50: 0x10,
    51: 0x11,
    52: 0x12,
    53: 0x13,
    54: 0x22,
    55: 0x23,
    56: 0x21,
    57: 0x24,
    58: 0x2B,
    59: 0x2B,
    60: 0x2A,
    61: 0x2A,
    62: 0x2B,
    63: 0x29,
    64: 0x29,
    65: 0x29,
    66: 0x2A,
    67: 0x30,
    68: 0x30,
    69: 0x30,
}

LEVEL01_IDENTITIES = {
    0x10: "FLIK F",
    0x11: "FLIK L",
    0x12: "FLIK I",
    0x13: "FLIK K",
    0x14: "grain",
    0x21: "Green Berry / Homing Berry",
    0x22: "Gold Berry",
    0x23: "Blueberry / Superberry",
    0x24: "Purple Berry / Mega-Homing Berry",
    0x29: "orange/red seed token",
    0x2A: "blue seed token",
    0x2B: "green seed token",
    0x30: "Dewdrop telescope / hint-view trigger",
}

GENERIC_KIND_IDENTITIES = {
    0x10: "FLIK F (source-kind decode)",
    0x11: "FLIK L (source-kind decode)",
    0x12: "FLIK I (source-kind decode)",
    0x13: "FLIK K (source-kind decode)",
    0x14: "grain (source-kind decode)",
    0x21: "Green/Homing berry (source-kind decode)",
    0x22: "Gold berry (source-kind decode)",
    0x23: "Blue/Super berry (source-kind decode)",
    0x24: "Purple/Mega-Homing berry (source-kind decode)",
    0x29: "orange/red seed token (source-kind decode)",
    0x2A: "blue seed token (source-kind decode)",
    0x2B: "green seed token (source-kind decode)",
    0x2C: "token-like extra seed action (not production-tested in LEVEL01)",
    0x2D: "token-like extra seed action (not production-tested in LEVEL01)",
    0x30: "Dewdrop telescope / hint-view trigger",
}


@dataclass(frozen=True)
class Type3FRow:
    file: str
    top_level_dat_record_offset: int
    raw_entry_index: int
    entry_offset: int
    x: int
    y: int
    z: int
    source_kind: int
    decoded_identity: str
    movement_safe_status: str
    known_warnings: str
    runtime_x: int
    runtime_y: int
    runtime_z: int
    notes: str


@dataclass
class FileSummary:
    path: Path
    type3f_offsets: list[int] = field(default_factory=list)
    type3f_counts: list[int] = field(default_factory=list)
    rows: list[Type3FRow] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parse_error: str | None = None


def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def dat_record_size(data: bytes, off: int) -> int:
    count = s16(data, off)
    rec_type = s16(data, off + 2)
    if rec_type < 0:
        words = ((count * 3 + 1) + ((count * 3 + 1) >> 31)) >> 1
        return words * 4 + 0x10
    if rec_type == TYPE3F:
        return (count << 4) + 4
    return ((count * 3) << 2) + 4


def iter_dat_records(data: bytes):
    if len(data) < 4:
        raise ValueError("DAT is too small")
    total = struct.unpack_from("<i", data, 0)[0]
    if total < 0:
        raise ValueError(f"negative top-level record count: {total}")
    off = 4
    for ordinal in range(total):
        if off + 4 > len(data):
            raise ValueError(f"record {ordinal} header is outside the file")
        count = u16(data, off)
        rec_type = s16(data, off + 2)
        size = dat_record_size(data, off)
        if size < 4:
            raise ValueError(f"record {ordinal} has invalid size {size:#x}")
        if off + size > len(data):
            raise ValueError(
                f"record {ordinal} type {rec_type:#x} at {off:#x} overruns file"
            )
        yield ordinal, off, count, rec_type, size
        off += size


def is_level01_pristine_basename(path: Path) -> bool:
    return path.name == "LEVEL01_LEVEL.DAT"


def decode_entry(path: Path, index: int, kind: int) -> tuple[str, str, list[str], str]:
    warnings: list[str] = []
    notes: list[str] = []

    if is_level01_pristine_basename(path):
        identity = LEVEL01_IDENTITIES.get(kind, f"UNKNOWN kind 0x{kind:02x}")
        expected = LEVEL01_EXPECTED.get(index)
        if expected is None:
            warnings.append("LEVEL01 extra/appended entry; not in confirmed 0..69 map")
        elif expected != kind:
            warnings.append(
                f"LEVEL01 map mismatch: expected kind 0x{expected:02x} at entry {index}"
            )
        else:
            notes.append("LEVEL01 confirmed map")
    else:
        identity = GENERIC_KIND_IDENTITIES.get(kind, f"UNKNOWN kind 0x{kind:02x}")
        if kind in GENERIC_KIND_IDENTITIES:
            notes.append("decoded by source kind; level-specific identity unverified")

    if kind == 0x14:
        movement = "coordinate-safe; preserve kind"
    elif kind in {0x10, 0x11, 0x12, 0x13}:
        movement = "coordinate-safe; preserve FLIK kind"
    elif kind in {0x21, 0x22, 0x23, 0x24}:
        movement = "coordinate-safe; real berry; preserve kind"
        warnings.append("real berry/power-up; do not repurpose as sacrifice slot")
    elif kind in {0x29, 0x2A, 0x2B}:
        movement = "coordinate-safe; preserve token kind"
    elif kind in {0x2C, 0x2D}:
        movement = "caution; token-like but not LEVEL01 production-tested"
        warnings.append("token-like handler exists; not production-tested in LEVEL01")
    elif kind == 0x30:
        movement = "caution; telescope target/activation semantics not fully proven"
        warnings.append("telescope/hint-view trigger; moving it may desynchronize its authored camera target")
    else:
        movement = "UNKNOWN; do not move for production without evidence"
        warnings.append("unknown source kind")

    return identity, movement, warnings, "; ".join(notes)


def analyze_file(path: Path) -> FileSummary:
    summary = FileSummary(path=path)
    data = path.read_bytes()
    kinds_seen: set[int] = set()

    for _ordinal, rec_off, count, rec_type, _size in iter_dat_records(data):
        if rec_type != TYPE3F:
            continue
        summary.type3f_offsets.append(rec_off)
        summary.type3f_counts.append(count)
        if not is_level01_pristine_basename(path) and count != 70:
            summary.warnings.append(
                f"type-0x3f count {count} differs from LEVEL01 baseline 70; review level-specific expectations"
            )
        entry_base = rec_off + 4
        for raw_index in range(count):
            entry_off = entry_base + raw_index * ENTRY_SIZE
            x = s32(data, entry_off)
            y = s32(data, entry_off + 4)
            z = s32(data, entry_off + 8)
            kind = data[entry_off + 0x0C]
            kinds_seen.add(kind)
            identity, movement, warnings, notes = decode_entry(path, raw_index, kind)
            summary.rows.append(
                Type3FRow(
                    file=str(path),
                    top_level_dat_record_offset=rec_off,
                    raw_entry_index=raw_index,
                    entry_offset=entry_off,
                    x=x,
                    y=y,
                    z=z,
                    source_kind=kind,
                    decoded_identity=identity,
                    movement_safe_status=movement,
                    known_warnings="; ".join(warnings) if warnings else "",
                    runtime_x=x << 5,
                    runtime_y=y << 5,
                    runtime_z=z << 5,
                    notes=notes,
                )
            )

    if not summary.type3f_offsets:
        summary.warnings.append("no type-0x3f record")
    if len(summary.type3f_offsets) > 1:
        offsets = ", ".join(f"0x{off:06x}" for off in summary.type3f_offsets)
        summary.warnings.append(f"multiple type-0x3f records: {offsets}")
    unknown_kinds = sorted(k for k in kinds_seen if k not in GENERIC_KIND_IDENTITIES)
    if unknown_kinds:
        summary.warnings.append(
            "unknown source kinds: " + ", ".join(f"0x{k:02x}" for k in unknown_kinds)
        )
    cautious_kinds = sorted(kinds_seen & {0x2C, 0x2D, 0x30})
    if cautious_kinds:
        summary.warnings.append(
            "caution source kinds present: " + ", ".join(f"0x{k:02x}" for k in cautious_kinds)
        )
    berry_kinds = sorted(kinds_seen & {0x21, 0x22, 0x23, 0x24})
    if berry_kinds:
        summary.warnings.append(
            "real berry/source-power kinds present; preserve kind: "
            + ", ".join(f"0x{k:02x}" for k in berry_kinds)
        )
    if is_level01_pristine_basename(path):
        validate_level01(summary)
    return summary


def validate_level01(summary: FileSummary) -> None:
    if len(summary.type3f_counts) != 1:
        summary.warnings.append("LEVEL01 validation requires exactly one type-0x3f record")
        return
    if summary.type3f_offsets[0] != 0x4:
        summary.warnings.append(
            f"LEVEL01 type-0x3f offset mismatch: got 0x{summary.type3f_offsets[0]:x}, expected 0x4"
        )
    if summary.type3f_counts[0] != 70:
        summary.warnings.append(
            f"LEVEL01 type-0x3f count mismatch: got {summary.type3f_counts[0]}, expected 70"
        )
    rows_by_index = {row.raw_entry_index: row for row in summary.rows}
    for index, expected_kind in LEVEL01_EXPECTED.items():
        row = rows_by_index.get(index)
        if row is None:
            summary.warnings.append(f"LEVEL01 missing expected entry {index}")
        elif row.source_kind != expected_kind:
            summary.warnings.append(
                f"LEVEL01 entry {index} kind mismatch: got 0x{row.source_kind:02x}, expected 0x{expected_kind:02x}"
            )
    extra = sorted(set(rows_by_index) - set(LEVEL01_EXPECTED))
    if extra:
        summary.warnings.append(f"LEVEL01 has entries beyond confirmed map: {extra}")


def expand_paths(args: list[str]) -> list[Path]:
    paths: list[Path] = []
    for arg in args:
        matches = [Path(match) for match in glob.glob(arg)]
        paths.extend(matches if matches else [Path(arg)])
    return sorted(dict.fromkeys(paths))


def hex_offset(value: int) -> str:
    return f"0x{value:06x}"


def row_to_csv(row: Type3FRow) -> dict[str, str | int]:
    out: dict[str, str | int] = {}
    for column in CSV_COLUMNS:
        value = getattr(row, column)
        if column.endswith("offset"):
            out[column] = hex_offset(value)
        elif column == "source_kind":
            out[column] = f"0x{value:02x}"
        else:
            out[column] = value
    return out


def write_csv(path: Path, summaries: list[FileSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for summary in summaries:
            for row in summary.rows:
                writer.writerow(row_to_csv(row))


def write_markdown(path: Path, summaries: list[FileSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Type-0x3f Object Catalog",
        "",
        "Generated by `tools/catalog_type3f.py`. This is a non-mutating catalog.",
        "",
        "## Summary",
        "",
        "| file | type-0x3f offsets | entry counts | entries cataloged | warnings |",
        "|---|---:|---:|---:|---|",
    ]
    for summary in summaries:
        offsets = ", ".join(f"`{hex_offset(off)}`" for off in summary.type3f_offsets) or "-"
        counts = ", ".join(str(count) for count in summary.type3f_counts) or "-"
        warnings = "; ".join(summary.warnings) or "-"
        if summary.parse_error:
            warnings = f"parse failure: {summary.parse_error}"
        lines.append(
            f"| `{summary.path}` | {offsets} | {counts} | {len(summary.rows)} | {warnings} |"
        )

    lines.extend(["", "## LEVEL01 Validation", ""])
    level01 = [s for s in summaries if is_level01_pristine_basename(s.path)]
    if not level01:
        lines.append("`DAT/LEVEL01_LEVEL.DAT` was not included in this run.")
    else:
        s = level01[0]
        validation_warnings = [
            warning for warning in s.warnings if warning.startswith("LEVEL01")
        ]
        catalog_cautions = [
            warning for warning in s.warnings if not warning.startswith("LEVEL01")
        ]
        if validation_warnings:
            lines.append("LEVEL01 confirmed-map validation failed:")
            lines.extend(f"- {warning}" for warning in validation_warnings)
        else:
            lines.append("LEVEL01 confirmed-map validation passed against the 70-entry map.")
        if catalog_cautions:
            lines.extend(["", "Catalog cautions for LEVEL01:"])
            lines.extend(f"- {warning}" for warning in catalog_cautions)

    lines.extend(
        [
            "",
            "## Stale-Doc Warnings Carried Forward",
            "",
            "- `docs/DAT_FORMAT_AND_RELOCATION.md` still contains an older \"awaiting in-game result\" append note before the later confirmed append section.",
            "- `docs/COORDINATE_MODDING.md` still contains an older note that FLIK letter spawn coords are not mapped, superseded by later FLIK mapping and phase outputs.",
            "",
            "## Entries",
            "",
        ]
    )

    for summary in summaries:
        lines.extend(
            [
                f"### `{summary.path}`",
                "",
                "| raw | off | kind | identity | X | Y | Z | runtime X | runtime Y | runtime Z | movement | warnings |",
                "|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
            ]
        )
        if not summary.rows:
            lines.extend(["| - | - | - | no type-0x3f entries | - | - | - | - | - | - | - | - |", ""])
            continue
        for row in summary.rows:
            warnings = row.known_warnings or "-"
            lines.append(
                f"| {row.raw_entry_index} | `{hex_offset(row.entry_offset)}` | "
                f"`0x{row.source_kind:02x}` | {row.decoded_identity} | "
                f"{row.x} | {row.y} | {row.z} | "
                f"{row.runtime_x} | {row.runtime_y} | {row.runtime_z} | "
                f"{row.movement_safe_status} | {warnings} |"
            )
        lines.append("")

    path.write_text("\n".join(lines) + "\n")


def print_summary(summaries: list[FileSummary]) -> None:
    print("file,type3f_offsets,type3f_counts,entries,warnings")
    for summary in summaries:
        offsets = ";".join(hex_offset(off) for off in summary.type3f_offsets) or "-"
        counts = ";".join(str(count) for count in summary.type3f_counts) or "-"
        warnings = "; ".join(summary.warnings) or "none"
        if summary.parse_error:
            warnings = f"parse failure: {summary.parse_error}"
        print(f"{summary.path},{offsets},{counts},{len(summary.rows)},{warnings}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catalog type-0x3f placement entries without mutating DAT files."
    )
    parser.add_argument("dat", nargs="*", help="DAT paths or glob patterns")
    parser.add_argument("--csv", type=Path, default=Path("DAT/type3f_catalog.csv"))
    parser.add_argument("--md", type=Path, default=Path("DAT/type3f_catalog.md"))
    parser.add_argument(
        "--format",
        choices=("summary", "none"),
        default="summary",
        help="stdout format; reports are still written unless --no-write is used",
    )
    parser.add_argument("--no-write", action="store_true", help="do not write CSV/Markdown reports")
    parser.add_argument(
        "--validate-level01",
        action="store_true",
        help="fail if DAT/LEVEL01_LEVEL.DAT is included and does not match the confirmed map",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = expand_paths(args.dat or ["DAT/LEVEL*_LEVEL*.DAT"])
    if not paths:
        raise SystemExit("no DAT files matched")

    summaries: list[FileSummary] = []
    for path in paths:
        try:
            summaries.append(analyze_file(path))
        except Exception as exc:  # noqa: BLE001 - keep cataloging other files.
            summaries.append(FileSummary(path=path, parse_error=str(exc)))

    if not args.no_write:
        write_csv(args.csv, summaries)
        write_markdown(args.md, summaries)
        print(f"csv: {args.csv}")
        print(f"markdown: {args.md}")

    if args.format == "summary":
        print_summary(summaries)

    if args.validate_level01:
        failures = []
        for summary in summaries:
            if not is_level01_pristine_basename(summary.path):
                continue
            if summary.parse_error:
                failures.append(f"parse failure: {summary.parse_error}")
            failures.extend(
                warning for warning in summary.warnings if warning.startswith("LEVEL01")
            )
        if failures:
            print("LEVEL01 validation failed:")
            for failure in failures:
                print(f"  {failure}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
