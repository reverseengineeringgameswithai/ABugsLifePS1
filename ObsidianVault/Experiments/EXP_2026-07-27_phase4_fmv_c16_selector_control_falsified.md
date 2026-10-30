---
kind: experiment
id: EXP_2026-07-27_phase4_fmv_c16_selector_control_falsified
date: 2026-07-27
phase: 4
campaign: fmv_playback
row: E15_fmv
status: staged_successor_intrinsically_valid_unadmitted
confidence: high
source_state: original_game
artifact: analysis/phase4_fmv_c16_selector_control_result.json
---

# Phase 4 C16 selector-control falsification and staged successor

## Claim and falsifier

Closure debt selected only `fmv_playback` / `E15_fmv`; `lifecycle` was the
first unmet policy dimension. The exact claim was that changing only the
resident C16 callsite word at `0x800500D4` from selector 46 to selector 40,
after a movie-frame-300 passive prelude, would preserve the loader ABI and
distinguish limit/completion/teardown behavior.

The explicit falsifier included a changed second word, failed original-word
verification/readback/invalidation, missing batch joins, truncation, or a
control that did not execute the typed prelude. The last predicate failed.
No lifecycle fact or dimension is promoted.

## Offline and static boundary

Ordered regeneration retained 55/55 capsules, a 107-row queue with zero
`offline_ready`, nine reusable derived indexes, and only E15 selected. Closed
offline receipt
`07a00b51829d7dd16254277834c86659a1b2275f0f59a8c68799ca2f75b148d5`
re-executes the tracked reader over all 16,060,589 bytes of external
`fmv-lifecycle-v2`. It finds the exact C16 and E15 movie identities and no
retained selector-40 counterfactual.

Pristine static reconstruction already fixes the 1,572-byte resident owner,
caller `0x800500D8`, selector instruction `0x800500D4`, loader
`0x8003E7C0`, mode zero, return `0x800500E0`, and the one permitted
`0x2404002E -> 0x24040028` word replacement.

## Executed result

Two fresh isolated profiles on ports 24671 and 24672 verified current
capabilities, pristine SCUS-94288 media, the pinned C16 movie/save identities,
two result-bearing atomic jobs each, and typed owned-PID stop plus
confirmation. The retained receipt identities are:

- passive: `cfbd104e589ca381dfe74364e45c88e8cfe313862b234844eb7d10353b94235a`;
- precise: `c7ea7e11010a4ba8f0f7258003476aff18558854835ffb8e6d22214b9e0b460c`.

The positive precise job verified the original word, wrote
`0x24040028`, invalidated translated code, and read back the replacement.
Its endpoint differs from the negative only at that callsite word. However,
all four jobs report `start_playback_index=0`, `target_frame=4006`, and
4,006 advanced frames. Their emitted raw spans are emulator frames
`265211..269217`, while the typed receipt bounds claim movie-frame starts 299
and 300. No loader, selected-limit, completion, or teardown observer event
appeared.

The operations completed, but the two v2 documents are not admissible live
receipts: their raw counters escape their typed clock/bounds, and the write
was applied before the intended guest/movie prelude. They are preserved only
as failed-plan evidence.

## Banking and handoff

`config/phase4_fmv_c16_selector_control_result.yaml` pins both receipts, full
batch results, raw counters, cleanup documents, executed plans, media and
runtime identity. `tools/phase4_fmv_c16_selector_control_result.py
--write --check` rederives the write/readback, one-word endpoint difference,
zero observer events, playback-index mismatch, raw-bound escape and two
owned-PID cleanups. Mutation tests reject each of those low-level facts.

The batch adapter now derives raw counters from the declared clock and rejects
nonzero movie-frame `scenario.loadStateAndRun` plans unless an atomic staged
recipe is present. The failed plan remains historical evidence and is not
rewritten by the successor below.

No Canon original-game behavior or MOD-private state was added.

## Static successor: atomic staged prelude

The next method-ratchet iteration first re-queried the exact external
`fmv-lifecycle-v2` index. Closed offline receipt
`26bfe5ae583443bc9faf62e3b0d02bfee13db1cfe8d8621bd62eecd93e602d3f`
re-executes the tracked reader over its 16,060,589 bytes: the C16 movie is
indexed, while the missing `scenario.loadStateAndRun` staging/interface fact
is absent. Static source and API reconstruction therefore remained the
binding lane.

The current DuckStation dispatcher now accepts one closed
`staged_prelude={kind: movie_advance, target_frame, max_frames}` on
`scenario.loadStateAndRun`. After state/media verification and movie startup,
it advances movie input and guest execution together, returns the actual
start/target/advanced counters, then arms instrumentation and applies the
identity-checked `after_load` write. Boot recipes, absent movies, extra keys,
zero or over-limit bounds and failed advances reject before the observer or
write.

`tools/phase4_duckstation_batch.py` mirrors that finite contract, requires the
same staged anchor in both branches, makes a nonzero capture start equal the
stage target, retains index zero in the execution bound, and derives replay
and observer counters separately from the completed result. Mutation guards
reject mismatched pair anchors, unreachable/over-limit stages and
noncontiguous result counters. `analysis/phase3_duckstation_rpc_manifest.json`
pins the rebuilt source, scenario documentation and running binary;
`analysis/phase4_fmv_resident_identity.json` pins the resulting static control
contract.

No DuckStation process was launched, no live escalation was authored, and no
live receipt or original-game behavior was claimed. The regenerated debt
ledger keeps E15 at four met/five remaining but moves its next lane to
`live`: predeclare and validate a fresh paired passive/precise escalation using
the staged recipe. The retired P4-ITER96 plans remain inadmissible.

## Fresh staged-recipe predeclaration

The next method-trial iteration first reused the exact preserved
`fmv-lifecycle-v2` index rather than scanning capsule bytes. Closed offline
receipt SHA-256
`3a7d9f33bbaa628f9ccbd7f4c35ba59554e6613a9404d8962451c46b186f4f10`
re-executes the tracked reader over 16,060,589 input bytes. It finds the
centrally pinned C16 movie hash and no `staged_prelude`,
`scenario.loadStateAndRun`, `after_load`, selector-40 label or replacement-word
run. The index therefore localizes the anchor but cannot manufacture the
post-stage counterfactual.

`P4-ITER99-E15-C16-STAGED-SELECTOR-LIFECYCLE-CONTROL` is now a generated
`planned` escalation. Its passive plan retains the actual execution bound
`[0,4006)` and begins capture at movie frame 299; its precise plan retains the
same execution bound, stages both branches to frame 300, and then changes only
`0x800500D4:0x2404002E->0x24040028` in the positive. Focused guards reject
stage-target drift, nonzero authored execution starts, unpaired anchors,
pre-stage writes, second-word changes and noncontiguous raw counters.

No DuckStation process launched. The controller had captured this iteration's
immutable escalation-before ledger before P4-ITER99 existed, so a live receipt
would not satisfy the accepted v2 method contract. The next controller
iteration must retain P4-ITER99 as planned, run the passive receipt first and
supply it to the precise batch. No original-game fact, roadmap dimension or
MOD-private state is promoted by this predeclaration.

## Executed staged successor

The next controller iteration's immutable escalation ledger retained
P4-ITER99 as planned. It reused the same closed offline receipt and then ran
the predeclared passive plan in isolated profile
`/var/tmp/abl-phase4-e15-passive-PFBDQE` on port 23991 and the precise plan in
`/var/tmp/abl-phase4-e15-precise-8x1Gem` on port 23992. Both numeric owned PIDs
were stopped and confirmed. The closed receipt SHA-256 identities are:

- passive: `926c85ae85b70a856cab78f1051690e53ec59d663c1b8a35f9a93a374dd2ed4e`;
- precise: `9b407d66c7808123884e112d3f0f73ba4cba433cfd9e79e141af9b2211c688d9`.

All four atomic jobs start movie playback at index zero, advance guest
execution and input together to 299 or 300, and then run to 4006. The retained
raw counters are exactly `[0,4006)` for replay and `[299,4006)` or
`[300,4006)` for observation. Every movie endpoint is reproducible and
untruncated. The passive repeat endpoints are byte-identical.

At the identical frame-300 staged status, the positive verifies, replaces,
invalidates and reads back only
`0x800500D4:0x2404002E->0x24040028`; the native negative performs no write.
The first loader entries occur at the same emulator frame 265655 and cycle
150414500686, with function `0x8003E7C0`, caller `0x800500D8`, mode zero and
return `0x800500E0` unchanged. The selector alone changes 46 to 40. At emulator
frame 265826, the first access event for signed limit `0x80131EEE` retains
instruction PC `0x800B6DC0` and reports callback PC `0x800B6DC4` while the
value changes 281 to 3162.

Both branches then execute balanced `StClearRing` and callback teardown pairs
through callers `0x800B749C` and `0x800B74A4`; their first occurrences are
frames 266545 and 267891 respectively. The native negative publishes
completion request 1 through observer PC `0x800B6B4C` at frame 266492. The
writing instruction is `0x800B6B48`; `0x800B6B4C` is the callback-reported
post-instruction PC. The
synthetic selector-40 branch does not publish that natural completion-request
event in the retained suffix and later consumes recorded input whose semantics
were authored for selector 46. Endpoint equality is therefore not required or
claimed.

The original falsifier survives intrinsically: the stage is contiguous, the initial code
basis differs by one word, and caller/mode/return/frame/cycle remain fixed
while selector/limit change exactly as predicted. This confirms only the
retained synthetic selector/limit/teardown observation. The trial-pinned
legacy index still conservatively denies P4-ITER83 at this media/movie anchor;
the current metrics validator therefore admits zero of these two investigator
receipts for method credit. It does not prove natural
selector-40 completion, finale or Menu ownership, pause/repeat/viewer/error
behavior, the full lifecycle dimension, or any MOD-private behavior. The next
lane returns to static decomposition of a non-overlapping continuation/control
basis.
