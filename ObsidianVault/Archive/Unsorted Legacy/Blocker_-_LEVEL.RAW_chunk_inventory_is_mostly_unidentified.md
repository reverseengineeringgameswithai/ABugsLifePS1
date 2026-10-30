---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - LEVEL.RAW chunk inventory is mostly unidentified.md
aliases:
  - "Blocker - LEVEL.RAW chunk inventory is mostly unidentified"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - LEVEL.RAW chunk inventory is mostly unidentified.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - LEVEL.RAW chunk inventory is mostly unidentified
type: blocker
id: B9
severity: MEDIUM
category: level-format
confidence: CONFIRMED
tags: [blocker, major, levelraw, chunks, format]
updated: 2026-06-22
---

# 🟠 B9 — ~66 of 69 LEVEL.RAW chunks have no identified role

> LEVEL.RAW decompresses to **69 chunks**, but only **3** are semantically identified (31 = seeds, 32 = collision + sky color, 35 = terrain) — ~**4 %**. The per-chunk subtype dispatch is only sampled; there is no published 69-row inventory of (subtype, size, consumer, role).

**Severity:** ~~Major~~ → **Medium** · **Impact:** High · **Likelihood:** Medium · **Confidence:** CONFIRMED · **Difficulty:** High

## Audit reconciliation (2026-06-22)
**Body count is STALE.** The "3/69 ≈ 4 %" framing conflates two different milestones. CORRECTED:
- **All 69 chunks are now CLASSIFIED** (region + subtype + size) in [[MEM - LEVEL.RAW chunk inventory]] — there IS a published full-table inventory.
- **But only 3/69 have a VERIFIED SEMANTIC ROLE** (31 = seeds, 32 = collision + sky, 35 = terrain). The other ~62 carry **format-class labels only** (not consumer-traced meanings).

**TRUE STATUS = PARTIALLY ADDRESSED.** Frontmatter `severity` reconciled to **MEDIUM** (full classification done; semantic decode still the long pole). OPEN: Region-A bpp/CLUT; the Region-C `01 01` / `02 01` pairing meaning; chunk-34 on-screen role; the 6-byte header trailer. **Do not over-claim "resolved."**

## What is known (evidence)
- LEVEL.RAW = **69 chunks**, 1,269,304 B decompressed ([[Finding - LEVEL.RAW is compressed]], [[MEM - LEVEL.RAW chunk model]]). Each chunk carries a subtype byte that drives a large dispatch (`0x8003a4ec…0x8003c250`); observed subtype constants include `0,4,5,6,7,0xb,0xc,0xd,0x1b–0x1e,0x20,0x24,0x26,0x29`.
- Only **three subtype families** are characterized: `0x20` = environment/light (sky-color table, in chunk 32), `0xd` = texture/VRAM upload, and a "vertex/index builder tail" = mesh. **Identified chunks: 31 / 32 / 35.**
- `tools/parse_level_raw_chunks.py` walks the table but the resulting 69-row inventory with roles is never published; the offline chunk-32 estimate even drifts ~`0xb3c` vs the live converter output (precision gap → see [[Blocker - Collision internals are partly undecoded|B18]]).

## Why it matters
- A "full" level-format RE requires the complete chunk table with every subtype's meaning and consumer — this is the single largest level-format gap. It also gates a byte-precise chunk map for permanent edits ([[Blocker - Byte-exact disc reproduction is unproven|B4]]).

## Dependencies
- **Depends on:** [[Blocker - RE depth is LEVEL01-only|B8]] (inventory is per-level). **Feeds:** [[Blocker - Byte-exact disc reproduction is unproven|B4]] and any level editor. **Related assumption:** A5.

## Research opportunity (direction only)
- Enumerating all 69 chunks (subtype, decompressed size, consumer) by exercising the dispatch once per chunk, then mapping each subtype constant to its handler/consumer, would yield the missing inventory — the backbone the rest of the level-format work needs. (Direction only.)

## Evidence & sources
- vault: [[MEM - LEVEL.RAW chunk model]] · [[Finding - LEVEL.RAW is compressed]] · [[FUNC_8003A318]] · [[FUNC_8001A1DC]] · [[Asset - LEVEL.RAW]]
- corpus: `src_re_geometry/geometry_g25_level_raw_post_decompress_trace.md` (§3, §6), `tools/parse_level_raw_chunks.py`
- See also: [[Blockers]] · [[Risk Matrix]]
