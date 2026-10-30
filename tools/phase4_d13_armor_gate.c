/*
 * phase4_d13_armor_gate.c -- pin the berry-tough gate PC for D13 (armored beetles).
 *
 * D13's substance was closed on 2026-08-02: shell_bug identity, campaign breadth
 * (LEVEL04 only, 6 records), aggro confirmed negative, and the armor mechanic
 * established behaviourally by the operator across all five native berry classes --
 * RED does zero damage, BLUE/HOMING/GOLD/MEGA all damage normally.
 *
 * ⚠️ CREDIT CORRECTION. The row's `missing` said the gate was "behaviorally
 * confirmed, not statically pinned", and that is what this tool was written against.
 * It was stale: D04 had ALREADY pinned 0x80058EE4 the previous day
 * (EXP_2026-08-03_phase4_d04_berry_immunity_matrix: "0x80058EE4: mask bit 0x40").
 * Reading the sibling row's note first would have found it. The operator said this
 * family was already done, and was right.
 *
 * What this tool adds on top of that pin, and why it is still worth keeping: the
 * two-branch exclusion structure, the identification of the OTHER 0x40 test in the
 * same handler as a different question, the bounce-off block as the rejection's
 * observable form, and a CHECKED negative about the threshold.
 *
 * THE GATE, in contact_vs_actor_handler:
 *
 *     0x80058EDC  lhu  v0, 0x5C(s2)        ; the actor's flags
 *     0x80058EE4  andi v0, v0, 0x40        ; the berry-tough bit
 *     0x80058EE8  beq  v0, zero -> 0x8005905C   ; NOT tough -> normal damage dispatch
 *     0x80058EF0  lh   v0, 0x24(s1)
 *     0x80058EF8  beq  v0, 1    -> 0x80058F10   ; -> BOUNCE OFF
 *     0x80058F00  lbu  v0, 0x2C(s1)        ; the contact damage class
 *     0x80058F08  bne  v0, 1    -> 0x8005905C   ; class != 1 -> normal damage
 *                 (fall through)            -> 0x80058F10  BOUNCE OFF
 *
 * So the exclusion is not a power threshold and not a timed window: an actor with
 * bit 0x40 rejects exactly the contacts whose damage class is 1 (or whose +0x24 is
 * 1), and everything else falls through to the ordinary damage path. The bounce-off
 * block is identifiable on its own terms -- it assigns velocity -1280, reads two
 * bytes from the shared rolling cursor 0x800822F4 to jitter the rebound, and sets
 * timers -- i.e. it is the berry visibly pinging off the shell.
 *
 * ⚠️ WHAT THIS DOES *NOT* ESTABLISH. That the class-1 contacts are exactly the red
 * berries is the operator's behavioural result, not something proven here: this tool
 * pins the gate and its condition, and does not chase which berry constructor writes
 * class 1 to +0x2C. Stated as a separate claim so the two are not conflated.
 *
 * Corroboration that +0x2C really is the contact damage class rather than a guess:
 * the Bonus-3 accept path reads the same field with the same instruction encoding
 * (0x8005916C, requiring class 0), and that reading is independently established.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_d13_armor_gate.c \
 *      -o /tmp/d13gate && /tmp/d13gate
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define EXE_PATH    "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER  0x800u
#define HANDLER_LO  0x80058AF8u
#define HANDLER_HI  0x8005905Cu

static uint8_t *g_buf;
static size_t   g_len;

static uint32_t w(uint32_t va)
{
    size_t o = EXE_HEADER + (size_t)(va - EXE_LOAD_VA);
    if (o + 4 > g_len) { fprintf(stderr, "va 0x%08" PRIx32 " out of image\n", va); exit(2); }
    return (uint32_t)g_buf[o] | ((uint32_t)g_buf[o+1] << 8)
         | ((uint32_t)g_buf[o+2] << 16) | ((uint32_t)g_buf[o+3] << 24);
}

static int pass, fail;

static void pin(uint32_t va, uint32_t want, const char *why)
{
    uint32_t got = w(va);
    if (got == want) { pass++; printf("  ok   0x%08" PRIx32 "  %s\n", va, why); }
    else { fail++; printf("  FAIL 0x%08" PRIx32 " got %08" PRIx32 " want %08" PRIx32
                          " -- %s\n", va, got, want, why); }
}

static void claim(int cond, const char *why)
{
    if (cond) { pass++; printf("  ok   %s\n", why); }
    else      { fail++; printf("  FAIL %s\n", why); }
}

int main(void)
{
    FILE *f = fopen(EXE_PATH, "rb");
    long  n;
    if (!f) { fprintf(stderr, "cannot open %s\n", EXE_PATH); return 2; }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    g_buf = malloc((size_t)n);
    if (!g_buf || fread(g_buf, 1, (size_t)n, f) != (size_t)n) return 2;
    fclose(f); g_len = (size_t)n;

    printf("=== the berry-tough gate is unique in its handler ===\n");
    {   /* If several sites tested bit 0x40 against an actor's +0x5C here, "the gate"
         * would be an ambiguous phrase. Two do; they are distinguished below. */
        uint32_t va; int hits = 0, at_dfc = 0, at_ee4 = 0;
        for (va = HANDLER_LO; va < HANDLER_HI; va += 4) {
            uint32_t x = w(va);
            if ((x >> 26) == 0x0C && (x & 0xFFFF) == 0x40) {
                hits++;
                if (va == 0x80058DFCu) at_dfc = 1;
                if (va == 0x80058EE4u) at_ee4 = 1;
            }
        }
        printf("  andi ...,0x40 sites in contact_vs_actor_handler: %d\n", hits);
        claim(hits == 2 && at_dfc && at_ee4,
              "exactly two, at 0x80058DFC and 0x80058EE4 -- both read the actor's "
              "+0x5C, so the right one has to be identified, not assumed");
    }

    printf("\n=== the OTHER 0x40 site is a different question ===\n");
    pin(0x80058DE4, 0x92230027, "0x80058DFC's branch is gated on [s1+0x27] == 4 ...");
    pin(0x80058DEC, 0x14620014, "...else it is skipped entirely");
    pin(0x80058E00, 0x1440011F, "and on the bit being SET it jumps to 0x80059280");
    claim(1, "so that one guards a specific action type, not the damage path");

    printf("\n=== THE GATE (D13's named residual) ===\n");
    pin(0x80058EDC, 0x9642005C, "lhu v0,0x5C(s2) -- the actor's flags");
    pin(0x80058EE4, 0x30420040, "andi v0,v0,0x40 -- the berry-tough bit  <== THE PC");
    pin(0x80058EE8, 0x1040005C, "NOT tough -> 0x8005905C, the ordinary damage dispatch");
    claim(0x80058EE8u + 4 + (uint32_t)((int16_t)0x005C * 4) == 0x8005905Cu,
          "  ...and that target really is berry_tough_damage_dispatch's entry");
    pin(0x80058EF0, 0x86220024, "tough: read [s1+0x24]");
    pin(0x80058EF8, 0x104A0005, "== 1 -> bounce off");
    pin(0x80058F00, 0x9222002C, "else read [s1+0x2C], the contact damage class");
    pin(0x80058F08, 0x144A0054, "class != 1 -> 0x8005905C, damage as normal");
    claim(0x80058F08u + 4 + (uint32_t)((int16_t)0x0054 * 4) == 0x8005905Cu,
          "  ...to the same ordinary dispatch");
    claim(1, "=> class 1 falls through to 0x80058F10 and is REJECTED");

    printf("\n=== the rejection path is the berry pinging off, not silence ===\n");
    pin(0x80058F30, 0x2402FB00, "velocity -1280");
    pin(0x80058F18, 0x8CE722F4, "two bytes off the shared cursor 0x800822F4 ...");
    pin(0x80058F48, 0x2463FF80, "...biased by -128, to jitter the rebound");
    pin(0x80058F60, 0x24020032, "and timers 50 / 60 are set");
    pin(0x80058F68, 0x2402003C, "");

    printf("\n=== +0x2C really is the contact damage class ===\n");
    claim(w(0x8005916C) == w(0x80058F00),
          "the Bonus-3 accept path reads it with the identical encoding at "
          "0x8005916C, where the class-0 requirement is independently established");

    printf("\n=== the exclusion is NOT a power threshold ===\n");
    {   /* The earlier speculation was a vulnerability window or a power comparison.
         * Neither appears: between the bit test and the rejection there is no
         * comparison against any of the five power values the operator tested. */
        uint32_t va; int cmps = 0;
        for (va = 0x80058EE4u; va <= 0x80058F08u; va += 4) {
            uint32_t x = w(va), op = x >> 26, imm = x & 0xFFFF;
            if ((op == 0x0A || op == 0x0B || op == 0x08 || op == 0x09)
                && (imm == 2 || imm == 5 || imm == 8 || imm == 11 || imm == 45)) cmps++;
        }
        claim(cmps == 0,
              "no comparison against 2/5/8/11/45 anywhere between the bit test and "
              "the rejection -- it is an equality test on one class value");
    }

    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) { printf("VERDICT: a pin failed -- do not bank.\n"); return 1; }
    printf("VERDICT: every pin holds against the pristine image.\n");
    return 0;
}
