---
kind: function
id: FUNC_80031EFC
aliases:
- FUNC_80031EFC
- '0x80031efc'
- point_edge_crossing_test
address: '0x80031efc'
name: point_edge_crossing_test
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

# FUNC_80031EFC - point_edge_crossing_test

## Purpose
2D geometric predicate over a point and edge A-B (edge-crossing/side test), returns boolean

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- three coord pairs (a0,a1),(a2,a3),(sp+16,sp+20); axis-aligned special cases; cross-products via mult + signed div
- single boolean return 0/1

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
