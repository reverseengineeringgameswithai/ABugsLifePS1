#!/usr/bin/env python3
"""Census the resident code that analysis/functions_resident.txt does not cover.

THE HOLE
--------
Every static residual figure produced for E16 is relative to the 998 functions in
analysis/functions_resident.txt. Those cover 422,632 of the text segment's
468,992 bytes -- 90.1%. The other 46,360 bytes, in 79 gaps, were never analysed
by anything: not the region census, not the bound recovery, not the frontier.

This was not noticed by inspection. The validated LEVEL01 campaign movie caught a
PC touching an E16 table that the static frontier had not predicted, and that PC
(0x80010BF4, `lhu $t9,0($t9)` -- the accessLog reports the following instruction)
lies inside the second-largest gap, 0x800102D4..0x80013108. The runtime falsifier
did exactly the job it was declared for.

WHAT THIS DOES
--------------
Derives function starts for each uncovered range the same way the overlay census
does -- a function begins at the range start and after the delay slot of every
`jr ra` -- and runs the affine region census over them, so the gaps are measured
rather than assumed empty.

Over-approximating starts (data decoding as a false `jr ra` invents one) is the
safe direction: more, smaller analysis units, never a missed access.

Usage: python3 tools/phase4_resident_gap_census.py
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
FUNCS = ROOT / "analysis/functions_resident.txt"
TEXT_LO, TEXT_HI = 0x80010000, 0x80082800
HDR = 0x800
JR_RA = 0x03E00008

TARGETS = [("markers_0x30_0x57", 0x8009B5A8, 0x8009B648),
           ("markers_0x28_0x2F", 0x8009C210, 0x8009C230),
           ("markers_0x58_0x5F", 0x800A65B0, 0x800A65D0)]


def gaps() -> list[tuple[int, int]]:
    fns = []
    for line in FUNCS.read_text().splitlines():
        if line.startswith("#"):
            continue
        p = line.split()
        if len(p) >= 2:
            fns.append((int(p[0], 16), int(p[1])))
    fns.sort()
    out, cur = [], TEXT_LO
    for a, n in fns:
        if a > cur:
            out.append((cur, a - cur))
        cur = max(cur, a + n)
    if cur < TEXT_HI:
        out.append((cur, TEXT_HI - cur))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_resident_gap_census.json"))
    args = ap.parse_args()

    img = EXE.read_bytes()
    g = gaps()
    total_gap = sum(n for _, n in g)

    # derive starts inside every gap
    derived: list[tuple[int, int]] = []
    for a, n in g:
        starts = [a]
        for off in range(a, a + n - 3, 4):
            fo = HDR + off - TEXT_LO
            if fo + 4 > len(img):
                break
            if struct.unpack_from("<I", img, fo)[0] == JR_RA and off + 8 < a + n:
                starts.append(off + 8)
        starts = sorted(set(starts))
        for i, s in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else a + n
            if end > s:
                derived.append((s, end - s))

    tmp = Path(tempfile.mkdtemp(prefix="gapcen_"))
    ftxt = tmp / "gapfns.txt"
    ftxt.write_text("# derived from gaps in functions_resident.txt\n" +
                    "".join("0x%08X %d gapfn_%08X\n" % (a, n, a) for a, n in derived))
    tool = str(tmp / "abr")
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", tool,
                    str(ROOT / "tools/affine_bound_recovery.c")], check=True)
    sj = tmp / "s.json"
    r = subprocess.run([tool, str(EXE), str(ftxt), "--emit-all", "--json", str(sj)],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0 or not sj.exists():
        print(r.stderr[-500:], file=sys.stderr)
        raise SystemExit("gap census failed")
    sites = json.loads(sj.read_text())["sites"]

    hist = {"<64": 0, "64-1k": 0, "1k-16k": 0, ">=16k": 0}
    priority = []
    for s in sites:
        b, st = int(s["base"], 16), abs(s["stride"] or 1)
        best = None
        for tn, lo, hi in TARGETS:
            need = abs((lo - b + st - 1) // st if b <= lo else -((b - hi) // st + 1))
            if best is None or need < best[0]:
                best = (need, tn)
        need, tn = best
        hist["<64" if need < 64 else "64-1k" if need < 1024
             else "1k-16k" if need < 16384 else ">=16k"] += 1
        if need < 1024:
            priority.append({"pc": s["pc"], "base": s["base"], "stride": s["stride"],
                             "required_index": need, "target": tn, "bounded": s["bounded"]})

    out = {
        "_comment": "Region census of the resident code that functions_resident.txt does "
                    "not cover. Regenerate: tools/phase4_resident_gap_census.py",
        "generated": str(date.today()),
        "how_this_hole_was_found": (
            "Not by inspection. The validated LEVEL01 campaign movie caught 0x80010BF8 "
            "touching an E16 table -- accessLog reports the instruction AFTER the access, "
            "so the access is 0x80010BF4, `lhu $t9,0($t9)` -- and that PC lies inside the "
            "gap 0x800102D4..0x80013108. The declared runtime falsifier did its job."),
        "text_segment_bytes": TEXT_HI - TEXT_LO,
        "covered_by_functions_resident": (TEXT_HI - TEXT_LO) - total_gap,
        "uncovered_bytes": total_gap,
        "uncovered_percent": round(100.0 * total_gap / (TEXT_HI - TEXT_LO), 1),
        "gap_count": len(g),
        "largest_gaps": [{"start": "0x%08X" % a, "bytes": n}
                         for a, n in sorted(g, key=lambda x: -x[1])[:8]],
        "derived_functions_in_gaps": len(derived),
        "region_formed_sites_in_gaps": len(sites),
        "required_index_distribution": hist,
        "priority_sites_needing_index_under_1k": len(priority),
        "priority_sites": priority[:40],
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"uncovered: {total_gap:,} bytes ({out['uncovered_percent']}%) in {len(g)} gaps")
    print(f"derived functions: {len(derived)}   region-formed sites: {len(sites)}")
    print(f"required-index distribution: {hist}")
    print(f"priority sites (<1k): {len(priority)}")
    for p in priority[:10]:
        print(f"   {p['pc']} base={p['base']} stride={p['stride']} "
              f"need={p['required_index']} -> {p['target']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
