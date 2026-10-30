---
kind: playbook
id: PLAYBOOK_game_solving_phase_5
name: Phase 5 - Prove Cross-System and Full-Campaign Integration
aliases:
  - Phase 5 - Replace Scattered Patches with a Mod Runtime
status: planned
created: 2026-07-11
updated: 2026-07-11
confidence: high
parent: PLAYBOOK_game_solving_roadmap
previous: PLAYBOOK_game_solving_phase_4
next: PLAYBOOK_game_solving_phase_6
depends_on:
  - PLAYBOOK_game_solving_phase_2
  - PLAYBOOK_game_solving_phase_3
  - PLAYBOOK_game_solving_phase_4
---

# Phase 5 - Prove Cross-System and Full-Campaign Integration

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Previous phase]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]] · [[Phase 6 - Complete Matching Source Overlays Assets and Toolchain|Next phase]]

## Purpose

Prove that individually solved subsystems remain correct when composed throughout the
actual pristine campaign. Integration behavior is its own target: many regressions and
unknown rules appear only when valid systems interact over time.

## Required interaction classes

- Player actions across floor/wall/slope/hazard/mover/camera/animation states.
- Seed carrying, planting, powers, projectiles, enemies, damage, and objectives.
- Collectibles, equipment, counters, HUD, results, saves, reloads, and unlocks.
- Enemy AI, projectiles, plants, hazards, death, drops, respawn, and permanent quotas.
- Boss/objective state with pause, damage, death, respawn-anchor restoration, transition, and results.
- Renderer, double buffering, overlays, streaming, audio, FMV, and frontend transitions.
- Pool capacity, repeated allocation/retirement, long play, and scene reuse.

## Work packages

- [ ] Build an interaction matrix from every Phase 4 campaign dependency.
- [ ] Create paired and multi-system scenarios for every high-risk shared state or pool.
- [ ] Run a complete pristine campaign from cold boot with checkpointed behavioral
  assertions at every level and transition.
- [ ] Run 100% paths covering grain, FLIK, enemy quotas, success tokens, movie unlocks,
  bonus entries, and save/reload.
- [ ] Run death/continue and failure paths for normal, special, chase, flight, and boss
  stages.
- [ ] Run long-duration and repeated-level soaks to expose stale overlay/global state.
- [ ] Compare interpreter/recompiler or other execution modes where timing/undefined
  behavior could conceal an original contract.
- [ ] Record every permitted nondeterministic field and prove it does not change
  behavior.

## Exit gate

- A complete pristine campaign, representative 100% campaign, bonus paths, and failure
  paths pass deterministic behavioral assertions.
- Every high-risk cross-system interaction has a focused scenario and causal ownership
  model.
- No pool, counter, effect, audio voice, renderer iterator, overlay state, or objective
  state leaks across its intended lifetime.
- Save/load, continue, movie unlock, and frontend round trips preserve the confirmed
  game state.
- Phase 4 campaigns require no status downgrade after integration testing.

## Handoff to Phase 6

Phase 6 receives behaviorally integrated semantic models and a precise list of source,
overlay, asset, and toolchain gaps that still prevent reproducible reconstruction.

## Progress record

| Integration area | Status | Evidence |
|---|---|---|
| Focused recent regression interactions | partial | Berry/render/audio/Training cases exist |
| Complete normal campaign | pending | — |
| Complete 100%/bonus campaign | pending | — |
| Death/continue/save lifecycle | pending | — |
| Long soak and level reuse | pending | — |
