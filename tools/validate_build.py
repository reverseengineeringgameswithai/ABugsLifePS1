#!/usr/bin/env python3
"""Whole-image verdict for the substrate build (docs/SUBSTRATE.md).

PASS iff build/substrate/SCUS_942.88.rebuilt is SHA-1-identical to the
original (byte-splat => any difference means an attempted function failed to
match). On mismatch, differing byte ranges are mapped back to census
functions (analysis/functions.json) and listed. Exit 0 = PASS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substrate_common import BUILD, ROOT, load_segments, original_exe, sha1  # noqa: E402


def diff_ranges(a: bytes, b: bytes):
    ranges, start = [], None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y and start is None:
            start = i
        elif x == y and start is not None:
            ranges.append((start, i))
            start = None
    if start is not None:
        ranges.append((start, min(len(a), len(b))))
    if len(a) != len(b):
        ranges.append((min(len(a), len(b)), max(len(a), len(b))))
    return ranges


def main() -> int:
    seg = load_segments()
    rebuilt_path = BUILD / f"{seg['image']}.rebuilt"
    if not rebuilt_path.exists():
        raise SystemExit(f"no rebuilt image at {rebuilt_path} — run tools/build_psx_exe.py")
    original = original_exe(seg)
    rebuilt = rebuilt_path.read_bytes()
    got = sha1(rebuilt)
    if got == seg["sha1"]:
        n = len(seg["attempted"])
        print(f"[validate] PASS — rebuilt image is byte-identical to the original "
              f"(sha1 {got}); {n} function(s) assembled from source")
        return 0

    census = json.loads((ROOT / "analysis" / "functions.json").read_text())
    fns = [(int(r["start"], 16), int(r["end"], 16), r["name"] or r["start"])
           for r in census["functions"] if r["space"] == "resident"]
    print(f"[validate] FAIL — sha1 {got} != {seg['sha1']}")
    for lo, hi in diff_ranges(original, rebuilt)[:20]:
        va = lo - seg["header_bytes"] + seg["load_va"]
        owner = next((n for s, e, n in fns if s <= va < e), "<no census function>")
        print(f"  file 0x{lo:06x}..0x{hi:06x}  va {va:#010x}  in {owner}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
