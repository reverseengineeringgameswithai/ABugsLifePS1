#!/usr/bin/env python3
"""Prioritize the unknown resident functions for naming, by IMPORTANCE.

Phase-5 feedback loop: trace-derived coverage (analysis/traces/level_coverage.json)
+ the static call graph (analysis/functions.json) rank the ~640 classification=
unknown resident functions so naming effort targets the central, broadly-executed
ones first — not merely the smallest/cheapest (that is what decomp_candidates.py
already does for MATCHING).

Importance = executes-at-runtime (dynamic) × how many levels × call-graph centrality
(callers + callees). Names are NOT assigned here — this only ranks. Applying a name
still needs evidence and the three-tier convention (docs / EXP note):
  proven    = dynamic hit + a symbol/psyq/ghidra name or a byte-match  (confirmed)
  inferred  = role deduced from call-graph / args (high|medium; prefix to signal)
  temporary = FUNC_<addr> placeholder — no rename until evidence.

  python tools/naming_priority.py            # write analysis/naming_priority.json + .md
  python tools/naming_priority.py --top 40   # also print the top N
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "analysis" / "functions.json"
COVERAGE = ROOT / "analysis" / "traces" / "level_coverage.json"
OUT_JSON = ROOT / "analysis" / "naming_priority.json"
OUT_MD = ROOT / "analysis" / "naming_priority.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=0)
    args = ap.parse_args()

    fns = [r for r in json.loads(CENSUS.read_text())["functions"]
           if r.get("space") == "resident"]
    by = {int(r["start"], 16): r for r in fns}
    cov = json.loads(COVERAGE.read_text()) if COVERAGE.exists() else {"function_levels": {}}
    fn_levels = {int(a, 16): lv for a, lv in (cov.get("function_levels") or {}).items()}

    rows = []
    for r in fns:
        if r.get("classification") != "unknown":
            continue
        va = int(r["start"], 16)
        n_callers = len(r.get("callers") or [])
        n_callees = len(r.get("callees") or [])
        levels = fn_levels.get(va, [])
        dynamic = bool(levels) or "dynamic" in (r.get("discovery") or [])
        # importance: runtime-proven functions first, then breadth, then centrality
        score = (100 if dynamic else 0) + 8 * len(levels) + 3 * n_callers + n_callees
        rows.append({
            "address": f"{va:#010x}", "size": r["size"], "score": score,
            "dynamic": dynamic, "n_levels": len(levels), "levels": levels,
            "n_callers": n_callers, "n_callees": n_callees,
            "confidence": r.get("confidence"),
            # naming tier the evidence currently supports:
            "tier": ("proven" if (dynamic and r.get("name")
                                  and not r["name"].startswith("FUNC_"))
                     else "inferred" if (dynamic and (n_callers or n_callees))
                     else "temporary"),
        })
    rows.sort(key=lambda x: (-x["score"], x["address"]))

    dynamic_covered = sum(1 for r in rows if r["dynamic"])
    OUT_JSON.write_text(json.dumps({
        "generated_by": "tools/naming_priority.py",
        "note": "Ranks classification=unknown resident fns by naming importance; "
                "does NOT assign names (evidence + three-tier convention required).",
        "unknown_total": len(rows),
        "dynamic_covered": dynamic_covered,
        "candidates": rows,
    }, indent=1) + "\n")

    tiers = {"proven": 0, "inferred": 0, "temporary": 0}
    for r in rows:
        tiers[r["tier"]] += 1
    lines = ["# Unknown-function naming priority (Phase 5)", "",
             f"- unknown resident fns: **{len(rows)}**; runtime-covered (dynamic): "
             f"**{dynamic_covered}**",
             f"- tiers — proven {tiers['proven']} · inferred {tiers['inferred']} · "
             f"temporary {tiers['temporary']} "
             f"(inferred = dynamic + call-graph-connected)", "",
             "| # | addr | sz | levels | callers | callees | tier |",
             "|---|------|----|--------|---------|---------|------|"]
    for i, r in enumerate(rows[:60], 1):
        lines.append(f"| {i} | `{r['address']}` | {r['size']} | {r['n_levels']} | "
                     f"{r['n_callers']} | {r['n_callees']} | {r['tier']} |")
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"[naming] {len(rows)} unknown fns ranked; "
          f"dynamic-covered {tiers['proven'] + tiers['inferred']}; "
          f"wrote {OUT_JSON.name} + {OUT_MD.name}")
    if args.top:
        for i, r in enumerate(rows[:args.top], 1):
            print(f"  {i:>2} {r['address']} sz{r['size']:>4} L{r['n_levels']} "
                  f"c{r['n_callers']}/{r['n_callees']} {r['tier']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
