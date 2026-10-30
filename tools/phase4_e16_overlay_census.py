#!/usr/bin/env python3
"""Region-census the OVERLAYS for accesses that could reach E16's chunk tables.

THE GAP THIS CLOSES
-------------------
Every residual number produced for E16 so far is RESIDENT-ONLY. The census tool
takes analysis/functions_resident.txt -- 998 functions, 0x80010000..0x80082508 --
and nothing else, so overlay code has never been region-censused at all. That
matters because each level swaps a DIFFERENT overlay into the same region, and
an earlier displacement-only sweep over the .BIN files does not count: it had the
indexed-access blind spot that was the entire reason the affine tool exists.

Until this runs, "nothing else touches the tables" is a statement about the
resident EXE only.

METHOD
------
Overlays carry no symbol table, so function starts are derived the same way the
overlay-ABI work derived them: a function begins at the image's first code word,
and after the delay slot of every `jr ra`. That over-approximates (data decoding
as a false `jr ra` invents a start) which is the safe direction here -- more
analysis units means more, smaller scopes, never a missed access.

Each overlay is then run through the affine region census at its true load base,
and every region-formed site is tested for whether its index could land in any
of E16's three table windows.

Usage: python3 tools/phase4_e16_overlay_census.py [--out analysis/phase4_e16_overlay_census.json]
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

# Load bases from config/phase4_static_analysis.yaml in the accepted tranche.
REGION_A = 0x800B39A0        # per-level LEVEL*.BIN swap buffer
REGION_B = 0x800B5788        # MEMORY.BIN / FMV.BIN

TARGETS = [
    ("markers_0x30_0x57", 0x8009B5A8, 0x8009B648),
    ("markers_0x28_0x2F", 0x8009C210, 0x8009C230),
    ("markers_0x58_0x5F", 0x800A65B0, 0x800A65D0),
]

JR_RA = 0x03E00008


def derive_functions(path: Path, base: int) -> list[tuple[int, int]]:
    """(addr, size) for each derived function start, from `jr ra` boundaries."""
    b = path.read_bytes()
    starts = [0]
    for off in range(0, len(b) - 3, 4):
        if struct.unpack_from("<I", b, off)[0] == JR_RA:
            nxt = off + 8
            if nxt < len(b):
                starts.append(nxt)
    starts = sorted(set(starts))
    out = []
    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(b)
        if end > s:
            out.append((base + s, end - s))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_overlay_census.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16ov_"))
    tool = str(tmp / "abr")
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-o", tool,
                    str(ROOT / "tools/affine_bound_recovery.c")], check=True)

    images = []
    for p in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.BIN")):
        images.append((f"{p.parent.name}/{p.name}", p, REGION_A))
    for rel in ("BITS/MEMORY.BIN", "FMV/FMV.BIN"):
        p = ROOT / "REBUILD/files" / rel
        if p.is_file():
            images.append((rel, p, REGION_B))

    rows, total_sites, total_reach = {}, 0, 0
    for name, path, base in images:
        funcs = derive_functions(path, base)
        if not funcs:
            rows[name] = {"skipped": "no derived function starts"}
            continue
        ftxt = tmp / "f.txt"
        ftxt.write_text("# derived\n" + "".join(
            "0x%08X %d fn_%08X\n" % (a, n, a) for a, n in funcs))
        sj = tmp / "s.json"
        r = subprocess.run([tool, str(path), str(ftxt), "--raw-base", "0x%08X" % base,
                            "--emit-all", "--json", str(sj)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not sj.exists():
            rows[name] = {"error": (r.stderr or "")[-200:]}
            continue
        sites = json.loads(sj.read_text())["sites"]
        total_sites += len(sites)
        # REQUIRED INDEX, not "could reach". Asking whether an unbounded index can
        # reach a window is a tautology -- it flagged 714 of 958 sites on the first
        # run, every one of them unbounded. The discriminating question is how large
        # an index the access would need.
        reaching, hist = [], {"<64": 0, "64-1k": 0, "1k-16k": 0, ">=16k": 0}
        for s in sites:
            bs, st = int(s["base"], 16), abs(s["stride"] or 1)
            for tn, lo, hi in TARGETS:
                need = (lo - bs + st - 1) // st if bs <= lo else -((bs - hi) // st + 1)
                n = abs(need)
                key = ("<64" if n < 64 else "64-1k" if n < 1024
                       else "1k-16k" if n < 16384 else ">=16k")
                hist[key] += 1
                if n < 1024:
                    reaching.append({"pc": s["pc"], "base": s["base"], "stride": s["stride"],
                                     "target": tn, "required_index": n,
                                     "above_window": bs >= hi, "bounded": s["bounded"]})
        total_reach += len(reaching)
        rows[name] = {"load_base": "0x%08X" % base, "size": path.stat().st_size,
                      "derived_functions": len(funcs), "region_formed_sites": len(sites),
                      "priority_sites_needing_index_under_1k": len(reaching),
                      "required_index_distribution": hist,
                      "examples": reaching[:6]}

    out = {
        "_comment": "Overlay region census for E16. Closes the gap that every prior E16 "
                    "residual number was RESIDENT-ONLY. Regenerate: "
                    "tools/phase4_e16_overlay_census.py",
        "generated": str(date.today()),
        "why": "Each level swaps a different overlay into the same region, and overlay "
               "code had never been region-censused. A displacement-only sweep does not "
               "count -- it has the indexed-access blind spot the affine tool exists to fix.",
        "method": "Function starts derived from `jr ra` boundaries (over-approximating, "
                  "which is the safe direction); each image censused at its true load base.",
        "images": len(images),
        "total_region_formed_sites": total_sites,
        "total_overlay_sites_needing_index_under_1k": total_reach,
        "why_not_could_reach": "Asking whether an UNBOUNDED index can reach a "
                               "window is a tautology: it flagged 714 of 958 "
                               "sites, every one unbounded. Required index "
                               "magnitude is the metric that discriminates.",
        "per_image": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"images censused: {len(images)}")
    print(f"region-formed sites in overlay code: {total_sites}")
    print(f"overlay sites needing an index < 1k to reach a table: {total_reach}")
    for n, v in rows.items():
        if v.get("priority_sites_needing_index_under_1k"):
            print(f"   {n}: {v['priority_sites_needing_index_under_1k']} of "
                  f"{v['region_formed_sites']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
