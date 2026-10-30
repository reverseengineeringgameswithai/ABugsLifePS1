/* hoisted_load_idiom_scan -- enumerate every load the compiler moved ABOVE its
 * own bounds check.
 *
 * WHY THIS EXISTS
 * ---------------
 * An E16 campaign movie caught 0x80010BF4 reading a marker table. Four levels
 * later a second movie caught 0x80010D9C -- the identical instruction sequence,
 * 424 bytes away, in a duplicated copy of the same loop body:
 *
 *     sltu $a3, $t9, $s5      ; range test COMPUTED
 *     add  $t9, $t9, $s1      ; base + index
 *     lhu  $t9, 0($t9)        ; LOAD HAPPENS REGARDLESS
 *     beq  $a3, $zero, ...    ; range test ACTED ON, one instruction too late
 *
 * Finding these one movie at a time is not a method. GCC schedules the load into
 * the branch's shadow and discards the result on the failing path, so the read
 * is architecturally harmless but WILL touch whatever global happens to sit at
 * base+index -- and it will show up in any accessLog watch over that address,
 * looking exactly like an unenumerated consumer. Every watch-based investigation
 * in this project can be spoofed this way, so the family is worth enumerating
 * once, project-wide.
 *
 * WHAT IT MATCHES
 * ---------------
 * A four-instruction window, in order:
 *   [0] sltu/slt  rCond, rIdx, rLim        (register form; the bound test)
 *   [1] add/addu  rIdx,  rIdx, rBase       (address formed, base in a REGISTER)
 *   [2] load      rDst,  0(rIdx)           (any width)
 *   [3] beq/bne   rCond, $zero, target     (the test finally acted on)
 *
 * The signature is the ORDERING, not the opcodes: the comparison feeding [3] is
 * computed before the load and consumed after it. Allowing one filler
 * instruction between [1] and [2] would widen the net; it is deliberately not
 * allowed, so this reports a floor rather than a guess.
 *
 * WHAT A HIT IS AND IS NOT
 * ------------------------
 * A hit is NOT a bug in the game -- the discard makes it correct. It is a
 * known-benign source of stray reads. Anything this reports should be treated as
 * incidental in a watch investigation unless a materialisation site says the
 * address could have been formed deliberately
 * (tools/const_address_materialization.c).
 *
 * Build:  cc -O2 -Wall -Wextra -Werror -o /tmp/hls tools/hoisted_load_idiom_scan.c
 * Usage:  /tmp/hls SCUS_942.88 [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO 0x80010000u
#define TEXT_HI 0x80082800u
#define HDR     0x800u
#define MAXHIT  512

struct hit {
    uint32_t load_pc;     /* the load itself */
    uint32_t logged_pc;   /* what accessLog will report (load_pc + 4) */
    uint32_t cmp_pc, branch_pc;
    uint32_t idx_reg, base_reg, cond_reg;
    const char *width;
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

static const char *load_width(uint32_t op)
{
    switch (op) {
    case 0x20: return "lb";
    case 0x21: return "lh";
    case 0x23: return "lw";
    case 0x24: return "lbu";
    case 0x25: return "lhu";
    default:   return NULL;
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s <exe> [--json out]\n", argv[0]); return 2; }
    const char *jsonout = NULL;
    for (int i = 2; i < argc; i++)
        if (!strcmp(argv[i], "--json") && i + 1 < argc) jsonout = argv[++i];

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); img_len = ftell(f); fseek(f, 0, SEEK_SET);
    img = malloc((size_t)img_len);
    if (!img || fread(img, 1, (size_t)img_len, f) != (size_t)img_len) {
        fprintf(stderr, "read failed\n"); return 2;
    }
    fclose(f);
    if (img_len < 0x800 || memcmp(img, "PS-X EXE", 8) != 0) {
        fprintf(stderr, "not a PSX-EXE\n"); return 2;
    }
    /* Pin the two instances the campaign actually caught. If these stop decoding
     * as the idiom, the image is not the one this was written against. */
    if (rd32(0x80010BF4u) != 0x97390000u || rd32(0x80010D9Cu) != 0x97390000u) {
        fprintf(stderr, "pinned instructions do not match; wrong image\n"); return 2;
    }

    static struct hit hits[MAXHIT];
    int nh = 0;
    for (uint32_t pc = TEXT_LO; pc + 12 < TEXT_HI && nh < MAXHIT; pc += 4) {
        uint32_t w0 = rd32(pc), w1 = rd32(pc + 4), w2 = rd32(pc + 8), w3 = rd32(pc + 12);

        /* [0] slt/sltu rCond, rIdx, rLim  (SPECIAL, funct 0x2A/0x2B) */
        if ((w0 >> 26) != 0u) continue;
        uint32_t f0 = w0 & 0x3Fu;
        if (f0 != 0x2Au && f0 != 0x2Bu) continue;
        uint32_t cond = (w0 >> 11) & 31, idx0 = (w0 >> 21) & 31;
        if (cond == 0u) continue;

        /* [1] add/addu rIdx, rIdx, rBase  (funct 0x20/0x21), same rIdx */
        if ((w1 >> 26) != 0u) continue;
        uint32_t f1 = w1 & 0x3Fu;
        if (f1 != 0x20u && f1 != 0x21u) continue;
        uint32_t rd1 = (w1 >> 11) & 31, rs1 = (w1 >> 21) & 31, rt1 = (w1 >> 16) & 31;
        if (rd1 != idx0 || (rs1 != idx0 && rt1 != idx0)) continue;
        uint32_t base = (rs1 == idx0) ? rt1 : rs1;

        /* [2] load rDst, 0(rIdx) */
        const char *wd = load_width(w2 >> 26);
        if (!wd || ((w2 >> 21) & 31) != idx0 || (w2 & 0xFFFFu) != 0u) continue;

        /* [3] beq/bne rCond, $zero */
        uint32_t op3 = w3 >> 26;
        if (op3 != 4u && op3 != 5u) continue;
        uint32_t rs3 = (w3 >> 21) & 31, rt3 = (w3 >> 16) & 31;
        if (!((rs3 == cond && rt3 == 0u) || (rt3 == cond && rs3 == 0u))) continue;

        hits[nh].load_pc = pc + 8;
        hits[nh].logged_pc = pc + 12;
        hits[nh].cmp_pc = pc;
        hits[nh].branch_pc = pc + 12;
        hits[nh].idx_reg = idx0;
        hits[nh].base_reg = base;
        hits[nh].cond_reg = cond;
        hits[nh].width = wd;
        nh++;
    }

    printf("hoisted-load sites (load above its own bounds check): %d\n\n", nh);
    for (int i = 0; i < nh; i++)
        printf("  load 0x%08X  %-3s  logs as 0x%08X   idx=r%-2u base=r%-2u cond=r%-2u\n",
               hits[i].load_pc, hits[i].width, hits[i].logged_pc,
               hits[i].idx_reg, hits[i].base_reg, hits[i].cond_reg);

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"Every load the compiler scheduled above the branch "
                   "that bounds it. Regenerate: tools/hoisted_load_idiom_scan.c\",\n");
        fprintf(j, " \"why\": \"These reads touch base+index REGARDLESS of the range test "
                   "and discard the result on the failing path. Harmless to the game, but "
                   "they appear in any accessLog watch over the address they overrun and "
                   "look exactly like an unenumerated consumer. Two were found the slow way, "
                   "one movie at a time, before this existed.\",\n");
        fprintf(j, " \"match\": \"slt/sltu rCond,rIdx,rLim ; add/addu rIdx,rIdx,rBase ; "
                   "load rDst,0(rIdx) ; beq/bne rCond,zero -- contiguous, no filler allowed, "
                   "so this is a floor.\",\n");
        fprintf(j, " \"note\": \"accessLog reports the instruction AFTER the access, so match "
                   "watch events against logged_pc, not load_pc.\",\n");
        fprintf(j, " \"sites\": %d,\n \"hits\": [\n", nh);
        for (int i = 0; i < nh; i++)
            fprintf(j, "  {\"load_pc\": \"0x%08X\", \"logged_pc\": \"0x%08X\", "
                       "\"width\": \"%s\", \"cmp_pc\": \"0x%08X\", \"branch_pc\": \"0x%08X\", "
                       "\"idx_reg\": %u, \"base_reg\": %u, \"cond_reg\": %u}%s\n",
                    hits[i].load_pc, hits[i].logged_pc, hits[i].width, hits[i].cmp_pc,
                    hits[i].branch_pc, hits[i].idx_reg, hits[i].base_reg, hits[i].cond_reg,
                    i + 1 < nh ? "," : "");
        fprintf(j, " ]\n}\n");
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(img);
    return 0;
}
