#!/usr/bin/env python3
"""Classify all type-0x3f placement entries in a LEVEL .DAT by source kind.

Labels are based on confirmed/candidate evidence recorded in ABL_RE_NOTES.md:
  0x14            grain            (confirmed)
  0x10..0x13      FLIK letters F/L/I/K (confirmed)
  0x21..0x24      FLIK trigger/marker actions (confirmed, not visible letters)
  0x29            orange seed-power token (confirmed; obj 0x16, counter 0x800a6598)
  0x2a            blue  seed-power token  (confirmed; obj 0x17, counter 0x800a6599)
  0x2b            green seed-power token  (confirmed; obj 0x19, counter 0x800a659a)
  0x2c..0x2d      seed-power token (candidate; not present/tested in LEVEL01)
  0x30            Dewdrop telescope / hint-view trigger (not a collectible)
Runtime coords = file coords << 5.

Usage:
  python tools/list_level_pickups.py DAT/LEVEL01_LEVEL.DAT
  python tools/list_level_pickups.py DAT/LEVEL01_LEVEL.DAT --kinds 0x29 0x2a 0x2b
"""
import struct, sys, argparse

LABELS = {
    0x10: "FLIK-F", 0x11: "FLIK-L", 0x12: "FLIK-I", 0x13: "FLIK-K",
    0x14: "grain",
    0x21: "FLIK-trig", 0x22: "FLIK-trig", 0x23: "FLIK-trig", 0x24: "FLIK-trig",
    0x29: "seed-orange", 0x2a: "seed-blue", 0x2b: "seed-green",
    0x2c: "seed-token?", 0x2d: "seed-token?",
    0x30: "telescope",
}
# per-kind powered-up object index (kind 0x29 hardcoded 0x16; 0x2a..0x2d from
# table 0x80078e90 = 17 19 18 2f); informational only.
SEED_OBJ = {0x29: 0x16, 0x2a: 0x17, 0x2b: 0x19, 0x2c: 0x18, 0x2d: 0x2f}
# per-kind seed counter byte (state address); informational.
SEED_CTR = {0x29: 0x800a6598, 0x2a: 0x800a6599, 0x2b: 0x800a659a,
            0x2c: 0x800a659b, 0x2d: 0x800a659c}

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def s32(b, o): return struct.unpack_from("<i", b, o)[0]

def type_3f(b):
    cnt = struct.unpack_from("<I", b, 0)[0]; off = 4
    for _ in range(cnt):
        n = u16(b, off); t = u16(b, off + 2); eoff = off + 4
        if t == 0x3f:
            return off, n, eoff
        off = eoff + n * 0x10
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dat")
    ap.add_argument("--kinds", type=lambda x: int(x, 0), nargs="*", default=None,
                    help="only show these source kinds")
    args = ap.parse_args()
    b = open(args.dat, "rb").read()
    rec = type_3f(b)
    if not rec:
        print("No type-0x3f record"); return
    recoff, n, eoff = rec
    print(f"file: {args.dat}")
    print(f"type-0x3f record @ {recoff:#x}, {n} entries\n")
    hdr = (f"{'idx':>3} {'entryoff':>8} {'yoff':>6} {'kind':>4} {'label':>11} "
           f"{'X':>7} {'Y':>7} {'Z':>7} | {'rtX':>9} {'rtY':>9} {'rtZ':>9} | extra")
    print(hdr); print("-"*len(hdr))
    counts = {}
    for i in range(n):
        o = eoff + i * 0x10
        k = b[o + 0xc]
        if args.kinds is not None and k not in args.kinds:
            continue
        counts[k] = counts.get(k, 0) + 1
        x, y, z = s32(b, o), s32(b, o+4), s32(b, o+8)
        lbl = LABELS.get(k, "?")
        extra = ""
        if k in SEED_OBJ:
            extra = f"seed_obj={SEED_OBJ[k]:#x} ctr={SEED_CTR[k]:#x}"
        print(f"{i:>3} {o:>#8x} {o+4:>#6x} {k:>#4x} {lbl:>11} "
              f"{x:>7} {y:>7} {z:>7} | {x<<5:>9} {y<<5:>9} {z<<5:>9} | {extra}")
    print("\ncounts by kind:")
    for k in sorted(counts):
        print(f"  {k:#04x} {LABELS.get(k,'?'):>11}: {counts[k]}")

if __name__ == "__main__":
    main()
