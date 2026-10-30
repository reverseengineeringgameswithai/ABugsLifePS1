---
kind: function
id: FUNC_8006DCF0
aliases:
- FUNC_8006DCF0
- 2147933424
- '0x8006dcf0'
- CdDataCallback
address: '0x8006dcf0'
name: CdDataCallback
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_80065434
reads: []
writes: []
evidence:
- EXP_2026-07-08_c_decompilation_campaign_v2
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/8006dcf0_CdDataCallback.c
patch_policy: unknown
---

# FUNC_8006DCF0 - CdDataCallback

## Status

**Byte-matched from C** (decomp substrate): `src/main/8006dcf0_CdDataCallback.c` compiles to the exact original bytes at `0x8006dcf0` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8006dcf0`
- Matching source: `src/main/8006dcf0_CdDataCallback.c`
- Callees: [[FUNC_80065434]]

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
