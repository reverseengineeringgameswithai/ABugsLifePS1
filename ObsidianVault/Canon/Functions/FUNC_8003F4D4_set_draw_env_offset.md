---
kind: function
id: FUNC_8003F4D4
aliases:
- FUNC_8003F4D4
- '0x8003f4d4'
- set_draw_env_offset
address: '0x8003f4d4'
name: set_draw_env_offset
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/8003f4d4_set_draw_env_offset.c
patch_policy: safe_to_read
---

# FUNC_8003F4D4 - set_draw_env_offset

## Purpose
Records an (x,y) draw offset into gp state and both display buffers

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Stores (a0,a1) to gp+1332/gp+1336 and to 0x801CC508/0A and 0x801E14C4/C6 (double buffer)
- callers boot_video_audio_init, main_shell_state_machine, sub_80055538

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
