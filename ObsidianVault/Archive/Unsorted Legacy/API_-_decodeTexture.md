---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - decodeTexture.md
aliases:
  - "API - decodeTexture"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - decodeTexture.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - decodeTexture
type: api
category: GPU-VRAM
tags: [api, duckstation, gpu, texture]
---
# API — decodeTexture

> Decode a VRAM region (with CLUT) to an RGBA8 image file.

## Methods & syntax
**`gpu.decodeTexture {x, y, width, height, bpp:4|8|16, output_path, clut_x?, clut_y?, mask_black?=true}`** → writes a `.png/.jpg/.webp` and returns `{image_path, wrote_image, width, height, bpp, vram_x, vram_y, clut?}`. For 4/8 bpp supply `clut_x`+`clut_y` (palette read straight from VRAM). Caps width≤4096, height≤512.

## Best use in ABL RE
Dumping a recognizable texture/sprite from VRAM to confirm what a region holds, or to inspect a model's skin. Composes with [[API - frame hashing]] / [[API - visual diff]].

[[API - gpu.pickObject]] returns the visible primitive's texture-page and CLUT descriptors and uses the same 4/8/16-bpp zero-texel semantics to reject transparent candidates. Use those coordinates here to dump the identified texture.

## Common mistakes / gotchas
- Pause for coherent VRAM. Supply BOTH clut coords for paletted formats.

## ABL examples
General VRAM inspection during the rendering work; the terrain itself is shaded quads (not a paletted texture) so most terrain analysis used [[API - gpu.readVramRect]] instead.

## Related
[[API - gpu.pickObject]] · [[API - gpu.readVramRect]] · [[API - frame capture]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
