---
kind: function
id: FUNC_80049AB8
aliases:
- FUNC_80049AB8
- '0x80049ab8'
- enemy_deathanim_set_anim3
address: '0x80049ab8'
name: enemy_deathanim_set_anim3
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- actor_set_anim_sequence
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80049AB8 - enemy_deathanim_set_anim3

## Purpose
Death-animation state case starting anim sequence 3 (param 25) before the shared finalize

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- part of enemy_update_deathanim 0x800498ac: actor_set_anim_sequence(actor,3,25); j 0x80049b64 shared tail

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
