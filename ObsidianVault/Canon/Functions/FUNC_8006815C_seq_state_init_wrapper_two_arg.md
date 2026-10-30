---
kind: function
id: FUNC_8006815C
aliases:
- FUNC_8006815C
- '0x8006815c'
- seq_state_init_wrapper_two_arg
address: '0x8006815c'
name: seq_state_init_wrapper_two_arg
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- seq_playback_state_init
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
- src/main/8006815c_seq_state_init_wrapper_two_arg.c
patch_policy: safe_to_read
---

# FUNC_8006815C - seq_state_init_wrapper_two_arg

## Purpose
Public two-argument wrapper around seq_playback_state_init

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- sign-extends a0,a1 to 16-bit, jal seq_playback_state_init; thin wrapper

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
