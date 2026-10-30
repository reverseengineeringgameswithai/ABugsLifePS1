---
type: experiment
status: complete
date: 2026-08-03
system: stage completion / Birdnest bird boss
phase: 4
artifacts:
  - analysis/phase4_f06_birdnest.json
  - analysis/phase4_d17_bird.json
  - movies/Phase4/Interpreter/D17_Goldberry.movie.json
---

# Phase 4 F06 Birdnest — synthesized from D17_bird, plus one results-screen discrepancy noted

## Question

F06_birdnest was `unresolved`, its own entire content a stub: one scene-binding line and a
literal `"See D17 bird"` pointer, with `missing: Boss/objective` and `next: Same as D17 —
bird state machine from the movie replay`. Following the exact same pattern that just
worked for F15_canyon_showdown/D20_hopper, the natural move was to check how much of this
row's own stated need D17_bird already answers before doing anything new.

## Synthesis from D17

D17_bird turned out to be an even richer donor than D20_hopper was for F15 — it's already
a `partial` row covering the Birdnest boss fight end to end, using operator-recorded
fixtures that already reach the level-complete results screen:

- **Scene identity confirmed**: all three of D17's own fixtures read `scene_id=11`,
  matching campaign-progression ordinal "Level 6" — this row's own subject exactly.
- **Two bird manifestations**: a scripted setpiece flyby (pure flight, no player
  interaction) and a separate combat actor (`id=30`, max hp 50) that circles at fixed
  altitude while undamaged. Whether these are the same sequence back to back is D17's own
  stated hypothesis, not confirmed — inherited here as open, not resolved.
- **The full fight, answering this row's own "Boss/objective"**: the bird attacks Flik
  early; a gold berry launches it higher (confirmed at the exact operator-named frame); a
  mega homing-berry seed plant fires automatically at the airborne bird (not a direct
  throw), draining hp in a steady ~-4/hit staircase; the bird descends and becomes
  vulnerable again; defeat is a **threshold state** (hp freezes around 18-22, never reaches
  0) with a `vm_ip` jump to a generic park/loop primitive — cross-verified almost frame-exact
  against the operator's own precise annotations.
- **Retreat confirmed**: after defeat, the bird's Y climbs further (not descends), matching
  the operator's own "retreating" description.

None of this needed re-proving — cited directly from `analysis/phase4_d17_bird.json`.

## One new check: what do the results-screen counters mean?

D17's own `STILL_OPEN` named this directly: *"what the unlabeled '0/4' and '00/09'
results-screen counters represent."* Cheap to check with the tooling still fresh from the
F15/Hopper 100%-run investigation earlier this session — loaded `D17_Goldberry.movie.json`
(already reaches the results screen per D17's own notes), advanced to mf5600, captured a
screenshot.

**Result**: `level complete / 00/50 / 0/4 / 00/09` — the exact same three-counter layout
already established for F15's own results screen (grain / FLIK letters / seed tokens).
This closes D17's own open question: `0/4` is FLIK-letter progress, `00/09` is this level's
own seed-token total (9 — different from Hopper's stage-15 target of 16, confirming
seed-token targets are level-specific).

**A discrepancy surfaced, not resolved.** The displayed grain count read `00`, while a raw
memory poll of `0x800a65a1` at a similar frame showed 29. Two hypotheses, neither chosen
between: the results-screen digits might animate/count up from 0 (this game's other HUD
counters are documented elsewhere as pulse-animated) and mf5600 was sampled too early; or
the results screen shows a per-visit delta rather than the raw cumulative counter, and this
particular recording happened to collect zero additional grain before reaching the boss.
Flagged honestly as unresolved rather than guessed at.

## The 100% run: a new cutscene found, the grain discrepancy partially resolved (2026-08-03)

Operator: *"done in 100% folder"* — following up on the earlier "similar to level15 do you
need a 100% run of bird's nest?" exchange. `movies/Phase4/Interpreter/100% Runs/
LEVEL06.movie.json`, 12,917 frames, format v4, anchored on `LEVEL06.movie.sav`.

**Method.** A coarse 11-point survey located the collection/transition/tail regions via
grain, FLIK bits, and `scene_id`; a finer sweep (pi7600–12800) pinned the exact transition
boundaries.

**Full timeline.** Grain and FLIK letters both reach full (50, 4/4) by pi~7600, still
inside `scene_id=11` — ordinary collection during play. `scene_id` flips to 0 between
pi8600–8800, exactly where the already-known `"level complete / 00/50 / 0/4 / 00/09"`
banner appears (re-confirmed via screenshot, identical to the prior pass's finding). The
banner **persists with the same static zero values through at least pi9600** — 800 frames
(13+ real seconds) after first appearing, with grain and FLIK both genuinely at 100% in raw
memory the whole time. `scene_id` then flips back to 11 between pi9600–9800 — not a return
to free-roam gameplay, but a **scripted cutscene continuing within the Birdnest scene
context**: a shot of a bug (fly/beetle-like) upside down in a spotlight against a
purple-lit backdrop (pi~11000), then a nighttime ambient establishing shot with a glowing
object and blue moonlight beams (pi~12200) — genuinely new content, never captured by any
prior fixture for this row. `scene_id` flips to 0 again (pi12400–12600, a fade to black),
and the movie's own tail lands on the already-established **Flik's Journey** hub, exactly
matching the operator's own prior description — "bird nest" shown as the currently-selected
level in the carousel.

**The grain discrepancy: partially resolved.** The prior pass's two hypotheses can now be
adjudicated. **Per-visit delta is refuted** — a genuine 100% collection run (50/50 grain,
4/4 FLIK confirmed in raw memory) still displays `00/50` and `0/4`, ruling out "it shows
what you collected this visit." **Count-up animation is weakened but not cleanly ruled
out** — the banner was checked 800 frames after first appearing and still showed static
zeros, a long time for a typical animation to remain unresolved, though not impossible if
it's gated on a button press rather than elapsed time (never given in this poll-only
check). New leading hypothesis, not yet confirmed: this specific banner may not be a real,
wired-up per-level tally at all — unlike Hopper's own results screen (a fight-focused,
non-100% run) which showed a real, apparently-accurate `10/50`, Birdnest's shows static
zeros across two independent fixtures at two different real collection states (29-raw and
50-raw grain). A genuine, documented behavioral difference between the final-stage results
screen and an ordinary-stage one — not yet explained at the instruction level.

## Operator clarifies the cutscene's own trigger condition (2026-08-03)

Operator, directly, correcting the "whether it's present on non-100% completions or gated
specifically on 100% collection" question the prior section left open: *"The new cutscenes
happen when a first 100% completion occurs after the level. If it's the first time entering
a level, another FMV starts before entering the level. No FMV starts if it's any%."*

This closes that question cleanly: the bug-in-spotlight / night-ambient cutscene is a
**first-time-100%-completion reward FMV**, not a generic post-fight element — which is
exactly why `D17_Goldberry.movie.json` (an any%-style fixture, only 29/50 raw grain) never
showed it. It also surfaces a **separate, previously-undocumented fact**: a distinct FMV
plays before a level's first-ever entry (not its completion) — not yet captured in any
fixture for this row, a new standalone residual rather than the same mechanism.

With the cutscene's own trigger now understood independently, it's clearer that the
results banner's own static-zero display and the cutscene's appearance are **two decoupled
events**, not one continuous sequence that happened to be observed together — the banner's
own quirk remains open on its own terms, not explained by the 100%-gating logic that
governs the cutscene.

## Residuals

The exact reason the Birdnest results banner shows static zeros while Hopper's showed real
numbers (not traced to the instruction level); whether all non-final-stage results banners
behave this way (only Birdnest tested); which game system renders the newly-found cutscene
(not traced to source); Birdnest's own level-entry FMV (operator-confirmed to exist,
distinct from the completion cutscene, not yet captured in any fixture); whether the
scripted flyby and the `id30` combat phase are truly one sequence (inherited from D17);
which telescope ordinal maps to the bird's own waypoint record (inherited); the
shooter-plant's exact per-hit damage instruction and the mega-homing-berry plant's own
mechanism (inherited, entirely unexamined); whether re-engage is possible; source closure;
cross-system audio/HUD; no dedicated Canon page created, matching the thin-stub pattern the
other F-rows use.

## Stopping point, justified (2026-08-03)

Operator asked directly whether to keep drilling or move on. Triaged the remaining
residuals rather than treating them as uniformly open:

**Not worth chasing further right now** — decorative/non-blocking, doesn't change
understanding of the mechanics: why the results banner shows static zeros regardless of
real collection state; which specific system renders the newly-found cutscene; whether
other non-final stages show the same banner behavior. These would need instruction-level
tracing for a payoff that's cosmetic, not mechanical.

**Needs a fixture this row doesn't have, not answerable from existing evidence**:
Birdnest's own level-entry FMV (would need a from-boot or fresh-save capture of this
level's first-ever entry — operator-confirmed to exist, never captured); whether re-engage
(a second fight in one session) is possible.

**One genuinely promising lead, flagged but not chased**: the mega homing-berry seed
plant's own mechanism is completely unexamined — D17 only ever inferred its existence from
what it does to the bird, never traced the plant itself (planting, activation, auto-fire
targeting). This project already has fully-closed rows for yellow/purple/green/blue/brown
seed plants (see the relevant `*-seed-plants-solved` memory/Canon material). There's a real
chance the homing-berry plant is a variant already covered by one of those campaigns, which
would make it a cheap synthesis win rather than fresh investigation — worth checking first
if this row is picked up again, before assuming new live work is needed.

**Assessment**: F06_birdnest remains `partial` after three passes but has moved
substantially — most of the boss mechanics closed via direct synthesis from D17_bird, the
operator-supplied 100% run both closed one hypothesis on the grain discrepancy and surfaced
a genuine new discovery (the mid-level cutscene), and the operator's own direct
clarification closed the cutscene's trigger condition cleanly. Not claimed solved — the
grain-display difference from Hopper's own screen and the cutscene's own visual meaning
remain open, honestly reported rather than resolved. Stopping here is a deliberate choice
(operator-confirmed), not an assumption that nothing remains — the highest-value unexplored
thread if this row is revisited is the homing-berry plant's possible overlap with an
already-solved seed-plant row.
