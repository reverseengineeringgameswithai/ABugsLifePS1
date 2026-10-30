---
kind: function
id: FUNC_80060634
aliases:
- FUNC_80060634
- '0x80060634'
- gte_control_reg26_set
address: '0x80060634'
name: gte_control_reg26_set
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80060634 - gte_control_reg26_set

## Purpose
Writes its argument into GTE control register 26 during boot init

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Single COP2 instr 0x48c4d000 = ctc2 a0,cop2_control_reg26 then jr ra
- Caller boot_subsystem_init

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
