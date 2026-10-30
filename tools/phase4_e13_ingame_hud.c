/* Phase 4 E13 step 1: identify the IN-GAME HUD render stage.
 *
 * The function census names 0x800526FC "results_screen_render".  That name is
 * WRONG on two counts, and this tool pins the evidence for both:
 *
 *  1. 0x800526FC is not a function ENTRY.  The real entry is 0x800526F4, an
 *     8-byte head that reads the transition timer 0x80082470 and falls through.
 *     (Same shape as the C05 marker stage's 0x80051938 -> 0x80051940.)
 *  2. It is not the results screen.  The level-complete results screen is
 *     FUNC_800B7DA0 in the BITS/MEMORY.BIN overlay (C05, 2026-08-04), which reads
 *     the unlock array 0x8009B878 -- an address this function never touches.
 *
 * What it actually is: the per-frame IN-GAME HUD stage.
 *   - called from the gameplay state machine 0x8004ECD4 (jal at 0x8004F3E4),
 *     the same driver that calls the C05 reward-token marker stage;
 *   - reads exactly the on-screen counter set: grain 0x800A65A1, FLIK letter mask
 *     0x800A65A2, enemy quota 0x800A658E, enemy total 0x80082258, lives
 *     0x800A65A0, goal latch 0x800823A0;
 *   - draws through hud_draw_sprite_tile 0x80025F54.
 *
 * The FLIK letters are four near-identical blocks, one per mask bit, drawn at
 * evenly spaced x with consecutive tile ids -- matching the already-committed
 * "FLIK letters are glyphs, sprite tiles 0x10-0x13" finding:
 *
 *     bit 0x01 -> x=0x70   bit 0x02 -> x=0x88 tile 0x11
 *     bit 0x04 -> x=0xA0 tile 0x12   bit 0x08 -> x=0xB8 tile 0x13
 *
 * MODE SELECTION (E13 step 3): the head gates on the transition timer, and when a
 * transition is running with the goal latch 0x800823A0 still CLEAR -- i.e. a
 * non-completion transition -- it writes 0x400 into 0x800B0188/18C/190.  The same
 * goal latch is what the results screen uses to pick its header tile (54 when set,
 * 55 otherwise).  So one flag, 0x800823A0, selects completion-vs-not in BOTH
 * renderers.  What the tile-55 variant looks like on screen is NOT established here.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_e13_ingame_hud.c \
 *      -o /tmp/e13_hud
 *   /tmp/e13_hud REBUILD/files/SCUS_942.88
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

enum { EXE_HEADER_SIZE = 0x800, EXE_LOAD_VA = 0x80010000u };

static uint8_t *exe;
static size_t exe_size;

static uint32_t exe_u32(uint32_t va)
{
    size_t off;
    if (va < EXE_LOAD_VA) { fprintf(stderr, "va below base\n"); exit(2); }
    off = EXE_HEADER_SIZE + (size_t)(va - EXE_LOAD_VA);
    if (off + 4 > exe_size) { fprintf(stderr, "va outside image\n"); exit(2); }
    return (uint32_t)exe[off] | ((uint32_t)exe[off+1] << 8) |
           ((uint32_t)exe[off+2] << 16) | ((uint32_t)exe[off+3] << 24);
}

struct pin { uint32_t va, word; const char *role; };

static const struct pin pins[] = {
    /* the REAL entry, and its caller */
    {0x800526F4u, 0x3C028008u, "entry 0x800526F4: lui v0, 0x8008"},
    {0x800526F8u, 0x84422470u, "entry: v0 = [0x80082470] (transition timer), then falls through"},
    {0x8004F3E4u, 0x0C0149BDu, "gameplay_state_machine 0x8004ECD4 calls it: jal 0x800526F4"},

    /* the completion-vs-not gate -- same latch the results screen uses */
    {0x80052728u, 0x1040000Cu, "if transition timer == 0 -> skip the transition block"},
    {0x80052734u, 0x844223A0u, "v0 = [0x800823A0] (goal latch)"},
    {0x8005273Cu, 0x14400007u, "if latch != 0 -> skip (so this block is the NON-completion case)"},
    {0x80052748u, 0xA4220188u, "non-completion: [0x800B0188] = 0x400"},

    /* the four FLIK letter blocks: one mask bit each, evenly spaced, tiles 0x11-0x13 */
    {0x80052D9Cu, 0x906365A2u, "letter 1: lbu [0x800A65A2]"},
    {0x80052DA8u, 0x30630001u, "letter 1: andi 0x01"},
    {0x80052DB4u, 0x24040070u, "letter 1: x = 0x70"},

    {0x80052DFCu, 0x904265A2u, "letter 2: lbu [0x800A65A2]"},
    {0x80052E04u, 0x30420002u, "letter 2: andi 0x02"},
    {0x80052E0Cu, 0x24040088u, "letter 2: x = 0x88"},
    {0x80052E14u, 0x24060011u, "letter 2: tile 0x11"},

    {0x80052E50u, 0x904265A2u, "letter 3: lbu [0x800A65A2]"},
    {0x80052E58u, 0x30420004u, "letter 3: andi 0x04"},
    {0x80052E60u, 0x240400A0u, "letter 3: x = 0xA0"},
    {0x80052E68u, 0x24060012u, "letter 3: tile 0x12"},

    {0x80052EA4u, 0x904265A2u, "letter 4: lbu [0x800A65A2]"},
    {0x80052EACu, 0x30420008u, "letter 4: andi 0x08"},
    {0x80052EB4u, 0x240400B8u, "letter 4: x = 0xB8"},
    {0x80052EBCu, 0x24060013u, "letter 4: tile 0x13"},
};

int main(int argc, char **argv)
{
    FILE *f;
    long n;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];

    if (argc != 2) { fprintf(stderr, "usage: %s <SCUS_942.88>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 2; }
    n = ftell(f);
    if (n <= 0) { fclose(f); return 2; }
    rewind(f);
    exe_size = (size_t)n;
    exe = malloc(exe_size);
    if (!exe) { fclose(f); return 2; }
    if (fread(exe, 1, exe_size, f) != exe_size) { free(exe); fclose(f); return 2; }
    fclose(f);

    for (i = 0; i < total; i++) {
        uint32_t got = exe_u32(pins[i].va);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 "  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, pins[i].word, got, pins[i].role);
    }

    printf("\n%zu/%zu pins OK\n", ok, total);
    if (ok != total) { free(exe); return 1; }

    puts("\nE13 STEP 1: 0x800526F4 is the IN-GAME HUD render stage.");
    puts("  The census name 'results_screen_render' at 0x800526FC is wrong twice:");
    puts("  0x800526FC is a fall-through body, not an entry; and the results screen");
    puts("  is FUNC_800B7DA0 in BITS/MEMORY.BIN, which reads the unlock array that");
    puts("  this function never touches.");
    puts("E13 STEP 3: the goal latch 0x800823A0 selects completion-vs-not in BOTH");
    puts("  renderers -- here it gates the transition block, and in the results");
    puts("  screen it picks header tile 54 vs 55.");
    free(exe);
    return 0;
}
