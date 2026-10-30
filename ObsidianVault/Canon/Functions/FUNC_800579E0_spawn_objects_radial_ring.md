---
kind: function
id: FUNC_800579E0
aliases:
- FUNC_800579E0
- '0x800579e0'
- spawn_objects_radial_ring
address: '0x800579e0'
name: spawn_objects_radial_ring
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- contact_object_spawn_full
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/800579e0_spawn_objects_radial_ring.c
patch_policy: safe_to_read
---

# FUNC_800579E0 - spawn_objects_radial_ring

## Purpose
Spawns 8 objects in a radial ring using a sine/cosine table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8-iter loop (s0 0->4096 step 512) reads sine table 0x80074970 (stride 0x400) with +0x200 quadrature for cosine
- contact_object_spawn_full with center XYZ, computed direction, params 64,44
- sole caller seed_plant_type7_handler

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
