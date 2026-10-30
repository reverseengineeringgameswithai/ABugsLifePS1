---
kind: function
id: FUNC_80030B98
aliases:
- FUNC_80030B98
- '0x80030b98'
- vec3_project_point_onto_plane
address: '0x80030b98'
name: vec3_project_point_onto_plane
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
- src/main/80030b98_vec3_project_point_onto_plane.c
patch_policy: safe_to_read
---

# FUNC_80030B98 - vec3_project_point_onto_plane

## Purpose
Computes b - n*(n.b): projects point a1 onto the plane through origin with normal a0

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 3 halfwords a0 (normal), 3 words a1 negated; s=(a0.-a1)>>11; a2[i]=a1[i]+(a0[i]*s)>>17

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
