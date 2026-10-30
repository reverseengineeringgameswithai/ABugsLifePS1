#!/usr/bin/env python3
"""Phase-2 exit-gate item 1: every Phase-1 row has a pristine trigger or a
documented fixture blocker.

Joins analysis/mechanics_baseline.yaml (rows + fixture references) with
analysis/phase2_fixture_audit.json (media-classified fixtures) and emits
analysis/phase2_row_coverage.json:

  * pristine_fixtures     — row fixtures the audit classified as pristine media
  * non_pristine_fixtures — row fixtures on MOD/derived media (oracle-ineligible)
  * status                — "pristine_trigger" | "blocked"
  * blocker               — for blocked rows, the documented fixture requirement
                            (the row's fixture_need) — the exit gate accepts a
                            documented blocker, not silence.

Usage: python3 tools/phase2_row_coverage.py
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

import sys
sys.path.insert(0, str(ROOT / "tools"))
import fixture_reference_sets  # noqa: E402


def documented_blocker(row: dict) -> str:
    """Return a non-empty, human-readable blocker for a row without a fixture."""
    fixture_need = row.get("fixture_need")
    if isinstance(fixture_need, str) and fixture_need.strip():
        return fixture_need.strip()
    if isinstance(fixture_need, list):
        joined = "; ".join(str(item).strip() for item in fixture_need
                           if str(item).strip())
        if joined:
            return joined
    # Some bounded static campaigns explicitly require no further fixture.
    # Their retained open-work statement is still the honest reason they do
    # not have a pristine trigger; never emit an empty list as a blocker.
    fallback = row.get("missing") or row.get("next")
    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    raise ValueError(f"{row.get('id')}: blocked row has no documented blocker")


def main() -> int:
    rows = yaml.safe_load((ROOT / "analysis" / "mechanics_baseline.yaml").read_text())["rows"]
    reference_sets = fixture_reference_sets.load()
    fixture_reference_sets.validate_rows(rows, reference_sets)
    audit = json.loads((ROOT / "analysis" / "phase2_fixture_audit.json").read_text())
    media_class = {}
    for coll in ("saves", "movies"):
        for rel, e in audit[coll].items():
            media_class[rel] = e["media_class"]

    coverage = {}
    counts = {"pristine_trigger": 0, "blocked": 0}
    for r in rows:
        pristine, non_pristine, missing = [], [], []
        for fx in fixture_reference_sets.resolve_row(r, reference_sets):
            cls = media_class.get(fx)
            if cls in ("pristine", "pristine_serial"):
                pristine.append(fx)
            elif cls is None:
                missing.append(fx)
            else:
                non_pristine.append(fx)
        status = "pristine_trigger" if pristine else "blocked"
        counts[status] += 1
        coverage[r["id"]] = {
            "status": status,
            "pristine_fixtures": pristine,
            "non_pristine_fixtures": non_pristine,
            "unaudited_fixtures": missing,
            **({} if pristine else {"blocker": documented_blocker(r),
                                    "next_experiment": r["next"]}),
        }
    doc = {
        "_comment": "Phase-2 row coverage: every Phase-1 registry row either has a "
                    "pristine-media fixture (audited) or documents its fixture blocker. "
                    "Regenerate: tools/phase2_row_coverage.py (after phase2_oracle.py).",
        "generated": date.today().isoformat(),
        "counts": counts,
        "rows": coverage,
    }
    out = ROOT / "analysis" / "phase2_row_coverage.json"
    out.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"[row_coverage] wrote {out}: {counts}")
    blocked = [rid for rid, c in coverage.items() if c["status"] == "blocked"]
    print(f"  blocked rows ({len(blocked)}): {', '.join(blocked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
