---
kind: function
id: FUNC_80014AD4
aliases:
- FUNC_80014AD4
- '0x80014ad4'
- gte_vec_length_sqrt_helper
address: '0x80014ad4'
name: gte_vec_length_sqrt_helper
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

# FUNC_80014AD4 - gte_vec_length_sqrt_helper

## Purpose
Standalone GTE vector-length helper that sums components and tail-calls SquareRoot0

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 48B, called by vec_normalize_len; sets COP2/GTE regs; lui t0,0x8006; ori t0,0x154; jr t0 -> tail-calls SquareRoot0 (0x80060154); sums components in delay slots

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
