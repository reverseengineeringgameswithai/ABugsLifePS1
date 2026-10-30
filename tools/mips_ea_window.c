/*
 * mips_ea_window.c -- decode a window of MIPS and resolve GLOBAL effective addresses.
 *
 * WHY THIS EXISTS. Searching for "who touches global X" by matching a load/store
 * displacement against X's offset from a `lui` finds only FIXED accesses. The
 * common table access is INDEXED:
 *
 *      lui   $at, 0x800A
 *      addu  $at, $at, $v0        # $v0 = index * elemsize
 *      lh    $t7, -0x4c54($at)    # displacement is NOT X's offset
 *
 * Here the displacement encodes the table base MINUS whatever the index scaling
 * assumes, so a displacement-window scan misses the access entirely -- which is
 * exactly how an E16 scan concluded "these tables are never read" while a live
 * watch caught 276 reads. This tool decodes each instruction, tracks lui/addiu/
 * ori chains AND `addu reg, reg, idx` index folding, and reports for every load
 * and store either a resolved constant EA or "base + index" with the constant
 * part resolved, so indexed accesses are visible rather than silently absent.
 *
 * The register shadow is deliberately LOCAL to the printed window (it is seeded
 * by scanning back `lookback` instructions), because a whole-file linear shadow
 * is worthless: unrelated later code overwrites the register and the shadow goes
 * stale without saying so.
 *
 * Build: cc -O2 -Werror -o /tmp/mipsw tools/mips_ea_window.c
 * Usage: /tmp/mipsw <binary> <load_vaddr_hex> <pc_hex> [before] [after] [lookback]
 *          PS-EXE headers (0x800) are detected and skipped automatically.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *RN[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"
};

/* Value shadow: kind 0 = unknown, 1 = constant, 2 = constant + unknown index. */
struct Val { int kind; uint32_t c; };

static const char *ls_name(uint32_t op, int *is_store)
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

static void step(struct Val *v, uint32_t w)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31, rd = (w >> 11) & 31;
    uint32_t fn = w & 0x3F;
    int32_t imm = (int16_t)(w & 0xFFFF);

    if (op == 0x0F) {                                  /* lui rt, imm        */
        v[rt].kind = 1; v[rt].c = (uint32_t)(w & 0xFFFF) << 16;
    } else if (op == 0x09) {                           /* addiu rt, rs, imm  */
        if (v[rs].kind) { v[rt].kind = v[rs].kind; v[rt].c = v[rs].c + (uint32_t)imm; }
        else v[rt].kind = 0;
    } else if (op == 0x0D) {                           /* ori rt, rs, imm    */
        if (v[rs].kind) { v[rt].kind = v[rs].kind; v[rt].c = v[rs].c | (uint32_t)(w & 0xFFFF); }
        else v[rt].kind = 0;
    } else if (op == 0x00 && (fn == 0x21 || fn == 0x20)) {  /* addu/add rd,rs,rt */
        uint32_t a = (w >> 21) & 31, b = (w >> 16) & 31;
        if (v[a].kind == 1 && v[b].kind == 0) { v[rd].kind = 2; v[rd].c = v[a].c; }
        else if (v[b].kind == 1 && v[a].kind == 0) { v[rd].kind = 2; v[rd].c = v[b].c; }
        else if (v[a].kind && v[b].kind) { v[rd].kind = 2; v[rd].c = v[a].c + v[b].c; }
        else v[rd].kind = 0;
    } else if (op == 0x00) {
        if (fn != 0x08 && fn != 0x0C) v[rd].kind = 0;  /* not jr / syscall   */
    } else if (op == 0x03) {
        v[31].kind = 0;
    } else if (op == 0x08 || op == 0x0A || op == 0x0B || op == 0x0C || op == 0x0E ||
               op == 0x10 || op == 0x11 || op == 0x12 || op == 0x13 ||
               (op >= 0x20 && op <= 0x26) || (op >= 0x30 && op <= 0x33)) {
        v[rt].kind = 0;
    }
    v[0].kind = 1; v[0].c = 0;
}

int main(int argc, char **argv)
{
    if (argc < 4) {
        fprintf(stderr, "usage: %s <binary> <load_vaddr_hex> <pc_hex> "
                        "[before] [after] [lookback]\n", argv[0]);
        return 2;
    }
    uint32_t vaddr = (uint32_t)strtoul(argv[2], NULL, 16);
    uint32_t pc    = (uint32_t)strtoul(argv[3], NULL, 16);
    long before   = (argc > 4) ? strtol(argv[4], NULL, 0) : 12;
    long after    = (argc > 5) ? strtol(argv[5], NULL, 0) : 6;
    long lookback = (argc > 6) ? strtol(argv[6], NULL, 0) : 400;

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc(n > 0 ? n : 1);
    if (!b || fread(b, 1, n, f) != (size_t)n) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);

    long start = (n >= 8 && memcmp(b, "PS-X EXE", 8) == 0) ? 0x800 : 0;
    long target = start + (long)(pc - vaddr);
    if (target < start || target + 4 > n) {
        fprintf(stderr, "pc 0x%08x outside %s\n", pc, argv[1]); return 2;
    }

    struct Val v[32];
    memset(v, 0, sizeof v);
    v[0].kind = 1;

    long seed = target - 4 * lookback;
    if (seed < start) seed = start;
    for (long o = seed; o < target - 4 * before; o += 4) {
        uint32_t w; memcpy(&w, b + o, 4); step(v, w);
    }

    printf("# %s  window around 0x%08x  (shadow seeded %ld instrs back)\n",
           argv[1], pc, (target - seed) / 4);
    for (long o = target - 4 * before; o <= target + 4 * after && o + 4 <= n; o += 4) {
        if (o < start) continue;
        uint32_t w; memcpy(&w, b + o, 4);
        uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int32_t imm = (int16_t)(w & 0xFFFF);
        uint32_t at = vaddr + (uint32_t)(o - start);
        char mark = (o == target) ? '>' : ' ';

        int is_store;
        const char *nm = ls_name(op, &is_store);
        char text[160];
        if (nm) {
            if (v[rs].kind == 1)
                snprintf(text, sizeof text, "%-4s $%s, %d($%s)   EA=0x%08x",
                         nm, RN[rt], imm, RN[rs], v[rs].c + (uint32_t)imm);
            else if (v[rs].kind == 2)
                snprintf(text, sizeof text, "%-4s $%s, %d($%s)   EA=0x%08x + index  [INDEXED]",
                         nm, RN[rt], imm, RN[rs], v[rs].c + (uint32_t)imm);
            else
                snprintf(text, sizeof text, "%-4s $%s, %d($%s)   EA=unknown",
                         nm, RN[rt], imm, RN[rs]);
        } else if (op == 0x0F) {
            snprintf(text, sizeof text, "lui  $%s, 0x%04x", RN[rt], w & 0xFFFF);
        } else if (op == 0x09) {
            snprintf(text, sizeof text, "addiu $%s, $%s, %d%s", RN[rt], RN[rs], imm,
                     v[rt].kind == 1 ? "" : "");
        } else if (op == 0x00 && (w & 0x3F) == 0x21) {
            snprintf(text, sizeof text, "addu $%s, $%s, $%s",
                     RN[(w >> 11) & 31], RN[rs], RN[rt]);
        } else if (op == 0x00 && (w & 0x3F) == 0x00) {
            snprintf(text, sizeof text, "sll  $%s, $%s, %u",
                     RN[(w >> 11) & 31], RN[rt], (w >> 6) & 31);
        } else if (op == 0x00) {
            uint32_t fn = w & 0x3F, rd = (w >> 11) & 31, sa = (w >> 6) & 31;
            const char *r3 = NULL, *sh = NULL;
            switch (fn) {
            case 0x02: sh = "srl";  break;
            case 0x03: sh = "sra";  break;
            case 0x04: r3 = "sllv"; break;
            case 0x06: r3 = "srlv"; break;
            case 0x07: r3 = "srav"; break;
            case 0x20: r3 = "add";  break;
            case 0x22: r3 = "sub";  break;
            case 0x23: r3 = "subu"; break;
            case 0x24: r3 = "and";  break;
            case 0x25: r3 = "or";   break;
            case 0x26: r3 = "xor";  break;
            case 0x27: r3 = "nor";  break;
            case 0x2A: r3 = "slt";  break;
            case 0x2B: r3 = "sltu"; break;
            default: break;
            }
            if (sh)
                snprintf(text, sizeof text, "%-4s $%s, $%s, %u", sh, RN[rd], RN[rt], sa);
            else if (r3)
                snprintf(text, sizeof text, "%-4s $%s, $%s, $%s", r3, RN[rd], RN[rs], RN[rt]);
            else if (fn == 0x08)
                snprintf(text, sizeof text, "jr   $%s", RN[rs]);
            else if (fn == 0x09)
                snprintf(text, sizeof text, "jalr $%s, $%s", RN[rd], RN[rs]);
            else if (fn == 0x10 || fn == 0x12)
                snprintf(text, sizeof text, "%s  $%s", fn == 0x10 ? "mfhi" : "mflo", RN[rd]);
            else if (fn == 0x18 || fn == 0x19 || fn == 0x1A || fn == 0x1B)
                snprintf(text, sizeof text, "%-5s $%s, $%s",
                         fn == 0x18 ? "mult" : fn == 0x19 ? "multu" : fn == 0x1A ? "div" : "divu",
                         RN[rs], RN[rt]);
            else
                snprintf(text, sizeof text, ".word 0x%08x  (special fn=0x%02x)", w, fn);
        } else if (op == 0x04 || op == 0x05 || op == 0x06 || op == 0x07 || op == 0x01) {
            uint32_t tgt = at + 4 + (uint32_t)(imm * 4);
            const char *bn = (op == 0x04) ? "beq" : (op == 0x05) ? "bne"
                           : (op == 0x06) ? "blez" : (op == 0x07) ? "bgtz"
                           : ((rt & 1) ? "bgez" : "bltz");
            if (op == 0x04 || op == 0x05)
                snprintf(text, sizeof text, "%-4s $%s, $%s, 0x%08x", bn, RN[rs], RN[rt], tgt);
            else
                snprintf(text, sizeof text, "%-4s $%s, 0x%08x", bn, RN[rs], tgt);
        } else if (op == 0x0A || op == 0x0B || op == 0x0C || op == 0x0E || op == 0x08) {
            const char *inm = (op == 0x0A) ? "slti" : (op == 0x0B) ? "sltiu"
                            : (op == 0x0C) ? "andi" : (op == 0x0E) ? "xori" : "addi";
            if (op == 0x0C || op == 0x0E)
                snprintf(text, sizeof text, "%-5s $%s, $%s, 0x%04x", inm, RN[rt], RN[rs],
                         (unsigned)(w & 0xFFFF));
            else
                snprintf(text, sizeof text, "%-5s $%s, $%s, %d", inm, RN[rt], RN[rs], imm);
        } else if (op == 0x03) {
            snprintf(text, sizeof text, "jal  0x%08x", (at & 0xF0000000) | ((w & 0x3FFFFFF) << 2));
        } else if (op == 0x02) {
            snprintf(text, sizeof text, "j    0x%08x", (at & 0xF0000000) | ((w & 0x3FFFFFF) << 2));
        } else if (w == 0) {
            snprintf(text, sizeof text, "nop");
        } else {
            snprintf(text, sizeof text, ".word 0x%08x  (op=0x%02x)", w, op);
        }
        printf("%c 0x%08x  %08x  %s\n", mark, at, w, text);
        step(v, w);
    }
    free(b);
    return 0;
}
