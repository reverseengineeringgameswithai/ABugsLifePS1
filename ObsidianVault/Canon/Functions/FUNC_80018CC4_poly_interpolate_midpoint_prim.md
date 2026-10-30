---
kind: function
id: FUNC_80018CC4
aliases:
- FUNC_80018CC4
- '0x80018cc4'
- poly_interpolate_midpoint_prim
address: '0x80018cc4'
name: poly_interpolate_midpoint_prim
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

# FUNC_80018CC4 - poly_interpolate_midpoint_prim

## Purpose
Reads corner pos/color/UV, computes midpoints+centroid with GTE clamp, emits interpolated GPU polygon (subdivision helper)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- averages coord pairs (add;sra 1 midpoints) + 4-way centroid (sra 2), GTE mtc2/mfc2 clamp
- averages 8-bit color channels; writes 4 packed verts s3+4/16/28/40 stride 0xC; POLY tag lui 0xc00

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
