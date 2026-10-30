---
kind: playbook
id: PLAYBOOK_phase4_closure_conundrum
name: Phase 4 - Closure Conundrum and Recovery Plan
status: current
created: 2026-08-19
updated: 2026-08-19
confidence: audit_supported
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_roadmap
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_phase4_reverse_engineering_operating_method
---

# Phase 4 — Closure Conundrum and Recovery Plan

> [!warning] Read before extending Phase 4
> Phase 4's experimental work is often rigorous. Its principal failure mode is
> the machinery that converts an observation into a causal, reproducible,
> preserved, finitely closed claim. More tracing does not by itself solve that
> problem.

This note records the 2026-08-19 documentation/evidence audit so a future agent
does not restart the same investigation or mistake administrative growth for
closure. It is a diagnosis and proposed recovery path, **not** permission to
silently weaken `engineering-specs/phase4-closure.md`, redefine a roadmap gate,
or promote a row. Any phase-boundary change requires an explicit operator
decision and corresponding roadmap/spec update.

Navigation: [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 execution note]] ·
[[Phase 4 - Reverse Engineering Operating Method|operating method]] ·
[[Phase 4 - F01 Closure Roadmap|F01 closure roadmap]] ·
[[Game Solving Roadmap - From Reconstruction to Reliable Modding|main roadmap]]

## The conundrum

The roadmap assigns Phase 4 subsystem closure, Phase 5 cross-system/full-campaign
integration, and Phase 6 complete matching source. But the Phase 4 definition of
done already requires broad exceptional-path coverage, cross-system behavior,
and reviewed semantic source. Therefore Phase 4 partly contains the work of
Phases 5 and 6.

Terms such as "every applicable path" and "no unresolved path intersects this
row" are not finite until each row declares its universe. Discovering another
level, overlay, indirect caller, exceptional transition, or lifecycle path can
reopen a supposedly complete row forever. The result is an open-world research
program being managed as though it were a finite checklist.

The operator must eventually choose explicitly between:

1. **Finite phase boundaries:** Phase 4 delivers bounded subsystem contracts,
   causal mechanisms, and explicit residual frontiers; Phase 5 owns integration
   breadth; Phase 6 owns matching-source closure.
2. **Combined closure:** retain the existing Phase 4 bar, but acknowledge and
   plan it as the effective combination of Phases 4–6.

Do not obtain apparent progress by quietly choosing option 1 in campaign files
while the written gate still demands option 2.

## Audit snapshot — 2026-08-19

These figures describe the dirty working tree inspected on that date. Recompute
before quoting them as current status.

- The read-only gate model reported 107 rows, 15 campaign-complete labels, 91
  open rows, all four closure predicates false, and all six work-package
  prerequisites false. The retained `analysis/phase4_gate.json` was stale.
- All 15 campaign-complete artifacts were still `partial` in
  `analysis/mechanics_baseline.yaml`; separate tests could validate the older
  bounded artifact and the later campaign-complete artifact simultaneously.
- The inventory recomputation found 261 generators versus 149 declarations,
  473 artifacts versus 127 declarations, 112 undeclared generators, 346 orphan
  artifacts, 90 missing test declarations, and 80 dependency mismatches.
- `analysis/phase4_external_evidence_manifest.json` declared 155 objects and a
  two-copy preservation policy, but reported zero fully replicated objects and
  `preservation_ready: false`.
- The main gate did not consume that preservation result. A whole-phase green
  result was therefore structurally possible without durable evidence copies.
- The exact DuckStation binary hashes cited by the 15 completed campaigns were
  absent from the central preservation registry. Their facts may be useful, but
  exact replay from centrally preserved inputs was not demonstrated.
- Since 2026-07-14, roughly 393 commits had touched `analysis/phase4*`, while 18
  touched `src_re/**`. This is evidence of control-plane growth, not proof that
  any individual experiment was weak.

The vault-lint failures found during that audit were repaired later on
2026-08-19 and the ratchet was lowered to zero. Vault lint cleanliness is now a
guard, but it does not resolve the Phase 4 closure design described here.

## Where proof promotion was too weak

Representative campaigns, especially run locomotion, contained careful media
identity, isolated emulator configuration, trace limits, state inspection,
positive/control cold boots, and cleanup provenance. The problem was downstream:

- `tools/phase4_common.py`'s assertion audit checked a retained JSON hash and
  leaf value. That proves transcript integrity, not independent reproduction.
- Its finding audit checked that a named guard function existed; it did not
  execute the guard.
- Campaign completion did not require the exact debugger binary/source to be
  present in the preservation registry.
- External raw evidence, two-copy preservation, semantic-source promotion, and
  baseline status were separate truth surfaces rather than one atomic promotion.

The missing chain was:

```text
observation
  -> causal discriminator / falsifier
  -> executable assertion
  -> preserved raw evidence + exact runtime/source
  -> independent reproduction
  -> finite declared coverage
  -> campaign closure
```

## Operating rule until the boundary is decided

1. **Do not start a new live replay merely because a row is open.** Validate and
   query the relevant retained trace capsule first. Name the missing domain that
   requires live execution.
2. **Do not count a retained JSON leaf as behavioral proof.** The decisive guard
   must execute against its declared input, fail on a falsifying control, and
   remain tied to the raw receipt.
3. **Do not promote evidence whose exact runtime cannot be recovered.** Preserve
   the binary, source state, API surface, settings, media/movie/save identities,
   and raw receipt—or label the result `legacy_supported`/reproduction pending.
4. **Do not maintain status in parallel by hand.** One claim ledger should drive
   the baseline, campaign scorecard, Canon links, and gate inputs.
5. **Declare a finite scope per claim.** State levels, overlays, lifecycle
   segments, input classes, exceptions, and explicit nonclaims. Residuals outside
   that universe stay visible without making the scoped claim meaningless.
6. **Separate observation, inference, causal confirmation, generalization,
   independent reproduction, preservation, and closure.** Never collapse them
   into one `complete` boolean.
7. **Treat check commands as read-only contracts.** During the audit,
   `tools/phase4_inventory.py --help` rewrote three retained summaries; they were
   restored. Do not use that path for inspection until its CLI separates
   `check` from explicit `regen`.

## Minimum promotion record

Every claim proposed for closure should carry:

- stable claim ID, finite scope, and explicit nonclaims;
- pristine media/fixture/source/binary/API/settings identities;
- reproduction scenario or exact command;
- observed event/window, coordinate mapping, and truncation/completeness state;
- same-anchor positive and negative controls;
- causal discriminator and stated falsifier;
- raw external artifact IDs/hashes plus preservation receipt;
- an executable assertion that is actually run;
- semantic-source and Canon consumers;
- residual frontier and next experiment, if any;
- independent verifier receipt.

## Recovery sequence

1. Pause broad new trace collection long enough to settle the Phase 4/5/6
   boundary explicitly.
2. Establish one authoritative claim ledger and derive all other status views.
3. Add preservation readiness and executed-guard results to the hard gate.
4. Migrate the 15 legacy completions by replaying only their smallest decisive
   assertions on a preserved runtime; do not regenerate enormous transcripts
   without a named need.
5. Separate guaranteed read-only `check` commands from explicit `regen`
   commands and topologically declare generator dependencies.
6. Preserve the external evidence store on two independently verified copies
   before collecting more irreplaceable evidence.
7. Keep one short generated current-status page; move chronological/retracted
   history into dated experiment journals or Archive.

## Cross-port acceleration boundary

[[EXP_2026-08-19_pc_to_ps1_semantic_bridge_pilot]] provides a read-only,
versioned PC-to-PS1 hypothesis path. Use it to rank a bounded candidate or
choose a discriminator when PC-native evidence supplies a distinctive semantic
shape. A cross-port ranking is `ps1_candidate_only`: it cannot satisfy a Phase
4 gate, promote Canon, replace a target-native causal control, or count as
independent reproduction. Keep the matcher upstream of the claim ledger so it
reduces search work without becoming another manually maintained status
surface.

## Stop condition for future agents

If a proposed task only adds another trace, receipt, status paragraph, generated
summary, or worktree without reducing a named causal/coverage/preservation
residual, stop and re-read this note. State which missing link in the promotion
chain the work will close before proceeding.
