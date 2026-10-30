---
kind: function
id: FUNC_8005EC94
aliases: [FUNC_8005EC94, 0x8005ec94]
address: 0x8005EC94
name: ANM_animation_player_(keyframe_core)
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

# FUNC_8005EC94 - ANM animation player (keyframe core)

## Purpose

Plays a character's `.ANM` animation: walks the active animation sub-block's frames and decodes its **bitmask-compressed channel keyframes**, producing the per-frame pose. Identified live (no operator) while driving Flik forward → [[Finding - Character ALL model format]].

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8005EC94.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8005EC94`
- Name: `ANM_animation_player_(keyframe_core)`
- Original note: `ObsidianVault/Functions/FUNC_8005EC94.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8005EC94.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8005EC94.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8005EC94.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

