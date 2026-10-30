---
kind: function
id: FUNC_8005B4E4
aliases:
- FUNC_8005B4E4
- '0x8005b4e4'
- sub_8005b4ec_entry
address: '0x8005b4e4'
name: sub_8005b4ec_entry
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

# FUNC_8005B4E4 - sub_8005b4ec_entry

## Purpose
Alternate entry preloading 0x8009EDCC into v0, falling into sub_8005b4ec

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui v0,0x800a; lw v0,-4660(v0)=0x8009EDCC, no return; 2 callers; falls into sub_8005b4ec

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
