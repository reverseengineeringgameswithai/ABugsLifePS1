---
system: hostile-blue-plant-projectiles
phase: 4
status: confirmed-bounded
---

# Hostile blue-plant projectiles

## Native producer

Constructor 59 is the hostile ballistic output of blue **type-7** plants. The only
resident immediate selections of constructor 59 are `0x8005C78C` and `0x8005C7E4`,
both inside handler `0x8005C744..0x8005C818`.

| Blue tier | Plant route | Constructor-59 law |
|---|---|---|
| 1 | type 7, extra `0x2000` | 1/4 per qualifying activation; otherwise c37 |
| 2 | type 7, extra `0x3000` | 1/4 per qualifying activation; otherwise c38 |
| 3 | type 6, extra `0x0000` | **Never through the native handler**; one-shot c31 only |
| 4 | type 7, extra `0x4000` | 1/4 before power bit `0x20`; forced c59 after it is set |

This supersedes the earlier claim that every blue tier eventually emits constructor
59. The type-6 handler computes `(extra>>12)+31`, uses profile 3, sets one-shot latch
`0x0008`, and has no constructor-59 branch.

## Spawn and cadence

Type 7 spawns one object at `(plant.x, plant.y-0x4000, plant.z)` with contact profile
6, then calls radial helper `0x800579E0`. In the accepted all-tier fixture, all three
type-7 tiers first qualify `194` movie frames after plant creation and repeat every
`168` frames. These are fixture timing values owned by shared animation/scheduler
state, not counters local to the type-7 handler.

Type 6 emits constructor 31 once, `28` movie frames after its fixture plant birth.

## Constructor-59 record

| Field | Value |
|---|---:|
| action ID | `8` |
| active/lifetime | `200` logic updates |
| animation counter | `210` |
| radius addend | `100` |
| effective player radius | `400` |
| terminal state | `-60` |
| flags | `0xE3` |

Profile 6 produces an unguided ballistic arc:

- `VX`, `VZ`: `-1016..1024`;
- `VY`: `-2560..-2056`;
- `AY`: `+128` per logic update;
- no homing/target-follow, because flags bit `0x08` is clear.

Action 8 enters impact state `0x13` and reaches `FUNC_8004A700`, which subtracts one
health at `0x8004A888` unless an existing power intercepts contact damage.

## Retirement

Constructor 59 retires on its 200-update lifetime, terrain/world contact, or player
contact. Terrain and timeout retain terminal state `-60`; the finalizer negates it and
spawns constructor 60 at the terminal coordinates. Player contact sets active `1` and
state `0x13`, deals damage, and retires on the next update.

The retained all-tier capsule observes five constructor-59 objects. All five hit
terrain/world geometry after `80, 82, 84, 80, 86` movie frames, and all five emit the
constructor-60 terminal effect.

## Consumption contract

- Constructor 59 is safe to consume as a resident, non-homing ballistic contact
  hazard owned by the shared 64-slot contact pool.
- Do not model blue tier 3 as a constructor-59 producer.
- Do not model the observed `194/168` movie-frame cadence as a constant in the type-7
  handler; animation/scheduler state owns qualification.
- Preserve action ID 8, flags `0xE3`, profile 6, the shared damage interceptors, and
  the second-pass finalizer if modifying the object.
- Exact sprite, GPU, SFX, and SPU ownership remains bounded and must not be inferred
  from constructor identity alone.

## Evidence

- [[EXP_2026-08-03_phase4_b14_hostile_plant_projectiles]]
- `analysis/phase4_b14_hostile_plant_projectiles.json`
- `tools/phase4_b14_static.c`
- `tools/phase4_b14_capsule.c`
- `analysis/phase4_trace_capsule_set.json`
- [[SYS_blue_health_power]]
- [[SYS_player_power_slot]]
- [[SYS_contact_objects_and_drops]]
