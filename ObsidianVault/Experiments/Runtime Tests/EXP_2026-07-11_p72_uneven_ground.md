---
kind: experiment
id: EXP_2026_07_11_p72_uneven_ground
name: P72 matched uneven terrain and collision
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod_experiment
related:
  - MOD_g3_p72_uneven_ground
  - MOD_g3_visual_collision_coverage_boundary
  - MOD_g3_native_anchor_alignment
---

# P72 matched uneven terrain and collision

## Question and construction

Can LEVEL01 gain gentle, OG-like irregular ground without recreating the earlier
render/collision split, unsafe platform-edge ramp, or bad respawn?

The final Blender scene was generated with:

```bash
flatpak run org.blender.Blender --background \
  --python tools/abl_blender/g3_native_p53_bigland_scene.py -- \
  build/g3_native_p72_uneven_ground.blend --nx 96 --nz 160 \
  --relief-scale 7 --micro-relief-scale 1.0
```

The exported surface/profile were preflighted with expected outside sink `800000`.
Result: pass, errors 0, exported grid 97x161, `dy=[-8614,4905]`, maximum adjacent
runtime step 499/512, and a valid walkable route. The matched build used the P71/P69
visual-union pit flags and `P57_FLOORS_ONLY=1 P58_ADAPTIVE_N=1 P60_SMOOTH=2`.

## Cold-boot evidence

All runtime work used fresh absolute `/tmp` config directories, dedicated loopback
ports/tokens, verified `SCUS-94288` media, the timing-matched
`flik_to_level01_stall.mv.movie.json` fixture, and PID-scoped cleanup.

Final manual media:

- BIN `ABL_P72_UNEVEN_GROUND_TEST.bin`, SHA-256
  `8551c5a7fadf9cb00c7bd77b1d3f66ca798f7a2c1509d9e65ec692657f793f6b`;
- CUE `ABL_P72_UNEVEN_GROUND_TEST.cue`, SHA-256
  `7aa1bd38e673b40b92666ff51b30d2939630b8c4758cc67e5afec202ac180512`.

Command:

```bash
python3 mod/smoke_test.py --disc ABL_P72_UNEVEN_GROUND_TEST.cue \
  --min-walk-y-span 250
```

Result: BOOT, ALIVE, RENDER, and WALK pass. Spawn X was 197088; walking moved 137022
runtime X/Z units locally. Body-Y samples spanned 283 (`-13171..-12888`) and floor-Y
samples spanned 140 (`-12848..-12708`). Smoke JSON SHA-256 is
`180394ca16b66560ec85624695e0de28e864afcd2931a05ea816d67ce2efe0cc`.

Boundary command:

```bash
python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/allmods_visual_union_boundary.yaml \
  --disc /tmp/abl-p72-build/ABL_P72_UNEVEN_GROUND_FINAL.cue \
  --output-dir /tmp/abl-p72-boundary-final2
```

All behavior assertions pass. The deep edge is ungrounded with floor Y `803200`;
Cross reaches the coyote check but causes zero mid-air jump-state writes, zero repeated
slam-sound re-arms, and zero vertical-hold re-arms. Native gravity and fall guards run,
mode-2 death/fade/respawn completes, Flik returns grounded near the exact checkpoint,
and pause/resume plus post-respawn Right movement work. Report JSON SHA-256 is
`a71f0c54fe0e4f1ec1854e00083284869713840da5f41d7855d4f0038902e296`.

The first final scenario run failed only `Z == 492896` after observing `492895`; every
physics, death, respawn, and pause assertion passed. The declarative check was corrected
to accept `[492894,492898]`, a bounded checkpoint neighborhood that still rejects the
historical shifted-spawn regression.

## Disc scope

Sector comparison against `ABL_P71_NATIVE_PIT_TEST.bin` found 378 changed sectors,
all confined to the LEVEL01 directory sector 2941 and DAT/RAW range 2944..3551; no
other disc sector changed. The active ALLMODS BIN/CUE and manifest were preserved.
