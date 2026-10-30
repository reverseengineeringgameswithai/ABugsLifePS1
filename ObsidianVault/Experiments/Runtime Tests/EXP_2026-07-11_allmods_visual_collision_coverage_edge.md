---
kind: experiment
id: EXP_2026_07_11_allmods_visual_collision_coverage_edge
name: ALLMODS turn-around edge — collision beyond rendered DAT terrain
status: confirmed_fixed
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mixed_original_and_mod_experiment
related:
  - SYS_render_collision_source_separation
  - MOD_g3_native_anchor_alignment
  - MOD_g3_visual_collision_coverage_boundary
  - SYS_world_render_dispatch
---

# ALLMODS turn-around edge — collision beyond rendered DAT terrain

## Question

Why can Flik turn left/back from LEVEL01 Bigland spawn and keep walking after the
pebbled terrain ends? The Blender lane feeds terrain and collision from one surface,
so does this disprove the one-mesh contract?

## Reproduction identity

The operator worktree was dirty and preserved. Project revision:
`e6402e8717f56df37b47405f6423aad0882ed502`.

`build/ABL_ALLMODS.bin` changed during the diagnostic from `772c...` to a newer
operator build. No conclusion mixes those images. The current image was copied to an
immutable `/tmp` directory and all causal runs used:

- BIN SHA-256 `76ed72f7549c2826bb34bf31d3cc120ddf72604a2c9e3cdd7fa07460bce86c04`;
- CUE SHA-256 `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`;
- serial/title `SCUS-94288` / `Disney-Pixar A Bug's Life`;
- movie `flik_to_level01_stall.mv.movie.json`, SHA-256
  `fa2e81925fbad56af07081fbfe6980f2789a0dd72e6b63b13f9e7b5fc23ed264`;
- DuckStation fork `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`, dirty;
- debugger binary SHA-256
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.

Every run used a freshly recreated absolute config under `/tmp`, a dedicated
loopback port (`23575` for the final control; `23579`/`23580` for the causal build),
and a per-run local token omitted from the repository. The mounted media was queried
before driving input. Owned instances were stopped through their config directories;
the operator's already-running DuckStation process/profile was untouched.

## Observation

Cold boot plus the movie reached exact Bigland spawn
`(197088,-12704,492896)`. Holding Left for 90 frames, releasing, settling 20,
then making a focused 18-frame walked capture produced at emulator frame `4515`:

- Flik `(X,Y,Z) = (229670,-13293,436578)`;
- file-space X/Z `(7177,13643)` by `runtime >> 5`;
- `grounded=0x0101`, `air_state=0`, `vy=-21`;
- pebble terrain ended at a hard rectangular edge while Flik stood/walked on tan.

`tools/floor_source_map.py` against the shipping P66 DAT reports **no floor payload**
at that X/Z. The adjacent registered payloads end around X `6900`/`6991`; the
Blender heightfield and emitted collision continue farther.

## GPU attribution

GPU causality was armed before fresh walked frames. Native CRTC geometry was
`512x224`.

- Beige pixels under/left of Flik resolve to a screen-wide, untextured `GP0(60)`
  sprite, raw header `0x606982a2`, submitted by GPU DMA kick instruction
  `0x80064658` through the normal presentation/DrawOTag chain.
- Pebbled pixels on the right include native `GP0(3C)` terrain quads, texture page
  `0x660`, CLUT `0x3FFC`.

Therefore the beige area is the original background/near-cover fill. It is not a
terrain primitive and cannot be used as evidence of visual floor coverage.

## CPU/collision evidence

A post-divergence non-halting watch on player-Y commit `0x80036CEC` captured four
events at frames `4497,4502,4507,4512`; `v1` was approximately
`-16431,-16452,-16472,-16493`. The integrator's later `+3200` body adjustment agrees
with the observed Flik Y band. The trace was bounded to 512 events and was not
truncated. `grounded` remained `0x0101`.

The focused window recorded no `0x8003573C` oriented-plane response, so this note
does not claim a particular plane/sector winner. The supported conclusion is only
that the native movement path committed collision Y and grounded Flik where no DAT
floor payload existed.

## Inference versus cause

Inference: one Blender mesh was being sampled by both generators, but the two engine
consumers had different coverage domains:

- visual = 30 registered DAT floor payload footprints;
- collision = expanded/replaced chunk-32 plane coverage.

Causal confirmation used the existing P60 hypothesis with one variable. A fresh
offline emission first reproduced the shipping P64 collision RAW byte-for-byte
(`a406a72d...`) using `P60_SMOOTH=2`. Applying a 60000-runtime-unit raised collision
outside the **actual P66 DAT floor union** produced:

- P67 collision RAW SHA-256
  `2aaeac176553829d4f17d6272e563b29fe85db23cf7964c337b76e7145f835b5`;
- same byte length `865558`;
- only compressed RAW chunk 32 differed from P64.

That chunk was layered over the current composed RAW in `/tmp` without changing
later emblem/glyph chunks. The cold-boot test disc BIN SHA-256 was
`fd688770163205cc809ea25ff397110dd8860dc8b310bb394b76b0ee3fc032bb`.

On the identical Left route:

- through 96 frames, movement remained grounded and matched the control band;
- frame `4499`, `(230751,-9318,441256)`: `grounded=0`, falling;
- frame `4559`, Y `99317`: still falling;
- frame `4589`: existing P57b rescue restored exact spawn
  `(197088,-12704,492896)`, grounded `0x0101`.

Thus removing out-of-visual-union collision removes the reported ability to stand on
the backdrop fill. This is causal, not a patched-byte-only claim.

## Regression

- A complete isolated `mod/build.py --mods mod/mods.yaml` integration succeeded at
  `/tmp/abl-p67-consolidated-final/ABL_ALLMODS_P67`: BIN SHA-256
  `2eceb9018774a8fa57d0e2af30d20cc13168127dc79a8ea3124696305ad69d18`,
  CUE SHA-256
  `8582b01c166b640f2c30cd3717624aee80f08a526ba5f3a41cb00656391a6132`.
  The build verified all 13 staged files inside the disc and restored the source tree.
- Consolidated smoke on that final image: BOOT/ALIVE/RENDER/WALK all pass;
  forward walk moved `137177` runtime X/Z with Y `-12869..-12698`.
- `tools/regress_g3_native_authoring.py` covers inside-union preservation, the exact
  `(7177,13643)` outside fixture, positive wall validation, and actual DAT-derived
  payload count.
- Declarative cold-boot scenario
  `tools/scenarios/duckstation/allmods_visual_union_boundary.yaml` **passes** on the
  final consolidated P67 BIN/CUE above. It asserts exact grounded spawn, then observes
  at frame `5097` X `232520`, Y `-7797`, and `grounded=0` outside the rendered union;
  at frame `5188` the rescue is back at exact `(197088,-12704,492896)`, grounded
  `0x0101`.
  The edge screenshot SHA-256 is
  `e2dc13ec819221b1b54a06e97b9893e7605f68d2929112fd8ef37c626826d151`.
  The JSON report is
  `/tmp/abl-p67-consolidated-final/scenario-report/allmods_visual_union_boundary.json`,
  SHA-256
  `027cc2734974f7924803fbe1bd7ae4a184ede575d731b6b358e020bfbc554b85`;
  PID-scoped cleanup succeeded.
- The scenario records a fixture-specific boot requirement already embodied by
  `mod/smoke_test.py`: turbo before reset,
  `movie.startPlayback(load_start_state=false)`, then the 4253 recorded inputs and a
  bounded post-stall Cross/settle. Enabling turbo only after playback starts shifts
  the input attachment point and reproducibly reaches LEVEL00 instead.
- Focused scenario-runner tests pass (`5 passed`); the broad safe suite passes
  (`143 passed`, `7 deselected`). Python compilation, the G3 authoring regression,
  mod-layout validation, vault consistency validation, and the scoped
  whitespace/diff check for P67 files also pass.
- All builds and runtime tests used `/tmp`; the operator's active ALLMODS disc and
  DuckStation profile remained untouched.

Large `cd.overlayFile` and chunked sector-overlay attempts exceeded/reset the current
debugger receive path before gameplay. They supplied no game evidence; the final
causal validation used a real rebuilt `/tmp` BIN/CUE.

## P68 follow-up — raised boundary enabled infinite jump

The P67 containment solved invisible standing but was not a valid platform end. On
the hash-pinned P67 disc, cold boot reached edge
`(230751,-9318,441256)` with `floor_Y=-31144`. The signed delta was `-21826`.
Repeated Cross presses recorded 7 hits at coyote decision `0x80048BAC` and 5 hits at
the jump-state store `0x80048BDC`, both untruncated. Flik first descended to Y `21493`,
then repeated jumps raised him back to Y `-2187`; lives remained 5. Control report:
`/tmp/abl-p68-infinite-jump-control.json`, SHA-256
`1db08f88752e10cbf106fd21baaeb29a27af3588c4c37a3c7f7acdda98c1ef47`.

Solved ASM and `src_re/player_update_80048138.c` explain the sign error. The exact
sequence computes `[player+0x48] - player_Y`, then `slti ...,1024` at `0x80048BAC`.
Raising a missing floor puts it above Flik and makes the signed difference negative,
which is always below 1024. This is the causal reason P67 re-armed coyote jump.

P68 replaces that wall with Y `800000` pit collision. Emission is cell-granular:
all four corners must be inside the final DAT floor union or the entire quad becomes
pit. This corrected an intermediate point-sampled prototype whose straddling quads
formed giant slopes at the edge. The level-local hook forces descent while ungrounded
over the deep floor and, at player Y `100000`, spends one life, resets fade progress
to 0, and coherently restores the spawn. This is a MOD-owned bottomless-pit contract;
native LEVEL01 did not spend a life on this generated path. A separate replay of the
historical Track-A movie on its surviving hash-pinned media also failed to reproduce
the later archived native-death attribution, so P68 does not claim it.

Final P68 artifacts:

- collision RAW SHA-256
  `ebb97ebb54461eca90d14dbcfcd2d9ba5443180d2a9c521bd74d6770f3b0e3e6`,
  865558 bytes; terrain P66 remains
  `5016106be99884b33438c540bdb9b099a77c2cc39fe323fe9ce626a8c964e63e`;
- consolidated BIN `/tmp/abl-p68-final5/ABL_ALLMODS_P68.bin`, SHA-256
  `0b3385a10dcc4dd60907bdf891d81afb2269e8d3088c917e2e72ad2d955a5e91`;
- CUE SHA-256
  `780bb037ee99e95625cd2eb79ce6652fd88505c9f261fc3d143a399b16492bed`;
- level overlay runtime `0x800B4030..0x800B43E4`, below state at `0x800B4400`;
- scenario report
  `/tmp/abl-p68-final5/scenario-report-final/allmods_visual_union_boundary.json`,
  SHA-256 `7dc9b169403de6b6a50336fedf65a04c5e7922e7baa8ae3bd66f73b835e0e37d`.

The final declarative cold boot observes exact grounded spawn, deep edge
`(214910,-4704,...)` with `floor_Y=803200`, 4 coyote-decision hits from six Cross
attempts, **zero** jump-state writes, lives `5 -> 4`, fade `128 -> 0`, and exact
grounded respawn `(197088,-12704,492896)`. Its isolated PID cleanup succeeded.
The scenario now pauses immediately after reset, advances exactly 175 neutral frames,
then attaches the historical movie. That explicit prefix replaces the movie's former
host-timing-dependent running-guest attachment. Two consecutive isolated runs produced
the same gameplay assertions; each then advances the 4253-input movie in bounded chunks
and settles the post-loading Bigland spawn.

## P69 follow-up — spawn pit, green lock, and missed authored landing

The operator's manual P68 test exposed three regressions that the earlier scenario did
not assert. The exact shipped control was `ABL_P68_PIT_TEST.bin`, SHA-256
`0b3385a10dcc4dd60907bdf891d81afb2269e8d3088c917e2e72ad2d955a5e91`.
A new cold-boot scenario against it observed:

- stable spawn `(197088,-12704,492896)` was grounded only because the hook seeded it;
  native `floor_Y` was already the pit value `803200`;
- the MOD death changed lives `5 -> 4` but wrote fade progress `128 -> 0` without a
  native transition owner; Start never set pause flag `0x8008224E`, and the guest later
  executed at low BIOS PCs (`0x00001AD8`/`0x000000A0`), matching the green/control lock;
- control report `/tmp/abl-p69-user-regression-control/allmods_visual_union_boundary.json`,
  SHA-256 `2751cab3c2d769b04c770ae62281f1ad56f8cd5049a88f2cc3b6483cb20b8eb3`.

Cause 1 was P68's all-four-corners classifier. The coarse collision cell containing
spawn straddles the visual payload's X `6900` edge, so the whole otherwise-valid cell
became pit. A literal AABB-edge splitting prototype was rejected because it expanded
LEVEL01 collision RAW to about 3.8 MiB and crashed during load at PC `0xA0`. P69 keeps
one plane per native-lattice cell and classifies the entire cell by its center. This
retains a discontinuous authored-or-pit ledge without either a slope or spawn erosion.

Cause 2 was the unowned fade write. P69 still spends one life and coherently respawns,
but leaves global fade progress clear at `128`; it does not pretend to start a native
transition that has no owner on this generated path.

A 30-frame Right hold then exposed a separate selector seam: `floor_Y` stayed authored
near `-12796`, but native collision missed the swept catch and player Y reached `48397`.
P69 adds a narrow level-local backstop only when player Y has crossed below a reported
authored floor (`floor_Y < 100000`). It clamps Y to that floor, zeros VY, and republishes
grounded. Normal jumps remain above the floor and pit cells fail the threshold.

P69 cold boot verifies: authored spawn floor `-12716`; deep edge `floor_Y=803200` at
Z `440255`; 5 coyote decisions and zero jump-state writes; lives `5 -> 4`; fade remains
`128`; exact grounded respawn; Start sets pause flag 1 and the second Start clears it;
and a post-respawn 30-frame Right hold remains local at
`(207426,-12981,493948)` over authored floor `-12776`. The isolated scenario report is
`/tmp/abl-p69-backstop/scenario/allmods_visual_union_boundary.json`, SHA-256
`f640e770ff19d24ff515cfd55c09f7afc36c94abe7cad59a96586a6c511e9488`.

The separate manual-test build in the repository root was then tested directly,
without replacing `build/ABL_ALLMODS.*`:

- `ABL_P69_PIT_TEST.bin`, SHA-256
  `7d890a347f6ce59a220b86487a396701e9c1fbd7ca8a67e54f28b2a8586db7d4`;
- `ABL_P69_PIT_TEST.cue`, SHA-256
  `89f053fd94c752b67e90c3d89ece587558cd42c5c5d9542a59b1d1ff7c6c4f06`;
- BOOT/ALIVE/RENDER/WALK smoke passed, including a local walk of `137192` runtime
  X/Z units with Y confined to `-12926..-12708`;
- the full declarative cold-boot scenario passed against that exact CUE with the same
  spawn, pit, no-midair-jump, life-loss, fade, pause/resume, and local-walk values
  above. Report `/tmp/abl-p69-root-final/allmods_visual_union_boundary.json`, SHA-256
  `85336aa04802e8b4c7c0db464d7c68d979065f7f8367790a6ba2ad2eceec69d9`.

The older root-level `ABL_P68_PIT_TEST.*` remains only as the hash-pinned regression
control and must not be used for P69 manual verification.

The P69 collision RAW is
`build/ABL_g3native_p69_visual_union_cell_pit_collision.RAW`, SHA-256
`188bd1df71546bd48a5233434963c496ae9eeb141a44d9cd8968024213e65313`.
The composed runtime occupies `0x800B4030..0x800B4428`; state begins at
`0x800B4428`, and the resident gate sources/installer were moved clear.

## P70 follow-up — retail gravity, native mode-2 death, safe authored respawn

P69 fixed the reported input, green-lock, pause, and spawn-floor regressions, but its
death remained synthetic: the hook forced Y/VY, decremented the displayed life, and
warped Flik back. The resolved SCUS-94288 assembly identifies the original path:

- `0x80048D68..0x80048D8C`: while ungrounded, VY increases by `256`, caps at `4096`,
  and is committed by the vertical update;
- `0x800497F4..0x80049870`: Y greater than `[0x800822B4]+8192`, transition state zero,
  and request guard non-positive lead to the temporary life adjustment at `0x80049858`
  and `FUNC_8004A700(..., mode=2)` at `0x80049868`;
- mode 2 stores transition state 2 at `0x8004A9F4` and fade timer 23 at `0x8004AA00`;
- the `0x8005B134` respawn handler restores X/Y/Z from player checkpoint offsets
  `+0x50/+0x54/+0x58` and performs the paired life adjustment at `0x8005B348`.

A media-validated pristine LEVEL01 save-state experiment mutated only Y to one unit
past the native threshold, VY to 4096, `air_state=2`, and `grounded=0`. It observed the
gravity commit and threshold comparison 54 times, one native life adjustment, one
mode-2 call, transition `0 -> 2`, fade timer `0 -> 23`, one native respawn, and final
grounded checkpoint state with displayed lives still 5. Evidence:

- `/tmp/abl-native-pit-re/native_transition_exec.json`, SHA-256
  `0f637c38acdf236c7b731f2253319d8a32c9456d0452d735d110e676f1dd034b`;
- `/tmp/abl-native-pit-re/native_transition_access.json`, SHA-256
  `6898a0a381dab642e46412730882a43fc4ea9a36171411dfe83fdf918374dd12`;
- `/tmp/abl-native-pit-re/native_transition_final_state.json`, SHA-256
  `30025d7e58ac91b32b8a560dc24c407b6d9fdf7702f09af39d11f12bb8d78aef`.

The P69 control proved why this never happened on the generated level: the deep
collision grid inflated scene fall base to `878592`, so the native guard ran but never
reached its transition call. P69 instead changed lives `5 -> 4` and respawned directly.
Control report `/tmp/abl-p70-p69-native-bypass-control/allmods_visual_union_boundary.json`,
SHA-256 `a94f5d43d540652257e1c9812513d5ddd81662ef9372dad47a6eb988564cb264`.

P70 therefore restores the scene base to `91808` (native threshold Y `100000`), seeds
only `air_state=2`/`grounded=0` at the authored-to-pit boundary, and leaves Y, VY, life,
fade, and transition state native-owned. A first native build respawned at edge position
`(237087,-13254,441797)`. Access logging causally identified `FUNC_80054C90` stores at
`0x80054E70/0x80054E78/0x80054E80` continuously replacing the checkpoint triplet with
the live edge position. The final hook pins that native restore source to the authored
Blender spawn `(197088,-12704,492896)` before the fall guard can request mode 2.

The exact separate root artifact, without replacing `build/ABL_ALLMODS.*`, is:

- `ABL_P70_NATIVE_PIT_TEST.bin`, SHA-256
  `a39b4d2a0f3b8499756d458cc5565406ba20ce3b8542e372f525c60b029808a1`;
- `ABL_P70_NATIVE_PIT_TEST.cue`, SHA-256
  `246b96d8160f464b36279831c507da6039fdb9f0f08c66356178188e80456b72`;
- smoke report `ABL_P70_NATIVE_PIT_TEST_smoke.json`, SHA-256
  `543d01bd93a395fe063b10182b9807a99577536206bcfbba3b1c2e0ef2aa0ca8`;
- exact-disc cold-boot scenario
  `/tmp/abl-p70-root-final/allmods_visual_union_boundary.json`, SHA-256
  `4ac1b1785cad3e2d49b79c3c88c924acc32fcbb96b0499b989b82ff2a1abb799`.

The scenario observes scene base `91808`, deep edge floor `803200`, zero off-edge
jump-state writes, 44 native gravity commits and comparisons, and one execution each
of the native life-adjust, mode-2 call, transition-state store, and respawn PCs. It
then observes state 2/fade timer 23, final lives 5, fade timer zero, exact grounded
authored respawn, working Start pause/resume, and local Right movement to
`(198471,-12935,480232)` over authored floor `-12732`. BOOT/ALIVE/RENDER/WALK smoke,
143 safe tests (7 deselected), authoring regression, hook/cave layout validation, and
the consolidated 13-file build all passed.

## P71 follow-up — `p70_failure` Cross/slam feedback loop

The operator supplied the reproducible v3 movie `p70_failure.movie.json` (703 frames,
SHA-256 `d0063d593f85c8733ed04239d6cc1df05c8d6a570cfe8b0100b64cf0f7a03857`)
and its media-validated P70 start state (SHA-256
`7650f0d53e61acdbb159c00f1940afc4026fb7288a0f5988e4c5c290ce3df28b`).
The first Cross hold begins at movie frame 145.

Observation on exact P70 media: before Cross, Flik was normally grounded on authored
floor at `(231480,-13188,450558)`, `air_state=0`. At the first pit frame, access logging
attributed `air_state=2` to the MOD store `0x800B4170`. Each later airborne Cross wrote
native state 4 at `0x80048CBC` and called sound 27 through `0x80048CA0`; the hook then
wrote state 2 again. Across the bounded frame-140-to-260 trace, this produced 11 sound-27
calls, 11 native state-4 writes, and 21 hook state-2 writes. At movie frame 260 Flik was
still at Y `-26259`, VY `0`, timer `8`, state 2 over pit floor `803200`.

The resolved code explains the hover: sound-27's airborne branch sets player timer
`+0x84=10`; while it is greater than one, `0x80048DBC` stores VY zero. Rewriting state
4 to 2 lets every new Cross press replay the branch and restart that timer. Evidence:

- `/tmp/abl-p70-failure-re/cross260_exec_events.json`, SHA-256
  `9d936ad3769866865fd71c323739aac326de53925f12004b25cc2fd9b2ef88b3`;
- `/tmp/abl-p70-failure-re/cross260_airground_writes.json`, SHA-256
  `a7ab674647a665b1bfad9ea03030efc18ac3e5f45d2419fe4e24f29ab95f4029`.

Causal confirmation replayed the same state/movie to frame 140, then changed only the
P70 `sh t3,0x80(t2)` instruction at `0x800B4170` to NOP while retaining the grounded
clear at `0x800B4174`. At movie frame 260, the same inputs had produced only one sound-27
call; native state remained 4, the timer had fallen to 1, and Flik was falling at Y
`12525`, VY `4096`. By movie frame 400, the native fall transition had executed once
at `0x80049868` and transition state was 2. Evidence:

- `/tmp/abl-p70-failure-re/nop_at140_exec.json`, SHA-256
  `986cd340dfe557cf8951433337d4e43f07a7dc458209ad7406673cb00bd8d984`;
- `/tmp/abl-p70-failure-re/nop_at140_vy.json`, SHA-256
  `d6178a1236ceab2ef96202762cf78f6053dc80944c31a57f58fb3ed4717fd1f9`;
- `/tmp/abl-p70-failure-re/nop_at140_to400_exec.json`, SHA-256
  `a21ee6c8385312d79a168098010b88190e2f90f1a1a8b1286082666fd35d3f7d`.

P71 permanently removes the air-state store and clears only stale grounded contact.
The cold-boot boundary scenario now asserts zero jump writes, zero repeated slam-sound
calls, and zero timer hold stores; it observed 38 native gravity commits/comparisons,
one mode-2 transition, exact grounded authored respawn, working pause/resume, and local
post-respawn movement. Exact root-CUE report
`/tmp/abl-p71-root-final/allmods_visual_union_boundary.json`, SHA-256
`7164fb0507dd909af313b0feb6c497b6554979c22c06394e108893c75421ab51`.

The separate root artifact is:

- `ABL_P71_NATIVE_PIT_TEST.bin`, SHA-256
  `d4db10ead77e6a0cdaf9fcfa5af35273225f3751fa76d2b4834b0f141b48ed28`;
- `ABL_P71_NATIVE_PIT_TEST.cue`, SHA-256
  `2f532542a7a5707a23fe3ca74574b912c6808b61405adf7f98d4ce82b2264d7b`;
- smoke report `ABL_P71_NATIVE_PIT_TEST_smoke.json`, SHA-256
  `b49417606f49d9a36b3d3ba16660cd9d822ef6320d03a5def59ec5876fab0b18`.

Because unrelated dirty TRAINING grain-gate C currently fails to compile undeclared
`emit_roof_slat`/`emit_face`, a new full all-assets build was not allowed to overwrite
that operator work. P71 was instead rebuilt from the already validated P70 consolidated
disc by replacing generated LEVEL01/LEVEL.BIN. Raw-disc comparison proves exactly two
sectors changed (LBAs 2942-2943; 1,041 differing bytes) and every other consolidated
sector remained byte-identical. BOOT/ALIVE/RENDER/WALK smoke, the authoring regression,
scenario schema, and cold-boot behavior pass; the safe suite is 140 passed / 3 unrelated
TRAINING failures / 7 deselected.

## Conclusion

The one-Blender-mesh statement remains true for **authored height sampling**. It was
too broad when read as a topology/coverage guarantee. The original renderer cannot
arbitrarily relocate/tile the 30 floor payloads (P54-P57 cull and primitive-budget
evidence). P71 makes the supported contract explicit: walkable chunk-32 collision is
cell-quantized from the DAT union; leaving it is a discontinuous deep pit that cannot
re-arm coyote jump. Original gravity and mode-2 death own the fall, and the native
checkpoint returns Flik to authored terrain. The boundary clears grounded only; native
air-state ownership prevents Cross from re-arming the slam/vertical-hold loop.
