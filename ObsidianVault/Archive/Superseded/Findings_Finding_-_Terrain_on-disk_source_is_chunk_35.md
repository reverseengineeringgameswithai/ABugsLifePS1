---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Terrain on-disk source is chunk 35.md
aliases:
  - "Finding - Terrain on-disk source is chunk 35"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Terrain on-disk source is chunk 35.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Terrain_on-disk_source_is_chunk_35.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Terrain on-disk source is chunk 35
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, rendering, terrain, levelraw, chunk35]
---

# Finding — `fcn.800172dc` mesh-buffer on-disk source = LEVEL.RAW chunk 35

> The `0x8012c1d0` mesh vertex buffer is decompressed from LEVEL.RAW **chunk 35** at level load. *(The chunk→buffer mapping is solid; the old "visible terrain" label is superseded — see callout.)*

**Confidence:** CONFIRMED *(chunk-35→buffer mapping)* · **Established:** G30 · **Findings-store id:** f10 *(visible-floor claim SUPERSEDED 2026-06-20)*

> [!warning] "Visible" is superseded/contested (GAP-0009/0011/0038)
> The 7-scene neutralize ([[Experiment - Visible floor renderer neutralize]]) found this buffer's renderer ([[FUNC_800172DC]]) contributes **~0 visible px (occluded)**; the **visible floor = LEVEL.DAT via [[FUNC_80010000]]** (f13). Chunk 35 feeds the **occluded** general-mesh buffer, **not** the visible walkable floor. The decompress mapping below is unaffected.

## Summary
- LEVEL01/LEVEL.RAW **chunk 35**: file offset `0x9908a`, compressed `0x1b24` → decompressed `0x34f4`.
- Decompressed by [[FUNC_8001A1DC]] into the persistent terrain buffer [[MEM - Terrain vertex buffer 8012C1D0]] (write PCs `0x8001a5e8 / 0x8001a5f0 / 0x8001a678`).
- The buffer is consumed by [[FUNC_800172DC]] — see [[Finding - Visible terrain renderer]].
- Level data streams from CD **LBA 1823–4149** (transferLog).

## Evidence
- Offline chunk map (`tools/parse_level_raw_chunks.py`) + accessLog WRITE-watch in the decompressor tie the buffer to chunk 35; transferLog gave the CD LBA range.

## Related functions
[[FUNC_8001A1DC]] · [[FUNC_8003A318]] · [[FUNC_800172DC]]

## Related memory structures
[[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - LEVEL.RAW chunk model]]

## Related experiments
[[Experiment - G30 localized terrain edit]]

## Related fixtures / save states
`SCUS-94288_2.sav` (pre-load) · [[Fixture - g30 openground]]

## DuckStation APIs used
[[API - accessLog]] · [[API - transferLog]]

## Next steps
Permanent disc edit of chunk 35 needs the [[Finding - LEVEL.RAW is compressed|LZ codec]]; RAM/save-state edits work today.

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §17; findings-store f10
