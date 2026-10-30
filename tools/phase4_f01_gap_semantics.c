/* phase4_f01_gap_semantics.c -- instruction-derived semantics for the
 * remaining unevidenced census gaps: the atan table, the sine-table tail, and
 * function-entry-pointer runs.
 *
 * Everything decisive is read from the pinned image:
 *
 *  1. ATAN TABLE. `atan2_heading` (0x80060854..) indexes a halfword table:
 *       sll v0, a0, 1 ; lui at, 0x8008 ; addu at, at, v0 ; lh v1, -0x181C(at)
 *     twice (both octant paths), with the index built as (min << 10) / maj
 *     (sll 10 then div; min <= maj by the octant selection), so the index
 *     domain is 0..1024 and the table is the 1,025 s16 entries at
 *     0x8007E7E4..0x8007EFE6. The fold constants 0x400 (90 deg) and 0x800
 *     (180 deg) confirm PSX angle units (4096 = 360 deg). This probe VERIFIES
 *     every one of those instruction words before claiming the extent.
 *     Content: compared against llround(atan2(k,1024)*4096/(2*pi)). The match
 *     is NOT exact -- a fixed set of entries sits exactly +1 above the
 *     analytic model (a build-time generator artifact; no uniform multiplier
 *     reproduces it, established by interval intersection) -- so the content
 *     model is reported as APPROXIMATE with the exact deviation histogram,
 *     and the extent claim rests on the instruction derivation alone.
 *
 *  2. SINE TAIL. The already-content-verified table at 0x80074970
 *     (llround(16384*sin(2*pi*i/4096)), 5,120 entries, ends 0x80077170)
 *     overlaps a third census gap at 0x80077080. The overlap entries are
 *     re-derived here and must match EXACTLY.
 *
 *  3. ENTRY-POINTER RUNS. Given the exact census entry set and a list of
 *     unevidenced ranges, report every run of >= 3 consecutive aligned words
 *     whose values are all census code/thunk entries. With ~1,000 entries in
 *     a 512 MiB address space the per-word false-positive rate is ~0.2%, so
 *     a >=3 run is ~1e-8 by chance; the model is stated, not hidden.
 *
 * usage: phase4_f01_gap_semantics <image> <base_hex> <entries_file> <ranges_file>
 *   entries_file: one hex address per line (census code/thunk entries)
 *   ranges_file:  "start_hex end_hex" per line (unevidenced ranges)
 * Output: JSON on stdout. Exit 0 on a well-formed run; the JSON is the finding.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static uint8_t *g_img;
static long g_len;
static uint32_t g_base;

static uint32_t word_at(uint32_t va)
{
    long off = (long)va - (long)g_base;
    if (off < 0 || off + 4 > g_len) { fprintf(stderr, "va outside image\n"); exit(2); }
    uint32_t v;
    memcpy(&v, g_img + off, 4);
    return v;
}
static int16_t half_at(uint32_t va)
{
    long off = (long)va - (long)g_base;
    if (off < 0 || off + 2 > g_len) { fprintf(stderr, "va outside image\n"); exit(2); }
    int16_t v;
    memcpy(&v, g_img + off, 2);
    return v;
}

/* ---- 1. the atan reader's indexing instructions, verified word by word --- */
typedef struct { uint32_t pc, expect; const char *what; } Check;
static const Check ATAN_CHECKS[] = {
    { 0x80060B9C, 0x00041040, "sll v0, a0, 1        (index * 2: halfword entries)" },
    { 0x80060BA0, 0x3C018008, "lui at, 0x8008       (table upper half)" },
    { 0x80060BA4, 0x00220821, "addu at, at, v0" },
    { 0x80060BA8, 0x8423E7E4, "lh v1, -0x181C(at)   (base 0x8007E7E4, s16)" },
    { 0x80060BF4, 0x00051280, "sll v0, a1, 10       (min << 10)" },
    { 0x80060BF8, 0x0044001A, "div v0, a0           (... / maj -> index 0..1024)" },
    { 0x80060C28, 0x00041040, "sll v0, a0, 1        (second octant path)" },
    { 0x80060C2C, 0x3C018008, "lui at, 0x8008" },
    { 0x80060C30, 0x00220821, "addu at, at, v0" },
    { 0x80060C34, 0x8423E7E4, "lh v1, -0x181C(at)" },
    { 0x80060C38, 0x24020400, "addiu v0, zero, 0x400 (90-degree fold: PSX 4096=360)" },
    { 0x80060C44, 0x24020800, "addiu v0, zero, 0x800 (180-degree fold)" },
};
#define ATAN_BASE 0x8007E7E4u
#define ATAN_ENTRIES 1025

static void emit_atan(void)
{
    int all_ok = 1;
    printf(" \"atan_table\": {\n  \"reader\": \"atan2_heading\",\n");
    printf("  \"instruction_checks\": [\n");
    for (size_t i = 0; i < sizeof ATAN_CHECKS / sizeof ATAN_CHECKS[0]; i++) {
        uint32_t w = word_at(ATAN_CHECKS[i].pc);
        int ok = w == ATAN_CHECKS[i].expect;
        if (!ok) all_ok = 0;
        printf("   {\"pc\":\"0x%08X\",\"expect\":\"0x%08X\",\"actual\":\"0x%08X\","
               "\"ok\":%s,\"what\":\"%s\"}%s\n",
               ATAN_CHECKS[i].pc, ATAN_CHECKS[i].expect, w, ok ? "true" : "false",
               ATAN_CHECKS[i].what,
               i + 1 < sizeof ATAN_CHECKS / sizeof ATAN_CHECKS[0] ? "," : "");
    }
    printf("  ],\n  \"all_instructions_verified\": %s,\n", all_ok ? "true" : "false");
    printf("  \"base\": \"0x%08X\", \"entries\": %d, \"entry_width\": 2,\n",
           ATAN_BASE, ATAN_ENTRIES);
    printf("  \"extent\": [\"0x%08X\", \"0x%08X\"],\n",
           ATAN_BASE, ATAN_BASE + 2 * ATAN_ENTRIES);
    printf("  \"index_domain\": \"0..1024 = (min<<10)/maj with min <= maj by octant selection\",\n");

    long exact = 0, plus_one = 0, other = 0;
    int first_other = -1;
    for (int k = 0; k < ATAN_ENTRIES; k++) {
        double model = atan2((double)k, 1024.0) * 4096.0 / (2.0 * M_PI);
        long expect = llround(model);
        int16_t actual = half_at(ATAN_BASE + 2u * (uint32_t)k);
        long d = (long)actual - expect;
        if (d == 0) exact++;
        else if (d == 1) plus_one++;
        else { other++; if (first_other < 0) first_other = k; }
    }
    printf("  \"content_model\": \"llround(atan2(k,1024)*4096/(2*pi))\",\n");
    printf("  \"content_model_exact\": %s,\n", (plus_one == 0 && other == 0) ? "true" : "false");
    printf("  \"deviation_histogram\": {\"0\": %ld, \"+1\": %ld, \"other\": %ld},\n",
           exact, plus_one, other);
    printf("  \"first_other_deviation_entry\": %d,\n", first_other);
    printf("  \"extent_claim_basis\": \"instruction derivation ONLY; the analytic "
           "content model is approximate (+1 on a fixed entry subset, generator "
           "unknown, no uniform multiplier fits by interval intersection) and is "
           "reported as corroboration, never as the claim\"\n },\n");
}

/* ---- 2. the sine tail over the third gap, exact or nothing -------------- */
#define SIN_BASE 0x80074970u
#define SIN_ENTRIES 5120
#define SIN_GAP_LO 0x80077080u
#define SIN_TABLE_END (SIN_BASE + 2u * SIN_ENTRIES)

static void emit_sine_tail(void)
{
    long mism = 0;
    int first = -1;
    int k_lo = (int)((SIN_GAP_LO - SIN_BASE) / 2);
    for (int k = k_lo; k < SIN_ENTRIES; k++) {
        long expect = llround(16384.0 * sin(2.0 * M_PI * (double)k / 4096.0));
        int16_t actual = half_at(SIN_BASE + 2u * (uint32_t)k);
        if ((long)actual != expect) { mism++; if (first < 0) first = k; }
    }
    printf(" \"sine_tail\": {\n");
    printf("  \"table_base\": \"0x%08X\", \"table_end\": \"0x%08X\",\n", SIN_BASE, SIN_TABLE_END);
    printf("  \"formula\": \"llround(16384*sin(2*pi*i/4096))\",\n");
    printf("  \"gap_overlap\": [\"0x%08X\", \"0x%08X\"],\n", SIN_GAP_LO, SIN_TABLE_END);
    printf("  \"entries_checked\": %d, \"mismatched_entries\": %ld, "
           "\"first_mismatch\": %d,\n", SIN_ENTRIES - k_lo, mism, first);
    printf("  \"content_model_exact\": %s\n },\n", mism == 0 ? "true" : "false");
}

/* ---- 3. entry-pointer runs over the given unevidenced ranges ------------ */
static uint32_t *g_entries;
static size_t g_n_entries;

static int is_entry(uint32_t v)
{
    size_t lo = 0, hi = g_n_entries;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        if (g_entries[mid] < v) lo = mid + 1;
        else hi = mid;
    }
    return lo < g_n_entries && g_entries[lo] == v;
}

static void emit_runs(FILE *ranges)
{
    printf(" \"entry_pointer_runs\": [\n");
    int first_row = 1;
    long covered = 0;
    uint32_t lo, hi;
    while (fscanf(ranges, "%x %x", &lo, &hi) == 2) {
        uint32_t start = (lo + 3u) & ~3u;
        uint32_t run_lo = 0;
        int run = 0;
        for (uint32_t pc = start; pc <= hi; pc += 4) {
            int member = pc + 4 <= hi && is_entry(word_at(pc));
            if (member) {
                if (!run) run_lo = pc;
                run++;
            }
            if ((!member || pc + 4 > hi) && run) {
                if (run >= 3) {
                    printf("%s  {\"start\":\"0x%08X\",\"end\":\"0x%08X\","
                           "\"entries\":%d}",
                           first_row ? "" : ",\n", run_lo, run_lo + 4u * (uint32_t)run, run);
                    first_row = 0;
                    covered += 4L * run;
                }
                run = 0;
            }
        }
    }
    printf("\n ],\n \"entry_pointer_run_bytes\": %ld,\n", covered);
    printf(" \"entry_pointer_model\": \"runs of >=3 consecutive aligned words, each "
           "exactly a census code/thunk entry; ~1e-8 chance per run under a "
           "uniform-random model with ~1e3 entries over the RAM space\"\n");
}

int main(int argc, char **argv)
{
    if (argc != 5) {
        fprintf(stderr, "usage: %s <image> <base_hex> <entries_file> <ranges_file>\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); g_len = ftell(f); fseek(f, 0, SEEK_SET);
    g_img = malloc((size_t)g_len);
    if (!g_img || fread(g_img, 1, (size_t)g_len, f) != (size_t)g_len) return 2;
    fclose(f);
    g_base = (uint32_t)strtoul(argv[2], NULL, 16);

    FILE *ef = fopen(argv[3], "r");
    if (!ef) { perror(argv[3]); return 2; }
    size_t cap = 4096;
    g_entries = malloc(cap * sizeof *g_entries);
    uint32_t v;
    while (fscanf(ef, "%x", &v) == 1) {
        if (g_n_entries == cap) { cap *= 2; g_entries = realloc(g_entries, cap * sizeof *g_entries); }
        g_entries[g_n_entries++] = v;
    }
    fclose(ef);
    /* insertion sort is fine at this size; the entries file is pre-sorted by
     * the driver anyway and this guards against a caller that forgets */
    for (size_t i = 1; i < g_n_entries; i++) {
        uint32_t key = g_entries[i];
        size_t j = i;
        while (j > 0 && g_entries[j - 1] > key) { g_entries[j] = g_entries[j - 1]; j--; }
        g_entries[j] = key;
    }

    FILE *rf = fopen(argv[4], "r");
    if (!rf) { perror(argv[4]); return 2; }

    printf("{\n");
    emit_atan();
    emit_sine_tail();
    emit_runs(rf);
    printf("}\n");
    fclose(rf);
    return 0;
}
