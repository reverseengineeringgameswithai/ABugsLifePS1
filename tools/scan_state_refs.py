#!/usr/bin/env python3
"""Scan MIPS code for references to candidate state globals."""

from __future__ import annotations

import argparse
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


GP = 0x80081D98
SCUS_BASE = 0x80010000
SCUS_TEXT_OFF = 0x800
OVL_BASE = 0x800B39A0
REG_NAMES = {
    0: "zero", 1: "at", 2: "v0", 3: "v1", 4: "a0", 5: "a1", 6: "a2", 7: "a3",
    8: "t0", 9: "t1", 10: "t2", 11: "t3", 12: "t4", 13: "t5", 14: "t6", 15: "t7",
    16: "s0", 17: "s1", 18: "s2", 19: "s3", 20: "s4", 21: "s5", 22: "s6", 23: "s7",
    24: "t8", 25: "t9", 26: "k0", 27: "k1", 28: "gp", 29: "sp", 30: "fp", 31: "ra",
}
MEM_OPS = {
    0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu",
    0x28: "sb", 0x29: "sh", 0x2B: "sw",
}


def s16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def load_words(path: Path, base: int, skip: int = 0):
    data = path.read_bytes()
    for off in range(skip, len(data) - 3, 4):
        word = struct.unpack_from("<I", data, off)[0]
        yield base + (off - skip), off, word


def insn_text(w: int) -> str:
    op = w >> 26
    rs = (w >> 21) & 0x1F
    rt = (w >> 16) & 0x1F
    imm = s16(w)
    if op == 0x0F:
        return f"lui {REG_NAMES[rt]}, {w & 0xffff:#x}"
    if op in MEM_OPS:
        return f"{MEM_OPS[op]} {REG_NAMES[rt]}, {imm:+#x}({REG_NAMES[rs]})"
    if op == 0x09:
        return f"addiu {REG_NAMES[rt]}, {REG_NAMES[rs]}, {imm:+#x}"
    if op == 0x0D:
        return f"ori {REG_NAMES[rt]}, {REG_NAMES[rs]}, {w & 0xffff:#x}"
    return f"word {w:#010x}"


def scan_file(path: Path, base: int, skip: int, targets: dict[int, str]) -> None:
    words = list(load_words(path, base, skip))
    by_va = {va: (off, w) for va, off, w in words}
    target_set = set(targets)
    print(f"\n{path}")

    print("GP-relative references")
    for va, _off, w in words:
        op = w >> 26
        if op not in MEM_OPS:
            continue
        rs = (w >> 21) & 0x1F
        if rs != 28:
            continue
        addr = GP + s16(w)
        if addr in target_set:
            print(f"{va:#010x} {targets[addr]:12s} {insn_text(w)}")

    print("full-address references, local LUI window")
    regs: dict[int, tuple[int, int]] = {}
    for va, _off, w in words:
        op = w >> 26
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        immu = w & 0xFFFF
        if op == 0x0F:
            regs[rt] = (immu << 16, va)
            continue
        if op in (0x09, 0x0D) and rs in regs:
            base_val, base_va = regs[rs]
            add = s16(w) if op == 0x09 else immu
            val = (base_val + add) & 0xFFFFFFFF
            regs[rt] = (val, va)
            if val in target_set:
                print(f"{base_va:#010x}->{va:#010x} {targets[val]:12s} {insn_text(by_va[base_va][1])}; {insn_text(w)}")
            continue
        if op in MEM_OPS and rs in regs:
            base_val, base_va = regs[rs]
            addr = (base_val + s16(w)) & 0xFFFFFFFF
            if addr in target_set:
                print(f"{base_va:#010x}->{va:#010x} {targets[addr]:12s} {insn_text(by_va[base_va][1])}; {insn_text(w)}")
        if op not in (0x09, 0x0D, *MEM_OPS):
            pass


def dump_block(good: Path, bad: Path) -> None:
    g = good.read_bytes()
    b = bad.read_bytes()
    start = 0x80082400
    end = 0x80082540
    print("\nRAM word diff 0x80082400..0x80082540")
    print("addr        good       bad")
    for va in range(start, end, 4):
        go = va - 0x80000000
        gv = struct.unpack_from("<I", g, go)[0]
        bv = struct.unpack_from("<I", b, go)[0]
        if gv != bv:
            print(f"{va:#010x} {gv:#010x} {bv:#010x}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--good", type=Path, default=Path(os.path.expanduser("~/good_iso.ram")))
    ap.add_argument("--bad", type=Path, default=Path(os.path.expanduser("~/bad_iso_black.ram")))
    args = ap.parse_args()
    targets = {
        0x80082438: "80082438",
        0x8008243C: "8008243c",
        0x80082440: "80082440",
        0x8008245C: "8008245c",
        0x80082504: "80082504",
    }
    scan_file(ROOT / "REBUILD" / "files" / "SCUS_942.88", SCUS_BASE, SCUS_TEXT_OFF, targets)
    scan_file(Path("OVL/LEVEL01_LEVEL.BIN"), OVL_BASE, 0, targets)
    scan_file(Path("OVL/LEVEL01_LEVEL1.BIN"), OVL_BASE, 0, targets)
    dump_block(args.good, args.bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
