---
kind: function
id: FUNC_80014724
aliases:
- FUNC_80014724
- '0x80014724'
- gte_mvmva_ir_transform
address: '0x80014724'
name: gte_mvmva_ir_transform
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80014724 - gte_mvmva_ir_transform

## Purpose
Loads a vector into GTE IR, runs MVMVA matrix-vector multiply, writes MAC1-3 to output (GTE transform helper)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- LWC2 load 0/4/8(a0) into cop2 IR1/IR2/IR3; GTE cmd 0x4a4ba012 func 0x12 = MVMVA; SWC2 store MAC1-3 to a1

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
