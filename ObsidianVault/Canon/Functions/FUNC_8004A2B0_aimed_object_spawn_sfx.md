---
kind: function
id: FUNC_8004A2B0
aliases: [FUNC_8004A2B0, 0x8004a2b0, aimed_object_spawn_sfx]
address: 0x8004A2B0
name: aimed_object_spawn_sfx
status: static_seen
confidence: confirmed
source_state: original_game
system: [SYS_enemy_ai, SYS_contact_object_pool]
reads: [0x800A6500, 0x800A6508]
writes: []
calls: [0x80060ae4, FUNC_8005A0E0, 0x8005044c]
evidence:
  - symbols/re_symbols.sym
  - analysis/naming/u2_batch04.json
  - analysis/phase3_fn_ptr_fields.json
  - analysis/phase4_b06_b08_powerups.json
  - analysis/phase4_d15_daddy_long_legs.json
patch_policy: hook_sensitive
---

# FUNC_8004A2B0 - aimed_object_spawn_sfx

## Purpose

Already named by prior static inference (`symbols/re_symbols.sym`,
`analysis/naming/u2_batch04.json`, rationale "spawns a contact object with
computed heading + sound") but had no Canon page and no live-confirmed
gameplay meaning until the D15 daddy-long-legs investigation
(`analysis/phase4_d15_daddy_long_legs.json`) traced it live as the producer
of that species' ranged web attack.

## Confirmed behavior (2026-08-02, live-traced)

Takes `a0` = a small caller-owned scratch pointer (NOT a persistent actor
record — live-read as a fixed stack address, `0x801ffea8`, across many
calls); `s0 = *(a0+4)` is the actor-shaped context the caller fills in per
candidate. Gated by:
1. A halfword suppress flag at `s0+0x4a` — nonzero skips the call entirely.
2. A per-candidate cooldown byte at `(*(s0+0x80))+0xf`, decremented each
   call; only at exactly 0 does it fire, then resets the cooldown to a
   semi-randomized value in `[40,103]` via a rotating byte-stream cursor at
   `0x800822f4` (masked to 6 bits, `+40`).

On firing: computes `dx,dz` from the candidate's own position
(`s0+4`/`s0+0xc`, the standard actor position offsets) to Flik's position
(`0x800A6500`/`0x800A6508`), calls an atan2-style helper (`0x80060ae4`,
matching the sibling [[FUNC_8004A234_actor_turn_toward_player]]'s own
`atan2_heading` call) to get the angle toward Flik, snap/clamps it against a
stored facing field at `s0+0x14`, and uses the result to compute a spawn
offset via the sin/cos LUT at `0x80074970`. Spawns the contact object via
the explicit-constructor sibling allocator ([[FUNC_80059E44]]'s own
`0x8005A0E0` entry, aka `contact_object_spawn_full`) with a FIXED metadata
pointer `0x80079da4` (`action_id=118`/`0x76`, `active_type=60` — read
directly from RAM, not inferred). Immediately afterward calls
`0x8005044c(a0=25, a1=s0+4)` — almost certainly the attack's own SFX
trigger (SFX id 25).

Live-confirmed twice in one movie replay (`movies/Phase4/Interpreter/
DaddyLongLegs.movie.json`): fires at movie-relative frames 78 and 168,
producing contact-pool records (`0x800B0D18` slots 33 and 37) that go on to
land health-decrementing hits on Flik at frames 312/604 — the daddy-long-legs'
web attack (D15 row).

## Dispatch — optional per-actor callback, not a hard-coded species check

`debugger.xrefsTo` finds no plain `jal` to this address — only one weak
`data`-type reference. `analysis/phase4_b06_b08_powerups.json` independently
confirms this function has NO `jal` caller anywhere in the image. This
matches `analysis/phase3_fn_ptr_fields.json`'s existing census:
`actor_record+0x7C` is a `jalr`-dispatched function-pointer field (1286 live
instances censused, 60.8% hit rate, 9 distinct handlers). `aimed_object_
spawn_sfx` accounts for 68 of those instances; `mosquito_species_callback`
(the D07_mosquitoes row's own confirmed callback, `0x8004A180`) is a sibling
value in the same slot. Species get an OPTIONAL attack-callback pointer
assigned at spawn-table init, not a hard-coded id branch inside any shared
dispatcher — **CONFIRMED LIVE 2026-08-03**: id=17's own live actor record
(`0x800a0ae8`) reads `+0x7C = 0x8004A2B0` exactly, at all 6 frames sampled
across the full `DaddyLongLegs.movie.json` replay, cross-validated against
the record's own hp/flags transitions matching the already-documented
combat timeline. A fresh, never-reloaded isolated instance resolved the
movie-replay non-determinism that blocked the first two attempts.

## Related

[[FUNC_80059E44]] (allocator + sibling explicit constructor) ·
[[FUNC_8004A234_actor_turn_toward_player]] (neighboring atan2-based facing
routine, same `+0x14`/position-offset conventions) · [[SYS_enemy_ai]] (D15
row) · [[SYS_contact_object_pool]] (allocator/dispatch mechanics) ·
`analysis/phase4_d15_daddy_long_legs.json`
