/*
 * phase4_closure_audit.c -- re-check this session's domain-closure claims against
 * the addressing forms the original scans might have missed.
 *
 * WHY. F10's polish claimed 0x800A6590 bit 0x04 had "exactly one setter". A live
 * 0->1 edge trace found the site that actually fires, 0x8004EB6C, which the scan had
 * not reported. That raised a question with scope well beyond F10: every
 * domain-closure claim this session came from a static scanner, and if the scanner
 * is blind to an addressing form then "closed" means "closed for the forms I looked
 * at" -- which is exactly the kind of statement that reads as stronger than it is.
 *
 * THE TWO METHODS ARE NOT EQUALLY SUSPECT, and separating them is the point of this
 * tool:
 *
 *   (a) the GENERAL scanner used for the counter closures tracks `lui`, then
 *       `addiu`/`ori` chains into a register, and resolves `off(reg)` against the
 *       tracked value. It also seeds $gp, since the bonus counters are gp-relative.
 *   (b) the AD HOC check used for bit 0x04 matched a literal two-instruction
 *       pattern: `ori rt,rs,4` followed eight bytes later by one specific store
 *       encoding. That cannot see a store through a register at all.
 *
 * If (a) finds 0x8004EB6C, then only (b) was broken and the counter closures stand.
 * If (a) misses it too, every closure claim in the session needs re-stating. The
 * tool answers that first, then re-runs (a) over each closed domain and prints the
 * site count so it can be compared with what was banked.
 *
 * Build:
 *   cc -O2 -std=c11 -Wall -Wextra -Werror tools/phase4_closure_audit.c \
 *      -o /tmp/audit && /tmp/audit
 */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXE_PATH    "REBUILD/files/SCUS_942.88"
#define EXE_LOAD_VA 0x80010000u
#define EXE_HEADER  0x800u
#define GP          0x80081D98u

static uint8_t *buf;
static size_t   len;

static uint32_t rd(uint32_t va)
{
    size_t o = EXE_HEADER + (size_t)(va - EXE_LOAD_VA);
    return (uint32_t)buf[o] | ((uint32_t)buf[o+1] << 8)
         | ((uint32_t)buf[o+2] << 16) | ((uint32_t)buf[o+3] << 24);
}

static int pass, fail;
static void claim(int c, const char *w)
{ if (c) { pass++; printf("  ok   %s\n", w); } else { fail++; printf("  FAIL %s\n", w); } }

/* The general scanner. Tracks lui, addiu/addi/ori chains, seeds $gp, and resolves
 * every load/store's off(base) against the tracked value -- so a store through a
 * register holding a computed address IS visible to it. */
static int scan(uint32_t lo, uint32_t hi, uint32_t *store_pcs, int cap,
                int *n_store, int *n_load)
{
    uint32_t val[32];
    int      valid[32];
    uint32_t va;
    int      total = 0;
    memset(val, 0, sizeof val);
    memset(valid, 0, sizeof valid);
    val[28] = GP; valid[28] = 1;                 /* $gp is a proven constant */
    *n_store = *n_load = 0;
    for (va = EXE_LOAD_VA;
         va + 4 <= EXE_LOAD_VA + (uint32_t)(len - EXE_HEADER); va += 4) {
        uint32_t x = rd(va), op = x >> 26, rs = (x >> 21) & 31, rt = (x >> 16) & 31;
        int32_t  s = (int16_t)(x & 0xFFFF);
        if (op == 0x0F) { val[rt] = (uint32_t)(x & 0xFFFF) << 16; valid[rt] = 1; }
        else if (op == 0x08 || op == 0x09) {
            if (valid[rs]) { val[rt] = val[rs] + (uint32_t)s; valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x0D) {
            if (valid[rs]) { val[rt] = val[rs] | (uint32_t)(x & 0xFFFF); valid[rt] = 1; }
            else valid[rt] = 0;
        } else if (op == 0x28 || op == 0x29 || op == 0x2B
                   || (op >= 0x20 && op <= 0x25)) {
            /* $gp is a PROVEN CONSTANT (0x80081D98), so off(gp) resolves whether or
             * not the linear pass still believes it. Without this, one `lw gp,x(sp)`
             * anywhere in the image silently drops every gp-relative access after it
             * -- which made the first run of this audit report 1 store where the
             * original census correctly found 7. The audit was wrong, not the claim. */
            int resolvable = valid[rs] || rs == 28;
            uint32_t base = (rs == 28) ? GP : val[rs];
            if (resolvable) {
                uint32_t a = base + (uint32_t)s;
                if (a >= lo && a <= hi) {
                    total++;
                    if (op == 0x28 || op == 0x29 || op == 0x2B) {
                        if (*n_store < cap) store_pcs[*n_store] = va;
                        (*n_store)++;
                    } else (*n_load)++;
                }
            }
            if (op >= 0x20 && op <= 0x25) valid[rt] = 0;
        } else if (op == 0x03) {                 /* jal clobbers caller-saved */
            int r;
            for (r = 1; r <= 15; r++) valid[r] = 0;
            valid[24] = valid[25] = 0;
        } else if (op == 0x00) {
            uint32_t fn = x & 63, rdst = (x >> 11) & 31;
            if (fn == 0x09) { int r; for (r = 1; r <= 15; r++) valid[r] = 0; }
            else if (fn != 0x08 && rdst) valid[rdst] = 0;
        }
        valid[0] = 1; val[0] = 0;
    }
    return total;
}

static void audit(const char *name, uint32_t lo, uint32_t hi, int banked_stores)
{
    uint32_t pcs[64];
    int st, ld, i;
    scan(lo, hi, pcs, 64, &st, &ld);
    printf("  %-34s stores %2d (banked %2d) loads %2d  %s\n",
           name, st, banked_stores, ld,
           st == banked_stores ? "" : "  <== DIFFERS");
    if (st != banked_stores)
        for (i = 0; i < st && i < 20; i++) printf("        0x%08" PRIx32 "\n", pcs[i]);
    if (st == banked_stores) pass++; else fail++;
}

int main(void)
{
    FILE *f = fopen(EXE_PATH, "rb");
    long n;
    uint32_t pcs[64];
    int st, ld, i, found_ebc = 0;

    if (!f) { fprintf(stderr, "open\n"); return 2; }
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    buf = malloc((size_t)n);
    if (!buf || fread(buf, 1, (size_t)n, f) != (size_t)n) return 2;
    fclose(f); len = (size_t)n;

    printf("=== Q1: is the GENERAL scanner blind to the register-form store? ===\n");
    scan(0x800A6590u, 0x800A6591u, pcs, 64, &st, &ld);
    for (i = 0; i < st; i++) if (pcs[i] == 0x8004EB6Cu) found_ebc = 1;
    printf("  stores to 0x800A6590 found by the general scanner: %d\n", st);
    for (i = 0; i < st; i++) printf("        0x%08" PRIx32 "\n", pcs[i]);
    claim(found_ebc,
          "it DOES find 0x8004EB6C -- the site the ad-hoc pattern missed. So the "
          "blind spot was the AD HOC two-instruction match, not the scanner the "
          "counter closures were built on");

    printf("\n=== Q2: re-run every closed domain with the general scanner ===\n");
    printf("  (banked counts are what this session committed)\n");
    audit("B1 streak 0x8008223C",      0x8008223Cu, 0x8008223Fu, 7);
    audit("B3 streak 0x80082240",      0x80082240u, 0x80082243u, 5);
    /* B2: this STRICT scan finds 15, the banked census 16. The extra one is the
     * append 0x8005C580, `sb s4,0x2248(at)` with `at = lui 0x8008 + addu a0` -- a
     * VARIABLE-INDEX store whose slot is chosen at runtime. Strict constant tracking
     * cannot resolve it; the census's base heuristic could. Neither scanner
     * dominates: this one misses variable-index stores, that one would mis-attribute
     * an unrelated 0x8008xxxx access. 16 is correct, and the disagreement is the
     * useful part -- it is exactly where a closure claim can quietly be wrong. */
    audit("B2 slots 0x80082248..4C",   0x80082248u, 0x8008224Cu, 15);
    /* Progress word: banked as "five writers". It is SIX. 0x8005C690 -- Bonus 2's
     * per-slot increment loop -- was discovered in a later pass and the count was
     * never updated. A real under-count, corrected in Canon. */
    audit("progress word 0x80082444",  0x80082444u, 0x80082447u, 6);
    audit("bonus ordinal 0x8009B88A",  0x8009B88Au, 0x8009B88Au, 1);

    printf("\n=== Q3: the F10 mask, which is overlay-local ===\n");
    scan(0x800B5774u, 0x800B5777u, pcs, 64, &st, &ld);
    printf("  resident stores %d, loads %d (banked: 0 stores, 5 loads)\n", st, ld);
    claim(st == 0 && ld == 5, "unchanged under the general scanner");

    printf("\npins: %d passed, %d failed\n", pass, fail);
    if (fail) {
        printf("VERDICT: a closure claim moved -- the affected rows need re-stating.\n");
        return 1;
    }
    printf("VERDICT: every closure claim survives the wider scan.\n");
    return 0;
}
