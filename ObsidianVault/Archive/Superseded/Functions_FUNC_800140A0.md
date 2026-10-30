---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_800140A0.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_800140A0.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_800140A0_GTE_trail-cull_transform.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_800140A0 — GTE trail-cull transform
type: function
address: 0x800140A0
confidence: CONFIRMED
tags: [function, rendering, gte, geometry, g6]
---
# FUNC_800140A0 — GTE transform / trail-cull pass

> The render pre-stage that transforms and culls pass-1 trail rows into survivor lists. The reader behind the G6 terrain-gate and the G7 body-field reads.

| Field | Value |
|-------|-------|
| Address | 0x800140A0 |
| Source file | `geometry_render_consumers.c` |
| Confidence | CONFIRMED runtime execution + trail-flag effect; field semantics UNKNOWN |

## Purpose
Loads a 3×3 matrix (a1) + vector (a2) into the GTE, loops `[0x80082440]` entries over the trail table (a0), runs MVMVA×2 + SQR×3, and culls pass-1 trail rows → writes survivor row pointers to LIST_A (`0x80096ea8`) and LIST_B (`0x8009e338`). A transform/visibility pre-stage, not a rasterizer.

## Arguments / Returns
`a0` = trail table (`0x80161cfc`), `a1` = view matrix (`0x1f8003b4`), `a2` = view vec (`0x1f800384`). Returns packed hi/lo halfwords.

## Calls (callees)
- GTE ops inline (MVMVA/SQR); no jal in the hot loop.

## Called by (callers)
- [[FUNC_800224EC]] @ `0x8002262c` (render driver).

## Globals & structures touched
- trail table [[MEM - Trail and pass3 tables]] · survivor lists [[MEM - Survivor lists]] · body-field gating bitmask `0x800901c8`.
- Reads the per-row flag `+0x0e` at site `0x80014170` (the G6 terrain-gate field, DAT `0x1526`); body fields `+0x00/04/08/0c` at `0x8001419c/a0/a4/b4` only when the bitmask bit is set.

## Evidence & confidence notes
G5.5/G6: read-watch hits at `0x80014170`; patching DAT `0x1526` `41 00→ff ff` removes most standing terrain render while collision stays intact — see [[Finding - Trail flag gates terrain render]]. G7/G9: entry24 body row is read but rejects before list-write → a culling/range row ([[Finding - entry24 is a culling row]]). Field semantics UNKNOWN.

## Related
- Findings: [[Finding - Trail flag gates terrain render]] · [[Finding - entry24 is a culling row]] · [[Finding - Visual is not collision]]
- Functions: [[FUNC_800224EC]] · [[FUNC_8001EA6C]] · [[FUNC_800206E8]]
- Experiments: [[Experiment - G6 render sentinel]] · [[Experiment - G8 entry24 body edits]]
- Source docs: `src_re_geometry/geometry_g55_dynamic_watch.md`, `geometry_render_consumers.c`
