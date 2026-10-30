/*
 * preview_arm.c -- dry-run preview: what would this breakpoint/watch/signature
 *                  actually match, before you spend a replay finding out?
 *
 * WHY THIS EXISTS. Two runtime failures in one session, both silent, both detectable
 * statically before arming anything:
 *
 *   1. An execute breakpoint on 0x800B4244 -- a stage overlay's mask store. Region A
 *      (0x800B39A0..0x800B5788) is a SHARED swap buffer, so the same address holds
 *      unrelated code in every other overlay. The breakpoint fired in a different
 *      level's code, the capture looked plausible (mask 0, records all zero), and it
 *      "refuted" a claim that was correct. Cost: a full replay plus a wrong belief.
 *
 *   2. A residency signature taken from a function prologue, used to locate an
 *      overlay in RAM. It matched 0x38 off, because the SIBLING overlay in the same
 *      disc directory opens with a byte-identical prologue. Cost: another replay.
 *
 * Neither needed the emulator to catch. Both are questions about the disc images,
 * answerable in milliseconds. This tool answers them and returns a VERDICT, so an
 * ambiguous arm is a hard error at setup time rather than a confusing capture later.
 *
 * It deliberately reports what it CANNOT see, because a preview that quietly ignores
 * an addressing form would be exactly the false-confidence problem it exists to
 * prevent.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/preview_arm.c -o /tmp/preview
 *
 * Use:
 *   preview --breakpoint 0x800B4244
 *   preview --watch 0x800B5774 [--len 4]
 *   preview --signature REBUILD/files/LEVEL06/LEVEL1.BIN:4:32
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH    "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER  0x800u
#define OVL_BASE    0x800B39A0u          /* region A: the shared overlay window */
#define MEMBIN_BASE 0x800B5788u
#define GP          0x80081D98u

typedef struct { char path[64]; uint8_t *buf; size_t len; uint32_t base, skip; } image;

static image g_exe;
static image g_img[64];
static int   n_img;

static int load(image *im, const char *p, uint32_t base, uint32_t skip)
{
    FILE *f = fopen(p, "rb");
    long  n;
    if (!f) return 0;
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    im->buf = malloc((size_t)n);
    if (!im->buf || fread(im->buf, 1, (size_t)n, f) != (size_t)n) { fclose(f); return 0; }
    fclose(f);
    snprintf(im->path, sizeof im->path, "%s", p);
    im->len = (size_t)n; im->base = base; im->skip = skip;
    return 1;
}

static int has(const image *im, uint32_t va)
{
    size_t o;
    if (va < im->base) return 0;
    o = im->skip + (size_t)(va - im->base);
    return o + 4 <= im->len;
}

static uint32_t rd(const image *im, uint32_t va)
{
    size_t o = im->skip + (size_t)(va - im->base);
    return (uint32_t)im->buf[o] | ((uint32_t)im->buf[o+1] << 8)
         | ((uint32_t)im->buf[o+2] << 16) | ((uint32_t)im->buf[o+3] << 24);
}

static const char *R[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"
};

static void dis(uint32_t w, char *out, size_t n)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31, fn = w & 63;
    int32_t  s  = (int16_t)(w & 0xFFFF);
    switch (op) {
    case 0x00: if (!w) { snprintf(out, n, "nop"); return; }
               snprintf(out, n, "special.%02x", fn); return;
    case 0x02: snprintf(out, n, "j 0x%08" PRIx32, ((w & 0x03FFFFFFu) << 2) | 0x80000000u); return;
    case 0x03: snprintf(out, n, "jal 0x%08" PRIx32, ((w & 0x03FFFFFFu) << 2) | 0x80000000u); return;
    case 0x09: snprintf(out, n, "addiu %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0C: snprintf(out, n, "andi %s,%s,0x%x", R[rt], R[rs], w & 0xFFFF); return;
    case 0x0F: snprintf(out, n, "lui %s,0x%x", R[rt], w & 0xFFFF); return;
    case 0x23: snprintf(out, n, "lw %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x24: snprintf(out, n, "lbu %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x25: snprintf(out, n, "lhu %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x28: snprintf(out, n, "sb %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x29: snprintf(out, n, "sh %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x2B: snprintf(out, n, "sw %s,%d(%s)", R[rt], s, R[rs]); return;
    default:   snprintf(out, n, "op%02x", op); return;
    }
}

static const char *region_of(uint32_t va, int *shared)
{
    *shared = 0;
    if (va >= EXE_LOAD_VA && va < 0x80090000u) return "resident EXE";
    if (va >= OVL_BASE && va < MEMBIN_BASE) { *shared = 1; return "region A -- SHARED overlay swap buffer"; }
    if (va >= MEMBIN_BASE && va < 0x800BE600u) return "BITS/MEMORY.BIN window";
    if (va >= 0x80090000u && va < OVL_BASE) return "resident data / pools";
    if (va >= 0x1F800000u && va < 0x1F800400u) return "scratchpad";
    return "unclassified";
}

/* ------------------------------------------------------------- breakpoint -- */

static int preview_breakpoint(uint32_t va)
{
    int shared, i, holders = 0, verdict_ok = 1;
    char txt[80];
    const char *reg = region_of(va, &shared);

    printf("BREAKPOINT preview: 0x%08" PRIx32 "\n", va);
    printf("  physical form       : 0x%08" PRIx32 "   (breakpoints need this)\n",
           va & 0x1FFFFFFFu);
    printf("  region              : %s\n", reg);

    if (!shared) {
        if (has(&g_exe, va)) {
            dis(rd(&g_exe, va), txt, sizeof txt);
            printf("  resident instruction: %s\n", txt);
            printf("\n  VERDICT: SAFE -- one resident image owns this address.\n");
        } else {
            printf("\n  VERDICT: UNKNOWN -- not inside the resident EXE image; this "
                   "tool cannot say what occupies it.\n");
            verdict_ok = 0;
        }
        return verdict_ok;
    }

    printf("\n  ⚠ This address is in the SHARED overlay window. An execute breakpoint\n"
           "    here fires for WHICHEVER overlay is resident. Images containing code\n"
           "    at this VA:\n\n");
    for (i = 0; i < n_img; i++) {
        if (!has(&g_img[i], va)) continue;
        holders++;
        dis(rd(&g_img[i], va), txt, sizeof txt);
        printf("      %-34s %08" PRIx32 "  %s\n", g_img[i].path, rd(&g_img[i], va), txt);
    }
    printf("\n  %d image(s) contain code at 0x%08" PRIx32 ".\n", holders, va);
    if (holders > 1) {
        printf("\n  VERDICT: AMBIGUOUS -- DO NOT ARM WITHOUT A SCENE GATE.\n"
               "    Every hit must be checked against the scene id (0x80082504) or a\n"
               "    residency probe, or you will capture another level's execution.\n");
        verdict_ok = 0;
    } else if (holders == 1) {
        printf("\n  VERDICT: SAFE -- only one overlay image covers this VA.\n");
    } else {
        printf("\n  VERDICT: NO IMAGE covers this VA -- the address is probably wrong.\n");
        verdict_ok = 0;
    }
    return verdict_ok;
}

/* ------------------------------------------------------------------ watch -- */

static int accesses(const image *im, uint32_t lo, uint32_t hi, int *stores)
{
    uint32_t val[32];
    int      valid[32];
    uint32_t va;
    int      n = 0;
    memset(val, 0, sizeof val); memset(valid, 0, sizeof valid);
    val[28] = GP; valid[28] = 1;
    *stores = 0;
    for (va = im->base; has(im, va); va += 4) {
        uint32_t w = rd(im, va), op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int32_t  s = (int16_t)(w & 0xFFFF);
        if (op == 0x0F) { val[rt] = (uint32_t)(w & 0xFFFF) << 16; valid[rt] = 1; }
        else if (op == 0x08 || op == 0x09) {
            if (valid[rs]) { val[rt] = val[rs] + (uint32_t)s; valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x0D) {
            if (valid[rs]) { val[rt] = val[rs] | (uint32_t)(w & 0xFFFF); valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x28 || op == 0x29 || op == 0x2B
                   || (op >= 0x20 && op <= 0x25)) {
            int ok = valid[rs] || rs == 28;
            uint32_t b = (rs == 28) ? GP : val[rs];
            if (ok && b + (uint32_t)s >= lo && b + (uint32_t)s <= hi) {
                n++;
                if (op == 0x28 || op == 0x29 || op == 0x2B) (*stores)++;
            }
            if (op >= 0x20 && op <= 0x25) valid[rt] = 0;
        }
        valid[0] = 1; val[0] = 0;
    }
    return n;
}

static int preview_watch(uint32_t va, uint32_t len)
{
    int shared, i, st, tot, ok = 1, holders = 0;
    const char *reg = region_of(va, &shared);
    uint32_t hi = va + (len ? len - 1 : 0);

    printf("WATCH preview: 0x%08" PRIx32 "..0x%08" PRIx32 "\n", va, hi);
    printf("  region              : %s\n", reg);

    tot = accesses(&g_exe, va, hi, &st);
    printf("  resident EXE        : %d access(es), %d store(s)\n", tot, st);

    for (i = 0; i < n_img; i++) {
        int s2, t2 = accesses(&g_img[i], va, hi, &s2);
        if (t2) { holders++; printf("  %-20s: %d access(es), %d store(s)\n",
                                    g_img[i].path + 14, t2, s2); }
    }

    if (shared) {
        printf("\n  ⚠ OVERLAY-LOCAL address. Its meaning depends on which overlay is\n"
               "    resident: %d overlay image(s) reference this range at all.\n", holders);
        printf("    A closure claim over this address CANNOT be phrased \"across all\n"
               "    images\" -- only per-scope. A live watch must be scene-gated.\n");
        printf("\n  VERDICT: %s\n", holders > 1
               ? "AMBIGUOUS -- more than one overlay references it."
               : "SAFE PER-SCOPE -- one overlay owns it, but still gate the run.");
        if (holders > 1) ok = 0;
    } else {
        printf("\n  VERDICT: SAFE -- resident address, stable across overlays.\n");
    }
    printf("\n  NOT VISIBLE TO THIS PREVIEW: stores through a runtime-computed base\n"
           "  (variable index, pointer chase) and effects inside callees. A zero here\n"
           "  is 'none of the forms I can resolve', not 'none'.\n");
    return ok;
}

/* -------------------------------------------------------------- signature -- */

static int preview_signature(const char *spec)
{
    char path[64];
    unsigned off = 0, len = 0;
    const uint8_t *pat;
    image src;
    int i, total = 0;

    if (sscanf(spec, "%63[^:]:%u:%u", path, &off, &len) != 3) {
        printf("  usage: --signature FILE:OFFSET:LENGTH\n");
        return 0;
    }
    if (!load(&src, path, 0, 0)) { printf("  cannot open %s\n", path); return 0; }
    if (off + len > src.len) { printf("  window past end of file\n"); return 0; }
    pat = src.buf + off;

    printf("SIGNATURE preview: %s bytes %u..%u (%u bytes)\n", path, off, off + len, len);
    printf("  first bytes: ");
    for (i = 0; i < (int)(len < 12 ? len : 12); i++) printf("%02x ", pat[i]);
    printf("\n\n  occurrences across every candidate image:\n");
    for (i = 0; i < n_img; i++) {
        size_t j; int c = 0;
        if (g_img[i].len < len) continue;
        for (j = 0; j + len <= g_img[i].len; j++)
            if (!memcmp(g_img[i].buf + j, pat, len)) c++;
        if (c) { total += c; printf("      %-34s %d\n", g_img[i].path, c); }
    }
    printf("\n  total matches: %d\n", total);
    if (total == 1)
        printf("\n  VERDICT: UNIQUE -- safe to use as a residency signature.\n");
    else
        printf("\n  VERDICT: NOT UNIQUE (%d matches) -- DO NOT USE.\n"
               "    A residency probe built on this will lock onto the wrong image or\n"
               "    the wrong offset. Sign on data, not on a function prologue:\n"
               "    sibling overlays are built from the same source and open alike.\n",
               total);
    return total == 1;
}

/* ------------------------------------------------------------------- main -- */

int main(int argc, char **argv)
{
    int lvl, i, rc = 0;
    uint32_t va = 0, len = 4;
    const char *mode = NULL, *sig = NULL;

    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--breakpoint") && i + 1 < argc)
            { mode = "bp"; va = (uint32_t)strtoul(argv[++i], NULL, 0); }
        else if (!strcmp(argv[i], "--watch") && i + 1 < argc)
            { mode = "watch"; va = (uint32_t)strtoul(argv[++i], NULL, 0); }
        else if (!strcmp(argv[i], "--len") && i + 1 < argc)
            len = (uint32_t)strtoul(argv[++i], NULL, 0);
        else if (!strcmp(argv[i], "--signature") && i + 1 < argc)
            { mode = "sig"; sig = argv[++i]; }
    }
    if (!mode) {
        printf("usage: preview --breakpoint VA | --watch VA [--len N] | "
               "--signature FILE:OFF:LEN\n");
        return 2;
    }

    if (!load(&g_exe, EXE_PATH, EXE_LOAD_VA, EXE_HEADER)) {
        fprintf(stderr, "cannot open %s\n", EXE_PATH); return 2;
    }
    for (lvl = 0; lvl <= 20 && n_img < 60; lvl++) {
        char p[64];
        snprintf(p, sizeof p, "REBUILD/files/LEVEL%02d/LEVEL.BIN", lvl);
        if (load(&g_img[n_img], p, OVL_BASE, 0)) n_img++;
        snprintf(p, sizeof p, "REBUILD/files/LEVEL%02d/LEVEL1.BIN", lvl);
        if (load(&g_img[n_img], p, OVL_BASE, 0)) n_img++;
    }
    printf("(%d overlay images loaded)\n\n", n_img);

    if (!strcmp(mode, "bp"))    rc = preview_breakpoint(va);
    else if (!strcmp(mode, "watch")) rc = preview_watch(va, len);
    else                        rc = preview_signature(sig);

    return rc ? 0 : 1;      /* nonzero exit == do not arm as specified */
}
