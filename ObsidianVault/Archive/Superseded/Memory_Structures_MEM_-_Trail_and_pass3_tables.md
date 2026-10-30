---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Trail and pass3 tables.md
aliases:
  - "MEM - Trail and pass3 tables"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Trail and pass3 tables.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Trail_and_pass3_tables.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - Trail and pass3 tables
type: memory-structure
confidence: CONFIRMED
tags: [memory, dat, rendering, geometry]
---

# MEM — Trail (pass-1) and pass-3 tables

> The two relocation-block tables the render driver walks each frame. The "trail flag" terrain-render lever lives here.

| Table | Global | Runtime | Stride / count | Role |
|-------|--------|---------|----------------|------|
| Trail (pass-1) | `G_TRAIL_BLOCK_PTR` `0x800824ac` | `0x80161cfc` (DATbase+`0x1504`) | `0x14` × 484 | culled by [[FUNC_800140A0]] |
| Pass-2 | `G_PASS2_BASE_PTR` `0x80082338` | DATbase+`0x3ae8` | EMPTY in LEVEL01 |
| Pass-3 | `G_PASS3_BASE_PTR` `0x80082508` | `0x801642e4` (DATbase+`0x3aec`) | `0x14` × 140 | culled by `fcn.80014360` |

## Trail row layout (stride 0x14)
| Offset | Meaning |
|--------|---------|
| +0x00 / +0x04 / +0x08 | vector (view-relative) |
| +0x0c | extent/range term |
| +0x0e | **flag / sentinel** (read every row at `0x80014170`) |
| +0x10 | → output record (`+0x18` → source) |

The flag halfword `DAT+0x1526` (runtime `0x80161d1e`) is the **terrain-render lever** — see [[Finding - Trail flag gates terrain render]]. Per-row body fields are gated by the bitmask table `0x800901c8`. entry24 is a culling row — see [[Finding - entry24 is a culling row]].

## Related
- Functions: [[FUNC_800140A0]] · [[FUNC_800224EC]] · [[FUNC_8001CDC0]] · [[FUNC_8001EA6C]]
- Structures: [[MEM - Parser output record]] · [[MEM - Survivor lists]] · [[MEM - DAT runtime memory map]]
- Findings: [[Finding - Trail flag gates terrain render]] · [[Finding - entry24 is a culling row]]
- Experiments: [[Experiment - G6 render sentinel]] · [[Experiment - G5.5 dynamic watch]]
