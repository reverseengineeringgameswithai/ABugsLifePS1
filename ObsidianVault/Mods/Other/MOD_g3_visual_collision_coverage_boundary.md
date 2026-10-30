---
kind: mod
id: MOD_g3_visual_collision_coverage_boundary
name: G3 rendered-floor collision boundary
status: composed_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
src_paths:
  - tools/build_g3_native.py
  - tools/regress_g3_native_authoring.py
  - tools/g3_bigland_stager.py
  - mod/mods.yaml
  - mod/caves/tier3_collision.c
  - mod/caves/tier3_otrender.c
build_paths:
  - build/ABL_g3native_p69_visual_union_cell_pit_collision.RAW
evidence:
  - EXP_2026_07_11_allmods_visual_collision_coverage_edge
related:
  - SYS_render_collision_source_separation
  - MOD_g3_native_anchor_alignment
---

# G3 rendered-floor collision boundary

## Contract

`tools/build_g3_native.py --visual-union-pit 800000` derives an X/Z union from
the actual post-regeneration terrain DAT (`floor_source_map.build_map(visual_bytes)`).
Inside that union, collision samples the unchanged Blender surface. Every emitted
native-lattice cell is classified by its center and emitted wholly as authored floor
or wholly as a fixed Y `800000` pit. This cell-quantized rule creates a discontinuous
ledge without interpolating a giant slope or eroding a valid edge cell merely because
one corner crosses a DAT-payload boundary.

At the authored/pit boundary, P71 clears only `grounded` while transition state is
zero. It does not write `air_state`, player Y, VY, lives, fade, or transition state.
The hook restores scene fall base `0x800822B4` to `91808`, so retail gravity
(VY +256, capped at 4096) reaches the original Y `100000` guard. The original code then
calls `FUNC_8004A700(..., mode=2)` and owns fade/death/respawn. Because
`FUNC_80054C90` otherwise records an edge position continuously, P71 pins the native
respawn-anchor triplet player+`0x50/+0x54/+0x58` to authored spawn
`(197088,-12704,492896)`.

For authored cells only, P69 also provides a missed-landing backstop: if the native
resolver publishes a valid authored `floor_Y` but Flik crosses below it at a selector
seam, the hook clamps Y to that floor, zeros vertical velocity, and republishes
grounded. It does not affect normal jumps because rising/airborne Flik is above the
floor, and pit cells fail the authored-floor threshold.

This is deliberately based on DAT coverage, not merely the Blender surface bounds.
The Blender heightfield is larger than the native renderer's registered payload
coverage, which caused the reported turn-around edge.

## Shipping configuration

`mod/mods.yaml` pins:

- terrain P66 SHA-256
  `5016106be99884b33438c540bdb9b099a77c2cc39fe323fe9ce626a8c964e63e`;
- P69 collision SHA-256
  `188bd1df71546bd48a5233434963c496ae9eeb141a44d9cd8968024213e65313`;
- `visual_union_pit_rt: 800000`.

`tools/g3_bigland_stager.py` rejects a pit that is not numerically deeper than Y `100000`
and records the topology/native-death contract in `ABL_ALLMODS_bigland_runtime_patch.json`.

Canonical generation adds the explicit flag to P66's command:

```bash
P57_FLOORS_ONLY=1 P58_ADAPTIVE_N=1 P60_SMOOTH=2 \
python3 tools/build_g3_native.py --planes \
  --out build/ABL_g3native_p69_visual_union_cell_pit \
  --pa-rt -15904 --rise 0 --corridor --flatten-blocks --suppress-grass \
  --replace-all-blocks --replace-tile-n 7 --coverage-margin 3000 \
  --p51-scratch-pack --blank-far-terrain --suppress-pass3-bitmap \
  --park-nonfloor-nodes --sink-outside-collision 800000 --no-marker-visual \
  --regen-visual 6 --refine-visual-point 6159:15403:12 \
  --visual-union-pit 800000 \
  --surface-json build/g3_native_p53_bigland_surface.json \
  --level-meta-json build/g3_native_p53_bigland_profile.json
```

## Scope and C distinction

Tier-3 Track A already reads render and collision from one shared triangle blob and
has a runtime no-floor branch in `mod/caves/tier3_collision.c`. ALLMODS Bigland is
Track B and does not execute that C hook; it uses native DAT visuals plus chunk-32
collision. The C comments now state this scope boundary so the stronger Track-A
topology guarantee is not misapplied to Track B.

This fix does not make every point in the Blender heightfield renderable. It converts
unsupported points into an intentional bottomless-pit boundary. Arbitrary full-field
visual coverage still requires solving the native payload cull/primitive-budget
frontier rather than enlarging collision alone.

## P67/P68 failures and P69 correction

P67 placed the outside collision floor `60000` runtime units above the authored
surface. That removed grounded contact but violated the original signed coyote check:
`floor_Y - player_Y < 1024` at `0x80048BAC`. A raised floor produces a large negative
delta, so repeated Cross presses remained eligible indefinitely. The P67 cold-boot
control recorded 7 coyote-decision hits and 5 jump-state writes at `0x80048BDC`; Flik
fell to Y `21493`, then repeated jumps climbed back to Y `-2187` without losing a life.

P68 reversed the sign by putting the outside floor far below Flik. The same attempted
input then saw a large positive delta. Its all-four-corners classifier avoided a ramp
but converted the coarse cell containing the valid spawn to pit because that cell
straddled payload X `6900`. Cold boot observed `floor_Y=803200` at spawn, large input
shifts, fade `0`, a green-screen lock, Start unable to set the pause flag, and eventual
execution in low BIOS memory.

P69 classifies the whole cell by its center, preserves the authored spawn floor, adds
the authored-floor missed-catch backstop, and never writes the global fade during the
MOD-owned death. An attempted exact AABB-edge splitter was rejected: it grew LEVEL.RAW
to about 3.8 MiB and crashed during level load. The center-classified RAW stays about
846 KiB and cold-boots normally.

## P70 native-death correction

P69 still bypassed the game: it forced Y/VY downward, decremented lives, and warped
Flik back without a native transition. Resolved assembly shows the retail sequence:

- ungrounded gravity adds `256`, caps VY at `4096`, and commits at `0x80048D8C`;
- `0x80049808` tests `player_Y > [0x800822B4] + 8192`;
- `0x80049868` calls `FUNC_8004A700` with mode 2, which stores transition state 2 and
  fade timer 23;
- the respawn handler restores the player from respawn-anchor offsets `+0x50/+0x54/+0x58`
  and executes the paired life adjustment at `0x8005B348`.

The deep chunk-32 pit had inflated the scene fall base to about `878592`, preventing
that guard from ever firing. P70 restores only that base, clears stale grounded state
at the boundary, and pins the authored respawn anchor. A first native-path build proved why
the respawn-anchor pin is required: `FUNC_80054C90` had continuously copied the live edge
position into the triplet, so mode 2 returned Flik beside the void rather than on terrain.

## P71 Cross/air-state correction

The operator's `p70_failure.movie.json` exposed a separate P70 feedback loop. At the
first pit frame, P70 wrote `air_state=2` at `0x800B4170`. Airborne Cross then followed
the retail `0x80048C6C` branch, called sound 27, set timer `player+0x84=10`, and wrote
state 4. The timer path at `0x80048DBC` holds VY at zero. P70 immediately rewrote state
4 to state 2, allowing every later Cross press to replay the sound and restart the hold.

P71 removes only the hook's state-2 store and retains the grounded clear. The native
state machine now advances state 1 to 2 itself, an airborne Cross can enter state 4 only
once, its timer expires, and gravity reaches the `4096` cap and mode-2 death threshold.
The same movie window changed from 11 sound-27 calls and 21 hook state-2 writes to one
sound-27 call, VY `4096`, and one native transition call.

## Verification

- Final consolidated runtime code occupies `0x800B4030..0x800B43E4`; level-local state
  begins at `0x800B4428`, with resident gate sources moved clear of it.
- Declarative cold boot reaches the exact grounded spawn, then the deep edge at
  Z `440252` with `floor_Y=803200` and no stable ground.
- Repeated Cross actions produce **zero** jump-state writes, **zero** repeated slam-sound
  calls, and **zero** vertical-hold stores. Native gravity commit and
  fall-compare PCs each execute 38 times; native life-adjust, transition-call, and
  transition-state-store PCs each execute once.
- Transition state reaches 2 with fade timer 23. Native respawn executes once and returns
  exact `(197088,-12704,492896)`, grounded `0x0101`, with displayed lives `5` after the
  original paired adjustments and fade timer back at zero.
- Start sets the pause flag after respawn and a second Start clears it. A subsequent
  Right hold remains local at `(198471,-12935,480232)` over authored floor `-12732`.
- The final scenario ran against the separate root-level
  `ABL_P71_NATIVE_PIT_TEST.cue`; its report is
  `/tmp/abl-p71-root-final/allmods_visual_union_boundary.json`, SHA-256
  `7164fb0507dd909af313b0feb6c497b6554979c22c06394e108893c75421ab51`;
  PID-scoped cleanup succeeded.
- Authoring regression and hash-pinned scenario/report evidence are listed in the
  experiment note.
- P71 was rebuilt from the validated P70 consolidated image because unrelated dirty
  TRAINING grain-gate C currently prevents a fresh all-assets build. Raw-disc comparison
  proves only LEVEL01/LEVEL.BIN sectors 2942-2943 changed (1,041 bytes differ). The
  separate manual-test BIN is `ABL_P71_NATIVE_PIT_TEST.bin`, SHA-256
  `d4db10ead77e6a0cdaf9fcfa5af35273225f3751fa76d2b4834b0f141b48ed28`.
  The operator's active ALLMODS image was intentionally left untouched.
