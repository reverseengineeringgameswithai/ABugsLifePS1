---
kind: experiment
date: 2026-07-11
status: unresolved
level: LEVEL01
system: native GTE terrain, collision, camera, backdrop, bottomless fall
---

# LEVEL01 native-terrain reverse-engineering investigation

## Status

This investigation is **not solved and not promoted**. It has established the original render/collision data flow, disproved several old tool classifications, completed a byte-identical Blender no-op round trip, proven a controlled Blender terrain edit, and isolated the remaining coverage problem. No diagnostic DAT, RAW, blend, BIN, or CUE has been promoted to the GUI/default workflow.

**ALLMODS was never edited, staged, rebuilt, or replaced during this investigation.** Every runtime comparison used pristine media or a standalone `/tmp/ABL_TERRAIN_*` image. `tools/build_autolayout_disc.py` temporarily staged LEVEL01 DAT/RAW and restored them; the pre/post hashes remained:

- `REBUILD/files/LEVEL01/LEVEL.DAT`: `c2ed8f34158470148ef79d96ea74d7fa44035aa7ecf7c261b1cf32293016e71a`
- `REBUILD/files/LEVEL01/LEVEL.RAW`: `c07452bafcf3799b55574d1622a37189358f5debcbd1127e167fd0fe0181700e`

The current acceptance blocker is visual pit/coverage ownership. The open-bottom replacement correctly falls, dies, and respawns, but the original tan GP0(60) underlay remains visible through screen rays that are not covered by authored GTE geometry. Horizontal coverage removes the tan region but becomes a false walkable-looking sheet or an overhead slab during a fall. Vertical-only banks are camera-safe but have not yet covered the centerline opening.

## Reproducibility identity

### ABL repository

- Revision: `0aa0fac392bb3bd781c502b71e42346cb0a2738b`
- Worktree: heavily dirty before this task; operator work was preserved.
- New evidence note: this file only. Existing dirty Canon/Experiment/Mod notes were not overwritten as part of this consolidation.

### DuckStation fork

- Revision: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`
- Fork status: dirty; the running binary contains uncommitted external-debugger work.
- Executable: `~/duckstation/build-release/bin/duckstation-qt`
- Executable SHA-256: `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`
- All sessions used a fresh absolute config directory, unique port/token, verified media path/serial, and config-owned PID cleanup.

### Pristine media and movie

- CUE: `Disney-Pixar A Bug's Life (v1.0).cue`
- CUE SHA-256: `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`
- BIN SHA-256: `2aeafad70d12b1bd0dc63bbb106f22ced4fae070cea8eef9de4f11072e944566`
- Serial: `SCUS-94288`
- Movie: `movies/100% Runs/LEVEL01.movie.json`
- Movie SHA-256: `ece62d4e6f92b887b0500dd8ac3bec48f3638ad5d9858cda7d5b0afb3a8d2602`
- Movie format: v3, 15,230 frames, from boot, reproducible, not truncated.

## Concise diagnosis

The replacement stalled because it treated three different problems as one height profile:

1. The walkable top and collision can receive authored height successfully.
2. The gameplay camera follows broad elevation and reduces its screen-space effect; visible relief requires appropriate local curvature/wavelength, not merely a large total rise.
3. The original lower-screen terrain coverage is not a backdrop toggle or a binary “non-floor skirt” class. It is supplied partly by broad, shallow retail GTE topography such as payload `0xEB14`. Removing it exposes the native tan GP0(60) underlay. Replacing it with a narrow perimeter skirt cannot reproduce its raster footprint; replacing it with a broad horizontal apron creates false ground and becomes an overhead slab during bottomless falls.

Therefore “height reached DAT/RAW” and “Flik follows the floor” are necessary but not sufficient. The compiler needs separately authored walkable tops, collision, deep camera-safe cliffs/banks, and an explicit pit-background/coverage policy.

## Evidence categories

### Observations

- Authored height samples reach appended native DAT payloads and regenerated collision.
- Flik's floor/body follows the authored surface while grounded.
- Generated payloads are submitted through `FUNC_80010000`, caller `0x80020698`.
- The pristine frame-4382 coverage pixel `(486,202)` is a GP0(3C) quad over the tan GP0(60) sprite.
- Collapsing pristine `0xEB14` changes 3,440 pixels in display bbox `x=224..510, y=197..223`; the same pixel becomes tan `(165,132,107)`.
- Collapsing `0xD934` changes zero pixels at that matched frame.
- Open-bottom authored collision produces unsupported falling, native mode-2 death, fade/transition, checkpoint restoration, and grounded respawn.
- V14 horizontal coverage becomes a large overhead slab as the camera follows Flik into the pit.
- V15 vertical-only perimeter cliffs remove that slab but leave the tan GP0(60) underlay exposed.
- V21's runtime-Y-deep vertical banks extend through the fall camera and remain vertical, but a centerline tan opening remains.

### Inferences still bounded

- A production pit needs either a camera-safe authored distant bank/curtain that intercepts the centerline rays, or an explicitly understood native pit-background primitive. Side walls alone cannot cover a ray looking through an open bottom.
- The next primitive-level test should subdivide or trace the constant-Z bank before any further placement change. V22's coarse corner strips caused zero screenshot change; primitive rejection is plausible but not yet causally confirmed.
- The net-new top still does not meet the visible-curvature acceptance gate. Coverage architecture should be closed before another terrain-profile edit.

### Causal confirmations

- Whole-payload `0xEB14` collapse causes the lower-band coverage loss while leaving the tan GP0(60) contributor.
- Generated V7 DAT top quads own selected gameplay pixels; retained retail triangles do not overlap the authored play region.
- V7 RAW sector 99 owns the sampled floor and agrees with the authored top within 6.2 runtime units at the measured frames.
- V7's repeated-Cross experiment after support loss produced no repeated jump-state write and proceeded to native death/respawn.
- V13's added horizontal coverage removes the tan gap but makes the area read as continuous ground.
- V14's horizontal pit/coverage surface removes gaps at gameplay height and becomes an overhead slab during the unsupported fall.
- V15 removes every horizontal apron/cap while keeping collision byte-identical to V11/V14; the overhead slab disappears and the tan gap returns.
- V18's ~2,200-quad visual payload shifts cold-boot timing enough that the pinned movie is still on the LEVEL01 title card at target 4382. Payload/primitive budget is a behavioral constraint, not only a performance concern.
- V21 corrects vertical coverage to the runtime-Y scale. The resulting deep vertical walls appear through the fall without becoming horizontal ceilings.
- V22 adds two coarse corner strips but produces byte-identical matched screenshots to V21 at frames 4382 and 4452, so those strips are not visible contributors in that window.

## Original LEVEL01 render ownership

### Backdrop and fill are separate systems

- DRAWENV sky/background fill is GP0(02), built through the `SetDrawEnv2`/`0x800639CC` area.
- The primary 128x96 and secondary 128x128 panorama images use the rotation-only `FUNC_8003E928` GP0(65) path.
- The native tan near-ground underlay is a separate full-width GP0(60) primitive linked at `0x8003DA90`.
- Registered GTE terrain payloads use `FUNC_80010000` and overdraw the tan underlay where their primitives survive projection/culling.
- Pass-1 records, pass-3 records/bitmap, grass/mound submission, panoramas, the tan fill, and registered GTE nodes are not one suppressible “background” class.

The old tool name `--park-nonfloor-nodes` is misleading: it collapses twelve payloads selected by an address threshold. `P57_FLOORS_ONLY` likewise encodes `payload offset >= 0x10000`, not a proven engine role. The 30/12 address split must not be used as terrain ownership evidence.

### Exact pristine EB14 owner

The proven pristine display pixel `(486,202)` resolves to:

- Payload: `LEVEL.DAT + 0xEB14`
- Node record: `0x46E0`
- Anchor: `(8192,-8192,24576)`
- Runtime payload: `0x8016F30C`
- Batch 0, primitive 8
- Primitive DAT offset: `0xF16C`
- Runtime-copy primitive address: `0x8016F964`
- Indices: `[26,27,28,29]`
- Control: `0x0060`
- Source UV words: `00ff 00c0 3fc0 3fff`
- GPU command: GP0(3C), tpage `0x0660`, CLUT `0x3FFD`

World/file vertices:

| Vertex | World X | World Y | World Z |
|---:|---:|---:|---:|
| 26 | 6500 | 45 | 15500 |
| 27 | 6113 | 71 | 15525 |
| 28 | 6170 | 79 | 15103 |
| 29 | 6660 | 45 | 15149 |

At the picked pristine GPU frame its framebuffer vertices are `(560,472)`, `(487,460)`, `(549,486)`, `(443,467)`. With CRTC source Y=264, the quad directly covers the selected display pixel.

This primitive is shallow retail topography, not a vertical cliff/skirt. Correct terrain-grade analysis must compare its runtime Y to runtime X/Z (`file X/Z * 32`), not runtime Y to raw file X/Z. The full EB14 payload is 124 vertices / 95 quads / six batches and contains broad top/bank geometry; no separable vertical skirt batch was found. Retaining an EB14 subset as a coverage shortcut would retain retail topography.

Key evidence:

- `/tmp/abl-terrain-pristine-f4382-pick-eb14_edge-486-202.json` — SHA `bf0f8c5b968bda4201170484bab9199dfda0210c67450ac4a62dde40909356cf`
- `/tmp/abl-terrain-og-level01-f4382.png` — SHA `a409d6128fa32eb82063895a405e5b14223a7512f0abc62b906621d0d66dcd1c`
- `/tmp/abl-terrain-ab-eb14-f4382.png` — SHA `bd5e7683e84a8b01943609c28eb3bbab3f945127ec3a5a28267faa258dd7472d`
- `/tmp/abl-terrain-level01-payload-manifest.json` — SHA `33266f9b060200d38d07f38e8a830ff0b83e6757ff64a51e343104f9a3360c03`

## Collision and mechanics findings

The collision plane codec was corrected during this work. Plane bytes `+0x0C..+0x16` are two XYZ triangle edge vectors:

- edge 1: `(+0x0C,+0x0E,+0x10)`
- edge 2: `(+0x12,+0x14,+0x16)`

The normal agrees with `edge2 × edge1`. The semantic compiler now emits two native triangle records per walkable quad along the V0-V2 diagonal. Visual-only skirts/banks emit no collision.

V7 sampled visual/collision residuals:

| Movie frame | Residual |
|---:|---:|
| 4382 | +6.2 runtime units |
| 4397 | -5.8 runtime units |
| 4402 | -3.1 runtime units |

Maximum measured magnitude was 6.2, below the provisional 32-runtime-unit bound. Evidence: `/tmp/abl-terrain-net-new-v7-visual-collision-residuals.json`, SHA `5263bf85e670a8e5b65f44d16aad7dda57f5a17c5b3d9233f922fa80e43a8806`.

Native unsupported-fall ownership was observed at:

- `0x80049858`, `0x80049868`, `0x8004A9F4` — mode-2 bottomless trigger path
- `0x8005B134`, `0x8005B348` — transition/checkpoint restoration path

Post-respawn state was grounded at the authored spawn/checkpoint with lives decremented. Evidence: `/tmp/abl-terrain-v7-edge-death-respawn-exec-events-continued.json`, SHA `70d7b1a79ac3aa445e7253e7e865305b3c9180ff48872b04b9190bc25253e05b`.

Repeated Cross input after genuine support loss did not create an infinite rescue jump in the captured window. This is a narrow pass, not a substitute for the full regression scenario.

## Camera findings

The pristine route shows strong follow-camera compensation. Broad player/floor elevation becomes camera elevation, so total height is not equivalent to screen-space curvature. Original visible terrain depends on local curvature/wavelength, texture projection, silhouette/occlusion, and camera lag.

At the V20 unsupported-fall frame 4452:

- Player runtime XYZ: `(166917,24697,432427)`
- Camera-position scratchpad XYZ: `(190369,-9115,464748)`
- Floor: `0x80000000` (unsupported)
- Air/state: `3`

This capture exposed an important coordinate-contract error in V15-V20: coverage wall X/Z were authored in native file units and scaled by the engine, while visual Y was already being compared in runtime scale. A wall bottom of Y=6000 was therefore still above the player/death window at runtime Y≈24697. V21 regenerated vertical walls to Y=24000 while keeping X/Z in file units.

The latest `gpu.getCameraTransform` at frame 4452 returned `available:false` because the live GTE matrix belonged to the last transformed object and was not a trustworthy shared camera transform. The scratchpad camera position plus player position is the usable measurement for this frame; the unavailable helper result was not treated as camera proof.

## Blender round trip and controlled edit

### No-op round trip

The smallest original native terrain package was decoded, imported into Blender with the uniform coordinate contract, exported unchanged, and re-encoded byte-identically. Evidence report:

- `/tmp/abl-native-terrain-noop-roundtrip.json`
- SHA-256 `2ac493a13e898749fbe741171d9ab637a93006985157b3d3d1b3bb0d3cf30cc0`

This proves the payload grammar, anchors, vertices, batches, UV words, texture controls, and collision package can survive the Blender authoring loop without semantic drift.

### Controlled edit

A small downward valley edit passed the controlled-edit gate: generated DAT vertices changed in the intended region, generated collision followed the same authored surface, Flik remained grounded and followed the floor, and the change was visible without relying only on tint. A raised crest failed because the original upward-facing collision plane cannot catch Flik from below; that failure is retained as a collision-direction constraint.

## Net-new V7 proof

V7 was the first net-new minimal semantic terrain proof. It replaced the authored play-region contributors `0xD934`, `0xEB14`, and `0x1B9F0`; exact triangle audits found no retained visual or collision overlap in the authored region.

Confirmed:

- Generated top pointer `0x801B11CC` was submitted to `FUNC_80010000` by caller `0x80020698`.
- Generated page-0 GP0(3C) quads owned selected top pixels.
- Sector 99 collision contained 24 authored triangles and an exact 16-edge bottomless boundary.
- Visual/collision residual stayed below 32 runtime units.
- Unsupported fall, native death, fade, checkpoint restore, and respawn worked.

Rejected:

- The coverage donors were implemented as narrow vertical perimeter faces instead of broad coverage geometry.
- The resulting frame exposed the tan GP0(60) underlay.
- The top still read as a broad sheet under the camera.

## Diagnostic build matrix

All rows below are standalone `/tmp` discs. None is accepted.

| Build | Single purpose/result | Status |
|---|---|---|
| V7 | Net-new top + collision + narrow perimeter faces | Mechanics/ownership pass; coverage fail |
| V8 | Reverse one EB14 quad winding | Matched screenshot unchanged; winding alone rejected |
| V9 | Coarse authored horizontal banks | Some coverage restored; tan cracks remain |
| V10 | Finer ~500-unit horizontal grid | Seams remain; density alone rejected |
| V11 | Pristine-like floor/camera envelope | Floor/camera alignment improves; tan seams remain |
| V12 | Move EB14 apron Y to join seam | Large seam reduced; right gap remains |
| V13 | Add far-right horizontal apron | No tan gap at test frame, but false continuous ground |
| V14 | Convert coverage to pit floor/banks + cliffs | Gameplay frame covered; fall reveals overhead slab |
| V15 | Remove all horizontal coverage; segmented two-sided perimeter cliffs only | Camera-safe open pit; large tan underlay exposed |
| V16 | Add far vertical opposing bank at pristine EB14 far-Z bound | Bank appears only on right; center/left remain tan |
| V17 | Add U-shaped side/far vertical banks | Banks render; open side/center remains tan |
| V18 | Extend vertical geometry with ~2,200 quads | Cold-boot timing failure; title card still active at target 4382 |
| V19 | Budgeted deep side/far banks to file Y=6000 | Timing restored; tan corridor remains |
| V20 | Add fourth near vertical bank | Side banks visible; centerline tan remains |
| V21 | Correct vertical extent to runtime Y=24000 | Deep walls persist through fall; centerline tan remains |
| V22 | Add coarse near-corner strips | Zero matched screenshot change from V21 |

Selected semantic/screenshot hashes:

| Build | Semantics SHA-256 | Frame 4382 SHA-256 | Frame 4452 SHA-256 |
|---|---|---|---|
| V14 | `d8fc2032571eb1a8fc3e2056093192869ac6af56232f948eee8e9227c1973d5f` | `436c2d7414ca6e37b5e47b260bbecfaaaab17cd4ee4e2b5d6ca55b9fdea7152d` | `cb8f101b3131405860059381474e0fc1645cdee13959f4cfde709605142b2ccd` |
| V15 | `c8dc4eb85a270b1ae7094b0483fdee296a718caa084b64345a66af925df6de62` | `8ca83a2320ceeeb0c44f8c18f1f135ebf6897d14bf0cb9109d9d6230fae6ee25` | `2afe0736418e14d22d94317eef4405f37abc001eca7240f2eae8ee8d4fc18fce` |
| V16 | `62d26d2b509ac8a9a8f52be3aa77d81e53ffba6e57c6724dd1d421a76042a36f` | `70f36ed00b531a5493f77b4ae3cc4246d53e4d437486caa3cb151b4a7d80dc6f` | see `/tmp/abl-terrain-v16-f4452.png` |
| V17 | `d8fe515101107e84e8f0fe72f571372247681c4280ac8a62d88bb5358e8e10b3` | `aa358cd87f8730e620f3f364cb587b6ae6d679e800d832dcbbf824d286f89067` | see `/tmp/abl-terrain-v17-f4452.png` |
| V18 | `d36f8e9216d12f66a3f34e226c2788d8a775021554a33d36307572ab075dbaac` | `116941a0e2052137470ab46de1daa1cddb2b938543becadff553943344ca3e5a` (title card, invalid gameplay comparison) | `272f4c850b257e3b365a862a20ea177190371facb404339fb63b84cf1b3c2958` |
| V19 | `0bbb363508bc1a3e07e4c711ff28d098195af457b387fbf5b9e4951bfc62d40d` | `411169f2c13c870d990595b8467ffaacb2a13c9e6f153a0d83315c2b79cb3188` | see `/tmp/abl-terrain-v19-f4452.png` |
| V20 | `b68a3de3ff9592ff53882b7ce8eee161b7b44c5c5d8f51abcd5eb7c1802dd673` | `a360fd90b55368b61646bba13253612a02438e1308fb293facd01af1c8bb79a6` | see `/tmp/abl-terrain-v20-f4452.png` |
| V21 | `e03aa1dd8c14900d3f2e5b00d827b645ab6bd1a72d238db90abaac4f81dc4ae4` | `3da82fe173325a565fca7c242aeaa4beaec2f68adea7ecd37e5edc317283e599` | `4b2e0f3f51c4faec975dc38bd9e44f8e9115db103a0385f577c1c59131be2199` |
| V22 | `605f961d1f992129d947b0f39c7687d862e79834b25a05c1818778381f8d000c` | `3da82fe173325a565fca7c242aeaa4beaec2f68adea7ecd37e5edc317283e599` | `4b2e0f3f51c4faec975dc38bd9e44f8e9115db103a0385f577c1c59131be2199` |

## Tooling implemented but not promoted

New/untracked authoring/compiler files created during the investigation:

- `tools/native_terrain_patch_package.py`
- `tools/abl_blender/import_native_terrain_patch.py`
- `tools/abl_blender/export_native_terrain_patch.py`
- `tools/abl_blender/edit_native_terrain_vertex.py`
- `tools/native_terrain_semantic_compiler.py`
- `tools/abl_blender/export_native_terrain_semantics.py`
- `tools/abl_blender/make_native_terrain_minimal_scene.py`
- `tests/test_native_terrain_semantic_compiler.py`

Targeted collision-format changes exist in:

- `tools/native_collision_mesh_codec.py`
- `tools/heightfield_collision.py`
- `tools/emit_collision_reheight.py`

The semantic compiler currently supports explicit payload targets/anchors, walkable flags, visual-only faces, collision-sector assignment, an exact authored bottomless boundary, appended/repointed DAT payloads, and replacement RAW collision sectors. The initial semantic tests passed 5/5 before the V15-V22 runtime work.

These files remain investigation WIP. The current Blender minimal-scene generator still describes an earlier V7-style scene and must not be treated as the accepted V21/V22 semantics. No GUI/default/ALLMODS integration was performed.

## Runtime command pattern

Representative clean cold-boot workflow (ports/configs/tokens changed per run):

```text
launch_debugger_instance.sh start --config-dir /tmp/<unique> --port <unique> --token <unique> --disc /tmp/<standalone>.cue
debugger.status
emulator.getMediaInfo
debugger.pause
movie.load {"path":"~/Downloads/ABL/movies/100% Runs/LEVEL01.movie.json"}
movie.startPlayback {"start_frame":0,"load_start_state":true}
movie.advanceToFrame {"frame":4382,"max_frames":5000}
debugger.pause
emulator.captureFrame {"path":"/tmp/<capture>.png"}
gpu.pickObject {"x":486,"y":202,"all_contributors":true}
```

Representative player-state read:

```text
debugger.scatterRead {
  "reads":[
    {"address":"0x800a6500","type":"u32"},
    {"address":"0x800a6504","type":"u32"},
    {"address":"0x800a6508","type":"u32"},
    {"address":"0x800a6530","type":"u32"},
    {"address":"0x800a6548","type":"u32"},
    {"address":"0x800a6580","type":"u16"},
    {"address":"0x800a6582","type":"u16"}
  ]
}
```

Every completed instance was stopped through `launch_debugger_instance.sh stop --config-dir <owned-config>`. No broad process-name kill was used.

## Invalid/failed runtime attempts retained

- One long frame advance timed out and closed the client connection. The instance was queried/stopped through its owned config and recreated; the state-changing call was not blindly repeated.
- One V10 bulk `gpu.pickObject` call timed out; its screenshot survived but the missing pick was not treated as negative evidence.
- A stopped/restarted pristine movie playback remained API-labeled reproducible but captured a nearly black frame and zero LEVEL01 renderer calls. That rerun was discarded, the instance was stopped, and a fresh config/port was used.
- V18 reached movie frame 4382 while still displaying the LEVEL01 title card. This is recorded as a cold-boot timing failure caused by the much larger visual payload, not as terrain-screen evidence.

## Current stop conditions

Do not:

- promote V13's horizontal apron, V14's horizontal pit surface, or V15-V22's incomplete vertical enclosure;
- retain pristine EB14/D934 topography as a coverage shortcut;
- suppress or blank the genuine panoramas;
- use the tan fill, a colored tint, or vertex shading as primary relief proof;
- call the workflow WYSIWYG;
- update ALLMODS or the GUI/default workflow;
- tune another height profile until the centerline coverage primitive is traced or designed causally.

## Next evidence gate

1. Trace the constant-Z near/far authored bank through its exact `FUNC_80010000` control path and packet-store PC at the matched V21/V22 frame.
2. Determine whether the centerline bank cells are backface/near-plane/size rejected, outside the active node projection, or simply outside the camera ray.
3. If primitive-size rejection is confirmed, subdivide one measured western/center cell only and require a matched pixel ownership change.
4. If vertical geometry cannot cover the open-bottom centerline without an artificial shaft wall, classify the tan GP0(60) as a separate pit-background problem and test a native replacement primitive without modifying the genuine panoramas.
5. Only after the coverage gate passes, return to local walkable-top curvature and require generated DAT pixel ownership plus visual/collision agreement.
6. Then complete pause, buttslam, unsupported repeated-jump, native death/fade/respawn, actors/grain, backdrop-hash, and standalone regression scenarios before any GUI or ALLMODS work.

## Related notes

- [[FUNC_80010000_per-object_mesh_draw_-_payload_emitter]]
- [[FUNC_80048138_player_vertical_update]]
- [[SYS_render_collision_source_separation]]
- [[MEM_8012C1D0_Shared_mesh_vertex_buffer_8012C1D0_(terrain_+_actors)]]
- [[Finding_-_Sky_is_a_GP0_background_fill]]
- [[FUNC_800639CC_DRAWENV_background-fill_builder]]
- [[EXP_2026-07-11_g3_ready_replacement_blender]]
- [[MOD_g3_p74_ready_replacement_blender]]
- [[MOD_g3_local_visual_refinement]]
- [[MOD_g3_visual_collision_coverage_boundary]]

