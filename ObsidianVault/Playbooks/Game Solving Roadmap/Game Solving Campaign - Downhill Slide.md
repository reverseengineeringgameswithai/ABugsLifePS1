---
kind: playbook
id: PLAYBOOK_game_solving_campaign_downhill_slide
name: Game Solving Campaign - Downhill Slide
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Downhill Slide

## Scope and decision

This completed child campaign covers Phase-1 row A06: the pristine ordinary
state-4 landing initializer, timer-12 carry latch, exact component boundary,
component decay, steering, terrain interface, animation, generic actor-contact
class, termination, ordinary gameplay breadth, and lifecycle.

E02 collision geometry, E05 animation asset decoding, enemy-family lifecycle,
boss/overlay-special contacts, and Riverbed Flight motion retain separate rows.
They cannot dilute or inflate A06.

## Oracle, controls, and breadth

The pinned native Training movie records state/timer/animation 1/12/28 at frame
406 after state-4 ground contact, 5/12/28 at 410 and 500, and state 0 after
Cross release at 714. Exact single-field controls establish the inclusive
component latch: forward/lateral 767 decays timer to 11 and selects animation
6, while forward 768, lateral 768, and lateral -768 re-arm timer 12 and select
animation 28.

Removing only Left from native movie frames 451..491 keeps state 5/timer 12 but
changes heading and X/Z path. Adding only Cross at cold-boot movie frames
8475..8481 preserves equal player fields, whole-block hash, cycle, and frame
before the edit, then changes the frame-8480 outcome from 0/10/6 to 5/12/28.
An ordinary held-jump landing reaches state 5/timer 0/animation 5 and is the
explicit shared-state negative.

All 18 ordinary gameplay anchors reproduce state 4, the landing initializer,
and state 5. Riverbed Flight stays state 0/animation 4/timer 0.

## Frontier, state, and lifecycle

- Player owner: resident `0x80048138..0x800498AB`; decisive setup
  `0x800484A4..0x800484C0`, state/landing `0x80048CD8..0x80048E0C`, and latch
  `0x80048ED4..0x80048F3C`.
- Animation owner: resident `0x800563D4..0x80056863`; timer-12 animation-28
  selection `0x8005684C..0x80056860`.
- Contact owner: resident `0x8004ABF4..0x8004B6AB`; positive timer 12 is
  separate from the generic negative-timer kick branch.
- State: decoded Cross; s16 timer/state/grounded/aux/animation; u32 12-bit
  heading; s32 forward/lateral components, velocity, position, and floor Y.

Ground contact writes aux -6144, timer 12, state 1, and vertical velocity 0.
Positive timer decrements per player update and re-arms from 11 to 12 when
Cross is held and signed forward is at least 768 or absolute lateral magnitude
is at least 768. Timer 12 targets component 0 with forward/lateral decay 2/8
and selects animation 28. No explicit slope predicate occurs in that latch;
E02 supplies collision-integrated terrain state.

Across 28 distinct active actor id/flag classes, timer 12 selected no offensive
target response -20/30. Pause freezes the full controller tuple. Native
same-scene respawn clears a marked timer/state/animation 12/5/28 tuple and
accepts a fresh slide entry without state reload. No A06-private allocation or
serialized state exists.

## Bounded residuals

- E02/E05 own collision geometry and animation asset decoding. A06 binds the
  values crossing those interfaces but does not infer their internal layouts.
- Enemy-family and boss owners determine HP, death, respawn, permanence,
  quotas, and special contacts. A06 proves only its generic non-offensive class.
- F14 owns Flight motion despite consuming the same physical Cross button.

None intersects the completed ordinary A06 law. Machine contract:
`config/phase4_downhill_slide.yaml`. Retained evidence:
`analysis/phase4_downhill_slide.json`. Original facts:
[[SYS_downhill_slide_controller]]. Procedure and failed hypotheses:
[[EXP_2026-07-15_phase4_downhill_slide]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
