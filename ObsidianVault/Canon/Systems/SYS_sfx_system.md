---
kind: system
id: SYS_sfx_system
created: 2026-07-08
updated: 2026-08-07
status: static_seen
confidence: medium
source_state: original_game_reference_or_mod_reference
src_paths:
  - src_re/sfx_system.c
  - src_re/sfx_voice_manager.c
address: 0x1f800374
patch_policy: safe_to_read
---

# SYS_sfx_system - sfx system

## Purpose

This page closes the migration source-coverage gap for `src_re/sfx_system.c`. It records the symbol `G_SFX_DEBOUNCE` and links the C reference into the structured vault.

- Address if known: `0x1f800374`
- Coverage comments: globals/constants: G_SFX_DEBOUNCE, G_SFX_DESC, G_SFX_VOICE_STATE, SFX_DISPATCH, SFX_MENU_BLIP, SFX_PLAY_SOUND, SFX_VOICE_KEYON, VAB_LOAD


## C source excerpt

Source: `src_re/sfx_system.c`

```c
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
 *    4 words/id: w0=vol pair, w1=flags, w2=pitch/param, w3=(pitch<<... | index-lo). The engine
 *    uses this precomputed table (does NOT re-derive program/tone from the VAB at runtime). The
 *    id -> VAG-sample resolution goes through this table + the VAB program/tone system; a clean
 *    1:1 id->VAG map is NOT trivially the w3 low halfword (ids 46-69 index a separate 32-55
 *    range) — pin per-sample via a live breakpoint on sfx_dispatch + which VAG keys on 0x80044D28.
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
```


## Voice scheduler — sfx_voice_manager (0x80044D28)  [src_re/sfx_voice_manager.c]
The SPU voice scheduler behind every SFX request (called by sfx_dispatch,
contact_pickup_sfx, ambient_sfx_sequence_update, and the sfx_voice_manager_glue_*
wrappers). Behavioral RE reconstruction ([[EXP_2026-07-09_audio_engine_probe]]):
- **8-slot voice pool** at `0x80089860` (stride 8: `+0` descriptor ptr, `+4` short
  voice_id; `-1` = free). Slot select = reuse the slot already owning this
  descriptor, else a free slot; **pool full -> the SFX is dropped (return -1)**.
- **Positional path** (a position arg): delta = source - **audio listener transform**
  in scratchpad `0x1f800374` (pos `+0/4/8`, projection axes `+32..` / `+44..`),
  projected for stereo pan + distance (`SquareRoot0`), scaled by the caller's base
  volume, clamped `[0,150]`. Non-positional path takes the base volume flat.
- **Key-on**: `SsUtKeyOn(vabId=*(u16*)gp+1040, pitch coarse/fine split, L/R vol)` after
  scaling by master vol `0x8008247E` and clamping `[0,160]`; a same-descriptor active
  slot is stopped first via `SsUtKeyOnV`. Global mute `gp+1284` suppresses default-bank
  (`0x800A6500`) SFX.
- **Bookkeeping**: dedup the new voice id out of any other slot, claim the chosen slot,
  then re-key the companion-voice table `0x8009FB56` (8 x 20 B) rows that shadow this
  voice. **Returns the average L/R loudness actually played** (callers use it to pick the
  loudest nearby pickup), or `-1`.
- CONFIRMED: pool/table layout, addresses, key-on path, return value. INFERRED (flagged
  in source): the two listener projection-axis rows and the companion-voice semantics.

## Lexical static index chain — machine interval rejected

`ambient_sfx_sequence_update@0x800510F0` contains this direct-path arithmetic
for the table at `0x80090AF4`:

- `0x800511B0`, word `0x304300FF`: `andi v1,v0,0xFF` yields `[0,255]` when
  that definition reaches the use;
- `0x800511C4`, word `0x00031840`: `sll v1,v1,1` would yield `[0,510]` from
  that masked value without overflow;
- `0x800511D0`, word `0x00621821`: the exact table-address definition is
  lexically `0x80090AF4 + v1`.

The first interval candidate incorrectly promoted this site. That disposition
is **retracted**. The current C query reports no interval and fails closed at
`0x8005128C`, word `0x03E00008` (`jr ra`), with reason
`locally_defined_ra_indirect_target_not_modelled`: a dynamic predecessor path
defines `ra` locally, so the indirect return can re-enter after bypassing the
masking definition. The arithmetic above remains an instruction observation,
not a reaching-definition proof. The complete static index also retains 160
indirect jump/call sites with unknown target domains, an additional global
entry-closure barrier. The site therefore remains in the separately reported
index-convention bucket. This does not prove debounce-table contents and does
not promote F01. Machine receipt:
`analysis/phase4_f01_typed_state.json`, row
`unresolved_access:SCUS_942_88:ambient_sfx_sequence_update@0x800510f0@0x800511E4`.
