---
kind: function
id: FUNC_80055478
aliases:
- FUNC_80055478
- '0x80055478'
- serialize_savegame_buffer
address: '0x80055478'
name: serialize_savegame_buffer
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
- src/main/80055478_serialize_savegame_buffer.c
patch_policy: safe_to_read
---

# FUNC_80055478 - serialize_savegame_buffer

## Purpose
Packs global game-state (lives + 19-byte header + 64 five-byte records) into a caller buffer (save/serialization)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- writes lives byte 0x800a65a0 to [a0+0], halfword 0x80082284 to [a0+1], 19 bytes from 0x8009b878, then 64 5-byte records from 0x80089938

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
