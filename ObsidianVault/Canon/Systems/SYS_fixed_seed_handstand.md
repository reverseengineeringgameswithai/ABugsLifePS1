---
kind: canon
id: SYS_fixed_seed_handstand
status: confirmed_bounded
updated: 2026-08-03
confidence: high
related:
  - SYS_seed_carry_plant_lifecycle
  - SYS_player_action_state_laws
  - EXP_2026_08_03_phase4_a10_handstand
---

# Fixed-seed handstand

## Confirmed resident law

The handstand and ordinary movable-seed pickup share the fresh-Square candidate
scan in `player_contact_response` (`0x80047284`). The selected actor is stored as
an offset from `0x8009FD80` in player `+0x5C`.

The discriminator is actor `+0x40`:

- values below 3 select movable-seed pull-in mode 8;
- values at least 3 select fixed-seed handstand mode 14;
- the captured LEVEL01 fixed seed has value 3, selected offset `0x108`, actor
  `0x8009FE88`, and source record `0x80094A70`.

The exact decision and store are `0x8004785C..0x80047874`. The actor's selected
bit `0x40` is set in flags `+0x5C` at `0x80047888`.

## Mounted lifetime

Mode 14 is tested at `0x80048B2C`. It branches directly to `0x80048D90`,
bypassing the ordinary grounded/air vertical-state evolution. In the retained
fixture it lasts for movie frames 1042 through 1215. Flik's XYZ is byte-exact
constant for 114 frame boundaries (1102 through 1215), while grounded remains
zero.

Proximity without a Square edge does not mount: movie frames 1024 through 1039
remain mode 0, selected offset 0, and grounded.

## Release and landing

A fresh Square edge takes the selected-actor release path:

- `0x80047C60` clears actor flags `+0x5C` bit `0x40`;
- behavior 3 selects `0x80047CD0`, which writes player action 17;
- `0x80047CE8` clears the selected offset;
- `0x80047D00` writes transient seed-action mode 13;
- `0x800490AC` clears mode 13 during the player update;
- `0x80048D64` advances vertical state 5 to handstand-dismount state 6.

The captured state-6 arc lasts 32 frame boundaries (1222 through 1253). Ground
contact appears at 1252 and the state returns to 0 at 1254.

## Camera implication

The handstand does not own a separate camera latch. The derived camera record at
`0x80095358` continues to be produced by `camera_follow_update` (`0x8004DF18`).
Its target has stable mounted spans at 1054..1105 and 1166..1221; camera position
continues converging rather than freezing. The producer has no mode-14 or
action-16 special case.

## Evidence boundary

This law is supported by a control-exact retained capsule and pristine resident
ASM plus passive block flow. The legacy capsule used CachedInterpreter, so it is
not cited as an instrumented replay or every-cycle trace.

- `analysis/phase4_a10_capsule.json`
- `analysis/phase4_a10_static.json`
- `analysis/phase4_a10_bounded_exhaustion.json`
- `src_re/fixed_seed_handstand_80047284_80048138.c`
