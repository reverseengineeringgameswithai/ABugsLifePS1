/* ============================================================================
 * training_board_sign.c — the tutorial ANT's chalkboard "sign" is an IMAGE
 * ----------------------------------------------------------------------------
 * Question answered (2026-07-04, live on retail SCUS-94288, TRAINING level —
 * scene 17, current_scene_id; a level DISTINCT from the Anthill/Level 1 scene
 * 1, though its board texture happens to reside under the LEVEL01 disc folder
 * — see the disc-provenance note below and [[Blocker - Training board sign
 * disc offset unresolved]]): the picture the instructor-ant raises/lowers on
 * the chalkboard signpost — is it built from font/HUD GLYPHS, or a texture IMAGE?
 *
 *   ANSWER: it is an IMAGE, drawn as ONE 64x64 4bpp textured quad sampling a
 *   VRAM texture atlas. The NPC "changing signs" = the quad's UV window moving
 *   to a different 64x64 tile of the same atlas. ⚠️ REVISED 2026-07-04: whether
 *   the "xN" COUNT is baked into that same tile or stamped separately is NOW
 *   OPEN, not settled. Live gp0Trace during a fresh boot->Training replay
 *   caught the tile's upload as a full-atlas LoadImage (frame 3707, 320,0
 *   64x256) FOLLOWED by a smaller per-tile update (frame 3866, 336,0 16x64)
 *   AND a still-smaller NESTED update inside that (frame 3866, 348,16 4x32) —
 *   the nested update is positioned like a separate digit stamp on top of a
 *   static silhouette. This was not cross-checked before the original (now
 *   retracted) claim. Next step: diff extract-tile output across several
 *   board states (different xN) — if only the small nested region changes,
 *   the digit is separate and only the silhouette needs finding for a picture
 *   swap. See the blocker note for the full investigation trail.
 *
 * ---------------------------------------------------------------------------
 * ON-SCREEN DRAW PATH (gpu.pickObject on the board face)
 * ---------------------------------------------------------------------------
 *   drawCall : GP0(0x3c) Gouraud-textured QUAD (opaque)
 *   texpage  : x=320, y=0, mode=0  (mode 0 => 4bpp / CLUT4)  raw 0x0605
 *   CLUT     : x=784, y=229 (raw 0x3971), 16 entries
 *   UV tile  : u 64..127, v 0..63  -> a 64x64 texel window
 *              (corners [[127,63],[64,63],[127,0],[64,0]])
 *   The "x6 bug" hint occupies the u:64-127 column, top row of the atlas.
 *
 *   VRAM page (320,0) read back as 4bpp 256x256 = a TEXTURE ATLAS of ~16
 *   tutorial tiles: "x6" bug, "x1" berries/bugs, mushrooms, seeds, green gems,
 *   and an "Exit" tile. Board cycling just re-points the quad UV at a tile.
 *   Atlas VRAM SHA256[:16] = 00f3cf71b4a28d30 (stable across two disc/frame
 *   states -> the board face is exactly this VRAM region, not a live-composited
 *   overlay).
 *
 * ---------------------------------------------------------------------------
 * DISC PROVENANCE — ✅ RESOLVED 2026-07-05 (blocker CLOSED)
 * ---------------------------------------------------------------------------
 *   The board's sign pictures are individual 64x64 4bpp tiles stored TILE-MAJOR
 *   (32 B/row x 64 rows = 2048 B contiguous) in LEVEL07/LEVEL1.RAW, logical
 *   chunk 29, first tile at intra-chunk +0xc == decompressed offset 0x8B7C8.
 *   Signs sit back to back: sign k at 0x8B7C8 + k*2048 (bug, mushrooms, seed,
 *   green gems, gem->dark transform, ...). At runtime the game GP0(0xA0)-uploads
 *   the active sign to VRAM (336,0) and stamps the "xN" digit on top. PROOF this
 *   is the real source: the disc tile == the live VRAM board tile byte-for-byte
 *   EXCEPT the ~165 bytes of the digit region (rows 16-47, cols 48-63).
 *
 *   ⚠️ The SAME art ALSO appears ROW-major at chunk 6 / 0x2D554 (a Region-A
 *   texture page that feeds the STATIC (320,0) texpage). Editing THAT copy does
 *   NOT change the board (its edit loads to RAM but is never the board's VRAM
 *   upload). Use the chunk-29 tile-major copy. (The old 0x98650 claim was a
 *   false-positive and is retracted.)
 *
 * ---------------------------------------------------------------------------
 * EXTRACT / REPLACE (both proven, in-game verified 2026-07-05)
 * ---------------------------------------------------------------------------
 *   Live extract : gpu.decodeTexture {x:336,y:0,width:64,height:64,bpp:4,
 *                  clut_x:784,clut_y:229} -> the current 64x64 board tile PNG.
 *   Replace      : tools/training_board_edit.py replace --image X --sign N
 *                  -> quantise to the board CLUT (blue-grey indices 0-12; the 3
 *                  green entries 13-15 speckle non-green art), splice tile-major
 *                  into chunk 29, recompress. SIZE-CHANGING (the LZ recompressor
 *                  can't hit the original ratio -> chunk grows ~+19 KB), so it
 *                  ships via the AUTO-LAYOUT reflow disc build, NOT the
 *                  size-preserving ASSET_MODS lane. Disc build/ABL_TRAINBOARD_HAND3.
 *
 * ---------------------------------------------------------------------------
 * GAMEPLAY FLOW / OBJECTIVE (Phase 1 RE, in progress 2026-07-05)
 * ---------------------------------------------------------------------------
 *   Reaching the in-world board: play movie LEVEL00_load.movie.json to its end
 *   (~4162 frames -> "Training Level ... loading..." screen), then KEEP advancing
 *   (no input) — the level auto-starts and the instructor+Flik+chalkboard scene
 *   appears (scene_id 0x80082504 == 0x11 the whole time, incl. the loading screen).
 *   The board is a wooden-framed chalkboard showing the active sign + an "xN"
 *   objective counter (N = berries to throw).
 *
 *   On-screen: the sign quad = GP0(0x3c) textured quad, texpage (320,0) CLUT
 *   (784,229); the "xN" digit is a SEPARATE quad from the same atlas (digit
 *   tiles), stamped over the sign tile at VRAM (348,16,4,32)-ish.
 *
 *   The "xN" digit is a GP0(0x3c) quad, texpage (320,0) but CLUT (768,229) —
 *   ONE LESS than the sign's CLUT (784,229) — sampling the atlas DIGIT tiles at
 *   small u (digit '6' -> uv0 u=0x0a, v=0x07..0x3f; digits live at the atlas's
 *   left edge, u:0..~15). Its packet is emitted by the generic primitive writer
 *   at ~0x80014c30-0x80014d04 (same OT emitter family as 0x800105f0/0x80014a70).
 *
 *   ⚠️ The digit UV is CACHED, not recomputed per frame from a live counter:
 *   poking ALL 190 byte==6 globals in 0x800a0000-0x800b0000 to 3 did NOT change
 *   the on-screen '6' (uv0.u stayed 0x0a). => the raised-sign state (which sign +
 *   what number) is computed ONCE when the board is RAISED and stored in a board
 *   object; the per-frame render just re-emits the cached packet. So the counter
 *   is NOT a plain byte==6 in the gameplay-globals page.
 *
 *   OBJECTIVE COUNTER — LOCATED 2026-07-05 (square = throw a berry). The board
 *   "xN" IS the objective (goal - thrown); it visibly ticks 6->5->4->3 as you
 *   throw (confirmed via gpu.frameSnapshot). Method that worked: clean input
 *   (setControllerState press+RELEASE — pressButton HOLDS the button and throws a
 *   storm; a held square persists across loadState and corrupts every read), a
 *   2-frame square = exactly one throw, then memoryScan **increased_by 1**.
 *     - Berries-THROWN is stored INCREASING (not the displayed "remaining"):
 *       count/index **0x800B4A3C** (++ per throw) + a per-throw word array at
 *       **0x800B4A58** (base, [index]*4). Goal = 7 (thrown=1 -> board "6").
 *     - This lives in the TRAINING-LEVEL OVERLAY (handler code ~**0x800B4768+**,
 *       data 0x800B4A..), NOT the static EXE — hence absent from re_symbols.sym.
 *       Handler also sets a 30-frame timer 0x800B4A50 and writes 0x800A_DE..(?).
 *     - The DISPLAYED digit is CACHED: poking 0x800B4A58/thrown to 7 does NOT
 *       refresh the board (stays '6'); only a real throw (which runs the handler)
 *       updates the drawn digit. So blanking the counter = intercept the handler's
 *       digit update / the cached digit, not just poke the count.
 *   RED HERRINGS (do not chase): 0x800910A3-0x800910AA are ANIMATION phase
 *   counters in the per-frame tick fn 0x8005518C (increment + wrap mod 2/3/5/6/7/
 *   8/16/32); 0x800910A7 survived a decreased_by-1 scan only as a timing artifact.
 *
 *   TUTORIAL SCRIPT ENGINE — DECODED 2026-07-05 (training overlay, all pieces for
 *   the dynamic-sign-trigger mod):
 *     - **0x800B3F58** = the 14-step tutorial state machine. Per-step dispatch via
 *       jump table **0x800B39A4** (step<<2). Each step: plays its audio line
 *       (`jal 0x80046AC0` = play-voice-once wrapper, a0 = packed id from table
 *       **0x800B4A14[step]** halfwords), decrements a per-step countdown **timer
 *       0x800B4A50** (nonzero => wait/skip), checks an objective flag (e.g.
 *       [0x800A6586]==17, [0x800A6580]==1, [0x800A6584]==9), and on completion
 *       calls the sign-raise to advance.
 *     - Audio table 0x800B4A14 = {0x18,0x19,..0x25} (14 ids). id=file<<3|chan =>
 *       **step 0 (FIRST monologue) = id 0x18 = AUDIO4.XA channel 0**; steps 0-7 =
 *       AUDIO4 ch0-7, steps 8-13 = AUDIO5 ch0-5. (Inject the custom line at AUDIO4 ch0.)
 *     - **Sign-raise = 0x800B3B54(a0=sign_index, a1=count)**. Draws sign a0 (via
 *       obj id 50) then, IF a1>=0, the "xN" digits (obj id 51, base-3 layout).
 *       **a1 < 0 SKIPS the digit entirely (`bltz s1`) => BLANK counter.** VERIFIED
 *       in-game: callFunction 0x800B3B54(0, -1) shows the hand sign with NO number.
 *       (sign 8<->9 are swapped internally.)
 *     - Objective (berries thrown) count/index 0x800B4A3C, per-throw array 0x800B4A58,
 *       goal 7; the throw handler ~0x800B4768 updates the cached drawn digit.
 *
 *   STEP-0 HANDLER DECODED 2026-07-05 (jump table 0x800B39A4[step]; step 0 =
 *   0x800B3FD4). Observed: throwing 6 berries advances the step index 0x800B4A3C
 *   0->1 and the NPC lowers the hand + raises the next sign. Handler logic:
 *     s0 = per-step state (persisted in 0x800B4A58[step], loaded each frame).
 *     if s0==0: play audio table[step] (0x80046AC0), s0=1.       // once
 *     if [0x800A6586]==17 (a berry-HIT pulse): s0++ ; if s0>=7 -> set advance
 *        flag s1=1 (engine tail 0x800B477C then step++ + timer 0x800B4A50=30);
 *        else re-raise sign 0 with count = 6 - s0 (0x800B3B54(a0=0, a1=6-s0)) --
 *        this is the ticking "xN". (So the displayed number == the objective.)
 *   The DISC file for all this = LEVEL07/LEVEL1.BIN, UNCOMPRESSED; load base
 *   0x800B39A0 (file_off = RAM - 0x800B39A0). Step-0 handler @ file 0x634.
 *
 *   => DYNAMIC-SIGN-TRIGGER MOD — BUILT + COLD-BOOT VERIFIED 2026-07-05:
 *   (1) audio: tools/media_replace.py audio --target AUDIO4:0 --no-loop (the line
 *       step 0 plays). (2) overlay: tools/patch_training_overlay.py rewrites the
 *       step-0 handler (LEVEL07/LEVEL1.BIN @file 0x634, size-preserving) to:
 *       play its audio, call 0x800B3B54(sign=0, count=-1) [hand + BLANK number],
 *       set the per-step timer 0x800B4A50 = HOLD ticks (~30/s), and on the next
 *       entry (timer elapsed) set the advance flag s1=1 -> engine advances to the
 *       next sign+audio (NO berries needed). (3) build: build_autolayout_disc.py
 *       stages LEVEL1.RAW(image, size-changed) + LEVEL1.BIN(overlay) + AUDIO4.XA
 *       (XA "mixed"; the autolayout LBA verifier false-mismatches XA Form2 sectors
 *       -- verify XA via a substring search of the .bin instead). Disc:
 *       build/ABL_TRAIN_TUTORIAL.bin. In-game: board opens on the blank hand,
 *       holds, then advances to the bug "x6" (step 1) -- confirmed cold-boot.
 *   ⚠️ AUDIO STREAMING BUG (open 2026-07-05): image/blank/advance all work
 *   in-game, but the INJECTED LINE DOES NOT STREAM at step 0 on the patched disc.
 *   PROVEN: the PRISTINE game DOES stream step-0 audio (AUDIO4 ch0, ~18s, right
 *   after load, getCdromState reading=True) -- so the injection + channel are
 *   correct. The regression is our patched step-0 HANDLER: it drives step 0 on a
 *   timer, and the timer counts down through the loading phase, so step 0's audio
 *   call fires / step 0 advances before the XA stream can start (CD monitor shows
 *   reading=False for the whole patched step 0; the unpatched step 1 streams fine).
 *   The pristine handler avoids this because it waits for berry HITS (which can't
 *   happen during loading), so it naturally stays until gameplay.
 *   ✅ AUDIO FIXED 2026-07-05 -- COLD-BOOT VERIFIED streaming. The bug was that a
 *   CAVE which RE-ISSUED the audio call landed in a "CD/XA subsystem not ready"
 *   window right after level-load and the CdlReadS silently no-op'd (flag set,
 *   reading=False). THE FIX: leave the stock handler's AUDIO-PLAY (0x800B3FD4..
 *   0x800B3FFC: play table[step] via 0x80046AC0, s0=1) EXACTLY as shipped -- it
 *   streams the line correctly (this is the same path the proven build/ABL_XAEXT
 *   AUDIO5-ch0 test used). Rewrite ONLY the ADVANCE half in-place (0x800B4000..
 *   0x800B4028, LEVEL1.BIN file 0x660..0x688, size-preserving):
 *       each frame: 0x800B3B54(0, -1)   ; raise hand, BLANK number
 *       v0 = [gp+0x6e0] & 1             ; audio-playing flag (=1 streaming, 0 @EOF)
 *       if v0 != 0: j 0x800B477C        ; still playing -> wait
 *       else: s1 = 1 ; j 0x800B477C     ; done -> engine lowers sign + advances
 *   No cave, no jump-table repoint, no EXE edit. In-game: blank hand shows, the
 *   injected AUDIO4-ch0 line streams full-length (line + its silence pad), then the
 *   board advances to the next sign the instant the line ends. The gp+0x6e0 flag =
 *   0x80082478 (gp=0x80081D98), read by 0x80046B14. Tool: tools/patch_training_overlay.py.
 *   Disc: build/ABL_TRAIN_TUTORIAL4.bin. See [[Plan - Training board dynamic sign trigger]].
 *   2026-07-06 consolidated-build correction: tools/patch_training_overlay.py had drifted
 *   back to the older EXE cave jump, causing active ALLMODS to fail after pressing X on
 *   the Training loading prompt. The tool now matches this documented in-place design:
 *   only LEVEL07/LEVEL1.BIN file 0x660..0x687 is rewritten; SCUS_942.88 is not staged by
 *   the Training tutorial stager unless bytes actually change. Active ALLMODS
 *   `3011ba45...` enters Training gameplay after the prompt.
 *
 *   2026-07-07 follow-up RE: the rest of the tutorial is a 14-step state machine
 *   at 0x800B3F58 with current step 0x800B4A3C and per-step state array
 *   0x800B4A58. Later "spawned" objective items are not allocated by this
 *   state machine directly. Training init scans the type-0x3f record, caches
 *   kind 0x2B / 0x2C entry pointers in 0x800B4A34..0x800B4A4C, hides them by
 *   adding +8000 to entry.y and entry+0x0E, then later handlers subtract 8000
 *   to reveal them. The normal type-0x3f pickup pass then constructs/collects
 *   them. See src_re/training_tutorial_progression.c and
 *   [[Training NPC progression]].
 *
 *   2026-07-07 ALLMODS step-2 blackberry gate: do NOT place custom code at
 *   0x800B4A30. It is live Training overlay state, and the broken build crashed
 *   at PC=0x000000A0 / COP0_EPC=0x800B4A34 after jumping into runtime data.
 *   The fixed build uses resident EXE caves 0x8007F0D8 (voice+collect gate) and
 *   0x8007F930 (reveal shim). See src_re/training_tutorial_progression.c.
 *
 * Related: [[Training board sign images]] · [[Plan - Training board dynamic sign trigger]] ·
 *          [[Blocker - Training board sign disc offset unresolved]] (CLOSED) ·
 *          src_re/xa_voice_streaming.c · tools/training_board_edit.py
 * ==========================================================================*/
