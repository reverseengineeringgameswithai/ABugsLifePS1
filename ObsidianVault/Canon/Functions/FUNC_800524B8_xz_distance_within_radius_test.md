---
kind: function
id: FUNC_800524B8
aliases:
- FUNC_800524B8
- '0x800524b8'
- xz_distance_within_radius_test
address: '0x800524b8'
name: xz_distance_within_radius_test
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
- src/main/800524b8_xz_distance_within_radius_test.c
patch_policy: safe_to_read
---

# FUNC_800524B8 - xz_distance_within_radius_test

## Purpose
2D (XZ) squared-distance-within-radius boolean test

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller seed_plant_propeller_handler
- Computes ((a0[0]-a1[0])>>8)^2 + ((a0[8]-a1[8])>>8)^2 and a2*a2; returns slt(distSq,a2Sq)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
