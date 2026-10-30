---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Collision on-disk source is chunk 32.md
aliases:
  - "Finding - Collision on-disk source is chunk 32"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Collision on-disk source is chunk 32.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Collision_on-disk_source_is_chunk_32.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Collision on-disk source is chunk 32
type: finding
confidence: CONFIRMED
gstep: G29/G30
tags: [finding, collision, levelraw, chunk32]
---

# Finding — Collision on-disk source = LEVEL.RAW chunk 32

> The collision plane geometry (and the sky color table) live in LEVEL.RAW **chunk 32**, decompressed at load and converted into the sector table.

**Confidence:** CONFIRMED · **Established:** G29 / G30 · **Findings-store id:** f11

## Summary
- LEVEL01/LEVEL.RAW **chunk 32**: file offset `0x492cf`, compressed `0x2c80f` → decompressed `0x39d90`.
- Decompressor [[FUNC_8001A1DC]] writes the plane block (`0x800c1690`, planes `0x800D0xxx`); accessLog WRITE hits at `0x8001a654 / 0x8001a678`.
- Sector table `0x800a7e48` is then built post-decompress by converter [[FUNC_80030F60]] (`0x80030fac/0x80030fd8`).
- Chunk 32 **also** holds the sky color table `0x800c1688` — see [[Finding - Sky color on-disk table]].

## Evidence
- accessLog WRITE-watch inside the decompressor caught the plane record `0x800D10E8` being written; offline chunk map (`tools/parse_level_raw_chunks.py`) maps `0x800c1688`/the plane block to chunk 32.

## Related functions
[[FUNC_8001A1DC]] · [[FUNC_8003A318]] · [[FUNC_80030F60]]

## Related memory structures
[[MEM - LEVEL.RAW chunk model]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]]

## Related experiments
[[Experiment - G29 collision lever validation]]

## Related fixtures / save states
`SCUS-94288_2.sav` (pre-load) · [[Fixture - g30 openground]]

## DuckStation APIs used
[[API - accessLog]] · [[API - transferLog]] (CD LBA provenance)

## Next steps
LZ codec gate blocks a permanent disc patch — see [[Finding - LEVEL.RAW is compressed]].

## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`, `geometry_g30_terrain_render_source_plan.md` §18; findings-store f11
