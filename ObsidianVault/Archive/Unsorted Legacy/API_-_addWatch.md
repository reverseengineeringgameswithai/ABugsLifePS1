---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - addWatch.md
aliases:
  - "API - addWatch"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - addWatch.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - addWatch
type: api
category: Watchpoints
tags: [api, duckstation, watch, tracing]
---
# API — addWatch (the non-halting watch model)

> The shared concept behind [[API - accessLog]] and [[API - execTrace]]: arm a non-halting watch, let the game run, collect events. "What touched this address / which registers at this PC?"

## Methods & syntax
Two families, same lifecycle:
- **`accessLog.addWatch {address, length=1..256, type:"read"|"write"|"readwrite", label?, max_events, stop_on_hit, filter?}`** — data access (main RAM only). See [[API - accessLog]].
- **`execTrace.addWatch {pc, capture?:[reg names ≤32], label?, max_events, stop_on_hit, filter?}`** — execution at a PC, capturing GPRs/COP0/`gte.*`. See [[API - execTrace]].
- Companions: `removeWatch`, `clear`, `get {offset,limit}`, `run {frames}`.
- **`filter`** (in-callback, pre-buffer): `{pc, registers:{name:val|{op,value}}, value:{op,value}, frame_mod:{div,rem}, max_per_frame}` (ops eq/ne/lt/le/gt/ge). `value` is invalid for exec watches.

## Best use in ABL RE
The primary, fast RE tool (no halting, no step-by-step). Arm before driving the game with [[API - advanceUntil]] / [[API - controller input]].

## Common mistakes / gotchas
> [!warning] **All watches are dropped on [[API - loadState]] — re-arm after every load. Settle one frame after load before addWatch or it can crash.**
- Any watch forces the **interpreter (~10–100× slower)** — remove when done.
- ≤64 live watches; global ring 200000 events. **DMA writes are invisible to CPU watchpoints** — use [[API - transferLog]] for DMA provenance.

## ABL examples
WRITE-watch on player Y `0x800A6504` found the writer [[FUNC_8003633C]] ([[Finding - Player Y writer FUNC_3633C]]); accessLog on the decompressor output mapped chunks 32/35 ([[Finding - Terrain on-disk source is chunk 35]]).

## Related
[[API - accessLog]] · [[API - execTrace]] · [[API - advanceUntil]] · [[API - loadState]] · [[Playbook - Trace collision resolution]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
