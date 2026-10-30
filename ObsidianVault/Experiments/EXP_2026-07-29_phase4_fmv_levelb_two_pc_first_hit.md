---
campaign: fmv_playback
row: E15_fmv
dimension: lifecycle
status: live_window_falsified
---

# Completed-Level-B typed two-PC first-hit boundary

The measured packet retained only `fmv_playback` / `E15_fmv`; the first
unmet dimension remained `lifecycle` and the scheduler-bound lane was
`static`. Recursive inventory found 110 files in the operator Phase-4 tree,
147 in the broader operator movie tree and 135 in the centrally provisioned
tree. No operator-owned movie bytes were imported.

Ordered regeneration reproduced 55/55 preserved capsules, all 107 queue
rows, nine derived indexes over 34 rows and E15 as the sole selected campaign.
The current `fmv-lifecycle-v2` index and the prior closed frame-15816
projection remain the applicable offline evidence. No new offline query was
executed because the missing fact was a typed current-debugger boundary, not
another frame-domain observation.

## Static interface result

`tools/phase4_duckstation_two_pc_first_hit.py` now owns a closed plan over
the complete statically reconstructed first-hit set:

- `0x8004FD74`, requiring pre-instruction registers `a0=3`, `a1=0`;
- `0x8005029C`, requiring pre-instruction registers `a0=6`, `a1=128`.

The adapter requires a valid paused anchor with no existing breakpoints,
installs exactly two managed execute breakpoints, lists both before one
`debugger.resume`, and accepts only the first paused target. It checks the
target-specific `pc/a0/a1` identity, requires exactly one winner hit and zero
loser hits, removes both owned breakpoint IDs, proves the breakpoint list
empty, and retains an atomic register capture. Every command/result body is
hash-retained under one server-session ID with finite frame, polling and
socket bounds.

Ordinary managed breakpoints are deliberate. The current debugger documents
temporary breakpoints as auto-clearing `bp_0` entries that cannot be removed
by ID, so they cannot prove cleanup of the non-winning stop.

## Falsifier and boundary

Both statically possible winners reproduce in deterministic synthetic
transcripts. Focused mutations reject a changed PC or register ABI, a
temporary/missing stop, resume without the exact pair, a pre-existing
breakpoint, an unexpected pause, a second/ambiguous hit, failed cleanup,
unbounded polling, stale debugger identity and incomplete atomic capture.

Generated artifact
`analysis/phase4_fmv_levelb_two_pc_first_hit.json` joins the current
DuckStation source/binary/API surface, pristine-media authority, the prior
transition re-localization and the documentation-grade semantic source. It
records zero offline queries, zero live receipts, zero native first hits,
zero DMA events and zero promoted dimensions for this iteration.

No DuckStation process launched and no escalation was added. The natural
branch, its earlier frame/cycle, the first Region-B DMA event and fresh
campaign-verifier consumption of the three prior live receipts remain open.
The next lane stays `static`: a later immutable-before-ledger packet may
predeclare a strictly wider passive cold-boot receipt and an earlier-anchor
first-hit receipt that invokes this adapter. Neither may execute
retrospectively.

Campaign handoff: [[Game Solving Campaign - FMV Playback and Skip]].
Prior localization: [[EXP_2026-07-29_phase4_fmv_levelb_transition_relocalization]].

## Static live predeclaration successor

Outage recovery preserved and revalidated the next static packet without
launching DuckStation. Generated escalation
`P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT` now names one strictly wider
passive cold-boot receipt over emulator frames `15776..15872` and one precise
managed-breakpoint receipt over `15792..15856`.

The passive two-job plan validates through
`tools/phase4_duckstation_late_batch.py`, whose typed
`emulator_advance` prelude is required because the legacy batch adapter cannot
stage a cold-boot job to a nonzero emulator frame. Both jobs use the centrally
provisioned pristine LEVEL01 movie and change no gameplay input, code, data,
or disc bytes.

This is predeclaration, not runtime evidence. The immutable iteration-1
before-ledger has 29 executed entries and zero planned entries, so it cannot
authorize the new escalation retrospectively. The current v2 metrics
validator also admits only the older transfer-specific direct-command
observer schema; it does not yet admit the managed two-breakpoint stream.
The binding next static task is therefore a tracked receipt emitter plus
validator/mutation admission that derives the exact 64-frame observer bound,
retains all normalized add/list/resume/status/register/remove/capture results
under one owned server session, and preserves historical receipt semantics.

No live receipt, natural first hit, frame/cycle, DMA event, lifecycle
promotion, Canon change, or MOD-private contract is claimed.

## Managed two-breakpoint v2 receipt admission

Method-ratchet iteration 1 completed the binding static successor without
launching DuckStation. The tracked
`tools/phase4_fmv_levelb_two_pc_first_hit_live.py` now emits an
`abl-phase4-live-run-receipt/2` document from one uninstrumented paused atomic
anchor followed by the direct two-PC observer. Its runtime contract fixes the
capture to emulator frames `15792..15856`, derives the 64-frame ceiling and
finite result limits from the adapter, and retains normalized
add/list/resume/status/register/remove/capture results under the owned server
session.

`tools/phase4_method_metrics.py` now recognizes this direct observer only
through `abl-phase4-observer-plan/2`. It requires exactly the two statically
proved add-breakpoint operations, a completed paused atomic anchor, current
method-schema identities, the exact finite capture window, adapter replay of
every direct result body, both owned removals and final empty breakpoint
pagination. The existing exact-PC v2 path and historical schema-v1 atomic
path remain independently accepted.

Both possible winners pass deterministic admission transcripts. Mutations of
the 64-frame ceiling, winner/result identity, cleanup, server session,
pagination and event ordering fail closed. Generated artifact
`analysis/phase4_fmv_levelb_two_pc_first_hit.json` records the two admissions
and the emitter/runtime/validator source hashes while retaining zero offline
queries, zero live receipts, zero native first hits and zero promoted
dimensions.

This closes method admission only. The current immutable before-ledger retains
`P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT` as its sole planned entry; this
static packet did not consume that authority. The next live work packet must
close the predeclared wider passive receipt first, then the native
`15792..15856` first-hit receipt, and obtain fresh campaign-verifier
consumption. The natural branch, first Region-B DMA event and E15 lifecycle
dimension remain open.

## Native window falsified

The authorized live packet closed the wider passive pristine control first.
Its two uninstrumented jobs agree through emulator frames `15776..15872` and
end at frame 15872, cycle 8986205047, PC `0x8004FEA4`.

The precise profile then cold-booted the identical movie and paused at frame
15792, cycle 8940908745. It installed and listed both managed execute
breakpoints before one resume. Neither `0x8004FD74` nor `0x8005029C`
executed through the finite frame-15856 ceiling. The adapter recorded failure
frame 15857, removed both owned breakpoint IDs, proved the final list empty,
and the isolated profile stopped only its owned PID.

Generated artifact
`analysis/phase4_fmv_levelb_two_pc_first_hit_result.json` retains both closed
receipt hashes, both atomic batch hashes, the direct-result hash, normalized
command replay, pristine media/current debugger identities, passive endpoint
equality, and the exact no-hit falsifier. No natural branch, argument pair,
DMA event, lifecycle fact, Canon change, MOD-private contract, or promoted
dimension is claimed. Fresh campaign-verifier consumption remains pending.

The binding lane returns to `static`: re-localize an anchor before frame
15792 and do not replay the escaped `15792..15856` window.
