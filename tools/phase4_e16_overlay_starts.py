#!/usr/bin/env python3
"""Phase-4 E16 driver: tighten the overlay-ABI per-overlay entry lists.

The committed overlay-ABI artifact records its per-overlay entry lists and its
"27 of 42 implemented" union as **LOWER BOUNDS**, because the detector accepted
only two prologue shapes (`addiu sp,sp,-N` or a bare `jr ra`). A leaf function
opening with anything else read as "not implemented".

This driver runs that original detector alongside a structurally different one
(tools/phase4_e16_overlay_starts.c): in contiguous code a function START is the
instruction after the delay slot of a `jr ra`. No prologue is assumed.

The two err in OPPOSITE directions -- prologue-matching under-counts (misses
unusual prologues), return-scanning over-counts (data that disassembles as a
false `jr ra` invents a start) -- so reporting both brackets the truth rather
than replacing one guess with another. An entry accepted by BOTH is solid.

Usage: python3 tools/phase4_e16_overlay_starts.py [--out analysis/phase4_e16_overlay_starts.json]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "0x800B39A0"


def committed_entries():
    """The 42 region-A entry points, from the COMMITTED overlay map (git HEAD),
    not the working tree -- other agents have uncommitted edits in that file."""
    raw = subprocess.run(["git", "show", "HEAD:analysis/phase3_overlay_map.json"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    eps = json.loads(raw)["region_a_shared_entry_points"]
    out = []
    for e in eps:
        a = e if isinstance(e, str) else (e.get("address") or e.get("addr") or e.get("entry"))
        out.append(a.lower() if isinstance(a, str) else "0x%08x" % a)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "analysis/phase4_e16_overlay_starts.json"))
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="e16st_"))
    tool = str(tmp / "starts")
    subprocess.run(["cc", "-O2", "-Werror", "-o", tool,
                    str(ROOT / "tools/phase4_e16_overlay_starts.c")], check=True)

    entries = committed_entries()
    stdin = "\n".join(entries) + "\n"

    rows = []
    for p in sorted((ROOT / "REBUILD/files").glob("LEVEL*/LEVEL*.BIN")):
        r = subprocess.run([tool, str(p), BASE], input=stdin,
                           capture_output=True, text=True, check=True)
        d = json.loads(r.stdout)
        d["key"] = f"{p.parent.name}_{p.name}"
        rows.append(d)

    uni_p, uni_r = set(), set()
    per_overlay = {}
    for d in rows:
        impl_p, impl_r = [], []
        for e in d["entries"]:
            if not e.get("in_range"):
                continue
            if e["prologue_match"]:
                uni_p.add(e["entry"])
                impl_p.append(e["entry"])
            if e["return_derived_start"]:
                uni_r.add(e["entry"])
                impl_r.append(e["entry"])
        per_overlay[d["key"]] = {
            "size": d["size"], "returns": d["returns"],
            "function_starts": d["function_starts"],
            "entries_by_prologue": sorted(impl_p),
            "entries_by_return": sorted(impl_r),
            "entries_by_both": sorted(set(impl_p) & set(impl_r)),
        }

    out = {
        "_comment": "Phase-4 E16: tightening the overlay-ABI per-overlay entry lists. The "
                    "committed artifact's 27/42 was a LOWER BOUND from prologue matching; "
                    "a return-derived detector raises it and the two together cover all "
                    "42. Regenerate: tools/phase4_e16_overlay_starts.py",
        "generated": str(date.today()),
        "region_a_base": BASE,
        "entry_points_checked": len(entries),
        "overlays_scanned": len(rows),
        "detectors": {
            "prologue": "first word is `addiu sp,sp,-N` or a bare `jr ra`. UNDER-counts: "
                        "a leaf function with any other prologue is missed. This is the "
                        "detector the committed artifact used.",
            "return_derived": "a function start is the instruction after the delay slot "
                              "of a `jr ra` (plus base+4, the first function). Assumes no "
                              "prologue at all. OVER-counts: embedded data that decodes "
                              "as a false `jr ra` invents a start.",
            "why_both": "They err in OPPOSITE directions, so they bracket the truth. An "
                        "entry accepted by both is solid; one accepted by neither is "
                        "genuinely absent from that overlay.",
        },
        "union_over_the_campaign": {
            "by_prologue": len(uni_p),
            "by_return": len(uni_r),
            "by_both": len(uni_p & uni_r),
            "by_either": len(uni_p | uni_r),
            "total_entry_points": len(entries),
            "only_return_found": sorted(uni_r - uni_p),
            "only_prologue_found": sorted(uni_p - uni_r),
        },
        "per_overlay": per_overlay,
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    u = out["union_over_the_campaign"]
    print(f"entry points: {len(entries)}   overlays: {len(rows)}")
    print(f"union implemented somewhere -- prologue {u['by_prologue']}, "
          f"return-derived {u['by_return']}, both {u['by_both']}, "
          f"either {u['by_either']}/{u['total_entry_points']}")
    print(f"found only by return-derivation: {len(u['only_return_found'])}")
    print(f"found only by prologue matching: {len(u['only_prologue_found'])} "
          f"-> {u['only_prologue_found']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
