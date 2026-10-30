---
kind: function
id: FUNC_8004C644
aliases:
- FUNC_8004C644
- '0x8004c644'
- vm_op_aimed_drop_spawn
address: '0x8004c644'
name: vm_op_aimed_drop_spawn
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- mover_vm_dispatch_next
- vm_native_aimed_drop_spawn
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8004C644 - vm_op_aimed_drop_spawn

## Purpose
Mover-VM opcode entry calling the aimed-drop-spawn native, advances IP, continues dispatch

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal 0x80057b84 (a0=s0); addiu s1,4; j mover_vm_dispatch_next; sibling of 0x8004c5d4

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
