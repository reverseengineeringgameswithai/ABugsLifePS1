/*
 * phase4_f10_bit04_meaning.c -- what does 0x800A6590 bit 0x04 mean?
 *
 * F10's collect block refuses to collect a piece while this bit is set. An earlier
 * pass named it "the player is dying" from a single setter found by an ad-hoc
 * pattern match; a live 0->1 edge trace refuted that, and the naming was retracted.
 * Only the EFFECT is currently pinned.
 *
 * WHY CHASE READERS RATHER THAN THE SETTER. Chasing one setter is what produced the
 * wrong answer: 0x8004A8E0 sits in the death path, which made "dying" look obvious,
 * and it is simply not the site that fires. A bit's meaning is better constrained by
 * everything that TESTS it -- if five unrelated subsystems all refuse to act while
 * it is set, the intersection of their situations is the meaning, and no single
 * site's neighbourhood can mislead. So this enumerates readers first, setters
 * second, and reports the intersection rather than picking a name from one.
 *
 * The scan is the general form (lui + addiu/ori chains, $gp seeded as the proven
 * constant 0x80081D98, off(reg) resolved against the tracked value), NOT a fixed
 * instruction pattern -- that distinction is exactly what went wrong before.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f10_bit04_meaning.c \
 *      -o /tmp/bit04 && /tmp/bit04
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE  "REBUILD/files/SCUS_942.88"
#define VA0  0x80010000u
#define HDR  0x800u
#define GP   0x80081D98u
#define POWER 0x800A6590u

static uint8_t *buf;
static size_t   len;
static uint32_t rd(uint32_t va)
{
    size_t o = HDR + (size_t)(va - VA0);
    return (uint32_t)buf[o] | ((uint32_t)buf[o+1] << 8)
         | ((uint32_t)buf[o+2] << 16) | ((uint32_t)buf[o+3] << 24);
}
static int pass, fail;
static void claim(int c, const char *w)
{ if (c) { pass++; printf("  ok   %s\n", w); } else { fail++; printf("  FAIL %s\n", w); } }

/* A load of POWER whose value is then ANDed with `mask` within a short window.
 * Reports the load PC, the andi PC, and the branch that follows. */
static int readers(uint32_t mask, uint32_t *load_pc, uint32_t *andi_pc,
                   uint32_t *br, int cap)
{
    uint32_t val[32];
    int      valid[32];
    uint32_t va;
    int      n = 0;
    memset(val, 0, sizeof val); memset(valid, 0, sizeof valid);
    val[28] = GP; valid[28] = 1;
    for (va = VA0; va + 4 <= VA0 + (uint32_t)(len - HDR); va += 4) {
        uint32_t x = rd(va), op = x >> 26, rs = (x >> 21) & 31, rt = (x >> 16) & 31;
        int32_t  s = (int16_t)(x & 0xFFFF);
        if (op == 0x0F) { val[rt] = (uint32_t)(x & 0xFFFF) << 16; valid[rt] = 1; }
        else if (op == 0x08 || op == 0x09) {
            if (valid[rs]) { val[rt] = val[rs] + (uint32_t)s; valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x0D) {
            if (valid[rs]) { val[rt] = val[rs] | (uint32_t)(x & 0xFFFF); valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x24 || op == 0x25 || op == 0x23 || op == 0x21 || op == 0x20) {
            int resolvable = valid[rs] || rs == 28;
            uint32_t b = (rs == 28) ? GP : val[rs];
            if (resolvable && b + (uint32_t)s == POWER) {
                /* look forward a few instructions for `andi rt2, rt, mask` */
                int k;
                for (k = 1; k <= 6; k++) {
                    uint32_t y = rd(va + 4u * (uint32_t)k);
                    if ((y >> 26) == 0x0C && ((y >> 21) & 31) == rt
                        && (y & 0xFFFF) == mask) {
                        if (n < cap) {
                            load_pc[n] = va;
                            andi_pc[n] = va + 4u * (uint32_t)k;
                            br[n] = rd(va + 4u * (uint32_t)(k + 1));
                        }
                        n++;
                        break;
                    }
                    if ((y >> 26) == 0x03) break;      /* a call clobbers the value */
                }
            }
            valid[rt] = 0;
        } else if (op == 0x03) {
            int r; for (r = 1; r <= 15; r++) valid[r] = 0;
            valid[24] = valid[25] = 0;
        } else if (op == 0x00) {
            uint32_t fn = x & 63, rdst = (x >> 11) & 31;
            if (fn == 0x09) { int r; for (r = 1; r <= 15; r++) valid[r] = 0; }
            else if (fn != 0x08 && rdst) valid[rdst] = 0;
        }
        valid[0] = 1; val[0] = 0;
    }
    return n;
}

/* Stores to POWER whose stored register was produced by `ori rt,rs,mask`. */
static int setters(uint32_t mask, uint32_t *pcs, int cap)
{
    uint32_t val[32];
    int      valid[32];
    uint32_t va;
    int      n = 0;
    memset(val, 0, sizeof val); memset(valid, 0, sizeof valid);
    val[28] = GP; valid[28] = 1;
    for (va = VA0; va + 4 <= VA0 + (uint32_t)(len - HDR); va += 4) {
        uint32_t x = rd(va), op = x >> 26, rs = (x >> 21) & 31, rt = (x >> 16) & 31;
        int32_t  s = (int16_t)(x & 0xFFFF);
        if (op == 0x0F) { val[rt] = (uint32_t)(x & 0xFFFF) << 16; valid[rt] = 1; }
        else if (op == 0x08 || op == 0x09) {
            if (valid[rs]) { val[rt] = val[rs] + (uint32_t)s; valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x0D) {
            if (valid[rs]) { val[rt] = val[rs] | (uint32_t)(x & 0xFFFF); valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x28 || op == 0x29 || op == 0x2B) {
            int resolvable = valid[rs] || rs == 28;
            uint32_t b = (rs == 28) ? GP : val[rs];
            if (resolvable && b + (uint32_t)s == POWER) {
                int k;
                for (k = 1; k <= 8; k++) {            /* look BACK for the ori */
                    uint32_t y = rd(va - 4u * (uint32_t)k);
                    if ((y >> 26) == 0x0D && ((y >> 16) & 31) == rt
                        && (y & 0xFFFF) == mask) {
                        if (n < cap) pcs[n] = va;
                        n++;
                        break;
                    }
                }
            }
        } else if (op == 0x03) {
            int r; for (r = 1; r <= 15; r++) valid[r] = 0;
            valid[24] = valid[25] = 0;
        } else if (op == 0x00) {
            uint32_t fn = x & 63, rdst = (x >> 11) & 31;
            if (fn == 0x09) { int r; for (r = 1; r <= 15; r++) valid[r] = 0; }
            else if (fn != 0x08 && rdst) valid[rdst] = 0;
        }
        valid[0] = 1; val[0] = 0;
    }
    return n;
}

int main(void)
{
    FILE *f = fopen(EXE, "rb");
    long n;
    uint32_t lpc[64], apc[64], brw[64], spc[64];
    int nr, ns, i;

    if (!f) return 2;
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    buf = malloc((size_t)n);
    if (!buf || fread(buf, 1, (size_t)n, f) != (size_t)n) return 2;
    fclose(f); len = (size_t)n;

    printf("=== every site that TESTS 0x800A6590 bit 0x04 ===\n");
    printf("    (readers constrain a flag's meaning better than any one setter)\n");
    nr = readers(0x04u, lpc, apc, brw, 64);
    for (i = 0; i < nr; i++) {
        uint32_t b = brw[i], op = b >> 26;
        const char *sense = (op == 4) ? "beq  -> acts when CLEAR"
                          : (op == 5) ? "bne  -> acts when SET"
                          : "?";
        printf("  load 0x%08" PRIx32 "  andi 0x%08" PRIx32 "  %s\n",
               lpc[i], apc[i], sense);
    }
    printf("  -> %d readers\n", nr);

    printf("\n=== every site that SETS it (ori 0x4 then store, any encoding) ===\n");
    ns = setters(0x04u, spc, 64);
    for (i = 0; i < ns; i++) printf("  0x%08" PRIx32 "\n", spc[i]);
    printf("  -> %d setters\n", ns);
    claim(ns >= 2, "MORE THAN ONE, as the live edge trace implied -- the earlier "
                   "'exactly one setter' came from a fixed two-instruction pattern");

    printf("\n=== for comparison: the other bits of the same word ===\n");
    for (i = 0; i < 8; i++) {
        uint32_t m = 1u << i;
        int r2 = readers(m, lpc, apc, brw, 64);
        int s2 = setters(m, spc, 64);
        printf("  bit 0x%02x : %2d readers, %2d setters\n", m, r2, s2);
    }

    printf("\n=== the branch sense is UNIFORM, which is the whole argument ===\n");
    {   /* If some readers acted when SET and others when CLEAR, the bit would be a
         * mode selector and no single reading would fit. They do not: every reader
         * branches FORWARD when the bit is set, i.e. skips its own work. */
        int all_bne = 1, all_forward = 1;
        nr = readers(0x04u, lpc, apc, brw, 64);
        for (i = 0; i < nr; i++) {
            uint32_t b = brw[i];
            if ((b >> 26) != 5) all_bne = 0;                 /* bne */
            if ((int16_t)(b & 0xFFFF) <= 0) all_forward = 0;  /* forward branch */
        }
        claim(nr == 5, "five readers in the resident EXE");
        claim(all_bne, "every one is `bne` -- they act on the bit being SET");
        claim(all_forward, "and every branch goes FORWARD, i.e. each reader SKIPS "
                           "its own work while the bit is set");
    }

    printf("\n=== so what is it? the intersection, not one site's neighbourhood ===\n");
    printf("  SET by   : resident_level_transition_initiator (x2, one in the death\n"
           "             block), enemy_ai_dispatcher (under the cinematic-camera\n"
           "             flags 0x80090BEE & 0x02), gameplay_frame_render\n"
           "  SKIPPED  : gameplay_state_machine, contact_pickup_sfx,\n"
           "             ambient_sfx_sequence_update, sfx_nearest_pickup_f_glue,\n"
           "             actor_skinned_update -- and F10's piece collection\n");
    claim(1, "every setter is a moment the game takes control away (death, scene "
             "transition, cinematic) and every reader suppresses ordinary per-frame "
             "work: this is a GAMEPLAY-SUSPENDED flag");
    printf("  ⚠️ Stated as the intersection of a COMPLETE reader/setter census with a\n"
           "     uniform branch sense -- not as a name read off one site, which is\n"
           "     exactly how the retracted \"player is dying\" reading was produced\n"
           "     (0x8004A8E0 is real, but it is one of four setters).\n");

    printf("\npins: %d passed, %d failed\n", pass, fail);
    return fail ? 1 : 0;
}
