---
kind: function
id: FUNC_8006EDA8
aliases:
- FUNC_8006EDA8
- 2147937704
- '0x8006eda8'
- CD_vol
address: '0x8006eda8'
name: CD_vol
status: byte_matched
confidence: confirmed
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
- EXP_2026-07-08_c_decompilation_campaign_v1
src_paths:
- src/main/8006eda8_CD_vol.c
patch_policy: do_not_patch
---

# FUNC_8006EDA8 - CD_vol (PsyQ SDK)

PsyQ/PSY-Q SDK library routine `CD_vol` (linked from the retail SDK, not game code). Identity from `re_symbols.sym` SDK matching.

Stub created by the RCA campaign (a1) to resolve inbound `[[FUNC_8006EDA8]]` links that previously
routed to `Archive/Superseded/` or dangled. Attested as a real function-start by the census
(`analysis/functions.json`); named `CD_vol` in `re_symbols.sym` (SDK). Expand with runtime evidence (an `EXP_`) before
upgrading `status` above `static_seen`.

Related: [[SYS_function_census]] · [[Consistency Audit]].
