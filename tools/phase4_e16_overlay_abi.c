/*
 * phase4_e16_overlay_abi.c -- verify the overlay calling contract (E16).
 *
 * The committed overlay map records 42 addresses inside overlay region A
 * (base 0x800B39A0) that RESIDENT code calls. They sit at irregular offsets
 * (+0x04, +0x18, +0x28, +0x3C, +0x13C ...), so the contract is NOT a vector
 * table: the resident EXE calls hardcoded absolute addresses, and whichever
 * overlay is resident must have a compatible routine at each address it covers.
 *
 * This tool tests that contract against the retail bytes. For one overlay file
 * loaded at `base`, and for each entry address given on stdin, it reports:
 *   - whether the address is inside this overlay at all (they differ in size),
 *   - the first instruction word there,
 *   - whether that word looks like a FUNCTION START: either a stack-frame
 *     opening `addiu sp,sp,-N` (opcode 0x09, rs=rt=29, negative imm) or a
 *     leaf/stub `jr ra` (0x03E00008), which is how a "present but does
 *     nothing" slot would be spelled.
 *
 * A contract holds if every in-range entry is a plausible function start in
 * every overlay. Entries past an overlay's end are simply not part of that
 * scene's contract and are reported as out_of_range rather than as failures.
 *
 * Build: cc -O2 -Werror -o /tmp/e16abi tools/phase4_e16_overlay_abi.c
 * Usage: /tmp/e16abi <overlay.BIN> <base_hex>   (entry addresses on stdin, hex per line)
 * Output: JSON on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

    printf("{\"file\":\"%s\",\"base\":\"0x%08x\",\"size\":%ld,\"entries\":[", argv[1], base, n);
    char line[64];
    int first = 1, in_range = 0, ok_start = 0, bad = 0;
    while (fgets(line, sizeof line, stdin)) {
        uint32_t a = (uint32_t)strtoul(line, NULL, 16);
        long off = (long)a - (long)base;
        printf("%s\n {\"entry\":\"0x%08x\",\"off\":%ld,", first ? "" : ",", a, off);
        first = 0;
        if (off < 0 || off + 4 > n) { printf("\"in_range\":false}"); continue; }
        in_range++;
        uint32_t w; memcpy(&w, b + off, 4);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int32_t imm = (int16_t)(w & 0xFFFF);
        int frame = (op == 0x09 && rs == 29 && rt == 29 && imm < 0);   /* addiu sp,sp,-N */
        int stub  = (w == 0x03E00008);                                 /* jr ra          */
        if (frame || stub) ok_start++; else bad++;
        printf("\"in_range\":true,\"word\":\"0x%08x\",\"frame\":%s,\"stub\":%s,\"plausible\":%s}",
               w, frame ? "true" : "false", stub ? "true" : "false",
               (frame || stub) ? "true" : "false");
    }
    printf("\n ],\"in_range\":%d,\"plausible_starts\":%d,\"implausible\":%d}\n",
           in_range, ok_start, bad);
    return 0;
}
