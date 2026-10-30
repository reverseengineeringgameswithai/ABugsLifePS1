---
kind: system
id: SYS_directional_spin_heading
name: Directional spin heading
status: confirmed
updated: 2026-07-16
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-07-15_phase4_directional_spin_heading
  - analysis/phase4_spin_heading.json
---

# Directional spin heading

The pristine A07 behavior is a succession of ordinary direction-to-heading
updates, not a distinct action mode. Pressing Left, Up, Right, Down makes the
resident controller traverse the 12-bit heading circle in one direction;
Left, Down, Right, Up produces the opposite signed traversal.

## Original-game facts

- Decoded action is u16 `0x80082488`; its direction mask is `0x00F0` with
  Up/Right/Down/Left bits `0x10/0x20/0x40/0x80`.
- Resident helper `0x80047EBC..0x80048137` reads the current action at
  `0x80047F6C` and writes desired player heading `0x800A6528`. The live
  AnalogController path writes at `0x80048044`; `0x80048104` is the pure
  digital fallback.
- Player heading is u32 `0x800A6520`, masked to `0..4095`. Observed writers
  `0x800491A4`, `0x80049298`, and `0x800492A8` snap or converge through the
  wrap with ordinary steps bounded by 256 in the retained exact controls.
- The helper retains no direction history and owns no private spin state.
  `actor_skinned_update` is among 21 resident static readers of player heading,
  so the result flows through the existing facing/render path.

The source and reverse sequences produced opposite signed heading paths in
LEVEL01, Training entry, and Training completion while state, action timer,
and auxiliary action state remained zero. Timing-matched source and neutral
branches preserved the same state/timer/aux value sets at every one of the 19
strict-pristine gameplay anchors, while all 19 exposed different heading
trajectories. Riverbed Flight remains an F14 movement/camera context even
though this resident heading controller still responds there.

## Lifecycle

Pause owns direction input and freezes the complete player block. A separate
clean resume branch accepts the sequence again. Reload restores both heading
fields exactly. Native same-scene death/respawn decrements lives, restores
health, and permits a fresh sequence. Heading is transient resident player
state, not independently saved progression or a cheat flag.

A cold-boot movie control was byte- and cycle-identical before frame 8103.
Editing only frames 8103..8134 to the source directions made final heading and
position diverge from the unedited branch while preserving the branch's
pre-existing state/timer/aux lifecycle.

The secondary web wording supplied only an experiment lead. It is not
original-game authority. This result does not establish a spin attack, damage
response, cheat, pause exploit, cross-tick gesture recognizer, or private action
mode. Machine contract: `config/phase4_spin_heading.yaml`. Retained evidence:
`analysis/phase4_spin_heading.json`, SHA-256
`ce6a28f37ade07f8959d240bac48847b5fe7f49574bbeb63c1c8e7293a26e61a`.
ALLMODS was not used as authority.

See [[EXP_2026-07-15_phase4_directional_spin_heading]],
[[Game Solving Campaign - Directional Spin Heading]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
