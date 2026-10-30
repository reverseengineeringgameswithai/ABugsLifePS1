---
kind: mod
id: MOD_g3_p73_pronounced_ground
name: G3 P73 pronounced uneven ground
status: separate_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
src_paths:
  - tools/abl_blender/g3_native_p53_bigland_scene.py
  - tools/build_g3_native.py
  - mod/smoke_test.py
build_paths:
  - build/g3_native_p73_pronounced_ground.blend
  - build/g3_native_p73_pronounced_ground_profile.json
  - build/g3_native_p73_pronounced_ground_surface.json
  - build/ABL_g3native_p73_pronounced_ground_terrain.DAT
  - build/ABL_g3native_p73_pronounced_ground_collision.RAW
related:
  - MOD_g3_p72_uneven_ground
  - MOD_g3_visual_collision_coverage_boundary
  - EXP_2026_07_11_p73_pronounced_ground
---

# G3 P73 pronounced uneven ground

## Retune

P72 was mechanically uneven but too subtle in ordinary gameplay. P73 widens and
raises the route mound, widens/deepens the following dip, and increases the global
micro-relief contribution. To retain walkable slopes, the older broad P53 relief is
reduced from scale 7 to 4.5 while the micro layer uses scale 2.0.

This makes the local terrain more legible without adding visual-only displacement:
the same Blender-exported `runtime_delta_y` grid still drives both regenerated DAT
terrain and chunk-32 collision RAW. The 500-unit flat spawn/respawn pad, smooth spawn
blend, outer-footprint taper, and P71 deep-pit boundary remain unchanged.

## Static result

- exported grid: 97x161;
- runtime delta range: `[-5912,3153]`;
- maximum adjacent runtime step: 462, below the proven 512 limit;
- authored first-route span: about 1812 runtime units;
- longer spawn-to-field mound/dip span: about 2559 runtime units.

Final assets:

- terrain DAT SHA-256
  `3426c1fb40b9fc03f6b7b46e9751a73b40963d9d5f6164c5a2c8723773b4dc52`;
- collision RAW SHA-256
  `1b6decca890f05f12710faa0ac685e5fa40692f81f1a4c5e5bf252688f93db73`;
- surface JSON SHA-256
  `834b45c05ab69e5279708dd75a04416f955e502c106599546fc49ca1a4105b70`;
- profile JSON SHA-256
  `684936109f435139d1f9a5435566022506432f68afedb1c8527d01377aa8014e`.

## Runtime and scope

The root test image is `ABL_P73_PRONOUNCED_GROUND_TEST.bin`, SHA-256
`bcb4c5c3194d1a6c689a3985563c33f679c342dbbc808835ef253ece47719a43`.
Cold-boot smoke observes a 1296-unit Flik-Y span and 1188-unit published floor-Y
span on the first Up walk, versus P72's 283 and 140. The complete P71 boundary,
native death/fade/respawn, pause/resume, and local post-respawn walk scenario passes.

This remains a separate operator-test artifact. Active ALLMODS and `mod/mods.yaml`
were not changed, and no runtime C change was needed. See
[[EXP_2026-07-11_p73_pronounced_ground]].
