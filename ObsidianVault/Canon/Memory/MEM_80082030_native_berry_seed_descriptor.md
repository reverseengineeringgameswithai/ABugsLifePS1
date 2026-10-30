---
kind: memory
id: MEM_80082030
aliases: [MEM_80082030, 0x80082030]
address: 0x80082030
name: native_berry_seed_descriptor
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - SYS_berry_pickup_render_descriptors
read_by:
  - FUNC_800253E8
written_by: []
related_structs: []
evidence:
  - src_re/known_crash_cave_hazards.c
  - mod/mods/registry.py
  - WHYPE_forbidden_patch_ranges
src_paths:
  - src_re/known_crash_cave_hazards.c
  - mod/mods/registry.py
patch_policy: forbidden
---

# MEM_80082030 - native_berry_seed_descriptor

## Purpose

Native berry/seed descriptor memory used by original pickup visuals.

## Confirmed behavior

- `0x80082030..0x8008203C` is native-owned descriptor data, not free scratch space.
- Overwriting this range caused seed colors to stop being purple and made mega/homing appear brownish-gold.
- Blackberry/Fastberry must use private descriptor memory instead. The current mod uses `0x80081234` and repairs `object_pointer_list[0x25]`.

## Modding policy

Do not patch or allocate code/data here for custom berry visuals. Route custom descriptors through private memory and a targeted object-pointer-list repair.

## Evidence

- `src_re/known_crash_cave_hazards.c`
- `mod/mods/registry.py`
- `WHYPE_forbidden_patch_ranges`
