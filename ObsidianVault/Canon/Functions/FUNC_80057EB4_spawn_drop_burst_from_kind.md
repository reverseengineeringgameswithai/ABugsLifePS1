---
kind: function
id: FUNC_80057EB4
aliases:
- FUNC_80057EB4
- '0x80057eb4'
- spawn_drop_burst_from_kind
address: '0x80057eb4'
name: spawn_drop_burst_from_kind
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- spawn_drop
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80057EB4 - spawn_drop_burst_from_kind

## Purpose
Spawns 5 drops whose type is selected from a kind-indexed table

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter spawn_drop(xyz from s1) type=table[kind]+(i&1), kind=low nibble byte at v1, table 0x80079FB8
- incr counter 0x800822F4, stack arg 2

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
