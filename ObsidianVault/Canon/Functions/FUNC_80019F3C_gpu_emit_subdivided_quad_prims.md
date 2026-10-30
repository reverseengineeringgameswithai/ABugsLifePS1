---
kind: function
id: FUNC_80019F3C
aliases:
- FUNC_80019F3C
- '0x80019f3c'
- gpu_emit_subdivided_quad_prims
address: '0x80019f3c'
name: gpu_emit_subdivided_quad_prims
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

# FUNC_80019F3C - gpu_emit_subdivided_quad_prims

## Purpose
Assembles two Gouraud GPU primitives from midpoint-subdivided verts/colors and links them into the OT (mesh subdivision emit)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- midpoint interp of vertex coords (add;sra1 signed-round) + byte-wise color avg (andi 0xff/srl8/add/srl1)
- builds two GPU packets tag 0x0c000000/0x09000000 into [t9], links 24-bit OT ptr; advances s3 52 then 40; GTE cop2 ops

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
