---
kind: function
id: FUNC_80039124
aliases:
- FUNC_80039124
- '0x80039124'
- noop_return_stub_80039124
address: '0x80039124'
name: noop_return_stub_80039124
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
- src/main/80039124_noop_return_stub_80039124.c
patch_policy: safe_to_read
---

# FUNC_80039124 - noop_return_stub_80039124

## Purpose
Standalone return-only no-op stub

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body is exactly jr ra; nop; preceding sub_800390f0 has its own complete epilogue; next display_env_setup has its own prologue

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
