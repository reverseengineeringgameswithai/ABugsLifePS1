# Finding: the closure ledger reports ~0 movies for stage rows that have dozens

**Date:** 2026-08-11 · **Status:** finding, offline, measured. Promotes nothing, changes
no status, edits no registry.

---

## The measurement

For the 19 F (stage) rows:

| source | movies |
|---|---:|
| `analysis/phase4_closure_debt.json` `movie_count`, summed over all 19 rows | **3** |
| centrally pinned movies whose filename names the row's stage | **87** |

Fifteen rows report `movie_count: 0` while holding between 3 and 17 pinned,
byte-matching movies each. F02 alone has **17**.

⚠️ **Caveat on my own count.** I derived the stage tag from the row's `stages` field,
which holds the stage *ordinal*. Four rows do not parse under that rule — F10 (its
`stages` was corrected to prose, "scene 7 (disc level07)") and the three bonus rows
(`stages: bonus`, and their movies are named `Bonus_Level_0N`). For those four my count
of 0 is a parser limitation, not a measurement. The finding rests on the fifteen that
parsed, where the gap is 0 reported against 87 present.

## Why it matters: it makes the campaign re-request evidence it already owns

Every row assessment run today independently hit this, on its own row:

| row | the row asks for | what already exists, pinned |
|---|---|---|
| F02 | a new pickup/berry recording | 17 LEVEL02 movies, incl. a 36,397-frame 100% run |
| F03 | an Interpreter re-take | a from-boot movie, `pristine_replay_accepted` |
| F05 | (fixture_need declared) | 7 pinned movies |
| F07 | (fixture_need declared) | 10 pinned movies |
| F09 | an Interpreter movie for E11 | 3 pinned stage-9 routes, none ever replayed |
| F10 | "None for the objective law" | a from-boot Clover capsule that would close its cold-boot clause |
| F04 | — | 5 undeclared, incl. 2 of its own hazard |
| F06/F14 | F14 declares 0 movies | from-boot completion oracles for both |

The downstream effect is concrete: the movie scheduler marks rows ineligible for *"no
associated movie under `movies/Phase4/`"* while the movies sit there pinned. So the
cheapest evidence in the project — a replay of an existing fixture — is invisible
precisely to the tool meant to schedule it.

⚡ This is the same trap I hit three times personally today (the jr tables, the E02
locator, the death-session access log): **the evidence was already retained, and the
index that should have surfaced it said nothing.**

## What is actually broken

Not the fixtures — they are intact and centrally pinned; `durable_evidence` measures
**met on 19/19 rows**. What is broken is *attribution*: nothing joins a pinned movie to
the row whose stage it covers.

The join is not trivial, and that is likely why it was never built:

- Movie filenames use the **stage ordinal** (`LEVEL09_BUGBAR`), while disc directories
  use the **scene id** (stage 9 → scene 14 → `LEVEL04/`). Three numbering spaces again.
- Some movies name the row's subject rather than its stage (`Thumper_spawned_mosquitto`,
  `Bonus_Level_01`, `hazard_ground_bird_LEVEL04`).
- Some are owned by a D-row campaign but cover an F-row stage.

A correct join needs the progression table `0x80077FA0` (ordinal → scene) plus each
movie's own recorded scene id, which is readable from its start state. Two row
assessments already did exactly that for their own rows, so the method is proven.

## Scope

- ✅ Measured: ledger `movie_count` sums to 3; 87 pinned movies name the fifteen
  parseable rows' stages.
- ✅ Corroborated: eight independent row assessments each found undeclared pinned movies
  on their own row.
- ❌ NOT claimed: that all 87 are *useful* to their row. Filename attribution is a lower
  bound and a coarse one; a movie naming a stage may cover a different subject.
- ❌ NOT claimed: that any row's conclusions are wrong. This is missing attribution, not
  false evidence.
