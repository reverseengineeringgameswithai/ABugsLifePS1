---
kind: function
id: FUNC_80061DEC
aliases:
- FUNC_80061DEC
- 2147884524
- '0x80061dec'
- SetLineG3
address: '0x80061dec'
name: SetLineG3
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
- src/main/80061dec_SetLineG3.c
patch_policy: unknown
---

# FUNC_80061DEC - SetLineG3

## Status

**Byte-matched from C** (decomp substrate): `src/main/80061dec_SetLineG3.c` compiles to the exact original bytes at `0x80061dec` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x80061dec`
- Matching source: `src/main/80061dec_SetLineG3.c`
- Callees: none (leaf)

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
