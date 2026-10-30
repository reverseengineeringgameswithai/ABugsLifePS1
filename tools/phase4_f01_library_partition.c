/* phase4_f01_library_partition.c
 *
 * Machine-derives the ADDRESS-MATERIALIZATION census into the gp-tail data
 * zone of SCUS_942.88: every site where analysed code builds a constant
 * pointer into [zone_lo, zone_hi) via the lui/addiu, lui/ori or gp-relative
 * idioms, every memory access performed through a register whose constant
 * value the linear tracker still knows, and the per-base aggregation of
 * those facts with the containing census function named.
 *
 * The tracker is deliberately CONSERVATIVE: all tracked constants are
 * discarded at every in-function branch target (labels), on every other
 * write to the register, and $ra on calls.  $gp is re-seeded with the
 * proven constant at every label.  A site this tool reports is a fact of
 * the bytes; a site it misses proves nothing (stated in the receipt).
 *
 * Usage:
 *   phase4_f01_library_partition IMAGE BASE_HEX FUNCS_TSV ZONE_LO ZONE_HI GP_HEX
 *
 * FUNCS_TSV lines: "<entry_hex> <end_hex> <name>" sorted by entry.
 * Output: one JSON document on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FUNCS 4096
#define MAX_SITES 65536
#define MAX_LABELS 16384

typedef struct { uint32_t entry, end; char name[96]; } Func;
typedef struct {
    uint32_t pc, target;
    uint8_t width;          /* 0 = address materialization, else access bytes */
    char kind[8];           /* addr | load | store */
    int func_idx;
} Site;

static Func funcs[MAX_FUNCS];
static int nfuncs;
static Site sites[MAX_SITES];
static int nsites;
static uint32_t labels[MAX_LABELS];
static int nlabels;

static const uint8_t *image;
static long image_len;
static uint32_t base, zone_lo, zone_hi, gp_value;

static uint32_t word_at(uint32_t va) {
    long off = (long)va - (long)base;
    if (off < 0 || off + 4 > image_len) return 0;
    return (uint32_t)image[off] | ((uint32_t)image[off + 1] << 8) |
           ((uint32_t)image[off + 2] << 16) | ((uint32_t)image[off + 3] << 24);
}

static int label_cmp(const void *a, const void *b) {
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}
static int is_label(uint32_t pc) {
    return bsearch(&pc, labels, (size_t)nlabels, sizeof(uint32_t), label_cmp) != NULL;
}

static void add_site(uint32_t pc, uint32_t target, uint8_t width,
                     const char *kind, int func_idx) {
    if (nsites >= MAX_SITES) { fprintf(stderr, "site overflow\n"); exit(1); }
    Site *s = &sites[nsites++];
    s->pc = pc; s->target = target; s->width = width; s->func_idx = func_idx;
    snprintf(s->kind, sizeof s->kind, "%s", kind);
}

static uint8_t mem_width(uint32_t op) {
    switch (op) {
    case 0x20: case 0x24: case 0x28: return 1;              /* lb lbu sb */
    case 0x21: case 0x25: case 0x29: return 2;              /* lh lhu sh */
    case 0x22: case 0x23: case 0x26:                        /* lwl lw lwr */
    case 0x2A: case 0x2B: case 0x2E: return 4;              /* swl sw swr */
    default: return 0;
    }
}
static int mem_is_store(uint32_t op) { return op >= 0x28; }

static void scan_function(int fi) {
    uint32_t fa = funcs[fi].entry, fb = funcs[fi].end;
    uint32_t pc, w;
    /* pass 1: in-function branch targets */
    nlabels = 0;
    for (pc = fa; pc < fb; pc += 4) {
        w = word_at(pc);
        uint32_t op = w >> 26;
        if (op == 1 || (op >= 4 && op <= 7) || (op >= 0x14 && op <= 0x17)) {
            int32_t off = (int16_t)(w & 0xFFFF);
            uint32_t t = pc + 4 + ((uint32_t)off << 2);
            if (t >= fa && t < fb && nlabels < MAX_LABELS) labels[nlabels++] = t;
        } else if (op == 2 || op == 3) {
            if (pc + 8 < fb && nlabels < MAX_LABELS) labels[nlabels++] = pc + 8;
        }
    }
    qsort(labels, (size_t)nlabels, sizeof(uint32_t), label_cmp);

    /* pass 2: linear constant tracking */
    uint32_t regval[32];
    uint8_t known[32];
    memset(known, 0, sizeof known);
    known[28] = 1; regval[28] = gp_value;
    for (pc = fa; pc < fb; pc += 4) {
        if (is_label(pc)) {
            memset(known, 0, sizeof known);
            known[28] = 1; regval[28] = gp_value;
        }
        w = word_at(pc);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31,
                 rd = (w >> 11) & 31, fn = w & 0x3F;
        uint32_t imm = w & 0xFFFF;
        int32_t simm = (int16_t)imm;
        uint8_t width = mem_width(op);
        if (op == 0x0F) {                                    /* lui */
            known[rt] = 1; regval[rt] = imm << 16;
        } else if (op == 0x09 && known[rs]) {                /* addiu */
            uint32_t val = regval[rs] + (uint32_t)simm;
            if (val >= zone_lo && val < zone_hi)
                add_site(pc, val, 0, "addr", fi);
            known[rt] = 1; regval[rt] = val;
        } else if (op == 0x0D && known[rs]) {                /* ori */
            uint32_t val = regval[rs] | imm;
            if (val >= zone_lo && val < zone_hi)
                add_site(pc, val, 0, "addr", fi);
            known[rt] = 1; regval[rt] = val;
        } else if (width && known[rs]) {                     /* mem op */
            uint32_t ea = regval[rs] + (uint32_t)simm;
            if (ea >= zone_lo && ea < zone_hi)
                add_site(pc, ea, width, mem_is_store(op) ? "store" : "load", fi);
            if (!mem_is_store(op)) known[rt] = 0;
        } else if (op == 0 &&
                   (fn == 0x21 || fn == 0x25) && rt == 0 && known[rs]) {
            known[rd] = 1; regval[rd] = regval[rs];          /* move */
        } else {
            if (op == 0) known[rd] = 0;
            else if (op >= 0x08 && op <= 0x0E) known[rt] = 0;
            else if (op == 0x10 || op == 0x11 || op == 0x12 || op == 0x13)
                known[rt] = 0;                               /* mfc0/mfc2/... */
            else if (width && !mem_is_store(op)) known[rt] = 0;
        }
        if (op == 3 || (op == 0 && fn == 9)) known[31] = 0;  /* jal/jalr */
    }
}

int main(int argc, char **argv) {
    if (argc != 7) {
        fprintf(stderr, "usage: %s IMAGE BASE FUNCS_TSV ZONE_LO ZONE_HI GP\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("image"); return 1; }
    fseek(f, 0, SEEK_END); image_len = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc((size_t)image_len);
    if (!buf || fread(buf, 1, (size_t)image_len, f) != (size_t)image_len) {
        fprintf(stderr, "image read failed\n"); return 1;
    }
    fclose(f);
    image = buf;
    base = (uint32_t)strtoul(argv[2], NULL, 16);
    zone_lo = (uint32_t)strtoul(argv[4], NULL, 16);
    zone_hi = (uint32_t)strtoul(argv[5], NULL, 16);
    gp_value = (uint32_t)strtoul(argv[6], NULL, 16);

    FILE *ft = fopen(argv[3], "r");
    if (!ft) { perror("funcs"); return 1; }
    char line[256];
    while (fgets(line, sizeof line, ft) && nfuncs < MAX_FUNCS) {
        Func *fu = &funcs[nfuncs];
        if (sscanf(line, "%x %x %95s", &fu->entry, &fu->end, fu->name) == 3)
            nfuncs++;
    }
    fclose(ft);

    int gp_relative_sites = 0;
    for (int i = 0; i < nfuncs; i++) scan_function(i);
    for (int i = 0; i < nsites; i++) {
        uint32_t insn = word_at(sites[i].pc);
        if (((insn >> 21) & 31) == 28) gp_relative_sites++;
    }

    printf("{\n \"zone\": [\"0x%08X\", \"0x%08X\"],\n \"gp_value\": \"0x%08X\",\n",
           zone_lo, zone_hi, gp_value);
    printf(" \"functions_scanned\": %d,\n \"site_count\": %d,\n", nfuncs, nsites);
    printf(" \"gp_relative_sites_into_zone\": %d,\n", gp_relative_sites);
    printf(" \"sites\": [\n");
    for (int i = 0; i < nsites; i++) {
        Site *s = &sites[i];
        printf("  {\"pc\": \"0x%08X\", \"target\": \"0x%08X\", \"kind\": \"%s\","
               " \"width\": %u, \"function\": \"%s\"}%s\n",
               s->pc, s->target, s->kind, s->width,
               funcs[s->func_idx].name, i + 1 < nsites ? "," : "");
    }
    printf(" ],\n");

    /* per-base aggregation: distinct materialized addresses below gp,
     * with owner entry min/max over their materializing functions */
    uint32_t owner_min = 0xFFFFFFFF, owner_max = 0;
    int below_gp_addr_sites = 0, crt0_gp_sites = 0;
    for (int i = 0; i < nsites; i++) {
        Site *s = &sites[i];
        if (strcmp(s->kind, "addr") != 0) continue;
        if (s->target == gp_value) { crt0_gp_sites++; continue; }
        if (s->target > gp_value) continue;
        below_gp_addr_sites++;
        uint32_t e = funcs[s->func_idx].entry;
        if (e < owner_min) owner_min = e;
        if (e > owner_max) owner_max = e;
    }
    printf(" \"below_gp_materializations\": %d,\n", below_gp_addr_sites);
    printf(" \"below_gp_owner_entry_min\": \"0x%08X\",\n", owner_min);
    printf(" \"below_gp_owner_entry_max\": \"0x%08X\",\n", owner_max);
    printf(" \"crt0_gp_setup_sites\": %d\n}\n", crt0_gp_sites);
    return 0;
}
