---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - readArray.md
aliases:
  - "API - readArray"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - readArray.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - readArray
type: api
category: Memory
tags: [api, duckstation, memory, struct]
---
# API — readArray (structured reads)

> Read tables, structs, and pointer chains in one call — the workhorse for decoding RAM layouts.

## Methods & syntax
- **`debugger.readArray {base, count(1..4096), stride, fields:[{name,offset,type}]}`** — record `i` at `base+i*stride` → `{records:[{index,address,fields:[…]}]}`. Span overflow → `-32006`.
- **`debugger.readStruct {base, fields:[{name,offset,type}]}`** (1..64 fields; types u8/s8/u16/s16/u32/s32) → typed fields; unmapped field → `valid:false` (not an error).
- **`debugger.readPointerChain {base, offsets:[signed], type=s32}`** (Cheat-Engine chase; derefs u32 for all but last). **Intermediate unmapped deref = hard `-32003`**; final unmapped = `valid:false`.
- **`debugger.readCString {address, max_length}`**, **`debugger.readMemory {address, length≤1 MiB}`** (hex+base64; unmapped bytes are `00`), **`debugger.readU8/U16/U32`**.

## Best use in ABL RE
Decoding fixed-stride tables in one shot: the 223-record collision sector table, the type-0x3f records, the contact array, payload vertex arrays.

## Common mistakes / gotchas
- Pause for a coherent snapshot. Watch the `valid` flags rather than assuming mapped.
- For non-contiguous addresses use [[API - scatterRead]] instead of many `readU32` calls.

## ABL examples
- [[MEM - Collision sector table 800A7E48]] — `readArray base=0x800A7E48, count=223, stride=0x30` reads all sectors at once ([[Finding - Collision lever sector186]]).
- [[MEM - Type-0x3f placement record]] — `readArray base=0x800B... stride=0x10` to dump pickups.
- [[MEM - Contact array 800B0D18]] — 64 × 0x38.

## Related
[[API - scatterRead]] · [[API - scatterWrite]] · [[API - memoryScan]] · [[Playbook - Identify structure fields]] · [[Playbook - Follow a pointer chain]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
