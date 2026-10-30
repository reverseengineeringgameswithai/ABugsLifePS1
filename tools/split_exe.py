#!/usr/bin/env python3
"""Carve the r2 disassembly listing into per-function reference files
(decomp substrate v0 — docs/SUBSTRATE.md).

Splits extracted/re_baseline/SCUS_942.88.asm along the census boundaries
(analysis/functions.json) into asm/nonmatchings/resident/<addr>_<name>.s.
These are REFERENCE LISTINGS for a human converting a function to a
hand-written assemblable .s in asm/hand_written/ — they are not themselves
assembler input. Both asm/ trees are untracked (derived from the copyrighted
EXE; preservation policy) and fully regenerable:

  python tools/re_baseline.py --disasm     # refresh the listing
  python tools/function_census.py          # refresh boundaries
  python tools/split_exe.py [--min-size N] [--only ADDRHEX[,ADDRHEX..]]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LISTING = ROOT / "extracted" / "re_baseline" / "SCUS_942.88.asm"
CENSUS = ROOT / "analysis" / "functions.json"
OUTDIR = ROOT / "asm" / "nonmatchings" / "resident"

_ADDR = re.compile(r"0x(80[0-9a-f]{6})\b")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-size", type=int, default=0, help="skip functions smaller than N bytes")
    ap.add_argument("--only", help="comma-separated hex start addrs to emit")
    args = ap.parse_args()
    only = ({int(a, 16) for a in args.only.split(",")} if args.only else None)

    census = json.loads(CENSUS.read_text())
    fns = sorted(((int(r["start"], 16), int(r["end"], 16), r["name"])
                  for r in census["functions"] if r["space"] == "resident"))
    if not LISTING.exists():
        raise SystemExit(f"missing {LISTING} — run: python tools/re_baseline.py --disasm")

    # bucket listing lines by the census function owning their address
    lines_by_fn: dict[int, list[str]] = {}
    starts = [s for s, _, _ in fns]
    import bisect
    for line in LISTING.read_text(errors="replace").splitlines():
        mo = _ADDR.search(line)
        if not mo:
            continue
        va = int(mo.group(1), 16)
        i = bisect.bisect_right(starts, va) - 1
        if i >= 0 and fns[i][0] <= va < fns[i][1]:
            lines_by_fn.setdefault(fns[i][0], []).append(line)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    emitted = 0
    for start, end, name in fns:
        if only is not None and start not in only:
            continue
        if end - start < args.min_size:
            continue
        body = lines_by_fn.get(start)
        if not body:
            continue
        fname = f"{start:08x}" + (f"_{name}" if name else "") + ".s"
        header = (f"# REFERENCE listing (r2 pD) — {name or 'unnamed'} "
                  f"{start:#010x}..{end:#010x} ({end - start} B)\n"
                  f"# NOT assembler input. Convert to asm/hand_written/ + register in\n"
                  f"# config/segments.yml to attempt a match (docs/SUBSTRATE.md).\n")
        (OUTDIR / fname).write_text(header + "\n".join(body) + "\n")
        emitted += 1
    print(f"[split] wrote {emitted} reference listings -> {OUTDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
