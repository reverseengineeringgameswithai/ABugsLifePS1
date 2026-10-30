---
kind: constant
id: CONST_DROP_TYPES_AND_ACTIONS
name: Drop Types and Contact Actions
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - Contact Objects and Drops
evidence:
  - src_re/enemy_drops.c
src_paths:
  - src_re/enemy_drops.c
---

# CONST_DROP_TYPES_AND_ACTIONS

## Meaning

Selected original-game contact/drop type IDs and action IDs.

## Values

- `type 32` -> `action_id 36`: arm mega.
- `type 33` -> `action_id 33`: arm homing.
- `type 34` -> `action_id 34`: arm gold; literal gold-berry equip pickup.
- `type 35` -> `action_id 35`: arm equip from native lane.
- `type 38` -> `action_id 9`: health leaf.
- `type 120` -> `action_id 123`: spinning gold-kill glyph visual row.

## Boundary

The Gold Berry token mod uses `type 120` plus a pickup hook. Do not document that as original-game type-120 collection semantics.
