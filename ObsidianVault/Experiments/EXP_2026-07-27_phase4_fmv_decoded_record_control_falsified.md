# Phase 4 FMV decoded-record control — observer saturation falsified

Date: 2026-07-27
Campaign: `fmv_playback`
Row: `E15_fmv`
Escalation: `P4-ITER102-E15-DECODED-RECORD-ABSENCE-CONTROL`

## Question

Does forcing only the decoded-record absence predicate at `0x800B6C40` cause
the instruction-attributed u8 stop-latch store at `0x800B6C84`, followed by
common teardown, while the identical native nonzero-record branch excludes the
store? The predeclared falsifier rejected any truncation or saturation.

## Retained result

The passive pair reproduced equal endpoints from the centrally pinned C16
movie/state/media anchor. In the precise positive, the sole post-stage change
was `0x800B6C40: 0x1220000E -> 0x1000000E`. It recorded one u8 write:

- instruction PC `0x800B6C84`;
- address `0x800B9A54`;
- old/new `0 -> 1`;
- frame `265861`, cycle `150531213774`;
- followed by ordered decode, `StClearRing`, and callback-teardown
  entry/exit events.

The native branch recorded no latch access and ended with latch zero and scene
nine. Its function trace nevertheless retained exactly the configured
64-event maximum, with indexes `27..90`. The first 26 function events were
therefore discarded even though the surrounding receipt pagination reported
complete.

## Interpretation

The positive instruction-attributed observation is retained, but the planned
same-anchor control is falsified by observer saturation. In particular, the
retained native suffix cannot prove that teardown was absent from its discarded
prefix. Neither live receipt is admission evidence for a lifecycle or roadmap
dimension, and native failure frequency or malformed-media policy remain
unclaimed.

The authoritative machine result is
`analysis/phase4_fmv_decoded_record_control_result.json`, generated from
`config/phase4_fmv_decoded_record_control_result.yaml` by
`tools/phase4_fmv_decoded_record_control_result.py`. It pins the immutable
before-ledger, closed offline receipt, both live receipts, raw results,
pagination, command events, owned-PID cleanup, plans, media and debugger
identities. Raw and copyrighted bytes remain external.

## Static retention decomposition

The completed native batch result is now consumed by closed offline receipt
`7156595a5e9822afa871075802ccfe0fd7b4f5ef60fc46aa89fe00f72f329b1b`.
It re-executes the tracked Phase-4 reader over all 295,593 bytes of exact
retained input SHA-256
`4d43e6ee87a8d822a57c55b95d8756973e1fbeea69bd9f5dbf2e86114a1a7968`.
The monotonically increasing final function-event index proves exactly 90
events over movie frames 650 through 850, or 0.45 events per movie frame. The
receipt deliberately does not infer the types of the discarded 26-event
prefix.

Hash-verified pristine `FMV/FMV.BIN` independently fixes the decoded-record
helper call at `0x800B7280`, its `0x800B6C24` target, the stop-latch read at
`0x800B728C`, and the common-exit branch at `0x800B7294` in a guarded 36-byte
window. The generated machine result now binds those static facts to a finite
successor: a 128-event ring has 38 events of same-window headroom.

## Next lane

`P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL` is the sole planned live
successor. Its guard rejects any native result that starts after index one,
ends after index 90, returns more than 90 events, or reaches the 128-event
limit. The precise receipt still requires its separately retained wider
passive prelude. This iteration did not launch DuckStation, create a live
receipt, promote lifecycle, or change Canon/Mods behavior.
