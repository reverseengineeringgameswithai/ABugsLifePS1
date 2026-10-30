/* const_address_materialization -- who can even FORM a pointer to these bytes?
 *
 * THE QUESTION THIS SCANS
 * -----------------------
 * E16's static frontier was built by censusing INDEXED ACCESSES whose base is a
 * `lui` constant. An any% campaign movie then caught a read of a marker table
 * from 0x80010BF4:
 *
 *     0x80010bec  sltu $a3, $t9, $s5     ; range test computed
 *     0x80010bf0  add  $t9, $t9, $s1     ; base is a REGISTER
 *     0x80010bf4  lhu  $t9, 0($t9)       ; the access
 *     0x80010bf8  beq  $a3, $zero, ...   ; range test acted on, one instr too late
 *
 * The base is a register, so no function-list repair would make this fixed-form
 * scan see the access. This tool therefore answers a narrower question: which
 * locally tracked `lui` plus `addiu`/`ori` or displacement encodings produce an
 * address in the requested ranges?
 *
 * Correction history: an earlier revision promoted that result to a complete
 * deliberate-access frontier. That was wrong. A pointer may be stored, reloaded,
 * passed, copied, or derived through an encoding this linear tracker does not
 * model. Absence from this output is not proof that an address is unreachable.
 *
 * WHAT IT REPORTS
 * ---------------
 * Every site materialising a constant inside a requested range, in three forms:
 *   ADDR_TAKE   lui rX,hi ; addiu/ori rX,rX,lo      -- a bare pointer, no access
 *   ACCESS      lui rX,hi ; load/store disp(rX)     -- the classic direct access
 *   NEAR        the same, landing within --slack bytes of the range
 * NEAR matters: an object based just below a table is exactly what an overrun
 * arrives from, so the near-misses name the suspects.
 *
 * SCOPE, STATED HONESTLY
 * ----------------------
 * Scans the whole text segment linearly, so it examines the 46 KB of live code the
 * function census omits (see tools/text_coverage_audit.c). It has no CFG merge,
 * carries state across function boundaries, and invalidates only selected register
 * writes. Those choices can create false pairs or miss a real pair; this is not a
 * sound superset claim.
 *
 * It does NOT chase pointers stored to memory and reloaded elsewhere. A site
 * that materialises A and stores it into a global is reported here; the reload
 * is not. So this bounds WHERE POINTERS ARE BORN, not every register that ever
 * holds one. The reported five E16 sites are scanner hits, not an access closure.
 *
 * Build:  cc -O2 -Wall -Wextra -Werror -o /tmp/cam tools/const_address_materialization.c
 * Usage:  /tmp/cam SCUS_942.88 --range 0x8009B5A8 0x8009B648 \
 *                              --range 0x8009C210 0x8009C230 \
 *                              --range 0x800A65B0 0x800A65D0 \
 *                              [--slack 512] [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO 0x80010000u
#define TEXT_HI 0x80082800u
#define HDR     0x800u
#define MAXR    16
#define MAXSITE 8192

struct range { uint32_t lo, hi; };
struct site {
    uint32_t pc;        /* the instruction that completes the constant */
    uint32_t lui_pc;    /* where the high half came from */
    uint32_t addr;      /* the materialised address */
    int      range_idx;
    int      kind;      /* 0 ADDR_TAKE, 1 ACCESS, 2 NEAR */
    char     detail[64];
    uint32_t consumer_pc;   /* first in-block use of the bare pointer */
    uint32_t consumer_ea;
    int      consumer_valid;
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

static int is_mem_op(uint32_t op)
{
    /* lb lh lwl lw lbu lhu lwr | sb sh swl sw swr | lwc2 swc2 */
    return (op >= 0x20u && op <= 0x26u) || (op >= 0x28u && op <= 0x2Eu) ||
           op == 0x32u || op == 0x3Au;
}

static const char *KIND[3] = {"ADDR_TAKE", "ACCESS", "NEAR"};

/* A bare ADDR_TAKE is only meaningful once you know what USES the pointer.
 * Find the first load/store in the same basic block that takes `reg` as its base.
 *
 * Deliberately conservative: stops at the first control transfer (after its delay
 * slot) and when the register is redefined, so it may report NO consumer where a
 * real one exists further on. It will not report a wrong one, which is the
 * property a frontier claim depends on. */
static void find_consumer(uint32_t pc, uint32_t reg, uint32_t addr,
                          uint32_t *out_pc, uint32_t *out_ea, int *ok)
{
    *ok = 0;
    for (uint32_t p = pc + 4; p < TEXT_HI && p < pc + 4 * 64; p += 4) {
        uint32_t w = rd32(p), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;

        if (is_mem_op(op) && rs == reg) {
            *out_pc = p;
            *out_ea = addr + (uint32_t)(int32_t)(int16_t)(w & 0xFFFFu);
            *ok = 1;
            return;
        }
        /* end of basic block: consume the delay slot, then stop */
        int is_jump = (op == 2u || op == 3u);
        int is_br = (op == 1u || (op >= 4u && op <= 7u) || (op >= 0x14u && op <= 0x17u));
        int is_jr = (op == 0u && ((w & 0x3Fu) == 8u || (w & 0x3Fu) == 9u));
        if (is_jump || is_br || is_jr) {
            uint32_t d = rd32(p + 4), dop = d >> 26;
            if (is_mem_op(dop) && ((d >> 21) & 31) == reg) {
                *out_pc = p + 4;
                *out_ea = addr + (uint32_t)(int32_t)(int16_t)(d & 0xFFFFu);
                *ok = 1;
            }
            return;
        }
        /* redefinition of the pointer register ends its life */
        if (op == 0u) {                       /* SPECIAL: rd is the destination */
            if (((w >> 11) & 31) == reg) return;
        } else if (op == 0x0Fu || op == 0x09u || op == 0x0Du || op == 0x0Cu ||
                   op == 0x0Au || op == 0x0Bu || op == 0x0Eu ||
                   (is_mem_op(op) && op < 0x28u)) {
            if (rt == reg) return;
        }
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <exe> --range LO HI [--range ...] "
                        "[--slack N] [--json out]\n", argv[0]);
        return 2;
    }
    struct range ranges[16];
    int nr = 0;
    uint32_t slack = 512;
    const char *jsonout = NULL;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--range") && i + 2 < argc && nr < 16) {
            ranges[nr].lo = (uint32_t)strtoul(argv[i + 1], NULL, 0);
            ranges[nr].hi = (uint32_t)strtoul(argv[i + 2], NULL, 0);
            nr++; i += 2;
        } else if (!strcmp(argv[i], "--slack") && i + 1 < argc) {
            slack = (uint32_t)strtoul(argv[++i], NULL, 0);
        } else if (!strcmp(argv[i], "--json") && i + 1 < argc) {
            jsonout = argv[++i];
        }
    }
    if (!nr) { fprintf(stderr, "no --range given\n"); return 2; }

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
    uint32_t t_addr = (uint32_t)img[0x18] | ((uint32_t)img[0x19] << 8) |
                      ((uint32_t)img[0x1A] << 16) | ((uint32_t)img[0x1B] << 24);
    if (t_addr != TEXT_LO) {
        fprintf(stderr, "t_addr 0x%08X != 0x%08X\n", t_addr, TEXT_LO); return 2;
    }

    static struct site sites[MAXSITE];
    int ns = 0;
    uint32_t hi_val[32] = {0}, hi_pc[32] = {0};
    int hi_ok[32] = {0};

    for (uint32_t pc = TEXT_LO; pc < TEXT_HI; pc += 4) {
        uint32_t w = rd32(pc), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        int16_t imm = (int16_t)(w & 0xFFFFu);

        if (op == 0x0Fu) {                       /* lui rt, imm */
            hi_val[rt] = (uint32_t)(w & 0xFFFFu) << 16;
            hi_pc[rt] = pc; hi_ok[rt] = 1;
            continue;
        }

        uint32_t addr = 0; int have = 0, kind = 0;
        char detail[64] = {0};

        if (op == 0x09u && hi_ok[rs]) {          /* addiu rt, rs, imm */
            addr = hi_val[rs] + (uint32_t)(int32_t)imm; have = 1; kind = 0;
            snprintf(detail, sizeof detail, "lui+addiu -> r%u", rt);
        } else if (op == 0x0Du && hi_ok[rs]) {   /* ori rt, rs, imm */
            addr = hi_val[rs] | (uint32_t)(w & 0xFFFFu); have = 1; kind = 0;
            snprintf(detail, sizeof detail, "lui+ori -> r%u", rt);
        } else if (is_mem_op(op) && hi_ok[rs]) { /* load/store disp(rs) */
            addr = hi_val[rs] + (uint32_t)(int32_t)imm; have = 1; kind = 1;
            snprintf(detail, sizeof detail, "%s disp(r%u)",
                     (op >= 0x28u) ? "store" : "load", rs);
        }

        /* writing a register kills its pending high half */
        if (op == 0x09u || op == 0x0Du || (is_mem_op(op) && op < 0x28u))
            hi_ok[rt] = 0;

        if (!have || ns >= MAXSITE) continue;
        for (int k = 0; k < nr; k++) {
            int in = (addr >= ranges[k].lo && addr < ranges[k].hi);
            int near = (!in && addr + slack >= ranges[k].lo &&
                        addr < ranges[k].hi + slack);
            if (!in && !near) continue;
            sites[ns].pc = pc; sites[ns].lui_pc = hi_pc[rs]; sites[ns].addr = addr;
            sites[ns].range_idx = k; sites[ns].kind = in ? kind : 2;
            snprintf(sites[ns].detail, sizeof sites[ns].detail, "%s", detail);
            if (sites[ns].kind == 0)
                find_consumer(pc, rt, addr, &sites[ns].consumer_pc,
                              &sites[ns].consumer_ea, &sites[ns].consumer_valid);
            ns++;
            break;
        }
    }

    int n_in = 0, n_take = 0, n_near = 0;
    for (int i = 0; i < ns; i++) {
        if (sites[i].kind == 2) n_near++;
        else { n_in++; if (sites[i].kind == 0) n_take++; }
    }

    printf("scanned 0x%08X..0x%08X linearly (%u bytes, includes the 46 KB the "
           "function census omits)\n", TEXT_LO, TEXT_HI, TEXT_HI - TEXT_LO);
    printf("materialisation sites INSIDE a requested range: %d (%d bare address-takes, "
           "%d direct accesses)\n", n_in, n_take, n_in - n_take);
    printf("near misses within %u bytes: %d\n\n", slack, n_near);
    for (int i = 0; i < ns; i++) {
        if (sites[i].kind == 2) continue;
        printf("  %-9s 0x%08X  -> 0x%08X  [range %d]  %s (lui at 0x%08X)",
               KIND[sites[i].kind], sites[i].pc, sites[i].addr,
               sites[i].range_idx, sites[i].detail, sites[i].lui_pc);
        if (sites[i].kind == 0) {
            if (sites[i].consumer_valid)
                printf("  consumed by 0x%08X (EA 0x%08X)",
                       sites[i].consumer_pc, sites[i].consumer_ea);
            else
                printf("  NO in-block consumer found");
        }
        printf("\n");
    }

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"Locally tracked lui-form materialisation hits "
                   "inside the requested ranges. Regenerate: tools/const_address_materialization.c\",\n");
        fprintf(j, " \"claim\": \"This is an encoding census of locally tracked lui plus "
                   "addiu/ori or displacement forms. It is not a complete pointer-birth or "
                   "access census.\",\n");
        fprintf(j, " \"correction_history\": \"An earlier claim said a missing hit meant "
                   "the address could not be reached deliberately and any access was incidental. "
                   "That was wrong because reloads, aliases, calls, CFG joins, and unmodelled "
                   "register definitions are outside this scanner.\",\n");
        fprintf(j, " \"scope\": \"Whole text scanned linearly, so the 46 KB omitted by the "
                   "function census is examined. Register state is not reset at function "
                   "boundaries, CFG merges are not modelled, and only selected clobbers are "
                   "handled. Pointers stored to memory and reloaded elsewhere are not chased.\",\n");
        fprintf(j, " \"slack_bytes\": %u,\n \"ranges\": [", slack);
        for (int k = 0; k < nr; k++)
            fprintf(j, "%s{\"lo\": \"0x%08X\", \"hi\": \"0x%08X\"}",
                    k ? ", " : "", ranges[k].lo, ranges[k].hi);
        fprintf(j, "],\n \"sites_inside\": %d,\n \"bare_address_takes\": %d,\n"
                   " \"direct_accesses\": %d,\n \"near_misses\": %d,\n \"sites\": [\n",
                n_in, n_take, n_in - n_take, n_near);
        int first = 1;
        for (int i = 0; i < ns; i++) {
            fprintf(j, "%s  {\"kind\": \"%s\", \"pc\": \"0x%08X\", \"lui_pc\": \"0x%08X\", "
                       "\"address\": \"0x%08X\", \"range\": %d, \"detail\": \"%s\"",
                    first ? "" : ",\n", KIND[sites[i].kind], sites[i].pc, sites[i].lui_pc,
                    sites[i].addr, sites[i].range_idx, sites[i].detail);
            if (sites[i].kind == 0) {
                if (sites[i].consumer_valid)
                    fprintf(j, ", \"consumer_pc\": \"0x%08X\", \"consumer_ea\": \"0x%08X\"",
                            sites[i].consumer_pc, sites[i].consumer_ea);
                else
                    fprintf(j, ", \"consumer_pc\": null");
            }
            fprintf(j, "}");
            first = 0;
        }
        fprintf(j, "\n ]\n}\n");
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(img);
    return 0;
}
