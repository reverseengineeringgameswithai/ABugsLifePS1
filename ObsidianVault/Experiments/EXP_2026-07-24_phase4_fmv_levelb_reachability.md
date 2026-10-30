# Phase 4 E15 corrected level-B reachability

## Question

Do either existing LEVEL01 lead—the centrally pinned full-level from-boot movie
or the pristine end-of-stage save plus its native completion/save recipe—reach
the completed-level-B caller at `0x8005031C`?

## Required funnel

The ordered Phase-4 regeneration retained 55/55 capsules and
3,391,058,326 external capsule bytes, 107 queue rows with 16 complete / 91
open, nine external indexes covering 34 rows, and only `fmv_playback` /
`E15_fmv` selected. The exact `fmv-lifecycle-v2` index reconstructs 4,549
frame records but contains only LEV1A and LOSE behavior. Static pristine scans
bind the completed-level call `0x8005031C -> 0x8003E7C0`, progress ID one to
selector 11, `BUGSFMV1/LEV1B.STR`, limit 485 and the common completion/teardown
frontier. Static reachability could not establish either candidate trigger.

The recursive movie inventory found
`movies/100% Runs/LEVEL01.movie.json`: 11,030,625 bytes, SHA-256
`ece62d4e6f92b887b0500dd8ac3bec48f3638ad5d9858cda7d5b0afb3a8d2602`,
v3, 15,230 frames and from-boot. Its filename was treated only as a lead.
`level01_end_of_stage.sav` is a centrally declared pristine 2,033,862-byte
state at SHA-256
`42047329754c56f6daaf413e192ba8e88ca40889714bbc9f57216f3462ed739f`.

## Superseded cold-boot movie attempt

Escalation `P4-ITER86-E15-LEVELB-LIFECYCLE-CONTROL` used one isolated profile
and an atomic two-job `scenario.runBatch` plan. Positive and neutral each cold
booted the hash-verified pristine CUE and advanced 18,000 frames with identical
bounded watches.

Both end at emulator frame 18,001 / cycle 10,191,652,884 and record zero exact
`0x8005031C` hits. The neutral branch observes typed FMV-player limit writes
156, 440 and 1,750. The movie positive observes those plus 386, proving it
reaches LEV1A. The positive completion-address watch reaches its 32-event bound
during pre-FMV address reuse; it is explicitly not used to exclude a later
completion write.

This receipt does not exclude the route. Its movie status reports
`from_boot=true` and `truncated=false` but `reproducible=false`: the boot recipe
did not restore the recorded boot anchor and armed precise observers from frame
zero. The zero caller hits and absent 485 event are retained only as failed-
observer provenance.

The 99,165-byte raw receipt is external at SHA-256
`669ff479be014be70b5381195c9cec8b2a7001447f9d1fcdad3487572b471aac`;
its 798-byte owned-PID cleanup receipt is
`d2f9867e70277a934af7350dca5858802cd7783d03b24f25589aa867f8918eda`.
The launcher stopped owned PID 1630355.

## Save-anchor method change

The first negative falsified the filename lead, so escalation
`P4-ITER87-E15-LEVELB-SAVE-ANCHOR-CONTROL` changed method instead of extending
the cold-boot observation. The client fallback was justified because the batch
surface cannot express the native save-state Up/Cross/Square held/press/wait
recipe. Instrumentation was re-armed only after each load.

Native and neutral branches have the exact anchor frame 7,162 / cycle
4,054,570,165 / PC `0x80010498` / SP `0x801FFE60` / scene 1. Both end at frame
12,302 / cycle 6,964,857,570. Native input changes scene 1 to 0; neutral remains
scene 1. Both retain zero exact completed-level caller hits and zero FMV
function events. Because the loader never ran, fixed Region-B FMV addresses
are untyped and their incidental access/value data is not authority.

The 136,858-byte raw receipt is external at SHA-256
`3aea80328c5ee8567f7e66fe04b755fe37fec81df89da3739135fc60fad2beb3`;
its 808-byte cleanup receipt is
`fcda9e890b7996a777c3ea32602efa3f5db2691fb29c3a646bb452cfd6eb05a3`.
The launcher stopped owned PID 1632571 after explicit controller, trace, turbo
and fast-forward cleanup.

## Recorded-anchor phase-neutral correction

Escalation `P4-ITER88-E15-LEVELB-PHASE-NEUTRAL-REVALIDATION` repaired the
load-bearing observer defect. `movie.traceToFrame` reset a transient copy of
the exact recording to its declared boot anchor for both an uninstrumented
cached-interpreter control and a passive-coverage pass. One unexecuted neutral
padding frame made the complete 15,230-frame source prefix observable. A
second transient derivative changed every non-neutral port-0 input to neutral;
both derivative files were deleted before banking.

Both original and neutral branches report `reproducible=true` and
`truncated=false`. Each passive pass exactly matches its own uninstrumented
RAM, register, cycle, emulator-frame and movie-frame endpoint. The original
input covers the level-A reset handoff `0x8005B788`, selected-limit writer and
completed-level-B caller `0x8005031C`. The neutral branch covers the
selected-limit writer but neither resident caller. This falsifies the
predeclared exclusion and proves that the existing full-level recording is a
natural level-B reachability positive.

The 209,259-byte raw result is external at SHA-256
`e1703728f98a7c55e7f70fc2dbd15e7e92f7f3a4eacd7a72283e0cd057e873ca`;
its 824-byte cleanup receipt is
`96e9790f22f7e0dfcc680547dd9fd1dfd6c93829fd86cffceeed6154ab0b0f34`.
The launcher stopped owned PID 1834352 for isolated profile
`/var/tmp/abl-p4-e15-levelb-phase-neutral.iter30b.24731`.

## Conclusion and boundary

The full-level recording is a positive natural level-B lead; only the
end-of-stage save recipe remains a bounded negative. The passive coverage is
cumulative, so it does not identify the first call frame/cycle, arguments,
selector 11/limit 485 publication, completion or teardown. Those facts plus
alternate/viewer paths, campaign breadth and adjacent C17/E14 policy remain
open. No closure dimension is promoted.

The next experiment should binary-localize the first `0x8005031C` frame from
this corrected positive, then predeclare one narrow instruction-attributed
same-anchor control for selector 11/limit 485 and downstream completion/
teardown. It must not infer viewer policy from the bonus selector.

## Guards

`tools/phase4_fmv_levelb_reachability.py --write --check` rebuilds
`analysis/phase4_fmv_levelb_reachability.json` from six hash-pinned external
receipts and validates fixtures, mounted media, debugger identity, exact
anchors/endpoints, both passive/control signatures, every coverage range and
owned-PID cleanup. It recomputes each PC-list digest and the exact caller
memberships instead of trusting authored booleans.
`tests/test_phase4_fmv_levelb_reachability.py` rejects rewriting the legacy
LEV1A selector 386 into level-B selector 485, falsifies an authored coverage
observation, and requires the corrected tracked summary to rebuild exactly.

The positive original-game reachability fact is promoted to Canon. No
MOD-private state or hook was introduced. Campaign scope remains in
[[Game Solving Campaign - FMV Playback and Skip]].
