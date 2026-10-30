---
kind: function
id: FUNC_8003E4E0
aliases:
- FUNC_8003E4E0
- '0x8003e4e0'
- sub_8003e4e8_entry
address: '0x8003e4e0'
name: sub_8003e4e8_entry
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

# FUNC_8003E4E0 - sub_8003e4e8_entry

## Purpose
Alternate entry preloading 0x80082504 into v0, falling into sub_8003e4e8

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui v0,0x8008; lw v0,9476(v0)=0x80082504, no return; falls into sub_8003e4e8 whose first branch tests v0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
