---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - VAB sound bank format.md
aliases:
  - "Finding - VAB sound bank format"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - VAB sound bank format.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_VAB_sound_bank_format.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - VAB sound bank format
type: finding
confidence: CONFIRMED
tags: [finding, audio, vab, b5, format]
updated: 2026-06-18
---

# Finding — VAB sound-bank format (extractable offline)

> The `.VH`/`.VB` sound banks (SFX + per-level) are a **compact PS1 VAB** that parses + SPU-ADPCM-decodes **fully offline** (no jpsxdec/vgmstream needed). Closes the VAB half of [[Blocker - Audio subsystem is completely unanalyzed|B5]] (the XA-streaming half was done via jpsxdec).

**Confidence:** CONFIRMED (table-verified split + decoded to real audio) · **Established:** 2026-06-18 (B5)

## Format (compact VAB, `pBAV` magic, version 6)
`SFX/GLOBAL.VH` (4128-B header) + `GLOBAL.VB` (178224-B waveform):
- **Header (0x20):** magic `pBAV` (LE "VABp"), `version`@0x04, `vabId`@0x08, `waveformSize`@0x0C, `numPrograms`@0x12 (u16), `numTones`@0x14, `numVAGs`@0x16, masterVol/Pan@0x18. GLOBAL = **3 programs / 43 tones / 43 VAGs**.
- **ProgAtr:** 128 × 16 B @ `0x20` (always 128).
- **ToneAtr:** `numPrograms × 16 × 32 B` @ `0x820` — **compact: only for the actual programs** (not all 128). Each tone has the **center note (pitch)**, ADSR, vol/pan, and its **VAG index**.
- **VAG size table:** 256 × u16 @ `0x20 + 0x800 + numPrograms×0x200` (= `0xE20` for GLOBAL). Entry[i] = VAG size `>> 3`; VAGs are concatenated in the VB in order (Σ sizes = VB size — **verified exact: 178224**).
- **Waveform (`.VB`):** raw **SPU-ADPCM** VAGs (no per-VAG header) — 16-B blocks: byte0 = `shift | filter<<4`, byte1 = flags, bytes 2–15 = 28×4-bit samples; decode `s = ((nib<<12)>>shift) + (h1·f0 + h2·f1)>>6`, filters `f0=[0,60,115,98,122]`, `f1=[0,0,-52,-55,-60]`.

## Verified
- 43 VAGs split; Σ sizes = **178224** = exact `GLOBAL.VB` size. Decoded VAGs → 16-bit PCM, confirmed **real audio** (VAG34 = 1.34 s, peak 31627, RMS 3717, ~10 kHz). WAVs in `extracted/vab/`.
- Per-VAG sample rate comes from the tone's center-note / playback pitch (44100 used as a default for the proof WAVs).

## Implications
- All **21** VAB banks (SFX/GLOBAL + per-level) extract with the same parser → every sound effect is recoverable offline. Music is XA-streamed (no `.SEQ` on disc). **Audio subsystem now fully addressable** (XA + VAB).

## Related
[[Blocker - Audio subsystem is completely unanalyzed]] · [[Asset - LEVEL.BIN and overlays]] · [[Finding - Build toolchain and PROPACK provenance]]
- Source: offline parse/decode of `REBUILD/files/SFX/GLOBAL.{VH,VB}`
