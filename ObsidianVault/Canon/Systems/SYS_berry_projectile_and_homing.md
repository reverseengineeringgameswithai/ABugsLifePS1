---
kind: system
id: SYS_berry_projectile_and_homing
name: Berry Projectile and Homing
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_80047170
  - FUNC_8005A0E0
  - FUNC_8005A308
  - FUNC_8005743C
memory:
  - MEM_800B0D18
  - MEM_8007941C
  - MEM_800A6597
  - MEM_80090748
tables:
  - TABLE_8007941C
constants:
  - CONST_BERRY_THROW_TYPES
evidence:
  - src_re/berry_throw_80047170.c
  - src_re/berry_homing.c
  - mod/berry_projectile.h
  - EXP_2026-07-07_blackberry_damage_parity
src_paths:
  - src_re/berry_throw_80047170.c
  - src_re/berry_homing.c
  - mod/berry_projectile.h
---

# SYS_berry_projectile_and_homing

## Purpose

Canonical original-game model for thrown berries, contact-object projectile records, homing acquisition, throw class, speed/gravity inputs, and enemy-damage routing.

## Confirmed original-game behavior

- Thrown berries are contact-array records in `0x800B0D18`.
- The throw dispatch at `0x80047170` reads equipped berry index `0x800A6597` and routes native indexes `0..4`.
- Native throw classes are red `2`, blue `5`, homing `8`, gold `11`, and mega `45`.
- `contact_object_spawn` receives position, velocity, gravity, and throw class from its caller. Initial throw speed is not a parameter-table field.
- Homing and mega use a two-object path: a primary berry spawns a homing projectile with the homing flag set.
- Homing target acquisition scans `0x80090748`, filters targetable/not-hit enemies, and chooses nearest in XZ.
- Damage has two relevant decoded lanes: the actor-local `enemy+0x6e` counter branch and the side HP-table branch. The side HP table is not the kill definition.
- Permanent enemy kills are handled separately by `SYS_enemy_death_and_permanence`.

## Confirmed native rows

| Berry | Equip index | Throw class | Homing behavior |
|---|---:|---:|---|
| red | 0 | 2 | straight |
| blue/super | 1 | 5 | straight |
| homing | 2 | 8 primary, 16 projectile | homing projectile |
| gold | 3 | 11 | straight, permanent-kill class |
| mega | 4 | 45 primary, 48 projectile | homing projectile |

## Mod boundary

Blackberry/Fastberry is not original-game behavior. It uses the native red straight-throw path and modifies only the modded equip-index-5 lane. See `MOD_blackberry_net_new_berry`.

Gold Berry token pickup is also not original-game berry projectile behavior. See `MOD_gold_berry_token_drop`.

## Do not promote

- Do not treat parameter-table `+0xe`, `+8`, or `+0xa` as speed/damage without new evidence.
- Do not claim mega/homing berry kills are permanent.
- Do not make Blackberry damage parity depend on only one lane; it needs red throw class and red HP selector.

## Evidence

- `src_re/berry_throw_80047170.c` documents the throw ABI and Blackberry implications.
- `src_re/berry_homing.c` documents nearest-target acquisition.
- `mod/berry_projectile.h` preserves the decoded contact record, parameter-table, and damage notes.

## Phase 4 A08 static closure (2026-08-03)

The native row is now closed to bounded-exhaustion depth by a C analyzer over the hash-verified pristine executable and retained ASM. Machine evidence is in `analysis/phase4_a08_static.json` and `analysis/phase4_a08_bounded_exhaustion.json`.

Square admission is an active-low new-press edge. The player writes action state `18`; the sole berry constructor call occurs later when state reaches `10`. Direct denials are action state `>=7`, owned count `0x800A6596 >=4`, player `+0xA3 !=0`, carried-object gate `0x800A657A !=0`, mode `+0x88` in `{8,10,13,17}`, latch `+0x9E >=12`, or player `+0x84 !=0`.

"Straight" has a more precise meaning than the earlier summary implied. Red, blue, and gold call `0x80046D24`, which selects the nearest eligible enemy in a heading cone and calculates a lead-adjusted ballistic launch. Eligibility is state mask `0x1` set and `0xA0` clear; lead horizon is `min(floor(sqrt(distance_squared)/96),30)`. With no target, heading is unchanged and `vy=-2048`. Shared velocity is `vx=3*(sin(h)>>4)`, `vz=3*(sin(h+1024)>>4)`, gravity `128`; the update is `pos += velocity`, then `vy += gravity`.

Homing type `8` transfers ownership to child type `16`, and mega type `45` to child type `48`; no-target fallbacks use the same terminal cleanup subtypes. Children use the common quarter-error turn law and vertical adjustment clamp `[-1024,1024]`. Each accepted throw increments `0x800A6596` once, and every straight or transferred terminal lane decrements it once.

Direct retirement causes are timer zero, floor intersection, far-distance cull, missing required active/render flags, and homing target hit/invalid state. Cleanup is `0 -> -1 -> 0` followed by the subtype dispatcher at `0x8005953C`. Accepted construction calls sound id `2` through `0x8005044C`.

## Phase 4 C10 Gold closure (2026-08-04)

Gold equip index `3` creates type `11`, action `2`, timer `100`, initial subtype `4`, and selector `127`. Direct actor contact rewrites subtype `4` to marker `11`, stages timer `1`, and applies exact `-4` to the contacted actor.

Impact is not splash damage. Terminal subtype `11` emits sixteen ctor `12/13` action-3 presentation records plus a positional effect and sound; the burst rows lack projectile/occupied bit `0x80`. Both subtype `4` retirement and impact subtype `11` decrement owned count `0x800A6596` once. See [[SYS_gold_berry]] and [[EXP_2026-08-04_phase4_c10_gold_berry]].
