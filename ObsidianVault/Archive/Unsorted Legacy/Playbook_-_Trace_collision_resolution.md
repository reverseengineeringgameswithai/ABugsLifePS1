---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Trace collision resolution.md
aliases:
  - "Playbook - Trace collision resolution"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Trace collision resolution.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Trace collision resolution
type: playbook
tags: [playbook, collision, method]
---

# Playbook — Trace collision resolution

> How G29 found the floor. Generalizes to "find what writes an effect, then walk back to its source."

## When to use
You want to know what controls a runtime *effect* (player Y / footing / a wall stop) when a static global scan turns up nothing ([[Finding - No static collision consumer]]).

## Steps
1. **Watch the effect, not the cause.** WRITE-watch the output value ([[API - addWatch]] / [[API - accessLog]] write on player Y `0x800a6504`) while moving Flik with scripted [[API - controller input]].
2. **Identify the writer PC** from the hits → the function ([[FUNC_8003633C]], commit `0x80036cec`). Get its callers with a jal scan.
3. **Walk back the data.** [[API - execTrace]] at the writer; read the source registers ([[API - readArray]] / [[API - scatterRead]]) to find the table/record it read — here the candidate list `0x8009c230` → [[MEM - Collision sector table 800A7E48|sector table]] → `[sector+0x10]` → [[MEM - Collision plane record|planes]].
4. **Prove causality.** Edit the suspected source in RAM ([[API - scatterWrite]]) and confirm the effect moves ~1:1 ([[Playbook - Verify a hypothesis]]). → [[Finding - Collision RAM edit moves footing 1to1]].
5. **Find the on-disk source.** accessLog WRITE-watch inside the decompressor [[FUNC_8001A1DC]] to catch which LEVEL.RAW chunk wrote the records; confirm with `tools/parse_level_raw_chunks.py` + [[API - transferLog]] LBA. → chunk 32.

## Gotchas
DMA writes are invisible to CPU watchpoints (use [[API - transferLog]]). The data may be reached via a non-global pointer ([sector+0x10]) — static scans miss it. The "winning record" capture is fiddly (the `sp+0x88` read was buggy) — re-derive carefully.

## Related
[[Collision]] · [[FUNC_8003633C]] · [[FUNC_800345CC]] · [[Experiment - G29 collision lever validation]] · [[Finding - Collision sector table]]
