---
kind: function
id: FUNC_8004FC64
aliases:
- FUNC_8004FC64
- '0x8004fc64'
- scene_flow_set_substate_2
address: '0x8004fc64'
name: scene_flow_set_substate_2
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch03_clusters.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch03_clusters.json
patch_policy: safe_to_read
---

# FUNC_8004FC64 - scene_flow_set_substate_2

## Purpose
Jump-table handler setting the scene-flow substate global 0x8008245c to 2

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- addiu v0,2; sh v0,0x8008245c; j 0x8004fcc0; sibling of scene_flow_set_substate_11

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
