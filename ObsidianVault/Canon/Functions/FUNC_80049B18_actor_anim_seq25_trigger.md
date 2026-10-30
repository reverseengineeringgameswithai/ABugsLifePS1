---
kind: function
id: FUNC_80049B18
aliases:
- FUNC_80049B18
- '0x80049b18'
- actor_anim_seq25_trigger
address: '0x80049b18'
name: actor_anim_seq25_trigger
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

# FUNC_80049B18 - actor_anim_seq25_trigger

## Purpose
Jump-table/VM handler starting animation sequence 25 on the actor

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- calls actor_set_anim_sequence(s0,1,25); tail j 0x80049b64 v0=-25; sibling of 0x80049a70

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
