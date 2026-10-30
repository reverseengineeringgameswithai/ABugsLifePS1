#!/usr/bin/env python3
"""
Relocation-aware scanner + inserter for A Bug's Life LEVEL .DAT files.

Reproduces the EXACT relocation walk performed by the DAT parser fcn.8001cdc0
(SCUS_942.88) so we can (a) list every baked file-offset field, and (b) build a
relocation-aware type-0x3f append/insert that keeps those baked offsets consistent
with the +0x10 data shift.

Parser relocation sites (each does `field += DATbase; store`), from static trace:

  PASS 1  (trailing stride-0x14 table; s3 = trail+0xe; while lh[s3] >= 0)
    flags = lhu[s3]   ; bit3 (0x8) selects path; bit5 (0x20) gates an extra field
    site A : [s3+2]                          (always)            field=4B
    if (flags & 8)==0:   # non-bit3 path
       site B : [s0+0x14]                    (always)
       site C : [s0+0x18]                    (only if flags & 0x20)
    else:                # bit3 path
       site D : [s0+0x1c]                    (always)
       site E : [s0+0x20]                    (only if flags & 0x20)
    (s0 = value read at [s3+2]; coordinate fields s0+0x12/0x16 are NOT relocated)

  PASS 2  (stride-4 pointer array right after pass1; base p2; n=lw[p2])
    for i in 0..n (inclusive):  a0 = p2 + 4*i
       v = lw[a0+4]; if v != 0:  site F : [a0+4]
    (the entry's [target+0x10] etc. are read as already-relocated pointers, not
     relocated here -> not baked-offset fields)

  PASS 3  (trailing stride-0x14 table after pass2; s3p = p3+0xe; while lh[s3p]>=0)
    flags = lhu[s3p]; bit3 (0x8) selects path
    site G : [s3p+2]                         (always)
    if (flags & 8)==0:  site H : [s0+0x14]
    else:               site I : [s0+0x1c]

Only fields whose CURRENT value is a real in-file offset into the shifted region
([INSERT_OFF, filesize)) are bumped by +0x10; values < INSERT_OFF (header/0x3f
region, unshifted) or outside the file (heap-relative negatives) are left alone.
"""
import struct
import sys

INSERT_OFF = 0x468       # end of type-0x3f entries (rec1 start) — the insertion point
ENTRY_BASE = 0x0008
ENTRY_SIZE = 0x10
T3F_HDR = 0x0004


class DAT:
    def __init__(self, data):
        self.d = bytes(data)

    def u32(self, o): return struct.unpack_from("<I", self.d, o)[0]
    def s32(self, o): return struct.unpack_from("<i", self.d, o)[0]
    def u16(self, o): return struct.unpack_from("<H", self.d, o)[0]
    def s16(self, o): return struct.unpack_from("<h", self.d, o)[0]

    # ---- top-level record walk (mirrors 0x8001ce8c..0x8001cf1c) ----
    def record_size(self, off):
        cnt = self.u16(off)
        typ = self.s16(off + 2)
        if typ >= 0:
            return (4 + cnt * 0x10) if typ == 0x3f else (4 + cnt * 0xc)
        return (((3 * cnt + 1) >> 1) << 2) + 0x10

    def trailing_base(self):
        n = self.u32(0)
        s2 = 4
        recs = []
        for _ in range(n):
            sz = self.record_size(s2)
            recs.append((s2, self.s16(s2 + 2), self.u16(s2), sz))
            s2 += sz
        # post-records advance: w=[s2]; s2 += (w<<7)+4   (0x8001cf20..0x8001cf30)
        w = self.u32(s2)
        s2 += (w << 7) + 4
        return s2, recs

    # ---- full relocation site enumeration ----
    def scan_sites(self):
        """Return list of dicts: {field, value, site, pass}. field = file offset of
        the 4-byte baked offset; value = current stored value."""
        sites = []
        trail, _ = self.trailing_base()

        # ---------- PASS 1 ----------
        s3 = trail + 0xe
        # gate: if first lh[s3] < 0 -> pass1 skipped (0x8001cf44 bltz)
        if self.s16(s3) >= 0:
            while self.s16(s3) >= 0:
                flags = self.u16(s3)
                a = s3 + 2
                s0 = self.u32(a)
                sites.append(dict(field=a, value=s0, site="P1.A [s3+2]", p=1))
                if (flags & 8) == 0:
                    f = s0 + 0x14
                    sites.append(dict(field=f, value=self.u32(f), site="P1.B [s0+0x14]", p=1))
                    if flags & 0x20:
                        f = s0 + 0x18
                        sites.append(dict(field=f, value=self.u32(f), site="P1.C [s0+0x18]", p=1))
                else:
                    f = s0 + 0x1c
                    sites.append(dict(field=f, value=self.u32(f), site="P1.D [s0+0x1c]", p=1))
                    if flags & 0x20:
                        f = s0 + 0x20
                        sites.append(dict(field=f, value=self.u32(f), site="P1.E [s0+0x20]", p=1))
                s3 += 0x14
        # locate pass2 base by faithful s2 register tracking:
        # s2 starts at trail; +=0x14 once per branch-eval (== #entries) + 1 extra (0x8001d1d8)
        # equivalently s2 = trail + 0x14*(N+1) where N = #pass1 entries; if pass1 skipped, s2 = trail+0x14
        n1 = (s3 - (trail + 0xe)) // 0x14
        p2 = trail + 0x14 * (n1 + 1)

        # ---------- PASS 2 ----------
        if self.s32(p2) >= 0:
            cnt = self.s32(p2)
            for i in range(cnt + 1):              # a1 = 0..cnt inclusive
                a0 = p2 + 4 * i
                f = a0 + 4
                v = self.u32(f)
                if v != 0:
                    sites.append(dict(field=f, value=v, site="P2.F [a0+4]", p=2))
        # ---------- PASS 3 ----------
        # p3 = p2 + (cnt<<2) + 8   (0x8001d2c0..0x8001d2c8), 32-bit register math
        cnt2 = self.u32(p2)
        p3 = (p2 + ((cnt2 << 2) & 0xffffffff) + 8) & 0xffffffff
        s3p = p3 + 0xe
        if self.s16(s3p) >= 0:
            while self.s16(s3p) >= 0:
                flags = self.u16(s3p)
                a = s3p + 2
                s0 = self.u32(a)
                sites.append(dict(field=a, value=s0, site="P3.G [s3+2]", p=3))
                if (flags & 8) == 0:
                    f = s0 + 0x14
                    sites.append(dict(field=f, value=self.u32(f), site="P3.H [s0+0x14]", p=3))
                else:
                    f = s0 + 0x1c
                    sites.append(dict(field=f, value=self.u32(f), site="P3.I [s0+0x1c]", p=3))
                s3p += 0x14

        return sites, dict(trail=trail, p2=p2, p3=p3)


def build_reloc_insert(orig_bytes, new_entry_bytes, verbose=True):
    """Return (new_dat_bytes, patch_report). Inserts new_entry at INSERT_OFF as a
    new type-0x3f entry, bumps the count, and applies relocation-aware fix-ups."""
    assert len(new_entry_bytes) == ENTRY_SIZE
    src = DAT(orig_bytes)
    orig_size = len(orig_bytes)

    sites, meta = src.scan_sites()

    # dedupe-check: no physical field may be relocated twice (parser invariant)
    seen = {}
    for s in sites:
        if s["field"] in seen:
            raise SystemExit(f"FIELD {s['field']:#x} relocated twice "
                             f"({seen[s['field']]} & {s['site']}) — model error")
        seen[s["field"]] = s["site"]

    # 1) build shifted file (naive byte shift) + bump count
    new = bytearray(orig_bytes[:INSERT_OFF] + new_entry_bytes + orig_bytes[INSERT_OFF:])
    cnt, typ = struct.unpack_from("<HH", new, T3F_HDR)
    assert typ == 0x3f and cnt == src.u16(T3F_HDR)
    struct.pack_into("<H", new, T3F_HDR, cnt + 1)

    # 2) apply relocation fix-ups
    report = []
    for s in sites:
        fo, val, site = s["field"], s["value"], s["site"]
        # field's new physical location (it lives in shifted region)
        new_fo = fo + (0x10 if fo >= INSERT_OFF else 0)
        # bump value only if it is an in-file offset into the shifted region
        is_off = INSERT_OFF <= val < orig_size
        new_val = val + 0x10 if is_off else val
        if is_off:
            struct.pack_into("<I", new, new_fo, new_val)
        report.append(dict(field=fo, new_field=new_fo, old=val, new=new_val,
                           site=site, bumped=is_off))
    return bytes(new), report, sites, meta


def _hexdump_line(label, b):
    return f"{label}: {b.hex()}"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("dat")
    ap.add_argument("--scan", action="store_true", help="just list relocation sites")
    ap.add_argument("--clone-entry", type=int)
    ap.add_argument("--dx", type=int, default=0)
    ap.add_argument("--dy", type=int, default=0)
    ap.add_argument("--dz", type=int, default=0)
    ap.add_argument("--entry-bytes", help="hex of the 16-byte new entry (overrides clone)")
    ap.add_argument("--out")
    args = ap.parse_args()

    data = open(args.dat, "rb").read()
    src = DAT(data)

    if args.scan:
        sites, meta = src.scan_sites()
        print(f"trail={meta['trail']:#x} p2={meta['p2']:#x} p3={meta['p3']:#x}")
        print(f"total relocation sites: {len(sites)}")
        bypass = {}
        for s in sites:
            bypass.setdefault(s["p"], 0)
            bypass[s["p"]] += 1
        print("by pass:", bypass)
        for s in sites:
            print(f"  {s['site']:<16} field={s['field']:#08x} value={s['value']:#010x}")
        return

    # build new entry
    if args.entry_bytes:
        ne = bytes.fromhex(args.entry_bytes)
    else:
        o = ENTRY_BASE + args.clone_entry * ENTRY_SIZE
        x, y, z, k = struct.unpack_from("<iiiI", data, o)
        ne = struct.pack("<iiiI", x + args.dx, y + args.dy, z + args.dz, k)

    new, report, sites, meta = build_reloc_insert(data, ne)
    if args.out:
        open(args.out, "wb").write(new)
    print(f"out={args.out} size {len(data)} -> {len(new)} (+{len(new)-len(data)})")
    print(f"new entry bytes: {ne.hex()}")
    bumped = sum(1 for r in report if r["bumped"])
    print(f"relocation fields: {len(report)} total, {bumped} bumped (+0x10)")


if __name__ == "__main__":
    main()
