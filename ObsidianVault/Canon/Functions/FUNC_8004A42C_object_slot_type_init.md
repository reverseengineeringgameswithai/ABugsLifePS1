---
kind: function
id: FUNC_8004A42C
aliases:
- FUNC_8004A42C
- '0x8004a42c'
- object_slot_type_init
address: '0x8004a42c'
name: object_slot_type_init
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- collision_candidate_builder
- memset
- mover_init_from_record
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_8004A42C - object_slot_type_init

## Purpose
Initializes the 64-slot object array, dispatching per type byte to install handlers + collision candidates

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller collision_grid_level_load_chu_glue; callees collision_candidate_builder, memset, sub_80049c30
- memsets 0x800A9D80(8448),0x800B2744(512); loops 64 slots stride 132, jr jump-table on (type-6)<36 (table 0x8002B2E4) writing handler ptrs to slot+116, calls collision_candidate_builder per slot

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
