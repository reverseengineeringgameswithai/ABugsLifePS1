---
kind: memory
id: MEM_800D0000
aliases: [MEM_800D0000, 0x800d0000, "MEM - Collision plane record"]
address: 0x800D0000
name: Collision_plane_record
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

# MEM_800D0000 - Collision plane record

## Purpose

The actual collision primitive Flik stands on: an oriented plane, pointed to by a [[MEM - Collision sector table 800A7E48|sector record]].

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Collision plane record
type: memory-structure
address: 0x800D0000
confidence: CONFIRMED
tags: [memory, collision, g29]
---

# MEM — Collision plane record (32-byte, `~0x800D0xxx`)

> The actual collision primitive Flik stands on: an oriented plane, pointed to by a [[MEM - Collision sector table 800A7E48|sector record]].

| Field | Value |
|-------|-------|
| Location | heap blocks `~0x800C/0x800D` (e.g. plane `0x800D10E8`) |
| Stride | 32 bytes |
| Reached via | `[sector+0x10]` from [[MEM - Collision sector table 800A7E48]] |
| On-disk | LEVEL.RAW chunk 32 — see [[Finding - Collision on-disk source is chunk 32]] |

## Layout (CONFIRMED — G29)
| Offset | Meaning |
|--------|---------|
| +0x00 / +0x02 / +0x04 | plane normal (s16) |
| +0x06 / +0x08 / +0x0a | reference point (s16) |
| +0x0c … +0x16 | face edges |

## Role
The resolver [[FUNC_800345CC]] does a swept plane-distance clamp against these (stop-with-skin `−0xc0`), gated by a point-in-face test (`0x80032610`). The floor is therefore a **set of planes**, not a scalar — see [[Finding - Collision is planes not scalar]].

## On-disk byte map (CONFIRMED 2026-06-18, B18)
- Decompressed **chunk 32** (LEVEL.RAW-decomp off `0x96cd8`, len `0x39d90`) loads **linearly** to live RAM base **`0x800C1688`** (header included; starts `03 01 00 00 b6 b2 …`; the sky-color table is at offset 0).
- **`live_addr = 0x800C1688 + chunk32_off`** (and back). The plane records are **raw decompressor output** — they byte-match the offline decode verbatim, which reconciles the provenance dispute: **planes = decompressor output**; the **sector table** `0x800a7e48` is the converter's *separate* product ([[FUNC_80030F60]]).
- Example: plane `0x800D10E8` → chunk32 off **`0xfa60`** → LEVEL.RAW-decomp `0xa6738`. **Permanent edit (byte-precise):** decode chunk 32 → edit the s16 normal/refpt at `chunk32_off` → recompress chunk 32 → splice; a live `scatterWrite` at the plane address is the same edit. → [[SYS_collision_and_floor_planes|current collision and floor-plane status]].

## Related
- Functions: [[FUNC_800345CC]] · [[FUNC_8003633C]] · [[FUNC_80030F60]] · [[FUNC_8001A1DC]]
- Structures: [[MEM - Collision sector table 800A7E48]] · [[MEM - LEVEL.RAW chunk model]]
- Findings: [[Finding - Collision is planes not scalar]] · [[Finding - Collision sector table]]
- Experiments: [[Experiment - G29 collision lever validation]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Collision plane record.md`
- Migration status: copy-first Canon seed.
