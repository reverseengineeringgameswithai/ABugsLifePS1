---
kind: system
id: SYS_run_locomotion_controller
name: Run locomotion controller
status: confirmed
updated: 2026-07-14
confidence: confirmed
evidence:
  - EXP_2026-07-14_phase4_run_locomotion
---

# Run locomotion controller

The pristine ordinary horizontal controller converts decoded D-pad/analog input
into a desired 12-bit heading, converges the player heading, updates signed local
forward/lateral components, rotates them into world X/Z velocity, and submits
that velocity to collision resolution.

## Original-game facts

- The resident helper `0x80047EBC..0x80048137` reads the decoded direction mask
  `0x00F0`. Analog axes use an internal deadzone of 6144 and magnitude cap of
  16384; the controller scales magnitude by `>>14`.
- Player `+0x20` (`0x800A6520`) is heading and `+0x28` is desired/input heading.
  Both are `u32` values masked into `0..4095`. The ordinary default turn step is
  bounded at 256 and shrinks as the remaining angular difference closes.
- Player `+0x38` is a signed local **forward component**, written at
  `0x800494AC`; `+0x3C` is its signed lateral companion, written at
  `0x800494B0`. The old universal `hypot(vx,vz)` label is superseded: it happens
  to approximate magnitude during aligned forward travel but becomes negative
  during some turns.
- Ordinary full input targets component 1792 inside a ±2048 bound. Forward
  friction is 64, lateral friction is 256, and active input adds 144, yielding
  a straight-input increment of 80 after forward friction once the path is
  active. These are component laws, not universal final displacement laws.
- Heading rotates the local pair into world velocity X/Z at player `+0x2C` and
  `+0x34`, written at `0x80049524/0x80049540`.
- Velocity is a proposal to the `0x8003633C` movement/collision integrator.
  Resolved position writers `0x80036CE8/0x80036CF0` often equal the proposal in
  open space but differ on retained slope/floor/wall-contact ticks.
- Ordinary movement selected animation 0 in all 18 applicable gameplay
  anchors. Riverbed Flight remained animation 4 and produced no Up-vs-neutral
  outcome delta; it is a separate special controller, not an A01 variant.

All instruction words and regions were re-read from hash-pinned pristine
`SCUS_942.88`. ALLMODS was not used as original-game authority. The machine
contract is `config/phase4_run_locomotion.yaml`; retained evidence is
`analysis/phase4_run_locomotion.json`.

## Controls and lifecycle

Four D-pad directions and full analog Up moved the player. Half analog produced
forward component 909 versus 1804 at full input, while an inside-deadzone input
remained decoded zero with no displacement. A straight hold accelerated from
zero past 1700, release decayed to zero, and re-entry restored motion. Turning
from Up to Right used nonzero steps no larger than 256.

The game updates player logic on alternating 60 Hz emulator frames. Fresh
controller input therefore appeared on sample 1–3 depending on anchor phase and
then stayed continuously asserted. Pause froze X/Y/Z, forward component, and
animation. Resume restored movement. Native death/respawn decremented lives,
restored health to 4, and re-read held Up in the same scene.

## Reuse boundary

A MOD must preserve the input → heading/components → world velocity → collision
owner order. It cannot treat `+0x38` as unsigned speed or a velocity write as a
guaranteed move. Initialization, release/reset, death/reload, transition,
residency, capacity, and downstream animation/render/audio/camera consumers must
be named. Jump, slide, bounce, swing, flight, and E02 collision internals remain
separately owned.

See [[EXP_2026-07-14_phase4_run_locomotion]],
[[Game Solving Campaign - Run Locomotion]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
