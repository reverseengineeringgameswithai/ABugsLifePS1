---
kind: memory
id: MEM_80089938
aliases: [MEM_80089938, 0x80089938, actor_berry_column_state_table]
address: 0x80089938
name: Actor berry-column state table
status: byte_matched
confidence: confirmed
source_state: original_game
read_by:
  - FUNC_80049C30
  - FUNC_80053814
  - FUNC_80057A94
  - FUNC_800586B0
  - FUNC_8005905C
written_by:
  - FUNC_80049C30
  - FUNC_8004ABF4
  - FUNC_80053814
  - FUNC_80055538
  - FUNC_800586B0
  - FUNC_80058AF8
serialized_by:
  - FUNC_80055478
initialized_by:
  - FUNC_80055414
evidence:
  - src/main/80055414_scene_flow_state_table_init.c
  - src/main/80055478_serialize_savegame_buffer.c
  - src/main/80055538_scene_config_apply.c
  - src/main/80057a94_spawn_drop_burst_effect.c
  - asm/nonmatchings/resident/8005905c_berry_tough_damage_dispatch.s
  - asm/nonmatchings/resident/8005921c.s
patch_policy: preserve_five_column_stride
---

# MEM_80089938 - Actor berry-column state table

## Confirmed layout

`0x80089938` is a 320-byte original-game table: 64 actor/object rows × five native berry columns.

```text
address = 0x80089938 + actor_id * 5 + native_berry_selector
native_berry_selector = 0..4
```

The five-byte stride is independently established by byte-matched C:

- `scene_flow_state_table_init` creates 64 records at save/config offset `28`, defaulting each to `{100,255,255,255,255}`;
- `scene_config_apply` copies those 64×5 bytes into `0x80089938`;
- `serialize_savegame_buffer` copies the same 64×5 bytes back out;
- `spawn_drop_burst_effect` reads `g_80089938[p[0]*5 + g_800a6597]` and tests the value against `100`.

Matched/disassembled contact paths use the same
`actor_id*5 + selector` address shape. A whole-image C census on 2026-08-04
found exactly 32 resident accesses (20 loads, 12 stores) and zero accesses in
the raw overlay images.

## Confirmed state law

- `mover_init_from_record` clamps an applicable entry below 64 up to 64.
- Two actor/player contact lanes subtract 2 while the old value is at least 65.
- A successful ordinary body-contact hit on Flik adds 2 while the old value is
  below 200 (`0x8004B4F4`). The increment is gated by true health
  `0x800A6594` changing across the shared damage call.
- The contact-vs-actor damage tail has a separate subtract-2 lane guarded at
  33 (`0x80059384`).
- The value participates in CHASE decisions. `mover_init_from_record` clears
  actor flag bit `0x2` at values `>=100` except actor ID 15; a landed-hit path
  sets bit `0x2` below 120 when the actor metadata class is 100, except IDs 13
  and 15. `SYS_enemy_ai` independently binds bit `0x2` as CHASE.
- `spawn_drop_burst_effect` tests the value against 100 for a reaction flag.

Consequently, `enemy_hp_table` is an unsafe universal name. The allocation is
a persistent per-actor-species, per-native-berry adaptive encounter-state
table. Individual consumers use score thresholds for hit, reaction, or CHASE
behavior; none makes every byte literal HP.

## Lazy berry-column inheritance

New-game initialization creates column zero at 100 and columns one through four
at `0xFF`. When the equipped berry selector changes, the gameplay pickup
dispatcher (`0x80054644..0x8005469C`) checks row zero of the destination column.
If it is still `0xFF`, it copies the old selector column into the destination
column for all 64 rows. The contact walker mirrors the same loop at
`0x80058A74..0x80058AB4`.

This is a whole-column first-use inheritance rule, not a frontend `0xFF` scan.
It gives a newly acquired berry class the accumulated species history of the
previously equipped class before later hits diverge the columns.

## ABI consequence

`0x800A6597` is not an extensible enum. Selector `5` is byte zero of the next actor row, not a sixth berry column. Any MOD-only sixth state must be stored privately and normalized to one of the native `0..4` columns before original code reads this table.

## Confidence boundary

The dimensions, addressing expression, complete resident access frontier,
initialization, lazy column inheritance, scene load, serialization, arithmetic
writers, and CHASE thresholds are confirmed. The designer reason for the actor
ID 15 exemption is not encoded in these branches and remains unknown.

## Related

[[MEM_800A6500]] · [[FUNC_80055414]] · [[FUNC_80055478]] · [[FUNC_80055538]] · [[FUNC_80057A94]] · [[SYS_berry_pickup_render_descriptors]]
