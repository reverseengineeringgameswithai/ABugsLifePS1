---
kind: function
id: FUNC_8001CA20
aliases:
- FUNC_8001CA20
- '0x8001ca20'
- mesh_draw_command_interpreter
address: '0x8001ca20'
name: mesh_draw_command_interpreter
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

# FUNC_8001CA20 - mesh_draw_command_interpreter

## Purpose
Display-list opcode interpreter emitting textured tri/quad GPU primitives from a pre-transformed vertex list

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 7-entry jump table 0x8001a900 (opcode = stream_halfword&0x1f); assembles GPU prims into buffer 0x8008249c
- advances packet 52/40, vertex words +4/16/28/40 UV +12/24/36/48; texpage/CLUT tables 0x800a7dd8/0x800894e8

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
