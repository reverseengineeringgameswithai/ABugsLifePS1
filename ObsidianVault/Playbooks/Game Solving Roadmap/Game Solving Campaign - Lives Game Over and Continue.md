---
kind: campaign
id: lives_gameover_continue
phase: 4
family: player_lifecycle
rows: [C16_lives_gameover]
status: active
evidence: [analysis/phase4_lives_gameover.json, analysis/phase4_lives_death_breadth.json, analysis/phase4_checkpoint_respawn.json, analysis/phase4_c16_frontend_card.json, analysis/phase4_c16_boss_death.json, analysis/phase4_c16_bonus_death.json, analysis/phase4_c16_thumper_death.json, analysis/phase4_c16_thud_boulder_death.json, analysis/phase4_c16_flight_death.json]
---

# Game Solving Campaign - Lives, Game Over, and Title Restart

## Scope and current decision

This active C16 campaign owns resident health/lives death selection, ordinary
respawn, final-life game over, title restart, death-class breadth, frontend/card
interfaces, safe-anchor coupling and stage lifecycle. C15 retains safe-position
capture/consume and broader authored-row/overlay-selector policy, E10
hazard-family policy, E14 native card serialization, E15
FMV playback and E16 generic overlay loading.

The campaign is **not complete**. One natural pristine Bug Bar path and three
single-variable controls now bind the resident final-life, ordinary-respawn,
no-death and title-restart writers. Fresh card-seeded replay corrects the
former Continue label: the fourth Start begins from the title, reaches stage
select, resets nonserialized lives and changes neither the native progress
block nor the isolated card. One LEVEL02 natural/neutral pair adds a second
stage and pit death class. The ordinary Bug Bar respawn now also has a
single-variable safe-anchor-consumption proof. Eight supporting natural damage
leads add four exact ordinary respawns, one exact final-life selection and three
nonfatal boundaries across five scene values. Their exact native producer calls
are bound without assigning hazard or actor identity. The existing Hopper-
showdown pair separately adds one scene-15 boss-context final-life path whose
fatal caller is resident proximity contact. This does not assign the damage to
Hopper or complete D20/F15. The Bonus-3 pair separately adds a scene-3 one-
field proximity-contact death and ordinary respawn without assigning a named
enemy or completing F18. The complete Thumper pair adds a scene-2 natural
health `4 -> 3` attack whose exact call-time `s1` identifies live pool slot 1,
actor id 16, the Thumper callback and authored-record backlink. Changing only
starting health `4 -> 0` makes that same invocation fatal, followed by ordinary
respawn health/lives `4/3`; this is one boss-actor damage path, not D16/F03
completion. The complete Thud pair adds a scene-14 arena path: row 4 is the
sole in-threshold live row at exact overlay call `0x800B4AE0`, and changing only
health `3 -> 0` turns the natural `3 -> 2` contact into health -1/master state 2
while final-life lives remains 0. This is one boss-arena final-life path, not a
new scripted/special/exceptional classification or D18/F09 completion.
The pristine Riverbed Flight anchor adds a scene-8 actor-owned proximity path:
corrected pool slot 5/id 37 owns exact call `0x8004B4A0`; natural death reaches
ordinary respawn health/lives `4/2`, while a one-byte matched response-only
control suppresses all damage/respawn hits at identical frame/cycle/PC/SP.
Type word `0x0125` remains unclassified, so this is not a species, special law,
or C16/F14 completion claim. Scripted/setpiece/exceptional classes, other bonus contexts,
remaining boss/actor ownership, alternate frontend/card effects
and remaining campaign breadth still intersect C16 behavior.

## Reproduced frontier

- centrally pinned v3 movie/state and load-free pristine media inspection;
- exact input segments across all 4,006 frames;
- signed health `0x800A6594`, u8 lives `0x800A65A0`, scene, master-state and
  fade fields;
- exact resident regions for damage/death, scene flow, respawn, scene config
  and gameplay reset;
- natural final-life damage and game-over selector;
- neutral movement control with no damage-region execution;
- a two-megabyte RAM control differing only at lives 0 to 1, selecting health-4
  same-scene respawn and lives 1 to 0;
- equality through movie frame 3662 followed by a fourth-Start causal split:
  the title-screen natural path reaches stage select and scene-config lives 0
  to 5, while Start-removed stays on title with lives 0;
- the E14-owned 336-byte native progress block and freshly seeded isolated card
  remain byte-identical throughout both branches; lives is outside that block;
- exact `0x8004A888`, `0x8005B30C`, `0x8005B348`, and `0x80055550`
  writer attribution plus cycle-neutral fixed-frame coverage; and
- a centrally pinned LEVEL02 pit pair whose natural input changes health/lives
  `3/5` to `4/4`, while neutralizing only frames 57–87 prevents respawn; and
- a C15-owned Bug Bar control where fatal safe-X-only `+4096` changes the first
  completed ordinary respawn X by exactly `+4096` without changing the C16
  health/lives `4/0` result or bounded branch coverage; and
- eight complete, cycle-neutral supporting replays: scene 6 plus scene 3/10/4
  paths execute the exact ordinary call/health/lives writers, while scene 12
  executes the final-life reader and selector after a transient 240-frame
  neutral suffix. Three additional paths stop at nonfatal health boundaries.
  All eight now also retain an exact first link caller into `0x8004A700`:
  proximity `0x8004B4A0` (one), contact walker `0x80058A48` (two), player
  region-code-4 `0x80049740` (one), player region-code-1 `0x800496B0` (three),
  and LEVEL06 overlay `0x800B3E94` (one). No filename-derived hazard kind or
  E10 actor/script owner is promoted; and
- the centrally pinned v1 Hopper-showdown pair in verified scene 15 naturally
  reaches final-life game over. One native proximity-updater invocation at
  `0x8004B4A0 -> 0x8004A700` changes health `0 -> -1` and master state `0 -> 2`
  while lives stays 0, followed by exact resident game-over PCs. Runtime
  Region-A matches neither staged LEVEL05 candidate, so actor/Hopper causation
  and D20/F15 completion are not promoted; and
- the centrally pinned v3 Bonus-3 pair naturally changes health `1 -> 0` in
  verified scene 3. At the exact pre-contact boundary, changing only true
  health 1 to 0 changes one RAM byte; the same proximity call then produces
  health -1/master state 2, and ordinary respawn restores health/lives `4/4`.
  All required resident PCs execute under internally neutral trace controls.
  No named enemy, attack, reward or F18 behavior is promoted.
- the centrally pinned complete Thumper v2 pair in verified scene 2 naturally
  changes health `4 -> 3` at movie frame 2423. Fresh natural and one-field-
  fatal controls both enter `0x8004A700` from `0x8004B4A0` with identical
  arguments and `s1=0x8009FE04`. That live pool-slot-1 record is actor id 16,
  callback `0x8004A0F4`, authored backlink `0x80094A54`; neighboring slot 2 is
  independently id 10/callback `0x8004A180`. Changing only true health `4 -> 0`
  changes one RAM byte, makes the invocation return at health -1/master 2, and
  reaches resident ordinary respawn health/lives `4/3` in scene 2. This binds
  one Thumper-owned attack without completing D16 or F03.
- the centrally pinned complete Thud v1 pair in verified scene 14 naturally
  changes health `3 -> 2` at its row-4 arena contact. Fresh natural and
  one-field-fatal controls both enter `0x8004A700` from `0x800B4AE0`; at entry,
  row 4 alone is inside its squared-distance threshold. Changing only true
  health `3 -> 0` changes one RAM byte and makes the invocation return at health
  -1/master 2 while lives remains 0. This binds one arena final-life path
  without promoting a death class or completing C16, D18, or F09.

## Open binding work

1. Identify remaining hazard and actor/script owners, and reproduce scripted,
   special and exceptional deaths plus other bonus contexts without borrowing
   E10/D20/F15/F18
   completion. The ground-bird-named path is an overlay transition call with
   `a3=3`, not filename proof of bird damage; the scene-15 boss-context path is
   a proximity call, not proof of Hopper damage; the Bonus-3 path is not proof
   of grasshopper or F18 behavior; and the Thumper result bounds only one
   actor-owned proximity attack, not the whole boss encounter.
   The Thud row-4 path is a proven arena contact, not evidence that any open
   scripted/special/exceptional class has been covered.
2. Reproduce explicit native Save/Load, no-card/corrupt-card paths and other
   frontend choices with E14-owned evidence. Do not infer a Continue menu from
   the historical fixture name.
3. Add remaining campaign-stage and transition breadth beyond Bug Bar and the
   five-scene natural death-law join.
4. Retain exceptional frontend refusal/error behavior before promoting C16.

## Guard and handoff

`tools/phase4_lives_gameover.py` regenerates the dedicated artifact from
hash-pinned pristine inputs and an isolated debugger process. Its three
derivatives are transient and deleted. `tools/phase4_lives_death_breadth.py`
separately regenerates the eight-fixture supporting join and deletes its one
neutral-suffix derivative; it also recomputes the pristine direct-call census,
first-entry coverage, stable link-register capture and typed effect boundary.
`tools/phase4_c16_frontend_card.py` uses the declared isolated-card launcher to
recompute the title/start visual boundary, progress-block hashes and zero-byte
card diff; its frame captures and edited movie are transient and deleted.
`tools/phase4_c16_boss_death.py` independently replays the v1 Stage-15 pair,
brackets the first fatal boundary, proves the exact call/return producer and
retains the bounded Region-A mismatch.
`tools/phase4_c16_bonus_death.py` independently replays the v3 Bonus-3 pair,
retains the one-byte health control, exact proximity invocation, internally
neutral resident-PC traces and an exact full-machine suffix/direct terminal.
`tools/phase4_c16_thumper_death.py` independently replays the complete v2
Thumper pair, brackets the natural hit, retains full-RAM one-byte isolation,
and requires both natural and fatal invocations to carry the exact live actor
record before accepting the C16 outcome.
`tools/phase4_c16_thud_boulder_death.py` independently replays the complete
Thud pair, requires row 4 to be the sole live in-threshold row at exact overlay
damage entry, and retains matched natural/final-life outcomes plus the one-byte
health isolation.
`tests/test_phase4_lives_gameover.py` and
`tests/test_phase4_lives_death_breadth.py` plus
`tests/test_phase4_c16_frontend_card.py` plus
`tests/test_phase4_c16_boss_death.py` plus
`tests/test_phase4_c16_bonus_death.py` plus
`tests/test_phase4_c16_thumper_death.py` plus
`tests/test_phase4_c16_thud_boulder_death.py` plus
`tests/test_phase4_c16_flight_death.py` recompute exact
fixture/static/runtime leaves, mutation failures, provenance and the open
coverage decision. `config/phase4_lives_gameover.yaml` is the typed and
MOD-safety contract. The smallest natural regression is declarative in
`tools/scenarios/duckstation/pristine_lives_gameover_continue.yaml`; the new
boss-context boundary is declarative in
`tools/scenarios/duckstation/pristine_hopper_context_final_life.yaml`; the
Bonus-3 control is declarative in
`tools/scenarios/duckstation/pristine_bonus3_contact_death.yaml`.
The actor-owned Thumper control is declarative in
`tools/scenarios/duckstation/pristine_thumper_actor_death.yaml`.
The bounded Thud arena control is declarative in
`tools/scenarios/duckstation/pristine_thud_boulder_final_life.yaml`.
The bounded Riverbed Flight response-only control is declarative in
`tools/scenarios/duckstation/pristine_riverbed_flight_actor37_death.yaml`.

Original facts: [[SYS_lives_gameover_continue]]. Runtime method and rejected
hypotheses: [[EXP_2026-07-16_phase4_lives_gameover_continue]]. No MOD-private
state, hook, cave or intended behavior was added.

## Iteration 34 — unclassified Riverbed Flight contact

After the required 110-file Phase-4 / 147-file broader movie census, this
campaign reused pristine `level_14.sav` and requested no operator fixture.
Fresh exact-call and passive traces bind corrected pool slot 5/id 37/callback
`0x80049E88`/source `0x80094AC4` to one ordinary proximity death. Natural
health/lives `0/3` reaches `-1/3`, then resident respawn `4/2`; a matched
one-byte response-only control records zero damage/respawn hits without
frame/cycle/PC/SP drift. The earlier-anchor version of that control is rejected
because native update overwrites it before contact.

This expands C16 into one special-stage context but promotes no distinct death
class or actor species and leaves F14 chase/motion/objective/transition open.
Artifact SHA-256 is
`bfa593ae8c2620fadbe52e46ce01ac5949087fa1e35744611e74afd457ad4114`.

The same iteration's source-fresh reconciliation replayed the mechanics-bound
Bonus-3, Stage-15 and Thumper artifacts. Current SHA-256 values are
`18a26655f057f3c0d3ca4f907af58c6c5a79d73ab061cc1916fe3729174df001`,
`b91cc806bc8c8c66a821aad00990b6a1e91315a42406dc0348e00455f0eb6269`
and `4c93ea7ade277365e2ee3d8cfe07e7f801e2381abeffbf14f3bc2cc6ef70a6aa`.
Two diagnostic Bonus-3 attempts and the final retained run supersede the old
one-cycle suffix difference: full RAM, registers, cycle, PC/SP, emulator frame
and typed lifecycle are now bit-identical to the direct terminal. Final configs
`/tmp/abl-phase4-i34-refresh-bonus3.sxu45D`,
`/tmp/abl-phase4-i34-refresh-boss.dz7S2e` and
`/tmp/abl-phase4-i34-refresh-thumper.67cPbF` stopped only owned PIDs
2744979/2745071/2745199.
