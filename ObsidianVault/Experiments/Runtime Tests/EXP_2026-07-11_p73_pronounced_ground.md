---
kind: experiment
id: EXP_2026_07_11_p73_pronounced_ground
name: P73 pronounced matched terrain runtime validation
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod_experiment
related:
  - MOD_g3_p73_pronounced_ground
  - MOD_g3_p72_uneven_ground
  - MOD_g3_visual_collision_coverage_boundary
---

# P73 pronounced matched terrain runtime validation

## Operator follow-up

The P72 manual test looked effectively flat. Candidate A proved that simply scaling
the micro layer to 3.0 produced a visible 2305-unit route span but failed preflight
with a 619-unit adjacent step. A narrower safe candidate passed at 504 but remained
subtle in a still frame. The accepted P73 shape widens the mound and dip, then uses
broad scale 4.5 and micro scale 2.0. It passes at 462/512 while producing larger,
smoother height changes.

## Media and cold boot

- BIN `ABL_P73_PRONOUNCED_GROUND_TEST.bin`, SHA-256
  `bcb4c5c3194d1a6c689a3985563c33f679c342dbbc808835ef253ece47719a43`;
- CUE SHA-256
  `b48bcbd4d079b4101f0d66ed36be2317fd6a4275787e5b466a6ebb655f82e403`;
- smoke JSON SHA-256
  `64142cfc928481d6d5a3466484f70bcd9ba614fc60cc5dae958691e45f1fb91e`.

The root artifact was cold-booted in the isolated smoke profile with:

```bash
python3 mod/smoke_test.py --disc ABL_P73_PRONOUNCED_GROUND_TEST.cue \
  --min-walk-y-span 1000
```

BOOT/ALIVE/RENDER/WALK all pass. The 64-frame Up walk moved 137125 runtime X/Z
units, stayed grounded, and recorded body Y `-14406..-13110` (span 1296) plus floor
Y `-13932..-12744` (span 1188). This is approximately 4.6x P72's body-Y observation
and 8.5x its floor-Y observation.

The declarative P71 boundary scenario also passes against the final P73 disc. Report:
`/tmp/abl-p73-boundary-final/allmods_visual_union_boundary.json`, SHA-256
`b494ca02584b17903d443633c9bfa714ae478e5f5c08e6fc40294a82e7d79f2e`.
It confirms deep-pit contact, no repeated Cross/slam feedback, native gravity and
mode-2 death, grounded checkpoint respawn, pause/resume, and local Right movement.
Media identity and PID-scoped cleanup passed.

Sector comparison with the P71 image found 378 changed sectors, all confined to the
LEVEL01 directory sector 2941 and DAT/RAW range 2944..3551. Active ALLMODS was not
rebuilt or replaced.
