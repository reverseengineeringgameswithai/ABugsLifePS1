/* RCA a4 (2026-07-09): SUPERSEDED for build purposes — 0x8001cdc0 is byte-matched in the
   shipping build as asm/hand_written/8001cdc0_dat_parser_relocator.s (config/segments.yml `attempted`;
   validate_build.py SHA-1 PASS). This src_re file is documentation-grade pseudocode,
   retained for its analysis/comments; it is NOT the build unit. */
/* ============================================================================
 * dat_parser_8001cdc0.c  —  DAT parser / relocator            [PHASE 1 — DECOMPILED]
 * ----------------------------------------------------------------------------
 * ORIGINAL ADDRESS : fcn.8001cdc0  (size 1548 bytes, 0x8001cdc0..0x8001d3cc)
 * CONFIDENCE       : CONFIRMED (control flow + all 9 relocation sites verified vs
 *                    tools/dat_reloc.py = 1248 LEVEL01 sites). Some auxiliary globals/
 *                    output-record semantics are LIKELY (labelled inline).
 * SOURCE NOTES     : docs/DAT_FORMAT_AND_RELOCATION.md, docs/EXPERIMENT_LOG.md,
 *                    r2 disasm (asm.arch=mips bits=32 LE anal.gp=0x80081d98).
 * KNOWN CALLERS    : fcn.8003cf2c @0x8003d568 (level/resource loader).
 *                    a0 = path/scratch (IGNORED inside — overwritten), a1 = output-buffer
 *                    byte offset (added to DATbase). Caller advances its buffer by retval.
 * KNOWN CALLEES    : fcn.80017b98 (GTE rotation-matrix setup; relocates NOTHING),
 *                    fcn.8003eec8 (epilogue finalize; a0 = 0/1).
 * KNOWN GLOBALS    : G_DAT_BASE_PTR(0x80082498 / gp+0x700), G_TYPE_TABLE(0x80096da0),
 *                    G_TRAIL_BLOCK_PTR(0x800824ac / gp+0x714), G_PASS2_BASE_PTR(0x80082338 /
 *                    gp+0x5a0), G_PASS3_BASE_PTR(0x80082508 / gp+0x770),
 *                    G_DAT_ENTRY_COUNTER(0x800822f0 / gp+0x558), 0x80091210.. (pass2 out table),
 *                    0x800b1ff4/1ff8/220c/2210 (init consts 0x200/0xf0), 0x80082504 (scene id),
 *                    gp+0x5f4/0x5fc/0x6a8/0x494/0x514/0x5c0/0x5c4/0x604/0x550 (parser scratch).
 * UNRESOLVED       : exact meaning of the *128 trailing-sizing word [s2]; purpose of the
 *                    0x80091210.. 16-bit table built by pass 2; semantics of scene-gated
 *                    sizes 0x580/0x500/0x600 at gp+0x5f4; the bit3-path 3x3 vector transform's
 *                    product (it applies the GTE matrix to out-record halfwords).
 *
 * RELOCATION SITE SUMMARY (CONFIRMED; matches tools/dat_reloc.py):
 *   PASS 1 (stride 0x14): A=[s3+2] always; non-bit3 -> B=[s0+0x14] (+C=[s0+0x18] if flag 0x20);
 *                         bit3 -> D=[s0+0x1c] (+E=[s0+0x20] if flag 0x20).   (LEVEL01: 968)
 *   PASS 2 (stride 4)   : F=[a0+4] if nonzero.                                (LEVEL01: 0, empty)
 *   PASS 3 (stride 0x14): G=[s3+2] always; non-bit3 -> H=[s0+0x14]; bit3 -> I=[s0+0x1c].
 *                                                                            (LEVEL01: 280)
 *   LEVEL01 total = 1248. Flag bit 0x20 is never set in LEVEL01 -> C/E never fire.
 *   NOT relocated (must NOT be touched): dynamic type table entries; [s0+0x12]/[s0+0x16]
 *   (scale halfwords); the pass-2 deref chain ([R+0x10], [s4+0x18]) which is read AFTER its
 *   own relocation; everything outside the 9 sites.
 * ============================================================================ */

#include "re_types.h"

/* ---- access helpers expressing MIPS load widths/signedness (pseudocode) ---- */
/*  LW=lw (signed word)   LH=lh (sign-extended half)   LHU=lhu (zero-extended half)
 *  SW=sw (word store)     SH=sh (halfword store)  */
#define LW(p)   (*(int32_t  *)(p))     /* lw  */
#define LH(p)   (*(int16_t  *)(p))     /* lh  (sign-extended)  */
#define LHU(p)  (*(uint16_t *)(p))     /* lhu (zero-extended)  */
#define SW(p,v) (*(int32_t  *)(p) = (int32_t)(v))
#define SH(p,v) (*(uint16_t *)(p) = (uint16_t)(v))

/* Arithmetic-shift-right with MIPS round-toward-zero idiom used throughout the
 * vector transform: `if (x < 0) x += 0xfff; x >>= 0xc;`  (i.e. trunc(x / 4096)). */
static inline int32_t sra12_rtz(int32_t x) { if (x < 0) x += 0xfff; return x >> 12; }

/* callees (decompilation pending in later phases / out of Phase-1 scope) */
extern void fcn_80017b98(void *angles /*=s0+0xc*/, void *out /*=s4*/); /* GTE rot-matrix setup */
extern void fcn_8003eec8(int a0);                                       /* epilogue finalize */

/*
 * fcn.8001cdc0 — parse the loaded DAT and relocate its internal baked file offsets.
 * Returns the number of output bytes produced (entries_processed * 0x20). arg1 ignored.
 */
int32_t dat_parse_relocate(void *arg1_ignored, int32_t out_off /* = a1 -> s5 */)
{
    (void)arg1_ignored;

    /* ---- prologue: fixed init constants (0x8001cdc4..0x8001cdf8) ---- */
    SW(0x800b1ff4, 0x200);  SW(0x800b220c, 0x200);   /* CONFIRMED writes; purpose UNKNOWN */
    SW(0x800b1ff8, 0x0f0);  SW(0x800b2210, 0x0f0);   /* CONFIRMED writes; purpose UNKNOWN */

    int32_t scene_id = LW(0x80082504);               /* current scene id (CONFIRMED global) */
    SW(0x80082394 /*gp+0x5fc*/, 0x600);              /* LIKELY a default size; purpose UNKNOWN */
    /* scene-gated size selection -> gp+0x5f4 (0x8008238c) (purpose UNKNOWN) */
    if      (scene_id == 0xf) SW(0x8008238c, 0x580);
    else if (scene_id == 0xb) SW(0x8008238c, 0x500);
    else                      SW(0x8008238c, 0x600);

    int32_t s5_out = out_off;                         /* s5 = arg2 = output-buffer offset */

    /* ---- init parser scratch (0x8001ce58..0x8001ce6c) ---- */
    uint8_t *DATbase = (uint8_t *)(uintptr_t)LW(G_DAT_BASE_PTR); /* [gp+0x700] */
    uint8_t *s2 = DATbase;
    SW(0x80082358 /*gp+0x5c0*/, 0);                   /* UNKNOWN */
    SW(0x8008235c /*gp+0x5c4*/, 0);                   /* UNKNOWN */
    SW(0x8008222c /*gp+0x494*/, 0xc00);               /* UNKNOWN */
    SW(0x800822ac /*gp+0x514*/, 0);                   /* UNKNOWN */

    int32_t rec_count = LW(s2);                       /* top-level record count (signed) */
    uint8_t *type_table = (uint8_t *)G_TYPE_TABLE;    /* a0 = 0x80096da0 */

    /* ===================================================================
     * (1) TOP-LEVEL RECORD WALK + dynamic type-table build (0x8001ce8c..)
     * Skipped entirely if rec_count <= 0 (blez).
     * =================================================================== */
    if (rec_count > 0) {
        s2 += 4;                                       /* point at first record header */
        int32_t n = rec_count;
        do {
            int16_t type = LH(s2 + 2);                 /* record type (signed half) */
            int32_t size;
            if (type < 0) {
                /* negative type: store at table + |type|*4 (subu a0 - type*4) */
                SW(type_table - (type << 2), (int32_t)(uintptr_t)s2);  /* type table (NOT a reloc) */
                int32_t cnt = LH(s2);                  /* count */
                /* size = ((3*cnt + 1) >> 1) << 2) + 0x10   (>>1 is arithmetic w/ sign add) */
                int32_t t = 3 * cnt + 1;
                t = (t + ((uint32_t)t >> 31)) >> 1;    /* srl 0x1f; addu; sra 1  (round toward 0) */
                size = (t << 2) + 0x10;
            } else {
                /* non-negative type: store at table + type*4 */
                SW(type_table + (type << 2), (int32_t)(uintptr_t)s2);  /* type table (NOT a reloc) */
                int32_t cnt = LH(s2);                  /* count */
                if (type == 0x3f) size = (cnt << 4) + 4;          /* 4 + cnt*0x10 */
                else              size = ((3 * cnt) << 2) + 4;    /* 4 + cnt*0x0c */
            }
            s2 += size;                                /* advance to next record */
        } while (--n > 0);                             /* bgtz */
    }

    /* ===================================================================
     * (2) TRAILING RELOCATION-BLOCK discovery (0x8001cf20..0x8001cf50)
     * w = lw[s2]; s2 += (w<<7)+4;  trail = s2.   (LEVEL01: w==0 -> +4)
     * =================================================================== */
    {
        int32_t w = LW(s2);
        s2 += (w << 7) + 4;
    }
    DATbase = (uint8_t *)(uintptr_t)LW(G_DAT_BASE_PTR); /* reload (v0) */
    int16_t first_flags = LH(s2 + 0xe);
    SW(G_DAT_ENTRY_COUNTER, 0);                        /* gp+0x558 = 0 (entries processed) */
    SW(G_TRAIL_BLOCK_PTR, (int32_t)(uintptr_t)s2);     /* gp+0x714 = trail */

    /* ===================================================================
     * (3) PASS 1 — stride-0x14 relocation table (0x8001cf54..0x8001d1d4)
     * Runs only if first_flags >= 0 (bltz -> skip to pass 2).
     * s3 walks the table; s4/s1 build 0x20-byte output records at DATbase+out.
     * =================================================================== */
    if (first_flags >= 0) {
        uint8_t *out_s4 = DATbase + s5_out;            /* s4 = DATbase + arg2 */
        uint8_t *s3 = s2 + 0xe;
        uint8_t *s1 = out_s4 + 0x18;
        for (;;) {
            SW(G_DAT_ENTRY_COUNTER, LW(G_DAT_ENTRY_COUNTER) + 1); /* count++ */
            uint16_t flags = LHU(s3);
            if (flags & 0x80) SH(s3, (uint16_t)((flags | 0x50) - 0x10)); /* flag normalize */

            uint8_t *s0;
            if ((LHU(s3) & 8) == 0) {
                /* ---- non-bit3 path ---- */
                s0 = (uint8_t *)(uintptr_t)(LW(s3 + 2) + (int32_t)(uintptr_t)DATbase); /* SITE A */
                SW(s3 + 2, (int32_t)(uintptr_t)s0);
                SW(s0 + 0x14, LW(s0 + 0x14) + (int32_t)(uintptr_t)DATbase);            /* SITE B */
                uint16_t f2 = LHU(s3);
                if (f2 & 0x20) {                                                       /* SITE C (gated; never LEVEL01) */
                    SH(s3, (uint16_t)(f2 | 0x40));
                    SW(s0 + 0x18, LW(s0 + 0x18) + (int32_t)(uintptr_t)DATbase);
                }
                /* GTE rotation-matrix setup from angle fields at s0+0xc into out_s4 */
                fcn_80017b98(s0 + 0xc, out_s4);
                SW(s1, (int32_t)(uintptr_t)s0);        /* [s1] = s0 */
                /* non-bit3 path SKIPS the vector transform (j 0x8001d1b8) */
            } else {
                /* ---- bit3 path ---- */
                s0 = (uint8_t *)(uintptr_t)(LW(s3 + 2) + (int32_t)(uintptr_t)DATbase); /* SITE A */
                SW(s3 + 2, (int32_t)(uintptr_t)s0);
                SW(s0 + 0x1c, LW(s0 + 0x1c) + (int32_t)(uintptr_t)DATbase);            /* SITE D */
                uint16_t f2 = LHU(s3);
                if (f2 & 0x20) {                                                       /* SITE E (gated; never LEVEL01) */
                    SH(s3, (uint16_t)(f2 | 0x40));
                    SW(s0 + 0x20, LW(s0 + 0x20) + (int32_t)(uintptr_t)DATbase);
                }
                fcn_80017b98(s0 + 0xc, out_s4);

                /* CONFIRMED 3x3 matrix scale (0x8001d04c..0x8001d1b0): the 3x3 rotation matrix
                 * that fcn.80017b98 wrote at out_s4+0..+0x10 (9 int16) is scaled IN PLACE,
                 * column-by-column, by the object's per-axis scale halfwords
                 * m0=[s0+0x12], m1=[s0+0x14], m2=[s0+0x16]; each elem = (elem*scale)>>12 (rtz).
                 * Builds a scale*rotation matrix. NOT a relocation. (In the bit3 path s0+0x14 is
                 * this SCALE halfword, NOT a relocated pointer.) Offsets relative to out_s4: */
                int16_t m0 = LH(s0 + 0x12), m1 = LH(s0 + 0x14), m2 = LH(s0 + 0x16);
                SH(out_s4 + 0x00, sra12_rtz(LH(out_s4 + 0x00) * m0)); /* s1-0x18 */
                SH(out_s4 + 0x06, sra12_rtz(LH(out_s4 + 0x06) * m0)); /* s1-0x12 */
                SH(out_s4 + 0x0c, sra12_rtz(LH(out_s4 + 0x0c) * m0)); /* s1-0x0c */
                SH(out_s4 + 0x02, sra12_rtz(LH(out_s4 + 0x02) * m1)); /* s1-0x16 */
                SH(out_s4 + 0x08, sra12_rtz(LH(out_s4 + 0x08) * m1)); /* s1-0x10 */
                SH(out_s4 + 0x0e, sra12_rtz(LH(out_s4 + 0x0e) * m1)); /* s1-0x0a */
                SH(out_s4 + 0x04, sra12_rtz(LH(out_s4 + 0x04) * m2)); /* s1-0x14 */
                SH(out_s4 + 0x0a, sra12_rtz(LH(out_s4 + 0x0a) * m2)); /* s1-0x0e */
                SH(out_s4 + 0x10, sra12_rtz(LH(out_s4 + 0x10) * m2)); /* s1-0x08 */
                SW(s1, (int32_t)(uintptr_t)s0);        /* [s1] = s0 */
            }

            s1 += 0x20;
            SW(s3 + 2, (int32_t)(uintptr_t)out_s4);    /* [s3+2] = out ptr (overwrites SITE A in RAM) */
            out_s4 += 0x20;
            s3 += 0x14;
            if (LH(s3) < 0) break;                      /* bgez continues; here we stop */
            s2 += 0x14;                                 /* delay-slot increments s2 each iter */
        }
        s2 += 0x14;                                     /* one extra (0x8001d1d8) on loop exit */
    } else {
        s2 += 0x14;                                     /* bltz path lands at 0x8001d1d8 */
    }

    /* ===================================================================
     * (4) PASS 2 — stride-4 pointer array (0x8001d1dc..0x8001d2ac)
     * n = lw[s2]; relocate [s2+4+4i] for i=0..n (if nonzero). LEVEL01: n=-1 -> empty.
     * =================================================================== */
    SW(G_PASS2_BASE_PTR, (int32_t)(uintptr_t)s2);       /* gp+0x5a0 = s2 */
    int32_t p2_count = LW(s2);
    if (p2_count >= 0) {
        uint8_t *a2 = s2;
        uint8_t *a0 = s2;
        int32_t v1 = 0;                                 /* output-table byte cursor (0x80091210..) */
        int32_t a1 = 0;
        do {
            int32_t ptr = LW(a0 + 4);
            if (ptr != 0) {
                uint8_t *R = (uint8_t *)(uintptr_t)(ptr + (int32_t)(uintptr_t)DATbase); /* SITE F */
                SW(a0 + 4, (int32_t)(uintptr_t)R);
                SH(0x80091216 + v1, LHU(R + 0xe));
                R = (uint8_t *)(uintptr_t)LW(a0 + 4);
                uint8_t *s4b = (uint8_t *)(uintptr_t)LW(R + 0x10);     /* already-relocated ptr (deref only) */
                uint8_t *s0b = (uint8_t *)(uintptr_t)LW(s4b + 0x18);   /* deref only */
                SH(0x80091218 + v1, LHU(s0b + 0xc));
                SH(0x8009121a + v1, LHU(s0b + 0xe));
                SH(0x8009121c + v1, LHU(s0b + 0x10));
                SH(0x80091210 + v1, LHU(s0b + 0x12));
                SH(0x80091212 + v1, LHU(s0b + 0x14));
                SH(0x80091214 + v1, LHU(s0b + 0x16));
            }
            v1 += 0x10;
            a1 += 1;
            a0 += 4;                                     /* delay slot */
        } while (LW(a2) >= a1);                          /* slt(count,a1); loop while count >= a1 */
    }

    /* ===================================================================
     * (5) PASS 3 — stride-0x14 relocation table (0x8001d2b0..0x8001d35c)
     * p3 = pass2base + (count<<2) + 8  (32-bit). Runs if lh[p3+0xe] >= 0.
     * =================================================================== */
    {
        uint8_t *p2 = (uint8_t *)(uintptr_t)LW(G_PASS2_BASE_PTR);
        int32_t cnt = LW(p2);
        uint8_t *p3 = p2 + (int32_t)(((uint32_t)cnt << 2) + 8); /* 32-bit wrap intended */
        SW(G_PASS3_BASE_PTR, (int32_t)(uintptr_t)p3);   /* gp+0x770 = p3 */
        if (LH(p3 + 0xe) >= 0) {
            uint8_t *a0 = p3 + 0xe;
            for (;;) {
                uint16_t flags = LHU(a0);
                SW(G_DAT_ENTRY_COUNTER, LW(G_DAT_ENTRY_COUNTER) + 1);
                uint8_t *s0;
                if ((flags & 8) == 0) {
                    s0 = (uint8_t *)(uintptr_t)(LW(a0 + 2) + (int32_t)(uintptr_t)DATbase); /* SITE G */
                    SW(a0 + 2, (int32_t)(uintptr_t)s0);
                    SW(s0 + 0x14, LW(s0 + 0x14) + (int32_t)(uintptr_t)DATbase);            /* SITE H */
                } else {
                    s0 = (uint8_t *)(uintptr_t)(LW(a0 + 2) + (int32_t)(uintptr_t)DATbase); /* SITE G */
                    SW(a0 + 2, (int32_t)(uintptr_t)s0);
                    SW(s0 + 0x1c, LW(s0 + 0x1c) + (int32_t)(uintptr_t)DATbase);            /* SITE I */
                }
                a0 += 0x14;
                if (LH(a0) < 0) break;                   /* bgez continues */
            }
        }
    }

    /* ===================================================================
     * (6) EPILOGUE (0x8001d360..0x8001d3c8)
     * =================================================================== */
    DATbase = (uint8_t *)(uintptr_t)LW(G_DAT_BASE_PTR);
    uint8_t *out_end = DATbase + s5_out;
    int32_t tail = LW(out_end - 4);
    int32_t a0_fin;
    if (tail != -1) { SW(0x8008239c /*gp+0x604*/, (int32_t)(uintptr_t)out_end - tail); a0_fin = 1; }
    else            { a0_fin = 0; }
    fcn_8003eec8(a0_fin);

    int32_t entries = LW(G_DAT_ENTRY_COUNTER);
    SW(0x800822e8 /*gp+0x550*/, 0x190);                 /* UNKNOWN */
    return entries << 5;   /* LIKELY: output bytes produced = entries * 0x20 (caller advances buffer) */
}

/* ----------------------------------------------------------------------------
 * PHASE 1 FINDINGS (feed back to docs / re_types.h):
 *  - CONFIRMED: all 9 relocation sites (A..I) and their flag gating match the model and
 *    tools/dat_reloc.py (LEVEL01: 968 pass1 + 0 pass2 + 280 pass3 = 1248).
 *  - CONFIRMED: dynamic type-table store (pos: table+type*4; neg: table+|type|*4) is rebuilt,
 *    not relocated. Record-size rules reproduced exactly (0x3f:4+cnt*0x10; other pos:4+cnt*0xc;
 *    neg:((3cnt+1)>>1)*4+0x10).
 *  - LIKELY: return value = (#pass1+#pass3 entries) << 5 = output bytes (records are 0x20 each);
 *    caller fcn.8003cf2c adds it to its buffer pointer. gp+0x558 (0x800822f0) = that entry counter.
 *  - CONFIRMED: bit3-path block scales the GTE rotation matrix (out_s4+0..+0x10, 9 int16) in place,
 *    column j by scale m_j=[s0+0x12/0x14/0x16], elem=(elem*scale)>>12 (rtz). Orientation*scale, NOT a reloc.
 *  - UNKNOWN: pass-2 output table @0x80091210.., scene-gated sizes @gp+0x5f4, the *128 trailing word.
 * ---------------------------------------------------------------------------- */
