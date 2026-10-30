---
kind: table
id: TABLE_8001B42C
address: 0x8001B42C
name: pickup_collect_dispatch
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - SYS_berry_pickup_render_descriptors
read_by:
  - FUNC_80053814
row_stride: 4
row_count: unknown
evidence:
  - src_re/source3f_dispatch_80053814.c
src_paths:
  - src_re/source3f_dispatch_80053814.c
patch_policy: hook_candidate_for_free_slots
---

# TABLE_8001B42C - pickup_collect_dispatch

## Purpose

Jump table used by `FUNC_80053814` for type-0x3f pickup collection behavior. The handler computes `kind - 0x10`, bounds-checks it, then indexes this table.

## Known rows

| Kind | Slot | Meaning |
|---:|---:|---|
| `0x20` | `0x10` | arm red/default berry, equip index `0` |
| `0x21` | `0x11` | arm homing/green berry, equip index `2` |
| `0x22` | `0x12` | arm gold berry, equip index `3` |
| `0x23` | `0x13` | arm blue/super berry, equip index `1` |
| `0x24` | `0x14` | arm mega/purple berry, equip index `4` |
| `0x25` | `0x15` | free native slot used by Blackberry/Fastberry mod |

## Mod boundary

The `0x25` entry is not original-game behavior. Blackberry/Fastberry redirects slot `0x15` at `0x8001B480` to `CAVE_ARM`, which stores equip index `5`.

## Evidence

See `src_re/source3f_dispatch_80053814.c`, `mod/berry_projectile.h`, and `MOD_blackberry_net_new_berry`.
