---
kind: system
id: SYS_abdomen_bounce
name: Abdomen bounce and spider-stomp qualification
status: confirmed_bounded
updated: 2026-08-03
confidence: confirmed
systems:
  - player_actions
  - movement_physics
  - actor_contact
  - bonus_unlocks
---

# Abdomen bounce and spider-stomp qualification

## Confirmed retail behavior

The abdomen action is owned by the resident player controller
`FUNC_80048138` and the shared actor-contact resolver `FUNC_8004ABF4`.
The Phase-2 `<=20` movie-frame double-tap window is an offline fixture
recognizer. The retail controller does not store or compare that window.

From airborne state 2, an active Cross action takes one of two paths:

- `floorY - Y < 8193`: state 3, the low slam path.
- `floorY - Y >= 8193`: event 27, phase `player+0x84=10`, state 4, and
  animation selector 2 or 7 depending on whether `vy <257`.

For the high path, phase values above 1 decrement by one and force `vy=0`.
At phase 1 the controller writes `vy=+4096` and leaves phase latched at 1.
The retained Training movie reaches every accepted spider contact in exactly
that state: state 4, phase 1, `vy=+4096`.

After a state-4 grounded contact, the player controller writes phase `-6144`,
action timer 12, `vy=0`, and state 1, then emits the radial impact effects,
contact object 91, and sound 16. Negative phase recovers toward zero in steps
of `+512` per gameplay update. The timer-12 presentation path selects animation
28 at `0x80056848..0x80056860`.

## Actor contact and the two phase outcomes

The shared resolver first checks an outer sphere. Its center is the actor
position plus actor `+0x64/+0x66/+0x68`; the player comparison uses `Y-7360`;
the radius is actor `+0x6A+250`. It then evaluates the actor's model-space
ellipsoid. Actor flags `0x20`, `0x40`, `0x80`, and `0x800` route away from this
abdomen-contact slice.

The decisive `0x8004B2AC` load is unsigned `player+0x84`, accessed as
`+0x0A(s6)` because `s6=player+0x7A`. It is not a separate interaction record.
Only phase 0 or 1 reaches the reaction:

- Both phases emit event `-4`, write actor `+0x6C=-20`, write actor
  `+0x54/+0x58=4096`, and call the `0x80057F44` entry to the eight-object
  drop-burst routine.
- Phase 0 writes player `vy=-1536`, state 5, grounded 0, and animation selector
  3. It does not increment the Bonus-1 streak.
- Phase 1 does not write an upward rebound velocity in this resolver. It reaches
  the Bonus-1 streak branch, then the player controller performs the ordinary
  state-4 impact recovery.

This is a reaction/drop path, not an HP-damage path. There is no store to actor
HP `+0x6E` in the qualifying slice. Across the natural capsule contacts, the
struck spider retains its immediate HP value while reaction `+0x6C` advances
from `-20` to `-19` to `-18`.

## Bonus-1 streak

The natural Training sequence increments `0x8008223C` at movie frames 128,
352, 590, 742, and 1072. Each accepted event has state 4, phase 1, and
`vy=+4096` at the retained frame boundary.

The counter has no target-uniqueness list and no miss reset. A direct writer
census found only the fifth-contact success clear and shared transition/reset
clears. The fifth event publishes progress command 118, sets low bonus flag
`0x02`, writes transition latch 6 and fade 30, then clears the streak.

## Evidence boundary

This confirms the resident trigger, low/high branches, phase law, actor contact,
phase-0 rebound, phase-1 challenge qualification, target reaction, HP
non-damage, miss behavior, and fifth-contact transition. It does not claim an
alias-complete repository proof, execution across every actor and terrain
variant, or pause/save/death interruption breadth.

See [[EXP_2026-08-03_phase4_a05_abdomen_bounce]],
[[EXP_2026-08-02_phase4_d10_spider_chain]],
`analysis/phase4_a05_abdomen_bounce.json`, and
`src_re/abdomen_bounce_80048138_8004abf4.c`.
