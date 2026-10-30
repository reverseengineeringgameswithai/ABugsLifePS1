---
kind: function
id: FUNC_8005222C
aliases: [FUNC_8005222C, 0x8005222c]
address: 0x8005222C
name: level-transition_orchestrator
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

# FUNC_8005222C - level-transition orchestrator

## Purpose

The transition wrapper the shell state machine runs to change level/scene. **It saves the requested `current_scene_id`, swaps it to the "loading" scene 19 to load global/common resources, runs a screen-fade + per-step resource pass, resets the gameplay-state cluster + scroll/subsystem state, then restores `current_scene_id` to the target.** It does **not** load the target stage's files itself (that is a separate `0x8003cf2c(scene_id)` call from the shell SM) and does **not** move the player. STATIC (`exe_read.py --disasm`); live execution unproven ([[Finding - Level-warp mechanism]] / GAP-0001).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8005222C.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8005222C`
- Name: `level-transition_orchestrator`
- Original note: `ObsidianVault/Functions/FUNC_8005222C.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8005222C.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8005222C.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8005222C.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

