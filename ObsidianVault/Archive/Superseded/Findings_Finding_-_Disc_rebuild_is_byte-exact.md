---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Disc rebuild is byte-exact.md
aliases:
  - "Finding - Disc rebuild is byte-exact"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Disc rebuild is byte-exact.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Disc_rebuild_is_byte-exact.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - Disc rebuild is byte-exact
type: finding
confidence: CONFIRMED
tags: [finding, disc, rebuild, build-reproduction, mkpsxiso]
updated: 2026-06-18
---

# Finding — The disc rebuild is byte-exact (dumpsxiso → mkpsxiso round-trips the master)

> Measured 2026-06-18 (Phase 2c): rebuilding the project's `REBUILD/abl.xml` with **mkpsxiso** produced an image **bit-for-bit identical** to the verified original master — **0 of 313,897 sectors differ**, 738,285,744 B, same size. This **resolves the core of [[Blocker - Byte-exact disc reproduction is unproven|B4]]**: the extract→rebuild pipeline IS byte-exact, including the system/IP area, ISO9660 descriptors, EDC/ECC, inter-file gaps, and the Form2 XA/STR sectors.

**Confidence:** CONFIRMED (whole-image byte diff = 0) · **Established:** Phase 2c

## Method
- `mkpsxiso -y -o roundtrip.bin -c roundtrip.cue abl.xml` (from `REBUILD/`), then a full 2352-byte-sector diff vs `Disney-Pixar A Bug's Life (v1.0).bin` (the hash-verified USA V1.0 → [[Finding - Build toolchain and PROPACK provenance]]).
- Result: size equal; **differing sectors = 0**, differing bytes = 0 across all 313,897 sectors ⇒ `REBUILD/files/` is fully pristine (incl. `LEVEL01/LEVEL.RAW`).
- Why it works: `abl.xml` carries **explicit per-file LBA `offs`** (from `dumpsxiso`), so mkpsxiso reproduces the exact layout; `xa_edc="false"` + the recorded attributes/timestamps match the original.

## What this resolves vs. leaves open
- ✅ **Whole-image byte-exact rebuild of the *unpatched* disc — PROVEN.** Build-reproduction at the *disc-assembly* level is solved (a much stronger result than "it boots").
- **Still open:** (1) **size-changing edits** shift LBAs — a *same-size in-place* edit preserves byte-exactness, but a growing edit (e.g. a larger recompressed chunk) needs LBA-shift handling → [[Blocker - Byte-exact disc reproduction is unproven|B4]] (now narrowed). (2) Editing a *compressed* asset and staying byte-exact needs a **PROPACK-equivalent encoder** (the literal recompressor changes bytes) → [[Blocker - Recompressor cannot reproduce original compression|B14]]. (3) Rebuilding the **executable from source** is a separate problem → [[Blocker - Decompilation has no build or symbol substrate|B1]].

## Related
[[Asset - Disc image and rebuild]] · [[Blocker - Byte-exact disc reproduction is unproven]] · [[Finding - Build toolchain and PROPACK provenance]] · [[Tools Catalog]]
- Source: Phase 2c measurement; `REBUILD/abl.xml`, `tools/rebuild_with_patched_dat.py`
