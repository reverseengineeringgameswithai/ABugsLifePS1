---
kind: function
id: FUNC_80067F68
aliases:
- FUNC_80067F68
- '0x80067f68'
- ss_seq_tick_every_other_dispatch
address: '0x80067f68'
name: ss_seq_tick_every_other_dispatch
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
- src/main/80067f68_ss_seq_tick_every_other_dispatch.c
patch_policy: safe_to_read
---

# FUNC_80067F68 - ss_seq_tick_every_other_dispatch

## Purpose
Body of _SsSeqCalledTbyT_1per2: divide-by-two VSync gate invoking the per-tick sound callback on alternate ticks

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _SsSeqCalledTbyT_1per2 @0x80067f60 loads flag 0x80080ec4, falls through; body toggles flag, on set calls *0x80080eb8 callback
- libsnd tick region

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
