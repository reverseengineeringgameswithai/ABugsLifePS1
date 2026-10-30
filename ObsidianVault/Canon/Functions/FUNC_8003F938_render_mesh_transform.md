---
kind: function
id: FUNC_8003F938
aliases: [FUNC_8003F938, 0x8003f938]
address: 0x8003f938
name: render_mesh_transform
status: live_confirmed
confidence: medium
source_state: original_game
system: [SYS_geometry_render_consumers]
calls: [SetRotMatrix, SetTransMatrix, RotTransPers4]
reads: []
writes: []
uses_tables: []
evidence:
  - EXP_2026-07-08_understanding_campaign_u1
src_paths: []
patch_policy: unknown
---

# FUNC_8003F938 - render mesh transform

## Purpose

Render-pass 3D geometry transform. Loads a rotation + translation matrix (`SetRotMatrix`/`SetTransMatrix`) and perspective-projects a mesh's vertices in 4-vertex batches (`RotTransPers4`), using the PS1 scratchpad (`0x1f8003xx`, seen in `a0`/`a1` at entry) as the working vertex buffer. Driven each frame by `scene_render_driver`.

## Evidence (runtime, u1.1)

- **Byte-matched** (asm) and **dynamic** — fired live during LEVEL01 via `execTrace` (this-session save-state `ABL_looking_at_ramp_OG_Graphics.sav`).
- Call-graph: sole caller `scene_render_driver`; callees `SetRotMatrix`, `SetTransMatrix`, `RotTransPers4`.
- Entry registers: `a0`/`a1` point into scratchpad `0x1f8003xx`.
- Naming tier: **proven** (byte-matched + dynamic + unambiguous render-pipeline call-graph). Deep per-field decomp not yet done.

Address `0x8003f938` (4288 B). See [[EXP_2026-07-08_understanding_campaign_u1]] · [[SYS_geometry_render_consumers]].
