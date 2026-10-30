---
kind: function
id: FUNC_80050EE4
aliases:
- FUNC_80050EE4
- '0x80050ee4'
- sfx_nearest_pickup_gp_entry
address: '0x80050ee4'
name: sfx_nearest_pickup_gp_entry
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

# FUNC_80050EE4 - sfx_nearest_pickup_gp_entry

## Purpose
Alternate entry preloading v0=gp+1716 before sfx_nearest_pickup_f_glue_0ee8

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- single lw v0,1716(gp), no return; falls into sfx_nearest_pickup_f_glue_0ee8 (0x80050ee8)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
