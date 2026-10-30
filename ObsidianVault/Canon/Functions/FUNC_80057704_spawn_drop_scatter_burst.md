---
kind: function
id: FUNC_80057704
aliases:
- FUNC_80057704
- '0x80057704'
- spawn_drop_scatter_burst
address: '0x80057704'
name: spawn_drop_scatter_burst
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- sfx_proximity_priority_gate
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

# FUNC_80057704 - spawn_drop_scatter_burst

## Purpose
Spawns a scatter burst of 5 drops (types 19/20) at stream-driven offsets, then a proximity-gated sound

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 5-iter reads 3 bytes from cursor 0x800822f4 (post-incr) as <<4 offsets (-2048) added to base a0[0..2]
- spawn_drop type alternating 19/20; then sfx_proximity_priority_gate a3=16480

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
