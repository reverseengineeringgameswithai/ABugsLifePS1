---
kind: system
id: SYS_yellow_tier2_vertical_shooter
name: Yellow tier-2 vertical shooter
status: confirmed
created: 2026-08-03
updated: 2026-08-03
confidence: high
source_state: original_game
evidence:
  - EXP_2026-08-03_phase4_b12_homing_shooter
---

# Yellow tier-2 vertical shooter

## Legacy-name correction

The mechanics registry historically called B12 the **Purple homing shooter**
and said the second yellow combat plant homes on enemies. That is not the
resident type-13 mechanism.

The yellow selector's four authored outputs are plant types `14, 13, 11, 1`.
Tier 2 is type 13. Its firing handler contains no acquisition scan and no
steering law.

## Confirmed type-13 law

Type 13 dispatches through `0x8005CA24`. It fires only when:

- plant state `+0x02` is 2; and
- plant phase `+0x04` is `0x00010000`.

It constructs ID 67 at:

- `X = plant X`;
- `Y = plant Y - 0x6400`;
- `Z = plant Z`;
- velocity `(0, -2048, 0)`; and
- gravity 128.

The resulting contact record is class 2, timer 20 logic ticks, model 124,
radii 50/50, subtype 14, flags `0xE5`, and byte `+0x27 = 0`.

No-target behavior is the only behavior because there is no target solver in
this path. X/Z remain fixed, VY increases by 128 per 30 Hz logic tick, and a
natural no-contact generation expires after 20 logic ticks / 40 video frames.

The dedicated retained capsule observes shots every 88 video frames / 44 logic
ticks, beginning at movie frame 406.

## Separation from player homing berries

The model-110/subtype-1 shots in the retained B12 movie follow Square input and
increment the player-owned projectile counter. They are red straight throws,
not plant emissions and not homing primaries.

Actual player homing uses primary type 8 and child type 16. Its acquisition,
quarter-error steering, vertical clamp, ownership transfer, and cleanup belong
to [[SYS_berry_projectile_and_homing]]. Homing damage and the berry-tough gate
belong to [[SYS_enemy_berry_resistance]].

Do not use the old B12 label or the movie filename to transfer those mechanics
to the type-13 plant.

## Lifecycle

The accepted yellow-tier capsule observes type-13 allocation, growth into
state 1, active state 2, repeated firing, operator uproot state 3, and slot
clear. The dedicated capsule independently observes a persistent type-13 plant
and eleven exact 88-frame firing intervals.

## Scope boundary

Campaign-wide visual-instance coverage, natural plant expiry without uproot,
every generic contact cull path, and exact GPU/SPU attribution remain deferred.
They do not alter the confirmed non-homing construction and recurrence law.

## Evidence

- [[EXP_2026-08-03_phase4_b12_homing_shooter]]
- `analysis/phase4_b12_homing_shooter.json`
