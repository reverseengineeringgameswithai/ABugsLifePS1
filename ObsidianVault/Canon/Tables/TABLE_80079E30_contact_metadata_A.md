---
kind: table
id: TABLE_80079E30
address: 0x80079E30
name: contact_metadata_table_A
status: selector_semantics_decoded
confidence: high
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

# TABLE_80079E30 - contact_metadata_table_A

## Purpose

Scatter-component source for contact records, indexed by `stackArg/extra`. Each
0x14-byte row contains a 16-bit selector pack in its first word and four
32-bit values at `+0x04/+0x08/+0x0c/+0x10`. `contact_alloc` takes one selector
nibble per value and calls `contact_scatter_component_decode` at `0x800593E8`;
the four results are stored at contact-record `+0x0c/+0x10/+0x14/+0x18`.

## Selector Semantics

Selectors outside 1..6 return the value unchanged. Selectors 1..6 consume one
byte from `g_800822F4` and apply these exact transforms, where `r` is that byte
and `v` is the row value:

| Selector | Result |
|---:|---|
| 1 | `((r & v) - (v >> 1)) << 3` |
| 2 | `(r & v) << 3` |
| 3 | `-(r & v) << 3` |
| 4 | `((r & v) + ((v & 0xff00) >> 4)) << 3` |
| 5 | `((r & v) - ((v & 0xff00) >> 4)) << 3` |
| 6 | `((r & v) - (v >> 1)) << 4` |

The helper's corrected extent is `0x800593E8..0x8005953C`; its six jump-table
targets are at `0x80059414`, `0x80059444`, `0x80059470`, `0x800594A0`,
`0x800594D4`, and `0x80059508`. The remaining open question is the gameplay
meaning assigned to individual table rows, not the selector math.
