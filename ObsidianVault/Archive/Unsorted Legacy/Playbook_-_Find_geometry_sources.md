---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Find geometry sources.md
aliases:
  - "Playbook - Find geometry sources"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Find geometry sources.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Find geometry sources
type: playbook
tags: [playbook, geometry, method]
---

# Playbook — Find geometry sources (which file/RAM backs a payload)

> Distinguish DAT-backed payloads (disc-editable) from LEVEL.RAW-decompressed buffers (RAM-only until the LZ codec exists).

## When to use
You found a buffer/payload that draws geometry and need its authoritative on-disk source.

## Steps
1. **Count-validate the payload** at EXEC [[FUNC_80010000]] (`[a0]` = vertex count must be sane). A garbage count means a bogus base (the G26 lesson — [[Finding - 0x801bdc58 is compressed source]]).
2. **Classify offline** with `tools/analyze_g27_floor_candidates.py` (vertex range, bbox, flatness, instancing). Flat + unique + world-space + lower-center = floor candidate; instanced/high-frequency = decor.
3. **Locate in RAM.** Is the runtime address inside the LEVEL.DAT image (`0x801607F8…0x801B6A10`, [[MEM - DAT runtime memory map]]) or the LEVEL.RAW buffer (`0x80115AAC…`)?
   - In DAT → **disc-editable**: map runtime→DAT offset, patch, rebuild ([[Asset - Disc image and rebuild]]).
   - In LEVEL.RAW → decompressed: find the source chunk.
4. **Find the chunk** with `tools/parse_level_raw_chunks.py <LEVEL.RAW> <runtime_addr>` (chunk 32 = collision/sky, chunk 35 = terrain), corroborate with an [[API - accessLog]] WRITE-watch inside [[FUNC_8001A1DC]] and [[API - transferLog]] LBA.
5. **Prove + edit** ([[Playbook - Verify a hypothesis]]).

## ABL example
This pipeline produced Candidate A (DAT-backed visual terrain, [[Finding - Candidate A is DAT-backed visual terrain]]) and mapped terrain→chunk 35 / collision→chunk 32.

## Related
[[Geometry]] · [[Geometry pipeline]] · [[MEM - LEVEL.RAW chunk model]] · [[FUNC_8003A318]] · [[Playbook - Trace rendering ownership]]
