---
kind: memory
id: MEM_800B0D18
aliases: [MEM_800B0D18, 0x800b0d18, "MEM - Contact array 800B0D18", "MEM - Contact array", MEM_-_Contact_array_800B0D18]
address: 0x800B0D18
name: Contact_array_800B0D18
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: unknown
---

# MEM_800B0D18 - Contact array 800B0D18

## Purpose

The 64-slot runtime array of active pickup "contact" entities. **This is pickup-proximity, NOT world floor collision.**

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Contact array 800B0D18
type: memory-structure
address: 0x800B0D18
confidence: CONFIRMED
tags: [memory, contact, pickup]
---

# MEM — Contact / pickup record array `0x800B0D18`

> The 64-slot runtime array of active pickup "contact" entities. **This is pickup-proximity, NOT world floor collision.**

| Field | Value |
|-------|-------|
| **Base** | `0x800B0D18` |
| **Count / stride** | 64 records × `0x38` |
| **Alloc cursor** | `0x8008234C` (pre-increment, wraps at 0x40) |
| **Filled by** | [[FUNC_80059E44]] (contact_alloc) from metadata tables A (`0x80079E30`) + B (`0x8007941C`) |
| **Walked by** | [[FUNC_800586B0]] (contact walker) |

## Record layout (0x38, CONFIRMED — selected fields)
| Offset | Field | Meaning |
|--------|-------|---------|
| +0x00/04/08 | x/y/z | runtime coords (file<<5) |
| +0x0c/10/14 | vel_X/Y/Z | **velocity**, integrated every tick by the updater `0x8005A308` (`pos += vel`) |
| +0x18 | accel_Y | added into `+0x10` each tick. All four come from table A via `fcn.800593e8` |
| +0x20 | action_id | walker dispatch id → table `0x8001B570[action_id-2]`; **= metaB[ctorType]+0x00** |
| +0x22 | active_type | live gate (>0); also the **lifetime counter** — the updater decrements it for every live record |
| +0x24/0x26 | anim timer | `+0x26` counts down from `+0x24`, stepping `+0x31` modulo `+0x30` |
| +0x28 | radius_add | contact radius = `0x12c + this` |
| +0x2c | state | grain disc 22 for ctor 0x51; walker writes state |
| +0x2e | ctor_signed | **the only field naming the ctorType at runtime**: `0`, `+ctorType`, or `-ctorType` per `metaB+0x0E`. A pool census must key on this (ctor `0x5A` reads `0xA6`). Also selects the colour-fade arm |
| +0x2f | behaviour_class | `= metaB[ctorType]+0x0F` → [[TABLE_8001B7F0_contact_behaviour_class_dispatch]]`[c-1]`; `0` = no handler |
| +0x30/0x31 | anim frames / cur | frame count and current frame |
| +0x33 | flags | **each bit gates a different consumer** — see below. `bit7(0x80)`=alloc-occupied |
| +0x34/35/36 | colour R/G/B | fade, driven by remaining `+0x22` from `metaB+0x11/12/13` |

## Contact math (CONFIRMED — in [[FUNC_800586B0]])
`dx=((pX-rx)*0x300)>>13`, `dy=((pY-ry)*0x100)>>13`, `dz=((pZ-rz)*0x300)>>13`; contact if `dx²+dy²+dz² < radius²`. Live gate: `lh rec+0x22 > 0 AND (lbu rec+0x33 & 2)`.

## flags `+0x33` — one bit per consumer (do NOT read bit 0x02 as a general "enabled")
| bit | gate PC | consumer |
|---|---|---|
| `0x01` | `0x8005A5A8` | ground-collision branch in the updater |
| `0x02` | `0x80058748` | pickup walker [[FUNC_800586B0]] — this bit **only** |
| `0x04` | `0x80058C6C` | contact-vs-actor `0x80058AF8` |
| `0x08` | `0x8005A358` | berry-projectile branch in the updater |
| `0x20`/`0x40` | — | no consumer located (`0x20` on 116/129 metaB rows) |
| `0x80` | — | alloc-occupied |

A ctor type whose flags clear `0x02`/`0x04`/`0x08` **and** whose `+0x2F` is `0` reaches no
gameplay consumer at all — it is still rendered, because
`contact_billboard_render` (`0x80014844`) gates only on `+0x22 != 0` with no flags test.
Worked example: ctor `0x5A`, the Tunnels falling debris, in
[[EXP_2026-08-04_phase4_f02_debris_damage_class]].

> [!note] Allocator has a documented **capacity hang risk**: no full-array escape; if all 64 slots are occupied it can spin.

## Related
- Functions: [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[FUNC_80053814]]
- System hub: [[LEVEL.DAT object pipeline]] · [[Physics]]
- Globals: metadata table B `0x8007941C`, table A `0x80079E30`, walker dispatch `0x8001B570` — see [[Symbols Index]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Contact array 800B0D18.md`
- Migration status: copy-first Canon seed.
