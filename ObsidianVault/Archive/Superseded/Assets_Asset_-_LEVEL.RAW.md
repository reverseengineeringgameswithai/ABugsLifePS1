---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - LEVEL.RAW.md
aliases:
  - "Asset - LEVEL.RAW"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - LEVEL.RAW.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_LEVEL.RAW.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - LEVEL.RAW
type: asset
confidence: CONFIRMED
tags: [asset, levelraw, geometry, collision, compression]
---
# Asset — LEVEL.RAW

> Per-level **compressed** geometry blob. Source of BOTH the terrain-mesh layer (chunk 35, occluded at render) and the collision geometry (chunk 32) — the key realization of G22–G30. *(The **visible** walkable floor is LEVEL.DAT via [[FUNC_80010000]], f13 — see [[Finding - Visible terrain renderer]].)*

## Summary
LEVEL.RAW is loaded compressed into high RAM, then decompressed per-chunk. Different chunks feed different consumers: **chunk 35 = the terrain-mesh layer** (buffer `0x8012c1d0`; renders *occluded* in tested scenes — the **visible** walkable floor is LEVEL.DAT via [[FUNC_80010000]] (f13), see [[Finding - Visible terrain renderer]]), **chunk 32 = collision plane geometry + the sky color table**.

## Format / layout
- Compressed container; per-chunk: BE32 `word0` = decompressed size, `word1` = compressed size, `0xe`-byte header, `0xffffffff` = terminator. See [[MEM - LEVEL.RAW chunk model]].
- Custom **LZSS/LZ77** codec (MSB-first bitstream) — decoded by [[FUNC_8001A1DC]] (structure confirmed; exact length/distance tables not byte-exact → no offline decoder yet = the **LZ codec gate** for permanent disc edits).

## Where it lives
- **Disk:** LEVEL01 CD **LBA 1823–4149**.
- **Runtime (compressed):** load base `0x80115aac`, size `0xb6be4`, range `[0x80115aac, 0x801cc690)`.
- **Decompressed outputs:** terrain → buffer `0x8012c1d0` ([[MEM - Terrain vertex buffer 8012C1D0]]); collision planes → `~0x800D0xxx`/`0x800F7xxx`, built into the sector table `0x800a7e48` ([[MEM - Collision sector table 800A7E48]]); sky color table → `0x800c1688`.

## How it's loaded / parsed
[[FUNC_80046330]] reads it (hit #4, ra `0x8003a390`); orchestrator [[FUNC_8003A318]] runs the per-chunk decompress loop, calling [[FUNC_8001A1DC]] each chunk and dispatching the output to builders (e.g. sector-table converter [[FUNC_80030F60]]).

## Edit path
- **Today (RAM/save-state):** edit the decompressed buffers directly (terrain buffer / sector table). See [[Experiment - G30 localized terrain edit]], [[Experiment - G29 collision lever validation]].
- **Permanent (disc):** blocked on completing the LZSS codec (decompress → edit → recompress). See [[Open Questions]].
- Inspect chunks: `tools/parse_level_raw_chunks.py` (maps a runtime addr → chunk).

## Related
- Findings: [[Finding - LEVEL.RAW is compressed]] · [[Finding - Floor resource is LEVEL.RAW]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Collision on-disk source is chunk 32]] · [[Finding - 0x801bdc58 is compressed source]]
- Functions: [[FUNC_8001A1DC]] · [[FUNC_8003A318]] · [[FUNC_80030F60]] · Structures: [[MEM - LEVEL.RAW chunk model]]
- Docs: `src_re_geometry/geometry_g22_high_heap_floor_source.md` … `geometry_g25_level_raw_post_decompress_trace.md`
