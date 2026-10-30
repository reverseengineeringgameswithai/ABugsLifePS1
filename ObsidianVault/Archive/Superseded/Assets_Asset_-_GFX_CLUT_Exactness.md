---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Assets/Asset - GFX CLUT Exactness.md
aliases:
  - "Asset - GFX CLUT Exactness"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Assets/Asset - GFX CLUT Exactness.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Asset_-_GFX_CLUT_Exactness.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Asset - GFX CLUT Exactness
type: asset
updated: 2026-06-22
tags: [asset, gfx, clut, texture, tim, bgr, milestone4, b20, gap-0027]
---

# Asset — GFX / CLUT exactness (bounded)

> Clarifies how exact GFX texture/CLUT handling is for safe modding ([[Gap Audit|GAP-0027]] / [[Blocker - Offline texture and font extraction is absent|B20]]). **Outcome: pixel decode + the embedded-CLUT path are CONFIRMED-exact; the *separately-uploaded* runtime CLUT for some surfaces is a bounded unknown** (rip from VRAM, local-only). Examples are metadata; no copyrighted payload committed.

## Known facts (CONFIRMED)
- **`GFX/*.RAW` = the same PROPACK container** as LEVEL.RAW. `GFX/CIRCUS.RAW` chunk0 → 33,548 B with the **Region-A texture header** (`<id u32> 0001 0001 0003 …`), decoded by `tools/decode_level_raw.py` ([[Finding - Build toolchain and PROPACK provenance]]). 19 GFX images extractable offline.
- **Region-A texture grammar (byte-exact):** `+0 u32 id · +4 W,H · +8 bpp/clut flag · +0xc CLUT (256×RGB / 16×RGB) · +0x30c pixels (4/8 bpp)` → [[Finding - Region-A texture format decoded]].
- **bpp:** flag `0` → **4bpp** (16-colour), flag `1` → **8bpp** (256-colour); `bpp = pixel_bytes·8 / (W·H)`.
- **`TTLOGO.BGR`** = 320×240 **BGR555** (direct 16-bit), decoded → `extracted/TTLOGO.png`.

## The CLUT exactness question (bounded unknown)
- For images whose **CLUT is embedded** at `+0xc`, decode is **colour-exact** — the palette is in the chunk. ✅ (defined exact subset)
- For some **runtime surfaces** (notably the in-game floor: VRAM `(960,255)`, a golden gradient), the **actual CLUT is NOT in the chunk's embedded 768-byte region** — palettes are **uploaded separately** to VRAM at load. For these, offline decode uses a placeholder/embedded palette and is **not** guaranteed colour-exact. ⚠️ (bounded unknown)
- **Current workaround (LOCAL-ONLY):** one-time `gpu.decodeTexture` rips from live VRAM → `level_editor/ripped_textures/pageNN_chC.png`. Accurate, but depends on the local fork ([[DuckStation Fork Reproducibility]]) — not reproducible from the disc alone.

## Separately-uploaded CLUT source — FOUND + decode CONFIRMED (2026-06-22; GAP-0027)
> **Refutes the "uploaded separately / not in a chunk" premise above.** The floor CLUT *is* embedded on disc — just in **`LEVEL01/LEVEL.RAW`, not `GFX/`** (the earlier offline decode searched the wrong file).
- **Live anchor:** isolated DuckStation (fork `fe0cca16b`, port 23460), `SCUS-94288_1.sav`. `gpu.readVramRect {x:960,y:255,w:16,h:1}` → the in-VRAM floor CLUT (16× BGR555, STP bit set): `bb3d b7db b276 ae35 a9f3 a5d2 a1b0 a58f a16e a56e a54d a52c a50a a4e9 a0c8 9ca7`.
- **Disc source (CONFIRMED-from-bytes):** a contiguous **48-byte run = 16 × 3-byte RGB888** in the decompressed `LEVEL01/LEVEL.RAW`, appearing **7×** across the texture-page chunks (chunk 1 @ rel `0x15c/0x21c/0x24c/0x27c`, chunk 2 @ `0x2ac`, chunk 3 @ `0x3c/0x6c`) — a per-page embedded CLUT. Disc bytes: `eb ca 71 | db b2 69 | ba 9a 61 | …` (RGB order). Absent from `LEVEL1A/1B/1C.RAW`.
- **Deterministic decode (CONFIRMED):** `bgr555 = (R>>3) | ((G>>3)<<5) | ((B>>3)<<10)`, then `| 0x8000` (STP) → reproduces **14/16 VRAM entries exactly**; indices [1]/[2] are off by **1 LSB in opposite directions** (a loader-side rounding/dither quirk on genuine 8-bit artist values — not a different source). Visually indistinguishable.
- ⇒ **The floor CLUT is now decodable offline from disc** (source byte-located + the truncation formula), removing the live-rip dependency for it. **Residual (bit-exact only):** the loader's exact rounding rule on the 2 LSB-off entries — a live `execTrace` on the CLUT DMA.

## Validation method
- Pixel/index decode: round-trip vs the byte-exact codec + the Region-A grammar (offline, CI-safe on the chunk0 oracle).
- Colour exactness: compare offline-decoded colours to a live VRAM rip (local-only) — matches for embedded-CLUT images; diverges for separately-uploaded ones.

## Unknowns
- ~~Where each separately-uploaded CLUT lives on disc~~ — **RESOLVED for the floor (2026-06-22)**: embedded in `LEVEL01/LEVEL.RAW` texture-page chunks, decoded deterministically (see *Separately-uploaded CLUT source* above). Residual: bit-exact rounding on 2/16 entries; generalize the chunk-scan to all pages/levels.
- Whether any GFX image uses 16-bit direct (5551) rather than indexed (the BGR logo does; most GFX are indexed).

## Conclusion (acceptance)
CLUT exactness is **confirmed for the embedded-CLUT subset**, and the **previously-"separately-uploaded" floor CLUT is now located on disc** (`LEVEL01/LEVEL.RAW`) **and decoded deterministically** (RGB888→BGR555, 14/16 exact, ≤1-LSB on 2). The acceptance — *offline decode matches in-VRAM colours without a live rip* — is **MET for the floor** (the case that motivated the gap); residual = bit-exact rounding on 2/16 + generalizing the page/level scan into a `decode_gfx.py`.

## Next experiments
1. **Trace the CLUT upload** for the floor texture: `accessLog`/`execTrace` the VRAM-CLUT DMA at load (local-only) → map disc offset → VRAM CLUT coordinate.
2. Once mapped, extend `tools/decode_level_raw.py` (or a `decode_gfx.py`) to resolve the external CLUT → offline colour-exact decode (removes the live-rip dependency).

## Related
[[Finding - Region-A texture format decoded]] · [[Asset - LEVEL.RAW Chunk Role Table]] · [[Asset Extraction Pipeline]] · [[API - decodeTexture]] · [[DuckStation Fork Reproducibility]]
