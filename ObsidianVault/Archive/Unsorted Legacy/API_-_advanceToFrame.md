---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - advanceToFrame.md
aliases:
  - "API - advanceToFrame"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - advanceToFrame.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - advanceToFrame
type: api
category: Execution control
tags: [api, duckstation, execution, frame, movie]
---
# API — advanceToFrame

> Fast-forward forward-only to a target frame with temporary turbo speed control, without hand-computing/chunking the delta.

## Methods & syntax
- **`emulator.advanceToFrame {frame, max_frames?=100000}`** → `{target_frame, start_frame, frames_advanced, status}`. `frame` is an absolute emulator `debugger.status.frame` / `status.frame`. Temporarily enables turbo for the run, restores the prior turbo state afterward, and returns immediately with `frames_advanced:0` if the target equals the current frame. If the target is before the current frame, it fails (no rewind). If the delta exceeds `max_frames`, it fails rather than accidentally burning a long run.
- **`movie.advanceToFrame {frame, max_frames?=100000}`** → `{target_frame, start_playback_index, frames_advanced, movie, status}`. Requires active playback. `frame` is the 0-based movie playback frame / `movie.status.playback_index`, not the emulator frame. `frame == frame_count` advances to the end and stops playback. Backward or out-of-range targets fail.

`emulator.advanceFrames` itself is only a deterministic frame-stepper and still obeys the current speed limiter. These `advanceToFrame` helpers temporarily engage turbo, while still reusing the same chunked frame-step path so controller holds are re-applied every frame. During movie playback, every intervening recorded input sample is consumed; this is not a seek/skip.

## Best use in ABL RE
Use `emulator.advanceToFrame` when a fixture/log gives an absolute emulator frame. Use `movie.advanceToFrame` after `movie.startPlayback` when a boot movie says the interesting point is at movie frame N. For the ABL boot movie case, this avoids manually calculating `advanceFrames` chunks while still replaying all menu/boot inputs.

## Common mistakes / gotchas
- This is forward-only. It cannot rewind a running emulator or a movie cursor; reload the anchor/start state and start playback again.
- `emulator.advanceToFrame.frame` and `movie.advanceToFrame.frame` are different coordinate systems.
- Raw `emulator.advanceToFrame` cannot pass menus by itself; a movie or injected controller input must supply input.

## Related
[[API - execution control]] · [[API - movie]] · [[API - controller input]] · [[API - advanceUntil]]

Source: ~/duckstation/docs/external-debugger.md (+ docs/external-debugger-movie.md, EXTERNAL_DEBUGGER_CONTROL.md)
