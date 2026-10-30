---
superseded_by:
  - SYS_game_identity_and_provenance
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Disc provenance is unverified.md
aliases:
  - "Blocker - Disc provenance is unverified"
migration_action: archive
confidence: low
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Disc provenance is unverified.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Disc provenance is unverified
type: blocker
id: B12
severity: MAJOR
category: provenance / versions-regional
confidence: CONFIRMED
tags: [blocker, major, provenance, redump, preservation, versions]
updated: 2026-06-22
---

# 🟠 B12 — The master disc image is not provenance-verified, and only NTSC-U exists

> All static RE rests on one `.bin` whose dump provenance is unverified — no Redump match, no whole-image checksum, a `v1.0` label with nothing behind it. And the corpus is single-region (NTSC-U only), foreclosing the cross-version diffing that is a primary RE technique.

**Severity:** Major · **Impact:** High (if the master is bad) · **Likelihood:** Low (it is *probably* fine) · **Confidence:** CONFIRMED (gap) · **Difficulty:** Low

## Audit reconciliation (2026-06-22)
**True status: PARTIALLY ADDRESSED** (body below was STALE — it read fully-open; corrected here).
- **Provenance half is RESOLVED.** The master `.bin` is identified as **USA V1.0**: **CRC32 `607704bb`** (the canonical Redump single-track value; V1.1 = `ed6e4cb9`), **MD5 `2c3861a3a568d0e8119693f2117d2e00`** — recorded in [[Checksum Manifest]]. The earlier "no whole-image checksum / `v1.0` unsubstantiated" claims are **false and retracted**.
- **Residuals (this blocker stays open):**
  - Formal **Redump datfile per-track comparison** still pending (cheap).
  - **Cross-region / prototype diffing is permanently out of scope** — no PAL/NTSC-J/proto media owned.

## What is known (evidence)
- `Disney-Pixar A Bug's Life (v1.0).bin/.cue` — **738,285,744 B, 313,897 sectors, MODE2/2352**, single track; file dated **2012**; `.cue` is a bare single FILE/TRACK01. ISO volume `A_BUGS_LIFE`, publisher `SCEA`, copyright `PIXAR_DISNEY`, dated 1998-10-20.
- **(Updated 2026-06-22)** The whole-`.bin` is now checksummed and version-identified: **CRC32 `607704bb` = canonical Redump USA V1.0** single-track value (V1.1 = `ed6e4cb9`), **MD5 `2c3861a3a568d0e8119693f2117d2e00`**, recorded in [[Checksum Manifest]]. (The project also records the boot-EXE SHA-1 `af43de22…` and the pristine LEVEL01-DAT SHA-1 `b376cb50…`.) The prior "no whole-image checksum / `v1.0` unsubstantiated" statement is retracted; only a formal Redump per-track datfile comparison remains.
- Exactly one region present — **NTSC-U / SCUS-94288** ("North America area"). **No PAL (SLES), NTSC-J (SLPS), prototype, or demo** anywhere for comparison.

## Why it matters
- Every offset, hash, and rebuild is anchored to an **unverified master**; a bad/modified dump would make findings subtly wrong and any preservation claim invalid. Low probability, foundational consequence.
- Cross-region / proto diffing routinely surfaces debug symbols and unused content (PAL Iguana builds sometimes ship debug strings) — its absence caps reachable depth ([[Blocker - Symbol recovery has no authoritative map|B15]]).

## Dependencies
- **Root** under [[Blocker - Decompilation has no build or symbol substrate|B1]] and [[Blocker - Byte-exact disc reproduction is unproven|B4]] (both need a trusted byte-baseline). **Related assumption:** A1.

## Research opportunity (direction only)
- Hashing the `.bin` and matching it against the Redump "A Bug's Life (USA)" datfile (recording CRC32/MD5/SHA-1 + serial) would settle provenance cheaply; acquiring the Redump PAL image (and any preview/demo) would unlock version diffing. (Direction only.)

## Evidence & sources
- vault: [[Asset - Disc image and rebuild]] · [[Assets]]
- corpus (disc): `Disney-Pixar A Bug's Life (v1.0).bin/.cue`, `SYSTEM.CNF`
- See also: [[Blockers]] · [[Risk Matrix]]
