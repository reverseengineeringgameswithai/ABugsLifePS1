---
date: 2026-08-03
phase: 4
row: B14_hostile_plant_projectiles
status: substantiated-partial-bounded-exhausted
---

# Phase 4 B14 - hostile blue-plant projectiles

## Decision

**B14 is a substantiated correction and bounded-exhausted Partial. Move on. No new
Interpreter movie and no cold boot are required for the current row.**

The prior baseline sentence saying every blue power-plant tier eventually emits the
hostile spike is superseded. Constructor 59 belongs to the type-7 blue tiers 1, 2,
and 4. Blue tier 3 is type 6 and emits constructor 31 once; the pristine handler has
no constructor-59 path, and the accepted tier-3 capsule segment supplies a 720-frame
negative control.

Machine summary: `analysis/phase4_b14_hostile_plant_projectiles.json`.

## Scope

This row owns the native constructor-59 object emitted as an alternate/fallback output
by blue power plants:

- tier applicability and producer selection;
- first-fire and repeat timing in the retained all-tier fixture;
- contact class, collision radius, damage, targeting, and ballistic motion;
- timeout, terrain/player-contact retirement, and the constructor-60 terminal effect.

It does not re-solve the power grants owned by [[SYS_blue_health_power]] and
[[SYS_player_power_slot]], nor the generic contact pool owned by
[[SYS_contact_objects_and_drops]].

## Provenance and capsule admission

The static input is the pristine `SCUS_942.88`, size `471040`, SHA-256
`1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`.

The runtime oracle is `movies/Phase4/A13/blue_seed_levels.movie.json`, SHA-256
`79d0aa0d26bcd760316f6bf685bf781f571ec63806a09d78be84d36ab01b68e1`,
anchored by save SHA-256
`9198c8c3daa896813f0198ecb2a1b7068c7035116aed0aadbc1072ffdb01f5c3`.
Its retained capsule is centrally pinned by
`analysis/phase4_trace_capsule_set.json`:

- manifest SHA-256 `81053aba5b5ec9bb9e33fbb944fffd09d9df2ed95528ff8dafb931e042b7f17d`;
- tree SHA-256 `e44dfa8b665f3c2f7f10dd453e2b986ee5adaf5237e2cd5ae65de7e82cda46b1`;
- `3796` frame-boundary records over `3795` movie frames;
- complete, untruncated, no error, and control-identical;
- C reconstruction verified `11,388` RAM/VRAM/SPU domain hashes.

The queried external `v3` mirror carried the same pinned manifest identity as the
central `v2` preservation entry. The capsule was therefore sufficient; a live replay
would have duplicated retained domains without adding the missing every-cycle or
behavioral information.

## C procedures

Static guard:

```bash
cc -O2 -std=c11 tools/phase4_b14_static.c -o /tmp/phase4_b14_static -lcrypto
/tmp/phase4_b14_static SCUS_942.88
```

Capsule reducer/guard:

```bash
cc -O2 -std=c11 tools/phase4_b14_capsule.c -o /tmp/phase4_b14_capsule -lzstd -lcrypto
/tmp/phase4_b14_capsule ~/Downloads/ABL-external-evidence/trace-capsules/Phase4/v3/A13__blue_seed_levels
```

The static guard checks executable identity, metadata rows, both plant handlers,
action-8 dispatch, profile 6, motion/terrain masks, retirement/effect instructions,
and the executable-wide constructor-59 immediate census. The capsule guard rebuilds
all domains, verifies every record hash, and asserts the exact four plant births,
output sequence, spike impact ages, constructor-60 effects, and relevant block counts.

## Static producer law

### Type 7: blue tiers 1, 2, and 4

The sole producer is `0x8005C744..0x8005C818`:

1. Require `slot+0x02 == 2` and `slot+0x04 == 0x00080000`.
2. For the ordinary path, consume one RNG byte.
3. If `(rng_byte & 3) == 0`, select constructor 59.
4. Otherwise select `(signed extra >> 12) + 35`: constructor 37, 38, or 39.
5. Spawn exactly one object at `(plant.x, plant.y - 0x4000, plant.z)` with table-A
   profile 6.
6. Call `0x800579E0` on the returned record, then dispatch cue/event `0x24`.

The exact ordinary split is therefore one constructor-59 result in four qualifying
activations. Tier 4 has an additional forced fallback: once global power bit `0x20`
is already set, it bypasses RNG and selects constructor 59 every time.

The pristine executable contains exactly two `a3 = 59` immediate sites. Both are in
this type-7 handler (`0x8005C78C`, `0x8005C7E4`). No independent constructor-59 plant
producer exists in the resident image.

### Type 6: blue tier 3

`0x8005C6F0..0x8005C744` requires the mature flag pattern, then calls the allocator
with constructor `(signed extra >> 12) + 31` and profile 3. Blue tier 3 has extra
`0x0000`, so this is constructor 31. The handler then ORs `0x0008` into
`slot+0x2E`, making the output one-shot. It has no RNG read and no branch to 59.

This directly refutes the old every-tier sentence. The capsule independently agrees:
type 6 lives from movie frame 2074 through 2793, emits constructor 31 at 2102, and
never produces constructor 59.

## Capsule timing and outputs

| Blue tier | Plant birth | Native outputs in order | Timing |
|---|---:|---|---|
| 1, type 7 / `0x2000` | 120 | c37 at 314, 482, 650 | first `+194`; repeats `+168` |
| 2, type 7 / `0x3000` | 1030 | c59 at 1224, c38 at 1392, c59 at 1560 | first `+194`; repeats `+168` |
| 3, type 6 / `0x0000` | 2074 | c31 at 2102 | one-shot `+28` |
| 4, type 7 / `0x4000` | 2950 | c39 at 3144, c59 at 3312, 3480, 3648 | first `+194`; repeats `+168` |

The `194` and `168` numbers are exact for this fixture, not falsely promoted to local
handler constants. Neither handler owns a recurrence counter. The shared animation
and scheduler state supplies the qualifying invocation timing.

Block-flow evidence covers the relevant code: type-6 handler `361` represented hits,
type-7 handler `1471`, allocator `42174`, and radial helper `170`.

## Constructor-59 contact and motion contract

Metadata-B row 59 creates:

- action ID `8`;
- lifetime/active counter `200` logic updates;
- initial animation counter `210`;
- radius addend `100`, giving total player-contact radius `300 + 100 = 400`;
- terminal state `-60`;
- flags `0xE3`.

Table-A profile 6 is `{selector=0x1510, values=255,5183,255,128}`. Applying the
confirmed scatter decoder gives:

- `VX` and `VZ`: independently random in `[-1016, 1024]`;
- `VY`: random in `[-2560, -2056]`, initially upward because negative Y is up;
- `AY`: constant `+128` per logic update.

Flag `0x08` is clear, so the target-follow/homing branch at `0x8005A308` is not used.
This is an unguided ballistic hazard, not a projectile that acquires Flik. The five
capsule births observed `VX -840..528`, `VY -2432..-2128`, and `VZ 56..936`, all
with `AY=128`.

`0x800579E0` performs eight sibling-spawner calls around a 4096-angle circle. That is
a radial presentation/effect operation around the newly constructed object; it does
not target or steer constructor 59.

## Damage and retirement

The contact walker maps action 8 to `0x80058854`. That case selects state `0x13`,
saves the contact record, and reaches `FUNC_8004A700`. Its damage-side write at
`0x8004A888` subtracts exactly one from true health. Existing invincibility and bubble
interception rules remain upstream authority; B14 does not duplicate those rows.

The generic updater provides three retirement paths:

- **Timeout:** counter `+0x22` starts at `200`, decrements once per logic update, and
  zero becomes `-1` for the second-pass finalizer.
- **Terrain/world contact:** flags bit 0 enables the terrain probe; a crossing clears
  the active counter early.
- **Player contact:** action 8 writes active `1` and state `0x13`; the next updater
  pass retires it after damage processing.

When terrain or timeout leaves state `-60`, `0x8005953C` negates that state and spawns
constructor 60 at the final coordinates. All five retained spikes hit terrain/world
geometry at ages `80, 82, 84, 80, 86` movie frames, and every one produces a matching
constructor-60 birth on its retirement frame.

## Observation, inference, and causal confirmation

- **Observation:** exact plant/contact state changes, positions, velocities, output
  frames, retirement ages, block counts, and full domain hashes reconstructed from the
  accepted capsule.
- **Inference:** the visible constructor-60 family is described as the terminal impact
  presentation; exact sprite/GPU/SFX ownership remains outside this row.
- **Causal confirmation:** pristine instructions uniquely bind type-7 selection to
  constructor 59, action 8 to damage state `0x13`, profile 6 to the ballistic law, and
  negative state `-60` to constructor-60 finalization. Type 6's no-path conclusion is
  supported by both exhaustive immediate-site census and a full natural lifecycle
  negative control.

## Phase 4 boundary

The high-value row-owned questions are closed. Strict Full would still require:

- campaign-wide plant-model/presentation census;
- exact sprite/GPU/SFX/SPU ownership for constructors 59 and 60;
- a natural constructor-59 player-hit positive control, although damage is already
  instruction-exact;
- an unobstructed natural 200-logic-update timeout control, although the counter and
  finalizer are already instruction-exact.

Those residuals cannot change the producer, damage, motion, targeting, or retirement
contract and have low B14-specific return. Reopen only if a pristine Interpreter movie
actually shows tier 3 producing a hostile object, or if a future MOD needs exact
presentation/audio ownership or a natural no-terrain timeout oracle.

## Links

- [[SYS_hostile_blue_plant_projectiles]]
- [[SYS_blue_health_power]]
- [[SYS_player_power_slot]]
- [[SYS_contact_objects_and_drops]]
- [[Whole-Game Mechanics Baseline]]
