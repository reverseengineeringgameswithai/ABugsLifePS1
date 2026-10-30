---
kind: function
id: FUNC_8005B12C
aliases:
- FUNC_8005B12C
- '0x8005b12c'
- respawn_transition_state_handler_entry
address: '0x8005b12c'
name: respawn_transition_state_handler_entry
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

# FUNC_8005B12C - respawn_transition_state_handler_entry

## Purpose
Alternate entry preloading current_scene_id before respawn_transition_state_handler

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8B, no return; caller scene_flow_dispatcher; lw v0,0x80082504 (current_scene_id); falls into respawn_transition_state_handler (0x8005b134)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
