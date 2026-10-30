---
kind: function
id: FUNC_80049AD0
aliases:
- FUNC_80049AD0
- '0x80049ad0'
- actor_anim1_state_handler
address: '0x80049ad0'
name: actor_anim1_state_handler
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

# FUNC_80049AD0 - actor_anim1_state_handler

## Purpose
Jump-table state handler selecting animation sequence 1 for the actor, continues at 0x80049b64

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- actor_set_anim_sequence(s0,1,1); tail j 0x80049b64; no prologue, consumes preset s0

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
