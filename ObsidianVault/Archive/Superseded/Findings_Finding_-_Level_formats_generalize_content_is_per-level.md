---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Level formats generalize, content is per-level.md
aliases:
  - "Finding - Level formats generalize, content is per-level"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Level formats generalize, content is per-level.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Level_formats_generalize-_content_is_per-level.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Level formats generalize, content is per-level
type: finding
confidence: CONFIRMED
tags: [finding, b8, leveldat, levelraw, generality]
updated: 2026-06-18
---

# Finding — Level FORMATS generalize across all 10 levels; CONTENT is per-level

> Offline cross-level analysis (2026-06-18, B8): the LEVEL.RAW PROPACK chunk container and the LEVEL.DAT parser both **generalize to all 10 levels** (the existing decoder/parser run unchanged). But the specific **chunk indices and record-type sets are per-level**, so LEVEL01's exact maps (chunk 32 = collision, records 1–10 = paths) are **not portable by index** — re-identify by content/type. No emulator/save-states needed.

**Confidence:** CONFIRMED (offline walk of all 10 disc images) · **Established:** 2026-06-18 (B8)

## LEVEL.RAW (chunk container)
- All 10 levels are PROPACK chunk containers, walked by the **same** logic (validates: LEVEL01 = 69 chunks ✓).
- Chunk count **varies 45–73**; decompressed size ~0.9–1.3 MB. The **33548-byte texture-frame** format recurs in every level (**3–17** frames each).
- "Biggest chunk" (LEVEL01 chunk 32 = collision, 236944 B) varies **33548–268372** per level ⇒ collision/terrain exist everywhere but at **level-specific indices** — find by content/subtype, not the fixed `31/32/35`.

## LEVEL.DAT (records)
- The parser **size rules generalize** (all 10 parse cleanly). **Every level has rec0 = type 0x3f pickups** (universal); pickup count varies **47–77** (confirms no 70-cap). *(LEVEL00 = dev stage, 0 records.)*
- **Non-pickup record set varies a lot:** L01 `[1,11,12,13,-2..-7]` · L02 `[1]` · L03 `[1,2,9,11,12]` · L04 `[1,2,3,4,5,6,9,11,12,13]` · L05 `[11,12,13,14]` (no type-1) · L06 `[]` (pickups only) · L07 `[1,11,12,13,14,15,16]` · L08 `[1]` · L09 `[1,11,12,13,-4]`. New types (2,3,4,5,6,9,14,15,16) appear that LEVEL01 lacks; the negative records (`-2..-7`) are mostly LEVEL01-only.
- ⇒ the [[Finding - LEVEL.DAT records are object paths|records-1–10-are-paths]] result is LEVEL01-specific in its **types**; the general "3×s32 records consumed as paths/data" pattern likely holds, but each level's type→role map needs its own (cheap) per-type consumer check.

## Net (B8)
- **Modding tooling generalizes** — decode/parse/edit any level with the existing tools, no per-level rework of the codec/parser.
- **The LEVEL01 index/type maps do NOT** — collision/terrain chunks and record roles must be re-identified per level (by content/subtype/consumer); the methods already cover that.
- **Runtime behavior** (render/collision/path *consumers*) — **NOW CONFIRMED (2026-06-18)** by loading operator start-saves for **LEVEL02/03/04/05** (stages 3/2/6/10): the **engine structures sit at FIXED addresses every level** — collision sector table `0x800a7e48`, player state/Y `0x800a6504`, mesh/render buffer `0x8012c1cc` are all populated in all 4 — while **data lands per-level** (`DATbase` varies `0x8015e22c / 0x80125c44 / 0x801430d8 / 0x8015baac`; record count 6/2/1/7; rec0 = type-0x3f pickups in *all*). ⇒ the engine generalizes (LEVEL01 fixed-address findings transfer directly); only per-level *data addresses/indices* must be read at runtime, never hardcoded. Validates [[Assumptions Register|A6]].

## Per-level snapshot (runtime, 2026-06-18)
| Level (stage) | DATbase | DAT recs | RAW chunks | Sample cast |
|---|---|---|---|---|
| LEVEL01 | `0x801607f8` | 11 | 69 | FLICK, BADBUG, MOS, WASP |
| LEVEL02 (3) | `0x8015e22c` | 6 | 45 | GRUB, GGRASSH |
| LEVEL03 (2) | `0x80125c44` | 2 | 55 | MOS, THUMPER |
| LEVEL04 (6) | `0x801430d8` | 1 | 65 | BBIRD, DRAGFLY |
| LEVEL05 (10) | `0x8015baac` | 7 | 63 | FLY, MOS, WASP, HSPIDER |

## Related
[[Blocker - RE depth is LEVEL01-only]] · [[MEM - LEVEL.RAW chunk inventory]] · [[Finding - LEVEL.DAT records are object paths]] · [[Finding - LEVEL.RAW is compressed]] · [[Asset - LEVEL.DAT]] · [[Asset - LEVEL.RAW]]
- Source: offline walk of `REBUILD/files/LEVEL0*/LEVEL.RAW` + `DAT/LEVEL0*_LEVEL.DAT`
