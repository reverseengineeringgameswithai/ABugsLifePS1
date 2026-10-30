---
kind: function
id: FUNC_8005CD2C
aliases: [FUNC_8005CD2C, 0x8005cd2c]
address: 0x8005cd2c
name: gameplay_effect_spawner
status: live_confirmed
confidence: medium
source_state: original_game
system: [SYS_contact_objects_and_drops]
calls: [spawn_fx_object, play_sound, contact_object_spawn_full, VectorNormal]
reads: []
writes: []
uses_tables: []
evidence:
  - EXP_2026-07-08_understanding_campaign_u1
src_paths: []
patch_policy: unknown
---

# FUNC_8005CD2C - gameplay effect spawner

## Purpose

Gameplay-driven effect burst. Runs a bounded loop (counter to `fp = 11` at entry) that spawns FX objects (`spawn_fx_object`) and contact objects (`contact_object_spawn_full`), plays sounds (`play_sound`), and uses `VectorNormal` for placement/direction. Invoked from `gameplay_state_machine`; touches the `0x800a` actor region.

## Evidence (runtime, u1.1)

- **Byte-matched** (asm) and **dynamic** — fired live during LEVEL01 (`execTrace`).
- Call-graph: caller `gameplay_state_machine`; callees `spawn_fx_object`, `play_sound`, `contact_object_spawn_full`, `VectorNormal`.
- Structure: `addiu fp, zero, 11` bound + `s5` counter at entry (spawn loop).
- Naming tier: **proven** (byte-matched + dynamic + spawn-pipeline call-graph). The exact triggering event/effect kind is not yet pinned.

Address `0x8005cd2c` (2016 B). See [[EXP_2026-07-08_understanding_campaign_u1]] · [[SYS_contact_objects_and_drops]].
