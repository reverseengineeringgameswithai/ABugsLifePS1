---
kind: function
id: FUNC_8004C624
aliases:
- FUNC_8004C624
- '0x8004c624'
- mover_vm_op_call_advance
address: '0x8004c624'
name: mover_vm_op_call_advance
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
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

# FUNC_8004C624 - mover_vm_op_call_advance

## Purpose
mover-VM opcode handler: invoke overlay routine, step bytecode ptr, chain to dispatcher

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal overlay 0x800b3dc8(a0=actor); addiu s1,s1,4 (advance IP); tail j 0x8004c818 mover_vm_dispatch_next

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
