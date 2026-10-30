---
kind: function
id: FUNC_8001A0E4
aliases:
- FUNC_8001A0E4
- '0x8001a0e4'
- gpu_build_poly_g4_gouraud
address: '0x8001a0e4'
name: gpu_build_poly_g4_gouraud
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8001A0E4 - gpu_build_poly_g4_gouraud

## Purpose
Emits a 12-word POLY_G4 Gouraud primitive into an OT node, GTE-transforming verts and interpolating corners

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- OT tag lui t8,0xc00 + mask + OR len 0x0c = POLY_G4 12-word packet
- COP2/GTE transform of source verts
- averages adjacent colors/coords (midpoint) for shaded quad corners

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
