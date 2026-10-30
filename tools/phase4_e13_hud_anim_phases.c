/* Phase 4 E13 follow-up: what 0x800B0188 / 0x800B018C / 0x800B0190 are.
 *
 * The in-game HUD stage (entry 0x800526F4, body 0x800526FC -- see
 * tools/phase4_e13_ingame_hud.c) writes 0x400 into all three of these halfwords
 * when a transition is running with the goal latch still clear.  This tool pins
 * what they actually are: PER-HUD-ELEMENT ANIMATION PHASE COUNTERS.
 *
 * Each runs a 0..0x1000 cycle advanced once per frame by the stage's own argument
 * (s3), and 0x400 is the significant point in that cycle.
 *
 *   0x800B0188 -- LIVES.  At phase == exactly 0x400 it latches the live value of
 *                 0x800A65A0 into the display slot; the phase then advances by s3
 *                 and resets to 0 once it passes 0x1000.
 *   0x800B018C -- GRAIN.  Identical shape, latching 0x800A65A1, whose tens/units
 *                 digits are split with the 0xCCCCCCCD divide-by-10 reciprocal.
 *   0x800B0190 -- drives a piecewise RAMP rather than a latch: phase >= 0xC01
 *                 subtracts 0x800; else phase >= 0x401 clamps to 0x400; the result
 *                 is then doubled.  So it rises, holds at the 0x400 plateau, then
 *                 falls -- an animation magnitude, not a value commit.
 *
 * That makes the transition write meaningful: forcing all three to 0x400 puts each
 * element at its commit / peak point.
 *
 * These same halfwords are also written and read by 0x80054EB4 -- the body behind
 * the already-Canon 8-byte head grain_pickup_handler 0x80054EAC, which is a FOURTH
 * instance of this codebase's 8-byte-head-then-fall-through idiom (the others being
 * 0x800526F4, 0x8004F478 and C05's 0x80051938).
 *
 * Usage:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_e13_hud_anim_phases.c \
 *      -o /tmp/e13_anim
 *   /tmp/e13_anim REBUILD/files/SCUS_942.88
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
    /* the non-completion transition forces all three to the 0x400 point */
    {0x80052748u, 0xA4220188u, "transition: [0x800B0188] = 0x400"},
    {0x80052750u, 0xA422018Cu, "transition: [0x800B018C] = 0x400"},
    {0x80052758u, 0xA4220190u, "transition: [0x800B0190] = 0x400"},

    /* 0x800B0188 -- LIVES, latch at phase 0x400, wrap past 0x1000 */
    {0x800528B8u, 0x84630188u, "lives phase: lh v1, [0x800B0188]"},
    {0x800528BCu, 0x24020400u, "lives phase: compare against 0x400"},
    {0x800528C0u, 0x14620005u, "lives phase: bne -> skip the latch"},
    {0x800528CCu, 0x904265A0u, "lives phase: at 0x400 latch LIVES [0x800A65A0]"},
    {0x800528E0u, 0xA4220188u, "lives phase += s3, stored back"},
    {0x800528ECu, 0x28421001u, "lives phase: slti 0x1001 (cycle bound)"},
    {0x800528FCu, 0xA4200188u, "lives phase: past the bound -> reset to 0"},

    /* 0x800B018C -- GRAIN, same shape, digits via the /10 reciprocal */
    {0x80052B44u, 0x8463018Cu, "grain phase: lh v1, [0x800B018C]"},
    {0x80052B4Cu, 0x14620011u, "grain phase: bne -> skip the latch"},
    {0x80052B58u, 0x908465A1u, "grain phase: at 0x400 latch GRAIN [0x800A65A1]"},
    {0x80052B60u, 0x3442CCCDu, "grain digits: 0xCCCCCCCD divide-by-10 reciprocal"},

    /* 0x800B0190 -- a piecewise ramp, not a latch */
    {0x80052924u, 0x84A50190u, "ramp: lh a1, [0x800B0190]"},
    {0x8005292Cu, 0x28A20C01u, "ramp: >= 0xC01 ?"},
    {0x8005293Cu, 0x24A5F800u, "ramp:   yes -> a1 -= 0x800 (falling limb)"},
    {0x80052934u, 0x28A20401u, "ramp: >= 0x401 ?"},
    {0x80052948u, 0x24050400u, "ramp:   yes -> clamp to 0x400 (plateau)"},
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

    puts("\nE13: 0x800B0188/018C/0190 are PER-HUD-ELEMENT ANIMATION PHASE COUNTERS.");
    puts("  0x0188 lives  -- latches 0x800A65A0 at phase 0x400, cycle bound 0x1000");
    puts("  0x018C grain  -- latches 0x800A65A1 at phase 0x400, digits via /10");
    puts("  0x0190        -- piecewise ramp (rise, plateau at 0x400, fall), a magnitude");
    puts("  The non-completion transition writes 0x400 to all three, i.e. forces each");
    puts("  element to its commit/peak point.");
    free(exe);
    return 0;
}
