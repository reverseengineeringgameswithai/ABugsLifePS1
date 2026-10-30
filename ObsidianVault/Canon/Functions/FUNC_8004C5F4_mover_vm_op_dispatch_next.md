---
kind: function
id: FUNC_8004C5F4
aliases:
- FUNC_8004C5F4
- '0x8004c5f4'
- mover_vm_op_dispatch_next
address: '0x8004c5f4'
name: mover_vm_op_dispatch_next
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- mover_vm_dispatch_next
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch03_clusters.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch03_clusters.json
patch_policy: safe_to_read
---

# FUNC_8004C5F4 - mover_vm_op_dispatch_next

## Purpose
Mover-VM opcode handler: invokes the dispatch-next helper on the actor and advances the bytecode IP

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal mover_vm_dispatch_next(0x8004c818)(a0=s0); addiu s1,s1,4 (advance VM IP); tail j 0x8004c818
- in the mover-VM opcode-handler cluster off FUNC_8004c13c

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
