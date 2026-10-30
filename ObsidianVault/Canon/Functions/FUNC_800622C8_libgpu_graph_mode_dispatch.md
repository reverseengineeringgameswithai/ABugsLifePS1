---
kind: function
id: FUNC_800622C8
aliases:
- FUNC_800622C8
- '0x800622c8'
- libgpu_graph_mode_dispatch
address: '0x800622c8'
name: libgpu_graph_mode_dispatch
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch06_residual.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch06_residual.json
patch_policy: safe_to_read
---

# FUNC_800622C8 - libgpu_graph_mode_dispatch

## Purpose
libgpu internal reading a graph-mode flag and dispatching driver callbacks / GPU display-mode packets

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- prologue/epilogue; reads mode byte, calls driver fnptrs from struct 0x800Bxxxx, issues GPU display packets 0x2000504/0x2000501; between SetGraphReverse and SetGraphDebug

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch06_residual.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
