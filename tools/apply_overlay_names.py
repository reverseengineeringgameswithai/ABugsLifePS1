#!/usr/bin/env python3
"""Apply a naming manifest into analysis/overlay_symbols.json — the per-overlay
name store (the overlay analogue of symbols/re_symbols.sym).

Overlays share load addresses (every LEVEL*.BIN loads at region_a 0x800B39A0), so
a flat ADDR->name map cannot name them: a name at 0x800b3b70 is a DIFFERENT
function in LEVEL02 vs LEVEL09. The census key is (space, overlay, start); this
store mirrors that, keyed by (overlay, address).

Manifest: a JSON list (or {"names":[...]}) of records:
  {"overlay": "MEMORY", "address": "0x800b687c", "name": "menu_nav_cursor",
   "tier": "proven|inferred|temporary",
   "evidence": ["dynamic:boot", "entry:resident_jal"], "rationale": "..."}
- tier "temporary" => intentionally NOT written (placeholder kept), logged skipped.
- Every named (overlay,address) MUST be an overlay function START for that overlay
  in analysis/functions.json (guards against naming a mid-function address or the
  wrong overlay); override with --allow-nonstart.

Policy (mirrors apply_symbol_names.py — hand/existing names win):
  - existing name == manifest name              -> agreed (no-op)
  - existing name != manifest name              -> CONFLICT: kept, reported, NOT overwritten
  - existing FUNC_/provisional_ placeholder     -> upgraded
  - new (overlay,address)                        -> inserted
A label that collides with a DIFFERENT address WITHIN THE SAME overlay is a hard
error (cross-overlay reuse of a name is legal — each overlay is its own namespace).

  python3 tools/apply_overlay_names.py analysis/naming/ovl_seed.json [more.json ...] [--dry-run]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "analysis" / "overlay_symbols.json"
CENSUS = ROOT / "analysis" / "functions.json"
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDER = re.compile(r"^(FUNC_|provisional_)")


def _addr(v) -> str:
    n = int(v, 16) if isinstance(v, str) else int(v)
    return f"0x{n:08x}"


def load_store() -> dict:
    if STORE.exists():
        return json.loads(STORE.read_text())
    return {"generated_by": "tools/apply_overlay_names.py", "overlays": {}}


def overlay_starts() -> dict[tuple[str, str], dict]:
    """(overlay, 0xaddr) -> census record, for overlay function starts only."""
    fj = json.loads(CENSUS.read_text())
    out = {}
    for f in fj["functions"]:
        if f.get("space") == "overlay" and f.get("range_type") == "code":
            out[(f["overlay"], _addr(f["start"]))] = f
    return out


def load_manifest(paths: list[Path]) -> list[dict]:
    items = []
    for p in paths:
        doc = json.loads(p.read_text())
        recs = doc["names"] if isinstance(doc, dict) else doc
        for r in recs:
            r = dict(r)
            r["_src"] = p.name
            items.append(r)
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-nonstart", action="store_true")
    args = ap.parse_args()

    store = load_store()
    starts = overlay_starts()
    manifest = load_manifest(args.manifests)

    added = upgraded = agreed = skipped = 0
    conflicts, errors = [], []
    for r in manifest:
        ov = str(r["overlay"])
        addr = _addr(r["address"])
        name = str(r["name"])
        tier = r.get("tier", "inferred")
        if tier == "temporary":
            skipped += 1
            continue
        if not NAME_RE.match(name):
            errors.append(f"{ov}:{addr} bad name {name!r}")
            continue
        if not args.allow_nonstart and (ov, addr) not in starts:
            errors.append(f"{ov}:{addr} not an overlay function START (use --allow-nonstart to force)")
            continue
        ov_map = store["overlays"].setdefault(ov, {})
        # intra-overlay label collision (a DIFFERENT address in the same overlay)
        for a2, e2 in ov_map.items():
            if a2 != addr and e2.get("name") == name:
                errors.append(f"{ov}: label {name!r} already at {a2} (unique within overlay)")
                break
        else:
            existing = ov_map.get(addr, {}).get("name", "")
            if existing == name:
                agreed += 1
            elif existing and not PLACEHOLDER.match(existing):
                conflicts.append(f"{ov}:{addr} keep {existing!r} != manifest {name!r}")
            else:
                ov_map[addr] = {"name": name, "tier": tier,
                                "evidence": r.get("evidence", []),
                                "rationale": r.get("rationale", "")}
                upgraded += bool(existing)
                added += not bool(existing)

    # deterministic sort
    store["overlays"] = {ov: {a: store["overlays"][ov][a] for a in sorted(store["overlays"][ov])}
                         for ov in sorted(store["overlays"])}
    total = sum(len(m) for m in store["overlays"].values())
    print(f"overlay-names: +{added} added, {upgraded} upgraded, {agreed} agreed, "
          f"{skipped} temporary-skipped; store total {total} across {len(store['overlays'])} overlays")
    for c in conflicts:
        print("  CONFLICT", c)
    for e in errors:
        print("  ERROR", e)
    if errors:
        return 1
    if not args.dry_run:
        STORE.write_text(json.dumps(store, indent=1) + "\n")
        print(f"wrote {STORE.relative_to(ROOT)}")
    else:
        print("(dry-run: store not written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
