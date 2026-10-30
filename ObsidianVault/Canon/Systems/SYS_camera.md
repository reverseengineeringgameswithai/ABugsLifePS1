---
kind: system
id: SYS_camera
created: 2026-07-08
updated: 2026-07-08
status: live_confirmed
confidence: medium
source_state: original_game
functions: [camera_follow_update, camera_region_query]
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-08_understanding_campaign_u1]
src_paths: [src_re/camera_transform_block.c]
patch_policy: safe_to_read
---

# SYS_camera - world->view transform + follow

## Purpose
The camera's world→view rotation/position and the projection ABL's GTE performs — the data substrate
the Tier-3 render cave reads to project custom geometry exactly like the native world.

## World->view rotation R
- 3x3 row-major, 1.3.12 fixed-point (element = value × 4096), **includes the camera's baked ~1.6×
  horizontal zoom** (det ≈ 1.598 — rotation × zoom, not orthonormal). Equals GTE control regs 0..4 at
  the terrain world draw `0x80010718` (pure world→view, no per-object rotation loaded).
- **Mirrored live in main RAM, updated every frame:** `0x80090fb0` (authoritative copy the Tier-3
  render cave reads) + `0x8009e290` (near-identical sibling / staging). Reading the mirror needs no GTE
  access or hook-timing. Full layout + example matrix: src_re/camera_transform_block.c.

## Functions
- **`camera_follow_update`** (`0x8004df18`) — per-frame camera follow; calls the movement integrator
  (`player_movement_collision_integrator`), `atan2_heading`, and `camera_region_query`. The routine
  that recomputes R/C and loads the GTE each frame is not yet separately bounded (likely inline here).
- **`camera_region_query`** (`0x800376a0`) — point-in-polygon region test for the camera
  (calls `point_in_polygon_region_test`); determines which collision region the camera is over.
- CAMERA runtime struct near `0x80095358` (render/camera state; see [[Enemy_spawn_architecture]] note
  correcting the old "chaser" misread — `FUNC_8004DF18` = `camera_follow_update`, not enemy AI).

## Which camera feeds the frame
`camera_source_selector` `0x8004EA8C` chooses, every frame, between this follow camera
(`0x80095358`) and the **setpiece/cinematic camera** block `0x80090BC0`, writing the winner to
`0x8009EC50`. The switch is bit 0x01 of `0x80090BEE`. Full account, including why that word is not
a boss state variable: [[SYS_cinematic_camera]].

## Evidence
src_re/camera_transform_block.c (GTE-capture method, 2026-06-25); runtime call-graph cross-check in
[[EXP_2026-07-08_understanding_campaign_u1]]. Consumed by [[SYS_world_render_dispatch]] /
[[SYS_geometry_render_consumers]].
