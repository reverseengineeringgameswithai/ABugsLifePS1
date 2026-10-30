---
kind: system
id: SYS_seed_plant_behaviors
name: Seed Plant Behaviors
status: static_seen
confidence: confirmed
source_state: original_game
functions:
  - FUNC_8005BDBC
  - FUNC_8005C6F0
  - FUNC_8005CA7C
  - FUNC_8005CA24
  - FUNC_8005C918
memory:
  - MEM_800A6597
  - MEM_800A658E
tables: []
constants:
  - CONST_SEED_PLANT_TYPES
evidence:
  - src_re/purple_seed_plants.c
  - src_re/yellow_seed_plants.c
  - src_re/blue_seed_plants.c
  - src_re/brown_seed_plants.c
  - src_re/green_seed_plants.c
src_paths:
  - src_re/purple_seed_plants.c
  - src_re/yellow_seed_plants.c
  - src_re/blue_seed_plants.c
  - src_re/brown_seed_plants.c
  - src_re/green_seed_plants.c
---

# SYS_seed_plant_behaviors

## Purpose

Canonical hub for seed plant behavior lanes, especially berry-grant plants and the Mine Plant permanent-kill lane.

## Purple seed berry grants

Purple seed plants use plant type `6`, the berry-carrier handler at `0x8005C6F0`, and per-tier extras to spawn one berry-grant contact object.

| Tier | Extra | Grant type | Contact action | Equip result |
|---:|---:|---:|---:|---|
| 1 | `0x4000` | `0x23` / type 35 | 35 | blue/super, equip 1 |
| 2 | `0x2000` | `0x21` / type 33 | 33 | homing, equip 2 |
| 3 | `0x1000` | `0x20` / type 32 | 36 | mega, equip 4 |
| 4 | `0x3000` | `0x22` / type 34 | 34 | gold, equip 3 |

These are native contact-object grant types. They are not the Gold Berry token mod.

## Yellow seed permanent lane

Yellow Mine Plant explosions are the second confirmed permanent-kill source:

- Gold Berry permanent lane: hit-record `+0x24 == 11`.
- Mine Plant permanent lane: hit-record `+0x27 == 6`.

Shooters from yellow seed plants fire berry-like contact objects but are not the same as Flik's equipped berry dispatch and do not make their kills permanent unless they use the confirmed permanent lane.

## Descriptor relevance

Seed and berry plant visuals depend on native descriptor/CLUT state. Do not repurpose native descriptor memory for modded berries. In particular, `0x80082030..0x8008203C` must remain native-owned; overwriting it caused seed color and mega/homing color regressions.

## Mod boundary

Blackberry and Gold Berry token behavior are mod-only. Seed plant Canon should describe the original game unless a mod explicitly changes a seed/plant behavior.

## Evidence

- `src_re/purple_seed_plants.c` documents the purple berry-grant map.
- `src_re/yellow_seed_plants.c` documents the Mine Plant permanent lane.
- `src_re/known_crash_cave_hazards.c` documents the descriptor regression that affected seed and mega/homing colors.
