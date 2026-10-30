---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - saveState.md
aliases:
  - "API - saveState"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - saveState.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - saveState
type: api
category: Save-state
tags: [api, duckstation, savestate]
---
# API — saveState

> Persist the current machine state to a `.sav`, and inspect a state's header without loading it.

## Methods & syntax
- **`emulator.saveState {path}`** (absolute; parent dir must exist) → `{saved, path, game_serial, game_title, frame}`.
- **`emulator.getStateInfo {path}`** — header metadata WITHOUT loading → `{exists, valid, title, serial, media_path, timestamp, file_size, version, has_screenshot, screenshot_width/height}`. Missing file → `{exists:false}` (not an error).

Slot-based states are not exposed — absolute paths only.

## Best use in ABL RE
Capture a result or a new fixture (e.g. after recoloring the sky → [[Fixture - night starry]]). Use `getStateInfo` to verify serial/timestamp before relying on a `.sav`.

## Common mistakes / gotchas
- Save states are **bit-exact reproducible** for CPU/RAM/GTE — the foundation of CONFIRMED claims (see [[API - determinism]]).
- Register a saved state as a fixture via `fixtures.add` so future sessions can find it ([[API - findings store]]).

## ABL examples
The fixture catalog ([[Save States Index]]) is the set of `.sav` files captured this way; `SCUS-94288_g30_openground.sav` is the canonical terrain workbench.

## Related
[[API - loadState]] · [[API - findings store]] · [[API - snapshot bundle]] · [[Fixtures Index]] · [[Save States Index]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
