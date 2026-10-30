---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - LEVEL.RAW chunk inventory.md
aliases:
  - "MEM - LEVEL.RAW chunk inventory"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - LEVEL.RAW chunk inventory.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_LEVEL.RAW_chunk_inventory.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - LEVEL.RAW chunk inventory
type: memory-structure
confidence: CONFIRMED (structure) / LIKELY (per-region formats)
tags: [memory, levelraw, chunks, inventory, format]
updated: 2026-06-18
---

# MEM — LEVEL.RAW chunk inventory (LEVEL01, all 69 chunks)

> The full 69-row inventory addressing [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]]. Built offline from the project's cached decompressed dump (`tools/LEVEL_RAW_decompressed/LEVEL.RAW.decompressed` + `chunk_index.json`) and the compressed source `REBUILD/files/LEVEL01/LEVEL.RAW`. Companion to [[MEM - LEVEL.RAW chunk model]] (load/decompress mechanics). Codec = **PROPACK 2.29** ([[Finding - Build toolchain and PROPACK provenance]]).

## Chunk header (compressed, 14 = 0xe bytes)
`word0` (BE, **decompressed** size) · `word1` (BE, **compressed** size) · then **6 trailer bytes not consumed by the decompressor** (it starts the bitstream at `+0xe`) — `[8:12]` looks like a CRC, `[12]` ∈ {2,3,4}, `[13]` varies. *(LIKELY: CRC + flags; to confirm.)*

## Three regions (CONFIRMED by decompressed-content structure)
| Region | Chunks | What | Confidence |
|--------|--------|------|-----------|
| **A · textures** | 0–14, 28, 30 | Fixed-size **indexed image/VRAM frames** (`lbm`/tpage). `w0=33548=256×128+780B`, `17164=128×128+780B`; chunk 7 header `80 00 80 00`=128×128. Unique low id byte per frame. | CONFIRMED region · LIKELY 8bpp+780B |
| **B · sprites/seeds** | 15–31 | Subtype **`0x22/0x23/0x24`** small cells with W,H fields (24×24, 16×16, 32×48…). **Chunk 31 = seeds** (`0x23`). | CONFIRMED |
| **C · geometry** | 32–68 | **Level geometry + collision**, records prefixed `<n> 01` (n=1..4). The big four (32/33/34/35) then **paired** `01 01`/`02 01` sub-records 36–68 sharing an id (header/data pairs). | CONFIRMED region |

## Full table
> `dec`=decompressed bytes, `cmp`=compressed bytes, `sub`=decompressed first byte(s). ✅ = previously CONFIRMED.

### Region A — texture frames
| ch | dec_off | dec | cmp | sub | role |
|---:|--------:|----:|----:|----|------|
| 0 | 0 | 33548 | 24332 | 00 | 256×128 indexed frame |
| 1 | 33548 | 33548 | 28655 | 01 | frame |
| 2 | 67096 | 33548 | 21751 | 02 | frame |
| 3 | 100644 | 33548 | 20319 | 04 | frame |
| 4 | 134192 | 33548 | 21126 | 10 | frame |
| 5 | 167740 | 33548 | 13630 | 11 | frame |
| 6 | 201288 | 33548 | 22916 | 12 | frame |
| 7 | 234836 | 17164 | 5804 | 0e | 128×128 frame (`80 00 80 00`) |
| 8 | 252000 | 33548 | 18265 | 0b | frame |
| 9 | 285548 | 33548 | 20541 | 0c | frame |
| 10 | 319096 | 33548 | 11438 | 1c | frame |
| 11 | 352644 | 33548 | 2994 | 0f | frame (near-flat, 0.09×) |
| 12 | 386192 | 33548 | 14236 | 1d | frame |
| 13 | 419740 | 33548 | 14796 | 1e | frame |
| 14 | 453288 | 33548 | 9794 | 0a | frame |
| 28 | 535724 | 33548 | 10742 | 1a | frame |
| 30 | 582344 | 33548 | 9106 | 03 | frame |

### Region B — sprites / cells / seeds (subtype 0x22/0x23/0x24)
| ch | dec_off | dec | cmp | sub | role (W×H from header) |
|---:|--------:|----:|----:|----|------|
| 15 | 486836 | 4620 | 1549 | 22 | sprite cell |
| 16 | 491456 | 4620 | 1193 | 22 | sprite cell |
| 17 | 496076 | 4620 | 967 | 22 | sprite cell |
| 18 | 500696 | 4620 | 1948 | 22 | sprite cell |
| 19 | 505316 | 3852 | 1193 | 22 | cell (`20 00 30 00`=32×48) |
| 20 | 509168 | 4108 | 2617 | 22 | cell (32×32) |
| 21 | 513276 | 8204 | 4504 | 22 | cell (32×32) |
| 22 | 521480 | 2060 | 1130 | 22 | cell (16×16) |
| 23 | 523540 | 2060 | 1001 | 22 | cell (16×16) |
| 24 | 525600 | 1036 | 572 | 22 | cell (16×16) |
| 25 | 526636 | 1036 | 639 | 22 | cell (16×16) |
| 26 | 527672 | 4620 | 2461 | 22 | cell (32×32) |
| 27 | 532292 | 3432 | 1513 | 22 | cell (40×19) |
| 29 | 569272 | 13072 | 6963 | 24 | larger frame (`80 00 60 00`=128×96) |
| 31 | 615892 | 1796 | 584 | 23 | **✅ seeds** (`17 0c … b0 ff ff ff`) → [[Seed planting system]] |

### Region C — level geometry + collision
| ch | dec_off | dec | cmp | sub | role |
|---:|--------:|----:|----:|----|------|
| 32 | 617688 | 236944 | 182287 | 03 01 | **✅ collision planes + sky-color table** → [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Sky color on-disk table]] |
| 33 | 854632 | 17764 | 11435 | 04 01 | geometry (id `9a20`) |
| 34 | 872396 | 182342 | 133335 | 01 01 | **largest geom** — candidate master/world mesh (id 00) |
| 35 | 1054740 | 13556 | 6948 | 02 01 | **✅ terrain-mesh buffer `0x8012c1d0`** (occluded; visible floor = LEVEL.DAT/[[FUNC_80010000]]) → [[Finding - Terrain on-disk source is chunk 35]] |
| 36–68 | 1068296–1266444 | (various) | | 01 01 / 02 01 | **paired sub-records** (id-matched header/data pairs): 36/37 id09 · 38/39 id0a · 40/41 id27 · 42/43 id0d · 44/45 id28 · 46 id0b · 47/48 id0e · 49/50 id23 · 51/52 id6c · 53/54 id6e · 55/56 id6b · 57/58 id71 · 59/60 id70 · 61/62 id6a · 63/64 id6f · 65/66 id69 · 67/68 id6d |

## What this resolves vs. leaves open
- **Resolved:** every chunk now has a region + subtype + size; the 3 previously-known chunks (31/32/35) fit the taxonomy; the texture region's frame format is pinned to a fixed `W×H + 780B` shape.
- **Open (LIKELY/hypothesis):** exact bpp/CLUT of Region A (needs the `LoadImage`/upload path); the meaning of the `01 01`/`02 01` pairing in Region C (header+data? verts+faces?); chunk 34's role (largest mesh; **M7 ([[Gap Audit|GAP-0011]]): it is *not* the visible floor** — that is LEVEL.DAT/`fcn.80010000`; chunk-34/35 = occluded/collision-adjacent, so its on-screen role is the open question); the 6-byte header trailer.

## Related
[[MEM - LEVEL.RAW chunk model]] · [[Finding - LEVEL.RAW is compressed]] · [[Finding - Build toolchain and PROPACK provenance]] · [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified]] · [[Asset - LEVEL.RAW]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]]
- Source: `tools/LEVEL_RAW_decompressed/{LEVEL.RAW.decompressed,chunk_index.json}`, `REBUILD/files/LEVEL01/LEVEL.RAW`
