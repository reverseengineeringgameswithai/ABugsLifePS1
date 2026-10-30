---
kind: struct
id: STRUCT_contact_record
name: ContactRecord
status: static_seen
confidence: confirmed
source_state: original_game
system:
  - Contact Objects and Drops
memory:
  - MEM_800B0D18
evidence:
  - src_re/re_types.h
  - src_re/contact_alloc_80059e44.c
src_paths:
  - src_re/re_types.h
  - src_re/contact_alloc_80059e44.c
---

# STRUCT_contact_record

## Layout

Selected confirmed fields:

- `+0x00/+0x04/+0x08`: x/y/z runtime coords.
- `+0x0c..+0x18`: render attributes.
- `+0x1c`: initialized to `-1`; used by Gold Berry token mod as enemy tag only for tagged glyph records.
- `+0x20`: action ID.
- `+0x22`: active/lifetime gate.
- `+0x28`: radius add.
- `+0x33`: flags, including enabled/occupied bits.

## Source

See `src_re/re_types.h` and `src_re/contact_alloc_80059e44.c`.
