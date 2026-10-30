---
kind: function
id: FUNC_8004C604
aliases:
- FUNC_8004C604
- '0x8004c604'
- mover_vm_op_overlay_hook_b3b70
address: '0x8004c604'
name: mover_vm_op_overlay_hook_b3b70
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

# FUNC_8004C604 - mover_vm_op_overlay_hook_b3b70

## Purpose
Mover-VM opcode handler invoking the per-level overlay hook 0x800b3b70 then advancing the IP

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal overlay 0x800b3b70(a0=s0); addiu s1,s1,4; tail j mover_vm_dispatch_next 0x8004c818

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
