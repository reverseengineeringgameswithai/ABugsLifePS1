---
kind: function
id: FUNC_80038FC4
aliases:
- FUNC_80038FC4
- '0x80038fc4'
- build_division_lookup_tables
address: '0x80038fc4'
name: build_division_lookup_tables
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

# FUNC_80038FC4 - build_division_lookup_tables

## Purpose
Boot-time generation of two fixed-point reciprocal/division lookup tables

Named by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.

## Evidence
- Two index loops with div + break-6/7 guards, mflo quotient
- Loop1 writes 6072 halfwords to 0x800a3390 clamped <4096; loop2 1024 entries to 0x800963a8 clamped <4896
- sole caller boot_video_audio_init

Provenance: `symbols/re_symbols.sym`, the naming manifest `analysis/naming/sc1_batch01.json`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.

## Related
[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]
