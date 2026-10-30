---
kind: playbook
id: PLAYBOOK_game_solving_campaign_slow_walk_modifier
name: Game Solving Campaign - Slow Walk Modifier
status: complete
created: 2026-07-14
updated: 2026-07-14
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Slow Walk Modifier

## Scope and decision

This child campaign covers Phase-1 row A02 only: the pristine L2/R2 modifier's
decoded-input gate, movement-component boundary, locomotion-animation selection,
ordinary-stage breadth, explicit flight exception, pause, release/re-entry, and
death/respawn lifecycle. It is complete from reproduced low-level evidence.

It does not cover A01 acceleration, turning, slopes, collision, or final-speed
composition; kick's separate shoulder chord; frontend controller remapping; or a
MOD implementation. Those owners cannot be used to dilute or inflate A02.

## Pristine oracle and controls

The primary original-game oracle is the hash-pinned, from-boot LEVEL01 movie.
Control and session-local edited branches matched before frame 8103. The only
edit added R2 to an existing Up-only window through frame 8162; after the window
animation changed from 0 to 29.

The breadth oracle uses 19 centrally declared strict-pristine anchors: Training,
stages 1–15, and bonuses 1–3. R2+Up selected 29 in all 18 ordinary contexts;
Up alone never selected 29. Riverbed Flight was the native negative: both inputs
kept animation 4 and identical compared outcomes. L2 matched R2, shoulder-only
R2 caused no displacement and no animation 29, and release/re-entry produced
29/0/29.

## Semantic frontier and typed state

- Input owner: resident decoded action `u16` at `0x80082488`; A02 mask `0x0300`.
- Movement owner: player update `0x80048138..0x800498AB`; decisive read
  `0x8004848C`; default/slow intermediate component bounds 1792/768; clamp
  `0x800493C0..0x80049443`; forward-component writer `0x800494AC`.
- Animation owner: actor-skinned update `0x800563D4..0x800570F7`; decisive read
  `0x800566D0`; animation-29 writer `0x800566E8`.
- Both owners and state are resident. No callback, overlay-owned field, dynamic
  allocation, pool capacity, or A02-private serialized state participates.

`asm/hand_written/80048138_player_vertical_update.s` is the byte-matched build
unit for the player owner. `src_re/player_update_80048138.c` is semantic,
documentation-grade C, not a build input. The animation owner remains byte-exact
recovered assembly. `config/phase4_slow_walk.yaml` is the reusable typed contract.

## Lifecycle and dependencies

The resident consumers re-read input; release retires the modifier without a
private reset record. Pause freezes position, speed, and animation. Resume
re-enters animation 29. Native death/respawn decrements lives, restores health,
and re-reads held R2+Up. Resident ownership persists across scene unload/load,
while normal stage state is replaced.

Movement feeds collision and rendering, while the animation selection feeds the
actor/render path. Audio and camera may consume resulting ordinary locomotion
state, but the complete static frontier found no additional A02 owner. A01 and
frontend remapping are explicit non-scope dependencies.

## Bounded residuals

- A01 base run motion is now separately completed by
  [[Game Solving Campaign - Run Locomotion]]. Its guard composes with A02 without
  changing A02's mask, component-bound delta, animation selection, or flight exception.
- Frontend remap persistence still needs a HUD/frontend lifecycle campaign. It
  owns selector configuration before decoding, not the A02 low-bit modifier.

Neither residual intersects the behavior claimed complete here. Evidence and
failed hypotheses are in [[EXP_2026-07-14_phase4_slow_walk]]; original-game facts
are in [[SYS_slow_walk_modifier]]. Parent: [[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
