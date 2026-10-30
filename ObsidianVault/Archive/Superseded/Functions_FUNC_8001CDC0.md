---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8001CDC0.md
aliases: []
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8001CDC0.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8001CDC0_DAT_parser_-_relocator.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8001CDC0 — DAT parser / relocator
type: function
address: 0x8001CDC0
confidence: CONFIRMED
tags: [function, dat, parser, relocation]
---
# FUNC_8001CDC0 — LEVEL.DAT parser / relocator

> Parses a loaded LEVEL.DAT and relocates its baked file-offset pointers (3 passes), rebuilding the dynamic type-pointer table. The gateway of the whole object/geometry pipeline.

| Field | Value |
|-------|-------|
| Address | 0x8001CDC0 (size 1548 B, …0x8001D3CC) |
| Source file | `src_re/dat_parser_8001cdc0.c` (`dat_parse_relocate`); annotated in `src_re_geometry/dat_geometry_records.c` |
| Confidence | CONFIRMED (control flow + all 9 reloc sites verified vs `tools/dat_reloc.py`: 968 pass1 + 0 pass2 + 280 pass3 = 1248) |

## Purpose
Relocates internal baked absolute file offsets: `runtime_ptr = DATbase + baked_file_offset` where `DATbase = [0x80082498]`. Runs 3 relocation passes (stride 0x14 / stride 4 / stride 0x14) and writes 0x20-byte output records (a 3×3 rotation matrix per pass-1 entry; the bit3 path also scales the matrix). Rebuilds the dynamic type table `0x80096da0` (`slot = type*4`); the type-0x3f pointer ends up at `0x80096e9c`. **Runs exactly once per DAT load** (LEVEL01 `a1=0x51418`).

## Arguments / Returns
`a0` = path/scratch (IGNORED, overwritten); `a1` = output-buffer byte offset (added to DATbase). Returns the number of output bytes = `(pass1+pass3 entries) << 5`; the caller advances its heap cursor by this.

## Calls (callees)
- [[FUNC_80017B98]] — GTE rotation-matrix setup (fills the output-record matrices; relocates nothing).
- `fcn.8003eec8` — parser epilogue finalize (a0 = 0/1).

## Called by (callers)
- [[FUNC_8003CF2C]] @ `0x8003d568` — the resource/DAT-load caller (sole call site).

## Globals & structures touched
- `0x80082498` DATbase · `0x80096da0` type table · `0x80096e9c` type-0x3f ptr · `0x800822f0` entry counter · trail `0x800824ac` · pass-3 `0x80082508`.
- Structures: [[MEM - Type-0x3f placement record]], [[MEM - Parser output record]], [[MEM - Trail and pass3 tables]], and the two source-record formats — see [[Finding - Two parser source-record formats]].

## Evidence & confidence notes
All 1248 relocation sites (484 `[s3+2]` + 174 non-bit3 `[s0+0x14]` + 310 bit3 `[s0+0x1c]` pass-1; 140+85+55 pass-3) verified against the offline reloc engine. Flag bit 0x20 (extra-reloc) never set in LEVEL01. The stale-offset failure mode is the root cause of the naive-append black screen — see [[Finding - Relocation-aware DAT append]].

## Related
- Findings: [[Finding - Relocation-aware DAT append]] · [[Finding - Type-0x3f pickups are coordinate-moddable]] · [[Finding - Two parser source-record formats]]
- Functions: [[FUNC_8003CF2C]] · [[FUNC_80046330]] · [[FUNC_80053814]] · [[FUNC_80017B98]]
- Assets: [[Asset - LEVEL.DAT]] · System: [[LEVEL.DAT object pipeline]]
- Source docs: `src_re/dat_parser_8001cdc0.c`, `docs/DAT_FORMAT_AND_RELOCATION.md`
