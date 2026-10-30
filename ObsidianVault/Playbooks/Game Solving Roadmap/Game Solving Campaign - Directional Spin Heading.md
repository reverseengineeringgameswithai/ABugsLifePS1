---
kind: playbook
id: PLAYBOOK_game_solving_campaign_directional_spin_heading
name: Game Solving Campaign - Directional Spin Heading
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Directional Spin Heading

## Scope and decision

This completed child campaign covers Phase-1 row A07: the left-start source
sequence, reverse and neutral controls, typed current-direction/heading state,
owner and consumer attribution, all gameplay contexts, pause/reload/respawn
lifecycle, and a from-boot causal edit.

The positive pristine behavior is successive ordinary heading updates. This
campaign does not promote the secondary source's attack, damage, cheat, or
pause-effect language into original-game fact.

## Oracle, controls, and breadth

Left/Up/Right/Down and Left/Down/Right/Up produce opposite signed heading
traversals at LEVEL01, Training entry, and Training completion while action
state/timer/aux stay zero. Timing-matched neutral proves a different heading
trajectory at all 19 strict-pristine gameplay anchors without adding a new
state, timer, or auxiliary action value.

The cold-boot source and neutral branches are byte/cycle equal immediately
before frame 8103. Editing only frames 8103..8134 changes final heading and
position. The branch's pre-existing action state/timer/aux values remain
equal, bounding the causal claim to the current-direction/heading path.

## Frontier, state, and lifecycle

- Owner: resident current-direction helper `0x80047EBC..0x80048137` and the
  ordinary player heading controller.
- Inputs: u16 action `0x80082488`, mask `0x00F0`.
- State: u32 desired heading `0x800A6528` and player heading `0x800A6520`,
  each in `0..4095`; no private mode or history allocation.
- Consumers: movement/collision/camera plus the existing actor/render heading
  readers; F14 remains owner of Riverbed Flight movement/camera behavior.

Pause freezes the player block, clean resume re-enters, reload restores both
heading fields, and native respawn accepts a fresh sequence. All state is
transient resident player state.

## Bounded residuals

The source-reported spin attack, damage effect, cheat, and pause exploit are
not A07 claims without separate pristine reproduction. The Phase-3 bounded
negative remains historical evidence against an observed private mode or
unknown writer, not against the heading behavior confirmed here.

Machine contract: `config/phase4_spin_heading.yaml`. Retained evidence:
`analysis/phase4_spin_heading.json`. Original-game facts:
[[SYS_directional_spin_heading]]. Procedure and rejected hypotheses:
[[EXP_2026-07-15_phase4_directional_spin_heading]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
