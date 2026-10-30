---
kind: function
id: FUNC_8004AA34
aliases:
- FUNC_8004AA34
- '0x8004aa34'
- actor_transform_anim_vertex_emit
address: '0x8004aa34'
name: actor_transform_anim_vertex_emit
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- empty_function_stub_f8f8
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004AA34 - actor_transform_anim_vertex_emit

## Purpose
Yaw-rotates an animation-frame vertex+normal to world space and hands it to a draw/emit helper

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- actor+68 frame idx + actor+116 vertex base -> 16-byte frame record; cos/sin table 0x80074970 by actor+20 yaw
- rotates local vertex + actor pos -> world XYZ; clamps normal; passes to sub_8003f8f8

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
