/* repair_function_coverage -- give the function census back the 46 KB of live
 * code it never listed.
 *
 * THE PROBLEM
 * -----------
 * analysis/functions_resident.txt (derived from analysis/functions.json) lists
 * 998 functions covering 90.1% of the resident text. tools/text_coverage_audit.c
 * showed the missing 9.9% is not padding: 46,020 bytes in 14 gaps are reached by
 * direct j/jal/branch out of listed code. Every static census in this project --
 * region provenance, affine bound recovery, frontier compilation -- iterates that
 * list, so all of them walked past live code.
 *
 * ATTRIBUTION RULE
 * ----------------
 * The two kinds of missing code need opposite fixes, and MIPS distinguishes them
 * for us:
 *
 *   `jal TARGET`          TARGET is a function ENTRY   -> emit a new function
 *   `j` / branch TARGET   TARGET is the same function  -> EXTEND the function
 *                                                          that branches there
 *
 * So a gap is cut at its `jal` targets, and everything before the first one is a
 * continuation of whatever branches into it. That is why the emitter is one
 * function and not seventeen: `0x80010C88` is `j 0x800102D4`, a back-edge, and
 * its listed size of 724 bytes simply stopped at the loop head.
 *
 * Discovery is iterated to a fixpoint, because gap code calls other gap code: a
 * `jal` living inside a newly-recovered region can reveal a further entry that
 * no listed function references.
 *
 * WHAT IT WILL NOT DO
 * -------------------
 * Invent coverage. A gap nothing branches into stays unclaimed -- 340 bytes over
 * 65 gaps, which is what real inter-function padding looks like. Extending into
 * those would manufacture a clean 100% by swallowing data, and a census that
 * reads padding as code produces false sites, which is worse than the hole.
 *
 * Indirect flow IS followed for the one form this compiler emits verifiably: a
 * `jr rX` (rX != ra) whose jump table sits inline after the delay slot as 8-byte
 * `j TARGET ; <delay>` entries. Only consecutive in-range `j` words are taken, so
 * the scan stops at the first word that is not a table entry. Dispatch through a
 * table held in DATA, and calls through function pointers, are still not followed:
 * a region reached only that way stays unclaimed and is reported. Recovery is a
 * floor, never an overstatement.
 *
 * Build:  cc -O2 -Wall -Wextra -Werror -o /tmp/rfc tools/repair_function_coverage.c
 * Usage:  /tmp/rfc SCUS_942.88 analysis/functions_resident.txt \
 *             [--out functions_resident_repaired.txt] [--json report.json]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define TEXT_LO 0x80010000u
#define TEXT_HI 0x80082800u
#define HDR     0x800u
#define MAXFN   8192

struct fn {
    uint32_t addr, size;
    char name[96];
    int is_new;          /* recovered by this tool */
    int extended_by;     /* bytes added to a listed function */
    int rejected_ext;    /* bytes refused as not plausibly code */
};

static uint8_t *img;
static long img_len;
static struct fn fns[MAXFN];
static int nf;

static uint32_t rd32(uint32_t va)
{
    long off = (long)HDR + (long)(va - TEXT_LO);
    if (off < 0 || off + 4 > img_len) return 0;
    return (uint32_t)img[off] | ((uint32_t)img[off + 1] << 8) |
           ((uint32_t)img[off + 2] << 16) | ((uint32_t)img[off + 3] << 24);
}

static int cmp_fn(const void *a, const void *b)
{
    uint32_t x = ((const struct fn *)a)->addr, y = ((const struct fn *)b)->addr;
    return x < y ? -1 : x > y ? 1 : 0;
}

/* covered[i] = 1 if byte TEXT_LO+i*4 lies inside some listed function */
static uint8_t *covered;

static void mark_covered(void)
{
    memset(covered, 0, (TEXT_HI - TEXT_LO) / 4);
    for (int i = 0; i < nf; i++)
        for (uint32_t p = fns[i].addr; p < fns[i].addr + fns[i].size && p < TEXT_HI; p += 4)
            covered[(p - TEXT_LO) / 4] = 1;
}

static int is_covered(uint32_t va)
{
    if (va < TEXT_LO || va >= TEXT_HI) return 1;   /* out of scope == not our problem */
    return covered[(va - TEXT_LO) / 4];
}

/* Register an entry for code that is reached but lies outside the walking
 * function's range. Used for jal targets and for j/branch targets that leave the
 * function entirely -- a tail call, or an out-of-line block the census never
 * listed. Returns 1 if something new was added. */
static int add_entry(uint32_t t);

/* Is this region plausibly CODE?
 *
 * The zero-word guard was not enough. analysis/functions_resident.txt contains
 * DATA entries labelled as functions -- contact_metadata_table_a, sky_clear_r,
 * vm_program_pointer_table -- and walking one from its "entry" decodes a table
 * as instructions and wanders through it. That extended
 * contact_metadata_table_a by 8,068 bytes of a plainly regular lookup table
 * (02910fca, 028b0fcb, 02840fcc, ... an ascending sequence), which was 35% of
 * the whole recovery and pure inflation.
 *
 * Measured separation is wide enough to be safe: the emitter's real 11,828-byte
 * extension scores 0.0% implausible, a known-good function scores 0.0%, and the
 * two data extensions score 98.3% and 51.4%. Threshold 15%.
 *
 * "Implausible" = an undefined opcode, an undefined SPECIAL funct, or an ALU
 * SPECIAL writing to $zero -- a computed result thrown away, which real compiler
 * output does not emit but data reliably decodes into. */
static double implausible_fraction(uint32_t lo, uint32_t hi);

/* The walk boundary must come from the ORIGINAL listing, not the live one.
 *
 * Using "next entry in the current list" looked natural and was wrong: entries
 * get added DURING recovery, so the boundary creeps backwards and a function's
 * own forward branches start falling outside it. Each one then registered as a
 * new function and the clamp cut the parent at it -- the emitter came out as
 * 3,772 bytes in five pieces instead of one 12,552-byte function, and PCs that
 * had just been recovered fell back out of coverage.
 *
 * The original 998 starts are fixed points: whatever the truth about the code
 * between two of them, it does not span one. */
static uint32_t orig_starts[MAXFN];
static int n_orig;

static uint32_t stable_lim(uint32_t a)
{
    uint32_t best = TEXT_HI;
    for (int i = 0; i < n_orig; i++)
        if (orig_starts[i] > a && orig_starts[i] < best) best = orig_starts[i];
    return best;
}

static int add_entry(uint32_t t)
{
    if (t < TEXT_LO || t >= TEXT_HI) return 0;
    if (is_covered(t)) return 0;
    /* A function cannot begin on a zero word. Both entries the first version
     * recovered (0x8007F204, 0x8007F2B8) landed in a run of zeros inside the
     * 0x8007E8B8 region, which is 58.6% zero words and sits directly below
     * $gp = 0x80081D98 -- small data, not code. They were minted from two words
     * that decode as REGIMM `bgezal`, an instruction this compiler never emits,
     * and one of them was "extended" across 8,768 bytes that are 72.4% zero.
     * Refusing a zero entry point costs nothing real and stops that class. */
    if (rd32(t) == 0u) return 0;
    if (nf >= MAXFN) return 0;
    fns[nf].addr = t; fns[nf].size = 4; fns[nf].is_new = 1; fns[nf].extended_by = 0;
    fns[nf].rejected_ext = 0;
    snprintf(fns[nf].name, sizeof fns[nf].name, "recovered_%08X", t);
    nf++;
    mark_covered();
    return 1;
}

static double implausible_fraction(uint32_t lo, uint32_t hi)
{
    uint32_t n = 0, bad = 0;
    for (uint32_t pc = lo; pc < hi; pc += 4) {
        uint32_t x = rd32(pc);
        n++;
        if (x == 0u) continue;                       /* canonical nop */
        uint32_t op = x >> 26;
        if (op == 0u) {
            uint32_t fn = x & 0x3Fu, rd = (x >> 11) & 31;
            switch (fn) {
            case 0x00: case 0x02: case 0x03: case 0x04: case 0x06: case 0x07:
            case 0x20: case 0x21: case 0x22: case 0x23: case 0x24: case 0x25:
            case 0x26: case 0x27: case 0x2A: case 0x2B:
                if (rd == 0u) bad++;                 /* result discarded */
                break;
            case 0x08: case 0x09: case 0x0C: case 0x10: case 0x11: case 0x12:
            case 0x13: case 0x18: case 0x19: case 0x1A: case 0x1B:
                break;                               /* jr/jalr/syscall/hi-lo/mul-div */
            default:
                bad++;                               /* undefined funct */
            }
        } else {
            /* WHITELIST, not a blacklist. The first version blacklisted a partial
             * set of undefined opcodes and let a 51%-implausible data region pass
             * as code. Anything the R3000 does not define is implausible. */
            int ok = (op == 0x01u) ||                       /* REGIMM            */
                     (op >= 0x02u && op <= 0x0Fu) ||        /* j..lui            */
                     (op >= 0x10u && op <= 0x12u) ||        /* COP0/COP1/COP2    */
                     (op >= 0x14u && op <= 0x17u) ||        /* branch-likely     */
                     (op >= 0x20u && op <= 0x26u) ||        /* loads             */
                     (op >= 0x28u && op <= 0x2Bu) ||        /* stores            */
                     (op == 0x2Eu) ||                       /* swr               */
                     (op == 0x32u) || (op == 0x3Au);        /* lwc2 / swc2       */
            if (!ok) bad++;
        }
    }
    return n ? (double)bad / (double)n : 0.0;
}

static uint32_t branch_target(uint32_t pc, uint32_t w, int *is_call)
{
    uint32_t op = w >> 26;
    *is_call = 0;
    if (op == 2u || op == 3u) {                        /* j / jal */
        *is_call = (op == 3u);
        return ((pc + 4u) & 0xF0000000u) | ((w & 0x03FFFFFFu) << 2);
    }
    if (op == 1u) {
        /* REGIMM bltzal/bgezal ARE calls architecturally, but GCC 2.7.2 does not
         * emit them, so a word decoding this way is far likelier to be data. They
         * are followed as branches and never used to mint a function entry. */
        return pc + 4u + (uint32_t)((int32_t)(int16_t)(w & 0xFFFFu) * 4);
    }
    if ((op >= 4u && op <= 7u) || (op >= 0x14u && op <= 0x17u))
        return pc + 4u + (uint32_t)((int32_t)(int16_t)(w & 0xFFFFu) * 4);
    return 0u;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <exe> <functions.txt> [--out f] [--json f]\n", argv[0]);
        return 2;
    }
    const char *outp = NULL, *jsonp = NULL;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--out") && i + 1 < argc) outp = argv[++i];
        else if (!strcmp(argv[i], "--json") && i + 1 < argc) jsonp = argv[++i];
    }

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
    if (rd32(0x80010C88u) != 0x080040B5u) {
        fprintf(stderr, "pin 0x80010C88 (`j 0x800102D4`) does not match; wrong image\n");
        return 2;
    }

    FILE *g = fopen(argv[2], "r");
    if (!g) { perror(argv[2]); return 2; }
    char line[512];
    while (fgets(line, sizeof line, g) && nf < MAXFN) {
        if (line[0] == '#' || line[0] == '\n') continue;
        uint32_t a, n; char nm[96] = {0};
        if (sscanf(line, "%x %u %95s", &a, &n, nm) < 3) continue;
        if (a < TEXT_LO || a >= TEXT_HI) continue;
        fns[nf].addr = a; fns[nf].size = n; fns[nf].is_new = 0; fns[nf].extended_by = 0;
        fns[nf].rejected_ext = 0;
        snprintf(fns[nf].name, sizeof fns[nf].name, "%s", nm);
        nf++;
    }
    fclose(g);
    int n_listed = nf;
    qsort(fns, (size_t)nf, sizeof fns[0], cmp_fn);
    n_orig = nf;
    for (int i = 0; i < nf; i++) orig_starts[i] = fns[i].addr;

    covered = malloc((TEXT_HI - TEXT_LO) / 4);
    if (!covered) { fprintf(stderr, "oom\n"); return 2; }

    uint64_t before_covered = 0;
    mark_covered();
    for (uint32_t i = 0; i < (TEXT_HI - TEXT_LO) / 4; i++) before_covered += covered[i] ? 4 : 0;

    /* ---- flow walk: recover each function's real extent ----------------
     *
     * The first version of this scanned branch TARGETS and recovered 332 of
     * 46,020 bytes, because the dominant case is not a branch at all. A census
     * entry that truncates a function leaves the rest reachable by FALL-THROUGH:
     * `0x80010000 724 per_object_mesh_draw_payload_emitter` ends at 0x800102D4
     * and the very next instruction is the loop the campaign caught. Nothing
     * jumps there from inside the listed 724 bytes -- execution simply arrives.
     *
     * So walk the CFG from each entry: follow fall-through, follow both edges of
     * a conditional, follow `j` within range, and stop a path only at a real
     * terminator (`jr`, or `j` out of range = tail call), always consuming the
     * delay slot. Bounded by the next function's start so a walk can never
     * annex its neighbour. */
    static uint8_t reached[(TEXT_HI - TEXT_LO) / 4];
    static uint32_t stack[65536];
    int rounds = 0, added;

    do {
        added = 0;
        rounds++;
        qsort(fns, (size_t)nf, sizeof fns[0], cmp_fn);
        mark_covered();
        memset(reached, 0, sizeof reached);

        for (int i = 0; i < nf; i++) {
            uint32_t lim = stable_lim(fns[i].addr);
            if (lim <= fns[i].addr) continue;
            int sp = 0;
            stack[sp++] = fns[i].addr;
            uint32_t far = fns[i].addr;

            while (sp > 0) {
                uint32_t pc = stack[--sp];
                while (pc >= fns[i].addr && pc < lim) {
                    uint32_t idx = (pc - TEXT_LO) / 4;
                    if (reached[idx]) break;
                    reached[idx] = 1;
                    if (pc + 4 > far) far = pc + 4;

                    uint32_t w = rd32(pc), op = w >> 26;
                    int is_call;
                    uint32_t t = branch_target(pc, w, &is_call);

                    /* the delay slot always executes */
                    uint32_t dslot = pc + 4;
                    int is_jr = (op == 0u && ((w & 0x3Fu) == 8u));
                    int is_jump = (op == 2u);
                    int is_branch = (op == 1u) || (op >= 4u && op <= 7u) ||
                                    (op >= 0x14u && op <= 0x17u);

                    if (is_jr || is_jump || is_branch || is_call) {
                        if (dslot >= fns[i].addr && dslot < lim) {
                            uint32_t di = (dslot - TEXT_LO) / 4;
                            if (!reached[di]) {
                                reached[di] = 1;
                                if (dslot + 4 > far) far = dslot + 4;
                            }
                        }
                    }

                    if (is_call) {                       /* jal: record, then fall through */
                        added += add_entry(t);
                        pc = dslot + 4;
                        continue;
                    }
                    if (is_jr) {
                        /* `jr ra` is a return. `jr rX` is a computed dispatch, and
                         * this compiler emits the table INLINE right after the
                         * delay slot as 8-byte `j TARGET ; <delay>` entries --
                         * 0x80010364 `jr $t1` is followed at 0x8001036C by
                         * `j 0x8001046C`, `j 0x80010ADC`, ... Without following
                         * those, the walk stops dead and the emitter's whole body
                         * (including both PCs the campaign caught) stays unlisted.
                         *
                         * Only consecutive in-range `j` words are taken, so the
                         * scan ends at the first thing that is not a table entry. */
                        uint32_t rs_jr = (w >> 21) & 31;
                        if (rs_jr != 31u) {
                            for (uint32_t tp = dslot + 4; tp + 4 < lim; tp += 8) {
                                uint32_t tw = rd32(tp);
                                if ((tw >> 26) != 2u) break;
                                uint32_t tt = ((tp + 4u) & 0xF0000000u) |
                                              ((tw & 0x03FFFFFFu) << 2);
                                if (tt < fns[i].addr || tt >= lim) break;
                                for (uint32_t q = tp; q < tp + 8 && q < lim; q += 4) {
                                    uint32_t qi = (q - TEXT_LO) / 4;
                                    if (!reached[qi]) reached[qi] = 1;
                                    if (q + 4 > far) far = q + 4;
                                }
                                if (sp < (int)(sizeof stack / sizeof stack[0]))
                                    stack[sp++] = tt;
                            }
                        }
                        break;                           /* the path itself ends here */
                    }
                    if (is_jump) {
                        if (t >= fns[i].addr && t < lim) { pc = t; continue; }
                        break;                           /* tail call: not our block */
                    }
                    if (is_branch) {
                        if (t >= fns[i].addr && t < lim &&
                            sp < (int)(sizeof stack / sizeof stack[0]))
                            stack[sp++] = t;             /* taken edge, later */
                        pc = dslot + 4;                  /* not-taken edge, now */
                        continue;
                    }
                    pc += 4;                             /* ordinary instruction */
                }
            }

            if (far > fns[i].addr + fns[i].size) {
                uint32_t oldend = fns[i].addr + fns[i].size;
                /* Refuse an extension that is not plausibly code -- see
                 * implausible_fraction(). A data table walked as code will
                 * happily "extend" a function across thousands of bytes. */
                if (implausible_fraction(oldend, far) > 0.15) {
                    fns[i].rejected_ext = (int)(far - oldend);
                    continue;
                }
                fns[i].extended_by += (int)(far - oldend);
                fns[i].size = far - fns[i].addr;
            }
        }
    } while (added && rounds < 32);

    /* NO LINEAR SWEEP.
     *
     * A pass that decoded every byte of every function body to find transfers
     * into uncovered regions looked like free coverage and cost 4.7 points. The
     * bodies contain DATA -- this compiler puts jump tables inline as `j T ;
     * <delay>` pairs, and there are embedded constants -- and a data word that
     * happens to decode as `jal` mints a function entry in the middle of a real
     * function, which the clamp then truncates. Coverage went 97.7% -> 93.0% and
     * the emitter came apart again.
     *
     * Only REACHABLE instructions are decoded, and only a `jal` target names a
     * new function. Regions reachable solely through a data-held dispatch table
     * stay unclaimed and are reported. */

    /* ---- NORMALISE: no function may run into the next one -----------------
     * Extension and entry-discovery interleave, so a function can end up
     * spanning an entry added inside it. A census that iterates this list would
     * then scan those bytes twice and report inflated counts -- the exact 2x
     * inflation a second implementation caught in this project before. Clamp. */
    qsort(fns, (size_t)nf, sizeof fns[0], cmp_fn);
    int clamped = 0;
    for (int i = 0; i + 1 < nf; i++) {
        if (fns[i].addr + fns[i].size > fns[i + 1].addr) {
            fns[i].size = fns[i + 1].addr - fns[i].addr;
            clamped++;
        }
    }

    mark_covered();
    uint64_t after_covered = 0;
    for (uint32_t i = 0; i < (TEXT_HI - TEXT_LO) / 4; i++) after_covered += covered[i] ? 4 : 0;

    int n_extended = 0;
    uint64_t bytes_extended = 0;
    for (int i = 0; i < nf; i++)
        if (fns[i].extended_by > 0) { n_extended++; bytes_extended += (uint32_t)fns[i].extended_by; }

    uint32_t text = TEXT_HI - TEXT_LO;
    printf("listed functions   : %d  covering %llu bytes (%.1f%%)\n", n_listed,
           (unsigned long long)before_covered, 100.0 * (double)before_covered / text);
    printf("recovered entries  : %d  (jal targets in unlisted code, %d walk rounds)\n",
           nf - n_listed, rounds);
    printf("functions extended : %d  (+%llu bytes of dropped tails)\n",
           n_extended, (unsigned long long)bytes_extended);
    printf("repaired list      : %d  covering %llu bytes (%.1f%%)\n", nf,
           (unsigned long long)after_covered, 100.0 * (double)after_covered / text);
    printf("still unclaimed    : %llu bytes  (padding + anything reached only via jr)\n",
           (unsigned long long)(text - after_covered));
    printf("overlaps clamped   : %d  (a function may never run into the next entry)\n",
           clamped);
    {
        int nrej = 0; uint64_t brej = 0;
        for (int i = 0; i < nf; i++)
            if (fns[i].rejected_ext > 0) { nrej++; brej += (uint32_t)fns[i].rejected_ext; }
        printf("extensions REFUSED : %d  (%llu bytes that decode as data, not code)\n",
               nrej, (unsigned long long)brej);
        for (int i = 0; i < nf; i++)
            if (fns[i].rejected_ext > 0)
                printf("     refused 0x%08X %-40s +%d\n", fns[i].addr, fns[i].name,
                       fns[i].rejected_ext);
    }

    if (outp) {
        FILE *o = fopen(outp, "w");
        if (!o) { perror(outp); return 2; }
        fprintf(o, "# base 0x%08X end 0x%08X count %d\n", TEXT_LO, TEXT_HI, nf);
        fprintf(o, "# REPAIRED by tools/repair_function_coverage.c -- recovers code the\n");
        fprintf(o, "# census dropped. jal targets become new functions; j/branch targets\n");
        fprintf(o, "# extend the function that branches to them. Padding stays unclaimed.\n");
        for (int i = 0; i < nf; i++)
            fprintf(o, "0x%08X %u %s\n", fns[i].addr, fns[i].size, fns[i].name);
        fclose(o);
        printf("wrote %s\n", outp);
    }

    if (jsonp) {
        FILE *j = fopen(jsonp, "w");
        if (!j) { perror(jsonp); return 2; }
        fprintf(j, "{\n \"_comment\": \"Repair of the resident function census. Regenerate: "
                   "tools/repair_function_coverage.c\",\n");
        fprintf(j, " \"rule\": \"jal target = function entry (new entry); j/branch target = "
                   "same function (extend it). Iterated to a fixpoint because gap code "
                   "calls other gap code.\",\n");
        fprintf(j, " \"will_not_do\": \"Claim bytes nothing branches into, or follow jr "
                   "(jump tables, function pointers). Recovery is a floor.\",\n");
        fprintf(j, " \"text_bytes\": %u,\n", text);
        fprintf(j, " \"listed_functions\": %d,\n \"listed_covered_bytes\": %llu,\n"
                   " \"listed_covered_percent\": %.2f,\n",
                n_listed, (unsigned long long)before_covered,
                100.0 * (double)before_covered / text);
        fprintf(j, " \"recovered_entries\": %d,\n \"functions_extended\": %d,\n"
                   " \"bytes_recovered_by_extension\": %llu,\n",
                nf - n_listed, n_extended, (unsigned long long)bytes_extended);
        fprintf(j, " \"overlaps_clamped\": %d,\n", clamped);
        fprintf(j, " \"repaired_functions\": %d,\n \"repaired_covered_bytes\": %llu,\n"
                   " \"repaired_covered_percent\": %.2f,\n \"still_unclaimed_bytes\": %llu,\n",
                nf, (unsigned long long)after_covered,
                100.0 * (double)after_covered / text,
                (unsigned long long)(text - after_covered));
        fprintf(j, " \"extended\": [\n");
        int first = 1;
        for (int i = 0; i < nf; i++) {
            if (fns[i].extended_by <= 0) continue;
            fprintf(j, "%s  {\"addr\": \"0x%08X\", \"name\": \"%s\", \"new_size\": %u, "
                       "\"added\": %d}", first ? "" : ",\n",
                    fns[i].addr, fns[i].name, fns[i].size, fns[i].extended_by);
            first = 0;
        }
        fprintf(j, "\n ],\n \"recovered\": [\n");
        first = 1;
        for (int i = 0; i < nf; i++) {
            if (!fns[i].is_new) continue;
            fprintf(j, "%s  {\"addr\": \"0x%08X\", \"size\": %u}", first ? "" : ",\n",
                    fns[i].addr, fns[i].size);
            first = 0;
        }
        fprintf(j, "\n ]\n}\n");
        fclose(j);
        printf("wrote %s\n", jsonp);
    }
    free(img); free(covered);
    return 0;
}
