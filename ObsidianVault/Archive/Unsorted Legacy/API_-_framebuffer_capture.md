---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - framebuffer capture.md
aliases:
  - "API - framebuffer capture"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - framebuffer capture.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - framebuffer capture
type: api
category: GPU-VRAM
tags: [api, duckstation, gpu, vram, framebuffer, screenshot]
---
# API — framebuffer capture (deterministic, flip-race-free)

> Capture an exact VRAM rectangle, or a specific buffer (displayed vs the in-progress drawing buffer), decoded to PNG/RGBA/raw — with no double-buffer flip race.

## Why
PS1 VRAM is a **single** 1024×512 buffer; games "double buffer" by **displaying** one rectangle while **drawing** into another. The old screenshot path captured the host-display scanout, which flips, so a capture near a frame boundary was non-deterministic (edit one buffer, the capture showed the other) and there was no way to grab a *specific* buffer. Reading `g_vram` directly (after a GPU sync) is scanout/flip-independent: repeated captures of a **paused** frame are **byte-identical**.

## Methods & syntax
- **`gpu.captureVramRect {x, y, width, height, format?="png"}`** — an exact VRAM rect. `format` ∈ `png` (RGBA8 PNG, BGR555 decoded) | `rgba` (raw RGBA8, `w*h*4`) | `raw16` (BGR555 LE, like [[API - gpu.readVramRect]]).
- **`gpu.frameSnapshot {buffer?="displayed", rect?, format?="png"}`** — a specific buffer:
  - `displayed` — the region scanned out to the screen (`GetCRTCVRAMSourceRect`).
  - `drawing` — the current drawing clip = the **back buffer** being rendered into (`GetDrawingArea`).
  - `by_rect` — the explicit `rect:{x,y,width,height}`.
- Both return `{buffer, format, x, y, width, height, base64, byte_length}`. Cap `w*h ≤ 524288` (full VRAM). **Pause first** for a coherent (state-vs-VRAM) snapshot.

## Best use in ABL RE
- **Compare the displayed frame vs what's being drawn** for the next frame — e.g. catch a renderer writing to the off-screen buffer before it's flipped.
- **Byte-exact frame fingerprinting while paused** — feed `raw16`/`rgba` to [[API - frame hashing]] without the PNG-flush race that bites [[API - frame capture|captureFrame]].
- **Grab a precise VRAM region as a PNG** (e.g. a texture page or the CLUT strip) in one call instead of `readVramRect` + manual BGR555 decode.

## Common mistakes / gotchas
- **Color-depth caveat:** `png`/`rgba` decode assumes **15-bit BGR555**. For a **24bpp** display (FMV/MDEC) the bytes are exact but the colour decode is wrong → use `raw16` and unpack 24bpp yourself.
- Not paused ⇒ the resolved rect (display/drawing) can change under you between calls — pause for coherence.
- `drawing` returns the GP0 **drawing-area** clip; some games set it to the whole framebuffer bounds.

## Related
[[API - gpu.readVramRect]] · [[API - decodeTexture]] · [[API - frame hashing]] · [[API - frame capture]] · [[API - in-memory frame diff]] · [[API - gp0Trace]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
