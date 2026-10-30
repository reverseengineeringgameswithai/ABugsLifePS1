---
kind: function
id: FUNC_8005B714
aliases: [FUNC_8005B714, 0x8005b714]
address: 0x8005B714
name: gameplay-state_reset_-_byte-stream_cursor_seed
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

# FUNC_8005B714 - gameplay-state reset - byte-stream cursor seed

## Purpose

The **only place in the whole game image** that *seeds* the shared byte-stream cursor `0x800822f4` ([[Gameplay - DAT Event Stream]], [[MEM - Event System Globals]]). It is a gameplay-state reset: it zeroes a broad block of the `0x80082xxx` state cluster and sets the cursor to a **fixed resident address `0x80017DB4`**. All STATIC (`tools/exe_read.py` on `SCUS_942.88`); runtime confirmation is local-only ([[DuckStation Fork Reproducibility]] / GAP-0001). *Earlier "0 `jal` callers" was an artifact of searching for `0x8005b714` (the `addiu sp` line); the real entry is `0x8005b70c`.* The function is **not** in the scene-handler/loader/state dispatch tables — it is a direct callee of the state machine. State path = **gameplay/level-init (scene entry)**, not warp-execution, death, or menu.

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8005B714.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Address / identity

- Address: `0x8005B714`
- Name: `gameplay-state_reset_-_byte-stream_cursor_seed`
- Original note: `ObsidianVault/Functions/FUNC_8005B714.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8005B714.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8005B714.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8005B714.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

