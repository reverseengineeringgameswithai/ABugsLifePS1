---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Trail flag gates terrain render.md
aliases:
  - "Finding - Trail flag gates terrain render"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Trail flag gates terrain render.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Trail_flag_gates_terrain_render.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Trail flag gates terrain render
type: finding
confidence: CONFIRMED
gstep: G6
tags: [finding, rendering, terrain]
---

# Finding — A trail-flag halfword gates terrain rendering

> The first hard evidence of render/collision separation: flipping one DAT halfword erased most standing terrain while Flik kept walking on it.

**Confidence:** CONFIRMED · **Established:** G6

## Summary
The pass-1 trail entry flags at `DAT 0x1512`/`0x1526` (runtime `0x80161d0a`/`0x80161d1e`) are read every row by the render cull pass [[FUNC_800140A0]] at `0x80014170` (`lh t3,0x0e(a0)`). Patching `DAT+0x1526` `41 00`→`ff ff` makes entry1 a negative sentinel that stops the scan after entry0.

## Evidence
Build `ABL_G6_RENDER_SENTINEL_TEST` → standing terrain/ground render mostly disappears; sky/horizon/grass remain; Flik/objects still load; **ground collision still usable**. → render and collision are different layers ([[Finding - Visual is not collision]]).

## Related functions
[[FUNC_800140A0]] · [[FUNC_800224EC]]

## Related memory structures
[[MEM - Trail and pass3 tables]]

## Related experiments
[[Experiment - G6 render sentinel]]

## Related fixtures / save states
n/a (disc build)

## DuckStation APIs used
[[API - accessLog]] (read-watch) · [[API - execTrace]]

## Next steps
This gates the *render-stage trail* broadly; per-surface terrain control came later via [[FUNC_800172DC]] / Candidate A.

## Source
`src_re_geometry/geometry_g55_dynamic_watch.md` §8
