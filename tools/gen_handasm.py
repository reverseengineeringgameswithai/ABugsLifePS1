#!/usr/bin/env python3
"""Generate an assemblable hand-written .s from the original EXE bytes for a
resident function (campaign v4 hand-asm ladder).

Real MIPS-I mnemonics + local labels for internal branch/j targets; `.word` for
jal (absolute), COP2/GTE, and anything not in the decoded subset. Byte-exactness
is GUARANTEED by the build+validate SHA-1 round-trip — on a mismatch, replace the
offending line with `.word 0x........` (the tool prints each word's hex as a
comment, so the fix is mechanical).

  python tools/gen_handasm.py <start_hex> <end_hex> <name> [-o out.s] [--desc "..."]

asm/hand_written/*.s is gitignored (derived from the copyrighted EXE); only the
config/segments.yml entry + Canon note are committed.
"""
from __future__ import annotations
import argparse, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
TEXT_LO = 0x80010000

R = ["$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
     "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
     "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
     "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"]

# R-type funct -> (mnemonic, form) ; form: 'rd_rs_rt','rd_rt_sa','rd_rt_rs','rs_rt','rd','rs'
RTYPE = {
    0x20: ("add", "rd_rs_rt"), 0x21: ("addu", "rd_rs_rt"), 0x22: ("sub", "rd_rs_rt"),
    0x23: ("subu", "rd_rs_rt"), 0x24: ("and", "rd_rs_rt"), 0x25: ("or", "rd_rs_rt"),
    0x26: ("xor", "rd_rs_rt"), 0x27: ("nor", "rd_rs_rt"), 0x2a: ("slt", "rd_rs_rt"),
    0x2b: ("sltu", "rd_rs_rt"),
    0x00: ("sll", "rd_rt_sa"), 0x02: ("srl", "rd_rt_sa"), 0x03: ("sra", "rd_rt_sa"),
    0x04: ("sllv", "rd_rt_rs"), 0x06: ("srlv", "rd_rt_rs"), 0x07: ("srav", "rd_rt_rs"),
    0x08: ("jr", "rs"), 0x09: ("jalr", "rd_rs"),
    0x10: ("mfhi", "rd"), 0x12: ("mflo", "rd"), 0x11: ("mthi", "rs"), 0x13: ("mtlo", "rs"),
    0x18: ("mult", "rs_rt"), 0x19: ("multu", "rs_rt"),
}
# I-type op -> (mnemonic, signed_imm?)
ITYPE = {
    0x08: ("addi", True), 0x09: ("addiu", True), 0x0a: ("slti", True), 0x0b: ("sltiu", True),
    0x0c: ("andi", False), 0x0d: ("ori", False), 0x0e: ("xori", False), 0x0f: ("lui", False),
}
MEM = {0x20: "lb", 0x21: "lh", 0x22: "lwl", 0x23: "lw", 0x24: "lbu", 0x25: "lhu",
       0x26: "lwr", 0x28: "sb", 0x29: "sh", 0x2a: "swl", 0x2b: "sw", 0x2e: "swr"}


def imm_str(v: int, signed: bool) -> str:
    if signed:
        v = v - 0x10000 if v >= 0x8000 else v
        return str(v)
    return f"{v:#x}"


def decode(word: int, va: int, labels: dict):
    op = word >> 26
    rs, rt, rd = (word >> 21) & 31, (word >> 16) & 31, (word >> 11) & 31
    sa, imm = (word >> 6) & 31, word & 0xFFFF
    funct = word & 0x3F
    if word == 0:
        return "nop"
    if op == 0 and funct in RTYPE:
        m, form = RTYPE[funct]
        if form == "rd_rs_rt":  return f"{m}\t{R[rd]},{R[rs]},{R[rt]}"
        if form == "rd_rt_sa":  return f"{m}\t{R[rd]},{R[rt]},{sa}"
        if form == "rd_rt_rs":  return f"{m}\t{R[rd]},{R[rt]},{R[rs]}"
        if form == "rs_rt":     return f"{m}\t{R[rs]},{R[rt]}"
        if form == "rd":        return f"{m}\t{R[rd]}"
        if form == "rs":        return f"{m}\t{R[rs]}"
        if form == "rd_rs":     return f"{m}\t{R[rd]},{R[rs]}"
    if op == 0x0f:  # lui
        return f"lui\t{R[rt]},{imm:#x}"
    if op in ITYPE:
        m, sgn = ITYPE[op]
        return f"{m}\t{R[rt]},{R[rs]},{imm_str(imm, sgn)}"
    if op in MEM:
        return f"{MEM[op]}\t{R[rt]},{imm_str(imm, True)}({R[rs]})"
    if op in (4, 5):  # beq/bne
        tgt = va + 4 + ((imm - 0x10000 if imm >= 0x8000 else imm) << 2)
        if tgt in labels:   # else external target (wrong bound / data) -> .word
            return f"{'beq' if op == 4 else 'bne'}\t{R[rs]},{R[rt]},{labels[tgt]}"
    if op in (6, 7):  # blez/bgtz
        tgt = va + 4 + ((imm - 0x10000 if imm >= 0x8000 else imm) << 2)
        if tgt in labels:
            return f"{'blez' if op == 6 else 'bgtz'}\t{R[rs]},{labels[tgt]}"
    if op == 1:  # regimm bltz/bgez/bltzal/bgezal
        tgt = va + 4 + ((imm - 0x10000 if imm >= 0x8000 else imm) << 2)
        m = {0: "bltz", 1: "bgez", 0x10: "bltzal", 0x11: "bgezal"}.get(rt)
        if m and tgt in labels:
            return f"{m}\t{R[rs]},{labels[tgt]}"
    if op == 2:  # j (internal -> label; else .word)
        tgt = (va & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
        if tgt in labels:
            return f"j\t{labels[tgt]}"
    return None  # -> .word


def branch_target(word: int, va: int):
    op = word >> 26
    imm = word & 0xFFFF
    if op in (1, 4, 5, 6, 7):
        return va + 4 + ((imm - 0x10000 if imm >= 0x8000 else imm) << 2)
    if op == 2:  # j
        return (va & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("start"); ap.add_argument("end"); ap.add_argument("name")
    ap.add_argument("-o", "--out"); ap.add_argument("--desc", default="")
    a = ap.parse_args()
    s, e = int(a.start, 16), int(a.end, 16)
    exe = EXE.read_bytes()
    words = [struct.unpack_from("<I", exe, (s - TEXT_LO + 0x800) + i)[0]
             for i in range(0, e - s, 4)]

    # pass 1: internal branch/j targets -> labels
    labels = {}
    for i, w in enumerate(words):
        t = branch_target(w, s + i * 4)
        if t is not None and s <= t < e:
            labels.setdefault(t, f".L_{t:08x}")

    # pass 2: emit
    out = [".set noreorder", ".set noat", ".text",
           f"# {a.name} @ {s:#010x} ({e - s} B) — hand-asm transcription (campaign v4)"]
    if a.desc:
        for ln in a.desc.split("\n"):
            out.append(f"# {ln}")
    for i, w in enumerate(words):
        va = s + i * 4
        if va in labels:
            out.append(f"{labels[va]}:")
        m = decode(w, va, labels)
        if m is None:
            op = w >> 26
            tgt = (va & 0xF0000000) | ((w & 0x03FFFFFF) << 2) if op in (2, 3) else None
            cmt = f"  # jal {tgt:#x}" if op == 3 else "  # (cop2/other)"
            out.append(f".word 0x{w:08x}{cmt}")
        else:
            out.append(m)
    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text)
        print(f"[gen_handasm] wrote {a.out} ({len(words)} words, {len(labels)} labels)")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
