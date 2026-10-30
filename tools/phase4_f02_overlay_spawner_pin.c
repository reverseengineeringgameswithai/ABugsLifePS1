/* phase4_f02_overlay_spawner_pin -- pin the F02 debris spawner to a real overlay image.
 *
 * THE PROBLEM
 * -----------
 * The live Tunnels trace (analysis/phase4_f02_spawner_trace.json) recorded four
 * contact-pool callers in OVERLAY address space:
 *     ra 0x800B43F8  contact_alloc  717 calls   a3 = 0x5A   <- the debris spawner
 *     ra 0x800B436C  explicit_ctor  890 calls
 *     ra 0x800B3E34  contact_alloc  104 calls
 *     ra 0x800B4288  explicit_ctor   66 calls
 * Overlay space is REUSED: every level's overlay loads at the same base, so a bare
 * "0x800B43F8" names an address, not a file. The prior artifact recorded the spawner as
 * belonging to the LEVEL02 overlay because the row is called F02_tunnels -- that was an
 * assumption, never a measurement.
 *
 * THE METHOD
 * ----------
 * A `jal` at file offset K in an overlay loaded at base B returns to B + K + 8. So each
 * (file, base) pair PREDICTS a set of return addresses. Score every overlay image against
 * every plausible base and keep the pair that reproduces ALL FOUR recorded callers, with
 * the right call target (alloc vs explicit ctor) for each. That is a 4-constraint match on
 * a 2-parameter search, so a unique hit is strong evidence rather than a coincidence.
 *
 * Then, at the winning site, recover the ctorType by back-scanning for the instruction that
 * materialises a3 and the stack argument from the `sw rX, 0x10(sp)` that precedes the call,
 * and confirm a3 equals the 0x5A the live trace recorded. That closes the loop: the static
 * image and the live register agree.
 *
 * WHAT IT PRINTS
 * --------------
 * The scoreboard (so a near-miss is visible rather than hidden), the winning file+base, and
 * a disassembly of the call site with a3/stackArg resolved. It refuses to nominate a winner
 * that does not match all four callers.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/f02ovl tools/phase4_f02_overlay_spawner_pin.c
 * Usage: /tmp/f02ovl "OVL/"*.BIN [--json out.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define ALLOC 0x80059E44u          /* contact_alloc  (FUNC_80059E44) */
#define CTOR  0x8005A0E0u          /* explicit contact constructor   */
#define BASE_LO 0x800B3980u        /* plausible overlay load bases   */
#define BASE_HI 0x800B39C4u

/* the overlay-space callers the live Tunnels run recorded */
struct want { uint32_t ra; int is_alloc; int calls; const char *note; };
static const struct want WANT[] = {
    {0x800B43F8u, 1, 717, "debris spawner, a3=0x5A"},
    {0x800B436Cu, 0, 890, ""},
    {0x800B3E34u, 1, 104, ""},
    {0x800B4288u, 0,  66, ""},
};
#define NWANT ((int)(sizeof WANT / sizeof WANT[0]))

static uint32_t jal_word(uint32_t target)
{
    return 0x0C000000u | ((target >> 2) & 0x03FFFFFFu);
}

static uint32_t rd32(const uint8_t *d, long i)
{
    return (uint32_t)d[i] | ((uint32_t)d[i+1] << 8) |
           ((uint32_t)d[i+2] << 16) | ((uint32_t)d[i+3] << 24);
}

static const char *REG[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"
};

/* enough of MIPS I to read an argument-setup sequence */
static void disasm(uint32_t w, uint32_t pc, char *out, size_t n)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    uint32_t rd = (w >> 11) & 31, sa = (w >> 6) & 31, fn = w & 0x3F;
    int16_t imm = (int16_t)(w & 0xFFFFu);
    uint32_t uimm = w & 0xFFFFu;
    if (w == 0) { snprintf(out, n, "nop"); return; }
    switch (op) {
    case 0:
        switch (fn) {
        case 0x21: snprintf(out, n, "addu   %s,%s,%s", REG[rd], REG[rs], REG[rt]); return;
        case 0x23: snprintf(out, n, "subu   %s,%s,%s", REG[rd], REG[rs], REG[rt]); return;
        case 0x25: snprintf(out, n, "or     %s,%s,%s", REG[rd], REG[rs], REG[rt]); return;
        case 0x00: snprintf(out, n, "sll    %s,%s,%u", REG[rd], REG[rt], sa); return;
        case 0x02: snprintf(out, n, "srl    %s,%s,%u", REG[rd], REG[rt], sa); return;
        case 0x03: snprintf(out, n, "sra    %s,%s,%u", REG[rd], REG[rt], sa); return;
        case 0x08: snprintf(out, n, "jr     %s", REG[rs]); return;
        case 0x2A: snprintf(out, n, "slt    %s,%s,%s", REG[rd], REG[rs], REG[rt]); return;
        case 0x18: snprintf(out, n, "mult   %s,%s", REG[rs], REG[rt]); return;
        case 0x12: snprintf(out, n, "mflo   %s", REG[rd]); return;
        default:   snprintf(out, n, "op0.fn=0x%02x", fn); return;
        }
    case 2: snprintf(out, n, "j      0x%08X", ((pc + 4) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2)); return;
    case 3: snprintf(out, n, "jal    0x%08X", ((pc + 4) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2)); return;
    case 9: snprintf(out, n, "addiu  %s,%s,0x%x", REG[rt], REG[rs], uimm); return;
    case 0x0D: snprintf(out, n, "ori    %s,%s,0x%x", REG[rt], REG[rs], uimm); return;
    case 0x0C: snprintf(out, n, "andi   %s,%s,0x%x", REG[rt], REG[rs], uimm); return;
    case 0x0F: snprintf(out, n, "lui    %s,0x%x", REG[rt], uimm); return;
    case 0x0A: snprintf(out, n, "slti   %s,%s,0x%x", REG[rt], REG[rs], uimm); return;
    case 0x23: snprintf(out, n, "lw     %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x25: snprintf(out, n, "lhu    %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x24: snprintf(out, n, "lbu    %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x2B: snprintf(out, n, "sw     %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x29: snprintf(out, n, "sh     %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 0x28: snprintf(out, n, "sb     %s,%d(%s)", REG[rt], imm, REG[rs]); return;
    case 4: snprintf(out, n, "beq    %s,%s,0x%08X", REG[rs], REG[rt], pc + 4 + imm * 4); return;
    case 5: snprintf(out, n, "bne    %s,%s,0x%08X", REG[rs], REG[rt], pc + 4 + imm * 4); return;
    case 6: snprintf(out, n, "blez   %s,0x%08X", REG[rs], pc + 4 + imm * 4); return;
    case 7: snprintf(out, n, "bgtz   %s,0x%08X", REG[rs], pc + 4 + imm * 4); return;
    case 1: snprintf(out, n, "%s   %s,0x%08X", rt ? "bgez" : "bltz", REG[rs], pc + 4 + imm * 4); return;
    default: snprintf(out, n, "op=0x%02x", op); return;
    }
}

struct img { const char *path; uint8_t *d; long n; };

/* back-scan for the last instruction that sets a register to a constant before `at` */
static int const_reg_before(const struct img *m, long at, uint32_t reg, uint32_t *val)
{
    for (long j = at - 4; j >= 0 && j >= at - 200; j -= 4) {
        uint32_t w = rd32(m->d, j), op = w >> 26;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        if ((op == 9u || op == 0x0Du) && rt == reg && rs == 0u) { *val = w & 0xFFFFu; return 1; }
        /* any other definition of the register invalidates the constant */
        if (op == 0u && ((w >> 11) & 31) == reg && (w & 0x3F) != 0x08u) return 0;
        if ((op == 0x23u || op == 0x24u || op == 0x25u || op == 0x21u || op == 0x0Fu) && rt == reg) return 0;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *jsonout = NULL;
    const char *paths[64]; int npath = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--json") && i + 1 < argc) { jsonout = argv[++i]; continue; }
        if (npath < 64) paths[npath++] = argv[i];
    }
    if (!npath) { fprintf(stderr, "usage: %s OVL/*.BIN [--json out]\n", argv[0]); return 2; }

    const uint32_t JA = jal_word(ALLOC), JC = jal_word(CTOR);

    struct { const char *path; uint32_t base; int score; } board[512];
    int nb = 0, best = -1;

    for (int i = 0; i < npath; i++) {
        FILE *f = fopen(paths[i], "rb");
        if (!f) { perror(paths[i]); continue; }
        struct img m; m.path = paths[i];
        fseek(f, 0, SEEK_END); m.n = ftell(f); fseek(f, 0, SEEK_SET);
        m.d = malloc((size_t)m.n);
        if (!m.d || fread(m.d, 1, (size_t)m.n, f) != (size_t)m.n) { fclose(f); continue; }
        fclose(f);

        for (uint32_t base = BASE_LO; base <= BASE_HI; base += 4) {
            int score = 0;
            for (long k = 0; k + 4 <= m.n; k += 4) {
                uint32_t w = rd32(m.d, k);
                if (w != JA && w != JC) continue;
                uint32_t ra = base + (uint32_t)k + 8u;
                for (int q = 0; q < NWANT; q++)
                    if (WANT[q].ra == ra && WANT[q].is_alloc == (w == JA)) score++;
            }
            if (score > 0 && nb < 512) {
                board[nb].path = m.path; board[nb].base = base; board[nb].score = score;
                if (best < 0 || score > board[best].score) best = nb;
                nb++;
            }
        }
        free(m.d);
    }

    printf("scoreboard -- (overlay image, load base) scored against the %d overlay-space\n"
           "callers the live Tunnels run recorded:\n", NWANT);
    for (int i = 0; i < nb; i++)
        printf("  %d/%d  %-26s base 0x%08X%s\n", board[i].score, NWANT,
               board[i].path, board[i].base, i == best ? "   <== BEST" : "");
    if (best < 0) { fprintf(stderr, "\nno overlay matched any recorded caller\n"); return 3; }
    if (board[best].score != NWANT) {
        fprintf(stderr, "\nbest match is only %d/%d -- refusing to nominate a spawner overlay\n",
                board[best].score, NWANT);
        return 3;
    }
    /* uniqueness: no other pair may reach the same score */
    int ties = 0;
    for (int i = 0; i < nb; i++) if (board[i].score == NWANT) ties++;
    printf("\nwinner: %s @ base 0x%08X  (%d/%d, %s)\n", board[best].path, board[best].base,
           board[best].score, NWANT, ties == 1 ? "UNIQUE" : "NOT UNIQUE -- ambiguous");

    /* reload the winner and describe the debris call site */
    FILE *f = fopen(board[best].path, "rb");
    if (!f) { perror(board[best].path); return 2; }
    struct img m; m.path = board[best].path;
    fseek(f, 0, SEEK_END); m.n = ftell(f); fseek(f, 0, SEEK_SET);
    m.d = malloc((size_t)m.n);
    if (!m.d || fread(m.d, 1, (size_t)m.n, f) != (size_t)m.n) { fclose(f); return 2; }
    fclose(f);

    uint32_t base = board[best].base;
    long site = -1;
    for (long k = 0; k + 4 <= m.n; k += 4)
        if (rd32(m.d, k) == JA && base + (uint32_t)k + 8u == WANT[0].ra) site = k;
    if (site < 0) { fprintf(stderr, "debris call site vanished on reload\n"); return 3; }

    uint32_t a3 = 0, stackarg = 0;
    int have_a3 = const_reg_before(&m, site, 7 /*a3*/, &a3);
    /* stackArg is the 5th argument: `sw rX, 0x10(sp)` before the call */
    int have_sa = 0;
    for (long j = site - 4; j >= 0 && j >= site - 200; j -= 4) {
        uint32_t w = rd32(m.d, j);
        if ((w >> 26) == 0x2Bu && ((w >> 21) & 31) == 29u && (int16_t)(w & 0xFFFFu) == 0x10) {
            uint32_t src = (w >> 16) & 31, v;
            if (const_reg_before(&m, j, src, &v)) { stackarg = v; have_sa = 1; }
            break;
        }
    }

    printf("\ndebris call site (ra 0x%08X, %d calls in the traced run):\n", WANT[0].ra, WANT[0].calls);
    for (long k = site - 0x30; k <= site + 8 && k + 4 <= m.n; k += 4) {
        if (k < 0) continue;
        char t[64]; uint32_t pc = base + (uint32_t)k;
        disasm(rd32(m.d, k), pc, t, sizeof t);
        printf("  0x%08X  %08X  %s%s\n", pc, rd32(m.d, k), t,
               k == site ? "   <== jal contact_alloc" : "");
    }
    printf("\n  a3 (ctorType) : %s0x%02X%s\n", have_a3 ? "" : "(not an immediate) ", a3,
           have_a3 ? (a3 == 0x5A ? "   MATCHES the live trace's a3=0x5A"
                                 : "   *** DOES NOT match the live trace's a3=0x5A ***") : "");
    printf("  stackArg      : %s0x%02X  -> render/motion attr table A row %u\n",
           have_sa ? "" : "(unresolved) ", stackarg, stackarg);

    if (jsonout) {
        FILE *j = fopen(jsonout, "w");
        if (!j) { perror(jsonout); return 2; }
        fprintf(j, "{\n \"_comment\": \"F02 Tunnels: which overlay image actually contains the "
                   "debris spawner. Regenerate: tools/phase4_f02_overlay_spawner_pin.c\",\n");
        fprintf(j, " \"row_id\": \"F02_tunnels\",\n");
        fprintf(j, " \"method\": \"a jal at file offset K in an overlay based at B returns to "
                   "B+K+8; score every (image, base) pair against the four overlay-space "
                   "callers the live run recorded\",\n");
        fprintf(j, " \"overlay_image\": \"%s\",\n \"load_base\": \"0x%08X\",\n",
                board[best].path, base);
        fprintf(j, " \"callers_matched\": %d,\n \"callers_total\": %d,\n \"unique\": %s,\n",
                board[best].score, NWANT, ties == 1 ? "true" : "false");
        fprintf(j, " \"debris_call_pc\": \"0x%08X\",\n \"debris_return_pc\": \"0x%08X\",\n",
                base + (uint32_t)site, WANT[0].ra);
        fprintf(j, " \"debris_ctor_type\": \"0x%02X\",\n \"debris_stack_arg\": %u,\n", a3, stackarg);
        fprintf(j, " \"corrects\": \"the prior artifact attributed 0x800B43F8 to the LEVEL02 "
                   "overlay by name; overlay space is reused and the address alone does not "
                   "name a file\"\n}\n");
        fclose(j);
        printf("\nwrote %s\n", jsonout);
    }
    free(m.d);
    return 0;
}
