---
kind: function
id: FUNC_80053754
aliases:
- FUNC_80053754
- '0x80053754'
- seed_token_reskin_cycle
address: '0x80053754'
name: seed_token_reskin_cycle
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- token_descriptor_reskin
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_80053754 - seed_token_reskin_cycle

## Purpose
Advances a seed/token reskin index (mod 8) and applies it via token_descriptor_reskin

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- incr per-object counter seed_counter_0[s0] 0x800a6598 mod 8, spacing v0*17
- token_descriptor_reskin(cycled index-1); updates nibble table 0x800b0196

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
