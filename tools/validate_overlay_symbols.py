#!/usr/bin/env python3
"""Validate analysis/overlay_symbols.json (the per-overlay name store).

Invariants:
- schema: {generated_by, overlays: {overlay: {"0xaddr": {name, tier, evidence}}}}
- name grammar [A-Za-z_][A-Za-z0-9_]*; tier in {proven, inferred, temporary}
- every (overlay, address) is an overlay function START for that overlay in the census
- names are unique WITHIN an overlay (cross-overlay reuse is legal)
Exit 1 on any violation.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "analysis" / "overlay_symbols.json"
CENSUS = ROOT / "analysis" / "functions.json"
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
TIERS = {"proven", "inferred", "temporary"}


def check():
    errs = []
    doc = json.loads(STORE.read_text())
    fj = json.loads(CENSUS.read_text())
    starts = {(f["overlay"], int(f["start"], 16))
              for f in fj["functions"]
              if f.get("space") == "overlay" and f.get("range_type") == "code"}
    total = 0
    for ov, m in doc.get("overlays", {}).items():
        seen = {}
        for a, e in m.items():
            total += 1
            if not re.fullmatch(r"0x[0-9a-f]{8}", a):
                errs.append(f"{ov}:{a} bad address form")
                continue
            if not NAME_RE.match(e.get("name", "")):
                errs.append(f"{ov}:{a} bad name {e.get('name')!r}")
            if e.get("tier") not in TIERS:
                errs.append(f"{ov}:{a} bad tier {e.get('tier')!r}")
            if (ov, int(a, 16)) not in starts:
                errs.append(f"{ov}:{a} not an overlay function START")
            if e.get("name") in seen:
                errs.append(f"{ov}: name {e['name']!r} at both {seen[e['name']]} and {a}")
            seen[e.get("name")] = a
    return total, len(doc.get("overlays", {})), errs


def main() -> int:
    total, novl, errs = check()
    if errs:
        for e in errs[:40]:
            print("  ERROR", e)
        print(f"FAIL: {len(errs)} violation(s)")
        return 1
    print(f"OK: {total} overlay symbols across {novl} overlays; all starts, unique-per-overlay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
