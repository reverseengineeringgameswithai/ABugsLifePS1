---
kind: function
id: FUNC_80049AE8
aliases:
- FUNC_80049AE8
- '0x80049ae8'
- anim_state_set_seq_1_1
address: '0x80049ae8'
name: anim_state_set_seq_1_1
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

# FUNC_80049AE8 - anim_state_set_seq_1_1

## Purpose
Jump-table handler setting actor anim sequence (1,1), tail-continues neighbor

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- calls actor_set_anim_sequence(s0,1,1); tail j 0x80049b64 with addiu v0,-24 cluster convention

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
