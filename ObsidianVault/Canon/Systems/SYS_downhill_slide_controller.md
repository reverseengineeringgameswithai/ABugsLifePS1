---
kind: system
id: SYS_downhill_slide_controller
name: Ordinary downhill abdomen-slide controller
status: confirmed
updated: 2026-07-15
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-07-15_phase4_downhill_slide
  - analysis/phase4_downhill_slide.json
---

# Ordinary downhill abdomen-slide controller

The pristine ordinary A06 controller is a resident state-4 landing initializer
followed by a context-reused timer-12 carry latch. Shared state 5 and raw
player `+0x42/+0x46` animation counters do not identify the slide.

## Original-game facts

- Decoded Cross is `0x4000` in the u16 action word `0x80082488`.
- When state 4 reaches a collision-reported ground contact, the resident slice
  `0x80048DD8..0x80048E0C` writes player s16 `+0x84=-6144`, s16
  `+0x7A=12`, state 1, and vertical velocity 0. The next grounded update with
  Cross held selects shared state 5.
- Positive `+0x7A` decrements once per resident player update. After 12 becomes
  11, `0x80048EEC..0x80048F3C` writes 12 again exactly when Cross remains held
  and either signed forward component `+0x38 >= 768` or
  `abs(lateral component +0x3C) >= 768`.
- The exact live boundary is inclusive 768: forward/lateral 767 produced timer
  11 and animation 6; forward 768, lateral 768, and lateral -768 produced timer
  12 and animation 28 from otherwise identical pre-edit state.
- Timer 12 selects a zero target component, forward decay 2, lateral decay 8,
  and animation 28 per player update. It does not add acceleration. Left/right
  steering continues to alter the 12-bit heading and redirects carried X/Z
  motion while the latch remains active.
- The latch reads Cross and the two movement components. It contains no floor,
  slope-normal, or terrain predicate. Collision-resolved terrain supplies
  position, floor Y, and carried components to later player updates; E02 owns
  the internal geometry.
- Releasing Cross on the ground selects state 0. Releasing it airborne from
  state 5 selects state 6. A threshold failure lets timer 12 fall to 11 and
  animation leave 28 even when held Cross temporarily leaves shared state 5.
- Positive timer 12 is not the negative-timer generic kick class. Across the 28
  distinct active actor id/flag classes in the retained gameplay anchors, no
  trial selected offensive target response -20 or 30. Ordinary actor-specific
  contact still damaged Flik for eight classes; 20 preserved health.

The native Training movie records state/timer/animation 1/12/28 at frame 406,
then 5/12/28 at frames 410 and 500, and state 0 after Cross release at frame
714. A timing-matched cold boot added only Cross at movie frames 8475..8481
and changed the frame-8480 outcome from 0/10/6 to 5/12/28. An ordinary held
jump landing separately reached state 5 with timer 0 and animation 5, directly
falsifying state 5 as a unique discriminator.

## Breadth, lifecycle, and boundaries

All 18 ordinary gameplay anchors reproduced state 4, the native landing
initializer, and state 5. Riverbed Flight remained state 0, animation 4, timer
0 and is owned by F14. Pause froze position, heading, components, timer, state,
grounded, aux, and animation; resume continued the controller. Native
same-scene respawn changed a marked 12/5/28 tuple to timer/state 0/0, decremented
lives, and accepted a fresh state-4 landing without reloading a state.

No A06-private allocation or serialized state exists. E02/E05, enemy-family
lifecycle, boss/overlay contacts, and Flight remain independently owned and do
not intersect this ordinary controller law. The machine contract is
`config/phase4_downhill_slide.yaml`; retained evidence is
`analysis/phase4_downhill_slide.json`, SHA-256
`a78387f11f089b49adfeff3a4e728e7f2a14163a8cded2fc507c4ccb7c4214f6`.
ALLMODS was not original-game authority.

See [[EXP_2026-07-15_phase4_downhill_slide]],
[[Game Solving Campaign - Downhill Slide]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
