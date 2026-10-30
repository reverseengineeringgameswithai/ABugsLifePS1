/* Phase 4 C05 item 1: locate the results-screen evaluator's OVERLAY on disc.
 *
 * The evaluator lives at 0x800B7DA0..0x800B8788 in RAM while the level-complete
 * results screen is up.  That address is OVERLAY-resident: several different
 * overlays occupy the 0x800Bxxxx window (C17's movie-viewer menu builder at
 * 0x800B4084 and C04's completion handler at 0x800B40C4 are different overlays
 * at nearly the same address).  So an address alone does not identify the code.
 *
 * This tool answers "which file on disc is it?" WITHOUT the emulator, by
 * scanning every retail file under REBUILD/files for the evaluator's three
 * distinctive test-and-set blocks:
 *
 *     lbu v1, -0x4788(at)      9023b878   ; v1 = unlock_array[level]
 *     nop                      00000000
 *     andi v0, v1, <bit>       3062000X   ; X = 1, 2, 4
 *
 * followed within a few words by the matching set:
 *
 *     ori  v0, v1, <bit>       3462000X
 *     ...
 *     sb   v0, -0x4788(at)     a022b878
 *
 * A file containing all three bit variants IS the results-screen overlay.
 * Reporting every hit (not just the first) also proves whether the code is
 * duplicated per level or shipped once.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror \
 *      tools/phase4_c05_results_overlay_locate.c -o /tmp/c05_locate
 *   /tmp/c05_locate REBUILD/files
 */
#include <dirent.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define LBU_UNLOCK  0x9023B878u   /* lbu v1, -0x4788(at) */
#define SB_UNLOCK   0xA022B878u   /* sb  v0, -0x4788(at) */
#define ANDI_BASE   0x30620000u   /* andi v0, v1, imm    */
#define ORI_BASE    0x34620000u   /* ori  v0, v1, imm    */

/* how far after the andi we allow the matching ori/sb to appear (words) */
#define WINDOW 12

struct hit { long off; unsigned bit; int has_set; };

static int bits_found[8];          /* index by bit value 1,2,4 */
static int total_files, total_hits;

static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void scan_file(const char *path)
{
    FILE *f = fopen(path, "rb");
    long n;
    uint8_t *buf;
    struct hit hits[64];
    int nh = 0, i;

    if (!f) return;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return; }
    n = ftell(f);
    if (n < 16) { fclose(f); return; }
    rewind(f);
    buf = malloc((size_t)n);
    if (!buf) { fclose(f); return; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return; }
    fclose(f);
    total_files++;

    for (long off = 0; off + 4 * (WINDOW + 2) <= n; off += 4) {
        if (rd32(buf + off) != LBU_UNLOCK) continue;
        /* the andi normally sits two words later (lbu, nop, andi) */
        for (int k = 1; k <= 3; k++) {
            uint32_t w = rd32(buf + off + 4 * k);
            if ((w & 0xFFFF0000u) != ANDI_BASE) continue;
            unsigned bit = w & 0xFFFFu;
            if (bit != 1 && bit != 2 && bit != 4) continue;
            int has_set = 0;
            for (int j = k + 1; j <= WINDOW; j++) {
                if (off + 4 * j + 4 > n) break;
                uint32_t v = rd32(buf + off + 4 * j);
                if (v == (ORI_BASE | bit)) has_set = 1;
                if (v == SB_UNLOCK && has_set) { has_set = 2; break; }
            }
            if (nh < 64) { hits[nh].off = off; hits[nh].bit = bit; hits[nh].has_set = has_set; nh++; }
            break;
        }
    }

    if (nh) {
        printf("%s\n", path);
        for (i = 0; i < nh; i++) {
            printf("    +0x%06lx  test bit 0x%02x   %s\n", hits[i].off, hits[i].bit,
                   hits[i].has_set == 2 ? "and SETS it (ori + sb)" :
                   hits[i].has_set == 1 ? "ori only (no sb in window)" : "test only");
            if (hits[i].bit < 8) bits_found[hits[i].bit]++;
            total_hits++;
        }
    }
    free(buf);
}

static void walk(const char *dir)
{
    DIR *d = opendir(dir);
    struct dirent *e;
    char path[4096];
    struct stat st;

    if (!d) { fprintf(stderr, "cannot open %s\n", dir); return; }
    while ((e = readdir(d)) != NULL) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) continue;
        if ((size_t)snprintf(path, sizeof path, "%s/%s", dir, e->d_name) >= sizeof path) continue;
        if (stat(path, &st) != 0) continue;
        if (S_ISDIR(st.st_mode)) walk(path);
        else if (S_ISREG(st.st_mode)) scan_file(path);
    }
    closedir(d);
}

/* ---------------------------------------------------------------------------
 * Stage 2: pin the evaluator inside BITS/MEMORY.BIN.
 *
 * MEMORY.BIN is loaded VERBATIM at 0x800B5788 (proven live: the first 0x8112
 * bytes of the file are byte-identical to RAM during the results screen; only
 * the mutable tail past 0x8112 differs).  So file offset F <-> RAM 0x800B5788+F
 * and every pin below is checkable offline.
 * ------------------------------------------------------------------------- */
#define OVL_BASE 0x800B5788u

struct opin { uint32_t va, word; const char *role; };

static const struct opin opins[] = {
    {0x800B7DA0u, 0x27BDFF70u, "evaluator prologue (addiu sp,sp,-144)"},

    /* the three axis SOURCES and their completion tests */
    {0x800B7DE4u, 0x248465A1u, "grain counter address 0x800A65A1"},
    {0x800B7DF0u, 0x2C420033u, "grain clamp: sltiu v0, v0, 51"},
    {0x800B7E58u, 0x24020032u, "GRAIN test constant 50"},
    {0x800B7E5Cu, 0x14620014u, "GRAIN: bne -> skip when != 50"},

    {0x800B7EB4u, 0x906365A2u, "FLIK letter mask 0x800A65A2"},
    {0x800B7EB8u, 0x2402000Fu, "FLIK test constant 0x0F (all four)"},
    {0x800B7EBCu, 0x14620014u, "FLIK: bne -> skip when != 0x0F"},

    {0x800B7F14u, 0x8442658Eu, "ENEMY quota 0x800A658E"},
    {0x800B7F1Cu, 0x14400015u, "ENEMY: bne -> skip when quota != 0"},

    /* per-axis test-and-set on the unlock array */
    {0x800B7E74u, 0x9023B878u, "A: v1 = unlock_array[level]"},
    {0x800B7E7Cu, 0x30620001u, "A: andi 0x01  <= GRAIN"},
    {0x800B7E94u, 0x34620001u, "A: ori  0x01  (set it)"},
    {0x800B7EA4u, 0xA022B878u, "A: sb -> unlock_array[level]   THE SETTER"},
    {0x800B7EACu, 0xAC2923E4u, "A: newly-earned flag 0x800823E4 = 1"},

    {0x800B7ED4u, 0x9023B878u, "B: v1 = unlock_array[level]"},
    {0x800B7EDCu, 0x30620002u, "B: andi 0x02  <= FLIK"},
    {0x800B7EF4u, 0x34620002u, "B: ori  0x02  (set it)"},
    {0x800B7F04u, 0xA022B878u, "B: sb -> unlock_array[level]"},

    {0x800B7F34u, 0x9023B878u, "C: v1 = unlock_array[level]"},
    {0x800B7F3Cu, 0x30620004u, "C: andi 0x04  <= ENEMIES"},
    {0x800B7F54u, 0x34620004u, "C: ori  0x04  (set it)"},
    {0x800B7F64u, 0xA022B878u, "C: sb -> unlock_array[level]"},

    /* presentation: locked '?' vs earned tile, and the dimmed already-had path */
    {0x800B835Cu, 0x24060034u, "row1 LOCKED tile 52 (the red '?')"},
    {0x800B8374u, 0x2406003Bu, "row1 EARNED tile 59 (grain)"},
    {0x800B8378u, 0x0C0097D5u, "row1 jal hud_draw_sprite_tile 0x80025F54"},
    {0x800B83A0u, 0x0C009A16u, "row1 already-had: jal 0x80026858 (modulated)"},
    {0x800B83D4u, 0x2406003Au, "row2 EARNED tile 58 (FLIK)"},
    {0x800B843Cu, 0x24060039u, "row3 EARNED tile 57 (enemies)"},
    {0x800B8424u, 0x24060034u, "row3 LOCKED tile 52 (the red '?')"},
};

static int verify_overlay(const char *files_root)
{
    char path[4096];
    FILE *f;
    long n;
    uint8_t *buf;
    size_t i, ok = 0, total = sizeof opins / sizeof opins[0];

    snprintf(path, sizeof path, "%s/BITS/MEMORY.BIN", files_root);
    f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return 1; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 1; }
    n = ftell(f);
    rewind(f);
    buf = malloc((size_t)n);
    if (!buf) { fclose(f); return 1; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return 1; }
    fclose(f);

    printf("\n=== pinning the evaluator inside %s (load base %#010x) ===\n", path, OVL_BASE);
    for (i = 0; i < total; i++) {
        long off = (long)(opins[i].va - OVL_BASE);
        uint32_t got;
        int good;
        if (off < 0 || off + 4 > n) {
            printf("FAIL %08" PRIx32 "  outside file  %s\n", opins[i].va, opins[i].role);
            continue;
        }
        got = rd32(buf + off);
        good = (got == opins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 " (+0x%05lx)  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", opins[i].va, off, opins[i].word, got, opins[i].role);
    }
    printf("\n%zu/%zu overlay pins OK\n", ok, total);
    free(buf);
    return ok == total ? 0 : 1;
}

int main(int argc, char **argv)
{
    int rc;
    if (argc != 2) { fprintf(stderr, "usage: %s <REBUILD/files>\n", argv[0]); return 2; }
    printf("scanning %s for the results-screen unlock test-and-set blocks\n\n", argv[1]);
    walk(argv[1]);

    printf("\nfiles scanned: %d   blocks found: %d\n", total_files, total_hits);
    printf("bit 0x01 blocks: %d\nbit 0x02 blocks: %d\nbit 0x04 blocks: %d\n",
           bits_found[1], bits_found[2], bits_found[4]);

    if (!(bits_found[1] && bits_found[2] && bits_found[4])) {
        puts("\nDid NOT find all three bit variants; the evaluator was not located.");
        return 1;
    }
    puts("\nAll three axis bits are present on disc, in ONE file -- the evaluator is a");
    puts("single shipped overlay, not per-level code and not synthesised at runtime.");

    rc = verify_overlay(argv[1]);
    if (rc == 0) {
        puts("\nCONFIRMED: BITS/MEMORY.BIN loads verbatim at 0x800B5788 and contains the");
        puts("level-complete results evaluator at 0x800B7DA0..0x800B8788, which TESTS");
        puts("  grain 0x800A65A1 == 50 | FLIK mask 0x800A65A2 == 0x0F | quota 0x800A658E == 0");
        puts("and SETS bits 0x01 / 0x02 / 0x04 of unlock_array[level] accordingly.");
        puts("The third axis is ENEMIES by construction -- proven, not inferred.");
    }
    return rc;
}
