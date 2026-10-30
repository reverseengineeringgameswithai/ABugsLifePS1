---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8001DFE4.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8001DFE4.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8001DFE4_scene-geometry_draw_dispatcher.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8001DFE4 — scene-geometry draw dispatcher
type: function
address: 0x8001DFE4
confidence: CONFIRMED
tags: [function, rendering, terrain, g30]
---
# FUNC_8001DFE4 — scene-geometry draw dispatcher (5 emitters)

> Dispatches scene geometry to a fixed set of 5 emitter routines — one of which ([[FUNC_800172DC]]) draws the terrain-mesh layer (later found to render **occluded** — the **visible** floor is LEVEL.DAT via [[FUNC_80010000]], f13; see [[Finding - Visible terrain renderer]], [[Gap Audit|GAP-0011]]). Found in G30 while mapping the render call tree.

| Field | Value |
|-------|-------|
| Address | 0x8001DFE4 |
| Source file | disasm only (G30) |
| Confidence | CONFIRMED (call tree mapped) |

## Purpose
Calls 5 scene-geometry emitters: `0x80014b04` (player/central prop), `0x80014ee0`, `0x800153d0`, `0x800163e0`, and `0x800172dc` (the **occluded** terrain-mesh layer — [[FUNC_800172DC]]; the visible floor is LEVEL.DAT via [[FUNC_80010000]]). A post-object pass `fcn.80027004`→`0x8001881c` (×26) applies depth-cue / sky-bg effects.

## Arguments / Returns
Scene context. Void.

## Calls (callees)
- [[FUNC_800172DC]] (occluded terrain-mesh layer) + 4 sibling emitters (`0x80014b04 / 0x80014ee0 / 0x800153d0 / 0x800163e0`).

## Called by (callers)
- [[FUNC_800224EC]] (render driver, scene path).

## Globals & structures touched
- geom base `[0x8008249c]`; OT base `[0x8008240c]`; per-frame staging `0x801cxxxx–0x801exxxx`.

## Evidence & confidence notes
G30 R1 mapped the render call tree and narrowed terrain to these emitters; R5 confirmed `fcn.800172dc` as the terrain-mesh emitter (later found to render **occluded** — the visible floor is LEVEL.DAT/`fcn.80010000`, [[Gap Audit|GAP-0011]]).

## Related
- Functions: [[FUNC_800172DC]] · [[FUNC_800224EC]] · [[FUNC_80060724]]
- Findings: [[Finding - Visible terrain renderer]] · Hubs: [[Rendering]]
- Source docs: `src_re_geometry/geometry_g30_terrain_render_source_plan.md`
