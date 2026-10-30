---
kind: function
id: FUNC_8005D53C
aliases:
- FUNC_8005D53C
- '0x8005d53c'
- chunk_pointer_relocate_index_fixup
address: '0x8005d53c'
name: chunk_pointer_relocate_index_fixup
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

# FUNC_8005D53C - chunk_pointer_relocate_index_fixup

## Purpose
Post-load relocation of intra-chunk pointers plus -2-sentinel index remapping

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- iterates arg0 entries (count+2, stride 12): relocates non-zero +8 offsets by chunk base
- if arg1&0xff publishes gp+1412/gp+1180; remaps -2 sentinel shorts via allocator 0x80082298 into 0x8009b368
- caller level_chunk_loader

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
