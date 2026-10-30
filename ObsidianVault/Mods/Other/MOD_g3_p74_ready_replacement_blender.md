---
kind: mod
id: MOD_g3_p74_ready_replacement_blender
name: G3 P74 ready-replacement Blender workflow
status: visible_hills_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
src_paths:
  - G3_READY_REPLACEMENT_TEST.blend
  - templates/g3_native_ready_replacement.blend
  - tools/abl_blender/g3_native_ready_replacement_scene.py
  - tools/abl_blender/g3_coord_contract.py
  - tools/abl_blender/export_g3_native_profile.py
  - tools/native_terrain_export.py
  - tools/g3_native_gameplay_objects.py
  - tools/g3_native_replacement_build.py
  - tools/mod_studio_gui.py
  - tools/tier3_lanes.py
  - mod/smoke_test.py
  - tools/scenarios/duckstation/g3_ready_replacement_objects.yaml
build_paths:
  - build/ABL_G3_GUI_TEST.bin
  - build/ABL_G3_GUI_TEST.cue
  - build/ABL_G3_READY_REPLACEMENT_TEST.bin
  - build/ABL_G3_READY_REPLACEMENT_TEST.cue
  - build/g3_native_ready_replacement_replacement.DAT
  - build/g3_native_ready_replacement_replacement.RAW
related:
  - MOD_g3_p73_pronounced_ground
  - MOD_g3_visual_collision_coverage_boundary
  - EXP_2026_07_11_g3_ready_replacement_blender
---

# G3 P74 ready-replacement Blender workflow

## Result

`templates/g3_native_ready_replacement.blend` is now the practical authoring entry
point for a GTE-native LEVEL01 replacement. It composes the P73 pronounced matched
heightfield with native pickup and chunk-31 enemy Empty lanes instead of requiring a
separate Track-A scene or hand-written placement sidecar.

The starter scene has three collections:

- `G3_Controls`: Spawn, Goal, Marker;
- `G3_GameplayObjects`: 12 grain, four FLIK letters, four berry types, three seed
  token types, and one telescope;
- `G3_Enemies`: spider and worm donor examples.

The `.blend` contains a `G3_READY_REPLACEMENT_README` text block. The current root
scene and template are byte-identical, SHA-256
`567099f9b7634612c9c7855e886fab4aaf7b58df4c3016ebda38439ae716722d`.

## Visible-hill closure

The runtime-preview correction alone did not satisfy the visual acceptance test. Two
additional render facts mattered:

- the temporary `slope_gouraud_v1` default produced the yellow patch in front of
  Flik; it was a synthetic vertex tint, not a hill, and is no longer set by the
  starter scene;
- the retail renderer linked a full-width flat `GP0(60)` near-ground fill every
  frame at `0x8003DA90`. It visually restored a flat plane over the authored world.
  Both the standalone wrapper and consolidated `g3_bigland` stager now unlink that
  AddPrim call.

The primary grass/cliff panorama is deliberately **kept**. `--blank-backdrop` was
used only for a P80 isolation experiment and is not part of the replacement command.

The starter surface now uses broad hills rather than narrow bumps: exported delta
range `[-15507,11218]`, maximum adjacent step 1396/1536. It does not taper into an
artificial flat ring at the island boundary; the final DAT floor union ends directly
at the existing P71 bottomless pit.

On the final GUI disc, a fixed-frame Up climb kept grounded state `0x0101` at every
sample. The live floor rose from `-12392` at spawn to `-17384` after 96 input frames
and settled at `-18076`; Flik rose with it. The terrain visibly occludes the intact
cliff/grass backdrop at different screen heights. Evidence and hashes are in
[[EXP_2026-07-11_g3_ready_replacement_blender]].

## Coordinate and build contract

The current scene sets `abl_g3_coordinate_system=runtime_preview_v2`. The exporter
records gameplay Empty X/Z in native floor file coordinates and Z as a runtime Y
delta. Blender displays those unlike storage units at one runtime scale:

```text
Blender X = (file X * 32) / 256
Blender Y = (file Z * 32) / 256
Blender Z = -runtime delta Y / 256
```

The prior scene used `file X/256`, `file Z/256`, and
`-runtime delta Y/256`, so its viewport exaggerated every slope by 32x. That was a
preview/export-contract defect, not evidence of a flat fallback in LEVEL01. The V2
inverse is versioned in the exporter so the displayed mesh round-trips exactly.

`g3_native_replacement_build.py` resolves the P61 floor anchor
`-15904`, producing native runtime positions as:

```text
runtime X = file X << 5
runtime Z = file Z << 5
runtime Y = -15904 + exported runtime_delta_y
```

Every active gameplay Empty must be inside the final regenerated DAT floor union and
within 256 runtime Y units of the exported heightfield unless explicitly marked
`abl_g3_allow_float=true`. The starter placements are within 13 units.

Native type-0x3f composition is fixed-size. Authored entries are relocated in place;
the 46 unused supported retail slots are parked at file
`(-30000,25000,-30000)` / runtime `(-960000,800000,-960000)`. DAT remains 338352
bytes, preserving P57/P66 payload offsets and the P71 runtime gate. Unsupported pool
overflow fails instead of appending.

Actor composition runs after terrain collision generation. Chunk 31 is rebuilt from
LEVEL01 donor parameters and cleared to the authored roster, while the final chunk-32
terrain and pit collision remain intact.

## One-command authoring loop

```bash
python3 tools/g3_native_replacement_build.py \
  templates/g3_native_ready_replacement.blend
```

The wrapper performs Blender export, static G3 preflight, matched DAT/RAW generation,
object height/coverage validation, fixed pickup placement, actor roster replacement,
and an autolayout disc build. Active ALLMODS is never staged or replaced.

## ABL Mod Studio workflow

The repository-root `G3_READY_REPLACEMENT_TEST.blend` is a byte-identical working
copy of the frozen starter template. Its purpose is to make the intended authoring
loop unambiguous:

1. open `G3_READY_REPLACEMENT_TEST.blend` in Blender;
2. edit the `G3_Terrain` mesh and gameplay/enemy Empties, then save the scene;
3. run `python3 tools/mod_studio_gui.py`;
4. select **Level 1 — Anthill → Custom Level → Use ready test file**;
5. leave the separate output as `build/ABL_G3_GUI_TEST` and press **Build disc**.

`g3_replacement_blend` is intentionally a GUI source entry rather than a registered
disc stager. At build time the GUI invokes
`g3_native_replacement_build.py --prepare-only`, hashes the resulting DAT, RAW,
profile, and surface files, and writes `build/mod_studio_resolved.yaml`. That resolved
manifest replaces any stale `g3_bigland` entry and inserts the generated `g3_bigland`
asset first. The normal consolidated `mod/build.py` then layers the remaining selected
texture/audio assets over LEVEL01 and builds one disc. The source manifest retains the
`.blend`, so a later Build Disc always re-exports current saved Blender work rather
than silently reusing stale generated assets.

The GUI preserves a loaded legacy `g3_bigland` entry when no new `.blend` is selected.
The old generic `tier3_level` source key remains readable, but new manifests save the
explicit `g3_replacement_blend` key. Non-Anthill tabs show the current LEVEL01 scope
instead of accepting a file that cannot be built.

The exact GUI-equivalent artifact, fresh isolated DuckStation identities, object and
boundary scenario results, and report hashes are recorded in
[[EXP_2026-07-11_g3_ready_replacement_blender]].

## Historical P74 artifact (superseded by the V2 media below)

The validation disc is `build/ABL_G3_READY_REPLACEMENT_TEST.cue`:

- BIN SHA-256
  `9aa2092d97e2ed9cac68f2373abfcb236c206f746ddcb221e71ae5e7ac656f48`;
- CUE SHA-256
  `351f86531e5031ad91ae8c8efe8c3655e99d689ddd70b0b5f228ea6429e87996`;
- final DAT SHA-256
  `3db937b4874b43cea5c1fc9245cb54e5f72216a38920f9af8ad566d4f94e83fe`;
- final RAW SHA-256
  `e26e6ecb8af89d4f9dcdb8e5529f60fc7e0906b122f9dd8fb00138435ce39a0e`.

The normal one-command output `build/ABL_G3_READY_REPLACEMENT.cue` was then rebuilt
from the corrected scene. Its BIN SHA-256 is
`b48b2a809bd1d441402287cf07375cf0b32a18d6e5711748ff5a0e91f2669c23`; its CUE
SHA-256 remains
`db95cfc20a46ef4347ecc3e307f44699bc04ff84e1e7fcd42a27c937a5681e40`.

The GUI-equivalent consolidated disc is `build/ABL_G3_GUI_TEST.cue`; BIN SHA-256
`caed04f58358e61308c9d39c4a2c6b73806b1cd1e835d0c9e55ccf5a98264c29` and CUE
SHA-256 `f7a263ae73bc1d065334b5dec4367e591e4a15b3704725365c142760d3661eab`.
It contains the corrected G3 replacement plus blackberry, golddrop, and grain_hud,
and remains separate from `build/ABL_ALLMODS.*`.

Cold-boot behavior and provenance are in
[[EXP_2026-07-11_g3_ready_replacement_blender]].
