---
kind: playbook
id: PLAYBOOK_game_solving_campaign_jump_controller
name: Game Solving Campaign - Jump Controller
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Jump Controller

## Scope and decision

This completed child campaign covers Phase-1 row A03: ordinary pristine Cross
takeoff, hold/release height, coyote eligibility, native super-jump modifier,
gravity/terminal velocity, state/grounded/animation publication, collision
handoff, and lifecycle behavior.

E02 collision geometry, A05 butt-slam, seed/plant activation, swing state reuse,
and Riverbed Flight retain their own rows. They cannot dilute or inflate A03.

## Oracle, controls, and breadth

The original oracle is the pinned from-boot LEVEL01 movie. Control and in-memory
edited branches were identical before frame 8011. Removing only Cross through
frame 8038 left the player grounded/state 0 instead of airborne/state 1 at
frame 8025.

The breadth oracle covers Training, stages 1–15, and bonuses 1–3. All 18
ordinary anchors entered airborne state, selected animation 3, and returned
grounded. Riverbed Flight consumed Cross through separate movement while
remaining state 0/animation 4. Controls cover hold/release heights, normal and
native super-jump, coyote positive/boundary/guard cases, pause/Resume, and native
same-scene death/respawn.

## Frontier, state, and lifecycle

- Owner: resident player function `0x80048138..0x800498AB`; ordinary branch
  `0x80048B2C..0x80048D93`.
- Input: decoded Cross `0x4000` at `0x80082488`, read `0x80048B60`.
- State: player `+0x30` signed vertical velocity, `+0x48` floor Y, `+0x80`
  shared action state, `+0x82` grounded, `+0x88` animation, low flag `0x0020`
  at `+0x90`.
- Collision interface: call `0x800495C8` to `0x8003633C`; resolved Y writer
  `0x80036CEC` and collision-owned landing/grounded publication.

No private pool, callback, overlay state, capacity, or serialized jump state
exists. The resident player block is reused; release and landing retire the
transient state; scene load and native respawn reinitialize it.
`config/phase4_jump.yaml` is the reusable typed contract.

## Bounded residuals

- E02 owns ceiling/floor/ledge geometry and internal collision response. A03
  proves the velocity/grounded interface and ordinary completed arcs.
- A05, plant actions, swing, and F14 own their separate Cross/state consumers.
  The ordinary branch is guarded from these paths and does not claim their law.

Neither boundary intersects the completed ordinary jump controller. Evidence
and failed hypotheses: [[EXP_2026-07-15_phase4_jump_controller]]. Original-game
facts: [[SYS_jump_controller]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
