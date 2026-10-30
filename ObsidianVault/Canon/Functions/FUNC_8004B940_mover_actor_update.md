---
kind: function
id: FUNC_8004B940
aliases: [FUNC_8004B940, 0x8004b940]
address: 0x8004b940
name: mover_actor_update
status: live_confirmed
confidence: medium
source_state: original_game
system: []
calls: [player_movement_collision_integrator, sector_region_code_query, spawn_drop, atan2_heading]
reads: []
writes: []
uses_tables: []
evidence:
  - EXP_2026-07-08_understanding_campaign_u1
src_paths: []
patch_policy: unknown
---

# FUNC_8004B940 - mover actor update

## Purpose

Per-frame update of a mover actor. Integrates the actor's movement + collision (`player_movement_collision_integrator`), computes a heading (`atan2_heading`), queries its collision sector (`sector_region_code_query`), and can spawn drops (`spawn_drop`). Invoked from `mover_updater`; `a0` at entry is an actor struct in the `0x800a09xx` actor region.

## Evidence (runtime, u1.1)

- **Byte-matched** (asm) and **dynamic** — fired live during LEVEL01 (`execTrace`).
- Call-graph: caller `mover_updater`; callees `player_movement_collision_integrator`, `sector_region_code_query`, `spawn_drop`, `atan2_heading`.
- Entry register `a0 = 0x800a09e0` (actor region).
- Naming tier: **proven** (byte-matched + dynamic + gameplay call-graph). Which specific mover class it serves is not yet pinned.

Address `0x8004b940` (1996 B). See [[EXP_2026-07-08_understanding_campaign_u1]].
