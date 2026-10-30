---
kind: function
id: FUNC_8003DAF0
aliases:
- FUNC_8003DAF0
- '0x8003daf0'
- scroll_backdrop_moveimage
address: '0x8003daf0'
name: scroll_backdrop_moveimage
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- MoveImage
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
patch_policy: safe_to_read
---

# FUNC_8003DAF0 - scroll_backdrop_moveimage

## Purpose
Animates/scrolls a full-screen backdrop by blitting VRAM strips (MoveImage) driven by an accumulated angle

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- reads angle 0x800822b2, accumulates scroll phase in gp+1364/1536/1328; two width branches (320/512) call MoveImage(rect 0x800823b8) in a loop; source table 0x80071230/0x8007125c

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
