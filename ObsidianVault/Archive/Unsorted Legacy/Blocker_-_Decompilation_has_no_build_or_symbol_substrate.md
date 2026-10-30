---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Decompilation has no build or symbol substrate.md
aliases:
  - "Blocker - Decompilation has no build or symbol substrate"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Decompilation has no build or symbol substrate.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Decompilation has no build or symbol substrate
type: blocker
id: B1
severity: CRITICAL
category: decompilation-coverage / toolchain
confidence: CONFIRMED
tags: [blocker, critical, decompilation, toolchain, reproducibility]
updated: 2026-06-22
---

# 🔴 B1 — Decompilation has no build / link / diff / symbol substrate

> ~0.3–0.5 % of the executable is decompiled, and the C that exists **cannot be compiled, linked, or diffed against the original**. There is no toolchain, symbol map, or persisted disassembly. As a *matching/reproducible decompilation* the project is effectively unstarted; what exists is high-quality **annotated disassembly**.

> [!info] **Charter reconciliation (2026-06-20 → 2026-06-21; GAP-0043).** The recorded [[Roadmap]] charter (modding-grade goal, **decomp-forward** method) **supersedes** the earlier 2026-06-18 "B1 won't-do" decision. B1 is **in scope**, split by payoff: its *enabling* halves are **active** — the symbol map ([[Blocker - Symbol recovery has no authoritative map|B15]] → [[Gap Audit|GAP-0018]] **Verified**) and the overlay baseline ([[Blocker - Function boundaries and overlays evade the static call graph|B17]] → [[Gap Audit|GAP-0020]] In Progress) — while the **compile / link / diff substrate** ([[Gap Audit|GAP-0021]]) stays **deferred / payoff-gated**: pursued only when a concrete modding payoff (e.g. a relocation-regression oracle) justifies the toolchain cost. Matching / byte-identical decompilation is **optional** and is never required for project success. The 🔴 severity below grades the **full-RE yardstick** the [[Blockers]] dashboard uses — not the controlling charter.

**Severity:** 🔴 Critical *against the full-RE yardstick* → **deferred / payoff-gated** under the modding charter (not "won't-do"; see reconciliation above) · **Impact:** High (only under a decomp/preservation goal) · **Confidence:** CONFIRMED · **Difficulty:** High

## What is known (evidence)
- `src_re/` contains ~**9 original functions** with real C bodies (6 `.c` files + `pickup_projector_800253e8.c` + the split `pickup_handlers_*` cases) over one vertical slice: type-0x3f pickup → HUD → contact/walker → DAT parser. Header `re_types.h` defines **2 structs**.
- The resident image is `0x80010000`–`0x800827FF`, text `0x72800` = **468,991 B** (`docs/EXECUTABLE_AND_OVERLAYS.md`) → an estimated **1,875–3,126 functions**. The geometry/docs corpus references **~1,070 distinct addresses**; only ~27 are documented behaviorally ([[Functions Index]]), ~35 even named.
- A repo-wide search for `Makefile`, `*.ld`, `*.map`, `*.sym`, `splat.yaml`, `CMakeLists.txt`, `SConstruct` returns **nothing**. The `.c` files `#include "re_types.h"`, declare callees as `extern` stubs, and use absolute addresses as lvalues (`LW(...)`, `SW(0x800822f4, ...)`).
- ~~No persisted disassembly DB~~ **PARTIALLY ADDRESSED (2026-06-22):** a headless Ghidra 12.1.2 project now persists at `ghidra/project/ABLPilot` (`SCUS_942.88` imported `MIPS:LE:32` @ base `0x8000f800`, `re_symbols.sym` applied) — used as a decompiler / cross-check layer, NOT a build/matching substrate (no objects, no `.ld`/`.map`, no splat split). The r2 settings (`anal.gp=0x80081d98`) still live only in code comments, and Ghidra's `$gp` context is not yet set. Raw EXE + hand-saved excerpt `tools/level_raw_decompressor.asm` remain. See `ghidra/PILOT_REPORT.md`.
- `docs/DECOMPILATION_PLAN.md` is explicitly **non-matching / scope-limited** — there is no function census, symbol-recovery plan, or build target.

## Audit reconciliation (2026-06-22)
**TRUE STATUS: PARTIALLY ADDRESSED — keep OPEN, payoff-gated.** An exhaustive repo-wide search confirms **no build / link / asm-diff / matching-decomp substrate exists anywhere** (no `Makefile`/`*.ld`/`*.map`/`splat.yaml`/objects). A Ghidra cross-check project now exists at `ghidra/` — but it is a **decompiler / cross-check layer, not a matching-decomp substrate** (no compile→link→diff loop). Note that `ghidra/.gpr` is **0 bytes**; the live project is in `ghidra/project/ABLPilot.rep`. The 🔴 grade is against the full-RE yardstick; under the modding charter B1 stays **deferred / payoff-gated**, not closed.

## Why it matters
- Without compile→link→**asm-diff**, no decompiled body is provably accurate to the target; **regressions are undetectable** and "decompilation" cannot be verified. This is the gap between *annotated disassembly* (what exists) and a *decompilation* (the full-RE goal).
- It also blocks downstream type/symbol/boundary recovery, and any from-source disc rebuild ([[Blocker - Byte-exact disc reproduction is unproven|B4]]).

## Dependencies
- **Depends on:** [[Blocker - Disc provenance is unverified|B12]] (a trusted byte-baseline) · [[Blocker - Original toolchain ground-truth is unmined|B13]] (compiler/linker identity to even attempt matching).
- **Blocks:** [[Blocker - Symbol recovery has no authoritative map|B15]] · [[Blocker - Struct and type recovery is shallow|B16]] · [[Blocker - Function boundaries and overlays evade the static call graph|B17]] · a matching decompilation · partly [[Blocker - Byte-exact disc reproduction is unproven|B4]].

## Research opportunity (direction only)
- The first decision is *goal*: **modding-grade understanding** (current trajectory, well-served by the present approach) vs a **matching decompilation** (a far larger, different effort). The blocker only bites for the latter.
- If matching is wanted, the missing pieces are a *reproducible* disassembly project pinned to `gp=0x80081d98` and the resident map, an authoritative address→name symbol store the disassembler and any build both consume, and a per-function asm-diff loop. Where those might come from: PsyQ signature/library matching ([[Blocker - Original toolchain ground-truth is unmined|B13]]) to name SDK leaves, and the existing `src_re/` C as a spec to port into the harness.

## Evidence & sources
- vault: [[Functions Index]] · [[Symbols Index]] · [[Asset - LEVEL.BIN and overlays]] · [[API - symbols]]
- corpus: `src_re/*.c`, `src_re/re_types.h`, `docs/DECOMPILATION_PLAN.md`, `docs/EXECUTABLE_AND_OVERLAYS.md`, `tools/level_raw_decompressor.asm`
- See also: [[Blockers]] · [[Risk Matrix]]
