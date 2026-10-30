---
kind: function
id: FUNC_8006250C
aliases:
- FUNC_8006250C
- '0x8006250c'
- handler_register_8007fbd4
address: '0x8006250c'
name: handler_register_8007fbd4
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
- src/main/8006250c_handler_register_8007fbd4.c
patch_policy: safe_to_read
---

# FUNC_8006250C - handler_register_8007fbd4

## Purpose
Standalone handler-register: stores s0 into 0x8007FBD4, returns previous value, optional callback

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- prologue/epilogue; if v0<2 call (*0x8007FBC4)(0x8001BF84,s0); reads old *0x8007FBD4, stores s0, returns old; SDK region near DrawSyncCallback

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
