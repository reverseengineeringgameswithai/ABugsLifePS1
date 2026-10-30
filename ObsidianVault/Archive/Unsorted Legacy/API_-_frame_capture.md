---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - frame capture.md
aliases:
  - "API - frame capture"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - frame capture.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - frame capture
type: api
category: GPU-VRAM
tags: [api, duckstation, screenshot]
---
# API — frame capture

> Render the current frame to an image file on disk (for the eye, for hashing, or for diffing).

## Methods & syntax
- **`emulator.captureFrame {path}`** (absolute; ext png/jpg/webp) → `{captured, path, width, height, format, frame, paused, running}`. Synchronous, rendered on the video thread (safe).
- **`emulator.getVideoStatus`** → `{valid, running, paused, frame, resolution_scale, default_format, default_extension}`.

## Best use in ABL RE
Capture before/after screenshots around a perturbation, then feed them to [[API - frame hashing]] / [[API - visual diff]]. Operator visual confirmation of a build/edit.

## Common mistakes / gotchas
- Screenshots are corroboration, not proof — they are "mostly reproducible" (see [[API - determinism]]). Rest CONFIRMED claims on CPU/RAM/VRAM state.
- ABL caveat: near-ground geometry clips off the bottom at native 512×224, so a real change can be off-screen.

## ABL examples
The starry-night before/after/diff PNGs (`starry_night_result/`) → [[Fixture - night starry]]. Operator visual tests for G6/G14/G16/G28 builds.

## Related
[[API - frame hashing]] · [[API - visual diff]] · [[API - snapshot bundle]] · [[API - gpu.readVramRect]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
