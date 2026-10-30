---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - visual diff.md
aliases:
  - "API - visual diff"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - visual diff.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - visual diff
type: api
category: GPU-VRAM
tags: [api, duckstation, diff]
---
# API — visual diff

> Pixel-diff two image files → changed-pixel count, normalized score, bounding box, optional diff image.

## Methods & syntax
**`emulator.diffFrames {a, b, region?, grid?:{cols,rows}, diff_path?}`** → `{width, height, total_pixels, pixel_diff_count, normalized_score(0..1), mean_abs_difference, max_difference, changed_bbox|null, grid?, ahash_a, ahash_b, hamming, diff_image?}`. The diff image (red over dimmed base) is written **only if `diff_path` is supplied**. Identical → counts 0, bbox null.

> [!tip] (new) Prefer the **race-free in-memory** path for live frames. [[API - in-memory frame diff|gpu.diffCurrentFrame]] (+ `gpu.captureFrameSnapshot`) diffs RAM-to-RAM with the same `FrameDiff` core — **no PNG, so the capture/flush race below cannot occur.** Use file-based `emulator.diffFrames` only to compare two PNGs that already exist on disk; it is now the **legacy** route for live frames. `diffFrames` now also returns **`mean_abs_difference`** / **`max_difference`** (the same metrics `gpu.diffCurrentFrame` reports as `meanAbsoluteDifference`/`maxDifference`).

## Best use in ABL RE
The quantitative "did my edit do anything, and *where*?" — the changed bbox localizes the effect on screen. Essential when an edit is subtle.

## Common mistakes / gotchas
- A *uniform* terrain lower can score ~0 because the camera follows Y and the texture is uniform — [[Finding - Visual is not collision]]. Use MOVE/RECOLOR/localized edits, not uniform ones.
- **Animation drowns the diff.** Diffing before→after on a *running* scene shows mostly idle animation. Use the **animation-aware** [[API - experiment runner]] (`experiment.run captureControl:true`) instead: it diffs a no-perturbation **control** frame against the perturbed frame from the same snapshot, so shared animation cancels and only the perturbation's effect remains. Same pixel-diff core (`FrameDiff::Compute`) as `diffFrames`, computed **in memory** (no PNG round-trip → sidesteps the flush race below).
- ⚠️ **Capture/flush race (observed 2026-06-18):** `emulator.captureFrame` can return *before* the PNG is fully flushed, so a `diffFrames` called immediately after may read a **partial file** and report a wildly inflated diff (seen: **62.69%** where a pixel compare of the same *settled* files was **1.6%**). **Trust a re-read pixel compare** (PIL on settled files, or native `tools/vramdiff.py` / [[API - gpu.readVramRect]]) over an immediate `diffFrames`; or settle before diffing. This briefly mis-pointed a [[Blocker - Headline results rest on single-source evidence|B3]] floor-render test at f13. The in-memory `experiment.run captureControl` path avoids files entirely.

## ABL examples
- Sky recolor differential (cache-clean) confirmed dirt is a separate background layer → [[Experiment - G30 sky recolor]].
- Bulk floor edit measured **38090** changed px → [[Finding - Visible ground from DAT verts]].
- `tools/vramdiff.py` is the project's lightweight equivalent over native VRAM.

## Related
[[API - in-memory frame diff]] · [[API - frame capture]] · [[API - frame hashing]] · [[API - gpu.readVramRect]] · [[API - experiment runner]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
