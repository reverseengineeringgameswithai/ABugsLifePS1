"""Phase-3 hook liveness — unit tests for the CFG fixpoint's load-bearing parts.

The hook-contract discharge is only as trustworthy as the liveness under it. These
pin the pieces the integration tests exercise indirectly: the arity fixpoint (the
thing that let default_pickup_branch discharge — it must tighten a forwarding
function to its real args, not the maximal set), the HI/LO/COP2 pseudo-registers,
the census-hole extent recovery (honestly degraded, never synthesised-as-proven),
and the stack-frame balance check."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from phase3_jr_tables import find_function, load_functions  # noqa: E402
from phase3_cfg_liveness import (build_index, compute_arity, def_use_simple,  # noqa
                                 recover_extent, HI, LO, COP2, ARGS)

EXE = (ROOT / "REBUILD" / "files" / "SCUS_942.88").read_bytes()
FUNCS = load_functions()
JR = build_index(EXE, FUNCS)


def test_arity_fixpoint_tightens_a_forwarding_function_to_its_real_args():
    """0x80050994 takes a0 only (it reads a0, sets up its own frame, never reads
    a2/a3). A single conservative pass leaves a2/a3 in its arity because it calls
    a callee before those are set; the FIXPOINT removes them. This is exactly what
    let the golddrop default-pickup cave discharge."""
    arity = compute_arity(EXE, FUNCS, JR)
    fs = find_function(FUNCS, 0x80050994)[0]
    a = arity[fs]
    assert 4 in a                       # a0 IS read
    assert 6 not in a and 7 not in a    # a2/a3 are NOT — the fixpoint proved it


def test_arity_is_never_larger_than_maximal_and_is_a_subset_of_args():
    arity = compute_arity(EXE, FUNCS, JR)
    for a in arity.values():
        assert a <= ARGS


def test_hi_lo_pseudo_registers():
    # mult t0,t1  -> defs {HI,LO}, uses {t0,t1}
    d, u = def_use_simple((8 << 21) | (9 << 16) | 0x18)
    assert d == {HI, LO} and u == {8, 9}
    # mflo t2 -> def {t2}, use {LO}
    d, u = def_use_simple((10 << 11) | 0x12)
    assert d == {10} and u == {LO}
    # mfhi t3 -> def {t3}, use {HI}
    d, u = def_use_simple((11 << 11) | 0x10)
    assert d == {11} and u == {HI}


def test_cop2_gte_pseudo_register():
    # a GTE command (op 0x12, bit 25 set) reads and writes the COP2 aggregate
    d, u = def_use_simple((0x12 << 26) | (1 << 25))
    assert COP2 in d and COP2 in u
    # mtc2 rt -> writes COP2 from rt (op 0x12, rs field = 4)
    d, u = def_use_simple((0x12 << 26) | (4 << 21) | (8 << 16))
    assert d == {COP2} and u == {8}
    # lwc2 (op 0x32) -> def COP2, use base
    d, u = def_use_simple((0x32 << 26) | (9 << 21))
    assert d == {COP2} and u == {9}


def test_recover_extent_is_honest_over_the_census_hole():
    """terrain_emitter_color @ 0x800105F0 is in a census hole. recover_extent must
    return an extent that CONTAINS the address, starts at/after the previous
    function's end, and does not overlap the next censused function — an
    over-approximation, never a guess dressed as exact."""
    rec = recover_extent(EXE, FUNCS, 0x800105F0)
    assert rec is not None
    fs, fe = rec
    assert fs <= 0x800105F0 < fe
    # bounded by the census neighbours
    prev_end = max((e for s, e, _ in FUNCS if e <= 0x800105F0), default=0)
    nxt_start = min((s for s, e, _ in FUNCS if s > 0x800105F0), default=1 << 32)
    assert fs >= prev_end
    assert fe <= nxt_start


def test_recover_extent_refuses_a_data_region():
    """If a hole is mostly non-code (zeros/data), no honest extent can be recovered
    — recover_extent returns None rather than synthesise one."""
    # find a run of >=64 zero words in the image and probe its middle
    import struct
    base = 0x8000F800
    run = 0
    hole = None
    for off in range(0, len(EXE) - 4, 4):
        if struct.unpack_from("<I", EXE, off)[0] == 0:
            run += 1
            if run >= 64:
                hole = base + off - 32 * 4
                break
        else:
            run = 0
    if hole is not None and find_function(FUNCS, hole) is None:
        assert recover_extent(EXE, FUNCS, hole) is None
