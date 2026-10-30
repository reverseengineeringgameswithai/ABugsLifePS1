---
kind: function
id: FUNC_8002FC90
aliases:
- FUNC_8002FC90
- '0x8002fc90'
- gpu_gt_prim_list_advance
address: '0x8002fc90'
name: gpu_gt_prim_list_advance
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
- src/main/8002fc90_gpu_gt_prim_list_advance.c
patch_policy: safe_to_read
---

# FUNC_8002FC90 - gpu_gt_prim_list_advance

## Purpose
Walks a chained GPU primitive packet buffer stepping by each primitive's decoded size, returns end-of-list pointer

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- reads code byte [a0+3] &0x7c; 0x34 POLY_GT3 -> +36, 0x3c POLY_GT4 -> +48; loops until code==0; returns a0+4 past terminator

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
