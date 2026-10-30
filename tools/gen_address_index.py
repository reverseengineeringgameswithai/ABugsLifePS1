#!/usr/bin/env python3
"""Regenerate ObsidianVault/Canon/Indexes/Address Index.md from the Canon notes.

Scans Canon/{Functions,Memory,Tables,Structs,Constants,Hooks} for primary notes
carrying an address (frontmatter `address:` or an 8-hex in the filename), and
emits a sorted, complete address -> note table with accurate header counts.
Notes with explicit `canonical_address: false` remain searchable history or
secondary views and are omitted. Deterministic (no timestamps); run after
adding/renaming Canon notes. RCA a6 (AUDIT-25).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "ObsidianVault" / "Canon"
OUT = CANON / "Indexes" / "Address Index.md"
FUNCTIONS = ROOT / "analysis" / "functions.json"
SYM = ROOT / "symbols" / "re_symbols.sym"

FOLDERS = ["Functions", "Memory", "Tables", "Structs", "Constants", "Hooks"]
TYPE = {"Functions": "functions", "Memory": "memory", "Tables": "tables",
        "Structs": "structs", "Constants": "constants", "Hooks": "hooks"}
ADDR_RE = re.compile(r"^address:\s*['\"]?(0x[0-9A-Fa-f]{6,8})", re.M)
STEM_RE = re.compile(r"([0-9A-Fa-f]{8})")
SECONDARY_RE = re.compile(r"^canonical_address:\s*false\s*(?:#.*)?$", re.M | re.I)


def note_addr(p: Path) -> int | None:
    front = p.read_text(errors="replace")[:1200]
    if SECONDARY_RE.search(front):
        return None
    m = ADDR_RE.search(front)
    if m:
        return int(m.group(1), 16)
    sm = STEM_RE.search(p.stem)
    return int(sm.group(1), 16) if sm else None


def main() -> int:
    rows = []
    for folder in FOLDERS:
        d = CANON / folder
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            a = note_addr(p)
            if a is None:
                continue
            rows.append((a, TYPE[folder], p.stem))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))

    # header counts
    res_fns = sym_count = named = "?"
    if FUNCTIONS.exists():
        fj = json.loads(FUNCTIONS.read_text())
        res_fns = fj["resident"]["functions"]
        named = sum(1 for f in fj["functions"]
                    if f.get("space") == "resident" and f.get("name")
                    and f.get("range_type") != "data")
    if SYM.exists():
        sym_count = sum(1 for ln in SYM.read_text().splitlines() if ln.strip())

    lines = [
        "---", "kind: index", "id: ADDRESS_INDEX",
        "status: generated", "generated_by: tools/gen_address_index.py", "---", "",
        "# Address Index", "",
        f"Scope: every Canon note that carries an address ({len(rows)} entries across "
        f"{', '.join(TYPE[f] for f in FOLDERS)}). Regenerate with "
        "`python tools/gen_address_index.py` after adding/renaming Canon notes.", "",
        f"The full function inventory is **{res_fns} resident functions** "
        f"({named} named); the authoritative name source is `symbols/re_symbols.sym` "
        f"(**{sym_count} symbols**). Canon `FUNC_*` notes are created only for "
        "*analyzed* functions, never bulk-generated. See [[SYS_function_census]].", "",
        "| Address | Type | Note |", "| --- | --- | --- |",
    ]
    for a, typ, stem in rows:
        lines.append(f"| `0x{a:08X}` | {typ} | [[{stem}]] |")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"[address-index] wrote {len(rows)} rows "
          f"(resident {res_fns}, {sym_count} syms) -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
