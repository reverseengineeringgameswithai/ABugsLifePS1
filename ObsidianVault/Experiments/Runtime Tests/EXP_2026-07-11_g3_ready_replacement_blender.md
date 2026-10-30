---
kind: experiment
id: EXP_2026_07_11_g3_ready_replacement_blender
name: G3 ready-replacement Blender cold-boot validation
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod_experiment
related:
  - MOD_g3_p74_ready_replacement_blender
  - MOD_g3_p73_pronounced_ground
  - MOD_g3_visual_collision_coverage_boundary
---

# G3 ready-replacement Blender cold-boot validation

## Identity

The build was generated directly from
`templates/g3_native_ready_replacement.blend`, SHA-256
`8cde2b2084ce08fc13fee53973073f77f167e982c56be8d6a0c15b8137dce09e`,
with `tools/g3_native_replacement_build.py`. The resulting media is:

- BIN SHA-256
  `9aa2092d97e2ed9cac68f2373abfcb236c206f746ddcb221e71ae5e7ac656f48`;
- CUE SHA-256
  `351f86531e5031ad91ae8c8efe8c3655e99d689ddd70b0b5f228ea6429e87996`;
- serial/title `SCUS-94288` / `Disney-Pixar A Bug's Life`.

All emulator runs used fresh absolute `/tmp` configs, dedicated loopback ports and
tokens, timing-matched cold boot, verified media identity, and PID-scoped cleanup.

## Static composition

Preflight passes with a 97x161 surface, delta range `[-5912,3153]`, maximum adjacent
step 462/512, and sink Y 800000. The wrapper exported 24 native pickup objects and two
enemy records. All 26 active Empty placements are inside regenerated DAT coverage and
within 13 runtime Y units of the shared heightfield. Forty-six unused native object
slots were parked without changing DAT size.

## Behavioral proof

Smoke command:

```bash
python3 mod/smoke_test.py \
  --disc build/ABL_G3_READY_REPLACEMENT_TEST.cue \
  --min-walk-y-span 1000 --min-grain-count 1 --min-enemy-actors 1 \
  --expect-enemy-anchor 83200:-17472:537600
```

BOOT/ALIVE/ACTORS/RENDER/WALK pass. The authored spider is actor ID 9 at live pointer
`0x8009FD80` with exact Blender-authored anchor `(83200,-17472,537600)`. The normal
Up walk remains grounded, spans 1296 body-Y and 1188 floor-Y units, and collects seven
native Grain Empties; the captured HUD reads `07`. Smoke JSON SHA-256 is
`239783b1602f671de53855bec20bf700e143d6f70f432ffa85ff505de8eccab1`.

The final default-named artifact `build/ABL_G3_READY_REPLACEMENT.cue` was also
cold-booted directly with the same command and assertions. Its smoke JSON SHA-256 is
`fa62156a3b3bf59503764dc641381750ae6f665a376f0a56a0348cb0c89c5977`;
the BIN is byte-identical to the test image.

The smallest declarative regression is
`tools/scenarios/duckstation/g3_ready_replacement_objects.yaml`. It cold-boots the
same disc, asserts the spider pointer/ID/anchor before input, asserts grain count zero,
walks the authored trail, observes grain count greater than zero, and keeps grounded
authored-floor contact. Report:
`/tmp/abl-g3-ready-objects/g3_ready_replacement_objects.json`, SHA-256
`69d530170b8c69d60c88f8e7e25517548f94a2018eb972e783bb38947cf7f1df`.

The P71 boundary scenario also passes on the standalone replacement disc when its
ALLMODS-overlay-only init-flag expectation is overridden to zero. Deep pit contact,
Cross suppression, retail gravity, mode-2 death/fade/respawn, pause/resume, and local
post-respawn movement all pass. Report:
`/tmp/abl-g3-ready-boundary-final/allmods_visual_union_boundary.json`, SHA-256
`dff7d1ed994cbdcfba63d13cf54ec0c4d6b7aabd9e4c1e322b10ce564dd2610c`.

The active `build/ABL_ALLMODS.*` artifact and `mod/mods.yaml` were not changed.

## ABL Mod Studio source-to-disc validation

The GUI integration was validated by materializing the same source manifest shape
that `tools/mod_studio_gui.py` saves:

```yaml
code_mods: [blackberry, golddrop, grain_hud]
asset_mods:
  - tool: g3_replacement_blend
    level: anthill
    params: {blend_file: G3_READY_REPLACEMENT_TEST.blend}
```

`g3_native_replacement_build.py --prepare-only` regenerated the assets, and
`resolve_g3_blend_manifest()` produced `build/mod_studio_resolved.yaml` before the
normal consolidated build. The resulting separate test media is:

- `build/ABL_G3_GUI_TEST.bin`, SHA-256
  `820a2e1525a0a67bd2da744f167ac8623c9dd28ccaab77454cabf181fc35334d`;
- `build/ABL_G3_GUI_TEST.cue`, SHA-256
  `f7a263ae73bc1d065334b5dec4367e591e4a15b3704725365c142760d3661eab`;
- resolved manifest SHA-256
  `ef33f8e1c93956ae1f804855ffb949f2140cb9099c290619c5c68c785ebf2740`;
- generated DAT/RAW SHA-256
  `3db937b4874b43cea5c1fc9245cb54e5f72216a38920f9af8ad566d4f94e83fe` /
  `e26e6ecb8af89d4f9dcdb8e5529f60fc7e0906b122f9dd8fb00138435ce39a0e`.

Two fresh cold boots verified media as `SCUS-94288` / Disney-Pixar A Bug's Life.
They used configs `/tmp/abl-ps1-scenario-c0ewtlw0` on port 47683 and
`/tmp/abl-ps1-scenario-4540co1x` on port 45473. Both PID-scoped cleanup operations
succeeded. DuckStation was dirty fork revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, using
`build-release/bin/duckstation-qt` SHA-256
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.

`g3_ready_replacement_objects` passed on the GUI disc, proving the authored spider
anchor, native grain collection, and grounded uneven-floor walk. Report:
`/tmp/abl-g3-gui-test/g3_ready_replacement_objects.json`, SHA-256
`934e8b660f808006724fac5c2032b14fca1596cf05fbfcbe72d1108ee06ec11d`.

`allmods_visual_union_boundary` also passed without expectation overrides. It proved
deep-pit contact outside the visual union, Cross/coyote suppression, retail gravity,
native mode-2 death and life accounting, respawn on the authored floor, working
pause/resume, and local post-respawn movement. Report:
`/tmp/abl-g3-gui-boundary/allmods_visual_union_boundary.json`, SHA-256
`2501945bc2bbc9d0b4a4eb1ddf773b49a33d3071343e26edb0194c13654b10fb`.

Static validation after the GUI change: `148 passed, 7 deselected`; the declarative
hook/cave validator reported the selected blackberry, golddrop, and grain_hud module
layout valid. No save state was used for either behavioral run.

## 2026-07-11 WYSIWYG verification

The operator questioned whether the strongly wavy Blender overview was actually
present in LEVEL01. A fresh exact-media smoke run confirms that the authored surface
is active, but also confirms that the Blender viewport is not a literal game-scale
preview.

Observation:

- the current root working scene and the scene hash recorded by the GUI preparation
  report are both
  `8cde2b2084ce08fc13fee53973073f77f167e982c56be8d6a0c15b8137dce09e`;
- the disc-embedded DAT verification SHA-1
  `6b7f2ee76b45021d4b46707daf55f31feeda9d43` exactly matches
  `build/mod_studio_g3_replacement_replacement.DAT`;
- BOOT/ALIVE/ACTORS/RENDER/WALK passed again on `ABL_G3_GUI_TEST.cue`;
- the 137125-runtime-unit walk changed the live collision floor by 1188 units and
  Flik's body Y by 1296 units, remained grounded, and collected seven grain;
- the captured frame `build/ABL_G3_GUI_TEST_smoke.png` is visually much flatter than
  the Blender whole-map overview. Smoke JSON SHA-256:
  `d1bb0ea455a7bc4f2b3d47cbdacad206663a393551bb171e44aded356c007285`.

Confirmed explanation from the exporter/build contract: Blender stores horizontal
file coordinates and vertical runtime deltas at the same `1/256` display scale
(`bx=X/256`, `by=Z/256`, `bz=-runtime_delta_y/256`). At runtime, however, horizontal
X/Z are shifted by five (`*32`), while `runtime_delta_y` is already in runtime units;
the visual DAT delta is correspondingly `dy/32`. The exported full surface spans 9065
runtime Y units, but 711296 by 1295552 runtime horizontal units. Thus the Blender
viewport shows apparent whole-map height/span ratios of about 40.8%/22.4%, whereas
the game ratios are about 1.27%/0.70%: the preview exaggerates slopes by 32x.

Conclusion: terrain/collision export is functioning and matched, but the starter
`.blend` is not presently WYSIWYG for terrain proportions. The operator's visual
concern is valid; a follow-up workflow change should either display horizontal axes
at runtime scale in Blender or provide a game-scale preview object/view without
changing the established exporter data contract.

### Causal mapping check

A follow-up separated a faulty game mapping from a misleading Blender display scale.
The result confirms the former is not the problem:

- the smoothed source heightfield spans 8975 runtime Y units (`-5865..3110`);
- the 30 generated DAT floor payloads span 279 native file-Y units, or 8928 runtime
  units after the original renderer's uniform `<<5`; therefore the visual DAT retains
  essentially the full authored amplitude;
- at nine live grounded samples from spawn through the Up walk, the surface model
  predicted a 1709-unit contact-height span and actual Flik contact
  (`player_y - 3200`, per the native movement-integrator bias) spanned 1702 units;
- spawn contact was model `-15909`, live `-15904`; maximum pointwise residual on the
  moving/coarsely-tessellated path was 481 units, while every sample remained grounded.

The exact comparison is `/tmp/abl-g3-live-surface-compare.json`, SHA-256
`7bde56033d27f36b5ad1f9d6bc54c257136323932f56d7981f94eda9533d9d22`.
It used a fresh cold boot at `/tmp/dsrepro-smoke`, port 23465, verified media
`SCUS-94288` at `build/ABL_G3_GUI_TEST.cue`, and PID-scoped cleanup.

This narrows the defect precisely: the `.blend` contains valid authoring values and
the game maps visual and collision heights correctly. What is invalid for a
ready-editor promise is the viewport presentation: horizontal values are file-frame
coordinates while vertical values are already runtime deltas, so displaying those
axes with one Blender unit scale makes the terrain look 32x steeper than it will in
the original engine.

### Requested visual proof at the steepest authored transition

The operator then requested an actual in-game view rather than coordinate evidence.
The smoothed heightfield's strongest safe local transition was selected near
file-space `(1284,19518)`, runtime X/Z `(41088,624576)`, with modeled ground Y
`-16853`. The exact GUI disc was cold-booted, Flik was placed at that contact height,
the native camera/collision were advanced for 120 frames and then settled through
`experiment.warpAndSettle` (`stable=true`, frame 4510). Flik remained grounded at
body Y `-13653`, exactly ground + the native 3200 body bias.

Six captures covered the settled view and progressive L1/R1 camera rotations:

- `build/ABL_G3_BUMP_PROOF_SETTLED.png`;
- `build/ABL_G3_BUMP_PROOF_L1_30.png`, `...L1_60.png`;
- `build/ABL_G3_BUMP_PROOF_R1_30.png`, `...R1_60.png`, `...R1_90.png`.

The strongest-slope settled image SHA-256 is
`cc704bd45dc8bc68389b5972a453b40633b786a3e1f0e1535390d76106c8e56d`.
Structured proof is `/tmp/abl-g3-bump-visual-proof.json`, SHA-256
`2d5801ccb59056730462765e889cc306b782a16f7107d060caf22fdac769646f`.
The isolated PID was stopped through `/tmp/dsrepro-smoke` ownership.

Visual result: none of the six frames presents terrain a player would reasonably
describe as pronounced bumps or hills. The coordinate/render mapping evidence remains
valid, but it is insufficient to claim that the delivered starter scene is visibly
bumpy in play. The practical acceptance claim is therefore **failed**: the current
terrain is at most a broad, gentle grade under the normal game camera. A replacement
starter must be tuned against actual in-game screenshots/traversal, not approved from
the vertically exaggerated Blender overview or height-span numbers alone.

## Intermediate WYSIWYG contract correction (superseded by visible-hill closure)

This section fixed the coordinate contract but still did not satisfy the operator's
visible-hill acceptance test. The later closure section below supersedes its visual
claims while preserving the intermediate evidence.

### Observation

A fresh exact-disc GPU pick/trace at visible LEVEL01 floor pixels identified the floor
draw as the regenerated native pebble payload (`GP0(3c)` textured Gouraud quads). A
`GP0(60)` sprite was behind it, not covering it. Structured evidence:
`/tmp/abl-g3-floor-gpu-picks.json`, SHA-256
`1547b86629c4c44729f67ff1bd65c8060f394a95ec1bd12b727ee3abb153e813`.
Therefore the flat-looking capture was not a hidden retail floor or fallback sprite.

The legacy Blender scene displayed file-space horizontal X/Z and runtime-space Y with
the same `1/256` factor. Runtime X/Z are `file << 5`; runtime Y already is a runtime
quantity. The screenshot that looked dramatically wavy was therefore a 32x vertical
exaggeration relative to the game.

### Inference

Two authoring/display problems remained even though terrain and collision mapping was
numerically correct:

1. the `.blend` could not honestly serve as a WYSIWYG replacement because its axes
   represented unlike units;
2. Blender solid-mode normal lighting had no native LEVEL01 equivalent because the
   regenerated floor forced neutral `0x808080` vertex attributes. Under the follow
   camera and repeating pebble texture, broad safe grades had little relief cue.

### Causal correction

`runtime_preview_v2` now displays every axis at one runtime scale:

```text
bx = (file X * 32) / 256
by = (file Z * 32) / 256
bz = -runtime delta Y / 256
```

The inverse exporter is versioned and exact; unit tests cover coordinate round-trip
and equal displayed axis scale. The surface material requests
`slope_gouraud_v1`, which derives restrained native grayscale vertex attributes from
the authored physical slope. Its derivative explicitly converts file X/Z to runtime
X/Z by 32, avoiding the same unit error in the shading normal. Flat terrain remains
neutral `0x808080`.

The build wrapper now carries the scene's `abl_g3_max_step` into preflight instead of
silently applying the legacy default. Final preflight passes at 97x161, source delta
range `[-4525,2859]`, maximum adjacent step 1436/1536, with one informational
inspection warning and no errors.

Current byte-identical authoring files:

- `G3_READY_REPLACEMENT_TEST.blend`;
- `templates/g3_native_ready_replacement.blend`;
- SHA-256
  `3ee8a08f59befbfd6ffd620872647d19e21ded151bd0155d5acb2585e0366f03`.

### Behavioral confirmation

The corrected scene was passed through the actual ABL Mod Studio preparation and
consolidated `mod/build.py` lane with blackberry, golddrop, and grain_hud. The active
`build/ABL_ALLMODS.*` media was not changed. Final separate GUI media:

- BIN SHA-256
  `aea46ebc00fe35e2e4c7aaa0c37e4261879ffcbbbb2b7811f2a35183ee9231f7`;
- CUE SHA-256
  `f7a263ae73bc1d065334b5dec4367e591e4a15b3704725365c142760d3661eab`;
- generated DAT/RAW SHA-256
  `75bd9587f4e0a499b8539a4efaff760e4909e8f5d53d310304d63ce0f3e53056` /
  `b471aa579234bffce771bf0c73f4c00a7281d08277f3bb7a99d9221a822f9e85`.

A fresh cold-boot smoke run on `build/ABL_G3_GUI_TEST.cue` passed BOOT, ALIVE,
ACTORS, RENDER, and WALK. The Up traversal moved 138857 runtime XZ units, Flik body Y
spanned 3169 units, live floor Y spanned 2420, final grounded state was `0x0101`,
seven authored grain were collected, and actor ID 9 instantiated at exact authored
anchor `(83200,-16032,537600)`. Smoke JSON SHA-256:
`f0cfc6747a62109dca6e690f287cba3a9457ccfe82f2f257390d3eb3532808d5`.

The smallest declarative terrain/object regression
`g3_ready_replacement_objects.yaml` passed from cold boot. Report:
`/tmp/abl-g3-final-objects/g3_ready_replacement_objects.json`, SHA-256
`9775a41f61df664e94835f21aec3d4cfd3d2496ed012a9b6ce6ce91a4b95e929`.

The full visual-union boundary regression also passed on that GUI disc: leaving the
rendered floor produced deep-pit collision, retail gravity continued, repeated Cross
did not write a midair jump or re-arm butt-slam sound/hold, native mode-2 death and
life accounting ran, respawn returned grounded on the authored floor, pause/resume
worked, and right-walk remained local. Report:
`/tmp/abl-g3-final-boundary-pass/allmods_visual_union_boundary.json`, SHA-256
`a664d1c623df5c6ba695e1c6f340eb4bd89acd90ad024a624dded66aeb7813da`.

No save state was used. Each scenario used a fresh absolute DuckStation config,
dedicated loopback port/token, verified `SCUS-94288` media, and PID-scoped cleanup.

## P86 visible-hill closure with backdrop retained

The operator rejected the intermediate result because the floor still presented as a
long flat plane and identified a coloured patch in front of Flik as a possible clue.
The closure criterion was restated accurately: hills must be visible, and Flik must
walk up the same rendered terrain.

### Observation and controlled differentials

GPU picking separated three layers:

1. regenerated textured `GP0(3c)` floor quads;
2. a full-width untextured brown `GP0(60)` near-ground fill, linked each frame by the
   AddPrim call at `0x8003DA90`;
3. the primary grass/cliff panorama backdrop.

A cold-boot RAM A/B changed only `0x8003DA90` from pristine
`jal 0x80061b74` (`0x0c0186dd`) to `nop`. The in-memory frame diff reported 29794
changed pixels. Evidence: `/tmp/abl-g3-ground-fill-ab.json`, SHA-256
`772fdc834ab8fb967d2ad982bfa818d533a07d828a92904a4f5ba1b8112d6a1f`.
The experiment restored the instruction before PID-scoped shutdown.

The yellow foreground patch remained in that A/B and traced to the intermediate
`slope_gouraud_v1` vertex tint. It was not geometry. The starter no longer requests
that tint; neutral native attributes preserve the pebble texture without a false
colour cue.

`--blank-backdrop` was used once in the P80 differential to expose the authored mesh
silhouette. It proved that the small P79/P83 bumps existed but were visually too
weak. Per operator requirement, this flag was then removed. The final build retains
the primary grass/cliff panorama and suppresses only the flat near-ground fill.
The pristine and final GUI-prepared chunk-29 palette+image bytes are identical,
SHA-256 `ee884d1856387dc7b559a855f586d3db0bdb5ad7d6640a77c0890ec76b81b754`.

### Terrain correction

The narrow 2--4k runtime-unit Gaussian bumps were replaced with broad hills up to
roughly 15k units above the anchored spawn surface. Width increased with amplitude,
so the final 97x161 source grid still passes preflight:

- runtime delta range `[-15507,11218]`;
- maximum adjacent runtime step 1396/1536;
- no errors, one offline-inspection warning.

The artificial outer flat-ring taper was removed. Rendered terrain now continues as
authored to the DAT floor-union edge, where P71 changes directly to bottomless-pit
collision.

The consolidated stager now applies the same proven source patch as standalone builds:
`p57_ground_fill_suppressed = {site: 0x8003da90, was: jal 0x80061b74, now: nop}`.
It does not globally suppress `FUNC_8003E928` and does not blank the primary backdrop.

### Direct visible-hill and player-contact proof

Final authoring files are byte-identical:

- `G3_READY_REPLACEMENT_TEST.blend`;
- `templates/g3_native_ready_replacement.blend`;
- SHA-256
  `567099f9b7634612c9c7855e886fab4aaf7b58df4c3016ebda38439ae716722d`.

Final separate GUI media:

- `build/ABL_G3_GUI_TEST.bin`, SHA-256
  `caed04f58358e61308c9d39c4a2c6b73806b1cd1e835d0c9e55ccf5a98264c29`;
- CUE SHA-256
  `f7a263ae73bc1d065334b5dec4367e591e4a15b3704725365c142760d3661eab`;
- DAT/RAW SHA-256
  `b40a4cea7155977c47315bf432fb36a93fd9a8f2b971f8659457006521da0f42` /
  `c9ba2fc9319a1fb0e9fa67917e62725dccfca6f0ca001465483d947ab0267c2d`.

The cold-boot smoke walk on that exact GUI disc passed with:

- body-Y span 6541 (`-12797..-19338`);
- queried floor-Y span 6364 (`-12472..-18836`);
- final grounded state `0x0101`;
- seven grain and authored spider anchor `(83200,-20992,537600)`.

The fixed-frame climb is the direct closure artifact:
`/tmp/abl-g3-visible-hill-climb.json`, SHA-256
`cebf2940c76c1d70f8af0bb88b4d953dd4658690982f67a1713400e83b8b6e3d`.
At walk frames 0/24/48/72/96, grounded state was always `0x0101`; floor Y was
`-12392/-12600/-13300/-15256/-17384`, and Flik Y rose in the same sequence. After
release, floor Y settled at `-18076` with Flik grounded. The captures show the 3D
pebble terrain rising through and occluding the intact grass/cliff backdrop at
different heights rather than terminating in one horizontal plane.

### Regression closure

The strengthened declarative object scenario now asserts the spawn hill-base floor,
final floor below `-18000`, Flik body below `-18000`, and grounded state in addition
to the authored objects. It passed from cold boot; report
`/tmp/abl-g3-visible-final-objects-v2/g3_ready_replacement_objects.json`, SHA-256
`016cecb02574374e453eea4ceafb4141b40ab392f7b050bf78d2223e49292888`.

The full bottomless-boundary/death/respawn/pause scenario also passed with the new
hills; report `/tmp/abl-g3-visible-final-boundary/allmods_visual_union_boundary.json`,
SHA-256
`d7de7759ea77830a9d35992cdf8a2855cff07400b7eeb53a2f14f00c6937910d`.

All behavioral runs were cold boots with verified `SCUS-94288` media, fresh absolute
configs, dedicated loopback ports/tokens, no save state, and PID-scoped cleanup.
