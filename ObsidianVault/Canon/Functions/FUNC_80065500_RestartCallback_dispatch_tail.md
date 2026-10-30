---
kind: function
id: FUNC_80065500
aliases:
- FUNC_80065500
- '0x80065500'
- RestartCallback_dispatch_tail
address: '0x80065500'
name: RestartCallback_dispatch_tail
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
- src/main/80065500_RestartCallback_dispatch_tail.c
patch_policy: safe_to_read
---

# FUNC_80065500 - RestartCallback_dispatch_tail

## Purpose
Body of libapi RestartCallback; dispatches kernel callback-table slot +0x18

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- RestartCallback @0x800654f8 loads table ptr, falls through; body lw v0,24(v0); jalr v0 (slot +0x18)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
