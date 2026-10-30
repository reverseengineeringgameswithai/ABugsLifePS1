---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Contact array 800B0D18.md
aliases:
  - "MEM - Contact array 800B0D18"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Contact array 800B0D18.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Contact_array_800B0D18.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

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
| +0x0c…0x18 | render_attr[4] | render/texture attrs (from table A via `fcn.800593e8`) |
| +0x20 | action_id | walker dispatch id → table `0x8001B570[action_id-2]` |
| +0x22 | active_type | live gate (>0) |
| +0x28 | radius_add | contact radius = `0x12c + this` |
| +0x2c | state | grain disc 22 for ctor 0x51; walker writes state |
| +0x33 | flags | bit1(0x2)=enabled, bit7(0x80)=alloc-occupied |

## Contact math (CONFIRMED — in [[FUNC_800586B0]])
`dx=((pX-rx)*0x300)>>13`, `dy=((pY-ry)*0x100)>>13`, `dz=((pZ-rz)*0x300)>>13`; contact if `dx²+dy²+dz² < radius²`. Live gate: `lh rec+0x22 > 0 AND (lbu rec+0x33 & 2)`.

> [!note] Allocator has a documented **capacity hang risk**: no full-array escape; if all 64 slots are occupied it can spin.

## Related
- Functions: [[FUNC_80059E44]] · [[FUNC_800586B0]] · [[FUNC_80053814]]
- System hub: [[LEVEL.DAT object pipeline]] · [[Physics]]
- Globals: metadata table B `0x8007941C`, table A `0x80079E30`, walker dispatch `0x8001B570` — see [[Symbols Index]]
