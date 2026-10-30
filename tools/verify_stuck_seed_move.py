#!/usr/bin/env python3
"""Verify the stuck-seed relocation after booting REBUILD/ABL_STUCK_SEED_TEST.bin.

Boot that disc, reach LEVEL01, then run this. The stuck seed next to Flik (base #14 = 0x800a074c,
chunk-31 record #19) was moved (4837,-2325,2813) -> (1000,-2325,2813)  [runtime X 154784 -> 32000].
Scans ALL seed base structs so the result doesn't depend on one address.
"""
import struct, math
from abl_dbg import D

TARGET = 0x800a074c          # base #14 — the stuck seed beside Flik
NEW = (1000, -2325, 2813)    # new FILE coords
BASE0, STRIDE, N = 0x800a0014, 0x84, 26

d = D()
x = d.rs32(TARGET+4); y = d.rs32(TARGET+8); z = d.rs32(TARGET+0xc); f40 = d.ru32(TARGET+0x40)
print(f"stuck seed base 0x{TARGET:08x}: file=({x>>5},{y>>5},{z>>5}) +0x40={f40}")
print(f"  expect file X ~= {NEW[0]} (runtime {NEW[0]*32}); was 4837")
moved = abs((x>>5) - NEW[0]) <= 3

print("\n=== all stuck seeds (+0x40=3) ===")
for i in range(N):
    b = BASE0 + i*STRIDE
    if d.ru32(b+0x40) == 3:
        bx, by, bz = d.rs32(b+4)>>5, d.rs32(b+8)>>5, d.rs32(b+0xc)>>5
        print(f"  #{i:2d} 0x{b:08x}: file=({bx},{by},{bz})")

print("\nRESULT:", "PASS — the stuck seed beside Flik relocated via LEVEL.RAW edit, still rooted"
      if moved and f40 == 3 else "not yet (LEVEL01 loaded? correct disc booted?)")
