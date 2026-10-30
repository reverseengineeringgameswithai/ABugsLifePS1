#!/usr/bin/env python3
"""Static reader for the PS-X EXE (SCUS_942.88) — map a virtual address to a file
offset, dump a u32 jump/dispatch table, or xref a RAM global (gp-relative + absolute).
Reads the local copyrighted EXE READ-ONLY; emits only ADDRESS METADATA (facts about
the code — addresses, mnemonics, registers — committable per [[Preservation Policy]];
never bulk copyrighted byte payloads).

EXE load map (docs/EXECUTABLE_AND_OVERLAYS.md): load VA 0x80010000, file header 0x800,
text size 0x72800; resident address A -> file offset (A - 0x80010000) + 0x800.
Runtime gp = 0x80081d98 (re_symbols.sym).

Usage:
  exe_read.py <exe> --dump  <va_hex> --len N            # hexdump N bytes at VA
  exe_read.py <exe> --table <va_hex> --count N           # N u32-LE entries as a table
  exe_read.py <exe> --xref  <va_hex> [--gp <gp_hex>]     # find gp-rel + absolute accesses
  exe_read.py <exe> --disasm <va_hex> --count N          # decode N MIPS words to mnemonics

Overlay mode (LEVEL.BIN etc. — a raw code blob with no PS-EXE header):
  add  --base <load_va> --hdr 0   to any mode, e.g. Region-A overlay base 0x800b39a0:
  exe_read.py LEVEL.BIN --base 0x800b39a0 --hdr 0 --xref 0x800822f4
  (gp stays 0x80081d98 — overlays share the resident gp, so gp-relative + absolute
   accesses to the DAT globals cluster are found the same way as in the EXE.)
"""
from __future__ import annotations
import argparse, math, struct, sys

LOAD_VA = 0x80010000
HDR = 0x800
TEXT_SIZE = 0x72800
RESIDENT_END = 0x800827ff
DEFAULT_GP = 0x80081d98
GP_REG = 28

LOADSTORE = {0x20: "lb", 0x21: "lh", 0x22: "lwl", 0x23: "lw", 0x24: "lbu", 0x25: "lhu",
             0x26: "lwr", 0x28: "sb", 0x29: "sh", 0x2a: "swl", 0x2b: "sw", 0x2e: "swr"}


def _dst(w):
    """Register written by instruction w (or None) — used to detect base-reg clobber."""
    op = w >> 26
    if op == 0:                                   # R-type
        fn = w & 0x3f
        if fn in (0x08,):                          # jr (and jalr writes rd, rare) -> ignore
            return None
        return (w >> 11) & 0x1f                    # rd
    if op in (0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f):   # addi/addiu/slti/sltiu/andi/ori/xori/lui
        return (w >> 16) & 0x1f                    # rt
    if op in (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26):         # loads
        return (w >> 16) & 0x1f                    # rt
    return None                                    # stores / branches / jumps


def foff(va):
    return (va - LOAD_VA) + HDR


def looks_code(v):
    return 0x80010000 <= v <= 0x800bffff


REGS = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3",
        "t4", "t5", "t6", "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "s8", "ra"]
_LS = {0x20: "lb", 0x21: "lh", 0x22: "lwl", 0x23: "lw", 0x24: "lbu", 0x25: "lhu",
       0x26: "lwr", 0x28: "sb", 0x29: "sh", 0x2a: "swl", 0x2b: "sw", 0x2e: "swr"}


def disasm_one(va, w):
    """Decode a single MIPS R3000 word to a metadata mnemonic string (no copyrighted bytes)."""
    op = w >> 26; rs = (w >> 21) & 0x1f; rt = (w >> 16) & 0x1f; rd = (w >> 11) & 0x1f
    sh = (w >> 6) & 0x1f; fn = w & 0x3f; imm = w & 0xffff
    si = imm - 0x10000 if imm >= 0x8000 else imm
    R = REGS
    tgt = lambda: f"0x{(va + 4 + (si << 2)) & 0xffffffff:08x}"
    jt = lambda: f"0x{(((w & 0x3ffffff) << 2) | 0x80000000):08x}"
    if w == 0:
        return "nop"
    if op == 0:
        R0 = {0x00: ("sll", "shift"), 0x02: ("srl", "shift"), 0x03: ("sra", "shift"),
              0x04: ("sllv", "v"), 0x06: ("srlv", "v"), 0x08: ("jr", "jr"), 0x09: ("jalr", "jr"),
              0x10: ("mfhi", "d"), 0x12: ("mflo", "d"), 0x18: ("mult", "st"), 0x19: ("multu", "st"),
              0x1a: ("div", "st"), 0x1b: ("divu", "st"), 0x20: ("add", "3"), 0x21: ("addu", "3"),
              0x22: ("sub", "3"), 0x23: ("subu", "3"), 0x24: ("and", "3"), 0x25: ("or", "3"),
              0x26: ("xor", "3"), 0x27: ("nor", "3"), 0x2a: ("slt", "3"), 0x2b: ("sltu", "3")}
        if fn in R0:
            mn, k = R0[fn]
            if k == "3": return f"{mn} {R[rd]},{R[rs]},{R[rt]}"
            if k == "shift": return f"{mn} {R[rd]},{R[rt]},{sh}"
            if k == "v": return f"{mn} {R[rd]},{R[rt]},{R[rs]}"
            if k == "jr": return f"jr {R[rs]}" if fn == 8 else f"jalr {R[rs]}"
            if k == "d": return f"{mn} {R[rd]}"
            if k == "st": return f"{mn} {R[rs]},{R[rt]}"
        return f".word 0x{w:08x}"
    if op == 1:
        return f"{'bltz' if rt == 0 else 'bgez'} {R[rs]},{tgt()}"
    if op == 2: return f"j {jt()}"
    if op == 3: return f"jal {jt()}"
    if op in (4, 5): return f"{'beq' if op == 4 else 'bne'} {R[rs]},{R[rt]},{tgt()}"
    if op in (6, 7): return f"{'blez' if op == 6 else 'bgtz'} {R[rs]},{tgt()}"
    II = {8: "addi", 9: "addiu", 0xa: "slti", 0xb: "sltiu"}
    if op in II: return f"{II[op]} {R[rt]},{R[rs]},{si}"
    IL = {0xc: "andi", 0xd: "ori", 0xe: "xori"}
    if op in IL: return f"{IL[op]} {R[rt]},{R[rs]},0x{imm:x}"
    if op == 0xf: return f"lui {R[rt]},0x{imm:x}"
    if op in _LS: return f"{_LS[op]} {R[rt]},{si}({R[rs]})"
    return f".word 0x{w:08x} (op=0x{op:02x})"


def xref(data, addr, gp=DEFAULT_GP, base=LOAD_VA, hdr=HDR, span=TEXT_SIZE):
    """Return list of (va, kind, mnemonic, rt_reg). kind in {gp,abs,abs-ptr}.
    Pure function over a raw code image — used by the synthetic tests.
    base/hdr/span let the SAME scanner run over an overlay blob (e.g. LEVEL.BIN
    at runtime base 0x800b39a0, header 0, span = file size) as well as the EXE."""
    out = []
    start, end = hdr, min(len(data), hdr + span)
    gpoff = addr - gp
    gp_imm = gpoff & 0xffff
    gp_ok = -0x8000 <= gpoff < 0x8000
    lo = addr & 0xffff
    hi = (addr >> 16) & 0xffff
    hi_adj = (hi + 1) & 0xffff if lo >= 0x8000 else hi  # lui imm when lo is sign-extended
    o = start
    while o + 4 <= end:
        w = struct.unpack_from("<I", data, o)[0]
        op = w >> 26; rs = (w >> 21) & 0x1f; rt = (w >> 16) & 0x1f; imm = w & 0xffff
        va = (o - hdr) + base
        if gp_ok and op in LOADSTORE and rs == GP_REG and imm == gp_imm:
            out.append((va, "gp", LOADSTORE[op], rt))
        if op == 0x0f and imm == hi_adj:                 # lui rt, hi_adj
            breg = rt
            for k in range(1, 9):
                if o + (k + 1) * 4 > len(data):
                    break
                w2 = struct.unpack_from("<I", data, o + k * 4)[0]
                op2 = w2 >> 26; rs2 = (w2 >> 21) & 0x1f; rt2 = (w2 >> 16) & 0x1f
                rd2 = (w2 >> 11) & 0x1f; imm2 = w2 & 0xffff
                va2 = (o + k * 4 - hdr) + base
                if op2 in LOADSTORE and rs2 == breg and imm2 == lo:
                    out.append((va2, "abs", LOADSTORE[op2], rt2)); break
                if op2 == 0x09 and rs2 == breg and imm2 == lo:        # addiu -> pointer
                    out.append((va2, "abs-ptr", "addiu", rt2)); break
                # base register clobbered before use -> stop following this lui
                if _dst(w2) == breg:
                    break
        o += 4
    return out


_STORES = {0x28: "sb", 0x29: "sh", 0x2a: "swl", 0x2b: "sw", 0x2e: "swr"}
_LOADS = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26}


def find_addr_stores(data, target, base=LOAD_VA, hdr=HDR, span=TEXT_SIZE):
    """Constant-track registers (lui / ori / addiu) through a linear scan and report
    EVERY store whose effective address == target, regardless of idiom. Catches seeds
    the exact-offset xref() misses (e.g. `lui at,hi; ori at,at,lo; sw rt,0(at)` or
    `lui r,hi; addiu r,r,lo; sw rt,0(r)`). Returns [(va, mnemonic, rt, ea_base_const, off)].
    Constant-tracking is linear (no CFG) so treat hits as candidates to disassemble."""
    out = []
    start, end = hdr, min(len(data), hdr + span)
    reg = [None] * 32
    o = start
    while o + 4 <= end:
        w = struct.unpack_from("<I", data, o)[0]
        va = (o - hdr) + base
        op = w >> 26; rs = (w >> 21) & 0x1f; rt = (w >> 16) & 0x1f; rd = (w >> 11) & 0x1f
        imm = w & 0xffff; si = imm - 0x10000 if imm >= 0x8000 else imm
        rsv = 0 if rs == 0 else reg[rs]
        # 1) check stores against current register constants
        if op in _STORES and rsv is not None and ((rsv + si) & 0xffffffff) == (target & 0xffffffff):
            out.append((va, _STORES[op], rt, rsv, si))
        # 2) update the constant model for the written register
        if op == 0x0f:                                   # lui rt, imm
            reg[rt] = (imm << 16) & 0xffffffff
        elif op == 0x0d:                                 # ori rt, rs, imm
            reg[rt] = (rsv | imm) if rsv is not None else None
        elif op in (0x08, 0x09):                         # addi / addiu rt, rs, imm
            reg[rt] = ((rsv + si) & 0xffffffff) if rsv is not None else None
        elif op in _LOADS:                               # load -> rt unknown
            reg[rt] = None
        elif op == 0:                                    # R-type writes rd (jr/jalr write nothing useful)
            if (w & 0x3f) not in (0x08, 0x09) and rd != 0:
                reg[rd] = None
        else:
            d = _dst(w)
            if d is not None and d != 0:
                reg[d] = None
        reg[0] = 0
        o += 4
    return out


def region_stats(data, start, end, base=LOAD_VA, hdr=HDR):
    """METADATA-ONLY statistics over [start,end) of a code/data image — NO raw bytes
    are returned, so the result is committable per [[Preservation Policy]]. Used to
    classify a resident data table (e.g. is it structured vs pseudo-random?):
    size, Shannon entropy (bits/byte; ~8.0 = random), mean (0x80 ⇒ zero-mean as
    signed `byte-0x80`), distinct values, zero count, printable %, and the % of bytes
    within [0x70,0x90] (a 'tightly centred' test)."""
    o0 = (start - base) + hdr
    o1 = (end - base) + hdr
    buf = data[o0:o1]
    n = len(buf)
    if n == 0:
        return {"size": 0}
    hist = [0] * 256
    for x in buf:
        hist[x] += 1
    ent = -sum((c / n) * math.log2(c / n) for c in hist if c)
    return {
        "size": n,
        "entropy_bits": round(ent, 3),
        "mean": round(sum(buf) / n, 2),
        "distinct": sum(1 for c in hist if c),
        "zeros": n - sum(1 for x in buf if x),
        "printable_pct": round(100 * sum(1 for x in buf if 32 <= x < 127) / n, 1),
        "near80_pct": round(100 * sum(1 for x in buf if 0x70 <= x <= 0x90) / n, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--dump", type=lambda x: int(x, 16))
    ap.add_argument("--len", type=lambda x: int(x, 0), default=64)
    ap.add_argument("--table", type=lambda x: int(x, 16))
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--xref", type=lambda x: int(x, 16))
    ap.add_argument("--gp", type=lambda x: int(x, 16), default=DEFAULT_GP)
    ap.add_argument("--disasm", type=lambda x: int(x, 16))
    ap.add_argument("--store-ea", type=lambda x: int(x, 16),
                    help="report ALL stores whose effective address == this VA (any lui/ori/addiu idiom)")
    ap.add_argument("--region-stats", type=lambda x: int(x, 16),
                    help="metadata-only stats (entropy/mean/distinct/...) over [VA, --region-end)")
    ap.add_argument("--region-end", type=lambda x: int(x, 16),
                    help="end VA (exclusive) for --region-stats")
    ap.add_argument("--base", type=lambda x: int(x, 16), default=LOAD_VA,
                    help="image load VA (overlay: 0x800b39a0); default = EXE 0x80010000")
    ap.add_argument("--hdr", type=lambda x: int(x, 0), default=HDR,
                    help="bytes of file header before code (overlay: 0); default = EXE 0x800")
    a = ap.parse_args()
    data = open(a.exe, "rb").read()
    base, hdr = a.base, a.hdr
    span = TEXT_SIZE if base == LOAD_VA else (len(data) - hdr)
    def foff(va):
        return (va - base) + hdr

    if a.disasm is not None:
        o = foff(a.disasm)
        print(f"# disasm VA 0x{a.disasm:08x}, {a.count} instructions")
        for i in range(a.count):
            w = struct.unpack_from("<I", data, o + i * 4)[0]
            va = a.disasm + i * 4
            print(f"  0x{va:08x}: {disasm_one(va, w)}")
        return 0

    if a.dump is not None:
        o = foff(a.dump)
        print(f"# hexdump VA 0x{a.dump:08x} (file 0x{o:x}), {a.len} B")
        for i in range(0, a.len, 16):
            words = " ".join(f"{struct.unpack_from('<I', data, o + i + j)[0]:08x}" for j in range(0, 16, 4) if o + i + j + 4 <= len(data))
            print(f"  0x{a.dump + i:08x}: {words}")
        return 0

    if a.table is not None:
        o = foff(a.table)
        print(f"# table @ VA 0x{a.table:08x} (file 0x{o:x}), {a.count} u32-LE entries")
        for i in range(a.count):
            v = struct.unpack_from("<I", data, o + i * 4)[0]
            region = "OVERLAY-A/B" if 0x800b39a0 <= v <= 0x800bffff else ("resident" if 0x80010000 <= v <= RESIDENT_END else "")
            print(f"{i:>3} 0x{v:08x}  {region}")
        return 0

    if getattr(a, "region_stats", None) is not None:
        end = a.region_end if a.region_end is not None else (a.region_stats + 0x100)
        st = region_stats(data, a.region_stats, end, base=base, hdr=hdr)
        print(f"# region-stats VA 0x{a.region_stats:08x}..0x{end:08x} (metadata only, no bytes)")
        for k, v in st.items():
            print(f"  {k:14s} {v}")
        return 0

    if getattr(a, "store_ea", None) is not None:
        res = find_addr_stores(data, a.store_ea, base=base, hdr=hdr, span=span)
        print(f"# effective-address stores to VA 0x{a.store_ea:08x} (base=0x{base:08x},hdr=0x{hdr:x}) — {len(res)} hits")
        for va, mn, rt, eab, off in res:
            print(f"  0x{va:08x}  {mn} {REGS[rt]},{off}({REGS[0] if eab==0 else 'r'})  ea=0x{(eab+off)&0xffffffff:08x} (basereg const 0x{eab:08x})")
        return 0

    if a.xref is not None:
        res = xref(data, a.xref, a.gp, base=base, hdr=hdr, span=span)
        stores = [r for r in res if r[2][0] == "s"]
        loads = [r for r in res if r[2][0] == "l" and r[1] != "abs-ptr"]
        ptrs = [r for r in res if r[1] == "abs-ptr"]
        print(f"# xref VA 0x{a.xref:08x} (gp=0x{a.gp:08x}, gp-off 0x{(a.xref - a.gp) & 0xffff:x}) — {len(res)} hits")
        print(f"WRITERS ({len(stores)}):")
        for va, k, mn, rt in stores:
            print(f"  0x{va:08x}  {mn} r{rt} ({k})")
        print(f"READERS ({len(loads)}):")
        for va, k, mn, rt in loads:
            print(f"  0x{va:08x}  {mn} r{rt} ({k})")
        if ptrs:
            print(f"POINTER-MATERIALIZE ({len(ptrs)}):")
            for va, k, mn, rt in ptrs:
                print(f"  0x{va:08x}  {mn} r{rt}")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
