---
kind: experiment
id: Experiment_-_G6_render_sentinel
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: medium
legacy_source: ObsidianVault/Experiments/Experiment - G6 render sentinel.md
aliases:
  - "Experiment - G6 render sentinel"
---

# Experiment — G6 render sentinel

> Migrated from `ObsidianVault/Experiments/Experiment - G6 render sentinel.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G6 render sentinel

> Prove the trail-flag field has a visible effect by flipping it to a negative sentinel.

| Field | Value |
|-------|-------|
| Fixture / save state | operator boot of the built disc |
| Build image / tool | `ABL_G6_RENDER_SENTINEL_TEST.cue` via `tools/patch_g6_render_sentinel_test.py` → `tools/rebuild_with_patched_dat.py` |
| Patch | `DAT+0x1526` (runtime `0x80161d1e`) `41 00` → `ff ff` |
| Build SHA1 | `717a0875f28fd8c93c6db9209c5e7981f3fcc97d` |
| APIs used | offline build + operator visual test |

## Goal
Turn trail entry1's flag into `0xffff` (a negative sentinel) so the per-entry scan in [[FUNC_800140A0]] stops after entry0, and observe the rendered result.

## Procedure (reproducible)
1. `tools/patch_g6_render_sentinel_test.py <pristine LEVEL01 DAT> <out DAT>` — patches `0x1526`, verifies pristine bytes, hashes.
2. `tools/rebuild_with_patched_dat.py --patched-dat <out> --target files/LEVEL01/LEVEL.DAT --out-bin ABL_G6_RENDER_SENTINEL_TEST.bin ... --write`.
3. Boot the image; observe LEVEL01 ground/terrain.

## Result
Standing terrain/ground render mostly empty/missing; sky/horizon/grass remain; Flik and objects still load; **ground collision still usable** (Flik walks on now-invisible ground).

## Conclusion
`DAT+0x1526` gates terrain-render visibility at the render stage. Visual terrain and collision are separable — collision survived the visual kill. Early support for [[Finding - Visual is not collision]].

## Linked findings / functions / structures
- [[Finding - Trail flag gates terrain render]] · [[Finding - Visual is not collision]]
- [[FUNC_800140A0]] · [[MEM - Trail and pass3 tables]]
## Source
`src_re_geometry/geometry_g55_dynamic_watch.md` (§8), `src_re_geometry/geometry_notes.md`
