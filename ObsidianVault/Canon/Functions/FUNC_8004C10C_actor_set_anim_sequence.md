---
kind: function
id: FUNC_8004C10C
aliases:
- FUNC_8004C10C
- '0x8004c10c'
- actor_set_anim_sequence
address: '0x8004c10c'
name: actor_set_anim_sequence
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
- src/main/8004c10c_actor_set_anim_sequence.c
patch_policy: safe_to_read
---

# FUNC_8004C10C - actor_set_anim_sequence

## Purpose
Assigns an animation frame-index sequence (and start param) to an actor object

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- indexes ptr table 0x80077e28 by arg2<<2 -> frame-sequence ptr; stores it at obj+76, first byte<<16 at obj+64 (16.16 accumulator), arg1 at obj+68
- called by 15 handlers incl player_vertical_update, seed_plant_cannon_handler

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
