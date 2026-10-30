---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Follow a pointer chain.md
aliases:
  - "Playbook - Follow a pointer chain"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Follow a pointer chain.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Follow a pointer chain
type: playbook
tags: [playbook, method, pointers]
---

# Playbook — Follow a pointer chain

> Dereference structures the way the engine does — including the non-global chains that defeat static scans.

## When to use
A global holds a pointer to a record that holds a pointer… (e.g. DATbase → trail table → output record → source record → payload; or sector → `[+0x10]` → plane records).

## Steps
1. **One-shot chase** with [[API - readArray|readPointerChain]] (`base, offsets[], type`): it derefs u32 at each offset and returns the final address + value. Great for "DATbase + 0x1504 → … → payload".
2. **Validate each hop.** An intermediate unmapped deref is a hard error; sanity-check values (a "vertex count" of `0x70d4001a` means a bogus base — [[Finding - 0x801bdc58 is compressed source]]).
3. **For runtime-built pointers** (not reachable from a global), use [[API - execTrace]] at the consumer and read the pointer register live, or [[API - accessLog]] to catch the store that fills `[record+offset]`.
4. **Cross-check against the relocation model.** LEVEL.DAT pointers are baked file offsets relocated to `DATbase + offset` ([[Finding - Two parser source-record formats]], [[MEM - DAT runtime memory map]]).

## ABL examples
- Render bridge: trail row `+0x10` → [[MEM - Parser output record|output record]] `+0x18` → source record `+0x14/+0x1c` → payload ([[FUNC_8001EA6C]]).
- Collision: [[MEM - Collision sector table 800A7E48|sector]] `+0x10` → [[MEM - Collision plane record|plane records]] (a non-global chain — why G5 static scan saw nothing, [[Finding - No static collision consumer]]).

## Related
[[API - readArray]] · [[API - execTrace]] · [[API - accessLog]] · [[Playbook - Identify structure fields]]
