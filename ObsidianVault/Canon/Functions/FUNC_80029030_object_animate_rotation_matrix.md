---
kind: function
id: FUNC_80029030
aliases:
- FUNC_80029030
- '0x80029030'
- object_animate_rotation_matrix
address: '0x80029030'
name: object_animate_rotation_matrix
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- gte_rotation_matrix_setup
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80029030 - object_animate_rotation_matrix

## Purpose
Per-object: scales stored rotation params by angle args, builds GTE rotation, transforms object 3x3 orientation

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- indexes table 0x80091210 by a0*16, rotation params (lh 4624/26/28) * a1/a2/a3 >>12
- stores to struct+18/20/22, gte_rotation_matrix_setup(struct+12,s0), applies to 3x3 matrix

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
