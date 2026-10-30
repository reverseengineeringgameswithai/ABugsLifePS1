#!/usr/bin/env python3
"""List candidate FLIK-letter placement entries in A Bug's Life LEVEL*.DAT files."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


FLIK_SOURCE_KINDS = {
    0x21: 2,
    0x22: 3,
    0x23: 1,
    0x24: 4,
}


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


def print_flik_entries(path: Path, dy: int) -> int:
    data = path.read_bytes()
    found = 0
    print(f"file: {path}")
    print(
        "record_type  record_off  raw_entry  entry_off  y_off     "
        "x       y       z       source_kind  marker  patched_y  orig_y_bytes  patched_y_bytes"
    )
    for _ordinal, rec_off, count, rec_type, _size in iter_dat_records(data):
        if rec_type != 0x3F:
            continue
        for raw_index in range(count):
            entry_off = rec_off + 4 + raw_index * 0x10
            source_kind = data[entry_off + 0x0C]
            if source_kind not in FLIK_SOURCE_KINDS:
                continue
            y_off = entry_off + 4
            x = s32(data, entry_off)
            y = s32(data, y_off)
            z = s32(data, entry_off + 8)
            patched_y = y + dy
            found += 1
            print(
                f"0x{rec_type:04x}      0x{rec_off:06x}  {raw_index:9d}  "
                f"0x{entry_off:06x}  0x{y_off:06x}  "
                f"{x:7d} {y:7d} {z:7d}  "
                f"0x{source_kind:02x}         {FLIK_SOURCE_KINDS[source_kind]}       "
                f"{patched_y:9d}  "
                f"{data[y_off:y_off+4].hex(' '):>11}  {pack_s32(patched_y).hex(' '):>15}"
            )
    print(f"candidate_flik_count: {found}")
    return 0 if found else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List candidate FLIK-letter type-0x3f placement entries."
    )
    parser.add_argument("dat", type=Path, help="Path to a LEVEL.DAT or LEVEL1.DAT file")
    parser.add_argument(
        "--dy",
        type=int,
        default=-512,
        help="signed Y delta in file units for patch-byte suggestions",
    )
    args = parser.parse_args()
    return print_flik_entries(args.dat, args.dy)


if __name__ == "__main__":
    raise SystemExit(main())
