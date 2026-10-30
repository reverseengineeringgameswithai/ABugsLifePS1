---
kind: session
id: SESSION_2026-07-11_training_25_grain_cage_handoff
name: TRAINING 25-grain cage handoff
date: 2026-07-11
status: ready_for_operator_retest
systems:
  - SYS_native_grain_gates
mods:
  - MOD_training_25_grain_corner_cage
artifacts:
  - desired_letter_loc.sav
  - walk_up_sound_jingle.sav
  - ceiling_cage_issue.sav
  - fall_through_floor.sav
  - on_crate.sav
  - on_crate_1.sav
  - movies/crate_ceiling_issue.movie.json
  - tools/scenarios/duckstation/training_grain_gate.yaml
---

# Session 2026-07-11 — TRAINING 25-grain cage handoff

## Resume here

The task was to move one existing TRAINING letter to the Flik position captured
in `desired_letter_loc.sav`, enclose it in a distinct corner cage, and require at
least 25 grain plus physical cage contact before it lowers. The behavior borrows
the confirmed threshold/contact/stepped-drop shape of the retail LEVEL02 gate,
but it deliberately does not copy that gate's twig visual.

**Fifth pass (same day, follow-up session).** The operator retest found the
roof still was not a walkable floor (stuck jump-fall pose, ice-slide movement,
occasional death when stepping off an edge). Root causes and fixes are in
[[MOD_training_25_grain_corner_cage]] ("Native roof landing and walk-off
correction") and the fifth-regression section of
[[EXP_2026-07-11_native_and_training_grain_gate]]: touchdown now publishes the
full native landing (`anim 5`/`air 0`/momentum kill), roof support uses the
exact slat rectangle, and a footprint exit undoes the native ground-glue and
falls normally instead of teleporting 14k down. The same session did a
render-only aesthetic pass (Gouraud shading, per-face ambient, denser bars,
framed drop-shadowed plaque, diamond grain kernel, slatted deck with beams).

**Sixth pass (same day).** The operator's `crate_ceiling_issue.movie.json`
showed butt-slam misbehavior on the roof. Root cause: the fifth pass wrote
MORE than the native integrator contact path writes. Measured native contracts
(pebbled ground): the contact path writes Y/VY/grounded plus a landing anim
keyed by incoming air state (`6` for heavy-fall `air 4`, else `5`) and NEVER
writes `air_state`; held X parks in `air 5` without re-jumping. Forcing
`air 0` had created a bounce loop, forcing `air 2`/`anim 4` at walk-off broke
the heavy-fall recovery (anim `6` stuck permanently on plain terrain), and the
VY-sign release made the latch flap during roof sprints. The roof tick is now
integrator-exact; latch releases only on real takeoff (`air 1` + rising VY) or
footprint exit. See the sixth-regression section of
[[EXP_2026-07-11_native_and_training_grain_gate]].

**Seventh pass (same day).** `on_crate.sav` showed plain walking on the deck
lurching ~1500 units on alternating ticks (skating Flik off the roof): the
integrator's resolved commit discards the movement code's raw proposal on real
ground, but 15k above the sector floor the collision loop never settles and
the unresolved fallback (`0x80036d00`) lets the proposal survive. The roof
tick now re-commits `prev + V` each tick using the native previous-position
mirror `0x800A6510/18`, and the stand offset corrected 256 → native 128
(body Y `-9128`). Ground-protocol measurements confirm accel/stop/reversal
were already identical to pebbled ground.

**Eighth pass (same day).** `on_crate_1.sav`: no walk anim on the deck, camera
shift on R2 slow-walk, corner clip-through death. Two causes. (a) TIMING -- the
pin ran only in the RAW HUD-pump tick, AFTER its consumers: the anim selector
(`actor_skinned_update` 0x800563D4) early-exits on grounded==0, and the camera
reads position mid-tick; the native grounded clear at 0x80036B90 lands one frame
ahead of the pump. The pin now ALSO runs at integrator exit via a guard cave
(hook `0x800495D0`, guard `0x8007FB28`) that tail-jumps into a pin appended to
the RAW payload. (b) GEOMETRY -- the operator's diagnosis was right: the cage
overlapped the recess wall and the void pit was reachable through the corner.
Cage + letter relocated 25,000 local units out the front onto probed-solid floor
(anchor `(-7104,3092,112128)`, entry 65 `(-222,-134,3504)`, roof body Y -10628).

GOTCHA worth remembering: `0x80081858` is reported "candidate_free" by
`mod/build.py --suggest-caves` but lives in a BOOT-POLLED table -- a cave there
hangs the disc at the PlayStation logo. `--suggest-caves` only samples gameplay
states; watch a candidate from COLD BOOT before using it.

The implementation is rebuilt and behaviorally passing (74/74 cold-boot
assertions, smoke gate PASS). No known open code defect; next session should
begin with operator playtesting of the rebuilt ALLMODS disc. Known native
interaction, judged acceptable: once OPEN latches, the native construct pass
awards G at its native letter radius (~13k), so riding the roof down collects G
during the descent.

Do not treat this session note as Canon. Original LEVEL02 behavior belongs in
[[SYS_native_grain_gates]], MOD-private behavior belongs in
[[MOD_training_25_grain_corner_cage]], and the full runtime evidence belongs in
[[EXP_2026-07-11_native_and_training_grain_gate]].

## Intended finished behavior

- Final TRAINING `G`, type-`0x3F` entry `65`, is staged at file coordinates
  `(-931,-45,3832)`, corresponding to runtime X/Z `(-29775,122634)`.
- At grain `0..24`, four solid walls and a standable roof prevent every route to
  the letter. Closed denial awards no bit and plays no collection jingle.
- The cage is drawn in the scene-depth ordering table, so native Flik renders on
  top of it.
- Grain `25` alone does not move the cage. A real wall/roof touch latches ACTIVE;
  drop then advances by `320` per Training HUD cadence to `16000`.
- Collision opens at drop `12000`; only OPEN authorizes collection.
- Bars, plaque, `25`, grain glyph, and roof clip at ground Y `6500` while
  lowering and disappear from the ground up.
- Closed wall collision behaves like a stop: restore the immediately previous
  X/Z, clear VX/VZ, and preserve Y/VY, native air state, floor ownership, render
  state, and respawn state.
- A downward top-plane crossing lands at body Y `roofY-128` (native grounded
  body offset; roof body Y `-10628` at the relocated anchor). A MOD-private roof
  latch keeps that support across native landing state `5`; jumping upward or
  leaving the footprint releases it. The pin runs BOTH at integrator exit (guard
  cave) and in the RAW pump tick, so the anim selector and camera see it.

## Implementation map

- `mod/caves/training_grain_gate.c`: relocation-free MIPS-I C for cage state,
  collision, roof support, lowering, ground clipping, projection, and rendering.
- `tools/training_word_pickups.py`: compiles/appends the C blob to the Training
  type-`0x22` helper, stages entry `65`, and patches collection authority.
- `tools/scenarios/duckstation/training_grain_gate.yaml`: cold-boot behavioral
  regression, including silent denial, wall/floor integrity, airborne wall
  contact, persistent roof support, opening, and collection.
- `src_re/player_update_80048138.c`: bounded player air/landing-state notes used
  to understand why native landing state `5` temporarily lost MOD roof support.
- `src_re/pickup_handlers_80054288_80054554.c`: bounded reconstruction comment
  for the false-jingle denial branch.

Packed MOD state is word `0x800813EC`:

| Field | Meaning |
|---|---|
| low `u16` | drop distance |
| byte `+2`, bit 0 | ACTIVE after qualifying contact |
| byte `+2`, bit 1 | ROOFED support latch |
| byte `+2`, bit 7 | OPEN and collection-authorized |

Current compiled gate blob is 9,072 bytes, SHA-256
`3fccd825b506308a4429d64ef984c5a4dfffbbbe595a09a40a5e5532841c4b02`
(eighth pass; earlier blobs `75aab92e…`, `58332f06…`, `37ab38c0…`,
`2a9e2bba…` are superseded).

## Regression saves and exact reproductions

All save loads are narrow runtime evidence, not a replacement for cold boot.
Re-arm every trace/watch after each load and validate state media first.

| Save | SHA-256 | Pre-fix reproduction | Corrected result |
|---|---|---|---|
| `walk_up_sound_jingle.sav` | `cfedb8ad512acb600aa7223c348ff92c4a6be94d5a247b98dc18c83142272e6d` | Hold Up; closed G reached retail result `-2` and called `0x8005044C` | Three deny-branch hits, zero pickup-sound calls, bit 7 clear |
| `ceiling_cage_issue.sav` | `06a33a64b618bcdb957ca6a5f23bce25801ffd930b9a62a4d77222ce87294590` | Hold Jump+Up; roof landing at step 37 was lost after step 42 and Flik shifted off | Y `-9256`, floor `-9000`, grounded `0x0101`, ROOFED set through step 80 |
| `fall_through_floor.sav` | `6d4da41e141014412e9281e562ddb0ef75c17a8c74f70312af01693f4bf5208d` | Hold Up; tangential wall slide left valid terrain, Y reached `114235`, then respawn | Stops near `(-30710,5414,109984)`, floor about `5540`, VX/VZ zero, no fall through step 90 |

The two latest saves report state version `84`, serial `SCUS-94288`, and embedded
media path `build/ABL_ALLMODS.cue`. The exact corrected-save checks used a
transient injection of the newly compiled C blob into the saves' existing helper
allocation, followed by instruction-cache invalidation. Persistent disc/code
evidence comes from the cold-boot scenario below.

## Verified build and evidence

- ABL revision observed during work:
  `e6402e8717f56df37b47405f6423aad0882ed502`; the operator's large dirty
  worktree was preserved.
- Rebuilt `build/ABL_ALLMODS.bin` SHA-256 (eighth pass):
  `281a560d715fd4792e75b518b7e645dd6727b3fba33da5d562167e6b8535227c`
  (seventh-pass disc `aabff70c…`, sixth `aa1fedc4…`, fifth `3e6b1a11…`).
- `build/ABL_ALLMODS.cue` SHA-256:
  `07d1c83c0b87ab7f14b0c9e6dc988ab8f70fda58de76fe1b4cdc7f9e1f37bf8e`.
- Cold-boot scenario report SHA-256 (eighth pass, 74/74):
  `014962b31bae6f75b33c66125ab7d5bc4d338a2bdc7848432e5d5d1cf5e70e28`
  at `/tmp/abl-ps1-report-training_grain_gate/training_grain_gate.json`
  (seventh-pass 72/72 `f6a70319…`, sixth 69/69 `2fa66fd7…`).
- Smoke gate PASS: `build/ABL_ALLMODS_smoke.json` SHA-256
  `83e8998f6662cc4576e5f11fffdb9af50b7c1e60fec253eff1d5e2c378fa6794`.
- Focused tests: `15 passed`.
- Safe suite: `148 passed, 7 deselected`.
- Mod layout and scenario schema validation passed. The handoff introduces no
  dangling-link or schema finding. At the time of this note's final check, the
  global vault ratchet was independently blocked by the concurrent
  `SYS_bonus_unlock_challenges.md` evidence-policy finding; do not attribute that
  unrelated dirty-worktree item to the cage work.

Reproduction commands:

```bash
python3 mod/build.py --mods mod/mods.yaml --out build/ABL_ALLMODS --force
python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/training_grain_gate.yaml --disc build/ABL_ALLMODS.cue
python3 -m pytest tests/test_training_word_pickups.py -q
python3 tools/run_safe_tests.py
python3 tools/validate_mod_layout.py
python3 tools/validate_vault.py --check
```

## Takeover procedure

1. Read `AGENTS.md`, use the `duckstation-external-debugger` skill, and route API
   operations through [[DuckStation_API_Index]].
2. Inspect `git status --short`; do not overwrite the operator's unrelated dirty
   files or commit generated discs, saves, captures, tokens, or copyrighted data.
3. Verify the current build hashes. If source inputs changed, rebuild before
   judging behavior and record the new hashes rather than silently replacing the
   evidence above.
4. Run the declarative cold-boot scenario first. It verifies media identity and
   exercises all gate contracts on the rebuilt disc.
5. Manually retest the supplied saves/routes: sustained Up at each wall and
   corner, Jump+Up onto the roof, walking across and jumping off the roof, falling
   from above, grain 24 denial, grain 25 no-contact, grain 25 contact/lowering,
   disappearance, passage, and final collection.
6. If a new divergence appears, capture identity, exact input, frame/cycle,
   player XYZ/velocity/floor/grounded/air-state, and packed cage state before
   patching. Convert the smallest reproduction into another scenario assertion.
7. Keep original-game discoveries in Canon, experimental traces/hashes in
   Experiments, and new cage state/hooks/intended behavior in Mods.
8. Every DuckStation run must use a fresh absolute config directory, dedicated
   loopback port/token, and verified media. Stop only the PID owned by that config
   directory. At this handoff, no DuckStation/external-debugger process from the
   work remained running.

## Current judgment

The fifth pass showed the general law for MOD platforms in this engine: a
post-integrator grounded republish alone can never make a platform first-class.
The native integrator owns landing (`anim 5` + friction), it glues grounded
actors to its own recomputed floor every frame, and both of those must be
explicitly reproduced (at touchdown) or undone (at footprint exit) by the MOD
tick. The ROOFED latch, native-landing publication, exact-footprint support,
and glue-undo fall handoff together make the roof behave as ordinary ground.
Continue from the verified implementation; do not restore the older
ground-query snap, fixed-front ejection, tangential-slide, or padded-footprint
roof responses documented as superseded in the Mod and Experiment notes.
