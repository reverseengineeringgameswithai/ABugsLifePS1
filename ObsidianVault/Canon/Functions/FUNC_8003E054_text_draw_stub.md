---
kind: function
id: FUNC_8003E054
aliases:
- FUNC_8003E054
- '0x8003e054'
- text_draw_stub
address: '0x8003e054'
name: text_draw_stub
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
- src/main/8003e054_text_draw_stub.c
patch_policy: safe_to_read
---

# FUNC_8003E054 - text_draw_stub

## Purpose
Stubbed-out text-draw primitive (the disabled draw target of draw_string_centered)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- body addiu sp,-32/+32/jr ra (no-op); it is the tail-call target of draw_string_centered (0x8003e064)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
