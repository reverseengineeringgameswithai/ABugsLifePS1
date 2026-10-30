---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - FMV STR video replacement.md
aliases:
  - "Finding - FMV STR video replacement"
migration_action: convert_to_canon
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - FMV STR video replacement.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_FMV_STR_video_replacement.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Finding - FMV (STR) video replacement
type: finding
status: SOLVED — custom video baked into an STR + cold-boot verified in-game
updated: 2026-07-02
confidence: CONFIRMED (frame patch is size-preserving; custom clip plays on a cold boot)
tags: [finding, fmv, str, mdec, video, jpsxdec, modding, rcg-011, leveleditor]
---

# Finding — Replacing an FMV: in-place STR frame patch (size-preserving)

> Any `*.STR` movie's video can be replaced with a custom clip by re-encoding its
> frames with **jpsxdec** into the SAME per-frame sector budget — the STR keeps its
> exact size, so the disc's fixed LBAs stay valid. **Cold-boot verified**: a custom
> "CUSTOM FMV TEST" clip baked into `BUGSFMV1/LEV1A.STR` plays in the Level-1 intro
> cutscene on a rebuilt disc. Advances the FMV half of **RCG-011**. Format background:
> [[Core - FMV and MDEC Playback]].

## How it works

- **STR container** (2336-byte Mode-2 sectors on disc): MDEC video frames striped across
  N sectors/frame, interleaved with an XA audio track. jpsxdec indexes it into a **Video
  item** (e.g. LEV1A = `320×128, 386 frames, 5 sectors/frame, 2× disc speed → 30 fps`) plus
  an **XA audio item** (mono/stereo ADPCM).
- **Frame replacement** = jpsxdec re-encodes each supplied image to an MDEC bitstream that
  fits that frame's original sector allotment and **patches the STR in place** (byte size
  unchanged). Only video sectors change; the clip's interleaved audio is untouched.
  ```
  jpsxdec -f movie.STR -x idx.idx                     # index
  jpsxdec -x idx.idx -i 0 -replaceframes replace.xml  # patch video frames in place
  ```
  `replace.xml` (schema from the jpsxdec `ReplaceFrames` class):
  ```xml
  <?xml version="1.0"?>
  <str-replace version="0.3">
    <replace frame="1">/abs/frame00001.png</replace>   <!-- 1-based frame index -->
    ...one per frame, dimensions must match the item...
  </str-replace>
  ```
- **Bit-budget caveat:** a frame too detailed to compress into its sector budget even at
  max qscale fails (`CMD_UNABLE_TO_COMPRESS_FRAME_SMALL_ENOUGH`). Dark/simple/low-motion
  content (like the game's own cutscenes) fits comfortably; very busy footage may need a
  smaller effective resolution. The tool surfaces this error clearly.

## Proof

`tools/media_replace.py fmv --target BUGSFMV1/LEV1A.STR --input testclip.mp4 --build …`:
transcoded a 6 s clip (ffmpeg → 320×128 @ 30 fps, looped to 386 frames), patched the STR
(4,559,872 B → **same size**), rebuilt the disc, and **cold-booted** via
`flik_to_level01_stall.mv.movie.json`: the custom clip renders in the LEV1A cutscene slot
(~movie frame 3534). Offline jpsxdec re-decode of the patched STR reproduces the clip 1:1.

## Every STR is replaceable — including the boot intros (verified)

The frame-patch is **format-generic**: the tool probes each STR's own dims/fps/frame-count, so
it handles any movie. Confirmed across the intro clips (all probe + replace cleanly):
`BUGSFMV3/TT.STR` (320×128, 441f @ 20fps), `BUGSFMV3/DLOGO.STR` (**320×240**, 156f @ 10fps),
`BUGSFMV2/INTRO.STR` (320×128, 1750f @ 30fps), plus the 39 `LEV*/ALT*/LOSE` clips.

**Boot intros need NO save state** — they auto-play on a cold boot. Proven end-to-end: a
custom clip baked into `TT.STR`, cold-booted, **plays during the boot logo sequence**
(orange "MODDED INTRO" at ~frame 3261, `mod`-less pure-data build `ABL_MEDIA_INTRO`).

### Disc→cutscene mapping + observed boot order
FMV play order is data-driven by the **FMV.BIN 25-entry manifest** ([[Core - FMV and MDEC Playback]]):
manifest lists `BUGSFMV3\tt` → `dlogo` → `fmv\ad` → per-level `LEVnA/nB` → `INTRO/ALT*/LOSE`.
Notes from the live boot: the **runtime boot order is DLOGO (Disney Interactive) then TT**, not
the manifest's literal TT-first order; `fmv\ad.str` is **referenced in the manifest but absent
on the disc** (the game skips it). `LEV1A.STR` = the Level-1 intro (plays right before the
Level-1 loading screen).

## Tool + reuse

`tools/media_replace.py` (`list` / `fmv` / `audio` / `build`) — accepts any ffmpeg-readable
video, matches the STR's dims/fps/frame-count automatically, patches in place, and
(optionally) rebuilds + embed-verifies the disc. Recipe:
[[Playbook - Replace FMV and streamed audio]]. This is a **pure asset pipeline** (jpsxdec
offline) — it does NOT touch the in-engine MDEC-player overlay (the residual call site in
[[Core - FMV and MDEC Playback]] is unrelated to replacement).

## Related

[[Core - FMV and MDEC Playback]] · [[Finding - XA streamed music replacement]] ·
[[Playbook - Replace FMV and streamed audio]] ·
[[Finding - File loading is by-name (LBA-shift tolerant)]] · [[Asset Extraction Pipeline]]
