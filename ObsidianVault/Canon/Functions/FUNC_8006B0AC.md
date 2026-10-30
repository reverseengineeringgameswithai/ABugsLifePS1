---
kind: function
id: FUNC_8006B0AC
aliases:
- FUNC_8006B0AC
- '0x8006b0ac'
- SsVabClose
address: '0x8006b0ac'
name: SsVabClose
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
- src/main/8006b0ac_SsVabClose.c
patch_policy: unknown
---

# FUNC_8006B0AC - SsVabClose

## Status

**Byte-matched from C** (decomp substrate): `src/main/8006b0ac_SsVabClose.c` compiles to the exact original bytes at `0x8006b0ac` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8006b0ac`
- Matching source: `src/main/8006b0ac_SsVabClose.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
