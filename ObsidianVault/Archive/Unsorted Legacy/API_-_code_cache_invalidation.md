---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - code cache invalidation.md
aliases:
  - "API - code cache invalidation"
migration_action: needs_review
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - code cache invalidation.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - code cache invalidation
type: api
category: Memory
tags: [api, duckstation, write, recompiler, icache, patch]
---
# API — code cache invalidation (live code patches take effect)

> Patching *executing* guest code now runs the new instruction immediately — no breakpoint-toggle workaround. Fixes the old SILENT failure where `writeMemory` into hot code landed in RAM but never executed.

## The bug this fixes
`writeMemory`/`writeU32` into code the CPU is actively running used to be invisible: the recompiler kept executing the already-translated block, and the pure interpreter served the stale word from the emulated guest I-cache. The write was in RAM and read back correct, but the OLD instruction kept running → every live hook / NOP / early-return / suppression test looked like "no effect" and produced **wrong conclusions**. The only workaround was toggling an execute breakpoint to force a re-fetch.

## Methods & syntax
- **`writeMemory {address, hex|base64, invalidate_code?=true}`**, **`writeU8/U16/U32 {address, value, invalidate_code?=true}`** — after a successful write that lands in **main RAM**, the covering recompiler block(s) are invalidated and the emulated I-cache flushed, so the patch runs on the next frame. Response echoes `code_invalidated`. Pass `invalidate_code:false` for bulk **data** writes where you don't want the (small) cost; a non-RAM target makes invalidation a no-op anyway.
- **`debugger.invalidateCodeCache {address?, length?}`** → `{invalidated:N, scope:"range"|"all"}` — force it manually. With `address` (+ optional `length`, default 4) invalidates just the covering RAM page(s); with **no range**, invalidates **all** RAM blocks. `N` = distinct RAM code-pages affected. Cheap/safe in interpreter mode (only flushes the I-cache there).

## Best use in ABL RE
- **Hook / suppress / NOP a routine and see the effect on the very next frame.** `writeU32 {address:<hot PC>, value:0}` (NOP) or an early `jr ra`, then `advanceFrames` — the patch is live. No more `addBreakpoint → resume → removeBreakpoint` dance.
- **After a `scatter-write` or the experiment runner patches code,** call `invalidateCodeCache {address,length}` (those paths default-invalidate too, but be explicit if unsure).
- **Reverting a patch** (`writeU32` the original word back, default `invalidate_code:true`) likewise takes effect immediately.

## Common mistakes / gotchas
- `invalidate_code` only matters for **code** addresses in main RAM; data writes and non-RAM targets are unaffected (no-op).
- It does NOT change determinism for two runs that apply the **same** writes — the invalidation is deterministic. But a code patch is itself an intervention; pair with [[API - determinism]] when comparing.
- This is about the **emulator's** caches (recompiler block + guest I-cache), not the game's own data caching.

## Related
[[API - readArray]] · [[API - scatterWrite]] · [[API - experiment runner]] · [[API - execution control]] · [[API - determinism]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
