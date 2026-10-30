---
kind: experiment
id: EXP_2026-07-30_phase4_e08_class_frontier
date: 2026-07-30
phase: 4
campaign: props_movers_gates
rows: [E08_props_movers_gates, E10_hazards, D11_mites_grubs]
method: offline_then_static
status: bounded_frontier_banked
evidence: [analysis/phase4_e08_class_frontier.json]
---
# Phase-4 E08 uncontrolled-class frontier

## Claim and falsifier

The exact 28 E08 type-word classes without a native outcome control form an
exhaustive, duplicate-free subset of the 47 unowned actor/source classes. Each
must join to one decoded VM selector program, authored source signatures, the
resident callback census, and exactly one retained-evidence cohort. A missing
or duplicated class, selector outside `0..39`, unknown callback, source-bound
drift, or priority-evidence drift falsifies the layer.

This claim does not assign a semantic owner, identify a native writer, or
promote frame-boundary correlation to instruction-level causality.

## Offline evidence

The retained contact/hazard index was queried through the tracked Phase-4
offline receipt producer. Its seven uncontrolled type-word search terms
produce no literal raw-index matches: the type words are correctly supplied by
the tracked actor-to-authored-source join in
`analysis/phase4_offline_e08_batch.json`, not by fixture filenames or authored
digest strings. That joined layer partitions the 28 classes into:

- five significant: `0x050D`, `0x1B1F`, `0x1E20`, `0x2528`, `0x2629`;
- two timing-only: `0x1F04`, `0x2223`; and
- 21 absent from the relevant actor-change records.

The closed offline receipt is retained outside the repository under the
iteration-1 run root; its receipt SHA-256 is
`19cab011065af7afebb4a96e31cfc924dc362905e6bc2d4ef85705ee647cf83f`.

## Static reconstruction

`analysis/phase4_e08_class_frontier.json` derives the 47 = 19 + 28 partition,
joins all 28 classes to the complete 40-program E07 decode, retains authored
signature and parameter hashes, and resolves every nonzero callback through
the ten confirmed resident function bounds plus byte-matched C/ASM source path.
No uncontrolled class has a moved observation.

The declared interface weighting ranks `0x2528`, `0x2629`, `0x050D`,
`0x1B1F`, and `0x1E20` first. The ranking chooses the next reconstruction
targets; it is not evidence that the historical program names are semantic
owners.

## Decision

No live escalation was opened. Static evidence answered the iteration's
exhaustiveness, join, and prioritization question. The missing facts are now
specific: reconstruct the native trigger/writer candidates for the five ranked
classes, then use an isolated live positive/negative control only if an exact
causal boundary remains absent.

`complete_frontier` stays open because native writers, final owners, authored
switch/gate state, denial/success behavior, lifecycle, and persistence still
intersect E08. E10 and D11 receive no row or dimension promotion.
