---
kind: function
id: FUNC_800457DC
aliases:
- FUNC_800457DC
- '0x800457dc'
- noop_return_stub_800457dc
address: '0x800457dc'
name: noop_return_stub_800457dc
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
- src/main/800457dc_noop_return_stub_800457dc.c
patch_policy: safe_to_read
---

# FUNC_800457DC - noop_return_stub_800457dc

## Purpose
Self-contained 8-byte return-only leaf stub

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body jr ra; nop; preceding 0x8004574c ends with its own jr ra; next 0x800457e4 has a full prologue

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
