#!/usr/bin/env python3
"""Regenerate the EXTENTS table in tools/phase4_f01_frontier_resolve.c.

The table is GENERATED from analysis/phase4_static_frontier_index.json --
every `range_type == "code"` record in every analysed image -- and must never
be hand-edited. Both historical defects in it were hand-typing defects: the
ENDS stopped short of the real functions (2026-08-05, 20 of 29), then the SET
was a subset of its own criterion (2026-08-06, 29 of 37). This tool exists so
the third occasion cannot happen: it derives the rows, rewrites the block in
place, and `--check` fails if the retained table differs from the derivation.

Row identity and order are deterministic: the resident image first (short id
"SCUS"), then overlays, each sorted by start address; the name column is the
index name or `sub_%08x` when the index has none.

Usage:
  tools/phase4_gen_resolver_extents.py [--check]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
SOURCE_PATH = ROOT / "tools/phase4_f01_frontier_resolve.c"
BLOCK_RE = re.compile(
    r"(static const Extent EXTENTS\[\] = \{\n(?:\s*/\*.*?\*/\n)?)(.*?)(\n\};)",
    re.S)


def derive_rows() -> list[str]:
    index = json.loads(INDEX_PATH.read_bytes())
    if not index.get("valid"):
        raise SystemExit("static index reports valid=false; regenerate it first")
    rows: list[tuple[int, str, int, int, str]] = []
    for record in index["records"]:
        if record.get("range_type") != "code":
            continue
        start = int(record["entry"], 16)
        end = int(record["end"], 16)
        image = record["image_id"]
        short = "SCUS" if image == "SCUS_942_88" else image
        name = record.get("name") or f"sub_{start:08x}"
        rows.append((0 if short == "SCUS" else 1, short, start, end, name))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return [f'    {{ "{short}", 0x{start:08x}, 0x{end:08x}, "{name}" }},'
            for _, short, start, end, name in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the retained table differs from the derivation")
    args = parser.parse_args()
    source = SOURCE_PATH.read_text()
    match = BLOCK_RE.search(source)
    if not match:
        raise SystemExit("EXTENTS block not found in resolve.c")
    fresh_body = "\n".join(derive_rows())
    current_body = match.group(2)
    # The leading comment inside the initializer is part of group 1 only when it
    # is the FIRST thing in the block; keep whatever commentary precedes the
    # first row untouched by splitting at the first row line.
    first_row = current_body.find("    { \"")
    preamble, table = current_body[:first_row], current_body[first_row:]
    if table == fresh_body:
        print(f"[gen-resolver-extents] {SOURCE_PATH.name}: table is fresh "
              f"({fresh_body.count(chr(10)) + 1} rows)")
        return 0
    if args.check:
        current_rows = set(table.splitlines())
        fresh_rows = set(fresh_body.splitlines())
        for row in sorted(fresh_rows - current_rows):
            print(f"missing from retained table: {row.strip()}", file=sys.stderr)
        for row in sorted(current_rows - fresh_rows):
            print(f"retained but not derived:    {row.strip()}", file=sys.stderr)
        print("[gen-resolver-extents] STALE: rerun without --check", file=sys.stderr)
        return 1
    updated = source[:match.start(2)] + preamble + fresh_body + source[match.end(2):]
    SOURCE_PATH.write_text(updated)
    print(f"[gen-resolver-extents] rewrote EXTENTS "
          f"({fresh_body.count(chr(10)) + 1} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
