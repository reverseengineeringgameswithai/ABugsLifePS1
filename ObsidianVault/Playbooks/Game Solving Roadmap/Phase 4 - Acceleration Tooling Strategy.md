---
kind: playbook
id: PLAYBOOK_phase4_acceleration_tooling_strategy
name: Phase 4 - Acceleration Tooling Strategy
status: accepted
acceleration_ratchet: accepted
acceleration_next3_ratchet: accepted
acceleration_third3_ratchet: accepted
acceleration_scheduler3_ratchet: accepted
created: 2026-07-31
updated: 2026-08-05
confidence: high
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_roadmap
  - PLAYBOOK_game_solving_phase_4
  - PLAYBOOK_phase4_reverse_engineering_operating_method
---

# Phase 4 - Acceleration Tooling Strategy

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 execution note]] · Accepted operating-method ratchet · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]]

<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_START -->
Hard-truth accepted. Run `phase4-acceleration-hard-truth-r6-20260731T222602-0400` reviewed commit `3e30b6ef8171c1c0cc7177d70971ff0ac2558337` at 2026-07-31T22:26:02-04:00. Conclusion: The exact candidate satisfies the Phase-4 acceleration tooling ratchet. Static-frontier, overlay, proof-pilot, promotion-preflight, raw Ghidra evidence, inventory, downstream regeneration, vault, forbidden-artifact, and regression-neutral safe-suite claims survived independent regeneration and adversarial mutation. No DuckStation method-universe path changed; the verifier launched or altered no DuckStation component. Decision SHA-256: `2fd5a6ceee7eede4ccba9427a6c57fcbec0515dea023b4cbe2768221978f098c`.
<!-- PHASE4_ACCELERATION_RATCHET_VERDICT_END -->

<!-- PHASE4_ACCELERATION_NEXT3_RATCHET_VERDICT_START -->
Hard-truth accepted. Run `phase4-acceleration-next3-hard-truth-r7-20260801T003827-0400` reviewed commit `f400f2d911c75e32e145310aebd5567d55bca7e2` at 2026-08-01T00:38:27-04:00. Conclusion: The exact repaired candidate satisfies the complete Phase 4 acceleration next-three ratchet. The previously terminal dangling-output-symlink defect is repaired and independently reproduced as fail-closed; all retained and adversarial DAG, minimizer, and MIPS checks pass; generated integration checks are clean at the retained generation epoch; and the full candidate-versus-parent safe-suite differential has zero candidate-only failed nodes. No DuckStation method/source/configuration, process, live emulator, fixture, movie, receipt, or evidence path was touched, and the candidate bank was not run. Decision SHA-256: `312c5aa41eb4e585ed95954fce6602244dfd57cd0d19d6cc777bff946679f901`.
<!-- PHASE4_ACCELERATION_NEXT3_RATCHET_VERDICT_END -->

<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_START -->
Hard-truth accepted. Run `phase4-acceleration-third3-hard-truth-r10-20260801T054122-0400` reviewed commit `4b7cba1e2eba0e0774d1bbf59743309c8669301e` at 2026-08-01T05:41:22-04:00. Conclusion: The exact repaired candidate satisfies the complete third acceleration tranche; all Round 1-9 exploits, exact retained-set completeness, artifact, external-run, integration, and symmetric differential checks pass without DuckStation or Redux contact. Decision SHA-256: `2284517b0114dc08f12bc4ca5419d35aba61433989367572b0533d4128e7a4ed`.
<!-- PHASE4_ACCELERATION_THIRD3_RATCHET_VERDICT_END -->

<!-- PHASE4_ACCELERATION_SCHEDULER3_RATCHET_VERDICT_START -->
Hard-truth accepted. Run `phase4-acceleration-scheduler-hard-truth-r8-20260801T202839-0400` reviewed commit `151a5a3bbf07186126a54070e5b2ddc401396e04` at 2026-08-01T20:28:39-04:00. Conclusion: The exact scheduler candidate satisfies investments 10-12 with a monotonic four-node safe-suite improvement and without DuckStation or Redux contact. Decision SHA-256: `831064e0c81c3f80855cecab771f17a0686b8a7d7e6159abb19c331d3cb74503`.
<!-- PHASE4_ACCELERATION_SCHEDULER3_RATCHET_VERDICT_END -->

## Decision

Phase 4 should accelerate by making static semantic closure, overlay analysis, and
promotion preflight machine-assisted. The immediate implementation tranche is:

1. a production Phase-4 Static Frontier Compiler;
2. an overlay-first semantic index; and
3. a promotion-packet preflight linter.

This tooling tranche is finished when it indexes the complete current resident and
overlay census, reproduces the E15 hand-audited benchmark, produces bounded E08 and
C13 application reports, fails closed under mutations, and passes a fresh detached
hard-truth verifier. It does **not** finish Phase 4, close any campaign row, promote a
nine-dimension leaf, or replace the fresh campaign verifier.

The second implementation tranche is:

4. a bounded incremental evidence DAG for the Phase-4 control-plane chain;
5. a DuckStation movie/scenario minimizer with assertion-plus-control replay; and
6. a bounded MIPS32LE micro-execution oracle.

This second tranche is a candidate until its separate hard-truth marker is accepted.
It does not reopen or weaken the accepted first tranche, promote a campaign claim, or
make micro-execution behavioral authority.

The third implementation tranche is:

7. an external DuckDB/Parquet trace warehouse with four standardized query packs;
8. read-only Kaitai schemas plus a bounded deterministic parser-fuzz harness; and
9. hash-only external-evidence registry, receipt verifier, and private git-annex plan.

This third tranche is a candidate until its own hard-truth marker is accepted. The
warehouse pilot uses synthetic frame records and does not claim that the 55 retained
capsules have been imported. The preservation registry names 178 required objects but
authors zero availability: real replication is complete only after two private,
independent external receipts verify every object.

DuckStation is the primary RE emulator. The static frontier, overlay index, promotion
preflight, evidence DAG, and MIPS oracle remain emulator-neutral. The minimizer uses a
narrow external replay adapter: it does not modify the DuckStation fork/API, existing
scenarios, fixtures, or historical evidence. PCSX-Redux is neither a dependency nor a
focus of either tranche.

For all new movie-driven work, `execTrace` and the movie replay must run with the CPU
execution mode set to **Interpreter**. Every DuckStation instance started for this
work must use a freshly created isolated config whose runtime settings verify
`Interpreter`; cached-interpreter receipts fail closed. This is the durable resolution
of the movie/`execTrace` problem.

The setting is necessary but no longer sufficient evidence. Preserve
`debugger.status.execution_mode` from the beginning and end of the window,
including configured/effective/last-dispatch modes, override reason/subsystem,
`transition_pending`, and bounded frame/cycle history. Record `history_total`,
`history_retained`, `history_capacity`, `history_dropped`, `history_truncated`,
and each entry's monotonic `sequence`. Prove the interval by retaining the
beginning/end totals and every contiguous sequence from beginning total plus one
through ending total and inspecting every `to` mode; a lower ending total means
the CPU runtime restarted and invalidates the interval. Prefer a beginning boundary
with `transition_pending:false` and `last_dispatch == effective == Interpreter`;
require the same at the end. If the beginning is pending, the first new sequence
must connect its `last_dispatch` to its `effective` mode. Global truncation is
acceptable only when the full interval-specific sequence remains retained. The
history records effective-mode transitions, not override-subsystem changes which
leave the mode unchanged, so preserve live/boundary `override_subsystems` separately
when instrumentation ownership matters. Final mode strings or the configured setting
alone cannot establish how the window executed; any unaccounted transition makes
timing-sensitive evidence incomplete.

## Authority and safety boundary

- `AGENTS.md`, the roadmap hub, the Phase-4 execution note, and the accepted operating
  method remain authoritative.
- The hash-verified pristine SCUS-94288 retail image is the sole original-behavior
  authority and the sole patch/build base. ALLMODS and derivatives remain historical
  comparison evidence only.
- Retail images, overlay blobs, decompiled C, raw p-code, Ghidra databases, movies,
  saves, capsules, BIOS files, captures, credentials, and generated discs stay out of
  Git. Git may retain bounded addresses, graph relationships, schemas, hashes,
  generators, tests, and non-copyrighted summaries.
- Static indexing is localization and frontier evidence. It is not automatic semantic
  ownership, every-path behavior, campaign breadth, lifecycle, or causal runtime proof.
- The dirty operator checkout is read-only. This work starts at retained Phase-4 seed
  `dbab87c1c2bfe87ae2cb7ffe222ee2b87f745f8b` in an isolated worktree.

## DuckStation deterministic-runtime contract

These are fail-closed gates for new live evidence, not retroactive rewrites of
the retained Phase-3/Phase-4 artifacts:

1. Treat the JSON-RPC surface as additive-only. Existing response members remain
   compatibility fields; clients consume new members without replacing old
   shapes. Residency generations, phase audit state, and mode history are
   debugger-runtime-only and must never enter save-state serialization or force a
   `SAVE_STATE_VERSION` bump.
2. Query `debugger.capabilities` for the runtime concurrency contract. The source
   manifest contains 220 dispatched `KnownMethods`; capabilities reports 221
   because it also describes connection-only `debugger.authenticate`. Each method
   advertises `methods.<name>.scenario_execution_policy` as `exclusive`,
   `observation`, `batch_control`, or `connection_control`; the top-level
   `scenario_execution_gate` publishes the fail-fast contract. While an
   asynchronous scenario worker owns the runtime-only gate for a job, a concurrent
   direct `exclusive` call must fail immediately with `-32005`; its `error.data`
   must contain
   `reason:"scenario_execution_busy"`, the requested `method`,
   `policy:"exclusive"`, `retryable:true`, and `runtime_only:true`. Observation calls and
   `scenario.getBatch`, `scenario.cancelBatch`, and `scenario.resumeBatch` remain responsive;
   `scenario.runBatch` itself returns promptly as `batch_control`, while workers
   serialize on the one core. Authentication is independent, newly known methods
   default fail-safe to `exclusive`, and gate state is never serialized.
3. Before resolving any Region-A/Region-B address, call
   `memory.getResidency`; retain source/file offset, runtime base/size,
   source/resident hashes, `sourceMatchesResident`, and load
   generation/timestamp. Re-query the generation tuple plus resident hash before
   the breakpoint and after the window. A generation change invalidates the
   attribution; a hash-only change records resident-byte divergence. A source mismatch may be
   legitimate self-modification when exact load provenance still identifies the
   source; missing/ambiguous provenance is never filled in by guesswork.
4. Prefer `movie.loadAndArm` for a movie/start-state experiment. It stages the
   movie and start frame, rejects active movie work, verifies optional media,
   and preflights movie/start-state serial, metadata, size, and optional hash
   before mutation. It then pauses/snapshots, loads the anchor, explicitly
   re-verifies `expected_media` because a save-state load can replace the mounted
   image, and only then clears trace and breakpoint state, consumes a pending
   correction when requested, arms new watches/breakpoints, and establishes one
   paused boundary. Post-load verification occurs before trace clear/phase/arm;
   mismatch enters cleanup. Preserve `media_after_start_state` and
   `media_changed_during_setup` on success.
   Preserve both coordinate systems and all phase fields from `movie.status`:
   `anchor_emulator_frame`, `current_movie_frame`,
   `current_emulator_frame`, `movie_to_emulator_offset`,
   `phase_correction_pending`, and `phase_correction_consumed_at`.
   `atomic:true` means
   `atomic_scope:"serialized_request_to_paused_arm_boundary"`, not full rollback.
   Require `transactional_rollback:false` and inspect any
   `error.data.failure_cleanup`. Cleanup reports the mount separately: after a
   state-driven swap require `media_identity_restored:true`, not merely
   `machine_state_restored:true`.
5. A normal RPC return is not proof that bounded execution reached its target.
   Require `execution.completed:true`; otherwise use
   `execution.advanced_frames`, `execution.end_frame`, `execution.stop_reason`, and
   `execution.stop_details` as the actual endpoint. Legacy top-level
   `frames_advanced`/`framesAdvanced` fields may preserve requested-count or
   movie-coordinate-delta meanings; only `execution.advanced_frames` is measured
   guest progress. `debugger.stepInstruction`, `debugger.stepOver`,
   `debugger.stepOut`, `debugger.advanceFrame`, and
   `debugger.runUntilAddress` preserve their immediate legacy top-level status and
   add `end_status`, `execution`, and top-level completion aliases. Use
   `end_status` as their post-operation snapshot. Use
   `movie.resumeUntilMovieFrame` for a throttled/normal-speed claim, and retain
   the `movieCompleted` terminal coordinates/hashes when playback ends.
6. For `movie.traceToFrame`, preserve the old predicates but do not mistake them
   for coordinate-aware proof. `control.movie_frame` and
   `instrumented.movie_frame` remain legacy `playback_index` values;
   `current_movie_frame` is the explicit mapped coordinate.
   `comparison.same_frame` remains the emulator-frame/playback-index comparison,
   and `comparison.cycle_neutral` remains its legacy composite. Require additive
   `comparison.same_movie_coordinate`, `comparison.same_phase`,
   `comparison.coordinate_neutral`, and `comparison.comparison_valid` all true;
   the last is only an alias of `coordinate_neutral`. For mapped-coordinate proof,
   also require non-null `current_movie_frame` in both signatures. Separately
   require `execution.control.completed`, `execution.instrumented.completed`, and
   `coverage[*].coverage.truncated:false` with declared ranges covering the claim.
7. Evidence reads use `debugger.scatterRead {atomic:true}` or an explicit
   `invalidValuePolicy:"omit"|"null"|"error"`. A legacy zero with
   `valid:false` is not data.
8. Express hit/no-hit, first/last, value-at-hit, ordering, signed frame/cycle
   delta, and non-truncation claims through `trace.assert` or scenario assertions.
   When a predicate needs RAM at an execution hit, opt into bounded
   `execTrace` `capture_memory`; do not substitute a later memory read.
9. Use `debugger.xrefsAcrossOverlays` for identity-preserving static
   cross-references. Preserve the run with `evidence.captureBundle` and
   machine-readable `trace.export`; keep payloads external and commit only hashes,
   schemas, commands, and preservation metadata.
10. Prefer intent-labelled inputs to naked absolute frames:
   `movie.findInputEdges`, `movie.resumeUntilInputEdge`, bookmarks, and bounded
   `movie.timingSweep`. Sweep variants become evidence only after deterministic
   replay plus a complete relational/non-truncation assertion and control.

Normal-speed trace capsules move from convenience to a required experiment
primitive whenever interpreter timing or throttled real-time behavior is itself
part of the claim. They remain frame-exact/checkpoint-exact artifacts, not
every-cycle hardware traces, and all capsule acceptance/control rules still
apply.

## Audited repository snapshot

### Observations

At the selected retained seed:

- the debt ledger contains 107 rows: 16 complete/reviewed absent and 91 open;
- open work routes to 89 static lanes and two offline lanes, with no currently planned
  live lane;
- the nine-dimension ledger contains 149 met, 57 partial, and 757 gap leaves;
- the offline queue contains 42 `offline_partial` and 65 `no_capsule` rows;
- resident reconstruction accounts for 998 census records and reports 913 matched
  functions, 91.48% of the resident function census and 98.209% of resident code
  bytes;
- the overlay census contains 158 code functions, only 15 of which are byte-matched
  in the retained overlay progress report, or 9.49%; and
- the accepted methodology audit recorded five promotion events in 16 successful
  iterations, eleven no-reduction iterations, a net four met leaves, zero row
  closures, four gap-free verifier decisions out of fourteen, and 21 controller
  timeouts reported separately from semantic work.

The repository already has a strong function census, PsyQ identification, a Ghidra
12.1.2 pilot, `$gp` recovery, typed state, record schemas, phase-wide xrefs, overlay
hashes, persistent trace capsules, declarative scenarios, mutation guards, a closure
debt scheduler, and a fresh-verifier ratchet.

### Inference

The dominant bottleneck is not absence of emulator observations. It is converting a
localized fact into a complete, typed, falsifiable semantic claim without reopening
source ownership, interfaces, lifecycle, breadth, dependencies, or durability. The
89/2 static/offline split, overlay coverage gap, and promotion-boundary rejection
history independently support this inference.

More broad replay or universal capsule capture would optimize the wrong lane. The
highest-value automation is a fail-closed static frontier that makes missing ownership
and unclassified intersections explicit before a live experiment or promotion packet
is attempted.

## Prioritized investments

| Priority | Investment | Expected effect | This tranche |
|---|---|---|---|
| P0 | Canonical integration snapshot | Prevent stale-branch and generated-file rework | Ratchet worktree only; no operator-WIP integration |
| P1 | Static Frontier Compiler | Attack the 89 static rows directly | **accepted implementation** |
| P1 | Overlay-first analysis | Open loading, bosses, special stages, lifecycle | **accepted implementation** |
| P1 | Promotion-packet linter | Improve first-pass verifier acceptance | **accepted implementation** |
| P2 | Incremental evidence DAG | Reduce generator/hash cascades | **accepted implementation** |
| P2 | Movie/scenario minimizer | Reduce replay and observer windows | **accepted implementation** |
| P2 | MIPS micro-execution oracle | Settle bounded arithmetic/state questions | **accepted implementation** |
| P2 | DuckDB/Parquet warehouse | Consolidate repeated offline queries | **accepted implementation** |
| P3 | Structured binary schemas and fuzzing | Harden parsers, codecs, and asset tools | **accepted implementation** |
| P3 | External-evidence content management | Improve preservation/location tracking | **accepted implementation** |
| P2 | Reviewed two-no-reduction cooldown | Stop repeated low-yield row/lane work | **accepted implementation** |
| P2 | Expected-value scheduler rank | Prefer dependency unlock and reducible, ready debt at lower observed cost | **accepted implementation** |
| P2 | Weighted breadth-fixture cover | Reduce replay/capsule work while retaining row/domain/control breadth | **accepted implementation** |

## Investment 1 — Static Frontier Compiler

### Purpose

Convert the existing Ghidra/census/symbol/schema substrate into a deterministic,
claim-directed index. Given function roots, state ranges, record-relative offsets, or
an overlay set, it must enumerate calls, accesses, state joins, and unresolved
boundaries without inventing semantic owners.

### Inputs

- `analysis/functions.json` as the canonical resident/overlay census;
- `symbols/re_symbols.sym` as authoritative project naming;
- `config/segments.yml`, `config/overlays.yml`, and the pristine build-baseline
  manifest for load addresses, `$gp`, file roles, and hashes;
- `config/semantic_state.yaml` and `config/record_types.yaml` for explicit type joins;
- target declarations for E15, E08, and C13; and
- local, hash-verified pristine executable/module bytes provisioned outside Git.

### Output contract

Every census record is keyed by `{image_id, entry_address}`. Code/thunk records contain
extent, blocks, direct calls, indirect-call sites, returns, switch/branch structure,
delay-slot context, normalized memory expressions, widths, signed-operation evidence,
resolved absolute or `$gp`-relative accesses, typed joins, exact and structural
fingerprints, analysis method, input hashes, and unresolved boundaries. Data records
are retained as explicit non-code records rather than silently dropped.

Raw high p-code and decompiler output stay external. The committed normalized index
contains only bounded graph facts and hashes. A failed high-p-code decompilation must
fall back to instruction p-code/static decoding; a record with neither path is a fatal
index error.

### Frontier rules

- A target declares roots, in-scope images/ranges, explicit boundary owners, and any
  record type bindings.
- The compiler walks all direct edges and retains every indirect edge as unresolved
  until a bounded target set is independently declared.
- No depth limit may be used to claim a complete frontier.
- Every excluded edge carries an owner/reason. Every address-range intersection is
  classified as reader, writer, read/write, or unresolved.
- Structural fingerprints create investigation candidates only. Exact fingerprints
  do not prove runtime equivalence across residency, global state, or lifecycle.
- The compiler may report a frontier as closed only when the declared universe is
  exhaustive and its unresolved-intersection set is empty. It never changes a Phase-4
  dimension by itself.

### Ghidra basis

The existing pilot already showed complementary value: it reproduced the HUD model,
resolved deferred scene panels, applied project symbols, and eliminated `unaff_gp`
through the `0x80081D98` context. The PSX loader project identified PsyQ 4.0 and hundreds
of SDK functions. The production exporter builds on Ghidra's headless API,
`DecompInterface`, high p-code, and the installed `ghidra_psx_ldr`; it does not require
GhidraMCP.

References: [Ghidra](https://github.com/NationalSecurityAgency/ghidra),
[PyGhidra](https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Features/PyGhidra/src/main/py/README.md),
[p-code](https://ghidra.re/ghidra_docs/languages/html/pcodedescription.html), and
[PSX loader](https://github.com/lab313ru/ghidra_psx_ldr).

## Investment 2 — Overlay-first semantic analysis

The resident image is already substantially reconstructed while the overlay code
census remains 9.49% byte-matched. Overlay work is therefore a first-class closure
lane, not an optional tail of resident decompilation.

The semantic overlay index must:

- cover all current Region-A level overlays and Region-B `MEMORY.BIN` code functions;
- preserve same-address functions as distinct `{overlay,address}` identities;
- distinguish the Region-A four-byte header and code-at-base-plus-four convention;
- record per-image input identity, base, `$gp`, extents, resident callees,
  overlay-local state, unresolved calls, and source/match status;
- cluster exact fingerprints separately from weaker normalized structural candidates;
- support extra Region-B modules such as FMV without conflating their lifetimes; and
- fail on missing/duplicate census rows, overlapping extents, hash drift, wrong base,
  wrong `$gp`, or undeclared input bytes.

The immediate value is semantic transfer: a solved helper in one level can nominate a
related helper elsewhere, while constants, branches, interfaces, and residency
differences remain explicit. Full matching C is not a prerequisite for a useful
frontier, and clustering never promotes ownership.

## Investment 3 — Promotion-packet preflight

Verifier history shows that plausible facts are often rejected at the promotion
boundary. A promotion packet makes every applicable obligation inspectable before the
fresh campaign verifier is invoked.

Each packet names its row, campaign, dimension, before-debt hash, proposed transition,
confidence, low-level assertions, tracked authoritative paths, relevant static
frontier, typed state, interfaces, lifecycle, breadth, controls, source status,
external dependencies, bounded residuals, knowledge-layer disposition, and a
disposable falsifier. Inapplicable layers require a reason.

The linter derives dimension-specific obligations from the Phase-4 closure policy,
checks current hashes and tracked paths, rejects authored success booleans, and emits
stable error codes. Its strongest positive result is `ready_for_fresh_verifier`; it
never edits the campaign registry or certifies a promotion.

## Required proof pilots

### E15 FMV benchmark

The new compiler must reproduce the retained hand-audited FMV boundary: 30 Region-B
address rows, 99 exact xrefs, and 58 player-boundary xrefs. Differences require an
exact address-level explanation and mutation guard. This benchmark proves recall and
guards against a plausible-looking but incomplete Ghidra export.

### E08 props/movers application

The application report must join the retained 28 uncontrolled classes, all 40 decoded
selectors, and ten callback functions. It must produce bounded candidate slices for
the five highest-priority classes while retaining zero automatic semantic-owner or
dimension promotions.

### C13 grain/harvester application

The report must recover the retained grain/harvester function and state roots and name
known readers/writers. It must keep steering, clear writers, enemy/all-level breadth,
render, animation, audio, reset, and future MOD consumption open wherever the retained
campaign leaves them open.

## Second acceleration tranche

### Incremental evidence DAG

The Phase-4 control plane is large enough that dependency-aware regeneration should
eventually replace broad hash cascades. Preserve both exact byte hashes and normalized
semantic hashes; the latter may prevent timestamp/ordering churn from invalidating
unrelated semantics but may never replace exact preservation identity. Evaluate a
small repository-native DAG before adopting [DVC pipelines](https://dvc.org/doc/user-guide/pipelines/running-pipelines).

`tools/phase4_evidence_dag.py` implements that repository-native pilot over the
six-node chain that caused the first tranche's stale-hash repairs: offline queue,
closure debt, live escalations, movie priority, promotion preflight, and Phase-4 gate.
`config/phase4_evidence_dag.yaml` declares every node's generator, command,
classification, inputs, outputs, comparison mode, and accepted exit codes. The graph
rejects unsafe paths, duplicate output ownership, missing producer edges, cycles,
missing bytes, undeclared execution classes, symlinked movie trees, and removed nodes.

Every file has an exact SHA-256 and a normalized semantic SHA-256. JSON semantic
normalization removes presentation-only dates/comments plus explicitly declared JSON
pointers; it does not erase provenance hashes by default. Each input edge independently
chooses exact or semantic invalidation, so preservation identity is never silently
replaced. `--plan` reports direct dirtiness and a conservative downstream order;
`--run` recomputes identity after every generator and skips a descendant when an
upstream semantic no-op leaves its selected input identity unchanged. Static execution
is the default. Local-media and live nodes require separate explicit allows.

The tracked graph is intentionally bounded, not advertised as complete Phase-4 DAG
coverage. Its synthetic mutation pilot proves exact-churn detection, presentation-only
semantic suppression, real semantic-change detection, exact-consumer invalidation,
and dynamic semantic no-op pruning. Expansion beyond this chain should be justified by
measured invalidation/rebuild cost, not by adopting DVC as a prerequisite.

### Movie and scenario minimization

Use hierarchical delta debugging: remove frame ranges, neutralize buttons/axes, tighten
anchors, and replay the assertion and control after every reduction. Preserve whether
the claim needs cold boot or a validated state. References:
[delta debugging](https://www.st.cs.uni-saarland.de/papers/tse2002/) and
[Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html).

`tools/phase4_movie_minimizer.py` implements hierarchical frame-range deletion,
frame-range neutralization, whole-control removal, analog neutralization, and bounded
scenario start-frame tightening. Deleting frames reindexes the movie and shifts only
movie-frame playback/trigger anchors; emulator-frame triggers remain unchanged. The
source movie, scenario assertions, and cold-boot/save-state anchor class remain
immutable. Minimized movies, scenarios, receipts, and reports remain outside the
repository. Existing paths, including dangling symlinks, are collisions, and every
resolved output destination is checked before the first write.

The tool is deliberately adapter-driven. Every candidate—including the baseline—must
produce a schema-checked DuckStation receipt binding the exact movie/scenario bytes,
binary, source revision, verified media, recreated absolute config, loopback port,
launcher, config identity, runtime settings, and hashed token. Exactly two distinct
replays are required: assertion and control. Both must pass without errors or
truncation, preserve the complete assertion-ID universe and anchor class, verify movie
reproducibility, re-arm instrumentation after load, use an owned PID, and complete
owned cleanup. Legacy receipt fields `execution_mode` and `movie_execution_mode`, plus
the verified runtime setting, must still equal `Interpreter`, but those final strings
are not interval proof. Each assertion/control receipt must also retain beginning/end
`debugger.status.execution_mode` snapshots, `history_total`, `history_retained`,
`history_capacity`, `history_dropped`, `history_truncated`, endpoint
`last_dispatch`/`effective`/`transition_pending`, and every contiguous history
`sequence` added during the replay. Reject the receipt unless that complete
sequence proves all guest work in the interval used `Interpreter`, the end has
`transition_pending:false`, and its `last_dispatch` is `Interpreter`. A
cached-interpreter, incomplete-history, unaccounted-transition, or raw-token receipt
is rejected.

The tracked pilot uses a synthetic, non-game movie and demonstrates reduction from 12
frames to the two required signal frames while removing an irrelevant input. It is an
algorithm/contract proof, not DuckStation runtime evidence and not a claim that any
existing project movie has already been minimized.

### Bounded MIPS micro-execution

Use [Unicorn](https://github.com/unicorn-engine/unicorn) plus generated/shrunk inputs
for pure or RAM-local routines: masks, capacities, dispatch selectors, signedness,
wraparound, and arithmetic. Reject MMIO, DMA, GTE, CD, GPU, SPU, interrupt,
self-modifying, and timing-sensitive functions unless modeled and calibrated against
known PS1 controls. Micro-execution supplements rather than replaces native behavior.

`tools/phase4_mips_oracle.py` pins Unicorn 2.1.4 and accepts declarative MIPS32
little-endian routine specs. It generates Cartesian boundary cases, evaluates results
against a small typed 32-bit model language, preserves signed/unsigned and wraparound
semantics explicitly, and shrinks a failing input toward canonical boundaries. Code,
stack, return sentinel, allowed RAM, instruction count, engine version, and output
identity are bounded and recorded.

Only `pure` and `ram_local` classes are accepted. Static preflight rejects COP0,
COP2/GTE, cache, syscall, and break instructions. Runtime hooks reject MMIO,
undeclared data access, self-modifying writes, control escape, and failure to return
within the instruction limit. DMA, CD, GPU, SPU, interrupts, and timing-sensitive
questions remain categorically outside the oracle. The synthetic pilot exercises
masking, signed comparison, 32-bit wraparound, and declared RAM-local load/store
behavior. Its results localize arithmetic hypotheses only; a native DuckStation
control is still required for behavioral claims.

## Third acceleration tranche

### Trace warehouse

Valid capsule-derived frame records can become external partitioned Parquet queried
through [DuckDB](https://duckdb.org/docs/stable/data/parquet/overview). Standardize
first-change, positive/negative contrast, block enrichment, and cross-movie queries.
Commit schemas, readers, queries, manifests, and bounded results only. This remains
localization evidence, not exact causality.

`tools/phase4_trace_warehouse.py` implements this as an external-only DuckDB 1.5.5
database plus Zstandard-compressed Parquet domain partitions. Its import manifest must
bind every imported movie to the retained capsule manifest/tree hashes. The retained
capsule set must be complete, control-matched, untruncated, error-free, and
reproducible. Input partitions are byte/hash/row-count pinned; paths, symlinks,
repository output, collisions, unknown domains, and unbound movie/cohort rows fail
closed. Top-level capsule errors must be exactly empty, retained v2 rows reject
undeclared status fields, booleans cannot masquerade as integers, and every event is
bounded to the closed movie-relative frame-boundary interval
`[0, retained capsule frames]`. A retained movie can bind only once across all capsule
IDs and cohorts. Partition paths must use canonical POSIX-relative spelling, and
duplicate physical files—including hard links—cannot be imported twice. The complete
recursively typed warehouse policy is immutable: complete/control requirements,
domains, cohorts, limits, output layout, query definitions, and authority flags all
fail on any value or type drift. `cross_movie` counts distinct movies. DuckDB extension
auto-install/load is disabled.

The fixed query packs are `first_change`, `cohort_contrast`, `block_enrichment`, and
`cross_movie`. The retained pilot exercises all four over three synthetic capsules and
eight events. Database and Parquet bytes remain external; Git retains the policy,
reader/query implementation, tests, and bounded synthetic result only. A real import
is intentionally still unclaimed.

### Binary schemas, fuzzing, and evidence preservation

- Use [Kaitai Struct](https://kaitai.io/) for stable read-only binary format schemas;
  keep existing writers until round-trip and mutation proofs pass.
- Fuzz narrow deterministic parsers, decompressors, relocators, and VM decoders with
  [AFL++](https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/fuzzing_in_depth.md)
  or [libFuzzer](https://llvm.org/docs/LibFuzzer.html) using synthetic/corpus-safe data.
- Pilot [git-annex](https://git-annex.branchable.com/) with private local/offline
  remotes for large external evidence. Do not move retail bytes to a public remote.
- [objdiff](https://github.com/encounter/objdiff) may improve local MIPS matching
  ergonomics but is lower leverage than semantic frontier closure.

`schemas/phase4/` now contains CC0 read-only Kaitai schemas for the decompressed seed
table, LEVEL.RAW container framing, and bounded compressed-chunk envelope. Endianness
is adapter-pinned as `seed_table=le`, `level_raw_container=be`, and
`level_raw_chunk=be`; missing, mistyped, or swapped declarations fail closed.
`tools/phase4_binary_schema_fuzz.py` validates the exact schema set, creates a
synthetic-only corpus, applies deterministic truncation, bit-flip, boundary-length,
and append mutations, and runs each parser adapter in a memory-, time-, input-, and
output-bounded child process. Its exact contract pins seed `424242`, limits of
1,048,576 input bytes, 4,194,304 output bytes, 96 cases per target, 500 ms, and
268,435,456 memory bytes, plus ordered schema declarations, ordered mutation
operators, and every authority boolean. Integer fields reject booleans and every
policy value/type drift fails closed. Caller-supplied policies use this same exact
validator before parser work or corpus creation, including falsey supplied values.
The retained pilot replays 285 cases twice with zero
crashes, timeouts, output-limit escapes, or nondeterminism. Existing writers are not
replaced; any AFL++/libFuzzer corpus export remains external.

`tools/phase4_external_evidence.py` derives a path-free central registry from the
retained trace-capsule set. It records 178 capsule trees, collection manifests,
movies, saves, pristine media identities, DuckStation binary/runtime/source
snapshots, and the offline reader. Every availability field remains `unverified` in
Git. An external receipt set must bind the registry hash, private remote kind,
content-addressed location, exact bytes/hash, and named failure domain. Two remotes in
one failure domain count once. For local/removable roots, independence additionally
requires distinct verified filesystem devices (`st_dev`); caller labels cannot split
one device. Private-annex roots remain uncounted until an immutable remote attestation
is verifiable. Tamper, public-remote, secret-retention, traversal, collision, symlink,
overlapping/canonical-root aliases, and hard-linked-copy cases fail closed.
Capsule and runtime tree objects additionally bind the exact retained manifest hash;
their manifests must cover every regular payload file, with undeclared files and any
recursive symlink rejected. The complete policy is recursively exact, including the
hash/layout, remote/media lists, backend, physical-domain rules, and all authority
booleans. Registry and receipt documents have exact top-level and nested contracts;
byte and copy counts reject booleans/floats, roles are non-empty strings, retained
summary/source/authority state is derived exactly, and authored readiness is rejected.

The git-annex portion is deliberately a non-executing private plan: it initializes no
repository, publishes no remote, and separates file objects from tree objects that
need externally validated packaging. The synthetic pilot proves same-filesystem
directories cannot manufacture independence and separately exercises the distinct-
verified-device grouping model. It does not claim real preservation readiness; the
retained registry currently reports zero of 178 objects fully replicated because no
real external receipt set was provided to this tranche.

## Fourth acceleration tranche — scheduler investments 10-12

### Investment 10 — reviewed two-no-reduction cooldown

The prior movie-ready scheduler rotated after one no-reduction iteration, while the
closure controller only surfaced a two-iteration stagnation warning. It did not carry
enough authenticated attempt history to prevent the next generated packet from
returning to either recently exhausted row set.

`config/phase4_scheduler_policy.yaml` now makes the rule explicit and reviewed. Packet
schema v3 requires the exact prior queue, packet, progress, debt-before, and debt-after
snapshots together; the prior packet must regenerate from its queue, policy, and
genesis-anchored history. The controller and validator share one transition-derivation
implementation. One no-reduction attempt forces a disjoint batch. Two consecutive
no-reduction attempts activate a rolling cooldown on the union of both selected row
sets. A completed disjoint iteration advances the window; any real row/dimension
reduction releases the cooldown. Demotions, fabricated transitions or row lists,
Boolean-as-integer fields, malformed hashes, reset/truncated history, unknown fields,
snapshot disagreement, or the 32-attempt retention limit fail closed. The policy
never invents progress and does not treat a verdict as debt reduction.

### Investment 11 — expected-value scheduler rank

`tools/phase4_scheduler_policy.py` replaces the old total-points ordering with an
integer benefit/cost rank. Benefit exposes dependency unlock, candidate reducible
dimensions, retained evidence, static ownership, independent controls, and bounded
frontier readiness. Cost exposes the current lane base, all remaining nine-dimension
leaves, and prior overlapping no-reduction attempts. Ratios are compared by exact
integer arithmetic; the stored per-1000 value is display-only, so no float rounding
controls selection.

Candidate reducibility is deliberately weaker than promotion: it lists only unmet
dimensions whose required static/offline/durability surface is presently available.
It never changes a leaf, claims a probability, authorizes live work, or certifies
closure. The complete 107-row queue binds the reviewed policy and helper hashes, emits
all component inputs, and reranks every coherent candidate batch deterministically.
Historical no-reduction overlap remains visible as cost after cooldown release, so an
expensive method is not instantly forgotten merely because another batch progressed.

### Investment 12 — weighted breadth-fixture cover

Every candidate batch now contains a deterministic weighted greedy set cover over its
verified movie/start-state anchors. Mandatory requirements include every selected row
and family; retained capsule anchors additionally require each row's registers, RAM,
VRAM, SPU RAM, block-flow, full-state-checkpoint, and independent-control requirements.
Fixture cost includes a fixed setup unit, declared frame extent, and a penalty when no
retained capsule exists. A single current centrally pinned fixture can cover multiple
rows only when those rows independently name that exact anchor.

The generated cover records the complete weighted universe, each greedy choice and
newly covered requirement, exact current movie/save hashes, capsule manifest/tree
identity, verified per-domain evidence, total cost, and an empty uncovered set. A
same-path movie with a different save/capsule/control identity is rejected rather than
merged, and missing control/domain evidence stays in the uncovered universe. It is a
work-minimization plan—not
behavioral breadth proof. A missing pin, stale bytes, invalid capsule/control, or
uncovered requirement invalidates the queue before a packet is issued.

All three scheduler features are emulator-neutral and operate on retained hashes,
machine debt, and offline metadata. This tranche launches neither DuckStation nor
PCSX-Redux. If a selected packet later names genuinely missing live causality, the
existing isolated DuckStation rules still apply, including Interpreter execution for
movie playback.

## Operating changes

### Integration and ownership

- Never clean or reset the operator checkout. Inventory operator WIP separately from
  generated, external, copyrighted, and commit-eligible work.
- One integration owner edits central Phase-4 registries and regenerates joined
  artifacts once after low-level source/schema changes stabilize.
- Contributors own disjoint semantic lanes. Generated central files are regenerated,
  not hand-merged.
- A fresh verifier starts from the exact integrated commit in a detached worktree.

### Scheduler operation

The movie-ready scheduler now applies the reviewed two-no-reduction cooldown, exact
integer expected-value rank, and weighted fixture cover. These remain generated,
mutation-guarded work-order policies; they cannot be bypassed ad hoc, promote debt, or
authorize a live run. Hard-truth Round 8 accepted the fourth tranche, and the exact
decision is banked in the dedicated marker above.

### Avoided approaches

- Do not start broad live replay or universal capsule capture while static work
  dominates the debt ledger.
- Do not use a frame-boundary capsule as every-cycle or exact-writer evidence.
- Do not use broad symbolic execution over PS1 device behavior; restrict bounded
  reasoning to pure/static functions.
- Do not make GhidraMCP, a graph database, wholesale Splat migration, or hosted
  decompilation uploads prerequisites.
- Do not upload retail-derived assembly or other copyrighted sources to hosted tools.
- Do not lower the nine-dimension gate or let the linter self-certify promotion.

## Hard-truth implementation contract

Implementation proceeds in an isolated branch through an implementer-to-fresh-
verifier ratchet. Every candidate is committed, tested, and clean. Every verifier uses
a new detached checkout, re-provisions declared external inputs, independently
regenerates the indexes, performs mutations, checks the three pilots, and remains
read-only. Rejection returns exact gaps to the next implementer. The ratchet never
merges or pushes.

Acceptance requires:

1. complete current census coverage with no duplicate/silent omission;
2. two fresh Ghidra/static exports producing byte-identical normalized results;
3. exact E15 benchmark recovery or independently accepted address-level differences;
4. bounded, non-promoting E08 and C13 application reports;
5. promotion packets that accept valid retained claims and reject all declared
   mutations with stable codes;
6. pristine identities, external dependencies, and toolchain versions pinned;
7. green scoped acceleration, vault, generated-artifact, and clean-checkout
   validation, plus no candidate-only failure in an immutable-seed differential of
   the broader safe suite;
8. no copyrighted/raw analysis payload committed; and
9. an independent verifier decision with no gaps or required input.

## Efficiency measures and reassessment

Retain the accepted six-iteration method gate:

- at least three distinct retained row/dimension reductions;
- at least four gap-free first verifier decisions;
- zero unplanned live runs and duplicate investigator experiment keys;
- every precise window smaller than its passive/cold-boot prelude;
- complete knowledge joins for accepted increments; and
- at most one repair-only tested iteration.

Measure the new tooling separately:

- percentage of static rows with machine-generated bounded frontiers;
- unclassified indirects/intersections per row;
- median time from selected debt leaf to accepted reduction;
- replay and precise-observer frames per accepted reduction;
- first-pass verifier acceptance and gap categories;
- overlay functions indexed, clustered, typed, and semantically bounded;
- downstream artifacts invalidated per semantic change; and
- semantic-source/generator work versus joined-hash/prose-only repair.

If six real iterations do not improve retained promotion yield and first-pass verifier
acceptance, change the tool/method rather than weakening closure requirements.

## First-tranche implementation receipt

The isolated candidate implements all three immediate investments:

- `tools/phase4_static_frontier.py` indexes all 1,190 canonical records: 998
  resident records, 900 resident code records, 158 overlay code functions, and 78
  explicit data records. All 21 indexed resident/overlay images match the central
  staged-input pins; no duplicate key, overlap, fatal analysis error, or automatic
  semantic-owner promotion remains. The configured `$gp` is independently reconciled
  against both segment maps; reachable-CFG analysis resolves 854 `$gp`-relative
  accesses and 1,706 memory-access instances join declared typed state. Records retain
  explicit blocks, branches, successors, terminators, and delay-slot addresses.
  Constants are
  intersected at control-flow joins, unreachable instructions cannot supply facts,
  and caller-saved constants are invalidated after calls.
- `analysis/phase4_overlay_semantic_index.json` keeps all same-VA overlay identities
  distinct, records the Region-A four-byte header rule, indexes 20 overlay images,
  retains six exact and thirteen structural multi-image candidate clusters, and binds
  FMV as one separate Region-B lifetime with its own verified identity.
- `ghidra/scripts/ExportPhase4StaticFrontier.java` and
  `tools/phase4_ghidra_export.py` ran two fresh disposable full-corpus exports with the
  pinned Ghidra 12.1.2 Flatpak commit. All 21 images and 1,190 records reproduced
  byte-identically: 1,108 high-p-code records, four explicit instruction-fallback
  records, and 78 non-code records. The roughly 30.7 MiB per-run normalized-p-code
  exports, projects,
  specs, and logs remain external; Git retains only their bounded hash receipt. The
  comparison rereads every raw file, verifies its hash/size/schema/image/`$gp`, joins
  all function identities to the canonical index, recomputes status summaries, and
  rejects manifest-only forgeries.
- `analysis/phase4_static_frontier_pilots.json` reproduces E15 at 30 Region-B rows,
  99 exact xrefs, and 58 player xrefs; joins E08 at 28 uncontrolled classes, all 40
  selectors, ten callbacks, and five priority slices; and binds all six C13 declared
  slices, both state roots, the exact unsigned-reader/writer contract, and all three
  open residual classes. E08 and C13 retain zero automatic promotions.
- E08 and C13 now expose root-directed, unbounded-depth direct-call/tail-jump
  frontiers. Every excluded edge has an explicit owner and reason; indirect edges
  remain named unresolved boundaries. `--query-target` returns a bounded target
  frontier without changing retained claims.
- `tools/phase4_promotion_preflight.py` returns `ready_for_fresh_verifier` for the
  retained E15 complete-frontier and E08 original-oracle controls. It correctly
  returns `not_ready` for C13 complete-frontier promotion because the registry claim
  and knowledge binding are absent and residuals still intersect. Mutation tests
  cover stale debt, fake success, frontier/class/xref drift, writer and signedness
  drift, untracked/missing dependencies, missing knowledge, intersecting residuals,
  and external hash drift.

### First hard-truth rejection and repairs

The first detached hard-truth run rejected candidate commit
`49bffdd26e8e7fb9a2a8c220f154789070dc68b1`; it was not banked. Its adversarial
mutations proved seven gaps: unreachable/call-clobbered constants could leak into
static facts; census header/type/size/count/lifetime guards were incomplete; target
frontiers were not transitive/queryable; E15/E08/C13 pilots could fail open under
provenance mutations; promotion policy and nested success fields could be forged;
Ghidra comparison trusted manifests without raw evidence; and the broad safe suite
was already red at the immutable seed.

The repair round added reachable CFG dataflow with intersection joins and ABI call
clobbers; exact census/type/extent/Region-A ordinal/lifetime guards; provenance joins
for every pilot; transitive queryable frontiers; recursively rejected verdict-like
booleans; hash-pinned canonical policy/layer obligations; and full raw-evidence
revalidation. Stable mutations reproduce every former fail-open. Two new full Ghidra
runs, `repaired-v2-full-a` and `repaired-v2-full-b`, each validate all 21 images and 1,190
records with empty run-error lists and byte-identical raw outputs.

The safe-suite claim is intentionally scoped, not relabeled green. Acceleration,
vault, inventory, generated-artifact, and clean-checkout checks must pass; the broad
suite must have no candidate-only failure relative to immutable seed
`dbab87c1c2bfe87ae2cb7ffe222ee2b87f745f8b`. Existing DuckStation external-debugger
identity drift and pre-existing absolute-home-path portability failures are inherited,
non-intersecting facts. This tranche neither edits nor expands their method universe.

A second detached audit rejected commit
`987be7b06148d97a18c86591bc430b5cb1eda28c` before banking. The new inventory changed
the retained fixture-audit hash, while the offline opportunity queue still pinned the
seed hash; its clean-checkout dependency test therefore failed. The repair follows the
declared dependency chain rather than suppressing the check: regenerate the offline
queue, closure debt, live-escalation ledger, movie-priority queue, promotion preflight,
campaign inventory, and Phase-4 gate, then submit the resulting exact commit to a
fresh audit. That regeneration changes hashes and scheduling metadata only; it does
not change a campaign claim, closure state, emulator method, runtime fixture, or
DuckStation artifact.

The third audit rejected commit
`0e5655692ad6da30889a81cfd7b66b3063d3d47d` because the Phase-4 gate had been
generated while the preceding dependency repair was still dirty and therefore
retained those temporary mutations. Regenerating the gate from its clean committed
parent removes every tracked-input mutation and makes the retained gate equal a clean
`phase4_gate.build()`.

The fourth audit then rejected commit
`4c03f08c67d87582e51070fca61e08bc1e8c179c`: the comparison rehashed existing raw
files, but two coordinated forged trees could label all 1,190 code/data/thunk records
`not_applicable` and omit the p-code payload fields. The strengthened validator now
requires exact canonical names and range/status compatibility, pins the expected
code/thunk/data status census, validates high-p-code counts and SHA-256 fingerprints,
validates call/memory-op list shape, and requires explicit bounded fallback reasons.
The exact rehashed-content forgery is retained as a negative test. These are receipt
integrity rules only; they do not add emulator execution or change runtime evidence.

The fifth audit rejected commit
`724896a4211383adfad533fe8dde92c558de7e4c` after constructing a more plausible
census-perfect forgery: range-compatible statuses and syntactically valid but invented
p-code counts/fingerprints. The complete normalized p-code operation list is therefore
retained in each external raw record. Comparison independently recomputes every
operation count, fingerprint, call projection, and memory-operation projection, then
checks a pinned aggregate of all 1,190 canonical raw-record hashes. Two new full runs,
`normalized-pcode-full-a` and `normalized-pcode-full-b`, independently produced the
same 1,190-record contract SHA-256
`a7a7911bb2272ad36742511408195ee778f5dc9cec43c30b1633ce581b04e9f6`.
The normalized p-code stays external; Git retains only its exporter, validation rules,
aggregate hash, bounded receipt, and adversarial tests.

This first-tranche receipt was accepted by the banked hard-truth marker above. It did
not change any Phase-4 row or dimension.

## Second-tranche candidate implementation receipt

The isolated next-three candidate implements the three P2 investments selected for
this tranche:

- `analysis/phase4_evidence_dag.json` retains a six-node, ten-edge bounded control-
  plane graph with exact and semantic identity for every declared input/output. Its
  tracked graph contains zero live nodes. The runner supports static-by-default
  planning, explicit local/live authorization, tree identities, conservative planning,
  and dynamic downstream pruning after semantic no-ops.
- `analysis/phase4_movie_minimizer_pilot.json` is explicitly synthetic and non-runtime.
  It reduces twelve frames to two required input frames, retains both required signals,
  and removes the irrelevant signal. Production receipt validation makes DuckStation,
  recreated isolation, verified media/runtime identity, assertion/control replay,
  anchor preservation, owned cleanup, and three independent `Interpreter` checks
  mandatory.
- `analysis/phase4_mips_oracle_pilot.json` uses pinned Unicorn 2.1.4 MIPS32LE. Four
  synthetic routines generate 21 passing cases covering masking, signed comparison,
  32-bit wrapping increment, and RAM-local load/store. Static and dynamic mutation
  guards reject GTE/COP0/syscall, forbidden classes, MMIO, self-modification, undeclared
  memory, control escape, and instruction exhaustion. A deliberately wrong model
  produces and shrinks a counterexample.
- `tools/requirements.txt` pins the new Unicorn dependency. The three generators,
  three configs, three retained artifacts, four focused test modules, and bank-only
  tool are declared in the Phase-4 inventory.
- No DuckStation process was launched, no existing movie/scenario/fixture/evidence was
  edited, no DuckStation fork or API path was changed, and no PCSX-Redux dependency or
  path was introduced. All retained code and movies in these pilots are synthetic.

The second-tranche acceptance contract is
`engineering-specs/phase4-acceleration-next3-ratchet.md`. The banked next-three marker
above accepted this exact tranche. It cannot promote a row, dimension, source match,
or behavior claim.

## Third-tranche candidate implementation receipt

The isolated third-three candidate implements the remaining selected acceleration
investments without emulator work:

- `analysis/phase4_trace_warehouse_pilot.json` runs DuckDB 1.5.5 with extension
  loading disabled and reproduces first-change, cohort-contrast, block-enrichment,
  and distinct-movie cross-movie queries over eight synthetic events. Production
  writes only an external database and Parquet set after exact policy,
  capsule/import/partition, exact-complete retained-movie binding, canonical-path, and
  physical-file validation. A missing or unexpected retained movie fails with sorted
  identities before an output directory is created.
- `analysis/phase4_binary_schema_fuzz_pilot.json` pins three CC0 read-only Kaitai
  schemas, deterministic seed and mutation order, exact authority booleans, and all
  five resource limits, then replays 285 synthetic mutations twice. The retained run
  reports zero crashes, timeouts, output-limit escapes, and nondeterministic cases.
- `analysis/phase4_external_evidence_manifest.json` is a path-free, hash-only registry
  of 178 required objects totaling 4,503,245,017 declared bytes. It correctly reports
  zero objects replicated and `preservation_ready: false`; availability cannot be
  authored without external receipts for two independent failure domains.
- `analysis/phase4_external_evidence_pilot.json` proves same-device directories do
  not count independently, exercises distinct verified-device grouping, and rejects
  aliases, hard links, tamper, public-remote, and symlink cases using synthetic bytes.
  Its private git-annex plan performs no initialization, transfer, or publication.
- DuckDB is the only new runtime dependency. No DuckStation process, method, source,
  configuration, fixture, movie, save, capsule, or real external-evidence byte was
  launched, modified, or copied. No PCSX-Redux path or dependency was introduced.

The third-tranche acceptance contract is
`engineering-specs/phase4-acceleration-third3-ratchet.md`. This receipt remains a
candidate until the pending third-three marker is replaced by the bank-only tool. The
bank accepts no evidence-free verdict: it binds the exact accepted parent, a real
RFC3339 verification time, retained-artifact hashes, isolation and pinned-environment
facts (including Python exactly 3.14.5), the complete focused/integration and
all-prior-round regression checks through an ordered, exact test-node catalog, and a zero-
candidate-only-failure parent differential through an exact typed JSON contract.
Immediately before writing, it also requires exact reviewed `HEAD`, proves accepted-
parent ancestry, and rejects staged, unstaged, or non-ignored untracked worktree state.

## Fourth-tranche accepted implementation receipt

The isolated scheduler candidate retains 107 queue rows, 30 eligible rows, 29
selectable rows, and 12 coherent candidate batches. Its first detached hard-truth run
rejected the implementation with six concrete exploits: resettable history,
snapshot-free fabricated progress, same-path capsule aliasing, omitted mandatory
domain/control requirements, Boolean numeric normalization, and a bank whose reviewed
commit could be selected by decision content. No rejection was waived.

The repaired candidate answers those findings with packet schema v3 and a
genesis-anchored exact-entry chain; exact prior queue/packet/progress/debt snapshot
propagation through normal continuation and automatic reseed; one shared, independently
recomputed progress function; strict integer inputs; exact movie/save/capsule identity
alias rejection; mandatory six-domain-plus-control universes whose missing evidence
stays uncovered; and an external `--reviewed-commit` bank authority. The bank also
pins current queue/gate/DAG hashes and counts, the complete mutation-node catalog, and
exact integration commands. It cannot write the pending marker from a self-selected
commit or evidence-free decision.

The second detached hard-truth run rejected `ffcbcc2fec7e` with six further
trust-boundary exploits: manifest-only capsules inheriting unverified payload-tree
claims; noncanonical or count-inconsistent 107-row progress ledgers; Boolean readiness
collections on eligible and ineligible queue rows; capsule availability disappearing
from the mandatory cover universe; forged batch rank/expected-value/score/coupling in
a coordinated prior queue and packet; and continuation/reseed silently returning to a
genesis packet when all five snapshots were absent. No Round-2 finding was waived.

The next repair hashes every manifest-declared capsule payload and exact tree before
crediting domains or control; requires the canonical row IDs, exact debt-row schema,
and re-derived row/top counts; strictly validates all readiness collections and their
anchor equivalence; independently regenerates every row rank and complete batch; and
makes a missing normal-continuation or automatic-reseed snapshot terminal. The
hard-truth mutation catalog names each Round-1 and Round-2 exploit explicitly.

The third detached hard-truth run rejected `db4cd877e3b2` with three remaining
trust-boundary failures. A coordinated, internally consistent score/expected-value/
rank/batch rewrite could keep every claimed input hash while changing the queue;
continuity-hashed summaries for nonexistent older attempts could influence cooldown
when only the latest five snapshots were replayed; and a positive capsule-tree cache
entry could keep all six domains and independent-control credit after a payload file
disappeared. No Round-3 finding was waived. The verifier independently reproduced all
three, ran the 521-test acceleration catalog, verified all 1,362 declared inputs,
reported build identity 327/327 and clean DAG/gate/vault/forbidden checks, and emitted
no acceptance artifact.

The Round-3 repair moves the packet to schema v4. A queue is accepted only when it is
both internally reproducible and byte-identical to authoritative generation from the
current source documents and capsule payload state. Every retained attempt now binds
deterministically compressed exact copies of its queue, progress, debt-before, and
debt-after evidence; uncached prefixes are fully replayed, while a validated-prefix
cache is usable only under the same complete runtime source/tree fingerprint. This
preserves the 32-entry fail-closed capacity without hash-only history or quadratic
replay cost. Capsule payload trees are rehashed on every observation, so positive
credit cannot survive in-process deletion or drift. The bank mutation catalog names
the three Round-3 falsifiers explicitly.

The fourth detached hard-truth run rejected `4808624ddb96` after its 75-test focused
set and 524-test acceleration catalog passed. It found that the queue-cache runtime
fingerprint omitted external derived-index payload files, allowing previously cached
readiness to survive deletion, and that every historical queue was incorrectly
revalidated against the current debt-derived source state. The latter made a genuine
debt reduction unable to advance to its newly generated queue, so the cooldown-release
test had covered only a transient unchanged-source simulation. No Round-4 finding was
waived. Its symmetric safe-suite differential reported 77 inherited failures and 12
candidate-only failures, ten of which exercised that historical-queue defect. It
emitted no acceptance artifact.

The Round-4 repair moves the movie-priority queue to schema v2 and embeds
deterministically compressed raw bytes for its exact ten policy/data sources. The
active queue must reproduce from source snapshots that byte-match the current files;
each historical queue reproduces from its own bound snapshot, so a real debt change
can produce a different valid active queue without erasing old provenance. Runtime
cache identity now includes every referenced movie/start-state file, capsule tree, and
external derived-index payload. The retained-history cache combines those per-queue
runtime identities, and the Round-4 release/payload falsifiers are mandatory bank
mutations.

The fifth detached hard-truth run rejected `b36bf1836f95` with one exact leak after
77/77 focused tests and both Round-4 replays passed. Queue construction embedded all
ten historical sources, but each row's static-ownership identity still read the
current ownership path. A valid ownership A queue therefore stopped reproducing after
a valid ownership B queue became current. No finding was waived, and the verifier
correctly stopped the broad catalog/differential after the terminal rejection. The
repair derives row-level ownership provenance from the bound raw ownership bytes and
adds an A-to-B source-change continuation falsifier to the mandatory bank catalog.

The sixth detached hard-truth run rejected `95e95295a21a` with three repository-level
integration defects after the focused 78-test set, 527-test acceleration catalog,
42-test mutation replay, all nine declared integrations, source/history/runtime
adversarial probes, and the 32-attempt capacity run passed. The retained live-
escalation ledger still named the prior offline-queue hash; promotion preflight still
pinned the prior closure-debt hash; and the inherited Phase-3 ownership freshness test
left its deliberately regenerated tracked file in the shared checkout after failing.
That last side effect caused 15 candidate-only safe-suite failures even though a clean
individual scheduler run passed. No finding was waived. The repair rebinds both
generated ledgers and their inventory/gate/DAG consumers, updates the reviewed debt
pin, and makes the freshness test transactional: it restores the exact original bytes
in `finally` while preserving the honest stale-artifact failure.

The seventh detached hard-truth run rejected `7ad45eb494c8` with two banking defects.
First, the retained Phase-4 gate had been generated while six implementation paths
were dirty, so a clean exact checkout recomputed an empty mutation list and failed the
byte-exact gate check. The gate is now generated and committed from a clean tracked
state before its evidence-DAG identity is refreshed. Second, the candidate repaired
four inherited safe-suite failures, but the bank incorrectly demanded identical
candidate/parent failed-node hashes and no parent-only failures. The reviewed
specification requires zero candidate-only failures, not reintroduction of parent
defects. The bank now accepts a strictly validated parent-only improvement list while
still rejecting every candidate-only failure, malformed node list, inconsistent set-
equality flag, hash relation, or failure count.

The fourth-tranche acceptance contract is
`engineering-specs/phase4-acceleration-scheduler-ratchet.md`. Hard-truth Round 8
accepted exact commit `151a5a3bbf07186126a54070e5b2ddc401396e04`; the bank validated
and replaced the pending marker with decision SHA-256
`831064e0c81c3f80855cecab771f17a0686b8a7d7e6159abb19c331d3cb74503`.
This work launched neither DuckStation nor PCSX-Redux and did not edit any emulator,
movie, save, capsule, or historical evidence. Future movie execution remains
Interpreter-only.

## Confidence, residuals, and supersession

**Confidence: high for accepted investments 1-12.**

Residuals:

- Ghidra recovery is an independent analysis signal, not behavioral authority.
- Indirect calls, aliasing, dynamic record bases, and overlay lifetime can remain open
  even when p-code is available.
- The E15/E08/C13 pilots prove production readiness and boundaries, not all-row
  semantic coverage.
- The bounded DAG is not yet a complete graph of every Phase-4 generator.
- The minimizer pilot proves its algorithm/receipt contract, not live replay reduction.
- The MIPS pilot is not native-device, timing, or behavioral evidence.
- The warehouse pilot has not imported the 55 real capsules.
- The read-only schemas cover three stable formats; they do not replace existing
  writers or prove every asset parser safe.
- The external registry has no real availability receipts, so none of its 178 objects
  is yet claimed independently replicated by this tooling tranche.
- The expected-value score is a deterministic work-order heuristic, not an empirical
  probability of promotion; its weights should be reassessed against retained yield.
- Weighted fixture cover minimizes the declared batch universe; it does not prove
  unrecorded stage, lifecycle, or subject breadth.

Supersede this note only with a newer evidence-backed playbook that preserves the
accepted verifier receipt, records the changed repository/toolchain identities, and
explains which measured result falsified or outgrew this strategy.
