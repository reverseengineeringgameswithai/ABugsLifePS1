---
kind: function
id: FUNC_800309CC
aliases:
- FUNC_800309CC
- '0x800309cc'
- vector_project_onto_plane
address: '0x800309cc'
name: vector_project_onto_plane
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/800309cc_vector_project_onto_plane.c
patch_policy: safe_to_read
---

# FUNC_800309CC - vector_project_onto_plane

## Purpose
Removes the N-direction component of P (projects P onto plane perpendicular to N)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- reads 3-short N at a0, 3-word P at a1
- negated dot(N,P)>>10, then P + N*(that)>>17 stored to a2

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
