---
kind: playbook
id: PLAYBOOK_game_solving_campaign_kick_attack
name: Game Solving Campaign - Kick Attack
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Kick Attack

## Scope and decision

This completed child campaign covers Phase-1 row A04: ordinary pristine
L2/R2+fresh-Square input, signed timer and recovery, animation phase/id, generic
resident actor-contact geometry and flag responses, pause, and respawn reset.

Enemy-family AI, authored rosters, berry immunity, death/respawn, permanence,
quotas, boss/overlay contacts, E02 geometry, and Riverbed Flight retain their own
rows. The active class matrix cannot dilute or inflate those campaigns.

## Oracle, controls, and breadth

The original oracle is the pinned from-boot LEVEL01 movie. Control and in-memory
edited branches were identical before frame 8135. Adding only L2 and a fresh
Square press produced timer -13/animation 1 instead of timer 0/animation 0 at
frame 8148.

The breadth oracle covers Training, stages 1–15, and bonuses 1–3. All 18
ordinary anchors armed -16/animation 1; Riverbed Flight retained timer 0,
grounded 0, animation 4. Native controls include both shoulders, missing and
pre-held inputs, negative-timer retry, player gate, exact 1023/1024 floor
boundary, recovery/re-entry, pause/resume, nonzero precondition, native
same-scene respawn, and fresh post-respawn kick.

The contact breadth union contains 28 distinct active `(id,flags)` classes from
those saved moments. Fresh timer-0/-16 trials at exact animation-geometry contact
centers produced 20 ordinary state-30 classes, three response-only `0x80`
classes, two separate-path `0x20` classes, and three suppressed `0x800` classes.
All 28 matched static classification.

## Frontier, state, and lifecycle

- Input owner: resident player update, ordinary arm branch
  `0x80048F40..0x80048FB7`.
- Animation owner: resident actor-skinned update paths
  `0x80056700..0x80056718` and `0x80056910..0x80056924`.
- Contact owner: resident proximity updater `0x8004ABF4..0x8004B6AB`.
- State: decoded actions `0x80082488`, previous pad `0x80082380`, player
  `+0x48` floor, `+0x5C` gate, signed `+0x7A` timer, `+0x88` animation,
  actor `+0x44` phase, `+0x5C` flags, `+0x6C` response, `+0x74` geometry.

No A04-private pool, callback, overlay state, capacity, or serialized attack
state exists. The player block and actor records are reused; the live pointer
table compacts on removal. Negative timer recovery retires the attack. Scene,
action-reset, transition, respawn, and plant/cannon writers clear the timer.
`config/phase4_kick.yaml` is the reusable typed contract.

## Bounded residuals

- D-family campaigns own authored rosters, AI, attacks, immunity, death,
  respawn, permanence, drops, and quotas. Generic A04 classifies current flags
  and geometry rather than closing those lifecycles.
- D16–D20 and F-stage campaigns own boss and overlay-special contacts under
  their actual residency.
- F14 owns Riverbed Flight motion; its retained timer-0/animation-4 result is an
  exact exceptional control.

None intersects the completed ordinary input/timer/contact law. Evidence and
failed hypotheses: [[EXP_2026-07-15_phase4_kick_attack]]. Original-game facts:
[[SYS_kick_attack]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
