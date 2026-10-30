---
kind: table
id: TABLE_8007941C
address: 0x8007941C
name: contact_metadata_table_B
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - Contact Objects and Drops
read_by:
  - FUNC_80059E44
row_stride: 0x14
row_count: unknown
evidence:
  - src_re/contact_alloc_80059e44.c
src_paths:
  - src_re/contact_alloc_80059e44.c
patch_policy: safe_to_read
---

# TABLE_8007941C - contact_metadata_table_B

## Purpose

Constructor metadata table for contact records. Indexed by `ctorType`/drop type.

## Layout

Confirmed fields include action ID, active/lifetime value, radius, flags, and several behavior/render bytes. See `src_re/contact_alloc_80059e44.c` for exact field mapping.
