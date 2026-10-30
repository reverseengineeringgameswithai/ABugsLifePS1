---
kind: mod
id: MOD_g3_p72_uneven_ground
name: G3 P72 deterministic uneven ground
status: separate_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
src_paths:
  - tools/abl_blender/g3_native_p53_bigland_scene.py
  - tools/build_g3_native.py
  - mod/smoke_test.py
  - tools/scenarios/duckstation/allmods_visual_union_boundary.yaml
build_paths:
  - build/g3_native_p72_uneven_ground.blend
  - build/g3_native_p72_uneven_ground_profile.json
  - build/g3_native_p72_uneven_ground_surface.json
  - build/ABL_g3native_p72_uneven_ground_terrain.DAT
  - build/ABL_g3native_p72_uneven_ground_collision.RAW
related:
  - MOD_g3_native_anchor_alignment
  - MOD_g3_visual_collision_coverage_boundary
  - EXP_2026_07_11_p72_uneven_ground
---

# G3 P72 deterministic uneven ground

## Contract

P72 adds opt-in, deterministic small-scale relief to the P53 Bigland Blender
generator with `--micro-relief-scale`. The default is zero, so existing P53/P66
generation is unchanged. With the P72 value `1.0`, the surface combines broad waves,
a crossing wave, a shallow ramped shelf, broad soil swells, and a mound/dip pair on
the ordinary spawn-to-field route. It is fixed geometry, not per-run randomness.

The spawn/respawn pad itself remains flat: micro relief is zero inside 500 file units and
smoothly reaches full strength by 1200. Relief also tapers at the authored footprint
edge so it cannot turn the P71 discontinuous bottomless boundary into a ramp.

This is not visual-only noise. Blender exports one `runtime_delta_y` heightfield and
`tools/build_g3_native.py` samples that same grid for the regenerated terrain DAT and
chunk-32 collision RAW. The scene records `abl_g3_sink_outside_collision=800000`, so
unsupported rendered-floor cells retain the P71 pit contract.

## P72 build

Canonical authoring values are a 97x161 exported grid, broad relief scale `7`, micro
relief scale `1.0`, and `P60_SMOOTH=2`. Preflight passes with exported deltas
`[-8614,4905]`, maximum adjacent runtime step `499` under the `512` limit, and a
walkable spawn-to-goal path.

Final matched assets:

- terrain DAT SHA-256
  `ee558e63c290f910daeb0dffc7a5e37180e8202f8f1c1848914eddf758a10192`;
- collision RAW SHA-256
  `d2a9643f4add49e7f7269a219aa79ea6863028ea7f4db250f736f8e0e88f8cc2`;
- surface JSON SHA-256
  `3a3045bb4ab1510545c05b3ef435c31808eb4344319dcdd7f6dc94f01381840d`;
- profile JSON SHA-256
  `85ea0cbe5d8f0c12f1921b9011471db3bdcdeda93a25893c3191b3a6d4cd47dd`.

The manual-test image is deliberately separate from active ALLMODS:
`ABL_P72_UNEVEN_GROUND_TEST.bin`, SHA-256
`8551c5a7fadf9cb00c7bd77b1d3f66ca798f7a2c1509d9e65ec692657f793f6b`.
It inherits the validated P71 `LEVEL.BIN`; only the LEVEL01 directory sector and the
DAT/RAW sector range differ from the P71 image. `mod/mods.yaml` and
`build/ABL_ALLMODS.*` were not switched to P72.

## Verification

Cold-boot smoke passes BOOT/ALIVE/RENDER/WALK. Holding Up on the ordinary route moved
137022 runtime X/Z units; Flik's sampled Y span was 283 and the published collision
floor span was 140. The previous flat P71 control produced only a 218 body-Y span and
fails the P72-specific `--min-walk-y-span 250` assertion.

The P71 boundary scenario also passes on P72: outside terrain publishes floor Y
`803200`, repeated Cross cannot write another jump state or re-arm the slam sound,
native gravity/death/fade/respawn runs, Flik returns grounded on the authored spawn,
and pause/resume plus the post-respawn Right walk remain functional. The scenario's
spawn-Z check now allows native integration jitter of one runtime unit instead of
requiring a brittle exact value.

Runtime commands, media hashes, and report hashes are recorded in
[[EXP_2026-07-11_p72_uneven_ground]].

## P73 follow-up

The operator found this P72 tuning too subtle. P73 is the stronger manual-test
successor: it widens the route mound/dip and produces a 1296-unit runtime body-Y span
while retaining the shared terrain/collision grid and P71 pit behavior. See
[[MOD_g3_p73_pronounced_ground]].
