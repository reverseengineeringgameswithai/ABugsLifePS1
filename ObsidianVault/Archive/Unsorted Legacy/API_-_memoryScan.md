---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - memoryScan.md
aliases:
  - "API - memoryScan"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - memoryScan.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - memoryScan
type: api
category: Memory
tags: [api, duckstation, scanner, cheat-engine]
---
# API — memoryScan

> Cheat-Engine-style value scanner over the 2 MB main RAM (single shared session).

## Methods & syntax
- **`memoryScan.start {type=s32|u8|s8|u16|s16|u32|float, mode, value?, range?:{start,length}}`** → `{count}`. Start modes: `unknown/any, exact/equal, not_equal, greater(_than), greater_equal, less(_than), less_equal`.
- **`memoryScan.refine {mode, value?}`** → `{count}`. Refine adds: `changed, unchanged, increased, decreased, increased_by, decreased_by, changed_by`.
- **`memoryScan.results {offset, limit≤10000}`** → `{total, results:[{address(KSEG0 0x80..), physical, value, value_hex, previous, first, changed}]}`.
- **`memoryScan.clear`**.

## Best use in ABL RE
Locating an unknown global by behavior: scan `unknown`, change the in-game quantity, refine `increased`/`changed`, repeat. How counters/markers (grain count, berry marker) and player coords were pinned.

## Common mistakes / gotchas
- Pause between start→advance→refine for determinism. `float` is tolerant equality — rarely useful on fixed-point PS1 (the client CLI omits float; the RPC supports it).
- `range` is virtual, must lie in `[0, 0x200000)`. Single shared session — `clear` before a new hunt.

## ABL examples
Player position `0x800A6500/04/08`, grain count `0x800A65A1`, berry marker `0x800A6597`, seed counters `0x800A6598..` were all found/confirmed by scan-and-refine. See [[Symbols Index]].

## Related
[[API - readArray]] · [[API - addWatch]] · [[Playbook - Identify structure fields]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
