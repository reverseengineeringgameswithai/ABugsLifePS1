---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - symbols.md
aliases:
  - "API - symbols"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - symbols.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - symbols
type: api
category: Symbols
tags: [api, duckstation, symbols, labels]
---
# API — symbols

> In-memory label/comment store with import/export — annotate addresses as you reverse them.

## Methods & syntax
- **`debugger.addLabel {address, name}`** (empty name removes), **`debugger.addComment {address, text}`**, **`debugger.getComments`**, **`debugger.getSymbols`**, **`debugger.resolveSymbol`**.
- **`debugger.exportSymbols {path?, format?="sym"|"csv"}`** (default `<data dir>/re_symbols.sym`; `sym` = `AAAAAAAA name`, `csv` = labels+comments).
- **`debugger.importSymbols {path?, format?, merge?=true}`** (`merge:false` replaces) → counts.

## Best use in ABL RE
Persist the address→name map this vault documents so the DuckStation disassembler shows meaningful names (e.g. `0x8003633c → player_y_writer`). Round-trip via `.sym`/`.csv`.

## Common mistakes / gotchas
- Independent of the game's symbol DB. Labels in CSV must not contain commas.

## ABL examples
The [[Symbols Index]] is the master address→name table; exporting it as `.sym` makes the live disassembler legible for the next session.

The tracked M3 baseline and reproducible offline consumer proof are [[Symbol Map Baseline]] and [[Symbol Import Round Trip]]. The proof matches the fork's CSV layout and also loads all 85 labels into r2; live fork import remains local-only until GAP-0001 is preserved.

## Related
[[Symbol Map Baseline]] · [[Symbol Import Round Trip]] · [[Symbols Index]] · [[Functions Index]] · [[API - findings store]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
