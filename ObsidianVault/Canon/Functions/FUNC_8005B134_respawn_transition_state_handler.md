---
kind: function
id: FUNC_8005B134
aliases: [FUNC_8005B134, 0x8005b134, respawn_transition_state_handler]
address: 0x8005B134
name: respawn_transition_state_handler
status: static_seen
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
  - EXP_2026-07-09_identity_reconciliation
src_paths: []
patch_policy: unknown
---

# FUNC_8005B134 - player-pos - Region-A overlay dispatcher (superseded claim)

> **RCA a3 identity fix (2026-07-09):** Renamed the superseded "Region-A overlay dispatcher" claim -> **respawn_transition_state_handler** (authoritative `re_symbols.sym`).


## Purpose

Once believed to be the sole player-position writer (static-era guess). **Superseded** by [[FUNC_8003633C]] for the per-frame collision-Y write; its true role and relationship remain open. [!check] Live-traced 2026-06-18 (B17). It is an **8-way state-handler**: `index = v0−3`, bounds-checked `<8`, jumps through table `0x8001b828` to **internal** cases `0x8005b174/84/94/a4/b4` (states 5/7/9 → default `0x8005b1bc`). **0 hits over 8 idle frames** → it only runs under specific states (`v0∈[3,10]`) and **does not write player Y *per-frame in idle states*** — confirming the G5 "sole *per-frame* writer" claim is DISPROVEN (per-frame writer = [[FUNC_8003633C]]). Reached indirectly (0 `jal` callers — itself a dispatcher). **REFINED 2026-06-20:** the sub-question "what triggers states 3–10" is **answered** — those are **respawn/transition states**, and the handler's **common tail `0x8005b1bc` DOES...

## Known behavior

This page is a copy-first Canon seed generated from `ObsidianVault/Functions/FUNC_8005B134.md`. Treat claims as Canon only to the status/confidence level above. Do not promote stale or speculative material without evidence from `_Revamp/CONFLICTS.md` and linked experiments.

## Confirmed as the sole death-respawn path (2026-08-03)

Phase 4 C15 confirms this function's common tail is the ONLY restore path death respawn
uses — the scene spawn table (`FUNC_80046B20`/`FUNC_8005B714`) is level-entry only, never a
death-respawn fallback. The anchor it restores from (`0x800A6550/54/58`) is maintained by
[[FUNC_80054C90]], which excludes `F04_cliffside_canyon` (scene 6) from ever updating it —
live-confirmed frozen across 440+ frames there, and live-confirmed tracking normally in
scene 1 as a contrast. Cliffside's own bird-hazard overlay separately hardcodes a
pre-authored coordinate directly into the anchor at the exact death moment (PC `0x800B3B00`,
a literal immediate construction, not derived from Flik's position or the scene table) —
answering why that encounter's respawn point looks "pre-determined." See
[[EXP_2026-08-03_phase4_c15_respawn_anchor]], `analysis/phase4_c15_respawn_anchor.json`.

## Address / identity

- Address: `0x8005B134`
- Name: `player-pos_-_Region-A_overlay_dispatcher_(superseded_claim)`
- Original note: `ObsidianVault/Functions/FUNC_8005B134.md`
- Source path: `none matched`

## C source excerpt

Source: `none matched`

```c
// No matching C source found during revamp audit.
```

## Evidence

- Original note: `ObsidianVault/Functions/FUNC_8005B134.md`
- Source coverage row: `_Revamp/SRC_COVERAGE.md`

## Related

See `Canon/Indexes/Address Index.md` and `_Revamp/MIGRATION_MAP.md`.

## Legacy Migration Reference

- Legacy source archived from `ObsidianVault/Functions/FUNC_8005B134.md`.
- Archive copy: `ObsidianVault/Archive/Superseded/Functions_FUNC_8005B134.md`.
- Added during the 2026-07-08 migration completion pass; the archive copy is provenance, not current Canon.

