---
kind: function
id: FUNC_80042C70
aliases:
- FUNC_80042C70
- '0x80042c70'
- record_slots_populate_free
address: '0x80042c70'
name: record_slots_populate_free
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- table_836byte_record_populate
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80042C70 - record_slots_populate_free

## Purpose
Walks an 8-entry 836-byte record table filling free slots via table_836byte_record_populate (actor/mover registration)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loops 8 (a1+=836), occupancy check lh[0x8009c8b0+a1], skip if occupied
- only callee table_836byte_record_populate 0x8003f620 with stack descriptor + caller params

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
