#!/usr/bin/env python3
"""tools/probe_floor_vs_collision.py -- OFFLINE: does the authored COLLISION sit where the
authored VISUAL floor is drawn?

Flik stands on chunk-32 planes but sees FUNC_80010000 payloads. The P53 one-mesh contract says
both come from the same surface function, so at any XZ they must agree. When they don't, he falls
through ground he can see, or hovers over a hole -- and every live symptom looks like a physics bug
rather than an authoring bug. This answers it without booting anything.

Reports, per sample point: the runtime Y of every chunk-32 floor plane whose footprint covers the
point, the runtime Y of the nearest authored visual vertex, and the disagreement.
"""
from __future__ import annotations
import argparse, json, os, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import decode_level_raw as DEC            # noqa: E402
import edit_collision_sector as ECS       # noqa: E402
import native_collision_mesh_codec as MC  # noqa: E402
import native_mesh_codec as NC            # noqa: E402

NODE_BASE, NODE_STRIDE, FLOOR_MARKER = 0x45F0, 0x18, 0xC0080000


def chunk32(raw_path):
    chunks = ECS.split_chunks(raw_path.read_bytes())
    return bytes(DEC.decompress_chunk(chunks[ECS.COLL_CHUNK][3]))


def sector_array_off(dec):
    # +0x04 holds the block-region length in s16 units; add_block/replace_block RELOCATES the
    # sector array, so the pristine 0x36570 must never be assumed on a built RAW.
    return 4 + struct.unpack_from("<I", dec, 4)[0] * 2


def sectors(dec):
    arr = sector_array_off(dec)
    n = max(0, min(ECS.N_SECTORS, (len(dec) - arr) // ECS.SECTOR_STRIDE))
    off = 0x08
    for i in range(n):
        o = arr + i * ECS.SECTOR_STRIDE
        ox, oy, oz = struct.unpack_from("<iii", dec, o + 0x08)
        units = struct.unpack_from("<i", dec, o + 0x04)[0]
        yield i, (ox, oy, oz), off, units * 2
        off += units * 2


def collision_ys(dec, x, z):
    """Runtime Y of every chunk-32 plane whose XZ footprint covers world-file (x, z)."""
    out = []
    for i, (ox, oy, oz), boff, blen in sectors(dec):
        if blen <= 0:
            continue
        try:
            groups, _end = MC.decode_block(dec, boff, boff + blen)
        except Exception:
            continue                      # relocation-region / non-mesh blocks
        lx, lz = x - ox, z - oz
        for g in groups:
            for p in g.planes:
                fx, ex, fz, ez = p.footprint
                if fx <= lx <= fx + ex and fz <= lz <= fz + ez:
                    out.append({"sector": i, "runtime_y": (p.v0[1] + oy) << 5,
                                "ny": p.normal[1], "floorish": p.normal[1] < 0})
    return out


def visual_ys(dat, x, z, radius=200):
    """Runtime Y of authored visual vertices near world-file (x, z) (world = T_obj + local)."""
    best = []
    o = NODE_BASE
    while o + NODE_STRIDE <= len(dat):
        if struct.unpack_from("<I", dat, o + 0x10)[0] != FLOOR_MARKER:
            break
        tx, ty, tz = struct.unpack_from("<3i", dat, o)
        pay = struct.unpack_from("<I", dat, o + 0x14)[0]
        o += NODE_STRIDE
        if tx <= -25000 or tz <= -25000:
            continue
        try:
            mesh = NC.decode(dat, pay)
        except Exception:
            continue
        for v in mesh.verts:
            wx, wz = tx + v.x, tz + v.z
            if abs(wx - x) <= radius and abs(wz - z) <= radius:
                best.append({"pay": f"{pay:#08x}", "wx": wx, "wz": wz,
                             "file_y": ty + v.y, "runtime_y": (ty + v.y) << 5,
                             "d": abs(wx - x) + abs(wz - z)})
    best.sort(key=lambda r: r["d"])
    return best[:6]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True)
    ap.add_argument("--dat", required=True)
    ap.add_argument("--at", nargs=2, type=int, action="append", required=True,
                    metavar=("X", "Z"), help="world-FILE XZ sample point (repeatable)")
    ap.add_argument("--json")
    a = ap.parse_args()

    dec = chunk32(Path(a.raw))
    dat = Path(a.dat).read_bytes()
    report = []
    for x, z in a.at:
        col = collision_ys(dec, x, z)
        vis = visual_ys(dat, x, z)
        floors = [c["runtime_y"] for c in col if c["floorish"]]
        print(f"\n=== ({x},{z}) file ===")
        print(f"  collision planes covering: {len(col)}  (floor-facing {len(floors)})")
        if floors:
            print(f"    floor runtime Y: min {min(floors)} max {max(floors)}")
        else:
            print("    ⚠️ NO floor-facing plane covers this point -- nothing to stand on")
        if vis:
            vy = [v['runtime_y'] for v in vis]
            print(f"  visual verts near: {len(vis)}  runtime Y {min(vy)}..{max(vy)}"
                  f"   nearest pay {vis[0]['pay']} at ({vis[0]['wx']},{vis[0]['wz']})")
            if floors:
                print(f"  ==> DISAGREEMENT (collision - visual, runtime): "
                      f"{min(floors) - min(vy)} .. {max(floors) - max(vy)}")
        else:
            print("  ⚠️ NO authored visual vertex within 200 file units")
        report.append({"x": x, "z": z, "collision": col[:40], "visual": vis})
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
        print(f"\n[probe] -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
