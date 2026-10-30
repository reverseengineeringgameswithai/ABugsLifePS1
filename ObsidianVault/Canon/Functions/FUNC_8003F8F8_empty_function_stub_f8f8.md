---
kind: function
id: FUNC_8003F8F8
aliases:
- FUNC_8003F8F8
- '0x8003f8f8'
- empty_function_stub_f8f8
address: '0x8003f8f8'
name: empty_function_stub_f8f8
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
- src/main/8003f8f8_empty_function_stub_f8f8.c
patch_policy: safe_to_read
---

# FUNC_8003F8F8 - empty_function_stub_f8f8

## Purpose
Compiler-emitted no-op function (stubbed-out routine)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body: addiu sp,-80; addiu sp,+80; jr ra; nop — no work

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
