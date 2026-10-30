---
kind: function
id: FUNC_8003F5B8
aliases:
- FUNC_8003F5B8
- '0x8003f5b8'
- load_memory_bin
address: '0x8003f5b8'
name: load_memory_bin
status: byte_matched
confidence: confirmed
source_state: original_game
tier: inferred
calls:
- universal_file_loader
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch01.json
- EXP_2026-07-10_c_conversion_at_scale
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch01.json
- src/main/8003f5b8_load_memory_bin.c
patch_policy: safe_to_read
---

# FUNC_8003F5B8 - load_memory_bin

## Purpose
Loads bits\memory.bin into a buffer and installs its base pointer

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- caller main_shell_state_machine
- universal_file_loader('bits\\memory.bin' @0x8001ADFC, buf 0x800B5788); installs gp+1416=0x800D5790, calls setup 0x800bd518

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
