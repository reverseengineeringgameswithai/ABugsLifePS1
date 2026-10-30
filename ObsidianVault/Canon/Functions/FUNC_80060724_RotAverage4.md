---
kind: function
id: FUNC_80060724
aliases: [FUNC_80060724, 0x80060724, RotAverage4, libgte_transform_leaf_bank]
address: 0x80060724
name: RotAverage4
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
evidence:
  - EXP_2026-07-09_identity_reconciliation
src_paths: []
patch_policy: do_not_patch
---

# FUNC_80060724 - libgte transform leaf bank

> **RCA a3 identity fix (2026-07-09):** Renamed libgte_transform_leaf_bank -> **RotAverage4** (PsyQ GTE library routine; identified by `re_symbols.sym` SDK signature match). `patch_policy: do_not_patch` (SDK).


## Purpose

A shared libgte transform leaf (reads source verts a0–a3, writes screen XY). The render layer earlier G-work missed because it only searched the inline `0x8001xxxx` rtps sites.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80060724.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80060724`
- Name: `libgte_transform_leaf_bank`
- Original note: `ObsidianVault/Functions/FUNC_80060724.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80060724.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80060724.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80060724.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

