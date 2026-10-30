---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - XA streamed music replacement.md
aliases:
  - "Finding - XA streamed music replacement"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - XA streamed music replacement.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_XA_streamed_music_replacement.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - XA streamed music replacement
type: finding
confidence: CONFIRMED
tags: [finding, audio, xa, music, b5, gap-0031, modding]
updated: 2026-06-23
---

# Finding — XA streamed music: cue→channel map + replacement pipeline

> LEVEL01's **sustained gameplay music = `BUGXASTR/AUDIO1.XA`, interleaved channel 0** (258 s, 37800 Hz / 4-bit / stereo XA-ADPCM), **CONFIRMED in-game**: a rebuilt disc with that channel's payload swapped plays the new track and loops. Closes the practical half of [[Blocker - Audio subsystem is completely unanalyzed|B5]] / GAP-0031 (runtime cue→channel + asset replace). Decompiled engine: `src_re/music_8004699c.c` + `src_re/audio_music.h`.

**Confidence:** CONFIRMED (in-game music swap + 55.8 dB round-trip from the rebuilt disc) · **Established:** 2026-06-23

## Engine path (decompiled — see [[Core - Runtime Audio Path]])
- `music_start()` **FUNC_8004699c(packed_id)**: `file = packed_id>>3` (→ AUDIO(file+1)), `channel = packed_id&7`. Builds `CdlFILTER{file=1, chan}` → `CdControlB(CdlSetfilter)` @ `0x80046a6c`, then `CdlSetmode 0xe8` (Speed|ADPCM|SectorSize|SubheaderFilter), `CdlSetloc`, **`CdlReadS` (0x1b) @ `0x80046aa0`**, `CdlDemute`.
- **XA stream table** RAM `0x800772c8` (EXE off `0x67ac8`): 5 × 12-byte `{*name, CdlLOC start, u32 size}`, record N → AUDIO(N+1); `start`/`size` filled at runtime by `CdSearchFile` (`xa_open` FUNC_80045e00).
- **Looping is SOFTWARE** (`music_poll` FUNC_80046828): per frame it polls the CD position and, at track end, re-issues SetFilter+Setloc+ReadS at the saved start — **not** the XA EOF subheader bit. ⇒ a size-preserving payload swap keeps the loop identical.

## Cue→channel facts
| | value |
|---|---|
| LEVEL01 gameplay theme | **AUDIO1 ch0** (packed id 0x00) — CONFIRMED in-game |
| LEVEL01 LOAD-screen cue | AUDIO3 ch2 (packed id 0x12), ~12 s — a transient, NOT the loop |
| selection default | engine reset `FUNC_8004fa40` → area ctr `0x8008243c=0` → switch `0x8001b3c4` case 0 → music_id 1 → a0=0 |

> **GOTCHA:** the live `CdlSetfilter` trace at the load frame caught AUDIO3 ch2 and would have mis-targeted the build. Trace *into* gameplay and cross-check channel capacity (a 12 s clip ≠ a level theme).

## All-level gameplay-theme map — SOLVED (2026-07-03)

Traced across **all 15 level save states** (`level01.sav`…`level_15.sav`): the resident
music id `G_MUSIC_ID` (`0x8008245c`) **= the level number**, and `packed_id = id − 1` (as in
`level_music_start`). So **level N → packed (N−1) → `AUDIO{((N-1)>>3)+1}` : channel `(N-1)&7`**:

| Lv | target | Lv | target | Lv | target |
|---|---|---|---|---|---|
| 1 | AUDIO1:0 | 6 | AUDIO1:5 | 11 | AUDIO2:2 |
| 2 | AUDIO1:1 | 7 | AUDIO1:6 | 12 | AUDIO2:3 |
| 3 | AUDIO1:2 | 8 | AUDIO1:7 | 13 | AUDIO2:4 |
| 4 | AUDIO1:3 | 9 | AUDIO2:0 | 14 | AUDIO2:5 |
| 5 | AUDIO1:4 | 10 | AUDIO2:1 | 15 | AUDIO2:6 |

**Evidence (four independent lines):** (1) `G_MUSIC_ID` reads a clean 1…15 across the saves;
(2) the decode matches the **in-game-confirmed** LEVEL01 = AUDIO1:0; (3) the **live CD read
position** (`emulator.getCdromState.current_lba`) during each level's gameplay lands in
**AUDIO1's LBA range (183718–222709) for L1–L8** and **AUDIO2's (222710–264581) for L9–L15**,
directly confirming the file split; (4) the 15 targets fill exactly the long-theme channels
(AUDIO1 ch0-7 + AUDIO2 ch0-6, all ≥233 s) with no gaps — the one short AUDIO2 channel (ch7,
11 s) and AUDIO3-5 (short cues) are correctly *not* level themes. Closes the "all-level music
cue table" residual of **RCG-011**. (Note: `last_sector_subheader.channel` is NOT the selected
channel — the drive physically reads every interleaved sector — so channel rests on the
confirmed packed encoding + L1 ground truth, not that field.)

## Replacement pipeline (reproducible)
1. `ffmpeg -i in.mp3 -ar 37800 -ac 2 -c:a pcm_s16le out.wav`
2. `psxavenc -t xa -f 37800 -c 2 -b 4 out.wav out.xa`  (channel payload only is used; `-F/-C` irrelevant)
3. `tools/xa_splice splice <AUDIOn.XA> <chan> out.xa edited.XA`  (C; `tools/xa_audio.py splice` is the Python equivalent) — in-place payload swap, loop-fills, preserves every subheader/EOF/EDC byte → identical size.
4. `tools/build_music_disc.py --spliced edited.XA --channel <chan> ...` → `mkpsxiso` rebuild (XA files are `type="mixed"` raw copy) + byte-exact embed verify + pristine restore.

**Channel capacities (s):** AUDIO1 = 258/233/252/237/249/241/254/245 (all level themes); AUDIO2 ch0-6 ≈239-277 (ch7=11); AUDIO3 ch3/4/5 ≈125 (music), ch0/1/2/6/7 ≈11-12 (short cues). To replace a level's *full* long track, target an AUDIO1/AUDIO2 channel ≥ the track length.

**Deliverable (LEVEL01 + musicForLevel1.mp3):** `REBUILD/ABL_MUSIC_L1.bin` / `.cue`.

> **Now wrapped by a user-friendly tool:** `tools/media_replace.py audio --target AUDIOn:C
> --input <any audio file> --build <out>` runs this whole pipeline (ffmpeg → psxavenc →
> splice → rebuild + embed-verify) for any channel. See [[Playbook - Replace FMV and streamed audio]].

## Related
[[Core - Runtime Audio Path]] · [[Finding - VAB sound bank format]] · [[Finding - FMV STR video replacement]] · [[Playbook - Replace FMV and streamed audio]] · [[Blocker - Audio subsystem is completely unanalyzed]] · [[Core - CD Streaming and Caching]]
