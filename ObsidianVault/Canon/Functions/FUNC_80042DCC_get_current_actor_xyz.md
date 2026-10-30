---
kind: function
id: FUNC_80042DCC
aliases:
- FUNC_80042DCC
- '0x80042dcc'
- get_current_actor_xyz
address: '0x80042dcc'
name: get_current_actor_xyz
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
- src/main/80042dcc_get_current_actor_xyz.c
patch_policy: safe_to_read
---

# FUNC_80042DCC - get_current_actor_xyz

## Purpose
Returns XYZ of the current (count-1) slot of an 836-byte-stride array via output pointers

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller actor_skinned_update; leaf
- reads count at 0x800A6580, (count-1) indexes stride-836 array, reads words +0/4/8, stores to *a0/*a1/*a2; blez guard when count<=0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
