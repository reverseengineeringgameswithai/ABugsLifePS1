---
kind: function
id: FUNC_80066700
aliases:
- FUNC_80066700
- '0x80066700'
- pad_reset_wait_delay
address: '0x80066700'
name: pad_reset_wait_delay
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
- src/main/80066700_pad_reset_wait_delay.c
patch_policy: safe_to_read
---

# FUNC_80066700 - pad_reset_wait_delay

## Purpose
Clears a PAD control field then spins a settle delay

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loads *0x80080e6c, zeroes +10; two nested busy-wait countdowns (from 10), no side effects; PAD-init region

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
