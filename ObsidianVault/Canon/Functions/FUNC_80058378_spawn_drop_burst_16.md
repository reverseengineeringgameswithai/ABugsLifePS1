---
kind: function
id: FUNC_80058378
aliases:
- FUNC_80058378
- '0x80058378'
- spawn_drop_burst_16
address: '0x80058378'
name: spawn_drop_burst_16
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
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
- src/main/80058378_spawn_drop_burst_16.c
patch_policy: safe_to_read
---

# FUNC_80058378 - spawn_drop_burst_16

## Purpose
Spawns 16 drops of type 119 via spawn_drop

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Caller sfx_play_sound_glue; callee spawn_drop
- Loops 16x calling spawn_drop with a3=119 type, stack param 5, passthrough s1/s2/s3

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
