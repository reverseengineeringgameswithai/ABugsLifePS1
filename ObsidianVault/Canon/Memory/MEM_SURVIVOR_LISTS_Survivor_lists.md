---
kind: memory
id: MEM_SURVIVOR_LISTS
aliases: [MEM_SURVIVOR_LISTS, "MEM - Survivor lists"]
address: multiple
name: Survivor_lists
status: static_seen
confidence: confirmed
source_state: original_game
system: []
read_by: []
written_by: []
related_structs: []
evidence: []
src_paths: []
patch_policy: unknown
---

# MEM_SURVIVOR_LISTS - Survivor lists

## Purpose

Intermediate lists between visibility culling and primitive emission.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

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

> [!note] The LIST_B consumer remains an open question.

## Related
- Functions: [[FUNC_800140A0]] · [[FUNC_8001EA6C]] · [[FUNC_800206E8]] · [[FUNC_80010000]] · [[FUNC_800224EC]]
- Structures: [[MEM - Trail and pass3 tables]] · [[MEM - Parser output record]] · [[MEM - fcn.80010000 mesh payload]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Survivor lists.md`
- Migration status: copy-first Canon seed.
