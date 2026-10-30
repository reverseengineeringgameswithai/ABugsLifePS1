---
kind: function
id: FUNC_80030AAC
aliases:
- FUNC_80030AAC
- '0x80030aac'
- vec3_reject_normal_component
address: '0x80030aac'
name: vec3_reject_normal_component
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
- src/main/80030aac_vec3_reject_normal_component.c
patch_policy: safe_to_read
---

# FUNC_80030AAC - vec3_reject_normal_component

## Purpose
Removes the a0-normal component from vector a1 (slide/project onto plane), output a2

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- dot(a0,a1) over 3 halfword lanes, sra 10; out[i]=a1[i]+a0[i]*(-dot)>>17 to a2 (3 halfwords)
- no callees

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
