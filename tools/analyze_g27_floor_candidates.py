#!/usr/bin/env python3
"""G27 — read-only consumer-side decode/classification of count-validated fcn.80010000 payloads.

These five payload bases were captured by the operator at EXEC 0x80010000 (a0 = raw payload base,
[a0] = vertexCount), so they are count-validated REAL fcn.80010000 payloads (unlike the retracted
G17 Candidate B 0x801bdc58, which is compressed LEVEL.RAW source and is NOT decoded here).

For each candidate this decodes the CONFIRMED payload layout (G11):
    +0x00  u32 vertexCount
    +0x04  Vertex verts[N]  (stride 0xc: s16 x; s16 y; s16 z; s16 pad=0; u32 attr)
    ...    primitive command stream  (starts at +4 + N*0xc; ends at next-payload boundary / ffff ffff)
and reports: DAT offset, vertex-table range, bbox, flatness, local Y band (q25-q75), command-stream
start/span, a halfword reference scan (which vertex byte-offsets the command stream cites), and the
instancing count (how many pass-1/pass-3 source records bridge to this payload).

Read-only. No mutation, no patch, no build. Collision/pathing is NOT inferred.

Usage:
  python3 tools/analyze_g27_floor_candidates.py DAT/LEVEL01_LEVEL.DAT
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

DATBASE = 0x801607F8
FILESIZE = 0x51418
TRAIL = 0x1504
P3BASE = 0x3AFA
SRC_LO, SRC_HI = 0x45F0, 0x8BD8
PAY_LO, PAY_HI = 0x8BD8, 0x4F32C
VSTRIDE = 0xC

# Candidate runtime a0 bases captured at EXEC 0x80010000 (operator, Candidate B floor view).
CANDIDATES = [
    ("A", 0x801790C4, 0x53),
    ("B", 0x80199068, 0x30),
    ("C", 0x801994A8, 0x3A),
    ("D", 0x80198D40, 0x24),
    ("E", 0x8018DC58, 0x19),  # known instanced decor (G18b 0x2d460) — re-validated here
]


def quart(vals, q):
    s = sorted(vals)
    if not s:
        return 0
    i = (len(s) - 1) * q
    lo = int(i)
    hi = min(lo + 1, len(s) - 1)
    frac = i - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def main() -> int:
    dat = Path(sys.argv[1] if len(sys.argv) > 1 else "DAT/LEVEL01_LEVEL.DAT")
    d = dat.read_bytes()
    assert len(d) == FILESIZE, f"unexpected size 0x{len(d):x}"
    u16 = lambda o: struct.unpack_from("<H", d, o)[0]
    s16 = lambda o: struct.unpack_from("<h", d, o)[0]
    u32 = lambda o: struct.unpack_from("<I", d, o)[0]

    # ---- build the set of all referenced payloads (for command-stream boundary) and the
    #      instancing histogram (payload -> how many source records bridge to it) ----
    pay_refs: dict[int, int] = {}
    allpay: set[int] = set()

    def add_ref(p):
        if PAY_LO <= p <= PAY_HI:
            allpay.add(p)
            pay_refs[p] = pay_refs.get(p, 0) + 1

    for e in range(484):
        row = TRAIL + e * 0x14
        src = u32(row + 0x10)
        if not (SRC_LO <= src < SRC_HI):
            continue
        flag = u16(row + 0x0E)
        add_ref(u32(src + 0x1C) if (flag & 0x8) else u32(src + 0x14))
    for i in range(140):
        a0 = P3BASE + i * 0x14
        src = u32(a0 + 2)
        if not (SRC_LO <= src < SRC_HI):
            continue
        for off in (0x14, 0x1C):
            add_ref(u32(src + off))
    bounds = sorted(allpay) + [PAY_HI]

    print(f"# G27 count-validated payload decode   DATbase=0x{DATBASE:08x}  filesize=0x{FILESIZE:x}")
    print(f"# pristine {dat}  ({len(allpay)} distinct referenced payloads)\n")

    for name, a0, claimed in CANDIDATES:
        off = a0 - DATBASE
        print("=" * 78)
        print(f"Candidate {name}:  a0=0x{a0:08x}  DAT off=0x{off:05x}  claimed count=0x{claimed:x}/{claimed}")
        if not (0 <= off < FILESIZE):
            print(f"  !! DAT offset out of range — NOT a DAT-backed payload")
            continue
        cnt = u32(off)
        print(f"  [a0] vertexCount = 0x{cnt:08x} / {cnt}   (claimed {claimed})  "
              f"{'MATCH' if cnt == claimed else '*** MISMATCH ***'}")
        if not (0 < cnt < 4000):
            print(f"  !! implausible vertex count — reject")
            continue

        vb = off + 4
        vend = vb + cnt * VSTRIDE
        print(f"  vertex table: [0x{vb:05x}, 0x{vend:05x})   "
              f"runtime [0x{DATBASE+vb:08x}, 0x{DATBASE+vend:08x})")
        if vend > len(d):
            print("  !! vertex table runs past EOF — reject")
            continue

        xs = [s16(vb + i * VSTRIDE) for i in range(cnt)]
        ys = [s16(vb + i * VSTRIDE + 2) for i in range(cnt)]
        zs = [s16(vb + i * VSTRIDE + 4) for i in range(cnt)]
        pads = [s16(vb + i * VSTRIDE + 6) for i in range(cnt)]
        nonzero_pad = sum(1 for p in pads if p != 0)
        xsp, ysp, zsp = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
        flat = ysp / max(xsp, zsp, 1)
        yq25, yq75 = quart(ys, 0.25), quart(ys, 0.75)
        print(f"  bbox X[{min(xs)},{max(xs)}]({xsp})  Y[{min(ys)},{max(ys)}]({ysp})  "
              f"Z[{min(zs)},{max(zs)}]({zsp})")
        print(f"  flatness Ysp/max(Xsp,Zsp) = {flat:.3f}   "
              f"Y q25-q75 = {yq25:.0f}-{yq75:.0f} (band {yq75-yq25:.0f})   "
              f"pad!=0 in {nonzero_pad}/{cnt} verts")

        # command stream
        nxt = min((b for b in bounds if b > off), default=PAY_HI)
        cmd_start = vend
        # find ffff ffff terminator within [cmd_start, nxt)
        term = None
        o = cmd_start
        while o + 4 <= nxt:
            if u32(o) == 0xFFFFFFFF:
                term = o
                break
            o += 2
        cmd_end = term if term is not None else nxt
        span = cmd_end - cmd_start
        print(f"  command stream: start 0x{cmd_start:05x}  next-payload 0x{nxt:05x}  "
              f"terminator {'0x%05x' % term if term is not None else 'none'}  span 0x{span:x}/{span}")

        # halfword reference scan: a halfword that is a multiple of 0xc and < cnt*0xc is a vertex byte-offset
        maxoff = cnt * VSTRIDE
        refhist = [0] * cnt
        ctrl_like = 0
        nh = 0
        o = cmd_start
        while o + 2 <= cmd_end:
            h = u16(o)
            if h % VSTRIDE == 0 and 0 <= h < maxoff:
                refhist[h // VSTRIDE] += 1
            elif (h & 0x1F) <= 7 and h < 0x1000:
                ctrl_like += 1  # plausible control word (type<=7, small)
            nh += 1
            o += 2
        refd = sum(1 for c in refhist if c > 0)
        total_refs = sum(refhist)
        once = sum(1 for c in refhist if c == 1)
        print(f"  cmd halfwords={nh}  vertex-offset refs total={total_refs}  "
              f"distinct verts referenced={refd}/{cnt}  (once={once})  ctrl-like words={ctrl_like}")

        # first few command halfwords (raw)
        head = " ".join(f"{u16(cmd_start + 2*i):04x}" for i in range(min(12, span // 2)))
        print(f"  cmd head: {head}")

        # first 0x40 bytes of payload (eyeball: count then s16 triples)
        raw = d[off:off + 0x40]
        print("  first 0x40 bytes:")
        for r in range(0, 0x40, 16):
            print("    " + " ".join(f"{b:02x}" for b in raw[r:r + 16]))

        # instancing
        nref = pay_refs.get(off, 0)
        print(f"  INSTANCING: {nref} source-record bridge(s) point at this payload  "
              f"({'unique/drawn-once' if nref <= 1 else 'INSTANCED ×%d -> decor tell' % nref})")

        # first 3 vertices decoded
        print("  v0..v2:")
        for i in range(min(3, cnt)):
            b = vb + i * VSTRIDE
            print(f"    v{i} = (x={s16(b)}, y={s16(b+2)}, z={s16(b+4)}) pad={s16(b+6)} "
                  f"attr=0x{u32(b+8):08x}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
