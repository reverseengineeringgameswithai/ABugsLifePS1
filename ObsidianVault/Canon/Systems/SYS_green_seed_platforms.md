# Green seed platforms

## Scope

Phase 4 row B05 covers the green seed outputs used as climbable leaf platforms. The green counter selects four plant types:

| Green count | Plant type | Runtime role seen in the retained fixture |
|---:|---:|---|
| 1 | 4 | Low platform |
| 2 | 10 | Tall leaf with an upper support surface |
| 3 | 9 | Multi-level leaf platform |
| 4 | 1 | Tallest multi-level leaf platform |

The selector is read by the spawner at `0x8005BDBC`; live slots occupy the 20-entry pool at `0x80090BF0` with stride `0x30`.

## Dispatch and common behavior

The plant walker at `0x8005BFBC` calls `player_sector_lookup` (`0x80038E48`), checks plant `extra_state & 0x04`, and dispatches by type through the table at `0x8001B848`. Types 1, 4, 9, and 10 reach `0x8005CCE8`, but that address is only the walker continuation. The common animation, contact-reaction, lifecycle, and render loop continues at `0x8005CD2C`.

This corrects the older shorthand that green plants are wholly passive and have no vertical-velocity writer. Mature leaves support Flik through ordinary model collision, but the common growth reaction is active:

- The gate requires slot state 0, animation accumulator `0x00030000`, `extra_state` bit `0x04`, and quantized squared 3D distance below 900.
- Type 4 writes Flik `VY=-3584` at `0x8005D01C`.
- Green types 1, 9, and 10 take the generic radial branch, which writes `VY=-2048`, applies horizontal push, and sets player flag bit 2.
- The `VY=-3328` type 3/5 branch is not a green-tier rule.

After growth, the visible leaf surfaces are collision geometry from the selected plant model. They feed the ordinary sector/collision resolver and player Y-commit path; the resident executable does not contain a second green-only platform controller with hard-coded tier heights.

## Retained-capsule behavior

The verified `A13__green_seed_levels` capsule reconstructs 2,714 frame boundaries with all 8,142 embedded RAM/VRAM/SPU-RAM hashes valid and an exact independent control. It observes all four green types and the shared timing law:

- `extra_state` bit `0x04` becomes set 28 movie frames after spawn.
- Mature state 1 begins 66 movie frames after spawn for every tier.
- Type 4 holds Flik about 11,111 to 11,191 world units above its base.
- Type 9 exposes observed holds about 5,572, 13,821, and 25,143 units above base.
- Type 1 exposes observed holds about 8,684, 17,963, 27,159, and 36,501 units above base.

The capsule did not place Flik on type 10's upper leaf, so it could not close that asset-defined surface by itself.

## Type-10 upper leaf

`B05_tall_leaf_boost.movie.json` closes the named gap under pure Interpreter playback. Type 10 remains in slot 3, mature state 1, `extra_state=0x0007`, with base `(-67461,-93178,-319006)`.

Flik reaches an apex 28,105 units above the base and settles at `Y=-115765`, with collision floor `Y=-115634`. This is a stable upper surface 22,587 units above the plant base. The hold persists from movie boundaries 192 through 437 (246 sampled boundaries). Flik then leaves the leaf, loses the upper floor by boundary 450, falls, and settles on the lower floor at `Y=-94888` by boundary 492.

The movie uses an external boost while a type-5 slot is also active. It proves type-10 upper-leaf reachability and support; it must not be cited as proof that mature type 10 itself creates that boost.

## Phase 4 disposition

B05 is a substantiated Partial and is bounded-exhausted for Phase 4. Selection, lifecycle, growth reaction, mature collision ownership, all four output tiers, and the previously missing type-10 upper surface are covered. Exhaustively decoding every triangle in every plant asset would add model-specific detail with minimal behavioral return and is not a blocker to moving on.

See [[EXP_2026-08-03_phase4_b05_green_leaf_platforms]].
