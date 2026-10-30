---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Sky is a GP0 background fill.md
aliases:
  - "Finding - Sky is a GP0 background fill"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Sky is a GP0 background fill.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Sky_is_a_GP0_background_fill.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Sky is a GP0 background fill
type: finding
confidence: CONFIRMED
gstep: G30
tags: [finding, rendering, sky, drawenv]
---

# Finding — The sky is a GP0 0x02 background FILL (not an image)

> The daytime sky is **not** a bitmap/PNG in VRAM — it's a flat GP0 `0x02` background fill whose RGB comes from a small cache. That's why the [[Finding - GPU primitive injection|starry-night]] effect had to *draw over* it.

**Confidence:** CONFIRMED · **Established:** G30 · **Findings-store id:** f1, f3

## Summary
- The background is emitted as a GP0 `0x02BBGGRR` fill, built each frame by [[FUNC_800639CC]] from the active DRAWENV RGB bytes.
- RGB source = the cache [[MEM - Sky DRAWENV color cache 800771BC]] (`0x800771bc`/`c0`/`c4`), which is loaded pre-level from the on-disk table `0x800c1688` ([[Finding - Sky color on-disk table]]).
- **Recolor lever:** patch the cache (or the on-disk table for persistence) — NOT the transient per-frame command copies at `0x801cc3c8 / 0x801e1384`.

## Evidence
- Red cache patch → VRAM top rows read `0x001f`; green patch → `0x03e0` after the double-buffer flip (gpu.readVramRect + visual diff). No VRAM bitmap exists for the sky.
- execTrace at `0x800639cc`: `v0 = 0x02db5931` built from DRAWENV bytes `31 59 db`.

## Related functions
[[FUNC_800639CC]]

## Related memory structures
[[MEM - Sky DRAWENV color cache 800771BC]]

## Related experiments
[[Experiment - G30 sky recolor]] · [[Experiment - Starry night sky injection]]

## Related fixtures / save states
[[Fixture - night starry]] · [[Fixture - g30 openground]]

## DuckStation APIs used
[[API - gp0Trace]] · [[API - execTrace]] · [[API - gpu.readVramRect]] · [[API - visual diff]]

## Next steps
For a true starry night, *draw stars over* the fill (see [[Finding - GPU primitive injection]]); for a recolor, patch the cache/table.

## Source
`src_re_geometry/geometry_g30_terrain_render_source_plan.md` §19; findings-store f1, f3
