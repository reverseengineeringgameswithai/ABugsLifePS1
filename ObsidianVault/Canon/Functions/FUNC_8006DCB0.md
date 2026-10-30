---
kind: function
id: FUNC_8006DCB0
aliases:
- FUNC_8006DCB0
- 2147933360
- '0x8006dcb0'
- CdGetSector
address: '0x8006dcb0'
name: CdGetSector
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_8006F3AC
reads: []
writes: []
evidence:
- EXP_2026-07-08_c_decompilation_campaign_v2
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/8006dcb0_CdGetSector.c
patch_policy: unknown
---

# FUNC_8006DCB0 - CdGetSector

## Status

**Byte-matched from C** (decomp substrate): `src/main/8006dcb0_CdGetSector.c` compiles to the exact original bytes at `0x8006dcb0` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8006dcb0`
- Matching source: `src/main/8006dcb0_CdGetSector.c`
- Callees: [[FUNC_8006F3AC]]

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
