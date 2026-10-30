---
kind: function
id: FUNC_8001A1DC
aliases: [FUNC_8001A1DC, 0x8001a1dc]
address: 0x8001A1DC
name: LEVEL.RAW_LZSS_decompressor
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

# FUNC_8001A1DC - LEVEL.RAW LZSS decompressor

## Purpose

The custom codec that decompresses every LEVEL.RAW chunk (visible terrain + collision + sky color table). **The "LZ codec gate"** that blocks permanent disc edits.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8001A1DC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8001A1DC`
- Name: `LEVEL.RAW_LZSS_decompressor`
- Original note: `ObsidianVault/Functions/FUNC_8001A1DC.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8001A1DC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8001A1DC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8001A1DC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

