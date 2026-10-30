---
kind: function
id: FUNC_8004F478
aliases:
- FUNC_8004F478
- '0x8004f478'
- gameplay_frame_render_entry
address: '0x8004f478'
name: gameplay_frame_render_entry
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
patch_policy: safe_to_read
---

# FUNC_8004F478 - gameplay_frame_render_entry

## Purpose
Alternate entry preloading 0x800822B0 into v0, falling into gameplay_frame_render

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui v0,0x8008; lh v0,8880(v0)=0x800822B0, no return; falls through into gameplay_frame_render; called via jal by scene_flow_dispatcher

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
