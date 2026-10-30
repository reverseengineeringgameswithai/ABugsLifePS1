/*
 * phase4_e16_bound_hint_counterexample.c -- a proven-false EXCLUDED_OUT_OF_BOUND.
 *
 * WHAT THIS PINS
 * --------------
 * tools/region_provenance.c's Tier 3 exclusion (EXCLUDED_OUT_OF_BOUND) reads a
 * loop's own bounds check out of the disassembly and proves the index needed to
 * reach a target is beyond it. Its header discloses the assumption this rests
 * on: "the detected comparison genuinely gates the index at the region's
 * formation point, not just 'a comparison against this register happened
 * somewhere'".
 *
 * That assumption FAILS at 0x8003BF48, and this tool proves it from the pristine
 * bytes -- independently of region_provenance.c, so the two are not the same
 * implementation agreeing with itself.
 *
 * The site (LEVEL.RAW loader, registering a chunk pointer by subtype marker):
 *
 *      0x8003BF30  addiu $v0, $s4, -48        # marker - 0x30
 *      0x8003BF34  sltiu $v0, $v0, 40         # gate: (marker-0x30) < 40
 *      0x8003BF38  beq   $v0, $zero, ...      #   -> marker in [48, 87]
 *      0x8003BF3C  sll   $v0, $s4, 2          # INDEX IS THE RAW MARKER
 *      0x8003BF40  lui   $at, 0x800A
 *      0x8003BF44  addu  $at, $at, $v0
 *      0x8003BF48  sw    $s3, -19224($at)     # EA = 0x8009B4E8 + marker*4
 *
 * So the reachable address set is 0x8009B5A8 .. 0x8009B644, and index 48 (the
 * first slot) is IN range. region_provenance.c instead reports
 * `idx_bound: 32`, excluding index 48 as out of bound. 32 is the immediate of
 * the ONLY slti/sltiu applied directly to $s4 anywhere in the function --
 * `slti $v0, $s4, 32` at 0x8003A4F4, roughly 7 KB earlier, which is the loader's
 * class split (marker < 32 = texture page). On the path that reaches 0x8003BF48
 * that branch went the OTHER way, so it bounds the index from BELOW, not above.
 *
 * The exclusion is therefore not merely imprecise, it is WRONG, and independent
 * runtime evidence says so: analysis/phase4_e16_table_read_watch.json records
 * this exact PC writing that exact window 36 times in one replay.
 *
 * WHAT THIS TOOL CHECKS (each fails loudly rather than being asserted in prose):
 *   1. the seven instructions above are the pristine bytes at those addresses;
 *   2. the gate is on a DERIVED value (s4-48), not on s4;
 *   3. the index feeding the region is the RAW s4;
 *   4. `slti $v0,$s4,32` at 0x8003A4F4 is the only slti/sltiu applied directly
 *      to $s4 in the whole loader -- i.e. the only possible source of "32";
 *   5. the target index 48 lies INSIDE the gate's true range [48, 87].
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/e16bh tools/phase4_e16_bound_hint_counterexample.c
 * Usage: /tmp/e16bh SCUS_942.88
 * Output: JSON on stdout; exit 1 if any check fails.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TEXT_VADDR 0x80010000u
#define HDR        0x800

#define LOADER_LO  0x8003A318u
#define LOADER_HI  0x8003BF4Cu
#define STORE_PC   0x8003BF48u
#define CLASS_PC   0x8003A4F4u
#define TABLE_BASE 0x8009B4E8u        /* 0x800A0000 - 19224 */

static uint8_t *img; static long ilen;

static uint32_t rd(uint32_t pc)
{
    long off = HDR + (long)(pc - TEXT_VADDR);
    uint32_t v;
    if (off < 0 || off + 4 > ilen) { fprintf(stderr, "pc 0x%08x out of image\n", pc); exit(2); }
    memcpy(&v, img + off, 4);
    return v;
}

static int fail;
static void check(const char *name, int ok)
{
    if (!ok) fail = 1;
    printf("  {\"check\":\"%s\",\"ok\":%s},\n", name, ok ? "true" : "false");
}

int main(int argc, char **argv)
{
    if (argc != 2) { fprintf(stderr, "usage: %s SCUS_942.88\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); ilen = ftell(f); fseek(f, 0, SEEK_SET);
    img = malloc(ilen);
    if (!img || fread(img, 1, ilen, f) != (size_t)ilen) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    printf("{\n \"target\":\"0x%08x\",\n \"claim\":\"region_provenance.c reports "
           "EXCLUDED_OUT_OF_BOUND with idx_bound 32 for a site whose true index range "
           "is [48,87] and which runtime evidence shows firing 36 times\",\n"
           " \"checks\":[\n", STORE_PC);

    uint32_t sub  = rd(STORE_PC - 0x18);   /* addiu v0, s4, -48  */
    uint32_t gate = rd(STORE_PC - 0x14);   /* sltiu v0, v0, 40   */
    uint32_t sll  = rd(STORE_PC - 0x0C);   /* sll  v0, s4, 2     */
    uint32_t lui  = rd(STORE_PC - 0x08);   /* lui  at, 0x800A    */
    uint32_t addu = rd(STORE_PC - 0x04);   /* addu at, at, v0    */
    uint32_t sw   = rd(STORE_PC);          /* sw   s3, -19224(at)*/

    /* 1. pristine bytes */
    check("addiu_v0_s4_minus48", sub == 0x2682FFD0u);
    check("sltiu_v0_v0_40",      gate == 0x2C420028u);
    check("sll_v0_s4_2",         sll  == 0x00141080u);
    check("lui_at_0x800A",       lui  == 0x3C01800Au);
    check("addu_at_at_v0",       addu == 0x00220821u);
    check("sw_s3_m19224_at",     sw   == 0xAC33B4E8u);

    /* 2. the gate tests a DERIVED value, not s4 itself */
    check("gate_operand_is_not_s4", ((gate >> 21) & 31) != 20);
    check("gate_operand_is_the_sub_result",
          ((gate >> 21) & 31) == ((sub >> 16) & 31));

    /* 3. the index feeding the region is the RAW s4 */
    check("index_register_is_raw_s4", ((sll >> 16) & 31) == 20);

    /* 4. the only slti/sltiu applied DIRECTLY to $s4 in the loader is at 0x8003A4F4,
     *    and its immediate is 32 -- the sole possible source of the reported bound. */
    int direct_s4_cmps = 0; uint32_t only_pc = 0, only_imm = 0;
    for (uint32_t pc = LOADER_LO; pc < LOADER_HI; pc += 4) {
        uint32_t w = rd(pc), op = w >> 26, rs = (w >> 21) & 31;
        if ((op == 0x0A || op == 0x0B) && rs == 20) {
            direct_s4_cmps++; only_pc = pc; only_imm = w & 0xFFFF;
        }
    }
    check("exactly_one_direct_s4_comparison", direct_s4_cmps == 1);
    check("it_is_the_class_split_at_0x8003A4F4", only_pc == CLASS_PC);
    check("its_immediate_is_32_the_reported_bound", only_imm == 32);
    check("class_split_is_far_from_the_store", (STORE_PC - CLASS_PC) > 0x1000);

    /* 5. the target index is INSIDE the true range, so the exclusion is false. */
    int32_t idx_lo = 48, idx_hi = 87;                 /* from sltiu(s4-48) < 40 */
    uint32_t reach_lo = TABLE_BASE + (uint32_t)idx_lo * 4;
    uint32_t reach_hi = TABLE_BASE + (uint32_t)idx_hi * 4;
    int32_t target_idx = 48;
    check("target_index_48_is_within_true_bounds",
          target_idx >= idx_lo && target_idx <= idx_hi);
    check("reachable_window_is_0x8009B5A8_0x8009B644",
          reach_lo == 0x8009B5A8u && reach_hi == 0x8009B644u);
    check("reported_bound_32_is_below_the_true_minimum_48", 32 < idx_lo);

    printf("  {\"check\":\"__summary__\",\"ok\":%s}\n ],\n", fail ? "false" : "true");
    printf(" \"true_index_range\":[%d,%d],\n \"true_reachable_window\":[\"0x%08x\",\"0x%08x\"],\n"
           " \"reported_idx_bound\":32,\n \"verdict\":\"%s\"\n}\n",
           idx_lo, idx_hi, reach_lo, reach_hi,
           fail ? "CHECKS FAILED -- do not rely on this counterexample"
                : "EXCLUDED_OUT_OF_BOUND is UNSOUND here: a comparison that gates the "
                  "opposite branch, 7 KB away, was used as an upper bound on an index "
                  "whose true range starts above it");
    free(img);
    return fail ? 1 : 0;
}
