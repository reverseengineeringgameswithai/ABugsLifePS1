# Phase 4 Reverse-Engineering Methodology Ratchet

## Purpose

Select and bank the best-supported, efficient operating method for completing Phase 4
of the ABL whole-game solve. This is a focused methodology decision, not a Phase 4
implementation pass and not a Phase 4 closure decision.

The authoritative requirements are:

- `AGENTS.md`;
- `ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md`;
- `ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md`.

The ratchet must preserve their meaning. It may not weaken a work package, redefine a
completed campaign, promote partial evidence, or treat ALLMODS as behavioral authority.
Only the hash-verified pristine retail image is behavioral authority.

## Two-step decision loop

### Step 1 — Implementer Advisory

A fresh advisory agent must audit the current repository and retained run history,
compare plausible Phase 4 RE workflows, and write a concrete candidate operating
method. It is an advisor in the sense that it proposes how future implementation
agents should work; it does not implement or close Phase 4 mechanics.

The advisory must inspect and cite, at minimum:

1. The authoritative roadmap hub and Phase 4 note, including the strict subsystem
   Definition of Done and reusable-finding Definition of Finished.
2. The current 107-row mechanics/campaign registry, Phase 4 campaign configuration,
   scorecards, coverage matrices, offline opportunity queue, live-escalation queue,
   fixture manifests, and trace-capsule index.
3. Relevant retained ratchet decisions/logs and Git history, enough to distinguish
   productive architectural RE from repeated replay, stale-evidence repair,
   documentation churn, and gate bookkeeping.
4. Relevant authoritative machine layers: ASM/symbols, typed schemas, registries,
   validators, matching or documentation-grade `src_re` C, tests, and their known
   residuals. The advisory must inspect representative C and machine-readable sources
   for the currently open high-centrality families rather than discussing “C code” in
   the abstract.
5. The current local DuckStation external-debugger fork, including its API index,
   scenario/batch/provenance/movie/trace-capsule documentation, generated RPC surface,
   relevant C++ implementations, binary/source identity, and limitations. Method names
   or capabilities must not be invented from memory.
6. The operator movie inventory and declared external fixture/preservation manifests.
   Filenames are leads, not behavioral proof.

The advisory must compare at least three credible workflows, including:

- a closure ratchet acting as the primary investigator;
- local subsystem investigation followed by independent ratchet verification;
- capsule-first/offline batch analysis with narrowly justified live debugger
  escalation.

It may select a hybrid, but must explain why it is better supported than the rejected
alternatives under current project evidence. “Best” means the best defensible method
under the current repository, tooling, fixtures, and bottlenecks—not a universal or
unfalsifiable optimum.

### Step 2 — Hard-Truth Verification

A fresh agent in a detached clean checkout must independently challenge the advisory.
It must assume the proposal is wrong until the cited repository evidence, DuckStation
API/source, retained run history, and executable checks support it.

The verifier must reject the candidate when any of the following is true:

- it merely restates the current ratchet prompt or roadmap;
- it optimizes for green summary counts rather than solved subsystem semantics;
- it recommends live replay for information already retained in a valid capsule;
- it treats frame-boundary capsules as every-cycle traces or campaign closure;
- it recommends offline analysis where exact writer/DMA/GPU/SPU causality or a native
  behavioral control is required;
- it lacks a precise row-to-campaign selection rule, escalation rule, evidence-banking
  path, or independent rejection path;
- it does not map confirmed findings into the appropriate ASM/symbol, typed schema,
  registry, matching/documentation-grade C, validator, test, Canon, and Experiment
  layers;
- it ignores campaign breadth, lifecycle, capacity, reset, transitions, cross-system
  dependencies, or the clean-checkout/external-fixture contract;
- it silently depends on dirty operator files, undeclared media, undocumented
  DuckStation features, or an unpinned binary;
- it lacks power-outage/restart, concurrent-work, ownership, and non-conflict rules;
- it gives no measurable way to determine whether the method is actually reducing
  repeated emulator work and increasing durable semantic closure;
- it changes Phase 4 evidence, implementation, scorecards, C/ASM, tests, gates, or
  roadmap requirements to make its recommendation appear successful.

Acceptance requires direct inspection and falsification attempts, not agreement with
the advisory’s prose.

## Required final Obsidian result

The candidate and final decision live at:

`ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Reverse Engineering Operating Method.md`

The Phase 4 execution note must contain a reciprocal link to it. Before acceptance the
method note must say:

```yaml
status: candidate
methodology_ratchet: pending
```

and contain exactly one verdict marker block:

```text
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_START -->
Pending independent verification.
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_END -->
```

Only an accepted hard-truth decision may change those fields to `accepted` and
`verified` and replace the marker block with the retained verification receipt.

The final note must include:

- authority and scope/non-scope;
- exact repository, roadmap, run-history, DuckStation API/source, C/ASM/schema, fixture,
  and capsule surfaces audited;
- current bottleneck diagnosis, with observation separated from inference;
- alternatives considered and falsifiable reasons for selecting/rejecting each;
- the chosen end-to-end workflow from row selection through durable banking;
- a decision table for static analysis, capsule/offline analysis, targeted live
  debugger work, cold-boot behavioral proof, and fresh verification;
- campaign-sized batching and dependency-centrality rules;
- required DuckStation API identity/isolation/provenance/control practices;
- exact authoritative machine-layer and Obsidian promotion contracts;
- verifier acceptance/rejection criteria;
- clean-checkout and external-fixture requirements;
- concurrent-work and operator-WIP ownership rules;
- outage/restart/checkpoint behavior;
- efficiency metrics and a scheduled reassessment trigger;
- confidence, residuals, supersession policy, and the independent verifier receipt.

## Write boundary

During the advisory/verifier loop, the only repository files that may change are:

- the final methodology note named above; and
- the Phase 4 execution note, solely to add or maintain the reciprocal link without
  weakening or rewriting its requirements.

No Phase 4 implementation, evidence artifact, fixture, C/ASM, test, scorecard, queue,
gate, or campaign status may be changed. The verifier is read-only. If it identifies a
methodology defect, it must reject and return that defect to the next advisory round;
it may not repair the candidate itself.

## Acceptance contract

The methodology is accepted only when:

1. The advisory worktree is committed and clean, and its changes stay inside the write
   boundary.
2. The candidate note satisfies every required section and links reciprocally to the
   Phase 4 execution note.
3. The recommendation is derived from current evidence and current DuckStation
   source/API rather than generic RE advice.
4. The verifier reproduces the decisive low-level inputs from a fresh detached checkout
   and reports no gap or required external input.
5. The verifier explicitly concludes that the recommendation is the best-supported
   efficient way forward under the current evidence, while bounding what it has not
   proven.
6. The deterministic banking step changes only the candidate/verification fields and
   receipt, the vault validator passes, and the final branch is clean.

This decision does not close Phase 4. The ratchet must not claim Phase 4 itself is
closed; it decides only the operating method for pursuing Phase 4.
