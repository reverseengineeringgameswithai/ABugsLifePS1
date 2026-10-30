#!/usr/bin/env python3
"""Normalize the complete function-census caller/callee frontier for WP8."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis" / "functions.json"


def key(row: dict) -> str:
    return f"{row.get('space')}:{row.get('overlay') or 'resident'}:{row['start']}"


def build() -> dict:
    source = json.loads(SOURCE.read_text())
    functions = [row for row in source["functions"]
                 if row.get("range_type") in ("code", "thunk")]
    rows = {}
    callers = {}
    callees = {}
    for row in functions:
        fid = key(row)
        record = {
            "start": row["start"],
            "end": row["end"],
            "space": row.get("space"),
            "overlay": row.get("overlay"),
            "name": row.get("name"),
            "classification": row.get("classification"),
            "callers": list(row.get("callers") or []),
            "callees": list(row.get("callees") or []),
        }
        rows[fid] = record
        callers[fid] = record["callers"]
        callees[fid] = record["callees"]
    counts = Counter(row.get("space") for row in functions)
    return {
        "_comment": "WP8 caller/callee report normalized from every code/thunk "
                    "row in analysis/functions.json. Direct edges are preserved; "
                    "indirect jr/jalr edges remain explicitly delegated to the "
                    "Phase-3 dispatch reports. Regenerate: python3 tools/phase3_call_graph.py",
        "generated": date.today().isoformat(),
        "exhaustive": True,
        "exhaustive_over": "all range_type=code|thunk rows in analysis/functions.json",
        "source_sha256": {
            "analysis/functions.json": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "analysis/phase3_jr_tables.json": hashlib.sha256(
                (ROOT / "analysis/phase3_jr_tables.json").read_bytes()).hexdigest(),
            "analysis/phase3_jalr_callbacks.json": hashlib.sha256(
                (ROOT / "analysis/phase3_jalr_callbacks.json").read_bytes()).hexdigest(),
        },
        "summary": {
            "functions": len(functions),
            "resident": counts.get("resident", 0),
            "overlay": counts.get("overlay", 0),
            "direct_caller_edges": sum(len(value) for value in callers.values()),
            "direct_callee_edges": sum(len(value) for value in callees.values()),
        },
        "indirect_edges": {
            "jr": "analysis/phase3_jr_tables.json",
            "jalr": "analysis/phase3_jalr_callbacks.json",
            "reason": "indirect targets cannot be silently converted into direct census edges",
        },
        "functions": rows,
        "callers": callers,
        "callees": callees,
    }


def main() -> int:
    doc = build()
    (ROOT / "analysis/phase3_call_graph.json").write_text(
        json.dumps(doc, indent=1) + "\n")
    s = doc["summary"]
    print(f"[call-graph] {s['functions']} functions; "
          f"{s['direct_caller_edges']} caller refs; {s['direct_callee_edges']} callee refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
