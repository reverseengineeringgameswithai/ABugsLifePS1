---
kind: function
id: FUNC_80051358
aliases:
- FUNC_80051358
- '0x80051358'
- sfx_proximity_priority_gate
address: '0x80051358'
name: sfx_proximity_priority_gate
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
patch_policy: safe_to_read
---

# FUNC_80051358 - sfx_proximity_priority_gate

## Purpose
Squared-distance proximity gate tracking the nearest positional sound source to the listener

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 11 callers, all effect/spawn/sound emitters
- squared 3D distance ((listener-arg)>>8)^2 over x,y,z from listener 0x800A6500/6504/6508; early-out dist>=0xFE00; else if closer than stored nearest, records new pos/params and updates counter

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
