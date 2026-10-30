---
kind: function
id: FUNC_8006F5B4
aliases:
- FUNC_8006F5B4
- '0x8006f5b4'
- cd_interrupt_callback_body
address: '0x8006f5b4'
name: cd_interrupt_callback_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- getintr
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006F5B4 - cd_interrupt_callback_body

## Purpose
Body of the libcd interrupt callback dispatcher: polls CD interrupt status and invokes the registered ready/complete callbacks

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- callback @0x8006f5ac loads a global, falls through; body loops getintr, tests bits 4/2, dispatches ready(INT1)/complete(INT2) fnptrs; libcd region

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
