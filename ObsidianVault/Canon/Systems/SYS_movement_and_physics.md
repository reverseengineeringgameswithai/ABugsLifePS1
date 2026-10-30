---
kind: system
id: SYS_movement_and_physics
created: 2026-07-08
updated: 2026-07-08
status: live_confirmed
confidence: medium
source_state: original_game
functions: [player_vertical_update, player_movement_collision_integrator, collision_resolve_pass, collision_resolver_accumulate, ground_height_query, mover_actor_update]
memory: []
tables: []
constants: []
evidence: [EXP_2026-07-08_understanding_campaign_u1]
src_paths: [src_re/movement_integrator_8003633c.c, src_re/player_update_80048138.c]
patch_policy: safe_to_read
---

# SYS_movement_and_physics - movement integration + collision resolution

## Purpose
How the player (and mover actors) advance position each frame: a state machine picks the intent,
an integrator applies gravity + collision resolution and commits the resolved position. This is the
substrate the Tier-3 custom-collision hook attaches to.

## Pipeline (per frame)
1. **`player_vertical_update`** (`0x80048138`, byte-matched) — jump / land / butt-slam state machine.
   Reads buttons `0x80082488`; drives `air_state` (player+0x80), the grounded flag (player+0x82),
   and `anim_index` (player+0x88). It only ever CLEARS grounded; it never SETs it. Called from
   `gameplay_state_machine`. Detail: [[FUNC_80048138_player_vertical_update]] · src_re/player_update_80048138.c.
2. **`player_movement_collision_integrator`** (`0x8003633c`) — writes Flik's Y up to 3× per frame:
   gravity (`-3200`), collision commit (from the resolved position staged on the stack), then a final
   `+3200` adjust (the Tier-3-hooked writer). Player position = `0x800a6500` (X/Y/Z/w int32).
   For the player call, `0x800495B8` passes player+0x82 and the integrator writes `{1,1}` at
   `0x80036CB8`/`0x80036CC0`, a proven producer of `grounded = 0x0101`. Its raw set condition is
   `a3 != 2 && (s0 == 1 || a3 == 1)`; global producer exclusivity is not established. Callers:
   `player_vertical_update`, `mover_actor_update`, `camera_follow_update`.
   **Correction history (2026-08-04 audit):** the former “sole producer” wording exceeded the
   unresolved pointer/indirect-call census and is retracted.
3. **Collision passes** — `collision_resolve_pass` (`0x80035280`), `collision_resolver_accumulate`
   (`0x800345cc`, byte-matched — swept-plane resolver), `ground_height_query` (`0x80037a38`). Collision
   *source* is the per-sector origin-Y + swept planes; see [[SYS_geometry_collision_consumers]] /
   [[SYS_render_collision_source_separation]].

## Key facts
- `3200` = the fixed Y bracket (gravity subtracts before resolution, the tail adds it back).
- In the measured Tier-3 path, suppressing native collision removed this set transition and grounded
  stayed 0, freezing the landing/locomotion animation; the mod re-publishes grounded from its own floor
  (mod/caves/tier3_collision.c).

## Evidence
Runtime call-graph confirmed live in LEVEL01 ([[EXP_2026-07-08_understanding_campaign_u1]]); behavior
from the two `src_re` decompilation notes. Related: [[SYS_warp_and_level_transition_safety]].
