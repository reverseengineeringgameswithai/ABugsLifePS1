---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - accessLog.md
aliases:
  - "API - accessLog"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - accessLog.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - accessLog
type: api
category: Tracing
tags: [api, duckstation, accesslog, watch]
updated: 2026-07-06
---
# API — accessLog

> Non-halting data-access log: "which PC read/wrote this address, with what value?" Main RAM only.

## Methods & syntax
- **`accessLog.addWatch {address, length=1..256, type:"read"|"write"|"readwrite", label?, max_events=10000, stop_on_hit=false, filter?}`** → `{watch_id, …}`.
- **`accessLog.get {watch_id?, offset?, limit?≤10000}`** → `{events:[{frame, cycle, pc, reported_pc, instruction_pc, instruction_word, instruction, address, type, width, value, value_hex, new_value?, watch_id}], total, truncated}`.
  - `pc` is compatibility/callback PC; use `instruction_pc` + `instruction` for actual load/store attribution. This replaces the old manual `pc` vs `pc-4` check.
- **`accessLog.summary {watch_id?, top?=32}`** → server-side aggregate `{total, reads, writes, counts_by_width, top_pcs, counts_by_frame, first_event, last_event}` without paging raw events.
- **`accessLog.run {frames 1..600}`** — advance with watches armed, pause, return events. `removeWatch`, `clear`.
- **Value semantics:** callback fires **before** the access — `value` = value about to be read, or **pre-write/old** value; `new_value` decoded from `sb/sh/sw` (absent for reads + partial stores).

## (new) Retroactive write queries — lastWriter / findFirstWrite
- **`accessLog.lastWriter {address}`** → `{address, found, writer:{pc, instruction, cycle, frame, value, width, callStack:[]}, retention:{mode, oldestFrame, oldestCycle, bufferedWrites}}` — the **most recent** retained write to `address`. Width-aware (matches the store size). `retention` tells you how far back the buffer reaches (`bufferedWrites`, `oldestFrame`/`oldestCycle`).
- **`accessLog.findFirstWrite {address, since?, until?}`** → the **earliest** retained write in the window (`since`/`until` accept `"boot"`/`"current"` or a frame number).
> [!warning] These query **RETAINED write events** — they only see writes that a **WRITE watch was armed over when the write happened.** There is no time machine: to catch a one-shot write (an object/struct field being filled) you must **arm a broad write watch BEFORE the event** (e.g. before the load/spawn). After the fact with no prior watch → `found:false`.

**Spawn-write example** — "what code wrote this object/struct field?": arm a broad `accessLog.addWatch {address:<field>, length:<struct span>, type:"write"}` *before* triggering the spawn/load, let it run, then `accessLog.lastWriter {address:<field>}` → the producer `pc`+`instruction`. (`callStack` is currently empty.)

## Best use in ABL RE
Provenance: who writes a buffer (find the producer), who reads a table (find the consumer). The decisive CPU-side tool for "where does this data come from?" The event now names the exact decoded instruction, and `summary` gives hot writer/reader PCs before paging. `lastWriter`/`findFirstWrite` turn a *settled* state into "what last/first wrote here" — provided a write watch was armed over the address at write time.

## Common mistakes / gotchas
> [!warning] Dropped on [[API - loadState]] — re-arm after a load (and settle first). Forces the interpreter; remove when done.
- **DMA writes are NOT seen** (CPU watchpoint) — use [[API - transferLog]].
- ≤64 watches, 200000-event ring (oldest dropped + `truncated`).

## ABL examples
- WRITE-watches on the decompressor output located [[Finding - Terrain on-disk source is chunk 35]] and [[Finding - Collision on-disk source is chunk 32]] (writers `0x8001a5e8/f0/678`).
- WRITE-watch on `0x801bdc58` returned 0 hits → [[Finding - 0x801bdc58 is compressed source]].
- Pre-load copier trace `0x8003b2b8/d8/f8` → [[Finding - Sky color on-disk table]].

## Related
[[API - addWatch]] · [[API - execTrace]] · [[API - transferLog]] · [[API - provenance.timeline]] · [[API - trace.armWhen]] · [[API - advanceUntil]] · [[Playbook - Find geometry sources]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
