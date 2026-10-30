---
title: "Blue tier-2 health power"
system: seed-plant-powers
row: B07_health_power
status: confirmed-original-behavior
confidence: substantiated-partial
---

# Blue tier-2 health power

## Canonical behavior

Blue seed tier 2 selects plant type 7 with extra `0x3000`. On each qualifying activation, the plant consumes one RNG byte and emits exactly one object:

| Condition | Output | Probability |
|---|---|---:|
| `(rng_byte & 3) != 0` | Constructor 38 health leaf | 3/4 |
| `(rng_byte & 3) == 0` | Constructor 59 hostile spike | 1/4 |

Constructor 38 uses action 9. Collection adds exactly one to true health `s16 0x800A6594`, requests SFX 62, and enters the shared pickup tail. The pickup handler contains no maximum-health comparison or clamp, so a collection at health 4 writes 5 at this layer.

The retained pristine-runtime control observes the natural transition `3 -> 4` at emulator frame `212377`. The word at `0x800A6590` does not change and is not the health-power effect. `0x800A7E2A` is a HUD pulse field, not true health.

## Production cadence

The type-7 handler emits one object per qualifying plant activation and contains no local recurrence timer. Timing between separate activations is owned by the shared upstream plant-state scheduler. The hostile spike is a per-activation RNG alternative, not a separate lasting mode.

## Scope boundaries

- B07 owns the blue tier-2 route, constructor selection, and hostile-spike coexistence.
- C12 owns generic constructor-38/action-9 pickup behavior across all sources.
- B09 owns the super-jump extra `0x4000` and flag `0x20` special case.

Visible type-7 plant models occur in 10/15 operator levels. Seven levels contain enough locally authored blue tokens to reach tier 2 from zero; the persistent blue counter extends availability after an earlier unlock.

## Evidence

See [[EXP_2026-08-03_phase4_b07_health_power]] and `analysis/phase4_b07_health_power.json` for capsule acceptance, instruction addresses, hashes, campaign bounds, and the bounded-exhaustion rationale.
