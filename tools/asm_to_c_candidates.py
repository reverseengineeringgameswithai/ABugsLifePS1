#!/usr/bin/env python3
"""dc-0 selector: rank the already-matched HAND-ASM (.s) resident functions for
asm -> byte-exact-C rewriting.

decomp_candidates.py surfaces only UNMATCHED code (now empty). This selector runs
over the 837 `.s` entries in config/segments.yml, joins the census + the proven
`_features` classifier, and ranks them by convertibility for the C campaign:

  class      game / sdk_psyq / unknown / bios_thunk / crt0   (census classification)
  convert    plain | gp | jr_table | fragment | no_return    (route/difficulty)
  priority   plain > gp ; small > large ; understood (game/named) valued

Output: analysis/asm_to_c_queue.json  (deterministic; feeds the batch flow).
Excludes jr_table + fragment + no_return from the ready queue (deferred/hard).

  python3 tools/asm_to_c_candidates.py [--class game,sdk_psyq] [--top N]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from decomp_candidates import _features, _behavior_known, _words  # noqa: E402

EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
CENSUS = ROOT / "analysis" / "functions.json"
SEGMENTS = ROOT / "config" / "segments.yml"
OUT = ROOT / "analysis" / "asm_to_c_queue.json"


def _hard_signals(exe: bytes, start: int, end: int, fn_starts: set[int]) -> dict:
    """Detect features that a byte-exact C source CANNOT reproduce, even for a
    'plain' function: cop2/GTE register moves (swc2/lwc2/cop2), BIOS syscall/break,
    and an internal tail-`j` (terminates by jumping into the MIDDLE of a shared
    routine — e.g. the mover-VM dispatch loop — which is a fallthrough, not a
    standalone C return). These are the reason ~1/4 of nominally-'plain' leaves
    are not C-convertible; flagging them keeps the ready queue honest."""
    ws = _words(exe, start, end)
    cop2 = any((w >> 26) in (0x12, 0x32, 0x3a) for w in ws)          # COP2 / LWC2 / SWC2
    syscall = any((w & 0xFC00003F) == 0x0000000C for w in ws)       # syscall / break family
    has_jr_ra = any(w == 0x03E00008 for w in ws)
    tail_j_internal = False
    for i, w in enumerate(ws):
        if (w >> 26) == 2:                                           # plain j (not jal)
            pc = start + i * 4
            tgt = (pc & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
            if tgt not in fn_starts:                                 # mid-routine jump
                tail_j_internal = True
    return {"cop2": cop2, "syscall": syscall, "has_jr_ra": has_jr_ra,
            "tail_j_internal": tail_j_internal}


def convert_class(f: dict, h: dict) -> str:
    if not f["has_return"]:
        return "no_return"
    if f["fragment"]:
        return "fragment"
    if f["jr_table"]:
        return "jr_table"
    # hard blockers: byte-exact C is impossible for these even though the route
    # is otherwise linear (see _hard_signals).
    if h["cop2"]:
        return "cop2"
    if h["syscall"]:
        return "syscall"
    if not h["has_jr_ra"]:            # terminates via tail-j only, no real return
        return "tail_j"
    if f["uses_gp"]:
        return "gp"
    return "plain"


# ready = the classes the proven machinery converts today; the rest are deferred.
# jr_table/fragment/no_return = route-blocked; cop2/syscall/tail_j = byte-exact-C
# is impossible (GTE moves / BIOS traps / mid-loop fallthrough).
READY = {"plain", "gp"}
# lower rank sorts first within the ready queue
_ROUTE_RANK = {"plain": 0, "gp": 1}
_CLASS_RANK = {"game": 0, "unknown": 1, "sdk_psyq": 2, "bios_thunk": 3, "crt0": 4}


def build():
    exe = EXE.read_bytes()
    census = {int(f["start"], 16): f
              for f in json.loads(CENSUS.read_text())["functions"]
              if f["space"] == "resident" and f.get("range_type") == "code"}
    fn_starts = set(census)
    seg = yaml.safe_load(SEGMENTS.read_text())
    rows = []
    for a in seg.get("attempted", []):
        src = a.get("source", "")
        if not src.endswith(".s"):                # only hand-asm entries
            continue
        start = a["start"] if isinstance(a["start"], int) else int(a["start"], 16)
        rec = census.get(start)
        if not rec:
            continue
        f = _features(exe, rec)
        h = _hard_signals(exe, start, int(rec["end"], 16), fn_starts)
        cc = convert_class(f, h)
        known = _behavior_known(rec)
        rows.append({
            "start": rec["start"], "end": rec["end"], "size": f["size"],
            "name": rec.get("name"), "classification": rec.get("classification"),
            "convert": cc, "ready": cc in READY,
            "cop2": h["cop2"], "syscall": h["syscall"],
            "tail_j": not h["has_jr_ra"],
            "has_frame": f["has_frame"], "n_callees": f["n_callees"],
            "n_callers": f["n_callers"], "known": known, "dynamic": f["dynamic"],
        })
    # deterministic ordering: ready first, then route, then value, then size, then VA
    rows.sort(key=lambda r: (
        not r["ready"],
        _ROUTE_RANK.get(r["convert"], 9),
        _CLASS_RANK.get(r["classification"], 9),
        0 if r["known"] else 1,
        r["size"],
        int(r["start"], 16),
    ))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--class", dest="klass", help="filter census classes, comma list")
    ap.add_argument("--top", type=int, help="print only the top N ready rows")
    args = ap.parse_args()
    rows = build()
    OUT.write_text(json.dumps(rows, indent=1) + "\n")

    from collections import Counter
    ready = [r for r in rows if r["ready"]]
    by = Counter((r["classification"], r["convert"]) for r in rows)
    print(f"[asm2c] {len(rows)} hand-asm fns -> {OUT.relative_to(ROOT)}")
    print(f"  ready (plain+gp): {len(ready)}  |  deferred: {len(rows) - len(ready)}")
    for (cl, cc), n in sorted(by.items()):
        print(f"    {cl:11s} {cc:9s} {n}")
    show = rows
    if args.klass:
        ks = set(args.klass.split(","))
        show = [r for r in rows if r["classification"] in ks]
    if args.top:
        print(f"\n  top {args.top} ready:")
        for r in [r for r in show if r["ready"]][:args.top]:
            print(f"    {r['start']} {r['size']:>5}B {r['convert']:5s} "
                  f"{r['classification']:9s} {r['name'] or '(unnamed)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
