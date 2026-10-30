---
kind: function
id: FUNC_8006CCAC
aliases:
- FUNC_8006CCAC
- '0x8006ccac'
- SpuRead
address: '0x8006ccac'
name: SpuRead
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
- src/main/8006ccac_SpuRead.c
patch_policy: unknown
---

# FUNC_8006CCAC - SpuRead

## Status

**Byte-matched from C** (decomp substrate): `src/main/8006ccac_SpuRead.c` compiles to the exact original bytes at `0x8006ccac` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8006ccac`
- Matching source: `src/main/8006ccac_SpuRead.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
