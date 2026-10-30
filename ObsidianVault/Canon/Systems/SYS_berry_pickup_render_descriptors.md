---
kind: system
id: SYS_berry_pickup_render_descriptors
name: Berry Pickup Render Descriptors
status: live_confirmed
confidence: confirmed
source_state: original_game
functions:
  - FUNC_800253E8
  - FUNC_80053814
memory:
  - MEM_80082030
  - MEM_80096B98
  - MEM_800A6597
tables:
  - TABLE_8001B42C
constants:
  - CONST_TYPE3F_BERRY_KINDS
evidence:
  - src_re/source3f_dispatch_80053814.c
  - src_re/pickup_projector_800253e8.c
  - src_re/known_crash_cave_hazards.c
  - EXP_2026-07-07_blackberry_damage_parity
src_paths:
  - src_re/source3f_dispatch_80053814.c
  - src_re/pickup_projector_800253e8.c
  - src_re/known_crash_cave_hazards.c
patch_policy: do_not_touch_native_descriptors
---

# SYS_berry_pickup_render_descriptors

## Purpose

Canonical hub for berry pickup kinds, equip-arm dispatch, sprite descriptors, and descriptor-memory safety.

## Confirmed original-game behavior

- World berry pickups are type-0x3f entries whose kind byte drives collection behavior.
- `FUNC_80053814` reads the collected object kind, computes `kind - 0x10`, and dispatches through the pickup collection table.
- Native berry pickup kinds arm the native equip index at `0x800A6597`.
- Pickup rendering uses descriptors reachable through the object pointer list around `0x80096B98`.
- Berry/sprite color is affected by the descriptor/texpage/CLUT and by GP0 modulation.

## Native pickup kinds

| Kind | Meaning | Equip index |
|---:|---|---:|
| `0x20` | red/default berry | 0 |
| `0x21` | homing/green berry | 2 |
| `0x22` | gold berry | 3 |
| `0x23` | blue/super berry | 1 |
| `0x24` | mega/purple berry | 4 |

## Descriptor safety

`0x80082030..0x8008203C` is native berry/seed descriptor memory. It is not scratch space.

A bad Blackberry implementation reused this region and caused two user-visible regressions:

- seed colors stopped being purple;
- mega/homing visuals became brownish-gold.

The safe current pattern for a modded pickup is to use private descriptor memory, then repair only that modded kind's `object_pointer_list` entry. Blackberry uses private descriptor `0x80081234` for kind `0x25`.

## Mod boundary

Blackberry's kind `0x25`, equip index `5`, private descriptor `0x80081234`, and dark color word `0x2c2b051a` are mod behavior. Do not document them as native pickup semantics.

## Do not promote

- Do not reuse `0x80082030..0x8008203C`.
- Do not use global descriptor edits to color one custom berry.
- Do not assume a visually correct custom berry leaves native seed/mega visuals intact without verifying descriptor ownership.

## Evidence

- `src_re/known_crash_cave_hazards.c` records the descriptor-regression failure.
- `mod/mods/registry.py` rejects `0x80082030..0x8008203C` as a forbidden code range because it is live descriptor data, not executable cave space.
- `MOD_blackberry_net_new_berry` documents the current private-descriptor repair path.
