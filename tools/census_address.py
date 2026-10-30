#!/usr/bin/env python3
"""Alias-aware census of every instruction that can access a given RAM address.

WHY THIS EXISTS
---------------
A census built by grepping for an immediate (`0x657E`, or `+0x7E` off a pointer) is
NOT a completeness argument, and claiming otherwise is how a partial Phase-4 row got
mislabelled solved. The slot `0x800A657E` is reached at least three ways the immediate
scan cannot see:

    0x800588D0  sh v0, 0x0(fp)     fp = v0 - 25, where v0 is itself a computed address
    0x8004A7E0  lh v0, 0x0(a0)     a0 = 0x800A657E built by lui/addiu earlier
    0x8004A808  sh v0, 0x0(a0)     same base, different instruction
    0x80048654  sh v0, 0x7e(s1)    s1 = a0, the player pointer PASSED IN by the caller

The last one is the important one: no intraprocedural analysis can resolve it, because
the base arrives as a function argument.

WHAT THIS DOES
--------------
A may-constant value analysis over the whole resident image:

  * per-function CFG, worklist to fixed point, lattice = {set of <=MAX_VALS constants}
    or TOP; merge at join points is UNION (a MAY analysis -- if a register can hold the
    address on any path, the access is reported).
  * `lui / addiu / ori / addu / subu / or / move / sll` propagate constants.
  * INTERPROCEDURAL, to fixed point: at every `jal`, the resolved constants in a0..a3
    are propagated into the callee's entry state, so a base that arrives as an argument
    (`s1 = a0`) is resolved from the call sites.

WHAT IT HONESTLY CANNOT DO -- reported, not hidden
--------------------------------------------------
  * `jalr` (indirect calls) are not resolved, so arguments flowing through them are lost.
  * bases loaded FROM memory (`lw rX, off(rY)` -> a pointer read out of a struct) become
    TOP, since their value is not in the instruction stream.
  * every memory access whose base is TOP *could* alias the target. The tool counts them
    and lists the ones inside functions that are known to receive the target's owning
    block, because those are where a missed site would most plausibly hide.

So the output is a census PLUS an explicit residual. "Nothing else touches it" is only
warranted when the residual is enumerated and inspected -- which is the point.

USAGE
    tools/census_address.py 0x800A657E --block 0x800A6500 --json out.json
    tools/census_address.py 0x800A6594 --block 0x800A6500        # true health
"""

from __future__ import annotations

import argparse
import bisect
import json
import struct
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGS = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5",
        "t6", "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "t8", "t9", "k0", "k1",
        "gp", "sp", "fp", "ra"]
LOADS = {0x20: "lb", 0x21: "lh", 0x23: "lw", 0x24: "lbu", 0x25: "lhu", 0x22: "lwl", 0x26: "lwr"}
STORES = {0x28: "sb", 0x29: "sh", 0x2B: "sw", 0x2A: "swl", 0x2E: "swr"}
WIDTH = {"lb": 1, "lbu": 1, "sb": 1, "lh": 2, "lhu": 2, "sh": 2,
         "lw": 4, "sw": 4, "lwl": 4, "lwr": 4, "swl": 4, "swr": 4}
MAX_VALS = 6          # per-register constant-set cap; beyond this the register goes TOP
TOP = None            # unknown / too many possibilities


def s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def sx32(v: int) -> int:
    """Interpret a 32-bit register value as signed, for ids like a0 = -3."""
    return v - 0x100000000 if v & 0x80000000 else v


def merge(a, b):
    """MAY merge: union, saturating to TOP."""
    if a is TOP or b is TOP:
        return TOP
    u = a | b
    return TOP if len(u) > MAX_VALS else u


def merge_state(dst: dict, src: dict) -> bool:
    changed = False
    for r in REGS:
        m = merge(dst.get(r, set()), src.get(r, set()))
        if m != dst.get(r, set()):
            dst[r] = m
            changed = True
    return changed


class Image:
    def __init__(self, exe: Path, functions: Path):
        data = exe.read_bytes()
        if data[:8] != b"PS-X EXE":
            raise SystemExit(f"{exe}: not a PS-X EXE")
        self.base = struct.unpack_from("<I", data, 0x18)[0]
        self.text = data[0x800:]
        self.end = self.base + len(self.text)

        fns = json.loads(functions.read_text())
        if isinstance(fns, dict):
            fns = fns.get("functions", fns)
        recs = []
        for f in fns:
            a = f.get("address") or f.get("addr") or f.get("start")
            if isinstance(a, str):
                a = int(a, 16)
            if a and self.base <= a < self.end:
                recs.append((a, f.get("name") or "?", int(f.get("size") or 0)))
        recs.sort()
        self.funcs = recs
        self.starts = [r[0] for r in recs]

    def word(self, va: int) -> int:
        return struct.unpack_from("<I", self.text, va - self.base)[0]

    def owner(self, va: int):
        i = bisect.bisect_right(self.starts, va) - 1
        return self.funcs[i] if i >= 0 else (0, "?", 0)

    def extent(self, start: int) -> int:
        i = bisect.bisect_left(self.starts, start)
        a, _, size = self.funcs[i]
        if size:
            return a + size
        return self.funcs[i + 1][0] if i + 1 < len(self.funcs) else self.end

    def is_function_start(self, va: int) -> bool:
        i = bisect.bisect_left(self.starts, va)
        return i < len(self.starts) and self.starts[i] == va


def block_starts(img: Image, lo: int, hi: int) -> set:
    """Leaders: function entry, every branch target inside the function, and every
    instruction after a branch's delay slot."""
    leaders = {lo}
    for pc in range(lo, hi, 4):
        w = img.word(pc)
        op, rt, imm = w >> 26, (w >> 16) & 31, w & 0xFFFF
        tgt = None
        if op in (4, 5, 6, 7) or (op == 1 and rt in (0, 1, 16, 17)):
            tgt = pc + 4 + (s16(imm) << 2)
        if tgt is not None and lo <= tgt < hi:
            leaders.add(tgt)
        if tgt is not None or op in (2, 3) or (op == 0 and (w & 0x3F) in (8, 9)):
            if lo <= pc + 8 < hi:
                leaders.add(pc + 8)
    return leaders


def transfer(img: Image, pc: int, st: dict, hits: list, unresolved: list,
             targets: set, calls: list, block_lo: int, block_hi: int,
             globals_map=None, store_obs=None):
    """Apply one instruction to the register state; record any memory access.

    `globals_map` turns on GLOBAL-POINTER PROVENANCE. Without it, every value loaded
    from memory becomes TOP, so an access through a pointer held in a global -- which
    is how this game reaches most objects -- is unresolvable in principle, and the
    census can only say "might alias". With it, a `lw` whose effective address is a
    global with a known constant value-set propagates that set into the destination
    register, so the access resolves to real addresses and the residual shrinks to
    things that are genuinely dynamic.

    `store_obs` collects (ea, value-set) for every store with a resolvable address,
    which is what builds `globals_map` on the previous round.
    """
    w = img.word(pc)
    op, rs, rt, rd, sa, funct, imm = (w >> 26, (w >> 21) & 31, (w >> 16) & 31,
                                      (w >> 11) & 31, (w >> 6) & 31, w & 0x3F, w & 0xFFFF)

    def val(r):
        return st.get(REGS[r], TOP)

    def setv(r, v):
        if r == 0:
            return
        st[REGS[r]] = TOP if v is TOP else (TOP if len(v) > MAX_VALS else v)

    if op in LOADS or op in STORES:
        name = LOADS.get(op) or STORES[op]
        base = val(rs)
        off = s16(imm)
        rec = {"pc": "0x%08X" % pc, "insn": "%s %s, %s0x%x(%s)" % (
                   name, REGS[rt], "-" if off < 0 else "", abs(off), REGS[rs]),
               "kind": "read" if op in LOADS else "write",
               "width": WIDTH[name], "function": img.owner(pc)[1]}
        if base is TOP:
            unresolved.append(rec)
        else:
            for b in base:
                ea = (b + off) & 0xFFFFFFFF
                # OVERLAP, not equality. Testing `ea in targets` only catches an access
                # that STARTS on the target, so a word store at 0x800A657C -- which
                # writes bytes 7C..7F and therefore clobbers the halfword at 0x800A657E
                # -- was invisible to this census. The slot is at offset 0x7E, i.e. NOT
                # word-aligned, so it is straddled by the aligned word below it and this
                # is a reachable miss, not a theoretical one.
                span = range(ea, ea + WIDTH[name])
                covered = [x for x in span if x in targets]
                if covered:
                    hits.append({**rec, "address": "0x%08X" % ea,
                                 "base_value": "0x%08X" % b,
                                 "covers": ["0x%08X" % x for x in covered],
                                 "straddles": ea not in targets})
                    break
            if store_obs is not None and op in STORES:
                v = val(rt)
                for b in base:
                    store_obs.append(((b + off) & 0xFFFFFFFF, WIDTH[name],
                                      None if v is TOP else frozenset(v)))
        if op in LOADS:
            # Global-pointer provenance: a word loaded from a global whose stored value
            # set is known propagates that set, instead of collapsing to TOP.
            got = TOP
            if globals_map is not None and base is not TOP and WIDTH[name] == 4:
                acc = set()
                for b in base:
                    g = globals_map.get((b + off) & 0xFFFFFFFF)
                    if g is None:
                        acc = None
                        break
                    acc |= set(g)
                if acc and len(acc) <= MAX_VALS:
                    got = acc
            setv(rt, got)
        return

    if op == 0x0F:                                  # lui
        setv(rt, {(imm << 16) & 0xFFFFFFFF})
        return
    if op in (0x08, 0x09):                          # addi / addiu
        v = val(rs)
        setv(rt, TOP if v is TOP else {(x + s16(imm)) & 0xFFFFFFFF for x in v})
        return
    if op == 0x0D:                                  # ori
        v = val(rs)
        setv(rt, TOP if v is TOP else {(x | imm) & 0xFFFFFFFF for x in v})
        return
    if op in (0x0A, 0x0B, 0x0C, 0x0E):              # slti/sltiu/andi/xori -> not an address
        setv(rt, TOP)
        return
    if op in (2, 3):
        return   # jal/j handled by the block loop: MIPS runs the DELAY SLOT first, and
                 # for `jal` that delay slot is usually what sets a0 (e.g. 0x8004EFD8
                 # `jal player_vertical_update` / `addiu a0, s0, -0x90`). Recording the
                 # arguments at the jal itself reads them one instruction too early --
                 # which is exactly why every `+0x7E off the player pointer` site failed
                 # to resolve.
    if op == 0:
        if funct in (0x21, 0x20):                   # addu / add  (also `move rd,rs`)
            a, b = val(rs), val(rt)
            if b is not TOP and b == {0}:
                setv(rd, a)
            elif a is not TOP and a == {0}:
                setv(rd, b)
            elif a is TOP or b is TOP:
                setv(rd, TOP)
            else:
                setv(rd, {(x + y) & 0xFFFFFFFF for x in a for y in b})
        elif funct in (0x23, 0x22):                 # subu / sub
            a, b = val(rs), val(rt)
            setv(rd, TOP if (a is TOP or b is TOP)
                 else {(x - y) & 0xFFFFFFFF for x in a for y in b})
        elif funct == 0x25:                         # or
            a, b = val(rs), val(rt)
            if b is not TOP and b == {0}:
                setv(rd, a)
            elif a is not TOP and a == {0}:
                setv(rd, b)
            else:
                setv(rd, TOP)
        elif funct == 0x09:                         # jalr -- indirect call
            pass                                    # handled by the block loop
        elif funct == 0x08:                         # jr
            pass
        else:
            setv(rd, TOP)
        return
    # everything else: conservatively clobber the destination
    if op in (0x10, 0x11, 0x12, 0x13) and rs in (0, 2):
        setv(rt, TOP)


# A sentinel base for `sp`. Stack accesses then resolve to a private region instead of
# becoming residual, which is what makes the residual small enough to be a real bound.
# Sound as long as the target is nowhere near it.
STACK_BASE = 0x00100000

# $gp is a COMPILE-TIME CONSTANT in this image, and seeding it is worth 916 accesses.
# Proven from the image alone, not assumed:
#   * exactly one materialization -- `lui gp,0x8008 / addiu gp,gp,0x1d98` in stup1 at
#     0x8005F710, the startup routine;
#   * the only two other writes to $gp in code are `lw gp, 0x68(sp)` epilogue restores
#     (gte_rtps_mesh_assembler 0x80018800, decompress_lz_bitstream 0x8001A8E4), each
#     matched by an `sw gp, 0x68(sp)` prologue save at the same stack slot, so they
#     restore the same value rather than redefining it;
#   * the other 30 apparent writes are all in `data_nonzero`/`string` regions per
#     analysis/memory_map.json -- data being decoded as instructions, not code.
# With gp seeded, every gp-relative access has an exactly computable effective address.
GP_VALUE = 0x80081D98

ARGS = ("a0", "a1", "a2", "a3")


def analyse(img: Image, targets: set, max_rounds: int = 8, call_targets=None,
            calls_out=None, globals_map=None, store_obs=None, gp_value=GP_VALUE,
            resolved_jalr_out=None):
    # Entry arguments start at BOTTOM (empty set) and are filled in from call sites; a
    # function with no resolved direct caller gets TOP, because its arguments could be
    # anything. Seeding them TOP from the start (an earlier bug here) meant the union
    # merge could never bring them back down, so argument-passed bases -- the player
    # pointer, i.e. every `+0x7E off s1` site -- were silently never resolved.
    direct_callers = defaultdict(int)
    for fa, _, _ in img.funcs:
        lo, hi = fa, img.extent(fa)
        for pc in range(lo, min(hi, img.end), 4):
            w = img.word(pc)
            if (w >> 26) == 3:
                dst = (pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
                if img.base <= dst < img.end:
                    direct_callers[dst] += 1

    # `known_callable` starts as the statically-scanned `jal` targets and GROWS as the
    # dataflow itself resolves jalr targets (a function reached only via an indirect
    # call cannot be known callable before the analysis that discovers the call target
    # has run -- this is necessarily incremental, not a one-time pre-pass).
    known_callable = set(direct_callers)

    entry_seed = defaultdict(lambda: {r: set() for r in REGS})
    for fa, _, _ in img.funcs:
        for r in REGS:
            entry_seed[fa][r] = TOP
        entry_seed[fa]["zero"] = {0}
        entry_seed[fa]["sp"] = {STACK_BASE}
        if gp_value is not None:
            entry_seed[fa]["gp"] = {gp_value}
        for a in ARGS:
            entry_seed[fa][a] = set() if fa in known_callable else TOP

    hits, unresolved, indirect_calls = [], [], 0
    indirect_call_pcs = set()
    for _ in range(max_rounds):
        hits, unresolved = [], []
        indirect_call_pcs = set()
        if resolved_jalr_out is not None:
            resolved_jalr_out.clear()
        pending = defaultdict(lambda: {r: set() for r in REGS})
        seeded = set()
        for fa, _, _ in img.funcs:
            lo, hi = fa, img.extent(fa)
            if hi <= lo or hi > img.end:
                continue
            leaders = sorted(block_starts(img, lo, hi))
            bounds = {b: (leaders[i + 1] if i + 1 < len(leaders) else hi)
                      for i, b in enumerate(leaders)}
            state = {b: {r: set() for r in REGS} for b in leaders}
            state[lo] = dict(entry_seed[fa])
            work = [lo]
            seen = 0
            while work and seen < 4000:
                b = work.pop()
                seen += 1
                st = {r: (TOP if state[b].get(r) is TOP else set(state[b].get(r, set())))
                      for r in REGS}
                calls = []
                blo, bhi = b, bounds[b]
                pc = blo
                while pc < bhi:
                    w = img.word(pc)
                    op, funct = w >> 26, w & 0x3F
                    is_jal = (op == 3)
                    is_jalr = (op == 0 and funct == 0x09)
                    # jalr's jump-target register is latched by the jalr instruction
                    # itself, before the delay slot runs -- capture it here, ahead of
                    # the delay-slot transfer below, matching real CPU semantics.
                    jalr_rs_val = st.get(REGS[(w >> 21) & 31], TOP) if is_jalr else None
                    if is_jalr and jalr_rs_val is TOP and pc - 4 >= blo:
                        # DISPATCH-TABLE READ. `lw` always sets its destination to TOP
                        # in the general transfer() (a loaded value is not derivable
                        # from the instruction stream), which is the right default for
                        # arbitrary data but is needlessly pessimistic for the ONE case
                        # that matters here: a function-pointer/jump table baked into
                        # the EXE image as compile-time data. If the jump register was
                        # just loaded from an address inside the STATIC IMAGE (not a
                        # runtime .bss object array), that word is pristine load-time
                        # data and can be read directly -- unlike a general `lw` target,
                        # which could be runtime-mutated state (as the render-descriptor
                        # table at 0x80096B98 demonstrably is), so this path is
                        # deliberately NOT applied to ordinary loads, only to resolving
                        # a jalr target, and every hit is tagged `via_static_table` so
                        # it stays inspectable rather than silently trusted.
                        pw = img.word(pc - 4)
                        pop, prs, prt, pimm = (pw >> 26, (pw >> 21) & 31,
                                               (pw >> 16) & 31, pw & 0xFFFF)
                        if pop == 0x23 and prt == ((w >> 21) & 31):   # lw target == rs
                            base = st.get(REGS[prs], TOP)
                            if base is not TOP:
                                eas = {(b + s16(pimm)) & 0xFFFFFFFF for b in base}
                                if all(img.base <= ea < img.end - 3 for ea in eas):
                                    jalr_rs_val = {img.word(ea) for ea in eas}
                                    jalr_via_static_table = True
                                else:
                                    jalr_via_static_table = False
                            else:
                                jalr_via_static_table = False
                        else:
                            jalr_via_static_table = False
                    else:
                        jalr_via_static_table = False
                    transfer(img, pc, st, hits, unresolved, targets, calls, blo, bhi,
                             globals_map=globals_map, store_obs=store_obs)
                    if (is_jal or is_jalr) and pc + 4 < bhi:
                        # run the delay slot BEFORE snapshotting arguments
                        transfer(img, pc + 4, st, hits, unresolved, targets, calls,
                                 blo, bhi, globals_map=globals_map, store_obs=store_obs)
                        if is_jal:
                            dsts = [(pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2)]
                        elif jalr_rs_val is not TOP:
                            # RESOLVED INDIRECT CALL. The jump-target register derives
                            # from the same value analysis as everything else (constant
                            # propagation, $gp seeding, global-pointer provenance) --
                            # previously this branch discarded that and always recorded
                            # the call as unresolved, which is why every jalr counted
                            # against the "238 indirect calls unresolved" residual even
                            # when its target was already known. Keep only candidates
                            # that are valid function entries in the image.
                            dsts = sorted(
                                d for d in jalr_rs_val
                                if d % 4 == 0 and img.base <= d < img.end
                                # must be a KNOWN FUNCTION ENTRY, not merely some
                                # in-range address -- otherwise a resolved-but-wrong
                                # register value (e.g. a data pointer that happens to
                                # land inside the image) would be treated as a call.
                                and img.is_function_start(d))
                        else:
                            dsts = None
                        if dsts:
                            args = {REGS[4 + i]: st.get(REGS[4 + i], TOP) for i in range(4)}
                            if is_jalr and resolved_jalr_out is not None:
                                resolved_jalr_out.append({
                                    "pc": "0x%08X" % pc, "function": img.owner(pc)[1],
                                    "targets": ["0x%08X" % d for d in dsts],
                                    "via_static_table": jalr_via_static_table})
                            for dst in dsts:
                                calls.append((dst, args))
                                # Argument capture at a named callee. Same machinery the
                                # interprocedural seeding already needs -- exposed so a
                                # caller census (which sound id? which memset range?)
                                # does not have to reimplement the value analysis.
                                if call_targets and dst in call_targets and calls_out is not None:
                                    calls_out.append({
                                        "pc": "0x%08X" % pc,
                                        "callee": "0x%08X" % dst,
                                        "function": img.owner(pc)[1],
                                        "via_jalr": is_jalr,
                                        "args": {k: (None if v is TOP else
                                                     sorted(sx32(x) for x in v))
                                                 for k, v in args.items()},
                                    })
                        else:
                            # Same revisit-inflation problem `hits`/`unresolved` had: a
                            # block can be reprocessed multiple times while its function
                            # converges, and this branch would fire again on every
                            # revisit of the same PC. Track the SITE, not a per-visit
                            # tally, so `indirect_calls` reports distinct instructions.
                            indirect_call_pcs.add(pc)
                        for r in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 31):
                            st[REGS[r]] = TOP       # caller-saved clobbered across the call
                        pc += 8
                        continue
                    pc += 4
                for dst, args in calls:
                    if dst is None:
                        continue
                    if img.base <= dst < img.end:
                        tgt = pending[dst]
                        for k, v in (args or {}).items():
                            tgt[k] = merge(tgt.get(k, set()), v)
                        seeded.add(dst)
                # successors
                w = img.word(bhi - 4) if bhi - 4 >= blo else 0
                op = w >> 26
                succs = []
                nxt = bhi
                if nxt in state:
                    succs.append(nxt)
                for pc in range(blo, bhi, 4):
                    ww = img.word(pc)
                    o, rt2, im = ww >> 26, (ww >> 16) & 31, ww & 0xFFFF
                    if o in (4, 5, 6, 7) or (o == 1 and rt2 in (0, 1, 16, 17)):
                        t = pc + 4 + (s16(im) << 2)
                        if t in state:
                            succs.append(t)
                    elif o == 2:
                        t = (pc & 0xF0000000) | ((ww & 0x3FFFFFF) << 2)
                        if t in state:
                            succs.append(t)
                for sdst in succs:
                    if merge_state(state[sdst], st):
                        work.append(sdst)

        changed = False
        # A function first proven reachable this round (a resolved jalr target that
        # was not in the static jal scan) starts its args at TOP, which a merge can
        # never lower -- flip it to BOTTOM now so this round's `pending` values (and
        # every later round's) can actually raise it, then let the merge loop below
        # pick up what was just computed for it.
        newly_callable = seeded - known_callable
        if newly_callable:
            changed = True
            known_callable |= newly_callable
            for fa in newly_callable:
                for a in ARGS:
                    entry_seed[fa][a] = set()
        for fa in seeded:
            if fa not in entry_seed or fa not in known_callable:
                continue
            for r in ARGS:
                m = merge(entry_seed[fa].get(r, set()), pending[fa].get(r, set()))
                if m != entry_seed[fa].get(r):
                    entry_seed[fa][r] = m
                    changed = True
        if not changed:
            break

    seen = {}
    for h in hits:
        seen.setdefault(h["pc"], h)
    # `unresolved` was returned RAW, unlike `hits` -- and a block gets reprocessed
    # every time an incoming edge's state changes during the internal worklist's
    # convergence, so a PC whose base genuinely never resolves gets appended again on
    # every revisit. Verified against this exact target: raw count 882 in the 34
    # related functions, but only 416 DISTINCT PCs. That inflation was never disclosed
    # -- every "882" quoted in Canon and the artifacts overstated the true residual by
    # roughly 2x. Dedupe here, the same way `hits` already is, so the number returned
    # is the number of actually-different problem instructions.
    useen = {}
    for u in unresolved:
        useen.setdefault(u["pc"], u)
    # Same fix for the indirect-call counter: it used to increment once per VISIT to
    # an unresolved jalr, not once per SITE, so "238" was also revisit-inflated and
    # not a reproducible measure of "how many distinct instructions". A PC set is.
    return (sorted(seen.values(), key=lambda x: x["pc"]),
            sorted(useen.values(), key=lambda x: x["pc"]), len(indirect_call_pcs))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address", help="target RAM address, e.g. 0x800A657E")
    ap.add_argument("--bytes", type=int, default=2, help="target width (default 2)")
    ap.add_argument("--block", help="owning block base, e.g. 0x800A6500; functions that "
                                    "receive it are where a missed site would hide")
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=Path("analysis/functions.json"))
    ap.add_argument("--json", type=Path, help="write the full census here")
    ap.add_argument("--expect", type=Path,
                    help="ratchet: a JSON baseline with `static_resolvable` and "
                         "`runtime_only` PC lists. Exits non-zero if the static pass "
                         "loses a site it used to find, or finds a site not in the "
                         "baseline. This is the executable guard -- a census nobody can "
                         "re-run is a prose claim, not evidence.")
    args = ap.parse_args()

    addr = int(args.address, 0)
    targets = set(range(addr, addr + args.bytes))
    img = Image(args.exe, args.functions)
    hits, unresolved, indirect = analyse(img, targets)

    block_fns = set()
    if args.block:
        bhits, _, _ = analyse(img, {int(args.block, 0)})
        block_fns = {h["function"] for h in bhits}
        block_fns |= {h["function"] for h in hits}

    risky = [u for u in unresolved if u["function"] in block_fns and u["width"] == args.bytes]
    out = {
        "target": args.address, "bytes": args.bytes, "exe": str(args.exe),
        "writers": [h for h in hits if h["kind"] == "write"],
        "readers": [h for h in hits if h["kind"] == "read"],
        "residual": {
            "_meaning": "accesses whose base register is TOP (not derivable from the "
                        "instruction stream) and which could therefore alias the target. "
                        "A completeness claim is only warranted once these are inspected.",
            "unresolved_accesses_total": len(unresolved),
            "unresolved_same_width_in_related_functions": len(risky),
            "related_functions": sorted(block_fns),
            "sites": risky[:80],
            "indirect_calls_unresolved": indirect,
        },
    }
    print("target %s   writers=%d  readers=%d" % (args.address, len(out["writers"]), len(out["readers"])))
    for h in out["writers"] + out["readers"]:
        print("  %-5s %s  %-28s [%s]" % (h["kind"], h["pc"], h["insn"], h["function"]))
    print("residual: %d unresolved-base accesses image-wide, %d of them same-width inside "
          "related functions; %d indirect calls unresolved"
          % (len(unresolved), len(risky), indirect))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("wrote", args.json)

    if args.expect:
        base = json.loads(args.expect.read_text())
        exp_static = {p.upper() for p in base.get("static_resolvable", [])}
        exp_runtime = {p.upper() for p in base.get("runtime_only", [])}
        found = {h["pc"].upper() for h in out["writers"] + out["readers"]}
        lost = sorted(exp_static - found)
        added = sorted(found - exp_static - exp_runtime)
        promoted = sorted(found & exp_runtime)
        still_runtime_only = sorted(exp_runtime - found)
        print("\nRATCHET vs %s" % args.expect)
        print("  static sites expected/found : %d / %d" % (len(exp_static), len(found & exp_static)))
        print("  runtime-only, still not statically resolvable: %s"
              % (", ".join(still_runtime_only) or "none"))
        if promoted:
            print("  PROMOTED (analysis now resolves these): %s" % ", ".join(promoted))
        if lost:
            print("  REGRESSION - no longer found: %s" % ", ".join(lost))
        if added:
            print("  NEW SITE - not in the baseline, review before accepting: %s" % ", ".join(added))
        if lost or added:
            return 1
        print("  OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
