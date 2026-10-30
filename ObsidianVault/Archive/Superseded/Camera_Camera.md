---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Camera/Camera.md
aliases:
  - "Camera"
migration_action: split
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Camera/Camera.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Camera.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Camera
type: hub
tags: [hub, camera]
---

# Camera — Map of Content

> Lightly explored so far, but it matters because the camera **follows Flik in Y**, which is why a uniform terrain lower is visually invisible.

## What's known
- View/camera state is staged in scratchpad: camera base `0x1f800374`, view vector `0x1f800384`, view matrix `0x1f8003b4` — loaded into the GTE by [[FUNC_800140A0]] / `fcn.800146e0` per frame.
- The actor/camera struct `0x800a0a64` carries coords (`+4/8/c`) and a transform matrix (`+0x28..0x3c`).
- Native render resolution is **512×224**; near-ground geometry clips off the bottom (`y>200`).

## Why it matters for terrain edits
Because the camera tracks Flik's Y and the ground texture is uniform/gouraud, a *uniform* matched lower of visual+collision is invisible on screen — a dramatic localized pit is **rendering-limited**, not a tooling limit. See [[Finding - Localized terrain edit]] and [[Finding - Visual is not collision]].

## Open questions
- Exact camera-follow law and how to compute model↔screen scale for spatial targeting (needs GTE-trace calibration via [[API - execTrace]] / [[API - GTE state]]).
- Viewport/draw-offset mapping is not byte-exact yet. See [[Open Questions]].
- **Observation (night-sky session):** the camera reorients substantially as Flik walks (translation +~21k and the loaded GTE matrix both change a lot over 40 frames) — so a fixed screen-space sky looks "wrong" on turns. Caveat: the GTE read is confounded by per-object matrices; read the pure view matrix at `0x1f8003b4` / `0x800a0a64+0x28`. Motivates the **camera-aware 360° skybox** candidate — see [[Open Questions]] #16 and [[Finding - Persistent night render hook]].

## Related
- Functions: [[FUNC_800140A0]] · [[FUNC_800224EC]] · [[FUNC_800172DC]]
- APIs: [[API - GTE state]] · [[API - execTrace]] · [[API - gpu.readVramRect]]
- Hubs: [[Rendering]] · [[Geometry]]
