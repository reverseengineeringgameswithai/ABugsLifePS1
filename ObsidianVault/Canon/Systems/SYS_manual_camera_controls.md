---
kind: system
id: SYS_manual_camera_controls
name: Manual camera controls
title: Manual camera controls
status: confirmed
updated: 2026-08-03
confidence: confirmed
source_state: original_game
functions: [camera_follow_update]
addresses: [0x8004DF18, 0x80082488, 0x80082220, 0x80095358]
evidence:
  - EXP_2026-08-03_phase4_a17_camera_controls
  - EXP_2026-07-15_phase4_manual_camera_controls
---

# Manual camera controls

## Interface

Normal gameplay manual camera control is decoded inside `camera_follow_update`
`0x8004DF18` from active-high pad word `0x80082488`:

| Input | Mask | Shoulder selector at `0x80082220` |
|---|---:|---:|
| none | - | `0` |
| L1 | `0x0400` | `2` |
| R1 | `0x0800` | `3` |

L1 has priority if both shoulders are held. This is direct branch priority, not a
combined mode.

## L1

L1 selects a close distance target of `600`, a default vertical offset of `0x3000`,
and a refreshed countdown/gate. Up changes the vertical offset to `0x8000`. Down
changes it to `0x1000` and adds look offset `0x3000`.

Camera distance at struct `0x80095358 + 0x1E` moves toward the target by 32 per 30 Hz
camera update. The 12-bit boom/look angle at `+0x18` uses shortest-arc quarter-step
smoothing.

## R1

R1 selects distance target `1400`, vertical offset `0x6000`, and supplies zero angular
step to the common `+0x20` heading writer. The follow heading therefore remains locked
for exactly the updates in which R1 is sampled.

The R1 leash compares scaled squared 3D player-camera distance against `1,960,000`,
equivalent to a radius of `44,800` world units. Releasing R1 immediately returns to
ordinary follow selection; distance and boom may continue converging through their
normal smoothing laws, but there is no separate lock latch.

## Camera control word and collision

Camera `+0x22` is not a stable mode enum. Its low byte carries the normal active/control
value (`0x01` in the confirmed gameplay fixture), while its signed high byte is a
decrementing countdown/control field refreshed by L1.

The producer first calls `camera_region_query 0x800376A0`. A later candidate solver is
admitted only inside the active leash threshold and when the countdown gate is zero;
candidate deltas of magnitude `1024` or greater restore the prior target.

## Scope

This contract covers manual controls in the normal gameplay producer. The special-view
global `0x800824DC` and telescope/cutscene/setpiece camera producers are separate from
this interface and remain documented under [[EXP_2026-08-03_phase4_e04_camera_system]].

Evidence: [[EXP_2026-08-03_phase4_a17_camera_controls]] and
`analysis/phase4_a17_camera_controls.json`.
