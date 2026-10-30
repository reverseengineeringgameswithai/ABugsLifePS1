---
kind: function
id: FUNC_8003A314
aliases:
- FUNC_8003A314
- '0x8003a314'
- high_heap_loader_entry
address: '0x8003a314'
name: high_heap_loader_entry
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

# FUNC_8003A314 - high_heap_loader_entry

## Purpose
gp-relative preload entry (gp+1556 -> v0) falling into high_heap_loader

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lw v0,1556(gp), no return; 3 callers; falls into high_heap_loader at 0x8003a318

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
