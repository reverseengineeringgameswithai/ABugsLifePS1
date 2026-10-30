/*
 * phase4_f17_f18_streak_law.c -- closing the Bonus-2 and Bonus-3 chain state.
 *
 * F16's counter turned out to have four clears that Canon did not mention, and the
 * causal model for one of them ("berry kills reset it") was wrong. That happened
 * because nobody had ever CLOSED the domain -- enumerated every instruction that
 * touches the counter -- so every description was a sample presented as a rule.
 *
 * This does the same closure for the other two chains, and it is deliberately a
 * cheap check rather than a second investigation: the payoff is not new mechanism,
 * it is turning "here is how it resets" into a statement that can be trusted.
 *
 *   Bonus 3 (F18): 0x80082240 = gp+1192, a word.
 *   Bonus 2 (F17): FIVE BYTES at 0x80082248..0x8008224C -- NOT five words. The
 *                  writers are `sb`, slot 0 reached as gp+1200 and slots 1..4
 *                  absolutely. An earlier revision of the runtime tracer watched
 *                  them at stride 4, which reads slot 4 as slot 1 and then three
 *                  unrelated globals; the mistake is easy and silent, so the byte
 *                  width is pinned here.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f17_f18_streak_law.c \
 *      -o /tmp/f1718law && /tmp/f1718law
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH    "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER  0x800u
#define GP          0x80081D98u
#define B3_STREAK   0x80082240u
#define B2_SLOT0    0x80082248u

typedef struct { const char *path; uint8_t *buf; size_t len; uint32_t base, skip; } image;

static image g_exe;
static image g_ovl[64];
static int   n_ovl;

static int load_image(image *im, const char *path, uint32_t base, uint32_t skip, int req)
{
    FILE *f = fopen(path, "rb");
    long  n;
    if (!f) { if (req) { fprintf(stderr, "cannot open %s\n", path); exit(2); } return 0; }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    im->buf = malloc((size_t)n);
    if (!im->buf || fread(im->buf, 1, (size_t)n, f) != (size_t)n) { fclose(f); exit(2); }
    fclose(f);
    im->path = path; im->len = (size_t)n; im->base = base; im->skip = skip;
    return 1;
}

static uint32_t rdw(const image *im, uint32_t va)
{
    size_t o = im->skip + (size_t)(va - im->base);
    return (uint32_t)im->buf[o] | ((uint32_t)im->buf[o+1] << 8)
         | ((uint32_t)im->buf[o+2] << 16) | ((uint32_t)im->buf[o+3] << 24);
}

static int in_img(const image *im, uint32_t va)
{
    size_t o;
    if (va < im->base) return 0;
    o = im->skip + (size_t)(va - im->base);
    return o + 4 <= im->len;
}

static int pass, fail;

static void claim(int cond, const char *why)
{
    if (cond) { pass++; printf("  ok   %s\n", why); }
    else      { fail++; printf("  FAIL %s\n", why); }
}

static void pin(uint32_t va, uint32_t want, const char *why)
{
    uint32_t got;
    if (!in_img(&g_exe, va)) { printf("  FAIL 0x%08" PRIx32 " out of image\n", va);
                               fail++; return; }
    got = rdw(&g_exe, va);
    if (got == want) { pass++; printf("  ok   0x%08" PRIx32 "  %s\n", va, why); }
    else { fail++; printf("  FAIL 0x%08" PRIx32 " got %08" PRIx32 " want %08" PRIx32
                          " -- %s\n", va, got, want, why); }
}

/* Fixed-form heuristic for gp-relative and 0x8008-displacement candidates.
 * It does not prove the runtime value of non-gp bases and is not an EA closure. */
static uint32_t target_of(uint32_t w)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31;
    int32_t  s  = (int16_t)(w & 0xFFFF);
    int is_mem = (op == 0x20 || op == 0x21 || op == 0x23 || op == 0x24 || op == 0x25
                  || op == 0x28 || op == 0x29 || op == 0x2B);
    if (!is_mem) return 0;
    if (rs == 28) return GP + (uint32_t)s;
    return 0x80080000u + (uint32_t)s;
}

static int is_store(uint32_t w)
{
    uint32_t op = w >> 26;
    return op == 0x28 || op == 0x29 || op == 0x2B;
}

static const char *width_of(uint32_t w)
{
    switch (w >> 26) {
    case 0x28: return "sb";
    case 0x29: return "sh";
    case 0x2B: return "sw";
    default:   return "??";
    }
}

static void census(uint32_t lo, uint32_t hi, const char *label,
                   uint32_t *store_pcs, int *n_store, int *n_load, int *ovl_hits)
{
    uint32_t va;
    int i;
    *n_store = *n_load = *ovl_hits = 0;
    printf("=== %s: resolved fixed-form candidates in the EXE and %d overlays ===\n",
           label, n_ovl);
    for (va = EXE_LOAD_VA; in_img(&g_exe, va); va += 4) {
        uint32_t w = rdw(&g_exe, va), a = target_of(w);
        if (a < lo || a > hi) continue;
        if (is_store(w)) {
            if (*n_store < 32) store_pcs[(*n_store)] = va;
            (*n_store)++;
            printf("  STORE %-2s 0x%08" PRIx32 " -> 0x%08" PRIx32 "\n",
                   width_of(w), va, a);
        } else {
            (*n_load)++;
        }
    }
    for (i = 0; i < n_ovl; i++)
        for (va = g_ovl[i].base; in_img(&g_ovl[i], va); va += 4) {
            uint32_t a = target_of(rdw(&g_ovl[i], va));
            if (a >= lo && a <= hi) (*ovl_hits)++;
        }
    printf("  loads %d | stores %d | overlay accesses %d\n",
           *n_load, *n_store, *ovl_hits);
}

int main(void)
{
    int lvl;
    uint32_t pcs[32];
    int ns, nl, no;
    char (*paths)[64] = malloc(64 * 64);
    if (!paths) return 2;

    load_image(&g_exe, EXE_PATH, EXE_LOAD_VA, EXE_HEADER, 1);
    for (lvl = 0; lvl <= 20 && n_ovl < 60; lvl++) {
        snprintf(paths[n_ovl], 64, "REBUILD/files/LEVEL%02d/LEVEL.BIN", lvl);
        if (load_image(&g_ovl[n_ovl], paths[n_ovl], 0x800B39A0u, 0, 0)) n_ovl++;
        snprintf(paths[n_ovl], 64, "REBUILD/files/LEVEL%02d/LEVEL1.BIN", lvl);
        if (load_image(&g_ovl[n_ovl], paths[n_ovl], 0x800B39A0u, 0, 0)) n_ovl++;
    }
    snprintf(paths[n_ovl], 64, "REBUILD/files/BITS/MEMORY.BIN");
    if (load_image(&g_ovl[n_ovl], paths[n_ovl], 0x800B5788u, 0, 0)) n_ovl++;

    /* ------------------------------------------------------------ BONUS 3 -- */
    census(B3_STREAK, B3_STREAK + 3, "Bonus 3 streak 0x80082240", pcs, &ns, &nl, &no);
    claim(nl == 1, "scanner resolves ONE direct read");
    claim(ns == 5, "scanner resolves FIVE direct writes -- one increment and four clears");
    claim(no == 0, "no fixed-form overlay candidate");

    printf("\n--- Bonus 3: the accept path ---\n");
    pin(0x8005916C, 0x9222002C, "contact damage class must be 0");
    pin(0x80059174, 0x1440001E, "...else skip");
    pin(0x80059184, 0x1462001A, "actor id must be 15 (grasshopper), else skip");
    pin(0x80059198, 0x30820040, "earned guard: flags & 0x40");
    pin(0x800591B0, 0x24420072, "progress command = streak + 114");
    pin(0x800591C0, 0xAF8304A8, "INCREMENT");
    pin(0x800591C4, 0x1462000A, "threshold 5");
    pin(0x800591C8, 0x34820004, "the fifth ORs low bit 0x04");
    pin(0x800591DC, 0xA42223A0, "latch 6");
    pin(0x800591E8, 0xA4222470, "fade 30");
    pin(0x800591EC, 0xAF8004A8, "and resets");
    {   /* Canon notes Bonus 3 has no scene test; make that a checked claim */
        uint32_t va; int scene_tests = 0;
        for (va = 0x8005916Cu; va <= 0x800591ECu; va += 4)
            if (target_of(rdw(&g_exe, va)) == 0x80082504u) scene_tests++;
        claim(scene_tests == 0,
              "the accept path reads no scene id -- Bonus 3 really has no scene gate");
    }

    printf("\n--- Bonus 3: the 'must be holding blue' clear ---\n");
    pin(0x80058B00, 0x90636597, "berry selector 0x800A6597 read at the handler's ENTRY");
    pin(0x80058B04, 0x24020001, "compared against 1 = blue");
    pin(0x80058B2C, 0x10620002, "equal -> skip the clear");
    pin(0x80058B34, 0xAF8004A8, "otherwise CLEAR");
    printf("       => this is NOT 'killing with the wrong berry resets it'. The clear\n"
           "          sits at the entry of the contact handler, so the streak is held\n"
           "          at 0 for as long as blue is not selected, hit or no hit.\n");

    printf("\n--- Bonus 3: the clear Canon does not mention ---\n");
    pin(0x80057428, 0xAF8004A8, "0x80057428, in the pool-reset routine 0x80057404");
    pin(0x80057418, 0x0C017DEB, "which memsets 0x800B0D18 for 3584 bytes first");
    pin(0x80057424, 0xAC20234C, "and clears 0x8008234C");
    {   /* housekeeping, not a player action: nothing guards it */
        uint32_t va; int branches = 0;
        for (va = 0x80057404u; va < 0x80057428u; va += 4) {
            uint32_t w = rdw(&g_exe, va), op = w >> 26, fn = w & 63;
            if (op == 1 || op == 2 || (op >= 4 && op <= 7)) branches++;
            if (op == 0 && (fn == 8 || fn == 9)) branches++;
        }
        claim(branches == 0, "unconditional within the routine -- a housekeeping reset");
    }
    printf("       => the B1 counter is NOT cleared here, so the two chains do not\n"
           "          share this reset.\n");
    {
        uint32_t va; int b1 = 0;
        for (va = 0x80057404u; va < 0x80057434u; va += 4)
            if (target_of(rdw(&g_exe, va)) == 0x8008223Cu) b1++;
        claim(b1 == 0, "confirmed: no write to 0x8008223C in that routine");
    }

    /* ------------------------------------------------------------ BONUS 2 -- */
    printf("\n");
    census(B2_SLOT0, B2_SLOT0 + 4, "Bonus 2 slots 0x80082248..4C", pcs, &ns, &nl, &no);
    claim(no == 0, "no overlay touches them");

    printf("\n--- Bonus 2: the slots are BYTES ---\n");
    {   /* every store into the five-byte window must be `sb`; if any is sh/sw the
         * five-identity reading is wrong and so is any tracer watching them */
        uint32_t va; int non_byte = 0, byte = 0;
        for (va = EXE_LOAD_VA; in_img(&g_exe, va); va += 4) {
            uint32_t w = rdw(&g_exe, va), a = target_of(w);
            if (a < B2_SLOT0 || a > B2_SLOT0 + 4 || !is_store(w)) continue;
            if ((w >> 26) == 0x28) byte++; else non_byte++;
        }
        printf("       byte stores %d, non-byte stores %d\n", byte, non_byte);
        claim(non_byte == 0, "EVERY store into the window is `sb` -- five 1-byte slots");
        claim(byte >= 5, "and there are at least five of them");
    }

    printf("\n--- Bonus 2: touching a mushroom already in the chain RESTARTS it ---\n");
    pin(0x8005C548, 0x240200FF, "v0 = 0xFF = the empty marker (-1 as a signed byte)");
    pin(0x8005C54C, 0xA39404B0, "slot0 := the identity just touched (gp+1200)");
    pin(0x8005C554, 0xA0222249, "slot1 := -1");
    pin(0x8005C55C, 0xA022224A, "slot2 := -1");
    pin(0x8005C564, 0xA022224B, "slot3 := -1");
    pin(0x8005C56C, 0xA022224C, "slot4 := -1");
    pin(0x8005C574, 0x24020071, "progress command 113 -- distinct from the 114..118 "
                                "of an accepted step");
    printf("       => a duplicate does NOT empty the chain, it restarts it at ONE.\n");

    printf("\n--- Bonus 2: appending a new identity ---\n");
    pin(0x8005C580, 0xA0342248, "sb s4, 0x80082248(at + slot index)");
    pin(0x8005C588, 0x24020071, "same progress command");

    /* Three separate blocks write all five slots. Naming only the interesting one
     * would repeat the failure this tool exists to catch, so both others are pinned
     * too and the arithmetic is checked: 3 blocks x 5 + 1 append == 16 stores. */
    printf("\n--- Bonus 2: the wipe, and what actually triggers it ---\n");
    /* CORRECTION. An earlier revision of this tool called 0x8005C06C "the earned
     * guard wipe". That is only the LAST of four independent entry conditions, and
     * not the one that matters in play: the first is being on the ground while not
     * touching a plant, which is the mechanism behind "five in a row". Naming a
     * shared exit block after the first guard that reaches it is a good way to
     * describe a rule backwards. */
    pin(0x8005BFF0, 0x06800008, "s4 < 0 (no plant in contact) -> s1 defaults to 5");
    pin(0x8005C01C, 0x84426582, "reads the GROUNDED flag 0x800A6582");
    pin(0x8005C024, 0x10400003, "airborne -> skip this test");
    pin(0x8005C02C, 0x1282000F, "GROUNDED and no plant in contact -> WIPE  <== the "
                                "'consecutive' rule");
    pin(0x8005C038, 0x1622000C, "plant type != 5 -> WIPE");
    pin(0x8005C04C, 0x10620007, "scene == 0x10 (inside the bonus stage) -> WIPE");
    pin(0x8005C064, 0x1040000A, "Bonus 2 already earned (flags & 0x10) -> WIPE");
    pin(0x8005C06C, 0xA38204B0, "the shared wipe: all five slots := 0xFF");
    printf("       => landing on the ground without a mushroom is what breaks the\n"
           "          chain. Verified live: the wipe runs at movie frames 0..40,\n"
           "          STOPS while Flik is airborne over the mushrooms, and resumes\n"
           "          at 239 -- the frame the operator reported landing.\n");

    printf("\n--- Bonus 2 DOES emit the progress burst, via a counting loop ---\n");
    /* SECOND CORRECTION. A previous revision concluded Bonus 2 wrote a constant 113
     * and could never pass the consumer's >= 115 gate. The 113 is real, but it is a
     * SEED: the very next block walks the five slots and increments the same word
     * once per occupied slot. Reading the store and its delay slot, and stopping
     * there, produced a confident wrong answer that the operator refuted. */
    pin(0x8005C660, 0xAF8206AC, "seed: [0x80082444] := 113");
    pin(0x8005C674, 0x80222248, "then walk slots 0..4 ...");
    pin(0x8005C67C, 0x10430005, "...skipping empty ones (-1)...");
    pin(0x8005C68C, 0x24420001, "...adding 1 per occupied slot...");
    pin(0x8005C690, 0xAF8206AC, "...and storing it back");
    printf("       => the command is 113 + occupied = 114..118 for chains of 1..5,\n"
           "          the same effective scheme as Bonus 1 and Bonus 3. Measured:\n"
           "          bounce 1 -> 114 (no burst), bounce 2 -> 115, bounce 3 -> 116.\n");

    printf("\n--- Bonus 2 completion is the progress word reaching 118 ---\n");
    pin(0x8005C6A0, 0x24020076, "v0 = 118");
    pin(0x8005C6AC, 0x1462000E, "progress != 118 -> not complete");
    pin(0x8005C6B8, 0xA42223A0, "118 -> transition latch 6");
    pin(0x8005C6CC, 0xA4222470, "fade 60 (Bonus 1 and 3 use 30)");
    pin(0x8005C6DC, 0xAC226530, "vertical speed -16384");
    pin(0x8005C6E4, 0xA0830000, "and flags |= 0x01");
    printf("       => the progress word doubles as the completion counter.\n");

    printf("\n--- Bonus 2: the init wipe ---\n");
    pin(0x8005BC80, 0x0C017DEB, "follows a memset call");
    pin(0x8005BC90, 0x240200FF, "v0 = 0xFF");
    pin(0x8005BC94, 0xA38204B0, "slot0 wiped (gp+1200)");
    pin(0x8005BCB8, 0x24020071, "and emits the seed 113");

    {   /* Count this heuristic's known sites; aliases remain outside its scope. */
        uint32_t va; int stores = 0;
        for (va = EXE_LOAD_VA; in_img(&g_exe, va); va += 4) {
            uint32_t w = rdw(&g_exe, va), a = target_of(w);
            if (a >= B2_SLOT0 && a <= B2_SLOT0 + 4 && is_store(w)) stores++;
        }
        claim(stores == 16,
              "scanner reports 16 known stores: three all-five blocks plus one append; "
              "this does not close pointer or variable-index aliases");
    }

    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) { printf("VERDICT: a pin failed -- do not bank anything above.\n"); return 1; }
    printf("VERDICT: every pin holds against the pristine image.\n");
    return 0;
}
