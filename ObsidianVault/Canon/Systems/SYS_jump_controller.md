---
kind: system
id: SYS_jump_controller
name: Ordinary jump controller
status: confirmed
updated: 2026-07-15
confidence: confirmed
evidence:
  - EXP_2026-07-15_phase4_jump_controller
---

# Ordinary jump controller

The pristine ordinary jump controller is resident inside
`FUNC_80048138`. It converts decoded Cross into a signed vertical-velocity
proposal, shared player action state, grounded publication, and animation, then
hands motion to the resident collision integrator.

## Original-game facts

- `0x80048B60` reads decoded action word `0x80082488`; Cross is `0x4000`.
- Grounded takeoff and eligible coyote takeoff converge at `0x80048BD8`.
  Writers `0x80048BDC`, `0x80048BE8`, and `0x80048BF4` publish state 1,
  grounded 0, and rise animation 3.
- Normal takeoff selects `-3072`. Native player flag `0x0020` at `+0x90`
  selects the stronger `-3776` super-jump impulse.
- While Cross remains held, state stays 1 and gravity adds 256 per native
  player update. This constant is not an emulator-frame law. Downward velocity
  is capped at `+4096`.
- Releasing Cross while state is 1 runs `0x80048D14..0x80048D50`. For a
  velocity below `-800`, it first adds 384, then computes a signed half and
  subtracts 256 before publishing state 2. This jump cut is why longer holds
  reach higher apices.
- Airborne coyote takeoff requires signed `(floor_y - y) < 1024` and global
  guard `0x80082434 == 0`. The exact boundary 1024 and a set guard both reject
  takeoff on their first native update. Level load clears this Boolean at
  `0x80046C84`; after collision, `0x800495E4` publishes the result of
  `FUNC_80038F20`'s signed-global threshold test.
- `0x80048D8C` commits signed vertical velocity at player `+0x30`.
  `0x800495C8` calls movement/collision integrator `0x8003633C`; resolved Y is
  written through `0x80036CEC` and collision owns grounded publication on
  landing. A later released grounded update resets shared action state to 0.
- State 2 is not globally “swing-release”: it is the ordinary released/falling
  jump state here and is also reused by separate action paths.

The retained hold curve for 1, 2, 4, 8, 12, and 20 emulator-frame holds was
`6336, 6336, 8256, 11520, 14016, 16896` world units. At a matched two-frame
hold, native flag `0x0020` increased height from 6336 to 9120.

All 18 ordinary gameplay anchors entered airborne state, selected animation 3,
and returned grounded. Riverbed Flight is an explicit exception: Cross changes
flight-specific X/Y/Z/vertical velocity while state remains 0 and animation 4.
It is an F14 motion law, not ordinary A03 jumping.

All instruction words and region hashes were re-read from hash-pinned pristine
`SCUS_942.88`. ALLMODS was not used as original-game authority. The machine
contract is `config/phase4_jump.yaml`; retained evidence is
`analysis/phase4_jump.json`.

## Lifecycle and boundaries

Neutral pause freezes X/Y/Z, velocity, state, grounded, and animation. Cross is
also the pause-menu confirm: from the retained default selection it resumes and
the held edge immediately enters state 1/animation 3. Native same-scene death
and respawn restore health 4, decrement lives, reinitialize grounded state, and
accept a fresh Cross jump.

A03 owns ordinary input-to-vertical-controller behavior and the collision
interface, not E02 ceiling/floor/ledge geometry, A05 butt-slam, plant/seed
activation, swing state reuse, or F14 flight motion. No A03-private allocation,
overlay field, or serialized progression exists.

See [[EXP_2026-07-15_phase4_jump_controller]],
[[Game Solving Campaign - Jump Controller]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]].
