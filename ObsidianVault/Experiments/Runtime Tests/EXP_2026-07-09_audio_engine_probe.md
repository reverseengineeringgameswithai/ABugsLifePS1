---
kind: experiment
id: EXP_2026-07-09_audio_engine_probe
name: Audio engine CLOSE — sequencer dead, voice scheduler, id→VAG map solved
status: success
confidence: confirmed
source_state: evidence
validates: [SYS_sfx_system, SYS_audio_music]
fixtures: [level01.sav, blue_berry_walk_up_to_collect.sav]
artifacts: [src_re/sfx_voice_manager.c, analysis/sfx_id_vag_map.json, analysis/functions.json, symbols/re_symbols.sym]
---

# EXP_2026-07-09_audio_engine_probe

## Question
Close (or reduce) the `audio_engine_closed` residual: "sequencer, SPU voice scheduling, non-XA SFX
internals." First pass — establish what is live vs dead and pin the SFX voice path.

## Method
Throwaway DuckStation instance (port 23460, pristine disc), `level01.sav`, execTrace watches with
register capture, driven gameplay bursts (run + jump). Static cross-check via the census call graph.

## Findings

### 1. The libsnd SEQ sequencer is LINKED-DEAD (residual CLOSED by exclusion)
- **Static:** `_SsSeqPlay 0x80067210` and `_SsSndPlay 0x800671e4` each have exactly **one caller, and it
  is `sdk_psyq`-class** (library-internal) — **zero game-class callers**. No game code ever starts a
  MIDI/SEQ sequence.
- **Runtime:** armed on both during an active-sound gameplay burst → **0 hits** while `SsUtKeyOn` fired
  10×. The MIDI engine is linked (PsyQ libsnd) but never driven with data. Music is XA (libcd); SFX are
  direct libspu voice key-ons. → the "sequencer" third of the residual is closed.

### 2. SFX voice path (confirmed shape)
Ambient/music voices key on via **`SsUtKeyOn(vabId=0, prog=0, note, ...)`** directly (10× in the idle/run
burst — the ambient loop). The **SFX** path is `sfx_dispatch 0x80050994 → sfx_voice_manager 0x80044d28 →
SsUtKeyOnV 0x80068b24`; it did **not** fire on run/jump in `level01.sav` (footsteps here are not
dispatch-routed) — capturing the id→VAG map needs a reliably-SFX scenario (pickup / hit / berry-throw),
recorded as the remaining live-capture step.

### 3. `music_loop_poll @ 0x80046828` is a MISLABELED 4-byte orphan
The census/Canon symbol `music_loop_poll` at `0x80046828` is a single stray word `lw v0, 0x6e0(gp)`
(`8f8206e0`) with **no callers**, sitting between `cd_controlb_shim` (which returns at `0x80046820`, so it
never falls through) and the next function's prologue at `0x8004682c` (`addiu sp,-0x38`). It is
unreachable dead/data, **not** a poll routine — the "software-loop poll" attribution to this address is
wrong. (Correction target for the census: reclassify as data / retract the name; the byte-splat build is
unaffected either way.)

### 4. SPU voice scheduling reconstructed — `src_re/sfx_voice_manager.c`
`FUNC_80044D28` (2384 B) reconstructed behaviorally: an **8-slot voice pool** (0x80089860, stride 8,
`-1`=free) with reuse/pre-empt/drop-on-full; positional stereo attenuation projecting `(source −
listener)` against the **audio listener transform in scratchpad 0x1f800374**; key-on via `SsUtKeyOn`
(vabId `gp+1040`, master vol `0x8008247E`, clamp `[0,160]`); returns average L/R loudness or −1. This is
the "SPU voice scheduling" third.

### 5. Non-XA SFX id→VAG map SOLVED — `analysis/sfx_id_vag_map.json`
The resolution is **not** the descriptor's w3 halfword — it is the `(id−16)` key-on path: `sfx_dispatch`
passes `a1 = id−16` → voice manager keys on `SsUtKeyOn(prog=(id−16)>>7, tone=(id−16)&0x7f)`; the VAB maps
`tone → VAG = tone+1` (GLOBAL prog0 is a 43-tone 1:1 ramp). So positive id N plays GLOBAL VAG `N−15` for
N∈[16,58]; higher ids play the per-level bank (own `vabId`) by the same rule; negative ids use the
variant pool `0x80089850`. **Validated live:** berry-pickup id `0x35` → `SsUtKeyOn(prog0, tone 0x25=37)`
→ GLOBAL VAG 38.

## Result — audio_engine_closed FLIPPED
All three named residuals addressed: **sequencer** (dead by exclusion), **SPU voice scheduling**
(reconstructed), **non-XA SFX id→VAG** (solved + live-validated); XA music start was already closed.
`music_loop_poll@0x80046828` corrected (orphan). `audio_engine_closed` → True. Remaining at
understanding-depth only (not a black box): the positional-voice cluster `0x80043184–0x80044350` (named,
not yet decompiled to `src_re/`). See [[SYS_sfx_system]] · [[SYS_audio_music]].
