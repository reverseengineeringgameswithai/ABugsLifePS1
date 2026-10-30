/* fmv_player_streaming.c — RE notes on A Bug's Life FMV (STR) playback / length control.
 *
 * Companion to file_loader_80046330.c (the by-name loader) and music_8004699c.c
 * (the analogous XA streaming path). This file documents what is CONFIRMED about how
 * an FMV is located, streamed, and TERMINATED — the last of which is the open blocker
 * for playing a LONGER replacement clip at normal speed.
 *
 * Vault: ObsidianVault/Findings/Finding - Longer FMV playback (normal-speed extension RE).md
 *        ObsidianVault/Core - FMV and MDEC Playback.md
 *
 * ---------------------------------------------------------------------------
 * CONFIRMED
 * ---------------------------------------------------------------------------
 *  - FMV.BIN player overlay loads to REGION-B 0x800B5788 via fmv_bin_load (0x8003E7C0,
 *    store site 0x8003E7FC) -> FUNC_80046330("fmv\\fmv.bin", 0x800B5788). The overlay
 *    holds the play-order manifest (NUL-terminated STR path strings; NO LBAs/sizes/counts)
 *    plus the MDEC decode/DMA code. Diagnostic strings incl. "time out in decoding !".
 *
 *  - Movies are located BY NAME (runtime ISO9660 directory), never by hardcoded LBA:
 *    FUNC_80046330 / CdSearchFile. A resized + LBA-shifted STR is still found and streamed
 *    (verified live on a reflowed disc: the CD read head walks the new TT range at the
 *    real-time 2x rate and our custom frames play). => growing an STR is disc-safe as long
 *    as the FMV/XA region is reflowed (tools/build_long_fmv_disc.py).
 *
 *  - The resident FMV player LOOP runs around ~0x80070D00 (observed PC while an FMV
 *    streams; the MDEC decode itself is in the 0x800B5788 overlay). Streaming almost
 *    certainly uses the same libcd idiom as music_start (CdlSetfilter{file,chan} +
 *    CdlSetmode 0xE8 + CdlReadS 0x1B), filtering file=1 / channel=1 (STR audio is
 *    mono 18900 Hz on channel 1; video sectors submode 0x48, audio submode 0x64).
 *
 * ---------------------------------------------------------------------------
 * OPEN — the playback-length cap (blocks longer clips)
 * ---------------------------------------------------------------------------
 *  Measured max streamed LBA per movie (deterministic paused stepping, DuckStation):
 *      pristine TT (441 f / 3328 sec)      -> +3437  (22.9 s)  FULL FILE (EOF @ last sector)
 *      our long TT (900 f / 4500 sec)      -> +2334  (15.6 s)  CAPPED
 *  The cap is CONTENT-INDEPENDENT (testsrc and smooth stop at the same sector) and is NOT
 *  the ISO dir size (correct 4500), NOT an XA EOF bit (none present), NOT a structural
 *  discontinuity. It ~equals 2340 sectors = DLOGO.STR's exact length (the FMV played
 *  immediately BEFORE TT; 156 f @ 10 fps = 15.6 s). Pristine TT uses its OWN length; our
 *  resized TT plays for the PREVIOUS FMV's length.
 *
 *  STREAM START PATH (corrected 2026-07-09 from SDK identities + overlay disassembly):
 *   - 0x8006D8E8 is PsyQ CdControl, not an event primitive. At 0x800B7030 the overlay
 *     polls CdControl(CdlGetlocP=0x15, 0x800CABD0, 0) until the command succeeds.
 *   - 0x80070898 is PsyQ CdRead2, not a terminator. At 0x800B704C the overlay retries
 *     CdRead2(0x1c0) until the streamed read starts, then issues
 *     CdControl(CdlDemute=0x0c, 0, 0) at 0x800B7058.
 *   - 0x80070A30..0x80070AC0 is the libpress CD-ready callback. The apparent entry
 *     at 0x80070A40 was only its delayed stack prologue. 0x80070AC0..0x80070B20 is
 *     the complete StGetBackloc; 0x80070AC8 was likewise a false split.
 *   - Playback completion is the overlay flag at 0x800CAC10, raised by the decoded
 *     frame-limit comparisons around 0x800B6B18/0x800B6B44.
 *
 *  ===========================================================================
 *  SOLVED 2026-07-04 — the length cap is a HARDCODED PER-MOVIE FRAME-COUNT TABLE in FMV.BIN.
 *  ===========================================================================
 *  The overlay decode loop @0x800B6B28 does, per frame:
 *      total = *(s16*)0x80131EEE;                       // this movie's frame count
 *      if (current_frame >= total - 2) *(int*)0x800CAC10 = 1;   // raise completion
 *  0x80131EEE is written at movie-start FUNC_800B6D68(a1=total, ...) @0x800B6DC0.
 *  Its caller @0x800B652C.. is a jump table of 40 cases, one per manifest movie, each
 *      addiu a1, zero, <FRAME_COUNT>       // hardcoded immediate
 *  in MANIFEST ORDER (TT=440, DLOGO=156, AD=1410, LEV1A=386, ... INTRO=1750, LOSE=281 — all
 *  match the movies' real frame counts; TT is 440 vs its file's 441).
 *
 *  The overlay is loaded VERBATIM to 0x800B5788 (file offset 0), so each immediate is a
 *  2-byte DATA patch in FMV.BIN. Table verified offline: 40 entries at file offsets
 *  0x0B4C(TT) 0x0B58(DLOGO) 0x0B74(AD) 0x0B94(LEV1A) ... 0x0DC4(INTRO) 0x0DD0(LOSE); each
 *  immediate = the low halfword of `?? ?? 05 24` (addiu a1,zero,imm). PROOF: patching TT's
 *  0x0B4C 440->900 made [0x80131EEE]=900 and TT streamed the FULL +4357/4500 (~29s, ~871
 *  frames) instead of capping at 440. => to play a longer replacement clip, patch that movie's
 *  FMV.BIN frame-count entry to the new STR's frame count. Tool: tools/fmv_frame_table.py.
 *
 *  RULED OUT (2026-07-04, each tested live): ISO directory size (ours is correctly 4500
 *  sectors), XA EOF submode bit (planted 0x80 mid-file @sector1499/frame~300, PRESERVED in
 *  the built disc as 0xc8, but the player IGNORED it — still capped at +2334/frame~466),
 *  decode timeout (smooth low-detail content caps identically to harsh testsrc), and the
 *  movie descriptor @0x800B9A4C (byte-identical pristine vs ours). 0x800CABD0 is an
 *  EVENT/message template (repeated 0x58010006/0x5bff0006 words, constant across positions),
 *  NOT a sector-budget counter.
 *
 *  STILL OPEN: MDEC VLC/decode and DMA internals inside FMV.BIN. Stream startup,
 *  per-movie frame-limit selection, and the completion flag are now statically pinned.
 *
 *  ===========================================================================
 *  ADDED 2026-08-01/02 — the movie_id SELECTION MECHANISM (how a case is chosen)
 *  ===========================================================================
 *  The 2026-07-04 work above proves and exploits the EFFECT of the per-movie table
 *  (each case's frame count is a patchable literal). It does not document HOW a case is
 *  selected -- that mechanism is added here, via a fresh static disassembly of
 *  0x800B6250..0x800B658C (Phase 4, analysis/phase4_e15_fmv_frontier.json). The frame
 *  counts recovered independently below CROSS-CHECK the 2026-07-04 values exactly; they
 *  are not a new discovery of the counts themselves.
 *
 *  TRIGGER (resident, NOT overlay-resident -- corrects an old open hypothesis):
 *      A whole-executable Phase-4 C census supersedes the earlier 3-site claim:
 *      there are 9 direct resident calls and zero overlay calls. They cover the
 *      boot trio, level A/B tables, LEV15C/D, LOSE, and the computed ALT sequence.
 *      fmv_bin_load(a0=movie_id, a1=flag) forwards movie_id UNCHANGED into the overlay:
 *      display_buffers_init -> [if a1: transition_fade_draw_loop] ->
 *      universal_file_loader(a0="fmv\\fmv.bin", a1=0x800B5788) ->
 *      [if a1: animated_overlay_display_loop_entry] -> jal 0x800B6250(a0=movie_id) ->
 *      boot_subsystem_init.
 *
 *  SELECTION (0x800B6250, the confirmed FMV.BIN entry point):
 *      sltiu v0, movie_id, 0x2F                 // valid range 0..46
 *      if (movie_id >= 47) goto out_of_range;   // falls through ~178 words ahead
 *      case_addr = *(u32*)(0x800B5AA4 + movie_id*4);   // 47-entry jr-table
 *      goto case_addr;
 *  47 slots = 3 boot clips (ids 0-2) + 7 UNUSED (ids 3-9, one shared DEFAULT handler --
 *  ClearImage, screen clear, no STR playback, no error) + 40 real cases (ids 0-2, 10-46).
 *  THE TRUE LEVEL COUNT IS 15 (matches all campaign stages F01-F15), NOT the 11 implied by
 *  the file's own stale 25-entry header manifest -- the header and the dispatch table are
 *  two different, INCONSISTENT in-file sources; the dispatch table is authoritative for
 *  what code can actually invoke. Full 47-slot table (id: file, frames) in
 *  analysis/phase4_e15_fmv_frontier.json -- reproduced in full in
 *  ObsidianVault/Canon/Systems/SYS_fmv_player_streaming.md.
 *
 *  Two verified irregularities (re-checked against raw bytes, not decode artifacts):
 *    - levels 4/5's A-clips are swapped in table order (id16->LEV5A, id18->LEV4A) while
 *      their B-clips are not (id17->LEV4B, id19->LEV5B).
 *    - level 15 is a 4-clip special case (ids 38-41: A/B/C/D), not the usual 2.
 *
 *  LITERAL TRIGGER SITES RESOLVED (content-based INFERENCE, not a traced guard-condition
 *  semantic -- flagged as such, not claimed confirmed):
 *      a0=40 (0x80050284) -> id40 = LEV15C, 3162 frames (longest clip by far -- inferred
 *                            campaign finale)
 *      a0=46 (0x800500D8) -> id46 = LOSE,   281 frames (short -- inferred game-over)
 *      a0=(a2&0xFF)+41 (0x8004FFD4) -> reaches LEV15D/ALT1/ALT2/ALT3 for a2=0..3 --
 *                            consistent with a variant-ending selector; a2's own source
 *                            was not traced this pass.
 *
 *  STILL OPEN: the movie_id -> filename resolution itself is now fully known; MDEC
 *  VLC/decode/DMA internals past this dispatch point remain undisassembled (item 2's
 *  function-boundary-recovery step, distinct from this selection mechanism).
 */

#define G_STR_BACKLOC          0x80088FFCu  /* libpress back-location value                       */
#define STR_READY_CALLBACK     0x80070A30u  /* callback body includes the old false 0x80070A40 split */
#define STR_GET_BACKLOC        0x80070AC0u  /* PsyQ StGetBackloc, complete through 0x80070B20     */
#define CD_READ2               0x80070898u  /* PsyQ streamed-read starter                         */
#define FMV_STREAM_START_CALL  0x800B704Cu  /* CdRead2(0x1c0), retried until accepted             */
#define CD_CONTROL             0x8006D8E8u  /* PsyQ CdControl                                     */
#define G_FMV_COMPLETE         0x800CAC10u  /* overlay completion request                          */
#define FMV_OVERLAY_BASE       0x800B5788u  /* FMV.BIN overlay (MDEC decode + manifest)          */
#define FMV_BIN_LOAD           0x8003E7C0u  /* loads fmv\fmv.bin -> FMV_OVERLAY_BASE              */
#define FILE_LOADER_BY_NAME    0x80046330u  /* CdSearchFile-based by-name loader                  */

#define SCENE_FLOW_DISPATCHER  0x8004FCA0u  /* jr-dispatch target of main_shell_substate_table    */
#define FMV_ENTRY_POINT        0x800B6250u  /* confirmed FMV.BIN entry; a0=movie_id               */
#define FMV_MOVIEID_TABLE      0x800B5AA4u  /* u32[47] jr-table, movie_id-indexed                 */
#define FMV_MOVIEID_MAX        46            /* sltiu $v0,$s0,0x2F bound; ids 3-9 unused          */
#define FMV_MOVIEID_DEFAULT    0x800B6574u  /* shared DEFAULT case (ClearImage, no STR)           */
#define FMV_PLAYBACK_CALL      0x800B6D68u  /* per-movie a1=frame_count entry point               */
