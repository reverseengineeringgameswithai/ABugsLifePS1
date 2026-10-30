---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md
aliases:
  - "Finding - Longer FMV playback (normal-speed extension RE)"
migration_action: convert_to_canon
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_Longer_FMV_playback_(normal-speed_extension_RE).md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Finding — Longer FMV playback (normal-speed extension RE)

**Goal:** replace a short FMV (e.g. a ~13–22 s cutscene) with a **longer** clip (~30 s) that
plays at **normal speed** with a proper end **fade**, instead of the size-preserving tool's
time-compression (which speeds a long clip up to fit the movie's fixed length).

**Status (2026-07-04): SOLVED + shipped.** A real 30 s clip plays at normal speed with a fade in
the TT slot, cold-boot verified (VRAM-24bit capture shows the clip; `[0x80131EEE]=902`, streamed
+4365/4510 ≈ 29 s). One-command tool: `tools/replace_fmv_long.py`. The cap was a **hardcoded
per-movie frame-count table in FMV.BIN** — patch that entry to the clip's frame count (2 bytes)
and the game plays the whole thing. See the "SOLVED" section below, `src_re/fmv_player_streaming.c`,
[[Core - FMV and MDEC Playback]], [[Finding - FMV STR video replacement]].

## The cap = a hardcoded per-movie frame-count table in FMV.BIN (SOLVED)
Overlay decode loop `0x800B6B28`: each frame, `total = *(s16*)0x80131EEE; if (cur_frame >= total-2)
raise completion`. `total` is set at movie-start `FUNC_800B6D68(a1=total)` `0x800B6DC0` from a
**40-case jump table** (`0x800B62D4..`, `addiu a1,zero,<count>` per movie, manifest order —
TT=440, DLOGO=156, LEV1A=386, INTRO=1750, LOSE=281, all matching real frame counts). The overlay
loads verbatim to `0x800B5788`, so each count is a **2-byte edit in FMV.BIN** (offsets 0x0B4C(TT)
… 0x0DD0(LOSE); tool `tools/fmv_frame_table.py`). PROVEN: TT 0x0B4C 440→900 → game streamed the
full +4357/4500 (~29 s). Fix = patch the target movie's count to the replacement STR's frame count.
The earlier "cap = DLOGO's 2340 sectors" was a coincidence (441 frames × 5 ≈ 2334).

**Pipeline (`tools/replace_fmv_long.py`):** N = round(30 × clip_seconds) frames (30 fps template),
author an N-frame STR (INTRO-prefix template + jpsxdec re-encode + length-scaled baked fade + XA
audio splice), patch the movie's FMV.BIN frame count to N, rebuild disc with LBA reflow. Any length
up to the 1750-frame (~58 s) INTRO-template limit. Deliverable: `build/ABL_USER30` (user's 30 s clip
in the TT slot).

## What was proven

### 1. Authoring an arbitrary-length STR (offline, proven)
jpsxdec cannot *create* an STR, only replace frames. So a longer STR is authored by:
1. **Template = a sector-prefix of a long native STR.** `INTRO.STR` is 1750 frames / 8768
   sectors, uniform **5 sectors/frame** @ 320×128/30fps. Truncate the raw 2336-byte sectors to
   `N*5` sectors → a valid **N-frame** template (jpsxdec re-indexes it cleanly; audio item
   intact). 900 frames = 4500 sectors = 30 s.
2. **Bake the video** (incl. a `fade=t=out` at the end) → 900 PNGs at native 30 fps →
   `jpsxdec -replaceframes` into the template (same per-frame sector budget).
3. **Splice the audio** (`xa_audio.splice_payloads`, mono 18900 Hz ch1) — see
   [[media-replace-fmv-audio]].
Result decodes back as a clean 900-frame / 30 s movie with the fade (frame 895 mean-brightness
12 = fading). Artifacts: `build/LEV1A_long30.str`, `build/TT_smooth30.str`.

### 2. Disc rebuild with an LBA reflow (tool: `tools/build_long_fmv_disc.py`)
FMV/XA files are packed **back-to-back at pinned LBAs** with zero slack (`REBUILD/abl.xml`
`offs=`), so a bigger STR must shift everything after it. The tool keeps all files **before**
the target pinned (game-logic region untouched) and bumps every `offs=` after the target by the
sector delta. Built discs: `build/ABL_TTLONG` (testsrc), `build/ABL_TTSMOOTH` (smooth),
`build/ABL_LONGFMV` (LEV1A). All build + embed-verify OK.

### 3. Longer STR LOADS + STREAMS by name (CONFIRMED live) — resolves [[Blocker - RE depth is LEVEL01-only]] GAP-0025 for FMV
On the reflowed `ABL_TTSMOOTH` disc, cold-boot (DuckStation debugger, isolated instance):
- The CD read LBA climbs **linearly at the real-time 2× rate (150 sectors/s)** through the
  new TT range (LBA 294035+), i.e. the game **finds the resized/shifted TT by name**
  (`FUNC_80046330`/`CdSearchFile`, runtime ISO directory — no hardcoded FMV LBAs) and **streams
  our custom content** (user visually confirmed the replacement clip plays after the Disney
  logo). This confirms the by-name loader tolerates in-region LBA shifts for FMV/XA.

## The blocker: playback length is capped by game logic, not the file

Measured **max CD LBA reached** while each TT streamed (deterministic paused stepping):

| disc | TT file | max stream | duration | note |
|---|---|---|---|---|
| pristine | 441 f / 3328 sec | **+3437** | 22.9 s | plays its **full** file (EOF at last sector 3327) |
| ABL_TTLONG (testsrc) | 900 f / 4500 sec | +2336 | 15.6 s | capped |
| ABL_TTSMOOTH (smooth) | 900 f / 4500 sec | +2334 | 15.6 s | capped (same → **content-independent**) |

The cap is **content-independent** (testsrc high-detail and smooth low-detail stop at the same
sector) → **not** a decode timeout (`"time out in decoding !"` string ruled out). Ruled out by
inspection: **not** the ISO directory size (correct: 4500 sectors = 9,216,000 B = 4500×2048),
**not** an XA EOF/EOR submode bit (our file has none; built disc has none), **not** a structural
discontinuity (frames 466→469 continuous, channel 1 throughout).

**Key clue:** the cap **≈ 2340 sectors = exactly DLOGO.STR's length** (DLOGO = 156 f @ 10 fps =
15.6 s = 4,792,320 B / 2048 = 2340 sectors). DLOGO is the FMV that plays **immediately before**
TT. Pristine TT uses **its own** length; our resized TT plays for **DLOGO's** length. ⇒ Strong
hypothesis: the intro sequencer holds a **per-FMV playback length / frame-or-sector budget** in a
variable that our size-changed TT fails to refresh, so it falls back to the **previous FMV's**
extent. The resident FMV **player loop is at ~`0x80070d00`** (observed PC while streaming; the
MDEC decode overlay is `FMV/FMV.BIN` @ `0x800B5788`).

## Session 2 (2026-07-04) — termination chain pinned; trigger still in the overlay
Corrected: the cap is **~468 streamed / 438 decoded frames** (counter `0x80088FFC` froze at 438)
≈ the **original TT frame count (441)** — the "2340 = DLOGO" match above was coincidence
(441 frames × 5 sectors ≈ 2334). The player plays a per-movie frame count independent of the
replacement file's own length.

**READOUT chain fully pinned** (memoryScan + `xrefsTo` + disasm):
- `G_FMV_FRAME 0x80088FFC` decoded-frame counter; setter `FUNC_80070A40` (store `0x80070A8C`),
  getter `FUNC_80070AC0` (load `0x80070AFC`, returns −1 when `G_FMV_DONE 0x80090744 != 0`).
- `G_FMV_DONE` set by terminator `FUNC_80070898` (flag-word arg: `bit8 && !bit5` → done).
- Overlay stop-call `0x800B704C`: `FUNC_80070898(448)`, reached when wait-loop `0x800B7034` sees
  `FUNC_8006D8E8(21, &0x800CABD0, 0) != 0` (a PSX event-primitive completion signal).

**Ruled out (each tested live):** ISO dir size (correct 4500 sec), **XA EOF bit** (planted 0x80
mid-file, preserved as 0xc8 in the built disc, but IGNORED — still capped +2334), decode timeout
(smooth == testsrc), movie descriptor `0x800B9A4C` (byte-identical pristine vs ours), 0x800CABD0
(an event/message template, not a sector counter).

**Only remaining piece:** what raises the code-21 completion event (`FUNC_8006D8E8`) at ~frame 468
— inside the FMV.BIN overlay's MDEC decode loop. Next: decode `FUNC_8006D8E8` (libapi event ops)
+ the overlay completion counter that trips it; patch that limit (code cave) to the movie's real
frame count, then rebuild + verify. All pinned addresses in `src_re/fmv_player_streaming.c`.

**Practical interim (no code patch):** the cap ≈ the slot's original frame count, so a clip
authored to a slot whose original count ≥ its frames plays fully at normal speed — but the movie
runs the slot's whole duration (trailing black). Only the code patch makes playback length track
the video length **dynamically** (the actual goal).

## Repro / fixtures
- Author: see `/tmp/.../scratchpad` steps + `tools/build_long_fmv_disc.py`.
- Trace: `~/duckstation/scripts/debugger-client/launch_debugger_instance.sh start --disc build/ABL_TTSMOOTH.cue --port 23460`; `emulator.getCdromState.current_lba`; `debugger.pause` + `emulator.advanceFrames` for deterministic stepping; TT range LBA 294035..298535.
- **Gotcha:** the emulator runs in real-time between RPC calls unless `debugger.pause`d first — un-paused `advanceFrames` overshoots the 30 s FMV window and you miss it. Pause, then step.
- **Gotcha:** during FMV the GPU is in **24-bit color mode**; reading VRAM as RGB555 yields
  garbage stripes. Use the CD LBA (format-independent) to measure playback, or decode 24-bit.

Related: [[media-replace-fmv-audio]], [[Core - FMV and MDEC Playback]], [[Core - CD Streaming and Caching]].
