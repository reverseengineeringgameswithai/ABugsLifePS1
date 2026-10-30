---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - camera transform.md
aliases:
  - "API - camera transform"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - camera transform.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - camera transform
type: api
category: GTE
tags: [api, duckstation, camera, gte, geometry, transform]
---
# API — camera transform

> Best-effort camera view/projection + position/orientation derived from the live GTE transform. **Approximate**, not a tagged camera.

## Methods & syntax
**`gpu.getCameraTransform {}`** → `{available, source:"gte", viewMatrix[16], projectionMatrix[16], cameraPosition[3], cameraForward[3], cameraRight[3], cameraUp[3], confidence:"probable"|"unknown", notes}`.
- Built from the GTE rotation matrix **RT** and translation **TR**: `cameraPosition = -(R^T) * TR`; the rows of R give `cameraRight`/`cameraUp`/`cameraForward`.
- `available:false` (and `confidence:"unknown"`, empty arrays) when no usable GTE transform is present.
- `confidence` is **`"probable"` at best — never `"exact"`**: the GTE matrix is a *per-object* model→view transform that only approximates the camera (the PS1 has no tagged camera), so a non-camera object's transform can populate it.

## Best use in ABL RE
A first-cut camera frame for spatial reasoning when you don't want to hand-decode [[API - GTE state]] yourself. Example — **camera-relative d-pad mapping**: to push Flik "toward a target" regardless of facing, project the world delta onto the camera basis —
`right_amount = dot(target - cameraPosition, cameraRight)`, `forward_amount = dot(target - cameraPosition, cameraForward)` — then pick the [[API - controller input|d-pad]] direction from the larger component. Pair with [[API - experiment runner|experiment.warpAndSettle]] to teleport toward a far object and settle the view.

## Common mistakes / gotchas
- **It only approximates the camera.** Always check `confidence`/`notes`; treat the result as a hypothesis, then confirm against on-screen position via [[API - gpu.pickObject]] / projected `SXY` ([[API - GTE state]]).
- The transform is whatever was last in the GTE — **pause** at a known draw PC (or capture via [[API - execTrace]]) so you read the frame's main view transform, not a stray object's.
- Matrices are flat 16-element arrays (4×4); `cameraPosition`/the basis vectors are 3-element.

## Related
[[API - GTE state]] · [[API - gpu.pickObject]] · [[API - controller input]] · [[API - experiment runner]] · [[API - execTrace]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
