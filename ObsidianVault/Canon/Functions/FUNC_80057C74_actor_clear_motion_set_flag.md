---
kind: function
id: FUNC_80057C74
aliases:
- FUNC_80057C74
- '0x80057c74'
- actor_clear_motion_set_flag
address: '0x80057c74'
name: actor_clear_motion_set_flag
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
- src/main/80057c74_actor_clear_motion_set_flag.c
patch_policy: safe_to_read
---

# FUNC_80057C74 - actor_clear_motion_set_flag

## Purpose
Standalone leaf clearing a motion flag and setting flag 0x80 on the actor struct

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- leaf ending jr ra; sw v1,80(a0); clears actor +92 bit2, sets 0x80, masks word+8 to +80; called by mover_vm_op_actor_flag_update

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
