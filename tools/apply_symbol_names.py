#!/usr/bin/env python3
"""Apply a batch naming manifest into symbols/re_symbols.sym (the AUTHORITATIVE map).

Phase-5 (trace-based naming) needs to record MANY hand/inferred game-function names
reproducibly. `merge_psyq_symbols.py` only ingests PsyQ library names from Ghidra; there is
no path for game names except hand-editing the map. This tool is that path: it takes a JSON
manifest of evidence-linked names and merges them under the SAME invariants the validator
enforces (grammar `[A-Za-z_][A-Za-z0-9_]*`, addresses strictly increasing, labels globally
unique), leaving a .bak and re-validating the result.

Manifest: a JSON list (or {"names": [...]}) of records:
  {"address": "0x8004ecd4", "name": "gameplay_state_machine",
   "tier": "proven|inferred|temporary",
   "evidence": ["dynamic:LEVEL01..15", "callers:12"], "rationale": "..."}
- tier "temporary" => intentionally NOT written (placeholder kept); logged as skipped.
- Every named address MUST be a resident function START in analysis/functions.json
  (guards against naming a mid-function address); override with --allow-nonstart.

Policy (mirrors merge_psyq_symbols.py — hand/existing names always win):
  - existing real name == manifest name        -> agreed (no-op)
  - existing real name != manifest name         -> CONFLICT: kept, reported, NOT overwritten
  - existing FUNC_/provisional_ placeholder     -> upgraded to the manifest name
  - new address                                 -> inserted (sorted)
A manifest label that collides with a DIFFERENT existing/again-manifest address is a hard
error (pick a unique name — we never auto-suffix a semantic name).

  python3 tools/apply_symbol_names.py analysis/naming/batch01.json [more.json ...] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYM = ROOT / "symbols" / "re_symbols.sym"
CENSUS = ROOT / "analysis" / "functions.json"
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDER = re.compile(r"^(FUNC_[0-9A-Fa-f]{8}|provisional_.*)$")
TIERS = {"proven", "inferred", "temporary"}


def _addr(v) -> int:
    if isinstance(v, int):
        return v
    return int(v, 16)


def load_manifest(paths: list[Path]) -> list[dict]:
    recs: list[dict] = []
    for p in paths:
        doc = json.loads(p.read_text())
        items = doc["names"] if isinstance(doc, dict) else doc
        for r in items:
            r = dict(r)
            r["_src"] = p.name
            recs.append(r)
    return recs


def resident_starts() -> set[int]:
    d = json.loads(CENSUS.read_text())
    return {int(r["start"], 16) for r in d["functions"] if r.get("space") == "resident"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-nonstart", action="store_true",
                    help="permit naming an address that is not a resident function start")
    a = ap.parse_args()

    sys.path.insert(0, str(ROOT / "tools"))
    from validate_symbol_map import parse_symbols

    existing = dict(parse_symbols(SYM))            # addr -> label (validated)
    starts = resident_starts()
    recs = load_manifest(a.manifests)

    # ---- validate manifest records up front (fail loud, change nothing) ----
    errors: list[str] = []
    want: dict[int, dict] = {}                     # addr -> record (to write)
    skipped_temp: list[tuple[int, str]] = []
    for r in recs:
        try:
            addr = _addr(r["address"])
        except (KeyError, ValueError):
            errors.append(f"bad/missing address in record from {r.get('_src')}: {r!r}")
            continue
        name = str(r.get("name", "")).strip()
        tier = str(r.get("tier", "")).strip()
        if tier not in TIERS:
            errors.append(f"{addr:08X}: tier must be one of {sorted(TIERS)} (got {tier!r})")
            continue
        if tier == "temporary":
            skipped_temp.append((addr, name))
            continue
        if not IDENT.match(name):
            errors.append(f"{addr:08X}: name {name!r} is not a valid C identifier")
            continue
        if not r.get("evidence"):
            errors.append(f"{addr:08X} ({name}): missing 'evidence' (required for proven/inferred)")
            continue
        if addr not in starts and not a.allow_nonstart:
            errors.append(f"{addr:08X} ({name}): not a resident function start in functions.json "
                          f"(use --allow-nonstart to override)")
            continue
        if addr in want and want[addr]["name"] != name:
            errors.append(f"{addr:08X}: conflicting names in manifest ({want[addr]['name']!r} vs {name!r})")
            continue
        want[addr] = {"name": name, "tier": tier}

    if errors:
        print(f"ABORT: {len(errors)} manifest error(s):")
        for e in errors:
            print(f"  - {e}")
        return 2

    # ---- label-collision check (global uniqueness) ----
    existing_by_label = {lbl: ad for ad, lbl in existing.items()}
    for addr, rec in sorted(want.items()):
        clash = existing_by_label.get(rec["name"])
        if clash is not None and clash != addr:
            print(f"ABORT: label {rec['name']!r} (for {addr:08X}) already used by {clash:08X}")
            return 2

    # ---- apply policy ----
    added, upgraded, agreed, conflicts = [], [], [], []
    merged = dict(existing)
    for addr in sorted(want):
        name = want[addr]["name"]
        if addr in existing:
            cur = existing[addr]
            if cur == name:
                agreed.append((addr, name))
            elif PLACEHOLDER.match(cur):
                upgraded.append((addr, cur, name)); merged[addr] = name
            else:
                conflicts.append((addr, cur, name))     # real name wins, report only
        else:
            added.append((addr, name)); merged[addr] = name

    print(f"manifest records:      {len(recs)} ({len(want)} to write, {len(skipped_temp)} temporary-skipped)")
    print(f"already agreed:        {len(agreed)}")
    print(f"placeholder upgrades:  {len(upgraded)}")
    for addr, cur, name in upgraded:
        print(f"    {addr:08X} {cur} -> {name}")
    print(f"new symbols added:     {len(added)}")
    for addr, name in added:
        print(f"    {addr:08X} {name}")
    print(f"conflicts (kept):      {len(conflicts)}")
    for addr, cur, name in conflicts:
        print(f"    {addr:08X} keeps {cur!r} (manifest suggested {name!r})")
    print(f"map size:              {len(existing)} -> {len(merged)}")

    if a.dry_run:
        print("(dry-run: map not written)")
        return 0
    if not added and not upgraded:
        print("(nothing to write)")
        return 0

    SYM.with_suffix(".sym.bak").write_text(SYM.read_text(encoding="ascii"), encoding="ascii")
    SYM.write_text("".join(f"{addr:08X} {label}\n" for addr, label in sorted(merged.items())),
                   encoding="ascii")
    parse_symbols(SYM)   # re-validate what we wrote (raises on any invariant break)
    print(f"wrote {SYM} (+ .bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
