---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80059E44.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80059E44.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80059E44_ContactRecord_allocator.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80059E44 — ContactRecord allocator
type: function
address: 0x80059E44
confidence: CONFIRMED
tags: [function, pickup, contact]
---
# FUNC_80059E44 — contact record allocator / constructor

> Allocates the next free slot in the 64-entry contact array and fills it from coords + two metadata tables. The constructor half of pickup spawning.

| Field | Value |
|-------|-------|
| Address | 0x80059E44 (size 668 B, …0x8005A0E0) |
| Source file | `src_re/contact_alloc_80059e44.c` (`contact_alloc`) |
| Confidence | CONFIRMED cursor/wrap, slot search, coord write, both metadata tables, field fill |

## Purpose
Allocates the next free slot in [[MEM - Contact array 800B0D18]] (cursor `0x8008234c`, wraps at 0x40) and fills it from the runtime coords plus metadata table B (`0x8007941c`, idx ctorType) and render-attr table A (`0x80079e30`, idx stackArg).

## Arguments / Returns
`a0`=x, `a1`=y, `a2`=z (runtime coords, caller already `<<5`), `a3`=ctorType, `[sp+0x40]`=stackArg. Returns ContactRecord* (the new record).

## Calls (callees)
- `fcn.800593e8` — render-attr lookup `(nibble,value)→attr word` (fills rec +0x0c..0x18).
- `fcn.80024ddc` — post-init step (a0 = new record).

## Called by (callers)
- [[FUNC_80053814]] (grain 0x51/3, generic 0x71/0x18, kind-0x30 0x71/0x17).

## Globals & structures touched
- [[MEM - Contact array 800B0D18]] · alloc cursor `0x8008234c` · metadata table B `0x8007941c` · table A `0x80079e30`.

## Evidence & confidence notes
CONFIRMED cursor pre-increment + wrap-at-0x40, slot search (skips occupied flag&0x80), coord write, full field fill from metaB. **Documented capacity hang risk**: no full-array escape → if all 64 slots occupied it can spin. `fcn.800593e8` internals + table A meaning are LIKELY/UNKNOWN.

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]]
- Functions: [[FUNC_80053814]] · [[FUNC_800586B0]]
- Memory: [[MEM - Contact array 800B0D18]] · System: [[LEVEL.DAT object pipeline]]
- Source docs: `src_re/contact_alloc_80059e44.c`
