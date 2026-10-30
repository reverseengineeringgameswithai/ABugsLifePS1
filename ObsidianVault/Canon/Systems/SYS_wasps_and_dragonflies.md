---
kind: system
id: SYS_wasps_and_dragonflies
status: confirmed
confidence: high
source_state: original_game
related: [SYS_enemy_ai]
evidence: [EXP_2026-08-03_phase4_d14_wasps_dragonflies]
---

# Wasps and dragonflies

## Family identities

| Visible/campaign family | Internal runtime family | Actor ID | Species callback | Mover program |
|---|---|---:|---|---|
| Dragonfly | dragonfly | 34 | `0x8004A20C` | `0x8007755C..0x80077578` |
| Wasp | bee | 13 | `0x8004A144` | `0x80077578..0x800775C8` |

“Wasp” is the asset/campaign name (`WASP.ALL`); the resident VM and fixtures call the same family bee.

## Dragonfly behavior

The dragonfly program loads animation `(1,2)`, waits for a random duration, chooses a random direction, parks in seek movement at `0x80077570`, and loops to `0x80077568`.

A live active ID-34 instance moved `(+4704, 0, -9842)` over 120 frames while its VM remained at `0x80077570`. Dormant same-family instances remained at their program entry.

The dragonfly program contains no species strike section. Callback `0x8004A20C` only calls `0x8005044C` with id 42 and the actor X coordinate plus 4. Therefore a dragonfly-specific sting state does not exist in this family program/callback; generic enemy-contact reactions remain shared-system behavior.

## Wasp/internal bee behavior

The bee program installs state bits `0x6`, performs random flight, and parks on opcode 18 at `0x80077592`. The shared contact gate compares its squared distance against `0x9C3F`. On success, `0x8004CA18` advances the actor VM by six bytes into `0x80077598`.

The strike sequence clears chase bit `0x2`, changes animation, waits 5, parks at arrival, calls native subroutine 2 at `0x80057920`, changes animation again, waits 15, and loops.

Live confirmation from `bee.sav`:

- no-input 600-frame control: no strike, no health loss;
- controlled approach: contact transition at frame 25958;
- native `0x80057920` at frame 25994 with ID-13 actor pointer `0x800A0098`;
- Flik health `4 -> 3`.

## Homing targetability

Homing acquisition at `0x8005743C` scans the damageable actor pointer table beginning `0x80090748` and filters each candidate:

- actor `+0x5C & 0x1` must be set;
- actor `+0x5C & 0xA0` must be clear;
- nearest valid candidate is chosen by X/Z squared distance; Y is ignored.

Both families can appear as valid targets:

- active dragonfly ID 34 at `0x800A0098`, flags `0x4005`;
- bee ID 13 at `0x800A0098`, flags `0x4007`.

The bee negative control changes the same slot to `0x1006`; it disappears from the table, which instead points to a different ID-13 instance whose flags are `0x4007`.

## Boundaries

This note confirms original-game family programs, targetability, and the wasp/bee strike. It does not claim that every visual animation variant or every shared generic collision response was replayed. Those are presentation/shared-system domains rather than an unresolved D14 species mechanic.
