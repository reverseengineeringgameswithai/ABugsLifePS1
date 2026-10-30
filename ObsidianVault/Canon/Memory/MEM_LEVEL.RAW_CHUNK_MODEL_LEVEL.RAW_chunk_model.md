---
kind: memory
id: MEM_LEVEL.RAW_CHUNK_MODEL
aliases: [MEM_LEVEL.RAW_CHUNK_MODEL, "MEM - LEVEL.RAW chunk model"]
address: unknown
name: LEVEL.RAW_chunk_model
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

# MEM_LEVEL.RAW_CHUNK_MODEL - LEVEL.RAW chunk model

## Purpose

How the compressed LEVEL.RAW becomes runtime terrain + collision. The two most important chunks for the geometry project are **32** (collision + sky color) and **35** (visible terrain).

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - LEVEL.RAW chunk model
type: memory-structure
confidence: CONFIRMED
tags: [memory, levelraw, compression, terrain, collision]
---

# MEM — LEVEL.RAW chunk model

> How the compressed LEVEL.RAW becomes runtime terrain + collision. The two most important chunks for the geometry project are **32** (collision + sky color) and **35** (visible terrain).

## Load + decompress pipeline
1. [[FUNC_80046330]] loads compressed LEVEL.RAW to `0x80115aac` (size `0xb6be4`), high in the heap. See [[Finding - Floor resource is LEVEL.RAW]].
2. [[FUNC_8003A318]] walks it **per chunk**: each chunk has a header (`0xe` bytes) with `word0` = decompressed size, `word1` = compressed size (both **big-endian**); `0xffffffff` = terminator.
3. [[FUNC_8001A1DC]] LZSS-decompresses each chunk into the output cursor `[gp+0x588]` (tops at `0x8015fcbc`) or into fixed destinations.

## Key chunks (LEVEL01)
| Chunk | File off | comp → dec | Becomes | Finding |
|------:|----------|-----------|---------|---------|
| **32** | `0x492cf` | `0x2c80f` → `0x39d90` | collision plane geom (`0x800c1690`/`0x800D0xxx`) + sky color table (`0x800c1688`) | [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Sky color on-disk table]] |
| **35** | `0x9908a` | `0x1b24` → `0x34f4` | terrain-mesh buffer `0x8012c1d0` (occluded; visible floor = LEVEL.DAT/`fcn.80010000`) | [[Finding - Terrain on-disk source is chunk 35]] |

CD provenance: level streams from **LBA 1823–4149** (transferLog).

> [!check] **LZ codec — decode solved** *(updated 2026-06-18)*. The codec is **RNC PROPACK 2.29**; an offline **byte-exact decoder** exists (`tools/decode_level_raw.py`, chunk0-validated). The **recompressor is literal-only and unproven on console**, so permanent *disc* edits of chunk 32/35/31 are *plausible but unverified* (pending the Phase 3 boot-test). RAM/save-state edits work today. See [[Finding - LEVEL.RAW is compressed]] · [[MEM - LEVEL.RAW chunk inventory]].

## Related
- Functions: [[FUNC_80046330]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]] · [[FUNC_80030F60]]
- Structures: [[MEM - Terrain vertex buffer 8012C1D0]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]]
- Asset: [[Asset - LEVEL.RAW]] · Tool: `tools/parse_level_raw_chunks.py`


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - LEVEL.RAW chunk model.md`
- Migration status: copy-first Canon seed.
