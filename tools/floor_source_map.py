#!/usr/bin/env python3
"""Per-region floor-source map for LEVEL01 (§1 residual #1 / GAP-0023).

"At a clicked world XZ, which FUNC_80010000 floor payload draws it?" — the lookup the
editor (and tools/sculpt_terrain.py) needs to sculpt the floor *anywhere* without naming
a payload by hand. Built offline from the LEVEL.DAT node array (GAP-0023): each node is
0x18 bytes — s32 T_obj @+0/4/8, marker @+0x10 (0xC0080000), payload file-offset @+0x14 —
and the visible floor is placed as **world = T_obj + v_local** (translation only; no
flip/scale for LEVEL01 floor). For each floor payload we read its local vertices
(+0x00 u32 count, +0x04 verts stride 0xc: s16 x,y,z,pad,u32 attr), translate by T_obj,
and record the world XZ footprint (bbox + Y band). A query XZ returns the covering
payload(s), most-specific (smallest footprint) first.

Coordinates are the placement/world (node) frame = **runtime >> 5** (so file/node units;
Flik runtime XZ ÷32 lands in this frame). Output offsets feed sculpt_terrain.py --payload-off.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

NODE_STRIDE = 0x18
VPT = 0xc


def node_anchors(d: bytes, base=0x45F0, marker=0xC0080000, pay_lo=0x10000, pay_hi=None):
    """{payload_off: (Tx,Ty,Tz)} from the contiguous marked node run."""
    if pay_hi is None:
        # Appended/repointed native payloads legitimately live anywhere below the
        # current DAT EOF.  The historical 0x51418 ceiling was one old file size
        # and silently hid every second-and-later append from coverage tooling.
        pay_hi = len(d) - 1
    out = {}
    o = base
    while o + NODE_STRIDE <= len(d):
        if struct.unpack_from("<I", d, o + 0x10)[0] != marker:
            break
        pay = struct.unpack_from("<I", d, o + 0x14)[0]
        if pay_lo <= pay <= int(pay_hi):
            out.setdefault(pay, struct.unpack_from("<iii", d, o))
        o += NODE_STRIDE
    return out


def payload_world_bbox(d: bytes, pay: int, tobj):
    cnt = struct.unpack_from("<I", d, pay)[0]
    if not (0 < cnt < 100000):
        return None
    vt = pay + 4
    tx, ty, tz = tobj
    xs = []; ys = []; zs = []
    for i in range(cnt):
        x, y, z = struct.unpack_from("<hhh", d, vt + i * VPT)
        xs.append(x + tx); ys.append(y + ty); zs.append(z + tz)
    return (cnt, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def build_map(d: bytes):
    """[(payload_off, count, x0,x1,y0,y1,z0,z1, area)] sorted by ascending XZ area."""
    recs = []
    for pay, tobj in node_anchors(d).items():
        bb = payload_world_bbox(d, pay, tobj)
        if bb is None:
            continue
        cnt, x0, x1, y0, y1, z0, z1 = bb
        area = (x1 - x0) * (z1 - z0)
        recs.append((pay, cnt, x0, x1, y0, y1, z0, z1, area))
    recs.sort(key=lambda r: r[-1])
    return recs


def query(recs, X, Z):
    """Payloads whose XZ bbox contains (X,Z), most-specific (smallest) first."""
    return [r for r in recs if r[2] <= X <= r[3] and r[6] <= Z <= r[7]]


def main() -> int:
    ap = argparse.ArgumentParser(description="LEVEL01 per-region floor-source map (world XZ -> payload).")
    ap.add_argument("dat", type=Path)
    ap.add_argument("--list", action="store_true", help="list all floor payloads + world footprints")
    ap.add_argument("--query", metavar="X:Z", help="world/node XZ (file units = runtime>>5); list covering payloads")
    ap.add_argument("--query-runtime", metavar="X:Z", help="runtime XZ (will be >>5 to the node frame)")
    args = ap.parse_args()

    d = args.dat.read_bytes()
    recs = build_map(d)

    if args.list or (not args.query and not args.query_runtime):
        print(f"{len(recs)} floor payloads in the node array (world = T_obj + v_local):")
        for pay, cnt, x0, x1, y0, y1, z0, z1, area in recs:
            print(f"  payload {pay:#07x}  {cnt:3d}v  X[{x0},{x1}] Z[{z0},{z1}] Y[{y0},{y1}]  area={area}")
        return 0

    if args.query_runtime:
        X, Z = (int(v, 0) >> 5 for v in args.query_runtime.split(":"))
    else:
        X, Z = (int(v, 0) for v in args.query.split(":"))
    hits = query(recs, X, Z)
    print(f"query world XZ=({X},{Z}) [node frame]:")
    if not hits:
        print("  no floor payload covers this XZ (may be chunk-35 / occluded fallback)")
        return 1
    for pay, cnt, x0, x1, y0, y1, z0, z1, area in hits:
        cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
        print(f"  payload {pay:#07x}  {cnt}v  X[{x0},{x1}] Z[{z0},{z1}] Y[{y0},{y1}]  centroid=({cx},{cz})")
    print(f"-> most specific: sculpt_terrain.py --payload-off {hits[0][0]:#x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
