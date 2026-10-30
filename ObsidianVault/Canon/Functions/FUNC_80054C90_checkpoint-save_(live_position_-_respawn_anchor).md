---
kind: function
id: FUNC_80054C90
aliases: [FUNC_80054C90, 0x80054c90]
address: 0x80054C90
name: respawn-anchor-update_(live_position_to_safe_anchor)
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

# FUNC_80054C90 - respawn-anchor update (live position to safe anchor)

## Purpose

Per-frame gameplay routine that, when its player/scene and contact-distance gates pass, **copies the live player position into the safe respawn anchor** `0x800a6550/54/58`. It is the update half of the native respawn-anchor pair ([[Gameplay - Player Spawn and Placement]]); the restore half is [[FUNC_8005B134]]'s tail. This continuously maintained internal state is not a player-activated world mechanic. STATIC (`exe_read.py --disasm`).

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_80054C90.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Full gate list, decoded and cross-verified (2026-08-03)

Hand-reconstructed at `asm/hand_written/80054c90_checkpoint_save.s`, cross-verified
instruction-for-instruction against the raw pristine listing
`asm/nonmatchings/resident/80054c90.s`. The anchor update fires only when ALL of these hold:

- player `+0x82` (`0x800A6582`) nonzero
- transition timer `0x80082470` == 0
- helper `0x80038e48` returns 0
- player `+0x84` (`0x800A6584`) == 0
- **scene_id (`0x80082504`) != 6** — a literal branch (`lw v1,0x2504(v1)` /
  `addiu v0,zero,6` / `beq v1,v0,exit`), verified directly against the raw ASM. Scene 6 is
  `F04_cliffside_canyon`: **the safe anchor NEVER updates in that scene**, confirmed live
  across 440+ frames of real movement (`analysis/phase4_c15_respawn_anchor.json`).
- helper `0x80038f84` returns nonzero
- helper `0x80038f38` does not return 4
- a 64-record proximity scan over the enemy actor pool (`0x8009FD80`, stride `0x84`) rejects
  the update if too close to certain flagged/typed actors (id near `0x27..0x29`,
  flags `& 0xA0`)

If all pass: writes live XYZ to the anchor plus companion fields `0x800A6578` and a bit in
`0x800A6590`.

The exact semantic meaning of `+0x82`/`+0x84` and the three helper functions is inferred from
their structural role, not independently proven. See
[[EXP_2026-08-03_phase4_c15_respawn_anchor]] and `analysis/phase4_c15_respawn_anchor.json`.

## Address / identity

- Address: `0x80054C90`
- Name: `respawn-anchor-update_(live_position_to_safe_anchor)` (legacy filename/symbol retained for compatibility)
- Original note: `ObsidianVault/Functions/FUNC_80054C90.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_80054C90.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_80054C90.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_80054C90.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.
