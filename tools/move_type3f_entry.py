#!/usr/bin/env python3
"""Conservative fixed-size mover for existing DAT type-0x3f entries.

Phase: Option C Phase 2. This tool changes only existing entry X/Y/Z fields,
preserves source kind and unknown bytes, never appends, and never touches
relocation logic. It defaults to dry-run; use --write with --out to emit a copy.
"""

from __future__ import annotations

import argparse
import difflib
import struct
from dataclasses import dataclass
from pathlib import Path

from catalog_type3f import (
    TYPE3F,
    Type3FRow,
    analyze_file,
    s16,
    u16,
    dat_record_size,
)


AXES = (("x", 0), ("y", 4), ("z", 8))
RISK_TOKEN_LIKE = {0x2C, 0x2D}
RISK_TELESCOPE = {0x30}
RISK_UNKNOWN = {0x31}
KNOWN_SAFE = {
    0x10,
    0x11,
    0x12,
    0x13,
    0x14,
    0x21,
    0x22,
    0x23,
    0x24,
    0x29,
    0x2A,
    0x2B,
}


@dataclass(frozen=True)
class Move:
    row: Type3FRow
    old_xyz: tuple[int, int, int]
    new_xyz: tuple[int, int, int]
    old_entry: bytes
    new_entry: bytes


def s32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def pack_s32(value: int) -> bytes:
    if value < -0x80000000 or value > 0x7FFFFFFF:
        raise ValueError(f"s32 coordinate overflow: {value}")
    return struct.pack("<i", value)


def iter_records_for_validation(data: bytes):
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


def normalize_identity(value: str) -> str:
    out = []
    for ch in value.lower():
        if ch.isalnum():
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def parse_index_list(values: list[str]) -> list[int]:
    out: list[int] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            out.append(int(part, 0))
    return out


def select_rows(rows: list[Type3FRow], entries: list[int], identity: str | None) -> list[Type3FRow]:
    selected: list[Type3FRow] = []
    by_index = {row.raw_entry_index: row for row in rows}

    for entry in entries:
        row = by_index.get(entry)
        if row is None:
            raise SystemExit(f"entry {entry} is outside the cataloged type-0x3f entries")
        selected.append(row)

    if identity is not None:
        needle = normalize_identity(identity)
        matches = [
            row
            for row in rows
            if needle == normalize_identity(row.decoded_identity)
            or needle in normalize_identity(row.decoded_identity)
        ]
        if not matches:
            raise SystemExit(f"identity {identity!r} did not match any cataloged entry")
        if len(matches) != 1:
            choices = ", ".join(
                f"{row.raw_entry_index}: {row.decoded_identity}" for row in matches[:20]
            )
            more = "" if len(matches) <= 20 else f" ... +{len(matches)-20} more"
            raise SystemExit(
                f"identity {identity!r} is ambiguous ({len(matches)} matches): {choices}{more}"
            )
        selected.append(matches[0])

    deduped: dict[int, Type3FRow] = {}
    for row in selected:
        deduped[row.raw_entry_index] = row
    return [deduped[index] for index in sorted(deduped)]


def check_risk(row: Type3FRow, args: argparse.Namespace) -> None:
    kind = row.source_kind
    if kind in RISK_TELESCOPE and not args.allow_telescope:
        raise SystemExit(
            f"entry {row.raw_entry_index} kind 0x{kind:02x} is a telescope/hint-view trigger; "
            "use --allow-telescope to override"
        )
    if kind in RISK_TOKEN_LIKE and not args.allow_token_like:
        raise SystemExit(
            f"entry {row.raw_entry_index} kind 0x{kind:02x} is token-like but not production-tested; "
            "use --allow-token-like to override"
        )
    if (kind in RISK_UNKNOWN or kind not in KNOWN_SAFE | RISK_TOKEN_LIKE | RISK_TELESCOPE) and not args.allow_unknown:
        raise SystemExit(
            f"entry {row.raw_entry_index} kind 0x{kind:02x} is unknown/unsupported; "
            "use --allow-unknown to override"
        )


def build_moves(data: bytes, rows: list[Type3FRow], dx: int, dy: int, dz: int) -> tuple[bytes, list[Move]]:
    patched = bytearray(data)
    moves: list[Move] = []
    deltas = (dx, dy, dz)

    for row in rows:
        off = row.entry_offset
        old_entry = bytes(patched[off : off + 0x10])
        old_xyz = (s32(patched, off), s32(patched, off + 4), s32(patched, off + 8))
        new_xyz = tuple(old_xyz[i] + deltas[i] for i in range(3))
        for i, (_axis, axis_off) in enumerate(AXES):
            if deltas[i] != 0:
                patched[off + axis_off : off + axis_off + 4] = pack_s32(new_xyz[i])
        new_entry = bytes(patched[off : off + 0x10])
        moves.append(Move(row=row, old_xyz=old_xyz, new_xyz=new_xyz, old_entry=old_entry, new_entry=new_entry))

    return bytes(patched), moves


def verify_patch(original: bytes, patched: bytes, moves: list[Move], changed_axis_offsets: set[int]) -> None:
    if len(original) != len(patched):
        raise SystemExit("verification failed: output size changed")

    expected_changed: set[int] = set()
    for move in moves:
        for axis_off in changed_axis_offsets:
            expected_changed.update(range(move.row.entry_offset + axis_off, move.row.entry_offset + axis_off + 4))

    actual_changed = {i for i, (a, b) in enumerate(zip(original, patched)) if a != b}
    unexpected = sorted(actual_changed - expected_changed)
    if unexpected:
        missing = sorted(expected_changed - actual_changed)
        unexpected = sorted(actual_changed - expected_changed)
        raise SystemExit(
            "verification failed: changed-byte set mismatch; "
            f"unexpected={unexpected[:16]} missing={missing[:16]}"
        )

    for move in moves:
        off = move.row.entry_offset
        if original[off + 0x0C : off + 0x10] != patched[off + 0x0C : off + 0x10]:
            raise SystemExit(f"verification failed: entry {move.row.raw_entry_index} kind/unknown bytes changed")

    original_records = [(off, count, rec_type, size) for _ord, off, count, rec_type, size in iter_records_for_validation(original)]
    patched_records = [(off, count, rec_type, size) for _ord, off, count, rec_type, size in iter_records_for_validation(patched)]
    if original_records != patched_records:
        raise SystemExit("verification failed: DAT record structure changed")
    if not any(rec_type == TYPE3F for _off, _count, rec_type, _size in patched_records):
        raise SystemExit("verification failed: output has no type-0x3f record")


def format_move(move: Move, dx: int, dy: int, dz: int) -> str:
    row = move.row
    parts = [
        f"entry {row.raw_entry_index} @ 0x{row.entry_offset:06x}",
        f"kind 0x{row.source_kind:02x}",
        row.decoded_identity,
        f"old XYZ {move.old_xyz}",
        f"new XYZ {move.new_xyz}",
        f"runtime delta ({dx << 5}, {dy << 5}, {dz << 5})",
        f"old bytes {move.old_entry.hex()}",
        f"new bytes {move.new_entry.hex()}",
    ]
    return " | ".join(parts)


def write_report(path: Path, source: Path, out: Path | None, moves: list[Move], args: argparse.Namespace, wrote: bool) -> None:
    lines = [
        "# Type-0x3f Fixed-Size Move Report",
        "",
        f"- input: `{source}`",
        f"- output: `{out}`" if out else "- output: dry-run only",
        f"- wrote file: {'yes' if wrote else 'no'}",
        f"- file-unit delta: dx={args.dx}, dy={args.dy}, dz={args.dz}",
        f"- runtime delta: dx={args.dx << 5}, dy={args.dy << 5}, dz={args.dz << 5}",
        f"- entries moved: {len(moves)}",
        "",
        "| entry | offset | kind | identity | old XYZ | new XYZ | old bytes | new bytes |",
        "|---:|---:|---:|---|---|---|---|---|",
    ]
    for move in moves:
        row = move.row
        lines.append(
            f"| {row.raw_entry_index} | `0x{row.entry_offset:06x}` | `0x{row.source_kind:02x}` | "
            f"{row.decoded_identity} | `{move.old_xyz}` | `{move.new_xyz}` | "
            f"`{move.old_entry.hex()}` | `{move.new_entry.hex()}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move existing type-0x3f entries by fixed-size X/Y/Z coordinate edits."
    )
    parser.add_argument("dat", type=Path, help="input DAT file")
    parser.add_argument("--entry", "--entries", dest="entries", nargs="*", default=[], help="raw entry index or comma-separated indices")
    parser.add_argument("--identity", help="decoded identity selector; must match exactly one catalog row")
    parser.add_argument("--dx", type=int, default=0, help="file-unit X delta")
    parser.add_argument("--dy", type=int, default=0, help="file-unit Y delta")
    parser.add_argument("--dz", type=int, default=0, help="file-unit Z delta")
    parser.add_argument("--out", type=Path, help="output DAT path; required with --write")
    parser.add_argument("--write", action="store_true", help="write --out; default is dry-run")
    parser.add_argument("--report", type=Path, help="optional Markdown patch report path")
    parser.add_argument("--allow-telescope", action="store_true", help="allow moving kind 0x30 telescope")
    parser.add_argument("--allow-checkpoint", dest="allow_telescope", action="store_true",
                        help=argparse.SUPPRESS)  # compatibility with pre-correction scripts
    parser.add_argument("--allow-token-like", action="store_true", help="allow moving kinds 0x2c/0x2d")
    parser.add_argument("--allow-unknown", action="store_true", help="allow moving unknown/unsupported kinds, including 0x31")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entries = parse_index_list(args.entries)
    if not entries and args.identity is None:
        raise SystemExit("select at least one --entry or one --identity")
    if args.dx == 0 and args.dy == 0 and args.dz == 0:
        raise SystemExit("refusing: at least one of --dx/--dy/--dz must be nonzero")
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    data = args.dat.read_bytes()
    summary = analyze_file(args.dat)
    if summary.parse_error:
        raise SystemExit(f"catalog parse failed: {summary.parse_error}")
    if len(summary.type3f_offsets) != 1:
        raise SystemExit(f"expected exactly one type-0x3f record, found {len(summary.type3f_offsets)}")
    rows = select_rows(summary.rows, entries, args.identity)
    if not rows:
        raise SystemExit("no entries selected")

    for row in rows:
        check_risk(row, args)

    patched, moves = build_moves(data, rows, args.dx, args.dy, args.dz)
    changed_axis_offsets = {axis_off for delta, (_axis, axis_off) in zip((args.dx, args.dy, args.dz), AXES) if delta != 0}
    verify_patch(data, patched, moves, changed_axis_offsets)

    print(f"type-0x3f @ 0x{summary.type3f_offsets[0]:06x}, {summary.type3f_counts[0]} entries")
    print(f"mode: {'write' if args.write else 'dry-run'}")
    print(f"file-unit delta: dx={args.dx} dy={args.dy} dz={args.dz}")
    print(f"runtime delta: dx={args.dx << 5} dy={args.dy << 5} dz={args.dz << 5}")
    for move in moves:
        print(format_move(move, args.dx, args.dy, args.dz))

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(patched)
        if args.out.read_bytes() != patched:
            raise SystemExit("verification failed: written output differs from verified buffer")
        print(f"wrote {args.out} ({len(patched)} bytes)")
    else:
        print("dry-run only; no DAT written")

    if args.report:
        write_report(args.report, args.dat, args.out, moves, args, args.write)
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
