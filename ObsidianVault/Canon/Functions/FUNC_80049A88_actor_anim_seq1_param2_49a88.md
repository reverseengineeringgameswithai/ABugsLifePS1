---
kind: function
id: FUNC_80049A88
aliases:
- FUNC_80049A88
- '0x80049a88'
- actor_anim_seq1_param2_49a88
address: '0x80049a88'
name: actor_anim_seq1_param2_49a88
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- actor_set_anim_sequence
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch03_clusters.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch03_clusters.json
patch_policy: safe_to_read
---

# FUNC_80049A88 - actor_anim_seq1_param2_49a88

## Purpose
Jump-table state handler assigning actor animation (seq 1, param 2)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- actor_set_anim_sequence(s0, a1=2, a2=1); tail j 0x80049b64; v0=-24 (identical body to 0x80049b30, distinct jump-table slot)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
