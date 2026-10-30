#!/usr/bin/env python3
"""Scenery/decor object catalog for LEVEL01 (§11.3a / step 9).

Enumerates the static decor/prop meshes and where each is instanced. The pass-1 instance
table (stride 0x14 @ the DAT trailing base) places props by **translation only** — each
record is pos(+0/4/8) + extent(+0xc) + flags(+0xe) + a NODE-record ptr(+0x10). The node
record (0x18 stride, marker 0xC0080000) bridges to the mesh PAYLOAD at node+0x14 (or +0x1c
when pass-1 flag bit3 is set) and carries an AABB (two ±scalar triples) — **NOT a rotation
matrix**, so there is no per-instance rotation (§11.4): a prop's orientation is baked into
its payload vertices. The meshes are **inline FUNC_80010000 payloads in LEVEL.DAT**, not
`.ALL`/`.ANM` model files, so they have no embedded names — this catalog classifies them
GEOMETRICALLY (semantic "mushroom/fence/rock" labels need a visual pass per mesh).

Output: per-mesh (payload) instance count, local geometry (vtx/bbox/flatness), a shape
class, and instance world positions. Read-only.

LEVEL01: 484 instances -> 152 distinct payloads (151 decode cleanly; 2 records with flags
0x14 bridge to payload 0x2f700, which doesn't decode as a vertex payload — an unresolved
anomaly, flagged "geometry unavailable"). Pass-1 controls visible decor: translating all 484
positions +60000 X changed 61% of the spawn frame in-game.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import dat_reloc

STR = 0x14
VPT = 0xc


def pass1_records(d: bytes):
    src = dat_reloc.DAT(d)
    trail = src.trailing_base()[0]
    o = trail
    while struct.unpack_from("<h", d, o + 0x0e)[0] >= 0:
        x, y, z = struct.unpack_from("<iii", d, o)
        flags = struct.unpack_from("<H", d, o + 0x0e)[0]
        node = struct.unpack_from("<I", d, o + 0x10)[0]
        payoff = node + (0x1c if (flags & 0x8) else 0x14)
        payload = struct.unpack_from("<I", d, payoff)[0]
        yield (x, y, z, flags, node, payload)
        o += STR


def payload_geom(d: bytes, pay: int):
    if not (0 < pay < len(d) - 4):
        return None
    cnt = struct.unpack_from("<I", d, pay)[0]
    if not (0 < cnt < 100000) or pay + 4 + cnt * VPT > len(d):
        return None
    xs = []; ys = []; zs = []
    for i in range(cnt):
        x, y, z = struct.unpack_from("<hhh", d, pay + 4 + i * VPT)
        xs.append(x); ys.append(y); zs.append(z)
    dx, dy, dz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    return cnt, dx, dy, dz


def shape_class(dx, dy, dz):
    horiz = max(dx, dz)
    if horiz == 0:
        return "point"
    if dy <= 0.20 * horiz:
        return "flat (ground/decor-mat)"
    if dy >= 1.5 * horiz:
        return "tall (upright prop)"
    if horiz >= 3 * min(dx, dz) + 1:
        return "long (fence/wall-ish)"
    return "blocky (rock/prop)"


def main() -> int:
    ap = argparse.ArgumentParser(description="LEVEL01 scenery/decor object catalog (pass-1 instances).")
    ap.add_argument("dat", type=Path)
    ap.add_argument("--payload", type=lambda s: int(s, 0), help="detail one mesh (all instance positions)")
    ap.add_argument("--sort", choices=["instances", "payload"], default="instances")
    args = ap.parse_args()

    d = args.dat.read_bytes()
    meshes: dict[int, list] = {}
    for x, y, z, flags, node, pay in pass1_records(d):
        meshes.setdefault(pay, []).append((x, y, z, flags, node))

    total_inst = sum(len(v) for v in meshes.values())

    if args.payload is not None:
        insts = meshes.get(args.payload)
        if not insts:
            raise SystemExit(f"payload {args.payload:#x} has no pass-1 instances")
        g = payload_geom(d, args.payload)
        print(f"mesh payload {args.payload:#x}: {len(insts)} instance(s)")
        if g:
            cnt, dx, dy, dz = g
            print(f"  geometry: {cnt} verts, local dims (dx={dx},dy={dy},dz={dz}), class={shape_class(dx,dy,dz)}")
        print("  instances (file pos -> runtime <<5):")
        for x, y, z, fl, node in insts:
            print(f"    ({x},{y},{z}) runtime ({x<<5},{y<<5},{z<<5})  flags={fl:#x} node={node:#x}")
        return 0

    print(f"# LEVEL01 scenery catalog: {len(meshes)} distinct meshes, {total_inst} pass-1 instances")
    print(f"# (decor placement is translation-only; meshes are inline FUNC_80010000 payloads, not .ALL/.ANM)")
    print(f"# {'payload':>9}  {'inst':>4}  {'verts':>5}  {'dx':>5} {'dy':>5} {'dz':>5}  class")
    items = sorted(meshes.items(),
                   key=lambda kv: (-len(kv[1]) if args.sort == "instances" else kv[0]))
    for pay, insts in items:
        g = payload_geom(d, pay)
        if g:
            cnt, dx, dy, dz = g
            print(f"  {pay:#09x}  {len(insts):>4}  {cnt:>5}  {dx:>5} {dy:>5} {dz:>5}  {shape_class(dx,dy,dz)}")
        else:
            print(f"  {pay:#09x}  {len(insts):>4}  (payload geometry unavailable @ {pay:#x})")
    # class histogram
    from collections import Counter
    cls = Counter()
    for pay, insts in meshes.items():
        g = payload_geom(d, pay)
        if g:
            cls[shape_class(g[1], g[2], g[3])] += 1
    print("\n# shape-class histogram (meshes):", dict(cls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
