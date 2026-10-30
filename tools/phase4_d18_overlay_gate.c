/*
 * phase4_d18_overlay_gate.c -- decode the Thud fight's hit-qualifier gate from
 * the Bug Bar overlay (D18/F09).
 *
 * Live capture proved the fight counter 0x800B4CC8 is incremented by the store
 * at 0x800B3DB0 (`sw v0,0x4cc8(at)`), exactly 8 times, while the resident berry
 * dispatch dealt 15 damage events -- i.e. a qualifier collapses bursts of hits
 * into one count. This tool finds that store INSIDE THE OVERLAY FILE, derives
 * the overlay's load base from the match (no assumed base), and disassembles
 * the surrounding handler so the gate condition is read off the retail bytes
 * rather than inferred from timing.
 *
 * Self-verifying: it refuses to proceed unless the anchor encoding occurs
 * exactly once, and it re-checks the derived base against a second known PC
 * (the HP restore store 0x800B3ED0, `sh v0,0x6e(s3)` = 0xA662006E).
 *
 * Build: cc -O2 -Werror -o /tmp/d18gate tools/phase4_d18_overlay_gate.c
 * Usage: /tmp/d18gate <overlay.BIN> [window_before] [window_after]
 * Output: JSON on stdout.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define COUNTER_STORE_VADDR 0x800B3DB0u
#define COUNTER_STORE_ENC   0xAC224CC8u   /* sw v0,0x4cc8(at) */
#define RESTORE_STORE_VADDR 0x800B3ED0u
#define RESTORE_STORE_ENC   0xA662006Eu   /* sh v0,0x6e(s3)   */
#define COUNTER_VADDR       0x800B4CC8u

static const char *R[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3",
    "t4","t5","t6","t7","s0","s1","s2","s3","s4","s5","s6","s7",
    "t8","t9","k0","k1","gp","sp","fp","ra"};

static uint8_t *buf; static long blen;

static uint32_t rd32(long off) { uint32_t v; memcpy(&v, buf + off, 4); return v; }

/* minimal MIPS-I disassembler covering what these handlers use */
static void dis(uint32_t w, uint32_t pc, char *out, size_t n)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31, rd = (w >> 11) & 31;
    uint32_t sa = (w >> 6) & 31, fn = w & 0x3F, imm = w & 0xFFFF;
    int32_t s = (imm & 0x8000) ? (int32_t)imm - 0x10000 : (int32_t)imm;
    uint32_t tgt = pc + 4 + (uint32_t)(s * 4);
    if (w == 0) { snprintf(out, n, "nop"); return; }
    switch (op) {
    case 0x00:
        switch (fn) {
        case 0x00: snprintf(out, n, "sll %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x02: snprintf(out, n, "srl %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x03: snprintf(out, n, "sra %s,%s,%u", R[rd], R[rt], sa); return;
        case 0x08: snprintf(out, n, "jr %s", R[rs]); return;
        case 0x09: snprintf(out, n, "jalr %s,%s", R[rd], R[rs]); return;
        case 0x21: snprintf(out, n, "addu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x23: snprintf(out, n, "subu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x24: snprintf(out, n, "and %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x25: snprintf(out, n, "or %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2A: snprintf(out, n, "slt %s,%s,%s", R[rd], R[rs], R[rt]); return;
        case 0x2B: snprintf(out, n, "sltu %s,%s,%s", R[rd], R[rs], R[rt]); return;
        default:   snprintf(out, n, "special.%02x", fn); return;
        }
    case 0x01:
        snprintf(out, n, "%s %s,0x%08x", (rt == 0) ? "bltz" : "bgez", R[rs], tgt); return;
    case 0x02: snprintf(out, n, "j 0x%08x", (pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)); return;
    case 0x03: snprintf(out, n, "jal 0x%08x", (pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)); return;
    case 0x04: snprintf(out, n, "beq %s,%s,0x%08x", R[rs], R[rt], tgt); return;
    case 0x05: snprintf(out, n, "bne %s,%s,0x%08x", R[rs], R[rt], tgt); return;
    case 0x06: snprintf(out, n, "blez %s,0x%08x", R[rs], tgt); return;
    case 0x07: snprintf(out, n, "bgtz %s,0x%08x", R[rs], tgt); return;
    case 0x08: snprintf(out, n, "addi %s,%s,%d", R[rt], R[rs], s); return;
    case 0x09: snprintf(out, n, "addiu %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0A: snprintf(out, n, "slti %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0B: snprintf(out, n, "sltiu %s,%s,%d", R[rt], R[rs], s); return;
    case 0x0C: snprintf(out, n, "andi %s,%s,0x%x", R[rt], R[rs], imm); return;
    case 0x0D: snprintf(out, n, "ori %s,%s,0x%x", R[rt], R[rs], imm); return;
    case 0x0F: snprintf(out, n, "lui %s,0x%x", R[rt], imm); return;
    case 0x20: snprintf(out, n, "lb %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x21: snprintf(out, n, "lh %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x23: snprintf(out, n, "lw %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x24: snprintf(out, n, "lbu %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x25: snprintf(out, n, "lhu %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x28: snprintf(out, n, "sb %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x29: snprintf(out, n, "sh %s,%d(%s)", R[rt], s, R[rs]); return;
    case 0x2B: snprintf(out, n, "sw %s,%d(%s)", R[rt], s, R[rs]); return;
    default:   snprintf(out, n, "op%02x", op); return;
    }
}

static long find_unique(uint32_t enc, int *count)
{
    long hit = -1; *count = 0;
    for (long o = 0; o + 4 <= blen; o += 4)
        if (rd32(o) == enc) { if (*count == 0) hit = o; (*count)++; }
    return hit;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s overlay.BIN [before] [after]\n", argv[0]); return 2; }
    long before = (argc > 2) ? strtol(argv[2], NULL, 0) : 0x140;
    long after  = (argc > 3) ? strtol(argv[3], NULL, 0) : 0x50;
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); blen = ftell(f); fseek(f, 0, SEEK_SET);
    buf = malloc(blen);
    if (!buf || fread(buf, 1, blen, f) != (size_t)blen) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    int c1 = 0, c2 = 0;
    long off1 = find_unique(COUNTER_STORE_ENC, &c1);
    if (c1 != 1) {
        printf("{\"located\":false,\"counter_store_matches\":%d,\"file\":\"%s\"}\n", c1, argv[1]);
        return 1;
    }
    uint32_t base = COUNTER_STORE_VADDR - (uint32_t)off1;
    long off2 = find_unique(RESTORE_STORE_ENC, &c2);
    int base_confirmed = (c2 == 1) && (base + (uint32_t)off2 == RESTORE_STORE_VADDR);

    printf("{\n \"located\": true,\n \"file\": \"%s\",\n \"file_size\": %ld,\n"
           " \"load_base\": \"0x%08x\",\n \"counter_store_file_off\": %ld,\n"
           " \"base_confirmed_by_restore_store\": %s,\n"
           " \"counter_vaddr\": \"0x%08x\",\n \"disasm\": [\n",
           argv[1], blen, base, off1, base_confirmed ? "true" : "false", COUNTER_VADDR);

    long start = off1 - before, end = off1 + after;
    if (start < 0) start = 0;
    if (end + 4 > blen) end = blen - 4;
    for (long o = start; o <= end; o += 4) {
        uint32_t pc = base + (uint32_t)o, w = rd32(o);
        char txt[96]; dis(w, pc, txt, sizeof txt);
        char mark[64]; mark[0] = 0;
        if (pc == COUNTER_STORE_VADDR)
            snprintf(mark, sizeof mark, ",\"mark\":\"COUNTER INCREMENT STORE\"");
        else if (pc == RESTORE_STORE_VADDR)
            snprintf(mark, sizeof mark, ",\"mark\":\"HP RESTORE STORE\"");
        printf("  {\"pc\":\"0x%08x\",\"word\":\"0x%08x\",\"text\":\"%s\"%s}%s\n",
               pc, w, txt, mark, (o + 4 > end) ? "" : ",");
    }
    printf(" ]\n}\n");
    return 0;
}
