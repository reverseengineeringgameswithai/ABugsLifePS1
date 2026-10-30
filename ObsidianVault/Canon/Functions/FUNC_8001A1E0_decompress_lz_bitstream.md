---
kind: function
id: FUNC_8001A1E0
aliases:
- FUNC_8001A1E0
- '0x8001a1e0'
- decompress_lz_bitstream
address: '0x8001a1e0'
name: decompress_lz_bitstream
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls: []
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch02.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch02.json
patch_policy: safe_to_read
---

# FUNC_8001A1E0 - decompress_lz_bitstream

## Purpose
Bit-controlled literal/back-reference LZ decompressor (src a0 -> dst a1)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- 4-byte BE header then MSB bit-reader over control stream; emits literals + window back-refs (len/dist bit-decoded)
- saves/restores entire register file; matches LEVEL.RAW LZ codec role

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
