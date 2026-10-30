---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/Memory Structures.md
aliases:
  - "Memory Structures"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/Memory Structures.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/Memory_Structures.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Memory Structures
type: hub
tags: [hub, memory, structures]
---

# Memory Structures — Map of Content

> RAM buffers, tables, and record layouts. Addresses are KSEG0; `$gp = 0x80081d98`. Field-level globals are in [[Symbols Index]]; the method for decoding a new one is [[Playbook - Identify structure fields]].

## Global axis
- [[MEM - Global memory map]] — executable, BSS, globals, overlay swap regions, DAT/RAW buffers, scratchpad, and stack evidence on one address axis

## Geometry — visual
- [[MEM - fcn.80010000 mesh payload]] — per-object mesh (Candidate A = editable terrain)
- [[MEM - Terrain vertex buffer 8012C1D0]] — shared mesh vertex buffer (LEVEL.RAW chunk 35; occluded terrain layer — the visible floor is LEVEL.DAT via [[FUNC_80010000]])
- [[MEM - Trail and pass3 tables]] — render cull input (the terrain-render flag lever)
- [[MEM - Survivor lists]] — LIST_A / LIST_B
- [[MEM - Parser output record]] — 484× 0x20 records after the DAT

## Geometry — collision
- [[MEM - Collision sector table 800A7E48]] — broadphase, 223× 0x30
- [[MEM - Collision plane record]] — the actual collision primitive (32-byte)

## Objects / player / sky
- [[MEM - Type-0x3f placement record]] — pickup placements (0x10)
- [[MEM - Contact array 800B0D18]] — runtime pickup contacts (64× 0x38)
- [[MEM - Player state 800A6500]] — player pos + progress counters
- [[MEM - Sky DRAWENV color cache 800771BC]] — sky recolor lever

## Maps / models
- [[MEM - DAT runtime memory map]] — where LEVEL.DAT lays out at runtime
- [[MEM - LEVEL.RAW chunk model]] — compressed-chunk → runtime pipeline

## Related
[[Symbol Map Baseline]] · [[Symbols Index]] · [[Executable and Overlays]] · [[Geometry pipeline]] · [[Playbook - Identify structure fields]] · [[Home]]
