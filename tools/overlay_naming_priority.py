#!/usr/bin/env python3
"""Rank the unnamed OVERLAY functions by naming importance (overlay analogue of
tools/naming_priority.py). Importance = executes-at-runtime (overlay_coverage.json)
× size × call-graph centrality (callers incl. the resident->overlay entry surface).
Writes analysis/overlay_naming_priority.{json,md}; does NOT assign names.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis" / "functions.json"
COV = ROOT / "analysis" / "traces" / "overlay_coverage.json"
OUT_JSON = ROOT / "analysis" / "overlay_naming_priority.json"
OUT_MD = ROOT / "analysis" / "overlay_naming_priority.md"


def main() -> int:
    fj = json.loads(CENSUS.read_text())
    cov = json.loads(COV.read_text()) if COV.exists() else {"overlays": {}}
    covered = {(ov, s) for ov, m in cov.get("overlays", {}).items() for s in m}

    rows = []
    for f in fj["functions"]:
        if f.get("space") != "overlay" or f.get("range_type") != "code":
            continue
        if f.get("name"):
            continue                                   # already named
        ov, start = f["overlay"], f["start"]
        n_callers = len(f.get("callers", []))
        n_callees = len(f.get("callees", []))
        hit = (ov, start) in covered
        score = (100 if hit else 0) + min(f["size"] // 8, 80) + 3 * n_callers + n_callees
        rows.append({"overlay": ov, "address": start, "size": f["size"],
                     "dynamic": hit, "n_callers": n_callers, "n_callees": n_callees,
                     "score": score,
                     "tier": ("inferred" if hit and (n_callers or n_callees)
                              else "temporary")})
    rows.sort(key=lambda r: (-r["score"], r["overlay"], r["address"]))

    dynamic_covered = sum(1 for r in rows if r["dynamic"])
    OUT_JSON.write_text(json.dumps({
        "generated_by": "tools/overlay_naming_priority.py",
        "note": "Ranks unnamed overlay code fns; coverage from overlay_coverage.json.",
        "unknown_total": len(rows),
        "dynamic_covered": dynamic_covered,
        "candidates": rows,
    }, indent=1) + "\n")

    lines = ["# Overlay-function naming priority", "",
             f"- unnamed overlay fns: **{len(rows)}**; runtime-covered (dynamic): "
             f"**{dynamic_covered}**", "",
             "| # | overlay | addr | sz | dyn | callers | callees | tier |",
             "|---|---------|------|----|-----|---------|---------|------|"]
    for i, r in enumerate(rows[:60], 1):
        lines.append(f"| {i} | {r['overlay']} | `{r['address']}` | {r['size']} | "
                     f"{'Y' if r['dynamic'] else ''} | {r['n_callers']} | {r['n_callees']} "
                     f"| {r['tier']} |")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"[ovl-naming] {len(rows)} unnamed overlay fns ranked; "
          f"dynamic-covered {dynamic_covered}; wrote {OUT_JSON.name} + {OUT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
