---
kind: function
id: FUNC_80050EA0
aliases: [FUNC_80050EA0, 0x80050ea0, sub_80050ea8_entry]
address: 0x80050ea0
name: sub_80050ea8_entry
status: static_seen
confidence: confirmed
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

# FUNC_80050EA0 - sub_80050ea8_entry

## Purpose
Alternate entry preloading a0=0x80082370, falling into sub_80050ea8

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui a0,0x8008; lw a0,9072(a0)=0x80082370, no return; falls into sub_80050ea8 which uses preloaded a0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
