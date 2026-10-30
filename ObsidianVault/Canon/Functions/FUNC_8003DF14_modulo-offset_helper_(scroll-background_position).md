---
kind: function
id: FUNC_8003DF14
aliases: [FUNC_8003DF14, 0x8003df14]
address: 0x8003DF14
name: modulo-offset_helper_(scroll-background_position)
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

# FUNC_8003DF14 - modulo-offset helper (scroll-background position)

## Purpose

A small leaf math helper, **not** a resource loader or scene selector. It computes a wrapped offset `a0 mod table[flag]` and stores it (plus `a1`) to two gp globals. Called by the transition orchestrator [[FUNC_8005222C]] `(0, −8)` to reset a scroll/background offset during the fade. STATIC (`exe_read.py --disasm`).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8003DF14.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8003DF14`
- Name: `modulo-offset_helper_(scroll-background_position)`
- Original note: `ObsidianVault/Functions/FUNC_8003DF14.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8003DF14.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8003DF14.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8003DF14.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

