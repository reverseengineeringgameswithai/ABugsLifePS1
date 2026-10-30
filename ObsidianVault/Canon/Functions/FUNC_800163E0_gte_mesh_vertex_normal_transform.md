---
kind: function
id: FUNC_800163E0
aliases:
- FUNC_800163E0
- '0x800163e0'
- gte_mesh_vertex_normal_transform
address: '0x800163e0'
name: gte_mesh_vertex_normal_transform
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- VectorNormal
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_800163E0 - gte_mesh_vertex_normal_transform

## Purpose
GTE-heavy per-vertex normal/transform setup for a mesh, driven by draw dispatchers

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Saves regs to scratchpad 0x1f800000, dense COP2/GTE vector pipeline
- Calls VectorNormal (0x80060284) x3 on mesh edge vectors
- Reads mesh header (vertex count lh at +12 of arg0), inits per-vertex table 0x80091a38 to -1 (4x -1 per stride-32)
- callers scene_geometry_draw_dispatcher, dirt_object_dispatch, boss_defeat_fsm_mesh_transform

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
