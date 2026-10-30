#!/usr/bin/env python3
"""Pass-1 scenery/prop instance editor for A Bug's Life LEVEL .DAT (punchlist §11.1-2).

Static decor/props (mushrooms, fences, rocks, ...) are placed by LEVEL.DAT "pass-1"
instance records: a stride-0x14 table starting at the trailing base (LEVEL01 @ 0x1504),
sentinel-terminated (a record whose +0x0e halfword is negative). Each record:

    +0x00/+04/+08  s32 X / Y / Z   world placement position   (NOT relocated -> editable)
    +0x0c          u16 extent
    +0x0e          u16 flags        (bit3 selects payload bridge; sentinel if high bit set)
    +0x10          u32 payload ptr  (a baked file-offset -> relocation site)

MOVE / SET edit the X/Y/Z in place (size-preserving, no relocation). DELETE removes the
0x14-byte record via the relocation-aware engine (dat_reloc.build_reloc_delete_bytes):
the region after it shifts up 0x14 and every baked offset pointing past is bumped -0x14.
The mesh PAYLOAD the deleted record pointed at is left in place (orphaned, harmless) —
this removes the instance, not the asset (assets may be shared).

Defaults to dry-run; writes only with --write --out. Never edits in place.
Multiple ops: moves/sets apply against ORIGINAL indices first, then deletes high-index
first so a removal never renumbers a not-yet-deleted lower record.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

import dat_reloc

STRIDE = 0x14


@dataclass(frozen=True)
class Pass1Record:
    index: int
    offset: int
    x: int
    y: int
    z: int
    extent: int
    flags: int
    ptr: int


def pass1_base(data: bytes) -> int:
    return dat_reloc.DAT(data).trailing_base()[0]


def pass1_count(data: bytes) -> int:
    src = dat_reloc.DAT(data)
    base = src.trailing_base()[0]
    p = base + 0x0e
    n = 0
    while src.s16(p) >= 0:
        p += STRIDE
        n += 1
    return n


def read_record(data: bytes, base: int, index: int) -> Pass1Record:
    off = base + index * STRIDE
    x, y, z = struct.unpack_from("<iii", data, off)
    extent = struct.unpack_from("<H", data, off + 0x0c)[0]
    flags = struct.unpack_from("<H", data, off + 0x0e)[0]
    ptr = struct.unpack_from("<I", data, off + 0x10)[0]
    return Pass1Record(index, off, x, y, z, extent, flags, ptr)


def list_records(data: bytes) -> list[Pass1Record]:
    base = pass1_base(data)
    return [read_record(data, base, i) for i in range(pass1_count(data))]


def _parse_triplet(spec: str, n: int) -> list[int]:
    parts = spec.split(":")
    if len(parts) != n:
        raise SystemExit(f"expected {n} colon-separated ints, got {spec!r}")
    return [int(p, 0) for p in parts]


def apply_moves_sets(data: bytes, base: int, count: int,
                     moves: list[tuple[int, int, int, int]],
                     sets: list[tuple[int, int, int, int]]) -> tuple[bytes, list[str]]:
    """Size-preserving X/Y/Z edits (no relocation). moves are deltas, sets are absolute."""
    buf = bytearray(data)
    log: list[str] = []
    for idx, dx, dy, dz in moves:
        if not (0 <= idx < count):
            raise SystemExit(f"move index {idx} outside 0..{count-1}")
        off = base + idx * STRIDE
        x, y, z = struct.unpack_from("<iii", buf, off)
        nx, ny, nz = x + dx, y + dy, z + dz
        struct.pack_into("<iii", buf, off, nx, ny, nz)
        log.append(f"move #{idx}: ({x},{y},{z}) -> ({nx},{ny},{nz})")
    for idx, x, y, z in sets:
        if not (0 <= idx < count):
            raise SystemExit(f"set index {idx} outside 0..{count-1}")
        off = base + idx * STRIDE
        ox, oy, oz = struct.unpack_from("<iii", buf, off)
        struct.pack_into("<iii", buf, off, x, y, z)
        log.append(f"set #{idx}: ({ox},{oy},{oz}) -> ({x},{y},{z})")
    return bytes(buf), log


def apply_deletes(data: bytes, indices: list[int]) -> tuple[bytes, list[str]]:
    """Delete records by ORIGINAL index, high-index first (so lower indices stay valid)."""
    cur = data
    log: list[str] = []
    for idx in sorted(set(indices), reverse=True):
        base = pass1_base(cur)
        count = pass1_count(cur)
        if not (0 <= idx < count):
            raise SystemExit(f"delete index {idx} outside 0..{count-1}")
        victim = read_record(cur, base, idx)
        before_sites = len(dat_reloc.DAT(cur).scan_sites()[0])
        new, report, _sites, _meta = dat_reloc.build_reloc_delete_bytes(cur, victim.offset, STRIDE)
        after_sites = len(dat_reloc.DAT(new).scan_sites()[0])
        dropped = sum(1 for r in report if r.get("dropped"))
        # a pass-1 record carries exactly its own site A (the +0x10 ptr) inside the region
        if dropped != 1:
            raise SystemExit(f"delete #{idx}: expected 1 in-record site dropped, got {dropped}")
        # the walk loses the deleted record's site A (in-record) AND its site B (via its ptr)
        if after_sites != before_sites - 2:
            raise SystemExit(f"delete #{idx}: site count {before_sites}->{after_sites} "
                             "(expected -2)")
        log.append(f"delete #{idx}: kind-ptr={victim.ptr:#x} XYZ=({victim.x},{victim.y},{victim.z}) "
                   f"size {len(cur)}->{len(new)} sites {before_sites}->{after_sites}")
        cur = new
    return cur, log


def verify(original: bytes, final: bytes, deleted: list[int], moves_sets: int) -> None:
    base = pass1_base(original)
    on = pass1_count(original)
    nn = pass1_count(final)
    ndel = len(set(deleted))
    if nn != on - ndel:
        raise SystemExit(f"verify failed: count {on}->{nn}, expected -{ndel}")
    if len(final) != len(original) - ndel * STRIDE:
        raise SystemExit(f"verify failed: size delta {len(final)-len(original)} != {-ndel*STRIDE}")
    # surviving records' X/Y/Z (not relocated) must match original-minus-deleted, in order
    survivors = [j for j in range(on) if j not in set(deleted)]
    fb = pass1_base(final)
    mismatch = 0
    for k, oldi in enumerate(survivors):
        a = struct.unpack_from("<iii", original, base + oldi * STRIDE)
        b = struct.unpack_from("<iii", final, fb + k * STRIDE)
        # a moved/set record legitimately differs; only assert identity for untouched ones
        if a != b:
            mismatch += 1
    if ndel and mismatch > moves_sets:
        raise SystemExit(f"verify failed: {mismatch} survivor XYZ mismatches exceed "
                         f"{moves_sets} edited records")
    # the result must re-parse and every record/pass3 pointer resolve in-bounds
    sites, _ = dat_reloc.DAT(final).scan_sites()
    for s in sites:
        if s["site"] in ("P1.A [s3+2]", "P3.G [s3+2]") and not (0 <= s["value"] < len(final)):
            raise SystemExit(f"verify failed: pointer field {s['field']:#x} value "
                             f"{s['value']:#x} out of bounds")


def main() -> int:
    ap = argparse.ArgumentParser(description="Pass-1 scenery/prop move/set/delete for LEVEL.DAT.")
    ap.add_argument("dat", type=Path)
    ap.add_argument("--list", action="store_true", help="list pass-1 records and exit")
    ap.add_argument("--move", action="append", default=[], metavar="I:DX:DY:DZ",
                    help="move record I by file-unit deltas; may repeat")
    ap.add_argument("--set", action="append", default=[], metavar="I:X:Y:Z",
                    help="set record I to absolute X/Y/Z; may repeat")
    ap.add_argument("--delete-index", action="append", default=[], type=lambda s: int(s, 0),
                    metavar="I", help="delete record I (original numbering); may repeat")
    ap.add_argument("--write", action="store_true", help="write --out; default dry-run")
    ap.add_argument("--out", type=Path, help="output DAT; required with --write")
    args = ap.parse_args()

    data = args.dat.read_bytes()
    base = pass1_base(data)
    count = pass1_count(data)

    if args.list:
        print(f"pass-1 table @ {base:#x}, {count} records (stride {STRIDE:#x})")
        for r in list_records(data):
            print(f"  #{r.index:3d} @ {r.offset:#06x}  X={r.x:7d} Y={r.y:7d} Z={r.z:7d}  "
                  f"extent={r.extent:#06x} flags={r.flags:#06x} ptr={r.ptr:#010x}")
        return 0

    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")
    if not (args.move or args.set or args.delete_index):
        raise SystemExit("provide at least one --move/--set/--delete-index (or --list)")

    moves = [tuple(_parse_triplet(s, 4)) for s in args.move]
    sets = [tuple(_parse_triplet(s, 4)) for s in args.set]
    print(f"pass-1 @ {base:#x}, {count} records")
    print(f"mode: {'write' if args.write else 'dry-run'}")

    # moves/sets first (against original indices), then deletes high-first
    data2, log1 = apply_moves_sets(data, base, count, moves, sets)
    for line in log1:
        print(" ", line)
    final, log2 = apply_deletes(data2, args.delete_index)
    for line in log2:
        print(" ", line)

    verify(data, final, args.delete_index, len(moves) + len(sets))
    print(f"size {len(data)} -> {len(final)} ({len(final)-len(data):+d}); "
          f"count {count} -> {pass1_count(final)}")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(final)
        if args.out.read_bytes() != final:
            raise SystemExit("verify failed: written output differs from buffer")
        print(f"wrote {args.out} ({len(final)} bytes)")
    else:
        print("dry-run only; no DAT written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
