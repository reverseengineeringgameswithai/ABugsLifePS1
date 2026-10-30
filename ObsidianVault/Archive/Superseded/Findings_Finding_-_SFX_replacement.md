---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Findings/Finding - SFX replacement.md
aliases:
  - "Finding - SFX replacement"
migration_action: split
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Findings/Finding - SFX replacement.md`
- Replacement/current location: `ObsidianVault/Canon/Systems/Finding_-_SFX_replacement.md`
- Archive reason: System/finding note; split confirmed claims into Canon and stale/history into Archive as needed.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Finding — Sound-effect (SFX) replacement

**Status (2026-07-04): SOLVED + shipped.** Any sound effect can be replaced with your own audio,
size-preserving, via a CLI or GUI. Byte-verified in the built disc (replaced GLOBAL sample #7 →
decoded ~796 Hz from the ISO). Tools: `tools/sfx_replace.py` (+ `sfx_replace.py gui`),
`tools/vab_audio.py`. Builds on the format work in [[Finding - VAB sound bank format]] and the
trigger RE in [[Core - Runtime Audio Path]]. RE: `src_re/sfx_system.c`.

## System
SFX are PsyQ **VAB** banks (distinct from the XA streamed music — see [[level01-music-replace]]):
- `SFX/GLOBAL.VAB` = **43 SPU-ADPCM samples**, resident; + 20 per-level banks (`LEVELnn/<NAME>.VH/.VB`)
  reloaded on the level-load path.
- `.VH` header (`pBAV` v6): programs/tones + a 256×u16 VAG size table (entry<<3 = bytes); `.VB` =
  concatenated headerless SPU-ADPCM (16-byte blocks). Sample K's VB span = cumulative sizes.

**Trigger (RE, confirmed):** `sfx_dispatch 0x80050994` (a0 = sound id) is the single choke point;
id → params/sample via the descriptor table `G_SFX_DESC 0x80078378` (stride 16); voice key-on
`FUNC_80044D28`. Bank load: `vab_load 0x80042FA0` → `SsVabOpenHead 0x8006B130` → `SsVabTransBody
0x8006B1C0` DMAs the `.VB` into SPU RAM. Known ids: 0x35 blue / 0x36 green / 0x37 purple / 0x38
gold berry pickup, 58 level-complete, 62 heal-leaf. (A clean 1:1 id→VAG label map still needs a
live breakpoint on `sfx_dispatch`; the GUI sidesteps this by letting you **preview** each sample.)

## Replacement (size-preserving, LBA-safe)
Encode your audio → SPU-ADPCM (`psxavenc -t vag`), overwrite the sample's VB span in place. The
SPU halts at the block **end-flag**, so trailing zero-pad never plays; VB byte size is unchanged →
`.VH` needs no edit and disc LBAs stay valid (same model as the XA/FMV tools). Longer input is
truncated to the byte budget; `--rate` tunes pitch/length (default 22050 Hz). VERIFIED end-to-end:
replaced GLOBAL #7 with an 800 Hz tone → decoded ~796 Hz from the **built disc**; GUI-built disc
with a 1000 Hz beep → ~994 Hz.

## Use
```
python3 tools/sfx_replace.py list                      # 43 samples + durations
python3 tools/sfx_replace.py preview --index 7 -o s7.wav
python3 tools/sfx_replace.py replace --index 7 --input honk.wav --build build/ABL_SFX
python3 tools/sfx_replace.py gui                        # pick + PLAY original + choose + Build
```
GUI: bank dropdown (GLOBAL + 20 level banks), sample list, **▶ Play original** (paplay) to identify
by ear, file picker + **▶ Play replacement**, rate spinbox, output path, Build.

## Pitch / playback rate (fixed 2026-07-04)
Each sample's playback rate = its **VAB tone**: `44100 * 2^((play_note - center_note)/12)`. For
GLOBAL that's **~11–16 kHz** (most 15592, some 11025) — NOT 44 kHz. (An earlier guess of ~44–52 kHz
from the descriptor `0x80078378` w3-high was WRONG — that field is not the effective SPU rate; the
symptom was previews sounding *too high* at 44100.) So a replacement must be encoded at the sample's
tone rate or it's pitch-shifted. Fix: `vab_audio.sample_rate()` computes the per-sample rate from the
tone headers; the CLI/GUI **default to it** (GUI auto-sets the Rate box on selection, tunable
8000–48000). Preview decodes at that rate = the true in-game pitch. Not measured live (SPU voice
registers 0x1F801C00 aren't exposed by the debugger memory API, and sfx_dispatch is event-driven so
it wasn't easy to catch idle voice) — the tone formula is the standard libsnd note→pitch relation.

## Voice / monologue lines (system mapped; trigger unresolved)
The idle/damage/enemy-kill Flik voice = GLOBAL bank (works). The **scripted monologue** (e.g. LEVEL01
"Gotta get to the ant hill!") is a per-level VAB system, fully identified:
- **The lines ARE on the disc** (not cut from data): LEVEL01 loads a per-level bank (LEVEL01/LEVEL1A
  or LEVEL2C, **76 samples**, ~500 kB) with **~10 long voice lines (1.8–2.9 s @ 15592 Hz)** at
  slots 35/41/50/54/55/68–76.
- **Trigger ids 46–69 → per-level slots 32–55** (clean 1:1 in the descriptor table 0x80078378): those
  ids are the monologue cues. `sfx_dispatch 0x80050994` has **22 caller sites** (0x8004xxxx–0x8005xxxx).
- So the monologue is **scripted** — fired by ids 46–69 at level events/locations.

**UNRESOLVED: why they don't play.** Could NOT confirm live whether ids 46–69 fire — execute
breakpoints work (verified on a hot addr) but `sfx_dispatch` was never hit during save-state LEVEL01
movement/combat/idle (SFX during movement route elsewhere; idle/scripted voice didn't fire in the
windows tried). So the cause is one of: (a) location/condition-gated triggers not reached, (b) a
speech/voice gate that's off, or (c) the trigger layer disabled in the PS1 port (data present, never
called). **Next step:** reach LEVEL01 *from level start* (movie fixture) with a BP on 0x80050994
logging a0, see whether 46–69 ever fire; if never, trace the gate on the caller(s). The per-level
voice banks are already **replaceable** by this tool (`--bank LEVEL1A`), so the lines can be
auditioned/swapped regardless.

## Training-level (LEVEL00) NPC voice = streamed XA (not VAB)
`REBUILD/files/LEVEL00/` (the Training level) exists but has **NO `.VH`/`.VB` bank** — so its
tutorial-NPC dialogue is **streamed XA**, in `BUGXASTR/AUDIO4.XA` + `AUDIO5.XA` (8 channels each;
`AUDIO3.XA` = music). Confirmed by ASR (faster-whisper `base.en`): every AUDIO4/AUDIO5 channel is a
tutorial line (berry throw, jump, bounce, seeds, tokens, grain/health, the berry-secret x3 in
AUDIO5 ch5-7). So training voice is replaceable via the **XA path** (`media_replace.py audio
--target AUDIO4:<ch>`), NOT the SFX/VAB tool. (Transcripts cached locally at
`extracted/xa_voice/transcripts.txt`, gitignored — copyrighted.) Method note: `faster-whisper`
(CPU, no torch) transcribes the extracted WAVs cleanly — reusable to label any game speech.

## XA voice length = EOF marker (data-driven), replacements CUT past capacity
Each XA voice channel is a one-shot line terminated by the standard PS1 **XA EOF submode bit
(0x80)** on its last audio sector (verified AUDIO5: every channel has one EOF = its last audio
sector; e.g. ch0 = 44 sectors ~2s, last @sector 344 submode 0xE4). The libcd streamer (CdlReadS)
auto-stops at EOF. Per-channel capacity (AUDIO5): ch0~2s ch1~4s ch2~10s ch3~7s ch4~20s ch5/6/7~27s.
- A **shorter** clip is fine: `--no-loop` pads the remainder with silence (plays once). [DONE]
- A **longer** clip is **CUT** to the channel's sectors — and unlike the FMV (hardcoded frame
  count → 2-byte patch), voice length has **no game-side counter to patch**; it *is* the data
  (EOF + interleave). `media_replace.py` now warns on truncation.
- **To exceed capacity** (mod = data re-mux, PLAN — not yet built/verified): append channel-C
  sectors + move the EOF later + LBA-reflow the disc (CdlReadS reads sequentially filtering the
  channel, so it should play appended sectors until the new EOF). Needs a from-Training-start
  in-game trace to confirm read-past-tail + interleave timing. **Interim:** use a channel with
  enough native room (ch4-7 = 20-27s). RE: `src_re/xa_voice_streaming.c`.

## Open / future
- **Longer XA voice:** build + in-game-verify the append-sectors/move-EOF re-mux (above).
- **XA voice in the GUI:** surface AUDIO4/5 channels (with transcript labels) in a replacer GUI. [DONE]
- **Missing monologue investigation:** which per-level bank LEVEL01 loads + the scripted id trigger.
- **Precise id→sample labels** (breakpoint `sfx_dispatch`, log a0 while triggering each event).
- **Loop SFX** (engine hums): current tool forces a one-shot end-flag (`-L`); looped samples would
  need the original loop point preserved.
- **Variable-size / higher-quality** replacement would need a full VH+VB rebuild + disc reflow
  (like the longer-FMV path) instead of size-preserving truncation.
- **Pitch fidelity**: the SPU plays at a tone-derived rate; `--rate` is a manual tuning knob.

Related: [[Finding - VAB sound bank format]], [[Core - Runtime Audio Path]], [[media-replace-fmv-audio]].
