---
kind: function
id: FUNC_80053640
aliases:
- FUNC_80053640
- '0x80053640'
- draw_mirrored_fullscreen_quads
address: '0x80053640'
name: draw_mirrored_fullscreen_quads
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- draw_textured_quad
- queue_draw_prim
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80053640 - draw_mirrored_fullscreen_quads

## Purpose
Draws a 2x2 grid of textured quads tiling the full screen with mirrored UVs (symmetric backdrop/overlay)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- four draw_textured_quad 0x80026a68 at (0,0),(512,0),(0,240),(512,240), color 0x70, mode 26
- mirrors UV 13056/-13056 and 8192/-8192; queue_draw_prim

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
