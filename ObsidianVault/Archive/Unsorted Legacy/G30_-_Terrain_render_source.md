---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Geometry/G30 - Terrain render source.md
aliases:
  - "G30 - Terrain render source"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Geometry/G30 - Terrain render source.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: G30 - Terrain render source
type: subproject
status: core achieved; photogenic pit OPEN
tags: [subproject, geometry, rendering, terrain, g30]
---

# G30 — Visible terrain render source (subproject)

> Goal: find the world-space dirt renderer + its editable source, then produce a *visible* localized terrain change matched to collision. Working state: [[Fixture - g30 openground]] / [[Fixture - g30 openfloor]]. Plan: `src_re_geometry/geometry_g30_terrain_render_source_plan.md`.

> [!warning] "Visible terrain renderer" attribution SUPERSEDED (2026-06-18; reconciled M7 2026-06-21 · GAP-0009/0010/0011)
> The later 7-scene neutralize ([[Experiment - Visible floor renderer neutralize]]) found `fcn.800172dc`/chunk-35 is **occluded (~0 visible px)** — it is **not** the visible surface. The **visible walkable floor = LEVEL.DAT via [[FUNC_80010000]]** (f13), confirmed to the spawn area in M7 ([[Gap Audit|GAP-0011]] Verified). Read "the broad terrain surface is drawn by `fcn.800172dc`" below as **the occluded terrain mesh layer**.

## What was found (CONFIRMED method; one attribution SUPERSEDED — see banner)
- The broad terrain mesh layer is drawn by [[FUNC_800172DC]] from the persistent buffer [[MEM - Terrain vertex buffer 8012C1D0]] (GP0 0x3C quads), sourced from LEVEL.RAW **chunk 35** — but this layer is **occluded** (SUPERSEDED as "the visible surface"). → [[Finding - Visible terrain renderer]] · [[Finding - Terrain on-disk source is chunk 35]].
- The bulk **foreground** floor under Flik is drawn by [[FUNC_80010000]] via the [[FUNC_80019934]] sub-emitter from LEVEL.DAT objects (vert+0xa Y lever). → [[Finding - Visible ground from DAT verts]].
- The **sky** is a GP0 0x02 fill, recolorable via cache `0x800771bc/c0/c4`. → [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]].
- Localized editing works (per-quad SXY capture), and a **matched** visual+collision lower lands Flik coincident — consistency proven. → [[Finding - Localized terrain edit]].

## Open
A **dramatic, photogenic localized pit** is rendering-limited (near-ground bottom-clip at 512×224, camera-follows-Y, uniform/gouraud texture, strip-ordered buffer). Needs GTE-trace/frame-diff calibration. → P1 in [[Open Questions]] · method in [[Playbook - Correlate rendering and collision]].

## Experiments
[[Experiment - G30 localized terrain edit]] · [[Experiment - G30 sky recolor]] · (earlier: [[Experiment - G16 emitted payload vertex wall]] · [[Experiment - G28 Candidate A floor Y]])

## Tools / APIs
`tools/abl_dbg.py` · `tools/parse_level_raw_chunks.py` · `tools/vramdiff.py` · [[API - execTrace]] · [[API - gp0Trace]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - visual diff]]

## Related
[[Geometry]] · [[Geometry pipeline]] · [[Rendering]] · [[G29 - Collision source]]
