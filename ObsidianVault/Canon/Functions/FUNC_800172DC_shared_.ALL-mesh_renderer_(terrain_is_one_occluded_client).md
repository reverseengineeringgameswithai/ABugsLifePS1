---
kind: function
id: LEGACY_FUNC_800172DC_shared_all_mesh_renderer
aliases: [LEGACY_FUNC_800172DC_shared_all_mesh_renderer, shared_.ALL-mesh_renderer_(terrain_is_one_occluded_client)]
address: 0x800172DC
name: shared_.ALL-mesh_renderer_(terrain_is_one_occluded_client)
status: superseded
canonical_address: false
superseded_by: FUNC_800172DC_master_mesh_renderer
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence: []
src_paths: []
patch_policy: unknown
---

# FUNC_800172DC - shared .ALL-mesh renderer (terrain is one occluded client)

## Purpose

Draws GP0 0x3C shaded-textured quads from a **shared mesh vertex buffer** (terrain **and** actors — e.g. `FLICK.ALL`). It is a **general mesh renderer**, **not** the confirmed visible-floor renderer: in the G30 terrain states its output is fully occluded (see callout). The **visible walkable floor = LEVEL.DAT via [[FUNC_80010000]]** (f13). [!important] **Scope correction (2026-07-07, P54): "occluded" holds for PRISTINE geometry only.** On Track-B authored discs the LEVEL.DAT payload floor is MOVED to authored heights, and this renderer's chunk-35 ground mass becomes **visible** (it was always drawn — the pristine payload floor merely covered it exactly). Live A/B on the bigland disc: stubbing `FUNC_800172DC` (or zeroing buffer `0x8012C1D0..0x8012E784`) removes the visible original ground mass while Flik/enemies/HUD keep rendering. Custom levels suppress it via the level-gated P11-cave RA...

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_800172DC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x800172DC`
- Name: `shared_.ALL-mesh_renderer_(terrain_is_one_occluded_client)`
- Original note: `ObsidianVault/Functions/FUNC_800172DC.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_800172DC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_800172DC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_800172DC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
