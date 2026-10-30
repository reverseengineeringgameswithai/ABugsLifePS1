---
kind: function
id: FUNC_8004C5D4
aliases:
- FUNC_8004C5D4
- '0x8004c5d4'
- vm_native_spawn_drop_burst
address: '0x8004c5d4'
name: vm_native_spawn_drop_burst
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- mover_vm_dispatch_next
- spawn_drop_burst_effect
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004C5D4 - vm_native_spawn_drop_burst

## Purpose
Mover-VM opcode: invokes spawn_drop_burst_effect on the actor, advances IP, returns to dispatch

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal spawn_drop_burst_effect 0x80057a94 (a0=s0); addiu s1,4; j mover_vm_dispatch_next 0x8004c818

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
