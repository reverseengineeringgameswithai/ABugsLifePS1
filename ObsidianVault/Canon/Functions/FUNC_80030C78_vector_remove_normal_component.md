---
kind: function
id: FUNC_80030C78
aliases:
- FUNC_80030C78
- '0x80030c78'
- vector_remove_normal_component
address: '0x80030c78'
name: vector_remove_normal_component
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
- src/main/80030c78_vector_remove_normal_component.c
patch_policy: safe_to_read
---

# FUNC_80030C78 - vector_remove_normal_component

## Purpose
B - A*(A.B)*scale: subtracts B's component along normal A (wall-slide/velocity reject)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- negated dot(A,B), scale sra 11, out[i]=B[i]+(A[i]*dot)>>17; 3-short vectors to a2

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
