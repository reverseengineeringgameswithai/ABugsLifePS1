---
kind: function
id: FUNC_80049C30
aliases: [FUNC_80049C30, 0x80049C30, enemy_reinstantiate_from_spawn]
address: 0x80049C30
name: enemy_reinstantiate_from_spawn
status: static_confirmed
confidence: confirmed
source_state: original_game
system: [SYS_enemy_spawn_update]
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - EXP_2026-08-03_phase4_d05_death_respawn
  - analysis/phase4_d05_static_resolution.json
src_paths:
  - tools/phase4_d05_static.c
  - src_re/enemy_respawn_scheduler.c
patch_policy: safe_to_read
---

# FUNC 0x80049C30 - enemy reinstantiate from spawn template

## Corrected entry and callers

`0x80049C2C` is a padding NOP. The functional entry and actual `JAL` target is
`0x80049C30`. A whole-pristine-EXE C scan finds exactly two direct callers:

- `0x8004A664`: construction/initialization path.
- `0x8004D3F0`: runtime KO respawn scheduler path.

The earlier zero-xref result queried the padding address and is superseded; an
indirect runtime call is not required to explain the observed HP writer.

## Reinstantiation

The routine rebuilds the actor from the spawn template referenced at actor
`+0x80`: template ID and coordinates, behavior program selection, HP, respawn
delay seed, and flags are restored while transient motion/reaction state is
cleared. The exact HP restore instruction is `0x80049CA0: sh ...,0x6e(...)`;
DuckStation's access callback can report the post-instruction PC `0x80049CA4`.
The template delay seed is stored at actor `+0x62` by `0x80049CC0`.

## Evidence

- Pristine executable SHA-256: `1aa28954a1871d0799bf306a5ae746d17b143fce6d1965740f798862be519d20`
- `tools/phase4_d05_static.c`
- `analysis/phase4_d05_static_resolution.json`
- `src_re/enemy_respawn_scheduler.c`
