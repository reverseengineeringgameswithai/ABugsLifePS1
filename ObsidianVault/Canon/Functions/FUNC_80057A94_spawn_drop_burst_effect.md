---
kind: function
id: FUNC_80057A94
aliases:
- FUNC_80057A94
- '0x80057a94'
- spawn_drop_burst_effect
address: '0x80057a94'
name: spawn_drop_burst_effect
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80057a94_spawn_drop_burst_effect.c
patch_policy: safe_to_read
---

# FUNC_80057A94 - spawn_drop_burst_effect

## Purpose
Spawns a burst of ~24 drops at an object and plays the accompanying sound

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller sub_8004c5d4; callees spawn_drop, play_sound
- double loop (8 x 0..2) issues ~24 spawn_drop calls then play_sound(24,obj+4,-3072)->obj+32; gates bit 0x2 in obj+92

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
