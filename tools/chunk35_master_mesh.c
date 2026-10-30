/*
 * tools/chunk35_master_mesh.c -- static decode of the LEVEL*.RAW chunk-34/35 MASTER MESH.
 *
 * WHY THIS EXISTS
 *   Chunk 35 is the terrain master mesh: the layer that draws LEVEL01's big brown wall/terrain
 *   masses through FUNC_800172DC as GP0(3c) quads. It is the ONE layer a Tier-3 replacement level
 *   still cannot author -- the on-disc format is not the runtime buffer, and a blanket 0x30-stride
 *   edit over its blocks CRASHES the load, while an identity recompress and a single aligned vertex
 *   edit both boot (memory `walls-are-chunk35`, 2026-07-04). Replacing the layer needs to know which
 *   bytes are coordinates and which are draw commands.
 *
 *   The authority for that is the CODE that reads it, not a pattern guess over the bytes. So this
 *   tool disassembles the loader/converter out of the pristine EXE and, separately, walks the
 *   decompressed chunk under whatever structural hypothesis the caller asks for -- keeping the two
 *   universes apart so a plausible-looking parse can never be mistaken for a proven one.
 *
 * MODES
 *   disasm  <SCUS_942.88> <va> <count>     annotated MIPS from a virtual address
 *   xref    <SCUS_942.88> <va>             aligned words that materialise or branch to <va>
 *   header  <chunk.dec>                    header bytes + candidate count fields
 *   scan    <chunk.dec> <off>              structural census of the stream from <off>
 *
 * FRAMES
 *   PS-X EXE: 0x800 header, text loaded at 0x80010000. All <va> arguments are virtual.
 *
 * NOTHING HERE IS CANON. The disassembly is mechanical and exact; every structural claim about the
 * chunk bytes is a HYPOTHESIS until a decoded field is shown to be read by a disassembled
 * instruction at a known offset.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_HDR   0x800u
#define EXE_BASE  0x80010000u

static unsigned char *g_buf;
static size_t g_len;

static int load(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); return -1; }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    g_buf = malloc((size_t)n);
    if (!g_buf || fread(g_buf, 1, (size_t)n, f) != (size_t)n) {
        fprintf(stderr, "read failed: %s\n", path); fclose(f); return -1;
    }
    g_len = (size_t)n;
    fclose(f);
    return 0;
}

static uint32_t rd32(size_t off)
{
    if (off + 4 > g_len) return 0;
    return (uint32_t)g_buf[off] | ((uint32_t)g_buf[off + 1] << 8)
         | ((uint32_t)g_buf[off + 2] << 16) | ((uint32_t)g_buf[off + 3] << 24);
}

static uint16_t rd16(size_t off)
{
    if (off + 2 > g_len) return 0;
    return (uint16_t)((uint32_t)g_buf[off] | ((uint32_t)g_buf[off + 1] << 8));
}

static size_t va_off(uint32_t va) { return EXE_HDR + (size_t)(va - EXE_BASE); }

static const char *REG[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3",
    "t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7",
    "t8","t9","k0","k1","gp","sp","fp","ra"
};

/* ---------------------------------------------------------------- disasm */

static void disasm_one(uint32_t va, uint32_t w, char *out, size_t cap)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    uint32_t rd = (w >> 11) & 31, sa = (w >> 6) & 31, fn = w & 63;
    int16_t  imm = (int16_t)(w & 0xFFFF);
    uint32_t tgt = (va & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
    uint32_t br  = va + 4 + ((int32_t)imm << 2);

    if (w == 0) { snprintf(out, cap, "nop"); return; }

    switch (op) {
    case 0x00:
        switch (fn) {
        case 0x00: snprintf(out, cap, "sll     %s, %s, %u", REG[rd], REG[rt], sa); return;
        case 0x02: snprintf(out, cap, "srl     %s, %s, %u", REG[rd], REG[rt], sa); return;
        case 0x03: snprintf(out, cap, "sra     %s, %s, %u", REG[rd], REG[rt], sa); return;
        case 0x04: snprintf(out, cap, "sllv    %s, %s, %s", REG[rd], REG[rt], REG[rs]); return;
        case 0x06: snprintf(out, cap, "srlv    %s, %s, %s", REG[rd], REG[rt], REG[rs]); return;
        case 0x07: snprintf(out, cap, "srav    %s, %s, %s", REG[rd], REG[rt], REG[rs]); return;
        case 0x08: snprintf(out, cap, "jr      %s", REG[rs]); return;
        case 0x09: snprintf(out, cap, "jalr    %s, %s", REG[rd], REG[rs]); return;
        case 0x0C: snprintf(out, cap, "syscall"); return;
        case 0x10: snprintf(out, cap, "mfhi    %s", REG[rd]); return;
        case 0x12: snprintf(out, cap, "mflo    %s", REG[rd]); return;
        case 0x18: snprintf(out, cap, "mult    %s, %s", REG[rs], REG[rt]); return;
        case 0x19: snprintf(out, cap, "multu   %s, %s", REG[rs], REG[rt]); return;
        case 0x1A: snprintf(out, cap, "div     %s, %s", REG[rs], REG[rt]); return;
        case 0x1B: snprintf(out, cap, "divu    %s, %s", REG[rs], REG[rt]); return;
        case 0x20: snprintf(out, cap, "add     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x21: snprintf(out, cap, "addu    %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x22: snprintf(out, cap, "sub     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x23: snprintf(out, cap, "subu    %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x24: snprintf(out, cap, "and     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x25: snprintf(out, cap, "or      %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x26: snprintf(out, cap, "xor     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x27: snprintf(out, cap, "nor     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x2A: snprintf(out, cap, "slt     %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        case 0x2B: snprintf(out, cap, "sltu    %s, %s, %s", REG[rd], REG[rs], REG[rt]); return;
        default:   snprintf(out, cap, ".word   0x%08x  ; special fn=0x%02x", w, fn); return;
        }
    case 0x01:
        switch (rt) {
        case 0x00: snprintf(out, cap, "bltz    %s, 0x%08x", REG[rs], br); return;
        case 0x01: snprintf(out, cap, "bgez    %s, 0x%08x", REG[rs], br); return;
        case 0x10: snprintf(out, cap, "bltzal  %s, 0x%08x", REG[rs], br); return;
        case 0x11: snprintf(out, cap, "bgezal  %s, 0x%08x", REG[rs], br); return;
        default:   snprintf(out, cap, ".word   0x%08x  ; regimm rt=0x%02x", w, rt); return;
        }
    case 0x02: snprintf(out, cap, "j       0x%08x", tgt); return;
    case 0x03: snprintf(out, cap, "jal     0x%08x", tgt); return;
    case 0x04:
        if (rt == 0 && rs == 0) snprintf(out, cap, "b       0x%08x", br);
        else snprintf(out, cap, "beq     %s, %s, 0x%08x", REG[rs], REG[rt], br);
        return;
    case 0x05: snprintf(out, cap, "bne     %s, %s, 0x%08x", REG[rs], REG[rt], br); return;
    case 0x06: snprintf(out, cap, "blez    %s, 0x%08x", REG[rs], br); return;
    case 0x07: snprintf(out, cap, "bgtz    %s, 0x%08x", REG[rs], br); return;
    case 0x08: snprintf(out, cap, "addi    %s, %s, %d", REG[rt], REG[rs], imm); return;
    case 0x09: snprintf(out, cap, "addiu   %s, %s, %d", REG[rt], REG[rs], imm); return;
    case 0x0A: snprintf(out, cap, "slti    %s, %s, %d", REG[rt], REG[rs], imm); return;
    case 0x0B: snprintf(out, cap, "sltiu   %s, %s, %d", REG[rt], REG[rs], imm); return;
    case 0x0C: snprintf(out, cap, "andi    %s, %s, 0x%04x", REG[rt], REG[rs], (uint16_t)imm); return;
    case 0x0D: snprintf(out, cap, "ori     %s, %s, 0x%04x", REG[rt], REG[rs], (uint16_t)imm); return;
    case 0x0E: snprintf(out, cap, "xori    %s, %s, 0x%04x", REG[rt], REG[rs], (uint16_t)imm); return;
    case 0x0F: snprintf(out, cap, "lui     %s, 0x%04x", REG[rt], (uint16_t)imm); return;
    case 0x10: snprintf(out, cap, "cop0    0x%07x", w & 0x1FFFFFF); return;
    case 0x12:
        if (rs == 0x00) { snprintf(out, cap, "mfc2    %s, $%u", REG[rt], rd); return; }
        if (rs == 0x02) { snprintf(out, cap, "cfc2    %s, $%u", REG[rt], rd); return; }
        if (rs == 0x04) { snprintf(out, cap, "mtc2    %s, $%u", REG[rt], rd); return; }
        if (rs == 0x06) { snprintf(out, cap, "ctc2    %s, $%u", REG[rt], rd); return; }
        snprintf(out, cap, "cop2    0x%07x", w & 0x1FFFFFF); return;
    case 0x20: snprintf(out, cap, "lb      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x21: snprintf(out, cap, "lh      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x22: snprintf(out, cap, "lwl     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x23: snprintf(out, cap, "lw      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x24: snprintf(out, cap, "lbu     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x25: snprintf(out, cap, "lhu     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x26: snprintf(out, cap, "lwr     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x28: snprintf(out, cap, "sb      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x29: snprintf(out, cap, "sh      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x2A: snprintf(out, cap, "swl     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x2B: snprintf(out, cap, "sw      %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x2E: snprintf(out, cap, "swr     %s, %d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x32: snprintf(out, cap, "lwc2    $%u, %d(%s)", rt, imm, REG[rs]); return;
    case 0x3A: snprintf(out, cap, "swc2    $%u, %d(%s)", rt, imm, REG[rs]); return;
    default:   snprintf(out, cap, ".word   0x%08x  ; op=0x%02x", w, op); return;
    }
}

static int cmd_disasm(const char *path, uint32_t va, uint32_t count)
{
    if (load(path)) return 1;
    printf("; disassembly of 0x%08x .. 0x%08x (%u instructions) from %s\n",
           va, va + count * 4 - 4, count, path);
    for (uint32_t i = 0; i < count; i++) {
        uint32_t a = va + i * 4;
        size_t o = va_off(a);
        if (o + 4 > g_len) { printf("; --- past end of image ---\n"); break; }
        uint32_t w = rd32(o);
        char t[128];
        disasm_one(a, w, t, sizeof t);
        printf("0x%08x  %08x  %s\n", a, w, t);
    }
    return 0;
}

/* Aligned words that reference a target: direct j/jal, and lui/addiu-ori halves. */
static int cmd_xref(const char *path, uint32_t va)
{
    if (load(path)) return 1;
    uint32_t hi = (va >> 16) & 0xFFFF, lo = va & 0xFFFF;
    uint32_t hi_carry = ((va + 0x8000) >> 16) & 0xFFFF;   /* addiu sign-extends */
    printf("; references to 0x%08x in %s\n", va, path);
    printf("; direct j/jal\n");
    long n = 0;
    for (size_t o = EXE_HDR; o + 4 <= g_len; o += 4) {
        uint32_t w = rd32(o);
        uint32_t a = EXE_BASE + (uint32_t)(o - EXE_HDR);
        uint32_t op = w >> 26;
        if (op == 2 || op == 3) {
            uint32_t tgt = (a & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
            if (tgt == va) { char t[128]; disasm_one(a, w, t, sizeof t);
                             printf("0x%08x  %08x  %s\n", a, w, t); n++; }
        }
    }
    printf("; %ld direct\n; lui halves (hi=0x%04x or 0x%04x, then lo=0x%04x within 8 words)\n",
           n, hi, hi_carry, lo);
    n = 0;
    for (size_t o = EXE_HDR; o + 4 <= g_len; o += 4) {
        uint32_t w = rd32(o);
        if ((w >> 26) != 0x0F) continue;                  /* lui */
        uint32_t imm = w & 0xFFFF;
        if (imm != hi && imm != hi_carry) continue;
        uint32_t rt = (w >> 16) & 31;
        for (size_t k = 1; k <= 8 && o + k * 4 + 4 <= g_len; k++) {
            uint32_t w2 = rd32(o + k * 4);
            uint32_t op2 = w2 >> 26, rs2 = (w2 >> 21) & 31;
            if (rs2 != rt) continue;
            uint16_t i2 = (uint16_t)(w2 & 0xFFFF);
            int hit = ((op2 == 0x09 || op2 == 0x08) && imm == hi_carry && i2 == lo)   /* addiu */
                   || (op2 == 0x0D && imm == hi && i2 == lo);                          /* ori   */
            if (hit) {
                uint32_t a = EXE_BASE + (uint32_t)(o - EXE_HDR);
                char t1[128], t2[128];
                disasm_one(a, w, t1, sizeof t1);
                disasm_one(a + (uint32_t)k * 4, w2, t2, sizeof t2);
                printf("0x%08x  %s   +0x%02zx  %s\n", a, t1, k * 4, t2);
                n++;
                break;
            }
        }
    }
    printf("; %ld materialised\n", n);
    return 0;
}

/* ---------------------------------------------------------------- chunk */

static int cmd_header(const char *path)
{
    if (load(path)) return 1;
    printf("file %s: %zu bytes\n", path, g_len);
    printf("first 0x40 bytes:\n");
    for (size_t r = 0; r < 0x40 && r < g_len; r += 16) {
        printf("  +0x%02zx ", r);
        for (size_t c = 0; c < 16 && r + c < g_len; c++) printf("%02x ", g_buf[r + c]);
        printf(" |");
        for (size_t c = 0; c < 16 && r + c < g_len; c++) {
            unsigned char ch = g_buf[r + c];
            putchar(ch >= 32 && ch < 127 ? ch : '.');
        }
        printf("|\n");
    }
    printf("candidate count fields (small plausible values):\n");
    for (size_t o = 0; o < 0x20 && o + 4 <= g_len; o++) {
        uint16_t h = rd16(o);
        uint32_t w = rd32(o);
        if (h > 0 && h < 4096) printf("  u16 @+0x%02zx = %u\n", o, h);
        if (w > 0 && w < 4096) printf("  u32 @+0x%02zx = %u\n", o, w);
    }
    return 0;
}

/*
 * Structural census from `off`: treat the stream as 0x30-byte blocks (the runtime render-quad
 * stride recorded for buffer 0x8012c1d0) and report, per block, how self-consistent that reading
 * is. A block whose four candidate vertex words carry plausible s16 coordinate pairs is COORDLIKE;
 * anything else is reported verbatim so the command bytes stay visible instead of being assumed.
 */
static int cmd_scan(const char *path, size_t off)
{
    if (load(path)) return 1;
    printf("scan %s from +0x%zx, 0x30-byte blocks (%zu bytes -> %zu blocks max)\n",
           path, off, g_len - off, (g_len - off) / 0x30);
    size_t coordlike = 0, other = 0, shown = 0;
    for (size_t p = off; p + 0x30 <= g_len; p += 0x30) {
        int ok = 1;
        int32_t ys[4];
        for (int v = 0; v < 4; v++) {
            uint32_t w = rd32(p + 0x04 + (size_t)v * 8);
            int16_t lo = (int16_t)(w & 0xFFFF), hi = (int16_t)(w >> 16);
            ys[v] = hi;
            if (lo < -20000 || lo > 20000 || hi < -20000 || hi > 20000) ok = 0;
        }
        if (ok) coordlike++; else other++;
        if (shown < 12) {
            printf("  +0x%05zx %s ys=[%6d %6d %6d %6d]  raw:",
                   p, ok ? "COORDLIKE" : "other    ", ys[0], ys[1], ys[2], ys[3]);
            for (int b = 0; b < 16; b++) printf(" %02x", g_buf[p + b]);
            printf(" ...\n");
            shown++;
        }
    }
    printf("blocks: %zu coordlike, %zu other\n", coordlike, other);
    return 0;
}


/*
 * WALK -- the structural hypothesis, stated so it can FAIL.
 *
 * Hypothesis: the master mesh is a sequence of GROUPS. Each group is
 *   [primitive records...] 0x00000000 [u32 vcount] [vcount x 8B vertex] [u16 index list]
 * where a primitive record starts with a word whose HIGH byte is a GP0 polygon command
 * (0x20..0x3F) and whose low 3 bytes are an RGB colour, and its length follows the standard
 * GP0 field rules (gouraud -> one colour word per vertex, textured -> one uv word per vertex).
 * A vertex is s16 X, s16 Y, s16 Z, u16 tail. The index list runs until the next word looks
 * like a primitive record again.
 *
 * The test is byte accounting: if this consumes the chunk EXACTLY and the group count matches
 * the header field, the decode is real. Any shortfall, overrun or unknown command is printed --
 * a walk that ends early is a refutation, not a rounding error.
 */
static int gp0_words(unsigned cmd)
{
    if (cmd < 0x20 || cmd > 0x3F) return 0;
    int nverts   = (cmd & 0x08) ? 4 : 3;
    int textured = (cmd & 0x04) ? 1 : 0;
    int gouraud  = (cmd & 0x10) ? 1 : 0;
    return (gouraud ? nverts : 1) + nverts + (textured ? nverts : 0);
}

static int looks_like_prim(size_t p)
{
    if (p + 4 > g_len) return 0;
    unsigned cmd = g_buf[p + 3];
    return gp0_words(cmd) != 0;
}

static int cmd_walk(const char *path, size_t off)
{
    if (load(path)) return 1;
    printf("walk %s from +0x%zx (%zu bytes total)\n", path, off, g_len);
    size_t p = off;
    long groups = 0, prims = 0, verts = 0, idxs = 0;
    long cmd_hist[0x40]; memset(cmd_hist, 0, sizeof cmd_hist);
    while (p < g_len) {
        /* primitive run */
        long gp = 0;
        while (p + 4 <= g_len && looks_like_prim(p)) {
            unsigned cmd = g_buf[p + 3];
            int w = gp0_words(cmd);
            if (p + (size_t)w * 4 > g_len) { printf("  +0x%05zx TRUNCATED prim cmd=0x%02x\n", p, cmd); p = g_len; break; }
            cmd_hist[cmd]++; prims++; gp++;
            p += (size_t)w * 4;
        }
        if (p >= g_len) break;
        uint32_t w0 = rd32(p);
        if (w0 != 0) {
            printf("  +0x%05zx STOP: expected 0x00000000 group terminator, got 0x%08x "
                   "(after %ld prims in this group)\n", p, w0, gp);
            break;
        }
        if (p + 8 > g_len) { printf("  +0x%05zx END: %zu trailing byte(s) after the last group\n",
                                    p, g_len - p); p = g_len; break; }
        p += 4;
        /* A 0x00000000 word is NOT always a group terminator: at +0x4e8 it is followed by
         * another GP0(0x34) record, so it also serves as a run separator. Only treat it as a
         * terminator when what follows is not itself a primitive. */
        if (looks_like_prim(p)) continue;
        uint32_t vc = rd32(p); p += 4;
        if (vc > 0xFFFF || p + (size_t)vc * 8 > g_len) {
            printf("  +0x%05zx STOP: implausible vertex count %u\n", p - 4, vc);
            break;
        }
        p += (size_t)vc * 8; verts += vc;
        size_t idx0 = p;
        /* Indices are u16 but a primitive record is word-aligned, so only WORD-aligned
         * positions may end the list -- testing every halfword found a phantom primitive
         * at +0x24e and derailed the walk two groups in. */
        while (p + 4 <= g_len && !(p % 4 == 0 && looks_like_prim(p))) p += 2;
        if (p > g_len) p = g_len;
        idxs += (long)((p - idx0) / 2);
        groups++;
        if (groups <= 6 || p >= g_len)
            printf("  group %2ld: %ld prims, %u verts, %zu indices, ends +0x%05zx\n",
                   groups, gp, vc, (p - idx0) / 2, p);
    }
    printf("consumed to +0x%05zx of 0x%05zx -- %s\n", p, g_len,
           p == g_len ? "EXACT, the grammar accounts for every byte"
                      : "RESIDUAL, the grammar does NOT account for every byte");
    printf("groups=%ld prims=%ld verts=%ld indices=%ld\n", groups, prims, verts, idxs);
    printf("GP0 command histogram:\n");
    for (unsigned c = 0x20; c < 0x40; c++)
        if (cmd_hist[c]) printf("   0x%02x (%d-pt %s%s): %ld\n", c,
            (c & 8) ? 4 : 3, (c & 4) ? "textured " : "flat ", (c & 0x10) ? "gouraud" : "solid",
            cmd_hist[c]);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr,
            "usage:\n"
            "  %s disasm <SCUS_942.88> <va-hex> <count>\n"
            "  %s xref   <SCUS_942.88> <va-hex>\n"
            "  %s header <chunk.dec>\n"
            "  %s scan   <chunk.dec> <off-hex>\n"
            "  %s walk   <chunk.dec> <off-hex>\n", argv[0], argv[0], argv[0], argv[0], argv[0]);
        return 2;
    }
    if (!strcmp(argv[1], "disasm") && argc >= 5)
        return cmd_disasm(argv[2], (uint32_t)strtoul(argv[3], NULL, 16),
                          (uint32_t)strtoul(argv[4], NULL, 0));
    if (!strcmp(argv[1], "xref") && argc >= 4)
        return cmd_xref(argv[2], (uint32_t)strtoul(argv[3], NULL, 16));
    if (!strcmp(argv[1], "header") && argc >= 3)
        return cmd_header(argv[2]);
    if (!strcmp(argv[1], "scan") && argc >= 4)
        return cmd_scan(argv[2], (size_t)strtoul(argv[3], NULL, 16));
    if (!strcmp(argv[1], "walk") && argc >= 4)
        return cmd_walk(argv[2], (size_t)strtoul(argv[3], NULL, 16));
    fprintf(stderr, "bad arguments\n");
    return 2;
}
