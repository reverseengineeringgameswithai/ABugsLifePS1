---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Struct and type recovery is shallow.md
aliases:
  - "Blocker - Struct and type recovery is shallow"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Struct and type recovery is shallow.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Struct and type recovery is shallow
type: blocker
id: B16
severity: LOW
category: struct-recovery
confidence: CONFIRMED
tags: [blocker, medium, structs, types]
updated: 2026-06-22
---

# 🟡 B16 — Struct / type recovery is shallow (2 structs; most fields and globals untyped)

> The project has recovered exact *offsets* for a couple of records but the *semantics* of most fields — and nearly all globals — remain unknown. Without a real type system, higher subsystems can't be expressed in C and field edits stay trial-and-error.

> [!check] Downgraded 2026-06-18: under the **modding-grade** scope ([[Blocker - Decompilation has no build or symbol substrate|B1]]), struct recovery is **optional QoL** — recover record layouts only as specific edits require, not as a blocker. (Type-0x3f, ContactRecord, collision/plane records are already mapped enough for current modding.)

**Severity:** ~~Medium~~ → **Optional (QoL)** · **Impact:** Low (modding) / Medium (decomp) · **Confidence:** CONFIRMED · **Difficulty:** Medium–High

## What is known (evidence)
- `re_types.h` defines exactly **two** structs: `Type3FEntry` (0x10, fully mapped) and `ContactRecord` (0x38, now **nearly fully named** in `src_re/re_types.h` — only `unk37` remains UNKNOWN). The header's discipline forbids speculative fields (good practice) — but that means most fields are unnamed.
- `ViewStruct` in `pickup_projector_800253e8.c` is partial (`_pad10`, `_pad1c`; only camera + matrix rows named; origin "UNVERIFIED").
- Dozens of globals are used as bare addresses with contents "UNKNOWN" (`0x800822f4`, `0x800910a4`, `0x80078d84`, metadata tables `0x80079e30`/`0x8007941c`). Sector/plane/output record **tails** are UNKNOWN ([[MEM - Collision plane record]]).

## Audit reconciliation (2026-06-22)
**TRUE STATUS: TRULY UNRESOLVED — keep OPEN / Optional.** Only **2–3 structs** are recovered across a **~470 KB** image; most fields and nearly all globals remain untyped. Minor refresh: `ContactRecord` is now **nearly fully named** (only `unk37` UNKNOWN), not "~12 unnamed fields." This narrows one record but does not change the overall verdict — struct/type recovery stays shallow and OPEN, pursued per-edit as a QoL item.

## Why it matters
- Type ambiguity blocks decompiling any function that manipulates these structs; render/collision/AI cannot be expressed in C until their records are typed; field-level edits remain empirical.

## Dependencies
- **Blocked by:** [[Blocker - Decompilation has no build or symbol substrate|B1]]. **Related:** [[Blocker - LEVEL.DAT non-pickup records are undecoded|B10]].

## Research opportunity (direction only)
- The metadata tables (`0x8007941c` constructor rows, `0x80079e30` render rows) and the DAT record format are natural drivers for struct recovery; promoting `unkNN` only with consumer evidence (the project's existing discipline) keeps it honest. (Direction only.)

## Evidence & sources
- vault: [[MEM - Contact array 800B0D18]] · [[MEM - Type-0x3f placement record]] · [[MEM - Collision plane record]] · [[Symbols Index]]
- corpus: `src_re/re_types.h`, `src_re/pickup_projector_800253e8.c`
- See also: [[Blockers]] · [[Risk Matrix]]
