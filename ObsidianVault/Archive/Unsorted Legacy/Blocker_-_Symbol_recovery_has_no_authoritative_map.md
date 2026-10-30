---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Symbol recovery has no authoritative map.md
aliases:
  - "Blocker - Symbol recovery has no authoritative map"
migration_action: superseded
superseded_by:
  - SYS_executable_image
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Symbol recovery has no authoritative map.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Symbol recovery has no authoritative map
type: blocker
id: B15
severity: LOW
category: symbol-recovery
confidence: CONFIRMED
tags: [blocker, medium, symbols, naming]
updated: 2026-06-22
---

# 🟡 B15 — No authoritative symbol map; names live in prose, not a queryable store

> The EXE is stripped, so every identifier is an address or an RE-derived name. Those names live in code banners and notes rather than one authoritative `address → name → confidence → evidence` store, and only ~35 of ~1,070 referenced addresses are even named.

> [!check] Downgraded 2026-06-18: under the **modding-grade** scope ([[Blocker - Decompilation has no build or symbol substrate|B1]]), a full symbol map is **optional QoL**, not a blocker. A lightweight address→name store (exportable via [[API - symbols]]) is worth keeping for note-queryability; whole-image symbol recovery is only needed for a matching decomp.

**Severity:** ~~Medium~~ → **Optional (QoL)** · **Impact:** Low (modding) / Medium (decomp) · **Confidence:** CONFIRMED · **Difficulty:** Medium / High

## What is known (evidence)
- `strings SCUS_942.88` yields **no** original `.c`/function symbols — the EXE is stripped (no symbol table, no RTTI, no debug build).
- Names are addresses (`ORIGINAL ADDRESS : fcn.80053814`); globals are macro-aliased addresses in `re_types.h`. Across `src_re/` + `tools/` only **~35 distinct `fcn.<addr>`** are named, vs **~1,070** addresses referenced in the plans/docs.
- `$gp = 0x80081d98` is load-bearing for every `[gp+off]` global and is recorded only in comments.

## Audit reconciliation (2026-06-22)
**TRUE STATUS: PARTIALLY ADDRESSED — keep Optional (QoL) / PARTIAL, do NOT close.** The body above is **stale**: the authoritative symbol map now **EXISTS** at `symbols/re_symbols.sym` (103 sorted entries, ~34 named `FUNC_` symbols, ~48 text-region), no longer merely "mentioned" or living only in prose. It **PASSES** `tools/validate_symbol_map.py` (a stray blank line + an unsorted appended block were just fixed). GAP-0018 **Verified**. It is **not** closeable: coverage is only **~2–3 % of ~1,070** referenced addresses, so whole-image symbol recovery remains open. The "names live in prose, not a queryable store" framing below is superseded by this map for the covered subset.

## Why it matters
- High naming-drift / mis-identification risk; cross-function reasoning depends on a human remembering what `fcn.8005044c` "probably" does. A matching decompilation and a reproducible disassembly both need one symbol source of truth.

## Dependencies
- **Blocked by:** [[Blocker - Decompilation has no build or symbol substrate|B1]] (no persisted disasm DB to anchor names). **Related:** [[Blocker - Function boundaries and overlays evade the static call graph|B17]]; a PAL/proto build might *carry* symbols ([[Blocker - Disc provenance is unverified|B12]]). **Related assumption:** A3.

## Research opportunity (direction only)
- A single authoritative symbol map (address → name → confidence → evidence) that both the disassembler and any future build consume — prioritizing the high-fan-in callees (`fcn.8005044c`, `fcn.80050994`, `fcn.80045678`) — would convert prose knowledge into a queryable substrate. (Direction only.)

## Evidence & sources
- vault: [[Symbols Index]] · [[API - symbols]] · [[Functions Index]]
- corpus: `src_re/re_types.h`, `src_re/*.c` (`ORIGINAL ADDRESS` banners)
- See also: [[Blockers]] · [[Risk Matrix]]
