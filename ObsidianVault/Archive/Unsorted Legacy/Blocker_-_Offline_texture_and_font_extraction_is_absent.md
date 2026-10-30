---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Offline texture and font extraction is absent.md
aliases:
  - "Blocker - Offline texture and font extraction is absent"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Offline texture and font extraction is absent.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Offline texture and font extraction is absent
type: blocker
id: B20
severity: LOW
category: textures / fonts-text
confidence: CONFIRMED
tags: [blocker, low, textures, fonts, text, images]
updated: 2026-06-22
---

# 🟡 B20 — No offline image/texture extraction; fonts and text are not located

> The project can only grab textures from **live VRAM**; there is no path from the disc's image files to extracted images, the GFX `.RAW`/`.BGR` formats are unconfirmed, and the game's on-screen text/font store has not been located at all.

> [!check] Update (2026-06-18): GFX images now render **end-to-end offline** — `GFX/CIRCUS.RAW` chunk0 decoded (PROPACK) + rendered with its embedded CLUT → the **"loading… / © start" screen** (`extracted/gfx_clean_128.png`, ~128×80, CLUT@+12, 8bpp). This confirms **UI text is image-baked into GFX RAW** (no separate font store — answers the font question). Remaining: per-frame W/H/CLUT-offset vary by chunk; a small parser would batch-extract all GFX/sprite frames. Severity effectively → **Low**.

> [!check] **BULK-EXTRACTED (2026-06-18).** All **19 `GFX/*.RAW` → PNG** in `extracted/gfx_all/` (PROPACK-decompressed + best-effort render at 256w / CLUT@+12; per-image W/H/CLUT still varies so a few render skewed, but every image is decompressed and dumped). Combined with the audio ([[Blocker - Audio subsystem is completely unanalyzed|B5]]) and FMV ([[Blocker - FMV video is completely unanalyzed|B6]]) bulk dumps, the disc's static-asset extraction is complete.

> [!check] **Font question CLOSED (2026-06-18, offline).** Decoded the `CIRCUS` / `TRAINING` / `FILM` loading screens — all **bake their "loading… / © start" text directly into the image**; `LOADING.RAW` is a sparse 320×512 mask (2 distinct values, 2.4% non-zero), *not* a glyph atlas. With the EXE carrying **zero text strings**, the answer is definitive: **there is no separate font / glyph-atlas / text-string store — all on-screen text is image-baked** (static = pre-rendered screens; dynamic HUD digits = small texture sprites in the level/VRAM texture data). The original "image-baked" hypothesis is CONFIRMED. **Font question CLOSED** (texture-extraction side remains partially open — see audit reconciliation below).

**Severity:** ~~Medium~~ → **Low** (font question CLOSED; texture format confirmed) — **NOT fully Resolved** (no committed offline extractor; minor CLUT residuals) · **Impact:** Low · **Likelihood:** Low · **Confidence:** LIKELY · **Difficulty:** Low

## Audit reconciliation (2026-06-22)
- **The body's "B20 resolved" OVERSTATES.** Reconciled to **Low but NOT Resolved**; frontmatter `confidence: LIKELY` kept (it matches the still-open texture residuals, not a fully-closed claim).
- **FONT question = genuinely CLOSED:** no separate font store; all on-screen text is image-baked; the EXE carries zero text strings.
- **Texture decode = format-CONFIRMED:** `tools/decode_level_raw.py` (PROPACK codec) + `level_editor/textures.py` CLUT path; GAP-0027 pixel decode is exact (14/16 floor CLUT entries exact).
- **Still OPEN (why not "Resolved"):**
  - **No committed offline extractor** — `tools/decode_gfx.py` does NOT exist; the depalettize step was **in-session only**, so `extracted/gfx_all/*.png` are **not repo-reproducible**.
  - CLUT bit-exactness: **2/16 entries off by 1 LSB**.
  - `level_editor/textures.py` still falls back to **live-VRAM rips** for some 4bpp pages.

## What is known (evidence)
- The only texture access is **live VRAM** via the DuckStation API ([[API - decodeTexture]] / `gpu.readVramRect`). There is **zero offline TIM/RAW image extraction** from disc files.
- `GFX/` has **19 `.RAW`** (`CIRCUS`, `FILM`, `LOADING`, `TRAINING`, `LEVEL1A…5C`) loaded via `LoadImage` (i.e. VRAM uploads), but their exact pixel format / CLUT layout is unconfirmed. `BITS/TTLOGO.BGR` is **153600 B = 320×240×2 = BGR555** (the title-screen bitmap). The leaked build log shows the `lbmbugs` tool emitting these with parameters like `… 32 256 128` ([[Blocker - Original toolchain ground-truth is unmined|B13]]).
- **Fonts/text NOT located.** The EXE has **zero** dialogue/menu/localization strings, so UI text is almost certainly **rasterized into the `gfx/*.raw` images** and/or a VRAM font sheet; subtitles (if any) live inside the `.STR` FMV ([[Blocker - FMV video is completely unanalyzed|B6]]). No glyph table or string store has been found.

## Why it matters
- Menus, loading/training screens, level backdrops, and the title logo are opaque; and any retranslation, subtitle, or text mod is fully blocked until the font/text store and the text-blit routine are found.

## Dependencies
- **Depends on:** [[Blocker - Original toolchain ground-truth is unmined|B13]] (the `lbmbugs` palette/width/height params; PROPACK packing). **Related:** [[Blocker - FMV video is completely unanalyzed|B6]] (subtitles in STR).

## Research opportunity (direction only)
- Decoding `TTLOGO.BGR` as 320×240 BGR555 is a quick confirmation; reversing the `gfx/*.raw` header against `LoadImage`'s RECT args would type those images; a glyph atlas is likely among the GFX `.RAW`, locatable by back-tracking the EXE's string-blit function to its source buffer. (Direction only.)

## Evidence & sources
- corpus (disc): `REBUILD/files/GFX/*.RAW`, `REBUILD/files/BITS/TTLOGO.BGR`, EXE `SCUS_942.88` (`LoadImage`; no text strings)
- vault: [[Asset - LEVEL.BIN and overlays]] · [[API - decodeTexture]]
- See also: [[Blockers]] · [[Risk Matrix]]
