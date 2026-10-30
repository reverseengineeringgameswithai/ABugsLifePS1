---
kind: function
id: FUNC_800292DC
aliases:
- FUNC_800292DC
- '0x800292dc'
- object_rotation_matrix_apply
address: '0x800292dc'
name: object_rotation_matrix_apply
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

# FUNC_800292DC - object_rotation_matrix_apply

## Purpose
Sets object orientation (base angle + deltas), builds rotation matrix, rotates its vector set

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- indexes object table gp+1440 by a0<<2, base angles from 0x80094000 region + a1/a2/a3
- calls gte_rotation_matrix_setup 0x80017b98; applies matrix (mult;sra12) writing rotated components

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
