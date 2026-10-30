---
kind: function
id: FUNC_80055414
aliases:
- FUNC_80055414
- '0x80055414'
- scene_flow_state_table_init
address: '0x80055414'
name: scene_flow_state_table_init
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80055414_scene_flow_state_table_init.c
patch_policy: safe_to_read
---

# FUNC_80055414 - scene_flow_state_table_init

## Purpose
Initializes a scene-flow struct with default 64-entry 5-byte record table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Writes header {5,1} at a0+0/+1, clears 19 bytes at a0+2
- Fills 64 five-byte records at a0+28 with {0x64,0xFF,0xFF,0xFF,0xFF}
- sole caller scene_flow_dispatcher

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
