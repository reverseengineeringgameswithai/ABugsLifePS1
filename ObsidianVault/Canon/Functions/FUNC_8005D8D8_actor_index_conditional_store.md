---
kind: function
id: FUNC_8005D8D8
aliases:
- FUNC_8005D8D8
- '0x8005d8d8'
- actor_index_conditional_store
address: '0x8005d8d8'
name: actor_index_conditional_store
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
- src/main/8005d8d8_actor_index_conditional_store.c
patch_policy: safe_to_read
---

# FUNC_8005D8D8 - actor_index_conditional_store

## Purpose
Standalone leaf: index-gated conditional store into an actor/slot table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- leaf jr ra; indexes 0x800A6300 by a1<<2, compares entry+2 vs a2, conditionally writes word+8

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
