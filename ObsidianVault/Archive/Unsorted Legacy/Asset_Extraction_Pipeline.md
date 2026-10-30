---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Asset Extraction Pipeline.md
aliases:
  - "Asset Extraction Pipeline"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Asset Extraction Pipeline.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset Extraction Pipeline
type: asset
updated: 2026-06-20
tags: [asset, extraction, pipeline, reproducibility, milestone4, gap-0005]
---

# Asset Extraction Pipeline

> Reproducible asset-extraction process for modding ([[Gap Audit|GAP-0005]]) — regenerate metadata/extracts from a **legal local disc** without committing copyrighted output. Supersedes/expands [[Asset - Asset extraction recipe]]. Governed by [[Preservation Policy]].

## Legal local inputs (you supply, never committed)
- The owner's disc image (gitignored): `Disney-Pixar A Bug's Life (v1.0).bin/.cue` — read-only ([[Checksum Manifest]]).
- Extracted disc files (gitignored `REBUILD/files/…` via `dumpsxiso`) — the per-file inputs.
- External tool **jpsxdec v2.1-beta** (gitignored; downloadable) for XA/STR.

## Ignored output directories (never committed)
`extracted/` (audio/FMV/GFX), `REBUILD/` (staged files + rebuilt images), `tools/LEVEL_RAW_decompressed/*.decompressed`, `*.png/*.RAW/*.bin` work products. Enforced by `.gitignore`; verified by Phase-J staging audit.

## Pipeline steps
| Output | Source | Tool / command | Committed? |
|---|---|---|---|
| disc files `REBUILD/files/` | disc | `dumpsxiso` (per `abl.xml`) | inputs only |
| `LEVEL.RAW` decompressed tree + `chunk_index.json` | `LEVEL01/LEVEL.RAW` | `python3 tools/dump_level_raw.py` | **index json yes**, payload no |
| **chunk role metadata** | decompressed cache | `python3 tools/level_raw_chunk_manifest.py --json tools/level_raw_chunk_roles.json` | **yes (metadata-only)** |
| GFX PNGs | `GFX/*.RAW` | `tools/decode_level_raw.py` + depalettize | no (copyrighted) |
| XA WAVs / FMV AVIs | `*.XA` / `*.STR` | `jpsxdec -a audio…` / `-a video…` | no |
| VAB WAVs | `*.VH`+`*.VB` | `python3 tools/extract_vab.py` ✅ | no |

## What is committable vs ignored
- **Committable (metadata only):** chunk index (`chunk_index.json`), the role manifest (`level_raw_chunk_roles.json`), hashes/sizes/markers, the **codec oracle pair** (minimal sample), tool scripts. *Facts about* the data.
- **Ignored (copyrighted payload):** every decompressed chunk, extracted WAV/AVI/PNG, rebuilt RAW/BIN, the disc image.

## Hash-manifest strategy for local outputs
- Critical inputs: `tools/verify_repro_inputs.py` + `tools/repro_inputs.sha256` (findings store, oracles, fork pin) — already in place.
- **Per-asset local manifest:** `extracted/SHA256SUMS` ✅ lets a modder verify their *local* outputs match a known-good set. Hashes only (committed); the assets stay ignored. Covers `audio_vab/ audio_xa/ fmv/ gfx/ gfx_all/` + the top-level `gfx_*.png` GFX-CLUT outputs (1879 entries). **Excludes** experiment/frame-diff screenshots (`b3*`, `b3y*`, `iso_*`, `q*`, `r_*`, `sw_*`, `tc_*`, `v_*`, `reveal_*`, `operator_current`, `warp_stage3`, `TTLOGO`, `INTRO.STR[*]`) and the jpsxdec `*.idx` files — those are analysis output / indexes, not disc assets. Verify with `cd extracted && sha256sum -c SHA256SUMS`. XA/FMV hashes are pinned to **jpsxdec v2.1-beta** (tool-version-specific output).

## Regenerate from a legal disc (clean setup)
1. `dumpsxiso` the owned `.bin` → `REBUILD/files/` (per `abl.xml`).
2. `python3 tools/dump_level_raw.py` → decompressed cache + `chunk_index.json`.
3. `python3 tools/level_raw_chunk_manifest.py --json tools/level_raw_chunk_roles.json` → role metadata (commit this).
4. `jpsxdec` + `decode_level_raw.py` + `python3 tools/extract_vab.py` → `extracted/` (local only).
5. `verify_repro_inputs.py` → confirm critical inputs match; `cd extracted && sha256sum -c SHA256SUMS` → confirm local extracted outputs match known-good.

## CI-safe vs local-only
- **CI-safe (no media):** `tests/test_level_raw_codec.py` (chunk0 oracle + synthetic), `test_repro_manifest.py`, `test_symbol_map.py`, `test_path_portability.py`, `test_tool_sanity.py` — run by `tools/run_safe_tests.py` / `.github/workflows/safe-tests.yml`.
- **Local-only (needs disc/decompressed cache):** `dump_level_raw.py`, `level_raw_chunk_manifest.py`, GFX/VAB extraction, any rebuild. Marked local; not in CI.

## Status / next
- ✅ Committed extractors: `dump_level_raw.py`, `decode_level_raw.py` (GFX), `level_raw_chunk_manifest.py` (metadata), `extract_vab.py` (VAB→WAV).
- ✅ GAP-0005 residual **CLOSED**: `tools/extract_vab.py` (pure-stdlib PS1 libsnd VAB→WAV; 21 banks → 1771 WAVs, **byte-identical** to the prior in-session set) + `extracted/SHA256SUMS` (1879-entry local-output manifest) committed. Audio is now fully script-regenerable and all extracted classes have local verification.

## Related
[[Asset - Asset extraction recipe]] · [[Preservation Policy]] · [[Asset - LEVEL.RAW Chunk Role Table]] · [[Asset - GFX CLUT Exactness]] · [[Checksum Manifest]] · [[Tools Catalog]] · [[Reproducibility Checklist]]
