---
kind: system
id: SYS_re_evidence_policy
name: Reverse Engineering Evidence Policy
status: live_confirmed
confidence: confirmed
source_state: project_methodology
functions: []
memory: []
tables: []
constants: []
evidence:
  - EXP_2026-07-08_coverageToFrame_cycle_neutrality
  - EXP_2026-07-08_trace_naming
src_paths:
  - src_re/pickup_handlers_80054288_80054554.c
  - src_re/source3f_dispatch_80053814.c
---

# SYS_re_evidence_policy

## Purpose

Canonical rule for how static RE, C reference files, runtime traces, and old notes should be ranked.

## Evidence order

1. Live DuckStation trace, movie verifier, or replayable runtime artifact.
2. `src_re` C reference tied to addresses and runtime evidence.
3. Current mod ASM/C implementation.
4. Current Canon note with evidence links.
5. Old session notes and planning notes.
6. Static-only guesses.
7. Superseded or contradicted notes.

## Function-boundary policy

Static function boundaries and `jal` call graphs are not authoritative by themselves. Jump-table cases, overlay code, and manually reconstructed C helpers can use invented boundaries that do not exist as standalone ABI functions in the binary.

Use `static_seen` for static-only claims. Promote to `runtime_seen`, `live_confirmed`, or `confirmed` only when stronger evidence exists.

## Superseded claim

Do not promote "static r2 function boundaries and `jal` graph are complete/authoritative" into Canon.
That historical claim is archived at `Archive/Wrong Hypotheses/WHYPE_static_callgraph_authority.md`.
