/*
 * region_provenance.c -- static pointer-provenance analysis over the pristine EXE,
 * in C for speed, extending the value-analysis technique in census_address.py with a
 * REGION lattice value so a base register can be classified "definitely derives from
 * pool K with stride S" even when its exact numeric value is data-dependent.
 *
 * WHY THIS EXISTS
 * ----------------
 * census_address.py's constant-propagation census leaves 882 same-width accesses to
 * the power slot (0x800A657E) with an unresolved base register, inside 34 functions
 * already shown to touch the player block. Most of those are NOT the player pointer
 * with an unknown value -- they're a DIFFERENT, named object (a dirt-pile record, a
 * ground-height query record) reached through array indexing the constant-only
 * analysis can't pin to a single address, because the index is data-dependent. The
 * question that actually needs answering isn't "what's the exact address" -- it's
 * "can this base register's value family ever equal the target." That is answerable
 * even when the exact value isn't, via alignment: if the base is provably
 * `K + i*S` for integer i and some fixed pool base K and stride S (both read directly
 * off the `sll`+`addu` instruction pair the compiler emits for `array[i]`), then the
 * target is UNREACHABLE from this access whenever `(target - offset - K) mod S != 0`
 * -- true for EVERY possible i, with no assumption about how large the array is.
 *
 * WHAT THIS PROVES, AND HOW SOUND EACH TIER IS
 * ----------------------------------------------
 * TIER 1 (EXCLUDED_ALIGNMENT) -- fully sound given the disassembled base IS
 *   `K + i*S`: the target address is not a multiple of S away from the base, so no
 *   integer i (positive, negative, or zero) reaches it. No assumption about array
 *   size or index sign.
 * TIER 2 (EXCLUDED_NEGATIVE_INDEX) -- sound GIVEN the standard compiler convention
 *   that these indices are non-negative (`array[i]`, i unsigned or i>=0 by
 *   construction): the aligned index needed to reach the target is negative, which no
 *   real element access produces. Labelled separately because it leans on that
 *   convention rather than being unconditional.
 * ⚠️ TIER 3 WAS UNSOUND UNTIL 2026-08-04. The bound below used to be asserted from the
 *   mere EXISTENCE of a comparison and propagated to EVERY successor block, including
 *   the one reached when the comparison FAILED. Proven counterexample, with runtime
 *   confirmation: tools/phase4_e16_bound_hint_counterexample.c +
 *   tests/test_region_provenance_bound_soundness.py. A bound is now applied only along
 *   the edge on which the comparison is true, is captured AT the branch (before the
 *   delay slot runs), and is dropped when the delay slot rewrites the register it
 *   names. B06's committed frontier is unaffected -- its artifact records
 *   excluded_out_of_bound == 0 in scope, so its 251 residual never used this tier --
 *   but 35 unsound exclusions elsewhere in the image disappeared with the fix.
 *
 * TIER 3 (EXCLUDED_OUT_OF_BOUND) -- STRICTLY STRONGER than alignment alone: reads the
 *   loop's own bounds check straight out of the disassembly (`slti`/`sltiu idx,N`) and
 *   proves the aligned, non-negative index the target would need is still >= that
 *   proven bound, i.e. beyond where the loop can ever put i. This is what actually
 *   closes an access whose residue class the target happens to land on -- alignment
 *   alone cannot. Relies on the same non-negative-index convention as Tier 2, PLUS
 *   the (weaker, disclosed) assumption that the detected comparison genuinely gates
 *   the index at the region's formation point, not just "a comparison against this
 *   register happened somewhere" -- see the `bound_hint` comment on `transfer()`.
 *
 * A SECOND way a REGION is discovered: a pointer WALKED via `addiu reg,reg,STRIDE`
 * inside a loop (rather than an index computed fresh via sll+addu) produces a CONST
 * value set that grows by one new value per loop-carried merge. It used to collapse
 * straight to TOP once that set exceeded MAXV (6) distinct values -- discarding a
 * perfectly regular arithmetic progression that is exactly as region-representable as
 * the sll/addu case. Detected in `merge_val` as a property of the value set itself
 * (sorted, every consecutive delta equal and non-zero), not by pattern-matching the
 * addiu instruction, so it fires regardless of which control-flow shape grew the set.
 * Because the observed set is only a SNAPSHOT of the true trajectory, the smallest
 * value seen is not provably the array's true start -- so these regions carry
 * `verified_anchor = 0` and Tiers 2/3 (which depend on the SIGN of the computed index
 * relative to that anchor) are suppressed for them; only Tier 1 (alignment, which is
 * invariant to which point in the progression is chosen as anchor) applies.
 * Anything that survives all three tiers stays in the residual -- correctly
 * conservative, not "probably fine."
 *
 * SCOPE, STATED NOT HIDDEN
 * -------------------------
 * The sll/addu pairing is detected via a per-register "shift hint" carried in the SAME
 * worklist that propagates register values: a flat 3-state lattice (BOTTOM/unmerged,
 * a concrete shift amount, or TOP/invalidated-or-conflicting) that flows across block
 * boundaries exactly like the value lattice does. An index computed in one block and
 * used to form a region in a LATER block is therefore recovered, not just the
 * single-block case. Still not fully general -- a shift amount only survives to a
 * later block along paths where nothing else has touched that register since, and any
 * disagreement between merged paths collapses to TOP (no region) rather than trying to
 * reconcile two different shift origins. A missed case just stays in the residual --
 * REDUCED RECALL, never a soundness risk. Interprocedural argument seeding mirrors
 * census_address.py's `known_callable`-grows-from-static-jal-scan logic, but resolved-
 * jalr propagation is deliberately NOT ported: measured on the real image in Python,
 * it changed the residual by exactly zero, so porting it would add engineering weight
 * for no verifiable gain. Global-pointer provenance (store-observed constants) is also
 * not ported -- it shaved the whole-image residual by ~0.16% in the Python run and is
 * orthogonal to the region question this tool exists to answer.
 *
 * VALIDATION
 * -----------
 * Before trusting ANY region-exclusion number, this must reproduce census_address.py's
 * pinned baseline exactly on the same inputs: 14 hits, 882 same-width residual in the
 * 34 related functions. That parity check is the point of --baseline-only.
 *
 * USAGE
 *   cc -O2 -o tools/region_provenance tools/region_provenance.c
 *   tools/region_provenance SCUS_942.88 analysis/functions_resident.txt \
 *       0x800A657E 2 --json analysis/phase4_region_provenance.json
 *
 *   # an overlay: raw image, load base supplied, function list from the index
 *   tools/region_provenance LEVEL02/LEVEL.BIN /tmp/level02.txt \
 *       0x800823A0 2 --raw 0x800B39A0 --json /tmp/level02.json
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>

/* ---------------------------------------------------------------- constants ---- */

#define MAXV 6                 /* per-register constant-set cap, matches census_address.py MAX_VALS */
#define MAX_FUNCS 4096
#define MAX_ROUNDS 10
#define STACK_BASE 0x00100000u
#define GP_VALUE   0x80081D98u

enum { K_BOT = 0, K_CONST = 1, K_REGION = 2, K_TOP = 3 };

typedef struct {
    uint8_t kind;
    uint32_t consts[MAXV];
    uint8_t nconsts;
    uint32_t rbase;
    uint32_t rstride;
    int64_t  roff;
    int32_t  idx_bound;   /* -1 = no known bound; else the raw loop index is provably
                           * < idx_bound on every path reaching this region's creation
                           * (see idx_bound_hint / TIER 3 below) */
    uint8_t  pb_taint;    /* 1 = this value MAY be derived from a player-block pointer.
                           * Survives the collapse to TOP, which is the whole point:
                           * once a value is unknown we still know whether it COULD be
                           * a pointer into the target's own block. */
    uint8_t  verified_anchor;  /* 1 = rbase is a compile-time literal (lui/addiu), so
                                * "i >= 0 from rbase" is a real claim about the array's
                                * true start -- Tiers 2/3 (which depend on the SIGN of
                                * the computed index) are sound. 0 = rbase is merely the
                                * SMALLEST value observed in an arithmetic-progression
                                * value set (a walking pointer, `addiu reg,reg,S` in a
                                * loop) -- alignment (Tier 1) is invariant to which point
                                * in the progression is chosen as the anchor, so it stays
                                * sound, but Tiers 2/3 are NOT: the true walk could extend
                                * below the smallest point this analysis happened to
                                * observe, so a "negative index relative to this anchor"
                                * is not actually proof of unreachability. */
} Val;

static const Val VBOT = {K_BOT, {0}, 0, 0, 0, 0, -1, 0, 0};
static const Val VTOP = {K_TOP, {0}, 0, 0, 0, 0, -1, 0, 0};

static Val vconst1(uint32_t x) {
    Val v = VBOT; v.kind = K_CONST; v.consts[0] = x; v.nconsts = 1; return v;
}

static bool is_const_zero(Val v) { return v.kind == K_CONST && v.nconsts == 1 && v.consts[0] == 0; }
static bool is_const_single(Val v, uint32_t *out) {
    if (v.kind == K_CONST && v.nconsts == 1) { *out = v.consts[0]; return true; }
    return false;
}

/* -------------------------------------------------------------- CPU regs ---- */

static const char *REGS[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5",
    "t6","t7","s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1",
    "gp","sp","fp","ra"
};

/* ---------------------------------------------------------------- image ---- */

static uint8_t *g_text;         /* pristine .text/.data, starting at g_base */
static uint32_t g_base, g_end;

typedef struct { uint32_t addr; uint32_t size; char name[96]; } FuncRec;
static FuncRec g_funcs[MAX_FUNCS];
static int g_nfuncs;

static inline uint32_t rd_word(uint32_t va) {
    uint32_t off = va - g_base;
    return g_text[off] | (g_text[off+1]<<8) | (g_text[off+2]<<16) | ((uint32_t)g_text[off+3]<<24);
}

static int32_t s16(uint32_t v) { return (v & 0x8000) ? (int32_t)v - 0x10000 : (int32_t)v; }

/* binary search: index of the last function whose addr <= va, else -1 */
static int func_index_at_or_before(uint32_t va) {
    int lo = 0, hi = g_nfuncs - 1, ans = -1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if (g_funcs[mid].addr <= va) { ans = mid; lo = mid + 1; }
        else hi = mid - 1;
    }
    return ans;
}

static bool is_function_start(uint32_t va) {
    int i = func_index_at_or_before(va);
    return i >= 0 && g_funcs[i].addr == va;
}

static uint32_t func_extent(int i) {
    if (g_funcs[i].size) return g_funcs[i].addr + g_funcs[i].size;
    if (i + 1 < g_nfuncs) return g_funcs[i + 1].addr;
    return g_end;
}

static const char *func_owner_name(uint32_t va) {
    int i = func_index_at_or_before(va);
    return i >= 0 ? g_funcs[i].name : "?";
}

/* -------------------------------------------------------- opcode helpers ---- */

typedef struct { int op, rs, rt, rd, sa, funct; int32_t imm; } Insn;

typedef struct { uint32_t *items; int n, cap; } U32List;
static void u32_push_unique(U32List *L, uint32_t v) {
    for (int i = 0; i < L->n; i++) if (L->items[i] == v) return;
    if (L->n == L->cap) { L->cap = L->cap ? L->cap * 2 : 64; L->items = realloc(L->items, L->cap * sizeof(uint32_t)); }
    L->items[L->n++] = v;
}

static Insn decode(uint32_t w) {
    Insn d;
    d.op = w >> 26; d.rs = (w >> 21) & 31; d.rt = (w >> 16) & 31;
    d.rd = (w >> 11) & 31; d.sa = (w >> 6) & 31; d.funct = w & 0x3F;
    d.imm = s16(w & 0xFFFF);
    return d;
}

static int width_of_load_store(int op, bool *is_load) {
    switch (op) {
        case 0x20: *is_load = true;  return 1;   /* lb  */
        case 0x24: *is_load = true;  return 1;   /* lbu */
        case 0x28: *is_load = false; return 1;   /* sb  */
        case 0x21: *is_load = true;  return 2;   /* lh  */
        case 0x25: *is_load = true;  return 2;   /* lhu */
        case 0x29: *is_load = false; return 2;   /* sh  */
        case 0x23: *is_load = true;  return 4;   /* lw  */
        case 0x22: *is_load = true;  return 4;   /* lwl */
        case 0x26: *is_load = true;  return 4;   /* lwr */
        case 0x2B: *is_load = false; return 4;   /* sw  */
        case 0x2A: *is_load = false; return 4;   /* swl */
        case 0x2E: *is_load = false; return 4;   /* swr */
        default: return 0;
    }
}

/* --------------------------------------------------------------- state ---- */

typedef struct { Val r[32]; } RegState;

/* A register walking a pool via `addiu reg,reg,STRIDE` inside a loop (rather than an
 * index computed fresh each iteration via sll+addu) produces a CONST set that grows
 * by one new value per loop-carried merge -- reg, reg+STRIDE, reg+2*STRIDE, ... --
 * and once that set exceeds MAXV it used to collapse straight to TOP, discarding a
 * perfectly regular arithmetic progression that is EXACTLY as region-representable as
 * the sll/addu case: `base + i*stride` for integer i >= 0. Detected here as a
 * property of the value SET itself (sorted, checking every consecutive delta is
 * equal and non-zero) rather than by pattern-matching the addiu instruction that
 * produced it -- works regardless of which control-flow shape grew the set. */
static bool arith_progression(uint32_t *vals, int n, uint32_t *out_base, uint32_t *out_stride) {
    if (n < 3) return false;   /* need at least 3 points to be confident it's a real AP */
    uint32_t sorted[MAXV * 2];
    for (int i = 0; i < n; i++) sorted[i] = vals[i];
    for (int i = 1; i < n; i++) {              /* insertion sort, n is tiny */
        uint32_t key = sorted[i]; int j = i - 1;
        while (j >= 0 && sorted[j] > key) { sorted[j + 1] = sorted[j]; j--; }
        sorted[j + 1] = key;
    }
    uint32_t delta = sorted[1] - sorted[0];
    if (delta == 0) return false;
    for (int i = 2; i < n; i++) if (sorted[i] - sorted[i - 1] != delta) return false;
    *out_base = sorted[0];
    *out_stride = delta;
    return true;
}

static Val merge_val(Val a, Val b) {
    if (a.kind == K_BOT) return b;
    if (b.kind == K_BOT) return a;
    uint8_t t = a.pb_taint | b.pb_taint;   /* MAY: taint survives every merge */
    if (a.kind == K_TOP || b.kind == K_TOP) { Val v = VTOP; v.pb_taint = t; return v; }
    if (a.kind == K_CONST && b.kind == K_CONST) {
        Val out = VBOT; out.kind = K_CONST;
        uint32_t seen[MAXV * 2]; int n = 0;
        for (int i = 0; i < a.nconsts; i++) seen[n++] = a.consts[i];
        for (int i = 0; i < b.nconsts; i++) {
            bool dup = false;
            for (int j = 0; j < n; j++) if (seen[j] == b.consts[i]) { dup = true; break; }
            if (!dup) seen[n++] = b.consts[i];
        }
        if (n > MAXV) {
            uint32_t base, stride;
            if (arith_progression(seen, n, &base, &stride)) {
                Val r = VBOT; r.kind = K_REGION; r.rbase = base; r.rstride = stride;
                r.roff = 0; r.idx_bound = -1; r.verified_anchor = 0; r.pb_taint = t;
                return r;
            }
            Val v = VTOP; v.pb_taint = t; return v;
        }
        out.nconsts = n;
        for (int i = 0; i < n; i++) out.consts[i] = seen[i];
        out.pb_taint = t;
        return out;
    }
    if (a.kind == K_REGION && b.kind == K_REGION &&
        a.rbase == b.rbase && a.rstride == b.rstride && a.roff == b.roff) {
        Val out = a;
        /* MAY-merge for the bound: if the index is provably < N1 on one incoming
         * path and < N2 on the other, it is provably < max(N1,N2) regardless of
         * which path was taken. -1 (unknown) poisons the merge to -1, same as TOP. */
        out.idx_bound = (a.idx_bound < 0 || b.idx_bound < 0) ? -1
                       : (a.idx_bound > b.idx_bound ? a.idx_bound : b.idx_bound);
        out.verified_anchor = a.verified_anchor && b.verified_anchor;
        out.pb_taint = t;
        return out;
    }
    /* SAME RESIDUE CLASS, different anchor/offset: a walking pointer's loop-carried
     * merge sees REGION(base,S,roff=0) against REGION(base,S,roff=S) after the
     * `addiu reg,reg,S` increment -- identical value family, and the old exact-
     * equality test above collapsed it to TOP, killing the region the moment the
     * loop closed. If the two anchors differ by a multiple of the stride, the union
     * is the same residue class. Tier 1 (alignment) is invariant under re-anchoring. */
    if (a.kind == K_REGION && b.kind == K_REGION && a.rstride == b.rstride) {
        int64_t da = (int64_t)a.rbase + a.roff, db = (int64_t)b.rbase + b.roff;
        int64_t S = (int64_t)a.rstride;
        if ((da - db) % S == 0) {
            if (a.verified_anchor && b.verified_anchor) {
                /* both anchors are proven literals: keep the smaller, which covers
                 * the other's i>=0 family; the finite set of literal anchors means
                 * this min-chain terminates. */
                Val out = (da <= db) ? a : b;
                out.verified_anchor = 1;
                out.idx_bound = -1; out.pb_taint = t;
                return out;
            }
            /* va=0 result: CANONICALIZE the anchor to a fixed representative of the
             * residue class (0x80000000 + (anchor mod S)). Without this, a REVERSE-
             * walking pointer (`addiu reg,reg,-S`) makes every revisit produce a
             * strictly smaller min-anchor, so the loop-carried merge never converges
             * and churns until the per-function visit cap -- which is exactly what
             * silently truncated the final-round scan (the observed 149 -> 143
             * indirect-site drop) the first time these merges ran. Tier 1 only ever
             * consults the residue class, so the canonical anchor is equally sound;
             * Tiers 2/3 are already disabled for va=0. */
            Val out = VBOT; out.kind = K_REGION; out.rstride = a.rstride;
            int64_t r = ((da - (int64_t)0x80000000) % S + S) % S;
            out.rbase = (uint32_t)((int64_t)0x80000000 + r); out.roff = 0;
            out.idx_bound = -1; out.verified_anchor = 0; out.pb_taint = t;
            return out;
        }
        { Val v = VTOP; v.pb_taint = t; return v; }
    }
    /* CONST absorbed into a compatible REGION: the other way a walking loop dies --
     * one path still holds the initial CONST pointer while another already widened
     * to the REGION. If every constant lies in the region's residue class, the union
     * IS the region; a constant below the anchor demotes verified_anchor (the true
     * family extends below the proven start), and any constant outside the proven
     * index bound drops the bound. A constant outside the residue class -> TOP. */
    if ((a.kind == K_REGION && b.kind == K_CONST) ||
        (a.kind == K_CONST && b.kind == K_REGION)) {
        Val r = (a.kind == K_REGION) ? a : b;
        Val c = (a.kind == K_REGION) ? b : a;
        int64_t anchor = (int64_t)r.rbase + r.roff;
        for (int i = 0; i < c.nconsts; i++) {
            int64_t dlt = (int64_t)c.consts[i] - anchor;
            if (dlt % (int64_t)r.rstride != 0) { Val v = VTOP; v.pb_taint = t; return v; }
        }
        for (int i = 0; i < c.nconsts; i++) {
            int64_t dlt = (int64_t)c.consts[i] - anchor;
            if (dlt < 0) { r.verified_anchor = 0; break; }
        }
        if (r.idx_bound >= 0) {
            for (int i = 0; i < c.nconsts; i++) {
                int64_t idx = ((int64_t)c.consts[i] - anchor) / (int64_t)r.rstride;
                if (idx < 0 || idx >= r.idx_bound) { r.idx_bound = -1; break; }
            }
        }
        r.pb_taint = t;
        return r;
    }
    { Val v = VTOP; v.pb_taint = t; return v; }   /* incompatible: TOP, taint kept */
}

/* The target's owning block. A value is PB-TAINTED when it may point into this
 * block -- the only way an access can reach the target through a computed pointer. */
static uint32_t g_block_lo, g_block_hi;

/* MAY the value point into the owning block?
 *
 * 2026-08-04. This used to inspect K_CONST only, so a K_REGION value -- the
 * `lui base; addu base,idx; lw/sw disp(base)` shape -- was never treated as a
 * block pointer no matter where it pointed. For a target whose pointers are
 * ALWAYS regions (an array indexed by a data-dependent value, e.g. the LEVEL.RAW
 * chunk pointer tables indexed by subtype marker) that made the escape analysis
 * structurally BLIND: it reported "0 stores may write a block pointer to memory"
 * without ever being able to say otherwise. A clean negative from a check that
 * cannot see the thing is not evidence.
 *
 * The fix is NOT to treat every region as may-alias. An arithmetic progression
 * with an unknown index reaches everything -- for any window at least as wide as
 * the stride the test becomes a tautology (measured: it flagged 57 stores and 258
 * argument-passing call sites for a 160-byte, stride-4 window, i.e. essentially
 * every region in the image). That is precision loss masquerading as rigour.
 *
 * So regions are classified in three ways, and the undecidable case is COUNTED
 * rather than silently resolved in either direction:
 *   - bounded region that provably reaches the block  -> may-alias (return 1)
 *   - bounded region that provably cannot             -> excluded (return 0)
 *   - UNBOUNDED region                                -> counted in
 *     g_region_undecided and returns 0, because reporting it as an escape would
 *     make every result vacuous. Callers MUST read that counter: a non-zero
 *     value means the escape argument is NOT established for this target.
 */
static long g_region_undecided;

static uint8_t val_is_pb(const Val *v) {
    if (v->pb_taint) return 1;
    if (v->kind == K_CONST) {
        for (int i = 0; i < v->nconsts; i++)
            if (v->consts[i] >= g_block_lo && v->consts[i] < g_block_hi) return 1;
    }
    if (v->kind == K_REGION) {
        int64_t base = (int64_t)v->rbase + v->roff;
        int64_t S = v->rstride ? (int64_t)v->rstride : 1;
        if (S < 0) S = -S;
        int64_t lo = (int64_t)g_block_lo, hi = (int64_t)g_block_hi;
        if (v->idx_bound <= 0) { g_region_undecided++; return 0; }
        /* proven index range [0, idx_bound): enumerate the reachable addresses */
        for (int64_t i = 0; i < v->idx_bound; i++) {
            int64_t a = base + i * S;
            if (a >= lo && a < hi) return 1;
            if (a >= hi && S > 0) break;
        }
        return 0;
    }
    return 0;
}

static bool val_eq(const Val *a, const Val *b) {
    if (a->kind != b->kind) return false;
    if (a->kind == K_CONST) {
        if (a->nconsts != b->nconsts) return false;
        for (int k = 0; k < a->nconsts; k++) if (a->consts[k] != b->consts[k]) return false;
        return true;
    }
    if (a->pb_taint != b->pb_taint) return false;
    if (a->kind == K_REGION)
        return a->rbase == b->rbase && a->rstride == b->rstride && a->roff == b->roff
            && a->idx_bound == b->idx_bound && a->verified_anchor == b->verified_anchor;
    return true;   /* BOT == BOT, TOP == TOP */
}

static bool merge_state(RegState *dst, const RegState *src) {
    bool changed = false;
    for (int i = 0; i < 32; i++) {
        Val m = merge_val(dst->r[i], src->r[i]);
        /* cheap inequality check covering the fields that matter */
        Val *d = &dst->r[i];
        bool eq = d->kind == m.kind;
        if (eq && m.kind == K_CONST) {
            eq = d->nconsts == m.nconsts;
            if (eq) for (int k = 0; k < m.nconsts; k++) if (d->consts[k] != m.consts[k]) { eq = false; break; }
        } else if (eq && m.kind == K_REGION) {
            eq = d->rbase == m.rbase && d->rstride == m.rstride && d->roff == m.roff
                && d->idx_bound == m.idx_bound && d->verified_anchor == m.verified_anchor;
        }
        if (eq) eq = (d->pb_taint == m.pb_taint);
        if (!eq) { dst->r[i] = m; changed = true; }
    }
    return changed;
}

/* ---------------------------------------------------- per-instruction transfer --- */

typedef struct {
    uint32_t pc_num;
    char pc[12]; char insn[64]; char kind[8]; char function[96];
    int width;
    /* only meaningful for target-covering accesses */
    char address[12];
} Access;

typedef struct { Access *items; int n, cap; } AccessList;
static void access_push(AccessList *L, Access a) {
    if (L->n == L->cap) { L->cap = L->cap ? L->cap * 2 : 64; L->items = realloc(L->items, L->cap * sizeof(Access)); }
    L->items[L->n++] = a;
}

typedef struct {
    uint32_t pc_num;
    char pc[12]; char function[96]; char kind[24]; /* EXCLUDED_ALIGNMENT / EXCLUDED_NEGATIVE_INDEX / EXCLUDED_OUT_OF_BOUND */
    uint32_t rbase; uint32_t rstride; int64_t roff; int32_t insn_off;
    int64_t computed_idx; int32_t idx_bound;   /* for audit: what the tier actually computed */
    uint8_t verified_anchor;  /* 1 = base is a compile-time literal; 0 = an
                               * arithmetic-progression-derived walking-pointer base */
} Exclusion;
typedef struct { Exclusion *items; int n, cap; } ExclList;
static void excl_push(ExclList *L, Exclusion e) {
    if (L->n == L->cap) { L->cap = L->cap ? L->cap * 2 : 64; L->items = realloc(L->items, L->cap * sizeof(Exclusion)); }
    L->items[L->n++] = e;
}

/* Dedup-by-pc_num, O(n log n): a block gets reprocessed every time an incoming edge's
 * state changes during the worklist's convergence, so without this, the SAME
 * instruction is recorded once per revisit -- exactly the bug found in
 * census_address.py's Python twin (882 "residual sites" turned out to be 416 distinct
 * ones once deduped). Keeps the LAST record for a given pc (arbitrary but
 * deterministic; all records for one pc carry the same classification in practice). */
static int access_pc_cmp(const void *a, const void *b) {
    uint32_t x = ((const Access*)a)->pc_num, y = ((const Access*)b)->pc_num;
    return x < y ? -1 : (x > y ? 1 : 0);
}
static void dedup_accesses(AccessList *L) {
    if (L->n == 0) return;
    qsort(L->items, L->n, sizeof(Access), access_pc_cmp);
    int w = 0;
    for (int i = 0; i < L->n; i++) {
        if (w > 0 && L->items[w-1].pc_num == L->items[i].pc_num) L->items[w-1] = L->items[i];
        else L->items[w++] = L->items[i];
    }
    L->n = w;
}
static int excl_pc_cmp(const void *a, const void *b) {
    uint32_t x = ((const Exclusion*)a)->pc_num, y = ((const Exclusion*)b)->pc_num;
    return x < y ? -1 : (x > y ? 1 : 0);
}
static void dedup_exclusions(ExclList *L) {
    if (L->n == 0) return;
    qsort(L->items, L->n, sizeof(Exclusion), excl_pc_cmp);
    int w = 0;
    for (int i = 0; i < L->n; i++) {
        if (w > 0 && L->items[w-1].pc_num == L->items[i].pc_num) L->items[w-1] = L->items[i];
        else L->items[w++] = L->items[i];
    }
    L->n = w;
}

static uint32_t g_target_lo, g_target_hi;      /* [lo, hi) target byte range */
static AccessList g_hits;
static AccessList g_unresolved;                /* base kind != CONST-with-a-hit-determined AND not region-excluded */
static ExclList g_exclusions;
static U32List g_indirect_pcs;   /* distinct unresolved-jalr PC set for this round */
static int g_visit_cap_hits;     /* functions whose scan was truncated by the visit cap */

/* JR-TABLE TAIL DISPATCH. A `jr` through a switch table is a TAIL JUMP: the target
 * continues with the dispatcher's ENTIRE register file, not a fresh a0-a3 argument
 * set -- which is exactly why the mover-VM opcode handlers (reached only through the
 * table at 0x8001B2F4, never by jal) had TOP everything and contributed ~55 residual
 * sites. Seeding them is sound under the same disclosed frame as jal-argument
 * seeding: enumerated entries are assumed complete, with the unresolved-jalr count
 * and the overlay call surface quoted as the standing holes. */
static RegState g_tail_pending[MAX_FUNCS];
static bool g_tail_seeded_this_round[MAX_FUNCS];
static bool g_tail_target[MAX_FUNCS];         /* persistent: once discovered, stays */

static U32List g_tainted_stores;   /* FULL-WIDTH stores whose VALUE may be a block pointer */
static U32List g_tainted_partial_stores; /* sb/sh: cannot install a loadable pointer alone */
static U32List g_taint_dests;      /* where those stores land (0xFFFFFFFF = unknown) */
static U32List g_tainted_arg_calls;/* jal sites passing a PB pointer as an argument */

typedef struct { uint32_t pc; uint32_t table; int ntargets; int skipped; uint32_t targets[64]; } DispatchRec;
static DispatchRec g_dispatch[256]; static int g_ndispatch;

static void record_dispatch(uint32_t pc, uint32_t table, int nt, int skipped, const uint32_t *tg) {
    for (int i = 0; i < g_ndispatch; i++) if (g_dispatch[i].pc == pc) return;
    if (g_ndispatch >= 256) return;
    DispatchRec *r = &g_dispatch[g_ndispatch++];
    r->pc = pc; r->table = table; r->ntargets = nt; r->skipped = skipped;
    for (int i = 0; i < nt && i < 64; i++) r->targets[i] = tg[i];
}

static void fmt_insn(char *out, int op, const char *name, int rt, int rs, int32_t off) {
    if (off < 0) snprintf(out, 64, "%s %s, -0x%x(%s)", name, REGS[rt], -off, REGS[rs]);
    else         snprintf(out, 64, "%s %s, 0x%x(%s)", name, REGS[rt], off, REGS[rs]);
}

/* returns true if this access's base is a CONST set (so the caller can do the
 * ordinary overlap hit-test); false if REGION or TOP (handled here directly). */
static void handle_mem_access(uint32_t pc, Insn d, bool is_load, int width, RegState *st) {
    static const char *names4[] = {NULL};
    (void)names4;
    const char *name = NULL;
    switch (d.op) {
        case 0x20: name = "lb"; break; case 0x24: name = "lbu"; break; case 0x28: name = "sb"; break;
        case 0x21: name = "lh"; break; case 0x25: name = "lhu"; break; case 0x29: name = "sh"; break;
        case 0x23: name = "lw"; break; case 0x22: name = "lwl"; break; case 0x26: name = "lwr"; break;
        case 0x2B: name = "sw"; break; case 0x2A: name = "swl"; break; case 0x2E: name = "swr"; break;
    }
    Val base = st->r[d.rs];
    char pcbuf[12]; snprintf(pcbuf, sizeof pcbuf, "0x%08X", pc);
    char insnbuf[64]; fmt_insn(insnbuf, d.op, name, d.rt, d.rs, d.imm);
    const char *fn = func_owner_name(pc);

    if (base.kind == K_CONST) {
        for (int i = 0; i < base.nconsts; i++) {
            uint32_t ea = base.consts[i] + (uint32_t)d.imm;
            uint32_t ea_hi = ea + width;
            /* OVERLAP test: [ea, ea+width) intersects [target_lo, target_hi) */
            if (ea < g_target_hi && ea_hi > g_target_lo) {
                Access a; a.pc_num = pc; snprintf(a.pc, 12, "%s", pcbuf); snprintf(a.insn, 64, "%s", insnbuf);
                snprintf(a.kind, 8, "%s", is_load ? "read" : "write");
                snprintf(a.function, 96, "%s", fn); a.width = width;
                snprintf(a.address, 12, "0x%08X", ea);
                access_push(&g_hits, a);
                return;   /* one hit record per site is enough, matches Python's `break` */
            }
        }
        return;   /* resolved base, definitively does not cover the target */
    }

    if (base.kind == K_REGION && base.rstride > 0) {
        /* Family of possible access START addresses: A = rbase + roff + off + i*S.
         * The access covers [A, A+width); the target covers [t_lo, t_hi). They
         * overlap iff A - t_lo lies in [-(width-1), t_width-1], i.e. iff some
         * multiple of S lies in the window
         *     [want - (width-1), want + t_width - 1]
         * where want = t_lo - off - rbase - roff (so A - t_lo = i*S - want).
         *
         * ⚠ SOUNDNESS FIX: the first version of this tier tested only
         * `want % S == 0` -- the A == t_lo case -- which is the SAME start-address-
         * only straddle hole found and fixed in census_address.py's hit test
         * earlier. An access can overlap the target without starting on it (e.g. a
         * width-4 access at t_lo-2), and `want % S` one off either way was being
         * wrongly excluded. The window below covers every overlapping start. */
        int tw = (int)(g_target_hi - g_target_lo);
        int64_t want = (int64_t)g_target_lo - d.imm - (int64_t)base.rbase - base.roff;
        int64_t cand[8]; int ncand = 0;
        for (int64_t r = want - (width - 1); r <= want + tw - 1; r++)
            if (r % (int64_t)base.rstride == 0 && ncand < 8)
                cand[ncand++] = r / (int64_t)base.rstride;
        if (ncand == 0) {
            Exclusion e = {0}; e.pc_num = pc; snprintf(e.pc, 12, "%s", pcbuf); snprintf(e.function, 96, "%s", fn);
            snprintf(e.kind, 24, "EXCLUDED_ALIGNMENT");
            e.rbase = base.rbase; e.rstride = base.rstride; e.roff = base.roff; e.insn_off = d.imm;
            e.computed_idx = 0; e.idx_bound = base.idx_bound;
            e.verified_anchor = base.verified_anchor;
            excl_push(&g_exclusions, e);
            return;
        }
        /* Tiers 2/3 depend on the SIGN/magnitude of the candidate indices, which is
         * only meaningful relative to the array's TRUE starting point. For an
         * arithmetic-progression-derived region (walking pointer, verified_anchor
         * == 0), rbase is merely the smallest value observed -- the true walk could
         * extend further back, so index-based reasoning is not sound; only Tier 1
         * (anchor-invariant) applies. With a verified anchor, EVERY candidate index
         * that could overlap must be individually unreachable (negative, or beyond
         * the proven loop bound) for the site to be excluded. */
        if (base.verified_anchor) {
            bool all_unreach = true, all_neg = true;
            for (int i = 0; i < ncand; i++) {
                bool neg = cand[i] < 0;
                bool oob = base.idx_bound >= 0 && cand[i] >= base.idx_bound;
                if (!neg) all_neg = false;
                if (!neg && !oob) { all_unreach = false; break; }
            }
            if (all_unreach) {
                Exclusion e = {0}; e.pc_num = pc; snprintf(e.pc, 12, "%s", pcbuf); snprintf(e.function, 96, "%s", fn);
                snprintf(e.kind, 24, all_neg ? "EXCLUDED_NEGATIVE_INDEX"
                                             : "EXCLUDED_OUT_OF_BOUND");
                e.rbase = base.rbase; e.rstride = base.rstride; e.roff = base.roff; e.insn_off = d.imm;
                e.computed_idx = cand[0]; e.idx_bound = base.idx_bound;
                e.verified_anchor = base.verified_anchor;
                excl_push(&g_exclusions, e);
                return;
            }
        }
        /* some candidate index is genuinely reachable (or the anchor is unproven):
         * stays in the residual, honestly. */
    }

    /* K_BOT = "no possible value reaches here" (an argument register of a function
     * whose seeding has not converged yet, or a genuinely dead path). Python's twin
     * represents this as the empty set and records NOTHING for it -- `for b in base`
     * iterates zero times -- so mirroring that here keeps the two implementations'
     * final-round outputs comparable. Only the final round's records survive, and by
     * then every reachable entry is seeded, so this is vacuous, not optimistic. */
    if (base.kind == K_BOT) return;

    /* TOP, or a REGION we could not exclude: residual. */
    Access a; a.pc_num = pc; snprintf(a.pc, 12, "%s", pcbuf); snprintf(a.insn, 64, "%s", insnbuf);
    snprintf(a.kind, 8, "%s", is_load ? "read" : "write");
    snprintf(a.function, 96, "%s", fn); a.width = width;
    a.address[0] = 0;
    access_push(&g_unresolved, a);
}

/* Full CPU-flag-free transfer for one instruction.
 *
 * `shift_hint` is a peephole side-table: shift_hint[r] = the sa of the most recent
 * `sll r,_,sa` seen on any path reaching this point (or -1). Invalidated for a
 * register the moment anything else writes to it.
 *
 * `bound_hint` is TIER 3's side-table: bound_hint[r] = N if the most recent
 * `slti/sltiu _,r,N` seen on any path reaching this point tested register r against
 * N (or -1). This is a WEAKER signal than shift_hint -- it records that a comparison
 * against r happened, not that the comparison's result was verified to GATE further
 * execution so that r < N is actually guaranteed here. It relies on the standard
 * compiler idiom (a bounds check immediately followed by the branch that uses it),
 * the same class of assumption TIER 2 (EXCLUDED_NEGATIVE_INDEX) already leans on --
 * disclosed, not hidden, and every TIER 3 exclusion is labelled as such.
 * Propagated through `sll` (the bound on the raw loop index survives being shifted
 * into a byte offset -- it's still the same index, just scaled) and invalidated by
 * everything else that writes the register, identically to shift_hint. */
static void transfer(uint32_t pc, RegState *st, int8_t *shift_hint, int32_t *bound_hint,
                     uint32_t *table_hint, int32_t *table_cnt,
                     int8_t *cmp_src, int32_t *cmp_val) {
    uint32_t w = rd_word(pc);
    Insn d = decode(w);
    bool is_load; int width = width_of_load_store(d.op, &is_load);

    if (width) {
        /* STORE-VALUE TAINT: does this store put a player-block pointer INTO memory?
         * If no store anywhere does, then no memory location can ever hold such a
         * pointer, so no `lw`-loaded base can be one -- which is exactly what the
         * ~110 memory-loaded residual sites need in order to be excluded. */
        if (!is_load && val_is_pb(&st->r[d.rt])) {
            u32_push_unique(&g_tainted_stores, pc);
            Val b = st->r[d.rs];
            if (b.kind == K_CONST) { for (int i=0;i<b.nconsts;i++)
                    u32_push_unique(&g_taint_dests, b.consts[i] + (uint32_t)d.imm); }
            else if (b.kind == K_REGION) u32_push_unique(&g_taint_dests,
                    (uint32_t)((int64_t)b.rbase + b.roff + d.imm));
            else u32_push_unique(&g_taint_dests, 0xFFFFFFFFu);   /* unknown destination */
        }
        handle_mem_access(pc, d, is_load, width, st);
        if (is_load) {
            /* JUMP-TABLE PROVENANCE for `jr`: a word loaded through a va=1, stride-4
             * REGION base is a switch/dispatch-table read -- the compiler's shape for
             * `table[i]` where the table start (rbase + roff + imm) is compile-time
             * data inside the image. Record the start VA (and the region's proven
             * index bound as the entry count, if one was captured) so a later
             * `jr rt` can enumerate the targets. Justified ONLY for jr targets:
             * switch tables in this image are .text/.rodata and never runtime-
             * written, the same disclosed reasoning as the jalr static-table read
             * in census_address.py. Any other write to the register kills the hint. */
            uint32_t th = 0; int32_t tc = -1;
            Val b = st->r[d.rs];   /* read base BEFORE the destination is clobbered */
            if (d.op == 0x23 && b.kind == K_REGION && b.rstride == 4 && b.verified_anchor) {
                int64_t t = (int64_t)b.rbase + b.roff + d.imm;
                if (t >= (int64_t)g_base && t < (int64_t)g_end) { th = (uint32_t)t; tc = b.idx_bound; }
            }
            st->r[d.rt] = VTOP;
            if (d.rt) { shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1;
                        table_hint[d.rt] = th; table_cnt[d.rt] = tc; }
        }
        return;
    }
    if (d.op == 0x0F) {                          /* lui */
        if (d.rt) { st->r[d.rt] = vconst1(((uint32_t)(d.imm & 0xFFFF)) << 16); shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1; table_hint[d.rt] = 0; }
        return;
    }
    if (d.op == 0x08 || d.op == 0x09) {           /* addi / addiu */
        Val v = st->r[d.rs];
        Val out;
        if (v.kind == K_CONST) {
            out = VBOT; out.kind = K_CONST; out.nconsts = v.nconsts;
            for (int i = 0; i < v.nconsts; i++) out.consts[i] = v.consts[i] + (uint32_t)d.imm;
        } else if (v.kind == K_REGION) {
            out = v; out.roff += d.imm;
        } else out = VTOP;
        out.pb_taint |= val_is_pb(&v);   /* offsetting a PB pointer keeps it one */
        if (d.rt) { st->r[d.rt] = out; shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1; table_hint[d.rt] = 0; }
        return;
    }
    if (d.op == 0x0D) {                           /* ori -- CONST only, matches Python */
        Val v = st->r[d.rs];
        Val out = VTOP;
        if (v.kind == K_CONST) {
            out = VBOT; out.kind = K_CONST; out.nconsts = v.nconsts;
            for (int i = 0; i < v.nconsts; i++) out.consts[i] = v.consts[i] | (uint32_t)(d.imm & 0xFFFF);
        }
        if (d.rt) { st->r[d.rt] = out; shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1; table_hint[d.rt] = 0; }
        return;
    }
    if (d.op == 0x0A || d.op == 0x0B) {           /* slti / sltiu -- TIER 3 bound signal */
        if (d.rt) { st->r[d.rt] = VTOP; shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1; table_hint[d.rt] = 0; }
        /* SOUNDNESS FIX 2026-08-04. This used to do `bound_hint[d.rs] = d.imm`
         * unconditionally, which asserts `rs < N` from the mere EXISTENCE of a
         * comparison -- and that bound then propagated to EVERY successor block,
         * including the one reached when the comparison is FALSE.
         *
         * Proven counterexample (tools/phase4_e16_bound_hint_counterexample.c):
         * at 0x8003BF48 the reported bound 32 comes from `slti $v0,$s4,32` at
         * 0x8003A4F4 -- the LEVEL.RAW loader's class split, ~7 KB earlier, whose
         * branch went the other way on this path. The true gate there is
         * `sltiu ($s4-48), 40`, i.e. index in [48,87], so index 48 IS reachable;
         * the tool excluded it as out of bound. Runtime confirms the access fires
         * (36 writes, analysis/phase4_e16_table_read_watch.json).
         *
         * Now the bound is attached to the comparison's RESULT register and is
         * applied only along the edge on which that result is TRUE (see the
         * successor propagation at the end of run_function). */
        if (d.rt && d.rs && d.imm > 0) { cmp_src[d.rt] = (int8_t)d.rs; cmp_val[d.rt] = d.imm; }
        return;
    }
    if (d.op == 0x0C || d.op == 0x0E) {           /* andi/xori -- not an address */
        if (d.rt) { st->r[d.rt] = VTOP; shift_hint[d.rt] = -1; cmp_src[d.rt] = -1; bound_hint[d.rt] = -1; table_hint[d.rt] = 0; }
        /* TIER 3 BOUND FROM A MASK (2026-08-04). `andi rt,rs,M` clamps the result to
         * [0, M] whatever rs held -- an UNCONDITIONAL index bound needing no branch and
         * no comparison, which is how table indices are clamped throughout this image.
         * Ported from tools/affine_bound_recovery.c, where adding this single idiom took
         * the recovered-bound yield from 236 to 702 sites. Sound without qualification:
         * the mask makes the bound a property of the instruction, not of a path. */
        if (d.op == 0x0C && d.rt) bound_hint[d.rt] = (int32_t)((uint16_t)d.imm) + 1;
        return;
    }
    if (d.op == 2 || d.op == 3) return;            /* j / jal -- handled by the block loop */

    if (d.op == 0) {
        if (d.funct == 0x00) {                     /* sll (0-word = true nop) */
            if (w == 0) return;
            if (d.rd) {
                int32_t inherited_bound = bound_hint[d.rt];   /* propagate BEFORE overwrite */
                st->r[d.rd] = VTOP; shift_hint[d.rd] = (int8_t)d.sa;
                bound_hint[d.rd] = inherited_bound;
                table_hint[d.rd] = 0;
            }
            return;
        }
        if (d.funct == 0x21 || d.funct == 0x20) {  /* addu / add (also move rd,rs) */
            Val a = st->r[d.rs], b = st->r[d.rt];
            Val out;
            if (is_const_zero(b)) out = a;
            else if (is_const_zero(a)) out = b;
            else {
                uint32_t ka, kb;
                bool a1 = is_const_single(a, &ka), b1 = is_const_single(b, &kb);
                bool a_top_shift = (a.kind == K_TOP && shift_hint[d.rs] >= 0);
                bool b_top_shift = (b.kind == K_TOP && shift_hint[d.rt] >= 0);
                if (a1 && b_top_shift) {
                    out = VBOT; out.kind = K_REGION; out.rbase = ka;
                    out.rstride = 1u << shift_hint[d.rt]; out.roff = 0;
                    out.idx_bound = bound_hint[d.rt]; out.verified_anchor = 1;
                } else if (b1 && a_top_shift) {
                    out = VBOT; out.kind = K_REGION; out.rbase = kb;
                    out.rstride = 1u << shift_hint[d.rs]; out.roff = 0;
                    out.idx_bound = bound_hint[d.rs]; out.verified_anchor = 1;
                } else if (a.kind == K_REGION && b1) {
                    out = a; out.roff += (int32_t)kb;
                } else if (b.kind == K_REGION && a1) {
                    out = b; out.roff += (int32_t)ka;
                } else if (a.kind == K_CONST && b.kind == K_CONST) {
                    out = VBOT; out.kind = K_CONST; int n = 0; uint32_t seen[MAXV*MAXV];
                    for (int i = 0; i < a.nconsts && n <= MAXV; i++)
                        for (int j = 0; j < b.nconsts && n <= MAXV; j++) {
                            uint32_t s = a.consts[i] + b.consts[j];
                            bool dup = false;
                            for (int k = 0; k < n; k++) if (seen[k] == s) { dup = true; break; }
                            if (!dup) seen[n++] = s;
                        }
                    if (n > MAXV) out = VTOP; else { out.nconsts = n; for (int i=0;i<n;i++) out.consts[i]=seen[i]; }
                } else out = VTOP;
            }
            out.pb_taint |= val_is_pb(&a) | val_is_pb(&b);
            if (d.rd) { st->r[d.rd] = out; shift_hint[d.rd] = -1; cmp_src[d.rd] = -1; bound_hint[d.rd] = -1; table_hint[d.rd] = 0; }
            return;
        }
        if (d.funct == 0x23 || d.funct == 0x22) {  /* subu / sub -- matches Python: TOP unless both CONST */
            Val a = st->r[d.rs], b = st->r[d.rt];
            Val out = VTOP;
            if (a.kind == K_CONST && b.kind == K_CONST) {
                out = VBOT; out.kind = K_CONST; int n = 0; uint32_t seen[MAXV*MAXV];
                for (int i = 0; i < a.nconsts && n <= MAXV; i++)
                    for (int j = 0; j < b.nconsts && n <= MAXV; j++) {
                        uint32_t s = a.consts[i] - b.consts[j];
                        bool dup = false;
                        for (int k = 0; k < n; k++) if (seen[k] == s) { dup = true; break; }
                        if (!dup) seen[n++] = s;
                    }
                if (n > MAXV) out = VTOP; else { out.nconsts = n; for (int i=0;i<n;i++) out.consts[i]=seen[i]; }
            }
            out.pb_taint |= val_is_pb(&a) | val_is_pb(&b);
            if (d.rd) { st->r[d.rd] = out; shift_hint[d.rd] = -1; cmp_src[d.rd] = -1; bound_hint[d.rd] = -1; table_hint[d.rd] = 0; }
            return;
        }
        if (d.funct == 0x25) {                     /* or */
            Val a = st->r[d.rs], b = st->r[d.rt];
            Val out;
            if (is_const_zero(b)) out = a;
            else if (is_const_zero(a)) out = b;
            else out = VTOP;
            out.pb_taint |= val_is_pb(&a) | val_is_pb(&b);
            if (d.rd) { st->r[d.rd] = out; shift_hint[d.rd] = -1; cmp_src[d.rd] = -1; bound_hint[d.rd] = -1; table_hint[d.rd] = 0; }
            return;
        }
        if (d.funct == 0x09 || d.funct == 0x08) return;  /* jalr / jr -- block loop */
        if (d.rd) { st->r[d.rd] = VTOP; shift_hint[d.rd] = -1; cmp_src[d.rd] = -1; bound_hint[d.rd] = -1; table_hint[d.rd] = 0; }
        return;
    }
}

/* --------------------------------------------------------- block leaders ---- */

static int u32_cmp(const void *a, const void *b) {
    uint32_t x = *(const uint32_t*)a, y = *(const uint32_t*)b;
    return x < y ? -1 : (x > y ? 1 : 0);
}

static void block_starts(uint32_t lo, uint32_t hi, U32List *leaders) {
    u32_push_unique(leaders, lo);
    for (uint32_t pc = lo; pc < hi; pc += 4) {
        uint32_t w = rd_word(pc);
        Insn d = decode(w);
        int has_tgt = 0; uint32_t tgt = 0;
        if ((d.op >= 4 && d.op <= 7) || (d.op == 1 && (d.rt==0||d.rt==1||d.rt==16||d.rt==17))) {
            tgt = pc + 4 + ((uint32_t)(d.imm) << 2); has_tgt = 1;
        }
        if (has_tgt && tgt >= lo && tgt < hi) u32_push_unique(leaders, tgt);
        int delayed = has_tgt || d.op == 2 || d.op == 3 || (d.op == 0 && (d.funct == 8 || d.funct == 9));
        if (delayed && pc + 8 < hi) u32_push_unique(leaders, pc + 8);
    }
}

/* ------------------------------------------------------------ per-function ---- */

typedef struct { RegState entry; } EntrySeed;
static EntrySeed g_entry_seed[MAX_FUNCS];
static bool g_known_callable[MAX_FUNCS];

/* pending[fa] accumulates argument values seen at call sites THIS round */
static RegState g_pending[MAX_FUNCS];
static bool g_seeded_this_round[MAX_FUNCS];

static int find_func_by_addr(uint32_t addr) {
    int i = func_index_at_or_before(addr);
    return (i >= 0 && g_funcs[i].addr == addr) ? i : -1;
}

/* Simplified worklist state for a single function's blocks, keyed by leader index.
 *
 * `shift` is the CROSS-BLOCK extension of the sll/addu peephole: SHIFT_BOTTOM (-2)
 * means "not yet merged from any predecessor", SHIFT_TOP (-1) means "known to be
 * invalidated, or predecessors disagree", 0..31 means "this register's most recent
 * write was `sll r,_,sa` and nothing has touched it since, on EVERY path reaching
 * this block". A flat 3-state lattice, merged the same way register values are:
 * BOTTOM adopts whatever arrives first; anything else that disagrees collapses to
 * TOP. This recovers the case the pure block-local peephole missed -- an index
 * computed in one block, used in a LATER block -- without weakening soundness: a
 * region is only ever CREATED where shift is a concrete 0..31, exactly as before. */
typedef struct { uint32_t addr; RegState st; int8_t shift[32]; int32_t bound[32]; bool seen; } BlockState;

#define SHIFT_BOTTOM (-2)
#define SHIFT_TOP    (-1)
#define BOUND_BOTTOM (-2)
#define BOUND_TOP    (-1)

static bool merge_shift(int8_t *dst, const int8_t *src) {
    bool changed = false;
    for (int r = 0; r < 32; r++) {
        int8_t m;
        if (dst[r] == SHIFT_BOTTOM) m = src[r];
        else if (dst[r] == src[r]) m = dst[r];
        else m = SHIFT_TOP;
        if (m != dst[r]) { dst[r] = m; changed = true; }
    }
    return changed;
}

/* Same flat 3-state lattice as merge_shift, but for TIER 3's index bound. Unlike
 * shift (where disagreement is meaningless and must collapse to TOP), two DIFFERENT
 * known bounds on the SAME register could in principle both be sound to keep as a
 * MAY-bound via max() -- but doing that here would mean bounds from entirely
 * different loops/registers-reused-for-different-purposes silently combining across
 * a merge point, which is a correctness risk for a signal that is already only
 * heuristically tied to its comparison. Collapsing to TOP on disagreement is the
 * conservative, safe choice: a bound that doesn't survive to a use site just means
 * that site stays in the residual, never a false exclusion. */
static bool merge_bound(int32_t *dst, const int32_t *src) {
    bool changed = false;
    for (int r = 0; r < 32; r++) {
        int32_t m;
        if (dst[r] == BOUND_BOTTOM) m = src[r];
        else if (dst[r] == src[r]) m = dst[r];
        else m = BOUND_TOP;
        if (m != dst[r]) { dst[r] = m; changed = true; }
    }
    return changed;
}

static void run_function(int fi, uint32_t lo, uint32_t hi) {
    U32List leaders = {0};
    block_starts(lo, hi, &leaders);
    qsort(leaders.items, leaders.n, sizeof(uint32_t), u32_cmp);

    BlockState *blocks = calloc(leaders.n, sizeof(BlockState));
    for (int i = 0; i < leaders.n; i++) {
        blocks[i].addr = leaders.items[i];
        memset(blocks[i].shift, SHIFT_BOTTOM, sizeof blocks[i].shift);
        /* NOT memset -- BOUND_BOTTOM is a 32-bit value (-2), and memset only ever
         * writes a repeating BYTE pattern (0xFEFEFEFE, not -2) for anything wider
         * than a byte. shift[] above is genuinely a byte array, so memset is correct
         * there; bound[] is int32_t and needs an explicit per-element store. */
        for (int r = 0; r < 32; r++) blocks[i].bound[r] = BOUND_BOTTOM;
    }
    blocks[0].st = g_entry_seed[fi].entry;
    /* function entry: no shift/bound knowledge carried in from anywhere (BOTTOM is
     * the correct start -- the first sll/slti seen in block 0 will set it) */

    /* simple index-based worklist (small function bodies; linear scan is fine) */
    bool *queued = calloc(leaders.n, sizeof(bool));
    int *stack = malloc(leaders.n * sizeof(int));
    int sp = 0; stack[sp++] = 0; queued[0] = true;
    int seen_count = 0;

    /* 20000, up from 4000: a coverage cap, not a tuning knob. If a function hits it,
     * the FINAL round's scan is truncated and accesses in unvisited blocks silently
     * vanish from every output list -- a completeness hole, so it is counted and
     * WARNED about rather than absorbed. (The va=0 anchor canonicalization in
     * merge_val removed the churn that made the old 4000 reachable at all.) */
    while (sp > 0 && seen_count < 20000) {
        int bi = stack[--sp]; queued[bi] = false; seen_count++;
        uint32_t blo = blocks[bi].addr;
        uint32_t bhi = (bi + 1 < leaders.n) ? blocks[bi + 1].addr : hi;
        RegState st = blocks[bi].st;
        int8_t shift_hint[32];
        int32_t bound_hint[32];
        uint32_t table_hint[32]; int32_t table_cnt[32];
        /* Pending comparison records: cmp_src[r] = the register that `slti/sltiu`
         * tested to produce r, cmp_val[r] = the immediate. Block-local: a bound is
         * only ever applied along the successor edge on which the comparison is
         * true (see the terminator analysis below). */
        int8_t cmp_src[32]; int32_t cmp_val[32];
        for (int r = 0; r < 32; r++) {
            shift_hint[r] = (blocks[bi].shift[r] >= 0) ? blocks[bi].shift[r] : -1;
            bound_hint[r] = (blocks[bi].bound[r] >= 0) ? blocks[bi].bound[r] : -1;
            table_hint[r] = 0; table_cnt[r] = -1;   /* block-local only (disclosed) */
            cmp_src[r] = -1; cmp_val[r] = -1;
        }

        /* Captured AT the conditional branch, before its delay slot runs -- the
         * branch reads its condition register at that instant. */
        int8_t edge_reg_at_branch = -1; int32_t edge_val_at_branch = -1;
        int edge_ft_at_branch = 0; uint32_t edge_tgt_at_branch = 0, branch_pc_seen = 0;

        uint32_t pc = blo;
        while (pc < bhi) {
            uint32_t w = rd_word(pc);
            Insn d = decode(w);
            if ((d.op == 4 || d.op == 5) && d.rt == 0 && d.rs
                && cmp_src[d.rs] >= 0 && cmp_val[d.rs] > 0) {
                edge_reg_at_branch = cmp_src[d.rs];
                edge_val_at_branch = cmp_val[d.rs];
                edge_tgt_at_branch = pc + 4 + ((uint32_t)(d.imm) << 2);
                edge_ft_at_branch = (d.op == 4);   /* beq ..,zero -> compare was FALSE */
                branch_pc_seen = pc;
            }
            bool is_jal = (d.op == 3);
            bool is_jalr = (d.op == 0 && d.funct == 0x09);
            transfer(pc, &st, shift_hint, bound_hint, table_hint, table_cnt, cmp_src, cmp_val);
            if ((is_jal || is_jalr) && pc + 4 < bhi) {
                transfer(pc + 4, &st, shift_hint, bound_hint, table_hint, table_cnt, cmp_src, cmp_val);   /* delay slot before snapshotting args */
                if (is_jal) {
                    for (int a2 = 4; a2 <= 7; a2++)
                        if (val_is_pb(&st.r[a2])) { u32_push_unique(&g_tainted_arg_calls, pc); break; }
                    uint32_t dst = (pc & 0xF0000000u) | ((w & 0x3FFFFFFu) << 2);
                    int di = find_func_by_addr(dst);
                    if (di >= 0) {
                        for (int a = 4; a <= 7; a++)
                            g_pending[di].r[a] = merge_val(g_pending[di].r[a], st.r[a]);
                        g_seeded_this_round[di] = true;
                    }
                } else {
                    /* jalr: unconditionally unresolved (see file header). Track the
                     * SITE, not a per-visit tally -- same revisit-inflation problem as
                     * accesses, and the Python twin had exactly this bug uncorrected
                     * until this pass (238 -> 149 once deduped). */
                    u32_push_unique(&g_indirect_pcs, pc);
                }
                for (int r = 2; r <= 15; r++) { st.r[r] = VTOP; shift_hint[r] = -1; bound_hint[r] = -1; table_hint[r] = 0; }
                st.r[24] = VTOP; st.r[25] = VTOP; st.r[31] = VTOP;
                shift_hint[24]=shift_hint[25]=shift_hint[31]=-1;
                bound_hint[24]=bound_hint[25]=bound_hint[31]=-1;
                table_hint[24]=table_hint[25]=table_hint[31]=0;
                pc += 8; continue;
            }
            /* jr through a recognized switch table = tail dispatch. Capture the hint
             * BEFORE the delay slot runs (the slot could clobber the register). */
            if (d.op == 0 && d.funct == 0x08 && d.rs != 31) {
                uint32_t jrT = table_hint[d.rs]; int32_t jrN = table_cnt[d.rs];
                if (pc + 4 < bhi)
                    transfer(pc + 4, &st, shift_hint, bound_hint, table_hint, table_cnt, cmp_src, cmp_val);
                if (jrT) {
                    /* Walk min(proven bound, 64) entries. Do NOT stop at the first
                     * word that is not a recognized function start -- skipping keeps
                     * the enumeration complete for every recognized handler (an early
                     * stop could leave a later slot's handler seeded from only SOME
                     * of its dispatch sites, silently narrowing its entry state).
                     * Skipped words are counted in the audit record. */
                    int cap = (jrN > 0 && jrN <= 64) ? jrN : 64;
                    uint32_t tgts[64]; int nt = 0, skipped = 0;
                    for (int i = 0; i < cap; i++) {
                        uint32_t a2 = jrT + 4u * (uint32_t)i;
                        if (a2 < g_base || a2 + 4 > g_end) break;
                        uint32_t word = rd_word(a2);
                        if (is_function_start(word)) {
                            if (nt < 64) tgts[nt++] = word;
                            int di = find_func_by_addr(word);
                            if (di >= 0) {
                                for (int r2 = 1; r2 < 32; r2++)
                                    g_tail_pending[di].r[r2] =
                                        merge_val(g_tail_pending[di].r[r2], st.r[r2]);
                                g_tail_seeded_this_round[di] = true;
                            }
                        } else if (jrN > 0) {
                            skipped++;   /* inside the proven bound but unrecognized */
                        } else {
                            break;       /* no proven bound: stop at first non-entry */
                        }
                    }
                    record_dispatch(pc, jrT, nt, skipped, tgts);
                }
                pc += 8; continue;
            }
            pc += 4;
        }

        /* TIER 3 EDGE DISCRIMINATION (soundness fix 2026-08-04).
         * A bounds check only constrains the path on which it SUCCEEDED. Find this
         * block's terminating conditional branch; if its condition register holds a
         * `slti/sltiu rs,N` result, then `rs < N` holds on exactly one outgoing edge:
         *   beq cond,zero,T  -> cond==0 means the compare was FALSE, so the bound
         *                       holds on the FALLTHROUGH, not on T.
         *   bne cond,zero,T  -> the reverse.
         * Propagating it to both edges (what this tool used to do) asserts the bound
         * on the path where the check FAILED -- the proven counterexample at
         * 0x8003BF48. Anything else (unconditional jump, no comparison record) gets
         * no bound at all. */
        int8_t edge_reg = edge_reg_at_branch; int32_t edge_val = edge_val_at_branch;
        int edge_true_is_fallthrough = edge_ft_at_branch;
        uint32_t edge_target = edge_tgt_at_branch;
        /* The bound names a REGISTER, but a register's value can change between the
         * comparison and the region that uses it. MIPS runs the delay slot after the
         * branch condition is read, so a delay slot that rewrites the compared
         * register leaves the bound describing a value that no longer exists there.
         * That is exactly the shape at 0x8003BF38: `sltiu $v0,$v0,40` bounds
         * `$v0 = $s4-48`, then the delay slot `sll $v0,$s4,2` replaces $v0 with the
         * scaled RAW index. Carrying the bound across would re-assert `< 40` about a
         * different quantity -- so drop it instead. */
        if (edge_reg >= 0 && branch_pc_seen && branch_pc_seen + 4 < bhi) {
            Insn ds = decode(rd_word(branch_pc_seen + 4));
            int dst = -1;
            if (ds.op == 0) dst = (int)ds.rd;                     /* R-type -> rd */
            else if (ds.op == 0x0F || ds.op == 0x09 || ds.op == 0x0D ||
                     ds.op == 0x08 || ds.op == 0x0A || ds.op == 0x0B ||
                     ds.op == 0x0C || ds.op == 0x0E ||
                     (ds.op >= 0x20 && ds.op <= 0x26)) dst = (int)ds.rt;
            if (dst == (int)edge_reg) { edge_reg = -1; edge_val = -1; }
        }

        /* successors -- deliberately matches census_address.py's over-approximation:
         * always include straight-line fallthrough to the next leader if it's a real
         * leader, PLUS every branch/jump target found anywhere in [blo,bhi). */
        uint32_t nxt = bhi;
        for (int i = 0; i < leaders.n; i++) {
            uint32_t sdst = 0; bool is_succ = false;
            if (blocks[i].addr == nxt) { sdst = nxt; is_succ = true; }
            if (is_succ) {
                int32_t eb[32];
                for (int r = 0; r < 32; r++) eb[r] = bound_hint[r];
                if (edge_reg >= 0 && edge_true_is_fallthrough) eb[edge_reg] = edge_val;
                bool ch1 = merge_state(&blocks[i].st, &st);
                bool ch2 = merge_shift(blocks[i].shift, shift_hint);
                bool ch3 = merge_bound(blocks[i].bound, eb);
                if ((ch1 || ch2 || ch3) && !queued[i]) { queued[i]=true; stack[sp++]=i; }
            }
        }
        for (uint32_t pc2 = blo; pc2 < bhi; pc2 += 4) {
            uint32_t w2 = rd_word(pc2);
            Insn d2 = decode(w2);
            uint32_t t = 0; bool has = false;
            if ((d2.op>=4&&d2.op<=7) || (d2.op==1 && (d2.rt==0||d2.rt==1||d2.rt==16||d2.rt==17))) {
                t = pc2 + 4 + ((uint32_t)(d2.imm) << 2); has = true;
            } else if (d2.op == 2) {
                t = (pc2 & 0xF0000000u) | ((w2 & 0x3FFFFFFu) << 2); has = true;
            }
            if (has) {
                for (int i = 0; i < leaders.n; i++) if (blocks[i].addr == t) {
                    int32_t eb[32];
                    for (int r = 0; r < 32; r++) eb[r] = bound_hint[r];
                    if (edge_reg >= 0 && !edge_true_is_fallthrough && t == edge_target)
                        eb[edge_reg] = edge_val;
                    bool ch1 = merge_state(&blocks[i].st, &st);
                bool ch2 = merge_shift(blocks[i].shift, shift_hint);
                bool ch3 = merge_bound(blocks[i].bound, eb);
                if ((ch1 || ch2 || ch3) && !queued[i]) { queued[i]=true; stack[sp++]=i; }
                }
            }
        }
    }
    if (sp > 0) g_visit_cap_hits++;   /* worklist non-empty at cap = truncated scan */
    free(queued); free(stack); free(blocks); free(leaders.items);
}

/* ------------------------------------------------------------------- main --- */

static void read_functions_txt(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        unsigned addr; unsigned size; char name[96];
        if (sscanf(line, "0x%x %u %95s", &addr, &size, name) == 3) {
            if (g_nfuncs >= MAX_FUNCS) { fprintf(stderr, "too many functions\n"); exit(2); }
            g_funcs[g_nfuncs].addr = addr; g_funcs[g_nfuncs].size = size;
            snprintf(g_funcs[g_nfuncs].name, 96, "%s", name);
            g_nfuncs++;
        }
    }
    fclose(f);
}

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr, "usage: %s IMAGE FUNCTIONS.TXT TARGET_ADDR_HEX WIDTH "
                        "[--json OUT] [--block LO_HEX HI_HEX] [--raw LOAD_BASE]\n",
                argv[0]);
        return 2;
    }
    const char *exe_path = argv[1], *funcs_path = argv[2];
    uint32_t target = (uint32_t)strtoul(argv[3], NULL, 16);
    int width = atoi(argv[4]);
    const char *json_out = NULL;
    /* Owning block: the address range a value must fall in to count as a pointer to
     * the target's containing object. Defaults to the 168-byte player block, which is
     * what every existing caller assumes -- pass --block to analyse a different
     * subsystem's state without disturbing them. */
    uint32_t block_lo = 0x800A6500u, block_hi = 0x800A65A8u;
    uint32_t raw_base = 0;
    for (int i = 5; i < argc; i++) {
        if (!strcmp(argv[i], "--json") && i + 1 < argc) json_out = argv[i + 1];
        else if (!strcmp(argv[i], "--raw") && i + 1 < argc)
            raw_base = (uint32_t)strtoul(argv[i + 1], NULL, 0);
        else if (!strcmp(argv[i], "--block") && i + 2 < argc) {
            block_lo = (uint32_t)strtoul(argv[i + 1], NULL, 16);
            block_hi = (uint32_t)strtoul(argv[i + 2], NULL, 16);
        }
    }

    FILE *f = fopen(exe_path, "rb");
    if (!f) { perror(exe_path); return 2; }
    fseek(f, 0, SEEK_END); long fsize = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *data = malloc(fsize);
    if (fread(data, 1, fsize, f) != (size_t)fsize) { perror("read"); return 2; }
    fclose(f);
    /* Overlays are RAW images: no PS-X EXE header, no 0x800 text offset, and a
     * load address the file cannot tell you. `--raw BASE` supplies it.
     *
     * An overlay run sees ONLY that overlay. Calls out to the resident EXE land
     * outside [g_base,g_end) and stay unresolved, so no overlay function gets
     * argument seeding from a resident caller -- it is marked not-known-callable
     * and its arguments start at TOP. That is the conservative direction: a TOP
     * register yields no region, so it produces an UNRESOLVED site, never an
     * exclusion. Overlay results are therefore weaker than resident ones, never
     * less sound. */
    if (raw_base) {
        g_base = raw_base;
        g_text = data;
        g_end = g_base + (uint32_t)fsize;
    } else {
        if (memcmp(data, "PS-X EXE", 8) != 0) { fprintf(stderr, "%s: not a PS-X EXE (use --raw BASE for an overlay)\n", exe_path); return 2; }
        g_base = data[0x18] | (data[0x19]<<8) | (data[0x1A]<<16) | ((uint32_t)data[0x1B]<<24);
        g_text = data + 0x800;
        g_end = g_base + (fsize - 0x800);
    }

    read_functions_txt(funcs_path);
    g_target_lo = target; g_target_hi = target + width;
    g_block_lo = block_lo; g_block_hi = block_hi;

    /* static direct-callers pre-pass (jal-only), matches census_address.py */
    for (int fi = 0; fi < g_nfuncs; fi++) {
        uint32_t lo = g_funcs[fi].addr, hi = func_extent(fi);
        if (hi > g_end) hi = g_end;
        for (uint32_t pc = lo; pc < hi; pc += 4) {
            uint32_t w = rd_word(pc);
            if ((w >> 26) == 3) {
                uint32_t dst = (pc & 0xF0000000u) | ((w & 0x3FFFFFFu) << 2);
                int di = find_func_by_addr(dst);
                if (di >= 0) g_known_callable[di] = true;
            }
        }
    }

    for (int fi = 0; fi < g_nfuncs; fi++) {
        RegState *e = &g_entry_seed[fi].entry;
        for (int r = 0; r < 32; r++) e->r[r] = VTOP;
        e->r[0] = vconst1(0);                 /* zero */
        e->r[29] = vconst1(STACK_BASE);        /* sp */
        e->r[28] = vconst1(GP_VALUE);          /* gp */
        for (int a = 4; a <= 7; a++) e->r[a] = g_known_callable[fi] ? VBOT : VTOP;
    }

    int changed = 1;
    for (int round = 0; round < MAX_ROUNDS && changed; round++) {
        changed = 0;
        g_hits.n = 0; g_unresolved.n = 0; g_exclusions.n = 0; g_indirect_pcs.n = 0; g_visit_cap_hits = 0; g_tainted_stores.n = 0; g_tainted_arg_calls.n = 0; g_taint_dests.n = 0;
        for (int fi = 0; fi < g_nfuncs; fi++) { memset(&g_pending[fi], 0, sizeof(RegState)); g_seeded_this_round[fi] = false; }
        for (int fi = 0; fi < g_nfuncs; fi++) { memset(&g_tail_pending[fi], 0, sizeof(RegState)); g_tail_seeded_this_round[fi] = false; }
        g_ndispatch = 0;

        for (int fi = 0; fi < g_nfuncs; fi++) {
            uint32_t lo = g_funcs[fi].addr, hi = func_extent(fi);
            if (hi > g_end || hi <= lo) continue;
            run_function(fi, lo, hi);
        }

        for (int fi = 0; fi < g_nfuncs; fi++) {
            if (!g_seeded_this_round[fi] || !g_known_callable[fi]) continue;
            for (int a = 4; a <= 7; a++) {
                Val m = merge_val(g_entry_seed[fi].entry.r[a], g_pending[fi].r[a]);
                Val *d = &g_entry_seed[fi].entry.r[a];
                bool eq = d->kind == m.kind;
                if (eq && m.kind == K_CONST) {
                    eq = d->nconsts == m.nconsts;
                    if (eq) for (int k=0;k<m.nconsts;k++) if (d->consts[k]!=m.consts[k]) { eq=false; break; }
                }
                if (!eq) { *d = m; changed = 1; }
            }
        }
        /* NO tail-dispatch ENTRY SEEDING -- attempted 2026-08-01h, measured, REVERTED.
         * Seeding a jr-table target's entry with the dispatcher's register file
         * required flipping that entry from all-TOP to all-BOTTOM first (the same
         * move jal-argument seeding makes). But a register the dispatch state does
         * not fill then STAYS bottom, and a bottom base records nothing -- five
         * whole-image sites (0x8005C13C, 0x8005C168, 0x8005C18C, 0x8005C19C,
         * 0x8005C1A4) silently VANISHED from every output list: a completeness hole,
         * strictly worse than the residual it was meant to shrink. It also measured
         * ZERO improvement in this target's scope, because the two biggest
         * jr-dispatch contributors are not reached the way this seeding assumes
         * (vm_motion_apply_chase arrives via `j` from a SECOND table at 0x8001B390,
         * not the `jr` at 0x8004C220). A correct version additionally needs
         * fall-through entry paths modelled -- these dispatch targets are contiguous
         * slices of one logical function, so control can enter a slice without going
         * through the table at all. The ENUMERATION below is kept: it is sound
         * (read-only) and is the finite dispatch-space evidence the closure argument
         * wants. */
    }

    fprintf(stderr, "region_provenance: %d functions, target 0x%08X width %d\n", g_nfuncs, target, width);
    if (g_visit_cap_hits > 0)
        fprintf(stderr, "WARNING: %d function(s) hit the visit cap -- final-round scan "
                        "TRUNCATED, output lists are incomplete for them\n", g_visit_cap_hits);
    fprintf(stderr, "PB-TAINT(partial-width sb/sh, cannot install a pointer alone): %d site(s)\n",
            g_tainted_partial_stores.n);
    fprintf(stderr, "PB-TAINT(UNDECIDED unbounded-region values seen): %ld -- non-zero means the "
            "escape argument is NOT established for this target\n", g_region_undecided);
    fprintf(stderr, "PB-TAINT: %d FULL-WIDTH store(s) may write a block pointer to memory; "
                    "%d jal site(s) pass one as an argument\n",
            g_tainted_stores.n, g_tainted_arg_calls.n);
    for (int i = 0; i < g_tainted_stores.n && i < 20; i++)
        fprintf(stderr, "   tainted store @ 0x%08X (%s)\n",
                g_tainted_stores.items[i], func_owner_name(g_tainted_stores.items[i]));
    fprintf(stderr, "   ESCAPE DESTINATIONS (%d):", g_taint_dests.n);
    for (int i = 0; i < g_taint_dests.n && i < 24; i++)
        fprintf(stderr, " %s0x%08X", g_taint_dests.items[i]==0xFFFFFFFFu?"UNKNOWN:":"",
                g_taint_dests.items[i]);
    fprintf(stderr, "\n");
    fprintf(stderr, "RAW (revisit-inflated, before dedup): hits=%d unresolved=%d exclusions=%d indirect_unresolved=%d\n",
            g_hits.n, g_unresolved.n, g_exclusions.n, g_indirect_pcs.n);

    /* dedupe hits by pc (matches Python's `seen.setdefault(h["pc"], h)`) */
    for (int i = 0; i < g_hits.n; i++) {
        for (int j = i + 1; j < g_hits.n; j++) {
            if (!strcmp(g_hits.items[i].pc, g_hits.items[j].pc)) {
                g_hits.items[j] = g_hits.items[--g_hits.n]; j--;
            }
        }
    }
    dedup_accesses(&g_unresolved);
    dedup_exclusions(&g_exclusions);

    /* Cross-list reconciliation: a block revisited mid-convergence can classify the
     * SAME pc differently on different visits (e.g. unresolved on an early, less-
     * refined incoming state; region-excluded once the state settles). Keep the
     * exclusion -- it reflects a more-refined state -- and drop that pc from the
     * unresolved list so a site is never counted in both buckets. */
    if (g_exclusions.n) {
        int w = 0;
        for (int i = 0; i < g_unresolved.n; i++) {
            bool in_excl = false;
            /* g_exclusions is sorted by pc_num after dedup_exclusions() */
            int lo = 0, hi = g_exclusions.n - 1;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                if (g_exclusions.items[mid].pc_num == g_unresolved.items[i].pc_num) { in_excl = true; break; }
                if (g_exclusions.items[mid].pc_num < g_unresolved.items[i].pc_num) lo = mid + 1; else hi = mid - 1;
            }
            if (!in_excl) g_unresolved.items[w++] = g_unresolved.items[i];
        }
        g_unresolved.n = w;
    }

    fprintf(stderr, "DISTINCT SITES (after dedup): hits=%d unresolved=%d exclusions=%d indirect_unresolved=%d\n",
            g_hits.n, g_unresolved.n, g_exclusions.n, g_indirect_pcs.n);

    int align_n = 0, neg_n = 0, bound_n = 0;
    for (int i = 0; i < g_exclusions.n; i++) {
        const char *k = g_exclusions.items[i].kind;
        if (!strcmp(k, "EXCLUDED_ALIGNMENT")) align_n++;
        else if (!strcmp(k, "EXCLUDED_NEGATIVE_INDEX")) neg_n++;
        else bound_n++;
    }
    fprintf(stderr, "  of which EXCLUDED_ALIGNMENT=%d EXCLUDED_NEGATIVE_INDEX=%d EXCLUDED_OUT_OF_BOUND=%d\n",
            align_n, neg_n, bound_n);

    if (json_out) {
        FILE *jf = fopen(json_out, "w");
        if (!jf) { perror(json_out); return 2; }
        fprintf(jf, "{\n");
        fprintf(jf, " \"_comment\": \"tools/region_provenance.c output. TIER 1 EXCLUDED_ALIGNMENT is unconditionally sound given the disassembled base shape; TIER 2 EXCLUDED_NEGATIVE_INDEX and TIER 3 EXCLUDED_OUT_OF_BOUND both rely on the standard non-negative, loop-bound-checked array-index convention -- disclosed, not hidden. Regenerate: cc -O2 -o tools/region_provenance tools/region_provenance.c && tools/region_provenance SCUS_942.88 analysis/functions_resident.txt <target> <width> --json <out>\",\n");
        fprintf(jf, " \"target\": \"0x%08X\", \"width\": %d,\n", target, width);
        fprintf(jf, " \"hits\": %d, \"unresolved_after_region\": %d, \"indirect_unresolved\": %d,\n",
                g_hits.n, g_unresolved.n, g_indirect_pcs.n);
        fprintf(jf, " \"exclusions_total\": %d, \"excluded_alignment\": %d, \"excluded_negative_index\": %d, \"excluded_out_of_bound\": %d,\n",
                g_exclusions.n, align_n, neg_n, bound_n);
        fprintf(jf, " \"hit_pcs\": [");
        for (int i = 0; i < g_hits.n; i++) fprintf(jf, "%s\"%s\"", i?", ":"", g_hits.items[i].pc);
        fprintf(jf, "],\n");
        fprintf(jf, " \"pb_taint\": {\"tainted_stores\": [");
        for (int i = 0; i < g_tainted_stores.n; i++)
            fprintf(jf, "%s\"0x%08X\"", i?", ":"", g_tainted_stores.items[i]);
        fprintf(jf, "], \"escape_destinations\": [");
        for (int i = 0; i < g_taint_dests.n; i++)
            fprintf(jf, "%s\"0x%08X\"", i?", ":"", g_taint_dests.items[i]);
        fprintf(jf, "], \"unknown_destination_escapes\": %d, \"arg_passing_call_sites\": %d},\n",
                ({ int u=0; for (int i=0;i<g_taint_dests.n;i++) if (g_taint_dests.items[i]==0xFFFFFFFFu) u++; u; }),
                g_tainted_arg_calls.n);
        fprintf(jf, " \"jr_dispatch_tables\": [\n");
        for (int i = 0; i < g_ndispatch; i++) {
            DispatchRec *r = &g_dispatch[i];
            fprintf(jf, "  {\"jr_pc\": \"0x%08X\", \"table\": \"0x%08X\", \"skipped_words\": %d, \"targets\": [",
                    r->pc, r->table, r->skipped);
            for (int t = 0; t < r->ntargets; t++)
                fprintf(jf, "%s\"0x%08X\"", t ? ", " : "", r->targets[t]);
            fprintf(jf, "]}%s\n", i + 1 < g_ndispatch ? "," : "");
        }
        fprintf(jf, " ],\n");
        fprintf(jf, " \"exclusions\": [\n");
        for (int i = 0; i < g_exclusions.n; i++) {
            Exclusion *e = &g_exclusions.items[i];
            fprintf(jf, "  {\"pc\": \"%s\", \"function\": \"%s\", \"kind\": \"%s\", "
                        "\"region_base\": \"0x%08X\", \"stride\": %u, \"accum_offset\": %lld, \"insn_offset\": %d, "
                        "\"computed_idx\": %lld, \"idx_bound\": %d, \"verified_anchor\": %s}%s\n",
                    e->pc, e->function, e->kind, e->rbase, e->rstride, (long long)e->roff, e->insn_off,
                    (long long)e->computed_idx, e->idx_bound,
                    e->verified_anchor ? "true" : "false",
                    i + 1 < g_exclusions.n ? "," : "");
        }
        fprintf(jf, " ],\n");
        fprintf(jf, " \"unresolved_all\": [\n");
        for (int i = 0; i < g_unresolved.n; i++) {
            Access *a = &g_unresolved.items[i];
            fprintf(jf, "  {\"pc\": \"%s\", \"insn\": \"%s\", \"kind\": \"%s\", \"function\": \"%s\", \"width\": %d}%s\n",
                    a->pc, a->insn, a->kind, a->function, a->width, i + 1 < g_unresolved.n ? "," : "");
        }
        fprintf(jf, " ]\n}\n");
        fclose(jf);
        fprintf(stderr, "wrote %s\n", json_out);
    }
    return 0;
}
