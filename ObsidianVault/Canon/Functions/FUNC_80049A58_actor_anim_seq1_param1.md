---
kind: function
id: FUNC_80049A58
aliases:
- FUNC_80049A58
- '0x80049a58'
- actor_anim_seq1_param1
address: '0x80049a58'
name: actor_anim_seq1_param1
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

# FUNC_80049A58 - actor_anim_seq1_param1

## Purpose
Jump-table state handler assigning actor animation (a2=1 sequence, a1=1 param)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- actor_set_anim_sequence(s0, a1=1, a2=1); tail j 0x80049b64; v0=-24 cluster convention

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch03_clusters.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
