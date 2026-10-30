---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - execTrace.md
aliases:
  - "API - execTrace"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - execTrace.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - execTrace
type: api
category: Tracing
tags: [api, duckstation, exectrace, gte]
---
# API — execTrace

> Non-halting execution trace: "every time PC hits this address, capture these registers (incl. GTE)."

## Methods & syntax
- **`execTrace.addWatch {pc, capture?=["pc"] (≤32 names), label?, max_events=10000, stop_on_hit=false, filter?}`** → `{watch_id, …}`.
- **`execTrace.addRangeWatch {start, end, capture?=["pc"], label?, max_events=10000, stop_on_hit=false, filter?}`** →
  `{watch_id, kind:"range", start, end, …}`. Function/range trace without planting one exact-PC watch per instruction.
  Uses one opt-in interpreter hook; keep ranges bounded.
- Capture names resolved once: plain = GPR/PC/COP0 (land in `regs`); **`gte.`-prefixed** = GTE register (land in `gte`). Unknown name → `-32006` (rejects the whole addWatch).
- **`execTrace.get`** → `{events:[{frame, cycle, pc, regs:{name:hex}, gte:{name:hex}}], total, truncated}`. **`execTrace.run {frames}`**, `removeWatch`, `clear`.
- **`execTrace.summary {watch_id?, top?}`** → hot PCs/frame counts. **`execTrace.analyze {watch_id?, offset?, limit?, top?}`** → call/return edges, unreturned calls, backward branches, and self-loop hints from retained events. For return matching, capture `ra`; for `jalr`, capture likely target registers (`t9`, `v0`, etc.).
- `filter` like accessLog except the `value` sub-filter is invalid (`-32602`).

## Best use in ABL RE
Capture argument registers (a0 = payload/buffer pointer) and **GTE state** (`gte.SXY0`, `gte.MAC0`) at a draw/emitter/transform PC — the way render ownership and projected screen coords were established.
For Track-B collision work, prefer `addRangeWatch` over dozens of exact watches around resolver functions such as
`FUNC_80035280` / `FUNC_8003633C`; pair it with [[API - exec range and access history|accessTrace]] to see the effective
addresses read by the same function window.

## Common mistakes / gotchas
> [!warning] Dropped on [[API - loadState]] — re-arm after a load (settle first). Forces the interpreter; remove when done.
- For data accesses use [[API - accessLog]]; execTrace is for PC hits + register/GTE capture. `execTrace.analyze` is post-processing over retained events, so it is only as complete as the range/window you captured.

## ABL examples
- EXEC at [[FUNC_800172DC]] (rtpt `0x80017464`) captured per-quad SXY + `a1` → [[Finding - Visible terrain renderer]] / [[Finding - Localized terrain edit]].
- EXEC at [[FUNC_80010000]] `0x80010718` (SXY) confirmed Candidate A projects to the lower-center screen → [[Finding - Candidate A is DAT-backed visual terrain]].
- EXEC `0x80046330` captured `a0`/`ra` to bracket the LEVEL.RAW load → [[Finding - Floor resource is LEVEL.RAW]].

## Related
[[API - accessLog]] · [[API - addWatch]] · [[API - trace.armWhen]] · [[API - GTE state]] · [[API - advanceUntil]] · [[Playbook - Trace rendering ownership]]
[[API - exec range and access history]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
