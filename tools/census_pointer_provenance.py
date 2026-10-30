#!/usr/bin/env python3
"""Resolve -- not merely count -- the pointer-based accesses in the slot census.

WHY THIS EXISTS
---------------
`tools/census_address.py` reports every access whose base register it could not pin to
a constant as an unresolved residual. For `0x800A657E` that residual was 937 same-width
accesses in related functions, 238 indirect calls and 4,967 more across the overlays.

Enumerating that residual is not bounding it. An adversarial review made exactly this
point, and it is right: `0x8004AFB0` -- a real writer of the slot -- lives inside that
class, so "none of the residual was ever observed writing the slot" is a statement
about the fixtures, not about the code. A census that stops at "this pointer might
alias" has not closed anything.

The reason the residual exists is structural: the base analysis turns every value
loaded from memory into TOP. But this game reaches almost every object through a
pointer held in a global, and those globals are written with constants. So the
information is recoverable -- it just is not in the instruction stream at the point of
use.

WHAT THIS DOES
--------------
A fixed-point loop over the whole resident image:

  1. run the value analysis, recording every store whose ADDRESS resolves, together
     with the value stored;
  2. build a global value map -- address -> set of constants it can hold -- from those
     stores, unioned with the global's INITIAL value in the EXE image;
  3. re-run with that map switched on, so a `lw` from a known global propagates the
     pointer instead of collapsing to TOP;
  4. repeat until neither the map nor the hit set changes.

Each round strictly increases what is known, so the loop terminates.

SOUNDNESS -- WHICH DIRECTION EACH RESULT IS GOOD FOR
----------------------------------------------------
The global map is OPTIMISTIC: a store through an unresolved pointer could write any
global, and this tool cannot see it. That has opposite consequences for the two things
one might want to conclude:

  * FINDING a new access is SOUND. If the analysis resolves a base to the slot, that
     is a real code path, and it is reported for disassembly-level confirmation.
  * PROVING a base never reaches the slot is NOT sound from this tool alone, because
     an unseen store could put the slot's address into the global. The count of
     unresolved stores is reported for exactly this reason -- it is the size of the
     hole in the exclusion argument, and it must be quoted alongside any claim of
     disjointness.

So: use it to hunt, and to shrink the residual; quote `unresolved_stores` whenever
using it to exclude.

USAGE
    tools/census_pointer_provenance.py 0x800A657E --block 0x800A6500
    tools/census_pointer_provenance.py 0x800A657E --json analysis/out.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import census_address as ca

ROOT = Path(__file__).resolve().parent.parent
STACK_LO, STACK_HI = 0x00080000, 0x00180000     # the analysis' synthetic stack sentinel


def build_globals(img, store_obs, cap: int) -> tuple[dict, int, int]:
    """address -> frozenset of constants it can hold. Returns (map, tainted, skipped)."""
    acc: dict[int, set] = {}
    tainted: set[int] = set()
    for ea, width, vals in store_obs:
        if width != 4:                    # only word stores can hold a pointer
            continue
        if STACK_LO <= ea < STACK_HI:     # stack slot, not a global
            continue
        if vals is None:
            tainted.add(ea)               # stored an unknown value -> unusable
            continue
        acc.setdefault(ea, set()).update(vals)

    out, skipped = {}, 0
    for ea, vals in acc.items():
        if ea in tainted:
            skipped += 1
            continue
        if len(vals) > cap:
            skipped += 1
            continue
        out[ea] = frozenset(vals)

    # Globals never stored to still have their INITIAL value from the EXE image. A
    # pointer table baked into .data is invisible to a store scan but is exactly the
    # kind of indirection this analysis needs to follow.
    for ea in list(out):
        if img.base <= ea < img.end - 4:
            try:
                init = img.word(ea)
            except Exception:
                continue
            if len(out[ea]) < cap:
                out[ea] = frozenset(out[ea] | {init})
    return out, len(tainted), skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address")
    ap.add_argument("--bytes", type=int, default=2)
    ap.add_argument("--block", default=None)
    ap.add_argument("--exe", type=Path, default=ROOT / "REBUILD" / "files" / "SCUS_942.88")
    ap.add_argument("--functions", type=Path, default=ROOT / "analysis/functions.json")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--cap", type=int, default=ca.MAX_VALS)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if not args.exe.exists():
        print("INPUTS ABSENT -- %s is gitignored (copyrighted); provision with "
              "tools/verify_repro_inputs.py --provision" % args.exe.name)
        return 2

    addr = int(args.address, 16)
    targets = set(range(addr, addr + args.bytes))
    img = ca.Image(args.exe, args.functions)

    rounds, gmap = [], None
    prev_key = None
    for i in range(args.rounds):
        store_obs = []
        hits, unresolved, indirect = ca.analyse(
            img, targets, globals_map=gmap, store_obs=store_obs)
        gmap, tainted, skipped = build_globals(img, store_obs, args.cap)
        key = (len(hits), len(unresolved), len(gmap))
        rounds.append({"round": i, "hits": len(hits), "unresolved": len(unresolved),
                       "indirect_calls": indirect, "globals_resolved": len(gmap),
                       "globals_tainted": tainted, "globals_over_cap": skipped,
                       "stores_seen": len(store_obs)})
        print("round %d: hits=%d unresolved=%d globals=%d (tainted %d, over-cap %d)"
              % (i, len(hits), len(unresolved), len(gmap), tainted, skipped), flush=True)
        if key == prev_key:
            break
        prev_key = key

    # Final pass with the converged map.
    store_obs = []
    hits, unresolved, indirect = ca.analyse(
        img, targets, globals_map=gmap, store_obs=store_obs)
    unresolved_stores = sum(1 for u in unresolved if u["kind"] == "write")

    base_hits, base_unres, _ = ca.analyse(img, targets)
    base_pcs = {h["pc"] for h in base_hits}
    new = [h for h in hits if h["pc"] not in base_pcs]

    out = {
        "_comment": "Pointer-provenance resolution of the slot census residual. "
                    "Finding an access is sound; EXCLUDING one is not sound from this "
                    "tool alone -- quote unresolved_stores as the hole in any "
                    "disjointness argument. Regenerate: "
                    "tools/census_pointer_provenance.py",
        "target": "0x%08X" % addr,
        "baseline": {"hits": len(base_hits), "unresolved": len(base_unres)},
        "with_provenance": {"hits": len(hits), "unresolved": len(unresolved),
                            "indirect_calls": indirect},
        "residual_reduction": len(base_unres) - len(unresolved),
        "unresolved_stores": unresolved_stores,
        "soundness": "globals_map is optimistic: %d stores still have an unresolved "
                     "destination and could write any global, so a base proven "
                     "disjoint here is disjoint ONLY under the assumption that none of "
                     "those %d stores plants this address in a global."
                     % (unresolved_stores, unresolved_stores),
        "rounds": rounds,
        "newly_resolved_accesses": new,
        "all_accesses": hits,
    }
    if args.json:
        args.json.write_text(json.dumps(out, indent=1) + "\n")
        print("wrote", args.json)

    print("\nbaseline:   %d accesses, %d unresolved" % (len(base_hits), len(base_unres)))
    print("provenance: %d accesses, %d unresolved  (residual -%d)"
          % (len(hits), len(unresolved), len(base_unres) - len(unresolved)))
    if new:
        print("\nNEWLY RESOLVED ACCESSES TO THE TARGET (confirm each by disassembly):")
        for h in new:
            print("  %s  %-28s %-5s %s" % (h["pc"], h["insn"], h["kind"], h["function"]))
    else:
        print("\nno new accesses -- the provenance pass found nothing the baseline missed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
