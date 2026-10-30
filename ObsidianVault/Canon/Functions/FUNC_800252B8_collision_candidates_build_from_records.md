---
kind: function
id: FUNC_800252B8
aliases:
- FUNC_800252B8
- '0x800252b8'
- collision_candidates_build_from_records
address: '0x800252b8'
name: collision_candidates_build_from_records
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- collision_candidate_builder
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_800252B8 - collision_candidates_build_from_records

## Purpose
Iterates the type-0x3f record list feeding coords into collision_candidate_builder (builds the frame's collision candidate set)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- count from type_3f record ptr 0x80096e9c; per record XZ<<5, calls collision_candidate_builder 0x80037320
- special-case byte+8==20 coord bias; /100 index into 0x80077ff4, sh to record+0x10

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
