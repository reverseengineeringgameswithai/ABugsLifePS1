---
kind: function
id: FUNC_8002D674
aliases: [FUNC_8002D674, 0x8002d674]
address: 0x8002d674
name: object_mesh_draw
status: live_confirmed
confidence: medium
source_state: original_game
system: [SYS_geometry_render_consumers]
calls: [SetRotMatrix, SetTransMatrix, RotTransPers]
reads: []
writes: []
uses_tables: []
evidence:
  - EXP_2026-07-08_understanding_campaign_u1
src_paths: []
patch_policy: unknown
---

# FUNC_8002D674 - object mesh draw

## Purpose

Per-object 3D mesh transform + draw for **dynamic** objects (enemies/props). Both object-render dispatchers — `dirt_object_dispatch` and `scene_geometry_draw_dispatcher` — call it; it builds a rotation + translation matrix and perspective-transforms the object's mesh (`SetRotMatrix`/`SetTransMatrix`/`RotTransPers`). At 9756 B this is the **largest resident unknown**; distinct from `FUNC_80010000` (the terrain/DAT payload emitter).

## Evidence (runtime, u1.2)

- **dynamic** — fired live in `bee.sav` (3 hits / 3 frames via `execTrace`); absent in the terrain-only ramp view, present once dynamic objects are on screen.
- Call-graph: callers `dirt_object_dispatch`, `scene_geometry_draw_dispatcher`; callees `SetRotMatrix`, `SetTransMatrix`, `RotTransPers` (+ helpers).
- Entry registers: `a0 = 0x8008a63c` (object data), `a2 = 0x00c09030` (packed colour/attr).
- Tier **proven** (runtime execution + unambiguous object-render call-graph). Deep per-field decomp pending.

Address `0x8002d674` (9756 B). See [[EXP_2026-07-08_understanding_campaign_u1]] · [[SYS_geometry_render_consumers]].
