---
kind: function
id: FUNC_8001DFE4
aliases: [FUNC_8001DFE4, 0x8001dfe4]
address: 0x8001DFE4
name: scene-geometry_draw_dispatcher
status: static_seen
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

# FUNC_8001DFE4 - scene-geometry draw dispatcher

## Purpose

Dispatches scene geometry to a fixed set of 5 emitter routines — one of which ([[FUNC_800172DC]]) draws the terrain-mesh layer (later found to render **occluded** — the **visible** floor is LEVEL.DAT via [[FUNC_80010000]], f13; see [[Finding - Visible terrain renderer]], [[Gap Audit|GAP-0011]]). Found in G30 while mapping the render call tree.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8001DFE4.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8001DFE4`
- Name: `scene-geometry_draw_dispatcher`
- Original note: `ObsidianVault/Functions/FUNC_8001DFE4.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8001DFE4.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8001DFE4.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8001DFE4.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

