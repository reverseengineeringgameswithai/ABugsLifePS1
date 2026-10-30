#!/usr/bin/env python3
"""Verify the LEVEL.RAW seed edit propagated to runtime after booting ABL_SEED_MOVE_TEST.bin.

Run AFTER: (1) boot REBUILD/ABL_SEED_MOVE_TEST.bin/.cue in DuckStation, (2) reach LEVEL01
(Flik's start area, the _9 scene). The game decompresses the edited LEVEL.RAW with its OWN
decompressor at level load, so a moved seed proves the full file write path end-to-end.

Edit applied on disc: start-seed file X 6184 -> 3000  (runtime base X 197888 -> 96000).
"""
import struct
from abl_dbg import D

OLD_FILE_X, NEW_FILE_X = 6184, 3000
SEED_BASE = 0x800a0ae8          # start-area seed base struct; +0x4 = runtime X (= file<<5)
TABLE_LO, TABLE_HI = 0x80094a38, 0x8009511c   # seed source-record region (file coords)

d = D()
base_x = d.rs32(SEED_BASE + 4)
print(f"seed base 0x{SEED_BASE+4:08x} (runtime X) = {base_x}  (expect {NEW_FILE_X*32}, old {OLD_FILE_X*32})")

# scan the seed source table for the file-coord value
blob = d.rmem(TABLE_LO, TABLE_HI - TABLE_LO)
def find_all(v):
    p = struct.pack('<i', v); out=[]; i=0
    while True:
        j = blob.find(p, i)
        if j < 0: break
        out.append(TABLE_LO + j); i = j + 1
    return out
print(f"file-X {NEW_FILE_X} found in seed table at: {[hex(a) for a in find_all(NEW_FILE_X)]}")
print(f"file-X {OLD_FILE_X} (old) still present at: {[hex(a) for a in find_all(OLD_FILE_X)]}")

ok = base_x == NEW_FILE_X * 32
print("\nRESULT:", "PASS — edited LEVEL.RAW reached runtime via the game's own codec"
      if ok else "not yet (is LEVEL01 fully loaded? right disc booted?)")
