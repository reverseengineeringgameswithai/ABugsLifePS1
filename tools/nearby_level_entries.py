#!/usr/bin/env python3
"""Spatial-neighbor search within a LEVEL .DAT type-0x3f placement record.

Parses the type-0x3f record (0x10-byte entries: X/Y/Z s32 at +0/+4/+8, source
kind byte at +0xc), then lists the nearest entries to a chosen anchor entry,
sorted by Euclidean distance in file coordinate units.

Usage:
  python tools/nearby_level_entries.py DAT/LEVEL01_LEVEL.DAT --anchor-entry 0 -n 20
  python tools/nearby_level_entries.py DAT/LEVEL01_LEVEL.DAT --anchor-xyz -8526 -3488 4544
"""
import struct, sys, argparse, math

def s32(b, o): return struct.unpack_from("<i", b, o)[0]
def u16(b, o): return struct.unpack_from("<H", b, o)[0]

def parse_dat_records(b):
    """Walk top-level DAT records per fcn.8001cdc0 rules. Returns list of
    (rec_type, rec_offset, entry_count, entries_offset)."""
    count = struct.unpack_from("<I", b, 0)[0]
    recs = []
    off = 4
    for _ in range(count):
        if off + 4 > len(b):
            break
        n = u16(b, off)           # entry count
        rtype = u16(b, off + 2)   # record type
        entries_off = off + 4
        recs.append((rtype, off, n, entries_off))
        off = entries_off + n * 0x10
    return recs

def get_type_3f_entries(b):
    for rtype, recoff, n, eoff in parse_dat_records(b):
        if rtype == 0x3f:
            ents = []
            for i in range(n):
                o = eoff + i * 0x10
                ents.append(dict(
                    idx=i, off=o,
                    x=s32(b, o), y=s32(b, o + 4), z=s32(b, o + 8),
                    kind=b[o + 0xc],
                ))
            return recoff, ents
    return None, []

def all_record_entries(b):
    """Every 0x10-byte entry across all top-level records, interpreting
    +0/+4/+8 as XYZ and +0xc as a kind/type byte (heuristic)."""
    out = []
    for rtype, recoff, n, eoff in parse_dat_records(b):
        for i in range(n):
            o = eoff + i * 0x10
            if o + 0x10 > len(b):
                break
            out.append(dict(rtype=rtype, recoff=recoff, idx=i, off=o,
                            x=s32(b, o), y=s32(b, o + 4), z=s32(b, o + 8),
                            kind=b[o + 0xc]))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dat")
    ap.add_argument("--anchor-entry", type=int, default=None,
                    help="raw entry index to use as anchor")
    ap.add_argument("--anchor-xyz", type=int, nargs=3, default=None,
                    help="explicit X Y Z anchor in file units")
    ap.add_argument("-n", type=int, default=20)
    ap.add_argument("--all-records", action="store_true",
                    help="scan every record type, not just type-0x3f")
    args = ap.parse_args()

    b = open(args.dat, "rb").read()
    if args.all_records:
        if not args.anchor_xyz:
            print("--all-records requires --anchor-xyz"); return
        ax, ay, az = args.anchor_xyz
        ents = all_record_entries(b)
        print(f"all-records scan: {len(ents)} entries across "
              f"{len(set(e['recoff'] for e in ents))} records")
        print(f"anchor = ({ax},{ay},{az})\n")
        for e in ents:
            e["dist"] = math.sqrt((e["x"]-ax)**2 + (e["y"]-ay)**2 + (e["z"]-az)**2)
        ranked = sorted(ents, key=lambda e: e["dist"])
        print(f"{'rank':>4} {'rtype':>6} {'idx':>4} {'entryoff':>9} {'kind':>5} "
              f"{'X':>8} {'Y':>8} {'Z':>8} {'dist':>10}")
        for rank, e in enumerate(ranked[:args.n]):
            print(f"{rank:>4} {e['rtype']:>#6x} {e['idx']:>4} {e['off']:>#9x} "
                  f"{e['kind']:>#5x} {e['x']:>8} {e['y']:>8} {e['z']:>8} {e['dist']:>10.0f}")
        return
    recoff, ents = get_type_3f_entries(b)
    if not ents:
        print("No type-0x3f record found."); return
    print(f"type-0x3f record @ file {recoff:#x}; {len(ents)} entries")

    if args.anchor_xyz:
        ax, ay, az = args.anchor_xyz
        anchor_desc = f"explicit ({ax},{ay},{az})"
    else:
        ai = args.anchor_entry if args.anchor_entry is not None else 0
        a = ents[ai]
        ax, ay, az = a["x"], a["y"], a["z"]
        anchor_desc = f"entry {ai} kind {a['kind']:#04x} ({ax},{ay},{az})"
    print(f"anchor = {anchor_desc}\n")

    for e in ents:
        e["dist"] = math.sqrt((e["x"]-ax)**2 + (e["y"]-ay)**2 + (e["z"]-az)**2)
    ranked = sorted(ents, key=lambda e: e["dist"])

    print(f"{'rank':>4} {'idx':>4} {'entryoff':>9} {'kind':>5} {'grain':>5} "
          f"{'X':>8} {'Y':>8} {'Z':>8} {'dist':>10}")
    for rank, e in enumerate(ranked[:args.n]):
        g = "yes" if e["kind"] == 0x14 else ""
        flag = ""
        if e["kind"] != 0x14 and rank > 0:
            flag = "  <-- NON-GRAIN"
        print(f"{rank:>4} {e['idx']:>4} {e['off']:>#9x} {e['kind']:>#5x} {g:>5} "
              f"{e['x']:>8} {e['y']:>8} {e['z']:>8} {e['dist']:>10.0f}{flag}")

    # where does each non-grain entry rank overall?
    print("\nAll non-grain (kind != 0x14) entries by distance rank:")
    for rank, e in enumerate(ranked):
        if e["kind"] != 0x14:
            print(f"  rank {rank:>3}  idx {e['idx']:>3}  off {e['off']:#06x}  "
                  f"kind {e['kind']:#04x}  XYZ ({e['x']},{e['y']},{e['z']})  dist {e['dist']:.0f}")

if __name__ == "__main__":
    main()
