---
kind: function
id: FUNC_8004C614
aliases:
- FUNC_8004C614
- '0x8004c614'
- mover_vm_op_call_b3bd4
address: '0x8004c614'
name: mover_vm_op_call_b3bd4
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch03_clusters.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch03_clusters.json
patch_policy: safe_to_read
---

# FUNC_8004C614 - mover_vm_op_call_b3bd4

## Purpose
Mover-VM opcode handler calling overlay routine 0x800b3bd4 and capturing its result in VM state s3

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal 0x800b3bd4(a0=s0); s3=v0; tail j 0x8004c788; in the mover-VM opcode band off FUNC_8004c13c

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
