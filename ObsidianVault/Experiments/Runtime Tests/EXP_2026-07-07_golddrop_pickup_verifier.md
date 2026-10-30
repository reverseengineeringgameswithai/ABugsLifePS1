---
kind: experiment
id: EXP_2026_07_07_golddrop_pickup_verifier
name: Gold-drop pickup verifier
status: success
confidence: confirmed
source_state: evidence
validates:
  - MOD_gold_berry_token_drop
  - HOOK_800592A4
  - HOOK_800589D4
  - SYS_hud_counters
fixtures:
  - killing_spider.movie.json
artifacts:
  - /tmp/golddrop_pickup_verify.json
---

# EXP_2026_07_07_golddrop_pickup_verifier

## Question

Does the Gold Berry token path spawn one floor glyph, collect on walk-over, increment the visible bottom gold-defeat counter, and avoid the old duplicate-token/crash behavior?

## Method

Cold-booted rebuilt ALLMODS, replayed `killing_spider.movie.json`, forced only the odds table, spawned one type-120 glyph, warped Flik onto it, and forced quota `1 -> 0` to exercise the all-defeated branch.

## Observations

- Death hook: 1.
- Spawn: 1.
- Pickup hook: 1.
- HUD pulse: 1.
- Quota store: 1.
- All-defeated call: 1.
- Finalizer call: 1.
- CPU state valid after pickup.

## Result

Success. This validates the working surface currently locked in `MOD_gold_berry_token_drop`.

## Artifacts

The detailed verifier JSON was temporary at `/tmp/golddrop_pickup_verify.json`; preserve a stable artifact if this experiment is rerun.
