---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Region-A texture format decoded.md
aliases:
  - "Finding - Region-A texture format decoded"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Region-A texture format decoded.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Region-A_texture_format_decoded.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Region-A texture format decoded
type: finding
confidence: CONFIRMED (visual)
gstep: editor-phase4
tags: [finding, textures, levelraw, assets, leveleditor]
---

# Finding — LEVEL.RAW Region-A texture page format decoded

> The game's texture atlases (dirt, grass, stone, bark, sprites) decode statically from the cached LEVEL.RAW dump. Unblocks ground/wall texturing in the editor.

**Confidence:** CONFIRMED (decoded images are real, recognizable tiles) · **Established:** editor Phase 4 (2026-06-20)

## Format (per Region-A chunk = one texture page)
```
+0x00  u32 id
+0x04  u16 W, u16 H
+0x08  u16 clut_bytes (=768 = 256 colors x 3 RGB), u16 flag
+0x0c  CLUT: 256 * RGB (3 bytes each)
+0x30c pixels: 4bpp (flag=0) or 8bpp (flag=1) indices, low nibble first
```
- bpp = `pixel_bytes * 8 / (W*H)`. e.g. chunk 0 = 256×256 4bpp (dirt page), chunk 7 = 128×128 8bpp.
- Region A = LEVEL.RAW chunks **0–14, 28, 30** (17 pages). Decoded mean colors confirm roles: ch0 brown (dirt), ch1/3/10–14 green (grass/foliage), ch2/8/9 gray (stone), ch28 orange, ch5/30 light blue-gray.
- Pixel decode is byte-exact; the CLUT-as-3-byte-RGB gives recognizable color (grass=green etc.), though some pages read slightly sepia — CLUT exactness (vs 16-bit 5551) is the one soft spot.

## Command-stream UV decode — STEP 2 DONE (2026-06-20)
The `fcn.80010000` command stream is a sequence of **batches**: `[ctrl][count]` header then `count`
primitives, each = **4 vertex byte-offsets** (mult of 0x0c, < count*0x0c) then **4 UV halfwords**
(`U = low byte, V = high byte`, 0..255 in page space). UVs are **constant within a batch**; occasional
1-halfword markers (`0x8064`…) and the next `[ctrl][count]` are skipped by resync. Each quad → 2
triangles carrying the matching corner UVs.

- Implemented in `scene_importer._extract_faces` (returns faces + `face_uvs`). **Validated:** ~100%
  vertex coverage on most floor meshes, all UVs in range; **13298/13298 faces carry UVs** for LEVEL01.
- Confirmed byte order by rendering: Candidate A quads sample U[0,63] V[192,255] of chunk 0 = the dirt
  tile, and the floor now textures cleanly (no smear). `confidence = DECODED` (was HEURISTIC).
- Example batch: `ctrl 0x0060, count 0x000a`, then 10 quads each `V0 V1 V2 V3 | c03f c000 ff00 ff3f`.

## Texture-page (tpage) binding — STEP 3 (floor DONE, scenery open)
Done via a live DuckStation session (isolated instance + `_1.sav` at LEVEL01 spawn), using
`gpu.pickObject` + `gpu.decodeTexture`:
- **The floor uses texture page VRAM (x=0,y=0,mode=0 = 4bpp) = chunk 0** (the dirt atlas — VRAM decode
  matches chunk 0 tile-for-tile: bark/pebbles/leaf/glyphs). So the editor's dirt-page shortcut is
  **CONFIRMED correct for the floor**. (A second terrain page sits at VRAM x=128.)
- **4bpp pages use 16-color CLUTs**, and the real floor CLUT (VRAM `960,255`, a golden/tan gradient)
  is **NOT in the chunk's embedded 768-byte region** — palettes are uploaded separately. So the chunk
  decode is right on pixels but wrong on color (came out brown vs the game's golden).
- **Fix shipped:** one-time `gpu.decodeTexture` rip of page (0,0) with the floor CLUT →
  `level_editor/ripped_textures/page00_dirt.png`; `textures.RIPPED_PAGES` overrides chunk 0 with it, so
  the editor floor is now game-accurate **offline** (no DuckStation needed at runtime).

### Per-mesh tpage — SOLVED statically (2026-06-20)
The texture page is encoded in the **command-stream batch ctrl word**: **`ctrl & 0x1f` = VRAM page
index n** (page base X = n*64). The first command halfword of a payload is its first batch ctrl, which
gives the mesh's primary page. Validated: Candidate A ctrl `0x0060` → n=0 → chunk 0 (dirt, matches
`pickObject`). LEVEL01 distribution: 124 meshes→dirt(0), 51→chunk2, 10→chunk1, 6→chunk4, …

**VRAM page n → LEVEL.RAW chunk** (built once via `gpu.readVramRect`, matching 4bpp index patterns 96-100%):
`{0:0,1:1,2:2,3:3,4:4,5:5,6:6,7:8,8:9,9:10,10:12,11:13}` (`scene_importer.LEVEL01_VRAM_PAGE_CHUNK`).
So per-mesh tpage is now **fully static** (no DuckStation at runtime).

**Colour (CLUT):** each page's correct 16-color palette lives in VRAM, not in the chunk (so the offline
chunk decode is gray/brown where the game is golden/green). Fixed by a **one-time rip**: each used page
decoded with its dominant game CLUT via `gpu.decodeTexture` → `level_editor/ripped_textures/pageNN_chC.png`,
overriding the chunk decode (`textures.RIPPED_PAGES`). Pages 0,1,2,3,4,10,12 ripped.

**Remaining nuances (minor):** (a) per-mesh uses the *first* batch's page; a mesh spanning multiple
pages uses only its primary one (per-quad page tracking is a future refinement). (b) CLUT is
per-primitive; one representative CLUT per page is used, so some surfaces' colour is approximate.
Helper: `tools/_step3.py` (connect + load `_1.sav`).

## Tools
`level_editor/textures.py` (decode pages, build atlas array, `match_page`); applied in `level_editor/scene3d.py` (`assemble`, `Renderer` sampler2DArray).

## Related
- [[MEM - fcn.80010000 mesh payload]] · [[MEM - LEVEL.RAW chunk inventory]] · [[Finding - DAT record holds decor instance world position]] · [[ABL 3D Level Editor Roadmap]]
