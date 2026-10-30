---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - GTE state.md
aliases:
  - "API - GTE state"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - GTE state.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - GTE state
type: api
category: GTE
tags: [api, duckstation, gte, geometry, pgxp]
---
# API — GTE state

> Read the PS1 GTE (COP2) transform pipeline — the heart of 3D geometry projection.

## Methods & syntax
- **`debugger.getGteState`** → decoded GTE: `control` (rotation/light/color matrices in 1.3.12 float, translation, screen_offset, projection_distance H, depth_queue, z_scale) + `data` (input_vectors, ir[4], mac[4], **screen_xy_fifo**, screen_z_fifo, color_fifo, rgbc, otz, flag).
- **`debugger.getRegisters`** — the 67 raw GTE registers live here (e.g. `gte.SXY0`, `gte.MAC0`).
- **`debugger.getPgxpData {include_gpr, include_gte}`** → PGXP high-precision sub-pixel X/Y/Z shadows (only meaningful when PGXP "Geometry Correction" is enabled).

## Best use in ABL RE
Reading projected screen coordinates (`SXY`) and transform inputs at a draw PC — to map a model-space vertex to its on-screen position, and to calibrate model↔world↔screen scale.

[[API - gpu.pickObject]] provides the draw-time bridge: `geometry.gteVertices` is populated only when captured SXY0..2/SZ1..3 exactly match the GP0 packet's screen vertices. If empty, break at the producer and use `getGteState`/[[API - execTrace]]; the FIFO may have advanced or the primitive may be 2D/a quad.

## Common mistakes / gotchas
- GTE data regs change every GTE op — **pause** (or capture via [[API - execTrace]] with `gte.`-prefixed names). 
- GTE registers are NOT under `gpu.*`.

## ABL examples
- Capturing `gte.SXY*` at [[FUNC_80010000]] (`0x80010718`) confirmed Candidate A's lower-center screen footprint → [[Finding - Candidate A is DAT-backed visual terrain]].
- The "photogenic localized pit" gate needs GTE-trace to calibrate model↔world scale → [[Open Questions]].

## Related
[[API - gpu.pickObject]] · [[API - execTrace]] · [[API - execution control]] · [[Playbook - Trace rendering ownership]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
