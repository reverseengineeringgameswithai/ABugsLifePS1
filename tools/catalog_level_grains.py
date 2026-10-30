#!/usr/bin/env python3
"""Build CSV and Markdown catalogs of source-kind 0x14 grain entries."""

from __future__ import annotations

import argparse
import csv
import glob
import struct
from dataclasses import dataclass, field
from pathlib import Path


CSV_COLUMNS = [
    "file",
    "dat_record_offset",
    "grain_index",
    "raw_entry_index",
    "entry_offset",
    "y_offset",
    "x",
    "y",
    "z",
    "source_kind",
    "orig_y_bytes",
    "patch_y_minus_0x40_bytes",
]


@dataclass(frozen=True)
class GrainRow:
    file: str
    dat_record_offset: int
    grain_index: int
    raw_entry_index: int
    entry_offset: int
    y_offset: int
    x: int
    y: int
    z: int
    source_kind: int
    orig_y_bytes: bytes
    patch_y_minus_0x40_bytes: bytes


@dataclass
class FileSummary:
    path: Path
    rows: list[GrainRow] = field(default_factory=list)
    type3f_offsets: list[int] = field(default_factory=list)
    type3f_counts: list[int] = field(default_factory=list)
    source_kinds: set[int] = field(default_factory=set)
    anomalies: list[str] = field(default_factory=list)


def s16(data: bytes, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def pack_s32(value: int) -> bytes:
    return struct.pack("<i", value)


def dat_record_size(data: bytes, off: int) -> int:
    count = s16(data, off)
    rec_type = s16(data, off + 2)
    if rec_type < 0:
        words = ((count * 3 + 1) + ((count * 3 + 1) >> 31)) >> 1
        return words * 4 + 0x10
    if rec_type == 0x3F:
        return (count << 4) + 4
    return ((count * 3) << 2) + 4


def iter_dat_records(data: bytes):
    if len(data) < 4:
        raise ValueError("DAT is too small")
    total = struct.unpack_from("<i", data, 0)[0]
    off = 4
    for ordinal in range(total):
        if off + 4 > len(data):
            raise ValueError(f"record {ordinal} header is outside the file")
        count = u16(data, off)
        rec_type = s16(data, off + 2)
        size = dat_record_size(data, off)
        if off + size > len(data):
            raise ValueError(
                f"record {ordinal} type {rec_type:#x} at {off:#x} overruns file"
            )
        yield ordinal, off, count, rec_type, size
        off += size


def analyze_file(path: Path) -> FileSummary:
    summary = FileSummary(path=path)
    data = path.read_bytes()

    for _ordinal, rec_off, count, rec_type, _size in iter_dat_records(data):
        if rec_type != 0x3F:
            continue
        summary.type3f_offsets.append(rec_off)
        summary.type3f_counts.append(count)
        for raw_index in range(count):
            entry_offset = rec_off + 4 + raw_index * 0x10
            kind = data[entry_offset + 0x0C]
            summary.source_kinds.add(kind)
            if kind != 0x14:
                continue
            y_offset = entry_offset + 4
            y = s32(data, y_offset)
            summary.rows.append(
                GrainRow(
                    file=str(path),
                    dat_record_offset=rec_off,
                    grain_index=len(summary.rows),
                    raw_entry_index=raw_index,
                    entry_offset=entry_offset,
                    y_offset=y_offset,
                    x=s32(data, entry_offset),
                    y=y,
                    z=s32(data, entry_offset + 8),
                    source_kind=kind,
                    orig_y_bytes=data[y_offset : y_offset + 4],
                    patch_y_minus_0x40_bytes=pack_s32(y - 0x40),
                )
            )

    if not summary.type3f_offsets:
        summary.anomalies.append("no type-0x3f record")
    if len(summary.type3f_offsets) > 1:
        offsets = ", ".join(f"0x{off:06x}" for off in summary.type3f_offsets)
        summary.anomalies.append(f"multiple type-0x3f records: {offsets}")
    if summary.rows and len(summary.rows) != 50:
        summary.anomalies.append(f"source-kind 0x14 count is {len(summary.rows)}, expected 50")
    if summary.source_kinds - {0x14}:
        kinds = ", ".join(f"0x{kind:02x}" for kind in sorted(summary.source_kinds - {0x14}))
        summary.anomalies.append(f"non-0x14 source kinds in type-0x3f: {kinds}")
    return summary


def csv_value(row: GrainRow, key: str) -> str | int:
    value = getattr(row, key)
    if key.endswith("offset"):
        return f"0x{value:06x}"
    if key == "source_kind":
        return f"0x{value:02x}"
    if isinstance(value, bytes):
        return value.hex(" ")
    return value


def write_csv(path: Path, summaries: list[FileSummary]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for summary in summaries:
            for row in summary.rows:
                writer.writerow({key: csv_value(row, key) for key in CSV_COLUMNS})


def write_markdown(path: Path, summaries: list[FileSummary]) -> None:
    lines = [
        "# Grain Coordinate Catalog",
        "",
        "Source-kind `0x14` entries from type-`0x3f` DAT records.",
        "",
        "## Summary",
        "",
        "| file | type-0x3f offsets | grain count | count is 50 | anomalies |",
        "|---|---:|---:|---|---|",
    ]
    for summary in summaries:
        offsets = ", ".join(f"`0x{off:06x}`" for off in summary.type3f_offsets) or "-"
        anomalies = "; ".join(summary.anomalies) or "-"
        lines.append(
            f"| `{summary.path}` | {offsets} | {len(summary.rows)} | "
            f"{'yes' if len(summary.rows) == 50 else 'no'} | {anomalies} |"
        )

    lines.extend(["", "## First Five Grains Per File", ""])
    for summary in summaries:
        lines.extend(
            [
                f"### `{summary.path}`",
                "",
                f"- grain count: {len(summary.rows)}",
                f"- anomalies: {'; '.join(summary.anomalies) if summary.anomalies else 'none'}",
                "",
            ]
        )
        if not summary.rows:
            lines.extend(["No source-kind `0x14` grains found.", ""])
            continue
        lines.extend(
            [
                "| grain | raw entry | entry off | Y off | X | Y | Z | orig Y bytes | Y-0x40 bytes |",
                "|---:|---:|---:|---:|---:|---:|---:|---|---|",
            ]
        )
        for row in summary.rows[:5]:
            lines.append(
                f"| {row.grain_index} | {row.raw_entry_index} | "
                f"`0x{row.entry_offset:06x}` | `0x{row.y_offset:06x}` | "
                f"{row.x} | {row.y} | {row.z} | "
                f"`{row.orig_y_bytes.hex(' ')}` | "
                f"`{row.patch_y_minus_0x40_bytes.hex(' ')}` |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n")


def expand_paths(args: list[str]) -> list[Path]:
    paths: list[Path] = []
    for arg in args:
        matches = [Path(match) for match in glob.glob(arg)]
        paths.extend(matches if matches else [Path(arg)])
    return sorted(dict.fromkeys(paths))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catalog grain coordinates across LEVEL*.DAT files.")
    parser.add_argument("dat", nargs="*", help="DAT paths or globs")
    parser.add_argument("--csv", type=Path, default=Path("DAT/grain_coordinate_catalog.csv"))
    parser.add_argument("--md", type=Path, default=Path("DAT/grain_coordinate_catalog.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = expand_paths(args.dat or ["DAT/LEVEL*_LEVEL.DAT", "DAT/LEVEL*_LEVEL1.DAT"])
    if not paths:
        raise SystemExit("no DAT files matched")

    summaries: list[FileSummary] = []
    for path in paths:
        try:
            summaries.append(analyze_file(path))
        except Exception as exc:  # noqa: BLE001 - keep cataloging other files.
            summaries.append(FileSummary(path=path, anomalies=[f"parse failure: {exc}"]))

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.csv, summaries)
    write_markdown(args.md, summaries)

    print(f"csv: {args.csv}")
    print(f"markdown: {args.md}")
    print("file,grain_count,anomalies")
    for summary in summaries:
        anomalies = "; ".join(summary.anomalies) or "none"
        print(f"{summary.path},{len(summary.rows)},{anomalies}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
