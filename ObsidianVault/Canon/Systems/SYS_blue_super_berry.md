---
system: blue_super_berry
phase4_row: C07_blue_berry
status: substantiated-partial-bounded-exhausted
source_state: original_game
---

# Blue/Super Berry

## Confirmed retail behavior

- Blue/Super is equipped selector 1 and constructor type 5.
- Its parameter row is `0x80079480`: record class 2, timer 100, model/marker 110, connection class 2, flags `0xE5`, damage byte 0, and presentation bytes `[0x20,0x80]`.
- Its trajectory, model, lifetime, active/render flags, four-shot ownership limit, and retirement causes are identical to red. See [[SYS_berry_projectile_and_homing]].
- Against both ordinary and runtime berry-tough (`enemy+0x5C & 0x40`) actors, blue subtracts exactly 2 from enemy-local counter `+0x6E`.
- Blue bypasses the berry-tough reaction-only exit because neither its connection class 2 nor damage byte 0 equals the excluded red value 1. See [[SYS_enemy_berry_resistance]].
- Counter exhaustion is a temporary defeat. Blue never decrements permanent-enemy quota `0x800A658E`.
- Collection writes selector 1 and uses pickup sound `0x35`; throwing uses shared sound 2.
- Blue damage byte 0 is the projectile class admitted by the bonus-3 grasshopper streak gate. Challenge progression is owned by the bonus rows.

## Limits

The presentation tuple `[0x20,0x80]` is structurally bound but its exact GPU/palette semantics are not named. Boss overlay defeat floors and exact impact SPU ownership are outside the bounded C07 core.

Evidence: [[EXP_2026-08-04_phase4_c07_blue_berry]] and `analysis/phase4_c07_blue_berry.json`.

