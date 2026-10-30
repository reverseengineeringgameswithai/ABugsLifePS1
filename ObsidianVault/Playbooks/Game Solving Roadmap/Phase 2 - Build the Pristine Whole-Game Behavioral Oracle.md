---
kind: playbook
id: PLAYBOOK_game_solving_phase_2
name: Phase 2 - Build the Pristine Whole-Game Behavioral Oracle
aliases:
  - Phase 2 - Convert ASM Knowledge into Executable Contracts
status: qualified
created: 2026-07-11
updated: 2026-07-12
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_1
next: PLAYBOOK_game_solving_phase_3
depends_on:
  - PLAYBOOK_game_solving_phase_0
  - PLAYBOOK_game_solving_phase_1
---

# Phase 2 - Build the Pristine Whole-Game Behavioral Oracle

**Navigation:** [[Phase 1 - Establish the Whole-Game Mechanics and Campaign Baseline|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 3 - Reconstruct Semantic Architecture and State Ownership|Next phase]]

## Purpose

Turn the Phase 1 inventory into deterministic evidence of how the verified pristine
game behaves. The oracle is the standard against which reconstruction, diagnostic
patches, and eventual MOD work are measured.

ALLMODS and other derivatives are excluded from oracle construction. Every diagnostic
image is created independently from the immutable pristine base.

## Coverage dimensions

### Campaign

- Training, all 15 stages, and each known bonus stage.
- Normal exit, grain-gated, boss, flight, chase, assembly, rescue, and finale objectives.
- Interior, exterior, city, tree, riverbed, rolling-world, and arena presentations.

### Player actions

- Run, slow walk, jump, kick, abdomen bounce, downhill slide, spin lead, berry throw,
  seed carry/drop/handstand/plant/uproot/cycle, vine/web swing, and camera controls.
- Grounded, airborne, damaged, powered, carrying, mounted, paused, dying, and respawning
  states.

### Systems and lifecycle

- Collectibles, plants, powers, enemies, bosses, hazards, objectives, HUD, results,
  audio, overlays, save/load, continue, and movie unlocks.
- Creation, first use, repetition, capacity, retirement, reset, pause, death, scene
  transition, reload, and long-running behavior.

## Work packages

- [x] Audit and hash-pin existing movies/save states; reject any that do not identify
  the intended pristine media and scene. — `analysis/phase2_fixture_audit.json`
  (tools/phase2_oracle.py, 2026-07-12): 123 pristine saves / 63 non-pristine saves
  (ALLMODS-media fixtures marked oracle-INELIGIBLE, e.g. `cannot_crack_seed.sav`,
  `holding_seed_change_seed_colour.sav`) / 60 pristine-serial movies, all sha256-pinned.
  Recorded caveat: a movie header carries the serial but not the image hash, so
  cold-boot oracle movies are only accepted by replaying them against the pristine
  image.
- [x] Create a timing-matched cold-boot fixture for every stage and special objective.
  — `movies/go_to_end/` holds FROM-BOOT v3 movies for Training + all 15 stages
  (operator-recorded 2026-07-08; the first Phase-2 pass wrongly declared this
  blocked). All 16 replayed 1:1 on the pristine image under the repro config
  (`tools/phase2_completion_oracle.py` → `analysis/phase2_completion_oracle.json`):
  every movie boots, navigates menus (~frames 4500–6500), enters its stage scene,
  plays the objective, and exits the stage by movie end. Determinism gotcha
  reconfirmed: from-boot movies replay ONLY under
  `tools/launch_repro_playback.sh` (recording-matched config + seeded memory card)
  — the plain debugger launcher free-runs and silently invalidates playback.
  Special-objective/bonus-completion fixtures remain open.
- [x] Create focused action fixtures that exercise every manual control and combination.
  — Mined instead of re-recorded: `analysis/phase2_action_windows.json`
  (tools/phase2_action_windows.py) extracts per-action frame windows OFFLINE from
  the 18 pristine movies' pad streams (in-stage: 1,140 jumps, 2,356 square actions,
  92 double-taps, 32 triangle, 51 camera-look, 7 kicks, 2 status). Live sampling
  (`analysis/phase2_action_oracle.json`, tools/phase2_action_oracle.py): 21 native
  instances snapshotted at −15/+2/+12/+32 frames, plus synthetic probes for the two
  actions the runs never perform — SLOW WALK measured at ≈0.605× run displacement
  over 60 held frames (first quantitative walk law), and the Circle negative
  control (null delta on all non-display fields). Remaining niche cases (handstand,
  downhill slide, seed-carry combinations) stay per-row blockers.
- [x] Define typed behavioral snapshots for player, objects, contacts, enemies,
  objectives, renderer, audio, and lifecycle state. — `analysis/phase2_stage_baseline.json`:
  12 typed fields (scene id 0x80082504, player kinematics block, health/lives/grain/
  quota/berry/power) + actor-record digest + kind-table digest, captured at anchor and
  anchor+60 frames for 42 anchors (16 identity, 3 bonus-entry, 8 lifecycle-completion,
  15 objective-progress). Renderer/audio snapshot fields are Phase-2 residual.
- [x] Record GPU/frame evidence for presentation behaviors and SPU/XA evidence for
  audio ownership and termination. — v1: `analysis/phase2_presentation_baseline.json`
  (tools/phase2_presentation_oracle.py): displayed-framebuffer sha256 at all 19
  identity anchors, each double-captured to prove per-anchor determinism (19/19,
  all hashes distinct), plus GPUSTAT/CRTC and CD-ROM/DMA state per anchor.
  RESIDUAL: SPU voice-level audio ownership (no spu.* API surface — XA/CD state
  recorded as the audio proxy) and in-motion presentation sequences.
- [x] Capture objective start/progress/success/failure state for every stage class. —
  START + SUCCESS now covered for ALL stages: the completion oracle records each
  stage's scene timeline (entry frame, in-stage span, exit transition = objective
  success) plus a typed completion-adjacent snapshot at the last in-stage sample,
  reproducible from movie + frame number. Progress states additionally anchored for
  stages 08/10/11 (performer/piece/Dot saves) and completion save-anchors for
  Training + 7 stages (incl. the `LEVEL12_ENDING`→stage-13 post-transition capture).
  FAILURE states (death/game-over per stage class) remain open.
- [x] Add repeated-use and soak cases for pools, counters, respawns, effects, and
  transitions. — v1: `analysis/phase2_soak.json` (tools/phase2_soak.py): reload×3
  determinism on 5 representative anchors (all identical), 1-emulated-minute idle
  soak on the two busiest rosters (guest alive, scene stable; only the HUD-animated
  health display drifts — the idle player takes contact damage, recorded), and
  10 pause/unpause cycles with post-cycle input responsiveness. RESIDUAL:
  pool-capacity stress (E06) and long multi-minute soaks.
- [x] Implement differential comparison masks for future reconstructed/diagnostic builds.
  — every baseline anchor carries `stable_fields`/`volatile_fields` (60-frame
  volatility window); the generated stage-identity scenarios assert ONLY stable
  fields, so the mask is applied by construction.
- [x] Verify that instrumentation is armed after timing-sensitive movie segments and
  does not change the reached state. — the scenario framework's lifecycle owns this
  (re-arm after load; `require_reproducible` movie playback); verified by the
  passing generated suite. Long-movie instrumentation perturbation checks remain
  with the cold-boot fixtures above.

## Oracle rules

- Cold boot is mandatory for code, disc, and asset evidence.
- Save states are narrow, hash-pinned runtime anchors only; instrumentation is re-armed
  after each load.
- Scene identity and a stage-specific anchor are asserted before evidence is accepted.
- Screenshots alone cannot establish state, timing, ownership, or lifecycle.
- A passing scenario does not promote an interpretation to Canon without evidence
  review.

## Exit gate

- Every Phase 1 row has a pristine trigger or a documented fixture blocker.
- Every campaign stage has identity, entry, main-objective, completion, and lifecycle
  assertions.
- Every core player action and major system has native positive and negative controls.
- Known catastrophic regressions are reproducibly detected by behavioral assertions.
- The oracle covers pause, death, respawn, results, save/reload, and transition rather
  than only stable gameplay frames.

## Known-regression sentinel map (2026-07-12)

Which committed pristine assertion detects each historically observed regression
class (external review asked for this join to be explicit):

| Regression class (historical) | Committed pristine sentinel | Status |
|---|---|---|
| Missing/corrupt terrain | Anchor frame hashes (`phase2_presentation_baseline.json`, 19/19 distinct+deterministic) + in-motion frame-hash sequence (`phase2_gate_residuals.json`) | covered |
| Audio corruption / high-pitched audio | SPU voice baseline incl. per-voice PITCH at every anchor + 120-frame key-on/off event signatures (`phase2_gate_residuals.json`); the prior XA/CD state was only a proxy | covered |
| Missing tokens/pickups | Corrected contact-pool census on the Canon frame (MEM_800B0D18; proximity-active slots + region digest per anchor) + pinned collected-counter end values for all 16 completion runs + the compare runner's counter checks | covered |
| Berry arc/visibility | Arc sentinel: per-frame trajectory of pool slot 52 from the pinned mid-throw save (reload-deterministic; gravity 128/frame²) + flight frame hashes | covered |
| Scene/boot-flow breakage | 19/19 stage-identity suite + 16/16 cold-boot completion replays (scene timelines) | covered |
| Renderer-class hook faults (t8/t9 clobber etc.) | MOD-side: hook/cave liveness validation (Phase 0 build gates) + the now-tracked ALLMODS regression scenario suite (`tools/scenarios/duckstation/regression_suite.json` — committed 2026-07-12; previously untracked, flagged by review) | covered (MOD lane) |

## Handoff to Phase 3

Phase 3 receives exact triggers, frames/cycles, register/state observations, expected
behavior, and lifecycle boundaries for semantic reconstruction.

## Progress record

| Oracle area | Status | Evidence |
|---|---|---|
| Fixture audit + hash pins | **done 2026-07-12** | `analysis/phase2_fixture_audit.json`: 246 fixtures pinned; 123 pristine saves, 63 non-pristine (ALLMODS-media) marked oracle-ineligible, 60 pristine-serial movies |
| Typed snapshots + differential masks | **done 2026-07-12** | `analysis/phase2_stage_baseline.json`: 42 anchors × 2 snapshots (anchor / +60 frames) with per-field stability masks; scene-id map for the whole campaign resolved from 0x80082504 (stage01..15 = 1,3,2,6,10,11,4,5,14,7,12,13,9,8,15; Training in-level = 17) |
| All-stage identity oracle (save anchors) | **done 2026-07-12** | 19 generated scenarios (`tools/scenarios/duckstation/stage_identity_*.yaml`, `stage_identity_suite.json`) — **19/19 PASS** on the pristine image (17 first pass; stage02/stage04 re-ran PASSED after transient 40s launch timeouts, assertion content identical). Reports under the session scratchpad; scenarios/baseline agreement is test-enforced offline (`tests/test_phase2_oracle.py`) |
| Row coverage vs Phase-1 registry | **done 2026-07-12** | `analysis/phase2_row_coverage.json`: 64 rows with pristine triggers, 43 rows blocked WITH documented blockers (exit-gate item 1 satisfied — no silent gaps) |
| All-stage cold-boot identity + completion | **done 2026-07-12 (second pass)** | `analysis/phase2_completion_oracle.json`: 16/16 `movies/go_to_end/*` from-boot movies replayed 1:1 on pristine (repro config); per-stage scene timelines, entry frames, completion transitions, and typed completion-adjacent snapshots; movie sha256 pins; `tests/test_phase2_completion.py` guards the artifact |
| Full player-action matrix | **done 2026-07-12** | Native positive controls for all core actions (jump/double-tap/square/kick/triangle/camera-look+lock/status from mined windows; slow walk 0.605× law; buttslide, carry-attachment (X/Z identity + fixed 19200 Y offset), handstand from operator fixtures); Circle negative control + no-input negative windows via the compare/negative tooling |
| Objectives/bosses/special stages | partial→strong | Objective success transitions for ALL stages (completion oracle); progression anchors stages 08/10/11; boss movies audited pristine (thumper/thud/hopper/bird); bonus-stage interiors + failure states open |
| Lifecycle/save/continue matrix | partial | Completion/post-transition anchors exist (incl. the LEVEL12_ENDING→stage-13 post-transition capture); death/respawn/game-over/save-reload cases open |
| GPU/SPU presentation oracle | **done 2026-07-12** | Static: 19/19 anchor frame hashes (`phase2_presentation_baseline.json`). In-motion: 7 movie-frame hashes byte-identical across two replays. Audio: `spu.status` per-voice pitch/volume/ADSR at 19/19 anchors (deterministic) + event signatures (`phase2_gate_residuals.json`) — the direct high-pitch sentinel |
| Soak/repeated-use cases | **done 2026-07-12** | reload×3, idle soaks (1-min ×2 + 3-min), pause×10, natural Bug Bar game-over; CAPACITY CLOSED with corrected semantics — free-slot-search allocator, >64 allocations/run churn (5 valid cursor wraps), and the all-occupied HANG proven by A/B callFunction (`phase2_capacity_hang_proof.json`) |
| Death/respawn/game-over | **done 2026-07-12** | TRUE health s16 @0x800A6594; contact-death law reproduced on tunnels/boss-arena/city classes (respawn hp=4, lives−1, spawn point); lives-0 death → game-over scene 0, corroborated by the natural Bug Bar game-over (`phase2_lifecycle_oracle.json`, `phase2_gate_residuals.json`) |

## Exit-gate assessment (2026-07-12, third pass) — NOT YET PASSED (close)

Met:
- Every Phase-1 row has a pristine trigger or documented blocker (row coverage).
- Every campaign stage has identity, entry, main-objective, and completion evidence:
  19/19 identity suite + 16/16 from-boot completion replays.
- Native positive controls for the core action classes (21 sampled instances across
  jump/double-tap/square/kick/triangle/camera/status) + the Circle NEGATIVE control
  + the measured slow-walk law (≈0.605× run).
- Lifecycle: save/reload determinism (12/12 fields), pause freeze/resume matrix,
  pause-cycle stress, idle soak, reload determinism.
- Presentation determinism: 19/19 anchor frame hashes (all distinct).
- Known catastrophic regression classes detected (smoke gate + suites + oracle).

- Death/respawn/game-over flows (closed 2026-07-12, fourth pass): TRUE HEALTH found
  at **s16 0x800A6594** (mercy-leaf gate `lh 0x6594; sltiu <4` at 0x8004999C; the
  damage applier at 0x8004A880 does `hp -= 1` and kills only when the result is
  NEGATIVE — hp 0 is the final hit, and lives 0 is the playable final life). Real
  contact-damage deaths reproduced by teleporting onto a censused actor at hp 0:
  death → ~120–180-frame animation → respawn at the level spawn point with hp
  restored to 4 and lives−1; final-life death leaves the stage to scene 0
  (game-over transition). On-hit side effects recorded (knockback velocity
  0x800A6530 := −1024; 0x800A6582/6584/6586/659E zeroed). The earlier disproofs
  (warp recovery; 0x800A7E2A = HUD pulse counter, NOT health) stand as evidence —
  the stage-baseline "health" snapshot field is that pulse counter and is
  semantically a display phase, kept only as a deterministic anchor value.

Closed by the residuals pass (2026-07-12, fifth pass — `analysis/phase2_gate_residuals.json`,
`tools/phase2_gate_residuals.py`, guarded by `tests/test_phase2_residuals.py`):
- SPU/audio-output oracle: the fork DOES expose `spu.status`/`spu.trace`/`spu.events`
  (the skill's method index was stale) — per-voice pitch/volume/ADSR baselines at all
  19 anchors (deterministic double-capture) + 120-frame key-on/off event signatures.
  Voice pitches are the direct high-pitched-audio sentinel.
- In-motion presentation: LEVEL03 movie frame hashes at 7 fixed movie frames,
  byte-identical across two full replays.
- Camera-lock native samples: both R1 instances (LEVEL02/LEVEL08 movies) sampled.
- Death matrix across stage classes: boss arena (stage03 — killed at Thumper's own
  record position) and city (stage07) reproduce the respawn law (hp:=4, lives−1,
  spawn point); tree (stage11) first records are non-hostile (documented).
- Multi-minute soak: stage01 3 emulated minutes alive/stable; Bug Bar soak produced a
  NATURAL end-to-end game-over (idle player killed twice by the arena → hp −1,
  lives 0, scene 0) — independent corroboration of every lifecycle law.
- The previously untracked scenario suites (regression/bonus/ALLMODS classes) are now
  committed as durable evidence.

Closed by the pool/arc pass (2026-07-12, sixth pass — `analysis/phase2_pool_arc_oracle.json`,
`tools/phase2_pool_arc_oracle.py`, guarded by `tests/test_phase2_pool_arc.py`):
- **CONTACT POOL SOLVED: 64 slots × 0x38 bytes at 0x800B0D48..0x800B1B47** (active
  signature `+2..3 == 20 20, +6..7 == 00 2E`; position s32 XYZ at +8). Found by
  scanning for the thrown berry's moving triple from `red_berry_thrown.sav`.
- Berry-arc sentinel (row A08): 20 per-frame projectile trajectory samples,
  byte-identical across reloads; **gravity constant = 128/frame² (Y-down)**;
  3 flight frame hashes cover visibility.
- Direct pickup-instance sentinel (C11/E06/E08): per-anchor pool census — active
  slot list + sha256 digest of the full pool region at all 19 anchors (all
  distinct) — plus pinned collected-counter end values for all 16 completion runs
  (`test_phase2_completion.py::test_collected_counter_sentinels`).
- Pool-capacity behavior (E06): 40-throw stress stable; max in-flight projectiles 2
  (cadence/ammo-bounded). RETRACTED (ninth pass): the earlier "64/64 saturation in
  normal play" claim was an artifact of a misaligned pool base + coincidental byte
  signature; on the Canon frame (MEM_800B0D18, active_type gate) anchors show 0–55
  proximity-active contacts, never forced saturation.

Buttslide (A06) closed by the operator helper fixture (2026-07-12, seventh pass):
`movies/Phase_Helpers/buttslide_carry_handstand.movie.json` (save-anchored on the
pristine image, Training). The EARLY section replays deterministically and yields
the slide state machine — anim pair 0x800A6542/46 = **(11,12)** during slide;
state word 0x800A6580 sequence **0 → 1 (air) → 4 (slam/dive) → 5 (ground slide)**;
fast ground displacement confirmed (`analysis/phase2_buttslide_oracle.json`,
`tools/phase2_buttslide_oracle.py`, `tests/test_phase2_buttslide.py`).

Seed-carry and handstand closed by the second operator fixture (2026-07-12, eighth
pass): `movies/Phase_Helpers/carry_handstand.movie.json` (save-anchored, replays
deterministically end to end — the shorter anchored clip eliminated the drift).
Laws extracted and test-pinned (`analysis/phase2_carry_handstand_oracle.json`,
`tools/phase2_carry_handstand_oracle.py`, `tests/test_phase2_carry_handstand.py`):
- **CARRY: the carried movable seed (chunk-31 actor, id 11) has its record X/Z
  slaved to the player EXACTLY while held, with Y at a FIXED 19,200-unit (600<<5)
  overhead offset** — verified to the unit at f660 (corrected ninth pass: the first
  statement claimed XYZ identity while testing only X/Z; external review caught the
  untested Y in the artifact's own sample).
- **HANDSTAND: position frozen >100 frames with the grounded flag reading 0 while
  animation cycles; dismount hop = state word 0x800A6580 == 6** (a new state id
  beyond the slide's 0/1/4/5).

## Ninth pass (reopen): corrections + executable oracle (2026-07-12)

External review found two factual errors in committed findings; both verified and
corrected, and the gate was strengthened rather than reinterpreted:

1. **Pool base corrected to Canon.** The empirically derived 0x800B0D48 was 0x30
   into the real contact array `MEM_800B0D18` (Canon note existed and was not
   consulted — process failure recorded). Census rerun on the Canon frame (XYZ +0,
   live gate `active_type(+0x22) > 0`; rest-state flags calibrated live to 0x20):
   anchors show 0–55 PROXIMITY-ACTIVE contacts. The "64/64 saturation in normal
   play" claim is RETRACTED (artifact of the misaligned signature). The arc
   sentinel survives re-anchored: the projectile is true slot 52, gravity 128/f².
2. **Carry law corrected.** X/Z identity + FIXED 19,200-unit (600<<5) overhead Y
   offset; the artifact's own f660 sample showed the offset the first test never
   checked. Test now asserts all three components.
3. **All-stage death matrix** (`analysis/phase2_death_matrix.json`): the
   death→respawn law (lives−1, respawn hp=4, same scene) reproduced on 8 stage
   classes directly + stage 9's natural game-over; 7 stages documented as
   non-hostile-at-anchor rosters (records tried listed; death attribution is by
   LOCATION, not record-id hostility).
4. **Per-action negative controls** (`analysis/phase2_negative_controls.json`):
   no-input idle (state word stays 0, nothing in flight), walking without Square
   (no carry attachment), single jump (never enters slam/slide states 4/5),
   movement without Start (no pause freeze) — all PASS.
5. **Executable comparison runner** (`tools/phase2_compare.py`): re-collects
   stable fields, frame hashes, SPU voice digests, pool censuses (anchor lane) and
   replays go_to_end movies asserting entry scene + end-state counters (movie
   lane); exits 1 on any divergence. Self-check vs pristine: PASS. NEW DETERMINISM
   GOTCHA found while building it: `emulator.loadState` restores the save state's
   EMBEDDED memory card, desyncing every later from-boot replay — the movie lane
   must run before the anchor lane (encoded in the tool).
6. Note contradictions fixed (sentinel table pickups/berry-arc now covered;
   saturation retracted; action-matrix progress row updated).

## Tenth pass: second review round — all four blockers closed (2026-07-12)

1. **Pool gating/capacity**: the walker's own gate was DISASSEMBLED
   (FUNC_800586B0+0x80..0x9C): `active_type(+0x22) > 0 AND flags(+0x33) & 0x02`;
   bit 2 toggles within the frame, so paused anchors show typed-but-not-enabled
   slots — the census now reports BOTH counts. TRUE capacity evidence: the alloc
   cursor (0x8008234C, wraps 0x40) **wrapped 6 times during one ordinary LEVEL03
   run** — the 64-slot ring's overwrite-oldest overflow is native-gameplay
   behavior, not a hypothetical.
2. **Negative controls de-vacuized**: the jump control now proves its premise
   (airborne state observed via dense sampling at a real in-level anchor) — and
   surfaced a semantic refinement: state 5 is a shared moving-landing/skid state;
   only state 4 (slam/dive) is double-tap-exclusive. The carry negative tracks the
   actual id-11 seed at the carry fixture's own anchor; a Triangle-without-carry
   control was added. 5/5 pass with premises.
3. **Death matrix at full rosters (14/16 stages)**: with three operator-observed
   method fixes (drop-from-above placement — exact-center teleports clip into seed
   geometry and burrowed spiders sit below the floor; lives normalization — six
   late-stage anchors sat at lives 0 where death fires the game-over FMV and a
   lives−1 detector misses it; id-11 seed records skipped), every stage with
   reachable contact damage reproduces ALL THREE laws (lives−1, respawn hp=4, same
   scene). Negatives: Training (tutorial roster) and Bug Bar (empty table; flow
   covered by the natural game-over). Caveats recorded in the artifact: negatives
   are method-bounded (airborne carriers, stage-14 Atta rail), knockback under
   drop-placement is not representative, attribution is by location.
4. **Candidate-lane visual/audio/pool coverage + mutation proof**: the movie lane
   now checks a mid-stage (entry+600) frame hash, SPU voice digest, and pool census
   per movie against `analysis/phase2_movie_baseline.json` (written from pristine,
   16/16). MUTATION TEST (`analysis/phase2_mutation_test.json`): the runner against
   ALLMODS (the known-bad build) FAILS with 16 mismatches spanning EVERY detector
   class — visual frame hash, SPU voices incl. a pitch difference (the
   high-pitched-audio class), pool contents, collected counters, and scene flow.

## Eleventh pass: third review round — allocator truth, guarded baselines, isolated proofs (2026-07-12)

1. **Allocator semantics corrected** (review caught a wrong inference; the C
   reconstruction `src_re/contact_alloc_80059e44.c` existed and was not consulted —
   the same process failure as the pool base, now a standing rule): contact_alloc
   is a **round-robin FREE-SLOT SEARCH** (skip occupied = `flags&0x80 &&
   active_type!=0`) with **no full-array escape**. Cursor wraps prove >64
   allocations over time (churn + reuse) — NOT saturation, NOT overwrite-oldest
   (retracted). Wrap counting now excludes invalid pre-game cursor values:
   **5 valid wraps** in the LEVEL03 run (review's recount confirmed exactly).
2. **CAPACITY HANG PROVEN** (`analysis/phase2_capacity_hang_proof.json`): A/B via
   `debugger.callFunction` on contact_alloc — with free slots it returns a valid
   record pointer (slot 55); with all 64 slots synthetically occupied the
   escape-less search loop **never returns (timeout)**. The capacity row is now
   CLOSED with the true semantics: the hazard is a hang, not an overwrite, and it
   is a REAL MOD-safety constraint (never let mods hold all 64 slots occupied).
3. **Baseline writer pristine-guarded**: `--write-movie-baseline` refuses to run
   unless the mounted BIN sha1-matches the pinned pristine image, and the baseline
   now records media hash + per-movie fixture sha256s. Baseline-writing runs no
   longer clobber the definitive comparison report.
4. **Same-scene SPU pitch proof** (`analysis/phase2_spu_pitch_mutation.json`): a
   pitch-only mutation of one on-voice fires the comparator's `spu_voices` check
   and NOTHING else — the high-pitch detector proven independently of scene
   divergence. (Runtime register mutation is blocked: the fork exposes no SPU
   register write surface — documented fork-extension candidate. The ALLMODS run
   remains the broad runtime negative.)
5. **Negative-control coverage map** (`analysis/phase2_negative_coverage_map.json`):
   16 core actions/systems mapped to their negative fixture — 13 covered, 3 gaps
   documented and bound to registry next-experiments (kick→A04,
   camera-mode→A17, status-panel→A19).

## Twelfth pass: closure pass — gate letter satisfied (2026-07-12)

Fourth review round conceded in full: the gate's action-control bullet CAN be met
without Phase-3 semantics, and the results lane and artifact freshness were real
holes. All four items closed:

1. **Paired BEHAVIORAL controls** (`analysis/phase2_action_behavior.json`,
   `tools/phase2_action_behavior.py`) — outcomes, not sample existence:
   - CAMERA: the camera struct 0x80095358 (Canon SYS_camera) MOVES under L1 and is
     byte-static under no input; R1 produces a different camera state than
     move-only. Positive + negative, both measured.
   - STATUS: Select yields a different displayed-frame hash than an identical
     no-Select window from the same anchor (the panel is a visual event).
   - KICK: **the kick EXISTS and is now a positive/negative control** (thirteenth
     pass; my earlier "disproof" was a METHOD ERROR — holding Square from a paused
     state never produces a press EDGE, and the operator's correction that berries
     are infinite killed the zero-ammo hypothesis outright). Static scan for
     L2/R2 button-mask tests near Square tests found the branch at **0x80048F4C**:
     pad `0x80082488 & 0x0300` (L2|R2 held) AND `& 0x8000` (Square) AND a FRESH
     press edge (prev-pad `0x80082380`) AND not-already-kicking AND grounded
     (|Y − floorY| < 1024) AND `player+0x5C == 0` → writes **−16 to the KICK TIMER
     `0x800A657A`**. Live control: L2+Square and R2+Square both fire the timer
     (−16, counting up); Square alone and no-input leave it at 0. Two invalid
     discriminators recorded on the way: `0x800A6542/46` is an animation FRAME
     COUNTER (cycles while idle), and a live actor's record mutates on its own.
     Residual (row A04): the kick's DAMAGE class — the action is bound, its
     damage path is not.
2. **Results lane executable** (`analysis/phase2_results_baseline.json`): the
   comparison runner now covers ALL 42 baseline anchors — identity, bonus,
   **lifecycle_completion (results screens)** and **objective_progress** — each
   with a pinned displayed-frame hash + typed stable fields, pristine-guarded.
   Definitive pristine self-check: **701 comparisons over 42 anchors + 16 movies,
   0 mismatches.**
3. **Row-coverage freshness**: artifact regenerated (67 pristine-trigger / 40
   blocked) and a regenerate-and-compare test now fails on drift.
4. **Standalone proofs regenerable** (`tools/phase2_proofs.py --hang/--spu`): both
   the capacity-hang A/B and the same-scene SPU pitch proof are committed tooling;
   their tests assert the tool's provenance, not merely the JSON's word.

Negative-control coverage map: **0 documented gaps remaining** (16/16 systems).

## Fourteenth pass: coverage map was SELF-GRADING — gate REOPENED honestly (2026-07-12)

Review found a defect the "16/16, zero gaps" count was HIDING: the coverage map was
hand-authored, so it omitted five core actions the phase's own scope names
(seed-as-weapon, plant-output cycling, planting/cracking, uprooting, swinging),
called handstand "covered" while its own status text said partial, and its test
permitted an empty gap list regardless. That is precisely the self-grading failure
this project has spent the session eliminating.

Fixes:
- **The map is now DERIVED from the registry** (`tools/phase2_coverage_map.py`):
  every section-A core-action row must be COVERED (naming artifact + observable) or
  a documented GAP (with a NEXT experiment). Omission is impossible by construction,
  and the generator EXITS 1 while any gap remains.
- **The test is falsifiable**: it regenerates the map, requires the row set to equal
  the registry's, and asserts `gate_bullet_3_met == (no gaps)`.
- **New behavioral pairs landed** (`tools/phase2_seed_action_controls.py`,
  `analysis/phase2_seed_action_controls.json`): A12 seed-colour change (Triangle
  while GENUINELY carrying — reached by replaying the operator fixture, since a
  synthetic teleport+Square never attaches — yields a distinct frame vs the
  identical no-input window), A13 output cycling (X, likewise, distinct from both
  control and Triangle), A10 handstand NEGATIVE (beside the seed without Square →
  grounded stays 1, pairing the existing mounted positive), A16 swinging (attached
  anchor state 5 vs grounded state 0).

### Fifteenth pass: the last four pairs — GATE BULLET 3 NOW MET (20/20)

- **A14 plant/crack** — the plant spawner FUNC_8005BDBC (Canon) fires exactly once
  in `blue_seed_levels.movie` (located by bisection: movie frames 400–800) and NEVER
  in 0–400. Positive/negative from one pristine fixture. The other four seed movies
  never call the spawner — they are VIEWING movies; Training's seed is carry-only BY
  DESIGN (operator-confirmed), so cracking it there was a category error. **Method
  gotcha recorded: an execTrace watch armed AFTER a movie seek misses events — it
  must be live while the frames execute.**
- **A15 uproot** — from the post-plant state of the same movie: Square at the grown
  plant yields a distinct frame vs the identical idle window.
- **A11 seed-as-weapon** — operator fixture `movies/seed_as_enemy.movie` (Square at
  f58 picks up, f327 drops on an enemy): the drop changes the LIVE ENEMY TABLE
  (0x80090748 slots 0–4) and the frame; the same window without the drop input does
  not.
- **A07 spin — DISPROVEN** (`analysis/phase2_spin_disproof.json`): the kick's
  static-scan method found NO directional-sequence recognizer. Every cluster of
  direction-mask tests was disassembled — all are pad decoders, menu navigation,
  analog mapping or object logic; none keeps the input-history state a spin
  necessarily requires, and the retail manual does not list the move (secondary
  sources only). Row reclassified `not_applicable` (like Circle) WITH evidence.

Derived coverage map: **20/20 core actions covered, 0 gaps, `gate_bullet_3_met: true`.**

## Sixteenth pass: review reopened the fifteenth — three evidence defects fixed (2026-07-12)

Codex re-verified the fifteenth pass and found the action layer overstated. All
five findings were CONFIRMED live and fixed:

1. **A15's window was empty.** The f900 "post-plant" trial ran against an empty
   plant table (single-seek ground truth: slot0 type 7 lives f120–f740, cleared
   by f765). The pass was Square-vs-idle frame noise. FIXED with the faithful
   full-movie timeline (below).
2. **A16 passed by comparing two anchors**, not by performing the action. FIXED:
   real same-anchor pairs — GRAB (hold up toward the vine + cross from
   `in_front_of_swing.sav` → sustained state 5, grounded 0, pendulum Y;
   cross-only/no-input never attaches) and RELEASE (cross while attached →
   leaves state 5, lands; idle keeps swinging). The earlier grab failure was
   simply not holding toward the vine.
3. **The "derived" coverage map still declared its verdicts** (hand-written
   COVERED dict, hardcoded-empty gap list). FIXED: `tools/phase2_coverage_map.py`
   now INSPECTS evidence — each row maps to (artifact, JSON path, predicate)
   checks evaluated at generation time; unmapped/failing rows become gaps
   automatically. Falsified by probe: corrupting one artifact value flips the
   row to GAP and the exit code to 1.
4. **A11's committed proof watched a weak proxy.** FIXED with per-frame causality
   (below). Codex's suggested watch-based branch proof turned out to be
   IMPOSSIBLE — see the platform gotchas.
5. **`phase2_row_coverage.json` was stale in the closure commit.** Regenerated
   and committed together this time.

### ⚠️ Platform gotchas discovered while fixing (cost: the fifteenth pass)

- **An execTrace watch armed during movie playback DESYNCS the replay.** A/B
  isolated: watch + single-seek diverges from the movie's first input; poll-only
  stepping (any granularity) is faithful and byte-deterministic (two full-movie
  15-frame-step scans hash identical). The fifteenth pass's A14 spawner trace —
  and its "the other seed movies never plant" claim — were measured on DESYNCED
  replays.
- **Armed instrumentation shifts outcomes in SYNTHETIC phases too**: with any
  exec-breakpoint or watch armed, the A11 seed drop MISSES the enemy; without,
  it hits reproducibly across every advance-chunking pattern tested.
- **accessLog and write-breakpoints never engage** under the CachedInterpreter
  repro config (player-X write watch: 0 events over 10 frames).
- Consequence: movie-lane evidence must be POLL-ONLY; PC-level traces only
  outside playback AND only when the scenario tolerates timing perturbation.

### The faithful blue_seed_levels timeline (poll-only, deterministic)

The movie is a FOUR-CYCLE demo at one seed: cross (X-slam) → plant-slot
creation 20–120f later (slots 0–3, cursor 0→4, types 7,7,6,7 — the type-6
cycle follows the triangle color change) → seed rides the plant top (raised
EXACTLY +20480 = 640<<5 over ground Y) → Square → seed descends to ground at
pinned X/Z → slot clears 40–170f after the press (expiry byte +0x2E still 5 =
player uproot, not wilt). 4/4 creations and 4/4 teardowns input-correlated;
zero events elsewhere in 3795 frames; seed record conserved throughout.

### A11 causal chain (uninstrumented, per-frame)

Square press → carry law breaks (X/Z identity) → ballistic travel toward the
enemy (dist 31k→11k) → ON THE LANDING FRAME enemy+0x6C := **−20** → decays
0.5/frame → enemy removed from the live actor table. No-press control: carry
holds, +0x6C stays 0, enemy persists. −20 is the exact value written by the
only two seed arms in the EXE (0x80058E14/18 carried-contact kind-4;
0x8004B2CC/D0 twin — both `jal 0x80050994, a0=-4`), found by full-range scan.

## Superseded exit-gate decision — passed 2026-07-12 (sixteenth pass)

All five bullets met with committed, regenerable, test-guarded evidence; the
coverage artifact both ENUMERATES from the registry (cannot omit a row) and
COMPUTES its verdicts by inspecting selected evidence-artifact fields (a
verdict cannot contradict the fields it checks — reviewer-falsified: one
corrupted value flips the row to GAP). The checks validate summary fields,
not every raw sample, so semantic review of the CHECKS table itself remains
part of any future gate audit:
1. Row coverage: pristine triggers / documented blockers (freshness-tested,
   regenerated WITH this commit).
2. Every stage: identity (19/19), entry, objective, completion (16/16 cold-boot
   replays), lifecycle (deaths on 15/16 + the natural Bug Bar game-over).
3. **Superseded claim:** core actions 20/20. The retroactive audit below found
   that A07's absence proof does not reproduce, so the mechanical count is 19/20.
4. Known catastrophic regressions: sentinel map + ALLMODS mutation test (fails
   across visual/audio-pitch/pool/counter/scene) + same-scene SPU pitch proof.
5. Beyond stable frames: pause, death, respawn, save/reload, transitions, soak,
   in-motion presentation, results screens, per-voice audio.
Executable oracle self-check: 696 comparisons over 42 anchors + 16 movies, 0
mismatches (independently re-run by the reviewer from a fresh instance).

## Iteration-5 pristine-origin correction — 2026-07-14

The former Training identity save was same-serial but not original authority:
`emulator.getStateInfo` identifies its embedded media as `ABL_ALLMODS.cue`. It is now
centrally classified `non_pristine` and retained only as comparison history. The
replacement `phase3_pristine_training_gameplay_i5.sav` was derived at target movie
frame 6900 from the hash-pinned 9,299-frame from-boot pristine Training recording,
saved at emulator frame 6905 in scene 17, and centrally pinned before use.

This changes honest low-level counts without weakening coverage. Training now supplies
10 stable fields instead of the contaminated state's 15, so the full pristine
self-comparison is **696**, not 701: 42 anchors + 16 movies, 0 mismatches, with 42
strict pre-load origin inspections. The replacement in-level Training roster also
reproduces contact death/respawn, raising the death matrix to **15/16**; Bug Bar remains
the sole method-bounded contact negative and its natural game-over stays covered by the
soak oracle. The movie/save collectors now reject generic launcher profiles, run their
from-boot lanes before any state can restore an embedded memory card, and pause
immediately after playback start so the first frame delta cannot race.

## Retroactive knowledge-closure audit — 2026-07-12

**Result:** the retained pristine oracle remains valid for the behavior it measures,
but the Phase-2 behavioral gate is **qualified, not closed**, and knowledge closure is
**partial**. The comparison lane has its corrected 696-comparison pristine baseline and
known-bad mutation sensitivity. The action gate now mechanically reports 19/20 with
one honest gap: A07 spin.

The prior hand-authored spin artifact claimed six inspected clusters and concluded
“NO SPIN MOVE.” Its stated scan did not reproduce that inventory, and absence of a
direct direction-mask cluster could not exclude table-driven, analog, overlay, or
differently encoded recognition. It is superseded by
`tools/phase2_spin_disproof.py`, which hash-verifies the pristine EXE and generates a
bounded nine-cluster negative. A07 is restored to `external_lead`; the generated
coverage map fails gate bullet 3 instead of manufacturing 20/20. This is the only
behavioral reopening produced by the audit.

The execTrace/movie perturbation is now a reproducible live A/B artifact rather than
prose: two poll-only frame-120 runs are byte-identical and create plant type 7/cursor
1, while the same movie with a plant-spawner execTrace watch armed has type 0/cursor
0. See `analysis/phase2_platform_gotchas.json` and
`tools/phase2_platform_gotchas.py`. The separate A11 watch-induced miss and
CachedInterpreter write-watch limitation remain explicitly non-regenerable residuals
with named follow-ups; they are no longer presented as independently proven platform
laws.

Coverage predicates now consume outcome fields (state sets, displacement, grounded
state, carry break, landing, −20 write, decay, retirement, attachment, distinct
frames, creation/teardown arrays) and contain **no `.passes` field references**. The
two newly introduced
`seed_as_enemy` fixtures are included in the regenerated central audit. All 251
referenced Phase-1/2 fixtures have central pins and matching local hashes; no confirmed
registry address remains prose-only after the typed `confirmed_sites` promotion.

Remaining blockers are the exact A07 runtime trigger, two bounded platform residuals,
the declared external fixture set, and the four repo-wide tracked→untracked imports.
The import count is historical: Phase 3 iteration 3 hash-pinned and committed those
non-copyrighted sources, and the current low-level audit reports zero import gaps.
Phase 3 may continue consuming the unaffected oracle contracts, but must not cite a
closed Phase-2 action gate until A07 is resolved or the gate is explicitly revised.

One audit run deliberately used the generic debugger launcher and produced **131/701
mismatches** despite pristine media. This was a harness-profile failure: the from-boot
movies require full boot, CachedInterpreter, and the pinned card seed. That attractive
failure is retained as diagnosis rather than hidden. `tools/launch_repro_playback.sh`
now detaches reliably for automation, and `tools/phase2_compare.py` requires
`--repro-config-dir` and validates the critical settings and card hash before the movie
lane. The final iteration-5 profile-guarded pristine run passed **696 comparisons over 42 anchors
+ 16 movies, 0 mismatches**. The live execTrace A/B passed; the working-tree safe
suite passed **265 / 27 deselected**; the detached clean worktree plus declared
fixtures and pristine EXE passed **222 / 4 media skips / 27 deselected**; and the
derived action map honestly exited nonzero at
**19/20, A07 only**.

## Superseded: earlier gate passes (twelfth pass, closure)

Every gate bullet now has committed, regenerable, test-guarded pristine evidence:
1. Every Phase-1 row: pristine trigger or documented blocker (row coverage).
2. Every stage: identity (19/19 suite), entry, main-objective, completion (16/16
   from-boot replays), lifecycle (death/respawn/game-over across stage classes +
   the natural Bug Bar game-over).
3. Core actions: native positive controls for jump, double-tap, square actions,
   kick, triangle, camera look/lock, status, slow walk (measured 0.605× law),
   buttslide (state machine), seed carry (attachment law), handstand (mount
   signature), plus the Circle negative control.
4. Known catastrophic regression classes: sentinel map (terrain/audio/scene-flow/
   pickups/berry-arc all covered by committed assertions; renderer-class hooks by
   the MOD-lane suites).
5. Beyond stable frames: pause matrix, death, respawn, save/reload, transitions,
   soak, in-motion presentation, per-voice audio baselines.

Residual refinements (post-gate, feed Phase 3/4 — none block the oracle):
A11 seed-as-weapon, wall-facing seed release/rebound behavior (the old blocked-drop
hypothesis is retracted; pristine fixture pending), the fixed-seed object class,
camera-mode words during mounts, and per-row `next` experiments throughout the
registry.

First-pass correction stands recorded: `movies/go_to_end/` (operator, 2026-07-08)
already held every stage's from-boot run; the audit test now guards that join.
