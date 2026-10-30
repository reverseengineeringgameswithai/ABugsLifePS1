---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Original toolchain ground-truth is unmined.md
aliases:
  - "Blocker - Original toolchain ground-truth is unmined"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Original toolchain ground-truth is unmined.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Original toolchain ground-truth is unmined
type: blocker
id: B13
severity: RESOLVED
category: toolchain / provenance
confidence: CONFIRMED
tags: [blocker, resolved, toolchain, psyq, propack, traveller-tales]
updated: 2026-06-22
---

# 🟢 B13 — The original build pipeline (documented *on the disc*) is now captured

> A leaked developer build log and editor-state file shipped on the retail disc reveal the exact original toolchain — developer **Traveller's Tales**, **SN Systems PsyQ / PsyMake 1.11**, **Rob Northen PROPACK 2.29**, custom `lbmbugs` art tool. This ground-truth **is now captured** in [[Finding - Build toolchain and PROPACK provenance]] and [[Toolchain Census]], so the core of this blocker is **RESOLVED**.

**Severity:** Low / Resolved · **Impact:** Medium (high leverage) · **Likelihood:** High · **Confidence:** CONFIRMED · **Difficulty:** Low

## Audit reconciliation (2026-06-22)
**Status: RESOLVED (core).** The note body was stale and self-falsifying — it claimed the provenance was "uncaptured" while it has since been mined and recorded. Corrections:
- The on-disc toolchain ground-truth **IS now captured** → [[Finding - Build toolchain and PROPACK provenance]] + [[Toolchain Census]]. Captured: **PsyMake 1.11**, **PsyQ** (libs dated ≥1997-03-28 via RCS `$Id$`), **PROPACK 2.29** (= the LEVEL.RAW codec), **`lbmbugs` v2.0**.
- **Developer name corrected:** the developer is **Traveller's Tales**, *not* Iguana Entertainment. **Iguana Entertainment** was only the **PROPACK licensee** (`REGISTERED TO IGUANA ENTERTAINMENT`) — i.e. the tool registration, not the studio that built ABL. The body below is corrected accordingly.
- **Residuals are real but minor and out of scope for B13:** the exact PsyQ / `ccpsx` compiler revision and any recompile attempt are tracked under [[Gap Audit|GAP-0016]] / [[Gap Audit|GAP-0021]], not here.

## What is known (evidence)
- `REBUILD/files/LEVEL00/ERRORS.ERR` — a leaked PC build/console log on the retail disc — states: compression = **Rob Northen PROPACK 2.29** registered to its **licensee Iguana Entertainment** (`PROPACK … REGISTERED TO IGUANA ENTERTAINMENT 01-FEB-95` — a tool registration, *not* the developer); "Packing DATA files", ~53 %; a custom **`lbmbugs`** tool converts art to level RAW (`lbmbugs \play\bugs\cd\level00\level.raw \play\bugs\level00\backdrop.bgr 32 256 128`); dev tree `C:\play\bugs\`. (Developer of ABL = **Traveller's Tales**.)
- `REBUILD/files/CHARS/STATE.RST` (plaintext dev editor-state) shows `[psyq] makefile=makefile.mak`; the EXE links **PsyQ** libs (libcd/libgpu/libgte/libspu/libsnd — corroborated by `SsVabOpenHead`/`CdlSetfilter` strings) and SN Systems **PsyMake 1.11**.
- These on-disc facts have since been **captured into the vault** — see [[Finding - Build toolchain and PROPACK provenance]] and [[Toolchain Census]] (the earlier "a grep returns nothing / uncaptured" claim no longer holds). The LEVEL.RAW LZ the project independently reverse-engineered is now identified as an **RNC/PROPACK-family** codec (= PROPACK 2.29) ([[Finding - LEVEL.RAW is compressed]], [[Assumptions Register|A13]]).
- `LEVEL00` is therefore a **developer/test stage** (it ships the build log) — not previously recognized as such ([[Blocker - RE depth is LEVEL01-only|B8]]).

## Why it matters
- Pins the exact original build pipeline — the missing half of toolchain/compiler identification for any matching decompilation ([[Blocker - Decompilation has no build or symbol substrate|B1]]) and for from-source rebuild ([[Blocker - Byte-exact disc reproduction is unproven|B4]]).
- PROPACK likely packs other `.RAW`/`.ALL` assets, so the **already-solved decompressor may unlock textures and models** with little new work ([[Blocker - Character and plant model formats are unreversed|B7]], [[Blocker - Offline texture and font extraction is absent|B20]]); the `lbmbugs … 32 256 128` invocation gives palette/width/height for background decode.

## Dependencies
- **Feeds:** [[Blocker - Decompilation has no build or symbol substrate|B1]] · [[Blocker - Byte-exact disc reproduction is unproven|B4]] · [[Blocker - Recompressor cannot reproduce original compression|B14]] · [[Blocker - Character and plant model formats are unreversed|B7]] · [[Blocker - Offline texture and font extraction is absent|B20]].

## Research opportunity (direction only)
- Capturing these on-disc facts into the vault is near-zero-cost and high-leverage; testing the existing LEVEL.RAW decoder against `GFX/*.RAW`, `TERRAIN.ALL`, and `BITS/*.ALL` (and comparing to a public RNC/PROPACK decoder) would reveal how much else the solved codec already unlocks. (Direction only.)

## Evidence & sources
- corpus (disc): `REBUILD/files/LEVEL00/ERRORS.ERR`, `REBUILD/files/CHARS/STATE.RST`, EXE `SCUS_942.88` (PsyQ library + `SsVab*`/`Cdl*` strings)
- vault: [[Finding - LEVEL.RAW is compressed]] · [[Asset - LEVEL.RAW]] · [[Asset - LEVEL.BIN and overlays]] · [[Asset - Disc image and rebuild]]
- See also: [[Blockers]] · [[Risk Matrix]]
