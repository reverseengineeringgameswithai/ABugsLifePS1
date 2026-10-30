---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Plans/Plan - Longer XA voice lines.md
aliases:
  - "Plan - Longer XA voice lines"
migration_action: needs_review
confidence: medium
---

# Archived Legacy Note

- Original path: `ObsidianVault/Plans/Plan - Longer XA voice lines.md`
- Archive reason: Planning/blocker/hypothesis material is not Canon unless evidence-backed claims are extracted.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

# Plan — Longer XA voice lines (beyond a channel's native length)

**Goal:** let a replaced XA voice/dialogue line (Training-level NPC etc.) be **longer** than the
channel's original duration, instead of being cut. See [[Finding - SFX replacement]] and
`src_re/xa_voice_streaming.c`. Tools: `tools/media_replace.py`, `tools/xa_audio.py`, the SFX GUI.

## Why it's cut (RE recap)
Voice = streamed XA (BUGXASTR/AUDIO4/5.XA), **one line per channel**. Length is **data-driven**: a
line ends at the **XA EOF submode bit (0x80)** on the channel's last audio sector; `CdlReadS`
auto-stops there. There is **no game-side length counter** to patch (unlike the FMV frame count).
So extending = adding more of that channel's **audio sectors** and moving the EOF — a data edit.

## The interleave (the key structural fact)
AUDIO5.XA is an **8-way interleave, gap = 8** (each channel one sector per 8-sector round). Real-time
playback at 37800/stereo REQUIRES this cadence (1/8 of the CD's 150 sec/s ≈ the audio rate). Verified:
- Long lines (ch4=20s, ch5/6/7=27s) are **pure gap-8** for their whole length (ch5: 501 audio sectors
  at gap 8, span 5..4005).
- Short lines (ch0-3) get gap-8 slots for a while after their audio (as **data** sectors, submode
  0x48), then drop to a **clustered** tail (gap 1) that is NOT usable for continuous playback.
- ch0 example: 44 audio sectors (0..344, ~2s) + gap-8 **data** slots 352..784 (~55 sectors) → a
  channel can be extended within its gap-8 run to ~**4.5s** with NO file change; beyond that its
  slots are clustered.

## Approach A — convert gap-8 data-slots (size-preserving)  [PHASE 1, in progress]
For an extension that fits the channel's remaining **gap-8** run:
1. Encode the clip → XA (37800/stereo) → ADPCM payloads.
2. Reuse the channel's existing audio sectors + its following **gap-8 data-slots**: flip submode
   `0x48 → 0x64` and write the clip's payloads in order.
3. **Move the EOF**: clear `0x80` on the old last audio sector (0xE4→0x64); set `0x80` on the new
   last audio sector (0x64→0xE4).
Result: same file size (no LBA reflow), plays via the existing interleave cadence. Capacity =
`(audio + adjacent gap-8 data slots)`; the tool reports it and truncates + warns beyond it.
Gain is modest (e.g. ch0 2s→~4.5s) but safe and immediate.

## Approach B — full re-mux + grow (bigger extensions)  [PHASE 2B, if needed]
To exceed the channel's gap-8 run, the interleave must give it more gap-8 slots:
- Re-mux the whole AUDIO*.XA (grow the file) so the target channel keeps gap-8 for the longer
  duration; short "done" channels stay as gap-8 data slots. File grows → LBA reflow the disc (reuse
  `build_long_fmv_disc.py`; loads are by-name/CdSearchFile, shift-tolerant).
- More complex (touches the interleave for all channels); only if A's capacity is insufficient.

## Verification (PHASE 3) — VERIFIED in-game ✅ (2026-07-04)
Confirmed on real hardware-path playback (operator's DuckStation, disc `build/ABL_XAEXT`, AUDIO5 ch0
"crack open the seed" extended 2s→4.5s with a test tone):
- **By ear:** the cue played the full **~4–5s** tone (not cut at the original ~2s).
- **Objective (CD LBA trace, port 2346):** during the cue the CD streamed AUDIO5 continuously from
  file sector ~160 **through 679 and on to ~950** — past the ORIGINAL EOF (344), through the moved
  EOF (**672**). Had it stopped at the original length the stream would have halted near 344.
⇒ **Voice length IS the XA EOF marker (data-driven), NOT a software end-sector.** The earlier risk
(that voice might reuse the music engine's software `cur >= end_sector` loop) is **RULED OUT** for
one-shot voice. So Approach A (convert gap-8 data-slots + move EOF, size-preserving) is correct and
`extend=True` is the right default for the SFX GUI's XA path. Beyond the gap-8 capacity, Approach B
(re-mux + reflow) is still the path — but the core is proven.

## Phases
- **Phase 1 (now):** build Approach A in tooling (`extend_xa_voice`: convert gap-8 data-slots + move
  EOF, report capacity, truncate+warn). Size-preserving.
- **Phase 2:** wire into `media_replace.py audio` (auto: fits-native→splice; needs-more→extend) and
  the SFX GUI XA path (a "full length" toggle, mirroring the FMV GUI).
- **Phase 2B (if capacity insufficient):** Approach B re-mux + disc reflow.
- **Phase 3:** in-game LBA-trace verification from the Training start; then enable by default.

Related: [[Finding - SFX replacement]], [[Finding - Longer FMV playback (normal-speed extension RE)]],
[[media-replace-fmv-audio]], `src_re/xa_voice_streaming.c`.
