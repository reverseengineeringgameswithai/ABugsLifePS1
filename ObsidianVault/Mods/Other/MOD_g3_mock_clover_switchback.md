---
kind: mod
id: MOD_g3_mock_clover_switchback
name: G3 Clover Switchback mock LEVEL01 replacement
status: r29_walked_visual_candidate_accepted_gate_b_unclaimed
created: 2026-08-10
updated: 2026-08-11
confidence: high
source_state: mod
src_paths:
  - tools/abl_blender/g3_native_mock_switchback_semantic_scene.py
  - templates/g3_native_mock_switchback_r29_semantic.blend
  - tools/g3_native_semantic_replacement_build.py
  - tools/scenarios/duckstation/g3_mock_clover_switchback.yaml
  - tests/test_g3_mock_switchback.py
  - ObsidianVault/_attachments/g3_mock_switchback_concept.png
related:
  - MOD_native_blender_level_layout_export
---

# G3 Clover Switchback mock LEVEL01 replacement

## Scope

This is a real `LEVEL01` / Anthill replacement test built through the accepted
Blender-to-native Gate-A lane. It uses the original game's GTE renderer, native DAT
terrain, native RAW collision, fixed-pool gameplay objects, and approved donor
actors. It does not select the Track-A custom renderer or collision engine.

The mock is a Gate-B draft, not yet Gate-B acceptance. A complete cold-boot driven
route still has to prove that all accepted play is owned by the new visual and
collision surface.

## Concept image

![[g3_mock_switchback_concept.png]]

Generated project concept SHA-256:
`60d56ab92a56c51eb04ce052c3594310af5e7925db0625aa3b1d0a3baf113e6e`.

The built-in image-generation prompt requested an original late-1990s low-poly garden
environment with one continuous heightfield, a readable S-shaped switchback, broad
ramps, a pickup trail, and no caves, overhangs, stacked floors, vertical cliffs,
editor UI, text, logos, or recognizable copyrighted characters. The image is a design
target, not runtime evidence or a claim that every decorative prop is exportable.

## Authored layout

Working name: **Clover Switchback**.

```text
Spawn basin         ( 6159, 15403)  runtime delta-Y      0
First terrace       ( 3300, 17400)  target delta-Y   -1300
Western high turn   (-2600, 19700)  target delta-Y   -3900
Eastern saddle      ( 4700, 22500)  target delta-Y   -2200
Northwest goal turn (-1000, 24000)  target delta-Y   -6200
```

This creates three readable elevation events: climb, descend into a saddle, and climb
again. The first leg retains the proven Anthill entry coordinate so the pinned cold
boot fixture can enter the test, but the later hairpin route, terrain field, goal,
pickup trail, and enemy placements are newly authored.

The implementation is one smooth polyline-derived corridor field blended into broad
low-frequency soil relief. Adjacent switchback arms blend all segment samples instead
of choosing a discontinuous nearest segment. The generated exact native grid measures:

```text
grid                 97 x 161
runtime delta-Y      -6012 .. 3008
maximum adjacent step 899
authoring limit       1536
native objects        22
approved actors       2
```

## Draft failure and correction

R1 passed Blender export and preflight but failed the later DAT visual-ownership gate.
Three late-route placements were outside regenerated floor coverage:

```text
Grain.016   (-3585, 23337)
GreenBerry  (-3900, 22900)
Telescope   (-5800, 23900)
```

The validator was not weakened. A direct query of the generated DAT ownership map
showed the northwestern leg had crossed the supported union. R2 moved the final turn
inward to `(-1000, 24000)` and relocated the affected objects while retaining the
switchback and final climb.

## R2 prepare evidence

Command:

```bash
python3 tools/g3_native_replacement_build.py \
  templates/g3_native_mock_switchback.blend \
  --work-prefix build/g3_mock_switchback_r2 \
  --out build/ABL_G3_MOCK_SWITCHBACK_R2_20260810 \
  --prepare-only
```

Observed result:

```text
pristine identity       PASS 327/327
real Blender export     PASS
preflight               PASS, 0 errors, 0 warnings
visual/collision build  PASS, matched DAT/RAW
gameplay validation     PASS, all 22+2 placements on regenerated DAT coverage
Track-A modules         not selected
```

## R2 remaining work (historical)

At the R2 prepare-only checkpoint, the protected disc build, isolated cold boot,
runtime identity checks, and behavioral assertions remained outstanding. R4 below
completed those bounded integration checks. A complete newly authored start-to-goal
drive still remains necessary for Gate B; marker/goal teleports are functional
controls, not driven-path evidence.

## R4 stable test candidate

R3 moved the authored spider onto the first climb for a stronger cold-boot check.
Runtime diagnosis showed that the previous Gate-A scenario was candidate-specific:
it correctly reached and traversed the mock but hardcoded the old terrain's enemy
coordinates, elevation band, marker, and goal. R4 uses the final spider placement at
`(2600, 16800)` and a dedicated declarative scenario whose constants are regression-
checked against the mock generator.

Protected build command:

```bash
python3 tools/g3_native_replacement_build.py \
  templates/g3_native_mock_switchback.blend \
  --work-prefix build/g3_mock_switchback_r4 \
  --out build/ABL_G3_MOCK_SWITCHBACK_R4_20260810
```

The build passed pristine identity 327/327, real Blender export, 0-error/0-warning
preflight, placement coverage, module-matrix admission, protected output policy, and
post-layout embedded-byte verification. Final staged LBAs are EXE 23, LEVEL01 BIN
2905, DAT 2907, and RAW 3071. The 38-file build-manifest source closure has zero
post-build drift and neither ALLMODS nor a derivative image appears in the reports.

Key SHA-256 bindings:

```text
concept image       60d56ab92a56c51eb04ce052c3594310af5e7925db0625aa3b1d0a3baf113e6e
scene generator     f0a4372ef2ed1247077d27b944383680e8d091ebd040ae7e202849eb3b420362
Blender scene       43b701ffe7efa2427c2bedda433256fd072aa8e81a98ee2779d3ea1c99b93cba
runtime scenario    066be9f0c128727f35e9bbadd97428b7c8620885ac3f6333c98a659308b4c590
profile             dca984bca1cda3a503489ac18ce0be573dfd513e9e457f64922928768e810361
surface             9fef8eefdb56a5cb78f5ebe101e24ffc5c67f43fb95fd467be87365babb7c57e
roster              a3c0705a85fe01b12210ec3e34836d740607bc54ff6d386d035396423ef4de5c
replacement DAT     c4b017ec0e14affd3e2c68fef0b26743b1cdf038d3d9eb2079b7a06bb326ffd0
replacement RAW     045cd44e23be40194f29f65b72279983b16cb6f1d7ed4e858d0b0e4c47240cae
preflight           f74cd2fa5820c78390ae60b5e84f74bf93bb8379e1002d4c67ebed69ae7d2dd0
module manifest     250fa289c4087cd381135c52f957f2a025a3a992ba3f97ba0203d8a441b26593
disc BIN            14964c96a3060a08f4fbece7720d3a11415df6aa4d3c08ceb8c1c0db0aae5d9e
disc CUE            418d5c57df3cc302c1329a72393dcf3427be3be4edf9e32c5fab779d9adcd15d
build manifest      df0b06dfa682717afae06699c12fa820786dd66314e69d30a21b9ff67efe8649
wrapper report      d56c078c3445fcd2af2626034c5f661d4e54910de97c0a5c5e9cd9845ab457cb
runtime receipt     6df7e32a39c9dfb77ef9431066304e95ef272b4ca16ab6e1719c9ca981150f01
```

## Phase-4 capsule-first disposition

The current capsule validator was rerun before live testing. Report
`/tmp/abl_g3_mock_switchback_capsule_audit.json`, SHA-256
`8e66ec0495bd483e5e5b3898ac3027529070b3a6cf98d44cdcb3c85c97955dde`,
reports `complete=false`: 50/137 capsules are present and the independent comparison
has 87 mismatches. No retained pristine capsule can contain the newly authored
DAT/RAW and runtime hook state.

Named escalation reason: **invalid relevant capsule plus modified-disc-only visual,
collision, object, and control domains**.

## R4 cold-boot evidence

Command:

```bash
python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/g3_mock_clover_switchback.yaml \
  --disc build/ABL_G3_MOCK_SWITCHBACK_R4_20260810.cue \
  --output-dir /tmp/abl-g3-mock-switchback-r4-20260810-v1
```

Result: `PASSED`. Receipt
`/tmp/abl-g3-mock-switchback-r4-20260810-v1/g3_mock_clover_switchback.json`,
SHA-256 `6df7e32a39c9dfb77ef9431066304e95ef272b4ca16ab6e1719c9ca981150f01`.

The run started from reset/cold boot with the timing-matched movie and no state load.
It verified `SCUS-94288`, the exact R4 CUE/BIN, an isolated absolute config directory,
dedicated loopback port/token, and PID-owned cleanup. Before media inspection or guest
mutation it authenticated the running debugger binary SHA-256
`2ddaad7b1fdbca78110e3a871fd15496923e03be470d2e08e356a006b460dcf4`
and all 221 callable method schemas; the canonical inventory hash is
`abdb61e0fe33c6e957685d2e2fbda20c08272276eeb3a77d45abe802789edd4e`.

All six triggers completed and all 28 assertions passed. They cover the mock spawn,
new first climb, matched authored floor/collision, native grain collection, authored
spider donor slot and coordinates, marker, goal/transition, Track-B resident hook,
and pristine Track-A collision/render hook words.

The marker and goal phases intentionally teleport to the exported controls. Therefore
this is strong mock-level integration evidence but not a complete driven-path Gate-B
proof. The pinned movie naturally drives only the spawn and first-climb window.

## Final regression evidence

```text
focused mock/authoring/compiler/scenario tests  PASS 33/33
protected build/layout tests                   PASS 16/16
pristine identity                              PASS 327/327
hook/cave layout validator                     PASS
git diff --check                               PASS
```

## Hard-review handoff

James independently regenerated and preflighted the scene, verified pristine identity
327/327, reran the protected tests, found zero build-manifest drift, matched all four
staged payload hashes to their built-disc LBAs, and completed a fresh isolated
cold-boot rerun.

**James verdict: ACCEPTED (2026-08-10).**

The accepted claim is deliberately bounded: this is a new Blender-authored Anthill
replacement, a protected native disc build, and successful cold-boot integration.
James was not asked to accept full Gate B. The end-to-end driven route remains future
work.

## Post-acceptance visual gate: REJECTED

The first hard review proved integration but did not inspect the scenario's rendered
PNG captures. That omission was material. The scenario already declared screenshots,
but `ScenarioRunner` wrote them beneath the disposable isolated-config directory;
PID-owned cleanup then removed the files while the receipt retained only dead paths
and hashes. The runner now accepts a report-owned evidence directory, and its CLI
persists screenshots under `<output-dir>/evidence`. The focused scenario/identity
tests pass 9/9 with a regression for persistent screenshot evidence.

Fresh cold-boot visual command:

```bash
python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/g3_mock_clover_switchback.yaml \
  --disc build/ABL_G3_MOCK_SWITCHBACK_R4_20260810.cue \
  --output-dir /tmp/abl-g3-mock-switchback-r4-visual-20260810-v1
```

The run passed all behavioral assertions and preserved three 800x610 screenshots:

```text
receipt                    96497ef68f5ddeffa806bc12e6061985aa4f59c55703817a157c341d863cee62
mock_spawn_view            2566957df723b97a12d6a9ff09ba45820841ba71844f735f41b95208eb449f9d
mock_first_climb_view       a486adac9e90d26cd30db143362fb4bcc514d9820bc0d2c168b0012e18391c06
mock_route_objects_view     93a3e86580390ac836a1f33473a695c12082e689fad97ee4aa041aa264d16048
```

Direct inspection rejects R4's presentation. Observation: the ground contains large
flat peach/green polygons, stretched and smeared donor textures, abrupt tile changes,
and weak switchback readability. There is no evidence of a crash or missing terrain;
this is a visual mapping/retile failure, not a functional collision failure.

Therefore James's `ACCEPTED` remains valid only for the explicitly bounded native
integration claim. R4 is **not visually accepted**, not presentation-ready, and not
Gate B. Diagnose and repair the DAT visual/UV tiling path, rebuild from pristine, then
repeat behavioral and screenshot review before seeking another acceptance.

## R5 coherent-material refactor: still REJECTED

Diagnosis found that `build_grid_payload_styled` position-hashed unrelated harvested
UV/page rows and vertex colors onto new quads. R5 replaces the default with one proven
dirt UV cell, neutral vertex modulation, an explicit page primer, and bit-15 inherited
near-detail batches. The historical patchwork is retained only behind the explicit
`P57_STYLE_HASHED=1` experiment flag. New visual-material tests plus the focused
terrain/authoring suite pass 26/26.

Protected R5 build and fresh cold boot both pass. Bindings:

```text
disc BIN                    c66b044bea8582375c051dd9c13f73c86c5b106b5f580a2bebe77687b6f81543
disc CUE                    03c8bbbddb8149cdbb65198c935c8a307440ef8ed6e5ac005eb20f8b5b31d6b2
build manifest              e95c20c30aa67a7776b85008f910fea1eaffbdab13c93ced5cc02e8fa18c562c
replacement report          f21cc7950dc7260b589499fde8ee2cb28f4dc6c39003ba389a7875294f19755c
visual cold-boot receipt    fa430f208ebd7a1f5004f3afb2f0ac8df152892f966747f0b3c3dbc34e6306e5
spawn PNG                   ef43e771f9eb9c3be1d5027d0d483910d04837a9681911aa6150ff04e3d34940
first-climb PNG             f5bd72aabeb37fa6108ac5fb7c2ea6759197163e5c5d5493aa1b50c9888155d1
route-objects PNG           d22022e7058f442cb221d8838ba5cf670c61340c3903ff64dd8898d7bfa4b920
```

Direct inspection confirms the R4 peach/green holes and material discontinuities are
gone. It also exposes the next failure: the repeated high-frequency dirt tile creates
strong moire, and the current 0..-6200 runtime-Y route changes are too shallow over the
horizontal distances to read as a switchback from the native camera.

**James visual verdict: REJECTED (2026-08-10).** His executable falsifier is that a
player shown only the spawn/first-climb/route-object frames cannot identify the climb
or its intended direction. R6 must supply unmistakable medium-scale silhouette,
material/UV zoning, or native landmarks before another hard review.

## R18 failure: Phase-4 contract regression

R18 replaced retained descriptor-copy collision owners with explicit empty blocks,
which fixed the earlier hidden-retail-floor alias. A cold boot then proved spawn
ownership but Flik fell during the first climb. The retained Phase-4 C01 Anthill
capsule was validated directly before another replay: 11 chunks, 645 records,
1,935 RAM/VRAM/SPU checks, 944,067 flow items and 20,675,828 instructions with zero
mismatches. Its manifest SHA-256 is
`9cd98e28d7a7fd253f8f1227b3ebe290d49140022a4a2983b3159273ffa3f2fa`.
The global capsule-index check is presently stale because the operator movie tree
has expanded; that global failure was not misrepresented as invalidating this exact
pinned capsule.

The solved player chain is:

```text
0x8003633C  player movement/candidate builder
0x80036BC8  definitive player candidate boundary
0x80035280  ordinary swept resolver
0x80032610  collision point-in-triangle leaf
0x8003573C  accepted collision response
0x80036CE8/EC/F0  resolved X/Y/Z commits
```

R18 reached the boundary with authored sectors 150/152 and up to eight candidate
planes. At frame 5487 all candidates crossed the swept-plane distance gates but all
returned false from `0x80032610`; by frame 5489 Flik was below the planes and the
resolver correctly refused to recatch him. This ruled out missing candidate owners,
steep slopes and Track-A interference.

The cause was not an unknown seam rule. The Phase-4/July-11 note had already solved
plane bytes `+0x0C..+0x16` as two complete XYZ edge vectors. A newer codec regressed
them into three interleaved X/Z deltas. Its accessor reconstructed plausible Y values
from the normal, masking the corrupt on-disc layout in unit tests. The compiler was
therefore feeding scrambled edges to `0x80032610`.

The codec now packs literal `edge1.xyz, edge2.xyz`; every heightfield rectangle emits
two native triangles; and the compiler test asserts the six raw s16 words, not merely
a derived accessor. The Canon record table and recovered C commentary were corrected
to match the solved ASM. The same player ASM also proves `+0x1C/+0x1D` is the packed
player-Y candidate range; the older Canon "unread" claim was removed.

## R19 causal confirmation and current rejection

R19 changes only the native collision-record contract while retaining the bounded
87-quad sparse island. Protected build result:

```text
pristine identity           PASS 327/327
Blender semantic export     PASS, 6 payloads / 87 walkable quads
matched DAT/RAW             PASS
protected disc/module gate  PASS
embedded EXE/BIN/DAT/RAW    PASS
focused tests               PASS 30/30
```

The runtime scenario was reduced to the solved boundary/leaf/commit chain above plus
named GTE, camera, actor, enemy and pickup consumers and their established RAM rows.
Internal append-loop PCs, alternate resolvers and brittle numeric watch-ID retrieval
were removed.

Fresh isolated cold boot receipt:
`/tmp/abl-g3-mock-switchback-r19-semantic-20260810-v1/g3_mock_clover_switchback.json`,
SHA-256 `b161f53395d94e0554fdc9ce6e7892317f940da15f90eb17d1e241f3e2e8ba73`.
The formerly failing 176-frame first climb now passes grounded `0x0101` with authored
floor `-14116`; 18 accepted native collision responses were observed. This is the
causal positive control for the edge-layout repair.

R19 is still rejected as a level candidate. The later fixed `Up` segment continues
straight while the authored route turns, so Flik collects two grains and then leaves
support. Direct review of the hash-pinned DuckStation frames also finds the finite
island too narrow at spawn/foreground: large blue void wedges dominate the view and
the first hill remains visually weak. R20 must widen the finite landing/corridor,
strengthen medium-scale relief, and use a route-aware integration control before any
James review. Gate B remains unclaimed.

## R20–R28 visual controls (all rejected)

These revisions were reviewed locally before any new James handoff. They are retained
as controls because each falsified a distinct presentation inference:

```text
R20/R21  coherent texture, but broad floor still read as a tiled plane/blue void
R22      much larger hills; 1024–1152 file-unit quads vanished near the camera
R23      640-unit P58 pitch, 1,680 visual quads; fill suppression still exposed blue
R24      restored the solved P58 GP0(60) near-field fill; blue became flat tan
R25      512-unit pitch improved spawn/final coverage, not all walked viewpoints
R26      repartitioned the active route around donor-anchor bands; first climb improved
R27      node-transform recenter A/B did not repair presentation; code was removed
R28      P54 backdrop blank exposed blue and removed the native visual fallback
```

The durable Phase-4 conclusions are narrower. P58 proves projected floor quads wider
than 1023 pixels are rejected in the gameplay camera and that the retail near-field
fill must remain enabled. P61 requires the visual/collision anchor at `-15904` runtime.
The R27 negative control means donor-node anchor recentering must not be claimed as a
culling fix. P54 backdrop blanking is valid as a diagnostic lever but is unsuitable
for this layout's presentation.

## R29 walked-camera candidate

R29 keeps the original `FUNC_80010000` GTE payload renderer, original chunk-32
collision consumers, the P58 near-field fill, and the solved Phase-4 Flik chain. It
does not select the Track-A renderer or collision engine. The current authored field
is a finite `41 x 43` exact-grid lattice over:

```text
file X bounds              -11264 .. 10624
file Z bounds               -3584 .. 19200
native visual payloads      25
walkable visual quads        1680
native collision planes       840
collision stride                2 visual cells
max visual/collision gap       576 runtime (<0.2 Flik)
payload injection          16 in-place, 9 appended
DAT append growth             25520 bytes
```

The visual density remains GTE-heavy while the 2x2 collision decimation avoids making
the experiment CPU-bound. The collision compiler validates every skipped dense vertex
against the two emitted native triangles and fails above the scene's explicit 640-unit
tolerance. The full finite rectangle is walkable; only its outer perimeter has
bottomless semantics.

Protected build command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/g3_native_semantic_replacement_build.py \
  templates/g3_native_mock_switchback_r29_semantic.blend \
  --out build/ABL_G3_MOCK_SWITCHBACK_R29_SEMANTIC_20260811 \
  --work-prefix build/g3_mock_switchback_r29_semantic
```

The build passed pristine identity `327/327`, Blender semantic export, module-matrix
admission, protected-output policy, pristine staging restoration, and embedded
EXE/BIN/DAT/RAW verification. Key SHA-256 bindings:

```text
scene generator      0b091562b3f024b2991e96d0f0cd0e57231237af25a35574a9f8d23f2d469e02
Blender scene         159a52a66a380a1667f5d727b006b6f67b8dff5d5151aeef8d8873bc0d279b37
runtime scenario      b2c641b7d196a4305be93b846a87e6b15ea302f5fa1c17b5dfbecf1a6441f4be
replacement DAT       2d4cdcb50a99bfc38d665850a5235a9e8d654c454713f484ecbfd17649b4fd76
replacement RAW       5c2b602708049c20ad4bc4e12bb40ac7fd6e99aeaff78a323afd94ac5d12028c
disc BIN              5d5082a7c26b43948ee66e6f832100541ede901f9bb38a85602a9816dd4ae16b
disc CUE              0c7a7be737551873ca0ea35b3dad55536b8e23fd7a8c4c4a6b454b5c4eb52723
build manifest         446f5c121e467f9c42fd89e6b6631332727a8e6025d8751e8240e9c1498f37a7
compiler report        e10f4496f1cb60a172276585bf60313be059e2e14cfd04c0d2539b4f89ad17b5
wrapper report         c3ac0e18da63271413e993595656c74ec4f92898c78b3614a4e515a6864fe09f
```

### R29 isolated cold boot and direct image review

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_ps1_scenario.py \
  tools/scenarios/duckstation/g3_mock_clover_switchback.yaml \
  --output-dir /tmp/abl-g3-mock-switchback-r29-semantic-20260811-v2
```

Result: `PASSED`, seven phases and `44/44` assertions. It cold-boots the exact built
disc with the timing-matched movie and no state load, authenticates the debugger and
media, arms the solved player/collision/GTE/camera/actor/object rows, and uses PID-owned
isolated cleanup. Flik remains grounded on the authored collision, follows authored
elevation, collects a native grain, observes the authored actor roster, and exercises
marker plus goal/transition/fade. Track-A hook words remain pristine.

Presentation evidence is deliberately limited to two genuinely walked camera states.
The spawn stall and RAM-teleported marker/goal controls are not captured because P58
prohibits visual claims from those render states.

```text
runtime receipt       80deed0828e46fd1f07aa3a880aff705c62e5cb14a52c0f52be75af4a8e466d9
first-climb PNG       b61e1107cba7f0d9f7ef4dd0ecf005a45c42abdbba38ff132c45ee217b725703
second-leg PNG        1f56c3ba13d7341793b2c9de866273c77df3cbc60010c3445fc074c7e626607e
```

Direct inspection on 2026-08-11: both walked frames have textured terrain across the
full viewport rather than blue/tan replacement floor. The bright route is separated
from the darker shoulder, the pickup line follows the turn, and the second-leg frame
shows the authored surface climbing toward screen-right. This clears the local visual
gate for a James handoff; it is not yet an independent acceptance.

Final pre-handoff regression boundary:

```text
focused authoring/compiler/scenario tests  PASS 44/44
protected build/layout tests               PASS 16/16
pristine identity                          PASS 327/327
hook/cave manifest validator               PASS
git diff --check                           PASS
```

Gate B remains unclaimed. The cold boot genuinely drives the first two legs, while the
marker and goal remain functional teleport controls. A complete driven start-to-goal
movie is still required for final route ownership.

### R29 hard-review regression correction

James's first R29 review independently cleared the pristine build, semantic export,
native GTE/collision runtime, `44/44` cold-boot assertions, and both walked
presentation frames. He correctly rejected the overall handoff because
`test_g3_mock_switchback.py` still compared the shared current scenario with the
obsolete pre-semantic mock's marker and goal coordinates.

The regression was made revision-specific: historical landform tests still load
`g3_native_mock_switchback_scene.py`, while the executable scenario-coordinate test
now loads the current `g3_native_mock_switchback_semantic_scene.py`. The exact
seven-file falsifier now reports `36 passed`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_g3_mock_switchback.py \
  tests/test_g3_mock_switchback_semantic.py \
  tests/test_g3_semantic_walkable_validation.py \
  tests/test_native_terrain_visual_material.py \
  tests/test_native_terrain_semantic_compiler.py \
  tests/test_ps1_scenario.py \
  tests/test_ps1_scenario_identity.py
```

This correction changes only test provenance; the hash-pinned R29 scene, disc,
scenario, cold-boot receipt, and screenshots are unchanged. Candidate resubmitted to
James for the binary verdict. Gate B remains unclaimed.

### James verdict

`ACCEPTED` on 2026-08-11 for the bounded R29 claim. Independent review reproduced
the corrected `36/36` regression boundary and accepted the already verified pristine
build, exact semantic regeneration, original-engine GTE/collision behavior, `44/44`
cold-boot assertions, and the two genuinely walked presentation captures. The review
found no terrain, build, runtime, or presentation falsifier after the stale test was
made revision-specific.

This is acceptance of the R29 LEVEL01 replacement test and its walked visual/native
integration evidence. It is not Gate-B route-ownership acceptance: a timing-matched,
fully driven start-to-goal movie remains required before making that stronger claim.
