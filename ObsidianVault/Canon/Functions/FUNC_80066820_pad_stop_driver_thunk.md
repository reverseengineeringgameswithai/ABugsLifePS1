---
kind: function
id: FUNC_80066820
aliases:
- FUNC_80066820
- '0x80066820'
- pad_stop_driver_thunk
address: '0x80066820'
name: pad_stop_driver_thunk
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

# FUNC_80066820 - pad_stop_driver_thunk

## Purpose
Trampoline tail-jumping to the pad-driver fnptr 0x80086AAC during pad shutdown

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- lui t1,0x8008; lw t1,27308(t1)=0x80086AAC; jr t1; caller pad_subsystem_shutdown

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
