#!/usr/bin/env python3
"""tools/edit_chunk35_record.py -- author the chunk-35 master mesh on disc.

The decode in docs/CHUNK35_MASTER_MESH_DECODE.md (+ Canon SYS_chunk35_master_mesh) says a chunk-35
primitive is `RGB | GP0-command` followed by GP0-shaped fields, with four vertices at +0x04, +0x0C,
+0x14, +0x1C -- each an XY-packed word plus a Z word. This tool is the test of that claim: it edits
vertices THROUGH the grammar and writes a bootable LEVEL.RAW.

Why this is the decisive experiment: a blanket 0x30-STRIDE Y edit over this chunk is recorded as
CRASHING the load (2026-07-04), because a fixed stride walks straight through command bytes once a
0x24 triangle record appears. A grammar-driven edit touches only vertex words. If the naive edit
crashes and this one boots AND moves the walls, the grammar is right.

Modes
  --identity          recompress only, no edit  (control: isolates the codec round-trip)
  --record N --dy D   add D to record N's four vertex Y values
  --all-dy D          add D to EVERY record's four vertex Y values (the grammar-driven blanket)
  --list              print each record: offset, command, vertices

Every write re-walks the edited chunk and refuses to emit if the grammar no longer accounts for
every byte -- an edit that silently corrupts the stream is exactly the failure this is testing for.
"""
from __future__ import annotations
import argparse
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import edit_collision_sector as ECS      # noqa: E402
import decode_level_raw as DEC           # noqa: E402
import recompress_level_raw as REC       # noqa: E402

CHUNK = 35
DATA_START = 0x0C
VERT_OFF = (0x04, 0x0C, 0x14, 0x1C)      # XY-packed word per vertex; Z is the word after


def gp0_words(cmd: int) -> int:
    """Standard GP0 polygon field rules -- the same arithmetic FUNC_800172DC's dispatch implies."""
    if not 0x20 <= cmd <= 0x3F:
        return 0
    nverts = 4 if cmd & 0x08 else 3
    return (nverts if cmd & 0x10 else 1) + nverts + (nverts if cmd & 0x04 else 0)


def walk(dec: bytes, off: int = DATA_START):
    """Yield (offset, cmd, size) per primitive and return (records, groups, end_offset)."""
    recs, groups, p = [], 0, off
    n = len(dec)
    while p < n:
        while p + 4 <= n and gp0_words(dec[p + 3]):
            cmd = dec[p + 3]
            size = gp0_words(cmd) * 4
            if p + size > n:
                p = n
                break
            recs.append((p, cmd, size))
            p += size
        if p >= n:
            break
        if p + 8 > n:
            p = n                           # trailing bytes after the last group (2 in LEVEL01)
            break
        if struct.unpack_from("<I", dec, p)[0] != 0:
            return recs, groups, p          # grammar broke here
        if p + 4 < n and gp0_words(dec[p + 7]):
            p += 4                          # separator, not a terminator
            continue
        p += 4
        vc = struct.unpack_from("<I", dec, p)[0]
        p += 4
        if vc > 0xFFFF or p + vc * 8 > n:
            return recs, groups, p - 4
        p += vc * 8
        while p + 4 <= n and not (p % 4 == 0 and gp0_words(dec[p + 3])):
            p += 2
        if p > n:
            p = n
        groups += 1
    return recs, groups, min(p, n)


def verts(dec: bytes, rec_off: int, cmd: int):
    """The record's vertices as (x, y, z) -- 4 for a quad command, 3 otherwise."""
    n = 4 if cmd & 0x08 else 3
    out = []
    for i in range(n):
        o = rec_off + VERT_OFF[i]
        x, y = struct.unpack_from("<hh", dec, o)
        z = struct.unpack_from("<h", dec, o + 4)[0]
        out.append((x, y, z))
    return out


def shift_y(buf: bytearray, rec_off: int, cmd: int, dy: int) -> int:
    n = 4 if cmd & 0x08 else 3
    for i in range(n):
        o = rec_off + VERT_OFF[i] + 2                       # the Y half of the XY word
        y = struct.unpack_from("<h", buf, o)[0]
        struct.pack_into("<h", buf, o, max(-32768, min(32767, y + dy)))
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "REBUILD/files/LEVEL01/LEVEL.RAW"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--identity", action="store_true")
    ap.add_argument("--record", type=int)
    ap.add_argument("--dy", type=int, default=0)
    ap.add_argument("--all-dy", type=int)
    ap.add_argument("--only-cmd", type=lambda v: int(v, 0), default=None,
                    help="restrict --all-dy to this GP0 command. The 0x34 path loads lwc2 $1..$5 "
                         "from +0x08..+0x18, NOT the quad offsets, so its vertex layout is unproven.")
    ap.add_argument("--range", nargs=2, type=int, metavar=("FIRST", "LAST"),
                    help="with --dy: shift records FIRST..LAST inclusive (bisects how many a load tolerates)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    raw = open(a.raw, "rb").read()
    chunks = ECS.split_chunks(raw)
    comp = chunks[CHUNK][3]
    dec = bytearray(DEC.decompress_chunk(comp))
    recs, groups, end = walk(bytes(dec))
    print(f"[chunk35] {len(dec)} B: {len(recs)} records, {groups} groups, walk ends +0x{end:x} "
          f"({'EXACT' if end == len(dec) else 'RESIDUAL'})")
    if end != len(dec):
        return 2

    if a.list:
        for i, (off, cmd, size) in enumerate(recs):
            vs = verts(bytes(dec), off, cmd)
            span_y = max(v[1] for v in vs) - min(v[1] for v in vs)
            span_x = max(v[0] for v in vs) - min(v[0] for v in vs)
            print(f"  rec {i:3d} +0x{off:05x} cmd=0x{cmd:02x} size=0x{size:02x} "
                  f"spanX={span_x:6d} spanY={span_y:6d} v={vs}")
        return 0

    touched = 0
    if a.identity:
        label = "identity (recompress only)"
    elif a.all_dy is not None:
        n_rec = 0
        for off, cmd, _s in recs:
            if a.only_cmd is not None and cmd != a.only_cmd:
                continue
            touched += shift_y(dec, off, cmd, a.all_dy)
            n_rec += 1
        sel = f"cmd=0x{a.only_cmd:02x} only" if a.only_cmd is not None else "ALL commands"
        label = f"{n_rec}/{len(recs)} records ({sel}), dy={a.all_dy:+d} ({touched} vertices)"
    elif a.range is not None:
        lo, hi = a.range
        for i, (off, cmd, _s) in enumerate(recs):
            if lo <= i <= hi:
                touched += shift_y(dec, off, cmd, a.dy)
        label = f"records {lo}..{hi} ({hi-lo+1} of {len(recs)}), dy={a.dy:+d} ({touched} vertices)"
    elif a.record is not None:
        if not 0 <= a.record < len(recs):
            print(f"[chunk35] record {a.record} out of range 0..{len(recs)-1}")
            return 2
        off, cmd, _s = recs[a.record]
        before = verts(bytes(dec), off, cmd)
        touched = shift_y(dec, off, cmd, a.dy)
        after = verts(bytes(dec), off, cmd)
        label = f"record {a.record} @+0x{off:05x} cmd=0x{cmd:02x}, dy={a.dy:+d}"
        print(f"  before {before}")
        print(f"  after  {after}")
    else:
        print("[chunk35] pick --identity, --record N --dy D, --all-dy D, or --list")
        return 2

    # STIMULUS CHECK: the grammar must still account for every byte after the edit.
    recs2, groups2, end2 = walk(bytes(dec))
    if (len(recs2), groups2, end2) != (len(recs), groups, end):
        print(f"[chunk35] REFUSING: edit broke the grammar "
              f"({len(recs2)} recs / {groups2} groups / end +0x{end2:x})")
        return 2

    header6 = comp[8:0x0E]
    newcomp = REC.compress_chunk(bytes(dec), header6)
    if bytes(DEC.decompress_chunk(newcomp)) != bytes(dec):
        print("[chunk35] REFUSING: recompress round-trip mismatch")
        return 2
    coff = chunks[CHUNK][0]
    out = raw[:coff] + newcomp + raw[coff + len(comp):]
    open(a.out, "wb").write(out)
    print(f"[chunk35] {label}")
    print(f"[chunk35] chunk {len(comp)} -> {len(newcomp)} B; RAW {len(raw)} -> {len(out)} B -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
