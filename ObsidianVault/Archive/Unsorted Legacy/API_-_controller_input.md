---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - controller input.md
aliases:
  - "API - controller input"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - controller input.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - controller input
type: api
category: Execution control
tags: [api, duckstation, controller, input]
---
# API — controller input

> Inject frame-accurate controller input (the deterministic alternative to the keyboard).

> [!success] Updated 2026-06-26: **`setControllerState` now injects analog sticks too.** Pass `analog:{lx/ly/rx/ry:0..255}` (128=centre) alongside/instead of `buttons`; held axes re-apply every frame like held buttons, **driven directly past host deadzone/sensitivity/inversion**. `getControllerState` reports them in `analog`/`analog_held`; `clearControllerState` re-centres them. Analog requires an AnalogController (else `-32004`). **verify in `~/duckstation` before relying on it.**

## Methods & syntax
- **`emulator.setControllerState {port=0, buttons:{name:bool}?, analog:{lx/ly/rx/ry:0..255}?}`** (merged/partial; supply buttons and/or analog, ≥1 required), **`getControllerState`** (returns `buttons`, plus `analog`/`analog_held` for an AnalogController), **`clearControllerState`** (releases buttons + re-centres held axes).
- **`emulator.pressButton {button|buttons, frames=1 | seconds, port=0, release_after=true}`** → holds for a duration, advances, optionally releases. Duration is `frames` OR **`seconds`** (converted via the live frame rate, ~59.94 NTSC; takes precedence). Long holds (>600 frames) advance in chunks with the button held; cap 100000 frames (~28 min). *(pressButton is buttons-only; for sticks use `setControllerState` + `advanceFrames`.)*
- **`emulator.advanceFrames {frames | seconds}`** — same `frames`/`seconds` duration model. Frame rate is reported by `getVideoStatus.frame_rate`.
- Buttons: up/down/left/right, cross/circle/square/triangle, l1/r1/l2/r2, start/select (+l3/r3 analog only). Analog axes: lx/ly/rx/ry (0..255, 128=centre), AnalogController only. DigitalController/AnalogController only (else `-32004`).
- **Client/MCP:** `set-input --analog 'lx=255,ly=0,rx=128,ry=128'` (combinable with `--buttons`) / `set_controller_state(analog={"lx":255,"ly":0})`.
- **Hold for N seconds:** `press-button --button cross --seconds 2` (client) / `press_button("cross", seconds=2)` (MCP). Validated: 1 s→60 fr, 0.5 s→30 fr, 15 s→897 fr (chunked), button released after.

## Best use in ABL RE
Scripted, reproducible input — required for [[API - determinism]]. Held buttons are re-applied every frame by `emulator.advanceFrames`.

## Common mistakes / gotchas
- This sets emulated bind state (not OS keyboard, not memory). Held input is **left in place** after an experiment `run` — `clearControllerState` to release.
- Dropped on game unload / server stop.

## ABL examples
Driving Flik to walk/jump during the G29 collision test (jump then observe fall) and to reach a specific spot before arming watches → [[Experiment - G29 collision lever validation]].

## Related
[[API - advanceUntil]] · [[API - execution control]] · [[API - experiment runner]] · [[API - determinism]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
