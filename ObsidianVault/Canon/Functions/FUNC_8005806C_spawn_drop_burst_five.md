---
kind: function
id: FUNC_8005806C
aliases:
- FUNC_8005806C
- '0x8005806c'
- spawn_drop_burst_five
address: '0x8005806c'
name: spawn_drop_burst_five
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8005806c_spawn_drop_burst_five.c
patch_policy: safe_to_read
---

# FUNC_8005806C - spawn_drop_burst_five

## Purpose
Spawns 5 drops at the source position then triggers sound 5

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loop 0..4 spawn_drop(xyz from s1+0/4/8, alternating a3); then play_sound(5,s1)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
