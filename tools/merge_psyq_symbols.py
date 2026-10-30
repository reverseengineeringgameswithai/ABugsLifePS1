#!/usr/bin/env python3
"""Merge PsyQ signature matches into symbols/re_symbols.sym (the AUTHORITATIVE map).

Inputs: extracted/re_baseline/psyq_matches.csv (+ psyq_version.txt), written by
ghidra/scripts/ExportPsyqMatches.java from the ABLPsx PsxLoader project. Ghidra
never writes the map itself — this explicit merge is the only path in, and
hand-curated entries ALWAYS win.

Policy:
  - existing hand-named entry (not FUNC_/provisional_) -> kept verbatim; a
    conflicting PsyQ name is reported, never applied.
  - existing FUNC_xxxx placeholder at a matched address -> upgraded to the
    official PsyQ name (logged).
  - new address -> inserted (sorted), name sanitized to the validator's
    [A-Za-z_][A-Za-z0-9_]* grammar; duplicate lib names get _2/_3… suffixes.
  - ORACLE: if the matches contain 0x8006B130 it MUST be SsVabOpenHead (the
    address where the hand map and PsyQ signatures independently AGREE) — any
    other name means address drift / wrong SDK version and aborts the merge.
    History: the original oracle (0x8006B1C0 == SsVabTransBody) fired on first
    run and was investigated: the PsyQ family layout (SsVabClose/OpenHead/
    OpenHeadSticky/FakeHead/OpenHeadWithMode … TransBody@0x8006B59C) proved the
    old hand label at 0x8006B1C0 was a misidentification; corrected 2026-07-08.

Runs tools/validate_symbol_map.py rules on the result before writing; use
--dry-run to preview. A .bak of the previous map is left beside it.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYM = ROOT / "symbols" / "re_symbols.sym"
MATCHES = ROOT / "extracted" / "re_baseline" / "psyq_matches.csv"
VERSION_TXT = ROOT / "extracted" / "re_baseline" / "psyq_version.txt"

ORACLE_ADDR, ORACLE_NAME = 0x8006B130, "SsVabOpenHead"
PLACEHOLDER = re.compile(r"^(FUNC_[0-9A-Fa-f]{8}|provisional_.*)$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# Ghidra artifacts that are not PsyQ library identifications
SKIP = re.compile(r"^(entry|FUN_|LAB_|switch|caseD|AddrTable|thunk_).*|^entry$")


def sanitize(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not re.match(r"^[A-Za-z_]", s):
        s = "_" + s
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    sys.path.insert(0, str(ROOT / "tools"))
    from validate_symbol_map import parse_symbols

    existing = dict(parse_symbols(SYM))          # addr -> label (validated)
    labels = set(existing.values())

    with MATCHES.open() as f:
        rows = [r for r in csv.DictReader(f)]
    matches: dict[int, str] = {}
    for r in rows:
        addr, name = int(r["address"], 16), r["name"].strip()
        if SKIP.match(name):
            continue
        # EXE text image only — drops the extension's synthetic GTE-macro
        # segment (0x20000000) and anything outside the resident load map.
        if not (0x80010000 <= addr <= 0x800827FF):
            continue
        matches[addr] = name

    # ---- oracle gate
    if ORACLE_ADDR in matches and matches[ORACLE_ADDR] != ORACLE_NAME:
        print(f"ABORT: oracle mismatch @ {ORACLE_ADDR:08X}: "
              f"psyq says {matches[ORACLE_ADDR]!r}, confirmed truth is {ORACLE_NAME!r}")
        return 2
    oracle = "hit" if matches.get(ORACLE_ADDR) == ORACLE_NAME else "absent-from-matches"

    added, upgraded, agreed, conflicts = [], [], [], []
    for addr in sorted(matches):
        name = matches[addr]
        if addr in existing:
            cur = existing[addr]
            if cur == name:
                agreed.append((addr, name))
            elif PLACEHOLDER.match(cur):
                upgraded.append((addr, cur, name))
            else:
                conflicts.append((addr, cur, name))   # hand name wins, report only
            continue
        added.append((addr, name))

    merged = dict(existing)
    for addr, _cur, name in upgraded:
        merged[addr] = name
    for addr, name in added:
        merged[addr] = name

    # unique-label pass (validator requires globally unique labels)
    seen: dict[str, int] = {}
    out: dict[int, str] = {}
    for addr in sorted(merged):
        base = sanitize(merged[addr])
        n = seen.get(base, 0) + 1
        seen[base] = n
        label = base if n == 1 else f"{base}_{n}"
        assert IDENT.match(label), label
        out[addr] = label

    print(f"psyq version detected: {VERSION_TXT.read_text().strip() if VERSION_TXT.exists() else '?'}")
    print(f"matches considered:    {len(matches)} (oracle {oracle})")
    print(f"already agreed:        {len(agreed)}")
    print(f"placeholder upgrades:  {len(upgraded)}")
    for addr, cur, name in upgraded:
        print(f"    {addr:08X} {cur} -> {name}")
    print(f"new symbols added:     {len(added)}")
    print(f"conflicts (hand kept): {len(conflicts)}")
    for addr, cur, name in conflicts:
        print(f"    {addr:08X} keeps {cur!r} (psyq suggested {name!r})")
    print(f"map size:              {len(existing)} -> {len(out)}")

    if a.dry_run:
        print("(dry-run: map not written)")
        return 0

    SYM.with_suffix(".sym.bak").write_text(SYM.read_text(encoding="ascii"), encoding="ascii")
    SYM.write_text("".join(f"{addr:08X} {label}\n" for addr, label in sorted(out.items())),
                   encoding="ascii")
    parse_symbols(SYM)  # re-validate what we wrote
    print(f"wrote {SYM} (+ .bak)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
