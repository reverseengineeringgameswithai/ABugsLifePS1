---
kind: system
id: SYS_player
created: 2026-07-08
updated: 2026-07-08
status: live_confirmed
confidence: medium
source_state: original_game
functions: [player_vertical_update, player_movement_collision_integrator]
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-08_understanding_campaign_u1]
src_paths: [src_re/player_health.c, src_re/player_update_80048138.c]
patch_policy: safe_to_read
---

# SYS_player - Flik state, health, and lives

## Purpose
Flik's per-frame state and the health/lives economy — the player-side counterpart to
[[SYS_movement_and_physics]].

## Player object
- Base `0x800a6500`: position X/Y/Z/w (int32 @ +0/+4/+8/+0xc); `vy` @ +0x30; `floor_Y` @ +0x48;
  `air_state` @ +0x80 (0 grounded, 1 takeoff, 2 airborne, 3 butt-slam); `grounded` @ +0x82
  (`0x0101` grounded / `0` airborne); `anim_index` @ +0x88. State machine =
  `player_vertical_update` (`0x80048138`); the movement integrator is a statically proven grounded
  SET producer at `0x80036CB8`/`0x80036CC0` for the player call. This does not claim global producer
  exclusivity (see [[SYS_movement_and_physics]]).

## Health economy (RCG-021, CORRECTED by Phase 2 2026-07-12)

> ⚠️ **Correction.** This section previously named `0x800a7e2a` as health. It is
> **not**: it is the HUD *pulse/leaf-spin* counter and it cycles endlessly on its
> own. The true value is below. See [[EXP_2026-07-12_phase2_behavioral_oracle]].

- **TRUE health** = **s16 `0x800A6594`** (full = 7). Found via the mercy-leaf gate
  (`lh 0x6594; sltiu <4` @`0x8004999C`) and confirmed by the damage applier
  **`0x8004A880`** (`hp -= 1`). Enemy contact damage is a flat −1.
- **Death law:** death occurs **only when the decrement result is < 0**. So
  **hp 0 = alive on the final hit**, not dead.
- **Respawn:** ~120–180 frames after death, at the level spawn point, with
  **hp := 4** (not 7) and lives − 1. On-hit knockback writes `0x800A6530 := -1024`
  and zeroes `0x800A6582/84/86/9E`.
- **Lives** `0x800a65a0` (u8). **Lives 0 = the playable final life**; a death while
  lives == 0 runs the game-over path to scene 0.
- **Pit fall** = a SEPARATE instant death (spends a life directly, bypassing the −1
  contact path).
- **Health leaves** (type-38 drops, gated `[0x800a6594] < 4`) restore HP; drop
  machinery shared with [[SYS_contact_objects_and_drops]].
- **Do not reuse as health/damage discriminators:** `0x800A7E2A` (HUD pulse) and
  `0x800910A0-A7` (free-running modulo animation counters — `A2` is NOT a damage flag).

## Evidence
Live investigation (mosquito.sav) in src_re/player_health.c; state machine in
src_re/player_update_80048138.c ([[FUNC_80048138_player_vertical_update]]).
Runtime cross-check: [[EXP_2026-07-08_understanding_campaign_u1]].
Health-economy correction + death/respawn laws: [[EXP_2026-07-12_phase2_behavioral_oracle]]
(`analysis/phase2_death_matrix.json`, deaths reproduced on 14/16 stages).
Action/state laws: [[SYS_player_action_state_laws]].
