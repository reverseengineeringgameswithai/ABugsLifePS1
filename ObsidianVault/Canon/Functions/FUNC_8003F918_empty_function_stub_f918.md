---
kind: function
id: FUNC_8003F918
aliases:
- FUNC_8003F918
- '0x8003f918'
- empty_function_stub_f918
address: '0x8003f918'
name: empty_function_stub_f918
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
- src/main/8003f918_empty_function_stub_f918.c
patch_policy: safe_to_read
---

# FUNC_8003F918 - empty_function_stub_f918

## Purpose
Compiler-emitted no-op function

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body: addiu sp,-32; addiu sp,+32; jr ra; nop

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
