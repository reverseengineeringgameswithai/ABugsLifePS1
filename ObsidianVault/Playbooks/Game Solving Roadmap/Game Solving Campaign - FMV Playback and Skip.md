---
kind: campaign
id: fmv_playback
phase: 4
family: audio_cinematics
rows: [E15_fmv]
status: active
evidence: [analysis/phase4_fmv.json, analysis/phase4_offline_fmv_batch.json, analysis/phase4_fmv_static_owners.json, analysis/phase4_fmv_interface_frontier.json, analysis/phase4_fmv_lifecycle_continuations.json, analysis/phase4_fmv_resident_identity.json, analysis/phase4_fmv_callback_lifecycle.json, analysis/phase4_fmv_natural_completion.json, analysis/phase4_fmv_natural_exit_cause.json, analysis/phase4_fmv_teardown_ownership.json, analysis/phase4_fmv_lose_lifecycle.json, analysis/phase4_fmv_levelb_reachability.json, analysis/phase4_fmv_levelb_first_call.json, analysis/phase4_fmv_finale_route_probe.json, analysis/phase4_fmv_menu_owner_coverage.json, analysis/phase4_fmv_menu_phase_neutral_live.json, analysis/phase4_fmv_c16_selector_control_result.json, analysis/phase4_fmv_decoded_record_control_result.json, analysis/phase4_fmv_decoded_record_retention_result.json, analysis/phase4_fmv_cd_event_exit_result.json, analysis/phase4_fmv_file_open_failure_result.json, analysis/phase4_fmv_region_b_replacement_ownership.json, analysis/phase4_fmv_levelb_region_b_dma_attempt.json, analysis/phase4_fmv_levelb_region_b_dma_late_arm.json, analysis/phase4_fmv_levelb_region_b_dma_late_result.json, analysis/phase4_fmv_levelb_region_b_dma_subwindow.json, analysis/phase4_fmv_levelb_region_b_dma_exact_pc_arm.json, analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json, analysis/phase4_fmv_levelb_transition_relocalization.json, analysis/phase4_fmv_levelb_two_pc_first_hit.json]
---
# Game Solving Campaign - FMV Playback and Skip

## Scope and current decision

This active E15 campaign owns FMV path/frame selection, playback, native skip,
natural completion, pause/stop, stream/decode errors, Region-B residency and the
handoff to the owning scene or frontend transition. E12 retains general audio
policy, C17 retains movie-viewer selection/unlocks, E14 retains persistence and
E16 retains the generic overlay/resource loader.

The campaign is **not complete**. The exact static dispatch, caller, player,
completion-request and callback/consumer census, one causal LEV1A
Start-skip control, and natural cold-boot dlogo/title/intro sequence are
reproduced. The player-boundary typed state is exhaustive for direct absolute
accesses in its three declared state ranges. Selector 2 is a reviewed unreachable pristine manifest row,
not a movie-viewer route. Both optional callback slots, all three guarded
deliveries, callback installation and teardown, all nine synchronous resident
consumers, the partitioned six-target main-shell dispatch after the boot
returns, and the four
reachable exceptional-function categories are exact. The matching-C wrapper
also proves an unconditional FMV.BIN copy on every invocation and assigns
post-player Region-B replacement to the resident caller or a later loader.
Remaining live manifest paths plus native pause/stop and exceptional lifecycle
behavior remain open. A
current same-anchor control proves the Start-positive common-exit
`StClearRing` then callback-teardown sequence and excludes both calls from its
541-frame no-input control. A longer receipt proves no-input reachability at
frame 5305; an instruction-attributed successor identifies selected-limit
writer `0x800B6B48` after backloc reaches 384 of 386, with no resident
decoded-record stop-latch write. Pristine teardown bytes now reconcile its
functionTrace synthetic-unwind label with a conventional guest return, bind
both callback backends, exhaust every direct default-ready-slot xref, and
identify the unchanged captured words as CD-ROM MMIO pointer cells rather than
callback storage. A distinct C16 game-over control now binds natural selector
46, `BUGSFMV2/LOSE.STR`, limit 281, completion through `0x800B6B48`, the
balanced common teardown and loader return. A corrected recorded-anchor
control now proves that the 15,230-frame full-level input naturally reaches
completed-level-B caller `0x8005031C`; its all-neutral derivative reaches
neither that caller nor the level-A handoff. A bounded successor localizes the
first call to movie frame 14,382, observes selector 11/mode -1 at the loader,
publishes limit 485 and completion through `0x800B6B24`, then reaches balanced
common teardown. Its same-window all-neutral branch excludes that exact
Level-B route while retaining two different generic frontend loader entries.
The complete LEVEL15 recording was then rejected as a finale fixture lead:
register-filtered caller coverage finds neither selector-40 finale C nor
finale D after complete consumption of all 33,268 input samples, while an
unfiltered `0x80050284` query records 326 cold-boot address-reuse aliases. The
superseded playback-index-33,267 receipt omitted final input index 33,267; the
current guard targets `frame_count=33268` and stops at emulator frame 33,269.
No playback lifecycle is inferred from that negative.
The two central Menu-Navigation leads were then replayed through four typed v2
receipt runs. Both precise traces hit all three boot callers and zero of the
six non-boot candidates, but those zeros are inadmissible: both precise
endpoint controls diverged, Menu v2's passive repeat also differed by one
cycle/CPU capture, and all four movie statuses retained
`reproducible=false`. The machine artifact therefore falsifies the full-span
paired-PC method, promotes no owner exclusion, and binds an internally
phase-neutral single-observer redesign as the next experiment. That
replacement has now also been executed and falsified. Both native observers
changed RAM and reported repeated cached-block hits at bare PCs `0x800500D8`
and `0x80050284`. Those observations do not establish resident owner code,
selector or caller identity. Complete Menu replay is retired as an exclusion
method. Static reconstruction now qualifies both shared PCs against the
pristine resident executable, the 1,572-byte scene-flow owner, exact callsite
windows and the selector/call/delay ABI. It also specifies a bounded C16
single-word selector-46 versus selector-40 discriminator. Its first
predeclared control verified, wrote, invalidated and read back exactly that
word, but every job restarted movie playback at index zero rather than
executing the typed 299/300-frame prelude. The raw counters therefore escape
their movie-frame bounds, no lifecycle observer fired, and both emitted v2
documents are inadmissible. The retired plans remain rejected. The current
debugger and adapter implement a closed atomic `staged_prelude` that
advances recorded input and guest execution from the actual playback index
before observer arming or `after_load`, retains its own playback counters, and
forces the receipt execution bound to include index zero. P4-ITER99 has now
executed the guarded passive/precise pair. All four jobs stage contiguously and
remain inside the typed bounds. At the identical frame-300 status, the exact
one-word change preserves loader caller, mode, return, frame and cycle while
changing selector/first limit from 46/281 to 40/3162; both paths retain
balanced common teardown. The native branch publishes its completion request,
but the synthetic branch does not publish a natural completion request in the
recorded suffix. This confirms the bounded selector/limit/teardown interface,
not natural finale/Menu ownership or lifecycle closure. The next lane returns
to static continuation decomposition, not another selector replay.
The original-oracle,
complete-frontier, typed-state and durable-evidence dimensions plus the
teardown sub-boundary are met. The subsystem-wide original-interfaces
dimension remains partial with the other four closure dimensions because
level/viewer continuations and the E12/C17/E14/E16 boundaries still intersect
it.

The durable-evidence promotion is deliberately narrower than a behavioral
promotion. The regenerated central fixture set names every C16-to-E15 consumer
and generator, including the LOSE lifecycle paths and the phase-neutral
level-B collector/validator pair. The
knowledge audit reports 1,032 centrally pinned fixtures with zero missing
pins, untracked imports, operator-fixture errors or relocation errors; the
55-capsule preservation set and all centrally declared live receipts remain
hash-valid with owned-PID cleanup. The current versioned offline index also
reconstructs both joined capsules: 4,549 frame records and all 18 queue queries
in external `fmv-lifecycle-v2`, SHA-256
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
Sixteen direct low-level assertions, twenty tracked authoritative paths and two
explicitly non-intersecting residuals make the claim falsifiable. Independent
closure-debt mutations reject a stale fixture-set hash and stale nine-query
contract. This does not reduce lifecycle, breadth, cross-system, source or
original-interface debt, and it does not authorize a replay.

## Reproduced frontier

- pristine `FMV/FMV.BIN` SHA-256
  `a2ba85b4404f55e5b99189513e10959d2c8b99c9ba5c1f5aadcdbc26633f9fc9`;
- 40 unique manifest paths paired with 40 exact
  `addiu a1,zero,frame_count` rows, spanning 156 through 3,162 frames;
- resident FMV load, wait/bridge and shell-completion region identities;
- typed resident shared frame-sync wait, scene, shell-substate and
  stream-backloc fields; the historical `fmv_running_latch` capture name is
  retained as an alias only;
- Region-B completion and selected-limit fields guarded by the exact pristine
  FMV.BIN 0x100-byte head hash;
- centrally pinned state/movie pair with nine Start-only samples at frames
  334 through 342 and no other active input;
- exact branch equality at movie frame 333: cycle `2585837573`, emulator frame
  4568, PC `0x80070D00`, RAM SHA-256 `1044d5b7…24e5`, register SHA-256
  `754f0d34…3117`, and SP `0x801FF600`;
- immediate post-input PC split at movie frame 343:
  `0x80065340` with Start and `0x800B98F0` with Start removed, while both still
  retain pristine FMV.BIN and selected limit 386 for `BUGSFMV1/LEV1A.STR`;
- final movie boundary 541: the Start branch has retired FMV.BIN and backloc
  73; the Start-removed control still retains exact FMV.BIN identity, completion
  request 0, selected limit 386 and backloc 163; and
- nonzero, untruncated resident shell/load, libcd/libpress and FMV-overlay
  coverage for all six retained branch points, with every trace cycle/RAM/
  register/frame neutral against its own uninstrumented control;
- offline reconstruction of all 542 retained E15 records: exact FMV.BIN head
  residency at frames 69..416, completion clear at 86, selected-limit reset at
  168, LEV1A limit 386 at 183, backloc 1..73 over frames 218..362, and a
  one-frame retirement bound between 416 and 417;
- SPU-RAM changes only at frames 1..9 and 229..362 in this capsule, with no
  post-initial actor-pool, contact-pool, or boot-buffer-word delta intersection;
  these remain frame correlations rather than voice/producer ownership;
- centrally pinned `movies/go_to_end/LEVEL01.movie.json` SHA-256
  `bfedc0d0…40fb`, v3, pristine-serial and explicitly `from_boot`;
- an ephemeral timing-matched recipe that changes all 7,429 non-neutral port-0
  frames to neutral, records the exact changed-frame digest, and deletes the
  derivative bytes before retaining evidence;
- natural `BUGSFMV3/dlogo.str` completion at movie frame 3000 with request 1,
  limit 156 and backloc 154; natural `BUGSFMV3/tt.str` completion at frame 4600
  with limit 440/backloc 438; and natural `BUGSFMV2/INTRO.STR` completion at
  frame 8400 with limit 1750/backloc 1748;
- the exact FMV.BIN head remains resident across all three streams while the
  completion request and selected limit reset to 0 at frames 3200 and 4800;
- Region B is no longer FMV.BIN at frame 8500, and scene/shell state is 1/1 at
  frame 9400; and
- all eight cold-boot boundaries are full-RAM/register/cycle/frame neutral.
  The final trace has nonzero, untruncated resident, libcd/libpress, overlay and
  exact `0x800B6B00..0x800B6B60` completion coverage.
- all 47 FMV.BIN selector targets, with 40 stream cases, no-stream selectors
  3..9 and the common stream-start call;
- all nine direct resident `fmv_bin_load` calls across four bounded caller
  regions, plus both exact 16-byte selector tables resolving all level-A and
  level-B streams; and
- the single resident bonus-cursor read/write path, including modulo-256 wrap,
  ordinary ALT1/ALT2/ALT3/INTRO/LOSE outcomes and the exceptional old-255
  LEV15D outcome;
- selector 2 (`fmv/ad.str`, limit 1410) reviewed unreachable across the closed
  direct argument sources, all 23 pristine resident/level/MEMORY/FMV code-owner
  images, zero loader literals or standard computed materializations, exact
  def-use for the four formerly unresolved resident JALR sites, and the retained
  139-site resident indirect-call census;
- exactly three completion-request writers and one reader, with request one
  reaching the player stop target and bounded teardown; and
- exact player bounds with 50 direct calls to 30 unique targets and no `jalr`;
- 30 Region-B address rows with 99 exact absolute xrefs, 58 player-local xrefs,
  six pointer aliases and zero unclassified accesses across the entire
  `0x800B5788..0x800B9A4C` FMV code extent and three declared state ranges;
- a contiguous decode-commit record with current/prior frame indexes, stop
  latch, and cached width/height, including all seven previously omitted xrefs
  at `0x800B6B14`, `0x800B6B54`, `0x800B6B6C`, `0x800B6BB8`, `0x800B6BC0`,
  `0x800B6BD0`, and `0x800B6BE0`; and
- a typed two-pointer/active-index buffer record, two-slot RECT bank,
  presentation RECT, scalar domains, entry ABI, initialization/reuse and
  three-allocation teardown contract;
- the 11-function callback frontier, including fixed handler installation,
  wrapper/interrupt delivery, both disabled optional callback slots and all
  three guarded delivery sites, common
  critical-section teardown, and exhaustive resident SDK-call censuses;
- all nine synchronous loader consumers with exact hook-enable values, return
  PCs and shell/scene/completion/reset continuations, including the complete
  `0x8005B714..0x8005BC64` level-A owner and all 20 direct calls after the
  loader return, with `0x8005B7CC -> 0x8003F358`; and
- the three boot returns joined to the guarded `0x8004FC34` indirect dispatch,
  all six `0x8001B3C4` targets, five exact 20-byte target fragments, their
  destination stores, the guarded `0x8004FCF0 -> 0x8004FD04 -> 0x8004FD0C`
  scene-resolution link, and the separate `0x8004FCA0` scene-flow owner; and
- all 21 cited source files validated at generation time, with the twelve external
  handwritten ASM sources—including the split `0x80070A40` part—required to
  match `tools/repro_inputs.sha256`; and
- exact file-open failure, no-record stop-latch, finite decode-timeout and CD
  submission-retry branches without inflating static control flow into runtime
  outcome claims; and
- three hash-pinned current atomic receipts: two rejected early trigger
  hypotheses, shared `StClearRing` initialization at emulator frame 4443, and a
  movie-end causal control where only Start-positive calls player-exit
  `StClearRing` from `0x800B749C` then callback teardown from `0x800B74A4` at
  frame 4671 and retires FMV.BIN;
- one hash-pinned 1,500-frame atomic receipt from the same E15 save: no-input
  naturally reaches those same player common-exit call sites at emulator frame
  5305, 634 frames after Start and 529 frames beyond the earlier no-input
  endpoint; natural callback teardown returns normally while the Start trace
  retains its synthetic-unwind observer event, and both endpoints retire
  FMV.BIN;
- callback teardown `0x800709AC..0x80070A30` with a conventional balanced
  guest return to `0x800B74AC`, distinct from the preserved functionTrace
  synthetic-unwind event label;
- both teardown backends: default `CdDataCallback`/`CdReadyCallback` clears and
  mode-1 FMV.BIN channel-3/ready-slot wrappers;
- default ready slot `0x800818C8` with eight exhaustive direct xrefs, five
  reads, three writes and four guarded dispatches, plus the default data API's
  exact `DMACallback(3, callback)` SDK boundary; and
- pristine pointer cells `0x80081C28..0x80081C37` equal to
  `0x1F801800..0x1F801803`, with teardown byte stores through cells 0/3 to
  CD-ROM MMIO registers 0/3. The retained equal endpoint words observe pointer
  cells, not either volatile target byte; and
- a cycle-neutral staged C16 control that reaches
  `0x800500D8 -> 0x8003E7C0` with selector 46/mode 0, selects the
  281-frame `BUGSFMV2/LOSE.STR`, publishes completion through `0x800B6B48`,
  executes the balanced common teardown and returns to `0x800500E0`. Its
  frame-zero precise predecessor is retained only as observer-desync
  provenance because it made the movie non-reproducible; and
- a recorded-anchor passive control whose original and all-neutral branches
  are each reproducible, untruncated and RAM/register/cycle/frame neutral
  against their own uninstrumented run. Only the original input covers
  completed-level-B caller `0x8005031C` and the level-A handoff `0x8005B788`;
  and
- twelve internally controlled, untruncated passive localization queries that
  bind movie frames 14,381 absent / 14,382 present, followed by exact
  `0x8005031C` progress-ID-one pre-delay state and `0x8003E7C0` selector
  11/mode -1 post-delay state;
- selected limit 485 at frame 14,719, completion request 0 to 1 through
  frame-order-regression writer `0x800B6B24` at frame 15,763, zero FMV-owned
  decoded stop-latch writes, and ordered `StClearRing`/balanced callback
  teardown at frame 15,816; and
- a timing-matched all-neutral control with zero completed-Level-B caller,
  caller-owned loader or limit-485 event, while two generic frontend loader
  entries remain preserved rather than being suppressed; and
- a complete, cycle-neutral LEVEL15 fixture classification with zero exact
  selector-40 finale-C hits and zero finale-D hits after all 33,268 samples
  are applied, plus a guard proving that 326 unfiltered `0x80050284` hits are
  cold-boot address-reuse aliases rather than resident finale calls.
- one closed passive and one closed precise P4-ITER99 v2 receipt with four
  completed atomic jobs, 16,024 bounded replay frames, 14,826 bounded observer
  frames, exact selector-only write/readback/cache invalidation, same-anchor
  loader 46/40 and limit 281/3162 interfaces, balanced teardown in both
  branches and two confirmed owned-PID stops.

The filename supplied only a lead. The classification comes from the exact
single-variable edit, equal pre-trigger signatures, post-input PC split and
final overlay-residency difference on verified pristine media.

## Open binding work

1. Keep complete Menu-movie bare-PC replay, the unstaged P4-ITER96 C16 plans,
   the closed decoded-record window and the falsified file-open diagnostic
   route retired. Statically reconstruct the actual path/argument ownership
   from the forced `0x800B6E4C` target to the divergent selected-limit
   endpoint before considering a different experiment family.
2. Keep the escaped `15792..15856` two-PC managed-breakpoint observer retired.
   Static reconstruction now closes the formerly opaque early
   request-acceptance return from its only result setter through the wrapper
   and caller branch. That contract still cannot select natural execution or
   an exact frame. Change to a different static lifecycle question or
   scheduler lane before considering another live packet; do not relabel or
   widen the escaped observer.
3. Preserve the falsified timeout width/height hypothesis and the corrected
   static selected-slot `x`/`y` ownership, then capture natural decode
   timeout, CD failure and malformed-stream behavior without inferring it
   from the static correction or manufacturing a successful path.
4. Bind remaining level/viewer completion/transition writers and the
   E12/C17/E14/E16 interfaces before promoting E15 or any shared consumer.

## Guard and handoff

`tools/phase4_fmv.py` regenerates the retained static/live artifact only from
hash-pinned inputs and a freshly isolated debugger instance.
`tests/test_phase4_fmv.py` recomputes exact low-level predicates, provenance,
static rows, fixture pins, schema agreement and mutation failures, then checks
that E15 remains open. `config/phase4_fmv.yaml` is the typed residency and
MOD-safety contract.

`tools/phase4_fmv_lifecycle_continuations.py --write --check` independently
validates the complete matching-C wrapper, its six ordered direct calls,
unconditional Region-B reload, nine resident return continuations and five
transient player windows. `tests/test_phase4_fmv_lifecycle_continuations.py`
mutates every owner window and the exact reload edge, so the zero-unclassified
summary cannot survive pristine-byte drift.

`tools/phase4_fmv_static_owners.py --write --check` independently regenerates
the selector/caller/player/completion artifact from pristine staged bytes and
enforces the exact historical-oracle exception.
`tests/test_phase4_fmv_static_owners.py` recomputes it and mutates the dispatch
bound, call census, level table, completion reader, literal and computed loader
materialization scans, typed-state xrefs, any unclassified direct access in the
declared ranges, and the historical cleanup receipt so authored summaries
cannot pass alone.

`tools/phase4_fmv_interface_frontier.py --write --check` independently scans
the pristine resident executable and FMV.BIN for callback installers,
delivery through both optional slots, teardown, all direct consumers, the
six-target main-shell dispatch and source partitions, return continuations and exceptional
branches. `tests/test_phase4_fmv_interface_frontier.py` recomputes the artifact
and mutates callback materialization, each optional-callback setup/delivery,
the main-shell table and target semantics, teardown, the level-A scene-load
continuation, another consumer continuation and timeout
instructions. It also rejects any absent or drifted cited source. Its complete-
frontier claim has only non-intersecting residuals; lifecycle and breadth
remain open.

`tools/phase4_fmv_resident_identity.py --write --check` independently verifies
the pristine resident executable, exact scene-flow ASM pin, owner-range hash,
both shared-PC identity windows and selector/call/delay ABI, then validates the
single-word C16 selector discriminator and finite control windows.
`tests/test_phase4_fmv_resident_identity.py` recomputes it and mutates both
callsites, the loader target/ABI, staged-counter contract, after-load
fail-closed contract and the semantic source. The generated artifact binds the
current debugger dispatcher, scenario documentation, release binary and
tracked batch adapter. It now joins the two executed P4-ITER99 receipts to the
banked result artifact and requires the survived selector-interface falsifier,
two intrinsically valid receipts, zero method-trial-admissible receipts and no
dimension promotion. The trial-pinned conservative P4-ITER83 entry overlaps
the C16 anchor, so static work must identify a non-overlapping continuation or
control basis before another replay.

`tools/phase4_offline_fmv_batch.py` independently reconstructs both current
capsules, pins the versioned external derived index and all 18 queue queries,
and rejects drift in the reader, movie set, capsule pins, query distribution,
queue rank, record counts, residency window, typed changes, scheduled range
counts and selected E15 boundary PCs. The historical `fmv-skip-v1` index
remains preserved for older receipts; `fmv-lifecycle-v2` is the current
scheduling source. These findings narrow later experiments; they do not
replace a native control.

`tools/phase4_fmv_callback_lifecycle.py --write --check` verifies three
external current-toolchain batch receipts, the exact plan/media/state/debugger
identities, both same-anchor jobs, caller/order/frame/cycle events, endpoint
FMV.BIN identity and owned-PID cleanup. Its mutation tests reject a changed
caller, false negative teardown, media or residency drift and plan-bound drift.

`tools/phase4_fmv_teardown_ownership.py --write --check` independently scans
hash-verified pristine executable/FMV bytes, joins the retained live event
without rewriting it, and enumerates the balanced guest epilogue, both callback
backends, every direct ready-slot access/dispatch, the default-data SDK
boundary, MMIO pointer table and both target stores.
`tests/test_phase4_fmv_teardown_ownership.py` recomputes the artifact and
mutates the return, ready xref, pointer cell, FMV caller and retained live event.
It closes the teardown sub-boundary without promoting `original_interfaces`;
remaining level/viewer writers and E12/C17/E14/E16 contracts are explicit
intersecting residuals, while lifecycle, breadth, SDK-private and
observer-provenance residuals remain separately bounded.

`tools/phase4_fmv_natural_completion.py --write --check` verifies the external
1,500-frame current-toolchain receipt, exact plan/media/state/debugger identity,
the prior 541-frame retained-FMV boundary, both same-anchor jobs, common-exit
caller/return/frame/cycle order, endpoint Region-B identity and owned-PID
cleanup receipt. Its mutation tests reject caller, unwind, media,
endpoint-residency, cleanup and run-bound drift. It closes one LEV1A
common-exit reachability fact; it does not identify the cause.

`tools/phase4_fmv_natural_exit_cause.py --write --check` verifies the
instruction-attributed 1,100-frame same-anchor result and cleanup receipts.
For no-input LEV1A, it binds selected limit 386, backloc 384/385, exact
completion writer `0x800B6B48`, zero resident stop-latch writes, and the later
common exit. Its tests reject writer, ordering, stop-latch, truncation,
endpoint, plan and cleanup drift. This reduces one lifecycle residual without
promoting lifecycle or original interfaces.

`tools/phase4_fmv_lose_lifecycle.py --write --check` verifies the failed
frame-zero atomic receipt plus the reproducible staged C16 result, exact
movie/save/media/debugger identities, cycle-neutral cached prelude, selector,
limit, completion, balanced teardown, endpoint and both cleanup receipts.
`tests/test_phase4_fmv_lose_lifecycle.py` rejects observer-status, selector,
writer, truncation, control-neutrality and receipt drift. This binds one
natural LOSE path without promoting lifecycle, breadth or original interfaces.

`tools/phase4_fmv_levelb_reachability.py --write --check` verifies six
external result/cleanup receipts for the corrected movie and bounded save
leads. The old precise-observer receipt is preserved as non-reproducible
provenance. The phase-neutral recorded-anchor receipt instead proves that only
the original full-level input covers caller `0x8005031C`; both branches match
their own uninstrumented endpoint and the generator recomputes every PC-list
digest and membership. The end-of-stage native/neutral branches remain an
exact save-trigger negative. This is positive natural reachability, not exact
call timing, selector/limit causality or a dimension promotion.

`tools/phase4_fmv_levelb_first_call.py --write --check` independently verifies
the externally retained result and owned-PID cleanup receipt. It recomputes all
12 passive localization comparisons, exact pre/post-delay register boundaries,
instruction-attributed limit and completion writes, stop-latch exclusion,
ordered common teardown, trace truncation/counts, and the scoped all-neutral
control directly from low-level events. Its mutation guards reject changes to
localization neutrality, caller/loader registers, writer choice, teardown
semantics, control scope, truncation and cleanup. This reduces the named E15
lifecycle residual without promoting a subsystem dimension.

`tools/phase4_fmv_finale_route_probe.py --write --check` independently verifies
the complete external LEVEL15 result and owned-PID cleanup receipt. It
recomputes fixture/media/debugger identities, four internally controlled
coverage queries, complete consumption through target 33,268, exact endpoints,
truncation, the 326-hit bare-address alias and zero exact finale-owner hits.
Mutation guards reject the superseded 33,267 target, active playback at that
incomplete cursor, false owner coverage, bare-count drift, comparison
divergence, truncation and cleanup failure. This rejects one fixture lead and
promotes no subsystem dimension.

The iteration-92 receipt preflight is also binding. The live-escalation source
now declares both menu anchors as four typed v2 receipts: a strictly wider
passive prelude plus a precise caller-PC capture for each movie.
`tools/phase4_live_escalations.py` rejects a missing prelude, a
precision/method mismatch, a noncentral movie pin or a non-atomic receipt plan.
The method metrics layer admits those distinct same-iteration receipts under
their one predeclared escalation but still rejects semantic duplicates and
later escalation reuse. No live run was admitted and no behavior was promoted;
the retained method evidence is
[[EXP_2026-07-26_phase4_fmv_menu_owner_receipt_preflight]].

The typed menu plan has now executed. Four closed v2 receipts retain eight
atomic jobs, 60,620 replay frames, current API/source/running-binary/media
identities, complete command/result streams and four exact owned-PID cleanup
actions. `tools/phase4_fmv_menu_owner_coverage.py --write --check` re-reads
each hash-pinned receipt and preserved full batch result, reproduces the three
boot hits and six non-boot zeros per movie, and then rejects the behavioral
claim because three of four same-anchor endpoint controls fail. Its mutation
guards reject a hidden non-boot hit, rewritten endpoint equality, truncation
and media drift. The generated claim boundary retains
`observed_nonboot_zero_promoted=false` and `dimension_promoted=false`; exact
evidence is
[[EXP_2026-07-26_phase4_fmv_menu_owner_control_falsified]].

The replacement method is now predeclared as
`P4-ITER94-E15-MENU-PHASE-NEUTRAL-OWNER-COVERAGE`. Four validated plans retain
one strictly wider passive prelude and one precise direct native observer for
each Menu movie. The precise atomic jobs contain no instrumentation; one
`movie.traceToFrame` command covers all nine singleton PCs and retains its own
uninstrumented/passive cached-interpreter comparison. The receipt command
schema now hash-checks that direct result, recomputes coverage totals and joins
it to the typed observer plan after a completed `scenario.runBatch` control.
The current controller before-ledger had zero planned entries, so no emulator
was launched and no retrospective receipt was created. This is method
preflight only, promotes no behavior or dimension, and is retained in
[[EXP_2026-07-26_phase4_fmv_menu_phase_neutral_preflight]].

The replacement method has now executed in four fresh isolated profiles.
Four closed v2 receipts retain eight atomic jobs, 60,620 atomic replay frames,
15,155 direct native observer frames, exact current identities and four typed
owned-PID cleanup actions. Both direct observers hit all three boot PCs 327
times and bare PCs `0x800500D8`/`0x80050284` 326 times. Both also changed RAM
under instrumentation, so their native endpoint control is not phase neutral.
`tools/phase4_fmv_menu_phase_neutral_result.py --write --check` rederives those
counts and comparisons from the hash-pinned external receipts; mutation guards
reject changed equality, coverage, params, media and atomic controls. The
generated claim boundary promotes no owner call and no dimension, retires
full-span bare-PC replay, and moves the next method to static code-identity
reconstruction. Exact evidence is
[[EXP_2026-07-26_phase4_fmv_menu_phase_neutral_control_falsified]].

`tools/knowledge_closure_audit.py --write` regenerates the central external
fixture set and knowledge report. The bounded upstream dependency reconciler
then refreshes only retained artifact identities, and
`tools/phase4_reconcile_assertion_pins.py --write` updates only artifact pins
and SHA-valued joins. `tests/test_phase4_closure_debt.py` independently
falsifies the E15 durable-evidence claim by drifting its central fixture-set
pin. Runtime expectations and retained live payloads are unchanged.

Original facts: [[SYS_fmv_player_streaming]]. Runtime method and rejected
hypotheses: [[EXP_2026-07-16_phase4_fmv_skip]] and
[[EXP_2026-07-19_phase4_offline_fmv_batch]]. Static ownership and its bounded
negative claims: [[EXP_2026-07-19_phase4_fmv_static_owners]]. Callback and
consumer closure: [[EXP_2026-07-20_phase4_fmv_interface_frontier]]. Current
callback causality and rejected trigger hypotheses:
[[EXP_2026-07-24_phase4_fmv_callback_lifecycle]]. Static teardown ownership and
the pointer-table correction:
[[EXP_2026-07-24_phase4_fmv_teardown_ownership]]. No MOD-private state, hook or
intended behavior was introduced.
Natural level-A completion and its same-anchor control:
[[EXP_2026-07-24_phase4_fmv_natural_completion]].
Instruction-attributed selected-limit cause:
[[EXP_2026-07-24_phase4_fmv_natural_exit_cause]]. Natural game-over LOSE
lifecycle and rejected frame-zero observer:
[[EXP_2026-07-24_phase4_fmv_lose_lifecycle]].
Corrected full-level level-B reachability and bounded save-trigger negative:
[[EXP_2026-07-24_phase4_fmv_levelb_reachability]].
Exact first-call localization, selector-11 lifecycle and the rejected
over-broad neutral-loader hypothesis:
[[EXP_2026-07-25_phase4_fmv_levelb_first_call]].
Rejected LEVEL15 finale-route lead and the cold-boot address-reuse guard:
[[EXP_2026-07-25_phase4_fmv_finale_route_probe]].
Menu-owner live-receipt admissibility repair and retained index exclusion:
[[EXP_2026-07-26_phase4_fmv_menu_owner_receipt_preflight]].
Executed menu-owner observations and the falsified endpoint control:
[[EXP_2026-07-26_phase4_fmv_menu_owner_control_falsified]].
Executed native phase-neutral observer and its two-part falsifier:
[[EXP_2026-07-26_phase4_fmv_menu_phase_neutral_control_falsified]].
Residency-qualified shared-PC admission, the one-word selector discriminator
and current typed after-load method plus next-iteration control plan:
[[EXP_2026-07-26_phase4_fmv_resident_code_identity]].
Executed selector write, unstaged movie-frame falsifier and adapter correction:
[[EXP_2026-07-27_phase4_fmv_c16_selector_control_falsified]].
The same experiment note retains the static staged-prelude successor and its
no-live handoff.

The binding static continuation decomposition is now complete. The
hash-verified pristine artifact classifies all nine resident return windows
inside four centrally pinned ASM owners, including the boot repeat chain,
game-over/level transitions, Level-B progress scan and full Level-A reset
owner. It separately binds both completion writers, the stream-start clear,
sole completion reader, five player exit edges, common Pause/stop teardown and
four exceptional categories in FMV.BIN. Runtime outcomes are not inferred.

This closes `resident_post_fmv_continuation_ownership`, not the full lifecycle
dimension. The residual partition assigns native pause/error outcomes and
remaining live selectors to E15, movie-viewer return/unlock/persistence to
C17/E14, and audio presentation to E12. With the broad static question
exhausted, the scheduler's next lane is `live`: predeclare one same-anchor
decoded-record control at `0x800B6C40/0x800B6C84` and preserve the native
nonzero-record negative. Exact evidence is
[[EXP_2026-07-27_phase4_fmv_lifecycle_continuations]].

That decoded-record experiment is now predeclared as
`P4-ITER102-E15-DECODED-RECORD-ABSENCE-CONTROL`. A closed offline receipt
searched the exact 16,060,589-byte `fmv-lifecycle-v2` index and found none of
the predicate, latch-store, same-anchor, or native-control evidence needed for
the claim. Pristine static words instead bound the positive to the
`0x800B6C40` absent-record branch and the `0x800B6C84` byte store. Fresh
passive and precise plans validate with same-anchor staged frames 649/650, a
strictly wider passive prelude, one positive-only branch perturbation, and a
native unmodified negative.

The immutable iteration-before ledger did not contain the new plan, so no
emulator launched and no receipt was created retrospectively. E15 remains four
met/five remaining and Phase 4 remains 16/107. The next autonomous iteration
must execute the passive plan first, then the precise paired control, and bank
an outcome only if the latch writer, common teardown, negative exclusion,
bounds, pagination, endpoint control, and typed cleanup all survive. No Canon
or Mods layer changes are warranted before that result.

The next controller iteration executed both predeclared plans. Two fresh
isolated profiles retained two closed v2 receipts, four completed atomic jobs,
complete command/result pagination, verified pristine media and typed cleanup
for both owned PIDs. The passive endpoints were equal. The precise positive
changed only `0x800B6C40`, then recorded the exact `0x800B6C84` u8 `0 -> 1`
store at `0x800B9A54` and ordered decode, `StClearRing` and callback-teardown
events. The native branch recorded no latch write.

The declared control nevertheless failed its own falsifier. The native
function trace retained exactly the configured 64-event limit and began at
index 27, proving that 26 earlier function events were discarded. A complete
outer receipt/pagination stream does not repair that inner observer
saturation. The result therefore promotes no lifecycle or roadmap dimension,
and it cannot claim native teardown absence, failure frequency or
malformed-media behavior. Exact evidence is
[[EXP_2026-07-27_phase4_fmv_decoded_record_control_falsified]].

The binding static retention decomposition is complete. Closed offline receipt
`7156595a5e9822afa871075802ccfe0fd7b4f5ef60fc46aa89fe00f72f329b1b`
re-executes the tracked reader over the exact retained native batch result. Its
last source index proves 90 emitted function events over movie frames
650..850; the old 64-event ring retained only indexes 27..90. A finite
128-event successor therefore has 38 events of same-window headroom. The
receipt claims nothing about the types of the discarded prefix.

Pristine FMV.BIN reconstruction fixes the player helper call at `0x800B7280`,
the stop-latch read at `0x800B728C`, and the common-exit branch at
`0x800B7294`. The scheduler now binds the `live` lane to the sole planned
`P4-ITER104-E15-DECODED-RECORD-RETENTION-CONTROL`. Its plan guard rejects any
capacity drift, first index above one, last/total above 90, or a returned count
that reaches 128. This iteration launched no emulator and promotes no
lifecycle or roadmap dimension.

## Completed decoded-record retention successor

The next controller iteration executed that exact planned successor in two
fresh isolated profiles. Both profiles mounted hash-verified pristine retail
media, completed their two atomic jobs and stopped their owned numeric PIDs.
The passive branches have equal frame, cycle, RAM, register and capture
endpoints. The precise positive changes only the predeclared word at
`0x800B6C40`, records the exact `0x800B6C84` u8 latch writer and retains the
ordered helper, `StClearRing` and callback-teardown events.

The native branch records no latch access or selected teardown event and
retains exactly 90 function events as contiguous indexes 1 through 90, all 45
balanced calls to helper `0x800B6C24` from `0x800B7280`. The 128-event ring
has 38 events of headroom and reports no truncation, so the explicit retention
falsifier survives. This closes only the observer-retention fact. Lifecycle,
native failure policy and verifier admission remain open; E15 stays four
met/five remaining and Phase 4 stays 16/107 with 148 met dimensions. The
binding next lane is static partitioning of pause, repeat, unload/reload and
error owners. Exact evidence is
[[EXP_2026-07-27_phase4_fmv_decoded_record_retention]].

`tools/phase4_fmv_decoded_record_retention_result.py --write --check`
independently consumes the two closed v2 receipts and their batch, raw-result,
pagination, command-event and typed cleanup dependencies. It requires the
wider passive prelude, equal passive endpoints, the positive writer and
ordered teardown, and the native contiguous 1-through-90 sequence below the
128-event bound. Its focused test mutates each of those facts. The artifact
explicitly records zero promoted dimensions and keeps both investigator
receipts pending a fresh campaign verifier.

## Completed reload and retirement ownership successor

The method-ratchet iteration queried the exact retained
`fmv-lifecycle-v2` index before reading capsule bytes. Closed receipt
`15ea19ebaaac3aba5ff79d94b3e7f9df0780636c8aadaeb1021a184d25892356`
searched ten bounded unload/reload/repeat/pause/error owner terms against the
16,060,589-byte input and found zero matches. That answer localized the
missing domain to static code; it is not evidence that the behaviors are
absent.

The regenerated lifecycle artifact validates the complete pristine
`0x8003E7C0..0x8003E83C` wrapper and its matching-C source. Its six ordered
direct calls include unconditional `0x8003E7FC -> 0x80046330`, which copies
`fmv\fmv.bin` to `0x800B5788` once per wrapper invocation, then the
synchronous player and post-player display reinitialization. The wrapper has
no explicit Region-B unload or clear. Common teardown ends FMV use; the
resident return continuation or a later Region-B loader owns replacement.
Thus equal Region-B hashes across sequential streams do not prove reuse
without reload, and endpoint nonresidency does not identify an overwrite.

The exact static falsifier survives: all repeat/reload/retirement owners are
classified, and changing the pristine reload JAL makes the focused test fail.
No dimension is promoted. E15 remains four met/five remaining and Phase 4
remains 16/107 with 148 met dimensions. The binding next lane stays `static`
until one exact native pause/error trigger and same-anchor control are
predeclared; no DuckStation process launched in this successor. Exact evidence
is [[EXP_2026-07-27_phase4_fmv_lifecycle_continuations]].

## Native CD-event exit route and predeclared control

The current method iteration queried the exact retained `fmv-lifecycle-v2`
index first. Closed receipt
`6f4066bec9b6c68a61957d469caef6a585eb199299e0eabad6e0a755dd60c73e`
re-executes the pinned reader over all 16,060,589 bytes and confirms that its
frame-boundary domains contain none of the requested pause/error branch or
counterfactual terms.

Pristine static reconstruction closes four exact edges. `cd_subsystem_init`
registers callback `0x80045D5C` for event class `0xF0000003`/spec `0x8000`;
the matching callback stores one at `0x80082484`; FMV.BIN reads that address
at `0x800B7420` and compares it with the value-one sentinel at `0x800B7428`;
the taken target is `0x800B7464`, the `CdControl(0x0b)` and common-teardown
block. The generated artifact also exhausts all seven resident
`gp+0x06ec` xrefs and mutation-tests every load-bearing registration,
callback and player word.

This closes only `native_cd_event_to_pause_teardown_routing`. Native event
delivery/frequency, the Pause result and visible failure outcomes remain
lifecycle debt. `P4-ITER107-E15-CD-EVENT-EXIT-CONTROL` is the sole planned
successor: a strictly wider passive E15 replay covers frames 249..340, while
the precise same-anchor pair stages at frame 250, changes only
`0x800B7420: 0x8C422484 -> 0x24020001` in the positive, and stops at frame
330 before recorded Start input. Both plans validate against the current
debugger/media/fixture identities.

The immutable iteration-before ledger cannot admit an escalation authored
during this iteration, so no emulator launched and no live receipt was
created. E15 remains four met/five remaining, Phase 4 remains 16/107 and 148
met dimensions, and the next lane is `live` only when a future before-ledger
contains that exact ID. Exact evidence remains
[[EXP_2026-07-27_phase4_fmv_lifecycle_continuations]].

## Completed CD-event player-consumer control

The next controller iteration executed the exact predeclared successor in two
fresh isolated profiles. Both mounted hash-verified pristine retail media,
completed their two finite atomic jobs and stopped their owned numeric PIDs.
The passive branches are equal in staged status, run status and terminal
capture.

The precise positive verifies, changes and reads back exactly one word:
`0x800B7420: 0x8C422484 -> 0x24020001`. It then records balanced entry/exit
pairs for `CdControl(0x0B)` from `0x800B746C`, `StClearRing` from
`0x800B749C` and callback teardown from `0x800B74A4` as target indexes 1
through 6. The native same-anchor negative records zero target events. Both
branches stop at movie frame 4565 and cycle 2,584,138,962; neither trace
truncates or reaches its 128-event limit. The explicit falsifier survives.

This closes only the bounded player-consumer interface fact. Native CD-event
delivery/frequency, Pause result, file-open/decode-timeout/CD-retry behavior,
visible failure policy, lifecycle and verifier admission remain open. No
roadmap dimension is promoted: E15 remains four met/five remaining and Phase 4
remains 16/107 with 148 met dimensions.

`tools/phase4_fmv_cd_event_exit_result.py --write --check` consumes both
closed v2 receipts and their exact batch, raw-result, pagination,
command-event and cleanup dependencies. Its focused tests mutate the
one-word write, target order, native exclusion, passive endpoint, result-body
hash, prelude join and cleanup. The binding next lane is `static`: partition
upstream native event delivery and the distinct file-open, decode-timeout and
CD-retry branches, then select one pristine-triggerable failure edge and
paired visible outcome. Do not replay the closed decoded-record or CD-event
consumer windows. Exact evidence is
[[EXP_2026-07-27_phase4_fmv_cd_event_exit_control]].

## Upstream failure partition and next control

The next static iteration queried the retained `fmv-lifecycle-v2` index before
scanning code. Closed receipt
`5d1fa84670af306fd67daa52029de9df4554a710ec3c6f8c91593a40e2cc552a`
searched eight exact upstream event/failure terms over the complete
16,060,589-byte index and returned zero paths without truncation. The missing
fact is instruction/counterfactual resolution, not another frame-boundary
scan.

Pristine static reconstruction exhausts four resident direct callers of
`DeliverEvent`; none matches the FMV registration's
`0xF0000003`/spec-`0x8000` pair. The exact event producer remains bounded
behind BIOS/interrupt service rather than falsely attributed to resident
libcd. File open now has two exact helper failure returns plus a
diagnostic-to-shared-initialization player route. Decode timeout owns an exact
`0x00800000` budget and fallback state, and GetlocP/Read2 have distinct
retry-on-zero branches. Mutation guards cover every direct event caller and
one load-bearing word in each failure family.

`P4-ITER109-E15-FILE-OPEN-FAILURE-ROUTING` is the sole planned successor. Its
strictly wider passive window is movie frames 160..260. The precise pair
stages through frame 170, changes only
`0x800B6DE8: 0x12020018 -> 0x10000018` in the positive and stops at frame
240. Both words retain the same failure target. The positive must record the
failure diagnostic from `0x800B6E54`; the native negative must not; both must
reach shared initialization from `0x800B6E68` without saturation or unrelated
endpoint divergence.

This control proves only a bounded route consequence on pristine mounted
media. It cannot claim a naturally failed handle, missing/malformed media,
visible policy or complete lifecycle. Both atomic plans validate, but the
immutable before-ledger did not contain the new ID, so no emulator launched.
E15 remains four met/five remaining and Phase 4 remains 16/107 with 148 met
dimensions. The binding next lane is `live` only for that exact future plan.
Exact evidence is [[EXP_2026-07-28_phase4_fmv_failure_frontier]].

## Falsified file-open diagnostic-route control

The next controller iteration admitted the exact planned
`P4-ITER109-E15-FILE-OPEN-FAILURE-ROUTING` ID. A closed offline query first
confirmed that the retained 16,060,589-byte derived index has no every-cycle
diagnostic/branch domain. The passive and precise plans then completed in two
fresh isolated profiles with pristine mounted media, four finite atomic jobs,
complete command/pagination evidence and two confirmed owned-PID stops.

The passive branches are endpoint-identical. The precise positive changes
only `0x800B6DE8: 0x12020018 -> 0x10000018`; both branches retain the file
helper and one shared-initialization sequence. Both function traces contain
exactly 12 contiguous events with 116 events of headroom. Contrary to the
predeclared claim, neither trace records the diagnostic from
`0x800B6E54`. The explicit falsifier fires.

The positive still changes the retained selected-limit endpoint from
`18008000` to `1800f000` little-endian. That is a bounded counterfactual
observation whose owner and meaning remain unresolved; it is not evidence of
a native failed handle, missing/malformed media or visible failure policy.
The machine artifact promotes no dimension and keeps both live receipts
pending the fresh campaign verifier.

E15 remains four met/five remaining and Phase 4 remains 16/107 with 148 met,
46 partial and 769 gap dimensions. The binding next lane is `static`: recover
the exact executed path and argument/state ownership responsible for the
divergent endpoint. Do not replay the falsified diagnostic experiment.
Exact evidence is [[EXP_2026-07-28_phase4_fmv_failure_frontier]].

## Corrected endpoint ownership and next discriminator

The static follow-up corrects the stale four-byte endpoint label.
`0x800CAC08..0x800CAC0B` is signed presentation RECT width/height, not the
selected frame limit at `0x80131EEE`. The positive bytes decode as width 24 /
height 240 and the native bytes as width 24 / height 128. Pristine
initialization stores height 240 at `0x800B6F18` and width
`display_mode * 8` at `0x800B6F40`; the exhaustive direct xref census finds no
second direct height writer.

Closed offline receipt
`fb014629ad46e76e85f7b8f6c46fc05ef9702b1856da0289f378425f0949f40a`
confirms that the exact retained derived index does not name the field,
initializer or selected-limit writer. The static work-packet falsifier fires
because the native height-128 writer remains unattributed. No dimension is
promoted: E15 remains four met/five remaining and Phase 4 remains 16/107 with
148 met dimensions.

The binding lane is now `live` only for planned escalation
`P4-ITER110-E15-PRESENT-RECT-HEIGHT-WRITER`. Its passive pair covers the
strictly wider movie-frame 150..270 window. Its precise pair watches only
two-byte writes to `0x800CAC0A` over 160..260, repeats the unmodified native
anchor and performs no code/data perturbation. Matching unsaturated CPU
writer events are required; zero events falsifies CPU ownership and selects a
later DMA/host provenance experiment. Both plans validate, but the immutable
iteration-before ledger did not contain this new ID, so no emulator launched
and no live receipt was authored. Exact evidence remains
[[EXP_2026-07-28_phase4_fmv_failure_frontier]].

## Saturated presentation-RECT writer control

The next controller iteration admitted and executed the exact planned
`P4-ITER110-E15-PRESENT-RECT-HEIGHT-WRITER` successor. The wider passive pair
and the unperturbed precise pair completed in separate fresh isolated
profiles with pristine mounted media, four finite atomic jobs, complete
identity/command/pagination dependencies and two confirmed owned-PID stops.

Both passive endpoints are equal. Both precise endpoints are also equal and
retain presentation RECT height 128, selected limit 386, the historical
`fmv_running_latch` capture value zero and scene one. That capture key now
maps to shared frame-sync state, not FMV lifetime. After normalizing only the
generated watch ID, the precise
ordered event payloads match. Each records the 240 initializer at
`0x800B6F18`, the first exact `240 -> 128` store at `0x800B6BF0`, and repeated
stores from resident `0x80064178`.

Both access logs return exactly 32 events against the configured 32-event
capacity. This satisfies the work packet's explicit saturation falsifier.
The `0x800B6BF0` event is a repeatable bounded CPU-writer lead, but the
complete ordered writer sequence remains open; zero receipts are admitted for
promotion until a fresh campaign verifier consumes them.

No roadmap dimension is promoted. E15 remains four met/five remaining and
Phase 4 remains 16/107 with 148 met, 46 partial and 769 gap dimensions. The
binding next lane is `static`: reconstruct the cached-height-to-RECT pointer
alias and caller at `0x800B6BF0` plus the resident `0x80064178` helper before
authoring a finite successor observer. Do not repeat the saturated semantic
experiment under a new label. Exact evidence is
[[EXP_2026-07-28_phase4_fmv_failure_frontier]].

## Static presentation-height owner and narrowed successor

The next measured-method iteration stayed on `fmv_playback` / `E15_fmv`
and obeyed the binding static lane. Recursive inventory found 110 Phase-4
operator files, 147 files in the broader operator movie tree and 135
centrally provisioned files. No operator-owned recording was imported.

Closed offline receipt
`4d3e3d60016374f2386c3f30173fbb9f94dc4928fa2d9375ded80bfdd2549d5e`
re-executes the tracked JSON reader over retained derived-pristine index
`e232f9cd3da57de3f794495b0789904c6cb36bd8152e67f3f7d12576d5c828ab`.
Its exact writer/address/symbol search returns zero matches without
truncation. The frame-boundary index therefore does not answer this
instruction-ownership question.

Pristine static reconstruction closes it. Both player calls to
`0x800B6C24` pass base `0x800CABE0`; that helper preserves the argument into
`0x800B6A7C`. The commit function loads cached height `0x800B9A5C` and
stores it to presentation RECT height `0x800CAC0A` at `0x800B6BF0`.
Matching-C LoadImage and the pristine libgpu table separately resolve
resident `0x80064178` to the downstream PsyQ `_dws` RECT clamp. Every retained
writer PC is now classified.

Machine artifact
`analysis/phase4_fmv_present_rect_height_static_ownership.json` retains the
exact caller census, opcode/function hashes, table entries, source status,
offline receipt join and prior runtime-PC join. Mutation guards reject
height-store, second-caller, libgpu-table and retained-count drift. No live
process launched.

Saturation still prevents a complete ordered runtime sequence, so E15 remains
four met/five remaining and Phase 4 remains 16/107 with 148 met dimensions.
The binding lane changes to `live` only for a different experiment family if
cardinality remains load-bearing: a same-anchor `functionTrace` restricted to
`0x800B6A7C..0x800B6C24` over movie frames 160..260 with a 32-event
maximum. The prior three calls predict six balanced events; saturation or an
unbalanced call is the falsifier. Repeating the broad `0x800CAC0A` write
watch is prohibited. Exact evidence is
[[EXP_2026-07-28_phase4_fmv_present_rect_height_static_ownership]].

## Finite presentation-height function-cardinality plan

The next controller-trial iteration retained only `fmv_playback` / `E15_fmv`
and recursively reused the existing 110-file Phase-4 operator inventory,
147-file broader operator tree and 135-file centrally provisioned movie tree.
No operator-owned movie bytes were imported. Ordered regeneration still
selects E15 alone: 107 rows, 91 open, 42 offline-partial, nine reusable
indexes over 34 rows, 16 complete rows and 148 met dimensions.

Closed offline receipt
`3859838856b1b00c9bca8a8d9a171b70986a49e60cf62db0e0261a59bdcfe61e`
independently re-executes the tracked reader over the 16,060,589-byte
`fmv-lifecycle-v2` index. The exact bounded search returns no function/caller,
`functionTrace`, cached-height, presentation-RECT or movie-window paths and
does not truncate. This confines the missing fact to every-call cardinality;
it does not weaken the banked static owner result.

`P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY` is now the sole planned
successor. Its strictly wider passive repeat covers movie frames 150..270.
Its precise same-anchor repeat covers 160..260 and arms only
`functionTrace.start` for `0x800B6A7C` with a 32-event limit. Both unmodified
jobs must retain three calls from `0x800B6C24`, six balanced events beginning
at index one, identical ordered sequences and equal endpoints. Saturation,
another caller, imbalance, sequence drift or endpoint divergence falsifies
the claim.

The focused plan guard binds the typed v2 observer exactly to every atomic
job's instrumentation; a 32-to-31 event-limit mutation is rejected. Both
future plans validate, but this controller iteration's immutable before-ledger
contains no planned escalation. No emulator launched and no live receipt was
authored. E15 remains four met/five remaining and Phase 4 remains 16/107 with
148 met, 46 partial and 769 gap dimensions. Execute only this exact pair in a
later iteration whose before-ledger admits the ID; do not repeat the broad
write watch. Exact evidence is
[[EXP_2026-07-28_phase4_fmv_present_rect_height_static_ownership]].

## Falsified presentation-height function cardinality

The next controller iteration admitted the exact planned
`P4-ITER114-E15-PRESENT-RECT-FUNCTION-CARDINALITY` successor. Work-packet
SHA-256
`904f19d51008b2ed2543eeee67534ec4998b5c28f346c117c8d0302d1118e101`
retained one exact three-call claim and its saturation, caller, imbalance,
sequence and endpoint falsifiers. No second campaign or row was opened.

Closed offline receipt
`dcdf06fd4a24780d105e599151d2ee0d74544912b9805f90447181aa735f28af`
re-executed the tracked reader over the same 16,060,589-byte
derived-pristine index. Its six-term bounded output is byte-identical to the
prior retained search and again returns zero paths without truncation. The
missing information therefore remained exact function events rather than
another capsule query.

The strictly wider passive pair and the precise native pair completed in two
fresh isolated profiles. Both mounted hash-verified pristine SCUS-94288
media, completed four finite atomic jobs and stopped their owned numeric
PIDs. Receipt SHA-256 values are
`5b820de153b9874f3f3d08eb996676aac72965b4c37301ad10437491ffaa1ba8`
and
`29b4e6f4031d997a3081305ce52a1f8899e040bd0c891a083f222ca4832951c6`.
Both same-anchor branches retain equal ordered traces and endpoints.

Each precise branch records 22 contiguous events against a 32-event limit:
eleven entry/exit pairs, not the predicted three. The retained caller field
is the exact JAL instruction `0x800B6C34`; static ownership still places that
instruction inside helper `0x800B6C24`. One first-call exit is
observer-synthesized. The three argument classes occur 1, 1 and 9 times.
Thus the cardinality, caller-field and balanced-return falsifiers fire even
though the rings have ten events of headroom and the two sequences match.

Generated artifact
`analysis/phase4_fmv_present_rect_height_function_trace_result.json`
hash-lists both investigator receipts and their complete batch, raw,
pagination, command-event and typed-cleanup dependencies. Focused guards
reject caller, pairing, index, saturation and argument drift. The receipts
remain promotion-inadmissible until a fresh campaign verifier consumes them,
and no dimension is promoted: E15 remains four met/five remaining; Phase 4
remains 16/107 with 148 met, 46 partial and 769 gap dimensions.

The binding next lane is `static`: reconstruct the helper loop and ownership
of the retained 1/1/9 argument classes, including the first synthetic unwind.
Correct observer vocabulary distinguishes owning helper `0x800B6C24` from
call-instruction field `0x800B6C34`. Do not replay this cardinality experiment
or the broad presentation-RECT watch. Exact evidence remains
[[EXP_2026-07-28_phase4_fmv_present_rect_height_static_ownership]].

## Corrected decode-helper and outer-loop ownership

The first measured method-ratchet iteration retained only `fmv_playback` /
`E15_fmv`. Recursive inventory found 147 files in the broader operator movie
tree and 135 centrally provisioned files; no operator-owned recording was
imported. Ordered regeneration still selected E15 alone with 107 rows, 91
open, 42 offline-partial, nine reusable indexes covering 34 rows, 16 complete
rows and 148 met dimensions.

Closed offline receipt
`3412a5254070301df57bbf6d6972043c48ff10cb79102a33bae2f34dc0a14558`
re-executes the tracked reader over the 16,060,589-byte
derived-pristine `fmv-lifecycle-v2` index. Its exact helper,
call-instruction, argument-class and synthetic-unwind search returns zero
paths without truncation. The index therefore does not answer the selected
instruction/ABI question.

Pristine static reconstruction falsifies the packet's proposed helper loop.
`0x800B6C24..0x800B6CA4` has no back edge and calls `0x800B6A7C` exactly once
at `0x800B6C34`. The player calls that wrapper once at `0x800B70A0` before
entering its outer loop, preserves boundary base `0x800CABE0`, and calls it
again at `0x800B7280` once per loop iteration. The back edge at `0x800B745C`
targets `0x800B70E0` and cannot revisit the initialization call. The retained
eleven-call trace therefore partitions into one initialization call and ten
outer-loop calls; nine is only the final incidental argument-class count in
that bounded window.

Only `a0` is semantic on entry to `0x800B6A7C`. `a1` is replaced in the
`StGetNext` delay slot, while `a2` and `a3` are defined before their first
use; the hash-pinned `StGetNext` body likewise overwrites inherited `a2/a3`.
The 1/1/9 values are caller-saved residue, not three decoded-record types, so
`config/record_types.yaml` remains deliberately unchanged. Both commit and
wrapper functions have conventional `jr ra` epilogues, bounding the first
synthetic exit as observer provenance rather than a guest control-flow fact.

Generated artifact
`analysis/phase4_fmv_present_rect_height_helper_loop.json` retains the closed
offline-query join, complete direct/indirect caller frontier, exact function
hashes and opcodes, computed use-before-definition boundary, retained trace
partition, schema decision and corrected falsifier. Focused mutation guards
reject an early register read, outer-loop edge drift, inherited `StGetNext`
argument consumption and trace-class drift. No emulator launched and no live
receipt was authored.

This closes the selected helper/argument ownership sub-boundary without
promoting lifecycle: E15 remains four met/five remaining and Phase 4 remains
16/107 with 148 met dimensions. The binding lane remains `static`: reconstruct
the remaining native Pause/stop trigger producers and caller-owned
post-helper exit decisions before considering another live control. Do not
repeat the falsified function trace, invent a fixed nine-iteration bound or
promote caller-saved residue into record state.

## Complete post-helper exit and CD-command ownership

The first measured iteration of the current method-ratchet run retained only
`fmv_playback` / `E15_fmv`. Recursive inventory reused 110 files in the
Phase-4 operator tree, 147 files in the broader operator tree, and 135 files
in the centrally provisioned movie tree. No operator-owned movie bytes were
imported. Ordered regeneration validated 55/55 capsules
(3,391,058,326 preserved bytes), 107 queue rows with 42 offline-partial,
nine reusable derived indexes over 34 rows, and the single selected E15
campaign.

Closed offline receipt
`244e5b5ac038d6b9b805a13581007d36cfe4cd268e3f8881c8ed80d7e2b4aa0d`
re-executes the tracked reader over the exact 16,060,589-byte
`fmv-lifecycle-v2` derived-pristine index. Its bounded ten-term search covers
all five post-helper PCs, mask `0x4008`, `CdControl`, `CdlStop`, `CdlPause`
and ownership vocabulary. Every term returns zero paths without truncation,
so pristine static code owns the missing instruction-resolution question.

The generated ownership artifact classifies five predicates: u8 decode-stop
latch one, resident CD-event field one, controller-derived countdown twelve,
completion request one, and decoded-index/selected-limit comparison. Resident
`0x8003A2DC` polls and republishes controller halfword `0x80082412`; the
player calls it at `0x800B70E0`, applies mask `0x4008`, seeds its countdown
at one, increments it per active outer iteration, and exits at twelve.

An exhaustive scan of FMV executable code finds exactly six encoded entries
into `0x800B6E38`, `0x800B7464`, or `0x800B7468`, plus the classified
decoded-limit fallthrough, with no unclassified edge. Completion alone issues
`CdlStop(8)` before the shared `CdlPause(11)` and common teardown. All other
exit routes join Pause directly. `CdlPause` is libcd stream teardown, not the
frontend pause shell.

Focused guards recompute both pristine identities, the closed query, exact
producer/load/compare opcodes, edge census, controller chain and command
ordering. They reject a mask mutation, an added teardown edge, and a broken
resident controller publish. The explicit falsifier survives. No DuckStation
process launched and no live receipt was authored.

This closes only the post-helper exit/CD-command ownership sub-boundary and
does not promote lifecycle. E15 remains four met/five remaining. The binding
lane stays `static`: identify the first caller-owned Region-B overwrite after
one selected level/viewer return and classify its E16/E14 owner before
considering another live control.

## Natural LOSE caller-owned Region-B replacement

This measured iteration retained only `fmv_playback` / `E15_fmv`. Recursive
inventory reused 110 Phase-4 operator files, 147 files in the broader operator
tree, and 135 centrally provisioned files. Ordered regeneration validated
55/55 capsules, all 107 queue rows, nine derived indexes over 34 rows, and E15
as the sole selected campaign.

Closed offline receipt
`7ed2612007cf908309455b1dee5434ec993ab0cea1d2b9f1693ed67e307be03e`
re-executes byte-identically over the 16,060,589-byte derived-pristine
`fmv-lifecycle-v2` index. Its ten exact Region-B, loader and ownership terms
return zero paths without truncation, so pristine static bytes own the missing
instruction-resolution question.

The retained natural LOSE anchor enters `fmv_bin_load` with selector 46/mode 0
from `0x800500D8`, completes reproducibly, and returns to `0x800500E0`.
Pristine bytes then call `scene_setup_and_load(5, 64)`. Its display initializer
contains 19 direct GPU/display calls and no Region-B materialization or
resource/CD loader. The next call is
`resource_id_dat_load_dispatcher(0)`, whose selector-zero branch uniquely
materializes `bits\memory.bin` and destination `0x800B5788` before
`universal_file_loader` preserves that destination through the file helper's
`CdRead` request.

This classifies the selected ownership split: E16 owns replacement bytes, C16
owns the game-over transition choice, and E14 does not intersect this path.
Focused guards reject selector, destination and CdRead-destination drift. No
emulator launched and no live receipt was authored.

Only `game_over_lose_region_b_replacement_ownership` closes. Lifecycle remains
partial, E15 remains four met/five remaining, and Phase 4 remains 16/107 with
148 met dimensions. The binding lane remains `static`: extend the same
replacement census to one completed-level or movie-viewer return and classify
its transition/persistence policy before considering another live control.

## Natural completed-Level-B caller-owned Region-B replacement

The second measured iteration retained only `fmv_playback` / `E15_fmv`.
Recursive inventory again reused 110 Phase-4 operator files, 147 files in the
broader operator tree, and 135 centrally provisioned files. No operator-owned
recording was imported.

Closed offline receipt
`8fe4e94a84381d1106ae0df087db27347865dc0ed4db3320029b8268c22c6326`
re-executes the tracked reader over the exact 16,060,589-byte
derived-pristine index. Its ten-term completed-Level-B/Region-B/owner search
returns zero paths without truncation and retains output SHA-256
`caa68175e00a34700d26af492ff5edd1c6a1a7eb298698c9431220029b89fbb5`.

The retained natural first-call artifact supplies frame 14,382, progress
state one, selector 11/mode `-1`, completion writer `0x800B6B24`, and balanced
teardown. State one joins the guarded scene-flow call at `0x8005013C`.
Pristine scene flow calls `scene_setup_and_load(3, 0)` when its pending
request is negative and `scene_setup_and_load(6, 128)` otherwise. Both
non-skip transitions reach E16 selector zero, which uniquely requests
`bits\memory.bin` into `0x800B5788` through the universal loader and `CdRead`.

The completed owner has no Region-B materialization, save-serializer call, or
C17 movie-viewer unlock write. Its all-complete adjacent scene flag is not
persistence evidence. This closes
`completed_level_b_region_b_replacement_ownership` alongside the banked LOSE
sub-boundary, but lifecycle remains partial: E15 stays four met/five remaining
and Phase 4 stays 16/107 with 148 met dimensions.

Two consecutive no-reduction iterations force a method/lane change. The
binding lane is now `live` only for planned escalation
`P4-R6-ITER2-E15-LEVELB-REGIONB-DMA-PROVENANCE`: a wider passive pair and a
same-anchor non-halting `transferLog.start` pair over the centrally declared
from-boot LEVEL01 movie. It must identify the first post-teardown channel-3
CDROM DMA at `0x800B5788` without truncation or endpoint drift. The immutable
before-ledger did not authorize the new ID, so no emulator launched and no
live receipt was authored. Exact evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B DMA receipt preflight

Method-ratchet iteration 1 retained only `fmv_playback` / `E15_fmv` and the
first unmet lifecycle dimension. Recursive inventory reused 110 Phase-4
operator files, 147 files in the broader operator tree, and 135 centrally
provisioned files. Ordered regeneration still reports 55/55 capsules, all
107 rows, nine derived indexes, and no offline-ready row.

Closed offline receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`
replays byte-identically over the retained 16,060,589-byte
derived-pristine index. All ten transfer/CD/Region-B terms return zero paths
without truncation, retaining 2,094-byte output SHA-256
`dba41729dc61fa7bfe6d4c5a52d06d6c022fe2a51fdedce0067b924b7022a399`.

The required live preflight fails closed before DuckStation launch.
`bootAndRun` has no staged prelude, so its observers begin at cold boot rather
than authored frame 15720/15740. The current atomic capture also returns at
most 10,000 transfer records without transfer `total`/`truncated` metadata,
and the paired runner cannot paginate each job independently. The new
passive and precise plans retain honest `0..16120` / `0..16080` capture
windows and narrower analysis windows in their assertions. The passive plan
validates; the precise plan is rejected until complete per-job transfer
pagination is mechanically available.

No live receipt was authored and no dimension was promoted. The binding lane
remains the same planned DMA fact, but its next autonomous step is now exact:
manifest-pin a bounded atomic transfer result with total/truncated metadata
and complete ordered pages for each paired job, then require the tracked
precise plan to validate before executing either pair. Evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B atomic transfer pagination

The next measured method iteration closes only the blocking live-receipt
interface. The external debugger's atomic capture now retains a coherent
per-job transfer snapshot of the complete 100,000-event ring as at most ten
ordered 10,000-event pages. Every result includes exact
`total`, `returned`, `enabled`, `pagination_complete`, and `truncated`
metadata before a later paired job can clear the log.

Candidate-HEAD manifest identity covers the core service, dispatcher, closed
method schema, docs, release binary SHA-256
`8dce4a65c946f081f6db860f8ff5653d507c15d4dc15dca562fc456b3711b210`,
and embedded dirty-state identity
`38275389f4dbbb9d8d160e2d1de4c6e4f742d00c`. The tracked adapter requires
that identity join, full-ring capacity in both jobs, exact typed limits,
complete nontruncated pages, and contiguous event indexes. Mutation guards
reject each missing or weakened part.

The passive and precise LEVEL01 plans both validate. No emulator launched,
no live receipt was authored, and E15 remains four met/five remaining with
Phase 4 at 16/107 rows and 148 met dimensions. The binding lane stays
`live`: execute the passive receipt first, then its linked precise receipt,
and admit neither to promotion until a fresh campaign verifier consumes
both. Detailed evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B DMA passive closure and method rejection

The next measured iteration retains only `fmv_playback` / `E15_fmv` and the
first unmet lifecycle dimension. Recursive movie inventory remains 110
Phase-4 operator files, 147 files in the broader operator tree, and 135
centrally provisioned files. Ordered regeneration remains 55/55 capsules,
107 rows with 91 open and 42 offline-partial, nine derived indexes over 34
rows, and 148 met dimensions.

Closed offline receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`
again returns zero paths for all ten exact DMA/CD/Region-B terms without
truncation. Closed passive live receipt
`abe75bc65b419092c4858efbc3afc18d54c045ec92271f7c008a1024f96fcbe2`
retains two completed pristine cold-boot jobs through emulator frame 16120.
Both endpoints are identical at cycle 9126623583 and PC `0x8004FEA4`, all
32,238 replay/observer frames are accounted for, identity calls precede the
atomic batch, pagination is complete, and the owned numeric PID is stopped.

The precise full-cold-boot transfer branch produced no closed receipt:
complete transfer pagination failed closed before evidence banking. It is
absent, uncounted, and supplies no DMA event. Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_attempt.json` SHA-256
`a69ad6ad0681317384141c4d66f4ab69997ca038887009b585fb8ff6bb1fe15d`
therefore records one passive receipt, zero precise receipts, zero admitted
DMA events, and no promotion.

The full-cold-boot transfer observer is retired. Before another emulator
launch, the next autonomous iteration must implement and validate a typed
cold-boot emulator-frame staged prelude, authorize it under a new escalation
ID and immutable before-ledger, advance to a bounded point immediately before
the retained teardown, and only then arm `transferLog` for a finite late
window. The passive endpoint is not DMA causality evidence. Detailed evidence
remains [[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B typed late-arm preflight

Method-ratchet iteration 2 retained only `fmv_playback` / `E15_fmv` and the
first unmet lifecycle dimension. Recursive inventory again found 110
Phase-4 operator files, 147 files in the broader operator tree, and 135
centrally provisioned files. Ordered regeneration validates 55/55 capsules,
107 rows with 91 open and 42 offline-partial, nine reusable indexes over 34
rows, and E15 as the sole selected campaign with four dimensions met and five
remaining.

The retained offline receipt
`ecfd091f44f49943e5e8431ba92e823d55c155f6317a7e6242fcc841934d9126`
remains the complete negative answer for the missing transfer domain; no
duplicate offline query was authored. Static ownership still ends at the
selector-zero `bits\memory.bin` request to `0x800B5788`, so only the native
DMA stream can identify the executing channel, direction, cycle, size, and
sector predecessor.

The current debugger now admits a closed `emulator_advance` staged prelude
only for `scenario.bootAndRun`. It reports actual emulator start, target,
advanced-frame, status, and movie counters before instrumentation is armed.
The release binary hashes to
`d68b2c6d25f6795a921f5d1fa64ae33c66af3e3d47a786ee45853170766588cd`;
the dispatcher hashes to
`6ff2640dad39f85eacba9e8bbbfdb65d4e3707cb6d8f72cc74bf404579ae8a3e`.
The new `tools/phase4_duckstation_late_batch.py` adapter accepts the centrally
provisioned LEVEL01 movie and rejects a missing prelude, the wrong prelude
kind, target/capture drift, noncontiguous raw counters, or a post-prelude run
that does not exactly cover its typed capture window. The historical
`tools/phase4_duckstation_batch.py` remains byte-identical at SHA-256
`e94ec290a489484587b50fe72a472dbfa8578a7f17dcaf32f57af2efcf8bb375`
so the closed iteration-1 receipt retains its exact adapter-source join.

The passive pair stages to emulator frame 15720 and observes exactly
15720..16120. The precise pair stages to 15740, then arms `transferLog` for
exactly 15740..16080 with complete ten-page capacity. Generated escalation
`P4-R6-ITER3-E15-LEVELB-REGIONB-LATE-DMA-PROVENANCE` is the ledger's sole
planned entry, with the precise receipt linked to the strictly wider passive
receipt.

Artifact `analysis/phase4_fmv_levelb_region_b_dma_late_arm.json` SHA-256
`508b7af5b81b8cf37b49dd0944f3e033bc51526eabaeeb2ab12039e05e9b46b6`
banks only method readiness: zero live receipts executed, zero DMA events
admitted, and zero dimensions promoted. This iteration's immutable
before-ledger predates the new escalation, so no emulator launched. The next
iteration may execute the passive receipt first and the precise receipt only
after passive closure. Detailed evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B late passive closure and precise rejection

Method-ratchet iteration 1 executed only the authorized E15 late-DMA
escalation. The staged passive run used a fresh isolated profile and retained
closed v2 receipt
`d1c901b7c9aebcf9141088332cf4d625f5101d10c10410c50d65d7f14ccce833`.
Both pristine cold-boot jobs advance from emulator frame one to 15720 before
observation, then retain exactly 400 observer frames. They finish at frame
16120, cycle 9126623583, PC `0x8004FEA4`, and SP `0x801FFFD0` with equal
staged counters, registers, RAM, movie state, and Region-B endpoint bytes.
The receipt retains current source/binary/API/media identities, ordered
atomic command events, and typed numeric-PID cleanup.

The precise `15740..16080` transfer run failed closed before receipt
emission because its transfer pagination was incomplete or truncated. No
precise receipt or transfer record is admitted, so the first channel-3
from-device write to `0x800B5788` remains unobserved. The passive endpoint is
not promoted into DMA causality.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_late_result.json` SHA-256
`b0ec7e9fa015d94180fc26f74c376d7e343e53ee72a13d29ec5a00ef901d6433`
banks one passive receipt, zero precise receipts, zero admitted DMA events,
and no roadmap-dimension promotion. The 340-frame late transfer observer is
retired. The next lane is `static`: use the retained teardown frame and
transition edge to derive a causally complete subwindow that fits the typed
pagination bound before predeclaring another paired live experiment.
Detailed runtime evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B exact-PC submission subwindow

Method-ratchet iteration 2 retained only E15 lifecycle and followed the
binding static lane. The prior derived-index query was reused as a complete
negative frame-boundary answer; no new offline receipt was opened.

Pristine static reconstruction now identifies the selected file helper's
latest safe boundary. `BITS/MEMORY.BIN` has logical size 36,448 bytes. The
helper saves the 416-byte destination tail beyond that logical end to
scratch, then sets `a0=18` sectors and `a1=0x800B5788` immediately before
`CdRead` call `0x80046078`. It restores the tail after synchronous success.
Both success and failure join common epilogue `0x800460C4`, so
pre-instruction stops at those two PCs contain exactly one selected
submission. The only other direct resident `CdRead` call is a classified
fixed-sector wrapper at `0x8006FFEC`.

Artifact `analysis/phase4_fmv_levelb_region_b_dma_subwindow.json` SHA-256
`c7d3696ea7fbd0276b57f64f0790b57351932bb10a84e68cf6e80985d5120f07`
and its focused guard retain the exact opcodes, resource hash/size, argument
liveness, predecessor partition, global call census, and falsifier.

No DMA event is claimed and lifecycle remains partial. The next lane stays
`static`: implement a tracked exact-PC stop/arm adapter, because the current
frame-boundary `trace.armWhen` recipe cannot catch transient PC
`0x80046078`. A fresh live escalation is forbidden until that adapter is
mutation-tested and a strictly wider passive prelude is declared. Detailed
evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B exact-PC adapter readiness

Method-ratchet trial iteration 1 retained only `fmv_playback` / `E15_fmv`
and its first unmet lifecycle dimension. Ordered regeneration still validates
55/55 capsules and 3,391,058,326 preserved external bytes, 107 queue rows
with 91 open and 42 offline-partial, nine derived indexes over 34 rows, and
148 met dimensions. The relevant retained derived-index query remains a
complete negative frame-boundary answer, so this static adapter task opened
neither a duplicate offline query nor a live operation.

The new tracked `tools/phase4_duckstation_exact_pc_batch.py` composes direct
typed methods from an already paused atomic anchor. Before its first RPC
command, it requires the plan's current RPC-manifest, source revision and
dirty-state, dispatcher, release-binary, `SCUS-94288`, and pristine retail
media identities. It then stops before `0x80046078`, requires
`pc=0x80046078`, `a0=18`, and `a1=0x800B5788`, clears and starts
`transferLog`, stops before `0x800460C4`, stops the log, retains complete
bounded pagination, and takes a terminal atomic capture. Every retained
command/result is labeled with one server-session ID and hashed.

Artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_arm.json` SHA-256
`f29fa343d022f0ac647ad07d78384e652b9c272636f42935f28557fdc72246a4`
joins that plan to the prior static subwindow and candidate debugger
identities. Its deterministic synthetic transcript has eleven ordered
command events. Focused mutations reject wrong stop PCs or registers,
clear/start reordering, stale identities, incomplete/truncated or
noncontiguous pagination, and an exhausted finite poll bound.

This is adapter readiness only: zero offline queries executed, zero live
receipts, zero native DMA events, and zero promoted dimensions. E15 remains
four met/five remaining. The next lane stays `static`: predeclare a fresh
exact-PC escalation plus a strictly wider passive cold-boot receipt, and
admit neither to execution until a future immutable before-ledger selects
them. Detailed evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B exact-PC live preflight

Method-ratchet trial iteration 1 retained only `fmv_playback` / `E15_fmv`
and lifecycle. Recursive inventory remains 110 Phase-4 operator files, 147
files in the broader operator tree, and 135 centrally provisioned files.
Ordered regeneration validates 55/55 capsules and 3,391,058,326 preserved
external bytes, 107 queue rows with 91 open and 42 offline-partial, nine
derived indexes over 34 rows, and 148 met dimensions. The existing closed
derived-index receipt remains the relevant complete negative, so this
iteration opened no duplicate offline query.

Generated escalation
`P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE` is now the sole
planned row in the 29-entry live ledger. Its passive receipt repeats the
centrally provisioned pristine LEVEL01 cold boot without instrumentation
over emulator frames `15800..15896`. Independent native and repeat precise
receipts bind one paused `scenario.runBatch` anchor at frame 15816, then the
direct `0x80046078` stop, `a0=18` / `a1=0x800B5788` checks, transfer-log
clear/start, `0x800460C4` stop, complete finite pagination, and terminal
capture through the 15880 ceiling. The passive capture is strictly wider on
both sides.

Artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json` SHA-256
`16d3da88143ee5ad45188f990450e63bcbe20811992de3850119f3198b38f003`
mutation-guards the immutable before-ledger, retained offline negative,
single-submission static boundary, exact adapter identities and limits,
same-anchor receipt set, and non-claim boundary. The iteration-before ledger
contains no planned escalation, so DuckStation did not launch and no live
receipt, DMA event, or promotion is admitted.

The next lane remains `static`. Before execution, implement and guard the
narrow v2 admission path that joins each paused atomic anchor and every
later direct exact-PC command/result under one owned server session, while
preserving historical receipt validation. Regenerate debt before changing
lane, and require a later immutable before-ledger to authorize this exact
ID. Detailed evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B v2 direct-command receipt admission

Method-trial iteration 2 retained only `fmv_playback` / `E15_fmv`, lifecycle
and the binding static receipt-schema task. The retained derived-index receipt
remained the complete negative frame-boundary answer, so no duplicate offline
query was authored. The immutable iteration-before escalation ledger contains
exactly the planned
`P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE` entry.

The v2 receipt validator now admits a direct exact-PC stream only through
`abl-phase4-observer-plan/2`. That plan embeds the closed exact-PC adapter
contract and names `transferLog.start` directly. One completed
`scenario.runBatch` job must end paused at emulator frame 15816, and its
result-bearing `scenario.getBatch` must precede every direct event. Each
later status, stop, register, clear/start, terminal stop, transfer page and
atomic capture retains its normalized result body, finite socket timeout and
the same owned server-session ID. The validator replays those bodies through
the tracked adapter; it does not accept an authored transcript or hide the
observer inside the atomic scenario.

Generated artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_preflight.json` SHA-256
`106bd41b0ea3a85cf5a1bd29ecc4935314f22936a5851f22e4c81e1bdfa2761f`
retains one synthetic atomic anchor, eleven adapter-derived direct events and
three rejected command/anchor/pagination mutations. The historical
schema-v1 atomic fixture remains accepted. Focused tests also reject wrong
PC/register/result/session/order/bound identities.

This packet deliberately launched no DuckStation process. It authored no live
receipt and claims no native DMA event or lifecycle promotion. E15 remains
four met/five remaining and Phase 4 remains 16/107 with 148 met dimensions.
The regenerated next lane is `live`: a new work packet must close the
strictly wider passive receipt first, then execute the native and independent
repeat precise receipts, and require fresh campaign-verifier consumption
before any behavioral promotion. Detailed method evidence remains
[[EXP_2026-07-28_phase4_fmv_region_b_replacement_ownership]].

## Completed-Level-B exact-PC falsifier

The selected `fmv_playback` / `E15_fmv` packet executed escalation
`P4-R6-ITER4-E15-LEVELB-REGIONB-EXACT-PC-DMA-PROVENANCE`. Its wider passive
pristine control closed over frames `15800..15896`. Native and independent
repeat precise receipts then anchored paused at frame 15816 in distinct
isolated profiles, but both escaped the finite frame-15880 ceiling at frame
15881 before hitting `0x80046078`.

The result is a repeated falsifier, not a DMA observation. Artifact
`analysis/phase4_fmv_levelb_region_b_dma_exact_pc_result.json` retains the
three receipt hashes, exact result hashes, identity and cleanup joins, empty
DMA count, and non-promotion boundary. No Canon or Mods claim changes, and
fresh campaign-verifier consumption remains pending.

The binding lane returns to `static`. Re-localize the completed-Level-B
transition against the retained frame-15816 anchor and reconstruct an earlier
instruction boundary; do not replay the escaped exact-PC window. Detailed
runtime evidence is
[[EXP_2026-07-29_phase4_fmv_levelb_exact_pc_falsified]].

## Completed-Level-B transition re-localization

The retained frame-15816 atomic anchor is now projected through a closed
derived-pristine offline receipt without committing memory payload bytes. It
is already paused at resident wait PC `0x8004FEA4`, and Region B no longer
matches the retired FMV.BIN head.

Pristine resident reconstruction proves the complete earlier
completed-Level-B scene-setup first-hit set is `0x8004FD74` or `0x8005029C`.
The calls select `(scene, transition)` pairs `(3, 0)` and `(6, 128)`;
both transitions exclude the `-1` resource-skip sentinel and reach the
selector-zero `bits\memory.bin` request for `0x800B5788`. The nonnegative
call has exactly three classified incoming branches.

Artifact `analysis/phase4_fmv_levelb_transition_relocalization.json` banks
the offline observation, pristine opcode/function identities, complete
predecessor set, explicit inference boundary, and mutation falsifiers. This
closes a static re-localization sub-boundary only: it does not choose the
natural branch, identify a DMA event, verify the prior live receipts, or
promote lifecycle.

The binding lane remains `static`. Implement a typed first-hit boundary over
both earlier PCs before any new live escalation; do not replay the escaped
frame-15816 `0x80046078` window. Detailed evidence is
[[EXP_2026-07-29_phase4_fmv_levelb_transition_relocalization]].

## Completed-Level-B typed two-PC first-hit boundary

The next measured packet retained only `fmv_playback` / `E15_fmv` and the
first unmet lifecycle dimension. Recursive inventory reused 110 operator
Phase-4 files, 147 files in the broader operator movie tree and 135 centrally
provisioned files. Ordered regeneration remained 55/55 capsules, 107 queue
rows with 42 offline-partial, nine derived indexes over 34 rows and 148 met
dimensions. The applicable retained index and closed frame-15816 projection
were reused; no duplicate offline query was executed.

The tracked two-PC adapter now requires exactly two managed pre-instruction
execute stops at `0x8004FD74` and `0x8005029C`. Both must be listed before one
resume. The first accepted pause must match its statically reconstructed
`pc/a0/a1` identity, the winner must have one hit, the loser zero, both owned
IDs must be removed and the breakpoint list must be empty before atomic
capture. All result bodies, frame/poll/socket bounds and the current
source/binary/API/media identities are retained.

Both possible static branches pass deterministic synthetic transcripts.
Mutations reject stop, register, ordering, ambiguity, cleanup, bound,
capture and identity drift. Artifact
`analysis/phase4_fmv_levelb_two_pc_first_hit.json` records two synthetic
transcripts, zero offline queries, zero live receipts, zero native first
hits, zero DMA events and zero promoted dimensions.

No DuckStation process launched and no escalation was authored. The natural
branch and exact earlier frame remain unknown, the prior `0x80046078` window
remains falsified and the three investigator receipts remain pending fresh
campaign-verifier consumption. The binding lane stays `static`: a later
immutable-before-ledger packet may predeclare a strictly wider passive
cold-boot receipt plus an earlier-anchor first-hit receipt. Exact method
evidence is
[[EXP_2026-07-29_phase4_fmv_levelb_two_pc_first_hit]].

## Completed-Level-B managed v2 receipt admission

The measured packet retained only `fmv_playback` / `E15_fmv` and the first
unmet lifecycle dimension. It reused the complete E15 derived index and
retained frame-15816 projection; no new offline query and no DuckStation
operation were required for the static schema/interface fact.

The tracked v2 live emitter now joins one uninstrumented, result-bearing,
paused atomic anchor at frame 15792 to the direct two-breakpoint observer
under one owned server session. The validator admits only the exact
`15792..15856` capture and the two statically reconstructed breakpoint
operations. It replays all normalized result bodies through the tracked
adapter, requires one target-specific winner and zero loser hits, removes both
owned IDs and proves final empty breakpoint pagination. The exact-PC v2 path
and historical schema-v1 receipt semantics remain accepted.

Both static winners pass synthetic receipt admission. Mutations of the
65th frame, command result, cleanup, session, pagination and event order fail
closed. Artifact `analysis/phase4_fmv_levelb_two_pc_first_hit.json` retains
the emitter/runtime/validator identities and records zero live receipts,
zero native first hits and zero promoted dimensions.

The binding lane is now `live`. The current immutable before-ledger contains
the exact planned escalation, but this packet closed only its prerequisite
static admission. The next live work packet must close the predeclared wider
passive receipt before the native first-hit receipt and obtain fresh
campaign-verifier consumption. This method result does not choose the natural
branch or promote E15 lifecycle. Detailed evidence remains
[[EXP_2026-07-29_phase4_fmv_levelb_two_pc_first_hit]].

## Completed-Level-B typed live predeclaration

The recovery packet retained only `fmv_playback` / `E15_fmv` and lifecycle.
Recursive movie inventory remained 110 operator Phase-4 files, 147 broader
operator files, 135 centrally provisioned files and 100 centrally provisioned
Phase-4 files. Ordered regeneration reproduced 55/55 capsules, all 107 queue
rows, nine derived indexes over 34 rows and E15 as the only selected
campaign. No duplicate offline query was executed.

Escalation `P4-R10-ITER1-E15-LEVELB-TWO-PC-FIRST-HIT` predeclares a passive
`15776..15872` cold-boot window and a precise `15792..15856`
managed-breakpoint window. The passive two-job plan validates through the
tracked late-batch adapter; the legacy adapter correctly rejects this
cold-boot staged-prelude shape.

The immutable iteration-1 before-ledger contains zero planned entries, and
the current v2 validator has no managed-two-breakpoint direct-command
admission. No DuckStation process launched and no live receipt was authored.
No natural branch, DMA event, or roadmap dimension is promoted. The next lane
remains `static`: bank the tracked receipt emitter/validator path with an exact
64-frame ceiling, normalized command bodies, one owned server session and
complete breakpoint cleanup before a later immutable-ledger iteration runs
the passive and precise controls. Detailed method evidence remains
[[EXP_2026-07-29_phase4_fmv_levelb_two_pc_first_hit]].

## Completed-Level-B two-PC live falsifier

The selected live packet closed its strictly wider pristine passive control:
both uninstrumented jobs agree through emulator frames `15776..15872`. The
precise run then anchored paused at frame 15792, installed and listed managed
execute stops at `0x8004FD74` and `0x8005029C`, and resumed once.

Neither candidate executed through the finite frame-15856 ceiling. The typed
adapter recorded failure frame 15857, removed both owned breakpoint IDs and
proved the final set empty before the precise profile's owned-PID cleanup.
Artifact `analysis/phase4_fmv_levelb_two_pc_first_hit_result.json` banks the
two closed receipt hashes, atomic result hashes, direct command/result stream,
identity joins, passive equality and exact no-hit falsifier.

No natural branch, argument pair, DMA event or dimension is promoted, and
fresh campaign-verifier consumption remains pending. The binding lane returns
to `static`: find and reconstruct an anchor before frame 15792 rather than
replaying the escaped `15792..15856` window. Detailed evidence is
[[EXP_2026-07-29_phase4_fmv_levelb_two_pc_first_hit]].

## Completed-Level-B pre-15792 predecessor partition

The next measured packet reused the retained `fmv-lifecycle-v2` index before
any static work. Its closed query contains no exact E15 candidate or late
LEVEL01 frame lead, so no capsule bytes were rescanned. A second closed
derived-pristine query projects the retained current-toolchain passive pair:
both jobs are at emulator frame 15720, cycle 8900142073 and resident wait PC
`0x8004FEA4`.

Pristine static reconstruction retains the two candidate calls and closes
their predecessor ownership. `0x8004FD74` has one negative
`pending_scene_request` edge. `0x8005029C` has one request-acceptance-return
edge and two pending-request edges. The request result initializes to zero,
has one setter at `0x8005B63C` behind decoded-input bit 0, a clear local
one-shot and nonnegative `pending_scene_request`, then propagates through
`0x8005B6C8`, wrapper save `0x8005B850`, wrapper return `0x8005BC40` and
caller branch `0x8004FDF8` without redefinition. Resident s32 field
`0x8009EDCC` has thirteen classified compiler-standard direct xrefs: ten
reads and all three direct stores. Static control flow places predecessor
classes around the frame-15720 wait-control position, but the retained PC
does not prove dynamic execution on either side.

Artifact `analysis/phase4_fmv_levelb_pre15792_partition.json` banks two closed
offline receipts, pristine functions/opcodes, the complete two-call/four-edge
partition, transitive return def-use contract, typed state,
non-intersecting LOSE residual and mutation guards. No new offline query was
issued, no live escalation was added and no natural branch, exact frame, DMA
event or dimension is promoted.

The binding lane remains `static`. This changed decomposition closes a new
interface boundary but still does not reduce lifecycle debt. The next
iteration must choose a different static lifecycle question or scheduler
lane; it must not replay the escaped two-PC observer under a new label.
Detailed evidence is
[[EXP_2026-07-29_phase4_fmv_levelb_pre15792_partition]].

## Method-ratchet iteration 2 — decode-timeout field ownership corrected

The selected packet retained only `fmv_playback` / `E15_fmv` and lifecycle.
Ordered regeneration reproduced 55/55 retained capsules and
3,391,058,326 preserved external bytes, all 107 queue rows with zero
offline-ready and 42 offline-partial, nine reusable indexes over 34 rows, and
E15 as the sole selected campaign. The relevant catalog already records that
no exact instruction domain exists in the retained frame-boundary indexes, so
this correction issued no duplicate offline query, scanned no capsule bytes
and required no live escalation.

Pristine static reconstruction falsifies the packet's proposed timeout
width/height copy. `0x800B6D18`/`0x800B6D30` load the selected RECT slot's
signed `x`/`y` from `+0x10`/`+0x12`; `0x800B6D2C`/`0x800B6D38` store those
coordinates to presentation RECT `x`/`y` at `+0x24`/`+0x26`. The function
does not store presentation width or height at `+0x28`/`+0x2A`. The same
artifact binds the `0x00800000` decrement-before-test budget, sole caller
`0x800B72A0`, timeout diagnostic and index transition, ready-clear
convergence at `0x800B6D4C`, and sole return at `0x800B6D60`.

`analysis/phase4_fmv_failure_frontier.json` banks both the falsified packet
hypothesis and survived corrected claim against the authoritative typed
layouts, exact pristine instructions, semantic C and focused mutation guards.
No DuckStation process launched, no live receipt was authored, and no runtime
outcome, lifecycle dimension, row or Mods contract is promoted. E15 remains
four of nine dimensions and Phase 4 remains 16/107 rows with 148 met
dimensions. Original-game facts are reconciled in
[[SYS_fmv_player_streaming]]; the failed hypothesis and method boundary remain
in [[EXP_2026-07-28_phase4_fmv_failure_frontier]].

## Method-ratchet iteration 1 — shared frame-sync wait ownership

The selected packet retained only `fmv_playback` / `E15_fmv`, with lifecycle
as the first unmet dimension and `static` as the binding lane. Recursive movie
inventory found 110 operator Phase-4 files, 147 broader operator files, 135
centrally provisioned files and 100 central Phase-4 files; no operator fixture
was imported. Ordered regeneration retained 55/55 capsules,
3,391,058,326 preserved external bytes, all 107 opportunity rows, nine
derived indexes over 34 rows, and E15 as the sole selected campaign.

The relevant index and retained frame-15720 boundary were validated before
static work. No missing frame-boundary question required another offline
query, and exact instruction ownership was absent from the capsule domain.
This packet therefore scanned no capsule bytes and launched no DuckStation
process.

Pristine reconstruction corrects the historical `fmv_running_latch` label.
Resident u32 `0x80082250` has ten complete compiler-standard direct xrefs:
four reads and six writes. Context-save interrupt handlers clear it before
`frame_present`, pad start/stop clear it, and helper `0x8003F2F0` has five
classified callers spanning transition, display, overlay and gameplay-reset
owners. Scene-flow `0x8004FE98..0x8004FEB8` is instruction-identical to the
shared helper's set-one/wait-while-one protocol.

Artifact `analysis/phase4_fmv_frame_sync_wait_ownership.json` binds those
facts to exact pristine slices, authoritative typed state, source hashes,
the retained work packet and focused opcode/artifact mutations. Its
falsifier survived. The retained frame-15720 PC is only a shared frame-sync
control position, so no natural branch, retirement frame, DMA event, live
escalation or dimension is promoted.

E15 remains four met/five remaining and the lane remains `static`, but
`0x80082250`/`0x8004FEA4` is retired as a lifecycle discriminator. The next
packet must reconstruct a distinct earlier state producer or change scheduler
lane; it must not replay or relabel the escaped `15792..15856` observer.
Detailed evidence is
[[EXP_2026-07-29_phase4_fmv_frame_sync_wait_ownership]].
