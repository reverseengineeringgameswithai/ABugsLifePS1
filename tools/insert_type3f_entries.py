#!/usr/bin/env python3
"""Safe user-facing type-0x3f append wrapper around tools/dat_reloc.py.

Phase: Option C Phase 3. This tool appends one or more 0x10-byte type-0x3f
entries using the trusted dat_reloc relocation engine. It defaults to dry-run
and writes only with --write --out.
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

import dat_reloc
from catalog_type3f import analyze_file


ENTRY_SIZE = 0x10
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
class NewEntry:
    source: str
    data: bytes
    x: int
    y: int
    z: int
    kind_word: int

    @property
    def kind(self) -> int:
        return self.kind_word & 0xFF


@dataclass(frozen=True)
class AppendStep:
    index: int
    insertion_offset: int
    old_size: int
    new_size: int
    old_count: int
    new_count: int
    new_entry: NewEntry
    relocation_total: int
    relocation_bumped: int
    final_relocation_total: int


def s32(data: bytes, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def parse_int(value: str) -> int:
    return int(value, 0)


def pack_entry(x: int, y: int, z: int, kind_word: int) -> bytes:
    for name, value in (("x", x), ("y", y), ("z", z)):
        if value < -0x80000000 or value > 0x7FFFFFFF:
            raise SystemExit(f"{name} coordinate overflows s32: {value}")
    if kind_word < 0 or kind_word > 0xFFFFFFFF:
        raise SystemExit(f"kind word overflows u32: {kind_word:#x}")
    return struct.pack("<iiiI", x, y, z, kind_word)


def decode_entry(data: bytes, source: str) -> NewEntry:
    if len(data) != ENTRY_SIZE:
        raise SystemExit(f"{source}: entry must be exactly 16 bytes, got {len(data)}")
    x, y, z, kind_word = struct.unpack("<iiiI", data)
    return NewEntry(source=source, data=data, x=x, y=y, z=z, kind_word=kind_word)


def parse_append_clone(spec: str, original: bytes, rec_off: int, count: int) -> NewEntry:
    parts = spec.split(":")
    if len(parts) > 4:
        raise SystemExit(f"--append-clone expects ENTRY[:DX[:DY[:DZ]]], got {spec!r}")
    entry = parse_int(parts[0])
    deltas = [0, 0, 0]
    for i, part in enumerate(parts[1:]):
        deltas[i] = parse_int(part)
    if entry < 0 or entry >= count:
        raise SystemExit(f"clone entry {entry} outside valid range 0..{count - 1}")
    off = rec_off + 4 + entry * ENTRY_SIZE
    x, y, z, kind_word = struct.unpack_from("<iiiI", original, off)
    data = pack_entry(x + deltas[0], y + deltas[1], z + deltas[2], kind_word)
    return decode_entry(data, f"clone:{entry}:dx={deltas[0]}:dy={deltas[1]}:dz={deltas[2]}")


def parse_append_new(spec: str) -> NewEntry:
    parts = spec.split(":")
    if len(parts) not in {4, 5, 6, 7}:
        raise SystemExit(
            "--append-new expects KIND:X:Y:Z[:UNK0D[:UNK0E[:UNK0F]]], "
            f"got {spec!r}"
        )
    kind = parse_int(parts[0])
    if kind < 0 or kind > 0xFF:
        raise SystemExit(f"kind must fit in one byte for --append-new: {kind:#x}")
    x, y, z = (parse_int(parts[1]), parse_int(parts[2]), parse_int(parts[3]))
    unknown = [0, 0, 0]
    for i, part in enumerate(parts[4:]):
        value = parse_int(part)
        if value < 0 or value > 0xFF:
            raise SystemExit(f"unknown byte {i} must be 0..255, got {value:#x}")
        unknown[i] = value
    kind_word = kind | (unknown[0] << 8) | (unknown[1] << 16) | (unknown[2] << 24)
    return decode_entry(pack_entry(x, y, z, kind_word), f"new:{spec}")


def parse_entry_hex(hex_text: str) -> NewEntry:
    compact = "".join(hex_text.split())
    try:
        data = bytes.fromhex(compact)
    except ValueError as exc:
        raise SystemExit(f"--entry-bytes is not valid hex: {exc}") from exc
    return decode_entry(data, f"hex:{compact}")


def check_entry_risk(entry: NewEntry, args: argparse.Namespace) -> None:
    kind = entry.kind
    if kind in RISK_TELESCOPE and not args.allow_telescope:
        raise SystemExit(
            f"{entry.source}: kind 0x{kind:02x} is a telescope/hint-view trigger; "
            "use --allow-telescope to override"
        )
    if kind in RISK_TOKEN_LIKE and not args.allow_token_like:
        raise SystemExit(
            f"{entry.source}: kind 0x{kind:02x} is token-like but not production-tested; "
            "use --allow-token-like to override"
        )
    if (kind in RISK_UNKNOWN or kind not in KNOWN_SAFE | RISK_TOKEN_LIKE | RISK_TELESCOPE) and not args.allow_unknown:
        raise SystemExit(
            f"{entry.source}: kind 0x{kind:02x} is unknown/unsupported; "
            "use --allow-unknown to override"
        )


def type3f_info(data: bytes, path: Path) -> tuple[int, int, int]:
    summary = analyze_file(path) if path.exists() else None
    if summary and len(summary.type3f_offsets) == 1:
        rec_off = summary.type3f_offsets[0]
        count = summary.type3f_counts[0]
        return rec_off, count, rec_off + 4 + count * ENTRY_SIZE

    # Fallback for temp buffers: dat_reloc's record walker is the trusted parser model.
    src = dat_reloc.DAT(data)
    _trail, records = src.trailing_base()
    matches = [(off, count) for off, typ, count, _size in records if typ == 0x3F]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one type-0x3f record, found {len(matches)}")
    rec_off, count = matches[0]
    return rec_off, count, rec_off + 4 + count * ENTRY_SIZE


def type3f_info_from_bytes(data: bytes) -> tuple[int, int, int]:
    src = dat_reloc.DAT(data)
    _trail, records = src.trailing_base()
    matches = [(off, count) for off, typ, count, _size in records if typ == 0x3F]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one type-0x3f record, found {len(matches)}")
    rec_off, count = matches[0]
    return rec_off, count, rec_off + 4 + count * ENTRY_SIZE


def build_entries(args: argparse.Namespace, original: bytes, rec_off: int, count: int) -> list[NewEntry]:
    entries: list[NewEntry] = []
    for spec in args.append_clone:
        entries.append(parse_append_clone(spec, original, rec_off, count))
    for spec in args.append_new:
        entries.append(parse_append_new(spec))
    for spec in args.entry_bytes:
        entries.append(parse_entry_hex(spec))

    if args.clone_entry is not None:
        dx, dy, dz = args.dx, args.dy, args.dz
        entries.append(parse_append_clone(f"{args.clone_entry}:{dx}:{dy}:{dz}", original, rec_off, count))
    if args.kind is not None or args.x is not None or args.y is not None or args.z is not None:
        if args.kind is None or args.x is None or args.y is None or args.z is None:
            raise SystemExit("--kind/--x/--y/--z must be provided together")
        entries.append(
            parse_append_new(
                f"{args.kind}:{args.x}:{args.y}:{args.z}:{args.unk0d}:{args.unk0e}:{args.unk0f}"
            )
        )

    if not entries:
        raise SystemExit("provide at least one append operation")
    for entry in entries:
        check_entry_risk(entry, args)
    return entries


def apply_appends(original: bytes, rec_off: int, entries: list[NewEntry]) -> tuple[bytes, list[AppendStep], list[dict]]:
    current = original
    steps: list[AppendStep] = []
    all_reports: list[dict] = []

    for i, entry in enumerate(entries):
        cur_rec_off, cur_count, insert_off = type3f_info_from_bytes(current)
        if cur_rec_off != rec_off:
            raise SystemExit(
                f"type-0x3f record offset changed unexpectedly: 0x{cur_rec_off:x} != 0x{rec_off:x}"
            )
        before_sites, _before_meta = dat_reloc.DAT(current).scan_sites()
        dat_reloc.INSERT_OFF = insert_off
        dat_reloc.T3F_HDR = cur_rec_off
        new_data, report, _sites, _meta = dat_reloc.build_reloc_insert(current, entry.data)
        after_sites, _after_meta = dat_reloc.DAT(new_data).scan_sites()
        new_count = u16(new_data, cur_rec_off)
        steps.append(
            AppendStep(
                index=i,
                insertion_offset=insert_off,
                old_size=len(current),
                new_size=len(new_data),
                old_count=cur_count,
                new_count=new_count,
                new_entry=entry,
                relocation_total=len(report),
                relocation_bumped=sum(1 for row in report if row["bumped"]),
                final_relocation_total=len(after_sites),
            )
        )
        if len(report) != len(before_sites):
            raise SystemExit(
                f"verification failed: step {i} relocation report count {len(report)} "
                f"!= pre-insert scan count {len(before_sites)}"
            )
        all_reports.extend(report)
        current = new_data
    return current, steps, all_reports


def verify_result(original: bytes, final: bytes, rec_off: int, old_count: int, entries: list[NewEntry], steps: list[AppendStep]) -> None:
    expected_size = len(original) + ENTRY_SIZE * len(entries)
    if len(final) != expected_size:
        raise SystemExit(f"verification failed: size {len(final)} != expected {expected_size}")
    final_count = u16(final, rec_off)
    expected_count = old_count + len(entries)
    if final_count != expected_count:
        raise SystemExit(f"verification failed: count {final_count} != expected {expected_count}")
    if final[rec_off + 2 : rec_off + 4] != original[rec_off + 2 : rec_off + 4]:
        raise SystemExit("verification failed: type-0x3f record type changed")

    entry_base = rec_off + 4
    old_entries_len = old_count * ENTRY_SIZE
    if final[entry_base : entry_base + old_entries_len] != original[entry_base : entry_base + old_entries_len]:
        raise SystemExit("verification failed: existing type-0x3f entries changed")

    for i, entry in enumerate(entries):
        off = entry_base + (old_count + i) * ENTRY_SIZE
        actual = final[off : off + ENTRY_SIZE]
        if actual != entry.data:
            raise SystemExit(
                f"verification failed: appended entry {i} bytes mismatch "
                f"{actual.hex()} != {entry.data.hex()}"
            )

    if len(steps) != len(entries):
        raise SystemExit("verification failed: append step count mismatch")
    for i, step in enumerate(steps):
        if step.new_size != step.old_size + ENTRY_SIZE:
            raise SystemExit(f"verification failed: step {i} size delta is not 0x10")
        if step.new_count != step.old_count + 1:
            raise SystemExit(f"verification failed: step {i} count did not increment by 1")
        if step.relocation_total == 0:
            raise SystemExit(f"verification failed: step {i} reported zero relocation fields")
        if step.relocation_bumped == 0:
            raise SystemExit(f"verification failed: step {i} reported zero bumped relocation fields")
        if step.final_relocation_total != step.relocation_total:
            raise SystemExit(
                f"verification failed: step {i} final relocation scan count "
                f"{step.final_relocation_total} != report count {step.relocation_total}"
            )


def write_report(path: Path, source: Path, out: Path | None, old_count: int, final: bytes, entries: list[NewEntry], steps: list[AppendStep], wrote: bool) -> None:
    lines = [
        "# Type-0x3f Relocation-Aware Append Report",
        "",
        f"- input: `{source}`",
        f"- output: `{out}`" if out else "- output: dry-run only",
        f"- wrote file: {'yes' if wrote else 'no'}",
        f"- appended entries: {len(entries)}",
        f"- old count: {old_count}",
        f"- new count: {old_count + len(entries)}",
        f"- output size: {len(final)}",
        f"- expected size delta: {ENTRY_SIZE * len(entries)}",
        "",
        "## New Entries",
        "",
        "| new ordinal | source | X | Y | Z | kind | bytes |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for i, entry in enumerate(entries):
        lines.append(
            f"| {old_count + i} | `{entry.source}` | {entry.x} | {entry.y} | {entry.z} | "
            f"`0x{entry.kind:02x}` | `{entry.data.hex()}` |"
        )
    lines.extend(
        [
            "",
            "## Relocation Steps",
            "",
            "| step | insertion offset | size | count | relocation fields | bumped fields | final scan fields |",
            "|---:|---:|---|---|---:|---:|---:|",
        ]
    )
    for step in steps:
        lines.append(
            f"| {step.index} | `0x{step.insertion_offset:06x}` | "
            f"{step.old_size} -> {step.new_size} | {step.old_count} -> {step.new_count} | "
            f"{step.relocation_total} | {step.relocation_bumped} | {step.final_relocation_total} |"
        )
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "- Count changed by exactly the number of appended entries.",
            "- Existing type-`0x3f` entries are byte-identical.",
            "- Appended entry bytes match requested entries.",
            "- Each append step increased output size by `0x10`.",
            "- Each append step increased type-`0x3f` count by one.",
            "- Relocation fields were processed by `tools/dat_reloc.py`.",
            "- Final relocation-site scan count matched the relocation report count.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Relocation-aware multi-entry type-0x3f append wrapper around tools/dat_reloc.py."
    )
    parser.add_argument("dat", type=Path)
    parser.add_argument(
        "--append-clone",
        action="append",
        default=[],
        metavar="ENTRY[:DX[:DY[:DZ]]]",
        help="append a clone of an existing entry with optional file-unit deltas; may repeat",
    )
    parser.add_argument(
        "--append-new",
        action="append",
        default=[],
        metavar="KIND:X:Y:Z[:UNK0D[:UNK0E[:UNK0F]]]",
        help="append a structured new entry; may repeat",
    )
    parser.add_argument(
        "--entry-bytes",
        action="append",
        default=[],
        help="append explicit 16-byte entry hex; may repeat",
    )
    parser.add_argument("--clone-entry", type=int, help="compatibility single clone entry selector")
    parser.add_argument("--dx", type=int, default=0)
    parser.add_argument("--dy", type=int, default=0)
    parser.add_argument("--dz", type=int, default=0)
    parser.add_argument("--kind", help="compatibility structured kind for one append-new")
    parser.add_argument("--x")
    parser.add_argument("--y")
    parser.add_argument("--z")
    parser.add_argument("--unk0d", default="0")
    parser.add_argument("--unk0e", default="0")
    parser.add_argument("--unk0f", default="0")
    parser.add_argument("--write", action="store_true", help="write --out; default is dry-run")
    parser.add_argument("--out", type=Path, help="output DAT path; required with --write")
    parser.add_argument("--report", type=Path, help="optional Markdown verification report path")
    parser.add_argument("--allow-telescope", action="store_true", help="allow appending kind 0x30 telescope")
    parser.add_argument("--allow-checkpoint", dest="allow_telescope", action="store_true",
                        help=argparse.SUPPRESS)  # compatibility with pre-correction scripts
    parser.add_argument("--allow-token-like", action="store_true", help="allow appending kinds 0x2c/0x2d")
    parser.add_argument("--allow-unknown", action="store_true", help="allow appending unknown/unsupported kinds, including 0x31")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")

    original = args.dat.read_bytes()
    rec_off, old_count, insert_off = type3f_info(original, args.dat)
    if u16(original, rec_off + 2) != 0x3F:
        raise SystemExit("internal error: selected record is not type-0x3f")

    entries = build_entries(args, original, rec_off, old_count)
    final, steps, _reloc_report = apply_appends(original, rec_off, entries)
    verify_result(original, final, rec_off, old_count, entries, steps)

    print(f"type-0x3f @ 0x{rec_off:06x}, old count {old_count}, append count {len(entries)}")
    print(f"initial insertion offset: 0x{insert_off:06x}")
    print(f"mode: {'write' if args.write else 'dry-run'}")
    for i, entry in enumerate(entries):
        print(
            f"append {i}: new index {old_count + i} source={entry.source} "
            f"XYZ=({entry.x},{entry.y},{entry.z}) kind=0x{entry.kind:02x} bytes={entry.data.hex()}"
        )
    for step in steps:
        print(
            f"step {step.index}: insert @ 0x{step.insertion_offset:06x}, "
            f"size {step.old_size}->{step.new_size}, count {step.old_count}->{step.new_count}, "
            f"reloc fields {step.relocation_total}, bumped {step.relocation_bumped}, "
            f"final scan fields {step.final_relocation_total}"
        )
    print(f"expected output size: {len(original)} -> {len(final)} (+{len(final) - len(original)})")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(final)
        if args.out.read_bytes() != final:
            raise SystemExit("verification failed: written output differs from verified buffer")
        print(f"wrote {args.out} ({len(final)} bytes)")
    else:
        print("dry-run only; no DAT written")

    if args.report:
        write_report(args.report, args.dat, args.out, old_count, final, entries, steps, args.write)
        print(f"report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
