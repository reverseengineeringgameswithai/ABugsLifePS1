---
kind: function
id: FUNC_80062A54
aliases:
- FUNC_80062A54
- '0x80062a54'
- link_prim_packet_chain
address: '0x80062a54'
name: link_prim_packet_chain
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

# FUNC_80062A54 - link_prim_packet_chain

## Purpose
Initializes/links a GPU primitive-packet buffer into a forward-linked chain (ClearOTag-style)

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- loops records: sb 0,3(s0) clears code byte, writes 24-bit next-ptr preserving high byte, advances one word; final -> 0x8007fc44

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch02.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
