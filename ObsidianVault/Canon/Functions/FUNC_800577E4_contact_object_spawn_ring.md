---
kind: function
id: FUNC_800577E4
aliases:
- FUNC_800577E4
- '0x800577e4'
- contact_object_spawn_ring
address: '0x800577e4'
name: contact_object_spawn_ring
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- contact_object_spawn_full
- sfx_proximity_priority_gate
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_800577E4 - contact_object_spawn_ring

## Purpose
Spawns a ring of contact objects around a source using a wrapped offset table, then runs the proximity SFX gate

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 8-iter loop (sll<4096 step 512) contact_object_spawn_full using offset table 0x80074970 with 0xfff wrap
- then sfx_proximity_priority_gate on obj+0x128

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
