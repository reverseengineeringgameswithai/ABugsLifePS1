---
kind: function
id: FUNC_80061AFC
aliases:
- FUNC_80061AFC
- '0x80061afc'
- DumpClut
address: '0x80061afc'
name: DumpClut
status: byte_matched
confidence: confirmed
source_state: original_game
calls: []
reads: []
writes: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/80061afc_DumpClut.c
patch_policy: unknown
---

# FUNC_80061AFC - DumpClut

## Status

**Byte-matched from C** (decomp substrate): `src/main/80061afc_DumpClut.c` compiles to the exact original bytes at `0x80061afc` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80061afc`
- Matching source: `src/main/80061afc_DumpClut.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
