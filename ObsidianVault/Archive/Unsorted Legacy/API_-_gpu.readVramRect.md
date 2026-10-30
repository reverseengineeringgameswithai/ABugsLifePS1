---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - gpu.readVramRect.md
aliases:
  - "API - gpu.readVramRect"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - gpu.readVramRect.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - gpu.readVramRect
type: api
category: GPU-VRAM
tags: [api, duckstation, gpu, vram]
---
# API — gpu.readVramRect

> Read a rectangle of raw VRAM (16-bit BGR555) — the basis of VRAM/framebuffer inspection and diffing.

## Methods & syntax
- **`gpu.readVramRect {x, y, width, height}`** → `{x,y,width,height, format:"raw16le", base64}`. Row-major, stride=width, 16-bit LE. Validates `x+width≤1024`, `y+height≤512`; `width*height≤262144` (else `-32006`, "tile it"). **No PNG conversion — decode yourself.**
- **`gpu.writeVramRect {x, y, width, height, base64|hex}`** → `{x,y,width,height, format:"raw16le", bytes_written}`.
  Direct raw16le VRAM upload/write. Payload must be exactly `width*height*2` bytes; same bounds/cap as read. Useful for
  visual probes/texture experiments, but the game can overwrite it on the next draw.
- **`gpu.getStatus`** → GPUSTAT bitfields + `crtc` (video_width/height, active_rect, vram_source_rect).
- **`gpu.getClut`** → 256 BGR555 palette entries.

## Best use in ABL RE
Reading the native framebuffer to verify an on-screen change programmatically (not just by eye). The project's `tools/vramdiff.py` reads the native **512×224** BGR555 framebuffer this way and `diff(a,b)` returns (changed-pixel count, bbox).

## Common mistakes / gotchas
- Pause for a coherent state-vs-VRAM read.
- Tile reads larger than 512×512. The sky double-buffers — read after the flip (red→`0x001f`, green→`0x03e0`).

## ABL examples
- Sky recolor verification (red/green VRAM words) → [[Finding - Sky is a GP0 background fill]], [[Experiment - G30 sky recolor]].
- Pre/post terrain-edit framebuffer diffs (e.g. 38090 changed px) → [[Finding - Visible ground from DAT verts]].

## Related
[[API - provenance.timeline]] · [[API - visual diff]] · [[API - frame capture]] · [[API - gp0Trace]] · [[API - decodeTexture]] · `tools/vramdiff.py` ([[Tools Catalog]])

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
