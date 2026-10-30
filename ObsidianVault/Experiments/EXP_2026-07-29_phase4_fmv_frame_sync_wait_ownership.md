---
campaign: fmv_playback
row: E15_fmv
dimension: lifecycle
status: shared_frame_sync_wait_ownership_corrected
---

# FMV frame-sync wait ownership correction

The measured work packet retained only `fmv_playback` / `E15_fmv`, named
lifecycle as the first unmet dimension, and kept the scheduler's `static`
lane. Packet SHA-256 is
`1f9b530c50934f57888b37e70243e3dfde00596750ab7492d02c3e788034bb83`.

Recursive inventory found 110 files below the operator Phase-4 movie tree,
147 below the broader operator tree, 135 centrally provisioned files, and
100 central Phase-4 files. No operator-owned bytes were imported. Ordered
preflight reproduced 55/55 capsules and 3,391,058,326 preserved external
bytes; the opportunity queue retained 107 rows with 91 open, 42
offline-partial and zero offline-ready; the derived catalog retained nine
indexes over 34 rows; closure debt selected only E15 at four of nine
dimensions.

## Hypothesis and method

The exact claim was that resident u32 `0x80082250` is a shared frame-sync
interrupt handshake rather than an FMV-running or retirement latch, and that
the frame-15720 PC `0x8004FEA4` is only one inline use of that shared
protocol.

The falsifier required rejection for an unclassified direct xref or helper
caller, a mismatched set/wait protocol, missing interrupt or pad clear,
FMV-exclusive lifetime, inflation of frame 15720 into a scene-call or
retirement result, or any load-bearing mutation that left the guard green.

The retained derived index and boundary were validated first. They contain
frame-boundary state but not exact resident instruction ownership, so no
capsule byte scan or duplicate offline query was justified. Static pristine
reconstruction answered the packet; DuckStation was not launched.

## Result

A complete compiler-standard adjacent-LUI direct load/store census finds ten
xrefs to `0x80082250`: four reads and six writes. Two context-save interrupt
handlers read and clear the field before `frame_present`. Pad subsystem start
and stop also clear it.

Shared helper `0x8003F2F0..0x8003F358` has five direct callers:

- `0x80052338` and `0x8005235C`, level-transition orchestrator;
- `0x8005B490`, transition fade/draw loop;
- `0x8005B644`, animated overlay display loop;
- `0x8005B7F8`, gameplay reset/cursor-seed entry.

The helper protocol at `0x8003F328..0x8003F348` and inline scene-flow
protocol at `0x8004FE98..0x8004FEB8` contain identical eight-word sequences:
set one, reload while one, and wait for an interrupt-owned clear. The field
is not FMV-exclusive.

## Banked boundary

`analysis/phase4_fmv_frame_sync_wait_ownership.json` records exact pristine
slice hashes, all xrefs and callers, instruction bodies, authoritative
source hashes, the retained frame-15720 boundary and the work-packet hash.
Focused tests zero load-bearing interrupt, pad, helper, inline-wait and caller
instructions and require the generator to fail. Artifact and boundary
mutations also fail closed.

The falsifier survived. Authoritative typed state now uses
`frame_sync_wait_latch`; `fmv_running_latch` remains only a historical capture
alias. Frame 15720 cannot locate either completed-Level-B scene-setup call or
the exact FMV retirement point.

No new offline receipt or live receipt was created because no such operation
was performed. No natural branch, exact retirement frame, DMA event, live
escalation or lifecycle dimension is promoted. The next safe step is a
distinct earlier state producer or a scheduler-lane change; the escaped
`15792..15856` observer remains retired.
