---
kind: mod
id: MOD_training_pause_framebuffer_sync
name: TRAINING pause framebuffer synchronization (superseded)
status: superseded_invalid_verification
created: 2026-07-11
updated: 2026-07-11
confidence: disproved
source_state: mod_history
superseded_by:
  - MOD_training_pause_n_suppression
src_paths:
  - tools/training_word_pickups.py
  - tests/test_training_word_pickups.py
evidence:
  - EXP_2026_07_11_training_pause_n_double_buffer_flash
---

# TRAINING pause framebuffer synchronization (superseded)

## Historical approach

The first implementation called original `MoveImage` on the START-input tick to
copy framebuffer A to B. Its intent was to equalize two adjacent N phases before
the pause menu began alternating render contexts.

This is no longer present in `tools/training_word_pickups.py` or ALLMODS.

## Why it failed

The original verification loop invoked unsupported CLI command `advance-frame`
under `--quiet`; the emulator frame counter never advanced, so repeated captures
were falsely reported as stable. Correct `advance-frames --frames 1` testing
showed that pause keeps calling `frame_present` and replaying both resident scene
OTs. The next OT replay reintroduced its captured N phase after the one-time
framebuffer copy.

Post-present copy experiments were also rejected because placing `MoveImage`
around the original GPU synchronization path stalled guest progress. They were
debugger-only RAM experiments and were never shipped.

Current implementation: [[MOD_training_pause_n_suppression]]. Corrected original
RE and runtime evidence:
[[EXP_2026-07-11_training_pause_n_double_buffer_flash]].

