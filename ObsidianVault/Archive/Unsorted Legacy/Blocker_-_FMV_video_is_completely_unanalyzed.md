---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - FMV video is completely unanalyzed.md
aliases:
  - "Blocker - FMV video is completely unanalyzed"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - FMV video is completely unanalyzed.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - FMV video is completely unanalyzed
type: blocker
id: B6
severity: LOW
category: video
confidence: CONFIRMED
tags: [blocker, low, video, fmv, str, mdec]
updated: 2026-06-22
---

# 🟢 B6 — FMV / MDEC video (39 `.STR`, ~385 MB) is 0 % touched

> ⚠️ **Title is FALSE** (audit 2026-06-22): the FMV layer is NOT "completely unanalyzed" — it is RESOLVED as scoped (extraction + per-STR layout + front-end sequence all done). One bounded residual remains: the MDEC decode/DMA call site *inside* the FMV.BIN overlay. See [[#Audit reconciliation (2026-06-22)]].

> The entire cinematic layer — intro, per-level cutscenes, win/lose stingers, and Disney/Pixar/title logos — is **~385 MB of MDEC `.STR`** with no extraction tool, no decoder, and no note.

> [!check] **RESOLVED / BULK-EXTRACTED (2026-06-18).** jpsxdec decodes the format (Phase 1f proved `INTRO.STR` = 320×128 MDEC, 1750 frames + XA audio). Mechanical residual now done: **all 39 `.STR` → AVI (MJPEG + audio)** in `extracted/fmv/` (627 MB; jpsxdec `-a video -vidfmt avi_mjpg`, which muxes the embedded XA audio track). Every cutscene/logo/stinger is now a playable AVI. **FMV extraction 100% complete; Severity → Low.**

**Severity:** ~~Major~~ → **Low** (extracted) · **Impact:** High · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Low–Medium (solved format)

## What is known (evidence)
- **39 `.STR` files** under `REBUILD/files/BUGSFMV1/` (LEV1A…LEV9B), `BUGSFMV2/` (`INTRO.STR` 20 MB, ALT1-3, LEV10-15, `LOSE.STR`), `BUGSFMV3/` (`DLOGO.STR`, `TT.STR`). `INTRO.STR` header `01 01 48 00 …` = the classic Sony STR/MDEC frame-sector header (`0x0148` demux size, sector type `0x8001`).
- The EXE links `LoadImage`/MDEC-adjacent GPU paths and references `fmv\fmv.bin` (the Region-B overlay that runs FMV, [[Asset - LEVEL.BIN and overlays]]).
- Each `.STR` also carries an interleaved XA audio track — also unaddressed ([[Blocker - Audio subsystem is completely unanalyzed|B5]]).

## Why it matters
- Major content (the whole front-end + cutscene sequence) and a preservation requirement. Until decoded, the cinematic layer is opaque and the `fmv.bin` overlay's role is only inferred.

## Dependencies
- **Independent leaf** subsystem; relates to [[Blocker - Function boundaries and overlays evade the static call graph|B17]] (the `fmv.bin` Region-B overlay is un-analyzed).

## Audit reconciliation (2026-06-22)
- **Title "completely unanalyzed" is categorically FALSE.** jpsxdec is in-repo; `extracted/fmv/` holds 39 AVIs matching all 39 `.STR` on disc. `FMV.BIN` is decoded as a 25-entry manifest + MDEC-player overlay. The **front-end sequence is RESOLVED** (TT → DLOGO → AD → per-level, GAP-0032) and the **trigger is CONFIRMED** (`0x8003e7c0` → `0x80046330`). See [[Core - FMV and MDEC Playback]].
- **TRUE STATUS = RESOLVED as scoped** (extraction + per-STR layout + sequence). The **single bounded residual** is the MDEC decode/DMA call site *inside* the FMV.BIN overlay (Region-B `0x800B5788+`).
- The "Research opportunity" front-end-ordering item below is now SOLVED (GAP-0032); only the overlay-internal MDEC/DMA call site remains.

## Research opportunity (direction only)
- ~~Identify the front-end ordering (`DLOGO`/`TT`/`INTRO`)~~ — **SOLVED (GAP-0032).** Remaining: trace the **MDEC decode/DMA call site inside the FMV.BIN overlay** (Region-B `0x800B5788+`) — the only part of the playback path not yet read. (Direction only.)

## Evidence & sources
- corpus (disc): `REBUILD/files/BUGSFMV{1,2,3}/*.STR`, EXE `SCUS_942.88` (`LoadImage`, `fmv\fmv.bin`)
- vault: [[Asset - LEVEL.BIN and overlays]] · [[Assets]] · [[Core - FMV and MDEC Playback]]
- See also: [[Blockers]] · [[Risk Matrix]] · [[Blocker - Audio subsystem is completely unanalyzed]]
