#!/usr/bin/env python3
"""Phase-3 permuter: drive simonlindholm/decomp-permuter's rich randomizer (~34
transform passes, incl. variable reuse/rename, type variation, cast/no-op insertion,
declaration reorder -- the ones that shift GCC register allocation) with OUR scorer
(`dc_permute.score` -> `compile_at` byte-diff), closing the final register-naming
words the self-contained `dc_permute.py` transform set can't reach.

We reuse only the upstream *randomizer* (Candidate.from_source -> randomize_ast ->
get_source); scoring, annealing, and the toolchain stay ours. Correctness is enforced
by compile+byte-score, so every non-compiling / behaviour-changing mutation is
discarded automatically.

  python tools/dc_permute_upstream.py <addr> <seed.c> [--fn NAME] [--small-data]
                                      [--iters N] [--seed K]

Set ABL_PERMUTER_DIR to override the decomp-permuter checkout
(default ~/abl-toolchain/decomp-permuter).
"""
from __future__ import annotations

import argparse
import math
import os
import random
import re
import sys
from pathlib import Path

_PERMDIR = os.environ.get("ABL_PERMUTER_DIR",
                          str(Path.home() / "abl-toolchain" / "decomp-permuter"))
sys.path.insert(0, _PERMDIR)
sys.path.insert(0, str(Path(__file__).resolve().parent))

sys.stdout.reconfigure(line_buffering=True)
import dc_permute as P  # noqa: E402  (our score() + _want_for())
from src.candidate import Candidate  # noqa: E402
from src.perm.perm import EvalState  # noqa: E402
from src.helpers import (  # noqa: E402
    merge_randomization_weights, get_default_randomization_weights,
)

WEIGHTS = merge_randomization_weights(get_default_randomization_weights("base"), {})


def fn_name_of(src: str) -> str:
    # the function *definition* (has a body), not the extern prototypes
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{", src):
        return m.group(1)
    raise SystemExit("could not find a function definition in the seed")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("addr")
    ap.add_argument("src")
    ap.add_argument("--fn", default=None)
    ap.add_argument("--small-data", action="store_true")
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    va = int(args.addr, 16)
    want = P._want_for(va)
    entry = next((e for e in P.SEG.get("attempted", [])
                  if (int(e["start"], 16) if isinstance(e["start"], str) else e["start"]) == va), None)
    sd = args.small_data or bool(entry and entry.get("small_data"))
    src_path = P.ROOT / args.src
    base = src_path.read_text()
    fn = args.fn or fn_name_of(base)

    best_sc = P.score(base, va, want, sd)
    print(f"[upstream] fn={fn} seed={best_sc}w want={want}B small_data={sd} "
          f"passes={len(WEIGHTS)}")
    if best_sc == 0:
        print("[upstream] already MATCH"); return 0
    rng = random.Random(args.seed)
    best_src = cur_src = base
    cur = best_sc
    for it in range(args.iters):
        try:
            cand = Candidate.from_source(cur_src, EvalState(), fn, WEIGHTS, rng.randrange(1 << 30))
            for _ in range(rng.randint(1, 3)):
                cand.randomize_ast()
            cand_src = cand.get_source()
        except Exception:
            continue
        sc = P.score(cand_src, va, want, sd)
        T = max(0.05, 2.0 * (1 - it / args.iters))
        if sc <= cur or rng.random() < math.exp(-(sc - cur) / T):
            cur_src, cur = cand_src, sc
            if sc < best_sc:
                print(f"[upstream] iter {it}: {best_sc} -> {sc}w")
                best_sc, best_src = sc, cand_src
        if best_sc == 0:
            src_path.write_text(best_src)
            print(f"[upstream] MATCH at iter {it}; wrote {args.src}\n{best_src}")
            return 0
        if it % 60 == 59:
            cur_src, cur = best_src, best_sc
    if best_sc < P.score(base, va, want, sd):
        Path(str(src_path) + ".best").write_text(best_src)
        print(f"[upstream] wrote improved {best_sc}w seed -> {args.src}.best")
    print(f"[upstream] best={best_sc}w after {args.iters} iters")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
