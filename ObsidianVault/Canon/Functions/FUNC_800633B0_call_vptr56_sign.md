---
kind: function
id: FUNC_800633B0
aliases:
- FUNC_800633B0
- '0x800633b0'
- call_vptr56_sign
address: '0x800633b0'
name: call_vptr56_sign
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
- src/main/800633b0_call_vptr56_sign.c
patch_policy: safe_to_read
---

# FUNC_800633B0 - call_vptr56_sign

## Purpose
Standalone wrapper invoking method ptr at +0x38, returns result's sign bit

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- prologue/epilogue; loads fnptr [v0+56], jalr, returns v0>>31 (sign bit); between GetODE and SetTexWindow

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
