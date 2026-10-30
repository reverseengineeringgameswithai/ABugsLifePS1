---
kind: function
id: FUNC_800224EC
aliases: [FUNC_800224EC, 0x800224ec]
address: 0x800224EC
name: scene_-_render_driver
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

# FUNC_800224EC - scene - render driver

## Purpose

The per-scene/per-frame render driver. Reads the parser geometry pointers, sets up a camera matrix, runs the cull→build→emit pipeline. The top of the visible-geometry render chain (NOT collision).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_800224EC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x800224EC`
- Name: `scene_-_render_driver`
- Original note: `ObsidianVault/Functions/FUNC_800224EC.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_800224EC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_800224EC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_800224EC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

