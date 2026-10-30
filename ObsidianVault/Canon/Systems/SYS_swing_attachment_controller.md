---
kind: system
id: SYS_swing_attachment_controller
name: Swing attachment and pendulum controller
status: confirmed
updated: 2026-07-15
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-07-15_phase4_swing_attachment
  - analysis/phase4_swinging.json
---

# Swing attachment and pendulum controller

The pristine A16 controller gives the player a transient claim over one of
eight fixed scene records. The attachment selector is a 1-based player field;
shared player state 5 alone does not identify swinging.

## Original-game facts

- Player s16 `0x800A658C` (`+0x8C`) is the attachment index: 0 is detached and
  1..8 selects pool slot 0..7.
- The pool begins at `0x8009C870`, contains exactly eight records, and has
  stride `0x344` (836). Record s16 `+0x00` is its active/node count. S16
  `+0x04` is the attachment claim: 0 is available, acquisition writes 1, and
  native detach writes -30 before the pool updater recovers it toward 0.
- `0x80041AC4..0x80042427` scans all eight records. An acquisition candidate
  must be active, unclaimed, inside its horizontal camera gate, and have a
  selectable rope node whose scaled squared distance from the player is at
  most `0xFFFF`. The player index must be 0 and the player owner enters this
  path from states 1, 2, or 6.
- From `in_front_of_swing.sav`, Up plus Cross naturally selects Stage-1 slot 1
  as player index 2 and produces state/grounded/animation 5/0/4. No input,
  Cross-only, and Up-only remain detached from the same pristine anchor.
- The selected record holds relative player-to-anchor XYZ at `+0x14/+0x18/+0x1C`,
  selected node at `+0x20`, and anchor XYZ at `+0x24/+0x28/+0x2C`. The Y
  relation uses a 15000-unit bias.
- Record s16 velocity `+0x0C/+0x0E/+0x10` is sign-extended into player s32
  velocity `+0x2C/+0x30/+0x34` by exact writers `0x800423C8`, `0x800423DC`,
  and `0x800423F0`. All 13 retained pendulum samples matched this publication
  exactly while index 2 remained attached and player Y spanned 1208 units.
- The player owner supplies heading-derived drive components to the same
  function while attached. Native-update cadence must not be inferred from
  emulator frames.
- A fresh Cross calls matching-C detach `0x80041A74`: the selected claim writer
  `0x80041AB4` stores -30 and `0x80041AB8` clears the attachment index. The
  player owner selects state 1, animation 3, doubles horizontal X/Z velocity,
  and subtracts 2048 from vertical velocity. Idle remains attached.

## Consumers and lifecycle

Camera owner `0x8004DF18` reads the index at `0x8004E0AC`; clearing only that
index changes the otherwise matched 12-frame camera trajectory. Actor-skinned
owner `0x800563D4` calls `0x80042DCC` while attached. That matching-C helper
indexes the same record and returns anchor XYZ; its legacy
`get_current_actor_xyz` name is narrower than the confirmed role.

Pool reset `0x8003F5FC` clears `+0x00` in all eight records. Across the 19
strict-pristine gameplay anchors, Stage 1 has active counts `[16,12,16]`, The
Tree has `[16,22,16,22,16,16,19]`, and Bonus 2 reuses the Stage-1 layout. The
other 16 anchors have no active record. Direct one-record-available controls
selected every one of the ten records in the two distinct layouts; the fixed
capacity remains eight per scene.

Pause freezes the attached player tuple and all eight records. Native damaging
contact invokes detach before fatal flow; same-scene respawn remains detached
with health restored and lives decremented. Attachment, claims, selected node,
relative transforms, and pendulum values are transient, not saved progression.

E02 collision internals, E05 rope/model asset decoding, E12 audio, A17 manual
camera controls, and stage objectives remain separate owners. Machine contract:
`config/phase4_swinging.yaml`. Retained evidence:
`analysis/phase4_swinging.json`, SHA-256
`80aa3d28d1bd75e5cba6094870e1c7b2fdd4a09c8c707cd0db799bd20bc398fa`.
ALLMODS was not original-game authority.

See [[EXP_2026-07-15_phase4_swing_attachment]],
[[Game Solving Campaign - Swing Attachment]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
