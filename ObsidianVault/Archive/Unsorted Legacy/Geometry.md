---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Geometry/Geometry.md
aliases:
  - "Geometry"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Geometry/Geometry.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Geometry
type: hub
tags: [hub, geometry]
---

# Geometry — Map of Content

> The geometry investigation (G1→G30) is the backbone of this project: how level geometry is **sourced**, **rendered**, and made **editable**, and the discovery that visual ≠ collision. See also [[Geometry pipeline]] for the data-flow, and [[Rendering]] / [[Collision]] for the two halves.

## The one-paragraph summary
Level geometry comes from two files. **Visual** geometry is LEVEL.DAT payloads ([[FUNC_80010000]], Candidate A) plus a LEVEL.RAW chunk-35 terrain buffer ([[FUNC_800172DC]]). **Collision** geometry is LEVEL.RAW chunk-32 planes built into a sector table ([[FUNC_8003633C]] resolves it). They are independent — see [[Finding - Visual is not collision]].

## Confirmed findings
- [[Finding - Visual is not collision]] ⭐ (central)
- [[Finding - Candidate A is DAT-backed visual terrain]] · [[Finding - Visible terrain renderer]] · [[Finding - Visible ground from DAT verts]]
- [[Finding - fcn.80010000 payload format]] · [[Finding - Payload vertex edits are visible]] · [[Finding - 0x356bc is a wall not floor]]
- [[Finding - entry24 is a culling row]] · [[Finding - Trail flag gates terrain render]] · [[Finding - Two parser source-record formats]]
- [[Finding - Floor resource is LEVEL.RAW]] · [[Finding - LEVEL.RAW is compressed]] · [[Finding - 0x801bdc58 is compressed source]] (retraction)
- [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Collision on-disk source is chunk 32]]

## Key functions
[[FUNC_8001CDC0]] (parser) → [[FUNC_800224EC]] (driver) → [[FUNC_800140A0]] (cull) → [[FUNC_8001EA6C]] / [[FUNC_800206E8]] (builders) → [[FUNC_80010000]] (emitter); [[FUNC_800172DC]] (terrain surface); [[FUNC_8003A318]] / [[FUNC_8001A1DC]] (RAW load/decompress).

## Structures
[[MEM - fcn.80010000 mesh payload]] · [[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - Trail and pass3 tables]] · [[MEM - Parser output record]] · [[MEM - DAT runtime memory map]] · [[MEM - LEVEL.RAW chunk model]]

## Experiments (the arc)
[[Experiment - G6 render sentinel]] → [[Experiment - G14 payload vertex grass]] → [[Experiment - G16 emitted payload vertex wall]] → [[Experiment - G28 Candidate A floor Y]] → [[Experiment - G30 localized terrain edit]]

## Playbooks
[[Playbook - Find geometry sources]] · [[Playbook - Trace rendering ownership]] · [[Playbook - Correlate rendering and collision]]

## Source docs
`src_re_geometry/geometry_notes.md` (hub) · `docs/GEOMETRY_RE_PLAN.md` · the `geometry_g*.md` step files.
