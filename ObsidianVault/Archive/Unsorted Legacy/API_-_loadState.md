---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - loadState.md
aliases:
  - "API - loadState"
migration_action: needs_review
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - loadState.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - loadState
type: api
category: Save-state
tags: [api, duckstation, savestate, fixture]
---
# API — loadState

> Load a save state (the basis of every reproducible/fixture-based experiment).

## Methods & syntax
**`emulator.loadState {path, pause_after_load=true, validate_disc=true, auto_select_disc=false}`** (absolute path, must exist) → `{loaded, path, paused, pc, game_serial, game_title, ...}`.
Fixture variant: **`fixtures.load {id}`** loads the save state behind a [[API - findings store|fixture]].

## (new) Disc validation — guards the wrong-disc hard crash
> [!success] `loadState` now **checks the mounted disc matches the save state by default** (`validate_disc:true`). This retires the long-standing [[DuckStation API Index|footgun]]: loading a state with a *different disc* mounted hard-crashed the instance.
- **`validate_disc`** (default **true**): on a disc-serial mismatch, returns a **structured error `-32006`** with `error.data = {expected:{serial, title, media_path, subimage_index}, current:{serial, title, media_path, subimage_index}}` — *instead of* loading and crashing. Pass `validate_disc:false` to restore the raw historical (unsafe) behavior.
- **`auto_select_disc`** (default **false**): when the expected disc's `media_path` is known, the loader **inserts that disc** (via [[API - media control|loadMedia]]) and re-checks before loading — so the right disc is mounted automatically. Without it (and without the disc mounted) you get the `-32006` mismatch error and must insert the disc yourself.

## Best use in ABL RE
Start every experiment from a named [[Fixtures Index|fixture]] (not "wherever the game is") — this is rule #1 of [[API - determinism]].

## Common mistakes / gotchas
> [!warning] **loadState clears all non-halting instrumentation:** accessLog + execTrace watches are dropped, transferLog is disabled+cleared, the gp0Trace ring is cleared. **Re-arm/re-start after every load.** User breakpoints and controller holds DO persist.
- **Settle one frame after loadState before [[API - addWatch]]** — otherwise it can crash (ABL hard-won lesson).
- GUI/hotkey/rewind loads do NOT clear the gp0Trace ring — call `gp0Trace.clear` after those.

## ABL examples
Every G29/G30 run loads [[Fixture - g30 openground]] / [[Fixture - g30 openfloor]]; the starry-night work loads [[Fixture - starry night workbench]].

## Related
[[API - saveState]] · [[API - media control]] · [[API - findings store]] · [[API - accessLog]] · [[API - execTrace]] · [[API - determinism]] · [[Fixtures Index]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
