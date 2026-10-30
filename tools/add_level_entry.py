#!/usr/bin/env python3
"""Clone and append one type-0x3f placement entry in an ABL LEVEL .DAT.

This is intentionally an insert/add tool, not a coordinate patcher. It clones a
single existing 0x10-byte placement entry, applies optional coordinate deltas to
the clone only, appends that clone to the first type-0x3f record, increments that
record count, and writes a separate output file.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


ENTRY_SIZE = 0x10
TYPE_PLACEMENT = 0x3F


def s16(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<h", data, off)[0]


def u16(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def s32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<i", data, off)[0]


def dat_record_size(data: bytes | bytearray, off: int) -> int:
    count = s16(data, off)
    rec_type = s16(data, off + 2)
    if rec_type < 0:
        words = ((count * 3 + 1) + ((count * 3 + 1) >> 31)) >> 1
        return words * 4 + 0x10
    if rec_type == TYPE_PLACEMENT:
        return (count << 4) + 4
    return ((count * 3) << 2) + 4


def iter_dat_records(data: bytes | bytearray):
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


def find_first_type3f(data: bytes | bytearray) -> tuple[int, int, int, int]:
    for ordinal, rec_off, count, rec_type, size in iter_dat_records(data):
        if rec_type == TYPE_PLACEMENT:
            return ordinal, rec_off, count, size
    raise ValueError("no type-0x3f record found")


def pack_s32(value: int) -> bytes:
    if value < -0x80000000 or value > 0x7FFFFFFF:
        raise ValueError(f"s32 coordinate overflow: {value}")
    return struct.pack("<i", value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append a cloned type-0x3f placement entry to a LEVEL .DAT."
    )
    parser.add_argument("dat", type=Path)
    parser.add_argument("--clone-entry", type=lambda x: int(x, 0), required=True)
    parser.add_argument("--dx", type=int, default=0, help="file-unit delta for cloned X")
    parser.add_argument("--dy", type=int, default=0, help="file-unit delta for cloned Y")
    parser.add_argument("--dz", type=int, default=0, help="file-unit delta for cloned Z")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    in_path = args.dat.resolve()
    out_path = args.out.resolve()
    if in_path == out_path:
        print("Refusing in-place edit: --out must differ from input", file=sys.stderr)
        return 1

    data = bytearray(args.dat.read_bytes())
    original_len = len(data)
    top_level_count = struct.unpack_from("<i", data, 0)[0]
    ordinal, rec_off, count, rec_size = find_first_type3f(data)
    entry_base = rec_off + 4
    insertion_offset = rec_off + rec_size

    if count >= 0xFFFF:
        print("Refusing: type-0x3f count is already at u16 max", file=sys.stderr)
        return 1
    if args.clone_entry < 0 or args.clone_entry >= count:
        print(
            f"Refusing: clone entry {args.clone_entry} outside 0..{count - 1}",
            file=sys.stderr,
        )
        return 1

    source_off = entry_base + args.clone_entry * ENTRY_SIZE
    original_entry = bytes(data[source_off : source_off + ENTRY_SIZE])
    new_entry = bytearray(original_entry)

    old_x, old_y, old_z = (
        s32(original_entry, 0),
        s32(original_entry, 4),
        s32(original_entry, 8),
    )
    new_x = old_x + args.dx
    new_y = old_y + args.dy
    new_z = old_z + args.dz
    new_entry[0:4] = pack_s32(new_x)
    new_entry[4:8] = pack_s32(new_y)
    new_entry[8:12] = pack_s32(new_z)

    data[insertion_offset:insertion_offset] = new_entry
    struct.pack_into("<H", data, rec_off, count + 1)

    # Prove the edited DAT still walks with the same top-level record count.
    reparsed = list(iter_dat_records(data))
    if len(reparsed) != top_level_count:
        print("Refusing: edited DAT reparsed with unexpected record count", file=sys.stderr)
        return 1

    args.out.write_bytes(data)

    print(f"input: {args.dat}")
    print(f"output: {args.out}")
    print(f"top-level record count: {top_level_count} (unchanged)")
    print(f"type-0x3f record ordinal: {ordinal}")
    print(f"type-0x3f record offset: {rec_off:#x}")
    print(f"entry size: {ENTRY_SIZE:#x}")
    print(f"original type-0x3f count: {count}")
    print(f"new type-0x3f count: {count + 1}")
    print(f"source entry index: {args.clone_entry}")
    print(f"new entry index: {count}")
    print(f"source entry offset: {source_off:#x}")
    print(f"insertion offset: {insertion_offset:#x}")
    print(f"original cloned bytes: {original_entry.hex()}")
    print(f"new cloned bytes: {bytes(new_entry).hex()}")
    print(f"original X/Y/Z: {old_x} {old_y} {old_z}")
    print(f"new X/Y/Z: {new_x} {new_y} {new_z}")
    print(f"coordinate deltas: dx={args.dx} dy={args.dy} dz={args.dz}")
    print(f"source kind: {original_entry[0x0c]:#04x}")
    print(f"input size: {original_len}")
    print(f"output size: {len(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
