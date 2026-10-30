---
kind: function
id: FUNC_8004A234
aliases:
- FUNC_8004A234
- '0x8004a234'
- actor_turn_toward_player
address: '0x8004a234'
name: actor_turn_toward_player
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- atan2_heading
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/8004a234_actor_turn_toward_player.c
patch_policy: safe_to_read
---

# FUNC_8004A234 - actor_turn_toward_player

## Purpose
Rotates actor facing (+20) 1/16 toward the player each call

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loads player_x 0x800a6500/player_z 0x800a6508, dx/dz vs actor +4/+12, atan2_heading(dx,dz)
- delta wrapped ±2048 in 0xfff space, steps by delta>>4, writes +20

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
