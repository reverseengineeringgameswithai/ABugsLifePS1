---
kind: function
id: FUNC_80045CAC
aliases:
- FUNC_80045CAC
- '0x80045cac'
- music_play_looping_wrapper
address: '0x80045cac'
name: music_play_looping_wrapper
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- music_play_looping
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch05_final.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch05_final.json
- src/main/80045cac_music_play_looping_wrapper.c
patch_policy: safe_to_read
---

# FUNC_80045CAC - music_play_looping_wrapper

## Purpose
Thin wrapper biasing the track index by -2 before music_play_looping

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- jal music_play_looping (0x80046ae8); addiu a0,a0,-2 in delay slot

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch05_final.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
