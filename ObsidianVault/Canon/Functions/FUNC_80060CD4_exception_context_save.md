---
kind: function
id: FUNC_80060CD4
aliases:
- FUNC_80060CD4
- '0x80060cd4'
- exception_context_save
address: '0x80060cd4'
name: exception_context_save
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

# FUNC_80060CD4 - exception_context_save

## Purpose
Low-level exception-handler entry saving registers into the current TCB context

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- uses k0, reads kernel table [0x100]/[0x108], stores at/v0/v1/ra into +8 context block, mfc0; reached via exception vector not jal; PsyQ/kernel region

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
