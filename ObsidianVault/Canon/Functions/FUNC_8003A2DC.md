---
kind: function
id: FUNC_8003A2DC
address: '0x8003a2dc'
name: controller_input_latch_update
status: byte_matched
confidence: confirmed
source_state: original_game
calls:
- FUNC_80039C34
reads: []
writes: []
evidence:
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/8003a2dc_controller_input_latch_update.c
patch_policy: unknown
aliases:
- FUNC_8003A2DC
- '0x8003a2dc'
- controller_input_latch_update
---

# FUNC_8003A2DC - controller_input_latch_update

## Status

**Byte-matched from C** (decomp substrate): `src/main/8003a2dc_controller_input_latch_update.c` compiles to the exact original bytes at `0x8003a2dc` (config/segments.yml `attempted`; `validate_build.py` SHA-1 PASS). This note is Canon original-game truth for the function's *bytes*; higher-level purpose is refined separately.

## Identity

- Address: `0x8003a2dc`
- Matching source: `src/main/8003a2dc_controller_input_latch_update.c`
- Callees: FUNC_80039C34

## Behavior

See the matching C source; field/global meanings are address-anchored (no invented semantics) unless linked to a `MEM_*` note.
