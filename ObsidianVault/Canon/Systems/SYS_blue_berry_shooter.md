---
kind: system
id: SYS_blue_berry_shooter
name: Blue Berry Shooter
status: confirmed_original_behavior
confidence: high
row: B11_blue_berry_shooter
evidence:
  - EXP_2026_08_03_phase4_b11_blue_berry_shooter
  - analysis/phase4_b11_blue_berry_shooter.json
---

# Blue berry shooter

## Canonical binding

Yellow seed tier 1 selects plant type 14. The plant handler table is indexed by `type - 2`, so type 14 resolves through entry `0x8001B878` to handler `0x8005CA7C`.

## Targeting and firing

The mature shooter fires deterministic three-shot volleys from three authored muzzles. Shots are eight video frames apart; volley starts are 96 video frames apart. The first shot in the retained growth control occurs 190 frames after the plant slot is allocated.

Each muzzle calls ballistic target helper `0x80046D24`. It selects the nearest eligible enemy in that muzzle's heading cone, rejects inactive/already-hit targets, and computes bounded lead. With no target, the authored heading and `-2048` vertical launch survive. Shots are ballistic with gravity 128 and do not home after launch.

| Plant phase | Relative muzzle | Authored heading |
|---:|---|---:|
| `0x00010000` | `X-0x22A4, Y-0x5400, Z-0x1400` | `0x0AAA` |
| `0x00030000` | `X+0x22A4, Y-0x5400, Z-0x1400` | `0x0555` |
| `0x00050000` | `X, Y-0x5400, Z+0x2800` | `0x0000` |

## Projectile law

The handler passes spawner type 66 to `0x8005A0E0`. Metadata row 66 materializes:

- Collision/damage class 2.
- Timer 100 logic ticks.
- Model 110.
- Subtype 13.
- Flags `0xE5`, with no homing bit.
- Permanence byte `+0x27 = 0`.

This distinction is important: the shooter uses visual model 110 but **weak/red-equivalent class 2**, not blue/super class 5. A natural hit applies the generic `-2` side-HP-table delta and an ordinary non-permanent death transition. It does not decrement the permanent-enemy quota.

Shooter projectiles use the shared contact pool but do not increment Flik's owned-projectile byte `0x800A6596`. They do not consume his four-projectile allowance.

## Retirement and plant lifetime

Natural controls confirm immediate projectile retirement on enemy impact and timer-forced retirement on floor intersection. Generic timer, distance, and required-flag cleanup remain shared with other straight contact projectiles.

The yellow-ladder capsule bounds one complete type-14 plant instance from allocation at frame `262518` to type-clear at `263188`: exactly 670 video frames, or 335 logic ticks.

## Evidence boundary

See [[EXP_2026-08-03_phase4_b11_blue_berry_shooter]] for exact shot frames, target filters, damage state, capsule acceptance, C artifacts, hashes, and bounded-exhaustion rationale. Campaign-wide authored-instance breadth, resistant-family breadth, and GPU/audio ownership are not promoted here.
