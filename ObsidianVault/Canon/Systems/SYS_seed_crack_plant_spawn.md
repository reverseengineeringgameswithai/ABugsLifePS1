---
kind: system
id: SYS_seed_crack_plant_spawn
name: Seed crack and plant spawn lifecycle
title: Seed crack and plant spawn lifecycle
tags: [canon, seeds, plants, player-actions]
status: confirmed
confidence: confirmed
source_state: original_game
evidence:
  - EXP_2026-08-03_phase4_a14_plant_crack
  - EXP_2026-07-19_phase4_offline_seed_lifecycle_batch
---

# Seed crack and plant spawn lifecycle

## Confirmed retail law

- Cross starts the jump; it does not directly grow the plant.
- A qualifying player/seed contact arms `seed+0x6C` to `10` at
  `0x8004AEE4` during the Cross-held jump phase or at `0x8004AF7C` through
  the normal descending contact gates.
- The normal contact also bounces Flik with vertical velocity `-0x600`, sets
  air state `3`, action `5`, and dispatches event `-15`.
- `0x8004D488..0x8004D498` decrements the timer and raises seed Y by `0x800`
  per gameplay update. Ten updates lift it by `0x5000` (`20480`).
- When the decrement reaches zero, `0x8004D4E0` calls
  `plant_spawn` at `0x8005BDBC`.
- The spawner resolves the selected color/output, fills one `0x30`-byte slot
  in the 20-entry array at `0x80090BF0`, stores the same seed actor at
  `slot+0x20`, and advances cursor `0x800822B8`.
- Plant creation does not allocate or destroy a type-11 seed actor.
- Common initial growth publishes `slot+0x2E: 0x0005 -> 0x0007` after 28
  video frames and animation gate `slot+2: 0 -> 1` after 66 in the retained
  brown-seed fixture. Later animation is plant-type-specific.

## Admission gates

The seed must be inside the contact envelope, have actor flag `0x20`, lack
actor flag `0x40`, have `+0x5E != 0`, and have no active crack timer. The normal
arm additionally requires Flik above the seed, `player+0x9F == 0`, nonnegative
vertical velocity, nonzero action, and air state other than `17`.

## Selection and bounds

Normal type index is `4 * color + selected_output - 1`. A nonzero source
override uses `4 * low_nibble + high_nibble`. Neither path bounds-checks the
result before reading type table `0x8007A448`.

The cursor wraps at 20 and skips occupied slots. This depends on the retail
invariant that a free slot exists; an externally forced all-occupied pool has
no graceful failure exit. Scene `0x11` also suppresses ordinary allocation for
seed actor `0x8009FE04`.

## Provenance

Four pristine retained cycles create brown output types `5, 3, 8, 2`; the
normal arm, ten-step countdown, spawn call, and spawner execute exactly four
times while seed population stays constant. Nine other Cross edges are natural
negative controls. Static analysis independently extracted the hash-identical
retail executable directly from the pristine BIN.

Full hashes, commands, failure bounds, and closure reasoning are in
[[EXP_2026-08-03_phase4_a14_plant_crack]].
