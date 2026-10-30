---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Playbooks/Playbook - Replace FMV and streamed audio.md
aliases:
  - "Playbook - Replace FMV and streamed audio"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Playbooks/Playbook - Replace FMV and streamed audio.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Playbook - Replace FMV and streamed audio
type: playbook
status: proven end-to-end (FMV cold-boot verified; audio authoritative-decode verified)
updated: 2026-07-02
tags: [playbook, fmv, str, xa, audio, video, modding, rcg-011, leveleditor]
---

# Playbook — Replace any FMV or streamed-audio track

> One user-friendly tool, `tools/media_replace.py`, swaps A Bug's Life's movies (STR
> video) and streamed audio (XA music/voice) with your own files and bakes a bootable
> disc. Both edits are **size-preserving in-place patches** → fixed disc LBAs stay valid.
> Systems: [[Core - FMV and MDEC Playback]] · [[Finding - XA streamed music replacement]] ·
> [[Finding - FMV STR video replacement]]. **Pure asset pipeline — no C / no code cave.**

## Prerequisites (all local to the repo)

- `ffmpeg` (any input format → normalised), `mkpsxiso` (disc build).
- `jpsxdec_v2.1-beta/jpsxdec.jar` + `java` (STR video re-encode).
- `psxavenc/build/psxavenc` (XA audio encode; the tool falls back to the pure-python
  `tools/xa_audio.py` encoder if it's absent).

## 1. See what you can replace

```bash
python3 tools/media_replace.py list
```
- **AUDIO** targets = `AUDIOn:CHANNEL` (BUGXASTR). Each `AUDIOn.XA` interleaves 8 channels;
  the list shows each channel's capacity in seconds. Level themes live in AUDIO1/AUDIO2
  (~240-277 s); short cues in AUDIO3-5. **Pick a channel whose capacity ≥ your track**
  (shorter audio loops to fill; the game's software loop is preserved).
- **FMV** targets = `<dir>/<NAME>.STR` (BUGSFMV1/2/3, FMV). `fmv --probe` shows a clip's
  dimensions / frame-count / fps.

## 2a. Replace an FMV (video)

```bash
python3 tools/media_replace.py fmv --target BUGSFMV1/LEV1A.STR \
        --input my_clip.mp4 --build REBUILD/ABL_MYFMV
```
ffmpeg scales your video to the STR's dimensions and fps and loops/trims to the exact
frame count; jpsxdec re-encodes each frame into its original sector budget and patches the
STR in place; the disc is rebuilt + embed-verified. The clip's **own audio track is left
intact** (replace music separately below).

- **Fit failures:** if jpsxdec can't compress a frame small enough (very busy footage), it
  errors clearly — use a darker/simpler/lower-detail source. The retail cutscenes are
  low-motion, so most stylised clips fit.
- Cutscene→file map is the FMV.BIN manifest order (see [[Core - FMV and MDEC Playback]]):
  `TT`/`DLOGO`/`AD` = boot logos, `LEVnA/nB` = per-level intros, `INTRO/ALT*/LOSE` = story.

## 2b. Replace streamed audio (music / voice)

```bash
# by explicit channel …
python3 tools/media_replace.py audio --target AUDIO1:0 --input my_track.mp3 --build REBUILD/ABL_MYAUDIO
# … or by level (L1..L15) — the tool knows each level's gameplay-theme channel:
python3 tools/media_replace.py audio --target L2     --input my_track.mp3 --build REBUILD/ABL_L2MUSIC
```
ffmpeg → 37800 Hz stereo; psxavenc encodes XA-ADPCM; the payload is spliced into that
channel in place (subheaders/EOF/loop bytes preserved). **Every level's theme is mapped**
(`list` prints it; L1→AUDIO1:0 … L15→AUDIO2:6) — see the all-level table in
[[Finding - XA streamed music replacement]]. Pick a channel/level whose capacity ≥ your track.

## 3. Multiple edits in one disc

Skip `--build`, write each patch with `-o`, then batch them:
```bash
python3 tools/media_replace.py fmv   --target BUGSFMV1/LEV1A.STR --input clip.mp4 -o /tmp/LEV1A.STR
python3 tools/media_replace.py audio --target AUDIO1:0 --input song.mp3 -o /tmp/AUDIO1.XA
python3 tools/media_replace.py build -o REBUILD/ABL_MEDIA \
        --patch files/BUGSFMV1/LEV1A.STR=/tmp/LEV1A.STR \
        --patch files/BUGXASTR/AUDIO1.XA=/tmp/AUDIO1.XA
```

## Rules (enforced by the tool)

1. **Size-preserving only.** Both patches keep the file byte-length identical, so the
   fixed-LBA `REBUILD/abl.xml` rebuild stays valid (build aborts if a patch changed size).
2. **Pristine tree is never mutated** — `build` stages over copies and restores afterward.
3. **Verify on a cold boot**, not a save state (states snapshot old streamed media).
4. Match capacity: audio track ≤ channel seconds; video frames must fit the sector budget.

## Verification done

- **FMV**: custom clip baked into `LEV1A.STR`, cold-booted → plays in the Level-1 cutscene
  (movie `flik_to_level01_stall`, ~frame 3534). File byte-size unchanged.
- **Audio**: 440/660 Hz tone spliced into `AUDIO1:0`; authoritative jpsxdec re-decode reads
  exactly 440 Hz L / 660 Hz R, stereo 37800 Hz; file byte-size unchanged; embed-verified.

## Provenance

Built in the RCG-011 media-replacement session (2026-07-02) on top of the proven XA pipeline
([[Finding - XA streamed music replacement]]) + jpsxdec frame replacement
([[Finding - FMV STR video replacement]]). Tool: `tools/media_replace.py` (reuses
`tools/xa_audio.py`).
