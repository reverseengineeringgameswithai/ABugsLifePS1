---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8001A1DC.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8001A1DC.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8001A1DC_LEVEL.RAW_LZSS_decompressor.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8001A1DC — LEVEL.RAW LZSS decompressor
type: function
address: 0x8001A1DC
confidence: PARTIAL
tags: [function, levelraw, decompress, codec, gate]
---
# FUNC_8001A1DC — LEVEL.RAW LZSS / LZ77 decompressor

> The custom codec that decompresses every LEVEL.RAW chunk (visible terrain + collision + sky color table). **The "LZ codec gate"** that blocks permanent disc edits.

| Field | Value |
|-------|-------|
| Address | 0x8001A1DC (span …0x8001A8F8, ~456 instrs) |
| Source file | `src_re_geometry/geometry_runtime_buffers.c` (G23/G24) |
| Confidence | PARTIAL — structure CONFIRMED with PCs; exact length/distance code tables NOT byte-exact |

## Purpose
LZSS/LZ77 bitstream decompressor. Reads 2 **big-endian** header words (word0/word1, 0xe-byte header), MSB-first bit reader; main loop `0x8001a658` (flag 0 = literal `*a1++=*v1++`, 1 = back-reference match with variable-length length code + 16-bit distance); terminator at long-byte 0 (`0x8001a804`). No `jal`, no GTE. Single caller.

## Arguments / Returns
`a0` = src (LEVEL.RAW chunk base), `a1` = dst (`[gp+0x588]` decompressed cursor). Writes decompressed bytes to dst.

## Calls (callees)
- none (leaf).

## Called by (callers)
- [[FUNC_8003A318]] @ `0x8003a4e4` — once per chunk in the decompress loop.

## Globals & structures touched
- Writes the terrain buffer [[MEM - Terrain vertex buffer 8012C1D0]] (chunk 35; write PCs `0x8001a5e8/f0/678`) and the collision plane block (chunk 32; `0x8001a654/678`).

## Evidence & confidence notes
G23 proved LEVEL.RAW is compressed (entropy + disasm); G24 decoded the grammar structure but **no byte-exact offline decoder was built** — the length/distance code tables remain unresolved. This is the single biggest gate: a permanent disc patch of chunk 32 (collision) or chunk 35 (terrain) requires decompress→edit→**recompress** with this exact codec. RAM/save-state edits work today without it.

## Related
- Findings: [[Finding - LEVEL.RAW is compressed]] · [[Finding - Terrain on-disk source is chunk 35]] · [[Finding - Collision on-disk source is chunk 32]]
- Functions: [[FUNC_8003A318]] · [[FUNC_80030F60]]
- Open question: [[Open Questions]] (LZ codec gate) · Assets: [[Asset - LEVEL.RAW]]
- Source docs: `src_re_geometry/geometry_g24_level_raw_decompressor.md`
