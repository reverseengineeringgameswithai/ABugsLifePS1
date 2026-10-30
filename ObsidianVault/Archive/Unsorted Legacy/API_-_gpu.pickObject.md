---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - gpu.pickObject.md
aliases:
  - "API - gpu.pickObject"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - gpu.pickObject.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - gpu.pickObject
type: api
category: GPU-VRAM
tags: [api, duckstation, gpu, picking, provenance, gp0]
updated: 2026-07-06
---
# API — gpu.pickObject / gpu.traceRegion / VRAM provenance

> Resolve a native screen pixel or small region to GP0 drawable(s), texture/CLUT state, and best RAM/DMA/CD provenance.

## Method & syntax

**`gpu.pickObject {x, y, all_contributors?=false}`**. `x`/`y` are non-negative integer pixels in the native CRTC frame, not host-window or upscaled screenshot coordinates. Pause first for a coherent frame.

Hit shape:

```json
{
  "hit": true, "x": 123, "y": 45, "frame": 1000,
  "pixel": {"rgba": [124,82,41,255], "depthOrOrdering": "gp0:12345 (painter order)"},
  "drawCall": {
    "gp0Index": 12345, "frame": 1000, "command": "GP0(3c) quad",
    "primitiveType": "triangle|quad|sprite|line|unknown",
    "texturePage": "x=640,y=0,mode=1,raw=0x0000008a",
    "clut": "x=0,y=480,raw=0x00007800", "semiTransparency": "opaque",
    "rawGp0Words": ["0x3cffffff", "0x00640050"]
  },
  "texture": {"textured": true, "bpp": "8bpp", "pageX": 640, "pageY": 0, "clutX": 0, "clutY": 480},
  "drawMode": {"raw": "0x0000008a", "semiTransparency": "opaque", "textureXFlip": false},
  "geometry": {"screenVertices": `[80,100]`, "gteVertices": `[80,100,900]`, "uv": `[0,0]`, "screenRect": {"x":80,"y":100,"width":1,"height":1}, "uvRect": {"u":0,"v":0,"width":1,"height":1}},
  "source": {
    "ramAddress": "0x00123400", "vertexPointer": "0x00123404",
    "dmaSource": "0x00123400", "orderingTableEntry": "0x001233fc",
    "confidence": "probable", "notes": ["packet and vertex pointers exact; ordering-table header inferred"]
  }
}
```

No hit: **`{hit:false, reason:"background"|"outside_frame"|"unknown"}`**. `all_contributors:true` adds `contributors:[{drawCall,geometry,source},…]` in draw order while the top-level objects remain the final visible contributor.

## Companion calls added 2026-07-06

- **`gpu.traceRegion {x,y,width,height}`** — returns all retained GP0 contributors touching a small native CRTC screen box, in draw order. Use for UI tokens/sprites when one pixel is not enough. Contributors use the same `{drawCall, geometry, texture, drawMode, source}` shape as `pickObject`.
- **`gpu.vramWriteLog.get {offset?,limit?,filter?,include_disc?=false,include_transfer_events?=true}`** — retained VRAM fill/copy/upload timeline. Filter by destination rect or method (`fill`, `vram_to_vram`/`copy`, `cpu_to_vram`/`upload`). Entries include frame/cycle, destination/source rects, raw GP0 words, packet/payload RAM ranges, and transferLog event IDs/events when the payload overlaps logged DMA.
- **`gpu.resolveVramProvenance {x,y,width,height, bpp?, page_x?, page_y?, u?, v?, include_disc?=true, include_transfer_events?=true}`** / **`gpu.resolveClutProvenance {x,y, entries?=16, include_disc?=true}`** — focused wrappers over the retained VRAM write log. VRAM provenance returns a `texture` candidate block with bpp/page/UV/tpage interpretation when enough hints are supplied; CLUT returns live raw/RGBA-decoded entries. Use when texels changed but the primitive uses a different runtime palette.

## Provenance semantics

- Uses the same completed-command snapshot as [[API - gp0Trace]]; no prior `gp0Trace.start` is required. The bounded index retains 65536 draw/VRAM-write records and clears on reset/state load.
- Supports polygons/quads, sprites, lines, textured variants, overlap, and background/VRAM-write invalidation.
- Texture-zero rejection reuses the PS1 texture-page/CLUT semantics in [[API - decodeTexture]]. Historical texture mutation or mask-bit rejection lowers confidence to `probable` with a note.
- DMA packet and vertex-word addresses are exact. `orderingTableEntry = packet−4` is a probable linked-list-header inference.
- `gteVertices` appears only when draw-time SXY0..2/SZ1..3 exactly match the packet screen vertices. Empty means "not safely correlated"; use [[API - GTE state]] / [[API - execTrace]] at the producer.

## Best use in ABL RE

Click/pick a stable interior pixel on terrain, an enemy, pickup, sprite, or HUD element, then follow `source.vertexPointer` or `ramAddress` with [[API - accessLog]] / [[API - execTrace]]. `gp0Index` identifies the visible winner when primitives overlap.

## Replaces the old force-offscreen workflow

Old: save baseline → force each candidate offscreen/neutralize a draw → advance an exactly phase-matched control → capture/diff → fight animation and camera noise. New: pause the target frame → `gpu.pickObject {x,y}` → follow the returned packet and pointer chain. Use a move-test only to confirm the identified source, not to discover it blindly.

## Gotchas

- Coordinates are native CRTC output pixels. Use `gpu.getStatus.crtc` to understand active padding/source mapping.
- Pick inside a primitive, away from triangle edges, for stable PS1 raster-rule behavior.
- A direct GP0 MMIO packet has null RAM pointers and `confidence:"unknown"`.

## Related

[[API - provenance.timeline]] · [[API - gp0Trace]] · [[API - decodeTexture]] · [[API - GTE state]] · [[API - gpu.readVramRect]] · [[API - transferLog]] · [[Playbook - Trace rendering ownership]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
