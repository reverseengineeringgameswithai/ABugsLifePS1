/* text_coverage_audit -- how much of the resident text does the function census
 * actually cover, and how much of what it misses is REACHED CODE?
 *
 * WHY THIS EXISTS
 * ---------------
 * Every static residual figure this project produces -- region censuses, bound
 * recovery, frontier compilation -- is computed over the functions listed in
 * analysis/functions_resident.txt. Nothing had ever measured what that list
 * leaves out, so "we scanned every function" silently meant "we scanned every
 * function we had listed".
 *
 * It cost a real false negative. An E16 campaign movie caught 0x80010BF4 reading
 * an E16 table window; that address is in NO listed function. The entry
 *
 *     0x80010000 724 per_object_mesh_draw_payload_emitter
 *
 * ends at 0x800102D4 -- and 0x80010C88 is `j 0x800102D4`, the head of the loop
 * that contains the access. The emitter's entire main body sits in an 11,828-byte
 * hole, and every static pass walked straight past it.
 *
 * WHAT IT DECIDES
 * ---------------
 * A gap is not automatically a problem: the segment holds jump tables, constant
 * pools and padding as well as code. The discriminator used here is REACHABILITY:
 * if a listed function transfers control directly into a gap (j / jal / a
 * conditional branch), that gap is code the census dropped -- a truncated
 * function -- and any "we scanned everything" claim over that region is void.
 * Gaps nothing branches into are reported separately and left as candidates.
 *
 * This under-counts rather than over-counts: it follows only DIRECT transfers, so
 * code reached solely through `jr` (jump tables, function pointers) is scored as
 * unreferenced. Reported gap-code is therefore a floor, never an inflation.
 *
 * SELF-VERIFICATION
 * -----------------
 * Refuses to run unless the PSX-EXE header declares t_addr 0x80010000 and the two
 * pinned instructions below still decode as expected in the image handed to it.
 * A shifted or edited image fails loudly instead of producing plausible numbers.
 *
 * Build:  cc -O2 -Wall -Wextra -Werror -o /tmp/tca tools/text_coverage_audit.c
 * Usage:  /tmp/tca SCUS_942.88 analysis/functions_resident.txt [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO 0x80010000u
#define TEXT_HI 0x80082800u
#define HDR     0x800u
#define MAXFN   4096
#define MAXGAP  1024

struct fn { uint32_t addr, size; char name[96]; };
struct gap {
    uint32_t start, size;
    uint32_t entries;          /* direct transfers landing inside */
    uint32_t first_src;        /* a sample source PC */
    uint32_t first_dst;
    uint32_t zero_words;       /* how much of it is 0x00000000 */
    uint32_t total_words;
};

static uint8_t *img;
static long img_len;

static uint32_t rd32(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (off < 0 || off + 4 > img_len) return 0;
    return (uint32_t)img[off] | ((uint32_t)img[off + 1] << 8) |
           ((uint32_t)img[off + 2] << 16) | ((uint32_t)img[off + 3] << 24);
}

/* Direct-transfer target of one instruction, or 0 if it is not a direct branch. */
static uint32_t transfer_target(uint32_t pc, uint32_t w)
{
    uint32_t op = w >> 26;
    if (op == 2u || op == 3u)                       /* j / jal */
        return ((pc + 4u) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
    if (op == 1u || (op >= 4u && op <= 7u) ||       /* regimm, beq/bne/blez/bgtz */
        (op >= 0x14u && op <= 0x17u))               /* the *l likely variants */
        return pc + 4u + (uint32_t)((int32_t)(int16_t)(w & 0xFFFFu) * 4);
    return 0u;
}

static int cmp_fn(const void *a, const void *b)
{
    uint32_t x = ((const struct fn *)a)->addr, y = ((const struct fn *)b)->addr;
    return x < y ? -1 : x > y ? 1 : 0;
}

static int cmp_gap_size(const void *a, const void *b)
{
    uint32_t x = ((const struct gap *)a)->size, y = ((const struct gap *)b)->size;
    return x > y ? -1 : x < y ? 1 : 0;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <exe> <functions.txt> [--json out]\n", argv[0]);
        return 2;
    }
    const char *jsonout = NULL;
    for (int i = 3; i < argc; i++)
        if (!strcmp(argv[i], "--json") && i + 1 < argc) jsonout = argv[++i];

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); img_len = ftell(f); fseek(f, 0, SEEK_SET);
    img = malloc((size_t)img_len);
    if (!img || fread(img, 1, (size_t)img_len, f) != (size_t)img_len) {
        fprintf(stderr, "read failed\n"); return 2;
    }
    fclose(f);

    /* --- self-verification against the pristine image ------------------- */
    if (img_len < (long)HDR + 16 || memcmp(img, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PSX-EXE\n"); return 2;
    }
    uint32_t t_addr = (uint32_t)img[0x18] | ((uint32_t)img[0x19] << 8) |
                      ((uint32_t)img[0x1A] << 16) | ((uint32_t)img[0x1B] << 24);
    if (t_addr != TEXT_LO) {
        fprintf(stderr, "t_addr 0x%08X != 0x%08X -- wrong image\n", t_addr, TEXT_LO);
        return 2;
    }
    /* pin 1: the emitter loop back-edge that exposed the hole.
     * pin 2: the hoisted load itself. */
    if (rd32(0x80010C88u) != 0x080040B5u || rd32(0x80010BF4u) != 0x97390000u) {
        fprintf(stderr, "pinned instructions do not match; image is not the one this "
                        "tool was written against\n");
        return 2;
    }

    /* --- function list -------------------------------------------------- */
    FILE *g = fopen(argv[2], "r");
    if (!g) { perror(argv[2]); return 2; }
    static struct fn fns[MAXFN];
    int nf = 0;
    char line[512];
    while (fgets(line, sizeof line, g) && nf < MAXFN) {
        if (line[0] == '#' || line[0] == '\n') continue;
        uint32_t a, n; char nm[96] = {0};
        if (sscanf(line, "%x %u %95s", &a, &n, nm) < 2) continue;
        if (a < TEXT_LO || a >= TEXT_HI) continue;
        fns[nf].addr = a; fns[nf].size = n;
        snprintf(fns[nf].name, sizeof fns[nf].name, "%s", nm);
        nf++;
    }
    fclose(g);
    qsort(fns, (size_t)nf, sizeof fns[0], cmp_fn);

    /* --- gaps ------------------------------------------------------------ */
    static struct gap gaps[MAXGAP];
    int ng = 0;
    uint32_t cur = TEXT_LO;
    for (int i = 0; i < nf; i++) {
        if (fns[i].addr > cur && ng < MAXGAP) {
            gaps[ng].start = cur; gaps[ng].size = fns[i].addr - cur; ng++;
        }
        uint32_t end = fns[i].addr + fns[i].size;
        if (end > cur) cur = end;
    }
    if (cur < TEXT_HI && ng < MAXGAP) {
        gaps[ng].start = cur; gaps[ng].size = TEXT_HI - cur; ng++;
    }

    /* --- reachability: direct transfers from listed code into a gap ------ */
    for (int i = 0; i < nf; i++) {
        for (uint32_t pc = fns[i].addr; pc < fns[i].addr + fns[i].size; pc += 4) {
            uint32_t t = transfer_target(pc, rd32(pc));
            if (t < TEXT_LO || t >= TEXT_HI) continue;
            for (int k = 0; k < ng; k++) {
                if (t >= gaps[k].start && t < gaps[k].start + gaps[k].size) {
                    if (!gaps[k].entries) { gaps[k].first_src = pc; gaps[k].first_dst = t; }
                    gaps[k].entries++;
                    break;
                }
            }
        }
    }

    /* "Reached by a branch" is necessary but NOT sufficient for calling a gap
     * code. The largest one (0x8007E8B8, 13,536 B) is 58.6% zero words and sits
     * directly below $gp = 0x80081D98 -- it is the small-data region, and the
     * transfers "into" it decode out of data. Measure the zero content so the
     * headline cannot overstate how much real code was dropped. */
    for (int k = 0; k < ng; k++)
        for (uint32_t p = gaps[k].start; p < gaps[k].start + gaps[k].size; p += 4) {
            gaps[k].total_words++;
            if (rd32(p) == 0u) gaps[k].zero_words++;
        }

    uint64_t total_gap = 0, code_gap = 0, quiet_gap = 0, code_zero = 0, dense_gap = 0;
    int n_code = 0, n_dense = 0;
    for (int k = 0; k < ng; k++) {
        total_gap += gaps[k].size;
        if (gaps[k].entries) {
            code_gap += gaps[k].size; n_code++;
            code_zero += (uint64_t)gaps[k].zero_words * 4;
            if (gaps[k].total_words &&
                gaps[k].zero_words * 2 < gaps[k].total_words) {
                dense_gap += gaps[k].size; n_dense++;
            }
        }
        else quiet_gap += gaps[k].size;
    }
    uint32_t text = TEXT_HI - TEXT_LO;

    printf("text segment      : 0x%08X..0x%08X  %u bytes\n", TEXT_LO, TEXT_HI, text);
    printf("listed functions  : %d covering %llu bytes (%.1f%%)\n", nf,
           (unsigned long long)(text - total_gap), 100.0 * (double)(text - total_gap) / text);
    printf("uncovered         : %llu bytes in %d gaps (%.1f%%)\n",
           (unsigned long long)total_gap, ng, 100.0 * (double)total_gap / text);
    printf("  reached by direct transfer (DROPPED CODE): %llu bytes in %d gaps\n",
           (unsigned long long)code_gap, n_code);
    printf("  never branched into (data/padding candidates): %llu bytes in %d gaps\n",
           (unsigned long long)quiet_gap, ng - n_code);
    printf("  ... of the reached bytes, %llu (%.1f%%) are ZERO words; %llu bytes in %d "
           "gaps are majority non-zero and are the real dropped code\n",
           (unsigned long long)code_zero,
           code_gap ? 100.0 * (double)code_zero / (double)code_gap : 0.0,
           (unsigned long long)dense_gap, n_dense);

    static struct gap sorted_gaps[MAXGAP];
    memcpy(sorted_gaps, gaps, sizeof gaps);
    qsort(sorted_gaps, (size_t)ng, sizeof sorted_gaps[0], cmp_gap_size);
    printf("\nlargest gaps:\n");
    for (int k = 0; k < ng && k < 10; k++) {
        struct gap *G = &sorted_gaps[k];
        printf("  0x%08X +%-6u  %s", G->start, G->size,
               G->entries ? "CODE" : "quiet");
        if (G->entries)
            printf(" (%u direct transfers in, e.g. 0x%08X -> 0x%08X)",
                   G->entries, G->first_src, G->first_dst);
        printf("\n");
    }

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"Coverage of the resident text by the function "
                   "census, and how much of the remainder is reached code. Regenerate: "
                   "tools/text_coverage_audit.c\",\n");
        fprintf(j, " \"exe\": \"%s\",\n \"function_list\": \"%s\",\n", argv[1], argv[2]);
        fprintf(j, " \"text_bytes\": %u,\n \"listed_functions\": %d,\n", text, nf);
        fprintf(j, " \"covered_bytes\": %llu,\n \"covered_percent\": %.1f,\n",
                (unsigned long long)(text - total_gap),
                100.0 * (double)(text - total_gap) / text);
        fprintf(j, " \"uncovered_bytes\": %llu,\n \"gap_count\": %d,\n",
                (unsigned long long)total_gap, ng);
        fprintf(j, " \"dropped_code_bytes\": %llu,\n \"dropped_code_gaps\": %d,\n",
                (unsigned long long)code_gap, n_code);
        fprintf(j, " \"dropped_code_zero_bytes\": %llu,\n"
                   " \"dropped_code_dense_bytes\": %llu,\n \"dropped_code_dense_gaps\": %d,\n"
                   " \"zero_caveat\": \"Reachability alone overstates this. Zero-word "
                   "content is measured because the largest reached gap is majority zeros "
                   "and lies below $gp = 0x80081D98 -- small data, not code. The DENSE "
                   "figure is the defensible one.\",\n",
                (unsigned long long)code_zero, (unsigned long long)dense_gap, n_dense);
        fprintf(j, " \"unreferenced_bytes\": %llu,\n \"unreferenced_gaps\": %d,\n",
                (unsigned long long)quiet_gap, ng - n_code);
        fprintf(j, " \"method\": \"A gap counts as dropped CODE when a listed function "
                   "transfers into it via j/jal/branch. Only DIRECT transfers are followed, "
                   "so jr-reached code scores as unreferenced: the code figure is a floor.\",\n");
        fprintf(j, " \"gaps\": [\n");
        for (int k = 0; k < ng; k++) {
            fprintf(j, "  {\"start\": \"0x%08X\", \"bytes\": %u, \"is_code\": %s, "
                       "\"direct_entries\": %u, \"zero_percent\": %.1f",
                    gaps[k].start, gaps[k].size,
                    gaps[k].entries ? "true" : "false", gaps[k].entries,
                    gaps[k].total_words ? 100.0 * (double)gaps[k].zero_words /
                                          (double)gaps[k].total_words : 0.0);
            if (gaps[k].entries)
                fprintf(j, ", \"sample_src\": \"0x%08X\", \"sample_dst\": \"0x%08X\"",
                        gaps[k].first_src, gaps[k].first_dst);
            fprintf(j, "}%s\n", k + 1 < ng ? "," : "");
        }
        fprintf(j, " ]\n}\n");
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(img);
    return 0;
}
