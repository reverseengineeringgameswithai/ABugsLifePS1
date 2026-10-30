/*
 * phase4_e16_table_consumers.c -- who READS the chunk pointer tables? (E16)
 *
 * The LEVEL.RAW loader registers 46 chunks by pointer into three range-indexed
 * tables (see analysis/phase4_e16_chunk_census.json):
 *
 *   0x8009B4E8  markers 0x30..0x57  (40 slots, 160 bytes)
 *   0x8009C170  markers 0x28..0x2F  ( 8 slots,  32 bytes)
 *   0x800A6450  markers 0x58..0x5F  ( 8 slots,  32 bytes)
 *
 * The loader never interprets those chunks, so their FORMATS belong to whoever
 * reads the tables. This tool searches for those readers.
 *
 * WHY AN EFFECTIVE-ADDRESS SCAN. A first pass matched only the table BASE
 * displacement and found nothing but the three loader stores -- but a consumer
 * reading one fixed slot (say marker 0x35) spells it `lui rX,0x800A` +
 * `lw rY,-19204(rX)`, a displacement that base-only matching misses entirely.
 * Proving "never read" therefore needs every address the instruction can form,
 * not just the base. So this tool shadows register values through lui / addiu /
 * ori chains, computes the effective address of every load and store, and
 * reports each one that lands anywhere INSIDE a table.
 *
 * REACHABILITY (why the shadow is sufficient, not merely convenient). MIPS
 * load displacements are sign-extended, so each table window is reachable from
 * exactly one lui constant:
 *   0x8009B4E8..0x8009B588  <- lui 0x800A, disp [-19224, -19064]
 *   0x8009C170..0x8009C190  <- lui 0x800A, disp [-16016, -15984]
 *   0x800A6450..0x800A6470  <- lui 0x800A, disp [ 25680,  25712]
 * (lui 0x8009 + a positive disp cannot reach them: +0xB4E8 = 46312 overflows
 * signed 16-bit.) A base built by `lui 0x8009` + `ori 0xB4E8` and then indexed
 * with a small displacement is the other spelling, which the shadow follows.
 * $gp-relative access is impossible: $gp is the proven constant 0x80081D98 and
 * all three tables sit >0x19000 away, far outside a signed 16-bit displacement.
 *
 * Registers are invalidated on any write the shadow cannot model, so a reported
 * hit is a real computed address rather than a stale guess. Because the point
 * is to prove a NEGATIVE, the tool ALSO reports raw displacement matches with
 * no lui confirmation ("unconfirmed"), so a missed base-formation shows up as a
 * suspicious count instead of silently becoming evidence of absence.
 *
 * Build: cc -O2 -Werror -o /tmp/e16tc tools/phase4_e16_table_consumers.c
 * Usage: /tmp/e16tc <binary> <load_vaddr_hex> [label]
 *          resident EXE:  /tmp/e16tc SCUS_942.88 0x80010000   (0x800 hdr auto-skipped)
 *          overlay:       /tmp/e16tc LEVEL1.BIN 0x800B39A0
 * Output: JSON on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct { const char *name; uint32_t lo, hi; } TAB[] = {
    { "0x8009B4E8_markers_0x30_0x57", 0x8009B4E8u, 0x8009B4E8u + 40 * 4 },
    { "0x8009C170_markers_0x28_0x2F", 0x8009C170u, 0x8009C170u +  8 * 4 },
    { "0x800A6450_markers_0x58_0x5F", 0x800A6450u, 0x800A6450u +  8 * 4 },
};
#define NTAB 3

/* Displacement windows that can reach a table from `lui 0x800A` (see header). */
static const struct { int32_t lo, hi; } DISPWIN[NTAB] = {
    { -19224, -19064 }, { -16016, -15984 }, { 25680, 25712 },
};

static int which_table(uint32_t ea)
{
    for (int t = 0; t < NTAB; t++)
        if (ea >= TAB[t].lo && ea < TAB[t].hi) return t;
    return -1;
}

static int which_dispwin(int32_t d)
{
    for (int t = 0; t < NTAB; t++)
        if (d >= DISPWIN[t].lo && d <= DISPWIN[t].hi) return t;
    return -1;
}

static const char *opname(uint32_t op, int *is_store)
{
    *is_store = 0;
    switch (op) {
    case 0x20: return "lb";  case 0x21: return "lh";  case 0x22: return "lwl";
    case 0x23: return "lw";  case 0x24: return "lbu"; case 0x25: return "lhu";
    case 0x26: return "lwr";
    case 0x28: *is_store = 1; return "sb";
    case 0x29: *is_store = 1; return "sh";
    case 0x2A: *is_store = 1; return "swl";
    case 0x2B: *is_store = 1; return "sw";
    case 0x2E: *is_store = 1; return "swr";
    default: return NULL;
    }
}

/* Does this instruction write a GPR the shadow cannot model? Return dest or -1. */
static int unmodelled_dest(uint32_t w)
{
    uint32_t op = w >> 26, rt = (w >> 16) & 31, rd = (w >> 11) & 31;
    switch (op) {
    case 0x00:                                   /* SPECIAL: R-type -> rd    */
        if ((w & 0x3F) == 0x08 || (w & 0x3F) == 0x0C) return -1;  /* jr/syscall */
        return (int)rd;
    case 0x0F: case 0x09: case 0x0D: return -1;  /* lui/addiu/ori: modelled  */
    case 0x01: case 0x02: case 0x03:             /* branches/jumps           */
    case 0x04: case 0x05: case 0x06: case 0x07:
        return (op == 0x03) ? 31 : -1;           /* jal writes ra            */
    case 0x08: case 0x0A: case 0x0B: case 0x0C: case 0x0E:  /* addi/slti/andi/xori */
        return (int)rt;
    case 0x10: case 0x11: case 0x12: case 0x13:  /* COPz                     */
        return (int)rt;
    case 0x20: case 0x21: case 0x22: case 0x23:  /* loads write rt           */
    case 0x24: case 0x25: case 0x26:
    case 0x30: case 0x31: case 0x32: case 0x33:
        return (int)rt;
    default: return -1;
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <binary> <load_vaddr_hex> [label]\n", argv[0]);
        return 2;
    }
    const char *path = argv[1];
    uint32_t vaddr = (uint32_t)strtoul(argv[2], NULL, 16);
    const char *label = (argc > 3) ? argv[3] : path;

    FILE *f = fopen(path, "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(n > 0 ? n : 1);
    if (!b || fread(b, 1, n, f) != (size_t)n) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    /* PS-EXE carries a 0x800-byte header before the text image. */
    long start = (n >= 8 && memcmp(b, "PS-X EXE", 8) == 0) ? 0x800 : 0;

    uint32_t hi[32]; int valid[32];
    memset(hi, 0, sizeof hi); memset(valid, 0, sizeof valid);

    printf("{\"binary\":\"%s\",\"label\":\"%s\",\"vaddr\":\"0x%08x\",\"size\":%ld,"
           "\"header_skipped\":%ld,\"hits\":[", path, label, vaddr, n, start);

    int first = 1;
    long ea_hits = 0, ea_reads = 0, ea_writes = 0, unconfirmed = 0;
    for (long o = start; o + 4 <= n; o += 4) {
        uint32_t w; memcpy(&w, b + o, 4);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int32_t imm = (int16_t)(w & 0xFFFF);
        uint32_t pc = vaddr + (uint32_t)(o - start);

        int is_store;
        const char *nm = opname(op, &is_store);
        if (nm) {
            if (valid[rs]) {
                uint32_t ea = hi[rs] + (uint32_t)imm;
                int t = which_table(ea);
                if (t >= 0) {
                    ea_hits++; if (is_store) ea_writes++; else ea_reads++;
                    printf("%s\n {\"pc\":\"0x%08x\",\"op\":\"%s\",\"store\":%s,"
                           "\"ea\":\"0x%08x\",\"table\":\"%s\",\"slot\":%u,"
                           "\"confirmed\":true}",
                           first ? "" : ",", pc, nm, is_store ? "true" : "false",
                           ea, TAB[t].name, (ea - TAB[t].lo) / 4);
                    first = 0;
                }
            } else if (which_dispwin(imm) >= 0) {
                /* displacement could reach a table, but no modelled base */
                unconfirmed++;
                printf("%s\n {\"pc\":\"0x%08x\",\"op\":\"%s\",\"store\":%s,"
                       "\"disp\":%d,\"table\":\"%s\",\"confirmed\":false}",
                       first ? "" : ",", pc, nm, is_store ? "true" : "false",
                       imm, TAB[which_dispwin(imm)].name);
                first = 0;
            }
        }

        /* update the shadow */
        if (op == 0x0F) {                        /* lui rt, imm              */
            hi[rt] = (uint32_t)(w & 0xFFFF) << 16; valid[rt] = 1;
        } else if (op == 0x09 && valid[rs]) {    /* addiu rt, rs, imm        */
            hi[rt] = hi[rs] + (uint32_t)imm; valid[rt] = 1;
        } else if (op == 0x0D && valid[rs]) {    /* ori rt, rs, imm          */
            hi[rt] = hi[rs] | (uint32_t)(w & 0xFFFF); valid[rt] = 1;
        } else {
            int d = unmodelled_dest(w);
            if (d > 0) valid[d] = 0;             /* $zero is never valid     */
        }
        valid[0] = 0;
    }

    printf("\n ],\"ea_hits\":%ld,\"ea_reads\":%ld,\"ea_writes\":%ld,"
           "\"unconfirmed_disp\":%ld}\n", ea_hits, ea_reads, ea_writes, unconfirmed);
    free(b);
    return 0;
}
