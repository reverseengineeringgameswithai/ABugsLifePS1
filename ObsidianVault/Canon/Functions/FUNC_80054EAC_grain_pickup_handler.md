---
kind: function
id: FUNC_80054EAC
aliases: [FUNC_80054EAC, 0x80054eac]
address: 0x80054EAC
name: grain_pickup_handler
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

# FUNC_80054EAC - grain pickup handler

## Purpose

Handles collecting a grain: bumps the grain count and, at exactly 50, runs the all-grain reward path. **Cursor consumption (2026-06-20):** the "script byte" it reads is from the **resident pseudo-random table `0x80017DB4`** (the cursor `0x800822f4` is seeded there, NOT LEVEL.DAT — [[Gameplay - Resident Event Stream]]). Grain reads **1 byte** `first` (`cursor += 1`) used as a **gate** (`maybe_grain_pre_effect` runs only if `first & 0x0f == 0` and scene ≠ 0x11); the pre-effect then reads **1 more byte** `second`, using `second & 1` as a **variant** into `fcn.80044d28`. So grain pulls 1–2 noise bytes as low-bit gate/variant selectors — consistent with a shared PRNG source, not a script.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80054EAC.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x80054EAC`
- Name: `grain_pickup_handler`
- Original note: `ObsidianVault/Functions/FUNC_80054EAC.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80054EAC.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80054EAC.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80054EAC.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

