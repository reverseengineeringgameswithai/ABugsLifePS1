---
kind: function
id: FUNC_8001EA6C
aliases: [FUNC_8001EA6C, 0x8001ea6c]
address: 0x8001EA6C
name: survivor-list_primitive_builder_-1
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

# FUNC_8001EA6C - survivor-list primitive builder -1

## Purpose

Consumes the render survivor list (LIST_A), bridges each survivor to its source record + payload pointer, sets up a per-object transform, and tail-calls the mesh emitter. The bridge from culled rows to drawn geometry. In G30 this path renders the wooden fence.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8001EA6C.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8001EA6C`
- Name: `survivor-list_primitive_builder_-1`
- Original note: `ObsidianVault/Functions/FUNC_8001EA6C.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8001EA6C.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8001EA6C.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8001EA6C.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

