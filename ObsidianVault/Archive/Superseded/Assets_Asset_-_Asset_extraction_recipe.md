---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - Asset extraction recipe.md
aliases:
  - "Asset - Asset extraction recipe"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - Asset extraction recipe.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_Asset_extraction_recipe.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - Asset extraction recipe
type: asset
updated: 2026-06-20
tags: [asset, extraction, reproducibility, pipeline, b5, b6, b20]
---

# Asset — extraction recipe (regenerating `extracted/`)

> How the ~1.3 GB `extracted/` tree is produced from the owned disc, so it is **reproducible-by-recipe** without committing copyrighted media ([[Gap Audit|GAP-0005]]). `extracted/` is gitignored ([[Preservation Policy]]); only this recipe + tools are shared. **Status:** the recipe is complete and the LZ/codec steps are fully scripted; the VAB and GFX steps were run partly in-session and committing them as one-command extractors is the GAP-0005 follow-up (tracked under [[Roadmap]] M4).

## Inputs
- The owner's disc, reproduced byte-exact to `REBUILD/abl.xml` files (or mounted). Disc files: `AUDIO*.XA`, `*.STR` (FMV), `*.VH`/`*.VB` (VAB sound banks), `GFX/*.RAW`, `*.BGR`, `LEVEL*/LEVEL.RAW`.
- External tool: **jpsxdec v2.1-beta** (`jpsxdec_v2.1-beta/`, gitignored — downloadable). Pin its version in [[Reproducibility Checklist]] ([[Gap Audit|GAP-0016]]).

## Steps
| Output | Source | Tool / command | Scripted? |
|---|---|---|---|
| `extracted/audio_xa/` (40 WAVs) | `AUDIO*.XA` | `jpsxdec -f AUDIO1.XA -a audio -audfmt wav` (per file) | recipe (jpsxdec) |
| `extracted/fmv/` (39 AVIs) | `*.STR` | `jpsxdec -f INTRO.STR -a video -vidfmt avi_mjpg` (audio muxed) | recipe (jpsxdec) |
| `extracted/audio_vab/` (1771 WAVs, 21 banks) | `*.VH`+`*.VB` | compact-VAB parser + SPU-ADPCM decode (see [[Finding - VAB sound bank format]]) | **partly in-session — needs `tools/extract_vab.py` (GAP-0005)** |
| `extracted/gfx_all/` (19 PNGs) | `GFX/*.RAW` | PROPACK decode via `tools/decode_level_raw.py` (same container), then depalettize | recipe (decode tool) + in-session depalettize |
| `TTLOGO.png` | `TTLOGO.BGR` | BGR555 320×240 decode | in-session |
| `tools/LEVEL_RAW_decompressed/` | `LEVEL01/LEVEL.RAW` | `python3 tools/dump_level_raw.py` | **scripted** |

## Validation
- The disc itself is hash-pinned (CRC32 `607704bb` / MD5 `2c3861a3…` / SHA-1) — [[Finding - Disc rebuild is byte-exact]].
- Codec round-trip oracle: `tools/raw_chunk0_{compressed,decompressed}.bin` (in `tools/verify_repro_inputs.py`).
- **Gap:** no per-asset output hashes for `extracted/` yet — add a `extracted/SHA256SUMS` when the extractors are scripted (GAP-0005 acceptance).

## Format references
- Audio: [[Finding - VAB sound bank format]] · [[Blocker - Audio subsystem is completely unanalyzed|B5]] (XA channel→cue map open).
- Video: [[Blocker - FMV video is completely unanalyzed|B6]] (in-engine playback trigger open, [[Gap Audit|GAP-0032]]).
- Textures: [[Finding - Region-A texture format decoded]] · [[Blocker - Offline texture and font extraction is absent|B20]] (CLUT exactness open, [[Gap Audit|GAP-0027]]). Text is image-baked (no font store).
- Codec: [[Finding - LEVEL.RAW is compressed]] (PROPACK 2.29).

## See also
[[Preservation Policy]] · [[Assets]] · [[Tools Catalog]] · [[Reproducibility Checklist]] · [[Roadmap]] · [[Gap Audit]]
