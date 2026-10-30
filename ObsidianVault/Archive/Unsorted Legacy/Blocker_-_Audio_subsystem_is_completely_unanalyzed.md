---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Blockers/Blocker - Audio subsystem is completely unanalyzed.md
aliases:
  - "Blocker - Audio subsystem is completely unanalyzed"
migration_action: needs_review
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Blockers/Blocker - Audio subsystem is completely unanalyzed.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Blocker - Audio subsystem is completely unanalyzed
type: blocker
id: B5
severity: LOW
category: audio
confidence: CONFIRMED
tags: [blocker, low, audio, xa, vab, spu]
updated: 2026-06-22
---

# 🟢 B5 — Audio (XA streaming + VAB sound banks) is 0 % touched

> ⚠️ **Title is FALSE** (audit 2026-06-22): the audio subsystem is NOT "completely unanalyzed." The asset-format/extraction half is FULLY RESOLVED (parser + full bulk dump, below). The title now refers only to the still-open **runtime audio-engine path** (GAP-0031). See [[#Audit reconciliation (2026-06-22)]].

> Both audio classes on the disc are entirely unexamined: **~241 MB of CD-XA streaming audio** and **21 VAB sound banks**. No tool, no decoder, no note. The only audio artifact the project has produced is the observation that two `SsVab*` functions exist in the EXE. For a preservation/full-RE effort this is the whole soundtrack and SFX layer missing.

> [!check] Update (2026-06-18) — **RESOLVED.** Both audio classes are now extractable: **XA streaming** via jpsxdec (8 stereo channels proven, Phase 1f) and **VAB sound banks** via a pure-offline parser + SPU-ADPCM decoder — `GLOBAL.VAB` split into 43 VAGs (table-verified) and decoded to real WAV audio → [[Finding - VAB sound bank format]]. All 21 VAB banks use the same parser; SFX fully recoverable. (No `.SEQ` on disc → music is XA-streamed.) **Severity → Low** (mechanical bulk-extraction remains, but every format is solved).

> [!check] **MUSIC REPLACE PROVEN (2026-06-23).** The runtime XA cue→channel half is now partly closed: LEVEL01 gameplay music = `AUDIO1.XA` channel 0 (CONFIRMED in-game), engine decompiled (`src_re/music_8004699c.c`), and a full MP3→XA→disc replacement pipeline works end-to-end (`tools/xa_splice.c` / `tools/xa_audio.py` + `tools/build_music_disc.py`). → [[Finding - XA streamed music replacement]].

> [!check] **BULK-EXTRACTED (2026-06-18).** Mechanical residual now done — the full audio set is dumped to `extracted/`: **all 21 VAB banks → 1771 VAG WAVs** (`extracted/audio_vab/<bank>/vagNN.wav`, 35 MB; my generalized compact-VAB parser handled every bank's header), and **all 5 `AUDIO*.XA` → 40 channel WAVs** (`extracted/audio_xa/AUDIONXA[c].wav`, 630 MB; jpsxdec `-a audio -audfmt wav`, 8 interleaved streams per file). **Audio extraction is 100% complete.**

**Severity:** ~~Major~~ → **Low** (formats solved) · **Impact:** High · **Likelihood:** Low · **Confidence:** CONFIRMED · **Difficulty:** Low

## Audit reconciliation (2026-06-22)
- **Title "completely unanalyzed" is categorically FALSE.** The asset/extraction half is fully resolved and repo-backed: `tools/extract_vab.py` (committed VAB parser + SPU-ADPCM decoder, all 21 banks) → `extracted/audio_vab/` (1771 VAG WAVs); `extracted/audio_xa/` (40 XA channel WAVs).
- **TRUE STATUS = PARTIALLY ADDRESSED.** Asset-format/extraction = FULLY RESOLVED. The **runtime engine path is genuinely OPEN** — see **GAP-0031**: `SsUtKeyOn`/`SpuSetKey` call sites, music-vs-SFX dispatch, and the XA cue→channel map are not yet traced.
- Frontmatter `severity` reconciled MAJOR → **LOW** to match the body (formats solved; only the bounded runtime-engine gap remains).
- `REBUILD/files/BUGXASTR/AUDIO1.XA … AUDIO5.XA` — **~241 MB** (91/97/45/8.4/9.9 MB); CD-XA interleaved subheaders (`01 00 64 01 …`). The EXE references `\BUGXASTR\AUDIOn.XA;1` and links libcd's `CdlSetfilter`/`CdlReadS` (the XA streaming path).
- `SFX/GLOBAL.VB`+`GLOBAL.VH` plus per-level banks (`LEVEL01/LEVEL1A.VH/.VB`, …) — **21 `.VH` + 21 `.VB`**. `GLOBAL.VH` begins with the standard PS1 VAB magic `VABp`. The EXE's only game-authored debug strings are `SoundFX SsVabOpenHead : failed!` and `Sound FX SsVabTransBody : failed!` (PsyQ libsnd/libspu).
- **No `.SEQ`/`.SEP`** sequence files were found on disc → music is likely XA-streamed (open question).
- No tool in `tools/` touches `.XA`/`.VH`/`.VB`; no doc mentions ADPCM/VAB.

## Why it matters
- Music, sound effects, and likely voice. A preservation effort that cannot decode these is missing the entire audio dimension; an RE effort cannot claim subsystem coverage.
- Note: audio/SPU timing is explicitly **not reproducible** on the harness ([[API - determinism]]), so audio behavior can't be verified the way geometry is — extraction is offline/file-based, which is fine because the formats are solved.

## Dependencies
- Largely **independent leaf** subsystem. Minor relation to [[Blocker - Original toolchain ground-truth is unmined|B13]] (PsyQ libsnd/libspu identity helps locate the load calls).

## Research opportunity (direction only)
- The formats are industry-solved (XA-ADPCM, VAB) and handled by existing public tools, so the gap is cheap to retire offline: demux/decode the `.XA` per channel and map channels to in-game cues via the EXE's `CdlSetfilter` sites; split each `VH`/`VB` into VAG samples; and settle whether any sequence data exists or music is purely XA. (Direction only — no implementation here.)

## Evidence & sources
- vault: [[Asset - LEVEL.BIN and overlays]] (names `SFX`/`BITS`) · [[Assets]] · [[API - determinism]]
- corpus (disc): `REBUILD/files/BUGXASTR/*.XA`, `REBUILD/files/SFX/GLOBAL.{VH,VB}`, EXE `SCUS_942.88` (`SsVabOpenHead`, `SsVabTransBody`, `CdlSetfilter`)
- See also: [[Blockers]] · [[Risk Matrix]] · [[Blocker - FMV video is completely unanalyzed]]
