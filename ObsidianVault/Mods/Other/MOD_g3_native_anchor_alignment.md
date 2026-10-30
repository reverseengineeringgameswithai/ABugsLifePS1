---
kind: mod
id: MOD_g3_native_anchor_alignment
name: G3-native visual/collision anchor alignment
status: composed_into_allmods_smoke_verified
created: 2026-07-10
updated: 2026-07-10
confidence: confirmed
source_state: mod
src_paths:
  - tools/build_g3_native.py
  - tools/regress_g3_native_authoring.py
  - tools/abl_blender/export_g3_native_profile.py
  - tools/native_terrain_export.py
  - tools/g3_bigland_stager.py
  - mod/mods.yaml
related:
  - EXP_2026_07_10_allmods_g3_anchor_and_coverage_regression
  - EXP_2026_07_10_bigland_oddities_hard_replacement
  - SYS_render_collision_source_separation
---

# G3-native visual/collision anchor alignment

## Mod contract

For a surface-JSON G3 build, `tools/build_g3_native.py` derives the effective
collision anchor from the actual native GTE visual frame:

`effective_pa_rt = round(base_y_model(spawn) * runtime_scale)`

The same effective value feeds:

- the visual/collision surface closures;
- emitted chunk-32 collision planes;
- the P11 runtime spawn floor and body Y;
- build/runtime reports.

LEVEL01 currently resolves `-497 * 32 = -15904`. A stale profile or command that
still requests `2144` is corrected automatically and reported. Deliberately
separated A/B experiments must pass `--allow-misaligned-pa-rt`; normal authoring
must never use that flag.

## Verification

`python3 tools/regress_g3_native_authoring.py` passes and covers both the safe
auto-aligned path and explicit differential escape hatch. The rebuilt canonical
image cold-boots with exact spawn and active `FUNC_80010000`; see
[[EXP_2026-07-10_allmods_g3_anchor_and_coverage_regression]].

## ALLMODS composition

Composed on 2026-07-10 through `tools/g3_bigland_stager.py` and the manifest asset
lane. The stager layers the grown Bigland DAT/RAW through the existing auto-layout
ISO reflow and appends the solved P11 runtime to unused Region-A capacity in
`LEVEL01/LEVEL.BIN`:

- runtime code `0x800B4030..0x800B4428`;
- level-local flags at `0x800B4428`;
- overlay-init installer at `0x800B44E0..0x800B456C`;
- resident marker gates copied at load to `0x80081A28` and `0x80081B60`.

The installer patches the player hook in RAM only after LEVEL01 begins loading.
An earlier disk-baked global hook made the from-boot fixture miss its menu inputs
even though the gate itself never executed; it was rejected by a gate-only control.
The overlay-installed form preserves front-end behavior and prevents the P11 body
or flags from colliding with Blackberry, Gold-drop, Grain HUD, or Training code.

Current composed image (P66 local visual refinement): `build/ABL_ALLMODS.bin`, SHA-256
`370c873f28b3c716a6512a4927d5461946495bff930dedbda77175318e1beca9`.
The standard smoke gate passes BOOT/ALIVE/RENDER/WALK at exact P61 spawn X
`197088`; the 64-frame walk moved `139734` runtime XZ units with sampled Y
`-12923..-12732`.

## P63 coherent pebble material

P61 still used a position hash to choose a different harvested `(batch ctrl,
UV, vertex tint)` for every regenerated quad. In motion this appeared as a quilt
of square terrain patches, not a continuous pebble field. P63 changes the shipped
styled-grid path to:

- canonical native pebble UV `c03f,c000,ff00,ff3f` on every quad;
- neutral `0x808080` modulation except the intentional marker tint;
- one explicit `0x0060` texture-page batch per payload;
- native bit-15 `0x8064` near-detail control for remaining quads.

`P57_STYLE_HASHED=1` retains the old patchwork only for differential experiments.
The canonical P63 terrain has two styles total (pebble + marker), versus 31 styles
and 336 colors in P61. Smoke frame SHA-256
`7c855375d152e7430b1e59b1981e27d9df5a2fcb208537ea9edb1df2ef00be6a`
shows the continuous pebble material.

## P64 hard replacement of stock terrain

Two operator saves exposed independent residuals after P63:

- `bigland_oddity_1.sav`: the cyan/green patch was the deliberately authored
  marker tint (`0xf0d040`), not corrupt texture state. Bigland now keeps the P11
  marker AABB/flag as an invisible runtime validation trigger and omits the floor
  tint (`--no-marker-visual`; Blender `abl_g3_marker_visual=false`).
- `bigland_oddity_2.sav`: the large mounds, walls, and detached strips were the
  twelve native node payloads below the canonical floor-payload range. P63 used
  `P57_FLOORS_ONLY=1`, so floor regeneration never touched them. P64 applies the
  size-preserving `collapse_nonfloor_payloads` pass through
  `--park-nonfloor-nodes`; all vertices in each of those twelve payloads are
  collapsed to one point while their relocation and node registration remain
  structurally valid.

P64 also passes `--sink-outside-collision 800000`. In chunk 32 this yields 85
new blocks on formerly flat sectors, 86 replaced authored blocks, seven sunk
outside-region records, and eleven sunk undecodable relocation-region records.
No active stock chunk-32 collision remains in the offline audit. This is not yet
an arbitrary complete collision world: 1,764/15,617 sampled surface nodes are not
covered by a decoded authored plane, and chunk 33/non-floor runtime collision
sources remain outside this tool's proven scope. The accurate audit status is
`chunk32_stock_collision_disabled_or_replaced_with_coverage_gaps`.

Canonical P64 assets:

- terrain DAT SHA-256 `47c6b507fd1e41f97de7f977bad4eebcdafae5cc9c67e12226df26052ec09b5d`;
- collision RAW SHA-256 `a406a72d21b1ae6a8c1cd2b3597d4a4cfc743a0be47c8bc5bb9ec3dea8de0d79`;
- composed ALLMODS BIN SHA-256
  `dd78c90e5a2ae5d9dc945a9dabca2ea667c1662a6fc91c5491a97f94cd1eab42`.

The authoring regression now proves that the collapse changes only the twelve
non-floor payloads, preserves DAT size and every floor payload byte, and that a
marker without visual metadata leaves the terrain unchanged. Runtime evidence is
kept separately in [[EXP_2026-07-10_bigland_oddities_hard_replacement]].

## P65 shared-workspace preservation

The P54 runtime option `--suppress-bulk-mesh` performed a one-shot zero of
`0x8012C1D0..0x8012E784`. It is now classified as an unsafe historical
differential and is disabled in `tools/g3_bigland_stager.py`.

This is not a rewrite of original input or animation logic. The solved assembly
shows L2/R2 selects throttle `768` in `FUNC_80048138` and animation `29` in
`actor_skinned_update`; live bad-ALLMODS traces reached both states. The fix is
MOD-side memory ownership: preserve the shared post-load workspace and continue
using P64's DAT payload collapse and RAW collision sinking for hard replacement.

`tools/regress_g3_native_authoring.py` now proves the destructive range-load
signature is absent from the safe runtime, present only in an explicit unsafe
differential, and absent from the shipping stager configuration. The rebuilt
overlay runtime is `0x800B4030..0x800B4320` (752 bytes), and its report contains
no `p54_suppress_bulk_mesh` entry. The final composed image SHA-256 is
`1c49482fc496549134aa82804ce6ffe2fac59513745a1a1b0fe473a409e7a113`.
Runtime evidence is kept in
[[EXP_2026-07-10_allmods_slowwalk_animation_regression]].

## P66 local primitive refinement

The apparent foot burial at LEVEL01 spawn was not another Y-anchor regression.
At the matched frame, Flik's foot plane and the authored visual differed by only
about 7 runtime units, while GPU picking showed a coarse authored `GP0(3C)` quad
as the final contributor over the foot pixels. The custom quad was overpainting
Flik at primitive-level ordering-table granularity.

The ship asset now refines only the native floor payload containing file-space
spawn `(6159,15403)` from 64 to 144 quads. It appends 4348 bytes and changes only
the existing relocation pointer in the old DAT prefix. Collision RAW, player
spawn, and the P65 shared-workspace fix are unchanged. Implementation is kept in
[[MOD_g3_local_visual_refinement]]; runtime evidence is kept in
[[EXP_2026-07-11_allmods_spawn_feet_ot_overpaint]].

## Movie boundary

`g3native_movie.movie.json` is synchronized to the standalone G3 disc, not the
composed ALLMODS front end; on ALLMODS it selects Training/LEVEL00. It must not be
used as Bigland evidence. `flik_to_level01_stall.mv.movie.json` remains the valid
ALLMODS boot fixture, but its 4253 recorded frames end while LEVEL01 is loading;
validators must continue neutral frames until Flik X is `197088` and P11 magic
`0x47335031` is present. A new ALLMODS→Bigland route movie is required before
retesting the late P53 collision frontier.

The remaining P53 free-roam collision miss is an RE/experiment issue, not part
of this MOD's anchor guarantee.

## P67-P71 rendered-coverage boundary

The turn-around edge exposed a second meaning of “visual/collision match.” P61
guarantees a shared absolute Y frame; it does not make the native DAT renderer's
30 registered payload footprints equal the wider chunk-32 collision footprint.
P67 first constrained collision to the actual post-regeneration DAT floor union,
but its raised outside floor made the original signed coyote delta negative and
enabled infinite mid-air jumps. P68 emits whole collision cells as either authored
terrain or a fixed Y `800000` pit. Leaving visible terrain now loses ground and cannot
re-arm the jump-state store instead of standing on the tan GP0(60) backdrop fill. P69
corrects P68's spawn-cell erosion. P71 restores the original scene-relative fall guard,
uses retail gravity and mode-2 death/fade, and pins the native respawn anchor to the authored
spawn so Flik returns on actual terrain. It clears grounded only; native air-state ownership
prevents repeated Cross from re-arming the slam sound/vertical hold. See [[MOD_g3_visual_collision_coverage_boundary]] and
[[EXP_2026-07-11_allmods_visual_collision_coverage_edge]].

## P72 uneven-ground authoring

P72 keeps the P61 shared visual/collision anchor and adds deterministic micro relief
to the Blender heightfield. The same exported grid still feeds terrain DAT and
collision RAW; the spawn pad and outer footprint taper remain compatible with P71's
native bottomless-pit boundary. It is validated as a separate manual-test image and is
not yet selected in ALLMODS. See [[MOD_g3_p72_uneven_ground]] and
[[EXP_2026-07-11_p72_uneven_ground]].

P73 increases the visible local relief without changing this anchor contract; see
[[MOD_g3_p73_pronounced_ground]].
