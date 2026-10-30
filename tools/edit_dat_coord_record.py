#!/usr/bin/env python3
"""Edit the (X,Y,Z) entries of an uncompressed top-level LEVEL.DAT coord record (§3).

LEVEL.DAT begins with a top-level record array (count u32 @ 0; each record: u16 count,
s16 type, then payload). Several records hold flat (X,Y,Z) coordinate entries (stride 0xc,
file units, runtime = <<5):

  rec1  @ 0x468  type 1   104 entries = **mover-VM PATH WAYPOINTS** — the object/enemy
                          movement routes consumed by FUNC_8004C13C op9 (set-target).
                          Editing these relocates a mover's path (live-proven: poke -> object moves).
  rec2/3/4 @ 0x94c/0xa10/0xad4  types 11/12/13  16 entries each = **chaser spawn-area
                          records** (bee/mosquito/spider): header + 16 (X,Y,Z) waypoints;
                          spawn fn 0x8004d698 reads them via ptr table 0x80096dc8 and
                          derives the spawn pos from WP0(+0x4)/WP1(+0x10). Editing moves
                          the spawn/patrol area. (Spawn is state-machine-gated, so the
                          record is NOT read per-frame.)

This lists those records and translates / sets their coordinate entries (size-preserving,
no relocation — coords are not baked offsets). Dry-run unless --write --out. Records are
addressed by their file offset; type-0x3f pickups (rec0) are NOT handled here (use the
type-0x3f tools).
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import dat_reloc

PT = 0xc  # (s32 X, s32 Y, s32 Z)

# Friendly labels for the known coord records (offset -> (name, note)).
KNOWN = {
    0x468: ("mover-VM waypoints", "rec1 type 1 — object/enemy path routes (FUNC_8004C13C op9)"),
    0x94c: ("chaser spawn area 11", "rec2 type 11 — chaser spawn/patrol area (spawn fn 0x8004d698)"),
    0xa10: ("chaser spawn area 12", "rec3 type 12 — chaser spawn/patrol area (spawn fn 0x8004d698)"),
    0xad4: ("chaser spawn area 13", "rec4 type 13 — chaser spawn/patrol area (spawn fn 0x8004d698)"),
}


def coord_records(d: bytes):
    """Yield (offset, type, count) for top-level records whose payload is (X,Y,Z) entries.
    type 0x3f (pickups) is excluded; negative types (trailing tables) are excluded."""
    src = dat_reloc.DAT(d)
    n = src.u32(0); off = 4
    for _ in range(n):
        cnt = src.u16(off); typ = src.s16(off + 2); sz = src.record_size(off)
        if 0 < typ < 0x3f:                      # positive non-pickup -> 0xc-stride coord entries
            yield off, typ, cnt
        off += sz


def read_entries(d: bytes, off: int):
    cnt = struct.unpack_from("<H", d, off)[0]
    return [struct.unpack_from("<iii", d, off + 4 + i * PT) for i in range(cnt)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Edit (X,Y,Z) entries of an uncompressed LEVEL.DAT coord record.")
    ap.add_argument("dat", type=Path)
    ap.add_argument("--list", action="store_true", help="list coord records (type 1/11/12/13) and exit")
    ap.add_argument("--record", type=lambda s: int(s, 0), help="file offset of the record to edit")
    ap.add_argument("--move", metavar="DX:DY:DZ", help="translate ALL entries of --record by (dx,dy,dz)")
    ap.add_argument("--set-entry", action="append", default=[], metavar="I:X:Y:Z",
                    help="set entry I of --record to absolute X,Y,Z; may repeat")
    ap.add_argument("--write", action="store_true", help="write --out; default dry-run")
    ap.add_argument("--out", type=Path, help="output DAT; required with --write")
    args = ap.parse_args()

    data = bytearray(args.dat.read_bytes())

    if args.list or not args.record:
        for off, typ, cnt in coord_records(bytes(data)):
            name, note = KNOWN.get(off, ("?", ""))
            pts = read_entries(bytes(data), off)
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
            cx, cy, cz = sum(xs)//cnt, sum(ys)//cnt, sum(zs)//cnt
            print(f"@ {off:#06x}  type {typ:2d}  {cnt:3d} entries  [{name}]")
            print(f"     centroid file=({cx},{cy},{cz}) runtime=({cx<<5},{cy<<5},{cz<<5})  "
                  f"X[{min(xs)},{max(xs)}] Y[{min(ys)},{max(ys)}] Z[{min(zs)},{max(zs)}]")
            if note:
                print(f"     {note}")
        if args.list:
            return 0
        raise SystemExit("provide --record OFF with --move or --set-entry")

    off = args.record
    valid = {o for o, _t, _c in coord_records(bytes(data))}
    if off not in valid:
        raise SystemExit(f"{off:#x} is not a top-level coord record (valid: {[hex(o) for o in sorted(valid)]})")
    if args.write and args.out is None:
        raise SystemExit("--write requires --out")
    if args.out is not None and args.out.resolve() == args.dat.resolve():
        raise SystemExit("refusing in-place edit: --out must differ from input")
    if not args.move and not args.set_entry:
        raise SystemExit("provide --move DX:DY:DZ or --set-entry I:X:Y:Z")

    cnt = struct.unpack_from("<H", data, off)[0]
    orig = bytes(data)
    if args.move:
        dx, dy, dz = (int(x, 0) for x in args.move.split(":"))
        for i in range(cnt):
            o = off + 4 + i * PT
            x, y, z = struct.unpack_from("<iii", data, o)
            struct.pack_into("<iii", data, o, x + dx, y + dy, z + dz)
        print(f"record @ {off:#x}: translated {cnt} entries by ({dx},{dy},{dz})")
    for spec in args.set_entry:
        i, x, y, z = (int(v, 0) for v in spec.split(":"))
        if not (0 <= i < cnt):
            raise SystemExit(f"entry {i} outside 0..{cnt-1}")
        struct.pack_into("<iii", data, off + 4 + i * PT, x, y, z)
        print(f"record @ {off:#x}: set entry {i} -> ({x},{y},{z})")

    # verify size-preserving + only this record's payload changed
    if len(data) != len(orig):
        raise SystemExit("verify failed: size changed")
    span = 4 + cnt * PT
    if orig[:off] != bytes(data[:off]) or orig[off + span:] != bytes(data[off + span:]):
        raise SystemExit("verify failed: bytes outside the edited record changed")

    if args.write:
        assert args.out is not None
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(bytes(data))
        if args.out.read_bytes() != bytes(data):
            raise SystemExit("verify failed: written output differs")
        print(f"wrote {args.out} ({len(data)} bytes)")
    else:
        print("dry-run only; no DAT written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
