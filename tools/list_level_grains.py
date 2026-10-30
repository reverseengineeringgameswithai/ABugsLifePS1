#!/usr/bin/env python3
"""List type-0x3f grain-source entries in A Bug's Life LEVEL*.DAT files."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


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


def print_type3f(data: bytes, rec_ordinal: int, rec_off: int, count: int, only_grain: bool):
    print(f"type_0x3f record {rec_ordinal} at file offset 0x{rec_off:04x}")
    print(f"entries: {count}  entry_base: 0x{rec_off + 4:04x}  entry_size: 0x10")
    print(
        "idx  entry_off  y_off   kind grain  "
        "x       y       z       patched_y  orig_y_bytes  patched_y_bytes"
    )
    grain_count = 0
    for idx in range(count):
        entry_off = rec_off + 4 + idx * 0x10
        x = s32(data, entry_off)
        y = s32(data, entry_off + 4)
        z = s32(data, entry_off + 8)
        kind = data[entry_off + 0x0C]
        is_grain = kind == 0x14
        if is_grain:
            grain_count += 1
        if only_grain and not is_grain:
            continue
        patched_y = y - 0x40
        orig_y = data[entry_off + 4 : entry_off + 8]
        patched_y_bytes = pack_s32(patched_y)
        print(
            f"{idx:3d}  0x{entry_off:06x}  0x{entry_off + 4:06x}  "
            f"0x{kind:02x}  {'yes' if is_grain else ' no'}  "
            f"{x:7d} {y:7d} {z:7d} {patched_y:10d}  "
            f"{orig_y.hex(' '):>11}  {patched_y_bytes.hex(' '):>15}"
        )
    print(f"source_kind_0x14_count: {grain_count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse LEVEL*.DAT type-0x3f entries and suggest Y-up grain patches."
    )
    parser.add_argument("dat", type=Path, help="Path to a LEVEL.DAT or LEVEL1.DAT file")
    parser.add_argument(
        "--all",
        action="store_true",
        help="print non-grain entries too; default prints source kind 0x14 only",
    )
    args = parser.parse_args()

    data = args.dat.read_bytes()
    found = False
    for ordinal, off, count, rec_type, size in iter_dat_records(data):
        if rec_type == 0x3F:
            found = True
            print_type3f(data, ordinal, off, count, only_grain=not args.all)
    if not found:
        print("no type_0x3f records found")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
