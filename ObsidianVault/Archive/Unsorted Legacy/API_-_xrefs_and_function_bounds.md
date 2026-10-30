---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/DuckStation API/API - xrefs and function bounds.md
aliases:
  - "API - xrefs and function bounds"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/DuckStation API/API - xrefs and function bounds.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: API - xrefs and function bounds
type: api
category: Static analysis
tags: [api, duckstation, xref, function, disasm, static]
---
# API — xrefs and function bounds

> Find who references an address, and the start/end of the function containing it — automated, replacing hand-scanning `jal` words and backward prologue searches.

## Methods & syntax
- **`debugger.xrefsTo {address}`** → `{xrefs:[{from, type, instruction, confidence}], ...}`. Scans **all RAM** for references to `address`: `jal`/`j` targets, branch targets, and **`lui`+lower** register-build pairs (the two-instruction "load a 32-bit constant" idiom). `type` distinguishes the reference kind; `confidence` flags how certain the match is (a `lui`/lower pair is weaker than a direct `jal`).
- **`debugger.functionBounds {address}`** → `{functionStart, functionEnd, prologue:{address, instruction, frameSize}, epilogueCandidates, confidence, cleanEnd, mergedRegion, spanBytes, notes}`. Infers the enclosing function: walks back to the stack-frame **prologue** (`addiu sp,sp,-N` **or** `addi sp,sp,-N`; `frameSize` = N) and forward to `jr ra` **epilogue** candidates, stopping at a clean terminator (the next function's prologue, a `jr ra` followed by a new function/padding, or a symbol boundary).
- **Honest `confidence` ∈ `exact | probable | low | unknown`:** `exact` ONLY when there is a clean terminator (`cleanEnd:true`) AND a plausible span (`spanBytes ≤ 8 KiB`). An implausibly large or uncleanly-terminated result returns **`confidence:"low"` + `mergedRegion:true`** + a reason `note` instead of a misleading `exact`. (The old code returned one ~63 KB "exact" function spanning dozens of routines — that now reports `low`/`mergedRegion`.)
- **Symbols-first, disasm fallback:** both prefer loaded [[API - symbols|symbol]] info when present and fall back to scanning/disassembly otherwise.

## Best use in ABL RE
- **Who calls this function?** `xrefsTo {address:<func entry>}` lists every caller in one shot — the [[Playbook - Trace rendering ownership]] / [[Playbook - Find geometry sources]] move that previously meant computing the `jal` opcode word `(0x3<<26)|((target>>2)&0x03ffffff)` and grepping RAM by hand (see the [[DuckStation API Index]] call-shape note).
- **Who builds this pointer?** The `lui`+lower scan catches code that loads a struct/table base address as an immediate (e.g. finding what references a known terrain/collision table), which a pure `jal` scan misses.
- **What function am I in?** `functionBounds {address:<a PC from execTrace>}` gives the entry to break on and the extent to disassemble — no manual backward prologue hunt.

## Common mistakes / gotchas
- `lui`+lower pairs are heuristic — check `confidence`; a constant that happens to equal an address isn't always a real reference.
- `functionBounds` is bounded by its scan window: trust `notes` when it says the prologue/epilogue wasn't found — `functionStart`/`functionEnd` are then approximate.
- **Don't trust a `low`/`mergedRegion` result as a single function** — it almost certainly merges several routines (huge `spanBytes` or no clean terminator). Supply [[API - symbols|symbols]] (`importSymbols`) or query a narrower address to split it. Only `confidence:"exact"` (with `cleanEnd:true`) is a trustworthy single-function extent.
- Scans **RAM as currently loaded** — code that hasn't been streamed/overlaid in won't be seen. Pair with [[API - loadState]] to a fixture where the relevant code is resident.

## Related
[[API - symbols]] · [[API - execTrace]] · [[API - GTE state]] · [[API - gpu.pickObject]] · [[Playbook - Trace rendering ownership]] · [[Playbook - Find geometry sources]]

Source: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md (+ docs/external-debugger.md)
