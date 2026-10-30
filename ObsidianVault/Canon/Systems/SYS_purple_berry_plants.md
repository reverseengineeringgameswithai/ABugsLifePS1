---
kind: system
id: SYS_purple_berry_plants
name: Purple Berry Plants
status: confirmed_original_behavior
confidence: high
row: B10_purple_berry_plants
evidence:
  - EXP_2026_08_03_phase4_b10_purple_berry_plants
  - analysis/phase4_b10_purple_berry_plants.json
---

# Purple berry plants

## Canonical behavior

All four purple tiers grow plant type 6. The tier extra selects a berry-grant contact constructor:

| Tier | Extra | Constructor / action | Equip `0x800A6597` | Berry |
|---:|---:|---:|---:|---|
| 1 | `0x4000` | 35 / 35 | 1 | Blue/Super |
| 2 | `0x2000` | 33 / 33 | 2 | Green/Homing |
| 3 | `0x1000` | 32 / 36 | 4 | Purple/Mega Homing |
| 4 | `0x3000` | 34 / 34 | 3 | Gold |

The producer is deterministic. A qualifying type-6 activation spawns exactly one grant at plant X, plant Y minus `0x1400`, plant Z, then sets the plant instance's one-shot bit. No RNG or repeated production timer exists in this B10 handler.

## Collection and lifetime

The four grant objects share an initial 230-logic-tick countdown, auxiliary timer 240, effective collection radius 400, common state 7, and flags `0xE2`. Player overlap dispatches the matching action, directly overwrites `u8 0x800A6597`, plays SFX 53-56 according to tier, and retires the collected record through the shared contact tail.

The retained pristine control observes all four transitions at exact emulator frames:

```text
133396: 0 -> 1
133920: 1 -> 2
134486: 2 -> 4
135204: 4 -> 3
```

The tier-1 record becomes inactive by frame 133398, two video frames after collection.

## Equip and reset law

- A later grant overwrites the current equip value; the handlers have no stack or same-tier denial.
- Throw dispatch reads equip but does not clear it. Special berry selection persists across throws.
- Level initialization clears the `0x800A6500` player block for `0xA8` bytes, including equip, restoring default/red value 0.

Projectile flight, homing, damage, and retirement after a throw belong to [[SYS_berry_projectile_and_homing]]. Generic output selection belongs to [[Seed_plant_output_binding]]. Generic contact-pool behavior belongs to the contact-object system.

## Evidence boundary

See [[EXP_2026-08-03_phase4_b10_purple_berry_plants]] for capsule acceptance, exact instructions, hashes, C analysis, limitations, and the bounded-exhaustion decision. Campaign-wide visual-instance breadth and GPU animation ownership are not promoted here.
