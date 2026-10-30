---
kind: memory
id: MEM_DAT_RUNTIME_MEMORY_MAP
aliases: [MEM_DAT_RUNTIME_MEMORY_MAP, "MEM - DAT runtime memory map"]
address: multiple
name: DAT_runtime_memory_map
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

# MEM_DAT_RUNTIME_MEMORY_MAP - DAT runtime memory map

## Purpose

Where the parsed LEVEL.DAT lives at runtime and how its regions lay out. DATbase = `[0x80082498]` = `0x801607F8`.

## Layout / fields

The content below is copied from the original note for copy-first migration. Review before treating every claim as Canon.

---

---
title: MEM - DAT runtime memory map
type: memory-structure
confidence: CONFIRMED
tags: [memory, dat, map, geometry]
---

# MEM — LEVEL.DAT runtime memory map (LEVEL01)

> Where the parsed LEVEL.DAT lives at runtime and how its regions lay out. DATbase = `[0x80082498]` = `0x801607F8`.

| Range | Region | Notes |
|-------|--------|-------|
| `0x801607F8` … `0x801B1C10` | LEVEL.DAT image (`0x51418`) | parsed in place |
| `0x801607F8 + 0x1504` = `0x80161CFC` | trail (pass-1) block | [[MEM - Trail and pass3 tables]] |
| `…+0x3AE8` / `…+0x3AEC` | pass-2 (empty) / pass-3 base | |
| `…+0x45F0` … `…+0x8BD8` | source-record band | reloc targets land here |
| `…+0x8BD8` … `…+0x4F32C` | payload band | [[MEM - fcn.80010000 mesh payload]] (Candidate A @ `+0x188CC`) |
| `0x801B1C10` … `0x801B5890` | pass-1 output records (484 × 0x20) | [[MEM - Parser output record]] |
| `0x801B5890` … `0x801B6A10` | reserved gap | (484+140)<<5 |

All **1248** baked relocation fields point inside `[+0x45F0, +0x4F32C]` (none in the records/tables) — the basis of relocation-aware append ([[Finding - Relocation-aware DAT append]]).

> Separately, LEVEL.RAW loads to `0x80115AAC` (compressed) and decompresses upward to `0x8015FCBC` — see [[MEM - LEVEL.RAW chunk model]]. The runtime address `0x801BDC58` lies in the LEVEL.RAW buffer, NOT the DAT — see [[Finding - 0x801bdc58 is compressed source]].

## Related
- Functions: [[FUNC_8001CDC0]] · [[FUNC_8003CF2C]] · [[FUNC_800224EC]]
- Structures: [[MEM - Type-0x3f placement record]] · [[MEM - Parser output record]] · [[MEM - Trail and pass3 tables]] · [[MEM - LEVEL.RAW chunk model]]
- Asset: [[Asset - LEVEL.DAT]] · System: [[LEVEL.DAT object pipeline]]


## Provenance

- Original note: `ObsidianVault/Memory Structures/MEM - DAT runtime memory map.md`
- Migration status: copy-first Canon seed.
