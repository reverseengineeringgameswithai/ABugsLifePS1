---
kind: function
id: FUNC_80045A60
aliases:
- FUNC_80045A60
- 2147768928
- '0x80045a60'
- transition_finalizer_subsystem_reset
address: '0x80045a60'
name: transition_finalizer_-_subsystem_reset
status: byte_matched
confidence: confirmed
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-08-10_phase4_f01_oracle_breadth_repair
src_paths:
- src/main/80045a60_transition_finalizer_subsystem_reset.c
patch_policy: unknown
---

# FUNC_80045A60 - transition finalizer - subsystem reset

## Purpose

Called at the **end** of the transition orchestrator [[FUNC_8005222C]] (after the fade, before restoring `current_scene_id`). It clears a state flag bit and resets two higher-level subsystem managers. It is **not** player placement and **not** a camera reset. STATIC (`exe_read.py --disasm`).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80045A60.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80045A60`
- Name: `transition_finalizer_-_subsystem_reset`
- Original note: `ObsidianVault/Functions/FUNC_80045A60.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80045A60.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Runtime calling condition

The repaired F01 campaign oracle certifies the scene-flow decision at
`0x8004FF28` with pristine instruction word `0x846323A0`. Across the exact
declared 19-level corpus, all 35 certified decisions obeyed:

> this function is called iff `scene_transition_request != 2` and
> `[0x8008225C] == 0`.

The corpus contains 19 attributable calls and 16 skips, with zero law failures.
This is a bounded runtime result over those complete, non-truncated replay
windows, not a claim that the submitted sessions form a complete applicability
matrix. See [[EXP_2026-08-10_phase4_f01_oracle_breadth_repair]].

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80045A60.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80045A60.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
