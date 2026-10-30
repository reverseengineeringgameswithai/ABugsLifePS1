---
kind: playbook
id: PLAYBOOK_game_solving_campaign_swing_attachment
name: Game Solving Campaign - Swing Attachment
status: complete
created: 2026-07-15
updated: 2026-07-15
confidence: confirmed
parent: PLAYBOOK_game_solving_phase_4
---

# Game Solving Campaign - Swing Attachment

## Scope and decision

This completed child campaign covers Phase-1 row A16: pristine natural
acquisition, fixed record ownership and capacity, pendulum velocity publication,
steering/release boundary, camera and actor dependencies, applicability, pause,
damage/respawn, reset, and cold-boot initialization.

E02 collision internals, E05 rope/model asset decoding, E12 sound internals,
A17 manual camera controls, and stage objectives retain separate rows. They do
not dilute or inflate A16.

## Oracle, controls, and breadth

The pinned from-boot movie exposes the Stage-1 pool `[16,12,16]` at frame 8000
with attachment index 0. From the same strict-pristine approach anchor,
no input, Cross-only, and Up-only remain detached; Up+Cross selects record 1 as
1-based player index 2 and state/grounded/animation 5/0/4.

The 19-anchor census found records only in Stage 1, The Tree, and Bonus 2.
Bonus 2 reuses Stage 1. One-record-available controls exercised all ten records
across the distinct three- and seven-record layouts; every trial selected the
target slot+1 index within the fixed per-scene capacity of eight.

## Frontier, state, and lifecycle

- Pool: eight records at `0x8009C870`, stride `0x344`; active/node count
  `+0x00`, attachment claim `+0x04`, dynamic velocity `+0x0C/+0x0E/+0x10`,
  relative transform `+0x14..+0x1C`, node `+0x20`, anchor `+0x24..+0x2C`.
- Player: s16 index `0x800A658C`; 0 detached, 1..8 selects slot 0..7.
- Owners: reset `0x8003F5FC`, detach `0x80041A74`, acquisition/pendulum
  `0x80041AC4`, pool update `0x80042428`, anchor helper `0x80042DCC`, player
  `0x80048138`, camera `0x8004DF18`, actor-skinned `0x800563D4`.

All 13 pendulum samples matched record s16 velocity to player s32 velocity.
Fresh Cross wrote claim -30, cleared the index, and selected state/animation
1/3; idle remained attached. Pause froze player and pool. Clearing only the
index changed camera trajectory. Native damaging contact detached before fatal
flow, and same-scene respawn remained detached. Scene reset clears all eight
active counts; transient attachment state is not saved progression.

## Bounded residuals

- E02/E05 own collision internals and rope/model asset decoding.
- E12 and A17 own audio internals and manual camera input/modes.
- Stage objectives own any progression that happens to require traversal.

None intersects the completed A16 attachment law. Machine contract:
`config/phase4_swinging.yaml`. Retained evidence:
`analysis/phase4_swinging.json`. Original-game facts:
[[SYS_swing_attachment_controller]]. Procedure and failed hypotheses:
[[EXP_2026-07-15_phase4_swing_attachment]]. Parent:
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
