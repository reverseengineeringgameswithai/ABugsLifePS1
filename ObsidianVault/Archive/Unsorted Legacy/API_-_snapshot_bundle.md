---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - snapshot bundle.md
aliases:
  - "API - snapshot bundle"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - snapshot bundle.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - snapshot bundle
type: api
category: GPU-VRAM
tags: [api, duckstation, snapshot]
---
# API — snapshot bundle

> One atomic call that captures a coherent composite: screenshot + registers + disassembly + memory dumps + GPU status + VRAM rects.

## Methods & syntax
**`emulator.captureSnapshotBundle {screenshot_path?, include_registers?, disassembly?:{address, count≤1024}, memory_dumps?:[{label?,address,length}] (≤16, ≤1 MiB), include_gpu_status?, vram_rects?:[{label?,x,y,width,height}] (≤8, ≤512×512)}`** → one atomic result (single core-thread call). Per-section errors are non-fatal.

## Best use in ABL RE
Freeze one moment fully — useful for a finding's evidence record (everything from the same frame). Pause first for a frozen snapshot.

## Common mistakes / gotchas
- Pause before capturing; otherwise sections may reflect slightly different frames.

## ABL examples
Bundling registers + the relevant buffer dump + a VRAM rect when documenting a confirmed render finding.

## Related
[[API - frame capture]] · [[API - scatterRead]] · [[API - findings store]] · [[API - GTE state]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
