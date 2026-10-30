#!/usr/bin/env python3
"""Patch the Y coordinate of one or more type-0x3f entries in a LEVEL .DAT.

Selects entries by raw entry index or by source kind, applies a file-unit delta
to the Y s32 at entry+0x4, and writes a new DAT (size-preserving). Safe: requires
--out unless --in-place; verifies output size; prints before/after bytes.

Usage:
  # move all entries of kinds 0x10,0x11,0x12,0x13 up by 2048 file units
  python tools/patch_level_entry.py DAT/LEVEL01_LEVEL.DAT \
      --kinds 0x10 0x11 0x12 0x13 --dy -2048 --out DAT/LEVEL01_LEVEL_FLIK10_UP_BIG.DAT
  # move raw entry 50 only
  python tools/patch_level_entry.py DAT/LEVEL01_LEVEL.DAT --entries 50 --dy -2048 --out OUT.DAT
"""
import struct, sys, argparse

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def s32(b, o): return struct.unpack_from("<i", b, o)[0]

def type_3f_record(b):
    count = struct.unpack_from("<I", b, 0)[0]
    off = 4
    for _ in range(count):
        n = u16(b, off); rtype = u16(b, off + 2); eoff = off + 4
        if rtype == 0x3f:
            return off, n, eoff
        off = eoff + n * 0x10
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dat")
    ap.add_argument("--entries", type=lambda x: int(x, 0), nargs="*", default=[])
    ap.add_argument("--kinds", type=lambda x: int(x, 0), nargs="*", default=[])
    ap.add_argument("--dx", type=int, default=0, help="file-unit delta on X (entry+0x0; runtime = dx<<5)")
    ap.add_argument("--dy", type=int, default=0, help="file-unit delta on Y (entry+0x4; runtime = dy<<5)")
    ap.add_argument("--dz", type=int, default=0, help="file-unit delta on Z (entry+0x8; runtime = dz<<5)")
    ap.add_argument("--out")
    ap.add_argument("--in-place", action="store_true")
    args = ap.parse_args()

    b = bytearray(open(args.dat, "rb").read())
    rec = type_3f_record(b)
    if not rec:
        print("No type-0x3f record"); sys.exit(1)
    recoff, n, eoff = rec

    sel = set(args.entries)
    for i in range(n):
        o = eoff + i * 0x10
        if b[o + 0xc] in args.kinds:
            sel.add(i)
    if not sel:
        print("No entries selected"); sys.exit(1)
    if args.dx == 0 and args.dy == 0 and args.dz == 0:
        print("Refusing: at least one of --dx/--dy/--dz must be nonzero"); sys.exit(1)

    print(f"type-0x3f @ {recoff:#x}, {n} entries; runtime deltas "
          f"dx={args.dx<<5} dy={args.dy<<5} dz={args.dz<<5}")
    deltas = (("X", 0, args.dx), ("Y", 4, args.dy), ("Z", 8, args.dz))
    for i in sorted(sel):
        o = eoff + i * 0x10
        msg = [f"  idx {i:>3} kind {b[o+0xc]:#04x} entryoff {o:#06x}"]
        for name, foff, d in deltas:
            if d:
                fo = o + foff
                old = s32(b, fo); oldb = bytes(b[fo:fo+4])
                struct.pack_into("<i", b, fo, old + d)
                msg.append(f"{name}@{fo:#06x} {old}->{old+d} ({oldb.hex()}->{bytes(b[fo:fo+4]).hex()})")
        print("  ".join(msg))

    if args.in_place:
        out = args.dat
    elif args.out:
        out = args.out
    else:
        print("Refusing: provide --out or --in-place"); sys.exit(1)
    open(out, "wb").write(b)
    assert len(b) == len(open(args.dat, "rb").read()) if not args.in_place else True
    print(f"wrote {out} ({len(b)} bytes)")

if __name__ == "__main__":
    main()
