/* Phase 4 C05 item 1 (follow-up): the results-screen COUNTER ANIMATION.
 *
 * Closes the last undecoded piece of the level-complete screen.  Everything is
 * pinned OFFLINE against the pristine BITS/MEMORY.BIN -- no emulator -- using the
 * load base 0x800B5788 established by tools/phase4_c05_results_overlay_locate.c.
 *
 * THE MODEL
 * ---------
 * The screen is one per-frame loop: 0x800B7F98 (jal wait_for_frame_sync_flag)
 * ... 0x800B8740 (bne s3, zero -> 0x800B7F98).  s3 is the screen countdown,
 * seeded to 800 and decremented once per frame while > 0.
 *
 * Three numerators animate upward, one per axis:
 *   s4 = grain,   target [0x800A65A1]
 *   s6 = FLIK,    target popcount_table[0x800BE444 + mask(0x800A65A2)]
 *   s5 = enemies, target [sp+0x50] = [0x80082258] - quota(0x800A658E)
 *                                    i.e. TOTAL - REMAINING = DEFEATED
 *
 * Each has the identical increment law:
 *      if (numerator < target && fp == 0) { numerator++; sfx(14, ...); }
 * fp toggles every frame (fp = (fp+1) & 1), so the counters advance ONE unit
 * every OTHER frame -- 30 Hz, not 60.  s1 = (s1+1) & 0xF on the fp==0 frames is
 * the spinning-icon animation phase.
 *
 * Digits are drawn with hud_draw_sprite_tile(x, y, tile, DIGIT): tile 56 is the
 * digit font and the 4th argument is the glyph index, with 10 = the '/' glyph.
 * Row 1 emits [tens][units] '/' '5' '0' -- the grain denominator is TWO LITERAL
 * DIGITS, which is why the requirement is 50 on every level.  The tens digit is
 * numerator/10 via the classic 0x66666667 magic-multiply reciprocal.
 *
 * SKIP: a fresh press on the face-button mask 0xF000 -- [0x80082412] & 0xF000
 * nonzero AND [0x800822E4] & 0xF000 zero (both are zeroed at screen entry) --
 * enters the finish block, but only inside the window 25 <= s3 < 740.
 *   - all three numerators already at target, and the one-shot flag [sp+0x58]
 *     clear  ->  s3 = 24 (let the screen end shortly)
 *   - otherwise  ->  s3 = 54 AND the numerators are SNAPPED to their targets,
 *     i.e. the press fast-forwards the count-up rather than skipping the screen.
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_c05_counter_animation.c \
 *      -o /tmp/c05_counter
 *   /tmp/c05_counter REBUILD/files/BITS/MEMORY.BIN
 */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define OVL_BASE   0x800B5788u
#define POPCNT_TBL 0x800BE444u   /* lui at,0x800c ; lbu ...,-0x1bbc(at) */

static uint8_t *img;
static long img_size;

static uint32_t va32(uint32_t va)
{
    long off = (long)(va - OVL_BASE);
    if (off < 0 || off + 4 > img_size) { fprintf(stderr, "va %08" PRIx32 " outside\n", va); exit(2); }
    return (uint32_t)img[off] | ((uint32_t)img[off+1] << 8) |
           ((uint32_t)img[off+2] << 16) | ((uint32_t)img[off+3] << 24);
}

struct pin { uint32_t va, word; const char *role; };

static const struct pin pins[] = {
    /* the per-frame loop */
    {0x800B7F20u, 0x24130320u, "s3 (screen countdown) seeded to 800"},
    {0x800B7F98u, 0x0C00FCBCu, "loop head: jal wait_for_frame_sync_flag 0x8003F2F0"},
    {0x800B8638u, 0x1A600002u, "blez s3 -> skip the decrement"},
    {0x800B8640u, 0x2673FFFFu, "s3--"},
    {0x800B8740u, 0x1660FE15u, "loop tail: bne s3, zero -> 0x800B7F98"},

    /* the every-other-frame gate and the icon spin phase */
    {0x800B8614u, 0x27DE0001u, "fp++"},
    {0x800B861Cu, 0x33DE0001u, "fp &= 1   (so counters tick at 30 Hz)"},
    {0x800B8630u, 0x26310001u, "s1++ (icon spin phase, on fp==0 frames)"},
    {0x800B8634u, 0x3231000Fu, "s1 &= 0x0F"},

    /* enemies numerator target = total - remaining, computed once up front */
    {0x800B7E2Cu, 0x8463658Eu, "lh v1, [0x800A658E] (enemy quota remaining)"},
    {0x800B7E34u, 0x8C422258u, "lw v0, [0x80082258] (enemy TOTAL)"},
    {0x800B7E4Cu, 0x00431023u, "subu v0, v0, v1 -> DEFEATED"},
    {0x800B7E50u, 0xAFA20050u, "sw v0, 0x50(sp)  = the enemies target"},

    /* grain numerator s4 */
    {0x800B84BCu, 0x904265A1u, "grain target = [0x800A65A1]"},
    {0x800B84C4u, 0x0282102Au, "slt v0, s4, target"},
    {0x800B84D0u, 0x17C0000Cu, "bne fp, zero -> skip (every other frame)"},
    {0x800B84D8u, 0x26940001u, "s4++"},
    {0x800B84E4u, 0x0C010D7Eu, "jal 0x800435F8 (per-tick SFX)"},
    {0x800B84D4u, 0x2404000Eu, "SFX id 14"},
    {0x800B84ECu, 0x24020032u, "s4 == 50 milestone test"},

    /* FLIK numerator s6, target from the popcount table */
    {0x800B8574u, 0x26D60001u, "s6++"},
    {0x800B86B4u, 0x904265A2u, "FLIK mask [0x800A65A2] indexes the table"},
    {0x800B86C0u, 0x9022E444u, "lbu v0, -0x1bbc(at)  -> popcount_table[mask]"},
    {0x800B8734u, 0x9036E444u, "snap path: s6 = popcount_table[mask]"},

    /* enemies numerator s5 */
    {0x800B85D0u, 0x02A9102Au, "slt v0, s5, target"},
    {0x800B85FCu, 0x26B50001u, "s5++"},

    /* digit rendering: tile 56, 4th arg = glyph, 10 = '/', then literal 5 and 0 */
    {0x800B7F8Cu, 0x35296667u, "0x66666667 divide-by-10 reciprocal"},
    {0x800B8024u, 0x02890018u, "mult s4, reciprocal"},
    {0x800B803Cu, 0x00098083u, "sra -> tens digit"},
    {0x800B8030u, 0x24060038u, "digit font tile 56"},
    {0x800B8078u, 0x0C0097D5u, "jal hud_draw_sprite_tile"},
    {0x800B807Cu, 0x2407000Au, "glyph 10 = '/'"},
    {0x800B8090u, 0x24070005u, "literal denominator digit 5"},
    {0x800B80A4u, 0x00003821u, "literal denominator digit 0  -> '50' on EVERY level"},

    /* header tile depends on the goal latch */
    {0x800B7FC0u, 0x846323A0u, "lh v1, [0x800823A0] (goal latch)"},
    {0x800B7FDCu, 0x24060036u, "latch==1 -> header tile 54"},
    {0x800B7FE8u, 0x24060037u, "else      -> header tile 55"},

    /* skip: fresh press on the face-button mask, inside a window */
    {0x800B8660u, 0x84422412u, "lh v0, [0x80082412] (pad now)"},
    {0x800B8668u, 0x3042F000u, "andi 0xF000 (face buttons) -- must be NONZERO"},
    {0x800B8678u, 0x844222E4u, "lh v0, [0x800822E4] (pad previous)"},
    {0x800B8680u, 0x3042F000u, "andi 0xF000 -- must be ZERO  => fresh press"},
    {0x800B8688u, 0x2A6202E4u, "window: s3 < 740"},
    {0x800B8690u, 0x2A620019u, "window: s3 < 25 rejects"},
    {0x800B86ECu, 0x24130018u, "all counters done -> s3 = 24"},
    {0x800B8700u, 0x24130036u, "not done -> s3 = 54 and SNAP the counters"},
    {0x800B8720u, 0x929465A1u, "snap path: s4 = [0x800A65A1]"},
};

int main(int argc, char **argv)
{
    FILE *f;
    size_t i, ok = 0, total = sizeof pins / sizeof pins[0];
    long tbl_off;
    int tbl_ok = 1;

    if (argc != 2) { fprintf(stderr, "usage: %s <BITS/MEMORY.BIN>\n", argv[0]); return 2; }
    f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return 2; }
    img_size = ftell(f);
    rewind(f);
    img = malloc((size_t)img_size);
    if (!img) { fclose(f); return 2; }
    if (fread(img, 1, (size_t)img_size, f) != (size_t)img_size) { free(img); fclose(f); return 2; }
    fclose(f);

    for (i = 0; i < total; i++) {
        uint32_t got = va32(pins[i].va);
        int good = (got == pins[i].word);
        ok += (size_t)good;
        printf("%s %08" PRIx32 " (+0x%05lx)  want %08" PRIx32 "  got %08" PRIx32 "  %s\n",
               good ? "ok  " : "FAIL", pins[i].va, (long)(pins[i].va - OVL_BASE),
               pins[i].word, got, pins[i].role);
    }

    /* the FLIK count-target table really is popcount over the 4-bit mask */
    tbl_off = (long)(POPCNT_TBL - OVL_BASE);
    printf("\npopcount table at %#010x (file +0x%05lx):", POPCNT_TBL, tbl_off);
    for (i = 0; i < 16; i++) {
        unsigned want = (unsigned)__builtin_popcount((unsigned)i);
        unsigned got = img[tbl_off + (long)i];
        printf(" %u", got);
        if (got != want) tbl_ok = 0;
    }
    printf("\n  popcount(0..15) match: %s\n", tbl_ok ? "YES" : "NO");
    printf("  NOTE: this table lies in MEMORY.BIN's runtime-mutable tail (past\n"
           "  +0x8112), so these are the DISC bytes; a live re-read would be needed\n"
           "  to prove the loaded copy is not rewritten.\n");

    printf("\n%zu/%zu pins OK\n", ok, total);
    if (ok != total || !tbl_ok) { free(img); return 1; }

    puts("\nCOUNTER ANIMATION CLOSED:");
    puts("  one per-frame loop (s3: 800 -> 0); three numerators s4/s6/s5 each");
    puts("  incremented by 1 when below target and fp==0, i.e. 30 Hz;");
    puts("  targets = grain [0x800A65A1], FLIK popcount_table[mask], enemies");
    puts("  [0x80082258] - [0x800A658E] (total - remaining = defeated);");
    puts("  denominator '50' is two literal digits, so it is 50 on EVERY level;");
    puts("  a fresh face-button press inside 25<=s3<740 SNAPS the counters rather");
    puts("  than skipping the screen.");
    free(img);
    return 0;
}
