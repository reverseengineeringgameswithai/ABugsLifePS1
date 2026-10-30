---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - in-memory frame diff.md
aliases:
  - "API - in-memory frame diff"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - in-memory frame diff.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - in-memory frame diff
type: api
category: GPU-VRAM
tags: [api, duckstation, diff, frame, snapshot]
---
# API — in-memory frame diff

> Snapshot the current frame in RAM and pixel-diff the live frame against it — **no PNG, no disk** → no capture/flush race.

## Methods & syntax
- **`gpu.captureFrameSnapshot {}`** → `{snapshotId, width, height, frame}`. Grabs the current displayed frame into an in-memory registry (the `snapshotId` is the handle; `frame` = the frame number it was taken at).
- **`gpu.diffCurrentFrame {against, region?:{x,y,width,height}, threshold?}`** → `{changed, against, againstFrame, region, pixelCount, boundingBoxes:[{x,y,width,height}], metrics:{meanAbsoluteDifference, maxDifference, normalizedScore, totalPixels, changedPixels}}`. Diffs the **live** frame vs a stored snapshot (`against` = a `snapshotId`). `region` scopes the compare (bounds validated against the frame — out-of-range → error); `threshold` absorbs dither/per-channel noise. `changed:false` + `pixelCount:0` ⇒ no pixel moved.
- **`gpu.listFrameSnapshots {}`** → the live registry (`{snapshotId, width, height, frame}` each).
- **`gpu.clearFrameSnapshot {snapshotId?}`** — drop one snapshot, or all if `snapshotId` omitted.

Same `FrameDiff::Compute` core as [[API - visual diff|emulator.diffFrames]] and the [[API - experiment runner]] animation-aware path — identical metrics, just RAM-to-RAM.

## Best use in ABL RE
The race-free "did my edit change the picture, and *where*?" Capture a snapshot before a poke, advance/perturb, then `diffCurrentFrame against:<id>` — `boundingBoxes` localizes the effect on screen. This is now the **preferred path for live frames**; the file-based `emulator.diffFrames` is the **legacy** route (only needed to diff two PNGs that already exist on disk).

## Common mistakes / gotchas
- Snapshots live in memory only — a [[API - loadState]] / reset does **not** clear the registry, but the stored pixels are from the old frame, so re-capture after a reload.
- Still subject to **animation drowning the diff** on a running scene — for a perturbation test use the phase-matched control in [[API - experiment runner]] (`captureControl`) or [[API - experiment runner|experiment.warpAndSettle]], which reuse this same in-memory diff.
- `region` is validated; an out-of-bounds rect is rejected, not clamped.

## Related
[[API - visual diff]] · [[API - experiment runner]] · [[API - frame capture]] · [[API - frame hashing]] · [[API - gpu.readVramRect]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
