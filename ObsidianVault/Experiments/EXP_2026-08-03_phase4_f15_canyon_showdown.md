---
type: experiment
status: complete
date: 2026-08-03
system: stage completion / Hopper canyon showdown
phase: 4
artifacts:
  - analysis/phase4_f15_canyon_showdown.json
  - ObsidianVault/Canon/Functions/FUNC_800502C4_fmv_sequence_completion_check.md
  - analysis/phase4_d20_hopper.json
  - movies/Phase4/Interpreter/D20.movie.json
---

# Phase 4 F15 Canyon Showdown — synthesized from D20, plus a new ending-cutscene discovery

## Question

F15_canyon_showdown was `unresolved`, its own entire content a stub: one scene-binding
line and a literal `"See D20 Hopper"` pointer, with `missing: Multi-area boss/chase/ending
mechanics` and `next: Same as D20 — barrier state writes + finale trigger from the hopper
movies`. D20_hopper had just closed out a nine-pass session covering exactly that —
identity, the 3-section structure, both literal gates, the real health bar, and the
defeat-trigger caller. Rather than starting F15 from scratch, the natural first move was to
check how much of its own stated need this already satisfies, and whether anything
genuinely NEW was still open.

## Synthesis from D20

Nearly everything F15's own `missing` field named is already covered:

- **Multi-area structure**: the operator's own 3 sections (health-drain encounter,
  post-hit patrol/chase, mountain climb) are structurally confirmed and located in
  `D20.movie.json`, including the two literal wooden-barrier transition markers Hopper
  himself breaks through.
- **Chase mechanics**: confirmed to run on the same shared, already-documented mover-VM
  chase gate every regular enemy uses.
- **Boss/ending**: the real on-screen health bar (`0x800b4ba8`) and the exact
  defeat-trigger caller (`fmv_sequence_completion_check`, `0x800502C4`) are both closed.

None of this needed re-proving — it's cited directly from `analysis/phase4_d20_hopper.json`
into F15's own bindings. See `SYNTHESIS_FROM_D20_2026-08-03` in the new
`analysis/phase4_f15_canyon_showdown.json` for the exact cross-references.

## The one genuinely open piece: the ending

F15's own `fixture_need` asked for "a Full-showdown movie through the ending FMV."
`D20.movie.json` reaches the level-complete results screen (~mf16700) but its own recorded
input stream ends there, 16,711 frames total, only 11 frames past the results screen
appearing — nothing was ever known to happen after that point, because no fixture had
input recorded past it.

Rather than requiring a brand-new recording, this was cheap to check directly: load
`D20.movie.json` (`load_start_state:true`), advance to the results screen, then **stop**
movie playback and drive input live via `emulator.pressButton` past where the recording's
own input ends.

**Result: a genuine, previously-uncaptured ending cutscene exists.** The screen fades to
black on the first Cross press (not a crash — PC keeps advancing through normal-looking
code across every subsequent capture), then resolves into a letterboxed, multi-shot
cinematic that runs for at least ~5,000 frames (sampled from absolute frame 37465 through
42065+, still mid-sequence when this pass stopped):

1. A circus caravan/wagon surrounded by a crowd of tiny figures on the ground.
2. A close-up of an ant's head peering down through a gap in rock/bark.
3. A caterpillar-like creature resting in grass.
4. An ant colony walking through grass and low plants.
5. A wide nature shot of a tree root and grassy anthill.

This reads as the film's own actual ending beats (the circus troupe, an ant colony at
peace, nature imagery) rendered as the game's finale. `scene_id` (`0x80082504`) stays at
15 throughout the observed portion — the cutscene plays inside the same scene context as
the fight, not a dedicated post-game scene. Every sampled PC during the sequence is a
normal game-code address (`0x8006xxxx`/`0x800bxxxx`), not an obviously MDEC/STR-streaming
range — consistent with an **in-engine rendered** cutscene (matching the already-documented
bird-eats-Hopper setpiece pattern, `FUNC_8004DD98`) rather than a compressed video file, but
this was NOT independently confirmed against `SYS_fmv_player_streaming.md`'s own
MDEC-detection method — flagged as a residual, not claimed.

`FUNC_800502C4_fmv_sequence_completion_check.md` already statically documented (from an
earlier, purely static-inference pass) that this function calls `fmv_bin_load(41)` on
completion. That's consistent with — though not independently re-confirmed as the exact
mechanism behind — the cutscene found here. Updated that page with a live-confirmation note
cross-linking to this experiment.

## The ending, fully mapped (2026-08-03, operator-supplied 100% run)

Operator: *"a 100% run is recorded in Interpreter/100% -- it's a long movie."*
`movies/Phase4/Interpreter/100% Runs/LEVEL15.movie.json`, 76,310 frames (~21 real minutes),
format v4, anchored on `LEVEL15.movie.sav`. This closes the two biggest residuals from the
pass above in one shot: how the ending concludes, and whether the level's own non-boss
content was ever actually explored (this run collects everything — grain hits 50/50 and all
4 FLIK letters by movie-relative frame ~60000, versus `D20.movie.json`'s own 10/50 grain and
2/4 FLIK on a fight-focused run that barely touched the rest of the level).

**Method.** A coarse 10-point survey across the full 76,310 frames located the fight,
transition, and tail regions via grain count, FLIK bits, and `scene_id`. A finer sweep
(500–1000 frame steps, mf60500–mf75000) then pinned the exact `scene_id` transition to
between mf67000 and mf68000.

**Full timeline, confirmed:**

1. Grain and FLIK letters reach full (50/50, 4/4) by mf~60000 — `scene_id` still 15,
   collection happens during ordinary play, not some special end-state.
2. The already-known ending cutscene starts around mf60500, with MORE shots than the
   earlier D20.movie.json-derived probe found: a bird's nest with three baby birds
   (mf60500 — a narrative payoff, since a mother bird is what carries Hopper off in the
   already-Canon bird-eats-Hopper cinematic) and a wide circus-troupe farewell shot
   (mf64000 — the caterpillar carried by two ants with a flying insect overhead, matching
   the film's own ending beats).
3. `scene_id` stays 15 through at least mf67000, then flips to 0 by mf68000 — **exactly**
   where the screen changes to a literal **"Congratulations! Game Complete"** title card
   (Flik pictured, hands on hips).
4. This is followed by `scene_id=0` for the entire remaining tail: a genuine **scrolling
   end-credits sequence** (confirmed at mf70000: "character animation - jeremy pardon, dave
   burton" / "character artwork - neil allen, dave burton, bev bush, jeremy pardon, will
   thompson"), continuing through the movie's own final recorded frame (mf76309), which
   lands on a **"do you want to save?"** prompt featuring Tuck & Roll with yes/no options —
   the game's standard end-of-session save dialog.

**Conclusion.** This closes "how does it conclude" definitively: cutscene → "Congratulations!
Game Complete" → scrolling end credits → save prompt. This is strong (not airtight, but far
more confident than before) evidence that Stage 15/Hopper genuinely IS the final level of
the game — a literal "Game Complete" screen and a full credits roll are hallmarks of
whole-game completion, not an ordinary per-level transition. No other stage's own
completion was checked for comparison this pass, so "unique to the final stage" is inferred
from the content itself rather than independently disproven for other stages.

**Still not determined**: whether the credits sequence itself is in-engine or compressed
video (not tested); the full credits roll content beyond the 2 sampled screens; what
happens after choosing yes/no at the save prompt (the movie's own recording ends exactly
there); independent confirmation (vs. inference from content) that this is unique to the
final stage.

## Two residuals closed by the operator directly (2026-08-03)

Operator: *"that doesn't matter. fmv is mostly solved i think and the past save-prompt is
just the Flik's Journey, no different from any other level."*

- **FMV-vs-in-engine identity**: retracted as an open question for this row — already
  substantially handled elsewhere in the project (`SYS_fmv_player_streaming.md` and
  related pages), not something F15 needs to re-litigate.
- **Post-save-prompt destination**: confirmed as `Flik's Journey`, the game's standard
  post-level hub/level-select screen — the SAME destination any other level's completion
  reaches, not something stage-15-specific. This nuances rather than contradicts the
  "final level" conclusion: the destination *after* saving is generic, but the Game-Complete
  title card and credits roll *before* it remain the stage-15-specific content.

## Residuals

Independent confirmation that the Game-Complete/credits sequence is unique to the final
stage rather than a generic per-level flow (no comparison stage checked — operator has
deprioritized this, not required for closure); the full credits roll content beyond the 2
sampled screens; the barrier/gate-break opcode (a shared open residual with D20_hopper, not
re-investigated here); stage-specific hazards or content outside the boss encounter itself
proper (not investigated — both passes on this row and the D20 work they draw on were
entirely boss-fight/ending-focused); source closure; no dedicated Canon page created for
this row, matching the existing thin-stub pattern already used by the other F-rows that
point at a D-row (F06→D17, F12→D19).

**Assessment**: F15_canyon_showdown remains `partial` but is now considered bounded — the
multi-area/boss/chase mechanics its own `missing` field originally named are covered via
direct synthesis from D20_hopper, the entire ending sequence is mapped end to end (cutscene
→ title card → credits → save prompt → Flik's Journey), and the operator has directly
closed the two smallest remaining sub-questions as non-issues. What's left (stage-15
uniqueness independent confirmation, full credits content, stage hazards outside the boss
fight, source closure) is lower-priority last-mile material, not blocking anything.
