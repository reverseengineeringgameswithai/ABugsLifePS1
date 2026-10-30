---
kind: memory
id: MEM_800771BC
aliases: [MEM_800771BC, 0x800771bc, "MEM - Sky DRAWENV color cache 800771BC", "MEM - Sky DRAWENV color cache", MEM_-_Sky_DRAWENV_color_cache_800771BC]
address: 0x800771BC
name: Sky_DRAWENV_color_cache_800771BC
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

# MEM_800771BC - Sky DRAWENV color cache 800771BC

## Purpose

The **sky recolor lever**. The sky is NOT an image/bitmap — it's a GP0 0x02 background FILL whose RGB comes from these three words.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Sky DRAWENV color cache 800771BC
type: memory-structure
address: 0x800771BC
address_end: 0x800771C8
confidence: CONFIRMED
tags: [memory, sky, rendering, drawenv, g30]
---

# MEM — Sky clear-color cache `0x800771BC`

> The **sky recolor lever**. The sky is NOT an image/bitmap — it's a GP0 0x02 background FILL whose RGB comes from these three words.

| Field | Value |
|-------|-------|
| **Words** | `0x800771BC` (R), `0x800771C0` (G), `0x800771C4` (B) |
| **Copied to** | DRAWENV +0x19..0x1b, then emitted as GP0 `0x02BBGGRR` fill |
| **Fill builder** | [[FUNC_800639CC]] (builds the GP0 0x02 command each frame) |
| **On-disk source** | LEVEL.RAW color table `0x800C1688` entry 0 = `31 59 db` (chunk 32) — see [[Finding - Sky color on-disk table]] |
| **Pre-load copier** | `0x8003b2b8/0x8003b2d8/0x8003b2f8` copy table bytes 31/59/db from `0x800C1688` into the cache |

## Recolor procedure (CONFIRMED)
Patch the three cache words (or the on-disk table for a persistent change). Verified: red patch → VRAM `0x001f`; green patch → `0x03e0` after double-buffer flip. The transient submitted command copies at `0x801cc3c8 / 0x801e1384` are rebuilt every frame — **patch the upstream cache/table, not the transient command.**

## Related
- Findings: [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]] · [[Finding - GPU primitive injection]]
- Functions: [[FUNC_800639CC]]
- Experiments: [[Experiment - Starry night sky injection]] · Fixtures: [[Fixture - night starry]]
- APIs: [[API - accessLog]] · [[API - gp0Trace]] · [[API - gpu.readVramRect]] · Findings store ids: f1, f2, f3


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Sky DRAWENV color cache 800771BC.md`
- Migration status: copy-first Canon seed.
