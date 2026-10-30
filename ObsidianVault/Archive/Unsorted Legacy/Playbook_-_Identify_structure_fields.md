---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Identify structure fields.md
aliases:
  - "Playbook - Identify structure fields"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Identify structure fields.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Identify structure fields
type: playbook
tags: [playbook, structures, method]
---

# Playbook — Identify structure fields

> Turn a "record at address X, stride S" into a labeled field map.

## When to use
You have an array/record (e.g. a new table from a trace) and want to know what each offset means.

## Steps
1. **Get the shape.** Count + stride from the building loop (disasm) or from the consumer's index math. Dump records with [[API - readArray]] (`base, count, stride, fields`) — it reads up to 4096 records of ≤64 typed fields in one call.
2. **Diff across instances.** Compare records that *should* differ (e.g. different objects) — constant columns are flags/types, varying columns are coords/ids.
3. **Diff across time / state.** Re-dump after an in-game action; changed offsets are runtime state. Use [[API - memoryScan]] (changed/unchanged/increased) to find a field that tracks a known quantity.
4. **Find readers/writers** of a specific offset with [[API - accessLog]] (read/write watch at `base+offset`) — the accessing PC tells you the semantic (compared? added to position? used as a pointer?).
5. **Confirm a field's meaning** by perturbing it ([[API - scatterWrite]]) and watching the effect ([[Playbook - Verify a hypothesis]]).
6. **Record** the layout as a [[Memory Structures|MEM note]] and label addresses with [[API - symbols]].

## ABL examples
The [[MEM - Contact array 800B0D18|ContactRecord (0x38)]], [[MEM - Collision sector table 800A7E48|sector record (0x30)]], and [[MEM - fcn.80010000 mesh payload|mesh payload]] were all decoded this way; the contact-record fields map directly to metadata tables A/B.

## Related
[[API - readArray]] (covers readStruct/readPointerChain) · [[API - accessLog]] · [[API - memoryScan]] · [[Playbook - Follow a pointer chain]]
