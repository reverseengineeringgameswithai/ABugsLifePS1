---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_80030F60.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_80030F60.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_80030F60_collision_sector-table_builder.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_80030F60 — collision sector-table builder
type: function
address: 0x80030F60
confidence: CONFIRMED
tags: [function, collision, levelraw]
---
# FUNC_80030F60 — collision sector-table builder

> Converts the decompressed LEVEL.RAW chunk-32 source into the runtime collision sector table that the movement integrator queries.

| Field | Value |
|-------|-------|
| Address | 0x80030F60 (helpers `0x80030fac/0x80030fd8`; caller `0x800314CC`) |
| Source file | disasm (G29) |
| Confidence | CONFIRMED (G29 live) |

## Purpose
Builds and scales (`<<5`) the [[MEM - Collision sector table 800A7E48]] (`0x800a7e48`, 223 records × 0x30) from decompressed source records (`t1 = 0x800F7BF8`). Each sector record carries an AABB and a `[+0x10]` pointer to 32-byte collision plane records (`~0x800D0xxx`).

## Arguments / Returns
Source pointer into the decompressed chunk-32 region. Effect: populated sector table + plane records.

## Calls (callees)
- helpers `0x80030fac` / `0x80030fd8`.

## Called by (callers)
- `0x800314CC` (post-decompress build phase under [[FUNC_8003A318]]).

## Globals & structures touched
- [[MEM - Collision sector table 800A7E48]] · [[MEM - Collision plane record]] · source `0x800F7BF8`.

## Evidence & confidence notes
G29 confirmed the disk→table path: LEVEL.RAW chunk 32 decompressed by [[FUNC_8001A1DC]] → this builder → sector table queried at runtime by [[FUNC_8003633C]]/[[FUNC_800345CC]]. Findings store ids f6, f11.

## Related
- Findings: [[Finding - Collision sector table]] · [[Finding - Collision on-disk source is chunk 32]] · [[Finding - Collision is planes not scalar]]
- Functions: [[FUNC_8001A1DC]] · [[FUNC_8003A318]] · [[FUNC_8003633C]] · [[FUNC_800345CC]]
- Source docs: `src_re_geometry/geometry_g29_collision_source_plan.md`
