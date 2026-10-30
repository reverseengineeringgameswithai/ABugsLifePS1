---
kind: function
id: FUNC_80039780
aliases:
- FUNC_80039780
- '0x80039780'
- vram_clear_framebuffers
address: '0x80039780'
name: vram_clear_framebuffers
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- ClearImage
- DrawSync
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/80039780_vram_clear_framebuffers.c
patch_policy: safe_to_read
---

# FUNC_80039780 - vram_clear_framebuffers

## Purpose
Clears the display/back framebuffer quadrants to black then waits for GPU sync

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- builds four RECTs (1023x511 full VRAM), ClearImage x4 r=g=b=0, then DrawSync(0)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
