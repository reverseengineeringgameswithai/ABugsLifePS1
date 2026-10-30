---
kind: playbook
id: PLAYBOOK_game_solving_phase_7
name: Phase 7 - Whole-Game Closure and Modding Foundation
aliases:
  - Phase 7 - Expand Subsystem by Subsystem
status: planned
created: 2026-07-11
updated: 2026-07-11
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_6
next: null
depends_on:
  - PLAYBOOK_game_solving_phase_0
  - PLAYBOOK_game_solving_phase_1
  - PLAYBOOK_game_solving_phase_2
  - PLAYBOOK_game_solving_phase_3
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_game_solving_phase_5
  - PLAYBOOK_game_solving_phase_6
---

# Phase 7 - Whole-Game Closure and Modding Foundation

**Navigation:** [[Phase 6 - Complete Matching Source Overlays Assets and Toolchain|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · End of solve roadmap

## Purpose

Perform the final whole-game audit and declare exactly what has and has not been solved.
Only after the pristine closure gate passes does this phase design a production modding
foundation from the verified original interfaces.

## Whole-game closure audit

- [ ] Every row in [[Whole-Game Mechanics Baseline]] has a final evidence-backed status.
- [ ] Every subsystem campaign satisfies the strict Definition of Done.
- [ ] Every campaign stage/objective, boss, special mechanic, bonus path, and lifecycle
  passes the pristine oracle.
- [ ] Resident/overlay code and indirect dispatches have reviewed semantic roles and
  source coverage.
- [ ] State, assets, loaders, presentation, persistence, and lifecycle ownership are
  explicit and validated.
- [ ] Remaining unknowns are enumerated, bounded, and proven not to intersect the
  claimed solved surface.
- [ ] All contradictory or legacy “solved” claims are reconciled against current Canon
  and evidence.

## Closure decision

The game may be declared **whole-game solved** only when the audit passes without a
major mechanic, campaign path, overlay, asset owner, or lifecycle exception being
deferred. If bounded residuals remain, publish the narrower status—such as
“modding-safe for specified systems”—rather than calling the game solved.

## Modding foundation after closure

Once the pristine closure decision permits it:

- Build every MOD image independently from the immutable, hash-verified pristine base.
- Define stable extension boundaries from proven original ownership/lifecycle models.
- Use one linked, explicitly owned MOD arena and generated symbol/occupancy maps.
- Give modules private state, initialization, dependencies, and reset duties.
- Enforce hook live-in/live-out, stack, delay-slot, GTE, memory-effect, and continuation
  contracts mechanically.
- Normalize custom identities before any fixed-domain original selector/table.
- Preserve a pristine behavioral arm and whitelist only intentional MOD deltas.
- Test every supported module combination from a fresh pristine-derived build.

Existing ALLMODS artifacts remain historical regression evidence. They are never used
as the patch base for the new platform.

## Final exit gate

- The whole-game closure audit has an explicit evidence-backed decision.
- The pristine source/build and behavioral oracle are reproducible from clean inputs.
- The modding platform changes no pristine behavior when built with zero modules.
- Each enabled module has explicit intended deltas and passes native controls,
  lifecycle, composition, and long-soak tests.
- Operator testing on an actual seed or target hardware confirms the automated release
  candidate; it is final acceptance, not first-line regression discovery.

## Progress record

| Closure area | Status | Evidence |
|---|---|---|
| Whole-game mechanics closure | pending | [[Whole-Game Mechanics Baseline]] |
| Full campaign integration | pending | — |
| Reproducible matching source/assets | pending | — |
| Residual/contradiction audit | pending | — |
| Post-closure modding foundation | gated | Cannot begin as production architecture before pristine closure |

