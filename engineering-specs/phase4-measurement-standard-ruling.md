# Ruling: Phase 4 is measured per-dimension against the bars AS WRITTEN

**Date:** 2026-08-10 · **Decided by:** the assistant (these calls are mine per the
operator's standing instruction). **Follows:**
`engineering-specs/phase4-two-standards-finding.md`. **Changes no status, edits no
registry.**

## The ruling

One standard, applied uniformly to every row:

1. **Measurement is per-dimension**, against each bar **as written** — canonical item 2
   asks the frontier be **enumerated** (scoped to *relevant*); the exit gate asks that
   anything unresolved be **explicitly bounded**, not absent. The strict
   empty-unresolved-set reading is the documented overshoot ("corrected 2026-08-04 —
   this sentence stated the wrong bar") and is not the standard.
2. **Blanket dispositions are not measurements.** A single basis string covering nine
   dimensions records a *decision*, and the existing vocabulary already says so:
   bounded-exhausted "is not a claim that the DoD is met, and it should never be read as
   one." The 16 ledger rows at 9/9-by-blanket are therefore **dispositions pending
   measurement**, not counter-examples to F01. (Per the operator: noted, not assessed.)
3. **Publish both**, per the vocabulary section: the stop decision and the per-dimension
   scorecard. The label says what was decided; the scorecard says what was measured.

This preserves every banked lesson: [[phase4-status-vocabulary]] stands unchanged
(bounded-exhausted still never reads as met), and the item-2 ruling
(`phase4-item2-bar-ruling.md`) is the *bounding mechanism* item 2's written bar admits.

## The first test case

`tools/phase4_f01_written_bar_assessment.py` →
`analysis/phase4_f01_written_bar_assessment.json`. F01 against the written bars:

| state | dimensions |
|---|---|
| met | durable_evidence |
| **met-candidate** | original_oracle · complete_frontier |
| partial | typed_state · lifecycle · cross_system_behavior · original_interfaces · source_closure |
| not_met | campaign_breadth |

Notable in both directions: `campaign_breadth` **fails the written bar too** — "every
applicable stage" has no denominator without the applicability universe, so the
adjudicator's C1 finding is not an artifact of strictness. And `complete_frontier` is a
met-candidate **because** the written bar asks enumerated-and-bounded, which the 179-site
declared assumption (void on one counter-example) provides — five campaigns proved no
current technique resolves the sites, and the written bar never asked for that.

Facts in the assessment are derived from the pinned artifacts at run time; only the
judgments are authored, and they are attributable.

## What a fresh verifier is asked to adjudicate

- **`original_oracle`** — already out:
  `phase4-f01-original-oracle-resubmission-work-order.md` (includes the four
  deliberately-unfixed tests).
- **`complete_frontier`** — whether declared-assumption bounding meets written item 2.
  The kill switch (void on a single counter-example, non-transferable) must land on the
  row verbatim if promoted.
- The assessment itself — any judgment above is challengeable; `met_candidate` is a
  submission, not a met.

## What this unblocks, in order

1. Verifier adjudication of the two candidates (F01 could honestly reach 3/9 *measured*,
   which would be the highest measured row in the campaign).
2. The ~56 answered-but-unregistered rows become registerable through the **same**
   per-dimension path at a known cost — no blanket entries going forward.
3. The 16 blanket rows eventually get measured scorecards. Not assessed here.
