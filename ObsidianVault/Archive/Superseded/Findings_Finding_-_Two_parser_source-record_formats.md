---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Two parser source-record formats.md
aliases:
  - "Finding - Two parser source-record formats"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Two parser source-record formats.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Two_parser_source-record_formats.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Two parser source-record formats
type: finding
confidence: CONFIRMED
gstep: G2
tags: [finding, dat, parser, format]
---

# Finding — Parser source records come in two flag-selected formats

> Resolved a stride conflict in the DAT parser: a flag bit selects between an 0x18-byte and an 0x20-byte source record.

**Confidence:** CONFIRMED · **Established:** G2

## Summary
[[FUNC_8001CDC0]] reads two source-record shapes, selected by **flag bit3 (0x8)**:
- **non-bit3**, `0x18` bytes — relocated pointer at `+0x14`.
- **bit3**, `0x20` bytes — relocated pointer at `+0x1c`, plus a per-axis `scale[3]` at `+0x12` (12.4 fixed, `0x1000`=1.0).
Shared prefix: `s32 vec[3] @ +0x00`, `s16 angle[3] @ +0x0c`. Both point into the payload band; the bit3 form is read directly at runtime by the builder case `0x8001ec44`.

## Evidence
Reconciled the relocation walk (1248 sites split across the two strides) with the runtime builder reads (G10). Flag bit5 (0x20, "extras") is never set in LEVEL01.

## Related functions
[[FUNC_8001CDC0]] · [[FUNC_8001EA6C]] · [[FUNC_80017B98]]

## Related memory structures
[[MEM - Parser output record]] · [[MEM - DAT runtime memory map]]

## Related experiments
[[Experiment - G12 source vec]]

## Related fixtures / save states
n/a (static + live)

## DuckStation APIs used
[[API - accessLog]] · [[API - execTrace]]

## Next steps
Drives the relocation-aware append correctness ([[Finding - Relocation-aware DAT append]]).

## Source
`src_re_geometry/geometry_notes.md` (G2), `docs/DAT_FORMAT_AND_RELOCATION.md`
