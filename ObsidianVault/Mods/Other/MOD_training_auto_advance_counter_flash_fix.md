---
kind: mod
id: MOD_training_auto_advance_counter_flash_fix
name: TRAINING auto-advance counter-flash fix
status: composed_into_allmods_cold_boot_verified
created: 2026-07-11
updated: 2026-07-11
confidence: confirmed
source_state: mod
canon_dependencies:
  - Training_NPC_progression
  - Training_board_sign_images
src_paths:
  - tools/patch_training_overlay.py
  - tools/training_tutorial_stager.py
  - tests/test_training_overlay_patch.py
  - src_re/training_tutorial_progression.c
evidence:
  - EXP_2026_07_11_training_auto_advance_counter_flash
---

# TRAINING auto-advance counter-flash fix

## Change

`tools/patch_training_overlay.py` derives an incoming-step bitmask from the
manifest's voice-driven auto steps. When at least one auto step follows step 0,
the builder:

1. places a 56-byte MIPS count-selector shim in stock objective code made
   unreachable by an already-patched auto handler;
2. hooks the retail default-count logic at `0x800B3F18`, immediately before the
   animation-boundary `SIGN_RAISE` call at `0x800B3F30`;
3. returns `-1` for manifest auto rows and reproduces retail counts `5`, `2`, or
   `0` for every other row.

The current manifest auto-advances steps 0, 1, and 2, so the generated incoming
mask is `0x0006` for steps 1 and 2. The common tail at `0x800B47A8`
remains the retail `addiu v0,zero,30`; no transition timing is shortened.

The earlier zero-wait implementation is superseded. It removed the counters but
allowed Sign B to replace Sign A during the lowering animation. With the final
hook, Sign A remains selected until fully down, then blank Sign B is selected by
the original boundary call and rises normally.

This is emitted MIPS overlay code rather than a compiled C cave. The synchronized
C in `src_re/training_tutorial_progression.c` is reference pseudocode and remains
logically separate from the MOD implementation.

## Safety contract

- The shim preserves the retail 30-tick inter-step timer.
- The patch asserts all four original default-count instructions before replacing
  them.
- The cave allocator accepts only unreachable space after an auto handler's
  40-byte replacement and before the next live handler.
- Step 0 alone does not alter the common timer, because there is no customized
  incoming transition to protect.
- The selector supports only known steps 0-12 and preserves the final step-13
  loop policy.

`tests/test_training_overlay_patch.py` locks both the selective-mask behavior and
the step-0-only no-op case.

## Output

- Build: `build/ABL_ALLMODS.cue`.
- BIN SHA-256:
  `e5459d17dfd59b6a70d77125c3ee8cb6a0e0b9fb40b5ff3472072410129f6401`.
- Cold-boot movie verification: Sign A stays visible throughout lowering, Sign B
  first appears on the upward motion, and neither `6` nor `3` is visible.
- Original-engine cause and runtime evidence:
  [[EXP_2026-07-11_training_auto_advance_counter_flash]].
