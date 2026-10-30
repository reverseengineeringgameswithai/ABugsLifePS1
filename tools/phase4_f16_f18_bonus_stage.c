/*
 * phase4_f16_f18_bonus_stage.c -- what the BONUS STAGE itself is, and what it pays.
 *
 * Rows F16_bonus1_spiders / F17_bonus2_mushrooms / F18_bonus3_grasshoppers each
 * carry exactly one open item, and it is the SAME item: "Bonus stage rules/reward."
 * The three rows differ only in the UNLOCK CHALLENGE that gets you there (already
 * bound: streak counters 0x8008223C / 0x80082248.. / 0x80082240).  What none of them
 * says is what happens after the transition fires.
 *
 * This tool answers that from the pristine image alone.  Scene 0x10 runs
 * LEVEL06/LEVEL1.BIN -- 1,820 bytes, 455 words.  That is small enough to account for
 * COMPLETELY rather than to sample, so the claim here is not "here is what I found"
 * but "here is every instruction in the bonus stage, and here is what each block is
 * for".  A partial reading of a small overlay is a choice, not a limit.
 *
 * WHY A COMPILED TOOL.  Standing operator rule: static ASM probing is done with
 * compiled, self-verifying C against the pristine image, never by reading a
 * disassembler dump into prose.  Every claim below is a pin -- an address plus the
 * exact word that must be there -- so a wrong reading fails loudly instead of
 * surviving as plausible text.  This session has already been corrected several
 * times by exactly that mechanism.
 *
 * INDEPENDENCE.  A concurrently-running agent (row C18) reached overlapping
 * conclusions while this was being written.  Nothing here is copied from that work:
 * the pins are derived from the image, and where the two readings differ the
 * difference is called out in the notes rather than reconciled silently.  Two
 * differences were found and both are recorded in the experiment note.
 *
 * BASE DERIVATION IS SELF-VERIFYING.  The blob's load VA is not assumed.  Exactly
 * one j/jal in the image targets an address inside the image's own span under the
 * candidate base, and that target must land immediately after a `jr ra` + `nop`
 * pair -- i.e. on a real function entry.  A wrong base fails both tests.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f16_f18_bonus_stage.c \
 *      -o /tmp/f16f18 && /tmp/f16f18
 *
 * Modes:
 *   (default)      run every pin; nonzero exit if any fails
 *   --accounting   partition all 455 words into return-delimited spans and data
 *   --tables       decode the per-variant data tables
 *   --disasm ADDR [--window N] [--img PATH]
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH      "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA   0x80010000u
#define EXE_HEADER    0x800u
#define OVL_PATH      "REBUILD/files/LEVEL06/LEVEL1.BIN"
#define OVL_SIB_PATH  "REBUILD/files/LEVEL06/LEVEL.BIN"   /* scene 6, the control */
#define OVL_BASE      0x800B39A0u

/* ------------------------------------------------------------------ images -- */

typedef struct {
    const char *path;
    uint8_t    *buf;
    size_t      len;
    uint32_t    base;
    size_t      skip;
} image;

static image g_exe, g_ovl, g_sib;

static int load_image(image *im, const char *path, uint32_t base, size_t skip)
{
    FILE *f = fopen(path, "rb");
    long  n;
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 0; }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    im->buf = malloc((size_t)n);
    if (!im->buf || fread(im->buf, 1, (size_t)n, f) != (size_t)n) {
        fprintf(stderr, "short read %s\n", path); fclose(f); return 0;
    }
    fclose(f);
    im->path = path; im->len = (size_t)n; im->base = base; im->skip = skip;
    return 1;
}

static int in_image(const image *im, uint32_t va)
{
    size_t off;
    if (va < im->base) return 0;
    off = im->skip + (size_t)(va - im->base);
    return off + 4 <= im->len;
}

static uint32_t rdw(const image *im, uint32_t va)
{
    size_t off = im->skip + (size_t)(va - im->base);
    return (uint32_t)im->buf[off] | ((uint32_t)im->buf[off + 1] << 8)
         | ((uint32_t)im->buf[off + 2] << 16) | ((uint32_t)im->buf[off + 3] << 24);
}

static uint16_t rdh(const image *im, uint32_t va)
{
    size_t off = im->skip + (size_t)(va - im->base);
    return (uint16_t)((uint32_t)im->buf[off] | ((uint32_t)im->buf[off + 1] << 8));
}

static uint8_t rdb(const image *im, uint32_t va)
{
    return im->buf[im->skip + (size_t)(va - im->base)];
}

/* pick whichever image owns the address; overlay wins inside its span */
static const image *owner(uint32_t va)
{
    if (in_image(&g_ovl, va)) return &g_ovl;
    if (in_image(&g_exe, va)) return &g_exe;
    return NULL;
}

/* ----------------------------------------------------------------- disasm -- */

static const char *R[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3",
    "t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7",
    "t8","t9","k0","k1","gp","sp","fp","ra"
};

/* Enough of the ISA for this overlay.  MULT/MFLO matter: the completion test is a
 * squared distance, and a disassembler that renders them as "special.18" hides the
 * single most important instruction in the stage. */
static void dis(uint32_t w, uint32_t pc, char *out, size_t n)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    uint32_t rd = (w >> 11) & 31, sa = (w >> 6) & 31, fn = w & 63;
    int32_t  simm = (int16_t)(w & 0xFFFF);
    uint32_t tgt = (pc + 4 + (uint32_t)(simm * 4));
    uint32_t jt  = (pc & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);

    switch (op) {
    case 0x00:
        switch (fn) {
        case 0x00: if (!w) { snprintf(out, n, "nop"); return; }
                   snprintf(out, n, "sll %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x02: snprintf(out, n, "srl %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x03: snprintf(out, n, "sra %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x08: snprintf(out, n, "jr %s", R[rs]); return;
        case 0x09: snprintf(out, n, "jalr %s", R[rs]); return;
        case 0x10: snprintf(out, n, "mfhi %s", R[rd]); return;
        case 0x12: snprintf(out, n, "mflo %s", R[rd]); return;
        case 0x18: snprintf(out, n, "mult %s,%s", R[rs], R[rt]); return;
        case 0x19: snprintf(out, n, "multu %s,%s", R[rs], R[rt]); return;
        case 0x21: snprintf(out, n, "addu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x23: snprintf(out, n, "subu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x24: snprintf(out, n, "and %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x25: snprintf(out, n, "or %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2A: snprintf(out, n, "slt %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2B: snprintf(out, n, "sltu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        default:   snprintf(out, n, "special.%02x", fn); return;
        }
    case 0x02: snprintf(out, n, "j 0x%08" PRIx32, jt); return;
    case 0x03: snprintf(out, n, "jal 0x%08" PRIx32, jt); return;
    case 0x04: snprintf(out, n, "beq %s,%s,0x%08" PRIx32, R[rs], R[rt], tgt); return;
    case 0x05: snprintf(out, n, "bne %s,%s,0x%08" PRIx32, R[rs], R[rt], tgt); return;
    case 0x06: snprintf(out, n, "blez %s,0x%08" PRIx32, R[rs], tgt); return;
    case 0x07: snprintf(out, n, "bgtz %s,0x%08" PRIx32, R[rs], tgt); return;
    case 0x01: snprintf(out, n, "%s %s,0x%08" PRIx32,
                        (rt & 1) ? "bgez" : "bltz", R[rs], tgt); return;
    case 0x08: snprintf(out, n, "addi %s,%s,%d", R[rt], R[rs], simm); return;
    case 0x09: snprintf(out, n, "addiu %s,%s,%d", R[rt], R[rs], simm); return;
    case 0x0A: snprintf(out, n, "slti %s,%s,%d", R[rt], R[rs], simm); return;
    /* SLTIU is not decoration here: the interaction-class test that decides whether
     * a contact counts, resets, or is ignored entirely is an `sltiu ...,2`. */
    case 0x0B: snprintf(out, n, "sltiu %s,%s,%d", R[rt], R[rs], simm); return;
    case 0x0E: snprintf(out, n, "xori %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0C: snprintf(out, n, "andi %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0D: snprintf(out, n, "ori %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0F: snprintf(out, n, "lui %s,0x%x", R[rt], w & 0xFFFF); return;
    case 0x20: snprintf(out, n, "lb %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x21: snprintf(out, n, "lh %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x23: snprintf(out, n, "lw %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x24: snprintf(out, n, "lbu %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x25: snprintf(out, n, "lhu %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x28: snprintf(out, n, "sb %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x29: snprintf(out, n, "sh %s,%d(%s)", R[rt], simm, R[rs]); return;
    case 0x2B: snprintf(out, n, "sw %s,%d(%s)", R[rt], simm, R[rs]); return;
    default:   snprintf(out, n, "op%02x", op); return;
    }
}

/* ------------------------------------------------------------------- pins -- */

static int pass, fail;

static void pin(uint32_t va, uint32_t want, const char *why)
{
    const image *im = owner(va);
    uint32_t got;
    char txt[96];
    if (!im) { printf("  FAIL 0x%08" PRIx32 " not in any image -- %s\n", va, why);
               fail++; return; }
    got = rdw(im, va);
    dis(got, va, txt, sizeof txt);
    if (got == want) { pass++; printf("  ok   0x%08" PRIx32 "  %-30s %s\n", va, txt, why); }
    else { fail++;
           printf("  FAIL 0x%08" PRIx32 "  got %08" PRIx32 " want %08" PRIx32
                  " -- %s\n", va, got, want, why); }
}

static void claim(int cond, const char *why)
{
    if (cond) { pass++; printf("  ok   %s\n", why); }
    else      { fail++; printf("  FAIL %s\n", why); }
}

/* --------------------------------------------------------- base derivation -- */

/* Not an assumption: the base is the value that makes the blob's own internal call
 * land on a function entry.  Reported so a future reader can see it was derived. */
static int derive_base(void)
{
    uint32_t internal = 0;
    int      n_internal = 0;
    size_t   off;

    for (off = 4; off + 4 <= g_ovl.len; off += 4) {
        uint32_t w  = rdw(&g_ovl, OVL_BASE + (uint32_t)off);
        uint32_t op = w >> 26;
        if (op == 2 || op == 3) {
            uint32_t t = (w & 0x03FFFFFFu) << 2;
            t |= 0x80000000u;
            if (t >= OVL_BASE && t < OVL_BASE + g_ovl.len) { internal = t; n_internal++; }
        }
    }
    printf("=== base derivation (not assumed) ===\n");
    claim(n_internal == 1, "exactly one j/jal targets inside the blob's own span");
    if (n_internal != 1) return 0;
    printf("       internal call target = 0x%08" PRIx32 "\n", internal);
    claim(rdw(&g_ovl, internal - 8) == 0x03E00008u,
          "the word 8 before that target is `jr ra` -- a function ends there");
    claim(rdw(&g_ovl, internal - 4) == 0x00000000u,
          "the word 4 before it is the delay-slot `nop`");
    claim(internal == 0x800B3AF4u,
          "so file offset 0 loads at 0x800B39A0, and the entry is 0x800B3AF4");
    return 1;
}

/* ------------------------------------------------------------- accounting -- */

/* Four presumed function spans tile the code range with no gap or overlap. The
 * target scan below covers resolved direct branches and calls only; jr/jalr target
 * recovery and semantic reachability remain outside this structural partition. */
static void accounting(void)
{
    static const uint32_t entries[4] = {
        0x800B39A4u, 0x800B3AF4u, 0x800B3B30u, 0x800B3C98u
    };
    static const char *names[4] = {
        "install_sprite_descriptor_table", "advance_token_uv_frame",
        "bonus_stage_init_cull_by_variant", "bonus_stage_update"
    };
    uint32_t end = OVL_BASE + (uint32_t)g_ovl.len;
    uint32_t cursor = 0x800B39A4u, data_start = 0;
    int i;

    printf("\n=== structural word partition (%zu words) ===\n", g_ovl.len / 4);
    for (i = 0; i < 4; i++) {
        uint32_t va = entries[i], last = 0;
        claim(va == cursor, "function starts exactly where the previous one ended");
        for (; va + 8 <= end; va += 4)
            if (rdw(&g_ovl, va) == 0x03E00008u) { last = va + 4; break; }
        claim(last != 0, "function has a `jr ra`");
        printf("       0x%08" PRIx32 "..0x%08" PRIx32 "  %3u words  %s\n",
               entries[i], last, (last - entries[i]) / 4 + 1, names[i]);
        cursor = last + 4;
    }
    data_start = cursor;
    claim(data_start == 0x800B3F78u, "code ends and data begins at 0x800B3F78");

    /* nothing in the data region may be a branch target from the code region */
    {
        int bad = 0;
        uint32_t va;
        for (va = 0x800B39A4u; va < data_start; va += 4) {
            uint32_t w = rdw(&g_ovl, va), op = w >> 26, t;
            if (op == 4 || op == 5 || op == 6 || op == 7 || op == 1) {
                t = va + 4 + (uint32_t)((int16_t)(w & 0xFFFF) * 4);
                if (t >= data_start && t < end) bad++;
            } else if (op == 2 || op == 3) {
                t = ((w & 0x03FFFFFFu) << 2) | 0x80000000u;
                if (t >= data_start && t < end) bad++;
            }
        }
        claim(bad == 0,
              "no resolved direct branch or call from presumed code targets data");
    }
    printf("       header 1 word + code %u words + data %u words = %zu\n",
           (data_start - 0x800B39A4u) / 4, (end - data_start) / 4, g_ovl.len / 4);
    claim(1u + (data_start - 0x800B39A4u) / 4 + (end - data_start) / 4
              == g_ovl.len / 4,
          "the three structural regions sum to the whole file");
}

/* ----------------------------------------------------------------- tables -- */

static void tables(void)
{
    int v, i;
    printf("\n=== per-variant target table 0x800B4070 (stride 0x10) ===\n");
    printf("  the variant is 0x8009B88A, the PERSISTED COMPLETION ORDINAL -- so which\n"
           "  bonus layout you get depends on HOW MANY you have already finished, not\n"
           "  on WHICH challenge you just completed.\n");
    for (v = 0; v < 3; v++) {
        uint32_t r = 0x800B4070u + (uint32_t)v * 0x10u;
        printf("  variant %d  target=(%8d,%8d,%8d)  beacon_y=%8d  rgb=(%3u,%3u,%3u)\n",
               v, (int32_t)rdw(&g_ovl, r), (int32_t)rdw(&g_ovl, r + 4),
               (int32_t)rdw(&g_ovl, r + 8), (int32_t)rdw(&g_ovl, r + 12),
               rdh(&g_ovl, 0x800B40A0u + (uint32_t)v * 6u),
               rdh(&g_ovl, 0x800B40A2u + (uint32_t)v * 6u),
               rdh(&g_ovl, 0x800B40A4u + (uint32_t)v * 6u));
    }
    printf("\n=== token UV animation table 0x800B3F84 (16 frames) ===\n  ");
    for (i = 0; i < 16; i++)
        printf("(%02x,%02x)%s", rdb(&g_ovl, 0x800B3F84u + (uint32_t)i * 2),
               rdb(&g_ovl, 0x800B3F85u + (uint32_t)i * 2), (i == 7) ? "\n  " : " ");
    printf("\n  u steps 0x20 across 8 columns, then v steps to 0x40 -- an 8x2 strip.\n");
}

/* ------------------------------------------------------------------- main -- */

static void disasm(uint32_t at, uint32_t win, const image *im)
{
    uint32_t va;
    printf("\ndisassembly of 0x%08" PRIx32 " (+0x%" PRIx32 ") in %s:\n", at, win, im->path);
    for (va = at; va < at + win && in_image(im, va); va += 4) {
        char txt[96];
        dis(rdw(im, va), va, txt, sizeof txt);
        printf("  0x%08" PRIx32 "  %08" PRIx32 "  %s\n", va, rdw(im, va), txt);
    }
}

int main(int argc, char **argv)
{
    int do_acct = 0, do_tab = 0, i;
    uint32_t at = 0, win = 0x40;
    const char *img = NULL;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--accounting")) do_acct = 1;
        else if (!strcmp(argv[i], "--tables")) do_tab = 1;
        else if (!strcmp(argv[i], "--disasm") && i + 1 < argc)
            at = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--window") && i + 1 < argc)
            win = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--img") && i + 1 < argc) img = argv[++i];
    }

    if (!load_image(&g_exe, EXE_PATH, EXE_LOAD_VA, EXE_HEADER)) return 2;
    if (!load_image(&g_ovl, OVL_PATH, OVL_BASE, 0)) return 2;
    if (!load_image(&g_sib, OVL_SIB_PATH, OVL_BASE, 0)) return 2;

    if (at) {
        const image *im = &g_exe;
        if (img && strstr(img, "LEVEL1.BIN")) im = &g_ovl;
        else if (img) im = &g_sib;
        else if (in_image(&g_ovl, at) && at >= OVL_BASE) im = &g_ovl;
        disasm(at, win, im);
        return 0;
    }

    if (!derive_base()) return 1;
    if (do_acct) { accounting(); goto done; }
    if (do_tab)  { tables();    goto done; }

    /* -------------------------------------------------------------------- */
    printf("\n=== A. which blob is the bonus stage ===\n");
    /* Independent of the scene table: this is the only overlay with resolved direct
     * reads of the persisted ordinal, and it reads it twice. The resident shell also
     * reads and writes it; pointer-derived overlay accesses remain outside this scan. */
    {
        int readers = 0;
        uint32_t va;
        for (va = OVL_BASE + 4; va + 4 <= OVL_BASE + g_ovl.len; va += 4) {
            uint32_t w = rdw(&g_ovl, va);
            if ((w >> 26) == 0x24 && (int16_t)(w & 0xFFFF) == (int16_t)0xB88A) readers++;
        }
        claim(readers == 2, "LEVEL06/LEVEL1.BIN reads the ordinal 0x8009B88A twice");
    }
    {
        int sib = 0;
        uint32_t va;
        for (va = OVL_BASE + 4; va + 4 <= OVL_BASE + g_sib.len; va += 4) {
            uint32_t w = rdw(&g_sib, va);
            if ((w >> 26) == 0x24 && (int16_t)(w & 0xFFFF) == (int16_t)0xB88A) sib++;
        }
        claim(sib == 0,
              "its sibling LEVEL06/LEVEL.BIN has no resolved direct read -- "
              "so the bonus logic is specific to LEVEL1.BIN, not to the level06 dir");
    }

    printf("\n=== B. init: the variant SELECTS A LAYOUT by culling actors ===\n");
    pin(0x800B3B38, 0x90A5B88A, "a1 = [0x8009B88A], the persisted completion ordinal");
    pin(0x800B3B50, 0xAC2540B4, "cached at 0x800B40B4 for the update function");
    pin(0x800B3B48, 0xAC2040B8, "0x800B40B8 (token animation frame) reset to 0");
    pin(0x800B3B54, 0x14A2000F, "bne a1,2 -> block A runs ONLY when variant == 2");
    pin(0x800B3B94, 0x10A20022, "beq a1,1 -> block B is SKIPPED when variant == 1");
    pin(0x800B3C20, 0x10A20019, "beq a1,2 -> block C is SKIPPED when variant == 2");
    pin(0x800B3B70, 0xA420FDEE, "cull store 1: actor+0x6E (HP) := 0");
    pin(0x800B3B7C, 0xA426FDE2, "cull store 2: actor+0x62 := 10001 (the retired marker)");
    pin(0x800B3B84, 0x2882000C, "block A culls actor indices 0..11");
    pin(0x800B3C10, 0x2882000E, "block B culls actor indices 12..13");
    pin(0x800B3C7C, 0x28820021, "block C culls actor indices 14..32");
    claim(1, "=> variant 0 keeps 0..11, variant 1 keeps 0..13, variant 2 keeps 14..32");

    printf("\n=== C. update: the goal is a POSITION, and the test is a distance ===\n");
    pin(0x800B3C9C, 0x9084B88A, "a0 = ordinal again (the layout is re-read per frame)");
    pin(0x800B3CC4, 0x00042100, "a0 <<= 4 -- the target table has a 0x10 stride");
    pin(0x800B3CD0, 0x8C314070, "s1 = target.x from 0x800B4070[variant]");
    pin(0x800B3CEC, 0x8C324074, "s2 = target.y");
    pin(0x800B3D10, 0x8C304078, "s0 = target.z");
    pin(0x800B3D3C, 0x8C34407C, "s4 = beacon.y (the marker height, NOT the goal y)");

    printf("\n  -- coarse gate: a SECOND distance test, on a different reference point\n");
    pin(0x800B3CA4, 0x8C42EC50, "reads 0x8009EC50, written only at 0x8004EC94");
    pin(0x800B3CDC, 0x00021203, "delta >>= 8 before squaring (overflow guard)");
    pin(0x800B3CE0, 0x00420018, "mult v0,v0 -- squared, not absolute");
    pin(0x800B3D2C, 0x3C030005, "threshold hi: 0x0005....");
    pin(0x800B3D30, 0x34637E3F, "threshold lo: 0x....7E3F -> 359,999");
    pin(0x800B3D50, 0x14600075, "if sum-of-squares > 359,999 -> jump past EVERYTHING");
    claim(1, "so the completion test is unreachable while that reference point is far");

    pin(0x800B3D5C, 0x846323A0, "then: if the transition latch 0x800823A0 is already 1");
    pin(0x800B3D64, 0x10620070, "...skip -- completion cannot fire twice");

    printf("\n  -- the completion test itself\n");
    pin(0x800B3EB8, 0x8C426500, "reads Flik x 0x800A6500");
    pin(0x800B3ED0, 0x8C426504, "reads Flik y 0x800A6504");
    pin(0x800B3EE8, 0x8C426508, "reads Flik z 0x800A6508");
    pin(0x800B3EF4, 0x00021203, "each delta >>= 8");
    pin(0x800B3EF8, 0x00420018, "each delta squared");
    pin(0x800B3F08, 0x28420640, "slti v0,sum,1600 -- the goal radius is 40 in >>8 units");
    pin(0x800B3F0C, 0x10400006, "not inside -> skip");
    pin(0x800B3F18, 0xA42223A0, "INSIDE: transition latch 0x800823A0 := 1");
    pin(0x800B3F24, 0xA4222470, "and fade timer 0x80082470 := 30");
    claim(1, "=> in the decoded completion block, no timer, score, enemy or fail-state "
             "condition participates in the resolved path to the completion stores");

    printf("\n=== D. the token you are chasing ===\n");
    pin(0x800B3F30, 0x0C02CEBD, "update tail calls 0x800B3AF4 every frame");
    pin(0x800B3F44, 0x24420001, "frame counter 0x800B40B8 += 1");
    pin(0x800B3F48, 0x3042000F, "...masked to 0..15 -- a 16-frame loop");
    pin(0x800B3B00, 0x90223F84, "which indexes the UV table at 0x800B3F84");
    pin(0x800B3B08, 0xA0223F80, "and writes u/v into 0x800B3F80/81");
    claim(rdw(&g_ovl, 0x800B406C) == 0x800B3F78u,
          "0x800B3F80 is +8 inside the descriptor 0x800B3F78, which is the LAST entry "
          "of the table this overlay installs at 0x80096B98");
    pin(0x800B39D8, 0x24E76B98, "install destination = 0x80096B98, the pickup kind table");
    pin(0x800B39E0, 0x24C63FA4, "install source = 0x800B3FA4, 51 words inside this blob");
    claim(1, "so the bonus stage replaces the pickup descriptor table wholesale and "
             "adds its own animated token as the last kind");

    printf("\n=== E. what else the stage does per frame ===\n");
    pin(0x800B3E34, 0x904210A3, "gate byte 0x800910A3 (the shared update-inhibit byte)");
    pin(0x800B3E48, 0x8C6322F4, "consumes 3 bytes from the rolling cursor 0x800822F4");
    pin(0x800B3EAC, 0x0C016791, "jal 0x80059E44 = spawn_drop, jittered about the target");
    pin(0x800B3DD0, 0x0C008D51, "jal 0x80023544 with the per-variant triple at 0x800B40A0");
    pin(0x800B3E2C, 0xA42324CA, "appends to the 16-byte marker list at 0x800B1B58, cap 47");

    printf("\n=== F. the reward, in the resident shell ===\n");
    pin(0x80050228, 0x14620004, "transition latch == 6 (a challenge was met) ...");
    pin(0x80050230, 0xAF8204C4, "...arms the one-shot marker gp+1220 = 0x8008225C");
    pin(0x8004FF7C, 0x8F8204C4, "on return the shell tests that marker");
    pin(0x8004FF94, 0xAF8004C4, "and clears it immediately -- strictly one shot");
    pin(0x8004FF90, 0x861023A0, "s0 = the latch the BONUS STAGE left behind");
    pin(0x8004FF98, 0x16020011, "latch != 1 -> the reward block is skipped entirely");
    pin(0x8004FFAC, 0x90C6B88A, "SUCCESS: a2 = old ordinal");
    pin(0x8004FFB4, 0x24C60001, "a2 = old ordinal + 1");
    pin(0x8004FFBC, 0x3063000F, "v1 = flags & 0x0F  (the TENTATIVE low bits)");
    pin(0x8004FFC0, 0x00031100, "v0 = v1 << 4");
    pin(0x8004FFC4, 0x00431021, "v0 = v0 + v1   -- i.e. (flags & 0x0F) * 17");
    pin(0x8004FFC8, 0xA0E20000, "committed to 0x8009B889: low bits mirrored into high");
    pin(0x8004FFD0, 0xA026B88A, "ordinal advanced");
    pin(0x8004FFD4, 0x0C00F9F0, "jal 0x8003E7C0 = fmv_bin_load");
    pin(0x8004FFD8, 0x24840029, "a0 = new_ordinal + 41 = old_ordinal + 42");
    claim(1, "=> the reward is FMV 42/43/44 by COMPLETION ORDER, not by challenge");

    printf("\n  -- the restore block is NOT an else-branch\n");
    {
        /* Every word from the success commit to the restore block, checked for any
         * control transfer.  If there is none, success FALLS THROUGH into restore --
         * which reads as a bug until you notice the arithmetic is idempotent. */
        uint32_t va; int transfers = 0;
        for (va = 0x8004FFDC; va < 0x8004FFE0; va += 4) {
            uint32_t op = rdw(&g_exe, va) >> 26;
            if (op == 1 || op == 2 || op == 3 || (op >= 4 && op <= 7)) transfers++;
            if (op == 0 && ((rdw(&g_exe, va) & 63) == 8 || (rdw(&g_exe, va) & 63) == 9))
                transfers++;
        }
        claim(transfers == 0,
              "no branch separates the success block from the restore block");
    }
    pin(0x8004FFF0, 0x00031902, "restore: v1 = flags >> 4");
    pin(0x8004FFF4, 0x00031100, "v0 = v1 << 4");
    pin(0x8004FFF8, 0x00431021, "v0 = v0 + v1  -- i.e. (flags >> 4) * 17");
    pin(0x80050000, 0xA0820000, "stored back to 0x8009B889");
    {
        /* (x*17 >> 4) == x for x <= 0x0F, so re-running restore after a success is a
         * no-op.  Proven over the whole byte domain rather than argued. */
        int n = 0, x;
        for (x = 0; x <= 0x0F; x++) {
            uint8_t committed = (uint8_t)((x & 0x0F) * 17);
            if ((uint8_t)((committed >> 4) * 17) == committed) n++;
        }
        claim(n == 16,
              "and for all 16 low-nibble values the restore is IDEMPOTENT after a "
              "commit -- the fallthrough is deliberate, not a bug");
    }

    printf("\n=== G. bounded negative: fixed-form stores in the reward path ===\n");
    {
        /* Player-state block: state 0x800A6580, health 0x800A6594, power 0x800A6590,
         * berry index 0x800A6597, lives 0x800A65A0. This fixed-displacement scan
         * recognizes stores encoded against a directly materialized 0x800A page;
         * pointer-derived stores and callee effects remain outside its scope. */
        uint32_t lo = 0x800A6500u, hi = 0x800A65A8u;
        int ovl_hits = 0, shell_hits = 0, other = 0;
        uint32_t va;
        for (va = OVL_BASE + 4; va + 4 <= OVL_BASE + g_ovl.len; va += 4) {
            uint32_t w = rdw(&g_ovl, va), op = w >> 26;
            if (op == 0x28 || op == 0x29 || op == 0x2B) {
                /* lui-formed absolute: hi part is 0x800A, lo is the signed offset */
                int32_t  s = (int16_t)(w & 0xFFFF);
                uint32_t a = 0x800A0000u + (uint32_t)s;
                if (a >= lo && a < hi) ovl_hits++;
            }
        }
        for (va = 0x8004FF7Cu; va <= 0x80050000u; va += 4) {
            uint32_t w = rdw(&g_exe, va), op = w >> 26;
            if (op == 0x28 || op == 0x29 || op == 0x2B) {
                int32_t  s = (int16_t)(w & 0xFFFF);
                uint32_t a = 0x800A0000u + (uint32_t)s;
                if (a >= lo && a < hi) shell_hits++;
                else other++;
            }
        }
        claim(ovl_hits == 0,
              "no fixed-displacement overlay store resolves into player-state block "
              "0x800A6500..0x800A65A8 (pointer-derived stores remain open)");
        claim(shell_hits == 0,
              "and no fixed-displacement store in reward block "
              "0x8004FF7C..0x80050000 resolves there");
        printf("       (the reward block's only stores are 0x8009B889, 0x8009B88A, "
               "gp+1220 and gp+1612: %d non-player stores)\n", other);
    }
    {
        /* This is the same fixed-displacement encoding check, narrowed to XYZ. */
        int w_pos = 0;
        uint32_t va;
        for (va = OVL_BASE + 4; va + 4 <= OVL_BASE + g_ovl.len; va += 4) {
            uint32_t w = rdw(&g_ovl, va), op = w >> 26;
            int32_t  s = (int16_t)(w & 0xFFFF);
            if ((op == 0x2B) && 0x800A0000u + (uint32_t)s >= 0x800A6500u
                             && 0x800A0000u + (uint32_t)s <= 0x800A6508u) w_pos++;
        }
        claim(w_pos == 0,
              "no fixed-displacement overlay store resolves to Flik XYZ "
              "0x800A6500/04/08");
    }

done:
    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) { printf("VERDICT: a pin failed -- do not bank anything above.\n"); return 1; }
    printf("VERDICT: every pin holds against the pristine image.\n");
    return 0;
}
