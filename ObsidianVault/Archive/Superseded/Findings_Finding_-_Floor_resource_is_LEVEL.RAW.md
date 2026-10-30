---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Floor resource is LEVEL.RAW.md
aliases:
  - "Finding - Floor resource is LEVEL.RAW"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Floor resource is LEVEL.RAW.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Floor_resource_is_LEVEL.RAW.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Floor resource is LEVEL.RAW
type: finding
confidence: CONFIRMED
gstep: G22
tags: [finding, levelraw, collision, terrain]
---

# Finding — The floor/geometry resource file is LEVEL.RAW

> Bracketing the universal file loader pinned the geometry/floor resource to LEVEL.RAW, loaded high in the heap.

**Confidence:** CONFIRMED · **Established:** G22

## Summary
- [[FUNC_80046330]] hit #4 (ra `0x8003a390` = [[FUNC_8003A318]]) loads to dest `0x80115aac`, size `0xb6be4`.
- `dest-size = 0x801cc390 − 0x80115aac = 0xb68e4` = LEVEL.RAW's exact file size → identifies the file decisively.
- LEVEL.RAW's bytes are compressed ([[Finding - LEVEL.RAW is compressed]]); the floor/terrain/collision are the decompressor's *output*.

## Evidence
EXEC-watch at the loader callee entry caught the LEVEL.RAW load; hit #6 (control, `a1=0x801607f8`) was LEVEL.DAT. The address `0x801bdc58` (= `LEVEL.RAW+0xa81ac`) falls inside this buffer — see [[Finding - 0x801bdc58 is compressed source]].

## Related functions
[[FUNC_80046330]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]]

## Related memory structures
[[MEM - LEVEL.RAW chunk model]]

## Related experiments
n/a (live EXEC trace)

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]] · [[API - transferLog]]

## Next steps
Mapped to specific chunks: terrain=35 ([[Finding - Terrain on-disk source is chunk 35]]), collision=32 ([[Finding - Collision on-disk source is chunk 32]]).

## Source
`src_re_geometry/geometry_g22_high_heap_floor_source.md`
