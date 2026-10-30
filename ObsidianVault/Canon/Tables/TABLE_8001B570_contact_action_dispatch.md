---
kind: table
id: TABLE_8001B570
address: 0x8001B570
name: contact_action_dispatch
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - Contact Objects and Drops
read_by:
  - FUNC_800586B0
row_stride: 4
row_count: 117
evidence:
  - src_re/contact_walker_800586b0.c
  - src_re/enemy_drops.c
  - tools/phase4_f02_debris_class_bind.c
src_paths:
  - src_re/contact_walker_800586b0.c
  - src_re/enemy_drops.c
patch_policy: do_not_touch
---

# TABLE_8001B570 - contact_action_dispatch

## Purpose

Jump table for contact record collection behavior. The walker indexes it as `action_id - 2`.

## Extent — measured, and a trap worth naming

`0x8001B570` **is the table**. It is not a function, and it is not the *address of* a
dispatcher: the word at `0x8001B570` is `0x80058834`, the first handler pointer. Counted in
place it holds **exactly 117 consecutive in-text pointers (action ids 2..118), terminated by
a `0x00000000` word at `0x8001B744`**. 15 entries are specialized (14 distinct targets, one
shared by ids 58 and 118); the other 102 are the default case `0x800589D4`.

⚠️ A prior F02 attempt read the census "function size" for this address and hunted the table
at `0x8001B570 + 696 = 0x8001B828`, where it found an unrelated pointer run followed by ASCII
string data, and concluded the 117-entry table was "unlocated". Do not treat a census extent
for a data address as a function body.

## How a record gets its action id

The walker's index is **not** the value a spawner passes to the allocator. That argument
(`a3`) is a **ctorType**; the action id is a field of the metadata-B row it selects:

```
contact_alloc(x, y, z, ctorType = a3, stackArg = [sp+0x40])
record+0x20 (action_id) = metaB[ctorType] + 0x00      metaB = 0x8007941C, stride 0x14
walker index            = (int16_t)(action_id - 2),  taken only if (uint32_t)idx < 0x75
```

Indexing this table with a raw `a3` — or with `a3 - 2` — reads an unrelated slot.

Reaching the table at all requires passing the walker's gate first
(`record+0x22 > 0` **and** `record+0x33 & 0x02`, at `0x80058748`), so a ctor type whose
metadata-B flags lack bit `0x02` never dispatches here regardless of its action id. See
[[SYS_contact_object_pool]] and the *separate* behaviour-class dispatch
[[TABLE_8001B7F0_contact_behaviour_class_dispatch]].

## Known rows

- `action_id 9`: health leaf pickup.
- `action_id 33`: arm homing.
- `action_id 34`: arm gold.
- `action_id 35`: arm equip from `s7` lane.
- `action_id 36`: arm mega.
- `action_id 123`: type-120 default branch used by the Gold Berry token mod hook; original behavior is not a literal berry equip.

## Evidence

See `src_re/enemy_drops.c` and `src_re/contact_walker_800586b0.c`.
