#!/usr/bin/env python3
"""Find writes to an address performed by a CALLEE (memset/memcpy), not by a store site.

WHY THIS EXISTS
---------------
An instruction-level census of store sites is structurally blind to a whole class of
writes: anything a called routine does. The B06/B08 campaign hit this the hard way --
a level transition clears the power slot `0x800A657E`, and the write's PC is inside the
PS1 BIOS at `0xBFC02BB0`, in a generic `memset(dst, val, len)`. A census over the BIOS
finds zero hits and zero `lui 0x800A` material in all 512 KB, because the BIOS never
forms the address; it receives it as an argument.

So "nothing else writes this address" was never establishable from store sites alone,
independently of any aliasing residual.

WHY A `jal` SCAN DOES NOT FIND IT EITHER
----------------------------------------
The game reaches the BIOS through a PsyQ stub table, not a direct call:

    0x8005F7AC  addiu t2, zero, 0xA0     ; the A-function vector
    0x8005F7B0  jr    t2                 ; REGISTER-INDIRECT -- invisible to a jal scan
    0x8005F7B4  addiu t1, zero, 0x2B     ; function number (memset)

A scan for `jal 0x000000A0` / `jal 0x800000A0` returns zero sites in resident code. The
thunk itself, however, is called with an ordinary `jal`, so its call sites ARE
enumerable -- and their arguments are recoverable by the same value analysis the address
census already uses.

METHOD
------
For each configured block-write entry point, resolve `(dst, fill, len)` at every call
site and report which ranges cover the target. Destinations that are not derivable from
the instruction stream (a pointer passed in a register) are reported as UNRESOLVED
rather than dropped -- those are exactly the ones needing a runtime capture, and for the
power slot the unresolved one at `0x80046B68` turned out to be the real writer.

USAGE
    tools/census_callee_writes.py 0x800A657E --json analysis/phase4_callee_writes.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "census_address", Path(__file__).with_name("census_address.py"))
_ca = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ca)

# Block-write entry points. 0x8005F7AC is the PsyQ stub for BIOS A(0x2B); its body is
# `addiu t2,0xA0 / jr t2 / addiu t1,0x2B`, and the loop that actually stores lives at
# 0xBFC02BA0..0xBFC02BB8 in ROM.
BLOCK_WRITERS = {
    0x8005F7AC: "bios_A2B_memset_thunk  (dst=a0, fill=a1, len=a2)",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address", help="target RAM address, e.g. 0x800A657E")
    ap.add_argument("--bytes", type=int, default=2)
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=ROOT / "analysis/functions.json")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    target = int(args.address, 0)
    img = _ca.Image(args.exe, args.functions)
    calls: list = []
    _ca.analyse(img, set(), call_targets=set(BLOCK_WRITERS), calls_out=calls)

    # LAST wins, not first. `analyse` appends a record every fixed-point round, and on
    # round 0 the entry arguments of any function with a caller are still BOTTOM (the
    # empty set) because interprocedural propagation has not run yet. Keeping the FIRST
    # record therefore reports the pre-convergence state: it made this census claim an
    # "unattributed callee destination" at 0x8004DC40 that the very same analysis
    # resolves one round later. Since entry seeds only ever merge upward, the last
    # record is the converged may-set -- including when that set is TOP, which is a
    # truthful "unknown" rather than a stale "empty".
    seen = {}
    for c in calls:
        seen[c["pc"]] = c

    covering, unresolved, other = [], [], []
    for c in sorted(seen.values(), key=lambda x: x["pc"]):
        a = c["args"]
        dst = a.get("a0")
        ln = a.get("a2")
        fill = a.get("a1")
        d0 = dst[0] & 0xFFFFFFFF if dst and len(dst) == 1 else None
        l0 = ln[0] if ln and len(ln) == 1 else None
        rec = {"pc": c["pc"], "function": c["function"],
               "callee": c["callee"],
               "dst": ("0x%08X" % d0) if d0 is not None else None,
               "fill": fill[0] if fill and len(fill) == 1 else None,
               "len": l0}
        if d0 is None or l0 is None:
            unresolved.append(rec)
        elif d0 <= target < d0 + l0:
            covering.append(rec)
        else:
            other.append(rec)

    out = {
        "_comment": (
            "Writes to the target performed by a CALLEE rather than a store site. A "
            "store-site census cannot see these by construction. Regenerate: "
            "tools/census_callee_writes.py"),
        "target": args.address,
        "block_writers": {hex(k): v for k, v in BLOCK_WRITERS.items()},
        "why_a_jal_scan_misses_the_bios": (
            "the thunk reaches the BIOS via `jr t2` with t2 = 0xA0 -- register-indirect. "
            "A scan for jal 0x000000A0 / 0x800000A0 finds ZERO sites in resident code."),
        "call_sites_total": len(seen),
        "covering_target": covering,
        "unresolved_destination": unresolved,
        "not_covering": other,
        "residual_note": (
            "UNRESOLVED destinations are passed in a register and need a runtime capture "
            "(execTrace.addWatch on the store PC with capture=[ra,a0,a2], filtering for "
            "a0 == the target byte). For 0x800A657E that identified 0x80046B68 in "
            "level_load_player_spawn_writer: memset(player_block, 0, 168) on spawn, which "
            "is the clear observed across a level transition."),
    }
    print("target %s -- %d call sites to block-write entry points" % (args.address, len(seen)))
    print("  covering the target (statically resolved): %d" % len(covering))
    for r in covering:
        print("     %s %-38s dst=%s len=%s" % (r["pc"], r["function"][:36], r["dst"], r["len"]))
    print("  UNRESOLVED destination (need runtime capture): %d" % len(unresolved))
    for r in unresolved:
        print("     %s %-38s len=%s" % (r["pc"], r["function"][:36], r["len"]))
    print("  resolved and not covering: %d" % len(other))
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
