/*
 * affine_bound_recovery.c -- recover INDEX RANGES for region-formed accesses.
 *
 * WHY THIS EXISTS
 * ---------------
 * Phase-4 exit-gate item 2 needs every access that could reach a subsystem's
 * state to be resolved or explicitly bounded. The analyser that measures it
 * (tools/region_provenance.c) classifies a base register as REGION -- provably
 * `K + i*S` -- but usually cannot bound `i`, and an arithmetic progression with
 * an unbounded index reaches everything. That is the wall three rows have now
 * stopped against: B06/B08 (4,490 stores with unresolved destinations), E15, and
 * E16 (~20,180 region values with no proven index bound).
 *
 * The bounds are IN the code. They are just not in a form a per-register bound
 * table can use, because the compiler tests a DERIVED value:
 *
 *      addiu $v0, $s4, -48        # v0 = marker - 0x30
 *      sltiu $v0, $v0, 40         # gate
 *      beq   $v0, $zero, skip     #   -> marker in [48, 88)
 *      sll   $v0, $s4, 2          # ...and the INDEX is the raw marker
 *
 * A bound recorded against `$v0` is useless here twice over: it names the
 * derived value, and `$v0` is then reused for the scaled index. What is needed
 * is the affine RELATION `v0 = s4 - 48`, so the range implied for `v0` can be
 * translated back onto `s4`.
 *
 * WHAT THIS DOES
 * --------------
 * A per-function, block-level fixed-point pass that tracks, for every register,
 * an affine form over a symbolic root:
 *
 *      value = mul * sym + add          (or a constant, or unknown)
 *
 * `sym` is a fresh symbol per unresolvable definition (a load, a call return, a
 * function-entry value), so "whatever this loaded thing is" can still be
 * constrained. addiu/sll/addu/subu/or-with-const propagate the form.
 *
 * At a conditional branch guarded by slti/sltiu, the implied range on the root
 * is derived and applied to the TRUE edge only:
 *
 *   sltiu r, N with r = 1*sym + a   ->  sym in [-a, -a + N)     (unsigned window)
 *   slti  r, N with r = 1*sym + a   ->  sym < N - a             (upper bound only)
 *
 * The unsigned form is the compiler's standard range check and yields BOTH ends,
 * which is what makes it worth recovering.
 *
 * Then, for every load/store whose base was formed as `lui` + `addu` of a scaled
 * index, the index's root range (if known) is reported, turning an unbounded
 * region into a bounded one.
 *
 * SOUNDNESS
 * ---------
 * - A range is applied ONLY on the edge where the comparison is true, and only
 *   when the compared register's affine form has mul == 1 (scaling a range is
 *   sound but not needed here, and is not attempted).
 * - Any definition the transfer function cannot model produces a FRESH symbol
 *   rather than silently keeping a stale one.
 * - Merging at join points keeps a form only when both sides agree exactly, and
 *   keeps a range only when both sides have one (widening to their union).
 * - Ranges are therefore MAY-ranges: an index is guaranteed to lie inside, but
 *   the interval may be wider than reality. That is the safe direction for
 *   exclusion reasoning.
 *
 * SELF-CHECK
 * ----------
 * `--verify` asserts the known-hard case from E16: the access at 0x8003BF48 must
 * recover index range [48, 88) for register $s4. This is ground truth -- runtime
 * shows that access firing 36 times into 0x8009B5A8..0x8009B644 -- so a tool that
 * cannot recover it is not fit for the purpose it was built for.
 *
 * Build: cc -O2 -Wall -Wextra -Werror -o /tmp/abr tools/affine_bound_recovery.c
 * Usage: /tmp/abr <SCUS_942.88> <functions_resident.txt> [--json OUT] [--verify]
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FUNCS   2048
#define MAX_BLOCKS  16384
#define MAX_SITES   262144

/* ---------- image ---------- */
static uint8_t *g_img; static long g_len;
static uint32_t g_base, g_end;
static long g_hdr = 0x800;   /* PS-EXE header size; 0 for a raw overlay image */
static uint32_t rd_word(uint32_t va)
{
    if (va < g_base || va + 4 > g_end) return 0;
    uint32_t v; memcpy(&v, g_img + g_hdr + (va - g_base), 4); return v;
}

typedef struct { uint32_t addr, size; char name[96]; } Func;
static Func g_funcs[MAX_FUNCS]; static int g_nfuncs;

static void read_functions(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof line, f) && g_nfuncs < MAX_FUNCS) {
        uint32_t a, s; char nm[96] = {0};
        /* functions_resident.txt is "0xADDR <decimal size> name" -- parsing
         * the size as hex silently inflates every extent. */
        if (sscanf(line, "%x %u %95s", &a, &s, nm) >= 2) {
            g_funcs[g_nfuncs].addr = a; g_funcs[g_nfuncs].size = s;
            snprintf(g_funcs[g_nfuncs].name, sizeof g_funcs[g_nfuncs].name, "%s", nm);
            g_nfuncs++;
        }
    }
    fclose(f);
}

/* ---------- affine lattice ---------- */
enum { A_UNKNOWN = 0, A_CONST, A_AFFINE };
typedef struct {
    uint8_t  kind;
    uint8_t  width_cast; /* range came from a WIDTH mask (0xFF/0xFFFF), i.e. a C
                          * `(char)`/`(short)` truncation rather than an array bound.
                          * Still a sound bound, but worthless as evidence of an
                          * object's SIZE -- `andi 0xffff` "proves" a 128 KB reach. */
    int32_t  sym;      /* symbolic root id (A_AFFINE)          */
    int64_t  mul, add; /* value = mul*sym + add                */
    uint32_t c;        /* A_CONST                              */
    /* known range on the ROOT symbol, if any */
    uint8_t  has_range;
    int64_t  rlo, rhi; /* [rlo, rhi)                           */
} Aff;

static Aff aff_unknown(void) { Aff a; memset(&a, 0, sizeof a); a.kind = A_UNKNOWN; return a; }
static Aff aff_const(uint32_t c) { Aff a; memset(&a, 0, sizeof a); a.kind = A_CONST; a.c = c; return a; }
static Aff aff_sym(int32_t s)
{
    Aff a; memset(&a, 0, sizeof a);
    a.kind = A_AFFINE; a.sym = s; a.mul = 1; a.add = 0; return a;
}

/* An opaque value that nonetheless has a known RANGE.
 *
 * The measured dominant cause of unbounded indices was `addu` with both operands
 * non-constant (2,341 sites, 42% of the residual), then `subu`, `and`, `sra`. All
 * were dropped to a bare fresh symbol -- because the affine FORM is lost. But the
 * form and the range are different things: `i + j` has no affine form in one symbol
 * and a perfectly good range whenever both operands have one. Keeping the range on a
 * fresh symbol recovers exactly that. */
static Aff aff_ranged(int32_t sym, int64_t lo, int64_t hi)
{
    Aff a = aff_sym(sym);
    if (hi > lo) { a.has_range = 1; a.rlo = lo; a.rhi = hi; }
    return a;
}

/* The range a value occupies, if known. */
static int val_range(const Aff *v, int64_t *lo, int64_t *hi)
{
    if (v->kind == A_CONST) { *lo = (int32_t)v->c; *hi = *lo + 1; return 1; }
    if (v->kind == A_AFFINE && v->has_range) {
        int64_t a = v->mul * v->rlo + v->add, b = v->mul * (v->rhi - 1) + v->add;
        if (a > b) { int64_t t = a; a = b; b = t; }
        *lo = a; *hi = b + 1; return 1;
    }
    return 0;
}

static int aff_eq(const Aff *x, const Aff *y)
{
    if (x->kind != y->kind) return 0;
    if (x->kind == A_CONST) return x->c == y->c;
    if (x->kind == A_AFFINE)
        return x->sym == y->sym && x->mul == y->mul && x->add == y->add
            && x->has_range == y->has_range
            && (!x->has_range || (x->rlo == y->rlo && x->rhi == y->rhi));
    return 1;
}

/* Join: keep the form only if both agree; widen a range to the union. */
static Aff aff_merge(const Aff *x, const Aff *y)
{
    if (x->kind == A_UNKNOWN || y->kind == A_UNKNOWN) return aff_unknown();
    if (x->kind == A_CONST && y->kind == A_CONST)
        return (x->c == y->c) ? *x : aff_unknown();
    if (x->kind == A_AFFINE && y->kind == A_AFFINE
        && x->sym == y->sym && x->mul == y->mul && x->add == y->add) {
        Aff r = *x;
        if (x->has_range && y->has_range) {
            r.has_range = 1;
            r.rlo = x->rlo < y->rlo ? x->rlo : y->rlo;
            r.rhi = x->rhi > y->rhi ? x->rhi : y->rhi;
        } else r.has_range = 0;
        return r;
    }
    return aff_unknown();
}

/* ---------- decoding ---------- */
typedef struct { uint32_t op, rs, rt, rd, sa, funct; int32_t imm; } Insn;
static Insn dec(uint32_t w)
{
    Insn d;
    d.op = w >> 26; d.rs = (w >> 21) & 31; d.rt = (w >> 16) & 31;
    d.rd = (w >> 11) & 31; d.sa = (w >> 6) & 31; d.funct = w & 0x3F;
    d.imm = (int16_t)(w & 0xFFFF);
    return d;
}

/* ---------- results ---------- */
typedef struct {
    uint32_t pc;          /* the load/store                        */
    uint32_t func;
    uint32_t region_base; /* lui-derived constant part             */
    int64_t  stride;
    int32_t  idx_reg;
    uint8_t  bounded;
    uint8_t  width_cast;  /* the bound is a C width truncation, not an array bound */
    int64_t  lo, hi;      /* index range [lo, hi) when bounded     */
} Site;
static Site g_sites[MAX_SITES]; static int g_nsites;

static int is_ls(uint32_t op, int *store)
{
    *store = 0;
    switch (op) {
    case 0x20: case 0x21: case 0x23: case 0x24: case 0x25: return 1;
    case 0x28: case 0x29: case 0x2B: *store = 1; return 1;
    default: return 0;
    }
}

/* ---------- interprocedural argument ranges ----------
 *
 * Most indices that resist an intraprocedural bound are loaded values whose range
 * check lives in a CALLER. Propagating argument ranges into callee entry state is
 * therefore the next lever -- but only where it is sound, which is the hard part:
 *
 *   - ADDRESS-TAKEN functions can be reached through a pointer with arguments this
 *     analysis never sees, so their parameters stay unbounded.
 *   - OVERLAY-CALLED functions have call sites in a different binary; the resident
 *     image does not contain them, so their parameters stay unbounded.
 *   - Functions with NO static caller may be entry points or BIOS callbacks.
 *   - Functions in a call CYCLE would let a narrowed parameter justify itself, so
 *     every member of a cycle stays unbounded.
 *
 * Everything else takes the UNION of the ranges observed at its static call sites,
 * and a single call site without a range makes the parameter unbounded. */
typedef struct { uint8_t has; int64_t lo, hi; } PRange;
static PRange  g_param[MAX_FUNCS][4];      /* a0..a3 entry ranges, current       */
static PRange  g_pend[MAX_FUNCS][4];       /* accumulating this round            */
static uint8_t g_pend_any[MAX_FUNCS];      /* saw at least one call site         */
static uint8_t g_unbounded[MAX_FUNCS];     /* must keep TOP parameters           */
static uint8_t g_param_init[MAX_FUNCS];    /* params have been set at least once */
static int     g_ipa_enabled;
static int     g_emit_all;   /* --emit-all: dump unbounded sites too, for clustering */

static int find_func(uint32_t addr)
{
    int lo = 0, hi = g_nfuncs - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_funcs[mid].addr == addr) return mid;
        if (g_funcs[mid].addr < addr) lo = mid + 1; else hi = mid - 1;
    }
    return -1;
}

/* The range an argument value carries at a call site.
 *
 * A CONSTANT argument is the tightest bound there is -- [c, c+1) -- and discarding
 * it was worth 439 of the 447 eligible functions: the first version required the
 * value to already carry a range, so `jal f` with `a0 = 5` contributed nothing.
 * A scaled affine value (`mul != 1`) also has a perfectly good range, just scaled;
 * ignoring that threw away more. */
static int arg_range(const Aff *v, int64_t *lo, int64_t *hi)
{
    if (v->kind == A_CONST) { *lo = (int32_t)v->c; *hi = *lo + 1; return 1; }
    if (v->kind == A_AFFINE && v->has_range) {
        int64_t a = v->mul * v->rlo + v->add;
        int64_t b = v->mul * (v->rhi - 1) + v->add;
        if (a > b) { int64_t t = a; a = b; b = t; }   /* negative stride flips it */
        *lo = a; *hi = b + 1;
        return 1;
    }
    return 0;
}

static void pend_arg(int callee, int a, const Aff *v)
{
    if (callee < 0 || a < 0 || a > 3) return;
    PRange *p = &g_pend[callee][a];
    int64_t lo = 0, hi = 0;
    int have = arg_range(v, &lo, &hi);
    if (!g_pend_any[callee]) {                       /* first site seen           */
        p->has = (uint8_t)have; p->lo = lo; p->hi = hi;
        return;
    }
    if (!have || !p->has) { p->has = 0; return; }    /* one bad site poisons it   */
    if (lo < p->lo) p->lo = lo;
    if (hi > p->hi) p->hi = hi;
}

/* ---------- per-function analysis ---------- */
/* A symbol must identify the DEFINITION, not the visit. Allocating a fresh id each
 * time a block is re-analysed means the same definition gets a different symbol every
 * fixed-point round, so joins never agree and every value decays to UNKNOWN -- the
 * analysis silently returns almost nothing. Keying on the defining PC makes symbols
 * stable across rounds and lets the fixed point converge. */
static int32_t sym_of_pc(uint32_t pc) { return (int32_t)(pc & 0x7FFFFFFF); }
static int32_t sym_of_entry(int reg)  { return (int32_t)(0x70000000 | reg); }
/* "whatever this register holds on entry to THIS block". A register that merges to
 * UNKNOWN (e.g. a loop header joining the entry value with a loaded one) otherwise
 * loses every relation, and the two instructions that matter -- the bounds check and
 * the index use -- are typically in the SAME block, where an opaque-but-stable symbol
 * is enough to relate them. Sound because it names a single value: if a successor has
 * two predecessors carrying different block symbols, the join still collapses. */
static int32_t sym_of_block(int bi, int reg) { return (int32_t)(0x40000000 | (bi << 5) | reg); }

static void analyse(int fi)
{
    uint32_t lo = g_funcs[fi].addr;
    uint32_t hi = lo + (g_funcs[fi].size ? g_funcs[fi].size : 4);
    if (hi > g_end) hi = g_end;
    if (hi <= lo || (hi - lo) > 0x20000) return;

    /* leaders */
    static uint32_t leaders[MAX_BLOCKS]; int nl = 0;
    leaders[nl++] = lo;
    for (uint32_t pc = lo; pc + 4 <= hi; pc += 4) {
        Insn d = dec(rd_word(pc));
        int cond = (d.op >= 4 && d.op <= 7) || (d.op == 1);
        if (cond || d.op == 2 || d.op == 3) {
            uint32_t nxt = pc + 8;                       /* after the delay slot */
            if (nxt < hi && nl < MAX_BLOCKS) leaders[nl++] = nxt;
            if (cond) {
                uint32_t t = pc + 4 + ((uint32_t)d.imm << 2);
                if (t >= lo && t < hi && nl < MAX_BLOCKS) leaders[nl++] = t;
            }
        }
    }
    /* sort + unique */
    for (int i = 1; i < nl; i++) {
        uint32_t k = leaders[i]; int j = i - 1;
        while (j >= 0 && leaders[j] > k) { leaders[j + 1] = leaders[j]; j--; }
        leaders[j + 1] = k;
    }
    int m = 0;
    for (int i = 0; i < nl; i++) if (i == 0 || leaders[i] != leaders[i - 1]) leaders[m++] = leaders[i];
    nl = m;

    static Aff entry[MAX_BLOCKS][32];
    static uint8_t seeded[MAX_BLOCKS];
    for (int i = 0; i < nl; i++) { seeded[i] = 0; for (int r = 0; r < 32; r++) entry[i][r] = aff_unknown(); }
    for (int r = 1; r < 32; r++) entry[0][r] = aff_sym(sym_of_entry(r));  /* entry values */
    if (g_ipa_enabled && !g_unbounded[fi])
        for (int a = 0; a < 4; a++)
            if (g_param[fi][a].has) {
                entry[0][4 + a].has_range = 1;
                entry[0][4 + a].rlo = g_param[fi][a].lo;
                entry[0][4 + a].rhi = g_param[fi][a].hi;
            }
    entry[0][0] = aff_const(0);
    seeded[0] = 1;

    int changed = 1, rounds = 0;
    while (changed && rounds++ < 24) {
        changed = 0;
        for (int bi = 0; bi < nl; bi++) {
            if (!seeded[bi]) continue;
            uint32_t blo = leaders[bi];
            uint32_t bhi = (bi + 1 < nl) ? leaders[bi + 1] : hi;
            Aff st[32];
            for (int r = 0; r < 32; r++) {
                st[r] = entry[bi][r];
                if (st[r].kind == A_UNKNOWN) st[r] = aff_sym(sym_of_block(bi, r));
            }
            st[0] = aff_const(0);

            /* pending guard captured at the conditional branch */
            int guard_reg = -1; int64_t g_lo = 0, g_hi = 0; int guard_true_ft = 0;
            uint32_t guard_target = 0; int have_guard = 0;

            for (uint32_t pc = blo; pc + 4 <= bhi; pc += 4) {
                uint32_t w = rd_word(pc);
                Insn d = dec(w);

                /* --- record a region-formed access ------------------------ */
                int store;
                if (is_ls(d.op, &store)) {
                    Aff b = st[d.rs];
                    /* A REGION-FORMED access is `lui`-derived constant + scaled index:
                     * the affine form must carry a plausible RAM address as its constant
                     * part. Without this, every base whose definition the transfer
                     * function could not model (a fresh symbol, mul=1, add=0) counts as
                     * a region and the census saturates on noise. */
                    /* The constant part must look like a GAME GLOBAL, not merely like
                     * a big number. Accepting anything >= 0x80000000 let arithmetic
                     * constants through: `lui $v1,0x8421` (the RGB555 reciprocal) and
                     * shifted immediates synthesise values in that window, which showed
                     * up as 420 phantom "region" sites based at 0x800000xx -- 8% of the
                     * residual, none of them an array access at all. Nothing the game
                     * allocates lives below its own load address. */
                    int region_shaped = (b.kind == A_AFFINE && b.mul != 0
                                         && (uint32_t)b.add >= 0x80010000u
                                         && (uint32_t)b.add < 0x80200000u);
                    if (region_shaped && g_nsites < MAX_SITES) {
                        Site *s = &g_sites[g_nsites++];
                        s->pc = pc; s->func = g_funcs[fi].addr;
                        s->region_base = (uint32_t)(b.add + d.imm);
                        s->stride = b.mul; s->idx_reg = b.sym;
                        s->bounded = b.has_range;
                        s->width_cast = b.width_cast;
                        s->lo = b.rlo; s->hi = b.rhi;
                    }
                }

                /* --- record argument ranges at a static call --------------- */
                if (g_ipa_enabled && d.op == 3) {
                    uint32_t dst = (pc & 0xF0000000u) | ((w & 0x3FFFFFFu) << 2);
                    int ci = find_func(dst);
                    if (ci >= 0) {
                        /* the delay slot runs before the callee sees a0..a3 */
                        Aff post[32];
                        for (int r = 0; r < 32; r++) post[r] = st[r];
                        for (int a = 0; a < 4; a++) pend_arg(ci, a, &post[4 + a]);
                        g_pend_any[ci] = 1;
                    }
                }

                /* --- capture a guard at a conditional branch --------------- */
                if ((d.op == 4 || d.op == 5) && d.rt == 0 && d.rs) {
                    Aff c = st[d.rs];
                    if (c.kind == A_AFFINE && c.has_range) {
                        guard_reg = c.sym; g_lo = c.rlo; g_hi = c.rhi;
                        guard_true_ft = (d.op == 4);      /* beq zero => cmp FALSE */
                        guard_target = pc + 4 + ((uint32_t)d.imm << 2);
                        have_guard = 1;
                    }
                }

                /* --- transfer --------------------------------------------- */
                if (d.op == 0x0F) {                                  /* lui   */
                    if (d.rt) st[d.rt] = aff_const((uint32_t)(w & 0xFFFF) << 16);
                } else if (d.op == 0x09 || d.op == 0x08) {           /* addiu */
                    if (d.rt) {
                        Aff s0 = st[d.rs];
                        if (s0.kind == A_CONST) st[d.rt] = aff_const(s0.c + (uint32_t)d.imm);
                        else if (s0.kind == A_AFFINE) { Aff r = s0; r.add += d.imm; r.has_range = s0.has_range; st[d.rt] = r; }
                        else st[d.rt] = aff_sym(sym_of_pc(pc));
                    }
                } else if (d.op == 0x0A || d.op == 0x0B) {           /* slti/sltiu */
                    /* Record the range the comparison IMPLIES on the root. */
                    if (d.rt) {
                        Aff s0 = st[d.rs];
                        Aff res = aff_sym(sym_of_pc(pc));
                        if (s0.kind == A_AFFINE && s0.mul == 1) {
                            res.kind = A_AFFINE; res.sym = s0.sym; res.mul = 1; res.add = 0;
                            res.has_range = 1;
                            if (d.op == 0x0B) {          /* sltiu: two-sided window */
                                res.rlo = -s0.add;
                                res.rhi = -s0.add + (int64_t)(uint16_t)d.imm;
                            } else {
                                /* slti gives an UPPER bound only. Pairing it with an
                                 * implicit lower bound of 0 leans on the same
                                 * non-negative-index convention region_provenance.c's
                                 * TIER 2 already discloses -- `array[i]` with i unsigned
                                 * or i >= 0 by construction. Recorded here so the
                                 * assumption travels with the range rather than being
                                 * buried. Without it the "range" spans 2^31 entries,
                                 * intersects every target, and is not a bound at all. */
                                res.rlo = 0;
                                res.rhi = (int64_t)d.imm - s0.add;
                                if (res.rhi <= 0) res.has_range = 0;
                            }
                        }
                        st[d.rt] = res;
                    }
                } else if (d.op == 0 && (d.funct == 0x2A || d.funct == 0x2B)) {
                    /* slt/sltu rd, rs, rt -- the REGISTER form of the bound test.
                     * A loop with a named limit compiles to this, not to slti:
                     *     addiu $t2, $zero, 500      ; the limit
                     *     slt   $v0, $s2, $t2
                     *     bne   $v0, $zero, loop
                     * 1,191 of these exist against 1,552 immediate ones, so ignoring
                     * them was a 43% blind spot in bound recovery. Same shape as the
                     * slti case: the RESULT carries a range on the compared value's
                     * root, applied on the edge where the comparison is true.
                     *
                     * MEASURED YIELD HERE: ZERO. Only 8 of the 1,191 (1%) compare
                     * against a literal; 324 (27%) compare against a value LOADED from
                     * memory and 859 (72%) against something this pass cannot pin. The
                     * blind spot was real and is now closed, but it was not what was
                     * limiting bound recovery -- in this image loop limits come from
                     * DATA (chunk headers, save state, config), not from constants in
                     * the instruction stream. Kept because it is sound and general;
                     * recorded as zero-yield so nobody re-derives it hoping otherwise. */
                    if (d.rd) {
                        Aff a2 = st[d.rs], b2 = st[d.rt];
                        Aff res = aff_sym(sym_of_pc(pc));
                        if (a2.kind == A_AFFINE && a2.mul == 1 && b2.kind == A_CONST) {
                            int64_t lim = (d.funct == 0x2B)
                                        ? (int64_t)(uint32_t)b2.c : (int32_t)b2.c;
                            if (lim - a2.add > 0) {
                                res.kind = A_AFFINE; res.sym = a2.sym;
                                res.mul = 1; res.add = 0;
                                res.has_range = 1;
                                res.rlo = 0;            /* non-negative-index convention */
                                res.rhi = lim - a2.add;
                            }
                        }
                        st[d.rd] = res;
                    }
                } else if (d.op == 0x0C) {                           /* andi  */
                    /* An UNCONDITIONAL bound, needing no branch: `andi rt,rs,M`
                     * yields a value in [0, M+1) whatever rs was. This is how table
                     * indices are clamped all over this image, and it is pure yield:
                     * the result is a fresh opaque value that nonetheless has a range. */
                    if (d.rt) {
                        uint16_t m = (uint16_t)d.imm;
                        Aff r = aff_sym(sym_of_pc(pc));
                        r.has_range = 1; r.rlo = 0; r.rhi = (int64_t)m + 1;
                        r.width_cast = (m == 0xFFu || m == 0xFFFFu);
                        st[d.rt] = r;
                    }
                } else if (d.op == 0 && d.funct == 0x00) {           /* sll   */
                    if (d.rd) {
                        Aff s0 = st[d.rt];
                        if (s0.kind == A_CONST) st[d.rd] = aff_const(s0.c << d.sa);
                        else if (s0.kind == A_AFFINE) {
                            Aff r = s0; r.mul <<= d.sa; r.add <<= d.sa; st[d.rd] = r;
                        } else st[d.rd] = aff_sym(sym_of_pc(pc));
                    }
                } else if (d.op == 0 && (d.funct == 0x21 || d.funct == 0x20)) { /* addu */
                    if (d.rd) {
                        Aff a = st[d.rs], b = st[d.rt];
                        if (a.kind == A_CONST && b.kind == A_AFFINE) { Aff r = b; r.add += a.c; st[d.rd] = r; }
                        else if (b.kind == A_CONST && a.kind == A_AFFINE) { Aff r = a; r.add += b.c; st[d.rd] = r; }
                        else if (a.kind == A_CONST && b.kind == A_CONST) st[d.rd] = aff_const(a.c + b.c);
                        else {
                            int64_t al, ah, bl, bh;
                            if (val_range(&a, &al, &ah) && val_range(&b, &bl, &bh)
                                && al >= 0 && bl >= 0 && ah + bh < (int64_t)1 << 31)
                                st[d.rd] = aff_ranged(sym_of_pc(pc), al + bl, ah + bh - 1);
                            else st[d.rd] = aff_sym(sym_of_pc(pc));
                        }
                    }
                } else if (d.op == 0 && d.funct == 0x23) {           /* subu  */
                    if (d.rd) {
                        Aff a = st[d.rs], b = st[d.rt];
                        int64_t al, ah, bl, bh;
                        if (a.kind == A_AFFINE && b.kind == A_CONST) { Aff r = a; r.add -= b.c; st[d.rd] = r; }
                        else if (val_range(&a, &al, &ah) && val_range(&b, &bl, &bh)
                                 && al - (bh - 1) >= 0)          /* no unsigned wrap */
                            st[d.rd] = aff_ranged(sym_of_pc(pc), al - (bh - 1), ah - bl - 1);
                        else st[d.rd] = aff_sym(sym_of_pc(pc));
                    }
                } else if (d.op == 0 && d.funct == 0x24) {           /* and   */
                    /* For non-negative operands a bitwise AND cannot exceed either,
                     * so the tighter maximum bounds the result. */
                    if (d.rd) {
                        Aff a = st[d.rs], b = st[d.rt];
                        int64_t al, ah, bl, bh;
                        if (val_range(&a, &al, &ah) && val_range(&b, &bl, &bh)
                            && al >= 0 && bl >= 0)
                            st[d.rd] = aff_ranged(sym_of_pc(pc), 0, (ah < bh ? ah : bh) - 1);
                        else st[d.rd] = aff_sym(sym_of_pc(pc));
                    }
                } else if (d.op == 0 && (d.funct == 0x02 || d.funct == 0x03)) { /* srl/sra */
                    if (d.rd) {
                        Aff a = st[d.rt];
                        int64_t al, ah;
                        if (val_range(&a, &al, &ah) && al >= 0)
                            st[d.rd] = aff_ranged(sym_of_pc(pc), al >> d.sa, ((ah - 1) >> d.sa));
                        else if (d.funct == 0x02 && d.sa > 0)
                            /* A logical right shift bounds ANY 32-bit value
                             * unconditionally: the result cannot exceed 2^(32-sa). */
                            st[d.rd] = aff_ranged(sym_of_pc(pc), 0, ((int64_t)1 << (32 - d.sa)) - 1);
                        else st[d.rd] = aff_sym(sym_of_pc(pc));
                    }
                } else if (d.op == 0 && (d.funct == 0x25 || d.funct == 0x24)) { /* or/and */
                    if (d.rd) {
                        Aff a = st[d.rs], b = st[d.rt];
                        if (d.funct == 0x25 && b.kind == A_CONST && b.c == 0) st[d.rd] = a;
                        else if (d.funct == 0x25 && a.kind == A_CONST && a.c == 0) st[d.rd] = b;
                        else st[d.rd] = aff_sym(sym_of_pc(pc));
                    }
                } else {
                    /* anything unmodelled: fresh symbol for the destination */
                    int dst = -1;
                    if (d.op == 0) { if (d.funct != 0x08 && d.funct != 0x0C) dst = (int)d.rd; }
                    else if (d.op == 3) dst = 31;
                    else if (d.op == 0x0D || d.op == 0x0E
                             || (d.op >= 0x20 && d.op <= 0x26)) dst = (int)d.rt;
                    if (dst > 0) st[dst] = aff_sym(sym_of_pc(pc));
                }
                st[0] = aff_const(0);
            }

            /* --- propagate to successors, guard on the true edge only ----- */
            uint32_t succs[2]; int ns = 0;
            uint32_t fall = bhi;
            if (bhi < hi) succs[ns++] = fall;
            /* the block's terminating branch target */
            for (uint32_t pc = blo; pc + 4 <= bhi; pc += 4) {
                Insn d = dec(rd_word(pc));
                if ((d.op >= 4 && d.op <= 7) || d.op == 1) {
                    uint32_t t = pc + 4 + ((uint32_t)d.imm << 2);
                    if (t >= lo && t < hi && ns < 2) succs[ns++] = t;
                }
            }
            for (int k = 0; k < ns; k++) {
                int si = -1;
                for (int i = 0; i < nl; i++) if (leaders[i] == succs[k]) { si = i; break; }
                if (si < 0) continue;
                Aff out[32];
                for (int r = 0; r < 32; r++) out[r] = st[r];
                if (have_guard) {
                    int this_is_true_edge = guard_true_ft ? (succs[k] == fall)
                                                          : (succs[k] == guard_target);
                    if (this_is_true_edge) {
                        for (int r = 0; r < 32; r++)
                            if (out[r].kind == A_AFFINE && out[r].sym == guard_reg && out[r].mul != 0) {
                                out[r].has_range = 1;
                                out[r].rlo = g_lo; out[r].rhi = g_hi;
                            }
                    }
                }
                if (!seeded[si]) {
                    for (int r = 0; r < 32; r++) entry[si][r] = out[r];
                    seeded[si] = 1; changed = 1;
                } else {
                    for (int r = 0; r < 32; r++) {
                        Aff mg = aff_merge(&entry[si][r], &out[r]);
                        if (!aff_eq(&mg, &entry[si][r])) { entry[si][r] = mg; changed = 1; }
                    }
                }
            }
        }
    }
}

/* ---------- who may NOT receive propagated argument ranges ----------
 * Each rule below is a way a function can be entered with arguments this analysis
 * cannot see. Getting any of them wrong makes every downstream bound unsound, so
 * they are computed explicitly and counted in the report. */
static long g_ub_addr_taken, g_ub_overlay, g_ub_no_caller, g_ub_cycle;

static uint8_t g_has_static_caller[MAX_FUNCS];
static int32_t g_edge_from[262144], g_edge_to[262144]; static long g_nedges;

static void mark_address_taken(void)
{
    /* Any 4-byte-aligned word in the image equal to a function start could be a
     * jump-table entry or a stored callback, reachable via jalr with unknown args. */
    for (long o = 0; o + 4 <= g_len - 0x800; o += 4) {
        uint32_t v; memcpy(&v, g_img + 0x800 + o, 4);
        int fi = find_func(v);
        if (fi >= 0 && !g_unbounded[fi]) { g_unbounded[fi] = 1; g_ub_addr_taken++; }
    }
}

static void mark_overlay_called(const char *const *bins, int nbins)
{
    /* A `jal` inside an overlay encodes its target in the same 256 MB segment, so
     * the resident callee resolves without knowing the overlay's load base. */
    for (int i = 0; i < nbins; i++) {
        FILE *f = fopen(bins[i], "rb");
        if (!f) continue;
        fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
        uint8_t *b = malloc(n > 0 ? n : 1);
        if (b && fread(b, 1, n, f) == (size_t)n) {
            for (long o = 0; o + 4 <= n; o += 4) {
                uint32_t w; memcpy(&w, b + o, 4);
                if ((w >> 26) != 3) continue;
                uint32_t dst = 0x80000000u | ((w & 0x3FFFFFFu) << 2);
                int fi = find_func(dst);
                if (fi >= 0 && !g_unbounded[fi]) { g_unbounded[fi] = 1; g_ub_overlay++; }
            }
        }
        free(b); fclose(f);
    }
}

static void build_call_graph(void)
{
    for (int fi = 0; fi < g_nfuncs; fi++) {
        uint32_t lo = g_funcs[fi].addr;
        uint32_t hi = lo + (g_funcs[fi].size ? g_funcs[fi].size : 4);
        if (hi > g_end) hi = g_end;
        for (uint32_t pc = lo; pc + 4 <= hi; pc += 4) {
            uint32_t w = rd_word(pc);
            if ((w >> 26) != 3) continue;
            uint32_t dst = (pc & 0xF0000000u) | ((w & 0x3FFFFFFu) << 2);
            int ci = find_func(dst);
            if (ci >= 0) {
                g_has_static_caller[ci] = 1;
                if (g_nedges < (long)(sizeof g_edge_from / sizeof g_edge_from[0])) {
                    g_edge_from[g_nedges] = fi; g_edge_to[g_nedges] = ci; g_nedges++;
                }
            }
        }
    }
}

/* Iterative cycle marking: a function that can reach itself through static calls is
 * in a cycle. Computed by transitive closure over a bitset-free worklist -- N is
 * ~1000, so the simple O(V*E) sweep is fine and easier to audit than Tarjan. */
static void mark_cycles(void)
{
    static uint8_t reach[MAX_FUNCS];
    for (int start = 0; start < g_nfuncs; start++) {
        memset(reach, 0, sizeof reach);
        int changed = 1;
        for (long e = 0; e < g_nedges; e++) if (g_edge_from[e] == start) reach[g_edge_to[e]] = 1;
        while (changed) {
            changed = 0;
            for (long e = 0; e < g_nedges; e++)
                if (reach[g_edge_from[e]] && !reach[g_edge_to[e]]) { reach[g_edge_to[e]] = 1; changed = 1; }
        }
        if (reach[start] && !g_unbounded[start]) { g_unbounded[start] = 1; g_ub_cycle++; }
    }
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s SCUS_942.88 functions_resident.txt [--json OUT] [--verify]\n", argv[0]);
        return 2;
    }
    const char *json_out = NULL; int verify = 0; uint32_t explain = 0;
    uint32_t tlo = 0, thi = 0; int have_target = 0; int ipa = 0; uint32_t raw_base = 0;
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "--json") && i + 1 < argc) json_out = argv[++i];
        else if (!strcmp(argv[i], "--verify")) verify = 1;
        else if (!strcmp(argv[i], "--interprocedural")) ipa = 1;
        else if (!strcmp(argv[i], "--emit-all")) g_emit_all = 1;
        else if (!strcmp(argv[i], "--raw-base") && i + 1 < argc)
            raw_base = (uint32_t)strtoul(argv[++i], NULL, 16);
        else if (!strcmp(argv[i], "--explain") && i + 1 < argc) explain = (uint32_t)strtoul(argv[++i], NULL, 16);
        else if (!strcmp(argv[i], "--target") && i + 2 < argc) {
            tlo = (uint32_t)strtoul(argv[++i], NULL, 16);
            thi = (uint32_t)strtoul(argv[++i], NULL, 16); have_target = 1;
        }
    }

    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); g_len = ftell(f); fseek(f, 0, SEEK_SET);
    g_img = malloc(g_len);
    if (!g_img || fread(g_img, 1, g_len, f) != (size_t)g_len) { fprintf(stderr, "read\n"); return 2; }
    fclose(f);
    if (raw_base) {
        /* A raw overlay image: no PS-EXE header, loaded flat at --raw-base. The
         * resident census has only ever covered SCUS_942.88, so overlay code has
         * never been region-censused at all -- and each level swaps a different
         * overlay into the same region. */
        g_base = raw_base;
        g_hdr = 0;
        g_end = g_base + (uint32_t)g_len;
    } else {
        if (memcmp(g_img, "PS-X EXE", 8)) { fprintf(stderr, "not a PS-X EXE\n"); return 2; }
        g_base = g_img[0x18] | (g_img[0x19] << 8) | (g_img[0x1A] << 16) | ((uint32_t)g_img[0x1B] << 24);
        g_hdr = 0x800;
        g_end = g_base + (uint32_t)(g_len - 0x800);
    }

    read_functions(argv[2]);

    long intra_bounded = 0, intra_sites = 0;
    if (ipa) {
        /* Baseline first, so the IPA gain is a measured delta rather than a claim. */
        for (int i = 0; i < g_nfuncs; i++) analyse(i);
        for (int i = 0; i < g_nsites; i++) { intra_sites++; if (g_sites[i].bounded) intra_bounded++; }

        build_call_graph();
        mark_address_taken();
        static const char *bins[] = {
            "REBUILD/files/BITS/MEMORY.BIN", "REBUILD/files/FMV/FMV.BIN",
            "REBUILD/files/LEVEL00/LEVEL.BIN", "REBUILD/files/LEVEL01/LEVEL.BIN",
            "REBUILD/files/LEVEL01/LEVEL1.BIN", "REBUILD/files/LEVEL02/LEVEL.BIN",
            "REBUILD/files/LEVEL02/LEVEL1.BIN", "REBUILD/files/LEVEL03/LEVEL.BIN",
            "REBUILD/files/LEVEL03/LEVEL1.BIN", "REBUILD/files/LEVEL04/LEVEL.BIN",
            "REBUILD/files/LEVEL04/LEVEL1.BIN", "REBUILD/files/LEVEL05/LEVEL.BIN",
            "REBUILD/files/LEVEL05/LEVEL1.BIN", "REBUILD/files/LEVEL06/LEVEL.BIN",
            "REBUILD/files/LEVEL06/LEVEL1.BIN", "REBUILD/files/LEVEL07/LEVEL.BIN",
            "REBUILD/files/LEVEL07/LEVEL1.BIN", "REBUILD/files/LEVEL08/LEVEL.BIN",
            "REBUILD/files/LEVEL08/LEVEL1.BIN", "REBUILD/files/LEVEL09/LEVEL.BIN",
            "REBUILD/files/LEVEL09/LEVEL1.BIN", "REBUILD/files/LEVEL10/LEVEL.BIN",
        };
        mark_overlay_called(bins, (int)(sizeof bins / sizeof bins[0]));
        for (int i = 0; i < g_nfuncs; i++)
            if (!g_has_static_caller[i] && !g_unbounded[i]) { g_unbounded[i] = 1; g_ub_no_caller++; }
        mark_cycles();

        g_ipa_enabled = 1;
        for (int round = 0; round < 12; round++) {
            memset(g_pend, 0, sizeof g_pend);
            memset(g_pend_any, 0, sizeof g_pend_any);
            g_nsites = 0;
            for (int i = 0; i < g_nfuncs; i++) analyse(i);
            /* MONOTONE update. Replacing the range each round lets it NARROW, and a
             * narrowing chain through nested calls oscillates and never settles --
             * measured: all 447 eligible functions were still moving at the cap.
             * Joining (widen-only, and once poisoned always poisoned) makes the
             * sequence monotone, so it converges, and is sound because a wider range
             * admits more possibilities. */
            int changed = 0;
            for (int i = 0; i < g_nfuncs; i++) {
                if (g_unbounded[i] || !g_pend_any[i]) continue;
                for (int a = 0; a < 4; a++) {
                    PRange nv = g_pend[i][a], *cur = &g_param[i][a];
                    if (!g_param_init[i]) { if (cur->has != nv.has || cur->lo != nv.lo || cur->hi != nv.hi) changed = 1; *cur = nv; continue; }
                    if (!cur->has) continue;                     /* already poisoned  */
                    if (!nv.has) { cur->has = 0; changed = 1; continue; }
                    if (nv.lo < cur->lo) { cur->lo = nv.lo; changed = 1; }
                    if (nv.hi > cur->hi) { cur->hi = nv.hi; changed = 1; }
                }
                g_param_init[i] = 1;
            }
            if (!changed) break;
            /* Last round and still moving: the fixed point did not settle, so the
             * remaining parameters are not trustworthy. Say so rather than using them. */
            if (round == 11) {
                for (int i = 0; i < g_nfuncs; i++)
                    if (!g_unbounded[i]) { g_unbounded[i] = 1; g_ub_cycle++; }
                g_nsites = 0;
                for (int i = 0; i < g_nfuncs; i++) analyse(i);
            }
        }
    } else {
        for (int i = 0; i < g_nfuncs; i++) analyse(i);
    }

    long total = 0, bounded = 0;
    for (int i = 0; i < g_nsites; i++) { total++; if (g_sites[i].bounded) bounded++; }

    /* WHY do the unbounded ones resist? Classify each by where its index symbol was
     * born. This is the difference between "we need a better analysis" and "the bound
     * does not exist statically", and it decides whether more tooling is worth it. */
    long org_load = 0, org_entry = 0, org_block = 0, org_alu = 0, org_call = 0, org_other = 0;
    for (int i = 0; i < g_nsites; i++) {
        if (g_sites[i].bounded) continue;
        uint32_t sy = (uint32_t)g_sites[i].idx_reg;
        if (sy >= 0x70000000u)      { org_entry++; continue; }
        if (sy >= 0x40000000u)      { org_block++; continue; }
        uint32_t defpc = sy | 0x80000000u;
        if (defpc < g_base || defpc + 4 > g_end) { org_other++; continue; }
        uint32_t w = rd_word(defpc); uint32_t op = w >> 26;
        if (op >= 0x20 && op <= 0x26)      org_load++;
        else if (op == 3 || (op == 0 && (w & 0x3F) == 0x09)) org_call++;
        else if (op == 0 || (op >= 8 && op <= 0x0F))         org_alu++;
        else org_other++;
    }
    printf("unbounded index origins: load=%ld block-entry=%ld func-entry=%ld alu=%ld call-return=%ld other=%ld\n",
           org_load, org_block, org_entry, org_alu, org_call, org_other);
    {   /* which ALU ops dominate -- measure before modelling any of them */
        long hist[128]; memset(hist, 0, sizeof hist);
        for (int i = 0; i < g_nsites; i++) {
            if (g_sites[i].bounded) continue;
            uint32_t sy = (uint32_t)g_sites[i].idx_reg;
            if (sy >= 0x40000000u) continue;
            uint32_t defpc = sy | 0x80000000u;
            if (defpc < g_base || defpc + 4 > g_end) continue;
            uint32_t w = rd_word(defpc), op = w >> 26;
            if (op == 0) hist[64 + (w & 0x3F)]++; else if (op < 64) hist[op]++;
        }
        printf("  defining-op histogram (top): ");
        for (int k = 0; k < 6; k++) {
            int best = -1; long bv = 0;
            for (int j = 0; j < 128; j++) if (hist[j] > bv) { bv = hist[j]; best = j; }
            if (best < 0 || bv == 0) break;
            if (best >= 64) printf("SPECIAL fn=0x%02x:%ld  ", best - 64, bv);
            else printf("op=0x%02x:%ld  ", best, bv);
            hist[best] = 0;
        }
        printf("\n");
    }

    if (have_target) {
        /* Item-2 accounting for one state window: every region-formed access is
         * REACHING, EXCLUDED (bounded and provably disjoint), or UNDECIDED (no bound).
         * Only the UNDECIDED column blocks the gate. */
        long reach = 0, excl = 0, undec = 0;
        for (int i = 0; i < g_nsites; i++) {
            Site *s2 = &g_sites[i];
            if (!s2->bounded) { undec++; continue; }
            /* A range so wide it cannot exclude anything is not a bound; count it as
             * undecided rather than letting it inflate the reaching column. */
            if (s2->hi - s2->lo > 100000) { undec++; continue; }
            int hits = 0;
            for (int64_t k = s2->lo; k < s2->hi && !hits; k++) {
                int64_t a = (int64_t)s2->region_base + k * s2->stride;
                if (a >= (int64_t)tlo && a < (int64_t)thi) hits = 1;
                if (a >= (int64_t)thi && s2->stride > 0) break;
            }
            if (hits) reach++; else excl++;
        }
        printf("TARGET 0x%08X..0x%08X: reaching=%ld excluded_by_bound=%ld undecided=%ld\n",
               tlo, thi, reach, excl, undec);
    }

    if (explain) {
        int n = 0;
        for (int i = 0; i < g_nsites; i++) if (g_sites[i].pc == explain) {
            n++;
            printf("EXPLAIN 0x%08X: func=0x%08X base=0x%08X stride=%lld sym=%d bounded=%d [%lld,%lld)\n",
                   g_sites[i].pc, g_sites[i].func, g_sites[i].region_base,
                   (long long)g_sites[i].stride, g_sites[i].idx_reg,
                   g_sites[i].bounded, (long long)g_sites[i].lo, (long long)g_sites[i].hi);
        }
        if (!n) printf("EXPLAIN 0x%08X: NOT recorded as a region-formed site at all\n", explain);
    }

    /* the E16 ground-truth case */
    int found = 0; int64_t vlo = 0, vhi = 0;
    for (int i = 0; i < g_nsites; i++)
        if (g_sites[i].pc == 0x8003BF48u && g_sites[i].bounded) {
            found = 1; vlo = g_sites[i].lo; vhi = g_sites[i].hi; break;
        }

    if (ipa) {
        long ub = 0;
        for (int i = 0; i < g_nfuncs; i++) ub += g_unbounded[i] ? 1 : 0;
        printf("INTERPROCEDURAL: %ld/%d functions keep unbounded parameters "
               "(address-taken %ld, overlay-called %ld, no static caller %ld, cycle/unsettled %ld)\n",
               ub, g_nfuncs, g_ub_addr_taken, g_ub_overlay, g_ub_no_caller, g_ub_cycle);
        long fn_with_param = 0, params_bounded = 0, elig = 0;
        for (int i = 0; i < g_nfuncs; i++) {
            if (g_unbounded[i]) continue;
            elig++;
            int any = 0;
            for (int a = 0; a < 4; a++) if (g_param[i][a].has) { params_bounded++; any = 1; }
            if (any) fn_with_param++;
        }
        printf("  eligible functions: %ld; with >=1 bounded parameter: %ld (%ld params total)\n",
               elig, fn_with_param, params_bounded);
        printf("  intraprocedural baseline: %ld/%ld sites bounded\n", intra_bounded, intra_sites);
    }
    printf("region-formed access sites: %ld\n", total);
    printf("  with a recovered index range: %ld (%.1f%%)\n",
           bounded, total ? 100.0 * (double)bounded / (double)total : 0.0);
    printf("  E16 ground truth 0x8003BF48: %s", found ? "RECOVERED" : "NOT recovered");
    if (found) printf(" [%lld, %lld)", (long long)vlo, (long long)vhi);
    printf("\n");

    if (json_out) {
        FILE *jf = fopen(json_out, "w");
        if (jf) {
            fprintf(jf, "{\n \"_comment\": \"affine index-bound recovery over the pristine "
                        "resident EXE. Regenerate: tools/affine_bound_recovery.c\",\n");
            fprintf(jf, " \"region_formed_sites\": %ld,\n \"bounded_sites\": %ld,\n", total, bounded);
            fprintf(jf, " \"ground_truth_0x8003BF48\": {\"recovered\": %s, \"lo\": %lld, \"hi\": %lld},\n",
                    found ? "true" : "false", (long long)vlo, (long long)vhi);
            fprintf(jf, " \"sites\": [");
            int first = 1;
            for (int i = 0; i < g_nsites; i++) {
                if (!g_sites[i].bounded && !g_emit_all) continue;
                fprintf(jf, "%s\n  {\"pc\":\"0x%08X\",\"func\":\"0x%08X\",\"base\":\"0x%08X\","
                            "\"stride\":%lld,\"bounded\":%s,\"width_cast\":%s,\"sym\":%d,"
                            "\"lo\":%lld,\"hi\":%lld}",
                        first ? "" : ",", g_sites[i].pc, g_sites[i].func,
                        g_sites[i].region_base, (long long)g_sites[i].stride,
                        g_sites[i].bounded ? "true" : "false",
                        g_sites[i].width_cast ? "true" : "false",
                        g_sites[i].idx_reg,
                        (long long)g_sites[i].lo, (long long)g_sites[i].hi);
                first = 0;
            }
            fprintf(jf, "\n ]\n}\n");
            fclose(jf);
            fprintf(stderr, "wrote %s\n", json_out);
        }
    }

    if (verify) {
        if (!found || vlo != 48 || vhi != 88) {
            fprintf(stderr, "VERIFY FAILED: 0x8003BF48 expected [48,88), got %s [%lld,%lld)\n",
                    found ? "" : "(absent)", (long long)vlo, (long long)vhi);
            return 1;
        }
        fprintf(stderr, "VERIFY OK: 0x8003BF48 -> [48, 88)\n");
    }
    free(g_img);
    return 0;
}
