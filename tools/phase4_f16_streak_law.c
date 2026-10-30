/*
 * phase4_f16_streak_law.c -- what makes the Bonus-1 chain count, reset, or ignore.
 *
 * The operator's report: "killing enemies with the berry will reset the count, and I
 * believe one other action does too, but there are other things that will not reset
 * the count."  Three claims, one of which turns out to be slightly too narrow.  This
 * settles all three against the pristine image.
 *
 * RESOLVED DIRECT SITES.  The fixed gp/absolute-form scan reports eight direct
 * resident sites for 0x8008223C: one load, one increment, and six clears. An earlier
 * revision called that the complete whole-game domain. That was wrong: pointer-based
 * accesses and indirect calls are outside this scanner, so these are resolved sites,
 * not an exhaustive writer frontier.
 *
 * THE DECIDING STATE IS THE PLAYER'S, NOT THE ENEMY'S.  In the contact resolver
 * 0x8004ABF4, `s6` is set once at 0x8004AC78 to 0x800A6500 + 122 = 0x800A657A -- the
 * PLAYER struct.  Every `s6`-relative test in the streak region is therefore a test
 * of player state at the instant of contact.  This is why the row's old name
 * ("consecutive spider bounces") was a misreading of the fixture: nothing in the
 * code looks at which enemy it is.  The operator flagged exactly this.
 *
 * THE THREE-WAY CLASS TEST.  `sltiu` at 0x8004B2B4 is the crux and is easy to miss
 * as a plain comparison:
 *
 *     class = [0x800A6584]          ; player +0x84
 *     class >= 2  -> return, the counter is never touched      (does NOT reset)
 *     class == 1  -> count it                                  (the chain advances)
 *     class == 0  -> clear the counter                         (resets)
 *
 * So "some things reset it and some things don't" is not two rules but one field
 * with three outcomes.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_f16_streak_law.c \
 *      -o /tmp/f16law && /tmp/f16law
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
#define STREAK      0x8008223Cu
#define PLAYER      0x800A6500u

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

/* ------------------------------------------------------------------ helpers -- */

static int is_branch(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 63;
    if (op == 1 || op == 2 || op == 3 || (op >= 4 && op <= 7)) return 1;
    if (op == 0 && (fn == 8 || fn == 9)) return 1;   /* jr / jalr */
    return 0;
}

/* target of a conditional/relative branch, or 0 */
static uint32_t branch_target(uint32_t w, uint32_t pc)
{
    uint32_t op = w >> 26;
    if (op == 1 || (op >= 4 && op <= 7))
        return pc + 4 + (uint32_t)((int16_t)(w & 0xFFFF) * 4);
    if (op == 2 || op == 3) return ((w & 0x03FFFFFFu) << 2) | 0x80000000u;
    return 0;
}

/* An "unconditional" store is only unconditional if BOTH hold: no branch sits
 * between the entry and the store, AND nothing in the function jumps over it into
 * the middle.  Checking only the first is the classic way to get this wrong. */
static void prove_unconditional(uint32_t entry, uint32_t store, uint32_t fn_end,
                                const char *label)
{
    uint32_t va;
    int      branches = 0, jumps_past = 0;
    for (va = entry; va < store; va += 4)
        if (is_branch(rdw(&g_exe, va))) branches++;
    for (va = entry; va < fn_end; va += 4) {
        uint32_t t = branch_target(rdw(&g_exe, va), va);
        if (t > entry && t <= store) jumps_past++;
    }
    printf("  -- %s\n", label);
    claim(branches == 0, "    no branch between the function entry and the store");
    claim(jumps_past == 0, "    and nothing in the function branches over it");
}

/* ------------------------------------------------------------------- census -- */

/* Fixed gp-relative and displacement-form hits in each image. This does not resolve
 * runtime-computed bases, aliases, variable indexes, or callee effects. */
static void census(void)
{
    int loads = 0, stores = 0, ovl_hits = 0, i;
    uint32_t va;
    uint32_t inc_pc = 0, clear_pc[8];
    int      n_clear = 0;

    printf("=== resolved fixed-form counter sites over the EXE and %d overlays ===\n",
           n_ovl);
    for (va = EXE_LOAD_VA; in_img(&g_exe, va); va += 4) {
        uint32_t w = rdw(&g_exe, va), op = w >> 26, rs = (w >> 21) & 31;
        int32_t  s = (int16_t)(w & 0xFFFF);
        uint32_t a = 0;
        if (rs == 28) a = GP + (uint32_t)s;                 /* gp-relative */
        else if (op == 0x2B || op == 0x23) a = 0x80080000u + (uint32_t)s;
        else continue;
        if (a != STREAK) continue;
        if (op == 0x23) loads++;
        else if (op == 0x2B) {
            uint32_t rt = (w >> 16) & 31;
            stores++;
            if (rt == 0) { if (n_clear < 8) clear_pc[n_clear++] = va; }
            else inc_pc = va;
        }
    }
    for (i = 0; i < n_ovl; i++) {
        for (va = g_ovl[i].base; in_img(&g_ovl[i], va); va += 4) {
            uint32_t w = rdw(&g_ovl[i], va), op = w >> 26, rs = (w >> 21) & 31;
            int32_t  s = (int16_t)(w & 0xFFFF);
            uint32_t a = 0;
            /* $gp is NOT valid inside an overlay's own frame in the same way, but a
             * gp-relative access would still resolve here; check both anyway. */
            if (rs == 28) a = GP + (uint32_t)s;
            else if (op == 0x2B || op == 0x23) a = 0x80080000u + (uint32_t)s;
            else continue;
            if (a == STREAK) ovl_hits++;
        }
    }
    printf("  loads %d | stores %d (increment %d, clears %d) | overlay accesses %d\n",
           loads, stores, inc_pc ? 1 : 0, n_clear, ovl_hits);
    claim(loads == 1, "scanner resolves ONE direct read");
    claim(stores == 7, "scanner resolves SEVEN direct writes");
    claim(inc_pc == 0x8004B3A8u, "the single non-zero write is the increment 0x8004B3A8");
    claim(n_clear == 6, "and six resolved direct clears");
    claim(ovl_hits == 0, "no fixed-form direct overlay hit");
    printf("  clears:");
    for (i = 0; i < n_clear; i++) printf(" 0x%08" PRIx32, clear_pc[i]);
    printf("\n");
}

/* --------------------------------------------------------------------- main -- */

int main(void)
{
    int lvl;
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

    census();

    printf("\n=== A. the deciding state is the PLAYER's, not the enemy's ===\n");
    pin(0x8004AC1C, 0x24636500, "v1 = 0x800A6500, the player struct");
    pin(0x8004AC78, 0x2476007A, "s6 = v1 + 122 = 0x800A657A -- set ONCE, outside the "
                                "per-actor loop");
    {   /* if s6 were re-assigned inside the loop it could point at an enemy */
        uint32_t va; int writes = 0;
        for (va = 0x8004AC7Cu; va < 0x8004B6A8u; va += 4) {
            uint32_t w = rdw(&g_exe, va), op = w >> 26, fn = w & 63;
            uint32_t rd = (w >> 11) & 31, rt = (w >> 16) & 31;
            if (op == 0 && fn != 8 && fn != 9 && rd == 22) writes++;
            else if ((op == 0x08 || op == 0x09 || op == 0x23 || op == 0x0F) && rt == 22)
                writes++;
        }
        claim(writes == 0, "s6 is never reassigned inside the actor loop, so every "
                           "s6-relative test below reads PLAYER state");
    }
    printf("       => nothing in the streak logic looks at WHICH enemy it is.\n"
           "          The row name \"consecutive spider bounces\" described the\n"
           "          fixture, not the rule.\n");

    printf("\n=== B. the three-way class test (0x800A6584 = player +0x84) ===\n");
    pin(0x8004B2AC, 0x96C2000A, "lhu v0,10(s6) -- class = [0x800A6584]");
    pin(0x8004B2B4, 0x2C420002, "sltiu v0,v0,2  <- THE crux instruction");
    pin(0x8004B2B8, 0x104000F0, "class >= 2 -> branch to the function tail 0x8004B67C");
    claim(0x8004B2B8u + 4 + (uint32_t)((int16_t)0x00F0 * 4) == 0x8004B67Cu,
          "  ...and that tail is past every write to the counter -- class >= 2 "
          "NEITHER counts NOR resets");
    pin(0x8004B31C, 0x86C2000A, "class re-read");
    pin(0x8004B324, 0x1440000D, "class != 0 -> 0x8004B35C, the counting block");
    pin(0x8004B350, 0xAF8004A4, "class == 0 falls through to here: CLEAR");
    printf("       => one field, three outcomes: >=2 ignore, ==1 count, ==0 reset.\n");

    printf("\n=== C. the other contact-time resets (0x8004B1D4) ===\n");
    pin(0x8004B19C, 0x86C30000, "lh v1,0(s6)  = [0x800A657A], the carried-object gate");
    pin(0x8004B1A4, 0x1062000B, "== 12 -> CLEAR");
    pin(0x8004B1AC, 0x96C20016, "lhu v0,22(s6) = [0x800A6590], the power word");
    pin(0x8004B1B4, 0x30420080, "andi 0x80");
    pin(0x8004B1B8, 0x14400006, "bit 0x80 set -> CLEAR");
    pin(0x8004B1C0, 0x86C3000E, "lh v1,14(s6) = [0x800A6588], the mode/anim index");
    pin(0x8004B1C8, 0x14620038, "mode != 13 -> the class path; mode == 13 falls into...");
    pin(0x8004B1D4, 0xAF8004A4, "...CLEAR");

    printf("\n=== D. throwing a berry resets it -- and it is the THROW, not the kill ===\n");
    pin(0x800470D8, 0xAC20223C, "clear at 0x800470D8, inside berry_throw_dispatch");
    prove_unconditional(0x800470ACu, 0x800470D8u, 0x80047284u,
                        "0x800470AC .. 0x800470D8 (function entry -> the clear)");
    pin(0x80049088, 0x2402000A, "its ONLY caller tests the berry action state == 10");
    pin(0x80049094, 0x0C011C2B, "and calls 0x800470AC");
    printf("       Canon SYS_berry_projectile_and_homing: the player writes action\n"
           "       state 18, and the sole berry CONSTRUCTOR call happens when the\n"
           "       state reaches 10.  The clear is at the constructor's entry and is\n"
           "       reached before anything can hit anything.\n"
           "       PREDICTION (falsifiable): throw a berry at empty air with a live\n"
           "       chain and the chain still dies.\n");

    printf("\n=== E. the resets that are not player actions ===\n");
    pin(0x8004A6C4, 0xAF8004A4, "0x8004A6C4 in object_slot_type_init");
    prove_unconditional(0x8004A6C4u - 4, 0x8004A6C4u, 0x8004A700u,
                        "reached straight off the 64-actor loop exit");
    pin(0x8004A854, 0xAF8004A4, "0x8004A854 in resident_level_transition_initiator");
    printf("       => the chain does not survive a level load or a transition.\n");

    printf("\n=== F. the counting block's own guards ===\n");
    pin(0x8004B36C, 0x30820020, "andi a0,0x20 -- the already-earned guard");
    pin(0x8004B370, 0x144000C2, "earned -> skip");
    pin(0x8004B374, 0x24020010, "v0 = 0x10");
    pin(0x8004B384, 0x106200BD, "scene == 0x10 (inside the bonus stage) -> skip");
    pin(0x8004B394, 0x24430001, "v1 = count + 1");
    pin(0x8004B398, 0x24420072, "v0 = count + 114 -- the progress command");
    pin(0x8004B3A4, 0x24020005, "the threshold is 5");
    pin(0x8004B3AC, 0x146200B3, "count+1 != 5 -> stop here");
    pin(0x8004B3B0, 0x34820002, "the fifth ORs low bit 0x02 into the bonus flags");
    pin(0x8004B3C0, 0xA42223A0, "sets transition latch 6");
    pin(0x8004B3D0, 0xAF8004A4, "and resets the counter");

    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) { printf("VERDICT: a pin failed -- do not bank anything above.\n"); return 1; }
    printf("VERDICT: every pin holds against the pristine image.\n");
    return 0;
}
