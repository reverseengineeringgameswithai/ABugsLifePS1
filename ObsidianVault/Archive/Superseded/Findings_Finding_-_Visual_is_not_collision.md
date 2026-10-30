---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Visual is not collision.md
aliases:
  - "Finding - Visual is not collision"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Visual is not collision.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Visual_is_not_collision.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Visual is not collision
type: finding
confidence: CONFIRMED
gstep: G28/G29
tags: [finding, collision, rendering, geometry, central]
---

# Finding — Visual terrain ≠ collision source

> **The central result of the geometry arc.** The geometry you *see* and the geometry Flik *stands on* come from different files, different RAM, and different code. Editing one does not move the other.

> [!success] M7 corroboration (2026-06-21): the ≥2-method bar is now **met**. Angle 1 — source separation at the LEVEL01 spawn: visible floor = DAT (`fcn.80010000`, file `0x15dec..0x2f59c`) ↔ collision = chunk-32 `0x800a7e48` (separate RAM) → [[Experiment - Spawn-floor render source]]. Angle 2 — the **G29 Pass-3** pristine-vs-patched counterfactual **ran (both arms)**: a phase-matched pristine-vs-G28 differential differs in **only the visual-edit halfword** (`0x8017918a`, 5001→6025) while the collision sector-table SHA-256, the [[FUNC_800345CC]] candidate/plane reads, the [[FUNC_8003633C]] player-Y writer path, and Flik's exact footing trajectory are **byte-identical** → [[Experiment - G29 Pass-3 differential]] (GAP-0038 Verified).

**Confidence:** CONFIRMED · **Established:** G28 (visual) + G29 (collision) · **Findings-store id:** f8

## Summary
- **Visual** terrain/floor: rendered from LEVEL.DAT payloads ([[MEM - fcn.80010000 mesh payload]], Candidate A) by [[FUNC_80010000]], and from the persistent terrain buffer [[MEM - Terrain vertex buffer 8012C1D0]] (LEVEL.RAW **chunk 35**) by [[FUNC_800172DC]].
- **Collision** floor: resolved from the [[MEM - Collision sector table 800A7E48]] + plane records (LEVEL.RAW **chunk 32**) by [[FUNC_8003633C]].
- The two are independent layers. A **matched** lower of both lands Flik coincident on the lowered floor (consistency proven, G30 R6), but neither edit affects the other.

## Evidence
- **G28**: building a DAT edit to Candidate A's vertex Y (`DAT 0x18992` +1024) produced **visible terrain deformation** (caves inward), Flik/objects still rendered, and **collision did NOT follow** — Flik walked on the original surface. See [[Experiment - G28 Candidate A floor Y]].
- **G29**: tracing the actual player-Y writer ([[FUNC_8003633C]] @ commit `0x80036cec`) leads to the sector table + plane records, a *different* file (LEVEL.RAW chunk 32) than the visual payload. See [[Experiment - G29 collision lever validation]].
- Vindicates the **G5 negative** ([[Finding - No static collision consumer]]): collision reaches its data via a non-global `[sector+0x10]` pointer chain, invisible to a static global scan.

## Related functions
[[FUNC_80010000]] · [[FUNC_800172DC]] (visual) · [[FUNC_8003633C]] · [[FUNC_800345CC]] · [[FUNC_80030F60]] (collision)

## Related memory structures
[[MEM - fcn.80010000 mesh payload]] · [[MEM - Terrain vertex buffer 8012C1D0]] (visual) · [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] (collision)

## Related experiments
[[Experiment - G28 Candidate A floor Y]] · [[Experiment - G29 collision lever validation]] · [[Experiment - G30 localized terrain edit]]

## Related fixtures / save states
[[Fixture - g30 openground]]

## DuckStation APIs used
[[API - execTrace]] · [[API - accessLog]] · [[API - scatterWrite]] · [[API - gpu.readVramRect]] · [[API - visual diff]]

## Next steps
- Produce a *photogenic* matched localized pit — currently rendering-limited (see [[Finding - Localized terrain edit]]).
- A permanent disc edit of either layer needs the [[Finding - LEVEL.RAW is compressed|LZ codec]].

## Source
`src_re_geometry/geometry_g28_candidate_a_runtime_confirmation.md`, `geometry_g29_collision_source_plan.md`, `geometry_g30_terrain_render_source_plan.md` §12-19
