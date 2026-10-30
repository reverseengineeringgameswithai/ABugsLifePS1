---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8003A318.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8003A318.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8003A318_high-heap_loader_+_LEVEL.RAW_decompress_orchestrator.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8003A318 — high-heap loader + LEVEL.RAW decompress orchestrator
type: function
address: 0x8003A318
confidence: CONFIRMED
tags: [function, loader, levelraw, decompress]
---
# FUNC_8003A318 — high-heap loader + LEVEL.RAW per-chunk decompress orchestrator

> Loads compressed LEVEL.RAW into the high heap, then decompresses it chunk-by-chunk and builds the runtime geometry/collision resources.

| Field | Value |
|-------|-------|
| Address | 0x8003A318 (span …0x8003C384) |
| Source file | `src_re_geometry/geometry_runtime_buffers.c` (G22–G25/G29) |
| Confidence | CONFIRMED loop structure |

## Purpose
Reads LEVEL.RAW (compressed) to `0x80115aac` (dest = `0x801cc390 − align(size)`, top-down), then runs a per-chunk loop (`0x8003a4d4`…`0x8003c250`): each chunk has a header where **word0 = decompressed size**, **word1 = compressed size**, `0xe`-byte header, `0xffffffff` = terminator. Calls the decompressor per chunk and dispatches the output to resource builders. Finalize `0x8003c2dc` sets `[gp+0x4a0]=0x801cc390`, `[gp+0x588]=fp` (decompressed cursor, tops at `0x8015fcbc`).

## Arguments / Returns
Reached indirectly via the resource dispatcher. Effect: LEVEL.RAW resident + decompressed; sector table + plane records built.

## Calls (callees)
- [[FUNC_80046330]] — file read (`0x8003a388`, ra `0x8003a390`).
- [[FUNC_8001A1DC]] — LZSS decompressor (`0x8003a4e4`, per chunk).
- [[FUNC_80030F60]] — collision sector-table builder (downstream).
- `fcn.80063508` ×2 — finalize model/display registration; candidate builders `fcn.8003cc58`, `0x800628c0/0x800625fc/0x80061a48`.

## Called by (callers)
- The resource dispatcher chain (indirect; reached during level load).

## Globals & structures touched
- `0x80115aac` LEVEL.RAW buffer · `[gp+0x588]=0x80082320` decompressed cursor · `[gp+0x4a0]` heap top `0x801cc390`. See [[MEM - LEVEL.RAW chunk model]], [[MEM - DAT runtime memory map]].

## Evidence & confidence notes
G22 bracketed LEVEL.RAW here; G25 traced the per-chunk loop live. Decompressed output tops at `0x8015fcbc` — which is why `0x801bdc58` (far above) turned out to be compressed *source*, not output ([[Finding - 0x801bdc58 is compressed source]]).

## Related
- Findings: [[Finding - Floor resource is LEVEL.RAW]] · [[Finding - LEVEL.RAW is compressed]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Collision on-disk source is chunk 32]]
- Functions: [[FUNC_8001A1DC]] · [[FUNC_80046330]] · [[FUNC_80030F60]]
- Assets: [[Asset - LEVEL.RAW]] · Memory: [[MEM - LEVEL.RAW chunk model]]
- Source docs: `src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md`
