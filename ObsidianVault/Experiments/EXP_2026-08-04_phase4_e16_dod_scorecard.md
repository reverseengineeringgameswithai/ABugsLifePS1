---
date: 2026-08-04
row: E16_streaming_overlays
status: NOT SOLVED — 2/9 met (1 row-wide, 1 in scope), 6 partial, 1 open
---

# E16 against the nine-item Definition of Done

## Why this exists

Phase 4's standard is written down, and it is not the promotion tool. The
roadmap's *Definition of Done for a solved subsystem* lists nine items and says a
subsystem "is not called solved until every item below is satisfied"; the
Phase-4 exit gate adds that nothing unresolved may intersect the subsystem
"without being explicitly bounded".

`tools/phase4_promotion_preflight.py` encodes those same nine dimensions **1:1,
in the same order** — and wraps them in campaign-registry, debt-ledger and packet
scaffolding the written standard never asks for. When that scaffolding proved
unavailable on master I treated the tool as the bar and spent a long stretch
chasing it. The bar is the document, judged by review.

## The scorecard

| # | item | state | scope |
|---|---|---|---|
| 1 | original oracle | partial | the three registered-chunk tables |
| 2 | **complete frontier** | **met in scope** | the three registered-chunk tables |
| 3 | typed state | partial | the three registered-chunk tables |
| 4 | lifecycle | partial | one frontend → gameplay transition |
| 5 | original interfaces | partial | overlay entry ABI + loader contract |
| 6 | campaign breadth | partial | all 16 levels, for the three tables |
| 7 | **cross-system behavior** | **open** | rendering hand-off only |
| 8 | source closure | partial | loader + two consumers |
| 9 | durable evidence | met | whole row |

**E16 is not solved.** Two of nine met — one row-wide (durable evidence), one
within a declared sub-area (complete frontier).

## The scope trap, stated plainly

E16 is *"scene flow, level/MEMORY/FMV overlays, streaming, loader fixups, asset
residency, unload, and failure paths."* Almost every piece of evidence covers
**one sub-area**: the three registered-chunk pointer tables. Reporting "item 2
met" without that qualifier would be a row-level overclaim, which this row has
already had to retract once. Hence `met_in_scope` as a distinct state, and a
gate that fails if the frontier entry stops naming `0x8007EFE8`, region A and the
high heap as out of scope.

## What item 2 actually needed

The roadmap asks for the frontier to be **enumerated**, with the remainder
**explicitly bounded**. That is met here, by an argument that does not rest on
runtime silence: only five sites in the entire text segment can materialise a
pointer into those windows, and all five were already enumerated — so no
deliberate access exists outside the known set. The incidental readers are
enumerated as a family (22 hoisted-load sites), and 30 `bounded_residuals` carry
zero rejections.

⚠️ This is **not** the bar quoted in the B06 note on the Phase-4 page — *"item 2
requires the unresolved-intersection set to be empty"*. That is a
frontier-compiler rule scoped to a declared universe, and it is stricter than the
canonical DoD. Three rows have stalled against it. The two standards should be
reconciled before a fourth does.

## The weakest item

**7, cross-system behavior, is open** and honestly so. The rendering hand-off is
characterised end to end (46/46 registered chunks satisfy their consumer-derived
size law, visually confirmed) and the player-state relationship is bounded as
adjacency rather than overlap. Nothing else — physics, animation, audio, HUD,
objectives, save/load — has been validated. That is the next thing to attack if
the goal is to move E16, and the two most likely to bite are save/load and scene
transition.

Artifact: `analysis/phase4_e16_dod_scorecard.json` (every cited path checked to
exist; a missing one makes the scorecard BROKEN, not footnoted).
Gate: `tests/test_phase4_e16_dod_scorecard.py` (7) — including one that parses
the roadmap's own DoD text, so editing the standard fails the test instead of
silently rescoring the row.

Related: [[EXP_2026-08-04_phase4_e16_anypercent_campaign]],
[[SYS_registered_chunk_image_resources]]
