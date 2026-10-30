---
kind: function
id: FUNC_8006540C
aliases:
- FUNC_8006540C
- '0x8006540c'
- InterruptCallback_dispatch_tail
address: '0x8006540c'
name: InterruptCallback_dispatch_tail
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
- src/main/8006540c_InterruptCallback_dispatch_tail.c
patch_policy: safe_to_read
---

# FUNC_8006540C - InterruptCallback_dispatch_tail

## Purpose
Body of libapi InterruptCallback; dispatches kernel callback-table slot +8

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- InterruptCallback @0x80065404 loads table ptr, falls through; body lw v0,8(v0); jalr v0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
