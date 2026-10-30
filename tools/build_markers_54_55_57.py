#!/usr/bin/env python3
"""
Fixed-count "sacrifice remaining marker candidates" diagnostic for LEVEL01.

Converts LEVEL01 DAT type-0x3f entries 54, 55, 57 (invisible marker/action
candidates, original kinds 0x22/0x23/0x24) into visible/collectible kind-0x29
seed tokens placed in a row near the existing entry 64 orange-token area.

- No append. No record shift. Type-0x3f count stays 70. DAT size unchanged.
- Only entries 54, 55, 57 are modified. Entry 56 is deliberately left alone.

Run from repo root:  python3 tools/build_markers_54_55_57.py
"""
import hashlib
import struct
import sys

SRC = "DAT/LEVEL01_LEVEL.DAT"
OUT = "DAT/LEVEL01_LEVEL_MARKERS54_55_57_KIND29_NEAR64_TEST.DAT"
SRC_SHA1 = "b376cb506f437a1cda721fd13766ddbca7c6a247"
SRC_SIZE = 332824

ENTRY_BASE = 0x0008      # first type-0x3f entry
ENTRY_SIZE = 0x10
T3F_HDR = 0x0004         # type-0x3f record header: count(h) type(h)

# Target placements (absolute), kind 0x29 = orange seed-power token.
# entry 64 reference orange token area: X 4416, Y -50, Z -3655.
TARGETS = {
    54: dict(x=4928, y=-50, z=-3655, kind=0x29),
    55: dict(x=5440, y=-50, z=-3655, kind=0x29),
    57: dict(x=5952, y=-50, z=-3655, kind=0x29),
}


def enc_entry(x, y, z, kind):
    return struct.pack("<iiiI", x, y, z, kind)


def dec_entry(b):
    x, y, z, k = struct.unpack("<iiiI", b)
    return x, y, z, k


def entry_off(i):
    return ENTRY_BASE + i * ENTRY_SIZE


def main():
    data = bytearray(open(SRC, "rb").read())
    assert len(data) == SRC_SIZE, f"unexpected src size {len(data)}"
    sha = hashlib.sha1(data).hexdigest()
    assert sha == SRC_SHA1, f"src sha1 mismatch: {sha}"

    cnt, typ = struct.unpack_from("<HH", data, T3F_HDR)
    assert typ == 0x3F, f"first record is not type 0x3f (got {typ:#x})"
    assert cnt == 70, f"type-0x3f count != 70 (got {cnt})"

    orig = bytes(data)
    diffs = []
    for idx, t in sorted(TARGETS.items()):
        off = entry_off(idx)
        old = bytes(orig[off:off + ENTRY_SIZE])
        new = enc_entry(t["x"], t["y"], t["z"], t["kind"])
        data[off:off + ENTRY_SIZE] = new
        diffs.append((idx, off, old, new))

    out = bytes(data)
    open(OUT, "wb").write(out)

    # ---- verification ----
    print("== BUILD ==")
    print(f"src : {SRC}  sha1 {SRC_SHA1}")
    print(f"out : {OUT}")
    print(f"out sha1 : {hashlib.sha1(out).hexdigest()}")
    print()

    ok = True

    # 1. size
    same_size = len(out) == SRC_SIZE
    ok &= same_size
    print(f"[{'OK' if same_size else 'FAIL'}] out size == pristine ({len(out)} vs {SRC_SIZE})")

    # 2. type-0x3f count
    ocnt, otyp = struct.unpack_from("<HH", out, T3F_HDR)
    cnt_ok = ocnt == 70 and otyp == 0x3F
    ok &= cnt_ok
    print(f"[{'OK' if cnt_ok else 'FAIL'}] type-0x3f count == 70 (got {ocnt}, type {otyp:#x})")

    # 3+4. only entries 54,55,57 changed; 0..53,56,58..69 identical
    changed = set()
    for i in range(70):
        o = entry_off(i)
        if orig[o:o + ENTRY_SIZE] != out[o:o + ENTRY_SIZE]:
            changed.add(i)
    want = set(TARGETS)
    only_ok = changed == want
    ok &= only_ok
    print(f"[{'OK' if only_ok else 'FAIL'}] only entries {sorted(want)} changed (changed: {sorted(changed)})")

    # explicit: entry 56 untouched
    o56 = entry_off(56)
    e56_ok = orig[o56:o56 + ENTRY_SIZE] == out[o56:o56 + ENTRY_SIZE]
    ok &= e56_ok
    print(f"[{'OK' if e56_ok else 'FAIL'}] entry 56 byte-identical (left alone)")

    # 5. later records from 0x468 onward unchanged
    tail_ok = orig[0x468:] == out[0x468:]
    ok &= tail_ok
    print(f"[{'OK' if tail_ok else 'FAIL'}] bytes from 0x468 onward unchanged/unshifted")

    # also: everything outside the 3 patched entries identical
    rest = bytearray(out)
    rest_o = bytearray(orig)
    for idx in TARGETS:
        o = entry_off(idx)
        rest[o:o + ENTRY_SIZE] = b"\x00" * ENTRY_SIZE
        rest_o[o:o + ENTRY_SIZE] = b"\x00" * ENTRY_SIZE
    rest_ok = bytes(rest) == bytes(rest_o)
    ok &= rest_ok
    print(f"[{'OK' if rest_ok else 'FAIL'}] all bytes outside entries 54/55/57 identical")

    print()
    print("== BYTE DIFFS ==")
    for idx, off, old, new in diffs:
        print(f"entry {idx}  off {off:#06x}")
        print(f"  orig {old.hex()}")
        print(f"  new  {new.hex()}")

    print()
    print("== DECODE CHECK (patched entries) ==")
    print(f"{'entry':>5} {'off':>7} {'X':>7} {'Y':>6} {'Z':>8} {'kind':>5}  match")
    for idx, t in sorted(TARGETS.items()):
        off = entry_off(idx)
        x, y, z, k = dec_entry(out[off:off + ENTRY_SIZE])
        m = (x == t["x"] and y == t["y"] and z == t["z"] and k == t["kind"])
        ok &= m
        print(f"{idx:>5} {off:#07x} {x:>7} {y:>6} {z:>8} {k:#05x}  {'OK' if m else 'FAIL'}")

    print()
    print("RESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
