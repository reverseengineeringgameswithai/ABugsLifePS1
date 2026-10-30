#!/usr/bin/env python3
"""Non-mutating survey of LEVEL01 geometry payloads (G15 terrain-candidate analysis).

Read-only. Walks the pass-1 trail rows, bridges each surviving row to its source record and payload
(per the G10/G11 model: trail row +0x10 -> source record; source +0x14 (non-bit3) / +0x1c (bit3) ->
payload), parses the payload header `{u32 count; Vertex verts[N] stride 0xc (s16 x,y,z; s16 pad;
u32 attr); primitive command stream}`, and reports each payload's vertex count, bounding box, a
flatness ratio (Y spread / max horizontal spread), the horizontal footprint area, and the
command-stream byte span (computed from the next payload boundary).

Purpose: rank candidates as terrain/ground (wide + flat + tessellated) vs grass/decor (tall + narrow),
WITHOUT editing anything. This does NOT prove which payload is the on-screen / tangible ground; that
needs runtime confirmation (break at fcn.80010000 and log a0). No collision/pathing inference.

Usage:
  python3 tools/survey_level01_payloads.py DAT/LEVEL01_LEVEL.DAT [--top N] [--terrain|--decor|--all]
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

DATBASE = 0x801607F8          # LEVEL01 runtime DATbase (LIKELY; for runtime addr column)
TRAIL = 0x1504
P3BASE = 0x3AFA
SRC_LO, SRC_HI = 0x45F0, 0x8BD8
PAY_LO, PAY_HI = 0x8BD8, 0x4F32C
VSTRIDE = 0xC


def main() -> int:
    ap = argparse.ArgumentParser(description="Survey LEVEL01 payloads (read-only).")
    ap.add_argument("dat", type=Path)
    ap.add_argument("--top", type=int, default=20)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--terrain", action="store_true", help="rank wide+flat (terrain-like) first")
    g.add_argument("--decor", action="store_true", help="rank tall+narrow (decor/grass-like) first")
    g.add_argument("--all", action="store_true", help="list by entry index")
    args = ap.parse_args()

    d = args.dat.read_bytes()
    u16 = lambda o: struct.unpack_from("<H", d, o)[0]
    s16 = lambda o: struct.unpack_from("<h", d, o)[0]
    u32 = lambda o: struct.unpack_from("<I", d, o)[0]

    def payload_of(src: int, flag: int) -> int:
        return u32(src + 0x1C) if (flag & 0x8) else u32(src + 0x14)

    # collect all payload pointers (pass1 + pass3) for command-stream boundary computation
    allpay = set()
    rows = []
    for e in range(484):
        row = TRAIL + e * 0x14
        src = u32(row + 0x10)
        if not (SRC_LO <= src < SRC_HI):
            continue
        flag = u16(row + 0x0E)
        pay = payload_of(src, flag)
        if PAY_LO <= pay <= PAY_HI:
            rows.append((e, src, flag, pay))
            allpay.add(pay)
    for i in range(140):
        a0 = P3BASE + i * 0x14
        src = u32(a0 + 2)
        if not (SRC_LO <= src < SRC_HI):
            continue
        for off in (0x14, 0x1C):
            p = u32(src + off)
            if PAY_LO <= p <= PAY_HI:
                allpay.add(p)
    bounds = sorted(allpay) + [PAY_HI]

    cands = []
    for (e, src, flag, pay) in rows:
        cnt = u32(pay)
        if not (0 < cnt < 4000):
            continue
        vb = pay + 4
        end = vb + cnt * VSTRIDE
        if end > len(d):
            continue
        xs = [s16(vb + i * VSTRIDE) for i in range(cnt)]
        ys = [s16(vb + i * VSTRIDE + 2) for i in range(cnt)]
        zs = [s16(vb + i * VSTRIDE + 4) for i in range(cnt)]
        xsp, ysp, zsp = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
        horiz = max(xsp, 1) * max(zsp, 1)
        flat = ysp / max(xsp, zsp, 1)
        nxt = min((b for b in bounds if b > pay), default=PAY_HI)
        cands.append(dict(e=e, src=src, flag=flag, pay=pay, cnt=cnt, xsp=xsp, ysp=ysp,
                          zsp=zsp, horiz=horiz, flat=flat, cmd=nxt - end))

    if args.decor:
        cands.sort(key=lambda c: (-c["flat"], -c["ysp"]))
        title = "DECOR/GRASS-LIKE (tall+narrow first)"
    elif args.all:
        cands.sort(key=lambda c: c["e"])
        title = "ALL (by entry index)"
    else:
        # terrain: wide+flat first. score = horiz area, require flat<1 to float terrain up
        cands.sort(key=lambda c: (c["flat"] >= 1.0, -c["horiz"]))
        title = "TERRAIN-LIKE (wide+flat first)"

    print(f"# {title}   ({len(cands)} payloads)   DATbase=0x{DATBASE:08x}")
    print(f"{'ent':>4} {'src':>7} {'b3':>2} {'payload':>8} {'runtime':>10} {'cnt':>4} "
          f"{'Xsp':>6} {'Ysp':>6} {'Zsp':>6} {'flat':>5} {'horiz':>10} {'cmdspan':>7}")
    for c in cands[: args.top]:
        print(f"{c['e']:>4} 0x{c['src']:05x} {int(bool(c['flag']&8)):>2} 0x{c['pay']:05x} "
              f"0x{DATBASE+c['pay']:08x} {c['cnt']:>4} {c['xsp']:>6} {c['ysp']:>6} {c['zsp']:>6} "
              f"{c['flat']:>5.2f} {c['horiz']:>10} 0x{c['cmd']:>5x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
