---
kind: function
id: FUNC_8006680C
aliases:
- FUNC_8006680C
- '0x8006680c'
- call_via_ptr_80086aa8
address: '0x8006680c'
name: call_via_ptr_80086aa8
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

# FUNC_8006680C - call_via_ptr_80086aa8

## Purpose
Indirect-call thunk dispatching through the function pointer at 0x80086AA8

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui t1,0x8008; lw t1,27304(t1)=0x80086AA8; jr t1; called by pad_subsystem_init_65e8

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
