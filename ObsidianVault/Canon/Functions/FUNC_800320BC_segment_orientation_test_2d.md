---
kind: function
id: FUNC_800320BC
aliases:
- FUNC_800320BC
- '0x800320bc'
- segment_orientation_test_2d
address: '0x800320bc'
name: segment_orientation_test_2d
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
patch_policy: safe_to_read
---

# FUNC_800320BC - segment_orientation_test_2d

## Purpose
2D geometric orientation/edge-crossing predicate returning a boolean

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- three 2D coord pairs; axis-aligned special cases with +-5; cross-products via mult + signed div (break guards); returns 0/1 via slt

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
