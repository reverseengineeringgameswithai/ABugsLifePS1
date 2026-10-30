---
kind: function
id: FUNC_800577DC
aliases:
- FUNC_800577DC
- '0x800577dc'
- contact_object_spawn_ring_entry
address: '0x800577dc'
name: contact_object_spawn_ring_entry
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

# FUNC_800577DC - contact_object_spawn_ring_entry

## Purpose
Alternate entry preloading byte 0x800910AA before contact_object_spawn_ring

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8B, no return; caller player_contact_response; lbu v1,0x800910AA; falls into contact_object_spawn_ring (0x800577e4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
