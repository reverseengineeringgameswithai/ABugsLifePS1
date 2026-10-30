---
title: Enemy contact damage
system: player damage / enemy collision
phase4_row: D03_contact_damage
status: substantiated partial, bounded-exhausted
updated: 2026-08-04
---

# Enemy contact damage

## Confirmed shared law

Ordinary enemy body contact reaches resident handler `0x8004A700` through
`0x8004B4A0`. The damage amount is not an enemy-family property: an accepted,
unsuppressed ordinary hit subtracts exactly one from signed true health
`0x800A6594`.

The pristine executable has exactly six direct calls to `0x8004A700`. Four are
ordinary contact lanes (`0x80049740`, `0x8004B4A0`, `0x80058A48`, and
`0x8005C9F8`). Calls `0x800496B0` and `0x80049868` pass nonzero special kinds and
bypass the ordinary health branch. They must not be counted as enemy-contact
damage variants.

## Hitbox admission

Actor body contact uses two geometric stages in `0x8004ABF4`:

1. A broad sphere centered at actor XYZ plus signed actor fields
   `+0x64/+0x66/+0x68`. Player Y is biased by `-7360`; all three deltas are
   shifted right five. The radius is actor `+0x6A + 250`.
2. A pose-indexed oriented ellipsoid selected through actor `+0x44` and the
   table at actor `+0x74`. Its radius is also expanded by `250`.

Both stages must pass. Actor reaction lockout `+0x6C`, flags, player action
state, and global mode gates can still reject the candidate. Consequently,
families and animations can have different reach through authored geometry
without having different damage amounts.

## Knockback and suppression order

For ordinary contact, the handler builds a collision-derived X/Z vector, calls
the GTE-backed normalizer `0x80060284`, quarter-scales its components, and writes
player velocity X/Z at `0x800A652C/0x800A6534`. These horizontal writes occur
before the stagger and power suppression tests.

On an accepted health-damaging hit the handler then:

- writes vertical velocity `0x800A6530 = -1024`;
- writes player state `0x800A6580 = 5`;
- clears ground, air-timer, substate, and interaction-latch fields
  `0x800A6582/84/86/9E`;
- subtracts one from `s16 0x800A6594`;
- arms signed stagger timer `0x800A6592 = +45` if Flik survives.

A positive stagger timer suppresses another health decrement and the vertical
launch, but it does not refresh itself. The signed timer update at
`0x8004853C..0x800485F0` moves positive and negative values one step toward zero.
Power or region interception uses a separate `-30` signed-timer lane; fatal and
special transitions use `-45`. Those negative lanes are related state machinery,
not evidence for a different ordinary damage amount.

## Retained-capsule confirmation

Six centrally pinned, control-matched capsules were reduced offline in C. Their
2,692 reconstructed frame boundaries produced 8,076 RAM/VRAM/SPU-RAM hash checks
with zero mismatch.

Three independent actor families provide positive contact events:

| Capsule | Movie frame | Health | Timer | Velocity X/Y/Z |
|---|---:|---:|---:|---:|
| D08 fly | 190 | 4 -> 3 | 45 | `561/-1024/859` |
| D11 grub | 201 | 4 -> 3 | 45 | `-466/-1024/-913` |
| D11 mite | 111 | 4 -> 3 | 45 | `-244/-1024/-996` |

All three horizontal magnitudes are approximately `1025`, independently
corroborating the normalized-and-quarter-scaled static path. In every case the
timer reaches zero exactly 90 movie frames later after consuming 45 ticks: one
tick per two 60 Hz frames, or a 1.5-second health-immunity window.

## Scope boundary

D03 is a substantiated Partial and bounded-exhausted. The damage, hitbox,
suppression, timer, and knockback relationships are closed. A numeric census of
every pose ellipsoid for every actor would be low-return presentation breadth,
not a missing mechanic. Reopen for a contradictory family, a named pose-specific
reach question, or an explicit full hitbox catalog.

See [[EXP_2026-08-04_phase4_d03_contact_damage]].

## Native invulnerability-window control (D03 closure)

A pristine Interpreter save-state run on 2026-08-04 confirmed that collision admission continues while the contact timer is positive. The beetle re-entered `player_contact_damage_8004A700` at timer values 25, 14, and 3 without executing the health store or refreshing the timer. After the timer reached zero, the next native contact executed the health store, changed health 3 to 2, and reset the timer to 45. No movie, RAM write, code patch, function injection, or actor reposition was used.

The executable reproduction is `tools/scenarios/duckstation/d03_contact_iframe.yaml`; the guarded machine result is `analysis/phase4_d03_runtime_control.json`. Exact cycles, transient hashes, tool commands, and the closure rationale are in [[EXP_2026-08-04_phase4_d03_contact_damage]].

## Native invulnerability-window control (D03 closure)

A pristine Interpreter save-state run on 2026-08-04 confirmed that collision admission continues while the contact timer is positive. The beetle re-entered `player_contact_damage_8004A700` at timer values 25, 14, and 3 without executing the health store or refreshing the timer. After the timer reached zero, the next native contact executed the health store, changed health 3 to 2, and reset the timer to 45. No movie, RAM write, code patch, function injection, or actor reposition was used.

The executable reproduction is `tools/scenarios/duckstation/d03_contact_iframe.yaml`; the guarded machine result is `analysis/phase4_d03_runtime_control.json`. Exact cycles, transient hashes, tool commands, and the closure rationale are in [[EXP_2026-08-04_phase4_d03_contact_damage]].
