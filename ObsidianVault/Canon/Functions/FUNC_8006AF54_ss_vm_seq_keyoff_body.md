---
kind: function
id: FUNC_8006AF54
aliases:
- FUNC_8006AF54
- '0x8006af54'
- ss_vm_seq_keyoff_body
address: '0x8006af54'
name: ss_vm_seq_keyoff_body
status: static_seen
confidence: medium
source_state: original_game
tier: inferred
calls:
- _SsVmKeyOffNow
evidence:
- EXP_2026-07-09_static_inference_naming
- analysis/naming/sc1_batch04_lib.json
src_paths:
- symbols/re_symbols.sym
- analysis/functions.json
- analysis/naming/sc1_batch04_lib.json
patch_policy: safe_to_read
---

# FUNC_8006AF54 - ss_vm_seq_keyoff_body

## Purpose
Body of _SsVmSeqKeyOff: keys off every SPU voice allocated to the given sequence

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- _SsVmSeqKeyOff @0x8006af4c loads voice count 0x800a1b30, falls through; body loops 52-byte voice records matching seq id, calls _SsVmKeyOffNow(0)

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch04_lib.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
