---
kind: function
id: FUNC_8004C5E4
aliases:
- FUNC_8004C5E4
- '0x8004c5e4'
- mover_vm_op_spawn_burst_ring
address: '0x8004c5e4'
name: mover_vm_op_spawn_burst_ring
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- mover_vm_dispatch_next
- spawn_object_burst_ring
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004C5E4 - mover_vm_op_spawn_burst_ring

## Purpose
mover-VM opcode: spawn burst ring around actor, advance IP, return to dispatcher

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- calls spawn_object_burst_ring(s0); addiu s1,s1,4 (IP advance); tail j mover_vm_dispatch_next 0x8004c818

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
