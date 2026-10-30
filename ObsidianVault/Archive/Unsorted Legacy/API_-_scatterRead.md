---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - scatterRead.md
aliases:
  - "API - scatterRead"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - scatterRead.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - scatterRead
type: api
category: Memory
tags: [api, duckstation, memory, batch]
---
# API — scatterRead

> Read many non-contiguous addresses in a single core-thread call.

## Methods & syntax
**`debugger.scatterRead {reads:[{address,type} | {address,length}]}`** (1..4096 items; summed ≤1 MiB; each raw ≤1 MiB) → `{reads:[per-item typed-or-raw result + valid], count}`. Per-item unmapped → `valid:false`; over-cap → `-32006` (never silent truncation).

## Best use in ABL RE
Sampling scattered globals/fields together (e.g. several gp-relative counters + a couple of struct fields) without one round-trip each — keeps a snapshot internally consistent.

## Common mistakes / gotchas
- For a regular stride, [[API - readArray]] is cleaner; scatterRead is for genuinely scattered addresses.
- Pause first so all items reflect the same frame.

## ABL examples
Reading the parser geometry globals together (`0x80082498`, `0x800824AC`, `0x80082508`, `0x800822F0`) during G5.5/G3 corroboration.

## Related
[[API - readArray]] · [[API - scatterWrite]] · [[API - snapshot bundle]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
