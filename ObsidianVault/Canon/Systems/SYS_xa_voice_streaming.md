---
kind: system
id: SYS_xa_voice_streaming
created: 2026-07-08
updated: 2026-07-08
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re/xa_voice_streaming.c
address: 0x80046828
patch_policy: safe_to_read
---

# SYS_xa_voice_streaming - xa voice streaming

## Purpose

This page closes the migration source-coverage gap for `src_re/xa_voice_streaming.c`. It records the symbol `XA_SUBMODE_AUDIO` and links the C reference into the structured vault.

- Address if known: `0x80046828`
- Coverage comments: none


## C source excerpt

Source: `src_re/xa_voice_streaming.c`

```c
/* xa_voice_streaming.c — RE notes on A Bug's Life streamed-XA voice/dialogue length.
 *
 * The Training-level NPC dialogue (and other spoken lines) are STREAMED XA, not SPU/VAB
 * samples: BUGXASTR/AUDIO4.XA + AUDIO5.XA, one dialogue line per CHANNEL (8 ch/file).
 * (LEVEL00/Training has no .VH/.VB bank at all.) Music is the same libcd streaming path
 * (music_8004699c.c: CdlSetfilter{file,chan} + CdlSetmode 0xE8 + CdlReadS 0x1B).
 * Replacement tool: media_replace.py (audio / --no-loop) + the SFX GUI's XA-voice banks.
 *
 * ---------------------------------------------------------------------------
 * LENGTH IS DATA-DRIVEN (XA EOF submode bit) — VERIFIED IN-GAME 2026-07-04
 * ---------------------------------------------------------------------------
 *  CONFIRMED on real playback: AUDIO5 ch0 extended 2s->4.5s (move EOF 344->672, convert gap-8
 *  data-slots to audio) PLAYED the full ~4.5s, and the CD LBA streamed through file sector 679+
 *  (past the moved EOF 672), NOT stopping at the original 344. So a one-shot voice line stops on
 *  the XA EOF bit, NOT a software end-sector. (The MUSIC engine music_8004699c.c DOES loop via a
 *  software compare cur>=G_MUSIC_END_MARK 0x80081ff0 — that is MUSIC ONLY; voice differs.)
 *  => the data extension (tools/xa_audio.extend_xa_voice) is the correct fix; no code patch needed.
 *
 *  Each channel's audio ends with the standard PS1 XA **EOF** submode bit (0x80) on its LAST
 *  audio sector; the libcd streamer (CdlReadS) auto-stops when it reads that sector. Verified
 *  on AUDIO5.XA: every channel has exactly one EOF sector = its last audio sector, e.g.
 *      ch0: 44 audio sectors, last @abs sector 344, submode 0xE4 (0x80 EOF | 0x64 audio); none after.
 *  Per-channel capacity (AUDIO5): ch0~2s ch1~4s ch2~10s ch3~7s ch4~20s ch5/6/7~27s. The line's
 *  length == the number of that channel's audio sectors before its EOF (fixed by the interleave).
 *
 *  CONSEQUENCE (differs from FMV): the FMV cap was a hardcoded frame count in FMV.BIN (a 2-byte
 *  code/data patch — see fmv_player_streaming.c). Voice length has **no game-side counter to
 *  patch** — it is purely the EOF marker + how many sectors the interleave gives the channel.
 *  So a replacement LONGER than the channel is CUT (splice_payloads fills only the channel's
 *  slots; media_replace.py now warns). Encoding rate doesn't change this.
 *
 * ---------------------------------------------------------------------------
 * HOW TO EXCEED THE CAPACITY (mod = data re-mux, not a code cave)  [PLAN — not yet built/verified]
 * ---------------------------------------------------------------------------
 *  Because termination is EOF-driven and CdlReadS reads the file sequentially filtering for the
 *  channel, a channel can be given MORE audio by adding channel-C sectors and moving its EOF:
 *    1. Encode the (longer) line to XA sectors for channel C.
 *    2. APPEND the extra channel-C sectors to the XA (grow the file), clear the old EOF (0x80),
 *       set EOF on the new last channel-C sector. The drive reads past the other channels'
 *       sectors, plays channel C wherever it finds it, and stops at the new EOF.
 *    3. The XA file grows -> LBA reflow the disc (reuse tools/build_long_fmv_disc.py's approach:
 *       bump every file offs after the XA; all audio/FMV/level loads are by-name/CdSearchFile).
 *  Unknowns to verify in-game before shipping: (a) does the streamer keep reading past the
 *  original ~4264-sector end into appended channel-C sectors until EOF, and (b) CD read-ahead /
 *  interleave-timing tolerance for a non-uniform tail. Voice triggers are event-driven and were
 *  hard to catch live (see sfx_system.c), so this needs a from-Training-start trace to confirm.
 *  INTERIM (no re-mux): use a channel with enough native capacity (AUDIO5 ch4-7 = 20-27s), or
 *  keep the replacement within the channel's shown duration.
 */

#define XA_VOICE_FILES        "BUGXASTR/AUDIO4.XA, AUDIO5.XA"  /* 1 dialogue line per channel   */
#define XA_SUBMODE_EOF        0x80u   /* end-of-file bit on a channel's last audio sector -> stop */
#define XA_SUBMODE_AUDIO      0x04u   /* audio sector (submode 0x64 = RT|audio; 0xE4 = EOF|audio) */
/* Streaming primitives (shared with music): CdlSetfilter, CdlSetmode 0xE8, CdlReadS 0x1B —
 * see src_re/music_8004699c.c (music_start 0x8004699C, music_poll 0x80046828). No per-voice
 * end-sector counter: the EOF submode bit terminates a one-shot voice line. */
```
