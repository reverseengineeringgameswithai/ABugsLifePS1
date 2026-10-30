---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Functions/FUNC_8003CF2C.md
aliases: []
migration_action: convert_to_canon
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Functions/FUNC_8003CF2C.md`
- Replacement/current location: `ObsidianVault/Canon/Functions/FUNC_8003CF2C_resource-ID_dispatcher_-_DAT-load_caller.md`
- Archive reason: Existing function note; migrate only evidence-backed claims and link C source where available.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: FUNC_8003CF2C — resource-ID dispatcher / DAT-load caller
type: function
address: 0x8003CF2C
confidence: CONFIRMED
tags: [function, loader, dat]
---
# FUNC_8003CF2C — resource-ID dispatcher / DAT-load caller

> Resolves a resource id to a file, loads it, and (for DAT resources) sets DATbase and invokes the parser. The function that makes LEVEL.DAT resident.

| Field | Value |
|-------|-------|
| Address | 0x8003CF2C (parser call site `0x8003d568`) |
| Source file | disasm (G3/G19/G20); `geometry_runtime_buffers.c` |
| Confidence | CONFIRMED caller flow |

## Purpose
Resource-ID dispatcher via jump table `0x8001afb0` (17 handlers, 4 callers `0x8003f544 / 0x800503cc / 0x80052290 / 0x8005b830`). For a DAT resource it sets `DATbase = heap cursor [sp+0x98]` (`0x8003d4ac`), reads the file via [[FUNC_80046330]] (a0=path, a1=DATbase), calls the parser [[FUNC_8001CDC0]] with `a1=filesize`, then advances the heap cursor by the parser's return value. Confirms the parser runs once per DAT load.

## Arguments / Returns
Resource id (dispatched). Effect: DAT image resident at DATbase (LEVEL01 `0x801607f8`), parser output appended after it.

## Calls (callees)
- [[FUNC_80046330]] — universal file loader (file read `0x8003d550`).
- [[FUNC_8001CDC0]] — DAT parser (`0x8003d568`).

## Called by (callers)
- 4 callers: `0x8003f544 / 0x800503cc / 0x80052290 / 0x8005b830`.

## Globals & structures touched
- `0x80082498` DATbase. See [[MEM - DAT runtime memory map]].

## Evidence & confidence notes
G20 operator EXEC at `0x8003d550`/`0x8003d568` each hit ONCE for LEVEL01 (`a1=0x51418`) → parser runs exactly once (refuted the "second parsed DAT = floor" hypothesis).

## Related
- Findings: [[Finding - Floor resource is LEVEL.RAW]] (this loader path led there)
- Functions: [[FUNC_8001CDC0]] · [[FUNC_80046330]] · [[FUNC_8003A318]]
- Source docs: `src_re_geometry/geometry_g20_sidecar_loader_trace.md`, `docs/EXECUTABLE_AND_OVERLAYS.md`
