---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Byte-exact disc reproduction is unproven.md
aliases:
  - "Blocker - Byte-exact disc reproduction is unproven"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Byte-exact disc reproduction is unproven.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Byte-exact disc reproduction is unproven
type: blocker
id: B4
severity: MEDIUM
category: build-reproduction
confidence: LIKELY
tags: [blocker, medium, build-reproduction, disc, mkpsxiso]
updated: 2026-06-22
---

# 🔴 B4 — Byte-exact disc reproduction is unproven (rebuild verifies "boots", not "identical")

> The rebuild pipeline proves a *patched* image **boots** and that the one edited file matches — never that the whole image is bit-for-bit faithful to the original, and never that a *from-source* rebuild could reproduce the retail disc. For modding that is acceptable; for the "build-reproduction feasibility" and preservation scope it is a core gap.

> [!check] Update (2026-06-18, Phase 2c): **whole-image byte-exact rebuild is PROVEN** — `mkpsxiso` on `REBUILD/abl.xml` reproduced the master with **0 / 313,897 sectors differing** → [[Finding - Disc rebuild is byte-exact]]. This blocker **narrows** to (a) size-changing edits / LBA shifts and (b) byte-exact editing of *compressed* assets (needs a PROPACK encoder → [[Blocker - Recompressor cannot reproduce original compression|B14]]). Executable-from-source is separate ([[Blocker - Decompilation has no build or symbol substrate|B1]]). **Severity effectively downgraded to Medium.**

**Severity:** ~~Critical~~ → **Medium** (post-2c) · **Impact:** High · **Likelihood:** Low (core proven) · **Confidence:** CONFIRMED (round-trip = 0 diff) · **Difficulty:** Medium (only the edit-cases remain)

## Audit reconciliation (2026-06-22)
**True status: PARTIALLY ADDRESSED.** Severity **Medium is correct** and frontmatter now matches the body.
- **Independently reproduced during audit:** the UNPATCHED whole-image rebuild is genuinely byte-exact — `mkpsxiso` from `REBUILD/abl.xml` → `cmp` vs the master `.bin` reported **0 bytes differ** (738,285,744 B identical). The core round-trip claim holds.
- **Still-open residuals (this blocker stays open):**
  - **LBA-shift handling for size-growing edits is UNTESTED.** `REBUILD/ABL_LBA_SHIFT_TEST.cue` is an 81-byte bare `.cue` with no accompanying `.bin` or report — i.e. the test was never actually run.
  - **Byte-exact editing of *compressed* assets** remains blocked on [[Blocker - Recompressor cannot reproduce original compression|B14]] (audit: original-byte reproduction NOT achieved; ~1.4× literal stream).
  - The whole-image diff is a **one-off manual `cmp`**, not wired into any regression script.

## What is known (evidence)
- The workflow (`tools/rebuild_with_patched_dat.py`, [[Asset - Disc image and rebuild]]) extracts with `dumpsxiso`, stages a patched file, rebuilds with **mkpsxiso**, and verifies only the **embedded patched file's SHA-1 + its LBA** — *not* a whole-image hash. EDC/ECC, sector gaps, volume timestamps, and XA interleave are delegated to mkpsxiso and **unverified vs the original**.
- The corpus authority states the byte-exact whole-image rebuild is **unproven** (`docs/GEOMETRY_RE_PLAN.md` / `docs/TOOLING.md`); only size + LBA + embedded SHA-1 are checked.
- Size-changing edits shift LBAs: the seed-move test grew LEVEL.RAW by 1242 B but only "**stayed within the same 366 sectors → no LBA shift**" — a *lucky margin*, not a general solution; the rest-of-disc relocation story for larger edits is untested ([[Finding - LEVEL.RAW is compressed]]).
- The recompressor is **literal-only (~1.02× size) and has never been booted on console/emulator** ([[Blocker - Recompressor cannot reproduce original compression|B14]]); the original packer was **PROPACK 2.29** ([[Blocker - Original toolchain ground-truth is unmined|B13]]), so reproducing original compression would require a PROPACK-equivalent encoder.
- There is **no Redump / whole-disc checksum** anywhere ([[Blocker - Disc provenance is unverified|B12]]), so even the *baseline* a byte-exact rebuild would target is unconfirmed.

## Why it matters
- "Build reproduction feasibility" is an explicit scope area. Preservation-grade "reproduce the original from sources" is **not demonstrated**, and even modding edits that change a file's size are unproven beyond one fortunate case.
- A from-source matching rebuild additionally needs the original toolchain (compiler/linker/packer) — see B13.

## Dependencies
- **Depends on:** [[Blocker - Disc provenance is unverified|B12]] (baseline) · [[Blocker - Recompressor cannot reproduce original compression|B14]] · [[Blocker - Original toolchain ground-truth is unmined|B13]] · [[Blocker - LEVEL.RAW chunk inventory is mostly unidentified|B9]] (precise chunk byte-map). **Related assumptions:** A4, A10.

## Research opportunity (direction only)
- The cheapest clarifier is to define the *target* (boots vs byte-identical) and to measure the gap: a whole-image diff of an **unpatched** `dumpsxiso → mkpsxiso` round-trip would quantify exactly how far mkpsxiso output sits from the original (sector layout, gaps, XA interleave, EDC/ECC, timestamps). That number tells you whether byte-exact rebuild is reachable at all, and what an LBA-shift/size-budget story must cover for size-changing edits. (Direction only.)

## Evidence & sources
- vault: [[Asset - Disc image and rebuild]] · [[Tools Catalog]] · [[Finding - LEVEL.RAW is compressed]] · [[Finding - Relocation-aware DAT append]]
- corpus: `tools/rebuild_with_patched_dat.py`, `docs/TOOLING.md`, `docs/GEOMETRY_RE_PLAN.md`, `REBUILD/abl.xml`
- See also: [[Blockers]] · [[Risk Matrix]]
