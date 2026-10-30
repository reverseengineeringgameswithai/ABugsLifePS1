---
kind: function
id: FUNC_80054AAC
aliases:
- FUNC_80054AAC
- 2147830444
- '0x80054aac'
- store_four_bytes
address: '0x80054aac'
name: ''
status: byte_matched
confidence: confirmed
source_state: original_game
calls: []
reads: []
writes: []
evidence:
- EXP_2026-07-08_c_decompilation_campaign_v1
- EXP_2026-07-10_c_conversion_at_scale
src_paths:
- src/main/80054aac_store4_bytes.c
patch_policy: unknown
---

# FUNC_80054AAC - FUNC_80054AAC

## Status

**Byte-matched from C** (decomp substrate): `src/main/80054aac_store4_bytes.c` compiles to the exact original bytes at `0x80054aac` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80054aac`
- Matching source: `src/main/80054aac_store4_bytes.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
