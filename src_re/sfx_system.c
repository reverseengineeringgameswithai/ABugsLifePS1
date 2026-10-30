/* sfx_system.c — RE notes on A Bug's Life sound-effect (SPU/VAB) playback + replacement.
 *
 * SFX are PsyQ VAB banks (SFX/GLOBAL.VAB = 43 SPU-ADPCM samples, resident; + 20 per-level
 * banks LEVELnn/<NAME>.VH/.VB reloaded on the level-load path). Distinct from the XA
 * streamed MUSIC path (music_8004699c.c / CdlReadS). Replacement tool: tools/sfx_replace.py
 * (+ GUI), codec tools/vab_audio.py. Vault: "Core - Runtime Audio Path",
 * "Finding - VAB sound bank format", "Finding - SFX replacement".
 *
 * ---------------------------------------------------------------------------
 * TRIGGER (confirmed)
 * ---------------------------------------------------------------------------
 *  sfx_dispatch = 0x80050994 (a0 = sound id). The single choke point for all positive-id SFX.
 *    - a0 < 0  -> special/variant pool (footstep/impact round-robins via descriptor ptr array
 *                 0x80089850 + byte tables ~0x800878xx; case -1 also calls play_sound(12)).
 *    - a0 >= 0 -> real SFX pool (0x80050B78): ids [82,101] get a per-id "already playing"
 *                 debounce timer (=900) in the array 0x80090AF4 (index id<<1); then
 *                 a3 = *(s16*)(G_SFX_DESC + (id<<4));  a1 = id-16;  a2 = ((id-16)&0xf)<<7 | 0x1200;
 *                 jal FUNC_80044D28(voice_state=0x800A6500, a1, a2, a3);  *(gp+1444) = id.
 *  FUNC_80044D28 = voice manager / key-on: walks an 8-slot voice table (~0x80089860, stride 8),
 *    uses SPU scratch ptr 0x1F800374, and calls libspu helpers (0x80068B24, downstream) to key
 *    the SPU voice. (This is the libspu SpuSetVoiceAttr/SpuSetKey-equivalent site.)
 *  play_sound = 0x8005044C — higher-level effect+cue spawner (id + context ptr); NOT the pure
 *    SFX dispatcher. sfx_menu_blip = 0x80050838 (menu cursor).
 *
 *  G_SFX_DESC = 0x80078378 — per-sound descriptor table, stride 16 (id<<4), file off 0x68B78.
 *    4 words/id: w0=vol pair (base_vol -> voice_manager arg3), w1=flags, w2=pitch/param, w3=misc.
 *  id -> VAG map SOLVED (2026-07-09, [[EXP_2026-07-09_audio_engine_probe]], analysis/sfx_id_vag_map.json):
 *    the resolution is NOT the descriptor's w3 halfword — it is the (id-16) key-on path. sfx_dispatch
 *    passes a1 = id-16 to FUNC_80044D28, which keys on SsUtKeyOn(prog = (id-16)>>7, tone = (id-16)&0x7f).
 *    The VAB maps tone -> VAG = tone+1 (GLOBAL prog0 is a 1:1 ramp, 43 tones). So a positive id N plays
 *    GLOBAL VAG (N-15) for N in [16,58]; higher ids play the per-level bank (its own vabId in gp+1040)
 *    by the same tone=id-16 rule within that VAB. Negative ids -> variant/round-robin pool 0x80089850.
 *    VALIDATED LIVE: berry-pickup id 0x35 -> SsUtKeyOn(prog0, tone 0x25=37) -> GLOBAL VAG 38.
 *  Known ids (from src_re callers): 0x35 blue / 0x36 green / 0x37 purple / 0x38 gold berry
 *    pickup, 58 level-complete, 62 heal-leaf, 7 (via play_sound) Dot beckon.
 *
 * ---------------------------------------------------------------------------
 * BANK LOAD (confirmed)
 * ---------------------------------------------------------------------------
 *  vab_load = 0x80042FA0 (entry ~0x80042F58): file_loader 0x80046330 reads "sfx\global.vh" ->
 *    SsVabOpenHead 0x8006B130 (a0=hdr buf @gp+1768, a1=-1) -> vabId in gp+1040 ->
 *    SsVabTransBody 0x8006B1C0 (wrapper 0x8006B59C) DMAs the .VB into SPU RAM via the libspu
 *    DMA/wait pair 0x8006CE6C / 0x8006CE40 (SpuSetTransferAddr/SpuWrite internals; no strings).
 *    Fail strings: "SoundFX SsVabOpenHead : failed!" (0xB898), "Sound FX SsVabTransBody :
 *    failed!" (0xB8BC). Per-level banks ride the same path on level load, each its own vabId.
 *
 * ---------------------------------------------------------------------------
 * VAB FORMAT + REPLACEMENT (solved — tools/vab_audio.py, tools/sfx_replace.py)
 * ---------------------------------------------------------------------------
 *  .VH: magic 'pBAV' v6; +0x12 #progs, +0x14 #tones, +0x16 #vags; ProgAtr 128x16 @0x20;
 *    ToneAtr progs*16*32 @0x820 (tone+0x16 = VAG index, 1-based); 256xu16 VAG-size table
 *    (entry<<3 = bytes) in the last 512 B. .VB = concatenated headerless SPU-ADPCM (16-byte
 *    blocks), sample K span = cumulative sizes. GLOBAL = 3 progs / 43 tones / 43 vags,
 *    Sigma sizes = 178224 = exact VB size.
 *  Replacement is SIZE-PRESERVING: encode audio -> SPU-ADPCM (psxavenc -t vag), overwrite the
 *    sample's VB span (SPU halts at the block end-flag, so trailing pad never plays) -> no .VH
 *    edit, VB byte size unchanged -> disc LBA valid (same model as the XA/FMV tools). VERIFIED:
 *    replaced GLOBAL sample #7 with an 800Hz tone -> decoded from the BUILT DISC at ~796Hz.
 */

#define SFX_DISPATCH          0x80050994u  /* a0=sound id; positive-id SFX choke point          */
#define SFX_VOICE_KEYON       0x80044D28u  /* voice manager / SPU key-on                        */
#define SFX_PLAY_SOUND        0x8005044Cu  /* higher-level effect+cue spawner (not the dispatch)*/
#define SFX_MENU_BLIP         0x80050838u  /* menu cursor blip                                  */
#define G_SFX_DESC            0x80078378u  /* per-sound descriptor table (stride 16, id<<4)      */
#define G_SFX_VOICE_STATE     0x800A6500u  /* voice-manager state object (a0 to keyon)          */
#define G_SFX_DEBOUNCE        0x80090AF4u  /* per-id "already playing" timer array (ids 82..101)*/
#define VAB_LOAD              0x80042FA0u  /* loads sfx\global.vh + DMAs VB to SPU RAM          */
#define SsVabOpenHead         0x8006B130u
#define SsVabTransBody        0x8006B1C0u  /* SPU-RAM DMA of the .VB body                        */
