---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - DAT record holds decor instance world position.md
aliases:
  - "Finding - DAT record holds decor instance world position"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - DAT record holds decor instance world position.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_DAT_record_holds_decor_instance_world_position.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - DAT record holds decor instance world position
type: finding
confidence: CONFIRMED (visual)
gstep: editor-phase2
tags: [finding, geometry, dat, instancing, leveleditor]
---

# Finding — DAT pass-1 record carries each instance's world position

> Model-space `fcn.80010000` decor payloads are positioned in the world by the **pass-1 DAT records**, not a runtime transform. This unlocked placing the level's prop/foliage layer statically in the editor.

**Confidence:** CONFIRMED (visually validated headless render) · **Established:** level-editor Phase 2 (2026-06-20)

## Summary
Each LEVEL01 DAT **pass-1 record** (0x14-stride table at file `0x1504`, 484 records) holds a **world-space position** at `+0x00 / +0x04 / +0x08` (s32 x, y, z) and bridges via its source record (`+0x10` → src; src `+0x14`/`+0x1c`) to a payload offset. For a **model-space decor** payload (small local verts, instanced ≥2×), every copy is placed at `record_pos + local_vertex`. Validated: 20 decor payloads → **348 instances** spread across the level (X span ~20k) land coherently on the terrain among the pickups.

## Coordinate model (for the editor renderer)
- **World-space payloads** (floor/scenery, drawn once): vertices are absolute → render as-is.
- **Model-space decor** (instanced): render `record_pos + local_vertex` per instance.
- Both then take the global **Y flip** (`flip_y`, PS1 Y-down) that already aligns the DAT floor with the type-0x3f pickups.

## Evidence
- `tools` / `level_editor/scene_importer.py::survey_instances` walks pass-1 records; `scene3d.assemble` renders decor per-instance. Headless GPU render (`level_editor/test_scene3d.py::test_decor_instances_placed_in_world`) confirms instances span >10k world units (not piled at origin) and visually sit on the terrain.
- Candidate A (world-space, drawn once) has a single record at `(-263,-3476,-1249)`; decor `0x2d460` has 93 records spanning the level.

## Open / next
- **6 decor payloads have no pass-1 record** — likely referenced only by the **pass-3** table (`0x3afa`, 140 records); decode its position field to place the remainder.
- Per-instance **rotation/scale** (bytes after the position in the src record, e.g. `45 0f fd 10 …`) not yet decoded — props are placed translation-only.

## Coordinate frames — placement vs payload (CORRECTED 2026-06-20)
Two frames with **OPPOSITE Y sign** (proven by `grain_1_lower.sav`/`grain_1_higher.sav`: Flik's
runtime Y is −44196 at the *lower* grain and −42439 at the *higher* one → the game is **Y-UP**, a
higher object has a LARGER Y; the higher grain's file-Y −1465 > lower's −1618):
- **Placement frame** — type-0x3f pickups + decor record positions. **Y-up**: render Y = **+file_Y**.
- **Payload frame** — `fcn.80010000` vertices (floor/scenery + decor *local* verts). **Y-down**:
  render Y = **−vert_Y**. Floor/scenery then `+ WORLD_PAYLOAD_Y_OFFSET` (≈ render 1450) to land on the
  placement frame.

> [!bug] Earlier a single global `flip_y` negated BOTH frames → it **inverted pickup heights** (lower
> grain rendered higher — user-reported). Fixed by per-frame handling in `scene3d.assemble`: placement
> frame no-flip, payload frame flip. X/Z need no flip in either.

Also fixed: pick radius was `radius*0.02` (~13× the visual proxy) → clicks mis-picked far pickups; now
`focus_radius*0.008` (≈ proxy size). And `fcn.80010000` quads split as a **fan** `(v0,v1,v2)+(v0,v2,v3)`
(verts are perimeter-wound, not strip order).

## Related
- [[MEM - fcn.80010000 mesh payload]] · [[Finding - Candidate A is DAT-backed visual terrain]] · [[ABL 3D Phase 1 Gap Checklist]] · [[ABL 3D Level Editor Roadmap]]
- Tool: `level_editor/scene_importer.py` (`survey_instances`), `level_editor/scene3d.py` (`assemble`)
