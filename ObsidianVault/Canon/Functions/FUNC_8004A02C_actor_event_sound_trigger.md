---
kind: function
id: FUNC_8004A02C
aliases:
- FUNC_8004A02C
- '0x8004a02c'
- actor_event_sound_trigger
address: '0x8004a02c'
name: actor_event_sound_trigger
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- play_sound
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8004a02c_actor_event_sound_trigger.c
patch_policy: safe_to_read
---

# FUNC_8004A02C - actor_event_sound_trigger

## Purpose
Actor event handler playing sound 38 or 26 at the actor position depending on event and +0x44 state

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- s0=a0[4]; branch on event a0[0] in {22,10} and state s0[0x44]
- s0[0x44]==0 & match: play_sound(38,s0+4); s0[0x44]==1: play_sound(26,s0+4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
