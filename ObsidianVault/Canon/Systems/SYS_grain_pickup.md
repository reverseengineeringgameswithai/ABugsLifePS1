---
kind: system
id: SYS_grain_pickup
status: runtime_seen
confidence: confirmed
source_state: original_game
updated: 2026-08-03
---

# Grain pickup

## Canon behavior

- Ordinary placed grain is type-`0x3F` kind `0x14`.
- `FUNC_80053814` accepts only a runtime record with status `1` and Y not equal to `0x80000000`.
- Direct source contact uses the dispatcher's scaled-distance law and requires `dist2 < 0x9C4`; target `0x80054278` calls `FUNC_80054EAC`.
- When `0x800A6590 & 0x80` is set, a nearby grain instead enters the ctor-`0x51` branch at `dist2 <= 0x15F8F`; this constructs a contact actor and marks the source Y with the consumed sentinel.
- `FUNC_80054EAC` increments byte `0x800A65A1` with wrapping 8-bit arithmetic. It does not saturate.
- A natural pristine capsule captured `10 -> 11` and `11 -> 12`. Each pickup retired exactly one source entry at the same frame boundary by writing Y `0x80000000` and status `0`; the grain HUD pulse `0x800B018C` became `128`.
- Post-increment count exactly `50` enters a distinct reward branch. Its full behavioral order belongs to Phase 4 row C02.
- Ordinary grain does not attract itself to Flik. Attraction is exclusive to the equipped grain-harvester system in C13.

## Static placement scope

Pristine extracted `LEVEL.DAT` files contain 474 kind-`0x14` placements: 50 in each applicable table except `LEVEL04` with 24; `LEVEL00` has no type-`0x3F` table. This does not count runtime/dynamic drops.

## Evidence boundary

The exact instruction that clears the direct source status byte was not attributed because the retained capsule is frame-boundary/count-flow evidence. The before/after lifecycle is confirmed; an Interpreter access watch is only needed if the writer PC becomes a later dependency.

## Evidence

- [[EXP_2026-08-03_phase4_c01_grain_pickup]]
- [`analysis/phase4_c01_grain_pickup.json`](../../../analysis/phase4_c01_grain_pickup.json)
- [`analysis/phase4_trace_capsule_set.json`](../../../analysis/phase4_trace_capsule_set.json)

## Related

- [[FUNC_80054EAC_grain_pickup_handler]]
- [[FUNC_80053814_type-0x3f_construct_+_contact-action_dispatch]]
- [[MEM_TYPE-0X3F_PLACEMENT_RECORD_Type-0x3f_placement_record]]
- [[SYS_grain_harvester]]
