---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md
aliases:
  - "Asset - LEVEL.RAW Chunk Role Table"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - LEVEL.RAW Chunk Role Table.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_LEVEL.RAW_Chunk_Role_Table.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - LEVEL.RAW Chunk Role Table
type: asset
updated: 2026-06-20
tags: [asset, levelraw, chunks, milestone4, b9, gap-0022]
---

# Asset — LEVEL.RAW per-chunk role table (LEVEL01)

> Practical per-chunk role table for all **69** LEVEL01/LEVEL.RAW chunks ([[Gap Audit|GAP-0022]] / [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]]). Moves the inventory from a 3-region taxonomy to a marker-classified role per chunk. **Regenerate (metadata-only, no copyrighted payload):** `python3 tools/level_raw_chunk_manifest.py --json tools/level_raw_chunk_roles.json` (needs the local decompressed cache from `dump_level_raw.py`). Sizes/markers/hashes are facts *about* the data, safe to record ([[Preservation Policy]]).
>
> **Classification = 69/69 (100%).** Confidence: `CONFIRMED` (consumer traced) · `CONFIRMED-fmt` (content format decoded, consumer not separately traced) · `LIKELY` (marker-classified, untraced) · `Unknown`.

## Method / evidence basis
Each chunk's role comes from the **decompressed content marker** (`u16@0`) + structural fields, cross-referenced to the existing consumer findings. Chunk format (G24): `[word0 BE32 decomp size][word1 BE32 comp size][6-B header][PROPACK stream]`. Decoder is byte-exact on all 69 ([[Asset - PROPACK Rebuild Strategy]]).

| Marker (`u16@0` decompressed) | Meaning | Region |
|---|---|---|
| page-id + `0001 0001 0003 …` | VRAM texture page | **A** (textures) |
| `0x22` / `0x24` | 2D sprite / cell | **B** (sprites) |
| `0x23` | seed table | **B** |
| `0x101` / `0x102` | mesh **DEFINITION** / **PAYLOAD** (paired by obj-id `u32@4`) | **C** (geometry) |
| `0x103` | collision planes + sky color table | **C** |
| `0x104` | geometry/collision-adjacent record | **C** |

## Region summary
- **A — textures (17):** chunks 0–14, 28, 30. Uniform 33548 B decomp (one 17164 B). Full header grammar decoded → [[Finding - Region-A texture format decoded]] (`+0 id, +4 W,H, +8 bpp/clut flag, +0xc CLUT, +0x30c pixels`). CLUT exactness caveat → [[Asset - GFX CLUT Exactness]].
- **B — sprites + seeds (15):** chunks 15–31. `0x22` sprites (id + W×H), `0x24` cell (ch29), **`0x23` seed table (ch31)** — the only B chunk with a traced consumer (live-proven seed disc edit, [[Seed planting system]]).
- **C — geometry + collision (37):** chunks 32–68. The modding-critical region: **ch32 = collision + sky** (`0x103`), **ch34/35 = master/world mesh** def+payload (`0x101`/`0x102`, obj 0), and **ch36–68 = per-object mesh def/payload pairs** keyed by object-id.

## Full table (key columns)
*(comp/decomp in bytes; full per-chunk JSON incl. `sha256_16` fingerprint + obj-id in `tools/level_raw_chunk_roles.json`)*

| ch | reg | marker | comp | decomp | role | consumer / symbol | conf |
|---:|:--:|:--:|---:|---:|---|---|---|
| 0–14,28,30 | A | tex | varies | 33548 | VRAM texture page (id `u32@0`) | upload via texture path; [[Finding - Region-A texture format decoded]] | CONFIRMED-fmt |
| 7 | A | tex | 5804 | 17164 | texture page (half-size / CLUT page) | — | CONFIRMED-fmt |
| 15–27 | B | 0x22 | varies | 1036–8204 | 2D sprite (id + W×H) | sprite/HUD blit (untraced) | LIKELY |
| 29 | B | 0x24 | 6963 | 13072 | 2D cell / large sprite | — | LIKELY |
| **31** | B | 0x23 | 584 | 1796 | **seed table** | load-time seed parser; [[Seed planting system]] | **CONFIRMED** |
| **32** | C | 0x103 | 182287 | 236944 | **collision planes (`0x800c1690`) + sky table (`0x800c1688`)** | [[FUNC_8001A1DC]]→[[FUNC_80030F60]]→[[MEM - Collision sector table 800A7E48]] | **CONFIRMED** |
| 33 | C | 0x104 | 11435 | 17764 | geometry/collision-adjacent record | consumer untraced | LIKELY |
| **34** | C | 0x101 | 133335 | 182342 | **master/world mesh DEFINITION** (40 sub-meshes) | [[Asset - Chunk 34 Master Mesh]] | CONFIRMED-fmt |
| **35** | C | 0x102 | 6948 | 13556 | **master mesh PAYLOAD** = buffer `0x8012c1d0` | [[FUNC_800172DC]] (general mesh renderer; *occluded* for terrain — [[Finding - Visible terrain renderer]]) | CONFIRMED-fmt |
| 36–68 | C | 0x101/0x102 | varies | 1176–20912 | per-object mesh def/payload pairs (obj-id `u32@4`) | drawn via [[FUNC_800172DC]]/[[FUNC_80010000]] path (per-object consumer untraced) | LIKELY |

Object-id pairing (obj `u32@4`, def↔payload): (34,35)=obj 0 · (36,37)=9 · (38,39)=a · (40,41)=27 · (42,43)=d · (44,45)=28 · 46=b (payload, def via master) · (47,48)=e · (49,50)=23 · (51,52)=6c · (53,54)=6e · (55,56)=6b · (57,58)=71 · (59,60)=70 · (61,62)=6a · (63,64)=6f · (65,66)=69 · (67,68)=6d.

## Modding relevance (priority chunks)
- **ch32 (collision + sky):** the collision floor source ([[Finding - Collision on-disk source is chunk 32]]) + sky color ([[Finding - Sky color on-disk table]]). Edit = retexture-free terrain feel + recolor. Biggest chunk (236944 B), only 1820 B file-slack ([[Asset - LBA Shift Rebuild Proof]]).
- **ch34/35 (master mesh):** the world geometry def+payload — the **leading candidate for the spawn-area floor** ([[Asset - Chunk 34 Master Mesh]], reconciles [[Gap Audit|GAP-0011]]).
- **ch31 (seeds):** live-proven disc-editable ([[Seed planting system]]).
- **Textures (A):** editor terrain/scenery preview ([[ABL 3D Level Editor Roadmap]]).

## Next actions
- **GAP-0022 residual:** trace the *runtime consumer* of the per-object mesh pairs (ch36–68) and ch33/ch104 — `execTrace`/`accessLog` at load (local-only; cite [[DuckStation Fork Reproducibility]]). Promotes `LIKELY`→`CONFIRMED`.
- Decode the `0x22` sprite payload (Region B) for HUD/sprite modding.
- Reconcile the seed-chunk attribution (31 vs occasional "32" mentions) — ch31 is `0x23`/seed by marker; fix stray notes.

## Related
[[MEM - LEVEL.RAW chunk inventory]] · [[Asset - LEVEL.RAW]] · [[Asset - Chunk 34 Master Mesh]] · [[Asset - PROPACK Rebuild Strategy]] · [[Asset - GFX CLUT Exactness]] · [[Finding - Collision on-disk source is chunk 32]] · `tools/level_raw_chunk_manifest.py` · `tools/level_raw_chunk_roles.json`
