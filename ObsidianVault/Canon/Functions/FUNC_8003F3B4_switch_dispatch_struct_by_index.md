---
kind: function
id: FUNC_8003F3B4
aliases:
- FUNC_8003F3B4
- '0x8003f3b4'
- switch_dispatch_struct_by_index
address: '0x8003f3b4'
name: switch_dispatch_struct_by_index
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- high_heap_loader_entry
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
patch_policy: safe_to_read
---

# FUNC_8003F3B4 - switch_dispatch_struct_by_index

## Purpose
Compiled switch: table of entry points each selecting one 16-byte record then jumping to shared code at 0x8003f4bc

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- run of 3-instr thunks lui a0,0x8002/addiu -N (step 16)/j 0x8003f4bc; each selects a 16-byte struct then funnels to common handler 0x8003f4bc

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
