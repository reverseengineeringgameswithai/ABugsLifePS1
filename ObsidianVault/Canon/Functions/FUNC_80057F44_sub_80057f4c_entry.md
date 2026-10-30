---
kind: function
id: FUNC_80057F44
aliases:
- FUNC_80057F44
- '0x80057f44'
- sub_80057f4c_entry
address: '0x80057f44'
name: sub_80057f4c_entry
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

# FUNC_80057F44 - sub_80057f4c_entry

## Purpose
Alternate entry preloading 0x800822F4 into v0, falling into sub_80057f4c

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui v0,0x8008; lw v0,8948(v0)=0x800822F4, no return; falls through into sub_80057f4c; called by contact_vs_actor_handler, proximity_updater

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
