---
kind: function
id: FUNC_8006CAA4
aliases: [FUNC_8006CAA4, 0x8006caa4]
address: 0x8006caa4
name: _SpuSetAnyVoice
status: static_seen
confidence: inferred
source_state: original_game
system: []
calls: []
reads: []
writes: []
uses_tables: []
related_constants: []
related_hooks: []
evidence:
  - analysis/functions.json
src_paths: []
patch_policy: do_not_patch
---

# FUNC_8006CAA4 - _SpuSetAnyVoice (PsyQ SDK)

PsyQ/PSY-Q SDK library routine `_SpuSetAnyVoice` (linked from the retail SDK, not game code). Identity from `re_symbols.sym` SDK matching.

Stub created by the RCA campaign (a1) to resolve inbound `[[FUNC_8006CAA4]]` links that previously
routed to `Archive/Superseded/` or dangled. Attested as a real function-start by the census
(`analysis/functions.json`); named `_SpuSetAnyVoice` in `re_symbols.sym` (SDK). Expand with runtime evidence (an `EXP_`) before
upgrading `status` above `static_seen`.

Related: [[SYS_function_census]] · [[Consistency Audit]].
