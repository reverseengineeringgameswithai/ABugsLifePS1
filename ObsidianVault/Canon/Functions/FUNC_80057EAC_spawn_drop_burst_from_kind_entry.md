---
kind: function
id: FUNC_80057EAC
aliases:
- FUNC_80057EAC
- '0x80057eac'
- spawn_drop_burst_from_kind_entry
address: '0x80057eac'
name: spawn_drop_burst_from_kind_entry
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

# FUNC_80057EAC - spawn_drop_burst_from_kind_entry

## Purpose
Alternate entry preloading 0x800822F4 before spawn_drop_burst_from_kind

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8B, no return; lw v1,0x800822F4; falls into spawn_drop_burst_from_kind (0x80057eb4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
