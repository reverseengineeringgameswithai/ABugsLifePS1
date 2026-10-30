---
kind: function
id: FUNC_80029578
aliases:
- FUNC_80029578
- '0x80029578'
- gp_state_clear_three_shorts
address: '0x80029578'
name: gp_state_clear_three_shorts
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80029578_gp_state_clear_three_shorts.c
patch_policy: safe_to_read
---

# FUNC_80029578 - gp_state_clear_three_shorts

## Purpose
Zeroes three gp-relative halfword state globals at level load

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 20-byte leaf: sh $zero to gp+1280, gp+1272, gp+1866 then jr ra
- sole caller level_load_chunks

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
