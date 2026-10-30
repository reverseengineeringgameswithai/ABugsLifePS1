/*
 * phase4_e16_overlay_starts.c -- derive overlay function starts from RETURNS,
 * not from prologue patterns (E16).
 *
 * WHY. The committed overlay-ABI scan (tools/phase4_e16_overlay_abi.c) decides
 * whether an overlay implements a given entry address by testing whether the
 * word there is `addiu sp,sp,-N` or a bare `jr ra`. That recognises only two
 * prologue shapes, so a leaf function that opens with anything else reads as
 * "not implemented" -- which is why the artifact records its per-overlay entry
 * lists and its 27/42 union as LOWER BOUNDS.
 *
 * This tool tightens that bound with a structurally different test. In a
 * contiguous code region, a function START is the instruction after the delay
 * slot of a function RETURN. So:
 *
 *      starts = { base + 4 }                      (the header word is at +0)
 *             U { addr(jr ra) + 8  for every jr ra in the region }
 *
 * No prologue is assumed, so leaf functions of any shape are caught. The two
 * detectors are reported side by side, so the improvement is visible and the
 * previous number is not silently replaced.
 *
 * ASSUMPTIONS, stated because they bound the result:
 *  - The region is contiguous code. Embedded data (jump tables, constant pools)
 *    disassembles as garbage and can synthesise a false `jr ra`. Such a false
 *    return only ever ADDS a start, so this detector over-approximates: it can
 *    call an address a function start when it is not, but it cannot miss a real
 *    one that ends its predecessor with `jr ra`.
 *  - A function that never returns via `jr ra` (tail-jumps to a shared
 *    epilogue) will not create a start for its successor.
 * Because the two detectors err in OPPOSITE directions -- prologue-matching
 * under-counts, return-scanning over-counts -- an entry accepted by BOTH is
 * solid, and the pair brackets the truth instead of guessing at it.
 *
 * Build: cc -O2 -Werror -o /tmp/e16starts tools/phase4_e16_overlay_starts.c
 * Usage: /tmp/e16starts <overlay.BIN> <base_hex>   (entry addresses on stdin, hex/line)
 * Output: JSON on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define JR_RA 0x03E00008u

int main(int argc, char **argv)
{
    if (argc != 3) { fprintf(stderr, "usage: %s overlay.BIN base_hex\n", argv[0]); return 2; }
    uint32_t base = (uint32_t)strtoul(argv[2], NULL, 16);
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(n > 0 ? n : 1);
    if (!b || fread(b, 1, n, f) != (size_t)n) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    /* Mark every start implied by a return. */
    uint8_t *is_start = calloc(n / 4 + 2, 1);
    long returns = 0;
    if (n >= 4) is_start[1] = 1;                      /* base+4: first function */
    for (long o = 0; o + 4 <= n; o += 4) {
        uint32_t w; memcpy(&w, b + o, 4);
        if (w == JR_RA) {
            returns++;
            long nx = o / 4 + 2;                      /* skip the delay slot   */
            if (nx <= n / 4) is_start[nx] = 1;
        }
    }
    long total_starts = 0;
    for (long i = 0; i <= n / 4; i++) total_starts += is_start[i];

    printf("{\"file\":\"%s\",\"base\":\"0x%08x\",\"size\":%ld,"
           "\"returns\":%ld,\"function_starts\":%ld,\"entries\":[",
           argv[1], base, n, returns, total_starts);

    char line[64];
    int first = 1, in_range = 0, by_return = 0, by_prologue = 0, by_both = 0;
    while (fgets(line, sizeof line, stdin)) {
        uint32_t a = (uint32_t)strtoul(line, NULL, 16);
        long off = (long)a - (long)base;
        printf("%s\n {\"entry\":\"0x%08x\",\"off\":%ld,", first ? "" : ",", a, off);
        first = 0;
        if (off < 0 || off + 4 > n || (off & 3)) { printf("\"in_range\":false}"); continue; }
        in_range++;
        uint32_t w; memcpy(&w, b + off, 4);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int32_t imm = (int16_t)(w & 0xFFFF);
        int prologue = (op == 0x09 && rs == 29 && rt == 29 && imm < 0) || (w == JR_RA);
        int ret_start = is_start[off / 4] ? 1 : 0;
        by_prologue += prologue;
        by_return += ret_start;
        by_both += (prologue && ret_start);
        printf("\"in_range\":true,\"word\":\"0x%08x\",\"prologue_match\":%s,"
               "\"return_derived_start\":%s,\"both\":%s}",
               w, prologue ? "true" : "false", ret_start ? "true" : "false",
               (prologue && ret_start) ? "true" : "false");
    }
    printf("\n ],\"in_range\":%d,\"by_prologue\":%d,\"by_return\":%d,\"by_both\":%d}\n",
           in_range, by_prologue, by_return, by_both);
    free(is_start);
    free(b);
    return 0;
}
