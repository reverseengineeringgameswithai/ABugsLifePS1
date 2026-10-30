---
system: red_berry
phase4_row: C06_red_berry
status: substantiated-partial-bounded-exhausted
source_state: original_game
---

# Red berry

## Confirmed retail behavior

- Red is equipped selector 0 at `0x800A6597` and thrown contact type 2.
- Its constructor row is `0x80079444`: lifetime 100, connection class 1, flags `0xE5`, and damage byte `0x70`.
- Red uses the shared straight-ballistic throw and retirement system documented in [[SYS_berry_projectile_and_homing]].
- Against an ordinary actor, damage byte `0x70` selects the default path and subtracts exactly 1 from enemy-local counter `+0x6E`.
- Against runtime berry-tough state `enemy+0x5C & 0x40`, red connection class 1 takes reaction-only handling and inflicts zero counter damage.
- When red reduces the local counter to zero, the defeat is temporary: the shared hit/death program runs, but the permanent-enemy quota at `0x800A658E` is not decremented.
- Resistance is a runtime two-state law, not a hidden five-tier species table. See [[SYS_enemy_berry_resistance]].

## Implementation caution

The contact scan keeps its pointer eight bytes past the allocation base. ASM `s1+0x24` therefore names allocation-base `+0x2C` (connection class), while ASM `s1+0x2C` names allocation-base `+0x34` (damage byte). Preserve this bias when reconstructing the handler.

## Boundaries

Boss overlay defeat floors and phase FSMs remain boss-row behavior. Campaign-wide impact visuals and exact GPU/SPU ownership are not claimed.

Evidence: [[EXP_2026-08-04_phase4_c06_red_berry]] and `analysis/phase4_c06_red_berry.json`.

