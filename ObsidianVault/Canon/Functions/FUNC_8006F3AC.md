---
kind: function
id: FUNC_8006F3AC
aliases: [FUNC_8006F3AC, 0x8006f3ac]
address: 0x8006f3ac
name: CD_getsector
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

# FUNC_8006F3AC - CD_getsector (PsyQ SDK)

PsyQ/PSY-Q SDK library routine `CD_getsector` (linked from the retail SDK, not game code). Identity from `re_symbols.sym` SDK matching.

Stub created by the RCA campaign (a1) to resolve inbound `[[FUNC_8006F3AC]]` links that previously
routed to `Archive/Superseded/` or dangled. Attested as a real function-start by the census
(`analysis/functions.json`); named `CD_getsector` in `re_symbols.sym` (SDK). Expand with runtime evidence (an `EXP_`) before
upgrading `status` above `static_seen`.

Related: [[SYS_function_census]] · [[Consistency Audit]].
