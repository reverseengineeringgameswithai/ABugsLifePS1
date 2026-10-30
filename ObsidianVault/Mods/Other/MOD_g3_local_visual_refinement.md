---
kind: mod
id: MOD_g3_local_visual_refinement
name: G3 local visual refinement for primitive-order artifacts
status: composed_into_allmods_smoke_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
canon_dependencies:
  - FUNC_80010000
  - SYS_render_collision_source_separation
src_paths:
  - tools/native_terrain_export.py
  - tools/build_g3_native.py
  - tools/floor_source_map.py
  - tools/regress_g3_native_authoring.py
  - mod/caves/tier3_otrender.c
build_paths:
  - mod/mods.yaml
evidence:
  - EXP_2026_07_11_allmods_spawn_feet_ot_overpaint
---

# G3 local visual refinement for primitive-order artifacts

## Change

`tools/build_g3_native.py` now accepts repeatable
`--refine-visual-point X:Z:N`. After the ordinary coherent floor regeneration,
it locates the single native DAT floor payload containing that file-space point
and rebuilds only that payload as an `N x N` grid.

The implementation preserves:

- the original node translation/registration;
- the payload's current XZ footprint;
- the same authored height sampler;
- the P63 coherent pebble material and explicit/detail batch controls;
- all collision data.

If the refined bytes exceed the old slot, the existing append-and-repoint path
adds the payload at DAT EOF and updates its one loader relocation field. P66 also
removes `floor_source_map.node_anchors`' stale `0x51418` ceiling so tooling can
follow second and later appended payloads through the actual in-file bound.

## Shipping configuration

Bigland adds:

`--refine-visual-point 6159:15403:12`

This changes spawn payload `0x1B9F0` from 64 to 144 quads. It is deliberately
local: refining every payload would multiply DAT size and visible primitive load
to fix a problem observed only at isolated near-field positions.

Canonical assets/output:

- terrain DAT: `build/ABL_g3native_p66_spawn_refine12_terrain.DAT`, SHA-256
  `5016106be99884b33438c540bdb9b099a77c2cc39fe323fe9ce626a8c964e63e`;
- collision RAW unchanged, SHA-256
  `a406a72d21b1ae6a8c1cd2b3597d4a4cfc743a0be47c8bc5bb9ec3dea8de0d79`;
- test cue: `build/ABL_ALLMODS.cue`;
- composed BIN SHA-256
  `370c873f28b3c716a6512a4927d5461946495bff930dedbda77175318e1beca9`.

## Guard

`test_local_visual_refinement_only_rebuilds_containing_payload` proves the
point resolves to exactly one payload, append/repoint occurs, the new primitive
count is exact, and a flat authored height is unchanged. The ordinary G3
authoring suite and consolidated smoke gate both pass.

Do not use this option to conceal a real collision/visual anchor mismatch. First
compare world heights and use GPU contributor evidence; refine only when a large
terrain primitive is demonstrably overpainting an actor.
