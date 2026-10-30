/* Instruction-exact retirement attribution for F01's request cell.
 *
 * The fresh adjudication (bc03931c) rejected `lifecycle` because the breadth sweep's
 * writer_pcs are the true store instruction +4 (the write-watch reporting convention,
 * proved empirically at 0x800496FC/0x800496F8), and the claim map registered those +4
 * PCs as "value-0 writers" -- at which addresses sit an lw, a bgtz and a lui.
 *
 * This probe decodes the word at each REPORTED pc and at pc-4 from the pristine
 * executable and states which one is a store to the request cell (imm 0x23A0), so the
 * claim map can register instruction-exact PCs with the convention disclosed.
 *
 * Build: cc -std=c11 -O2 -Wall -Wextra -Werror -o /tmp/f01_attr tools/phase4_f01_store_attribution.c
 * Usage: f01_attr --selftest | f01_attr <exe> <reported_va>...   (JSON on stdout)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static uint32_t rd32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* is this word a store (sb/sh/sw)? sets rt and an addressing class. The runtime
 * access-log watch already proved each write LANDED on the request cell; the static
 * question is only whether the instruction is a store and of which shape. Register-
 * based stores (e.g. `sb zero,0(s6)`) are legitimate: the 16-bit clear can be split
 * into two byte writes through a pointer -- exactly what the movement integrator does. */
static int is_store(uint32_t w, uint32_t *rt, const char **mn, const char **mode) {
    uint32_t op = w >> 26;
    if (op == 0x28) *mn = "sb"; else if (op == 0x29) *mn = "sh";
    else if (op == 0x2B) *mn = "sw"; else return 0;
    *rt = (w >> 16) & 31;
    *mode = ((w & 0xFFFF) == 0x23A0 && ((w >> 21) & 31) == 1)
            ? "direct_0x23a0_at" : "register_base";
    return 1;
}

static int selftest(void) {
    uint32_t rt; const char *mn; int bad = 0;
    const char *mode;
    /* sh zero,0x23a0(at) = 0xA42023A0 (observed at 0x8004FE44 in the death probe) */
    if (!is_store(0xA42023A0u, &rt, &mn, &mode) || rt != 0 || strcmp(mn, "sh")
        || strcmp(mode, "direct_0x23a0_at")) bad = 1;
    /* sh v0,0x23a0(at) = 0xA42223A0 (the certified death store 0x8004A8B4) */
    if (!is_store(0xA42223A0u, &rt, &mn, &mode) || rt != 2) bad = 1;
    /* sb zero,0(s6) = 0xA2C00000 (integrator byte-clear, register base) */
    if (!is_store(0xA2C00000u, &rt, &mn, &mode) || rt != 0 || strcmp(mn, "sb")
        || strcmp(mode, "register_base")) bad = 1;
    /* lw v0,0x23a0(v1) = 0x8C6223A0 must NOT count (load, not store) */
    if (is_store(0x8C6223A0u, &rt, &mn, &mode)) bad = 1;
    /* lh v0,0x23a0(v0) = 0x844223A0 must NOT count */
    if (is_store(0x844223A0u, &rt, &mn, &mode)) bad = 1;
    printf("{\"selftest\":\"%s\"}\n", bad ? "FAIL" : "PASS");
    return bad;
}

int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--selftest")) return selftest();
    if (argc < 3) { fprintf(stderr, "usage: %s <exe> <reported_va>...\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "open %s\n", argv[1]); return 2; }
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char *buf = malloc((size_t)sz);
    if (!buf || fread(buf, 1, (size_t)sz, f) != (size_t)sz) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);
    if (sz <= 0x800 || memcmp(buf, "PS-X EXE", 8)) { fprintf(stderr, "not a PS-EXE\n"); return 2; }
    uint32_t base = rd32(buf + 0x18);
    printf("{\n \"convention\": \"write-watch reports store pc + 4\",\n \"rows\": [\n");
    int all_ok = 1;
    for (int i = 2; i < argc; i++) {
        uint32_t rep = (uint32_t)strtoul(argv[i], NULL, 0);
        uint32_t w_rep = rd32(buf + 0x800 + (rep - base));
        uint32_t w_ins = rd32(buf + 0x800 + (rep - 4 - base));
        uint32_t rt = 99; const char *mn = ""; const char *mode = "";
        uint32_t rt2; const char *mn2; const char *md2;
        int rep_is = is_store(w_rep, &rt2, &mn2, &md2);
        int ins_is = is_store(w_ins, &rt, &mn, &mode);
        if (!ins_is || rep_is) all_ok = 0;   /* convention demands: pc-4 IS a store, pc is NOT */
        printf("  %s{\"reported_pc\": \"0x%08X\", \"word_at_reported\": \"0x%08X\", "
               "\"reported_is_store\": %s, \"instruction_pc\": \"0x%08X\", "
               "\"word_at_instruction\": \"0x%08X\", \"instruction_is_store\": %s, "
               "\"mnemonic\": \"%s\", \"addressing\": \"%s\", \"value_register\": %u}",
               i > 2 ? ",\n" : "", rep, w_rep, rep_is ? "true" : "false",
               rep - 4, w_ins, ins_is ? "true" : "false", mn, mode, rt);
    }
    printf("\n ],\n \"convention_holds_at_every_row\": %s\n}\n", all_ok ? "true" : "false");
    return all_ok ? 0 : 1;
}
