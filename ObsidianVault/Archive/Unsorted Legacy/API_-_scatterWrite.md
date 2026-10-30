---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - scatterWrite.md
aliases:
  - "API - scatterWrite"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - scatterWrite.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - scatterWrite
type: api
category: Memory
tags: [api, duckstation, memory, batch, write]
---
# API — scatterWrite

> Write many addresses at once, optionally atomically (all-or-nothing).

## Methods & syntax
**`debugger.scatterWrite {writes:[{address,type,value} | {address,hex}], atomic=false}`** → `{writes:[{address,written,ok,error?}], count, applied}`.
- **`atomic:true`** pre-validates every target is mapped + writable (BIOS/unmapped rejected) and writes **nothing** if any is invalid (`applied:false`).

## Best use in ABL RE
Applying a multi-field RAM perturbation in one coherent step — e.g. editing several terrain vertices or several sector origins together for a localized edit.

## Common mistakes / gotchas
- RAM pokes **persist** until you reload the fixture — undo by reloading ([[API - loadState]]).
- Use `atomic:true` when a partial write would leave an inconsistent structure.

## ABL examples
- [[Experiment - G30 localized terrain edit]] — edit a screen-box of GP0 0x3C quads in [[MEM - Terrain vertex buffer 8012C1D0]].
- [[Experiment - G29 collision lever validation]] — lower sector origin Y in [[MEM - Collision sector table 800A7E48]].
- The starry-night injection patches the sky cache words together ([[Finding - GPU primitive injection]]).

## Related
[[API - scatterRead]] · [[API - readArray]] · [[API - experiment runner]] · [[API - loadState]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
