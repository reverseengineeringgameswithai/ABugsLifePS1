#!/usr/bin/env python3
"""LIVE: list the oriented COLLISION PLANES (walls/slopes) of the loaded level (§2.2).

The plane records are scattered in LEVEL.RAW chunk 32 and located via runtime tables
the converter FUNC_80030F60 builds, so — like probe_collision_sector.py — this reads
them from a running DuckStation, giving the chunk-32 offset to feed
tools/edit_collision_plane.py. Read-only.

Per plane it prints: index, sector, chunk-32 offset, the s16 normal (|n|~0x4000) and ref
point, the world position (sector_origin + ref<<5), and a slope/wall guess (which normal
axis dominates). Decode: src_re/collision_plane_resolver_800345cc.c.

Usage:
  probe_collision_planes.py --port 23461 --token cc5-token [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

PTR_ARRAY = 0x8009C230      # u32 per plane -> record
SECTOR_ARRAY = 0x80091718   # s16 per plane -> sector index
SECTOR_TABLE = 0x800A7E48   # stride 0x30, origin X/Y/Z @ +0/4/8
LIVE_BASE = 0x800C1688      # chunk 32 decompresses here
COUNT_GP_OFF = 0x57C


def main() -> int:
    ap = argparse.ArgumentParser(description="List the live oriented collision planes (read-only).")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23461)
    ap.add_argument("--token", default="cc5-token")
    ap.add_argument("--json", help="also write the plane list to this JSON path")
    args = ap.parse_args()

    sys.path.insert(0, os.path.expanduser("~/duckstation/scripts/debugger-client"))
    from duckstation_debug_client import DebuggerClient

    c = DebuggerClient(args.host, args.port, "ws")
    c.authenticate(args.token)
    c.transport.sock.settimeout(30)

    def rmem(a, n):
        return bytes.fromhex(c.call("debugger.readMemory", {"address": "0x%08x" % a, "length": n})["hex"])

    reg = c.call("debugger.getRegisters", {})
    g = reg.get("registers", reg)
    gp = g.get("gp")
    gp = int(gp, 16) if isinstance(gp, str) else gp
    count = struct.unpack("<i", rmem(gp + COUNT_GP_OFF, 4))[0]
    print(f"plane count [gp+0x57c] = {count}")
    if count <= 0:
        print("no planes (is a level loaded / in gameplay?)")
        return 0

    planes = []
    print("\nidx sec  chunk32_off  normal                 ref                 world                     kind")
    for i in range(count):
        ptr = struct.unpack("<I", rmem(PTR_ARRAY + i * 4, 4))[0]
        sec = struct.unpack("<h", rmem(SECTOR_ARRAY + i * 2, 2))[0]
        nx, ny, nz, rx, ry, rz = struct.unpack("<hhhhhh", rmem(ptr, 12))
        ox, oy, oz = struct.unpack("<iii", rmem(SECTOR_TABLE + sec * 0x30, 12))
        wx, wy, wz = ox + (rx << 5), oy + (ry << 5), oz + (rz << 5)
        dom = max(range(3), key=lambda k: abs((nx, ny, nz)[k]))
        kind = "slope/floor" if dom == 1 else "wall"
        coff = ptr - LIVE_BASE
        planes.append(dict(index=i, sector=sec, chunk32_off=coff,
                           normal=[nx, ny, nz], ref=[rx, ry, rz], world=[wx, wy, wz], kind=kind))
        print(f"{i:3d} {sec:4d}  0x{coff:06x}   ({nx:6d},{ny:6d},{nz:6d})  "
              f"({rx:5d},{ry:5d},{rz:5d})  ({wx:8d},{wy:8d},{wz:8d})  {kind}")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(planes, f, indent=2)
        print(f"\nwrote {args.json}")
    print("\nEdit one: tools/edit_collision_plane.py <LEVEL.RAW> --offset 0x<chunk32_off> "
          "--normal X:Y:Z --ref X:Y:Z  (then build_autolayout_disc.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
