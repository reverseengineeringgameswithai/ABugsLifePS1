---
kind: function
id: FUNC_8004FC50
aliases:
- FUNC_8004FC50
- '0x8004fc50'
- scene_flow_set_substate_11
address: '0x8004fc50'
name: scene_flow_set_substate_11
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004FC50 - scene_flow_set_substate_11

## Purpose
Scene-flow jump-table handler setting the flow substate variable to 11, rejoins common continuation

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- sh 11 to 0x8008245c; tail j 0x8004fcc0; siblings 0x8004fc3c/64 write 1/2 to same global, share tail

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
