#!/usr/bin/env python3
"""Disassemble a VA range of the resident SCUS_942.88 EXE (MIPS R3000, little-endian).

The PS-X EXE header gives the load address (t_addr) and the image starts at file
offset 0x800, so a RAM address maps to  (VA - t_addr) + 0x800.  Everything here is
read straight out of the pristine EXE -- no emulator, no symbols required.

USAGE
    tools/dis_exe.py 0x8004A78C 40            # 40 instructions from that VA
    tools/dis_exe.py 0x8004A78C 40 --exe build/other_SCUS_942.88

Covers the R3000 user-mode subset this project reads (loads/stores, ALU, branches,
jumps, shifts, mult/div, and the coprocessor moves that show up around GTE code);
anything unrecognised prints as a raw word rather than a wrong mnemonic.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGS = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5", "t6",
        "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "t8", "t9", "k0", "k1", "gp", "sp",
        "fp", "ra"]

# op -> mnemonic for the I/J-type instructions
IOPS = {0x02: "j", 0x03: "jal", 0x04: "beq", 0x05: "bne", 0x06: "blez", 0x07: "bgtz",
        0x08: "addi", 0x09: "addiu", 0x0A: "slti", 0x0B: "sltiu", 0x0C: "andi", 0x0D: "ori",
        0x0E: "xori", 0x0F: "lui", 0x20: "lb", 0x21: "lh", 0x22: "lwl", 0x23: "lw", 0x24: "lbu",
        0x25: "lhu", 0x26: "lwr", 0x28: "sb", 0x29: "sh", 0x2A: "swl", 0x2B: "sw", 0x2E: "swr"}
# funct -> mnemonic for SPECIAL (op 0)
ROPS = {0x00: "sll", 0x02: "srl", 0x03: "sra", 0x04: "sllv", 0x06: "srlv", 0x07: "srav",
        0x08: "jr", 0x09: "jalr", 0x0C: "syscall", 0x0D: "break", 0x10: "mfhi", 0x11: "mthi",
        0x12: "mflo", 0x13: "mtlo", 0x18: "mult", 0x19: "multu", 0x1A: "div", 0x1B: "divu",
        0x20: "add", 0x21: "addu", 0x22: "sub", 0x23: "subu", 0x24: "and", 0x25: "or",
        0x26: "xor", 0x27: "nor", 0x2A: "slt", 0x2B: "sltu"}
BRANCH = {"beq", "bne", "blez", "bgtz", "bltz", "bgez", "bltzal", "bgezal"}
MEM = {"lb", "lh", "lwl", "lw", "lbu", "lhu", "lwr", "sb", "sh", "swl", "sw", "swr"}


def s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def disasm(word: int, pc: int) -> str:
    op, rs, rt, imm = word >> 26, (word >> 21) & 31, (word >> 16) & 31, word & 0xFFFF
    rd, sa, funct = (word >> 11) & 31, (word >> 6) & 31, word & 0x3F

    if word == 0:
        return "nop"
    if op == 0:
        m = ROPS.get(funct)
        if m is None:
            return ".word 0x%08x" % word
        if m in ("sll", "srl", "sra"):
            return "%-6s %s, %s, %d" % (m, REGS[rd], REGS[rt], sa)
        if m in ("sllv", "srlv", "srav"):
            return "%-6s %s, %s, %s" % (m, REGS[rd], REGS[rt], REGS[rs])
        if m == "jr":
            return "%-6s %s" % (m, REGS[rs])
        if m == "jalr":
            return "%-6s %s, %s" % (m, REGS[rd], REGS[rs])
        if m in ("mfhi", "mflo"):
            return "%-6s %s" % (m, REGS[rd])
        if m in ("mthi", "mtlo"):
            return "%-6s %s" % (m, REGS[rs])
        if m in ("mult", "multu", "div", "divu"):
            return "%-6s %s, %s" % (m, REGS[rs], REGS[rt])
        if m in ("syscall", "break"):
            return m
        return "%-6s %s, %s, %s" % (m, REGS[rd], REGS[rs], REGS[rt])
    if op == 1:  # REGIMM
        m = {0x00: "bltz", 0x01: "bgez", 0x10: "bltzal", 0x11: "bgezal"}.get(rt)
        if m is None:
            return ".word 0x%08x" % word
        return "%-6s %s, 0x%08x" % (m, REGS[rs], pc + 4 + (s16(imm) << 2))
    if op in (0x10, 0x11, 0x12, 0x13):  # COPz
        if rs == 0:
            return "%-6s %s, $%d" % ("mfc%d" % (op & 3), REGS[rt], rd)
        if rs == 4:
            return "%-6s %s, $%d" % ("mtc%d" % (op & 3), REGS[rt], rd)
        if rs == 2:
            return "%-6s %s, $%d" % ("cfc%d" % (op & 3), REGS[rt], rd)
        if rs == 6:
            return "%-6s %s, $%d" % ("ctc%d" % (op & 3), REGS[rt], rd)
        return "%-6s 0x%07x" % ("cop%d" % (op & 3), word & 0x1FFFFFF)
    if op in (0x32, 0x3A):  # lwc2 / swc2
        return "%-6s $%d, %d(%s)" % ("lwc2" if op == 0x32 else "swc2", rt, s16(imm), REGS[rs])

    m = IOPS.get(op)
    if m is None:
        return ".word 0x%08x" % word
    if m in ("j", "jal"):
        return "%-6s 0x%08x" % (m, (pc & 0xF0000000) | ((word & 0x3FFFFFF) << 2))
    if m in ("beq", "bne"):
        return "%-6s %s, %s, 0x%08x" % (m, REGS[rs], REGS[rt], pc + 4 + (s16(imm) << 2))
    if m in ("blez", "bgtz"):
        return "%-6s %s, 0x%08x" % (m, REGS[rs], pc + 4 + (s16(imm) << 2))
    if m == "lui":
        return "%-6s %s, 0x%04x" % (m, REGS[rt], imm)
    if m in MEM:
        return "%-6s %s, %s0x%x(%s)" % (m, REGS[rt], "-" if s16(imm) < 0 else "",
                                        abs(s16(imm)), REGS[rs])
    return "%-6s %s, %s, %d" % (m, REGS[rt], REGS[rs], s16(imm))


def load(exe: Path):
    data = exe.read_bytes()
    if data[:8] != b"PS-X EXE":
        raise SystemExit(f"{exe}: not a PS-X EXE")
    t_addr = struct.unpack_from("<I", data, 0x18)[0]
    return data[0x800:], t_addr


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("va", help="start virtual address, e.g. 0x8004A78C")
    ap.add_argument("count", nargs="?", type=int, default=24, help="instruction count")
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--mark", action="append", default=[],
                    help="VA to flag with '>>' in the listing (repeatable)")
    args = ap.parse_args()

    text, base = load(args.exe)
    start = int(args.va, 0)
    marks = {int(m, 0) for m in args.mark}
    off = start - base
    if off < 0 or off + args.count * 4 > len(text):
        raise SystemExit(f"VA 0x{start:08X} outside {args.exe} text (base 0x{base:08X})")
    for i in range(args.count):
        pc = start + i * 4
        w = struct.unpack_from("<I", text, off + i * 4)[0]
        print("%s 0x%08X  %08x  %s" % (">>" if pc in marks else "  ", pc, w, disasm(w, pc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
