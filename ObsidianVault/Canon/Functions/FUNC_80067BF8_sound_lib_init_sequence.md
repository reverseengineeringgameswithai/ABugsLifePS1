---
kind: function
id: FUNC_80067BF8
aliases:
- FUNC_80067BF8
- '0x80067bf8'
- sound_lib_init_sequence
address: '0x80067bf8'
name: sound_lib_init_sequence
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- ResetCallback
- _SsInit
- spu__spu_init_glue
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/80067bf8_sound_lib_init_sequence.c
patch_policy: safe_to_read
---

# FUNC_80067BF8 - sound_lib_init_sequence

## Purpose
Ordered SPU/sound-library initialization wrapper

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller sound_system_init
- ResetCallback(), spu__spu_init_glue(), _SsInit() in sequence; 48-byte wrapper

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
