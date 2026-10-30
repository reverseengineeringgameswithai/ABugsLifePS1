---
type: experiment
status: complete
date: 2026-08-02
system: enemy AI / D09 cockroach identity
phase: 4
artifacts:
  - analysis/phase4_d09_redbug_identity.json
  - tests/test_phase4_d09_redbug_identity.py
---

# Phase 4 D09 ("cockroach") identity, damage, and death re-verification

## Question

Does D09_cockroaches' banked identity/damage/death finding hold up to a fresh,
independent replay, and does it satisfy the roadmap's Definition of Done for a solved
subsystem? (Asked directly by the operator, skeptical of an earlier "closed out"
characterization.)

## Provenance

- Authority: hash-verified pristine retail `SCUS-94288`; ALLMODS was not used.
- Movie: `movies/Phase4/D09_cockroach_contact_kill.movie.json`, recorded 2026-07-15,
  SHA-256 `9f4b295f2f92d6d08f1004011c239b0b229e011c58963289c9e1be5a6608faef`.
- Start-state: `movies/Phase4/D09_cockroach_contact_kill.movie.sav`, SHA-256
  `976969f3c996df5d090deb162d67f483c2224d2fafac922b5b4e353758179d88`. The movie's own
  embedded `start_state.sha256` is `null` (a known format gap); these hashes were
  computed independently and were absent from the original artifact.
- Movie metadata: `movie_version: 3`, `armed_while_paused: false`,
  `phase_delay_owed: false` — not flagged by the fork as one-frame-early.
- Isolated instance: config `/tmp/duckstation-debugger-d09-verify`, port `23495`,
  never the operator's own; stopped via the launcher at the end.

## Method

Replayed the fixture fresh rather than re-asserting the prior claims. Caught a real
methodology bug on the first attempt: `movie.startPlayback` with no params defaults
`load_start_state` to `false`, so the recorded input played against whatever state the
fresh boot happened to be in — `movie.status.reproducible` correctly read `false`,
which is what caught it. Corrected by always passing `{"load_start_state": true}`,
confirmed by `reproducible: true` and `debugger.status.frame == start_state.frame`
(141130) after each load.

Identified the actor deterministically this time: `readMemory` on the live-enemy
pointer table `0x80090748` gives `u32[0] = 0x800A095C`; reading the 0x84-byte record
there gives `id/hp/flags/vm_ip`. This replaces the original proximity heuristic with a
direct lookup — same actor, same address, confirmed by matching values.

Sampled `id/hp/ai_flags/vm_ip` at frames 436, 437, 493, and 583 (movie end) via
`movie.advanceToFrame` (never `debugger.resume` before it — an earlier attempt within
this same session let the emulator free-run past the target frame first, producing an
`RpcError -32006` rewind-rejection on the next `advanceToFrame` call).

For the post-recording kill: stopped movie playback at frame 583, `emulator.pressButton`
(square, one throw), then sampled every 10 frames via `emulator.advanceFrames` out to
+80 frames, then read the permanent-kill quota `0x800A658E` before the throw and again
after +360 further frames.

## Result

**Reconfirmed exactly:** identity (actor id 19, "Redbug"), HP at frame 437 (4) and 493
(2), the mover-VM instruction pointer (`0x800776A4`, program index 12), and HP=2 still
at frame 583 (movie end, matching the original claim precisely).

**One claim corrected:** the CHASE aggro bit (`flags+0x5c` bit `0x2`) is already set at
frame 437, i.e. it flips on the FIRST berry hit, not the second as originally banked
(frame 436: `0x4041`; frame 437: `0x4043`; frame 493: unchanged `0x4043`, only HP moves).
The underlying claim — berry damage triggers CHASE aggro for this species — still
holds; only which hit triggered it was wrong.

**One genuine refinement, not a contradiction:** death is two-stage. HP reads `999`
(the established dead sentinel) from roughly +20 to +60 frames after the kill-shot,
then the record clears to HP `0` (flags top nibble also clears, `0x48c1 -> 0x08c1`)
by +70 frames. The original artifact's "999" and this session's first quick single-sample
check ("0") were each correct for the instant they happened to sample — not a conflict,
once sampled densely enough to see both stages.

**One new, unresolved contradiction:** the permanent-kill quota `0x800A658E` read `23`
immediately before the extra kill and stayed `23` through 360 more frames afterward —
it did not increment for this kill. The original artifact reported "23 after the kill"
as though that number meant something; it does not, on its own, confirm the quota
tracks this kill at all. Not explained — named as open.

**Net effect on Phase-4-DoD status:** unchanged. This row was already `partial` in
`analysis/mechanics_baseline.yaml` and was never marked `solved`; the corrections here
tighten the evidence but do not close any of the 9 DoD items. See the artifact's
`DOD_SCORECARD_2026-08-02` block for the item-by-item accounting — 0 of 9 met.

## Reproduction

```bash
python3 -m pytest -q tests/test_phase4_d09_redbug_identity.py
```

The live portions (frame-by-frame HP/flags reconfirmation and the post-recording kill)
require a fresh isolated instance and are not scripted into a single runnable tool yet
— that gap is itself part of why DoD item 1 (original oracle) is not met.

## Follow-up 2026-08-02: operator-prompted aggro/chase live test

The operator explained the quota non-increment (blue damage doesn't spend the gold-kill
quota — expected, already documented in `SYS_enemy_death_and_permanence.md`, which this
investigation should have checked before calling it an open contradiction) and, separately,
was skeptical this species has real chase behavior: "I don't think this enemy has an
aggro mode, you can try to move Flik into its vicinity and throw a berry at it."

Second isolated instance, port `23496`, config `/tmp/duckstation-debugger-d09-aggro`,
stopped via the launcher at the end.

**New finding**: the CHASE flag (`flags+0x5c` bit `0x2`) is transient, not permanent —
later observed cleared (`0x5040`/`0x5041`) with a new, unidentified bit `0x1000` set
instead.

**Attempted a direct movement-correlation test, not cleanly resolved.** Manual analog
navigation was unreliable (apparent character-relative controls; no facing/camera readout
used to compensate — displacement direction for the same stick input changed between
attempts). Switched to direct position pokes. Caught and fixed a bug along the way:
writing `pos` alone let the game's own per-tick `pos = prev + velocity` integrator snap
Flik back within one frame — fixed by writing `pos`, `prev_pos`, and zeroed velocity
together (`scatterWrite`, atomic). One placement copied the Redbug's own Y and produced
valid nearby positions (dist 400–8825 units), but that observation window was contaminated
by residual analog input left over from earlier navigation attempts (controller state was
not re-cleared immediately before the poke). A later, deliberately clean attempt (input
cleared and confirmed zero immediately before writing) used Flik's own last Y at a
different XZ — invalid there, and Flik entered freefall (Y climbing from 1029 to 84997
over 60 frames). Stopped and recovered via a clean `movie.startPlayback` +
`load_start_state:true` reload before any crash.

**What the cleanest available data shows**: in the least-contaminated window (dist
400→19375 over ~80 frames, Redbug's own Y, but the CHASE flag had already expired by this
point per the finding above), distance to Flik *increased*, not decreased. Elsewhere in
the session the actor sat completely motionless for 240- and 540-frame stretches
(4–9 seconds), including at least one stretch with the CHASE flag actively set. No window
combined "CHASE flag freshly set" + "Flik verified stationary on valid ground" + "close
range" all at once.

**Honest conclusion**: NOT CONFIRMED either way. The evidence leans toward supporting the
operator's skepticism (long freezes regardless of flag state, one clean-ish window showing
increasing rather than decreasing distance, no directed approach observed anywhere in
~1500+ frames across both sessions) but does not establish it — a genuinely clean test
(fresh hit, verified-stationary Flik on validated ground, close range, watched through the
flag's full window) was not achieved. `SYS_enemy_ai.md`'s "confirmed live: taking berry
damage triggers chase aggro" is downgraded accordingly.

## Follow-up 2026-08-02: aggro/chase CONFIRMED (operator: "go forward with it, exhaust it")

Third isolated instance, port `23497`, config `/tmp/duckstation-debugger-d09-aggro2`,
stopped via the launcher at the end.

**Method fix**: stopped moving Flik entirely — every failure above (freefall, the
mysterious snap-back, contamination) traced back to touching player state. Moved the
**Redbug** next to Flik's own already-valid position instead: no ground-height risk, no
snap-back, and Flik's position was never written to, so any subsequent movement is
entirely the enemy's own. First tried the "obvious" fix — call `ground_height_query`
(`0x80037A38`) directly via `debugger.callFunction` to place Flik precisely — but a blind
call (`a0`=x, `a1`=z as raw scalars) hung and corrupted the guest (`sp` became
`0x000085c0`, `pc` landed in BIOS): the function almost certainly needs a sector/plane
pointer this call didn't supply (per `SYS_player_power_slot.md`'s own note that this
function's residual accesses are "plane-record pointers loaded from the sector table").
Abandoned rather than guess further; recovered via a clean `load_start_state:true` reload.

**Three trials.** Placed the Redbug ~500 units from Flik (its own Y, velocity zeroed via
atomic `scatterWrite`), then threw berries and watched for 200-350 frames per trial instead
of the 60-90 used before.

- **Trial 1 (hit)**: connected at dist 44869 (HP 6→4, flags→`0x4043`). ~60 frames of
  continued outbound momentum (44869→50306), THEN a clean ~100-frame accelerating approach
  straight at Flik (49968→46127→39202→29395→18927; `vx` climbed +200→+1058 in Flik's exact
  direction the whole time). Flag cleared once within ~11-15k units, approach stopped.
- **Trial 2 (miss, control)**: throw at dist 42670 did NOT connect — HP and flags never
  changed across 200 frames. Movement was plain undirected wander (42670→80936→76900,
  no sustained direction). This is the clean no-flag baseline the earlier attempt lacked.
- **Trial 3 (hit)**: connected at dist 64900 (HP 4→2, flags→`0x5043`). Same two-phase shape:
  ~40 frames outbound (64900→80667), then a ~200-frame accelerating approach
  (80667→...→21094, `vx`→~1000 toward Flik) — this time the CHASE flag stayed set through
  the approach AND the subsequent reversal (19524→47487), unlike trial 1 where the flag
  cleared when the approach stopped.

**Conclusion: CONFIRMED.** Taking berry damage does trigger real, directional pursuit
toward Flik — reproduced on 2 of 2 landed hits, absent on the 1 miss. The movement pattern
is an **approach/retreat stand-off oscillation** (close fast to roughly 11-22k units, then
reverse), not a monotonic charge to contact, and not always exactly the same
(flag-clears-on-approach in trial 1 vs. stays-set in trial 3 — unexplained). This
**supersedes** the earlier "NOT CONFIRMED" finding above, which is kept rather than
deleted: its 60-90 frame windows never ran past the ~40-100 frame outbound-momentum delay
this pass discovered, so it was reading the wrong phase of the cycle as "no chase" — a
real methodological lesson (short observation windows can invert a delayed-onset behavior
into its opposite), not just a fact correction.

## Follow-up 2026-08-02: audit — is the chase finding itself solid?

Operator: "do another audit to see if we truly exhausted the cockroach row." Rather than
re-assert, checked the confirmed-chase trials for gaps. Found one real one: none of the
three trials logged `vm_ip`, so the chase conclusion had never been cross-checked against
the Redbug's own disassembled mover-VM program.

Reading `analysis/vm_programs.md`'s `redbug @ 0x80077690` listing: the program's own
`flags_mask` instructions only ever touch **bit `0x4`**, never bit `0x2` (the CHASE bit
tracked throughout this row) — so bit `0x2` must be set by code outside this program (the
damage handler), consistent with the pre-existing Canon note that the interpreter "hands
off to the phase-2 motion-apply `vm_motion_apply_chase`." This mattered because it's the
one plausible way the "chase" conclusion could have been an artifact: if the observed
movement were actually the program's own `park_seek`/wander logic (e.g. drifting back
toward some internal anchor) that just happened to point toward Flik twice by coincidence,
that would invalidate the finding.

Fourth isolated instance, port `23498`, config `/tmp/duckstation-debugger-d09-audit`,
stopped via the launcher at the end. Repeated trial 1's setup, this time sampling `vm_ip`
every 10 frames through a complete hit → approach → disengage cycle (hit at dist ~43307,
approach down to dist 10871 where the flag cleared and velocity reversed). `vm_ip` read
`0x800776A4` — the program's very first `park_seek`, inside its first wander loop — at
**every single sample**. It never advanced to the program's own `chase_radius_scratch` at
`0x800776FE`.

**This rules out the coincidence-with-program-internal-wander confound**: the program's IP
structurally never reached that code path during the chase, so the movement cannot be that
opcode's own scripted behavior. It must be the separate global override
(`vm_motion_apply_chase`), which — per the architecture note already in Canon before this
row's work began — explicitly targets Flik's live position. This is a fourth independent
hit-trial showing the same approach pattern, and it strengthens the CONFIRMED conclusion
rather than undermining it.

**Not closed by the audit**: `vm_motion_apply_chase` (`0x8004C8AC`) itself was not traced
directly — no `execTrace` was armed (poll-only throughout, this fixture's movie predates
the Interpreter-safety discovery). The attribution to that function is architectural
inference (the existing Canon description) plus a negative result (IP never advances), not
a direct instruction-level trace of it executing.

**Row-level audit verdict**: the aggro/chase question specifically is now well-settled —
4 independent hit-trials (2 in the second attempt, 1 miss-control, 1 more in this audit)
all consistent, plus this architectural cross-check ruling out the main plausible
confound. The ROW as a whole is nowhere near DoD-exhausted: `DOD_SCORECARD_2026-08-02`
still reads 0 of 9 items met, with items 2 (frontier), 5 (interfaces), 6 (campaign
breadth), and 8 (source closure) not started at all. "Exhausted" is accurate only for the
specific aggro question asked; it is not accurate for the row.

## Respawn test — later same day, RETRACTED

Killed a Redbug (temporary KO) and watched 4000 frames with Flik stationary: hp stayed 0,
banked as "no in-session respawn". **Retracted** after the operator supplied direct
gameplay knowledge — enemies come back, but only after the player actually leaves and
returns, not while standing nearby. A live re-test with Flik genuinely walking away (real
controller input, not a position poke) far enough confirmed a full reset: hp back to 6, id
stayed 19. Position pokes (single teleport, a "real"-delta teleport, many small per-frame
increments) never reproduced it — only continuous real execution with real input did. The
mechanism was ASM-traced under D12 to a previously-undocumented reinstantiate-from-spawn-
template routine (`0x80049C2C`) sitting immediately adjacent to, and merged by the
debugger's own `functionBounds` into, the unrelated, already-documented `FUNC_800498AC` —
full trace, including two unresolved open questions (the routine's exact trigger, and a
contradiction in a distance-based admission check found nearby), in
`analysis/phase4_d12_worm_id40.json`'s `RESPAWN_MECHANISM_2026-08-02` and
`SYS_enemy_death_and_permanence.md`.

## Residuals

No scripted oracle exists for this row (item 1) — the confirmed chase cycle was produced
by unrecorded manual play across all four trials. No frontier/interface/lifecycle/
campaign-breadth/source-closure work has been done (items 2, 4, 5, 6, 8). Variants,
immunity specifics, the meaning of flags bit `0x1000`, why the flag-clear-on-approach is
inconsistent between trials, whether contact range is ever reached, `ground_height_query`'s
real calling convention, a direct trace of `vm_motion_apply_chase` itself, and the two open
questions in the respawn mechanism above all remain open.
