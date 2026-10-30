---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800206E8.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800206E8.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800206E8_survivor-list_primitive_builder_-2.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800206E8 — survivor-list primitive builder #2
type: function
address: 0x800206E8
confidence: CONFIRMED
tags: [function, rendering, geometry, gte]
---
# FUNC_800206E8 — survivor-list primitive builder #2

> The analog of [[FUNC_8001EA6C]] for a second primitive class; same bridge shape, different OT sub-range. In G30 this path renders the dark mound.

| Field | Value |
|-------|-------|
| Address | 0x800206E8 (span `0x800206e8..0x800212f4`) |
| Source file | `src_re_geometry/geometry_render_consumers.c` (G10) |
| Confidence | CONFIRMED (shape) |

## Purpose
Same shape as builder #1: reads `row+0x0c` extent, derives the OT z-index from `[gp+0x5f4]>>2` → `0x1f800390`; dispatch table `<0x4b`; writes to `a2 = [0x8008240c]+0x1c4`. Loads the payload `a0` from `[s2+0x1c]`/`[s2+0x20]` (no base add) and emits via [[FUNC_80010000]].

## Arguments / Returns
`a0`=LIST_A · `a1`=count · `a2`=`[0x8008240c]+0x1c4`. 

## Calls (callees)
- [[FUNC_80010000]] (mesh emitter, a0 from `[s2+0x1c]`/`[s2+0x20]`).

## Called by (callers)
- [[FUNC_800224EC]] (render driver).

## Globals & structures touched
- LIST_A `0x80096ea8`; OT buffer `[0x8008240c]+0x1c4`; payload band → [[MEM - fcn.80010000 mesh payload]].

## Evidence & confidence notes
G18 confirmed the emitter loads `a0` from `[s2+0x1c]` with no base-add — a key fact in retiring the `0x801bdc58` floor theory ([[Finding - 0x801bdc58 is compressed source]]).

## Related
- Functions: [[FUNC_8001EA6C]] · [[FUNC_80010000]] · [[FUNC_800224EC]]
- Source docs: `src_re_geometry/geometry_g18_output_buffer_floor_trace.md`, `geometry_render_consumers.c`
