---
kind: function
id: FUNC_80061CDC
aliases:
- FUNC_80061CDC
- 2147884252
- '0x80061cdc'
- SetPolyFT4
address: '0x80061cdc'
name: SetPolyFT4
status: byte_matched
confidence: confirmed
source_state: original_game
calls: []
reads: []
writes: []
evidence:
- EXP_2026-07-08_c_decompilation_campaign_v2
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/80061cdc_SetPolyFT4.c
patch_policy: unknown
---

# FUNC_80061CDC - SetPolyFT4

## Status

**Byte-matched from C** (decomp substrate): `src/main/80061cdc_SetPolyFT4.c` compiles to the exact original bytes at `0x80061cdc` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80061cdc`
- Matching source: `src/main/80061cdc_SetPolyFT4.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
