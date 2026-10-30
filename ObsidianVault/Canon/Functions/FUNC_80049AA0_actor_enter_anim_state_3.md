---
kind: function
id: FUNC_80049AA0
aliases:
- FUNC_80049AA0
- '0x80049aa0'
- actor_enter_anim_state_3
address: '0x80049aa0'
name: actor_enter_anim_state_3
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

# FUNC_80049AA0 - actor_enter_anim_state_3

## Purpose
Jump-table state-entry handler: puts actor into anim sequence 3

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- calls actor_set_anim_sequence(s0,3,1); tail j 0x80049b64; v0=-24 cluster convention

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
