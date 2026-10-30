---
kind: function
id: FUNC_8004C634
aliases:
- FUNC_8004C634
- '0x8004c634'
- mover_vm_op_actor_flag_update
address: '0x8004c634'
name: mover_vm_op_actor_flag_update
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- actor_clear_motion_set_flag
- mover_vm_dispatch_next
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004C634 - mover_vm_op_actor_flag_update

## Purpose
Mover-VM opcode: updates actor +0x5c flags and +0x50 field via sub_80057c74, resumes dispatch

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- opcode case in event_bytecode_interpreter 0x8004c13c, tail j 0x8004c818
- calls sub_80057c74(actor): clears +0x5c bit 0x2, sets 0x80, writes (actor+8-0x4000)&~1 to +0x50

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
