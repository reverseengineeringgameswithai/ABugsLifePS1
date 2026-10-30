---
kind: function
id: FUNC_80066768
aliases:
- FUNC_80066768
- '0x80066768'
- pad_status_ready_check
address: '0x80066768'
name: pad_status_ready_check
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_80066768 - pad_status_ready_check

## Purpose
Boolean readiness query over a two-word status struct in the PAD region

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loads *0x80080e70, tests word[+4]&1 and word[+0]&1; returns 1 only when both set; PAD region

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
