---
kind: system
id: SYS_fifty_grain_reward
status: runtime_seen
confidence: confirmed
source_state: original_game
updated: 2026-08-03
---

# Fifty-grain reward

## Trigger

`FUNC_80054EAC` increments byte `0x800A65A1` and tests the post-increment value for equality with `50`. Only exactly `50` enters the retail reward block at `0x80055014`.

The gate is resident and has no level-id exception. Scene `0x11` suppresses the optional random pre-effect but does not suppress the reward.

## Effects

- Player position and player field `+0x48` seed the transient emblem structure `0x80090B80..0x80090B90`; initial scale is `1024`.
- `0x8005044C` is called with id `-11`.
- True health is signed halfword `0x800A6594`; writer `0x80055124` sets it to `4`.
- Ordinary grain HUD `0x800B018C` and reward HUD `0x800B0190` pulse independently.
- Lives byte `0x800A65A0` is unchanged. The apparent extra-life branch is unreachable in pristine retail because it compares unequal constant addresses `0x80090B80` and `0x800B3988`.

A matched accelerated control from the same pristine state proved `48 -> 49` leaves forced health `1` unchanged, while `49 -> 50` sets it to `4` and seeds the emblem structure.

## Presentation lifecycle

In the retained natural movie, reward HUD is last nonzero 123 frames after the trigger and zero on the next frame. The emblem structure remains active through movie frame `409` and retires via the X sentinel at `410`, 250 frames after its frame-`160` trigger.

## Persistence boundary

`FUNC_80055478` does not directly serialize grain count, true health, or emblem state. The emblem is transient presentation; the in-level grain objective is count-derived. Results, campaign flags, and movie unlock presentation belong to downstream systems.

## Corrected legacy interpretation

`0x800A7E2A` is a free-running HUD/leaf animation counter, not true health. Older emblem documentation correctly observed the visible refill presentation but assigned health semantics to the animation counter. True health is `0x800A6594`.

## Evidence

- [[EXP_2026-08-03_phase4_c02_fifty_grain_reward]]
- [`analysis/phase4_c02_fifty_grain_reward.json`](../../../analysis/phase4_c02_fifty_grain_reward.json)
- [`analysis/phase4_trace_capsule_set.json`](../../../analysis/phase4_trace_capsule_set.json)

## Related

- [[SYS_grain_pickup]]
- [[FUNC_80054EAC_grain_pickup_handler]]
- [[FUNC_80055478_serialize_savegame_buffer]]
- [[FUNC_800526F4_HUD_draw]]
