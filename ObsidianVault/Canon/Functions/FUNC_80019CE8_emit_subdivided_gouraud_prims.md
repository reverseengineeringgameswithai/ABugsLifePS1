---
kind: function
id: FUNC_80019CE8
aliases:
- FUNC_80019CE8
- '0x80019ce8'
- emit_subdivided_gouraud_prims
address: '0x80019ce8'
name: emit_subdivided_gouraud_prims
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

# FUNC_80019CE8 - emit_subdivided_gouraud_prims

## Purpose
Subdivides a polygon by midpoint interpolation and emits multiple gouraud GPU primitives into the OT

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- midpoint interp of 3 verts/colors (add;sra1 XY; andi 0xff/srl8 RGB), GTE transform s7+148..
- GP0 poly cmds lui 0xc00/0x900, OT-links each prim, advances s3 by 52/40/40

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
