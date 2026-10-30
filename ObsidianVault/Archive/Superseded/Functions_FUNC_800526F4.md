---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800526F4.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800526F4.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800526F4_HUD_draw.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800526F4 — HUD draw
type: function
address: 0x800526F4
confidence: CONFIRMED
tags: [function, hud, ui]
---
# FUNC_800526F4 — HUD draw (grain / FLIK / seed meters)

> Draws and animates the HUD panels each frame from the pickup/progress globals. The visible read-out of the pickup pipeline.

| Field | Value |
|-------|-------|
| Address | 0x800526F4 (size 3908 B, …0x80053634) |
| Source file | `src_re/hud_800526f4.c` (`hud_draw`) |
| Confidence | CONFIRMED pickup HUD data sources + draw-call args; peripheral scene panels UNKNOWN |

## Purpose
Draws HUD panels (progress, seed total, grain, FLIK bits, seed meters, FLIK record icons, scene-specific panels). `a0` = per-frame animation increment (`frame_step`) added to pulse halfwords.

## Arguments / Returns
`a0` = frame_step. Returns void.

## Calls (callees)
- `fcn.800260f8` (draw number/glyph), `fcn.80025f54` (draw sprite/tile), `fcn.80026588/0x80026a68/0x80026df4` (rect/effect), `fcn.8005044c`, `fcn.80026d78` (flush).

## Called by (callers)
- `fcn.8004ecd4` / `fcn.8004f478`.

## Globals & structures touched
- grain count `0x800a65a1` · seed counters `0x800a6598..9a` · FLIK bits `0x800a65a2` · FLIK record ptrs `0x800a0220/0430/0a60/0d78` · pulse halfwords `0x800b0188..19c` · sin table `0x80074970`.

## Evidence & confidence notes
CONFIRMED grain/FLIK/seed data sources + draw-call args; peripheral scene-7/0x0c panels are TODO. Reflects the counters updated by [[FUNC_80054EAC]] and the berry/token handlers.

## Related
- System: [[Grain emblem and HUD total mod]] (the "collected/total" readout hooks `0x80052b40` here; "/" = glyph `0x0a` via `fcn.80025f54`) · [[Menu and HUD structure]] (front-end + SELECT status-icon map) · [[LEVEL.DAT object pipeline]]
- Functions: [[FUNC_80054EAC]] · [[FUNC_80053814]] · [[FUNC_800586B0]]
- Source docs: `src_re/hud_800526f4.c`
