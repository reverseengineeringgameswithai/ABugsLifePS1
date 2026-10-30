---
kind: function
id: FUNC_8006C43C
aliases:
- FUNC_8006C43C
- '0x8006c43c'
- spu_malloc_body
address: '0x8006c43c'
name: spu_malloc_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _spu_gcSPU
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006C43C - spu_malloc_body

## Purpose
Body of SpuMalloc: SPU-RAM allocator that searches/reserves a free block

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- SpuMalloc @0x8006c434 loads init flag, falls through; body walks SPU malloc block table, aligns request, calls _spu_gcSPU to compact

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
