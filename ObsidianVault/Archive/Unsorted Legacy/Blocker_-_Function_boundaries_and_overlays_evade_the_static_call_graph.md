---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Function boundaries and overlays evade the static call graph.md
aliases:
  - "Blocker - Function boundaries and overlays evade the static call graph"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Function boundaries and overlays evade the static call graph.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Function boundaries and overlays evade the static call graph
type: blocker
id: B17
severity: MEDIUM
category: function-matching
confidence: CONFIRMED
tags: [blocker, medium, function-matching, overlays, boundaries]
updated: 2026-06-22
---

# 🟡 B17 — Jump-table cases and overlay code sit outside the static call graph

> Where the binary uses jump tables and per-level overlays, the C representation is an *interpretation* with invented function boundaries, and whole bodies of overlay code are invisible to `jal`-based call-graph analysis. The static picture is therefore incomplete by construction.

> [!check] Partial progress (2026-06-18, B17): the long-open **`fcn.8005b134` role is resolved** by live trace — it's an 8-way state-handler (jump-table `0x8001b828`, `v0∈[3,10]`) that doesn't run in idle play and doesn't write player Y → [[FUNC_8005B134]]. One concrete jr-dispatched function characterized; the broader gap (overlay `LEVEL*.BIN` code, jr-tables modeled as pseudo-functions, no systematic boundary recovery) remains.

**Severity:** Medium · **Impact:** Medium · **Likelihood:** Medium · **Confidence:** CONFIRMED · **Difficulty:** High

## What is known (evidence)
- `pickup_handlers_*.c` states outright that its "functions" at `0x80054288…0x80054554` "are **not** standalone ABI functions … they are jump-table cases inside `fcn.80053814`" reusing the parent's live registers — i.e. the C invents helper signatures that don't exist in the binary ([[FUNC_80053814]]).
- [[FUNC_8005B134]] has **0 `jal` callers** (overlay/jump-table dispatched); its role is "UNKNOWN/PENDING" and *contradicts* the old G5 claim that it was the sole player-Y writer (the real writer is [[FUNC_8003633C]]). Trail helpers were also reclassified mid-project.
- Overlays are essentially un-analyzed and outside `jal`-scan: Region-A per-level `LEVEL*.BIN` MIPS code (entry `0x800B39A4`) and Region-B `fmv.bin`/`MEMORY.BIN`; the Region-A overlay **source file + ABI are UNKNOWN** ([[Asset - LEVEL.BIN and overlays]], `docs/EXECUTABLE_AND_OVERLAYS.md`). Unresolved gates remain (construct-phase byte `0x800910a4`/`0x800910f7`; allow-table `0x80078d84` contents).

## Audit reconciliation (2026-06-22)
**TRUE STATUS: PARTIALLY ADDRESSED — keep OPEN for the structural residual.** The "overlays essentially un-analyzed" framing above is now **stale**: overlay **enumeration is RESOLVED** (GAP-0020 ✅ Resolved 2026-06-22). Both swap buffers are enumerated; **three Region-A overlay verbs are CONFIRMED** — `level_overlay_init` (`0x800b39a4`), an object-spawner, and an event/update verb — with a spawn census across **20 `LEVEL*.BIN`**. What remains keeps this OPEN: the **structural** residual — `jr`/jump-table pseudo-function boundaries, **no systematic boundary recovery**, and per-scene overlay residency are still unmodeled.

## Why it matters
- A matching decomp needs exact boundaries and the real switch/`jr` structure, not helper-function fictions. Overlay-dispatched and jr-dispatched routines (including the consumers of the undecoded DAT records, [[Blocker - LEVEL.DAT non-pickup records are undecoded|B10]]) won't appear in any static call graph, so coverage estimates that ignore them are optimistic.

## Dependencies
- **Blocked by:** [[Blocker - Decompilation has no build or symbol substrate|B1]]. **Feeds:** [[Blocker - LEVEL.DAT non-pickup records are undecoded|B10]] · [[Blocker - Character and plant model formats are unreversed|B7]] (overlay/asset loaders). **Related:** [[Blocker - Symbol recovery has no authoritative map|B15]].

## Research opportunity (direction only)
- Representing jr-tables as switch-on-index within the parent function, resolving the `fcn.8005b134` vs `0x8003633c` relationship by EXEC-tracing the scripted/spawn path, and analyzing the `LEVEL.BIN`/`fmv.bin` overlays would close the largest static-coverage holes. (Direction only.)

## Evidence & sources
- vault: [[FUNC_80053814]] · [[FUNC_8005B134]] · [[FUNC_8003633C]] · [[Asset - LEVEL.BIN and overlays]]
- corpus: `src_re/pickup_handlers_80054288_80054554.c`, `src_re/source3f_dispatch_80053814.c`, `docs/EXECUTABLE_AND_OVERLAYS.md`
- See also: [[Blockers]] · [[Risk Matrix]]
