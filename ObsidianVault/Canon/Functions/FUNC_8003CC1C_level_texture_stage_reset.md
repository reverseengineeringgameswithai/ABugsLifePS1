---
kind: function
id: FUNC_8003CC1C
aliases:
- FUNC_8003CC1C
- '0x8003cc1c'
- level_texture_stage_reset
address: '0x8003cc1c'
name: level_texture_stage_reset
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- level_texture_stage
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8003cc1c_level_texture_stage_reset.c
patch_policy: safe_to_read
---

# FUNC_8003CC1C - level_texture_stage_reset

## Purpose
Zeroes a 249-byte state buffer then invokes level_texture_stage (reset-then-stage initializer)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- memset 249 bytes descending from 0x8009fb40; then jal level_texture_stage 0x8003c8bc

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
