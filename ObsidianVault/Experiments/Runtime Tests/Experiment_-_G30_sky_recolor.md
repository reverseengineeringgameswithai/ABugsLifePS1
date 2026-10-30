---
kind: experiment
id: Experiment_-_G30_sky_recolor
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G30 sky recolor.md
aliases:
  - "Experiment - G30 sky recolor"
---

# Experiment — G30 sky recolor

> Migrated from `ObsidianVault/Experiments/Experiment - G30 sky recolor.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G30 sky recolor

> Prove the sky is a GP0 0x02 background fill (not an image) by recoloring it via its RGB source.

| Field | Value |
|-------|-------|
| Fixture / save state | [[Fixture - g30 openground]] |
| Build image / tool | none — **live debugger** (RAM edits); `tools/vramdiff.py` |
| Patch | sky color cache words `0x800771bc` (R) / `0x800771c0` (G) / `0x800771c4` (B); on-disk source table `0x800c1688` (chunk 32) |
| APIs used | [[API - accessLog]], [[API - gp0Trace]], [[API - gpu.readVramRect]] + [[API - visual diff]] |

## Goal
Determine whether the sky is a stored bitmap/PNG or a generated fill, and find the recolor lever.

## Procedure (reproducible)
1. Load fixture; settle.
2. `accessLog` the pre-load copy writers `0x8003b2b8/d8/f8` → they copy `31 59 db` from table `0x800c1688` into cache `0x800771bc/c0/c4`.
3. Patch the cache words red, then green; `gpu.readVramRect` the top sky rows + `diffFrames`.
4. Confirm the builder [[FUNC_800639CC]] rebuilds the GP0 `0x02BBGGRR` fill each frame from the DRAWENV RGB (`v0=0x02db5931`).

## Result
Red patch → VRAM `0x001f`; green patch → `0x03e0` after the double-buffer flip. **The sky is a GP0 0x02 background FILL, not an image/polygon.** The transient submitted command copies (`0x801cc3c8/0x801e1384`) are rebuilt every frame — patch the upstream **cache** (RAM) or **table** (persistent) instead.

## Conclusion
Sky recolor lever confirmed; on-disk source is the LEVEL.RAW chunk-32 color table `0x800c1688`. This underpins the starry-night work ([[Experiment - Starry night sky injection]]).

## Linked findings / functions / structures
- [[Finding - Sky is a GP0 background fill]] · [[Finding - Sky color on-disk table]]
- [[FUNC_800639CC]] · [[MEM - Sky DRAWENV color cache 800771BC]]
## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` (§19)
