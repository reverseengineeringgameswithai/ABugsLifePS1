---
kind: function
id: FUNC_80044D28
aliases: [FUNC_80044D28, 0x80044d28]
address: 0x80044d28
name: sfx_voice_manager
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
evidence: [EXP_2026-07-09_understanding_u3]
src_paths: [symbols/re_symbols.sym, analysis/functions.json]
patch_policy: unknown
---

# FUNC_80044D28 - Audio — SFX voice manager

## Purpose

Manages the pool of active SFX voices (allocation/priority/stop). 2384 B, 8 callers — a hub of the sound subsystem.

## Known behavior

8 callers. u3-1 runtime: EnterCriticalSection/ExitCriticalSection are called around its voice-table edits.

## Address / identity

- Address: `0x80044d28`
- Name: `sfx_voice_manager` (evidence: [[EXP_2026-07-09_understanding_u3]] + static census `analysis/functions.json`)

## Evidence

- [[EXP_2026-07-09_understanding_u3]] — runtime execTrace campaign (pristine saves).
- Census row `analysis/functions.json` (callers/callees, dynamic coverage).

## Related

See [[Address Index]] and [[SYS_function_census]].
