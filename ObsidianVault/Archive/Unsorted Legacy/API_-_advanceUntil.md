---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - advanceUntil.md
aliases:
  - "API - advanceUntil"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - advanceUntil.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - advanceUntil
type: api
category: Execution control
tags: [api, duckstation, execution, condition]
---
# API — advanceUntil

> Advance one frame at a time until a memory/register/pc/frame condition holds (or a frame cap).

## Methods & syntax
**`emulator.advanceUntil`** `{condition:{kind:"memory"|"register"|"pc"|"frame"|"emulator_frame"|"movie_frame", address?, type?, name?, op:"eq|ne|lt|le|gt|ge|changed|unchanged|stable", value?, frames?}, max_frames (REQUIRED, 1..100000), observe?}`
→ `{stopped, reason:"condition"|"max_frames"|"timeout", frames_advanced, final_value, status, observed?}`.
- `changed/unchanged` compare vs the frame-0 baseline; `stable` needs `frames>=1`. `frame`/`emulator_frame` read emulator frame; `movie_frame` reads movie playback frame/index.

## Best use in ABL RE
Run to a meaningful game moment without scripting frame counts — e.g. advance until the player Y `0x800A6504` changes, or until a load flag flips, then inspect.

## Common mistakes / gotchas
- **`max_frames` is required** (`-32602` if missing). An already-satisfied condition returns `frames_advanced:0`. Latency scales with frame count.

## ABL examples
Used to drive the game to the moment a watch should fire during the live G29/G30 sessions — pairs with [[API - accessLog]] / [[API - execTrace]] armed beforehand. See [[Experiment - G29 collision lever validation]].

## Related
[[API - trace.armWhen]] · [[API - execution control]] · [[API - controller input]] · [[API - addWatch]] · [[Playbook - Create a deterministic experiment]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
