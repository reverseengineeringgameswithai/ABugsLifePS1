---
kind: experiment
id: EXP_2026_07_11_native_and_training_grain_gate
name: Native LEVEL02 grain gate and TRAINING 25-grain corner cage
status: confirmed_fixed
date: 2026-07-11
confidence: confirmed
source_state: experiment
systems:
  - SYS_native_grain_gates
mods:
  - MOD_training_25_grain_corner_cage
artifacts:
  - level02_graingate_locked.sav
  - desired_letter_loc.sav
  - walk_up_sound_jingle.sav
  - ceiling_cage_issue.sav
  - fall_through_floor.sav
  - on_crate.sav
  - movies/crate_ceiling_issue.movie.json
  - tools/scenarios/duckstation/training_grain_gate.yaml
  - /tmp/abl-training-gate-roof-floor-20260711-r1/training_grain_gate.json
---

# EXP_2026-07-11 Native and TRAINING grain gates

## Question

What original LEVEL02 behavior should the TRAINING letter enclosure preserve,
and does the custom cage remain locked below 25 grain, lower at 25, and stop
blocking Flik after opening?

## Preflight and provenance

- Followed `AGENTS.md` and the `duckstation-external-debugger` skill.
- API routing was taken from [[DuckStation_API_Index]] before checking detail
  notes/client/runtime contracts for media identity, state load, access logs,
  scatter reads/writes, execution control, input, and frame capture.
- ABL revision: `e6402e8717f56df37b47405f6423aad0882ed502` with the operator's dirty worktree preserved.
- DuckStation fork: `fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` (dirty external-debugger checkout).
- DuckStation binary SHA-256:
  `bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
- Pristine cue SHA-256:
  `463102187c2ada6ac90c2990e23cdaf2ef9f8eb56a95a57d8ab496248571d644`.
- `level02_graingate_locked.sav` SHA-256:
  `df5747c1b085cef903b7259bfacc12763dd83d22a4c3df01bb51a685c79d026a`.
- `desired_letter_loc.sav` SHA-256:
  `e90b6c0c95a708a75d6920f4ec78c6e5af9abfb133c0d7478779847b913c942e`.
- `ceiling_cage_issue.sav` SHA-256:
  `06a33a64b618bcdb957ca6a5f23bce25801ffd930b9a62a4d77222ce87294590`.
- `fall_through_floor.sav` SHA-256:
  `6d4da41e141014412e9281e562ddb0ef75c17a8c74f70312af01693f4bf5208d`.
- The operator named `level02_graingate_to_be_unlocked.sav`, but that file was
  not present in the checkout during this run. The same locked state plus a
  one-byte controlled grain perturbation supplied the causal threshold pair.
- Native work used owned config `/tmp/abl-training-grain-gate`, loopback port
  `23525`, and token `abl-training-grain-25`; it mounted the pristine image and
  was not shared with the normal DuckStation profile.

## Native LEVEL02 observation

The locked save begins in scene `3` at emulator frame `40262`, Flik
`(153707,32344,150073)`, grain `0`. Holding Up for 120 frames leaves Flik at the
visible crossed-twig barrier. A 120-frame read watch on grain returned 200
events without truncation: 180 threshold reads at `0x800B44BC` and 20 HUD reads
at `0x80052B58`.

The live nine-record table at `0x800B4C1C` has stride `0x14`. The nearest record
is `{state=4295,id=26,threshold=20,x=193754,z=131692}`. This is observation;
the record interpretation is supported by the subsequent causal stores.

## Native causal confirmation

Reloading the same hash-pinned locked state, re-arming instrumentation, writing
grain `20`, and holding Up caused:

1. `0x800B4530` to write state `4295 -> 4200`;
2. `0x800B4624` to step `4200,4060,3920,...,1680` by `-140`;
3. resident helper `0x80029030` to update the gate geometry;
4. Flik to cross the former barrier, ending at `(210984,65432,132404)`.

There were 19 state writes and no trace truncation. The untouched grain-0 arm
kept state `4295` and stayed blocked. Therefore the threshold compare and
stepped state are causal, while the exact denial sound and cadence predicate
remain open. The save's live overlay body differs from the currently extracted
LEVEL02 overlay bytes; `src_re/level02_grain_gate_update.c` records this bounded
runtime reconstruction rather than pretending a static byte match.

## TRAINING target and implementation

The desired save pins Flik at `(-29775,5943,122634)` in scene `0x11`. Resolved
type-`0x3F` code confirms X/Z are stored divided by 32 and the pickup Y compare
uses `(playerY>>5)-0xE6`; final G entry `65` is therefore staged at
`(-931,-45,3832)`.

The MOD copies only the native behavior shape. Its distinct wood corner cage
and `25`+grain plaque are rendered by the relocation-free C blob documented in
[[MOD_training_25_grain_corner_cage]].

## Reported regression and diagnosis

The operator reported that Flik could walk through/around the first cage, the
geometry did not wrap the letter, and the cage drew over Flik. Diagnosis was
completed before patching:

- static C inspection showed collision was limited to a shallow front band and
  the two returns extended only `4300` local units;
- the old renderer linked every packet at `GPU_OUTPUT+0x1B8`, the near/HUD OT
  bucket;
- resolved OT geometry places the scene OT near base at `output+0x1B4` with
  1,228 buckets, and the measured view-Z curve selects Flik's scene bucket;
- type-`0x3F` evidence showed the final letter source can receive the
  `0x80000000` consumed Y sentinel before bit 7 is awarded, so collision alone
  is not collection authority.

A 600-frame straight-Up cold-boot probe did not reproduce the operator's exact
manual route: it moved Flik from X `-8914` toward `-9099` but did not reach the
barrier. That negative result is bounded to that input route and is not treated
as refuting the manual observation. The complete-front and complete-right-face
scenario anchors below directly exercise the old gaps.

## Second regression: floor, trigger, burial, and roof

The operator then reported intermittent floor death during closed contact,
automatic lowering as soon as grain reached 25, underground cage geometry that
remained visible, and above-entry collection with no roof.

Observation on the pre-fix ALLMODS image used the same cold-boot movie, a
controlled front anchor, grain 24, held Up for 360 frames, and coherent player
state capture. Flik ended at `(-11695,9783,114584)` with vertical velocity
`1280`, floor field `3680`, and grounded `0`; the start Y was `5943`. Static C
inspection independently showed that the post-integrator projection wrote live
X/Z, the render reference, and respawn-anchor X/Z. The fall is therefore tied to
MOD/native position incoherence, not a missing edit to the terrain asset.

The activation mismatch was direct static evidence: `GRAIN_COUNT>=25` advanced
drop unconditionally. The burial mismatch was likewise direct: every primitive
used `y+drop` with no ground-plane clip, so packets continued below the visible
floor. The above-entry report was accepted as an additional route; the prior
four-wall renderer had no roof, and the collection guard tested grain rather
than physical OPEN state.

The interim correction reused native `0x80037A38` after a closed wall/roof
ejection, published `Y=floor-256`, zero velocity, and grounded `0x0101`, while
leaving the respawn anchor to the original game. It fixed the reported floor
death but created the airborne snap and face-shift behavior diagnosed below.
Packed word `0x800813EC` stores low-u16 drop, ACTIVE at byte `+2` bit 0, the
later roof-support latch at bit 1, and OPEN at bit 7. Cage packets clip at ground
Y `6500`; thirteen roof slats render and disappear with the rest of the cage.

## Third regression: wall physics, standable roof, and false jingle

The operator supplied `walk_up_sound_jingle.sav`, SHA-256
`cfedb8ad512acb600aa7223c348ff92c4a6be94d5a247b98dc18c83142272e6d`.
`emulator.getStateInfo` reports a valid SCUS-94288 state whose embedded media
path is `build/ABL_ALLMODS.cue`, despite the accompanying description calling
it pristine-backed. The provenance record therefore treats it as ALLMODS. It
was loaded with serial validation in a fresh instance initially mounting the
pristine cue; the state-selected media after load was ALLMODS. Runtime begins
in scene `0x11` at Flik `(-29482,5375,103528)`, grain `0`, cage state `0`.

Following [[DuckStation_API_Index]], `functionTrace` targeted both
`0x8005044C` and `0x80050994`, was re-armed after state load, then captured a
180-frame held-Up reproduction. At frame `18265`, caller `0x800545F0` entered
`0x8005044C` with `a0=0xFFFFFFFE` (`-2`) and returned `v0=1`; no corresponding
`0x80050994` event occurred. Live disassembly bounded the control flow:

- `0x800545CC`: `addiu s1,zero,-2`;
- `0x800545D0`: `addiu s2,s2,16`;
- `0x800545E8`: `beq s1,zero,0x80054628`;
- `0x800545F0`: `jal 0x8005044C`.

This causally separates the false sound from ordinary movement calls seen at
`0x80056DF0`/`0x80056E94`: the closed collection cave jumped into the retail
`s1=-2` assignment, and the shared post-loop tail deliberately dispatches every
nonzero result. The fix jumps to `0x800545D0` with `s1=0` in the delay slot;
the later Training C tick restores entry Y, so denial remains retryable and
silent. The bounded C reconstruction comment is recorded in
`src_re/pickup_handlers_80054288_80054554.c`.

Static inspection established the physics cause independently. The interim C
response sent every face to the front, called the ground query, rewrote Y, and
zeroed VX/VY/VZ even for an airborne hit. The replacement is a swept local box:
previous X/Z are reconstructed from velocity and the crossed face wins (minimum
penetration handles an already-inside warp). The later regression below changes
the response from tangential sliding to a full horizontal stop. A fall lands
only when it crosses the dynamic roof top;
side walls are inactive at/above that top so Flik can jump onto it normally.
Actual collision now supplies the ACTIVE touch signal.

## Fourth regression: persistent roof and floor-edge safety

`ceiling_cage_issue.sav` begins in scene `0x11` at emulator frame `9663`, Flik
`(-11686,3538,114302)`, floor `3664`, grounded `0x0101`. A frame-stepped
Jump+Up trace on the pre-fix build landed on the roof at step 37 with
`Y=-9256`, `VY=0`, and floor `-9000`. It remained there through step 42 while
the native air state was `5`; at step 43 the old MOD response shifted it away
from the box. The native update had restored terrain Y during its landing-state
transition, so the stateless roof test no longer recognized support and the
already-inside wall fallback performed the displacement.

`fall_through_floor.sav` begins at frame `7095`, Flik
`(-30624,5616,97922)`, floor `5744`, grounded `0x0101`. Holding Up against the
pre-fix wall reached `(-30693,5396,109834)` at step 32. The response retained
tangential velocity, so subsequent frames slid along the wall while the native
floor value collapsed through `5600`, `4768`, `4052`, and lower values. Y then
accelerated downward to `114235` by step 118, followed by respawn. This is not a
terrain edit failure: the MOD had moved Flik beyond the valid native floor.

`emulator.getStateInfo` accepted both states as version `84`, serial
`SCUS-94288`, with embedded media path `build/ABL_ALLMODS.cue`.

The causal runtime check compiled the corrected 7,888-byte blob and injected it
only into the two hash-pinned save states' existing Training helper allocation;
cache was invalidated after writes and instrumentation was re-armed after every
load. In the exact ceiling state, Jump+Up landed at step 37 and remained at
`Y=-9256`, floor `-9000`, grounded `0x0101` through step 80. Packed state bit 1
(`ROOFED`) remained set. In the exact floor state, held Up stopped at about
`(-30710,5414,109984)` with floor `5540`, VX/VZ `0`, and no fall through step
90.

The correction latches roof support only after an actual downward crossing and
releases it on upward velocity or footprint exit. A swept wall crossing restores
the immediately previous X/Z and zeroes both horizontal velocities while
leaving Y/VY, native air state, and native terrain ownership untouched.

## Declarative behavioral proof

Command:

`python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/training_grain_gate.yaml --disc build/ABL_ALLMODS.cue`

The scenario starts `ALLMODS_Training_Still.movie.json` from boot, verifies
serial `SCUS-94288` and scene `0x11`, then uses controlled anchors:

| Phase | Result |
|---|---|
| grain 0 visual | packed state `0`; roofed cage/plaque visible; Flik renders on top |
| grain 24 front collision | state `0`; front face resolves to `(-11702,114264)` |
| grain 24 right collision | right face resolves to `(-24766,133452)`; bit 7 remains `0` |
| grain 25 away from cage | drop `0`, flag byte `0`; no automatic lowering |
| grain 25 contact, 12 frames | drop `2240`, flag byte `1`; ACTIVE latched |
| completed drop | drop `16000`, flag byte `0x81`; OPEN latched |
| same face coordinate while open | remains `(-13450,115075)`; no closed clamp |
| final G at grain 25 | native collection awards bit 7 (`0x80`) |
| closed walk/floor integrity | Y `5400`, floor `5528`, VX/VZ `0`, lives `5`, state `0` |
| forced closed-G contact | deny branch executes `3` times; pickup-sound call executes `0`; bit 7 remains `0` |
| airborne front-wall hit | Y `-2444`, VY `-444`, VX/VZ `0`; vertical motion is untouched |
| fall above closed roof at grain 24 | X/Z stay at letter; Y `-9256`, VY `0`, ROOFED bit 1 remains set for 60 frames; OPEN bit 7 remains `0` |

All assertions passed and PID-scoped cleanup succeeded. The isolated run used
config `/tmp/abl-ps1-scenario-ygriyga9`, port `48691`, and the scenario runner's
dedicated token. Report SHA-256:
`3bfea4a5a3cede4464b6c19cede4f06bf559c4f6f079b2473f4c922845cb15e5`.

Capture hashes:

- closed/front: `f52ce52ddbd6905053ba66ca06ef825e036de64515516ffe3cb008a6c6bb18a6`;
- closed/full-wrap: `ef00d865c4c80a60aae9f26ee84f53344b6a5bc39a3baa8bf448138d2dd1518b`;
- lowering/ground clip: `66b77ae0fd59228cd72cb57f4ee77599043466323e2fe65e3a7156fe0cea7568`;
- fully lowered/no cage: `9f051e6cee4db1712f184f1c1cef9a83cc9b69e6c4cbaa643c594c815a7d46f5`;
- closed-walk floor integrity: `6fefc41fa5e6964d4992273aad2577e5ad607f6dc5e71b832520039e2d767572`;
- persistent standable closed roof: `f8672d53a1cdfa573a2b1357b074a63702422e6bace941354f64848dce01acf9`.

Visual inspection of the closed captures confirms Flik's native packet draws
over the cage/plaque rather than being overpainted.

An independent cold-boot scene-identity run also passed; its report SHA-256 is
`9af8777a04f2f44c848a0a9f99a0d96fd583988a8f7e665b4d5ea6a7f2ce5ef5`.

## Build and regression validation

- Consolidated command:
  `python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force`.
- All 13 staged files passed embedded-disc hash verification.
- ALLMODS BIN SHA-256:
  `1d7ecc99ab91a721e065b6fa9eb7896327718765d4d0698e9cc9143f9b9dde5d`.
- CUE SHA-256:
  `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`.
- Gate C blob: 7,888 bytes, SHA-256
  `2a9e2bba9122cb31a00900aa1c7bdf90b2d4dc1b31ab6f9412aae43ce7ee7919`.
- Focused test: `15 passed`.
- Safe suite: `143 passed, 7 deselected`.
- `validate_mod_layout.py --modules blackberry,golddrop,grain_hud` accepted
  the selected resident module declarations.
- The legacy `mod/smoke_test.py` launcher was attempted but could not create its
  Qt window because it hardcodes XCB and the current shell's `DISPLAY=:0`/`:1`
  were unavailable. It exited before emulation; this is not behavioral evidence.
  The two PID-scoped cold-boot scenario runs above launched successfully and are
  the boot/runtime evidence for this change.

## Fifth regression: the roof was not native ground

Operator report after the fourth-correction handoff: the roof still was "not a
walkable floor", acted very weird, and sometimes killed Flik. Reproduced live
from `ceiling_cage_issue.sav` (state version `84`, media `build/ABL_ALLMODS.cue`)
with the freshly compiled C blob injected into the save's helper allocation
(anim-table tile `0x35` entry `0x8011F318`, code at `0x8011F31C`, gate entry
`0x8011F384`; chunked `writeMemory` + `invalidateCodeCache`; the type-`0x3f`
table at `0x80121438` bounds the allocation at 8,476 bytes). Isolated instance:
config `/tmp/duckstation-debugger-cage-20260711`, port `23461`, token
`cage-roof-1`, fork `fe0cca16` (dirty), binary SHA-256
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`, rebuilt
ALLMODS disc mounted.

Two distinct causes, both observed per-frame:

1. **Stuck transient states.** Holding Jump+Up through the arc left native
   `air_state` in its transient (`1`, advancing to `5`) because the grounded
   latch alone never runs the integrator's landing path. `anim_index` stayed `4`
   (jump-fall pose) and horizontal velocity never received ground friction
   (VX drifted `-1104 → -1881` while "standing"). Ground walking is
   velocity-driven (clean-terrain baseline: dPos == V, ramp 137/213/288/364 per
   30fps tick), so the stale momentum slid Flik across the roof in falling pose.
   Poke experiment confirmed the missing contract: writing `anim=5`, `air=0`,
   `VX=VZ=0` once at touchdown makes idle settle to anim `22`, walking ramp
   exactly like terrain, friction decay on release, and native jump/re-land.
2. **Native ground-glue on the first unpinned frame.** The pin runs after the
   integrator, so while roofed the integrator glues grounded Flik to the
   recomputed terrain floor every frame and the tick re-pins him. On footprint
   exit the pin stops one frame too late: Flik teleported `-9256 → 5155`
   (14,411 units) in a single step (walk-off Up run, f090→f092), which lands in
   whatever native floor is below the exit point — a death pit near the recess
   edge kills him. The glue can also emit a small negative VY (`-2` observed on
   the Right edge), so velocity sign cannot identify a jump release; only the
   Y-delta can.

Correction (all in `mod/caves/training_grain_gate.c`): touchdown publishes the
full native landing (`anim 5`, `air 0`, VX/VZ zeroed) in the crossing branch;
roof support uses the exact slat rectangle instead of the wall pad, so Flik
cannot stand on air past the visible edge; a footprint exit whose Y sits more
than `2048` below the roof plane restores `Y = roofY-256`, clears grounded, and
publishes `air 2`/`anim 4` so gravity produces an ordinary fall; the
OPEN-while-roofed release performs the same airborne handoff. Verified per-edge
(Up/Down/Left/Right walk-offs all settle on terrain with anim `22`/`0`, lives
`5` unchanged; Right-edge glue leak retested after the Y-delta fix) and
jump-in-place re-lands at `-9256` twice with anim `5`.

One non-defect noted while testing: with the cage OPEN, the native construct
pass (writer `0x80053d10`, reported PC `0x80053d14`) awards the final-G bit
through the collection cave at distances up to ~13k runtime units — the native
letter-award radius, present in the handoff build as well. Standing on the roof
while it opens therefore awards G during the descent. Below 25 or while closed
the deny path still blocks and silences it (re-verified: 2 deny hits, 0
pickup-sound calls at the letter with the new blob).

Aesthetic pass in the same blob (render-only; collision constants untouched):
Gouraud-shaded members (GP0 `0x38`) with lit-top/shadowed-base gradients and
per-face ambient (front 256/256, left 224, right 200, back 164); seven bars per
side with thicker corner posts; framed plaque with gradient backing,
drop-shadowed seven-segment `25`, and a diamond grain kernel with highlight;
thirteen roof slats with front-to-back falloff over two edge beams. Worst-case
primitive usage near the closed cage measured `55,852` of `85,948` bytes per
GPU output buffer (double buffers `0x801CC390`/`0x801E134C`).

Evidence captures (transient, `/tmp/abl-training-cage-roof-20260711-r2/`):

- before (flat renderer, closed): `e40556f1e35620be41c5f31a9d4919b5650af8e4688e769b4b847bd354d4e9bd`;
- after closed: `d42396da1ea169c64712b7fa3246269445c8101209540e0dc8d0a6d734e4bf73`;
- after plaque close-up: `43bdf65e845a781f3057c5f3dd93689a83cc8c692970e1ec982a11ca40774853`;
- after roof stand: `96d7c65e126dce0d26123bb12562b6ae8cf5dc4b11ab97da1872fac590b80bee`;
- after open: `ffc9395fe96d60bfe490e9465ecf3c8d9a3bf80bcad954ca3670e01cfecd1aee`.

Cold-boot proof: the scenario gained two phases (`roof_is_native_ground`,
`roof_walk_off_is_ordinary_fall`) asserting air state `0`, idle anim `22`,
killed touchdown momentum, latch release on walk-off, terrain landing bands,
grounded recovery, and no life loss. Full run on the rebuilt disc:
`59/59` assertions passed; report SHA-256
`efee74bf0493b96f6b53c02f6db689ae70f1b38d5b98af4553d2763c6471ad96`
(`/tmp/abl-ps1-report-training_grain_gate/training_grain_gate.json`).
`mod/smoke_test.py --disc build/ABL_ALLMODS.cue` passed BOOT/ALIVE/RENDER/WALK
(`build/ABL_ALLMODS_smoke.json`, SHA-256
`0b4c8fbbaaf2a49ea75d1a0ad5df63107200e89c1689a89a6c83636d22b3d597`).
Rebuilt gate blob: 8,352 bytes, SHA-256
`37ab38c05b3b566b32e59f09696e6e7029f61e89ee6b2a7b7706d14e185c2229`; ALLMODS BIN
SHA-256 `3e6b1a11abd4d180ca9903badfe9ab5a306d89efefcccbc2e452767673b298f9`
(CUE unchanged). Focused tests `15 passed`; safe suite `143 passed,
7 deselected`; mod layout and vault ratchet clean.
`walk_up_sound_jingle.sav` could not take the larger blob in place (its older
allocation ends at `0x80120EC8`); its silent-denial behavior was re-verified
from `ceiling_cage_issue.sav` at the same letter coordinates instead, and by
the cold-boot scenario.

## Sixth regression: butt-slam on the roof was not pebbled ground

Operator evidence: `movies/crate_ceiling_issue.movie.json` (from-boot, 4,897
input frames, SHA-256
`b03218afaabb7e6d98fef6d05955efaaa11e38c2197393ebf0122d020857bc33`), replayed
on an isolated instance (config `/tmp/duckstation-debugger-slam-20260711`,
port `23462`, token `cage-slam-1`, fifth-pass disc). The replay reached the
cage and exposed three non-native behaviors, all traced to the fifth pass
writing MORE state than the native integrator's contact path writes:

1. **Fake bounce loop.** Touchdown forced `air_state = 0`; with Cross still
   held the state machine saw grounded + X + air 0 and issued a new takeoff
   every landing. Native ground behavior (measured on pebbled ground) never
   re-jumps while X is held: it parks in land sub-state `air 5`, grounded,
   idle anim, until X releases.
2. **Latch flap while sprinting.** The ROOFED keep-condition released on any
   negative VY, but native grounded slope math emits small negative VY blips
   with `air 0` (visible on plain terrain runs in the same movie). Sprinting
   across the roof released/re-latched every few frames (movie idx 4619-4645:
   air 0/2, anim 5/4/0 churn, floor flipping between `-9000` and terrain).
3. **Permanently stuck squash anim.** The walk-off restore forced
   `air 2`/`anim 4`, destroying the native heavy-fall recovery bookkeeping.
   After a slam attempt from roof height (`air 4`), the eventual terrain
   landing entered squash anim `6` whose exit never ran: from movie idx 4673
   to the end (220+ frames) Flik walked plain terrain in the squash pose.

Native landing contracts measured on pebbled ground (save-anchored, current
blob injected):

- normal/low-slam landing: contact writes Y-glue, `VY 0`, grounded `0x0101`,
  anim `5`; state machine then takes air to `0` (X released);
- heavy fall (`air 4`, X pressed >8193 above floor → anim 7 flail): landing
  anim is `6`, recovery runs `air 4 → 1 → 0`, squash exits to idle `22` after
  ~24 frames;
- X held through any landing: state machine parks in `air 5`, grounded, idle;
  no re-jump until release.
- The integrator contact path NEVER writes `air_state`.

Correction (sixth pass, `mod/caves/training_grain_gate.c`): touchdown now
writes exactly the integrator contact set — Y, `VY 0`, floor, grounded, and
landing anim keyed by incoming air state (`6` for `air 4`, else `5`) — plus
the roof-only VX/VZ zero (the roof never gets native ground friction).
`air_state` is never written anywhere. The latch releases only on a real jump
takeoff (`air 1` with rising VY) or footprint exit; the glue-undo restores
only Y/VY/grounded and leaves air/anim native. The OPEN-while-roofed handoff
clears grounded only.

Verified from `ceiling_cage_issue.sav` (blob injected): held-X arc lands and
parks natively (`air 1 → 5`, anim 5 → walk, no bounce); slam and heavy-fall
onto the roof reproduce the exact pebbled-ground sequence (anim `6`, `air 4 →
1 → 0`, idle after ~22 frames, latch held); a 46-frame sprint across the roof
shows exactly one latch transition (the legitimate edge exit); the movie's
stuck-anim scenario (heavy fall → roof → walk off → terrain) ends in idle
`22` with no life lost; all four edge walk-offs, jump-in-place, ride-down
through OPEN, the fall-through wall regression, and silent denial all pass.

Replaying the recorded movie against the FIXED build diverges after the first
physics difference (recorded inputs are open-loop against the old bounce
behavior); the movie is diagnosis evidence, not a regression asset. The
regression coverage moved into the cold-boot scenario instead:
`heavy_fall_slam_onto_roof_recovers_natively` (air-4 slam onto the roof →
latch, native recovery to `air 0`/idle `22`, no life lost) and
`held_jump_on_roof_parks_natively` (held X re-lands and parks in `air 5`, no
bounce loop). Full run on the rebuilt disc: `69/69`; report SHA-256
`2fa66fd7e01f6180dc8b37320cda18c5097e7de1a19353d1df6cd8c476707309`.
Smoke gate PASS (`build/ABL_ALLMODS_smoke.json`, SHA-256
`83e8998f6662cc4576e5f11fffdb9af50b7c1e60fec253eff1d5e2c378fa6794`).
Sixth-pass gate blob: 8,368 bytes, SHA-256
`58332f061cc9883f27dfeb6b587e0481eabaa249ae20809b33d627fa168f4e85`; ALLMODS
BIN SHA-256
`aa1fedc4cdc6e1a648b692dddaa0ee2980d710150b512bd0db6b0af2e1cd4cfc`.
Focused `15 passed`; safe suite `146 passed, 7 deselected`; layout and vault
ratchet clean.

## Seventh regression: walking on the roof lurched and skated off the deck

Operator evidence: `on_crate.sav` (SHA-256
`c10da6830216f3f391871aaad64484531162d15189a469bcdde4d8d15060f976`,
version `84`, media `build/ABL_ALLMODS.cue`, Flik idle on the closed roof).
Isolated instance: config `/tmp/duckstation-debugger-crate-20260711`, port
`23463`, token `cage-crate-1`, sixth-pass disc.

Per-frame walking traces showed the defect immediately: holding one direction
on the deck, **alternating game ticks teleported Flik ~1500 horizontal units**
(dPos == V on one tick, then a ~V+1300..1400 lurch on the next), skating him
off the deck within ~20 ticks. A ground control with the identical input
protocol showed dPos == V on every tick. (The same protocol also proved the
rest of the "feel" is native: the acceleration ramp, the slow ~8 %/tick stop
decay, and the wide reversal are identical on pebbled ground.)

Attribution (write-watch differential on `0x800A6500` + breakpoint):

- ground walking: X written only by the integrator's resolved commit
  (`0x80036cec` block, from the collision-resolved stack position);
- roof walking: alternating resolved commit and the previously undocumented
  **unresolved-move fallback at `0x80036d00..0x80036d44`**, which does
  `player.XYZ += [s5]` with `s5 = 0x800A652C` (the velocity vector) and, key
  to the bug, leaves the movement code's RAW pre-integrator position proposal
  standing instead of discarding it the way the resolved commit does. Fifteen
  thousand units above the sector floor the collision loop cannot settle, so
  this path runs and the raw proposal (~1500/tick) survives.

Also confirmed while instrumenting: **`0x800A6510` is the previous-tick
position mirror** — it lags `0x800A6500` by exactly one 30 fps game tick.
Both findings are folded into `src_re/movement_integrator_8003633c.c`.

Correction (seventh pass, `mod/caves/training_grain_gate.c`): while ROOFED
(and not in a takeoff tick), the tick re-commits the velocity-integrated
position `prev(0x800A6510/18) + V` before any footprint math — exactly what
the resolver's commit produces on real ground, and a no-op on unjolted ticks.
The stand offset also corrected from 256 to the native grounded body offset
`128` (every measured terrain sample lands at floor−126..130; 256 left Flik
visibly hovering above the slats). Body Y on the roof is now `roofY-128 =
-9128`.

Post-fix verification from `on_crate.sav`: 90-frame directional walks show
zero jolts (dPos == V every tick) with natural edge exit; held-X arc parks
natively; slam onto the roof recovers through squash to idle; walk-off after
slam lands on terrain with no life lost; all four edges exit safely; ride-down
at grain 25 opens and awards G. The blob (9,088 B) outgrew the save's helper
allocation, so save-injection used a transient relocation: payload written to
the runtime-proven idle window at `0x801F4000` (GAP-T3-7) with a fabricated
type/tile header and `anim_table[0x35]` repointed — test-only; the disc build
carries the chunk normally.

Cold-boot proof on the rebuilt disc: new scenario phase
`roof_walk_stays_on_deck` (24-frame directional walk keeps the latch, plane Y,
and native grounded), full run `72/72`; report SHA-256
`f6a7031912a7faef59c5addfe742fd859624fa9ebcc22f8b60e8699adcf58a41`.
Smoke gate PASS. Seventh-pass gate blob: 9,088 bytes, SHA-256
`75aab92e594b8d663834032d9c42f252ec38d059f5d160985c636109536e5c91`; ALLMODS
BIN SHA-256
`aabff70ce125b19cef489e9ac3bc487148560191af64ebd063a2d6c39e4e70a7`.
Focused `15 passed`; safe suite `148 passed, 7 deselected`; layout and vault
ratchet clean.

## Eighth regression: mid-tick timing, the alcove wall, and a false-free cave

Operator evidence: `on_crate_1.sav` (SHA-256
`b7695af18a687e68e5ec25d7a7ee616529736277a2547140ecd24e51eb8c71b2`), three
reports: the walk animation never engaged on the deck, R2 slow-walk shifted the
camera, and a corner walk could clip through the cage and kill Flik -- with the
operator's own diagnosis that the cage protrudes into the stone wall.

**Timing (reports 1 and 2).** The seventh-pass pin ran only in the RAW blob's
HUD-pump tick, which executes AFTER the consumers. Single-stepping the player
update from a roof frame showed `actor_skinned_update` (0x800563D4) taking its
`grounded == 0` early exit at 0x80056400 and jumping straight to 0x80056808 --
so the locomotion selector at 0x8005649C (which needs a held direction and
`0x800A65A3 == 0`) never ran, and the anim stayed idle 22. A write breakpoint on
`0x800A6582` during a roof walk caught the native clear at `0x80036B90` inside
the integrator, one frame ahead of the MOD publish at the pump. The same
ordering explains the camera: the follower reads position/floor mid-tick, so it
saw the unresolved raw proposal.

Correction: the pin now also runs at the integrator exit. `patch_exe` hooks the
pristine `jal 0x80037A38` at `0x800495D0` (ground query, `a0 = player`) into a
13-word guard cave; in Training with a published pointer it tail-jumps into a
pin appended to the RAW payload, which replays the query, overrides its result
with the roof plane (the caller's `sw v0,0x48(s1)` then publishes it as the
floor), publishes grounded, pins Y/VY, and re-commits `prev + V`. Verified on
the rebuilt disc: walk anim `0` and slow-walk anim `29` both engage on the deck,
and camera motion is now *calmer* than the ground control (max per-frame delta
1,026 vs 2,135; mean 372 vs 523).

**Relocation (report 3).** The operator's diagnosis was correct. Native wall
probes around the old anchor found the recess wall cutting the footprint, with
the void pit reachable past local `across > +10500, inward > -15700` (one probe
lost two lives). The cage and letter moved 25,000 local units straight out the
front to `(-7104, 3092, 112128)`; entry `65` restaged to `(-222,-134,3504)`,
`CAGE_TOP_Y` -10500, `CAGE_BOTTOM_Y` 5000, roof body Y `-10628`. All four padded
corners were floor-probed solid (settle floors 2084..4440) and the field runs
85k+ further out. Post-move stress: eight input-driven approaches into each face
and corner give zero penetration frames and zero deaths; a forced warp inside
(the clip-through's fatal case) ejects safely with lives intact.

**GOTCHA -- a "candidate_free" cave that hangs boot.** The guard was first placed
at `0x80081858` (listed by `mod/build.py --suggest-caves` as idle across 175
pristine states, and static-zero). The disc hung at the PlayStation logo. That
run is inside a live **boot-polled table**: readers at `0x8006EAC8`/`0x8006EBAC`
touched `0x80081A28` forty times in a 400-frame boot window, and
`src_re/training_tutorial_progression.c` already lists `0x80081858` among the
forbidden runtime ranges. `--suggest-caves` samples GAMEPLAY states, so a
boot-phase consumer is invisible to it. The guard moved to `0x8007FB28` (13
words, exact fit to `0x8007FB5C`; zero boot-phase accesses under a readwrite
watch). Rule: **watch a candidate cave from cold boot, not only in gameplay.**

Scenario: gained `player_control_is_live` (the movie tail hands control back
before any perturbation) and `roof_walk_stays_on_deck`; the airborne phase now
clears the denial phase's exec watches first (a traced advance observed no
integration), and the slam-recovery idle assert accepts the native idle-fidget
band 22..27 rather than exactly 22. Full cold-boot run on the rebuilt disc:
`74/74`; report SHA-256
`014962b31bae6f75b33c66125ab7d5bc4d338a2bdc7848432e5d5d1cf5e70e28`.
Smoke gate PASS. Eighth-pass gate blob 9,072 bytes, SHA-256
`3fccd825b506308a4429d64ef984c5a4dfffbbbe595a09a40a5e5532841c4b02`; ALLMODS BIN
SHA-256 `281a560d715fd4792e75b518b7e645dd6727b3fba33da5d562167e6b8535227c`.
Focused `15 passed`; safe suite `151 passed, 7 deselected`; layout and vault
ratchet clean. Isolated instance: config
`/tmp/duckstation-debugger-crate2-20260711`, port `23464`, token
`cage-crate2-1`.

## Separation rule

The LEVEL02 table, threshold compare, writer PCs, state sequence, and resident
geometry helper are Canon. Save hashes, perturbations, captures, commands, and
observed divergences stay in this Experiment. TRAINING geometry, threshold 25,
private state `0x800813EC`, collision plane, and RAW-resident C belong in Mods.
The next-session entry point is
[[Session_2026-07-11_-_TRAINING_25-grain_cage_handoff]].
