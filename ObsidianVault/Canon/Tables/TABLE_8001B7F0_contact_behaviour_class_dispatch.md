---
kind: table
id: TABLE_8001B7F0
address: 0x8001B7F0
name: contact_behaviour_class_dispatch
status: confirmed
confidence: high
source_state: original_game
created: 2026-08-04
system:
  - Contact object pool
  - Contact Objects and Drops
read_by:
  - FUNC_8005A308
row_stride: 4
row_count: 14
evidence:
  - tools/phase4_f02_debris_class_bind.c
  - analysis/phase4_f02_debris_class_bind.json
  - EXP_2026-08-04_phase4_f02_debris_damage_class
patch_policy: do_not_touch
---

# TABLE_8001B7F0 — contact_behaviour_class_dispatch

## Purpose

The **second, independent** dispatch over contact-pool records, and the one that is easy to
miss because [[TABLE_8001B570_contact_action_dispatch]] is the well-known one.

[[TABLE_8001B570_contact_action_dispatch]] is keyed by `action_id` (`record+0x20`) and is reached only from the
*pickup walker* `FUNC_800586B0`, after that walker's flags gate. This table is keyed by the
**behaviour class** `record+0x2F` and is reached from the per-frame record updater
`FUNC_8005A308`, on a different gate. A contact object that is not a pickup does whatever it
does through *this* table.

## Indexing

```
0x8005A8E8  lbu   v0, rec+0x2F
            idx = v0 - 1
0x8005A8F4  sltiu (uint32_t)idx < 0xE          ; out of range -> 0x8005B098 (shared tail)
0x8005A910  jr    [0x8001B7F0 + idx*4]
```

`record+0x2F` comes from `metaB[ctorType] + 0x0F` (metadata B at `0x8007941C`, stride
`0x14`). **Class `0x00` therefore has no handler**: `idx = -1` fails the unsigned range test.
95 of the 129 ctor types are class `0x00`.

## Rows

| class | handler | ctor types |
|---|---|---|
| `0x01` | `0x8005A918` | `0x02 0x05 0x0B 0x42 0x4E 0x6B` |
| `0x02` | `0x8005A978` | `0x28 0x29 0x2A 0x2B 0x3C 0x46 0x68` |
| `0x03` | `0x8005B098` (shared tail) | `0x00 0x34` |
| `0x04` | `0x8005B098` (shared tail) | `0x35` |
| `0x05` | `0x8005B098` (shared tail) | `0x20 0x21 0x22 0x23` |
| `0x06` | `0x8005B098` (shared tail) | `0x1A 0x38` |
| `0x07` | `0x8005A9F4` | `0x1F` |
| `0x08` | `0x8005AAF8` | `0x3E` |
| `0x09` | `0x8005AB54` | `0x40` |
| `0x0A` | `0x8005AB80` | `0x4D` |
| `0x0B` | `0x8005ABC8` | `0x6D` |
| `0x0C` | `0x8005ABE4` | `0x08 0x10` |
| `0x0D` | `0x8005AE1C` | `0x2D 0x30 0x43 0x44` |
| `0x0E` | `0x8005B070` | `0x7A` |
| `0x00` | *no handler* | 95 ctor types, including `0x5A` (Tunnels falling debris) |

Classes `0x03`–`0x06` resolve to `0x8005B098`, which is the loop's own shared no-op tail —
those classes are dispatched but do nothing extra.

## Evidence

Regenerate with `tools/phase4_f02_debris_class_bind.c`. Discovered while closing
F02_tunnels; see [[EXP_2026-08-04_phase4_f02_debris_damage_class]].

## Related

[[TABLE_8001B570_contact_action_dispatch]], [[SYS_contact_object_pool]], [[FUNC_80059E44]]
