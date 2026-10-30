---
kind: function
id: FUNC_8004A144
aliases:
- FUNC_8004A144
- '0x8004a144'
- actor_sound40_on_low_state
address: '0x8004a144'
name: actor_sound40_on_low_state
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
- src/main/8004a144_actor_sound40_on_low_state.c
patch_policy: safe_to_read
---

# FUNC_8004A144 - actor_sound40_on_low_state

## Purpose
Plays sound 40 for the object when its +68 state counter is below 2

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- obj=[a0+4], guard field+68<2 -> play_sound(40, obj+4)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
