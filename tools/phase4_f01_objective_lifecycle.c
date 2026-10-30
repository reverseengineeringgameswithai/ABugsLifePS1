/*
 * phase4_f01_objective_lifecycle.c -- Phase 4 row F01 (Stage 1 "Anthill"):
 * the WHOLE objective law and the WHOLE scene-transition lifecycle, recovered
 * statically from the shipped images with no emulator in the loop.
 *
 * The prior F01 pass bound one natural completion (region code 2 -> latch ->
 * timer -> teardown -> results).  That is one ARM of one dispatch.  This tool
 * enumerates the rest:
 *
 *   1. THE OBJECTIVE.  The collision region-code dispatch inside
 *      player_vertical_update is a five-way switch on the signed region code
 *      returned by FUNC_80038F38, guarded by a re-entry test on the transition
 *      request word.  Codes 1 and 4 route to the player DAMAGE handler; codes
 *      2 and 3 complete the scene.  All five arms, their branch targets and
 *      their effects are pinned as exact instruction words, so "reach the
 *      entrance" is upgraded from a description to a decided switch.
 *
 *   2. THE LIFECYCLE.  A gp-aware MIPS census (lui+addiu, lui+ori and
 *      $gp-relative forms, $gp = 0x80081D98) over the resident executable and
 *      every shipped overlay enumerates every reader and writer of the
 *      transition request word, its countdown timer and the scene-flow state.
 *      Stored constants are recovered by forward constant propagation, with an
 *      explicit join-crossed flag so a merged value is never reported as if it
 *      were linear.
 *
 *   3. THE FOOTPRINT.  LEVEL01's LEVEL.RAW chunk 32 is decompressed in-process
 *      and sector 177 -- the campaign-unique authored code-2 sector -- is
 *      walked down to its individual collision planes, giving the exact
 *      authored trigger geometry rather than just its origin.
 *
 * Inputs:  argv[1] = disc file root (the directory holding SCUS_942.88, BITS/,
 *          LEVEL00/ ... LEVEL10/).
 * Output:  JSON on stdout.  Exit 0 iff every pinned assertion holds.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/f01 tools/phase4_f01_objective_lifecycle.c
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ------------------------------------------------------------------ io --- */

static uint8_t *readall(const char *p, size_t *n)
{
    FILE *f = fopen(p, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); long z = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc((size_t)z ? (size_t)z : 1);
    if (!b || fread(b, 1, (size_t)z, f) != (size_t)z) { free(b); fclose(f); return NULL; }
    fclose(f); *n = (size_t)z; return b;
}
static uint32_t le32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }
static int32_t  les32(const uint8_t *p) { int32_t v; memcpy(&v, p, 4); return v; }
static int16_t  les16(const uint8_t *p) { int16_t v; memcpy(&v, p, 2); return v; }
static uint32_t be32(const uint8_t *p)
{ return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3]; }

/* --------------------------------------------- LEVEL.RAW chunk decoder --- */
/* Byte-exact reimplementation of the shipped LZ codec (same routine as
 * tools/phase4_f01_static.c; kept local so this tool has no Python or
 * cross-tool dependency). */

typedef struct { uint8_t *p; size_t n, cap; } Buf;
static void put(Buf *b, uint8_t v)
{
    if (b->n == b->cap) {
        b->cap = b->cap ? b->cap * 2 : 65536;
        b->p = realloc(b->p, b->cap);
        if (!b->p) exit(2);
    }
    b->p[b->n++] = v;
}
static uint8_t hist(const Buf *b, int64_t i)
{ return i >= 0 ? (i < (int64_t)b->n ? b->p[i] : 0) : 0; }

typedef struct { const uint8_t *c; size_t n, pos; Buf out; uint32_t t2, t7; int32_t t0, t1; } Dec;
static uint8_t rd(Dec *d)
{ if (d->pos >= d->n) { fprintf(stderr, "compressed input overrun\n"); exit(2); } return d->c[d->pos++]; }
static void bit(Dec *d)
{
    d->t2 *= 2; d->t7 = (d->t2 >> 8) & 1; d->t2 &= 0xff;
    if (!d->t2) { d->t2 = rd(d); d->t2 = d->t2 * 2 + d->t7; d->t7 = (d->t2 >> 8) & 1; }
}
static Buf dechunk(const uint8_t *c, size_t n)
{
    Dec d = { .c = c, .n = n, .pos = 0x0e };
    d.t7 = 1; d.t2 = rd(&d); d.t2 = d.t2 * 2 + d.t7; d.t2 *= 2; d.t7 = (d.t2 >> 8) & 1;
    enum { MAIN, MATCH, MATCH_BODY, A470, LEN_C, E724, SWAP, DIST, LITRUN } s = MAIN;
    uint64_t guard = 0;
    for (;;) {
        if (++guard > 20000000) { fprintf(stderr, "decode guard\n"); exit(2); }
        switch (s) {
        case MAIN:
            d.t2 *= 2; d.t7 = (d.t2 >> 8) & 1;
            if (d.t7) { s = MATCH; break; }
            put(&d.out, rd(&d));
            d.t2 *= 2; d.t7 = (d.t2 >> 8) & 1;
            if (!d.t7) { put(&d.out, rd(&d)); s = MAIN; } else s = MATCH;
            break;
        case MATCH:
            d.t2 &= 0xff;
            if (!d.t2) {
                d.t2 = rd(&d); d.t2 = d.t2 * 2 + d.t7; d.t7 = (d.t2 >> 8) & 1;
                if (!d.t7) { put(&d.out, rd(&d)); s = MAIN; break; }
            }
            s = MATCH_BODY; break;
        case MATCH_BODY:
            d.t0 = 2; d.t1 = 0; bit(&d);
            if (!d.t7) { s = A470; break; }
            bit(&d);
            if (!d.t7) { s = DIST; break; }
            d.t0++; bit(&d);
            if (d.t7) {
                d.t0 = rd(&d);
                if (!d.t0) { bit(&d); if (d.t7) { s = MAIN; break; } return d.out; }
                d.t0 += 8;
            }
            s = LEN_C; break;
        case A470:
            bit(&d); d.t0 = d.t0 * 2 + (int)d.t7; bit(&d);
            if (!d.t7) { s = LEN_C; break; }
            d.t0--; bit(&d); d.t0 = d.t0 * 2 + (int)d.t7;
            s = d.t0 == 9 ? LITRUN : LEN_C; break;
        case LEN_C:
            bit(&d);
            if (!d.t7) { s = DIST; break; }
            bit(&d); d.t1 = d.t1 * 2 + (int)d.t7; bit(&d);
            if (d.t7) { s = E724; break; }
            if (d.t1) { s = SWAP; break; }
            d.t1++; bit(&d); d.t1 = d.t1 * 2 + (int)d.t7; s = SWAP; break;
        case E724:
            bit(&d); d.t1 = d.t1 * 2 + (int)d.t7; d.t1 |= 4; bit(&d);
            if (d.t7) { s = SWAP; break; }
            bit(&d); d.t1 = d.t1 * 2 + (int)d.t7; s = SWAP; break;
        case SWAP:
            d.t1 = ((d.t1 << 8) & 0xff00) | ((uint32_t)d.t1 >> 8); s = DIST; break;
        case DIST: {
            uint32_t dist = (uint32_t)(d.t1 & 0xff00) | rd(&d);
            int64_t ref = (int64_t)d.out.n - dist - 1;
            for (int i = 0; i < d.t0; i++) put(&d.out, hist(&d.out, ref + i));
            s = MAIN; break;
        }
        case LITRUN:
            d.t0 = 3; d.t1 = 0;
            do { bit(&d); d.t1 = d.t1 * 2 + (int)d.t7; d.t0--; } while (d.t0 >= 0);
            d.t1 += 2;
            while (d.t1-- >= 0) for (int i = 0; i < 4; i++) put(&d.out, rd(&d));
            s = MAIN; break;
        }
    }
}

/* -------------------------------------------------------- image model --- */

typedef struct {
    const char *name;
    uint32_t base;          /* vaddr of image byte 0 (after any file header) */
    size_t   skip;          /* file bytes before the mapped image */
    uint8_t *bytes;
    size_t   len;
} Image;

static int img_word(const Image *im, uint32_t a, uint32_t *out)
{
    if (a < im->base) return 0;
    size_t off = im->skip + (size_t)(a - im->base);
    if (off + 4 > im->len) return 0;
    *out = le32(im->bytes + off);
    return 1;
}

/* -------------------------------------------------- MIPS xref scanner --- */

#define GP_VALUE 0x80081D98u

enum { ACC_LB, ACC_LH, ACC_LWL, ACC_LW, ACC_LBU, ACC_LHU, ACC_LWR,
       ACC_SB, ACC_SH, ACC_SWL, ACC_SW, ACC_SWR, ACC_NONE };
static const char *acc_name[] = { "lb", "lh", "lwl", "lw", "lbu", "lhu", "lwr",
                                  "sb", "sh", "swl", "sw", "swr", "?" };
static int acc_is_store(int a) { return a >= ACC_SB && a != ACC_NONE; }

typedef struct {
    const char *image;
    uint32_t pc;
    int kind;               /* ACC_* */
    uint32_t addr;
    int have_value;         /* store source register constant recovered */
    int32_t value;
    uint32_t value_def_pc;
    int joins_crossed;      /* branch targets between def and use (0 == linear) */
    int base_joins;         /* same, for the address base register */
} Hit;

static Hit  *hits; static size_t nhits, caphits;
static void add_hit(Hit h)
{
    if (nhits == caphits) {
        caphits = caphits ? caphits * 2 : 256;
        hits = realloc(hits, caphits * sizeof *hits);
        if (!hits) exit(2);
    }
    hits[nhits++] = h;
}

/* per-register constant state during the linear scan */
typedef struct { int valid; int32_t v; uint32_t def_pc; int joins; } RegSt;

static int acc_kind_of(uint32_t op)
{
    switch (op) {
    case 0x20: return ACC_LB;  case 0x21: return ACC_LH;  case 0x22: return ACC_LWL;
    case 0x23: return ACC_LW;  case 0x24: return ACC_LBU; case 0x25: return ACC_LHU;
    case 0x26: return ACC_LWR; case 0x28: return ACC_SB;  case 0x29: return ACC_SH;
    case 0x2a: return ACC_SWL; case 0x2b: return ACC_SW;  case 0x2e: return ACC_SWR;
    default:   return ACC_NONE;
    }
}

/* Pass 1: every in-image branch/jump target, so a join point can be flagged. */
static void collect_targets(const Image *im, uint8_t *tgt, size_t words)
{
    for (size_t i = 0; i < words; i++) {
        uint32_t pc = im->base + (uint32_t)(i * 4);
        uint32_t w = le32(im->bytes + im->skip + i * 4);
        uint32_t op = w >> 26;
        uint32_t t = 0; int have = 0;
        if (op == 2 || op == 3) {
            t = ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2); have = 1;
        } else if (op == 1 || (op >= 4 && op <= 7) || op == 0x14 || op == 0x15 ||
                   op == 0x16 || op == 0x17) {
            int32_t s = (int16_t)(w & 0xffff);
            t = pc + 4 + (uint32_t)(s * 4); have = 1;
        }
        if (have && t >= im->base) {
            size_t ti = (t - im->base) / 4;
            if (ti < words) tgt[ti] = 1;
        }
    }
}

/* Register-based struct accesses the absolute census cannot see: every
 * load/store whose immediate offset is one of `offs`, with the stored constant
 * recovered where it is linear.  This is how the query gate's WRITERS are
 * found -- they all address the player through a live base register. */
typedef struct {
    const char *image; uint32_t pc; int kind; int off; int base_reg;
    int have_value; int32_t value;
} OffHit;
static OffHit *offhits; static size_t noffhits, capoffhits;
static int regioncode_stores; static uint32_t regioncode_store_pcs[16];
/* bulk-write audit: every `jal` whose a0 (destination) and a2 (length) are both
 * statically constant, so [a0, a0+a2) can be tested against a watched word.
 * This is the memset/memcpy-shaped vector a store-site census cannot see -- the
 * B06 failure mode, where a transition clear was memset(block, 0, 168). */
static int bulk_calls_seen, bulk_calls_covering;
static uint32_t bulk_cover_pcs[16];
static void add_offhit(OffHit h)
{
    if (noffhits == capoffhits) {
        capoffhits = capoffhits ? capoffhits * 2 : 256;
        offhits = realloc(offhits, capoffhits * sizeof *offhits);
        if (!offhits) exit(2);
    }
    offhits[noffhits++] = h;
}

static void scan_image(const Image *im, const uint32_t *watch, size_t nwatch)
{
    size_t words = (im->len - im->skip) / 4;
    uint8_t *tgt = calloc(words, 1);
    if (!tgt) exit(2);
    collect_targets(im, tgt, words);

    RegSt r[32];
    memset(r, 0, sizeof r);
    r[0].valid = 1; r[0].v = 0;
    r[28].valid = 1; r[28].v = (int32_t)GP_VALUE;   /* proven constant $gp */
    int joins = 0;

    for (size_t i = 0; i < words; i++) {
        uint32_t pc = im->base + (uint32_t)(i * 4);
        uint32_t w = le32(im->bytes + im->skip + i * 4);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31, rd = (w >> 11) & 31;
        int32_t simm = (int16_t)(w & 0xffff);
        uint32_t uimm = w & 0xffff;

        if (tgt[i]) joins++;             /* a merge happened at this pc */

        int kind = acc_kind_of(op);
        /* bulk-call audit: jal with constant a0 and a2 */
        if (op == 0x03 && r[4].valid && r[6].valid) {
            uint32_t dst = (uint32_t)r[4].v;
            int32_t len = r[6].v;
            if (dst >= 0x80000000u && dst < 0x80200000u && len > 0 && len < 0x200000) {
                bulk_calls_seen++;
                if (0x800823a0u >= dst && 0x800823a0u < dst + (uint32_t)len) {
                    if (bulk_calls_covering < 16) bulk_cover_pcs[bulk_calls_covering] = pc;
                    bulk_calls_covering++;
                }
            }
        }
        /* region-code field writer census: any store with the sector-table
         * +0x2E displacement, whatever its base register */
        if (acc_is_store(kind) && (simm & 0xffff) == 0x7e76) {
            regioncode_store_pcs[regioncode_stores < 16 ? regioncode_stores : 15] = pc;
            regioncode_stores++;
        }
        /* struct-offset census (base register need not be constant) */
        if (kind != ACC_NONE && rs != 0 && rs != 28) {
            static const int track_offs[] = { 0x7c, 0x7e, 0x80, 0x82, 0x84, 0x92, 0x560 };
            for (size_t k = 0; k < sizeof track_offs / sizeof track_offs[0]; k++) {
                if (simm != track_offs[k]) continue;
                OffHit oh = { im->name, pc, kind, (int)simm, (int)rs, 0, 0 };
                if (acc_is_store(kind) && r[rt].valid) { oh.have_value = 1; oh.value = r[rt].v; }
                add_offhit(oh);
            }
        }
        if (kind != ACC_NONE && r[rs].valid) {
            uint32_t ea = (uint32_t)(r[rs].v + simm);
            for (size_t k = 0; k < nwatch; k++) {
                if (ea != watch[k]) continue;
                /* $zero and $gp are architecturally constant: a value sourced
                 * from them crosses no join, however many merges the linear
                 * scan has walked past. */
                Hit h = { im->name, pc, kind, ea, 0, 0, 0, 0,
                          rs == 28 ? 0 : joins - r[rs].joins };
                if (acc_is_store(kind) && r[rt].valid) {
                    h.have_value = 1; h.value = r[rt].v;
                    h.value_def_pc = rt == 0 ? 0 : r[rt].def_pc;
                    h.joins_crossed = rt == 0 ? 0 : joins - r[rt].joins;
                }
                add_hit(h);
            }
        }

        /* constant transfer */
        switch (op) {
        case 0x0f:  /* lui */
            if (rt) { r[rt].valid = 1; r[rt].v = (int32_t)(uimm << 16); r[rt].def_pc = pc; r[rt].joins = joins; }
            break;
        case 0x09:  /* addiu */
            if (rt) {
                if (r[rs].valid) { r[rt].valid = 1; r[rt].v = r[rs].v + simm;
                                   r[rt].def_pc = pc; r[rt].joins = joins; }
                else r[rt].valid = 0;
            }
            break;
        case 0x0d:  /* ori */
            if (rt) {
                if (r[rs].valid) { r[rt].valid = 1; r[rt].v = (int32_t)((uint32_t)r[rs].v | uimm);
                                   r[rt].def_pc = pc; r[rt].joins = joins; }
                else r[rt].valid = 0;
            }
            break;
        case 0x00:  /* SPECIAL */
            switch (w & 0x3f) {
            case 0x21: case 0x20:   /* addu / add */
                if (rd) {
                    if (r[rs].valid && r[rt].valid) { r[rd].valid = 1; r[rd].v = r[rs].v + r[rt].v;
                                                      r[rd].def_pc = pc; r[rd].joins = joins; }
                    else r[rd].valid = 0;
                }
                break;
            case 0x09:              /* jalr */
                for (int q = 2; q < 32; q++)
                    if ((q >= 2 && q <= 15) || q == 24 || q == 25 || q == 31) r[q].valid = 0;
                break;
            case 0x08: break;       /* jr */
            default:
                if (rd && rd != 28) r[rd].valid = 0;
                break;
            }
            break;
        case 0x03:  /* jal */
            for (int q = 2; q < 32; q++)
                if ((q >= 2 && q <= 15) || q == 24 || q == 25 || q == 31) r[q].valid = 0;
            break;
        default:
            /* every other rt-writing form kills the constant */
            if (op == 0x08 || op == 0x0a || op == 0x0b || op == 0x0c || op == 0x0e ||
                (op >= 0x20 && op <= 0x26))
                { if (rt && rt != 28) r[rt].valid = 0; }
            break;
        }
        r[0].valid = 1; r[0].v = 0;
        r[28].valid = 1; r[28].v = (int32_t)GP_VALUE;
    }
    free(tgt);
}

/* ------------------------------------------------------------- pins ----- */

typedef struct { uint32_t a, w; const char *n; } Pin;

static int check_pins(const Image *exe, const Pin *p, size_t n, char *failbuf, size_t failcap)
{
    int bad = 0; size_t used = 0;
    for (size_t i = 0; i < n; i++) {
        uint32_t got = 0;
        if (!img_word(exe, p[i].a, &got) || got != p[i].w) {
            bad++;
            if (used + 64 < failcap)
                used += (size_t)snprintf(failbuf + used, failcap - used, "%s%s@%08x",
                                         used ? "," : "", p[i].n, p[i].a);
        }
    }
    return bad;
}

/* branch target of a MIPS I-form branch word at pc */
static uint32_t btgt(uint32_t pc, uint32_t w) { return pc + 4 + (uint32_t)((int16_t)(w & 0xffff) * 4); }
static uint32_t jtgt(uint32_t pc, uint32_t w) { return ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2); }

/* --------------------------------------------------------------- main --- */

static char pathbuf[4096];
static const char *P(const char *root, const char *rel)
{ snprintf(pathbuf, sizeof pathbuf, "%s/%s", root, rel); return pathbuf; }

int main(int argc, char **argv)
{
    if (argc != 2) { fprintf(stderr, "usage: %s <disc_files_root>\n", argv[0]); return 2; }
    const char *root = argv[1];

    size_t en = 0;
    uint8_t *exeb = readall(P(root, "SCUS_942.88"), &en);
    if (!exeb) { perror("SCUS_942.88"); return 2; }
    Image exe = { "SCUS_942.88", 0x80010000u, 0x800, exeb, en };

    int fail = 0;
    char failbuf[512]; failbuf[0] = 0;

    /* ============================================================= (1) ===
     * The objective: the five-way collision region-code dispatch.
     * Every word below is asserted; the branch targets are decoded from the
     * asserted words, so the arm map cannot drift from the shipped code. */
    const Pin dispatch_pins[] = {
        /* --- the query, FUNC_80038F38 ------------------------------------ */
        { 0x80038f38, 0x90a30000, "query_gate_lbu_a1_0" },
        { 0x80038f3c, 0x24020001, "query_gate_const_1" },
        { 0x80038f40, 0x1462000e, "query_gate_bne_ret0" },
        { 0x80038f44, 0x00001021, "query_gate_ret0_delay" },
        { 0x80038f5c, 0x8c230560, "query_current_sector_lw" },
        { 0x80038f78, 0x84227e76, "query_region_code_lh" },
        { 0x80038f7c, 0x03e00008, "query_ret" },
        /* --- the call site, inside player_vertical_update ----------------- */
        { 0x80049640, 0x00002021, "call_a0_player0" },
        { 0x80049644, 0x0c00e3ce, "call_query" },
        { 0x80049648, 0x26250082, "call_a1_player_plus_0x82" },
        { 0x8004964c, 0x00401821, "code_to_v1" },
        { 0x80049650, 0x1060004f, "code0_skip" },
        { 0x80049654, 0xafa30028, "code_spill" },
        { 0x80049658, 0x3c028008, "latch_guard_hi" },
        { 0x8004965c, 0x844223a0, "latch_guard_lh" },
        { 0x80049664, 0x1440004a, "latch_guard_bnez_skip" },
        { 0x80049668, 0x24020002, "const_2" },
        { 0x8004966c, 0x10620015, "code2_beq" },
        { 0x80049670, 0x28620003, "slti_3" },
        { 0x80049674, 0x10400005, "ge3_beqz" },
        { 0x80049678, 0x24020001, "const_1" },
        { 0x8004967c, 0x1062000a, "code1_beq" },
        { 0x80049684, 0x080125d2, "default_join_lo" },
        { 0x8004968c, 0x24020003, "const_3" },
        { 0x80049690, 0x10620015, "code3_beq" },
        { 0x80049694, 0x24020004, "const_4" },
        { 0x80049698, 0x1062001f, "code4_beq" },
        { 0x800496a0, 0x080125d2, "default_join_hi" },
        /* --- arm bodies --------------------------------------------------- */
        { 0x800496a8, 0x00002821, "code1_a1_zero" },
        { 0x800496ac, 0x27a6002c, "code1_a2_sp2c" },
        { 0x800496b0, 0x0c0129c0, "code1_call_damage" },
        { 0x800496b4, 0x24070001, "code1_a3_one" },
        { 0x800496b8, 0x24090001, "code1_flag_one" },
        { 0x800496c0, 0xa7a90050, "code1_flag_store" },
        { 0x800496c4, 0x24090001, "code2_flag_one" },
        { 0x800496c8, 0x2404003a, "code2_sfx_58" },
        { 0x800496d0, 0x24020001, "code2_request_1" },
        { 0x800496d8, 0xa42223a0, "code2_request_store" },
        { 0x800496dc, 0x24020017, "code2_timer_23" },
        { 0x800496e0, 0x080125c0, "code2_join_timer" },
        { 0x800496e4, 0xa7a90050, "code2_flag_store" },
        { 0x800496e8, 0x2404003a, "code3_sfx_58" },
        { 0x800496f0, 0x24020001, "code3_request_1" },
        { 0x800496f8, 0xa42223a0, "code3_request_store" },
        { 0x800496fc, 0x24020017, "code3_timer_23" },
        { 0x80049704, 0xa4222470, "timer_store" },
        { 0x80049708, 0x0c014265, "sfx_call" },
        { 0x80049718, 0x8622007e, "code4_read_7e" },
        { 0x80049720, 0x14400009, "code4_7e_bail" },
        { 0x80049728, 0x86220092, "code4_read_92" },
        { 0x80049730, 0x14400005, "code4_92_bail" },
        { 0x80049740, 0x0c0129c0, "code4_call_damage" },
        { 0x80049744, 0x00003821, "code4_a3_zero" },
        /* --- the join: flag -> position commit + gate clear ---------------- */
        /* the commit flag is zero-initialised in the prologue and set by
         * ONLY the code-1 and code-2 arms, so code 3's body is code 2's body
         * minus exactly this one store -- refining E02's "identical". */
        { 0x800481bc, 0xa7a00050, "commit_flag_init_zero" },
        { 0x80049748, 0x97a90050, "join_read_flag" },
        { 0x80049754, 0x1040000e, "join_flag_beqz" },
        { 0x80049770, 0xa6200082, "join_clear_gate_0x82" },
        { 0x80049790, 0x86220082, "join_read_gate" },
        { 0x80049798, 0x10400002, "join_gate_beqz" },
        { 0x800497a0, 0xaf80073c, "join_gp73c_clear" },
        /* --- the gate's producer: the movement integrator FUNC_8003633C ---
         * player_vertical_update hands it &player+0x82 as a2; on floor contact
         * it writes byte 1 twice, giving the little-endian 0x0101 the query
         * gate then reads as low byte 1.  It also materialises the per-player
         * current-sector slot 0x80090560 + index and hands it to the sector
         * resolvers, so grounding and sector membership have one owner. */
        { 0x800495b8, 0x26260082, "integrator_a2_is_gate" },
        { 0x80036c00, 0x3c1e8009, "sector_slot_hi" },
        { 0x80036c04, 0x27de0560, "sector_slot_lo" },
        { 0x80036c14, 0x00fe9821, "sector_slot_index" },
        { 0x80036cb8, 0xa2d10000, "grounded_set_byte0" },
        { 0x80036cc0, 0xa2d10001, "grounded_set_byte1" },
        { 0x80036c50, 0x0c00d7c9, "grounded_sector_resolver" },
        { 0x80036c54, 0x02603821, "grounded_resolver_a3_slot" },
        /* --- the polygon record layout, asserted at its only reader --------
         * FUNC_80038090 is the point-in-polygon region test.  It reads the
         * normal at +0x00, the first vertex at +0x06 and TWO edge deltas at
         * +0x0c/+0x10 and +0x12/+0x16, i.e. each 0x20-byte record is a
         * TRIANGLE, not a lone plane. */
        { 0x80038138, 0x85420002, "poly_normal_y" },
        { 0x80038140, 0x0441015d, "poly_floor_only" },
        { 0x80038150, 0x8542000c, "poly_delta1_x" },
        { 0x80038154, 0x85430010, "poly_delta1_z" },
        /* --- the consumer: request!=0 && timer==0 -> teardown -------------- */
        { 0x8004fef0, 0x844223a0, "consumer_request_read" },
        { 0x8004ff04, 0x84422470, "consumer_timer_read" },
        { 0x8004ff30, 0x10620007, "consumer_request2_skips_finalizer" },
        { 0x8004ff48, 0x0c011698, "consumer_finalizer_call" },
        { 0x800553f8, 0xa4222470, "timer_decrement_store" },
        /* --- the death arm of the same request word ------------------------
         * The region codes 1 and 4 enter player_damage_handler, whose a3 is a
         * BRANCH FLAG (moved to s4, tested by bnez), not a destination.  The
         * request word only reaches value 2 after the health decrement leaves
         * health negative, so a hazard region requests a transition only when
         * the damage it deals is lethal. */
        { 0x8004a720, 0x00e0a021, "damage_a3_to_s4" },
        { 0x8004a73c, 0x1680003a, "damage_a3_is_a_flag" },
        { 0x8004a888, 0xa4236594, "damage_health_decrement" },
        { 0x8004a890, 0x04610016, "damage_death_gate" },
        /* --- the region-code field has EXACTLY TWO writers ------------------
         * Both are the authored source->runtime conversion (src +0x2C ->
         * runtime +0x2E, E02's mapping): a `lw v0, 0x2c(t1)` immediately
         * feeding `sh v0, 0x7e76(at)`.  The census below proves these are the
         * only two across the resident image AND every shipped overlay, so a
         * runtime region code can only ever be sourced from authored data --
         * which is what lets the LEVEL01 authored census speak for the whole
         * 223-entry runtime table. */
        { 0x80030f88, 0x8d22002c, "regioncode_src_load_a" },
        { 0x80030f94, 0xa4227e76, "regioncode_store_a" },
        { 0x80031258, 0x8d22002c, "regioncode_src_load_b" },
        { 0x80031264, 0xa4227e76, "regioncode_store_b" },
        { 0x8004a8b4, 0xa42223a0, "damage_request_2" },
        { 0x8004a8c0, 0xa4222470, "damage_timer_60" },
    };
    fail += check_pins(&exe, dispatch_pins, sizeof dispatch_pins / sizeof dispatch_pins[0],
                       failbuf, sizeof failbuf);

    /* decode the arm map from the (now asserted) branch words */
    uint32_t w_code2 = 0, w_code1 = 0, w_ge3 = 0, w_code3 = 0, w_code4 = 0, w_def = 0, w_join = 0;
    img_word(&exe, 0x8004966c, &w_code2); img_word(&exe, 0x8004967c, &w_code1);
    img_word(&exe, 0x80049674, &w_ge3);   img_word(&exe, 0x80049690, &w_code3);
    img_word(&exe, 0x80049698, &w_code4); img_word(&exe, 0x80049684, &w_def);
    img_word(&exe, 0x800496e0, &w_join);
    uint32_t t_code1 = btgt(0x8004967c, w_code1), t_code2 = btgt(0x8004966c, w_code2);
    uint32_t t_ge3   = btgt(0x80049674, w_ge3),   t_code3 = btgt(0x80049690, w_code3);
    uint32_t t_code4 = btgt(0x80049698, w_code4), t_def   = jtgt(0x80049684, w_def);
    uint32_t t_join  = jtgt(0x800496e0, w_join);

    if (t_code1 != 0x800496a8 || t_code2 != 0x800496c4 || t_ge3 != 0x8004968c ||
        t_code3 != 0x800496e8 || t_code4 != 0x80049718 || t_def != 0x80049748 ||
        t_join  != 0x80049700) fail++;

    /* code 3 falls through 0x800496fc -> 0x80049700 (the shared timer store),
     * so it shares code 2's effect except the sp+0x50 commit flag. */
    uint32_t w_fall = 0; img_word(&exe, 0x800496fc, &w_fall);
    if (w_fall != 0x24020017) fail++;

    /* ============================================================= (2) ===
     * The lifecycle: every access to the transition-request word, the
     * countdown timer, the scene-flow state, and the gp+0x73c companion. */
    const uint32_t watch[] = {
        0x800823a0u,   /* scene transition request */
        0x80082470u,   /* transition countdown timer */
        0x80082504u,   /* scene-flow state */
        0x800824d4u,   /* gp+0x73c, cleared beside the gate */
        0x800a6582u,   /* player[0] + 0x82, the query gate byte */
        0x80090560u,   /* player[0] current collision sector index */
        0x800a6580u,   /* the word that overlaps the gate byte */
    };
    const size_t nwatch = sizeof watch / sizeof watch[0];

    scan_image(&exe, watch, nwatch);

    /* every shipped overlay, at its proven load base */
    struct { const char *name; const char *rel; uint32_t base; } ovl[] = {
        { "BITS/MEMORY.BIN",     "BITS/MEMORY.BIN",     0x800b5788u },
        { "LEVEL00/LEVEL.BIN",   "LEVEL00/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL01/LEVEL.BIN",   "LEVEL01/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL01/LEVEL1.BIN",  "LEVEL01/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL02/LEVEL.BIN",   "LEVEL02/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL02/LEVEL1.BIN",  "LEVEL02/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL03/LEVEL.BIN",   "LEVEL03/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL03/LEVEL1.BIN",  "LEVEL03/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL04/LEVEL.BIN",   "LEVEL04/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL04/LEVEL1.BIN",  "LEVEL04/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL05/LEVEL.BIN",   "LEVEL05/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL05/LEVEL1.BIN",  "LEVEL05/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL06/LEVEL.BIN",   "LEVEL06/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL06/LEVEL1.BIN",  "LEVEL06/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL07/LEVEL.BIN",   "LEVEL07/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL07/LEVEL1.BIN",  "LEVEL07/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL08/LEVEL.BIN",   "LEVEL08/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL08/LEVEL1.BIN",  "LEVEL08/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL09/LEVEL.BIN",   "LEVEL09/LEVEL.BIN",   0x800b39a0u },
        { "LEVEL09/LEVEL1.BIN",  "LEVEL09/LEVEL1.BIN",  0x800b39a0u },
        { "LEVEL10/LEVEL.BIN",   "LEVEL10/LEVEL.BIN",   0x800b39a0u },
    };
    const size_t novl = sizeof ovl / sizeof ovl[0];
    size_t images_scanned = 1, images_missing = 0;
    for (size_t i = 0; i < novl; i++) {
        size_t n = 0;
        uint8_t *b = readall(P(root, ovl[i].rel), &n);
        if (!b) { images_missing++; continue; }
        Image im = { ovl[i].name, ovl[i].base, 0, b, n };
        scan_image(&im, watch, nwatch);
        images_scanned++;
        /* the bytes stay live: hits reference im.name only, which is static */
    }

    /* ============================================================= (3) ===
     * LEVEL01 chunk 32: sector census + sector 177's collision footprint. */
    size_t rn = 0;
    uint8_t *raw = readall(P(root, "LEVEL01/LEVEL.RAW"), &rn);
    if (!raw) { perror("LEVEL01/LEVEL.RAW"); return 2; }
    Buf ch = { 0 }; uint32_t declared = 0; size_t off = 0; int chunks = 0;
    while (off + 8 <= rn) {
        uint32_t w0 = be32(raw + off);
        if (w0 == 0xffffffffu) break;
        uint32_t w1 = be32(raw + off + 4);
        if (off + (size_t)0x0e + w1 > rn) { fprintf(stderr, "bad chunk table\n"); return 2; }
        if (chunks == 32) { declared = w0; ch = dechunk(raw + off, (size_t)0x0e + w1); }
        off += (size_t)0x0e + w1; chunks++;
    }
    if (!ch.p || ch.n != declared) { fprintf(stderr, "chunk32 decode mismatch\n"); return 2; }

    const size_t SO = 0x36570, STRIDE = 0x4c, COUNT = 189, BLOCK_BASE = 8;
    if (SO + COUNT * STRIDE > ch.n) { fprintf(stderr, "sector array out of range\n"); return 2; }

    int nonzero = 0, code2n = 0, code2_sector = -1;
    int code_hist[8]; memset(code_hist, 0, sizeof code_hist);
    long block_run = BLOCK_BASE, target_block = -1, target_end = -1;
    int32_t s177[19];
    for (size_t i = 0; i < COUNT; i++) {
        const uint8_t *s = ch.p + SO + i * STRIDE;
        int32_t code = les32(s + 0x2c);
        int32_t bsz  = les32(s + 0x04);
        if (code) nonzero++;
        if (code >= 0 && code < 8) code_hist[code]++;
        if (code == 2) { code2n++; code2_sector = (int)i; }
        if ((int)i == 177) {
            for (int k = 0; k < 19; k++) s177[k] = les32(s + k * 4);
            if (bsz > 0) { target_block = block_run; target_end = block_run + (long)bsz * 2; }
        }
        if (bsz > 0) block_run += (long)bsz * 2;
    }

    /* walk sector 177's block: groups of 0x20-byte plane records */
    const int32_t s177_ox = s177[2], s177_oy = s177[3], s177_oz = s177[4];
    long groups = 0, planes = 0, floors = 0, ceilings = 0, walls = 0;
    long tri_normal_ok = 0, tri_normal_bad = 0;
    int32_t minx = 0, maxx = 0, miny = 0, maxy = 0, minz = 0, maxz = 0;
    int have_bounds = 0;
    char plane_json[8192]; size_t pj = 0; plane_json[0] = 0;
    if (target_block >= 0 && target_end <= (long)ch.n) {
        long b = target_block;
        while (b + 2 <= target_end) {
            int16_t marker = les16(ch.p + b);
            if (marker < 0) break;
            if (b + 12 > target_end) break;
            int16_t cnt = les16(ch.p + b + 2);
            if (cnt < 0 || b + 12 + (long)cnt * 0x20 > target_end + 2) break;
            groups++;
            for (int k = 0; k < cnt; k++) {
                const uint8_t *p = ch.p + b + 12 + (long)k * 0x20;
                /* canon layout (tools/edit_collision_plane.py, resolver
                 * FUNC_800345CC): s16 normal at +0x00, s16 sector-local
                 * reference point at +0x06; the remaining 20 bytes are dumped
                 * verbatim rather than guessed at. */
                int16_t nx = les16(p), ny = les16(p + 2), nz = les16(p + 4);
                int16_t rx = les16(p + 6), ry = les16(p + 8), rz = les16(p + 10);
                /* two edge deltas -> the other two triangle vertices */
                int16_t d1x = les16(p + 0x0c), d1y = les16(p + 0x0e), d1z = les16(p + 0x10);
                int16_t d2x = les16(p + 0x12), d2y = les16(p + 0x14), d2z = les16(p + 0x16);
                planes++;
                if (ny < 0) floors++; else if (ny > 0) ceilings++; else walls++;

                /* PROOF that the record really is a triangle rather than a
                 * plane plus opaque padding: rebuild the surface normal from
                 * the cross product of the two decoded edges and require it to
                 * reproduce the SHIPPED normal (which is stored negated, at
                 * |n| == 0x4000).  If the +0x0c/+0x12 fields were anything but
                 * edge deltas this cannot hold. */
                {
                    double cx = (double)d1y * d2z - (double)d1z * d2y;
                    double cy = (double)d1z * d2x - (double)d1x * d2z;
                    double cz = (double)d1x * d2y - (double)d1y * d2x;
                    double m = cx * cx + cy * cy + cz * cz;
                    if (m > 0) {
                        m = 16384.0 / sqrt(m);
                        long ex = lround(-cx * m), ey = lround(-cy * m), ez = lround(-cz * m);
                        long ddx = ex - nx, ddy = ey - ny, ddz = ez - nz;
                        if (ddx * ddx + ddy * ddy + ddz * ddz > 3 * 2 * 2) tri_normal_bad++;
                        else tri_normal_ok++;
                    }
                }
                if (!have_bounds) {
                    minx = maxx = rx; miny = maxy = ry; minz = maxz = rz;
                    have_bounds = 1;
                } else {
                    if (rx < minx) minx = rx;
                    if (rx > maxx) maxx = rx;
                    if (ry < miny) miny = ry;
                    if (ry > maxy) maxy = ry;
                    if (rz < minz) minz = rz;
                    if (rz > maxz) maxz = rz;
                }
                if (pj + 460 < sizeof plane_json) {
                    const int32_t ox = s177_ox, oy = s177_oy, oz = s177_oz;
                    pj += (size_t)snprintf(plane_json + pj, sizeof plane_json - pj,
                        "%s{\"g\":%ld,\"i\":%d,\"off\":%ld,\"normal\":[%d,%d,%d],"
                        "\"tri_local\":[[%d,%d,%d],[%d,%d,%d],[%d,%d,%d]],"
                        "\"tri_world\":[[%d,%d,%d],[%d,%d,%d],[%d,%d,%d]],"
                        "\"unread_tail_hex\":\"",
                        planes == 1 ? "" : ",", groups - 1, k,
                        b + 12 + (long)k * 0x20, nx, ny, nz,
                        rx, ry, rz,
                        rx + d1x, ry + d1y, rz + d1z,
                        rx + d2x, ry + d2y, rz + d2z,
                        (ox + rx) * 32, (oy + ry) * 32, (oz + rz) * 32,
                        (ox + rx + d1x) * 32, (oy + ry + d1y) * 32, (oz + rz + d1z) * 32,
                        (ox + rx + d2x) * 32, (oy + ry + d2y) * 32, (oz + rz + d2z) * 32);
                    for (int q = 0x18; q < 0x20; q++)
                        pj += (size_t)snprintf(plane_json + pj, sizeof plane_json - pj, "%02x", p[q]);
                    pj += (size_t)snprintf(plane_json + pj, sizeof plane_json - pj, "\"}");
                }
            }
            b += 12 + (long)cnt * 0x20;
        }
    }

    if (code2n != 1 || code2_sector != 177 || nonzero != 1) fail++;
    if (tri_normal_bad != 0 || tri_normal_ok != planes) fail++;
    /* exactly two region-code writers, at the two pinned conversion sites */
    if (regioncode_stores != 2 ||
        regioncode_store_pcs[0] != 0x80030f94u || regioncode_store_pcs[1] != 0x80031264u) fail++;

    /* ---------------------------------------------------------- output --- */
    printf("{\n");
    printf("  \"row\": \"F01_anthill\",\n");
    printf("  \"tool\": \"tools/phase4_f01_objective_lifecycle.c\",\n");
    printf("  \"pins\": {\"asserted\": %zu, \"failed\": %d, \"failed_names\": \"%s\"},\n",
           sizeof dispatch_pins / sizeof dispatch_pins[0],
           check_pins(&exe, dispatch_pins, sizeof dispatch_pins / sizeof dispatch_pins[0],
                      failbuf, sizeof failbuf), failbuf);
    printf("  \"objective\": {\n");
    printf("    \"query\": \"FUNC_80038F38(player_index, &player+0x82)\",\n");
    printf("    \"gate\": \"returns 0 unless *(u8*)(player+0x82) == 1\",\n");
    printf("    \"source\": \"sector = [0x80090560 + idx*20]; code = s16 [0x800a7e48 + sector*0x30 + 0x2e]\",\n");
    printf("    \"reentry_guard\": \"0x8004965c: skip whole dispatch if [0x800823a0] != 0\",\n");
    printf("    \"arms\": [\n");
    printf("      {\"code\": 0, \"target\": null, \"effect\": \"no region; dispatch skipped at 0x80049650\"},\n");
    printf("      {\"code\": 1, \"target\": \"0x%08x\", \"effect\": \"player_damage_handler(0,0,sp+0x2c,a3=1); commit flag sp+0x50=1\"},\n", t_code1);
    printf("      {\"code\": 2, \"target\": \"0x%08x\", \"effect\": \"[0x800823a0]=1; [0x80082470]=23; sfx 58; commit flag sp+0x50=1\"},\n", t_code2);
    printf("      {\"code\": 3, \"target\": \"0x%08x\", \"effect\": \"[0x800823a0]=1; [0x80082470]=23; sfx 58; NO commit flag\"},\n", t_code3);
    printf("      {\"code\": 4, \"target\": \"0x%08x\", \"effect\": \"if player+0x7e==0 && player+0x92==0: player_damage_handler(0,0,sp+0x2c,a3=0)\"},\n", t_code4);
    printf("      {\"code\": \"other\", \"target\": \"0x%08x\", \"effect\": \"join, no effect\"}\n", t_def);
    printf("    ],\n");
    printf("    \"join\": {\"pc\": \"0x%08x\", \"flag\": \"sp+0x50\", \"effect\": \"commit prev->cur position, clear player+0x82\"}\n", t_def);
    printf("  },\n");

    printf("  \"lifecycle_census\": {\"images_scanned\": %zu, \"images_missing\": %zu, \"gp\": \"0x%08x\", \"hits\": [\n",
           images_scanned, images_missing, GP_VALUE);
    for (size_t i = 0; i < nhits; i++) {
        const Hit *h = &hits[i];
        printf("    {\"image\":\"%s\",\"pc\":\"0x%08x\",\"op\":\"%s\",\"addr\":\"0x%08x\",\"dir\":\"%s\"",
               h->image, h->pc, acc_name[h->kind], h->addr, acc_is_store(h->kind) ? "store" : "load");
        if (h->have_value)
            printf(",\"value\":%d,\"value_def_pc\":\"0x%08x\",\"joins_crossed\":%d",
                   h->value, h->value_def_pc, h->joins_crossed);
        else if (acc_is_store(h->kind))
            printf(",\"value\":null");
        printf(",\"base_joins\":%d}%s\n", h->base_joins, i + 1 == nhits ? "" : ",");
    }
    printf("  ]},\n");

    printf("  \"bulk_write_audit\": {\"constant_arg_calls_examined\": %d,\n"
           "    \"calls_whose_dest_range_covers_0x800823a0\": %d, \"pcs\": [",
           bulk_calls_seen, bulk_calls_covering);
    for (int i = 0; i < bulk_calls_covering && i < 16; i++)
        printf("%s\"0x%08x\"", i ? ", " : "", bulk_cover_pcs[i]);
    printf("],\n    \"method\": \"every jal with statically constant a0 (dest) and a2 (len), tested for [a0,a0+a2) covering the transition request word\",\n"
           "    \"closes\": \"the constant-argument bulk-write family only\",\n"
           "    \"does_not_close\": [\"dynamically computed destinations or lengths\", \"indirect calls (jalr / dispatch tables)\", \"callees whose arguments this scan could not recover\", \"callee-performed writes in general\"]},\n");
    printf("  \"region_code_writers\": {\"stores_found\": %d, \"pcs\": [", regioncode_stores);
    for (int i = 0; i < regioncode_stores && i < 16; i++)
        printf("%s\"0x%08x\"", i ? ", " : "", regioncode_store_pcs[i]);
    printf("], \"both_are_authored_source_conversion\": true,\n"
           "    \"consequence\": \"a runtime region code can only be sourced from authored data; nothing in the resident image or any overlay writes the field otherwise\"},\n");
    printf("  \"gate_offset_census\": {\"offsets\": [\"0x7c\", \"0x7e\", \"0x80\", \"0x82\", \"0x84\", \"0x92\", \"0x560\"], \"sites\": [\n");
    for (size_t i = 0; i < noffhits; i++) {
        const OffHit *o = &offhits[i];
        printf("    {\"image\":\"%s\",\"pc\":\"0x%08x\",\"op\":\"%s\",\"off\":\"0x%02x\",\"base_reg\":%d,\"dir\":\"%s\"",
               o->image, o->pc, acc_name[o->kind], o->off, o->base_reg,
               acc_is_store(o->kind) ? "store" : "load");
        if (o->have_value) printf(",\"value\":%d", o->value);
        else if (acc_is_store(o->kind)) printf(",\"value\":null");
        printf("}%s\n", i + 1 == noffhits ? "" : ",");
    }
    printf("  ]},\n");

    printf("  \"level01_chunk32\": {\"decoded_bytes\": %zu, \"sector_array_offset\": \"0x%zx\",\n"
           "    \"sector_stride\": %zu, \"authored_sectors\": %zu,\n"
           "    \"nonzero_region_codes\": %d, \"code_histogram\": {\"0\": %d, \"1\": %d, \"2\": %d, \"3\": %d, \"4\": %d},\n"
           "    \"code2_sector\": %d},\n",
           ch.n, SO, STRIDE, COUNT, nonzero,
           code_hist[0], code_hist[1], code_hist[2], code_hist[3], code_hist[4], code2_sector);

    printf("  \"sector_177\": {\n");
    printf("    \"record_words\": [");
    for (int k = 0; k < 19; k++) printf("%s%d", k ? "," : "", s177[k]);
    printf("],\n");
    printf("    \"block_offset\": %ld, \"block_end\": %ld, \"block_bytes\": %ld,\n",
           target_block, target_end, target_end - target_block);
    printf("    \"groups\": %ld, \"planes\": %ld, \"floors\": %ld, \"ceilings\": %ld, \"vertical\": %ld,\n"
           "    \"triangle_normal_reconstructed\": {\"ok\": %ld, \"bad\": %ld},\n",
           groups, planes, floors, ceilings, walls, tri_normal_ok, tri_normal_bad);
    if (have_bounds)
        printf("    \"ref_extent_sector_local\": {\"x\": [%d,%d], \"y\": [%d,%d], \"z\": [%d,%d]},\n"
               "    \"ref_extent_world_runtime\": {\"x\": [%d,%d], \"y\": [%d,%d], \"z\": [%d,%d]},\n",
               minx, maxx, miny, maxy, minz, maxz,
               (s177[2] + minx) * 32, (s177[2] + maxx) * 32,
               (s177[3] + miny) * 32, (s177[3] + maxy) * 32,
               (s177[4] + minz) * 32, (s177[4] + maxz) * 32);
    printf("    \"plane_records\": [%s]\n", plane_json);
    printf("  },\n");
    printf("  \"assertions_failed\": %d\n", fail);
    printf("}\n");
    return fail != 0;
}
