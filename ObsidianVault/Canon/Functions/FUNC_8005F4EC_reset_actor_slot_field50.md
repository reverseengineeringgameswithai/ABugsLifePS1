---
kind: function
id: FUNC_8005F4EC
aliases:
- FUNC_8005F4EC
- '0x8005f4ec'
- reset_actor_slot_field50
address: '0x8005f4ec'
name: reset_actor_slot_field50
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

# FUNC_8005F4EC - reset_actor_slot_field50

## Purpose
Clears the +0x32 halfword state field across ranges of 84-byte actor slots

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Indexes scene actor via 0x800a6300[a0[0]], count at +4, *84 stride
- Clears halfword slot+0x32 for slots 0..19 (skip 4,7) in 0x80099F58 and 26..28 in 0x8009A7E0
- callers gameplay_state_reset_cursor_seed, player_vertical_update, resident_level_transition_initiator, seed_plant_cannon_handler

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
