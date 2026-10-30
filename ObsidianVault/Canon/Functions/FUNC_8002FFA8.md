---
kind: function
id: FUNC_8002FFA8
address: '0x8002ffa8'
name: load_named_file
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_8002FCE8
- FUNC_80046330
- FUNC_8005F74C
- FUNC_8005F76C
reads: []
writes: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/8002ffa8_load_named_file.c
patch_policy: unknown
aliases:
- FUNC_8002FFA8
- '0x8002ffa8'
- load_named_file
---

# FUNC_8002FFA8 - load_named_file

## Status

**Byte-matched from C** (decomp substrate): `src/main/8002ffa8_load_named_file.c` compiles to the exact original bytes at `0x8002ffa8` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8002ffa8`
- Matching source: `src/main/8002ffa8_load_named_file.c`
- Callees: [[FUNC_8002FCE8]], [[FUNC_80046330]], FUNC_8005F74C, FUNC_8005F76C

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
