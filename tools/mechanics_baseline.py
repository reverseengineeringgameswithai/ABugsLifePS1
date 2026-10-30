#!/usr/bin/env python3
"""Validate and report the Phase-1 whole-game mechanics baseline registry.

Registry: analysis/mechanics_baseline.yaml (machine-readable twin of the vault note
"Whole-Game Mechanics Baseline"). Enforces the Phase-1 exit-gate shape:

  * every row has a status from the fixed vocabulary, an evidence class, explicit
    missing-work text, a fixture requirement, and a NEXT evidence-producing experiment;
  * every referenced existing fixture is actually present on disk;
  * the campaign matrix covers Training + stages 1-15 + 3 bonus rows;
  * every manual enemy family and boss has a row;
  * no hidden buckets — sections must meet their minimum row counts.

Usage:
    python3 tools/mechanics_baseline.py            # validate (exit 1 on violation)
    python3 tools/mechanics_baseline.py --report   # validate + coverage report
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "analysis" / "mechanics_baseline.yaml"

SECTION_MINIMUMS = {"A": 16, "B": 14, "C": 18, "D": 20, "E": 16, "F": 19}
REQUIRED_STAGE_ROWS = ["F00_training"] + [f"F{i:02d}_" for i in range(1, 16)] + \
    ["F16_bonus1", "F17_bonus2", "F18_bonus3"]
REQUIRED_FAMILY_KEYWORDS = [
    "grasshopper", "mosquito", "flies", "cockroach", "spider", "mites",
    "centipede", "beetle", "wasp", "daddy",  # 13 manual families (some share rows)
]
REQUIRED_BOSSES = ["thumper", "bird", "thud", "molt", "hopper"]
EVIDENCE_CLASSES = {"manual", "pristine_observation", "static_code", "runtime_trace",
                    "asset_disc", "secondary_lead"}


def load() -> dict:
    return yaml.safe_load(REGISTRY.read_text())


def validate(doc: dict, require_fixtures: bool = True) -> list:
    # require_fixtures=False skips the fixture_have on-disk check: operator
    # recordings (.sav/.movie) are local-only media and absent from a clean
    # source archive; everything else validates everywhere.
    errors = []
    statuses = set(doc.get("statuses") or [])
    rows = doc.get("rows") or []
    seen = set()
    for r in rows:
        rid = r.get("id", "<missing id>")
        if rid in seen:
            errors.append(f"{rid}: duplicate id")
        seen.add(rid)
        if r.get("section") not in SECTION_MINIMUMS:
            errors.append(f"{rid}: bad section {r.get('section')!r}")
        if r.get("status") not in statuses:
            errors.append(f"{rid}: status {r.get('status')!r} not in vocabulary")
        for field in ("name", "missing", "fixture_need", "next"):
            if not str(r.get(field) or "").strip():
                errors.append(f"{rid}: empty required field '{field}'")
        ev = r.get("evidence") or []
        if not ev:
            errors.append(f"{rid}: no evidence class")
        for e in ev:
            if e not in EVIDENCE_CLASSES:
                errors.append(f"{rid}: unknown evidence class {e!r}")
        if not isinstance(r.get("bindings", []), list):
            errors.append(f"{rid}: bindings must be a list (empty = explicit unknown)")
        for fx in r.get("fixture_have") or []:
            if require_fixtures and not (ROOT / fx).exists():
                errors.append(f"{rid}: fixture_have file missing on disk: {fx}")
        low = (r.get("name", "") + " " + rid).lower()
        if any(w in low for w in ("miscellaneous", " misc ", "other gameplay")):
            errors.append(f"{rid}: generic bucket name violates the exit gate")

    by_section: dict = {}
    for r in rows:
        by_section.setdefault(r.get("section"), []).append(r)
    for sec, minimum in SECTION_MINIMUMS.items():
        n = len(by_section.get(sec, []))
        if n < minimum:
            errors.append(f"section {sec}: {n} rows < required minimum {minimum}")

    ids = {r["id"] for r in rows if "id" in r}
    for prefix in REQUIRED_STAGE_ROWS:
        if not any(i == prefix or i.startswith(prefix) for i in ids):
            errors.append(f"campaign matrix missing stage row '{prefix}*'")
    blob = " ".join((r.get("id", "") + " " + r.get("name", "")).lower() for r in rows)
    for fam in REQUIRED_FAMILY_KEYWORDS:
        if fam not in blob:
            errors.append(f"enemy family '{fam}' has no row")
    for boss in REQUIRED_BOSSES:
        if boss not in blob:
            errors.append(f"boss '{boss}' has no row")
    return errors


def report(doc: dict) -> None:
    rows = doc["rows"]
    by = lambda k: sorted({r[k] for r in rows if k in r})  # noqa: E731
    print(f"[mechanics_baseline] {len(rows)} rows across sections {by('section')}")
    for sec in SECTION_MINIMUMS:
        sec_rows = [r for r in rows if r["section"] == sec]
        st = {}
        for r in sec_rows:
            st[r["status"]] = st.get(r["status"], 0) + 1
        print(f"  {sec}: {len(sec_rows):3d} rows  " +
              "  ".join(f"{k}={v}" for k, v in sorted(st.items())))
    unbound = [r["id"] for r in rows if not r.get("bindings")]
    have_fx = sum(1 for r in rows if r.get("fixture_have"))
    print(f"  explicit-unknown rows (no bindings yet): {len(unbound)}")
    for rid in unbound:
        print(f"    - {rid}")
    print(f"  rows with an existing repo fixture: {have_fx}/{len(rows)}")
    print(f"  lifecycle dimensions (Phase-2 oracle axes): {len(doc.get('dimensions') or [])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    doc = load()
    errors = validate(doc)
    if errors:
        print(f"[mechanics_baseline] FAIL — {len(errors)} violation(s):")
        for e in errors:
            print(f"  {e}")
        return 1
    if args.report:
        report(doc)
    print(f"[mechanics_baseline] PASS: {len(doc['rows'])} rows meet the Phase-1 gate shape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
