---
kind: function
id: FUNC_8005EC1C
aliases:
- FUNC_8005EC1C
- '0x8005ec1c'
- angle_delta_wrap
address: '0x8005ec1c'
name: angle_delta_wrap
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8005ec1c_angle_delta_wrap.c
patch_policy: safe_to_read
---

# FUNC_8005EC1C - angle_delta_wrap

## Purpose
Shortest signed angular difference in a 4096-unit circle, wrapped to ±half-turn

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- v1=[a1]-[a0]; mod 4096; clamp to (-2048,2048]; sign-extend

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
