---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Memory Structures/MEM - Survivor lists.md
aliases:
  - "MEM - Survivor lists"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Memory Structures/MEM - Survivor lists.md`
- Replacement/current location: `ObsidianVault/Canon/Memory/MEM_-_Survivor_lists.md`
- Archive reason: Existing memory-structure note; canonicalize with confidence/evidence fields.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: MEM - Survivor lists
type: memory-structure
confidence: CONFIRMED
tags: [memory, rendering, geometry]
---

# MEM — Render survivor lists (LIST_A / LIST_B)

> Intermediate lists between visibility culling and primitive emission.

| List | Address | Written by | Consumed by |
|------|---------|------------|-------------|
| LIST_A | `0x80096ea8` | [[FUNC_800140A0]] (cull survivors, cursor `0x80014124`) | [[FUNC_8001EA6C]] / [[FUNC_800206E8]] (primitive builders) |
| LIST_B | `0x8009e338` | [[FUNC_800140A0]] (cursor `0x80014140`) | **UNKNOWN** (write-only so far) |

## Flow
[[FUNC_800140A0]] tags survivor rows into LIST_A/LIST_B. The builders walk LIST_A, follow `row+0x10` → output record → `+0x18` → source record → payload pointer, and tail-call [[FUNC_80010000]] to draw. The GPU/OT output buffer is `[0x8008240c]` (`gp+0x674`).

> [!note] The LIST_B consumer is an [[Open Questions|open question]].

## Related
- Functions: [[FUNC_800140A0]] · [[FUNC_8001EA6C]] · [[FUNC_800206E8]] · [[FUNC_80010000]] · [[FUNC_800224EC]]
- Structures: [[MEM - Trail and pass3 tables]] · [[MEM - Parser output record]] · [[MEM - fcn.80010000 mesh payload]]
