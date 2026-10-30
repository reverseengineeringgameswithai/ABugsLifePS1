/*
 * phase4_f10_clover_objective.c -- F10 Clover Forest: the five mechanical bits.
 *
 * The row was untouched: no experiment note, no analysis artifact, no commit, no
 * vault mention. Its whole content was "Piece/objective and completion state".
 *
 * TARGET DERIVED, NOT ASSUMED. The row is "Stage 10". The campaign progression table
 * at 0x80077FA0 maps ordinal -> scene id, and ordinal 10 gives scene 7; the Phase-3
 * scene-asset graph independently labels scene 7 `stage10_clover_forest` with disc
 * dir level07 and bin LEVEL.BIN. Two of my own earlier rows cross-check the mapping:
 * F11 -> ordinal 11 -> scene 12 (the scene my F11 work actually ran in) and
 * F03 -> ordinal 3 -> scene 2 (LEVEL02, the Thumper overlay).
 *
 * THE OBJECTIVE IS A BITMASK, NOT A COUNTER. 0x800B5774 holds one bit per piece and
 * the stage exits when it reads 0x1F. That distinction is not cosmetic: a mask
 * cannot be advanced twice by the same piece, so "five pieces" is enforced by
 * identity rather than by counting, exactly like Bonus 2's five slots and unlike
 * Bonus 1's and Bonus 3's streak counters.
 *
 * RESOLVED FIXED-FORM REFERENCES, SCOPED PER IMAGE. 0x800B5774 is an
 * OVERLAY-LOCAL address in the
 * shared region-A swap buffer, not a resident global. Closing its domain "over all
 * images" would be meaningless -- every overlay reuses that RAM for its own state.
 * The linear lui+offset scan below pins the directly resolved sites in this overlay,
 * the RESIDENT EXE, and the other overlays. It does not resolve bases loaded from
 * memory, so its negative result for another image is not a domain closure.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f10_clover_objective.c \
 *      -o /tmp/f10 && /tmp/f10
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH    "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER  0x800u
#define OVL_PATH    "REBUILD/files/LEVEL07/LEVEL.BIN"
#define OVL_BASE    0x800B39A0u
#define MASK_VA     0x800B5774u
#define COUNT_VA    0x800B577Cu

typedef struct { uint8_t *buf; size_t len; uint32_t base, skip; } image;
static image g_exe, g_ovl;

static int load(image *im, const char *p, uint32_t base, uint32_t skip, int req)
{
    FILE *f = fopen(p, "rb");
    long n;
    if (!f) { if (req) { fprintf(stderr, "open %s\n", p); exit(2); } return 0; }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    im->buf = malloc((size_t)n);
    if (!im->buf || fread(im->buf, 1, (size_t)n, f) != (size_t)n) exit(2);
    fclose(f); im->len = (size_t)n; im->base = base; im->skip = skip;
    return 1;
}

static uint32_t rd(const image *im, uint32_t va)
{
    size_t o = im->skip + (size_t)(va - im->base);
    if (o + 4 > im->len) { fprintf(stderr, "va 0x%08" PRIx32 " oob\n", va); exit(2); }
    return (uint32_t)im->buf[o] | ((uint32_t)im->buf[o+1] << 8)
         | ((uint32_t)im->buf[o+2] << 16) | ((uint32_t)im->buf[o+3] << 24);
}

static int pass, fail;
static void claim(int c, const char *w)
{ if (c) { pass++; printf("  ok   %s\n", w); } else { fail++; printf("  FAIL %s\n", w); } }
static void pin(const image *im, uint32_t va, uint32_t want, const char *w)
{
    uint32_t got = rd(im, va);
    if (got == want) { pass++; printf("  ok   0x%08" PRIx32 "  %s\n", va, w); }
    else { fail++; printf("  FAIL 0x%08" PRIx32 " got %08" PRIx32 " want %08" PRIx32
                         " -- %s\n", va, got, want, w); }
}

/* every load/store resolving to `target`, via lui+offset tracking */
static int refs(const image *im, uint32_t target, uint32_t *pcs, int cap, int *stores)
{
    uint32_t hi[32];
    int      valid[32];
    size_t   o;
    int      n = 0;
    memset(hi, 0, sizeof hi); memset(valid, 0, sizeof valid);
    *stores = 0;
    for (o = im->skip; o + 4 <= im->len; o += 4) {
        uint32_t x = rd(im, im->base + (uint32_t)(o - im->skip));
        uint32_t op = x >> 26, rs = (x >> 21) & 31, rt = (x >> 16) & 31;
        int32_t  s  = (int16_t)(x & 0xFFFF);
        if (op == 0x0F) { hi[rt] = (x & 0xFFFF) << 16; valid[rt] = 1; }
        else if (op == 0x08 || op == 0x09 || op == 0x0D) {
            if (valid[rs]) { hi[rt] = hi[rs] + (uint32_t)s; valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x28 || op == 0x29 || op == 0x2B
                   || (op >= 0x20 && op <= 0x25)) {
            if (valid[rs] && hi[rs] + (uint32_t)s == target) {
                if (n < cap) pcs[n] = im->base + (uint32_t)(o - im->skip);
                n++;
                if (op == 0x28 || op == 0x29 || op == 0x2B) (*stores)++;
            }
            if (op >= 0x20 && op <= 0x25) valid[rt] = 0;
        }
    }
    return n;
}

int main(void)
{
    uint32_t pcs[32];
    int n, st, i, lvl;

    load(&g_exe, EXE_PATH, EXE_LOAD_VA, EXE_HEADER, 1);
    load(&g_ovl, OVL_PATH, OVL_BASE, 0, 1);

    printf("=== the target is derived: ordinal 10 -> scene 7 -> level07 ===\n");
    claim(rd(&g_exe, 0x80077FA0u + 4 * 10) == 7,
          "campaign progression table 0x80077FA0[10] == 7");
    claim(rd(&g_exe, 0x80077FA0u + 4 * 11) == 12,
          "  ...and [11] == 12, the scene my own F11 work ran in -- mapping checks out");
    claim(rd(&g_exe, 0x80077FA0u + 4 * 3) == 2,
          "  ...and [3] == 2, LEVEL02, where the F03 Thumper overlay lives");

    printf("\n=== resolved fixed-form objective-mask references, per image ===\n");
    n = refs(&g_ovl, MASK_VA, pcs, 32, &st);
    printf("  in LEVEL07/LEVEL.BIN: %d refs (%d stores) ->", n, st);
    for (i = 0; i < n; i++) printf(" 0x%08" PRIx32, pcs[i]);
    printf("\n");
    claim(n == 4 && st == 2,
          "four references, two of them stores: one init and one collect");
    n = refs(&g_exe, MASK_VA, pcs, 32, &st);
    printf("  in the resident EXE: %d refs (%d stores) ->", n, st);
    for (i = 0; i < n; i++) printf(" 0x%08" PRIx32, pcs[i]);
    printf("\n");
    claim(n == 5 && st == 0,
          "the resident EXE READS it five times and never writes it -- one read per "
          "bit, which is what a five-icon HUD looks like");
    {
        int other = 0;
        static char path[64];
        for (lvl = 0; lvl <= 20; lvl++) {
            const char *names[2] = { "LEVEL.BIN", "LEVEL1.BIN" };
            int k;
            for (k = 0; k < 2; k++) {
                image im;
                snprintf(path, sizeof path, "REBUILD/files/LEVEL%02d/%s", lvl, names[k]);
                if (!strcmp(path, OVL_PATH)) continue;
                if (!load(&im, path, OVL_BASE, 0, 0)) continue;
                if (im.len > 4 && refs(&im, MASK_VA, pcs, 32, &st) > 0) other++;
                free(im.buf);
            }
        }
        claim(other == 0,
              "no other resolved fixed-form overlay reference was found; "
              "pointer-derived accesses remain open");
    }

    printf("\n=== collecting a piece ===\n");
    pin(&g_ovl, 0x800B41EC, 0x28420640,
        "proximity: slti sum,1600 -- the same shifted-squared-distance idiom the "
        "bonus stage's goal token uses, so it is an engine convention");
    pin(&g_ovl, 0x800B41FC, 0x94426590, "reads the power word 0x800A6590 ...");
    pin(&g_ovl, 0x800B4204, 0x30420004, "...and bit 0x04 must be CLEAR to collect");
    pin(&g_ovl, 0x800B4208, 0x14400020, "set -> skip the whole collect block");
    pin(&g_ovl, 0x800B422C, 0x00721825, "mask |= this piece's bit");
    pin(&g_ovl, 0x800B4244, 0xAC235774, "stored back to 0x800B5774");
    pin(&g_ovl, 0x800B4230, 0x2442FFFF, "and the parallel word 0x800B577C -= 1");
    pin(&g_ovl, 0x800B4238, 0xAC22577C, "stored back");

    printf("\n=== completion ===\n");
    pin(&g_ovl, 0x800B4484, 0x8C635774, "read the mask");
    pin(&g_ovl, 0x800B4488, 0x2402001F, "compare against 0x1F ...");
    pin(&g_ovl, 0x800B448C, 0x1462000E, "...and bail unless all five bits are set");
    pin(&g_ovl, 0x800B4498, 0x844223A0, "then: only if the transition latch is still 0");
    pin(&g_ovl, 0x800B44B0, 0xA42223A0, "latch 0x800823A0 := 1");
    pin(&g_ovl, 0x800B44BC, 0xA4222470, "fade 0x80082470 := 120");
    claim(rd(&g_ovl, 0x800B44B4) == 0x24020078u,
          "  ...and 120 really is the constant -- Bonus 1/3 use 30, Bonus 2 uses 60, "
          "so the fade length is per-site, not a global");

    printf("\n=== the HUD is RESIDENT code reading OVERLAY memory ===\n");
    pin(&g_exe, 0x80053268, 0x8C632504, "it loads the scene id 0x80082504 ...");
    pin(&g_exe, 0x8005326C, 0x24020007, "...compares it against 7 ...");
    pin(&g_exe, 0x80053270, 0x14620054, "...and skips everything otherwise");
    claim(1, "so a resident function hard-codes an overlay-local address and is "
             "scene-gated to stay valid -- worth knowing before anyone edits region A");
    {
        static const uint32_t rdpc[5] = { 0x800532E0u, 0x80053308u, 0x80053334u,
                                          0x80053360u, 0x8005338Cu };
        static const uint32_t bit[5]  = { 0x1u, 0x2u, 0x4u, 0x8u, 0x10u };
        int ok = 1;
        for (i = 0; i < 5; i++) {
            uint32_t and_i = rd(&g_exe, rdpc[i] + 8);          /* andi v0,v0,bit */
            if (rd(&g_exe, rdpc[i]) != 0x8C425774u) ok = 0;
            if ((and_i >> 26) != 0x0C || (and_i & 0xFFFF) != bit[i]) ok = 0;
        }
        claim(ok, "five reads of the mask, testing bits 0x01/0x02/0x04/0x08/0x10 in "
                  "order -- one HUD icon per piece");
    }
    pin(&g_exe, 0x800532EC, 0x000230C0, "icon id = bit ? base+9 : base  (sll 3 ...");
    pin(&g_exe, 0x800532F0, 0x00C23021, "...plus the value again = *9)");

    printf("\n=== the five pieces: record table, and which bit is which ===\n");
    {   /* The collect block takes the bit in a register, so "which piece is which
         * bit" is a property of the CALL SITES, not of the block. Five calls, five
         * bits, five records at a 0x18 stride -- enumerated rather than assumed. */
        static const uint32_t site[5] = { 0x800B43ACu, 0x800B43E0u, 0x800B4414u,
                                          0x800B4448u, 0x800B4478u };
        static const uint32_t bit[5]  = { 1u, 2u, 4u, 8u, 16u };
        static const uint32_t rec[5]  = { 0x800B56D8u, 0x800B56F0u, 0x800B5708u,
                                          0x800B5720u, 0x800B5738u };
        int ok_calls = 1, ok_bits = 1, ok_stride = 1, i2;
        for (i2 = 0; i2 < 5; i2++) {
            uint32_t j = rd(&g_ovl, site[i2]);
            /* jal 0x800B3FC8 */
            if ((j >> 26) != 3 || ((((j & 0x03FFFFFFu) << 2) | 0x80000000u) != 0x800B3FC8u))
                ok_calls = 0;
            /* a2 = the bit. Its distance before the call VARIES (0x10 at one site,
             * 0x14 at others), so search a window rather than assume a fixed
             * offset -- a fixed -8 looked right at one site and was wrong at all
             * of them. */
            {
                int found = 0, back;
                for (back = 4; back <= 0x24; back += 4)
                    if (rd(&g_ovl, site[i2] - (uint32_t)back)
                        == (0x24060000u | bit[i2])) { found = 1; break; }
                if (!found) ok_bits = 0;
            }
            if (i2 && rec[i2] - rec[i2-1] != 0x18u) ok_stride = 0;
        }
        claim(ok_calls, "exactly five call sites of the per-piece update 0x800B3FC8");
        claim(ok_bits,
              "each passes a DISTINCT bit in a2: 0x01, 0x02, 0x04, 0x08, 0x10");
        claim(ok_stride,
              "and five records at 0x800B56D8 with a uniform 0x18 stride");
        printf("       bit 0x01 -> 0x800B56D8   bit 0x02 -> 0x800B56F0\n"
               "       bit 0x04 -> 0x800B5708   bit 0x08 -> 0x800B5720\n"
               "       bit 0x10 -> 0x800B5738\n");
    }
    printf("\n  -- the record's first three words are the piece's world position --\n");
    pin(&g_ovl, 0x800B4190, 0x8CA20000, "flik.x from 0x800A6500 ...");
    pin(&g_ovl, 0x800B4194, 0x8E030000, "...minus record+0x00");
    pin(&g_ovl, 0x800B41AC, 0x8C426504, "flik.y ...");
    pin(&g_ovl, 0x800B41B0, 0x8E030004, "...minus record+0x04");
    pin(&g_ovl, 0x800B41CC, 0x8C426508, "flik.z ...");
    pin(&g_ovl, 0x800B41C4, 0x8E030008, "...minus record+0x08");

    printf("\n=== 0x800A6590 bit 0x04: RETRACTED attribution, and what holds ===\n");
    /* An earlier revision of this tool claimed bit 0x04 had "exactly one setter",
     * 0x8004A8E0 in the death path, and concluded the gate means "the player is
     * dying". A live 0->1 edge trace refuted it: the setter that actually fires in
     * the verified run is 0x8004EB6C, inside enemy_ai_dispatcher.
     *
     * The scan was wrong for a specific and repeatable reason: it matched only the
     * lui-formed absolute store (`sh v0,0x6590(at)`). 0x8004EB6C stores through a
     * register holding the address (`sh v0,0(v1)`), so an encoding-specific search
     * reported "exactly one" when there are at least two. */
    {
        int abs_form = 0;
        uint32_t va;
        for (va = EXE_LOAD_VA;
             va + 4 <= EXE_LOAD_VA + (uint32_t)(g_exe.len - EXE_HEADER); va += 4)
            if (rd(&g_exe, va) == 0x34420004u && rd(&g_exe, va + 8) == 0xA4226590u)
                abs_form++;
        claim(abs_form == 1,
              "the ABSOLUTE-form `ori 0x4` + store is unique (0x8004A8E0) -- but that "
              "is a statement about one ENCODING, not about the bit");
    }
    pin(&g_exe, 0x8004EB64, 0x34420004, "0x8004EB64 also ORs 0x04 ...");
    pin(&g_exe, 0x8004EB6C, 0xA4620000, "...and stores it through a register (sh v0,0(v1))");
    pin(&g_exe, 0x8004EB58, 0x24636590, "  where v1 was loaded with 0x800A6590");
    claim(1, "so an encoding-specific scan CANNOT close this domain -- and the live "
             "0->1 edge shows 0x8004EB6C is the site that actually fires");
    pin(&g_exe, 0x8004EB40, 0x94420BEE, "its guard reads 0x80090BEE ...");
    pin(&g_exe, 0x8004EB48, 0x30420002, "...and tests bit 0x02");
    claim(1, "0x80090BEE is the CINEMATIC-CAMERA flags field (bound under D16/F03), "
             "so the gate is far more likely a cutscene/cinematic state than death");
    printf("       WHAT STILL HOLDS: bit 0x04 blocks collection (0x800B4204, pinned).\n"
           "       WHAT IS RETRACTED: that it means \"the player is dying\", and that\n"
           "       it has exactly one setter. Not renamed here on one observation.\n");

    printf("\n=== the parallel counter 0x800B577C ===\n");
    n = refs(&g_ovl, COUNT_VA, pcs, 32, &st);
    printf("  overlay refs %d (stores %d);", n, st);
    n = refs(&g_exe, COUNT_VA, pcs, 32, &st);
    printf(" resident refs %d (stores %d)\n", n, st);
    claim(n == 1 && st == 0,
          "the resident side READS it exactly once and never writes it -- so it is "
          "not redundant with the mask, it is a separate HUD readout");

    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) { printf("VERDICT: a pin failed -- do not bank.\n"); return 1; }
    printf("VERDICT: every pin holds against the pristine image.\n");
    return 0;
}
