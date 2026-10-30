---
kind: experiment
id: Experiment_-_G29_collision_lever_validation
created: 2026-07-08
updated: 2026-07-08
status: legacy_imported
confidence: confirmed
legacy_source: ObsidianVault/Experiments/Experiment - G29 collision lever validation.md
aliases:
  - "Experiment - G29 collision lever validation"
---

# Experiment — G29 collision lever validation

> Migrated from `ObsidianVault/Experiments/Experiment - G29 collision lever validation.md` during the 2026-07-08 vault completion pass. Original action: `convert_to_experiment`. Reason: Experiment note should preserve proof artifacts and link Canon claims it validates.

# Experiment — G29 collision lever validation

> Live-edit the collision sector table and prove Flik's footing follows it (collision source, no disc build).

| Field | Value |
|-------|-------|
| Fixture / save state | `SCUS-94288_1.sav` (gameplay), `SCUS-94288_2.sav` (pre-load) |
| Build image / tool | none — **live debugger only** (RAM edits) |
| Patch | sector origin Y at `0x800A91C8+4` (sector 104) and all-sector variants: +8192 / +16384 / −8192 / −3000 |
| APIs used | [[API - connection and auth]] (port 2346), [[API - addWatch]]/[[API - accessLog]] (WRITE-watch player Y `0x800a6504`), [[API - controller input]] (`setControllerState`/`pressButton`), [[API - execution control]] (`advanceFrames`), `writeU32`, [[API - frame capture]] |

## Goal
Find where Flik's resolved Y is written, trace the floor source, and prove (causally) that the collision sector table is the lever.

## Procedure (reproducible)
1. Load `SCUS-94288_1.sav`; settle one frame.
2. WRITE-watch `0x800a6504` (player Y) → writer = [[FUNC_8003633C]], decisive commit at `0x80036cec` (callers `0x800495c8/0x8004c024/0x8004e628`). This **supersedes** the earlier "writer = fcn.8005b134" claim.
3. Trace the resolver chain: sector table [[MEM - Collision sector table 800A7E48]] → `[sector+0x10]` plane records (`0x800D0xxx`) → candidate list `0x8009c230` → resolver `fcn.800345cc` (swept plane-distance clamp + skin `-0xc0`).
4. `writeU32` the player sector's origin Y (`0x800A91C8+4`) by each delta; `pressButton` to un-ground Flik; `advanceFrames`; `captureFrame`.

## Result
Flik's footing (endY) **scales ~1:1** with the edit while endX stays constant; large negative edits drop Flik through a kill-plane (~≤8000). Editing all 223 sectors moves the whole floor ~1:1.

## Conclusion
The collision/floor source is the sector table + plane records (built from **LEVEL.RAW chunk 32**), independent of the visual terrain payload — definitively explaining G28. The G5 "no static collision consumer" negative is vindicated (collision reaches data via the non-global `[sector+0x10]` pointer).

## Linked findings / functions / structures
- [[Finding - Collision sector table]] · [[Finding - Collision RAM edit moves footing 1to1]] · [[Finding - Player Y writer FUNC_3633C]] · [[Finding - Collision is planes not scalar]] · [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Visual is not collision]]
- [[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]] · [[FUNC_8001A1DC]] · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]]
## Source
`src_re_geometry/geometry_g29_collision_source_plan.md`
