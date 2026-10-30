---
kind: function
id: FUNC_8003F358
aliases:
- FUNC_8003F358
- '0x8003f358'
- seed_cursor_state_jump_dispatch
address: '0x8003f358'
name: seed_cursor_state_jump_dispatch
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

# FUNC_8003F358 - seed_cursor_state_jump_dispatch

## Purpose
Sets a state pointer then dispatches to one of 19 handlers via jump table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Callers gameplay_state_reset_cursor_seed and sub_8005b440
- Stores 0x800b5790 to gp+1416, bounds-checks (a0+1) via sltiu<19, jr through jump table 0x8001b048 indexed by (a0+1)*4

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
