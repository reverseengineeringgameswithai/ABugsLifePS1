---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - provenance.timeline.md
aliases:
  - "API - provenance.timeline"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - provenance.timeline.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - provenance.timeline
type: api
category: Tracing
tags: [api, duckstation, provenance, vram, dma, accesslog]
updated: 2026-07-06
---
# API — provenance.timeline

> One sorted retained-log evidence report for RAM ↔ DMA/CD ↔ CPU access ↔ VRAM upload provenance.

## Method & syntax
**`provenance.timeline {ram?|address?/length?, vram?, limit?, scan_limit?, include_disc?, include_transfer_events?}`** → `{query, method:"retained_log_timeline", confidence, events, total, truncated, discProvenance?, notes}`.

Queries can provide either or both:
- `ram:{address,length}` or top-level `address` + `length`
- `vram:{x,y,width,height}`

Events are sorted by frame/cycle and have `kind` = `transfer`, `cpu_access`, or `vram_write`, plus `match` and the original event shape from [[API - transferLog]], [[API - accessLog]], or [[API - gpu.pickObject]].

## Best use in ABL RE
Use after a focused replay/load window when answering: "which disc/RAM source produced this live texture/CLUT, and which CPU code then read or wrote that RAM?" It is especially useful when `gpu.resolveVramProvenance` finds a payload RAM address and you want the surrounding DMA/access context in one report.

```json
{"ram":{"address":"0x801f0000","length":4096},
 "vram":{"x":336,"y":0,"width":16,"height":64},
 "include_disc":true}
```

## Gotchas
- Retained-log only. It cannot recover events before the current session/state or before a log/watch was armed.
- For best evidence: `transferLog.start`, add relevant `accessLog` watches, `gpu.vramWriteLog.clear`, then replay/advance the load/draw window.
- `scan_limit` caps how many retained access/VRAM events are scanned; `limit` caps returned timeline events.

## Related
[[API - transferLog]] · [[API - accessLog]] · [[API - gpu.pickObject]] · [[API - gp0Trace]] · [[API - trace.armWhen]]

Source: ~/duckstation/docs/external-debugger.md
