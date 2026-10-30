---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Parser output record.md
aliases:
  - "MEM - Parser output record"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Parser output record.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Parser_output_record.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - Parser output record
type: memory-structure
address: 0x801B1C10
confidence: CONFIRMED
tags: [memory, dat, parser, geometry]
---

# MEM — Parser output record (`0x20`, base `0x801B1C10`)

> What the DAT parser produces: a 484-entry array of 0x20-byte records placed immediately after the LEVEL.DAT image.

| Field | Value |
|-------|-------|
| Base | `0x801B1C10` (= DATbase `0x801607F8` + filesize `0x51418`) |
| Count / stride | 484 (pass-1) × `0x20` |
| End | `0x801B5890`; reserved end `0x801B6A10` (= (484+140)<<5) |
| Written by | [[FUNC_8001CDC0]] |

## Layout (CONFIRMED)
| Offset | Field | Meaning |
|--------|-------|---------|
| +0x00 … +0x11 | rot[9] (s16) | 3×3 rotation matrix (bit3 records: scaled in place) |
| +0x12 … +0x17 | unk | UNKNOWN |
| +0x18 | src | → source record (relocated) — read by the [[FUNC_8001EA6C|builder bridge]] |
| +0x1c | unk1c | UNKNOWN (not written by visible parser code) |

> [!note] Shape resembles a PsyQ `MATRIX`, but `+0x18` stores a pointer over where `MATRIX.t[1]` would be — so it is probably NOT a live MATRIX. Source records come in two formats — see [[Finding - Two parser source-record formats]].

## Related
- Functions: [[FUNC_8001CDC0]] · [[FUNC_8001EA6C]] · [[FUNC_80017B98]] · [[FUNC_800140A0]]
- Structures: [[MEM - Trail and pass3 tables]] · [[MEM - DAT runtime memory map]]
- Findings: [[Finding - Two parser source-record formats]]
