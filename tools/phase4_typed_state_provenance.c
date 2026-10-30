/* phase4_typed_state_provenance.c -- what actually defines a base register?
 *
 * The typed-state compiler needs to bound memory accesses whose base register it
 * cannot resolve to a constant. Bounding is only sound if the register really
 * does hold a pointer into a declared region, and a YAML schema saying so is a
 * declaration, not evidence. This tool supplies the evidence by reading the
 * instructions.
 *
 * For each query (image, function extent, register) it enumerates EVERY
 * definition of that register inside the extent and classifies it:
 *
 *   global_load           lw reg, disp(base) with base a materialised constant,
 *                         so the register is loaded from a fixed address. The
 *                         address is reported; the caller decides what lives
 *                         there. This is the only class that can support a
 *                         typed_pointer_load binding.
 *   frame_reload          lw reg, disp(sp) -- a spill slot, including the
 *                         epilogue restore of a callee-saved register.
 *   materialised_constant lui / addiu / ori chain -- the register is an address
 *                         literal, not a pointer read from anywhere.
 *   register_copy         addu reg, X, zero and friends. CHASED: the source is
 *                         resolved in its place, up to 8 hops, through PURE moves
 *                         only and only inside one basic block. Arithmetic is not
 *                         followed -- `addiu rd, rs, 8` shifts the pointer and a
 *                         region bound for rs would be off by that much.
 *   table_address         reg = INDEX + CONST. The element is unknown, the table
 *                         is not.
 *   call_result           a jal/jalr clobbers it, i.e. the register is a return
 *                         value or scratch. The CALLEE is reported so the caller
 *                         can go and ask what that function returns.
 *   opaque                anything else -- arithmetic, a load through an
 *                         unrecovered base, a coprocessor move.
 *
 * Two further fields make interprocedural questions answerable (the ABI
 * accelerator):
 *
 *   incoming              the definition is a copy of a register that holds the
 *                         CALLER's value at that point -- i.e. an argument. The
 *                         test is point-local, because a0 is clobbered by every
 *                         jal yet is unambiguously the argument in the prologue.
 *   targets_all_hold_incoming
 *                         the queried register IS the incoming argument at every
 *                         targeted site, so typing it is a question about the
 *                         callers rather than about anything in this function.
 *
 * Query forms:
 *   IMAGE:START:END:REG[:PCS]     definitions of REG reaching PCS (or all uses)
 *   defsat@IMAGE:START:END:REG:PC what REG holds at an ARBITRARY point -- a call
 *                                 site. On a call the query point moves past the
 *                                 delay slot, which executes first.
 *   returns@IMAGE:START:END       what v0 holds at every `jr ra`: the return type.
 *                                 `no_return_site` when the extent has none.
 *   writers@IMAGE:ADDR            every store into a pointer table.
 *   progression@IMAGE:START:END:REG:STOREPC
 *                                 prove the register's VALUE DOMAIN at a store:
 *                                 every definition in the extent is a shadowed
 *                                 or agreeing constant anchor, a positive
 *                                 uniform self-adjustment, or a terminal-
 *                                 epilogue sp-reload -- with NO reachability
 *                                 argument, because def_is_observable follows
 *                                 the linear successor out of a delay slot and
 *                                 a proof must not rest on a walk with a known
 *                                 miss direction. Yields anchor+stride: the
 *                                 register is >= anchor on the stride lattice,
 *                                 upper bound deliberately not claimed.
 *   indexdom@IMAGE:START:END:REG:PC
 *                                 prove an unsigned interval for REG at PC.
 *                                 Every nearest reaching definition must be an
 *                                 architectural zero-extension (lbu/lhu),
 *                                 andi, srl, a non-negative constant, a
 *                                 sltiu-true guarded edge, or a composition of
 *                                 proved intervals through overflow-checked
 *                                 sll/addu/non-negative-addiu. Any other
 *                                 definition, unresolved indirect/interior-call
 *                                 edge, call clobber, dependency cycle, or entry
 *                                 path without a definition rejects the query
 *                                 and names the breaking instruction.
 *   island@IMAGE:CLO:CHI:ILO:IHI:REG:CALLPC[,CALLPC...]
 *                                 the instruction facts a proved-jr-cluster
 *                                 argument binding rests on: (a) the cluster
 *                                 prologue is straight-line up to a pure copy of
 *                                 an argument register into REG; (b) every OTHER
 *                                 write to REG in [CLO,CHI) is an sp-restore
 *                                 inside a TERMINAL epilogue (only sp loads /
 *                                 sp adjust / nop up to `jr ra`, no branches);
 *                                 (c) each CALLPC decodes as `jal CLO` whose
 *                                 delay slot purely copies a caller register
 *                                 into that same argument register; (d) the
 *                                 REG-based memory accesses inside [ILO,IHI)
 *                                 are enumerated for the caller to cross-check
 *                                 against the ledger. REG must be callee-saved,
 *                                 else calls inside the cluster clobber it and
 *                                 no invariance argument exists.
 *
 * It also answers the question that makes "all definitions agree" sound:
 *
 *   entry_reachable_uses  uses of the register as a base that are reachable from
 *                         the function entry WITHOUT passing any definition. If
 *                         this is non-zero the register can arrive holding the
 *                         caller's value and NO local definition governs it, so
 *                         the definitions prove nothing about those sites.
 *
 * The query says which register in which function. It cannot influence the
 * answer -- only what gets asked.
 *
 * usage: phase4_typed_state_provenance <image_map> IMAGE:START:END:REG[:PCS] ...
 *        the image map is `id path va_base` lines, generated from the static
 *        index so this tool never carries a second copy of the overlay table.
 * exit 0 always on a well-formed run; the JSON is the finding.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>

#define GP_VALUE 0x80081D98u

static const char *REGNAME[32] = {
    "zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
    "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra" };

static int reg_of(const char *name)
{
    for (int i = 0; i < 32; i++) if (strcmp(REGNAME[i], name) == 0) return i;
    return -1;
}

typedef struct { uint8_t *p; size_t n; } Blob;
static Blob slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END); long z = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *b = malloc((size_t)z ? (size_t)z : 1);
    if (!b || fread(b, 1, (size_t)z, f) != (size_t)z) { fprintf(stderr, "read %s\n", path); exit(2); }
    fclose(f);
    return (Blob){ b, (size_t)z };
}
static uint32_t le32(const uint8_t *p) { uint32_t v; memcpy(&v, p, 4); return v; }

/* Which register does this instruction WRITE? -1 for none. A jal/jalr is handled
 * by the caller because it writes many. */
static int def_reg(uint32_t w)
{
    uint32_t op = w >> 26, rt = (w >> 16) & 31, rd = (w >> 11) & 31, fn = w & 0x3f;
    switch (op) {
    case 0x00:
        if (fn == 0x08) return -1;                      /* jr    */
        if (fn == 0x09) return (int)rd;                 /* jalr  */
        if (fn == 0x0c || fn == 0x0d) return -1;        /* syscall/break */
        if (fn == 0x18 || fn == 0x19 || fn == 0x1a || fn == 0x1b) return -1;  /* mult/div */
        if (fn == 0x11 || fn == 0x13) return -1;        /* mthi/mtlo */
        return rd ? (int)rd : -1;
    case 0x01: return (w >> 16 & 0x1e) == 0x10 ? 31 : -1;   /* bltzal/bgezal */
    case 0x03: return 31;                                    /* jal */
    case 0x08: case 0x09: case 0x0a: case 0x0b:
    case 0x0c: case 0x0d: case 0x0e: case 0x0f:
        return rt ? (int)rt : -1;
    case 0x10: case 0x11: case 0x12: case 0x13:              /* cop0/2 moves */
        return ((w >> 21 & 31) == 0 || (w >> 21 & 31) == 2) ? (rt ? (int)rt : -1) : -1;
    case 0x20: case 0x21: case 0x22: case 0x23:
    case 0x24: case 0x25: case 0x26:
        return rt ? (int)rt : -1;
    default: return -1;
    }
}

static int is_call(uint32_t w)
{
    uint32_t op = w >> 26;
    return op == 0x03 || (op == 0 && (w & 0x3f) == 0x09);
}

/* The architectural link register written before a call's delay slot runs.
 * JAL always writes $ra; JALR names the destination in rd (rd==zero discards
 * the link and therefore has no observable link register). */
static int call_link_reg(uint32_t w)
{
    uint32_t op = w >> 26;
    if (op == 0x03) return 31;
    if (op == 0 && (w & 0x3f) == 0x09) {
        int rd = (int)((w >> 11) & 31);
        return rd ? rd : -1;
    }
    return -1;
}

static int call_boundary_suppresses_definition(uint32_t w, int queried_reg)
{
    return is_call(w) && call_link_reg(w) != queried_reg;
}

/* Caller-saved registers a call destroys. s0-s7, gp, sp, fp survive. */
static int call_clobbers(int r)
{
    return (r >= 1 && r <= 15) || r == 24 || r == 25 || r == 31;
}
static int is_load(uint32_t w) { uint32_t op = w >> 26; return op >= 0x20 && op <= 0x26; }

/* MIPS-I exposes a one-instruction result delay not only for the ordinary GPR
 * loads above, but also for move-from-coprocessor instructions.  The latter
 * are never interval roots, yet they still matter immediately before a
 * sltiu guard: the comparison reads the old register and the coprocessor value
 * can become visible before the guarded use. */
static int has_gpr_load_delay(uint32_t w)
{
    uint32_t op = w >> 26, rs = (w >> 21) & 31;
    return is_load(w) || ((op >= 0x10 && op <= 0x13)
                          && (rs == 0 || rs == 2));     /* mfcN / cfcN */
}

/* Is this instruction a control TRANSFER that owns a delay slot? */
static int is_transfer(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 0x3f;
    if (op == 2 || op == 3 || op == 1 || (op >= 4 && op <= 7)
        || (op >= 0x14 && op <= 0x17)) return 1;
    if (op == 0 && (fn == 8 || fn == 9)) return 1;                 /* jr/jalr */
    return 0;
}

/* Successors within the extent, as word indices -- DELAY-SLOT CORRECT.
 *
 * ⚠️ The original routed a transfer's edges directly from the transfer and
 * gave the delay slot a plain linear successor. That mismodels MIPS in a way
 * that was measured three times over: a delay-slot DEFINITION was reported
 * unobservable while execution carried its value through the jump
 * (mover_updater 0x8004D3FC), and a delay-slot USE was unreachable by the
 * def-observability and entry-reachability walks entirely -- so a store in a
 * `j` delay slot (LEVEL02 0x800B3EF4) had NO observable definitions yet read
 * as "governed", a vacuous and UNSAFE answer.
 *
 * Correct model: execution reaches a transfer, then its delay slot, and only
 * then the transfer's targets. So a transfer's sole successor is its delay
 * slot, and the DELAY SLOT inherits the owning transfer's targets (branch:
 * taken target plus the not-taken continuation; j: target; jal/jalr: the
 * post-call continuation, matching the call-boundary treatment elsewhere in
 * this file; jr: none). A transfer sitting in another transfer's delay slot
 * is architecturally unpredictable; the owner's targets win, which matches
 * no compiler output and is disclosed rather than guessed around. */
static int succs_of(const uint32_t *code, size_t words, size_t i, uint32_t start, uint32_t out[2])
{
    int n = 0;
    if (i > 0 && is_transfer(code[i - 1])) {
        uint32_t w = code[i - 1], op = w >> 26;
        uint32_t pc = start + (uint32_t)((i - 1) * 4);
        if (op == 0 && (w & 0x3f) == 8) return 0;                  /* jr */
        if (op == 0 && (w & 0x3f) == 9) {                          /* jalr */
            if (i + 1 < words) out[n++] = (uint32_t)(i + 1);
            return n;
        }
        if (op == 2) {                                             /* j */
            uint32_t t = ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
            if (t >= start && (t - start) / 4 < words) out[n++] = (uint32_t)((t - start) / 4);
            return n;
        }
        if (op == 3) {                                             /* jal */
            if (i + 1 < words) out[n++] = (uint32_t)(i + 1);
            return n;
        }
        /* conditional branch: taken target + not-taken continuation */
        int32_t d = (int16_t)(w & 0xffff);
        uint32_t t = pc + 4 + (uint32_t)(d * 4);
        if (t >= start && (t - start) / 4 < words) out[n++] = (uint32_t)((t - start) / 4);
        if (i + 1 < words) out[n++] = (uint32_t)(i + 1);
        return n;
    }
    if (is_transfer(code[i])) {
        /* control is committed but the DELAY SLOT executes first */
        if (i + 1 < words) out[n++] = (uint32_t)(i + 1);
        return n;
    }
    if (i + 1 < words) out[n++] = (uint32_t)(i + 1);
    return n;
}

/* Defined further down; both are needed by the dataflow helpers above them. */
static int def_is_observable(const uint32_t *code, size_t words, uint32_t start,
                             const uint8_t *isdef, const uint8_t *isuse, size_t d);
static void reach_avoiding_defs(const uint32_t *code, size_t words, uint32_t start,
                                const uint8_t *isdef, uint8_t *seen);
static int const_at(const uint32_t *code, const uint8_t *join, size_t words,
                    uint32_t start, size_t i, int reg, int depth, uint32_t *out);
static int const_at_call_boundary(const uint32_t *code, const uint8_t *join,
                                  size_t words, uint32_t start,
                                  size_t call_at, int reg, uint32_t *out);
static int cfg_fail_closed_barrier(const uint32_t *code, size_t words,
                                   uint32_t start, size_t *barrier,
                                   const char **barrier_reason);

/* Recover the constant a base register holds at index `i`, by walking back to the
 * nearest lui within the SAME basic block. Crossing a join point abandons the
 * walk: an instruction reached from two directions may arrive with a different
 * value, and guessing there is how a false bound gets minted. */
typedef struct {
    int have;
    size_t at;
    const char *reason;
} ConstFailure;

static void const_failure_set(ConstFailure *failure, size_t at,
                              const char *reason)
{
    if (!failure || failure->have) return;
    failure->have = 1;
    failure->at = at;
    failure->reason = reason;
}

/* Evaluate a straight-line constant chain in instruction order.  The old
 * accumulator treated ORI as addition while walking backwards.  That happens
 * to work for the usual LUI/ORI pair only because LUI leaves the low half zero;
 * a second ORI with overlapping bits fabricated a larger address. */
static int const_base_inner(const uint32_t *code, const uint8_t *join, size_t i,
                            int base, int depth, uint32_t *out,
                            ConstFailure *failure)
{
    if (base == 0)  { *out = 0; return 1; }
    if (depth > 8) return 0;
    if (base == 28) {
        /* `$gp` has a pinned value at the declared extent entry, but it is
         * still a writable GPR.  Treating the entry value as immutable let an
         * immediately preceding `addu gp,a0,zero` fabricate a table base.  A
         * local definition makes this straight-line hint unavailable; the
         * path-complete const_at() proof below decides whether definitions on
         * different paths agree.  Scanning the whole prefix is deliberately
         * conservative when a definition is dead or bypassed. */
        for (size_t k = 0; k < i; k++)
            if (def_reg(code[k]) == 28) return 0;
        *out = GP_VALUE;
        return 1;
    }
    for (size_t k = i; k-- > 0; ) {
        uint32_t w = code[k];
        if (is_call(w) && call_clobbers(base)) return 0;
        int d = def_reg(w);
        if (d == base) {
            uint32_t op = w >> 26, rs = (w >> 21) & 31, imm = w & 0xffff;
            if (k > 0 && is_call(code[k - 1]) && call_clobbers(base)
                && (op == 0x0f || op == 0x09 || op == 0x0d)) {
                /* A call's delay slot executes before the callee.  A value put
                 * in a caller-saved register there is clobbered on the call
                 * edge before the continuation can observe it. */
                const_failure_set(
                    failure, k - 1,
                    "call_delay_definition_clobbered_before_continuation");
                return 0;
            }
            if (op == 0x0f) { *out = imm << 16; return 1; }              /* lui */
            if (op == 0x09 || op == 0x0d) {                              /* addiu / ori */
                uint32_t source;
                /* Follow the chain ACROSS registers: `addiu a0, s0, -0x90`
                 * makes a0 whatever s0 was, minus 0x90.  Recursing to the
                 * point before this definition preserves the actual order of
                 * mixed ADDIU and ORI operations. */
                if (!const_base_inner(code, join, k, (int)rs, depth + 1,
                                      &source, failure)) return 0;
                *out = op == 0x09
                     ? source + (uint32_t)(int32_t)(int16_t)imm
                     : source | imm;
                return 1;
            }
            return 0;                                                    /* something else */
        }
        if (join[k]) return 0;             /* a merge: the walk is no longer linear */
    }
    return 0;
}

static int const_base(const uint32_t *code, const uint8_t *join, size_t i,
                      int base, uint32_t *out)
{
    return const_base_inner(code, join, i, base, 0, out, NULL);
}

static int const_base_detail(const uint32_t *code, const uint8_t *join,
                             size_t i, int base, uint32_t *out,
                             ConstFailure *failure)
{
    if (failure) *failure = (ConstFailure){0};
    return const_base_inner(code, join, i, base, 0, out, failure);
}

/* Evaluate a constant written in a targeted call's delay slot at the instant
 * the callee receives its arguments.  That boundary is deliberately distinct
 * from the call continuation: the slot has executed, but the callee has not
 * yet had an opportunity to clobber caller-saved registers.
 *
 * Source constants require the CFG-wide reaching-definition proof; when a
 * straight-line value is also available it must agree.  Starting both at
 * CALL_AT (rather than after the slot) prevents the owning call's continuation
 * clobber from being mistaken for a pre-slot clobber.  A source equal to the
 * call's architectural link destination is rejected: JAL writes $ra and JALR
 * writes its rd before the delay slot executes, while this small evaluator does
 * not model either link value. */
static int call_delay_argument_constant(const uint32_t *code,
                                        const uint8_t *join, size_t words,
                                        uint32_t start, size_t call_at, int reg,
                                        uint32_t *out)
{
    if (call_at + 1 >= words || !is_call(code[call_at])) return 0;
    uint32_t w = code[call_at + 1];
    if (def_reg(w) != reg) return 0;

    uint32_t op = w >> 26, fn = w & 0x3f;
    int rs = (int)((w >> 21) & 31), rt = (int)((w >> 16) & 31);
    int link = call_link_reg(code[call_at]);
    uint32_t imm = w & 0xffffu, source, lexical_source;
    if (op == 0x0f) {
        *out = imm << 16;
        return 1;
    }
    if (op == 0x09 || op == 0x0d) {
        if (rs == link
            || !const_at_call_boundary(code, join, words, start, call_at,
                                       rs, &source))
            return 0;
        if (const_base(code, join, call_at, rs, &lexical_source)
            && lexical_source != source)
            return 0;
        *out = op == 0x09
             ? source + (uint32_t)(int32_t)(int16_t)imm
             : source | imm;
        return 1;
    }
    if (op == 0 && (fn == 0x20 || fn == 0x21 || fn == 0x25)) {
        int source_reg = -1;
        if (rt == 0 && rs != 0) source_reg = rs;
        if (rs == 0 && rt != 0) source_reg = rt;
        if (source_reg < 0 || source_reg == link
            || !const_at_call_boundary(code, join, words, start, call_at,
                                       source_reg, &source))
            return 0;
        if (const_base(code, join, call_at, source_reg, &lexical_source)
            && lexical_source != source)
            return 0;
        *out = source;
        return 1;
    }
    return 0;
}

/* `lui at, HI; addu at, at, IDX; lw reg, LO(at)` -- a load from a fixed TABLE at
 * an index this pass cannot recover. The element is unknown but the table is
 * not, and for bounding purposes the table is what matters: every element of a
 * table of actor pointers is an actor pointer, whichever one this is.
 *
 * Returns 1 and sets *out to the table's base address. Refuses when BOTH addends
 * resolve (then it is an ordinary constant, already handled) or when neither
 * does. */
static int const_base(const uint32_t *code, const uint8_t *join, size_t i,
                      int base, uint32_t *out);

/* Prove the constant operand of one TABLE+INDEX definition at the point before
 * the ADD/ADDU executes.  A lexical LUI is only a diagnostic hint: the proof is
 * const_at(), which checks every dynamic reaching definition and rejects an
 * entry path that carries the caller's value.  Return -1 when the instruction
 * has the tempting lexical shape but that path-complete proof fails, 0 when it
 * is not a table-address definition, and 1 only for a proved definition. */
static int table_add_definition(const uint32_t *code, const uint8_t *join,
                                size_t words, uint32_t start, size_t at,
                                uint32_t *out, const char **index_reg,
                                const char **constant_reg,
                                size_t *failure_at,
                                const char **failure_reason)
{
    uint32_t w = code[at], op = w >> 26, fn = w & 0x3f;
    int rs = (int)((w >> 21) & 31), rt = (int)((w >> 16) & 31);
    if (op != 0 || (fn != 0x21 && fn != 0x20)) return 0;

    if (failure_at) *failure_at = at;
    if (failure_reason) *failure_reason = "table_base_operand_not_path_invariant";
    if (at > 0 && is_call(code[at - 1])
        && call_clobbers(def_reg(w))) {
        if (failure_at) *failure_at = at - 1;
        if (failure_reason)
            *failure_reason =
                "call_delay_definition_clobbered_before_continuation";
        return -1;
    }
    {
        size_t barrier = words;
        const char *reason = NULL;
        if (cfg_fail_closed_barrier(code, words, start, &barrier, &reason)) {
            if (failure_at) *failure_at = barrier;
            if (failure_reason) *failure_reason = reason;
            return -1;
        }
    }

    uint32_t a = 0, b = 0, lexical_a = 0, lexical_b = 0;
    ConstFailure failure_a = {0}, failure_b = {0};
    int la = const_base_detail(code, join, at, rs, &lexical_a, &failure_a);
    int lb = const_base_detail(code, join, at, rt, &lexical_b, &failure_b);
    if (failure_a.have || failure_b.have) {
        ConstFailure *failure = failure_a.have ? &failure_a : &failure_b;
        if (failure_at) *failure_at = failure->at;
        if (failure_reason) *failure_reason = failure->reason;
        return -1;
    }
    int ka = (la && const_at(code, join, words, start, at, rs, 0, &a)
              && a == lexical_a);
    int kb = (lb && const_at(code, join, words, start, at, rt, 0, &b)
              && b == lexical_b);
    if (ka && !kb) {
        *out = a;
        *index_reg = REGNAME[rt];
        *constant_reg = REGNAME[rs];
        return 1;
    }
    if (kb && !ka) {
        *out = b;
        *index_reg = REGNAME[rs];
        *constant_reg = REGNAME[rt];
        return 1;
    }

    /* Keep a precise failure only for the old false-proof shape: exactly one
     * operand looks constant in the lexical basic-block walk, but the CFG-wide
     * reaching-definition proof refuses it.  This hint can never authorize a
     * classification. */
    /* `$gp` is a useful lexical entry-value hint, not an immutable register.
     * Preserve a precise rejection when a local write removed that hint. */
    return ((la || rs == 28) != (lb || rt == 28)) ? -1 : 0;
}

static int table_base(const uint32_t *code, const uint8_t *join, size_t words,
                      uint32_t start, size_t i, int base, uint32_t *out,
                      const char **index_reg, const char **constant_reg,
                      size_t *failure_at, const char **failure_reason)
{
    /* A target at the use itself can bypass every lexical predecessor. */
    if (i < words && join[i]) return 0;
    for (size_t k = i; k-- > 0; ) {
        uint32_t w = code[k];
        if (is_call(w) && call_clobbers(base)) return 0;
        if (def_reg(w) == base) {
            if (k > 0 && is_call(code[k - 1]) && call_clobbers(base)) {
                if (failure_at) *failure_at = k - 1;
                if (failure_reason)
                    *failure_reason =
                        "call_delay_definition_clobbered_before_continuation";
                return -1;
            }
            return table_add_definition(code, join, words, start, k, out,
                                        index_reg, constant_reg, failure_at,
                                        failure_reason);
        }
        if (join[k]) return 0;
    }
    return 0;
}

/* Reach every index from entry WITHOUT executing any definition. */
static void reach_avoiding_defs(const uint32_t *code, size_t words, uint32_t start,
                                const uint8_t *isdef, uint8_t *seen)
{
    memset(seen, 0, words);
    if (!words || isdef[0]) return;
    uint32_t *stack = malloc(words * sizeof *stack);
    if (!stack) exit(2);
    size_t sp = 0;
    seen[0] = 1; stack[sp++] = 0;
    while (sp) {
        size_t i = stack[--sp]; uint32_t out[2];
        int n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++) {
            uint32_t t = out[k];
            if (isdef[t] || seen[t]) continue;
            seen[t] = 1; stack[sp++] = t;
        }
    }
    free(stack);
}

/* ================================================================== ABI ===
 * Two capabilities the bounding pass needs but plain classification lacks.
 *
 * COPY CHASING. `s2` is very often just `a0` or a loaded pointer moved into a
 * callee-saved register at function entry. Classifying the move as
 * "register_copy" and stopping throws away everything the source knew. Chasing
 * it -- only through PURE moves, never through arithmetic, and only while the
 * walk stays inside one basic block -- recovers it.
 *
 * CALL TARGETS. A `v0` base is a return value. Naming the callee is what lets
 * the compiler go and ask what that callee returns.
 * ========================================================================= */

/* The single definition of `reg` that reaches index `i`, or a negative code:
 * -1 the walk left the basic block (a merge, so no single definition governs),
 * -2 a call clobbered the register in between. */
static long def_of_reg_before(const uint32_t *code, const uint8_t *join,
                              size_t i, int reg)
{
    for (size_t k = i; k-- > 0; ) {
        uint32_t w = code[k];
        if (is_call(w) && call_clobbers(reg)) return -2;
        /* A definition AT a join point still executes on every path through it,
         * so check the definition before giving up on the join. */
        if (def_reg(w) == reg) {
            if (k > 0 && is_call(code[k - 1]) && call_clobbers(reg))
                return -2;
            return (long)k;
        }
        if (join[k]) return -1;
    }
    return -1;
}

/* Is this instruction a PURE move, and from which register?
 * `addu rd, rs, zero`, `or rd, rs, zero`, `addiu rd, rs, 0`, `ori rd, rs, 0`.
 * Arithmetic is deliberately excluded: `addiu rd, rs, 8` shifts the pointer, and
 * a region bound recovered for rs would be off by that much. */
static int move_source(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 0x3f, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    if (op == 0 && (fn == 0x21 || fn == 0x20 || fn == 0x25)) {
        if (rt == 0 && rs != 0) return (int)rs;
        if (rs == 0 && rt != 0) return (int)rt;
        return -1;
    }
    if ((op == 0x09 || op == 0x0d) && (w & 0xffff) == 0 && rs != 0) return (int)rs;
    return -1;
}

/* The jal target, or 0 for jalr (an indirect call names no callee statically). */
static uint32_t call_target(const uint32_t *code, size_t i, uint32_t start)
{
    uint32_t w = code[i];
    if ((w >> 26) != 0x03) return 0;
    return ((start + (uint32_t)(i * 4) + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
}


/* The constant `reg` holds at index `i`, recovered ACROSS basic blocks.
 *
 * `const_base` walks backwards in a straight line and gives up at the first
 * merge point, which is sound but far too weak for an argument: a caller
 * typically materialises the pointer once in the prologue and calls thirty
 * instructions and several branches later. This asks the CFG question instead --
 * of all the definitions of `reg` that can REACH `i`, do they all produce the
 * same constant? -- and additionally refuses when a path reaches `i` with no
 * definition at all, because then the register is whatever the caller left.
 *
 * Returns 1 and sets *out only when every reaching definition agrees. */
static int const_at_internal(const uint32_t *code, const uint8_t *join,
                             size_t words, uint32_t start, size_t i, int reg,
                             int depth, size_t ignored_call, uint32_t *out)
{
    if (reg == 0)  { *out = 0; return 1; }
    if (depth > 6 || i >= words) return 0;

    uint8_t *isdef = calloc(words, 1), *isuse = calloc(words, 1), *seen = calloc(words, 1);
    if (!isdef || !isuse || !seen) exit(2);
    for (size_t k = 0; k < words; k++)
        if (def_reg(code[k]) == reg
            || (is_call(code[k]) && call_clobbers(reg) && k != ignored_call))
            isdef[k] = 1;
    isuse[i] = 1;

    int ok = 0, have = 0;
    uint32_t val = 0;
    reach_avoiding_defs(code, words, start, isdef, seen);
    if (seen[i]) {
        if (reg != 28) goto done;            /* caller value on some path */
        /* `$gp` enters with a project-pinned value.  It participates as one
         * reaching definition and must agree with every local definition. */
        val = GP_VALUE;
        have = 1;
    }

    for (size_t d = 0; d < words; d++) {
        if (!isdef[d] || !def_is_observable(code, words, start, isdef, isuse, d)) continue;
        uint32_t w = code[d], op = w >> 26, rs = (w >> 21) & 31, imm = w & 0xffff, v;
        if (d > 0 && is_call(code[d - 1]) && call_clobbers(reg)
            && d - 1 != ignored_call)
            goto done;
        if (op == 0x0f) {
            v = imm << 16;
        } else if (op == 0x09 || op == 0x0d) {
            uint32_t base;
            if (!const_at_internal(code, join, words, start, d, (int)rs,
                                   depth + 1, ignored_call, &base))
                goto done;
            v = op == 0x09
              ? base + (uint32_t)(int32_t)(int16_t)imm
              : base | imm;
        } else {
            goto done;                      /* not a constant-producing definition */
        }
        if (!have) { val = v; have = 1; }
        else if (val != v) goto done;       /* two reaching definitions disagree */
    }
    if (have) { *out = val; ok = 1; }
done:
    free(isdef); free(isuse); free(seen);
    return ok;
}

static int const_at(const uint32_t *code, const uint8_t *join, size_t words,
                    uint32_t start, size_t i, int reg, int depth, uint32_t *out)
{
    return const_at_internal(code, join, words, start, i, reg, depth,
                             words, out);
}

/* A source-dependent value at a targeted call's argument-delivery boundary
 * can be queried only if the continuation cannot flow back to the same static
 * call.  Otherwise one static call node represents both the current
 * pre-callee boundary and a prior invocation whose callee clobber must be
 * retained; rejecting avoids conflating those two dynamic phases.  A direct
 * delay-slot constant remains sound because that instruction overwrites the
 * argument on every invocation without consulting pre-call state. */
static int call_continuation_reaches_call(const uint32_t *code, size_t words,
                                          uint32_t start, size_t call_at)
{
    if (call_at + 2 >= words) return 0;
    uint8_t *seen = calloc(words, 1);
    size_t *stack = malloc(words * sizeof *stack);
    if (!seen || !stack) exit(2);
    size_t sp = 0;
    stack[sp++] = call_at + 2;
    seen[call_at + 2] = 1;
    int reaches = 0;
    while (sp && !reaches) {
        size_t at = stack[--sp];
        if (at == call_at) {
            reaches = 1;
            break;
        }
        uint32_t successors[2];
        int count = succs_of(code, words, at, start, successors);
        for (int s = 0; s < count; s++) {
            size_t next = successors[s];
            if (!seen[next]) {
                seen[next] = 1;
                stack[sp++] = next;
            }
        }
    }
    free(seen);
    free(stack);
    return reaches;
}

static int const_at_call_boundary(const uint32_t *code, const uint8_t *join,
                                  size_t words, uint32_t start,
                                  size_t call_at, int reg, uint32_t *out)
{
    if (call_at >= words || !is_call(code[call_at])
        || call_continuation_reaches_call(code, words, start, call_at))
        return 0;
    return const_at_internal(code, join, words, start, call_at, reg, 0,
                             call_at, out);
}

/* Does `reg` hold the CALLER's value at index `use`?
 *
 * True exactly when no definition of `reg` reaches `use`. A whole-extent "is it
 * ever defined" test is far too strict for an argument register: a0 is clobbered
 * by every jal in the function, yet at the prologue copy `addu s1, a0, zero` --
 * before any call -- it is unambiguously the incoming argument. The question is
 * point-local, so it has to be asked point-locally. */
static int holds_incoming_at(const uint32_t *code, size_t words, uint32_t start,
                             int reg, size_t use,
                             const uint8_t *argument_call_boundary)
{
    uint8_t *isdef = calloc(words, 1), *isuse = calloc(words, 1);
    if (!isdef || !isuse) exit(2);
    for (size_t k = 0; k < words; k++)
        if (def_reg(code[k]) == reg
            || (is_call(code[k]) && call_clobbers(reg)
                && !(argument_call_boundary && argument_call_boundary[k])))
            isdef[k] = 1;
    isuse[use] = 1;
    int reached = 0;
    for (size_t d = 0; d < words && !reached; d++)
        if (isdef[d] && def_is_observable(code, words, start, isdef, isuse, d))
            reached = 1;
    free(isdef); free(isuse);
    return !reached;
}

/* Is definition `d` OBSERVABLE -- can any use of the register as a memory base be
 * reached from it without another definition overwriting it first?
 *
 * This matters because a single unobservable definition would otherwise veto an
 * otherwise-uniform register. The `lui` half of a `lui`/`lw` pair defines the
 * register for exactly one instruction, and the epilogue restore of a
 * callee-saved register is followed only by `jr`. Neither can be seen by any
 * use, so neither is evidence about what the uses read. Killing them is sound
 * in the safe direction: it only ever DISCARDS definitions that provably reach
 * nothing. */
static int def_is_observable(const uint32_t *code, size_t words, uint32_t start,
                             const uint8_t *isdef, const uint8_t *isuse, size_t d)
{
    uint8_t *seen = calloc(words, 1);
    uint32_t *stack = malloc(words * sizeof *stack);
    if (!seen || !stack) exit(2);
    size_t sp = 0;
    int found = 0;
    uint32_t out[2];
    int n = succs_of(code, words, d, start, out);
    for (int k = 0; k < n; k++)
        if (!seen[out[k]]) { seen[out[k]] = 1; stack[sp++] = out[k]; }
    while (sp && !found) {
        size_t i = stack[--sp];
        if (isuse[i]) { found = 1; break; }
        if (isdef[i]) continue;                  /* overwritten: stop here */
        n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++)
            if (!seen[out[k]]) { seen[out[k]] = 1; stack[sp++] = out[k]; }
    }
    free(seen); free(stack);
    return found;
}

typedef struct {
    long targeted, observable, dead, typed, other, ungoverned;
    int uniform; uint32_t from; int have_from;
} QueryResult;

static void run_query(const uint8_t *img, size_t img_len, uint32_t img_base, size_t skip,
                      const char *image, uint32_t start, uint32_t end, int reg,
                      const uint32_t *targets, size_t n_targets, int use_returns,
                      int any_target, int *first, QueryResult *out)
{
    size_t words = (end - start) / 4;
    size_t off0 = skip + (start - img_base);
    if (off0 + words * 4 > img_len) {
        fprintf(stderr, "extent 0x%08x..0x%08x outside %s\n", start, end, image);
        exit(2);
    }
    uint32_t *code = malloc(words * sizeof *code);
    uint8_t *join = calloc(words ? words : 1, 1);
    uint8_t *isdef = calloc(words ? words : 1, 1);
    uint8_t *seen = calloc(words ? words : 1, 1);
    uint8_t *argument_call_boundary = calloc(words ? words : 1, 1);
    if (!code || !join || !isdef || !seen || !argument_call_boundary) exit(2);
    for (size_t i = 0; i < words; i++) code[i] = le32(img + off0 + i * 4);

    /* join points: any index that is the target of a branch or jump, or that
     * follows an unconditional transfer. */
    for (size_t i = 0; i < words; i++) {
        uint32_t out[2];
        int n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++)
            if (out[k] != i + 1) join[out[k]] = 1;
        if (n == 0 && i + 1 < words) join[i + 1] = 1;
    }
    for (size_t i = 0; i < words; i++)
        if (def_reg(code[i]) == reg || (is_call(code[i]) && call_clobbers(reg)))
            isdef[i] = 1;


    /* The sites under scrutiny. When the caller names specific PCs -- the
     * unresolved accesses it is trying to bound -- only those count. That is the
     * question that actually matters: do the definitions reaching THESE sites
     * agree? Counting every use instead lets an unrelated site elsewhere in the
     * function veto a bound that genuinely holds here. With no PCs given it
     * falls back to every use of the register as a base. */
    uint8_t *isuse = calloc(words ? words : 1, 1);
    if (!isuse) exit(2);
    long targeted = 0; int no_return_site = 0;
    if (n_targets) {
        for (size_t t = 0; t < n_targets; t++) {
            if (targets[t] < start || targets[t] >= end) {
                fprintf(stderr, "target 0x%08x outside 0x%08x..0x%08x\n",
                        targets[t], start, end);
                exit(2);
            }
            size_t i = (targets[t] - start) / 4;
            /* MIPS executes the DELAY SLOT before the branch transfers control,
             * and that is exactly where an argument register is usually set:
             *     jal   player_vertical_update
             *     addiu a0, s0, -144      <- runs first, sets the argument
             * So "what does a0 hold at this call" must be asked from just past
             * the delay slot. Asking at the jal itself sees the jal's own
             * clobber and reports call_result -- the wrong answer, confidently. */
            if (any_target && i + 2 < words && is_call(code[i])) {
                argument_call_boundary[i] = 1;
                i += 2;
            }
            uint32_t w = code[i], op = w >> 26;
            int isacc = (op >= 0x20 && op <= 0x26) || (op >= 0x28 && op <= 0x2e);
            /* `any_target` asks about an ARBITRARY point -- a call site, where
             * the question is what the argument register holds when control
             * leaves, not whether the instruction dereferences it. */
            if (!any_target && (!isacc || (int)((w >> 21) & 31) != reg)) {
                fprintf(stderr, "target 0x%08x is not a %s-based access\n",
                        targets[t], REGNAME[reg]);
                exit(2);
            }
            isuse[i] = 1; targeted++;
        }
    } else if (use_returns) {
        /* The "uses" are the function's RETURN points. What the definitions of v0
         * reaching `jr ra` agree on IS the function's return type -- the ABI fact
         * a caller needs to type a v0 base. */
        for (size_t i = 0; i < words; i++) {
            uint32_t w = code[i];
            if ((w >> 26) == 0 && (w & 0x3f) == 0x08 && ((w >> 21) & 31) == 31) {
                isuse[i] = 1; targeted++;
            }
        }
        /* A function with no `jr ra` in its extent -- a tail-call thunk, or an
         * extent that stops short -- simply has no return point to type. That is
         * an ANSWER, not a malformed query, and killing the whole batch over it
         * would hide every other query's result. */
        no_return_site = !targeted;
    } else {
        for (size_t i = 0; i < words; i++) {
            uint32_t w = code[i], op = w >> 26;
            int isacc = (op >= 0x20 && op <= 0x26) || (op >= 0x28 && op <= 0x2e);
            if (isacc && (int)((w >> 21) & 31) == reg) { isuse[i] = 1; targeted++; }
        }
    }

    /* `defsat@...:CALL_PC` asks for the state delivered to the callee, after
     * its delay slot but before any callee instruction.  The general CFG uses
     * a call node as a caller-saved clobber for the continuation.  Suppress
     * exactly the explicitly targeted call here; every earlier/later call
     * remains a clobber.  Never suppress the call's own architectural link
     * definition when that link register is the query: doing so would expose a
     * stale pre-call value for $ra (JAL) or rd (JALR).  A delay-slot definition
     * then dominates the synthetic boundary, while an absent definition leaves
     * the entry path visible. */
    for (size_t i = 0; i < words; i++)
        if (argument_call_boundary[i]
            && call_boundary_suppresses_definition(code[i], reg))
            isdef[i] = 0;

    /* An access reachable from entry without passing ANY definition arrives
     * holding whatever the caller left; no local definition governs it. */
    reach_avoiding_defs(code, words, start, isdef, seen);

    printf("%s  {\"image\":\"%s\",\"function\":\"0x%08x\",\"register\":\"%s\",\n",
           *first ? "" : ",\n", image, start, REGNAME[reg]);
    printf("   \"targeted_sites\":%ld,\"target_selection\":\"%s\",\n", targeted,
           n_targets ? (any_target ? "caller-supplied pcs (arbitrary points)"
                                   : "caller-supplied pcs")
                     : use_returns ? "every `jr ra` in the extent (return typing)"
                                   : "every base use in the extent");
    *first = 0;
    printf("   \"definitions\": [");

    int dfirst = 1;
    long n_global = 0, n_other = 0, n_dead = 0;
    uint32_t single_addr = 0; int addr_agree = 1, have_addr = 0;
    for (size_t i = 0; i < words; i++) {
        if (!isdef[i]) continue;
        int observable = def_is_observable(code, words, start, isdef, isuse, i);
        uint32_t pc = start + (uint32_t)(i * 4);
        const char *cls = "opaque", *idxreg = "", *constant_reg = "";
        char extra[320], incbuf[16]; extra[0] = 0;

        /* Follow pure moves before classifying. `s2 = a0` at entry tells us
         * nothing on its own; what defined a0 does. Only whole-register moves
         * are followed, only inside one basic block, and only 8 deep. Each hop
         * is reported so the chain is auditable rather than asserted. */
        size_t site = i;
        int rr = reg, hops = 0, incoming = -1;
        size_t argument_call = words;
        if (i > 0 && argument_call_boundary[i - 1]) argument_call = i - 1;
        char chain[192]; chain[0] = 0;
        for (; argument_call == words && hops < 8; hops++) {
            int src = move_source(code[site]);
            if (src < 0) break;
            long prev = def_of_reg_before(code, join, site, src);
            if (prev < 0) {
                if (holds_incoming_at(code, words, start, src, site,
                                      argument_call_boundary))
                    incoming = src;
                snprintf(chain, sizeof chain,
                         ",\"chase\":\"%s <- %s, %s\"", REGNAME[rr], REGNAME[src],
                         incoming >= 0 ? "which is an INCOMING ARGUMENT (never defined here)"
                                       : "which has no single definition here");
                break;
            }
            size_t n = strlen(chain);
            snprintf(chain + n, sizeof chain - n, "%s%s<-%s@0x%08x",
                     n ? " " : ",\"chase\":\"", REGNAME[rr], REGNAME[src],
                     (unsigned)(start + (uint32_t)prev * 4));
            site = (size_t)prev; rr = src;
        }
        /* Close the chain string only if it is still open. Guarding on the
         * TEXT of a message is how this grew a stray quote the moment the
         * message was reworded; guard on the structure instead. */
        {
            size_t n = strlen(chain);
            if (n && chain[n - 1] != '"') snprintf(chain + n, sizeof chain - n, "\"");
        }

        uint32_t w = code[site];
        size_t delay_call = words;
        if (site > 0 && is_call(code[site - 1]) && call_clobbers(rr))
            delay_call = site - 1;
        if (argument_call < words) {
            uint32_t cv;
            if (call_delay_argument_constant(code, join, words, start,
                                             argument_call, reg, &cv)) {
                cls = "materialised_constant";
                snprintf(extra, sizeof extra,
                         ",\"value\":\"0x%08x\","
                         "\"call_boundary\":\"before_callee_execution\"",
                         cv);
            } else {
                cls = "opaque";
                snprintf(extra, sizeof extra,
                         ",\"reason\":"
                         "\"call_delay_argument_not_a_tracked_constant\"");
            }
        } else if (delay_call < words) {
            /* The instruction at SITE ran, but the callee subsequently owns
             * every caller-saved register before the continuation.  Report the
             * call rather than laundering its delay-slot definition into a
             * constant, load, or table fact. */
            cls = "call_result";
            uint32_t tgt = call_target(code, delay_call, start);
            if (tgt) snprintf(extra, sizeof extra, ",\"callee\":\"0x%08x\"", tgt);
            else snprintf(extra, sizeof extra, ",\"callee\":null,\"indirect\":true");
        } else if (is_call(w)) {
            if (call_link_reg(w) == rr) {
                cls = "opaque";
                snprintf(extra, sizeof extra,
                         ",\"reason\":\"call_link_value_not_modelled\"");
            } else {
                cls = "call_result";
            }
            uint32_t tgt = call_target(code, site, start);
            size_t n = strlen(extra);
            if (tgt)
                snprintf(extra + n, sizeof extra - n,
                         ",\"callee\":\"0x%08x\"", tgt);
            else
                snprintf(extra + n, sizeof extra - n,
                         ",\"callee\":null,\"indirect\":true");
        } else if (is_load(w)) {
            int base = (w >> 21) & 31;
            int32_t disp = (int16_t)(w & 0xffff);
            uint32_t bv, lexical_bv;
            size_t table_failure_at = site;
            const char *table_failure_reason = NULL;
            if (base == 29 || base == 30) {
                cls = "frame_reload";
                snprintf(extra, sizeof extra, ",\"slot\":%d", disp);
            } else if (const_base(code, join, site, base, &lexical_bv)
                       && const_at(code, join, words, start, site, base, 0, &bv)
                       && bv == lexical_bv) {
                cls = "global_load";
                uint32_t addr = bv + (uint32_t)disp;
                snprintf(extra, sizeof extra, ",\"address\":\"0x%08x\"", addr);
                if (observable) {
                    if (!have_addr) { single_addr = addr; have_addr = 1; }
                    else if (single_addr != addr) addr_agree = 0;
                }
            } else {
                int table_status = table_base(
                    code, join, words, start, site, base, &bv,
                    &idxreg, &constant_reg, &table_failure_at,
                    &table_failure_reason);
                if (table_status == 1) {
                    cls = "table_load";
                    uint32_t addr = bv + (uint32_t)disp;
                    snprintf(extra, sizeof extra,
                             ",\"table\":\"0x%08x\",\"index\":\"%s\","
                             "\"table_base_register\":\"%s\","
                             "\"table_base_proof\":"
                             "\"all_reaching_definitions_same_constant\"",
                             addr, idxreg, constant_reg);
                    if (observable) {
                        if (!have_addr) { single_addr = addr; have_addr = 1; }
                        else if (single_addr != addr) addr_agree = 0;
                    }
                } else if (table_status < 0) {
                    snprintf(extra, sizeof extra,
                             ",\"base\":\"%s\",\"table_address_failure\":{"
                             "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                             "\"reason\":\"%s\"}", REGNAME[base],
                             (unsigned)(start + (uint32_t)table_failure_at * 4),
                             code[table_failure_at], table_failure_reason);
                } else {
                    snprintf(extra, sizeof extra, ",\"base\":\"%s\"",
                             REGNAME[base]);
                }
            }
        } else {
            uint32_t op = w >> 26, fn = w & 0x3f, rs = (w >> 21) & 31, rt = (w >> 16) & 31;
            uint32_t cv;
            /* Straight-line first (cheap, already proven); the CFG-aware form
             * only as a FALLBACK, so results that were recoverable before stay
             * byte-identical and this can only ever decide more, never differently. */
            if (const_base(code, join, site + 1, rr, &cv)
                || const_at(code, join, words, start, site + 1, rr, 0, &cv)) {
                /* Whatever the chain looked like -- lui alone, lui+addiu, or an
                 * addiu off another register -- the value is pinned. */
                cls = "materialised_constant";
                snprintf(extra, sizeof extra, ",\"value\":\"0x%08x\"", cv);
            } else if ((op == 0x09) && (int)rs == rr && (w & 0xffff) != 0) {
                /* addiu r, r, K -- a SELF-ADJUSTMENT. On its own it says
                 * nothing; combined with a materialised anchor it makes the
                 * register an arithmetic progression, which is what the
                 * writer-value-domain check needs to see explicitly instead
                 * of an opaque wall. The delta is signed and reported as is:
                 * the CALLER decides whether all deltas are positive/uniform. */
                cls = "self_adjust";
                snprintf(extra, sizeof extra, ",\"delta\":%d",
                         (int)(int16_t)(w & 0xffff));
            } else if (op == 0x09 || op == 0x0d) {
                cls = "opaque";
                snprintf(extra, sizeof extra, ",\"from\":\"%s\"", REGNAME[rs]);
            } else if (op == 0 && (fn == 0x21 || fn == 0x20) && (rs == 0 || rt == 0)) {
                cls = "register_copy";
                snprintf(extra, sizeof extra, ",\"from\":\"%s\"", REGNAME[rs ? rs : rt]);
            } else if (op == 0 && (fn == 0x21 || fn == 0x20)) {
                /* reg = INDEX + CONST: an element of a fixed table whose index
                 * this pass cannot recover. The table is still pinned. */
                uint32_t tb; const char *ix, *cr, *table_failure_reason = NULL;
                size_t table_failure_at = site;
                int table_status = table_add_definition(
                    code, join, words, start, site, &tb, &ix, &cr,
                    &table_failure_at, &table_failure_reason);
                if (table_status == 1) {
                    cls = "table_address";
                    snprintf(extra, sizeof extra,
                             ",\"table\":\"0x%08x\",\"index\":\"%s\","
                             "\"table_base_register\":\"%s\","
                             "\"table_base_proof\":"
                             "\"all_reaching_definitions_same_constant\"",
                             tb, ix, cr);
                } else if (table_status < 0) {
                    snprintf(extra, sizeof extra,
                             ",\"table_address_failure\":{"
                             "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                             "\"reason\":\"%s\"}",
                             (unsigned)(start + (uint32_t)table_failure_at * 4),
                             code[table_failure_at], table_failure_reason);
                }
            }
        }
        int typed = strcmp(cls, "global_load") == 0 || strcmp(cls, "table_load") == 0;
        if (!observable) n_dead++;
        else if (typed) n_global++;
        else n_other++;
        printf("%s\n    {\"pc\":\"0x%08x\",\"class\":\"%s\",\"observable\":%s,"
               "\"word\":\"0x%08x\",\"hops\":%d,\"incoming\":%s%s%s}",
               dfirst ? "" : ",", pc, cls, observable ? "true" : "false",
               code[i], hops,
               incoming >= 0 ? (sprintf(incbuf, "\"%s\"", REGNAME[incoming]), incbuf) : "null",
               extra, chain);
        dfirst = 0;
    }
    printf("%s],\n", dfirst ? "" : "\n   ");

    /* uses of the register as a memory base, and whether any is governed by no
     * definition at all */
    long uses = 0, ungoverned = 0;
    for (size_t i = 0; i < words; i++) {
        if (!isuse[i]) continue;
        uses++;
        if (seen[i]) ungoverned++;
    }
    printf("   \"definition_count\":%ld,\"observable_defs\":%ld,"
           "\"unobservable_defs\":%ld,\n", n_global + n_other + n_dead,
           n_global + n_other, n_dead);
    printf("   \"typed_load_defs\":%ld,\"other_defs\":%ld,\n", n_global, n_other);
    printf("   \"every_observable_def_loads_one_address\":%s,\n",
           (n_global > 0 && n_other == 0 && addr_agree) ? "true" : "false");
    if (have_addr && addr_agree)
        printf("   \"loaded_from\":\"0x%08x\",\n", single_addr);
    else
        printf("   \"loaded_from\":null,\n");
    /* Does the register hold the CALLER's value at every targeted site? Then it
     * IS the incoming argument, and typing it is a question about the callers,
     * not about anything in this function. */
    int all_incoming = targeted > 0;
    for (size_t i = 0; i < words && all_incoming; i++)
        if (isuse[i] && !holds_incoming_at(code, words, start, reg, i,
                                          argument_call_boundary))
            all_incoming = 0;
    printf("   \"targets_all_hold_incoming\":%s,\"no_return_site\":%s,\n",
           all_incoming ? "true" : "false", no_return_site ? "true" : "false");
    printf("   \"base_uses\":%ld,\"entry_reachable_uses\":%ld,\n", uses, ungoverned);
    printf("   \"governs_every_use\":%s}", ungoverned == 0 ? "true" : "false");
    if (out) {
        out->targeted = targeted; out->observable = n_global + n_other;
        out->dead = n_dead; out->typed = n_global; out->other = n_other;
        out->ungoverned = ungoverned;
        out->uniform = (n_global > 0 && n_other == 0 && addr_agree);
        out->from = single_addr; out->have_from = have_addr && addr_agree;
    }

    free(code); free(join); free(isdef); free(seen); free(isuse);
    free(argument_call_boundary);
}

typedef struct {
    uint32_t pc;
    int value_reg;
    const char *spelling;
    int computed_scale;
    const char *value_source;
    uint32_t value_source_pc;
} TableWriter;

static int writer_cmp(const void *a, const void *b)
{
    const TableWriter *wa = (const TableWriter *)a;
    const TableWriter *wb = (const TableWriter *)b;
    return wa->pc < wb->pc ? -1 : wa->pc > wb->pc;
}

static int writer_present(const TableWriter *writers, size_t count, uint32_t pc)
{
    for (size_t i = 0; i < count; i++) if (writers[i].pc == pc) return 1;
    return 0;
}

/* Does REG carry TABLE by an exact lui + addiu/ori spelling before word AT?
 * The walk stops at the first earlier definition, so a stale lui cannot leak
 * across an intervening write. */
static int register_materialises_table(const uint32_t *code, size_t at,
                                       int reg, uint32_t table)
{
    for (size_t steps = 0, i = at; i-- > 0 && steps++ < 16; ) {
        uint32_t w = code[i], op = w >> 26;
        if (def_reg(w) != reg) continue;
        if ((op == 0x09 || op == 0x0d) && (int)((w >> 21) & 31) == reg) {
            uint32_t low = op == 0x09 ? (uint32_t)(int32_t)(int16_t)(w & 0xffffu)
                                      : (w & 0xffffu);
            for (size_t inner = 0, k = i; k-- > 0 && inner++ < 8; ) {
                uint32_t p = code[k];
                if (def_reg(p) != reg) continue;
                if ((p >> 26) == 0x0f) {
                    uint32_t value = ((p & 0xffffu) << 16);
                    value = op == 0x09 ? value + low : value | low;
                    return value == table;
                }
                return 0;
            }
        }
        if (op == 0x0f)
            return ((w & 0xffffu) << 16) == table;
        return 0;
    }
    return 0;
}

/* Recognise BASE = TABLE + (unknown_index << 2) before word AT. This is the
 * materialise-then-index spelling that hid 0x80049C10/14. It proves an address
 * FAMILY, not the index bound; the JSON says that explicitly. */
static int computed_table_base(const uint32_t *code, size_t at, int base,
                               uint32_t table, int *scale)
{
    size_t add_at = 0;
    int other = -1;
    for (size_t steps = 0, i = at; i-- > 0 && steps++ < 12; ) {
        uint32_t w = code[i];
        if (def_reg(w) != base) continue;
        if ((w >> 26) == 0 && (w & 0x3f) == 0x21) {       /* addu */
            int rs = (w >> 21) & 31, rt = (w >> 16) & 31;
            if (rs == base) other = rt;
            else if (rt == base) other = rs;
            else return 0;
            add_at = i;
        } else return 0;
        break;
    }
    if (!add_at || other < 0 || !register_materialises_table(code, add_at, other, table))
        return 0;
    for (size_t steps = 0, i = add_at; i-- > 0 && steps++ < 12; ) {
        uint32_t w = code[i];
        if (def_reg(w) != base) continue;
        if ((w >> 26) == 0 && (w & 0x3f) == 0x00 &&
            (int)((w >> 11) & 31) == base) {              /* sll base,idx,2 */
            int shamt = (w >> 6) & 31;
            if (shamt == 2) { *scale = 1 << shamt; return 1; }
        }
        return 0;
    }
    return 0;
}

/* Positive recogniser for stores into a pointer TABLE. It scans every aligned
 * store-shaped word in the loaded image, but its ADDRESS recognisers are not an
 * exhaustive alias analysis. The residual is therefore reported explicitly;
 * writer_count is a lower bound even after all six known spellings are found. */
static void scan_table_writers(const uint8_t *img, size_t img_len, uint32_t img_base,
                               size_t skip, const char *image, uint32_t table, int *first)
{
    if (skip == 0 && img_len >= 0x800 && memcmp(img, "PS-X EXE", 8) == 0)
        skip = 0x800;                                      /* loaded text only */
    size_t n = (img_len - skip) / 4;
    uint32_t *code = malloc(n * sizeof *code);
    TableWriter *writers = calloc(n ? n : 1, sizeof *writers);
    if (!code || !writers) exit(2);
    for (size_t i = 0; i < n; i++) code[i] = le32(img + skip + i * 4);
    printf("%s  {\"image\":\"%s\",\"table\":\"0x%08x\",\"method\":"
           "\"positive whole-loaded-image spelling recogniser; not a complete alias analysis\",\n",
           *first ? "" : ",\n", image, table);
    *first = 0;
    size_t writer_count = 0;
    long store_words = 0, nonnull = 0, computed = 0;
    uint32_t lo = table & 0xffff0000u, want = table & 0xffffu;
    for (size_t i = 0; i < n; i++) {
        uint32_t w = code[i], op = w >> 26;
        if (op != 0x28 && op != 0x29 && op != 0x2b) continue;       /* sb/sh/sw */
        store_words++;
        if ((w & 0xffffu) != want) continue;
        int base = (w >> 21) & 31, rt = (w >> 16) & 31;
        /* the base must be able to carry the table's upper half */
        int plausible = 0;
        for (size_t k = i; k-- > 0 && k + 64 > i; ) {
            uint32_t p = le32(img + skip + k * 4);
            if ((p >> 26) == 0x0f && (int)((p >> 16) & 31) == base) {
                plausible = ((p & 0xffffu) << 16) == lo; break;
            }
            if (def_reg(p) == base && (p >> 26) != 0) break;
        }
        if (!plausible) continue;
        writers[writer_count++] = (TableWriter){
            img_base + (uint32_t)skip + (uint32_t)(i * 4), rt,
            "low_immediate_plus_materialised_upper", 0, "not_classified", 0};
    }
    /* A second, independent spelling: store 0(TABLE + (index << 2)). */
    for (size_t i = 0; i < n; i++) {
        uint32_t w = code[i], op = w >> 26;
        if ((op != 0x28 && op != 0x29 && op != 0x2b) || (w & 0xffffu) != 0)
            continue;
        int base = (w >> 21) & 31, rt = (w >> 16) & 31, scale = 0;
        uint32_t pc = img_base + (uint32_t)skip + (uint32_t)(i * 4);
        if (writer_present(writers, writer_count, pc) ||
            !computed_table_base(code, i, base, table, &scale)) continue;
        const char *value_source = "not_classified";
        uint32_t value_source_pc = 0;
        if (rt == 0) value_source = "zero_by_encoding";
        else {
            for (size_t steps = 0, k = i; k-- > 0 && steps++ < 8; ) {
                uint32_t p = code[k];
                if (def_reg(p) != rt) continue;
                if ((p >> 26) == 0x23 && (p & 0xffffu) == 0) { /* lw rt,0(base) */
                    int source_base = (p >> 21) & 31, source_scale = 0;
                    if (computed_table_base(code, k, source_base, table, &source_scale) &&
                        source_scale == scale) {
                        value_source = "existing_entry_from_same_table_family";
                        value_source_pc = img_base + (uint32_t)skip + (uint32_t)(k * 4);
                    }
                }
                break;
            }
        }
        writers[writer_count++] = (TableWriter){pc, rt,
            "materialise_then_scaled_index", scale, value_source, value_source_pc};
        computed++;
    }
    qsort(writers, writer_count, sizeof *writers, writer_cmp);
    printf("   \"writers\": [");
    for (size_t i = 0; i < writer_count; i++) {
        TableWriter *row = &writers[i];
        if (row->value_reg != 0) nonnull++;
        printf("%s\n    {\"pc\":\"0x%08x\",\"value_register\":\"%s\","
               "\"clears_to_null\":%s,\"address_spelling\":\"%s\","
               "\"slot_index_scale\":%s,\"slot_index_domain_proved\":%s,"
               "\"value_source_kind\":\"%s\",\"value_source_pc\":",
               i ? "," : "", row->pc, REGNAME[row->value_reg],
               row->value_reg == 0 ? "true" : "false", row->spelling,
               row->computed_scale ? "4" : "null",
               row->computed_scale ? "false" : "null", row->value_source);
        if (row->value_source_pc) printf("\"0x%08x\"}", row->value_source_pc);
        else printf("null}");
    }
    printf("%s],\n", writer_count ? "\n   " : "");
    printf("   \"writer_count\":%zu,\"non_null_writers\":%ld,"
           "\"computed_base_writers\":%ld,\n", writer_count, nonnull, computed);
    printf("   \"syntactic_store_word_universe\":%ld,"
           "\"recognizer_residual_store_words\":%ld,"
           "\"enumeration_complete\":false,\"writer_count_is_lower_bound\":true,\n",
           store_words, store_words - (long)writer_count);
    printf("   \"residual_meaning\":\"every aligned sb/sh/sw-shaped word in the loaded image not identified by either positive table-writer spelling; these are not all table aliases, but this recogniser does not decide them and therefore cannot claim an exhaustive writer census\"}");
    free(code);
    free(writers);
}

/* ============================================================ island@ ===
 * The instruction facts behind a proved_jr_cluster_argument binding. Every
 * check either PASSES with the evidence enumerated or FAILS naming the exact
 * pc that broke it; nothing is assumed from the query's own numbers beyond
 * which addresses to look at.
 * ========================================================================= */

static int is_control(uint32_t w)
{
    uint32_t op = w >> 26, fn = w & 0x3f;
    if (op == 2 || op == 3 || op == 1 || (op >= 4 && op <= 7)) return 1;
    if (op == 0 && (fn == 8 || fn == 9)) return 1;
    return 0;
}

static int access_width(uint32_t op)
{
    switch (op) {
    case 0x20: case 0x24: case 0x28: return 1;              /* lb/lbu/sb  */
    case 0x21: case 0x25: case 0x29: return 2;              /* lh/lhu/sh  */
    default:                          return 4;
    }
}

static const char *access_mnemonic(uint32_t op)
{
    switch (op) {
    case 0x20: return "lb";  case 0x21: return "lh";  case 0x22: return "lwl";
    case 0x23: return "lw";  case 0x24: return "lbu"; case 0x25: return "lhu";
    case 0x26: return "lwr"; case 0x28: return "sb";  case 0x29: return "sh";
    case 0x2a: return "swl"; case 0x2b: return "sw";  case 0x2e: return "swr";
    default:   return "?";
    }
}

/* Is the restore at word index `i` part of a TERMINAL epilogue -- nothing but
 * sp-relative loads, the sp adjustment and nops between it and a `jr ra`, whose
 * delay slot then leaves the function? Returns the jr's pc via *jr_pc. */
static int is_terminal_epilogue(const uint32_t *code, size_t words, uint32_t start,
                                size_t i, uint32_t *jr_pc)
{
    for (size_t k = i; k < words && k < i + 16; k++) {
        uint32_t w = code[k], op = w >> 26;
        if (op == 0 && (w & 0x3f) == 8) {                    /* jr */
            if (((w >> 21) & 31) != 31) return 0;            /* not jr ra */
            *jr_pc = start + (uint32_t)(k * 4);
            return 1;                                        /* delay slot exits */
        }
        if (w == 0) continue;                                /* nop */
        if (op == 0x23 && ((w >> 21) & 31) == 29) continue;  /* lw rX, off(sp) */
        if (op == 0x09 && ((w >> 21) & 31) == 29
            && ((w >> 16) & 31) == 29) continue;             /* addiu sp, sp, imm */
        return 0;                                            /* anything else */
    }
    return 0;
}

static void run_island_query(const uint8_t *img, size_t img_len, uint32_t img_base,
                             const char *image, uint32_t c_lo, uint32_t c_hi,
                             uint32_t i_lo, uint32_t i_hi, int reg,
                             const uint32_t *call_pcs, size_t n_calls, int *first)
{
    size_t words = (c_hi - c_lo) / 4;
    size_t off0 = c_lo - img_base;
    if (off0 + words * 4 > img_len || i_lo < c_lo || i_hi > c_hi || i_hi <= i_lo) {
        fprintf(stderr, "island@ ranges invalid for %s\n", image);
        exit(2);
    }
    uint32_t *code = malloc(words * sizeof *code);
    if (!code) exit(2);
    for (size_t i = 0; i < words; i++) code[i] = le32(img + off0 + i * 4);

    printf("%s  {\"island_query\":true,\"image\":\"%s\","
           "\"cluster\":[\"0x%08x\",\"0x%08x\"],\"island\":[\"0x%08x\",\"0x%08x\"],"
           "\"register\":\"%s\",\n",
           *first ? "" : ",\n", image, c_lo, c_hi, i_lo, i_hi, REGNAME[reg]);
    *first = 0;

    int callee_saved = (reg >= 16 && reg <= 23) || reg == 30;
    printf("   \"register_is_callee_saved\":%s,\n", callee_saved ? "true" : "false");

    /* (a) straight-line prologue up to the first REG write, which must be a
     * pure copy of an argument register. Any control flow first means an entry
     * at c_lo is NOT guaranteed to execute the copy. */
    int prologue_ok = 0, arg_reg = -1;
    uint32_t prologue_pc = 0;
    const char *prologue_fail = "no write to the register before the first control flow";
    for (size_t i = 0; i < words; i++) {
        uint32_t w = code[i];
        if (is_control(w)) { break; }
        if (def_reg(w) == reg) {
            int src = move_source(w);
            if (src >= 4 && src <= 7) {
                prologue_ok = 1; arg_reg = src;
                prologue_pc = c_lo + (uint32_t)(i * 4);
            } else {
                prologue_fail = "first write is not a pure copy of a0-a3";
                prologue_pc = c_lo + (uint32_t)(i * 4);
            }
            break;
        }
    }
    if (prologue_ok)
        printf("   \"prologue\":{\"copy_pc\":\"0x%08x\",\"argument\":\"%s\","
               "\"straight_line\":true},\n", prologue_pc, REGNAME[arg_reg]);
    else
        printf("   \"prologue\":{\"copy_pc\":%s,\"failure\":\"%s\"},\n",
               prologue_pc ? "\"set\"" : "null", prologue_fail);

    /* (b) the write census: every OTHER write must be a terminal-epilogue
     * sp-restore. Reported one by one so a failure names its pc. */
    printf("   \"writes\": [");
    int wfirst = 1, all_epilogue = 1;
    long n_writes = 0;
    for (size_t i = 0; i < words; i++) {
        if (def_reg(code[i]) != reg) continue;
        uint32_t pc = c_lo + (uint32_t)(i * 4);
        n_writes++;
        const char *kind; uint32_t jr_pc = 0;
        if (prologue_ok && pc == prologue_pc) {
            kind = "prologue_argument_copy";
        } else if ((code[i] >> 26) == 0x23 && ((code[i] >> 21) & 31) == 29
                   && is_terminal_epilogue(code, words, c_lo, i + 1, &jr_pc)) {
            kind = "terminal_epilogue_restore";
        } else {
            kind = "OTHER";
            all_epilogue = 0;
        }
        printf("%s\n    {\"pc\":\"0x%08x\",\"word\":\"0x%08x\",\"kind\":\"%s\"",
               wfirst ? "" : ",", pc, code[i], kind);
        if (jr_pc) printf(",\"jr_ra_pc\":\"0x%08x\"", jr_pc);
        printf("}");
        wfirst = 0;
    }
    printf("%s],\n", wfirst ? "" : "\n   ");
    printf("   \"write_count\":%ld,"
           "\"all_nonprologue_writes_are_terminal_epilogue_restores\":%s,\n",
           n_writes, all_epilogue ? "true" : "false");

    /* (c) call sites: jal c_lo with a pure copy into the SAME argument register
     * in the delay slot. The copied SOURCE register is what the caller-side
     * typed-pointer query is then asked about. */
    printf("   \"callers\": [");
    int cfirst = 1, calls_ok = n_calls > 0;
    for (size_t c = 0; c < n_calls; c++) {
        uint32_t pc = call_pcs[c];
        size_t coff = pc - img_base;
        int ok = 0, src = -1;
        const char *why = "";
        if (coff + 8 > img_len) {
            why = "call pc outside the image"; calls_ok = 0;
        } else {
            uint32_t w = le32(img + coff), d = le32(img + coff + 4);
            uint32_t tgt = ((pc + 4) & 0xf0000000u) | ((w & 0x03ffffffu) << 2);
            if ((w >> 26) != 0x03 || tgt != c_lo) {
                why = "not a jal to the cluster entry"; calls_ok = 0;
            } else {
                src = move_source(d);
                int dest = def_reg(d);
                if (src < 0 || dest != arg_reg) {
                    why = "delay slot is not a pure copy into the argument register";
                    src = -1; calls_ok = 0;
                } else {
                    ok = 1;
                }
            }
        }
        printf("%s\n    {\"call_pc\":\"0x%08x\",\"decodes\":%s",
               cfirst ? "" : ",", pc, ok ? "true" : "false");
        if (ok) printf(",\"delay_slot_copies\":\"%s\"", REGNAME[src]);
        else printf(",\"failure\":\"%s\"", why);
        printf("}");
        cfirst = 0;
    }
    printf("%s],\n", cfirst ? "" : "\n   ");
    printf("   \"all_call_sites_decode\":%s,\n", calls_ok ? "true" : "false");

    /* (d) the island's REG-based accesses, for the caller to reconcile against
     * the ledger as an exact set. Control flow inside the island is counted so
     * a future island with internal branches is visible rather than assumed
     * straight-line. */
    printf("   \"island_accesses\": [");
    int afirst = 1;
    long island_defs = 0, island_control = 0;
    for (uint32_t pc = i_lo; pc < i_hi; pc += 4) {
        uint32_t w = code[(pc - c_lo) / 4], op = w >> 26;
        if (def_reg(w) == reg) island_defs++;
        if (is_control(w)) island_control++;
        int isacc = (op >= 0x20 && op <= 0x26) || (op >= 0x28 && op <= 0x2e);
        if (!isacc || (int)((w >> 21) & 31) != reg) continue;
        printf("%s\n    {\"pc\":\"0x%08x\",\"mnemonic\":\"%s\",\"store\":%s,"
               "\"offset\":%d,\"width\":%d}",
               afirst ? "" : ",", pc, access_mnemonic(op),
               op >= 0x28 ? "true" : "false",
               (int)(int16_t)(w & 0xffff), access_width(op));
        afirst = 0;
    }
    printf("%s],\n", afirst ? "" : "\n   ");
    printf("   \"island_register_defs\":%ld,\"island_control_flow\":%ld,\n",
           island_defs, island_control);
    printf("   \"verdict\":%s}",
           (callee_saved && prologue_ok && all_epilogue && calls_ok)
               ? "true" : "false");
    free(code);
}

/* ======================================================== progression@ ===
 * Prove the VALUE DOMAIN of a register at a store site: every definition of
 * the register in the extent must be a shadowed-or-agreeing constant
 * materialisation (the anchor), a positive self-adjustment (the stride), or an
 * sp-reload inside a TERMINAL epilogue. Then every value the register can hold
 * anywhere in the function is >= the anchor and on the anchor's stride
 * lattice.
 *
 * ⚠️ Deliberately NOT built on the observability walk: `def_is_observable`
 * follows the linear successor out of a delay slot, so a delay-slot definition
 * can be reported dead while execution carries its value through the owning
 * jump -- measured on mover_updater's own `addiu s2, s2, 0x84` at 0x8004D3FC.
 * A reach analysis with a known miss direction must not decide a PROOF, so
 * this check classifies EVERY definition with no reachability argument at
 * all; over-strict is the safe direction. The entry condition is the same
 * straight-line rule as island@: the register must be materialised before the
 * first control-flow instruction, so no path reaches a use holding the
 * caller's value. */
static void run_progression_query(const uint8_t *img, size_t img_len,
                                  uint32_t img_base, const char *image,
                                  uint32_t start, uint32_t end, int reg,
                                  uint32_t store_pc, int *first)
{
    size_t words = (end - start) / 4;
    size_t off0 = start - img_base;
    if (off0 + words * 4 > img_len || store_pc < start || store_pc >= end) {
        fprintf(stderr, "progression@ ranges invalid for %s\n", image);
        exit(2);
    }
    uint32_t *code = malloc(words * sizeof *code);
    uint8_t *join = calloc(words ? words : 1, 1);
    if (!code || !join) exit(2);
    for (size_t i = 0; i < words; i++) code[i] = le32(img + off0 + i * 4);
    for (size_t i = 0; i < words; i++) {
        uint32_t out[2];
        int n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++)
            if (out[k] != i + 1) join[out[k]] = 1;
        if (n == 0 && i + 1 < words) join[i + 1] = 1;
    }

    printf("%s  {\"progression_query\":true,\"image\":\"%s\","
           "\"function\":\"0x%08x\",\"register\":\"%s\",\"store_pc\":\"0x%08x\",\n",
           *first ? "" : ",\n", image, start, REGNAME[reg], store_pc);
    *first = 0;

    /* the store itself must exist and carry REG as its VALUE or BASE register:
     * a writer-domain proof asks about the value, a base-domain proof about
     * the base, and the query reports which role it found so the caller can
     * demand the one it meant. */
    size_t si = (store_pc - start) / 4;
    uint32_t sw_word = code[si], sw_op = sw_word >> 26;
    int is_store_insn = (sw_op >= 0x28 && sw_op <= 0x2e);
    int is_value = is_store_insn && (int)((sw_word >> 16) & 31) == reg;
    int is_base = (is_store_insn || (sw_op >= 0x20 && sw_op <= 0x26))
                  && (int)((sw_word >> 21) & 31) == reg;
    int store_ok = is_value || is_base;
    printf("   \"store_value_register_matches\":%s,\"register_role\":\"%s\",\n",
           is_value ? "true" : "false",
           is_value && is_base ? "value_and_base"
           : is_value ? "value" : is_base ? "base" : "none");

    /* straight-line entry: REG must be defined before the first control flow */
    int entry_ok = 0;
    for (size_t i = 0; i < words; i++) {
        if (is_control(code[i])) break;
        if (def_reg(code[i]) == reg) { entry_ok = 1; break; }
    }
    printf("   \"defined_before_first_control_flow\":%s,\n", entry_ok ? "true" : "false");

    /* classify EVERY definition, no reachability argument anywhere */
    printf("   \"definitions\": [");
    int dfirst = 1, all_ok = 1, have_anchor = 0, deltas_uniform = 1;
    uint32_t anchor = 0; int32_t stride = 0; int have_stride = 0;
    long n_defs = 0;
    for (size_t i = 0; i < words; i++) {
        if (def_reg(code[i]) != reg) continue;
        n_defs++;
        uint32_t pc = start + (uint32_t)(i * 4);
        uint32_t w = code[i], op = w >> 26, rs = (w >> 21) & 31;
        const char *cls; char extra[96]; extra[0] = 0;
        uint32_t cv; uint32_t jr_pc = 0;
        if (i > 0 && is_call(code[i - 1]) && call_clobbers(reg)) {
            cls = "call_clobber_after_delay_slot";
            all_ok = 0;
            printf("%s\n    {\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                   "\"class\":\"%s\"%s}",
                   dfirst ? "" : ",", pc, w, cls, extra);
            dfirst = 0;
            continue;
        }
        /* a constant def SHADOWED by an immediately following constant def of
         * the same register is the first half of a materialisation pair; the
         * pair's final value is what matters. Only valid when the shadowed
         * instruction is not a delay slot (its successor is then linear). */
        int shadowed = i + 1 < words && def_reg(code[i + 1]) == reg
                       && (i == 0 || !is_control(code[i - 1]))
                       && (const_base(code, join, i + 2, reg, &cv)
                           || const_at(code, join, words, start, i + 2, reg, 0, &cv));
        if (shadowed) {
            cls = "shadowed_by_next_definition";
        } else if (op == 0x23 && rs == 29
                   && is_terminal_epilogue(code, words, start, i + 1, &jr_pc)) {
            cls = "terminal_epilogue_restore";
            snprintf(extra, sizeof extra, ",\"jr_ra_pc\":\"0x%08x\"", jr_pc);
        } else if (const_base(code, join, i + 1, reg, &cv)
                   || const_at(code, join, words, start, i + 1, reg, 0, &cv)) {
            /* Constant resolution FIRST: the addiu half of a lui/addiu
             * materialisation pair has rs == reg and would otherwise be read
             * as a (negative) self-adjustment of the lui's throwaway value. */
            cls = "materialised_constant";
            snprintf(extra, sizeof extra, ",\"value\":\"0x%08x\"", cv);
            if (!have_anchor) { anchor = cv; have_anchor = 1; }
            else if (anchor != cv) all_ok = 0;
        } else if ((op == 0x09) && (int)rs == reg && (w & 0xffff) != 0) {
            int32_t d = (int16_t)(w & 0xffff);
            cls = "self_adjust";
            snprintf(extra, sizeof extra, ",\"delta\":%d", d);
            if (!have_stride) { stride = d; have_stride = 1; }
            else if (stride != d) deltas_uniform = 0;
            if (d <= 0) all_ok = 0;
        } else {
            cls = "OTHER";
            all_ok = 0;
        }
        printf("%s\n    {\"pc\":\"0x%08x\",\"word\":\"0x%08x\",\"class\":\"%s\"%s}",
               dfirst ? "" : ",", pc, w, cls, extra);
        dfirst = 0;
    }
    printf("%s],\n", dfirst ? "" : "\n   ");
    int verdict = store_ok && entry_ok && all_ok && have_anchor
                  && (!have_stride || (deltas_uniform && stride > 0));
    char anchor_json[16] = "null";
    if (have_anchor)
        snprintf(anchor_json, sizeof anchor_json, "\"0x%08x\"", anchor);
    printf("   \"definition_count\":%ld,\"anchor\":%s,"
           "\"stride\":%d,\"deltas_uniform\":%s,\n",
           n_defs, anchor_json, have_stride ? stride : 0,
           deltas_uniform ? "true" : "false");
    printf("   \"domain\":\"%s\",\n",
           verdict ? "anchor + k*stride, k >= 0 (no upper bound proved)"
                   : "NOT PROVED");
    printf("   \"verdict\":%s}", verdict ? "true" : "false");
    free(code); free(join);
}

/* ============================================================ indexdom@ ===
 * Prove an UNSIGNED interval for a register at one instruction. This is a
 * deliberately small whitelist. It is not another general value analyser:
 * every nearest reaching definition must be one of the operations below, and
 * every dependency of a composition must itself be proved by the same rules.
 *
 * A guarded `sltiu idx, IMM` is represented as a PATH-SPECIFIC reaching event
 * on the edge where the comparison is true. Treating the comparison as a
 * global hint would repeat the old region_provenance Tier-3 bug: the false edge
 * would inherit a bound it does not have. Calls are also edge events, after the
 * delay slot and before the continuation; the new proof crosses no call on an
 * ABI convention. Both rules reuse succs_of(), so definitions and guards in
 * delay slots have the same architecture-correct CFG as every other query.
 * ========================================================================== */

#define INDEXDOM_SIGNED_HI 0x80000000u

typedef struct {
    char *s;
    size_t n, cap;
} JsonBuf;

static void jb_init(JsonBuf *b)
{
    b->cap = 256;
    b->n = 0;
    b->s = malloc(b->cap);
    if (!b->s) exit(2);
    b->s[0] = 0;
}

static void jb_addf(JsonBuf *b, const char *fmt, ...)
{
    va_list ap;
    for (;;) {
        va_start(ap, fmt);
        int z = vsnprintf(b->s + b->n, b->cap - b->n, fmt, ap);
        va_end(ap);
        if (z < 0) exit(2);
        if ((size_t)z < b->cap - b->n) {
            b->n += (size_t)z;
            return;
        }
        size_t need = b->n + (size_t)z + 1;
        size_t next = b->cap;
        while (next < need) next *= 2;
        char *p = realloc(b->s, next);
        if (!p) exit(2);
        b->s = p;
        b->cap = next;
    }
}

typedef enum {
    INDEX_EVENT_DEFINITION,
    INDEX_EVENT_GUARD,
    INDEX_EVENT_CALL,
    INDEX_EVENT_LOAD_DELAY,
    INDEX_EVENT_ENTRY
} IndexEventKind;

typedef struct {
    IndexEventKind kind;
    size_t at;                         /* definition, sltiu, call, or query */
    size_t aux;                        /* branch pc for a guard */
    uint32_t imm;                      /* exclusive sltiu upper bound */
} IndexEvent;

typedef struct {
    IndexEvent *v;
    size_t n, cap;
} IndexEvents;

typedef struct {
    const uint32_t *code;
    size_t words;
    uint32_t start;
    uint8_t *reachable;
    uint8_t *active;                   /* [register][query word] recursion guard */
    int *pred_head;
    int *pred_from;
    int *pred_next;
    size_t edges;
} IndexContext;

typedef struct {
    int verdict;
    uint32_t lo, hi;
    char *json;                        /* array for a point, object for one def */
    int have_breaker;
    uint32_t breaker_pc, breaker_word;
    char breaker_reason[128];
    long event_count, definition_count, guard_count;
} IndexProof;

static void index_events_add(IndexEvents *events, IndexEvent event)
{
    for (size_t i = 0; i < events->n; i++) {
        IndexEvent *old = &events->v[i];
        if (old->kind == event.kind && old->at == event.at
            && old->aux == event.aux && old->imm == event.imm) return;
    }
    if (events->n == events->cap) {
        size_t cap = events->cap ? events->cap * 2 : 8;
        IndexEvent *p = realloc(events->v, cap * sizeof *p);
        if (!p) exit(2);
        events->v = p;
        events->cap = cap;
    }
    events->v[events->n++] = event;
}

static void index_context_init(IndexContext *ctx, const uint32_t *code,
                               size_t words, uint32_t start)
{
    memset(ctx, 0, sizeof *ctx);
    ctx->code = code;
    ctx->words = words;
    ctx->start = start;
    ctx->reachable = calloc(words ? words : 1, 1);
    ctx->active = calloc((words ? words : 1) * 32, 1);
    ctx->pred_head = malloc((words ? words : 1) * sizeof *ctx->pred_head);
    ctx->pred_from = malloc((words * 2 + 1) * sizeof *ctx->pred_from);
    ctx->pred_next = malloc((words * 2 + 1) * sizeof *ctx->pred_next);
    if (!ctx->reachable || !ctx->active || !ctx->pred_head
        || !ctx->pred_from || !ctx->pred_next) exit(2);
    for (size_t i = 0; i < words; i++) ctx->pred_head[i] = -1;
    if (!words) return;

    uint32_t *stack = malloc(words * sizeof *stack);
    if (!stack) exit(2);
    size_t sp = 0;
    ctx->reachable[0] = 1;
    stack[sp++] = 0;
    while (sp) {
        size_t i = stack[--sp];
        uint32_t out[2];
        int n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++) {
            if (!ctx->reachable[out[k]]) {
                ctx->reachable[out[k]] = 1;
                stack[sp++] = out[k];
            }
        }
    }
    free(stack);

    for (size_t i = 0; i < words; i++) {
        if (!ctx->reachable[i]) continue;
        uint32_t out[2];
        int n = succs_of(code, words, i, start, out);
        for (int k = 0; k < n; k++) {
            size_t to = out[k];
            if (!ctx->reachable[to]) continue;
            if (ctx->edges >= words * 2 + 1) exit(2);
            ctx->pred_from[ctx->edges] = (int)i;
            ctx->pred_next[ctx->edges] = ctx->pred_head[to];
            ctx->pred_head[to] = (int)ctx->edges++;
        }
    }
}

static void index_context_free(IndexContext *ctx)
{
    free(ctx->reachable);
    free(ctx->active);
    free(ctx->pred_head);
    free(ctx->pred_from);
    free(ctx->pred_next);
}

/* Can NODE be reached after a local definition of REG?  The ordinary return
 * model treats an untouched entry `$ra` as leaving the declared function
 * extent.  That model is not valid once instructions in the extent have
 * replaced `$ra`: `jr ra` can then target an interior PC and re-enter a query
 * while bypassing the definition that appeared to dominate it.  Walk the real
 * predecessor graph and reject if even one such path exists.  This is an
 * under-claiming boundary; no attempt is made to bless stack restores or to
 * recover a wanted return target from a convention. */
static int index_path_has_local_definition(const IndexContext *ctx, size_t node,
                                           int reg, size_t *definition_at)
{
    uint8_t *seen = calloc(ctx->words ? ctx->words : 1, 1);
    uint32_t *stack = malloc((ctx->words ? ctx->words : 1) * sizeof *stack);
    if (!seen || !stack) exit(2);
    size_t sp = 0;
    seen[node] = 1;
    stack[sp++] = (uint32_t)node;
    while (sp) {
        size_t at = stack[--sp];
        for (int edge = ctx->pred_head[at]; edge >= 0;
             edge = ctx->pred_next[edge]) {
            size_t pred = (size_t)ctx->pred_from[edge];
            if (def_reg(ctx->code[pred]) == reg) {
                *definition_at = pred;
                free(seen);
                free(stack);
                return 1;
            }
            if (!seen[pred]) {
                seen[pred] = 1;
                stack[sp++] = (uint32_t)pred;
            }
        }
    }
    free(seen);
    free(stack);
    return 0;
}

/* One fail-closed control-flow boundary shared by unsigned-index and exact
 * table-constant proofs.  The ordinary successor graph intentionally does not
 * invent exception returns, indirect targets, missing delay slots, or locally
 * computed `$ra` targets.  Any of those could re-enter a query after bypassing
 * the definition that appeared to dominate it, so neither proof may label its
 * reaching-definition set complete when one is reachable. */
static int index_context_fail_closed_barrier(const IndexContext *ctx,
                                             size_t *barrier,
                                             const char **barrier_reason)
{
    *barrier = ctx->words;
    *barrier_reason = NULL;
    for (size_t i = 0; i < ctx->words; i++) {
        if (!ctx->reachable[i]) continue;
        uint32_t w = ctx->code[i], op = w >> 26, fn = w & 0x3f;
        uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
        if (is_transfer(w) && i + 1 >= ctx->words) {
            *barrier = i;
            *barrier_reason =
                "control_transfer_delay_slot_outside_query_extent";
            return 1;
        }
        if (i > 0 && is_transfer(ctx->code[i - 1])) {
            for (int edge = ctx->pred_head[i]; edge >= 0;
                 edge = ctx->pred_next[edge]) {
                if ((size_t)ctx->pred_from[edge] != i - 1) {
                    *barrier = i;
                    *barrier_reason =
                        "delay_slot_word_has_ordinary_entry_not_modelled";
                    return 1;
                }
            }
        }
        if (op == 0 && (fn == 0x0c || fn == 0x0d)) {
            *barrier = i;
            *barrier_reason = fn == 0x0c
                ? "syscall_exception_transfer_not_modelled"
                : "break_exception_transfer_not_modelled";
            return 1;
        }
        if (op >= 0x10 && op <= 0x13 && rs == 0x08) {
            *barrier = i;
            *barrier_reason = "coprocessor_conditional_branch_not_modelled";
            return 1;
        }
        if (op >= 0x14 && op <= 0x17) {
            *barrier = i;
            *barrier_reason = "branch_likely_not_in_ps1_mips_i_model";
            return 1;
        }
        if (op == 0x01 && rt != 0x00 && rt != 0x01
            && rt != 0x10 && rt != 0x11) {
            *barrier = i;
            *barrier_reason = "unsupported_regimm_encoding_not_modelled";
            return 1;
        }
        if (op == 0x01 && (rt == 0x10 || rt == 0x11)) {
            *barrier = i;
            *barrier_reason = "conditional_link_call_return_not_modelled";
            return 1;
        }
        if ((op == 0x06 || op == 0x07) && rt != 0) {
            *barrier = i;
            *barrier_reason = "malformed_blez_bgtz_encoding_not_modelled";
            return 1;
        }
        if (i > 0 && is_transfer(ctx->code[i - 1]) && is_transfer(w)) {
            *barrier = i;
            *barrier_reason = "control_transfer_in_delay_slot_is_unpredictable";
            return 1;
        }
        if (op == 0 && fn == 0x08 && ((w >> 21) & 31) != 31) {
            *barrier = i;
            *barrier_reason =
                "unresolved_indirect_jump_may_enter_query_extent";
            return 1;
        }
        if (op == 0 && fn == 0x08 && ((w >> 21) & 31) == 31) {
            size_t ra_definition;
            if (index_path_has_local_definition(ctx, i, 31,
                                                &ra_definition)) {
                (void)ra_definition;
                *barrier = i;
                *barrier_reason =
                    "locally_defined_ra_indirect_target_not_modelled";
                return 1;
            }
        }
        if (op == 0 && fn == 0x09) {
            *barrier = i;
            *barrier_reason =
                "unresolved_indirect_call_or_jump_may_enter_query_extent";
            return 1;
        }
        if (op == 0x03) {
            uint32_t pc = ctx->start + (uint32_t)(i * 4);
            uint32_t target = ((pc + 4) & 0xf0000000u)
                              | ((w & 0x03ffffffu) << 2);
            if (target >= ctx->start
                && (target - ctx->start) / 4 < ctx->words) {
                *barrier = i;
                *barrier_reason = "direct_call_targets_query_extent_interior";
                return 1;
            }
        }
    }
    return 0;
}

static int cfg_fail_closed_barrier(const uint32_t *code, size_t words,
                                   uint32_t start, size_t *barrier,
                                   const char **barrier_reason)
{
    IndexContext ctx;
    index_context_init(&ctx, code, words, start);
    int found = index_context_fail_closed_barrier(
        &ctx, barrier, barrier_reason);
    index_context_free(&ctx);
    return found;
}

/* Does the edge FROM (a transfer's delay slot) TO cross a call before the
 * continuation? Direct jal/jalr always do. The link branches cross a call only
 * on their taken edge. No register-preservation convention is admitted here. */
static int index_call_edge(const IndexContext *ctx, size_t from, size_t to,
                           size_t *call_at)
{
    if (from == 0 || !is_transfer(ctx->code[from - 1])) return 0;
    size_t owner = from - 1;
    uint32_t w = ctx->code[owner], op = w >> 26;
    if (op == 0x03 || (op == 0 && (w & 0x3f) == 0x09)) {
        *call_at = owner;
        return 1;
    }
    if (op == 0x01 && (((w >> 16) & 31) == 0x10
                       || ((w >> 16) & 31) == 0x11)) {
        int32_t d = (int16_t)(w & 0xffff);
        uint32_t pc = ctx->start + (uint32_t)(owner * 4);
        uint32_t target = pc + 4 + (uint32_t)(d * 4);
        if (target >= ctx->start && (target - ctx->start) / 4 < ctx->words
            && to == (target - ctx->start) / 4) {
            *call_at = owner;
            return 1;
        }
    }
    return 0;
}

/* Recognise exactly the true (< IMM) edge of:
 *
 *   sltiu COND, REG, IMM
 *   beq/bne COND, zero, ...
 *   <delay slot that does not redefine REG>
 *
 * Anything less local is left unproved. IMM is positive and in the signed
 * non-negative half, so the reported [0, IMM-1] is also safe for the later
 * overflow-checked compositions. */
static int index_guard_edge(const IndexContext *ctx, size_t from, size_t to,
                            int reg, IndexEvent *event)
{
    if (from < 2 || !is_transfer(ctx->code[from - 1])) return 0;
    size_t branch_at = from - 1, sltiu_at = from - 2;
    uint32_t branch = ctx->code[branch_at], bop = branch >> 26;
    if (bop != 0x04 && bop != 0x05) return 0;          /* beq / bne only */
    if (is_transfer(ctx->code[from]) || def_reg(ctx->code[from]) == reg)
        return 0;                                      /* delay slot changed REG */

    uint32_t brs = (branch >> 21) & 31, brt = (branch >> 16) & 31;
    int cond = -1;
    if (brs == 0 && brt != 0) cond = (int)brt;
    if (brt == 0 && brs != 0) cond = (int)brs;
    /* If COND aliases REG, sltiu has replaced the value being bounded with
     * its boolean result.  In particular `sltiu r,r,1` reaches the true edge
     * with r==1, not with r in the claimed [0,0].  Follow the ordinary
     * reaching-definition path and reject sltiu as a non-whitelisted
     * definition instead of minting that false interval. */
    if (cond < 0 || cond == reg) return 0;

    uint32_t cmp = ctx->code[sltiu_at];
    if ((cmp >> 26) != 0x0b || (int)((cmp >> 16) & 31) != cond
        || (int)((cmp >> 21) & 31) != reg) return 0;
    /* Lexical adjacency is not execution.  A jump can enter BRANCH_AT while
     * skipping the preceding sltiu, leaving both COND and REG unconstrained.
     * Admit the guard only when the sltiu is reachable and is the sole dynamic
     * predecessor of the branch on every modelled path. */
    if (!ctx->reachable[sltiu_at]) return 0;
    int saw_sltiu_edge = 0;
    for (int edge = ctx->pred_head[branch_at]; edge >= 0;
         edge = ctx->pred_next[edge]) {
        size_t pred = (size_t)ctx->pred_from[edge];
        if (pred != sltiu_at) return 0;
        saw_sltiu_edge = 1;
    }
    if (!saw_sltiu_edge) return 0;
    uint32_t limit = (uint32_t)(int32_t)(int16_t)(cmp & 0xffff);
    if (limit == 0 || limit >= INDEXDOM_SIGNED_HI) return 0;
    /* MIPS-I result delay, over EVERY dynamic predecessor edge.  Looking only
     * at sltiu_at-1 misses the important non-linear spelling:
     *
     *     j Lcmp ; lbu REG,...     (load in the jump delay slot)
     *   Lcmp: sltiu COND,REG,IMM
     *
     * The comparison sees old REG while the later guarded use can see the
     * load.  Refuse the guard if any predecessor has a delayed GPR result and
     * let ordinary reaching-definition analysis prove or reject that result. */
    for (int edge = ctx->pred_head[sltiu_at]; edge >= 0;
         edge = ctx->pred_next[edge]) {
        size_t pred = (size_t)ctx->pred_from[edge];
        if (has_gpr_load_delay(ctx->code[pred])
            && def_reg(ctx->code[pred]) == reg) return 0;
    }

    int32_t d = (int16_t)(branch & 0xffff);
    uint32_t bpc = ctx->start + (uint32_t)(branch_at * 4);
    uint32_t taken_pc = bpc + 4 + (uint32_t)(d * 4);
    size_t fall = from + 1;
    size_t taken = ctx->words;
    if (taken_pc >= ctx->start && (taken_pc - ctx->start) / 4 < ctx->words)
        taken = (taken_pc - ctx->start) / 4;
    size_t true_edge = bop == 0x05 ? taken : fall;     /* bne takes COND != 0 */
    /* `bXX ..., +1` has the same successor whether the condition is true or
     * false.  It is not a guard: the site is reached on BOTH outcomes. */
    if (taken == fall) return 0;
    if (to != true_edge) return 0;

    *event = (IndexEvent){INDEX_EVENT_GUARD, sltiu_at, branch_at, limit};
    return 1;
}

/* Nearest reaching events at the point BEFORE USE. A definition or true guard
 * kills everything before it on that path; a call crossing and the function
 * entry are explicit rejecting events. */
static IndexEvents index_reaching_events(const IndexContext *ctx, int reg,
                                         size_t use)
{
    IndexEvents events = {0};
    uint8_t *seen = calloc(ctx->words ? ctx->words : 1, 1);
    uint32_t *stack = malloc((ctx->words ? ctx->words : 1) * sizeof *stack);
    if (!seen || !stack) exit(2);
    size_t sp = 0;
    seen[use] = 1;
    stack[sp++] = (uint32_t)use;
    while (sp) {
        size_t node = stack[--sp];
        if (node == 0) {
            index_events_add(&events,
                (IndexEvent){INDEX_EVENT_ENTRY, use, 0, 0});
            continue;
        }
        for (int edge = ctx->pred_head[node]; edge >= 0;
             edge = ctx->pred_next[edge]) {
            size_t pred = (size_t)ctx->pred_from[edge];
            size_t call_at;
            IndexEvent guard;
            if (index_call_edge(ctx, pred, node, &call_at)) {
                index_events_add(&events,
                    (IndexEvent){INDEX_EVENT_CALL, call_at, 0, 0});
                continue;
            }
            if (index_guard_edge(ctx, pred, node, reg, &guard)) {
                index_events_add(&events, guard);
                continue;
            }
            if (def_reg(ctx->code[pred]) == reg) {
                /* The query instruction is the load-delay slot when a load is
                 * its immediate dynamic predecessor. Following the old value
                 * precisely would require a latency-state CFG; rejecting this
                 * path is the deliberate under-claiming direction. A load
                 * separated by any intervening instruction is still admitted. */
                if (node == use && has_gpr_load_delay(ctx->code[pred]))
                    index_events_add(&events,
                        (IndexEvent){INDEX_EVENT_LOAD_DELAY, pred, 0, 0});
                else
                    index_events_add(&events,
                        (IndexEvent){INDEX_EVENT_DEFINITION, pred, 0, 0});
                continue;
            }
            if (!seen[pred]) {
                seen[pred] = 1;
                stack[sp++] = (uint32_t)pred;
            }
        }
    }
    free(seen);
    free(stack);
    return events;
}

static IndexProof index_prove_at(IndexContext *ctx, int reg, size_t use,
                                 int depth);

static void index_set_breaker(IndexProof *proof, uint32_t pc, uint32_t word,
                              const char *reason)
{
    proof->have_breaker = 1;
    proof->breaker_pc = pc;
    proof->breaker_word = word;
    snprintf(proof->breaker_reason, sizeof proof->breaker_reason, "%s", reason);
}

static void index_copy_breaker(IndexProof *to, const IndexProof *from,
                               uint32_t fallback_pc, uint32_t fallback_word,
                               const char *fallback_reason)
{
    if (from->have_breaker)
        index_set_breaker(to, from->breaker_pc, from->breaker_word,
                          from->breaker_reason);
    else
        index_set_breaker(to, fallback_pc, fallback_word, fallback_reason);
}

static IndexProof index_definition_proof(IndexContext *ctx, int reg, size_t at,
                                         int depth)
{
    IndexProof out = {0};
    JsonBuf json;
    jb_init(&json);
    uint32_t w = ctx->code[at], op = w >> 26, fn = w & 0x3f;
    uint32_t rs = (w >> 21) & 31, rt = (w >> 16) & 31;
    uint32_t sh = (w >> 6) & 31, imm = w & 0xffff;
    uint32_t pc = ctx->start + (uint32_t)(at * 4);
    const char *name = "not_whitelisted";

    /* Root facts whose interval does not depend on the input value. */
    if (op == 0x24 || op == 0x25) {                    /* lbu / lhu */
        name = op == 0x24 ? "lbu_zero_extend" : "lhu_zero_extend";
        out.verdict = 1;
        out.lo = 0;
        out.hi = op == 0x24 ? 0xffu : 0xffffu;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"interval\":{\"min\":%u,\"max\":%u},\"inputs\":[]}",
                pc, w, name, out.lo, out.hi);
    } else if (op == 0x0c) {                           /* andi */
        name = "andi_mask";
        out.verdict = 1;
        out.lo = 0;
        out.hi = imm;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"mask\":%u,\"interval\":{\"min\":0,\"max\":%u},"
                "\"inputs\":[]}", pc, w, name, imm, out.hi);
    } else if (op == 0 && fn == 0x02 && rs == 0) {     /* srl */
        name = "srl_zero_fill";
        out.verdict = 1;
        out.lo = 0;
        out.hi = UINT32_MAX >> sh;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"shift\":%u,\"interval\":{\"min\":0,\"max\":%u},"
                "\"inputs\":[]}", pc, w, name, sh, out.hi);
    } else if (op == 0x09 && rs == 0 && (int16_t)imm >= 0) {
        name = "non_negative_constant_addiu";
        out.verdict = 1;
        out.lo = out.hi = (uint32_t)(int16_t)imm;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"interval\":{\"min\":%u,\"max\":%u},\"inputs\":[]}",
                pc, w, name, out.lo, out.hi);
    } else if (op == 0x0d && rs == 0) {                /* ori reg,zero,imm */
        name = "non_negative_constant_ori";
        out.verdict = 1;
        out.lo = out.hi = imm;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"interval\":{\"min\":%u,\"max\":%u},\"inputs\":[]}",
                pc, w, name, out.lo, out.hi);
    } else if (op == 0x0f && (imm << 16) < INDEXDOM_SIGNED_HI) {
        name = "non_negative_constant_lui";
        out.verdict = 1;
        out.lo = out.hi = imm << 16;
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"interval\":{\"min\":%u,\"max\":%u},\"inputs\":[]}",
                pc, w, name, out.lo, out.hi);
    } else if (op == 0 && fn == 0x00 && rs == 0) {     /* sll */
        name = "sll_checked";
        IndexProof source = index_prove_at(ctx, (int)rt, at, depth + 1);
        uint64_t max = (uint64_t)source.hi << sh;
        uint64_t min = (uint64_t)source.lo << sh;
        out.verdict = source.verdict && max < INDEXDOM_SIGNED_HI;
        if (out.verdict) {
            out.lo = (uint32_t)min;
            out.hi = (uint32_t)max;
        } else {
            if (source.verdict)
                index_set_breaker(&out, pc, w,
                                  "sll_tracked_max_reaches_or_exceeds_2^31");
            else
                index_copy_breaker(&out, &source, pc, w,
                                   "sll_input_interval_not_proved");
        }
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\",\"shift\":%u,"
                "\"proved\":%s,\"inputs\":[{\"register\":\"%s\","
                "\"interval\":", pc, w, name, sh,
                out.verdict ? "true" : "false", REGNAME[rt]);
        if (source.verdict)
            jb_addf(&json, "{\"min\":%u,\"max\":%u}", source.lo, source.hi);
        else
            jb_addf(&json, "null");
        jb_addf(&json, ",\"reaching_definitions\":%s}]", source.json);
        if (out.verdict)
            jb_addf(&json, ",\"interval\":{\"min\":%u,\"max\":%u}",
                    out.lo, out.hi);
        else
            jb_addf(&json, ",\"failure\":\"%s\"", out.breaker_reason);
        jb_addf(&json, "}");
        free(source.json);
    } else if (op == 0 && fn == 0x21) {                /* addu */
        name = "addu_checked";
        IndexProof left = index_prove_at(ctx, (int)rs, at, depth + 1);
        IndexProof right = index_prove_at(ctx, (int)rt, at, depth + 1);
        uint64_t min = (uint64_t)left.lo + right.lo;
        uint64_t max = (uint64_t)left.hi + right.hi;
        out.verdict = left.verdict && right.verdict && max < INDEXDOM_SIGNED_HI;
        if (out.verdict) {
            out.lo = (uint32_t)min;
            out.hi = (uint32_t)max;
        } else {
            if (!left.verdict)
                index_copy_breaker(&out, &left, pc, w,
                                   "addu_left_input_interval_not_proved");
            else if (!right.verdict)
                index_copy_breaker(&out, &right, pc, w,
                                   "addu_right_input_interval_not_proved");
            else
                index_set_breaker(&out, pc, w,
                                  "addu_tracked_max_sum_reaches_or_exceeds_2^31");
        }
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\",\"proved\":%s,"
                "\"inputs\":[{\"register\":\"%s\",\"interval\":",
                pc, w, name, out.verdict ? "true" : "false", REGNAME[rs]);
        if (left.verdict)
            jb_addf(&json, "{\"min\":%u,\"max\":%u}", left.lo, left.hi);
        else
            jb_addf(&json, "null");
        jb_addf(&json, ",\"reaching_definitions\":%s},{\"register\":\"%s\","
                "\"interval\":", left.json, REGNAME[rt]);
        if (right.verdict)
            jb_addf(&json, "{\"min\":%u,\"max\":%u}", right.lo, right.hi);
        else
            jb_addf(&json, "null");
        jb_addf(&json, ",\"reaching_definitions\":%s}]", right.json);
        if (out.verdict)
            jb_addf(&json, ",\"interval\":{\"min\":%u,\"max\":%u}",
                    out.lo, out.hi);
        else
            jb_addf(&json, ",\"failure\":\"%s\"", out.breaker_reason);
        jb_addf(&json, "}");
        free(left.json);
        free(right.json);
    } else if (op == 0x09 && (int16_t)imm >= 0) {     /* addiu, non-negative */
        name = "addiu_non_negative_checked";
        IndexProof source = index_prove_at(ctx, (int)rs, at, depth + 1);
        uint32_t add = (uint32_t)(int16_t)imm;
        uint64_t min = (uint64_t)source.lo + add;
        uint64_t max = (uint64_t)source.hi + add;
        out.verdict = source.verdict && max < INDEXDOM_SIGNED_HI;
        if (out.verdict) {
            out.lo = (uint32_t)min;
            out.hi = (uint32_t)max;
        } else {
            if (source.verdict)
                index_set_breaker(&out, pc, w,
                                  "addiu_tracked_max_sum_reaches_or_exceeds_2^31");
            else
                index_copy_breaker(&out, &source, pc, w,
                                   "addiu_input_interval_not_proved");
        }
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\",\"addend\":%u,"
                "\"proved\":%s,\"inputs\":[{\"register\":\"%s\","
                "\"interval\":", pc, w, name, add,
                out.verdict ? "true" : "false", REGNAME[rs]);
        if (source.verdict)
            jb_addf(&json, "{\"min\":%u,\"max\":%u}", source.lo, source.hi);
        else
            jb_addf(&json, "null");
        jb_addf(&json, ",\"reaching_definitions\":%s}]", source.json);
        if (out.verdict)
            jb_addf(&json, ",\"interval\":{\"min\":%u,\"max\":%u}",
                    out.lo, out.hi);
        else
            jb_addf(&json, ",\"failure\":\"%s\"", out.breaker_reason);
        jb_addf(&json, "}");
        free(source.json);
    } else {
        const char *reason = "definition_operation_not_in_interval_whitelist";
        if (op == 0x20 || op == 0x21 || op == 0x22 || op == 0x23 || op == 0x26)
            reason = "load_is_not_unsigned_lbu_or_lhu";
        else if (op == 0x09 && (int16_t)imm < 0)
            reason = "addiu_immediate_is_negative";
        else if (op == 0 && fn == 0x20)
            reason = "signed_add_is_not_whitelisted";
        index_set_breaker(&out, pc, w, reason);
        jb_addf(&json, "{\"kind\":\"definition\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"operation\":\"%s\","
                "\"proved\":false,\"failure\":\"%s\"}",
                pc, w, name, reason);
    }
    out.json = json.s;
    (void)reg;                                         /* named by the query */
    return out;
}

static IndexProof index_prove_at(IndexContext *ctx, int reg, size_t use,
                                 int depth)
{
    IndexProof out = {0};
    JsonBuf json;
    jb_init(&json);
    jb_addf(&json, "[");
    uint32_t use_pc = ctx->start + (uint32_t)(use * 4);
    uint32_t use_word = ctx->code[use];

    if (reg == 0) {
        out.verdict = 1;
        out.lo = out.hi = 0;
        jb_addf(&json, "{\"kind\":\"architectural_zero\","
                "\"interval\":{\"min\":0,\"max\":0}}");
        jb_addf(&json, "]");
        out.json = json.s;
        return out;
    }
    if (depth > 64 || ctx->active[(size_t)reg * ctx->words + use]) {
        index_set_breaker(&out, use_pc, use_word,
                          "cyclic_reaching_definition_dependency");
        jb_addf(&json, "{\"kind\":\"cycle\",\"pc\":\"0x%08x\","
                "\"word\":\"0x%08x\",\"proved\":false,"
                "\"failure\":\"%s\"}]", use_pc, use_word,
                out.breaker_reason);
        out.json = json.s;
        return out;
    }
    ctx->active[(size_t)reg * ctx->words + use] = 1;

    IndexEvents events = index_reaching_events(ctx, reg, use);
    out.event_count = (long)events.n;
    out.lo = UINT32_MAX;
    int first = 1;
    if (!events.n) {
        index_set_breaker(&out, use_pc, use_word,
                          "no_entry_reachable_definition_or_guard");
        jb_addf(&json, "{\"kind\":\"no_reaching_event\","
                "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                "\"proved\":false,\"failure\":\"%s\"}",
                use_pc, use_word, out.breaker_reason);
        first = 0;
    }
    for (size_t i = 0; i < events.n; i++) {
        IndexEvent *event = &events.v[i];
        IndexProof one = {0};
        if (!first) jb_addf(&json, ",");
        first = 0;
        if (event->kind == INDEX_EVENT_DEFINITION) {
            out.definition_count++;
            one = index_definition_proof(ctx, reg, event->at, depth);
            jb_addf(&json, "%s", one.json);
        } else if (event->kind == INDEX_EVENT_GUARD) {
            uint32_t pc = ctx->start + (uint32_t)(event->at * 4);
            uint32_t bpc = ctx->start + (uint32_t)(event->aux * 4);
            one.verdict = 1;
            one.lo = 0;
            one.hi = event->imm - 1;
            out.guard_count++;
            jb_addf(&json, "{\"kind\":\"sltiu_true_edge_guard\","
                    "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                    "\"branch_pc\":\"0x%08x\","
                    "\"branch_word\":\"0x%08x\",\"exclusive_limit\":%u,"
                    "\"interval\":{\"min\":0,\"max\":%u}}",
                    pc, ctx->code[event->at], bpc, ctx->code[event->aux],
                    event->imm, one.hi);
        } else if (event->kind == INDEX_EVENT_CALL) {
            uint32_t pc = ctx->start + (uint32_t)(event->at * 4);
            index_set_breaker(&one, pc, ctx->code[event->at],
                              "call_crossing_not_in_interval_whitelist");
            jb_addf(&json, "{\"kind\":\"call_crossing\","
                    "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                    "\"proved\":false,\"failure\":\"%s\"}",
                    pc, ctx->code[event->at], one.breaker_reason);
        } else if (event->kind == INDEX_EVENT_LOAD_DELAY) {
            uint32_t pc = ctx->start + (uint32_t)(event->at * 4);
            index_set_breaker(&one, pc, ctx->code[event->at],
                              "load_result_not_visible_to_immediate_successor");
            jb_addf(&json, "{\"kind\":\"load_delay\","
                    "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                    "\"proved\":false,\"failure\":\"%s\"}",
                    pc, ctx->code[event->at], one.breaker_reason);
        } else {
            index_set_breaker(&one, use_pc, use_word,
                              "path_reaches_query_without_definition_or_guard");
            jb_addf(&json, "{\"kind\":\"entry_path_without_definition\","
                    "\"query_pc\":\"0x%08x\",\"query_word\":\"0x%08x\","
                    "\"proved\":false,\"failure\":\"%s\"}",
                    use_pc, use_word, one.breaker_reason);
        }
        if (one.verdict) {
            if (!out.verdict && !out.have_breaker && out.lo == UINT32_MAX) {
                out.lo = one.lo;
                out.hi = one.hi;
            } else {
                if (one.lo < out.lo) out.lo = one.lo;
                if (one.hi > out.hi) out.hi = one.hi;
            }
        } else if (!out.have_breaker && one.have_breaker) {
            index_set_breaker(&out, one.breaker_pc, one.breaker_word,
                              one.breaker_reason);
        }
        free(one.json);
    }
    jb_addf(&json, "]");
    out.verdict = events.n > 0 && !out.have_breaker;
    if (!out.verdict) out.lo = out.hi = 0;
    out.json = json.s;
    free(events.v);
    ctx->active[(size_t)reg * ctx->words + use] = 0;
    return out;
}

static IndexProof indexdom_eval(const uint32_t *code, size_t words,
                                uint32_t start, int reg, size_t use)
{
    IndexContext ctx;
    index_context_init(&ctx, code, words, start);
    IndexProof proof;
    size_t barrier = words;
    const char *barrier_reason = NULL;
    index_context_fail_closed_barrier(&ctx, &barrier, &barrier_reason);
    if (barrier_reason) {
        memset(&proof, 0, sizeof proof);
        JsonBuf json;
        jb_init(&json);
        uint32_t pc = start + (uint32_t)(barrier * 4);
        jb_addf(&json, "[{\"kind\":\"unresolved_control_transfer\","
                "\"pc\":\"0x%08x\",\"word\":\"0x%08x\","
                "\"proved\":false,\"failure\":\"%s\"}]",
                pc, code[barrier], barrier_reason);
        proof.json = json.s;
        index_set_breaker(&proof, pc, code[barrier], barrier_reason);
    } else if (use >= words || !ctx.reachable[use]) {
        memset(&proof, 0, sizeof proof);
        JsonBuf json;
        jb_init(&json);
        jb_addf(&json, "[]");
        proof.json = json.s;
        uint32_t pc = start + (uint32_t)(use * 4);
        uint32_t word = use < words ? code[use] : 0;
        index_set_breaker(&proof, pc, word, "query_site_not_entry_reachable");
    } else {
        proof = index_prove_at(&ctx, reg, use, 0);
    }
    index_context_free(&ctx);
    return proof;
}

static void run_indexdom_query(const uint8_t *img, size_t img_len,
                               uint32_t img_base, const char *image,
                               uint32_t start, uint32_t end, int reg,
                               uint32_t site_pc, int *first)
{
    size_t words = (end - start) / 4;
    size_t off0 = start - img_base;
    if (end <= start || ((end - start) & 3) || site_pc < start || site_pc >= end
        || ((site_pc - start) & 3) || off0 + words * 4 > img_len) {
        fprintf(stderr, "indexdom@ ranges invalid for %s\n", image);
        exit(2);
    }
    uint32_t *code = malloc(words * sizeof *code);
    if (!code) exit(2);
    for (size_t i = 0; i < words; i++) code[i] = le32(img + off0 + i * 4);
    size_t use = (site_pc - start) / 4;
    IndexProof proof = indexdom_eval(code, words, start, reg, use);

    printf("%s  {\"index_domain_query\":true,\"image\":\"%s\","
           "\"function\":\"0x%08x\",\"extent_end\":\"0x%08x\","
           "\"register\":\"%s\",\"site_pc\":\"0x%08x\","
           "\"site_word\":\"0x%08x\",\n",
           *first ? "" : ",\n", image, start, end, REGNAME[reg], site_pc,
           code[use]);
    *first = 0;
    printf("   \"scope\":\"all paths reachable from the declared extent entry; "
           "consumers must separately exclude external interior entries\",\n");
    printf("   \"whitelist\":[\"lbu\",\"lhu\",\"andi\",\"srl\","
           "\"sltiu_true_edge_guard\",\"non_negative_constant\","
           "\"overflow_checked_sll\",\"overflow_checked_addu\","
           "\"non_negative_overflow_checked_addiu\"],\n");
    printf("   \"reaching_event_count\":%ld,\"reaching_definition_count\":%ld,"
           "\"guard_count\":%ld,\n", proof.event_count,
           proof.definition_count, proof.guard_count);
    if (proof.verdict) {
        printf("   \"interval\":{\"min\":%u,\"max\":%u,"
               "\"min_hex\":\"0x%08x\",\"max_hex\":\"0x%08x\"},\n",
               proof.lo, proof.hi, proof.lo, proof.hi);
    } else {
        printf("   \"interval\":null,\n");
    }
    printf("   \"derivations\":%s,\n", proof.json);
    if (proof.have_breaker) {
        printf("   \"breaking_instruction\":{\"pc\":\"0x%08x\","
               "\"word\":\"0x%08x\",\"reason\":\"%s\"},\n",
               proof.breaker_pc, proof.breaker_word, proof.breaker_reason);
    } else {
        printf("   \"breaking_instruction\":null,\n");
    }
    printf("   \"all_reaching_definitions_whitelisted\":%s,"
           "\"verdict\":%s}", proof.verdict ? "true" : "false",
           proof.verdict ? "true" : "false");
    free(proof.json);
    free(code);
}

/* The image map comes from the static index, passed in as `id path va_base`
 * lines. Hardcoding a second copy of the overlay table here is how the two
 * analyses drift apart -- and a missing overlay silently narrows the scan. */
typedef struct { char id[64], path[512]; uint32_t base; Blob blob; int loaded; } Image;
static Image IMAGES[64];
static size_t N_IMAGES;

static Image *image_by_id(const char *id)
{
    for (size_t i = 0; i < N_IMAGES; i++)
        if (strcmp(IMAGES[i].id, id) == 0) {
            if (!IMAGES[i].loaded) { IMAGES[i].blob = slurp(IMAGES[i].path); IMAGES[i].loaded = 1; }
            return &IMAGES[i];
        }
    return NULL;
}

static void load_image_map(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char id[64], rel[512], base[32];
    while (fscanf(f, "%63s %511s %31s", id, rel, base) == 3) {
        if (N_IMAGES == sizeof IMAGES / sizeof IMAGES[0]) {
            fprintf(stderr, "image map too large\n"); exit(2);
        }
        Image *im = &IMAGES[N_IMAGES++];
        snprintf(im->id, sizeof im->id, "%s", id);
        snprintf(im->path, sizeof im->path, "%s", rel);
        im->base = (uint32_t)strtoul(base, NULL, 0);
    }
    fclose(f);
    if (!N_IMAGES) { fprintf(stderr, "empty image map %s\n", path); exit(2); }
}

/* Three synthetic functions that pin the properties a wrong answer here would
 * quietly break. The bypass case is the important one: a path that skips the
 * only definition must leave the site UNGOVERNED, because the register then
 * holds whatever the caller left and no local definition says anything about
 * it. Reporting it as governed would mint a bound out of nothing. */
static int self_test(void)
{
    static const uint32_t STRAIGHT[] = {
        0x3C118009,   /* lui s1, 0x8009        -- the address-materialising half */
        0x8E310748,   /* lw  s1, 0x748(s1)     -- the real definition            */
        0xAE220010,   /* sw  v0, 0x10(s1)      <- the site under scrutiny        */
        0x03E00008,   /* jr  ra                                                  */
    };
    static const uint32_t BYPASS[] = {
        0x14800003,   /* bne a0, zero, +3      -- jumps clear of both defs       */
        0x00000000,
        0x3C118009,   /* lui s1, 0x8009                                          */
        0x8E310748,   /* lw  s1, 0x748(s1)                                       */
        0xAE220010,   /* sw  v0, 0x10(s1)      <- reachable with s1 undefined    */
        0x03E00008,
    };
    static const uint32_t DEADTAIL[] = {
        0x3C118009,   /* lui s1, 0x8009                                          */
        0x8E310748,   /* lw  s1, 0x748(s1)                                       */
        0xAE220010,   /* sw  v0, 0x10(s1)      <- the site                       */
        0x8FB1004C,   /* lw  s1, 0x4c(sp)      -- epilogue restore, reaches none */
        0x03E00008,
    };
    struct {
        const char *name; const uint32_t *w; size_t n; size_t target;
        int want_uniform; long want_ungoverned, want_dead; int bindable;
    } cases[] = {
        /* `bindable` is what the compiler actually requires: uniform AND
         * governed. The bypass case is uniform too -- its definitions really do
         * agree -- which is exactly why uniformity alone must never be enough. */
        { "definition dominates the site",       STRAIGHT, 4, 2, 1, 0, 1, 1 },
        { "branch bypasses the only definition", BYPASS,   6, 4, 1, 1, 1, 0 },
        { "epilogue restore reaches no site",    DEADTAIL, 5, 2, 1, 0, 2, 1 },
    };
    const uint32_t BASE = 0x80010000u;
    int bad = 0;
    FILE *devnull = fopen("/dev/null", "w");
    for (size_t c = 0; c < sizeof cases / sizeof cases[0]; c++) {
        uint32_t target = BASE + (uint32_t)(cases[c].target * 4);
        QueryResult r = {0};
        int first = 1;
        FILE *saved = stdout;
        if (devnull) stdout = devnull;
        run_query((const uint8_t *)cases[c].w, cases[c].n * 4, BASE, 0, "SELFTEST",
                  BASE, BASE + (uint32_t)(cases[c].n * 4), 17 /* s1 */,
                  &target, 1, 0, 0, &first, &r);
        stdout = saved;
        int bindable = r.uniform && r.ungoverned == 0;
        int ok = r.uniform == cases[c].want_uniform
              && r.ungoverned == cases[c].want_ungoverned
              && r.dead == cases[c].want_dead
              && r.targeted == 1
              && bindable == cases[c].bindable;
        if (cases[c].want_uniform && (!r.have_from || r.from != 0x80090748u)) ok = 0;
        printf("%-38s %s (uniform=%d ungoverned=%ld dead=%ld bindable=%d)\n",
               cases[c].name, ok ? "ok" : "FAIL", r.uniform, r.ungoverned,
               r.dead, bindable);
        if (!ok) bad = 1;
    }

    /* The table constant is a separate proof obligation from the unsigned
     * index.  Pin both directions here: a dominating LUI remains useful, while
     * a branch that lands on the forming ADDU cannot lend that ADDU the LUI
     * from the other path. */
    static const uint32_t TABLE_BASE_SAFE[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x3c098009,   /* lui  t1,0x8009   */
        0x01285021,   /* addu t2,t1,t0    */
        0xad420000,   /* sw   v0,0(t2)    */
        0x03e00008, 0x00000000,
    };
    static const uint32_t TABLE_BASE_JOIN_BYPASS[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x14800002,   /* bne  a0,zero,join */
        0x00000000,   /* delay slot */
        0x3c098009,   /* lui  t1,0x8009 -- fallthrough only */
        0x01285021,   /* join: addu t2,t1,t0 */
        0xad420000,   /* sw   v0,0(t2) */
        0x03e00008, 0x00000000,
    };
    static const uint32_t TABLE_BASE_GP_ENTRY[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x03885021,   /* addu t2,gp,t0 -- pinned entry gp */
        0xad420000,   /* sw   v0,0(t2) */
        0x03e00008, 0x00000000,
    };
    static const uint32_t TABLE_BASE_GP_REDEFINED[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x0080e021,   /* addu gp,a0,zero -- caller value, not pinned gp */
        0x03885021,   /* addu t2,gp,t0 */
        0xad420000,   /* sw   v0,0(t2) */
        0x03e00008, 0x00000000,
    };
    static const uint32_t TABLE_BASE_TRUNCATED_JUMP[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x3c098009,   /* lui  t1,0x8009 */
        0x01285021,   /* addu t2,t1,t0 */
        0xad420000,   /* sw   v0,0(t2) */
        0x08004004,   /* j    0x80010010 -- missing delay slot */
    };
    static const uint32_t TABLE_BASE_UNRESOLVED_JR[] = {
        0x30a8003f,   /* andi t0,a1,0x3f */
        0x3c098009,   /* lui  t1,0x8009 */
        0x01285021,   /* addu t2,t1,t0 */
        0xad420000,   /* sw   v0,0(t2) */
        0x01600008,   /* jr   t3 -- target may enter the extent */
        0x00000000,
    };
    static const uint32_t TABLE_BASE_ORI_OVERLAP[] = {
        0x3c098008,   /* lui  t1,0x8008 */
        0x352923a0,   /* ori  t1,t1,0x23a0 -> 0x800823a0 */
        0x35292000,   /* ori  t1,t1,0x2000 -> unchanged, NOT +0x2000 */
        0x30880000,   /* andi t0,a0,0 -> exact zero index */
        0x01285021,   /* addu t2,t1,t0 */
        0xad420000,   /* sw   v0,0(t2) */
    };
    static const uint32_t TABLE_BASE_CALL_DELAY_CLOBBER[] = {
        0x0c008000,   /* jal  0x80020000 */
        0x3c098009,   /* delay: lui t1,0x8009; callee may clobber t1 */
        0x3088003f,   /* andi t0,a0,0x3f */
        0x01285021,   /* addu t2,t1,t0 */
        0xad420000,   /* sw   v0,0(t2) */
        0x0800c000,   /* j    0x80030000 */
        0x00000000,
    };
    struct {
        const char *name;
        const uint32_t *w;
        size_t n, at;
        int want_status;
        uint32_t want_table;
        const char *want_constant, *want_index;
        size_t want_failure_at;
        const char *want_failure_reason;
    } table_cases[] = {
        { "dominating table base accepted", TABLE_BASE_SAFE, 6, 2, 1,
          0x80090000u, "t1", "t0", 0, NULL },
        { "table base join bypass rejected", TABLE_BASE_JOIN_BYPASS, 8, 4, -1,
          0, NULL, NULL, 4, "table_base_operand_not_path_invariant" },
        { "entry gp table base accepted", TABLE_BASE_GP_ENTRY, 5, 1, 1,
          GP_VALUE, "gp", "t0", 0, NULL },
        { "locally redefined gp rejected", TABLE_BASE_GP_REDEFINED, 6, 2, -1,
          0, NULL, NULL, 2, "table_base_operand_not_path_invariant" },
        { "truncated jump table base rejected", TABLE_BASE_TRUNCATED_JUMP, 5, 2, -1,
          0, NULL, NULL, 4,
          "control_transfer_delay_slot_outside_query_extent" },
        { "unresolved jr table base rejected", TABLE_BASE_UNRESOLVED_JR, 6, 2, -1,
          0, NULL, NULL, 4,
          "unresolved_indirect_jump_may_enter_query_extent" },
        { "overlapping ori uses bitwise value", TABLE_BASE_ORI_OVERLAP, 6, 4, 1,
          0x800823a0u, "t1", "t0", 0, NULL },
        { "call-delay constant clobber rejected",
          TABLE_BASE_CALL_DELAY_CLOBBER, 7, 3, -1,
          0, NULL, NULL, 0,
          "call_delay_definition_clobbered_before_continuation" },
    };
    for (size_t c = 0; c < sizeof table_cases / sizeof table_cases[0]; c++) {
        uint8_t *joins = calloc(table_cases[c].n, 1);
        if (!joins) exit(2);
        for (size_t i = 0; i < table_cases[c].n; i++) {
            uint32_t successors[2];
            int n = succs_of(table_cases[c].w, table_cases[c].n, i, BASE,
                             successors);
            for (int s = 0; s < n; s++)
                if (successors[s] != i + 1) joins[successors[s]] = 1;
            if (n == 0 && i + 1 < table_cases[c].n) joins[i + 1] = 1;
        }
        uint32_t table = 0;
        const char *index = "", *constant = "";
        size_t failure_at = table_cases[c].n;
        const char *failure_reason = NULL;
        int status = table_add_definition(
            table_cases[c].w, joins, table_cases[c].n, BASE,
            table_cases[c].at, &table, &index, &constant,
            &failure_at, &failure_reason);
        int ok = status == table_cases[c].want_status;
        if (status == 1)
            ok = ok && table == table_cases[c].want_table
                    && strcmp(index, table_cases[c].want_index) == 0
                    && strcmp(constant, table_cases[c].want_constant) == 0;
        if (status < 0)
            ok = ok && failure_at == table_cases[c].want_failure_at
                    && failure_reason != NULL
                    && strcmp(failure_reason,
                              table_cases[c].want_failure_reason) == 0;
        printf("%-38s %s (status=%d", table_cases[c].name,
               ok ? "ok" : "FAIL", status);
        if (status == 1)
            printf(" table=0x%08x constant=%s index=%s", table, constant, index);
        if (status < 0)
            printf(" breaker=0x%08x/0x%08x reason=%s",
                   (unsigned)(BASE + (uint32_t)failure_at * 4),
                   table_cases[c].w[failure_at], failure_reason);
        printf(")\n");
        if (!ok) bad = 1;
        free(joins);
    }

    /* The same physical delay slot has two different temporal meanings.  Its
     * value is visible to the callee as an argument, while a caller-saved value
     * is not assumed to survive to the continuation.  Keep both halves pinned:
     * TABLE_BASE_CALL_DELAY_CLOBBER above is the continuation rejection; this
     * is the call-boundary acceptance. */
    static const uint32_t CALL_DELAY_ARGUMENT[] = {
        0x3c10800a,   /* lui   s0,0x800a */
        0x26106590,   /* addiu s0,s0,0x6590 -> 0x800a6590 */
        0x0c008000,   /* jal   0x80020000 */
        0x2604ff70,   /* delay: addiu a0,s0,-0x90 -> 0x800a6500 */
        0x0800c000,   /* continuation leaves the extent */
        0x00000000,
    };
    {
        size_t n_words = sizeof CALL_DELAY_ARGUMENT / sizeof CALL_DELAY_ARGUMENT[0];
        uint8_t *joins = calloc(n_words, 1);
        if (!joins) exit(2);
        for (size_t i = 0; i < n_words; i++) {
            uint32_t successors[2];
            int n = succs_of(CALL_DELAY_ARGUMENT, n_words, i, BASE,
                             successors);
            for (int s = 0; s < n; s++)
                if (successors[s] != i + 1) joins[successors[s]] = 1;
            if (n == 0 && i + 1 < n_words) joins[i + 1] = 1;
        }
        uint32_t value = 0;
        int ok = call_delay_argument_constant(
            CALL_DELAY_ARGUMENT, joins, n_words, BASE, 2, 4, &value)
            && value == 0x800a6500u;
        printf("%-38s %s (value=0x%08x)\n",
               "call-delay argument boundary accepted",
               ok ? "ok" : "FAIL", value);
        if (!ok) bad = 1;
        free(joins);
    }

    /* Calls write their link before the delay slot.  The link may therefore
     * neither be read as a stale source for a delay-slot argument nor be
     * suppressed when the boundary query asks for the link register itself.
     * JALR makes the link destination arbitrary, so pin both spellings. */
    static const uint32_t CALL_DELAY_JAL_LINK_SOURCE[] = {
        0x3c1f8009,   /* stale pre-call: lui ra,0x8009 */
        0x0c008000,   /* jal   0x80020000 -- writes ra */
        0x27e40000,   /* delay: addiu a0,ra,0 -- reads the NEW link */
        0x0800c000, 0x00000000,
    };
    static const uint32_t CALL_DELAY_JALR_LINK_SOURCE[] = {
        0x3c108009,   /* stale pre-call: lui s0,0x8009 */
        0x3c198002,   /* lui   t9,0x8002 */
        0x03208009,   /* jalr  s0,t9 -- writes the link to s0 */
        0x26040000,   /* delay: addiu a0,s0,0 -- reads the NEW link */
        0x0800c000, 0x00000000,
    };
    static const uint32_t CALL_DELAY_REENTRY_SOURCE[] = {
        0x3c108009,   /* lui   s0,0x8009 */
        0x0c008000,   /* jal   0x80020000 */
        0x26040000,   /* delay: addiu a0,s0,0 */
        0x08004001,   /* continuation loops to this same jal */
        0x00000000,
    };
    static const uint32_t CALL_DELAY_REENTRY_DIRECT[] = {
        0x0c008000,   /* jal   0x80020000 */
        0x3c048009,   /* delay: lui a0,0x8009 -- invocation-independent */
        0x08004000,   /* continuation loops to this same jal */
        0x00000000,
    };
    struct {
        const char *name;
        const uint32_t *w;
        size_t n, call_at;
        int want;
        uint32_t want_value;
    } call_boundary_cases[] = {
        { "jal link source rejected", CALL_DELAY_JAL_LINK_SOURCE, 5, 1,
          0, 0 },
        { "jalr link source rejected", CALL_DELAY_JALR_LINK_SOURCE, 6, 2,
          0, 0 },
        { "call-boundary re-entry rejected", CALL_DELAY_REENTRY_SOURCE, 5, 1,
          0, 0 },
        { "re-entrant direct lui accepted", CALL_DELAY_REENTRY_DIRECT, 4, 0,
          1, 0x80090000u },
    };
    for (size_t c = 0;
         c < sizeof call_boundary_cases / sizeof call_boundary_cases[0]; c++) {
        uint8_t *joins = calloc(call_boundary_cases[c].n, 1);
        if (!joins) exit(2);
        for (size_t i = 0; i < call_boundary_cases[c].n; i++) {
            uint32_t successors[2];
            int n = succs_of(call_boundary_cases[c].w,
                             call_boundary_cases[c].n, i, BASE, successors);
            for (int s = 0; s < n; s++)
                if (successors[s] != i + 1) joins[successors[s]] = 1;
            if (n == 0 && i + 1 < call_boundary_cases[c].n)
                joins[i + 1] = 1;
        }
        uint32_t value = 0;
        int got = call_delay_argument_constant(
            call_boundary_cases[c].w, joins, call_boundary_cases[c].n,
            BASE, call_boundary_cases[c].call_at, 4, &value);
        int ok = got == call_boundary_cases[c].want
              && (!got || value == call_boundary_cases[c].want_value);
        printf("%-38s %s (accepted=%d", call_boundary_cases[c].name,
               ok ? "ok" : "FAIL", got);
        if (got) printf(" value=0x%08x", value);
        printf(")\n");
        if (!ok) bad = 1;
        free(joins);
    }
    {
        int ok = call_boundary_suppresses_definition(0x0c008000, 4)
              && !call_boundary_suppresses_definition(0x0c008000, 31)
              && !call_boundary_suppresses_definition(0x03208009, 16)
              && call_boundary_suppresses_definition(0x03208009, 4);
        printf("%-38s %s\n", "call link definition preserved",
               ok ? "ok" : "FAIL");
        if (!ok) bad = 1;
    }

    /* indexdom@ controls. These are instruction words, not mocked analysis
     * answers: each case runs the same CFG/event/derivation engine as a real
     * image query. The negative controls pin both the work-order cases and the
     * architecture counterexamples found by detached review. */
    static const uint32_t MASKED_INDEX[] = {
        0x3088003f,   /* andi  t0, a0, 0x3f */
        0x00084080,   /* sll   t0, t0, 2    */
        0xad020000,   /* sw    v0, 0(t0)    */
        0x03e00008, 0x00000000,
    };
    static const uint32_t GUARDED_INDEX[] = {
        0x2c890010,   /* sltiu t1, a0, 16   */
        0x11200002,   /* beq   t1, zero, out */
        0x00000000,   /* delay slot          */
        0xac820000,   /* sw    v0, 0(a0)     -- true (<16) edge only */
        0x03e00008, 0x00000000,
    };
    static const uint32_t SIGNED_LOAD[] = {
        0x84880000,   /* lh    t0, 0(a0)     */
        0x00000000,   /* load-delay slot      */
        0xad020000,   /* sw    v0, 0(t0)     */
        0x03e00008, 0x00000000,
    };
    static const uint32_t ADDU_OVERFLOW[] = {
        0x00044042,   /* srl   t0, a0, 1     -- [0,0x7fffffff] */
        0x24090001,   /* addiu t1, zero, 1   */
        0x01095021,   /* addu  t2, t0, t1    -- max == 2^31, reject */
        0xad420000,   /* sw    v0, 0(t2)     */
        0x03e00008, 0x00000000,
    };
    static const uint32_t BYPASS_INDEX[] = {
        0x14800002,   /* bne   a0, zero, site -- bypasses the only def */
        0x00000000,
        0x30a8003f,   /* andi  t0, a1, 0x3f */
        0xad020000,   /* site: sw v0, 0(t0)  */
        0x03e00008, 0x00000000,
    };
    static const uint32_t UNGUARDED_ADDU[] = {
        0x00854021,   /* addu  t0, a0, a1 -- neither input bounded */
        0xad020000,   /* sw    v0, 0(t0) */
        0x03e00008, 0x00000000,
    };
    static const uint32_t CONVERGED_GUARD[] = {
        0x2c890010,   /* sltiu t1, a0, 16 */
        0x11200001,   /* beq t1, zero, +1 -- taken == fall-through */
        0x00000000,
        0xac820000,   /* reached whether a0 < 16 or not */
        0x03e00008, 0x00000000,
    };
    static const uint32_t INDIRECT_ENTRY[] = {
        0x3088003f,   /* andi t0, a0, 0x3f */
        0x01200008,   /* jr t1 -- its unknown target may be the site */
        0x00000000,
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t SCHEDULED_LBU[] = {
        0x90880000,   /* lbu t0, 0(a0) */
        0x00000000,   /* independent load-delay instruction */
        0x00084080,   /* sll t0, t0, 2 */
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t IMMEDIATE_LBU[] = {
        0x90880000,   /* lbu t0, 0(a0) */
        0x00084080,   /* consumes old t0 in the load-delay slot */
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t LOAD_THEN_GUARD[] = {
        0x84a40000,   /* lh a0, 0(a1) -- not visible to the comparison */
        0x2c890010,   /* sltiu t1, a0, 16 reads old a0 */
        0x11200004,   /* beq t1, zero, out */
        0x00000000,
        0xac820000,   /* current a0 is the signed load, not guarded old a0 */
        0x03e00008, 0x00000000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t ALIASED_GUARD_DEST[] = {
        0x2c840001,   /* sltiu a0, a0, 1 -- true edge carries a0==1 */
        0x10800004,   /* beq a0, zero, out */
        0x00000000,
        0xac820000,   /* site is reached with a0==1, never [0,0] */
        0x08004008,   /* j done */
        0x00000000,
        0x03e00008, 0x00000000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t NONLINEAR_LOAD_GUARD[] = {
        0x08004003,   /* j Lcmp */
        0x84a40000,   /* lh a0,0(a1) in delay slot: result is delayed */
        0x00000000,
        0x2c890010,   /* Lcmp: sltiu reads old a0 */
        0x11200004,   /* beq t1,zero,out */
        0x00000000,
        0xac820000,   /* current a0 can be the signed load */
        0x03e00008, 0x00000000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t COP_MOVE_GUARD[] = {
        0x48040000,   /* mfc2 a0,c2d0 -- delayed GPR result */
        0x2c890010,   /* sltiu reads old a0 */
        0x11200004,   /* beq t1,zero,out */
        0x00000000,
        0xac820000,
        0x03e00008, 0x00000000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t SYSCALL_BARRIER[] = {
        0x3088003f,   /* andi t0,a0,0x3f */
        0x0000000c,   /* syscall: exception target is not fall-through */
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t BREAK_BARRIER[] = {
        0x3088003f,
        0x0000000d,   /* break: exception target is not fall-through */
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t COP_BRANCH_BARRIER[] = {
        0x3088003f,
        0x49010001,   /* bc2t +1: COP condition/edge is not modelled */
        0x00000000,
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t REGIMM_LINK_BARRIER[] = {
        0x3088003f,
        0x04110001,   /* bgezal zero,+1: taken call can return to continuation */
        0x00000000,
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t TRANSFER_IN_DELAY[] = {
        0x08004003,   /* j outer_target */
        0x08004004,   /* j in delay slot: architecturally unpredictable */
        0x00000000,
        0x3088003f,
        0xad020000,
        0x03e00008, 0x00000000,
    };
    static const uint32_t DEAD_LEXICAL_GUARD[] = {
        0x08004003,   /* j branch: skip the lexical sltiu */
        0x00000000,
        0x2c890010,   /* dead: sltiu t1,a0,16 */
        0x15200003,   /* branch: bne t1,zero,site */
        0x00000000,
        0x03e00008, 0x00000000,
        0xac820000,   /* site can read unknown a0 */
        0x03e00008, 0x00000000,
    };
    static const uint32_t DUAL_CONTEXT_DELAY_SLOT[] = {
        0x08004005,   /* j branch */
        0x00000000,   /* slot_target: delay slot OR ordinary branch target */
        0xad020000,   /* site reads t0 */
        0x08004040, 0x00000000,
        0x1480fffb,   /* branch: bne a0,zero,slot_target */
        0x00000000,
        0x30a8003f,   /* only the not-taken path defines t0 */
        0x08004002, 0x00000000,
    };
    static const uint32_t LOCALLY_DEFINED_RA_REENTRY[] = {
        0x3c1f8001,   /* lui ra,0x8001 */
        0x37ff0028,   /* ori ra,ra,0x28 -- exact query PC */
        0x14800004,   /* bne a0,zero,Lreturn */
        0x00000000,
        0x30c8003f,   /* andi t0,a2,0x3f -- only the direct query path */
        0x0800400a,   /* j query */
        0x00000000,
        0x03e00008,   /* Lreturn: jr ra -- actually re-enters query */
        0x00000000,
        0x00000000,
        0xad020000,   /* query: reachable with t0 undefined */
        0x03e00008, 0x00000000,
    };
    static const uint32_t DIRECT_TRANSFER_WITH_TRUNCATED_DELAY[] = {
        0x3088003f,   /* andi t0,a0,0x3f -- tempting but not exhaustive */
        0xad020000,   /* query */
        0x84a80000,   /* signed lh reaches query after re-entry */
        0x08004001,   /* j query -- declared extent ends before its slot */
        0x00000000,   /* image-resident delay slot, outside query extent */
    };
    static const uint32_t BRANCH_WITH_TRUNCATED_DELAY[] = {
        0x3088003f,   /* andi t0,a0,0x3f -- tempting but not exhaustive */
        0xad020000,   /* query */
        0x84a80000,   /* signed lh reaches query after re-entry */
        0x1000fffd,   /* b query -- declared extent ends before its slot */
        0x00000000,   /* image-resident delay slot, outside query extent */
    };
    struct {
        const char *name;
        const uint32_t *w;
        size_t n, target;
        int reg, want_verdict;
        uint32_t want_lo, want_hi, want_break_word;
        const char *json_must_contain;
    } index_cases[] = {
        { "masked index interval", MASKED_INDEX, 5, 2, 8, 1,
          0, 252, 0, "sll_checked" },
        { "sltiu true-edge interval", GUARDED_INDEX, 6, 3, 4, 1,
          0, 15, 0, "sltiu_true_edge_guard" },
        { "signed load rejected", SIGNED_LOAD, 5, 2, 8, 0,
          0, 0, 0x84880000, "load_is_not_unsigned_lbu_or_lhu" },
        { "addu overflow rejected", ADDU_OVERFLOW, 6, 3, 10, 0,
          0, 0, 0x01095021, "addu_tracked_max_sum_reaches_or_exceeds_2^31" },
        { "definition-bypass path rejected", BYPASS_INDEX, 6, 3, 8, 0,
          0, 0, 0xad020000, "entry_path_without_definition" },
        { "unguarded addu rejected", UNGUARDED_ADDU, 4, 1, 8, 0,
          0, 0, 0x00854021, "path_reaches_query_without_definition_or_guard" },
        { "converged guard rejected", CONVERGED_GUARD, 6, 3, 4, 0,
          0, 0, 0xac820000, "entry_path_without_definition" },
        { "indirect interior entry rejected", INDIRECT_ENTRY, 6, 3, 8, 0,
          0, 0, 0x01200008, "unresolved_indirect_jump" },
        { "scheduled lbu interval", SCHEDULED_LBU, 6, 3, 8, 1,
          0, 1020, 0, "lbu_zero_extend" },
        { "immediate lbu consumer rejected", IMMEDIATE_LBU, 5, 2, 8, 0,
          0, 0, 0x90880000, "load_result_not_visible_to_immediate_successor" },
        { "load-before-guard rejected", LOAD_THEN_GUARD, 9, 4, 4, 0,
          0, 0, 0x84a40000, "load_is_not_unsigned_lbu_or_lhu" },
        { "aliased sltiu destination rejected", ALIASED_GUARD_DEST, 10, 3, 4, 0,
          0, 0, 0x2c840001, "definition_operation_not_in_interval_whitelist" },
        { "nonlinear load-before-guard rejected", NONLINEAR_LOAD_GUARD, 11, 6, 4, 0,
          0, 0, 0x84a40000, "load_is_not_unsigned_lbu_or_lhu" },
        { "cop move-before-guard rejected", COP_MOVE_GUARD, 9, 4, 4, 0,
          0, 0, 0x48040000, "definition_operation_not_in_interval_whitelist" },
        { "syscall transfer rejected", SYSCALL_BARRIER, 5, 2, 8, 0,
          0, 0, 0x0000000c, "syscall_exception_transfer_not_modelled" },
        { "break transfer rejected", BREAK_BARRIER, 5, 2, 8, 0,
          0, 0, 0x0000000d, "break_exception_transfer_not_modelled" },
        { "cop branch transfer rejected", COP_BRANCH_BARRIER, 6, 3, 8, 0,
          0, 0, 0x49010001, "coprocessor_conditional_branch_not_modelled" },
        { "regimm link return rejected", REGIMM_LINK_BARRIER, 6, 3, 8, 0,
          0, 0, 0x04110001, "conditional_link_call_return_not_modelled" },
        { "transfer in delay slot rejected", TRANSFER_IN_DELAY, 6, 4, 8, 0,
          0, 0, 0x08004004, "control_transfer_in_delay_slot_is_unpredictable" },
        { "dead lexical sltiu guard rejected", DEAD_LEXICAL_GUARD, 10, 7, 4, 0,
          0, 0, 0xac820000, "path_reaches_query_without_definition_or_guard" },
        { "dual-context delay slot rejected", DUAL_CONTEXT_DELAY_SLOT, 10, 2, 8, 0,
          0, 0, 0x00000000,
          "delay_slot_word_has_ordinary_entry_not_modelled" },
        { "locally-defined ra re-entry rejected", LOCALLY_DEFINED_RA_REENTRY,
          13, 10, 8, 0, 0, 0, 0x03e00008,
          "locally_defined_ra_indirect_target_not_modelled" },
        { "direct transfer missing delay rejected",
          DIRECT_TRANSFER_WITH_TRUNCATED_DELAY,
          4, 1, 8, 0, 0, 0, 0x08004001,
          "control_transfer_delay_slot_outside_query_extent" },
        { "branch missing delay rejected", BRANCH_WITH_TRUNCATED_DELAY,
          4, 1, 8, 0, 0, 0, 0x1000fffd,
          "control_transfer_delay_slot_outside_query_extent" },
    };
    for (size_t c = 0; c < sizeof index_cases / sizeof index_cases[0]; c++) {
        IndexProof p = indexdom_eval(index_cases[c].w, index_cases[c].n,
                                     BASE, index_cases[c].reg,
                                     index_cases[c].target);
        int ok = p.verdict == index_cases[c].want_verdict;
        if (p.verdict)
            ok = ok && p.lo == index_cases[c].want_lo
                    && p.hi == index_cases[c].want_hi;
        else
            ok = ok && p.have_breaker
                    && p.breaker_word == index_cases[c].want_break_word;
        ok = ok && strstr(p.json, index_cases[c].json_must_contain) != NULL;
        printf("%-38s %s", index_cases[c].name, ok ? "ok" : "FAIL");
        if (p.verdict)
            printf(" (interval=[%u,%u])\n", p.lo, p.hi);
        else
            printf(" (breaker=0x%08x reason=%s)\n",
                   p.breaker_word, p.breaker_reason);
        if (!ok) bad = 1;
        free(p.json);
    }
    if (devnull) fclose(devnull);
    return bad;
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    if (argc < 3) {
        fprintf(stderr, "usage: %s <image_map> IMAGE:START:END:REG[:PCS] | "
                        "writers@IMAGE:ADDR | indexdom@IMAGE:START:END:REG:PC ...\n",
                        argv[0]);
        return 2;
    }
    load_image_map(argv[1]);

    printf("{\n \"tool\": \"phase4_typed_state_provenance\",\n");
    printf(" \"question\": \"What defines this base register inside this function, "
           "and does any use escape every definition?\",\n");
    printf(" \"queries\": [\n");
    int first = 1;
    for (int a = 2; a < argc; a++) {
        char spec[4096]; snprintf(spec, sizeof spec, "%s", argv[a]);
        if (strncmp(spec, "writers@", 8) == 0) {
            char *im = strtok(spec + 8, ":"), *ad = strtok(NULL, ":");
            if (!im || !ad) { fprintf(stderr, "bad writers query %s\n", argv[a]); return 2; }
            uint32_t table = (uint32_t)strtoul(ad, NULL, 0);
            Image *g = image_by_id(im);
            if (!g) { fprintf(stderr, "unknown image %s\n", im); return 2; }
            scan_table_writers(g->blob.p, g->blob.n, g->base, 0, im, table, &first);
            continue;
        }
        if (strncmp(spec, "indexdom@", 9) == 0) {
            char *im = strtok(spec + 9, ":"), *s = strtok(NULL, ":"),
                 *e = strtok(NULL, ":"), *rg = strtok(NULL, ":"),
                 *pc = strtok(NULL, ":");
            if (!im || !s || !e || !rg || !pc) {
                fprintf(stderr, "bad indexdom query %s\n", argv[a]); return 2;
            }
            int reg = reg_of(rg);
            if (reg < 0) { fprintf(stderr, "unknown register %s\n", rg); return 2; }
            Image *g = image_by_id(im);
            if (!g) { fprintf(stderr, "unknown image %s\n", im); return 2; }
            run_indexdom_query(g->blob.p, g->blob.n, g->base, im,
                               (uint32_t)strtoul(s, NULL, 0),
                               (uint32_t)strtoul(e, NULL, 0), reg,
                               (uint32_t)strtoul(pc, NULL, 0), &first);
            continue;
        }
        if (strncmp(spec, "progression@", 12) == 0) {
            char *im = strtok(spec + 12, ":"), *s = strtok(NULL, ":"),
                 *e = strtok(NULL, ":"), *rg = strtok(NULL, ":"),
                 *pc = strtok(NULL, ":");
            if (!im || !s || !e || !rg || !pc) {
                fprintf(stderr, "bad progression query %s\n", argv[a]); return 2;
            }
            int reg = reg_of(rg);
            if (reg < 0) { fprintf(stderr, "unknown register %s\n", rg); return 2; }
            Image *g = image_by_id(im);
            if (!g) { fprintf(stderr, "unknown image %s\n", im); return 2; }
            run_progression_query(g->blob.p, g->blob.n, g->base, im,
                                  (uint32_t)strtoul(s, NULL, 0),
                                  (uint32_t)strtoul(e, NULL, 0), reg,
                                  (uint32_t)strtoul(pc, NULL, 0), &first);
            continue;
        }
        if (strncmp(spec, "island@", 7) == 0) {
            char *im = strtok(spec + 7, ":"), *cl = strtok(NULL, ":"),
                 *ch = strtok(NULL, ":"), *il = strtok(NULL, ":"),
                 *ih = strtok(NULL, ":"), *rg = strtok(NULL, ":"),
                 *cp = strtok(NULL, ":");
            if (!im || !cl || !ch || !il || !ih || !rg || !cp) {
                fprintf(stderr, "bad island query %s\n", argv[a]); return 2;
            }
            int reg = reg_of(rg);
            if (reg < 0) { fprintf(stderr, "unknown register %s\n", rg); return 2; }
            uint32_t calls[64]; size_t n_calls = 0;
            for (char *t = strtok(cp, ","); t; t = strtok(NULL, ",")) {
                if (n_calls == sizeof calls / sizeof calls[0]) {
                    fprintf(stderr, "too many call pcs in %s\n", argv[a]); return 2;
                }
                calls[n_calls++] = (uint32_t)strtoul(t, NULL, 0);
            }
            Image *g = image_by_id(im);
            if (!g) { fprintf(stderr, "unknown image %s\n", im); return 2; }
            run_island_query(g->blob.p, g->blob.n, g->base, im,
                             (uint32_t)strtoul(cl, NULL, 0), (uint32_t)strtoul(ch, NULL, 0),
                             (uint32_t)strtoul(il, NULL, 0), (uint32_t)strtoul(ih, NULL, 0),
                             reg, calls, n_calls, &first);
            continue;
        }
        int use_returns = 0, any_target = 0;
        char *body = spec;
        if (strncmp(spec, "returns@", 8) == 0) { use_returns = 1; body = spec + 8; }
        else if (strncmp(spec, "defsat@", 7) == 0) { any_target = 1; body = spec + 7; }
        char *image = strtok(body, ":"), *s = strtok(NULL, ":"),
             *e = strtok(NULL, ":"), *r = use_returns ? NULL : strtok(NULL, ":"),
             *pcs = use_returns ? NULL : strtok(NULL, ":");
        if (use_returns) r = (char *)"v0";
        if (!image || !s || !e || !r) { fprintf(stderr, "bad query %s\n", argv[a]); return 2; }
        int reg = reg_of(r);
        if (reg < 0) { fprintf(stderr, "unknown register %s\n", r); return 2; }
        uint32_t start = (uint32_t)strtoul(s, NULL, 0), end = (uint32_t)strtoul(e, NULL, 0);
        if (end <= start) { fprintf(stderr, "empty extent in %s\n", argv[a]); return 2; }
        uint32_t targets[512]; size_t n_targets = 0;
        for (char *t = pcs ? strtok(pcs, ",") : NULL; t; t = strtok(NULL, ",")) {
            if (n_targets == sizeof targets / sizeof targets[0]) {
                fprintf(stderr, "too many target pcs in %s\n", argv[a]); return 2;
            }
            targets[n_targets++] = (uint32_t)strtoul(t, NULL, 0);
        }
        Image *g = image_by_id(image);
        if (!g) { fprintf(stderr, "unknown image %s\n", image); return 2; }
        run_query(g->blob.p, g->blob.n, g->base, 0, image, start, end, reg,
                  targets, n_targets, use_returns, any_target, &first, NULL);
    }
    printf("\n ]\n}\n");
    for (size_t i = 0; i < N_IMAGES; i++) if (IMAGES[i].loaded) free(IMAGES[i].blob.p);
    return 0;
}
