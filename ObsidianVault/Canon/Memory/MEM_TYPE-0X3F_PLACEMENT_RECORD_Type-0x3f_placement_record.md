---
kind: memory
id: MEM_TYPE-0X3F_PLACEMENT_RECORD
aliases: [MEM_TYPE-0X3F_PLACEMENT_RECORD, "MEM - Type-0x3f placement record"]
address: unknown
name: Type-0x3f_placement_record
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

# MEM_TYPE-0X3F_PLACEMENT_RECORD - Type-0x3f placement record

## Purpose

The LEVEL.DAT object-placement record. Every pickup (grain, FLIK letter, berry, seed token, telescope) is one of these. The most thoroughly modded structure in the project.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - Type-0x3f placement record
type: memory-structure
confidence: CONFIRMED
tags: [memory, dat, pickup, type3f]
updated: 2026-07-05
---

# MEM — Type-0x3f placement record (`sizeof 0x10`)

> The LEVEL.DAT object-placement record. Every pickup (grain, FLIK letter, berry, seed token, telescope) is one of these. The most thoroughly modded structure in the project.

| Field | Value |
|-------|-------|
| **On-disk** | first top-level record in `LEVEL.DAT`; header `46 00 3f 00` (count LE u16 + type 0x3f) at file `0x4`; entries start at file `0x8`; entry N at `0x0008 + N*0x10` |
| **Runtime ptr** | `0x80096E9C` (= type table `0x80096DA0` + 0x3f*4) |
| **Coordinate rule** | **runtime coord = file coord `<< 5`** (×32) |
| **Parsed/relocated by** | [[FUNC_8001CDC0]] |
| **Consumed by** | [[FUNC_80053814]] (construct + contact action) |

## Layout (CONFIRMED)
| Offset | Type | Field | Meaning |
|--------|------|-------|---------|
| +0x00 | int32 | x | X (runtime = x<<5) |
| +0x04 | int32 | y | Y (more-negative = up); set to `0x80000000` sentinel when consumed |
| +0x08 | int32 | z | Z |
| +0x0c | uint8 | kind | source kind discriminator — **selects model AND behavior** (CONFIRMED live: grain `0x14`→telescope `0x30` rendered as the green telescope + triggered its "continue/exit level" hint menu → [[Experiment - Pickup kind-swap]]) |
| +0x0d | uint8 | status | runtime eligibility (must == 1 to be live) |
| +0x0e/+0x0f | uint8 | unk | unknown (lh +0x0a used by telescope alt path) |

## LEVEL01 entry map (70 entries)
grain `0..49` (kind 0x14) · FLIK letters `50..53` (0x10 F / 0x11 L / 0x12 I / 0x13 K) · special berries `54..57` (0x22 Gold / 0x23 Blue / 0x21 Green / 0x24 Purple) · seed tokens `58..66` (0x29/0x2a/0x2b) · **telescopes `67..69` (0x30)** — the hint device (reveals an item/exit location; "continue/exit level" hint UI). *(was mislabeled "checkpoint/trigger"; corrected by operator 2026-06-18 → [[Experiment - Pickup kind-swap]].)* See [[Finding - Type-0x3f pickups are coordinate-moddable]] and the [[Symbols Index]] kind map.

## Appended FLIK-letter proof (2026-07-05)
[[Experiment - FLIK5 five-letter token gate]] appends entry 70 as a duplicate native F (`kind 0x10`,
status byte `1`) after relocation-aware DAT append. Runtime proof from `build/ABL_FLIK5.cue`:
type-`0x3f` count `71`; entries 50–53 plus 70 collected cleanly; after entries 50–53 the FLIK mask was
`0x0f` and the progress/lives byte stayed `5`; after entry 70 the FLIK mask became `0x1f` and the byte
advanced to `6`.

Important modding constraint: keep entry 70 as a native `kind 0x10` if it should look like F. The failed
attempt to create a fake F by changing a free kind/descriptor slot corrupted the top-left Flik-head HUD
icon, because that descriptor address is shared with other UI/object graphics.

> [!warning] **Never change kind on entries 54–57** — that deletes a real berry. Only edit X/Y/Z. Don't naive-append (stale baked offsets → black screen); use the relocation-aware tool — see [[Finding - Relocation-aware DAT append]].

## Edit tools
`tools/patch_level_entry.py` (move), `tools/move_type3f_entry.py` (safe move), `tools/dat_reloc.py` + `tools/insert_type3f_entries.py` (relocation-aware append). See [[Tools Catalog]].

## Related
- Findings: [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Relocation-aware DAT append]]
- Functions: [[FUNC_8001CDC0]] · [[FUNC_80053814]] · [[FUNC_80059E44]]
- System hub: [[LEVEL.DAT object pipeline]] · Assets: [[Asset - LEVEL.DAT]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - Type-0x3f placement record.md`
- Migration status: copy-first Canon seed.
