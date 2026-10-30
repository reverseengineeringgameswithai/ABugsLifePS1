---
kind: system
id: SYS_mine_plant
name: Mine Plant
status: static_confirmed_runtime_behavior_control
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8005BDBC
  - FUNC_8005C918
  - FUNC_80052508
  - FUNC_80059E44
  - FUNC_800583F4
memory:
  - MEM_800A658E
evidence:
  - EXP_2026-08-03_phase4_b13_mine_plant
  - analysis/phase4_b13_mine_plant.json
src_paths:
  - src_re/yellow_seed_plants.c
  - src_re/enemy_death_permanence.c
---

# Mine Plant

## Retail identity

Yellow seed tiers 3 and 4 both select plant type 11. The mature plant walker routes
type 11 through dispatch index 9 to `seed_plant_mine_handler` at `0x8005C918`.

## Planted trigger

State `slot+0x02 == 1` is armed. The handler scans the enemy actor pointer table at
`0x80090748`, ignores candidates with `enemy+0x5C & 0x00A0`, and triggers on a strict
three-axis fixed-point sphere test below radius 150. It does not scan the player, so
Flik standing near a planted mine does not trigger it.

## Explosion

State 2 with animation word `0x00060000` allocates constructor 56 at the mine
coordinates. Its collision-visible values are radius components `2000, 2000`, damage
class `0`, and marker `6`. Damage class 0 subtracts 2 from the enemy-local hit counter;
the mine is not a universal instant-kill override.

The explosion effect helper emits 24 alternating constructor-12/13 debris records,
gates positional sound, and plays sound 13. Do not count those records as 24 proven
independent damage hits.

## Permanent death

If the `-2` hit is lethal, marker `6` selects the permanent lane in
`contact_vs_actor_handler`. The native death tail writes the 999 marker and hit state,
then decrements the per-level permanence quota at `0x800A658E`. A nonlethal mine hit
does not decrement the quota.

## Player and throw boundary

Flik proximity cannot arm the planted mine. A separate terminal branch may route a
marked overlap through the shared player-damage handler, so trigger safety is not a
claim of blast immunity.

An accepted Interpreter D02 movie behaviorally confirms that a carried mine can be
thrown into an enemy. The exact instruction that converts the carried/thrown form into
terminal blast state remains a bounded, low-return residual.

## Evidence boundary

The retained B13 capsule is integrity-valid but contains no type-11 plant, no quota
change, and no mine/permanence block coverage. It is negative-control evidence only.
Full hashes and the C-against-ASM derivation are in
[[EXP_2026-08-03_phase4_b13_mine_plant]].

