---
kind: function
id: FUNC_80014504
aliases:
- FUNC_80014504
- '0x80014504'
- build_render_survivor_list
address: '0x80014504'
name: build_render_survivor_list
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

# FUNC_80014504 - build_render_survivor_list

## Purpose
GTE-transforms an object array and appends visible ones to render_survivor_list (frustum/visibility cull)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- GTE RTPS/MVMVA transform of stride-20 object array a0, terminator lh+14
- writes visible record ptrs into render_survivor_list_a 0x80096ea8 after bounds tests; returns count

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
