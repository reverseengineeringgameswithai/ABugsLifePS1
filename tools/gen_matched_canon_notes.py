#!/usr/bin/env python3
"""Generate/update Canon function notes for byte-matched functions.

For every `.c` entry in config/segments.yml `attempted`, ensures a
ObsidianVault/Canon/Functions/FUNC_<ADDR>.md note exists (Canon = original-game
truth) with linked relationships per the vault philosophy: `calls` -> callee
FUNC ids (from the census), `src_paths` -> the matching src/main C, `evidence`
-> the campaign EXP. Creates absent notes; for existing notes it MERGES the
match provenance into the frontmatter without touching the prose body.

  python tools/gen_matched_canon_notes.py [--evidence EXP_ID]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = ROOT / "config" / "segments.yml"
CENSUS = ROOT / "analysis" / "functions.json"
NOTES = ROOT / "ObsidianVault" / "Canon" / "Functions"
DEFAULT_EVIDENCE = "EXP_2026-07-08_c_decompilation_campaign_v1"


def _census_by_addr():
    return {int(r["start"], 16): r
            for r in json.loads(CENSUS.read_text())["functions"]
            if r["space"] == "resident"}


def _frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), m.group(2)


def _dump(fm: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(fm, sort_keys=False).strip() + "\n---\n" + body


def _addr_note(addr: int):
    # match the ADDRESS at the filename prefix (FUNC_<ADDR>[_name].md) — NOT a loose
    # substring, which would wrongly match e.g. FUNC_80043114_sub_80043118_entry.md
    # when looking up 0x80043118.
    tag = f"FUNC_{addr:08X}"
    for p in NOTES.glob("FUNC_*"):
        stem = p.name.upper()
        if stem == f"{tag}.MD" or stem.startswith(f"{tag}_"):
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", default=DEFAULT_EVIDENCE)
    args = ap.parse_args()
    seg = yaml.safe_load(SEGMENTS.read_text())
    census = _census_by_addr()
    NOTES.mkdir(parents=True, exist_ok=True)
    created, updated = 0, 0
    # addresses that already have a Canon FUNC page — only link callees whose page
    # exists, so `calls`/body links never dangle (vault-lint baseline stays 0).
    have_page = set()
    for p in NOTES.glob("FUNC_*.md"):
        m = re.search(r"([0-9A-Fa-f]{8})", p.name)
        if m:
            have_page.add(int(m.group(1), 16))
    # every function we are about to (re)generate a page for also counts as present
    have_page |= {(e["start"] if isinstance(e["start"], int) else int(e["start"], 16))
                  for e in (seg.get("attempted") or []) if str(e["source"]).endswith(".c")}

    for entry in seg.get("attempted") or []:
        src = str(entry["source"])
        if not src.endswith(".c"):
            continue
        va = entry["start"] if isinstance(entry["start"], int) else int(entry["start"], 16)
        rec = census.get(va, {})
        name = rec.get("name") or ""
        calls = [f"FUNC_{int(a, 16):08X}" for a in rec.get("callees", [])
                 if (int(a, 16) if isinstance(a, str) else a) in have_page]
        fid = f"FUNC_{va:08X}"
        existing = _addr_note(va)
        if existing:
            fm, body = _frontmatter(existing.read_text())
            if fm is None:
                continue
            fm["address"] = f"0x{va:08x}"   # normalize (yaml parses 0x.. as int)
            al = fm.setdefault("aliases", []) or []
            for a in ([fid, f"0x{va:08x}"] + ([name] if name and name != fid else [])):
                if a not in al:
                    al.append(a)
            fm["aliases"] = al
            sp = fm.setdefault("src_paths", []) or []
            if src not in sp:
                sp.append(src)
            fm["src_paths"] = sp
            ev = fm.setdefault("evidence", []) or []
            if args.evidence not in ev:
                ev.append(args.evidence)
            fm["evidence"] = ev
            fm["status"] = "byte_matched"
            fm["confidence"] = "confirmed"
            existing.write_text(_dump(fm, body))
            updated += 1
            continue

        disp = name if name and not name.startswith("FUNC_") else fid
        fm = {
            "kind": "function", "id": fid,
            "aliases": [fid, f"0x{va:08x}"] + ([name] if name and name != fid else []),
            "address": f"0x{va:08x}",
            "name": name or "", "status": "byte_matched", "confidence": "confirmed",
            "source_state": "original_game",
            "calls": calls, "reads": [], "writes": [],
            "evidence": [args.evidence], "src_paths": [src],
            "patch_policy": "unknown",
        }
        body = (f"\n# {fid} - {disp}\n\n"
                f"## Status\n\n"
                f"**Byte-matched from C** (decomp substrate): `{src}` compiles to the exact "
                f"original bytes at `0x{va:08x}` (config/segments.yml `attempted`; "
                f"`validate_build.py` SHA-1 PASS). This note is Canon original-game truth for "
                f"the function's *bytes*; higher-level purpose is refined separately.\n\n"
                f"## Identity\n\n- Address: `0x{va:08x}`\n"
                f"- Matching source: `{src}`\n"
                f"- Callees: {', '.join(f'[[{c}]]' for c in calls) or 'none (leaf)'}\n\n"
                f"## Behavior\n\nSee the matching C source; field/global meanings are "
                f"address-anchored (no invented semantics) unless linked to a `MEM_*` note.\n")
        (NOTES / f"{fid}.md").write_text(_dump(fm, body))
        created += 1

    print(f"[canon] {created} created, {updated} updated in {NOTES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
