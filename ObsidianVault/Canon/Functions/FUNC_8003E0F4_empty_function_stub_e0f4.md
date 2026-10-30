---
kind: function
id: FUNC_8003E0F4
aliases:
- FUNC_8003E0F4
- '0x8003e0f4'
- empty_function_stub_e0f4
address: '0x8003e0f4'
name: empty_function_stub_e0f4
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
- src/main/8003e0f4_empty_function_stub_e0f4.c
patch_policy: safe_to_read
---

# FUNC_8003E0F4 - empty_function_stub_e0f4

## Purpose
A compiler-emitted no-op function (does nothing observable)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body addiu sp,-16/addiu sp,+16/jr ra/nop; no memory access, no callees

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
