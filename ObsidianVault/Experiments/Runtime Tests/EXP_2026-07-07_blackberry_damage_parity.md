---
kind: experiment
id: EXP_2026_07_07_blackberry_damage_parity
name: Blackberry damage parity and descriptor restoration
status: success
confidence: confirmed
source_state: evidence
validates:
  - MOD_blackberry_net_new_berry
  - SYS_berry_projectile_and_homing
  - SYS_berry_pickup_render_descriptors
fixtures:
  - redberry_blackberry_test.sav
  - killing_spider.movie.json
artifacts:
  - build/ABL_ALLMODS.bin
  - build/ABL_ALLMODS.cue
---

# EXP_2026_07_07_blackberry_damage_parity

## Question

Does the restored Blackberry/Fastberry path keep red-equivalent damage while preserving fast physics and dark visuals, without using the old spread-shot or native descriptor overwrite paths?

## Method

Built ALLMODS, checked embedded EXE hook sites, reloaded a Blackberry test save, patched stale resident words when required by the old save state, and ran a follow-up spider movie with forced equip index `5`.

## Observations

- Active hooks were present for speed, throw, tough HP selector, and normal HP selector.
- `0x80047228` remained native and stored `s1 = 2` for forced Blackberry.
- Old spread hook `0x80047254` and old throw-counter gate `0x80048FFC` matched pristine.
- Fast physics fired once for the throw and shifted velocity `<< 1`, gravity `<< 2`.
- Thrown color store wrote `0x2c2b051a`.
- Against spider id `9`, forced Blackberry matched red: `enemy+0x6e` went `2 -> 1`, then `1 -> 0 -> 999`.
- Permanent quota `0x800A658E` did not decrement.

## Result

Success. Blackberry/Fastberry is red-equivalent damage plus fast physics and dark visuals. It is not permanent, not spread-shot, and not homing.

## Follow-up Risk

Native descriptor memory must remain untouched. The known bad descriptor reuse at `0x80082030..0x8008203C` caused seed and mega/homing color regressions.
