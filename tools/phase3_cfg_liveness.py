#!/usr/bin/env python3
"""Phase-3 hook liveness: intra-function CFG backward-liveness fixpoint (R3000).

Replaces the linear backward scan in phase3_hook_contract.py. The linear scan
marks a0-a3 live at EVERY `jal`, so any post-resume call pins the argument
registers "live" and the cave can never be discharged. A real CFG fixpoint that
respects control flow and the o32 calling convention settles it.

SOUNDNESS (the entire point): LIVE is OVER-approximated => DEAD is
UNDER-approximated => the clobber check can REJECT a safe hook but can NEVER
ACCEPT an unsafe one. Every approximation below only GROWS the live set, with ONE
documented exception: a call KILLS the caller-saved registers (the PS1 o32 ABI the
game itself was compiled to). That single assumption is what makes discharge
possible at all; it is stated, not hidden.

Two liveness solutions per function:
  live_full       — boundary seeds (EXIT at `jr ra`, EXIT+args at a tail call,
                    ALL at an undecoded indirect `jr`) AND jal-use = the callee's
                    arity. This is the SOUND must-preserve set: what a cave must
                    not destroy.
  live_witnessed  — NO boundary seeds and jal-use = EMPTY, so a register is live
                    here ONLY because a CONCRETE instruction reads it downstream
                    before any redefinition. This is what gives the tool TEETH:
                    a clobber of a witnessed-live register is a real defect, and
                    it can be reported WITHOUT ever accusing a working mod over an
                    inferred may-read (arity) or a conservative return-value seed.

Public API:
  build_index(exe, funcs)                 -> jr_map (pc -> [in-func targets])
  compute_arity(exe, funcs, jr_map)       -> {fstart: frozenset(arg regs read)}
  FunctionLiveness(exe, fstart, fend, arity, jr_map, source)  — .must_preserve_at,
                    .witnessed_at, .witness_addr, .confidence, .degraded_reason
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))
from phase3_jr_tables import EXE_BASE, s16, word  # noqa: E402

# --- register universe: 32 GPRs + 3 pseudo-regs -----------------------------
HI, LO, COP2 = 32, 33, 34
GPR_NAMES = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3",
             "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7",
             "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
             "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]
PSEUDO_NAMES = {HI: "hi", LO: "lo", COP2: "cop2"}


def reg_name(r):
    return GPR_NAMES[r] if r < 32 else PSEUDO_NAMES[r]


ARGS = frozenset({4, 5, 6, 7})
# caller-saved under o32: at, v0-v1, a0-a3, t0-t9, ra, HI, LO. (COP2 is NOT — a
# GTE value set before a call and read after survives; we keep it live.)
CALLER_SAVED = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                          24, 25, 31, HI, LO})
# live on return: v0/v1 (result), ra, sp/gp/fp, s0-s7 (callee-saved).
EXIT = frozenset({2, 3, 31, 29, 28, 30, 16, 17, 18, 19, 20, 21, 22, 23})
ALLREGS = frozenset(range(1, 35))            # everything but r0 (undecoded jr)

BRANCH_PCREL = {0x01, 0x04, 0x05, 0x06, 0x07}
JUMP_ABS = {0x02, 0x03}
LOADS = {0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26}


def op_of(i):
    return i >> 26


def is_call(i):
    return op_of(i) == 0x03 or (op_of(i) == 0 and (i & 0x3F) == 0x09)   # jal / jalr


def is_jr(i):
    return op_of(i) == 0 and (i & 0x3F) == 0x08


def is_transfer(i):
    op = op_of(i)
    if op in BRANCH_PCREL or op in JUMP_ABS:
        return True
    if op == 0 and (i & 0x3F) in (0x08, 0x09):        # jr / jalr
        return True
    if op in (0x10, 0x12) and ((i >> 16) & 0x1F) in (8, 9):   # bc0f/bc2f
        return True
    return False


def branch_target(pc, i):
    op = op_of(i)
    if op in BRANCH_PCREL:
        return pc + 4 + s16(i & 0xFFFF) * 4
    if op in JUMP_ABS:
        return ((pc + 4) & 0xF0000000) | ((i & 0x3FFFFFF) << 2)
    return None


def def_use_simple(i):
    """(defs, uses) over the 35-reg universe for a NON-transfer instruction (and
    for branches, whose only effect is a register READ). Calls and jr are handled
    by the block walker, not here. r0 is discarded."""
    op = op_of(i)
    rs, rt, rd = (i >> 21) & 0x1F, (i >> 16) & 0x1F, (i >> 11) & 0x1F
    d, u = set(), set()
    if op == 0:                                        # R-type
        fn = i & 0x3F
        if fn in (0x00, 0x02, 0x03):                   # sll/srl/sra: rd = rt
            d, u = {rd}, {rt}
        elif fn in (0x04, 0x06, 0x07):                 # sllv/srlv/srav
            d, u = {rd}, {rt, rs}
        elif fn in (0x18, 0x19, 0x1A, 0x1B):           # mult/multu/div/divu
            d, u = {HI, LO}, {rs, rt}
        elif fn == 0x10:                               # mfhi
            d, u = {rd}, {HI}
        elif fn == 0x12:                               # mflo
            d, u = {rd}, {LO}
        elif fn == 0x11:                               # mthi
            d, u = {HI}, {rs}
        elif fn == 0x13:                               # mtlo
            d, u = {LO}, {rs}
        elif fn in (0x0C, 0x0D):                       # syscall/break
            d, u = set(), set()
        else:                                          # add/sub/and/or/slt/...
            d, u = {rd}, {rs, rt}
    elif op == 0x01:                                   # regimm bltz/bgez(al)
        u = {rs}
        if ((i >> 16) & 0x1F) in (0x10, 0x11):         # bltzal/bgezal write ra
            d = {31}
    elif op in (0x04, 0x05):                           # beq/bne
        u = {rs, rt}
    elif op in (0x06, 0x07):                           # blez/bgtz
        u = {rs}
    elif op == 0x0F:                                   # lui
        d = {rt}
    elif op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):  # addi..xori (I-type ALU)
        d, u = {rt}, {rs}
    elif op in (0x22, 0x26):                           # lwl/lwr: merge into rt
        d, u = {rt}, {rs, rt}
    elif op in LOADS:                                  # lb..lw
        d, u = {rt}, {rs}
    elif op in (0x28, 0x29, 0x2A, 0x2B, 0x2E):         # stores
        u = {rs, rt}
    elif op == 0x10:                                   # cop0 mfc0/mtc0
        if ((i >> 21) & 0x1F) == 0:                    # mfc0
            d = {rt}
        elif ((i >> 21) & 0x1F) == 4:                  # mtc0
            u = {rt}
    elif op == 0x12:                                   # cop2 / GTE
        if i & 0x02000000:                             # GTE command
            d, u = {COP2}, {COP2}
        else:
            sub = (i >> 21) & 0x1F
            if sub in (0, 2):                          # mfc2/cfc2
                d, u = {rt}, {COP2}
            elif sub in (4, 6):                        # mtc2/ctc2
                d, u = {COP2}, {rt}
    elif op == 0x32:                                   # lwc2
        d, u = {COP2}, {rs}
    elif op == 0x3A:                                   # swc2
        u = {rs, COP2}
    d.discard(0)
    u.discard(0)
    return d, u


def _call_def_use(i, arity_map, target_of_call):
    """(defs, uses) for a jal/jalr — the callee's effect (downstream-most)."""
    if op_of(i) == 0x03:                               # jal target
        d = set(CALLER_SAVED)                          # includes ra
        tgt = target_of_call
        u = set(arity_map.get(tgt, ARGS)) if tgt is not None else set(ARGS)
    else:                                              # jalr rd, rs
        rs, rd = (i >> 21) & 0x1F, (i >> 11) & 0x1F
        d = set(CALLER_SAVED) | {rd}
        u = set(ARGS) | {rs}                           # indirect: unknown callee
    d.discard(0)
    u.discard(0)
    return d, u


# ---------------------------------------------------------------------------
def build_index(exe, funcs):
    """pc -> [in-scope decoded targets] for every `jr` we resolved a table for.
    Used to add real CFG edges for a jr that dispatches WITHIN its function."""
    jr_map = {}
    p = ROOT / "analysis" / "phase3_jr_tables.json"
    if p.exists():
        for pcs, d in json.loads(p.read_text())["decoded"].items():
            jr_map[int(pcs, 16)] = [int(t["target"], 16) for t in d["targets"]]
    return jr_map


class _CFG:
    """Delay-slot-aware basic blocks over [fstart, fend)."""

    def __init__(self, exe, fstart, fend, jr_map):
        self.exe, self.fstart, self.fend = exe, fstart, fend
        end = min(fend, EXE_BASE + len(exe))
        self.end = end
        words = {pc: word(exe, pc) for pc in range(fstart, end, 4)}
        self.words = words

        # leaders
        leaders = {fstart}
        transfers = {}                                 # term_pc -> word
        for pc in range(fstart, end, 4):
            i = words[pc]
            if is_transfer(i):
                transfers[pc] = i
                if pc + 8 < end:
                    leaders.add(pc + 8)                # fall-through after delay slot
                for t in self._targets(pc, i, jr_map):
                    if fstart <= t < end:
                        leaders.add(t)
        # coalesce: a leader that is a delay slot (prev word is a transfer) is not
        # a real block start — the branch/delay pair stays atomic.
        self.anomaly = False
        clean = set()
        for L in leaders:
            if L - 4 in transfers:
                self.anomaly = True                    # a jump into a delay slot
                continue
            clean.add(L)
        clean.add(fstart)
        self.starts = sorted(clean)
        self.transfers = transfers

        # blocks: [start, next_start)
        self.block_end = {}
        for idx, s in enumerate(self.starts):
            e = self.starts[idx + 1] if idx + 1 < len(self.starts) else end
            self.block_end[s] = e

        # succ + boundary seed per block
        self.succ = {}
        self.seed = {}                                 # 'exit' | 'tail' | 'all' | None
        self.degraded = False
        for s in self.starts:
            e = self.block_end[s]
            term_pc = e - 8
            succ, seed = set(), None
            if term_pc >= s and term_pc in transfers and (term_pc + 4) < e:
                i = transfers[term_pc]
                op = op_of(i)
                if is_call(i):
                    if e < end:
                        succ.add(e)                    # returns to fall-through
                elif is_jr(i):
                    reg = (i >> 21) & 0x1F
                    if reg == 31:
                        seed = "exit"                  # jr ra
                    elif term_pc in jr_map:
                        outside = False
                        for t in jr_map[term_pc]:
                            if fstart <= t < end:
                                succ.add(t if t in self.block_end else
                                         self._owner(t))
                            else:
                                outside = True
                        if outside:
                            seed = "tail"
                    else:
                        seed = "all"                   # undecoded indirect jr
                        self.degraded = True
                elif op == 0x02:                        # j target
                    t = branch_target(term_pc, i)
                    if fstart <= t < end:
                        succ.add(self._owner(t))
                    else:
                        seed = "tail"
                elif op in BRANCH_PCREL:                # conditional
                    t = branch_target(term_pc, i)
                    if fstart <= t < end:
                        succ.add(self._owner(t))
                    else:
                        seed = "tail"
                    if e < end:
                        succ.add(e)                    # fall-through
                else:                                   # bc0f/bc2f etc.
                    if e < end:
                        succ.add(e)
            else:
                # fall-through block (no terminating transfer)
                if e < end:
                    succ.add(e)
            self.succ[s] = succ
            self.seed[s] = seed

    def _targets(self, pc, i, jr_map):
        op = op_of(i)
        if op in BRANCH_PCREL or op == 0x02:
            t = branch_target(pc, i)
            return [t] if t is not None else []
        if is_jr(i) and pc in jr_map:
            return jr_map[pc]
        return []

    def _owner(self, addr):
        """Block start owning `addr` (targets always land on a leader, but guard)."""
        best = self.fstart
        for s in self.starts:
            if s <= addr:
                best = s
            else:
                break
        return best

    def seed_set(self, kind, use_boundary):
        if not use_boundary or kind is None:
            return frozenset()
        if kind == "exit":
            return EXIT
        if kind == "tail":
            return EXIT | ARGS
        if kind == "all":
            return ALLREGS
        return frozenset()

    def _block_transfer(self, s, live_out, jal_use):
        """Backward transfer across block `s`, returning live-in. `jal_use` is a
        fn(target)->use-set for calls (EMPTY-returning for the witnessed pass)."""
        e = self.block_end[s]
        words = [(pc, self.words[pc]) for pc in range(s, e, 4)]
        live = set(live_out)
        term_pc = e - 8
        has_term = (term_pc >= s and term_pc in self.transfers
                    and (term_pc + 4) < e)
        if has_term:
            term_i = self.transfers[term_pc]
            ds_pc, ds_i = words[-1]
            if is_call(term_i):
                # callee effect is downstream of the delay slot: apply it FIRST.
                if op_of(term_i) == 0x03:
                    d = set(CALLER_SAVED)
                    tgt = branch_target(term_pc, term_i)
                    u = set(jal_use(tgt))
                else:                                  # jalr
                    rs, rd = (term_i >> 21) & 0x1F, (term_i >> 11) & 0x1F
                    d = set(CALLER_SAVED) | {rd}
                    u = set(jal_use(None)) | {rs}
                d.discard(0)
                u.discard(0)
                live = (live - d) | u
                dd, du = def_use_simple(ds_i)          # delay slot
                live = (live - dd) | du
            else:
                dd, du = def_use_simple(ds_i)          # delay slot first
                live = (live - dd) | du
                if is_jr(term_i):
                    live.add((term_i >> 21) & 0x1F)    # jr reads its register
                    live.discard(0)
                elif op_of(term_i) in BRANCH_PCREL:
                    _, tu = def_use_simple(term_i)
                    live |= tu
                # j: no register effect
            rest = words[:-2]
        else:
            rest = words
        for pc, i in reversed(rest):
            d, u = def_use_simple(i)
            live = (live - d) | u
        return live

    def solve(self, jal_use, use_boundary):
        live_in = {s: set() for s in self.starts}
        changed = True
        while changed:
            changed = False
            for s in reversed(self.starts):
                lo = set()
                for t in self.succ[s]:
                    lo |= live_in.get(t, set())
                lo |= self.seed_set(self.seed[s], use_boundary)
                li = self._block_transfer(s, lo, jal_use)
                if li != live_in[s]:
                    live_in[s] = li
                    changed = True
        return live_in

    def live_entering(self, addr, live_in, jal_use, use_boundary):
        """Registers live just before executing the instruction at `addr` — i.e.
        what code from `addr` onward requires. Walk the containing block backward
        from its end down to (and including) `addr`."""
        s = self._owner(addr)
        e = self.block_end[s]
        lo = set()
        for t in self.succ[s]:
            lo |= live_in.get(t, set())
        lo |= self.seed_set(self.seed[s], use_boundary)
        # replay the block backward but STOP at addr (keep addr's own effect)
        words = [(pc, self.words[pc]) for pc in range(s, e, 4)]
        live = set(lo)
        term_pc = e - 8
        has_term = (term_pc >= s and term_pc in self.transfers
                    and (term_pc + 4) < e)
        # process instructions from high to low, but only those with pc >= addr
        # (using the same call/branch ordering as _block_transfer)
        if has_term:
            term_i = self.transfers[term_pc]
            ds_pc, ds_i = words[-1]
            if is_call(term_i):
                if term_pc >= addr:
                    if op_of(term_i) == 0x03:
                        d = set(CALLER_SAVED)
                        u = set(jal_use(branch_target(term_pc, term_i)))
                    else:
                        rs, rd = (term_i >> 21) & 0x1F, (term_i >> 11) & 0x1F
                        d = set(CALLER_SAVED) | {rd}
                        u = set(jal_use(None)) | {rs}
                    d.discard(0)
                    u.discard(0)
                    live = (live - d) | u
                if ds_pc >= addr:
                    dd, du = def_use_simple(ds_i)
                    live = (live - dd) | du
            else:
                if ds_pc >= addr:
                    dd, du = def_use_simple(ds_i)
                    live = (live - dd) | du
                if term_pc >= addr:
                    if is_jr(term_i):
                        live.add((term_i >> 21) & 0x1F)
                        live.discard(0)
                    elif op_of(term_i) in BRANCH_PCREL:
                        _, tu = def_use_simple(term_i)
                        live |= tu
            rest = words[:-2]
        else:
            rest = words
        for pc, i in reversed(rest):
            if pc < addr:
                break
            d, u = def_use_simple(i)
            live = (live - d) | u
        return live


# --- arity pre-pass ---------------------------------------------------------
def compute_arity(exe, funcs, jr_map, rounds=8):
    """{fstart: frozenset(a0-a3 that MAY be read before written)}.

    Fixpoint refinement. Round 0 assumes every internal `jal` reads ALL args
    (maximal, no recursion). Each later round recomputes each function's arity
    using the PREVIOUS round's (tighter) callee arities. Starting from the maximal
    set and refining DOWNWARD keeps every intermediate an over-approximation of the
    true may-read set (sound: never drops an arg that is actually read), and the
    arities are non-increasing so it converges. Without this, a function that only
    FORWARDS args (calls a callee before setting a2/a3) inherits the callee's full
    arg set transitively and never tightens — which leaves working caves unverified."""
    cfgs = {}
    for fstart, fend, f in funcs:
        if f.get("range_type") not in ("code", "thunk"):
            continue
        try:
            cfgs[fstart] = _CFG(exe, fstart, fend, jr_map)
        except Exception:
            cfgs[fstart] = None
    arity = {fs: ARGS for fs in cfgs}                   # round 0: maximal
    for _ in range(rounds):
        changed = False
        jal_use = lambda t: arity.get(t, ARGS)         # noqa: E731
        for fs, cfg in cfgs.items():
            if cfg is None:
                continue
            li = cfg.solve(jal_use, use_boundary=True)
            new = frozenset(li.get(fs, set()) & set(ARGS))
            if new != arity[fs]:
                arity[fs] = new
                changed = True
        if not changed:
            break
    return arity


class FunctionLiveness:
    """Both liveness solutions for one function, plus witness lookup."""

    def __init__(self, exe, fstart, fend, arity, jr_map, source="census"):
        self.exe, self.fstart, self.fend = exe, fstart, fend
        self.source = source
        self.cfg = _CFG(exe, fstart, fend, jr_map)
        self._jal_full = lambda t: arity.get(t, ARGS)
        self._jal_none = lambda _t: frozenset()
        self._li_full = self.cfg.solve(self._jal_full, use_boundary=True)
        self._li_wit = self.cfg.solve(self._jal_none, use_boundary=False)
        self.degraded_reason = None
        if source == "recovered":
            self.degraded_reason = "recovered_extent"
        elif self.cfg.degraded:
            self.degraded_reason = "undecoded_indirect_jr"
        self.confidence = "degraded" if self.degraded_reason else "exact"

    def must_preserve_at(self, addr):
        """Sound over-approx of GPRs+pseudo live entering `addr`."""
        return self.cfg.live_entering(addr, self._li_full, self._jal_full,
                                      use_boundary=True)

    def witnessed_at(self, addr):
        """Registers live entering `addr` ONLY via a concrete downstream read."""
        return self.cfg.live_entering(addr, self._li_wit, self._jal_none,
                                      use_boundary=False)

    def witness_addr(self, reg, addr, limit=4000):
        """Forward CFG search from `addr` for the first instruction that READS
        `reg` before any redefinition — the concrete read that proves it live."""
        seen, stack = set(), [addr]
        while stack:
            pc = stack.pop()
            s = self.cfg._owner(pc)
            e = self.cfg.block_end[s]
            cur = pc
            while cur < e:
                i = self.cfg.words[cur]
                if is_call(i):
                    if op_of(i) == 0x03:
                        u = self._jal_full(branch_target(cur, i))
                        d = CALLER_SAVED
                    else:
                        u = set(ARGS) | {(i >> 21) & 0x1F}
                        d = CALLER_SAVED | {(i >> 11) & 0x1F}
                    if reg in u:
                        return f"0x{cur:08X}"
                    if reg in d:
                        break
                else:
                    d, u = def_use_simple(i)
                    if reg in u:
                        return f"0x{cur:08X}"
                    if reg in d and not is_transfer(i):
                        break
                cur += 4
            else:
                for t in self.cfg.succ[s]:
                    if t not in seen:
                        seen.add(t)
                        stack.append(t)
                continue
            # broke out (redefined or call clobbered) — do not follow successors
        return None


def recover_extent(exe, funcs, addr):
    """When `addr` falls in a census hole, synthesise an OVER-approximate function
    extent: back to the previous `jr ra`+delay (or a `addiu sp,sp,-N` prologue, or
    the previous censused function's end), forward to the next `jr ra`+delay (or
    the next censused start). Returns (fstart, fend) or None if the region does not
    look like code. Over-approximation keeps liveness sound (a larger frame can
    only add live regs)."""
    lo_lim = EXE_BASE
    hi_lim = EXE_BASE + len(exe)
    prev_end, next_start = lo_lim, hi_lim
    for fs, fe, f in funcs:
        if fe <= addr and fe > prev_end:
            prev_end = fe
        if fs > addr and fs < next_start:
            next_start = fs
    # backward to a start
    fstart = prev_end
    pc = addr - 4
    while pc >= prev_end:
        i = word(exe, pc)
        if is_jr(i) and ((i >> 21) & 0x1F) == 31:      # jr ra terminator
            fstart = pc + 8
            break
        if op_of(i) == 0x09 and ((i >> 21) & 0x1F) == 29 and \
                ((i >> 16) & 0x1F) == 29 and s16(i & 0xFFFF) < 0:   # addiu sp,sp,-N
            fstart = pc
            break
        pc -= 4
    # forward to an end
    fend = next_start
    pc = addr
    while pc < next_start:
        i = word(exe, pc)
        if is_jr(i) and ((i >> 21) & 0x1F) == 31:
            fend = min(next_start, pc + 8)
            break
        pc += 4
    # sanity: region must mostly decode as code (reject long zero/data runs)
    n = (fend - fstart) // 4
    if n <= 0:
        return None
    zero = sum(1 for pc in range(fstart, fend, 4) if word(exe, pc) == 0)
    if zero > n // 2:
        return None
    return fstart, fend
