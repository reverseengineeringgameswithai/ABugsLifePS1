---
kind: function
id: FUNC_800602C4
aliases:
- FUNC_800602C4
- '0x800602c4'
- gte_svector_store_wrapper
address: '0x800602c4'
name: gte_svector_store_wrapper
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- MSC02_OBJ_FC
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
patch_policy: safe_to_read
---

# FUNC_800602C4 - gte_svector_store_wrapper

## Purpose
Standalone leaf wrapper calling MSC02_OBJ_FC and storing its 3-halfword vector result

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jr ra; jal MSC02_OBJ_FC (0x800602e0); addu ra,a3,zero; sh t0/t1/t2 to a1[0/1/2] (SVECTOR result)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
