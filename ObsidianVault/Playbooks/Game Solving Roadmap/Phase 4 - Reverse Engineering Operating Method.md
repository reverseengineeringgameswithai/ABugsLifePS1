---
kind: playbook
id: PLAYBOOK_phase4_reverse_engineering_operating_method
name: Phase 4 - Reverse Engineering Operating Method
aliases: [Playbook - Replay headline experiments]
status: accepted
methodology_ratchet: verified
created: 2026-07-25
updated: 2026-07-26
confidence: medium
parent: PLAYBOOK_game_solving_phase_4
depends_on:
  - PLAYBOOK_game_solving_roadmap
  - PLAYBOOK_game_solving_phase_4
---

# Phase 4 - Reverse Engineering Operating Method

**Navigation:** [[Phase 4 - Solve Every Gameplay and Engine Subsystem|Phase 4 execution note]] · [[Game Solving Roadmap - From Reconstruction to Reliable Modding|Roadmap hub]]

<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_START -->
### Independent hard-truth acceptance

- **Status:** accepted
- **Verified:** 2026-07-25T23:06:50-04:00
- **Ratchet run:** `phase4-method-20260725-205442-43739`
- **Reviewed candidate:** `580340bc1469bbdb0dc32f94b7db4b3807fb55cd`
- **Verifier decision SHA-256:** `ed80ecd796ff86c8b4b98297b9cdeab65e8db7124faebe91d53a39ebe83226c0`

**Verifier conclusion:** Accepted as the best-supported efficient Phase 4 operating method under current evidence. It makes independently verified architectural debt reduction—not replay, prose, commits, or green counters—the unit of progress. This accepts the methodology only; it neither closes Phase 4 nor approves a trial before the declared v2 metrics tooling and stale-seed repairs pass fresh verification.

**Evidence independently inspected**

- The closure ledger deterministically reports 16/107 complete rows and 148 met dimensions, selecting fmv_playback/E15_fmv; mutating the reviewed focus order predictably selected safe_respawn_anchor, while mutating the authoritative dimension order invalidated the ledger.
- Representative pristine C, documentation-grade src_re C, hash-pinned external ASM, symbols, typed FMV schema, registries, generators, tests, Canon, Experiments, fixture manifests, and retained E15 artifacts support the proposed offline-localization/static-reconstruction/targeted-live/banking funnel.
- A pristine FMV opcode mutation at the selector upper-bound instruction was rejected by the static owner generator; truncation, writer-drift, observer-desynchronization, cleanup, and control mutations were also rejected by focused E15 guards.
- All 55 retained capsules are control-matched frame-boundary evidence totaling 70,589 frames and 3,391,058,326 external bytes; nine derived indexes cover 34 rows. The method correctly forbids treating these as every-cycle causality or subsystem closure.
- Retained history independently supports the bottleneck diagnosis: 16 progress receipts produced five promotion events, eleven no-reduction iterations, net four met leaves, zero row closures, and only four gap-free decisions among fourteen; 21 controller timeouts support the bounded outage circuit.
- Current DuckStation documentation and C++ implementations confirm serialized 1–128-job batches, process-local resume, recipe observer limits, state-load instrumentation invalidation, traceToFrame clearing/control behavior, atomic capture, provenance domains, and capsule limitations. No invented capability was found.
- The round-4 metrics contract closes the prior anti-gaming gaps by deriving promotions, classifications, joins, replay identity, and totals from chained hash-bound artifacts, typed bounds and controls, Git diffs, and fresh verifier decisions. The explicitly unbanked validator remains a mandatory pretrial implementation gate, not presumed evidence.
- The disclosed 74/75 generator-inventory mismatch and stale offline queue reproduce as seed defects. The method requires stopping and repairing them before selection; it does not silently treat the stale state as valid evidence.

**Validation and falsification attempts**

- `PYTHONPATH=. pytest -q tests/test_phase4_closure_debt.py tests/test_phase4_derived_index.py tests/test_phase4_duckstation_batch.py tests/test_phase4_trace_capsule_contract.py tests/test_vault_consistency.py`: 36 passed.
- `PYTHONPATH=. pytest -q tests/test_phase4_fmv_lose_lifecycle.py tests/test_phase4_fmv_natural_exit_cause.py`: 15 passed, including truncation and control falsifiers.
- `python3 tools/validate_vault.py --check`: zero dangling links, evidence-policy failures, dead evidence files, duplicate addresses, missing aliases, or schema errors; the parameterized vault suite separately passed 9 tests.
- Closure-debt, derived-index, live-escalation, and DuckStation RPC-manifest checks passed; the RPC manifest contains 207 methods at fe0cca16b85e09a304cfde3c39669ce8c0adb8f5 with 95 hash-pinned dirty paths.
- `sha256sum -c ../duckstation-surface.sha256`: all ten pinned DuckStation documentation, source, DMA, and executable identities passed.
- Candidate structure, pending verdict marker, reciprocal Phase 4 link, write-boundary history, `git diff --check`, required HEAD, and final clean worktree were verified.
- DuckStation was not launched because source, retained artifacts, offline data, and disposable mutations answered every methodology claim tested.

This receipt accepts the operating method only. It does not close Phase 4 or promote
any gameplay finding.
<!-- PHASE4_METHODOLOGY_RATCHET_VERDICT_END -->

## Decision

Use a **closure-debt-scheduled, campaign-local closure funnel**:

1. let the generated nine-dimension debt ledger select one campaign;
2. reuse a valid derived index or capsule for localization and mathematics;
3. reconstruct the static ownership, interface, state, and source frontier;
4. run one predeclared, same-anchor live control only for the precise fact still
   absent;
5. bank the result in machine layers before prose; and
6. have a fresh agent attack every promotion from a clean checkout.

The closure ratchet remains the scheduler, checkpoint enforcer, and adversarial
verifier. It is not the default primary investigator. This is a candidate operating
method, not a verified optimum and not a Phase 4 implementation or closure decision.

## Authority, scope, and non-scope

This note is subordinate to `AGENTS.md`,
[[Game Solving Roadmap - From Reconstruction to Reliable Modding]], and
[[Phase 4 - Solve Every Gameplay and Engine Subsystem]]. Those sources retain the
authoritative nine-dimension subsystem Definition of Done, eight-part reusable-finding
Definition of Finished, work packages, phase gate, and pristine-media policy.

This method governs how a future agent selects, investigates, proves, banks, checks,
and integrates Phase 4 work. It may not:

- promote a row or dimension merely because an artifact, note, or green summary exists;
- weaken lifecycle, capacity, reset, transition, breadth, source, or cross-system
  requirements;
- treat ALLMODS, a derivative disc, a filename, a screenshot, or a save-state endpoint
  as original-game behavioral authority;
- turn a frame-boundary capsule into an every-cycle or campaign-closure claim; or
- change a behavioral expectation through a dependency reconciler.

Only the hash-verified pristine SCUS-94288 retail image is the behavioral oracle. This
note does not close a Phase 4 row, dimension, campaign, work package, or gate.

## Audited basis

The advisory inspected the following exact current surfaces at candidate seed
`824a886562d8b2354a0a8c10493786f62138deaa`.

### Roadmap, registries, and generated control plane

- The roadmap hub and the complete Phase 4 execution note, including the strict
  subsystem and reusable-finding definitions.
- `analysis/mechanics_baseline.yaml`: all 107 `A01` through `F18` rows, their status,
  evidence, bindings, fixtures, missing facts, and next actions.
- `config/phase4_campaigns.yaml`, `config/phase4_closure_policy.yaml`,
  `analysis/phase4_campaign_inventory.json`,
  `analysis/phase4_coverage_matrix.json`, and
  `analysis/phase4_closure_debt.json`.
- `analysis/phase4_offline_opportunity_queue.json`,
  `analysis/phase4_derived_index.json`, and
  `analysis/phase4_live_escalations.json`.
- `tools/phase4_closure_debt.py`, `tools/phase4_offline_queue.py`,
  `tools/phase4_derived_index.py`, `tools/phase4_inventory.py`,
  `tools/phase4_duckstation_batch.py`, and their focused tests.

The retained debt ledger passes its own `--check`, but an ordered freshness audit
exposed three related interrupted-seed defects. First, the source tree contains new
generator `tools/phase4_fmv_levelb_first_call_live.py`, while the inventory declaration
and committed inventory still report 74 generators rather than the 75 now discovered.
Second, the committed offline queue pins the prior
`config/phase4_live_escalations.yaml` hash and omits planned escalation
`P4-ITER89-E15-LEVELB-FIRST-CALL-LIFECYCLE` from the E15 ledger IDs, even though the
live-escalation generator passes with 14 entries: 13 executed and that one planned.
Third, the focused test
`test_live_ledger_is_generated_and_retains_executed_missing_capsule_runs` hard-codes
the former 13-ID set and rejects the actual ledger solely because the new planned ID
is present. The provisioned focused suite therefore reports 94 passes and this one
failure. A disposable ordered regeneration after refreshing the low-level inputs
preserves the semantic selection: 16 of 107 rows complete or reviewed absent, 91 open,
and 148 met, 46 partial, and 769 gap row-dimension states. Open rows route to 88
static, two offline, and one live lane. The only selected campaign remains
`fmv_playback` / `E15_fmv`, with four dimensions met and five remaining. Its binding
next fact remains the first natural `0x8005031C` call and a bounded
instruction-attributed selector-11/limit-485/completion/teardown control.

The advisory write boundary forbids repairing those control-plane artifacts. A future
implementation must declare the new generator, make the live-ledger test derive or
accept the complete declared set, regenerate the inventory, queue, derived index, and
debt in the required order, and require every freshness and focused check before
relying on the selection. The recomputed numbers above diagnose the method; they are
not evidence that the phase is close to done.

### Authoritative code and knowledge layers

Representative inspection covered:

- the matching resident loader `src/main/8003e7c0_fmv_bin_load.c`;
- documentation-grade, explicitly non-matching
  `src_re/fmv_selector_dispatch.c`, `src_re/fmv_player_streaming.c`, and
  `src_re/fmv_callback_consumer_frontier.c`;
- high-centrality open-family references
  `src_re/player_health.c`, `src_re/player_bottomless_fall_800497f4.c`, and
  `src_re/prop_decor_catalog.c`;
- `symbols/re_symbols.sym`, `config/segments.yml`, and
  `tools/repro_inputs.sha256`;
- typed and ownership schemas including `config/phase4_fmv.yaml`,
  `config/record_types.yaml`, and `config/semantic_state.yaml`;
- the campaign and findings registries plus representative static, offline, live,
  reconciliation, mutation, knowledge-closure, and vault tests; and
- [[SYS_fmv_player_streaming]], [[EXP_2026-07-18_phase4_trace_capsules]],
  [[EXP_2026-07-19_phase4_closure_funnel]],
  [[EXP_2026-07-24_phase4_fmv_levelb_reachability]], and
  [[EXP_2026-07-19_phase4_fmv_static_owners]].

The representative open-family audit also exposed why semantic C is an input rather
than a completion signal. `src_re/player_health.c` joins C16 health/lives facts but
does not close scripted/exceptional death, card, or frontend behavior;
`src_re/player_bottomless_fall_800497f4.c` is an explicitly documentation-grade slice
inside a larger function and leaves the C15 multi-overlay selector/reset policy open;
and `src_re/prop_decor_catalog.c` records useful E08 visual/payload controls while the
current debt ledger still lacks complete ownership, source, lifecycle, persistence,
and 28 native class controls. C15 and C16 therefore each retain all nine dimensions as
partial, while E08 retains five partial and four gap dimensions. These are concrete
warnings against promoting a row from a readable C narrative.

The current source campaign reports 913 resident matching functions and a
byte-identical executable, while semantic/source residuals remain. That is evidence
against treating matching percentage as semantic closure. The tracked tree has no
`asm/` directory; applicable handwritten retail-derived ASM is a declared external
input whose identity is enforced by `tools/repro_inputs.sha256`. A clean checkout must
provision those inputs rather than silently reading an operator worktree.

The layer placement itself is typed. `config/phase4_fmv.yaml` owns 30 resident
Region-B address rows, 99 exact xrefs, 58 player xrefs, six pointer aliases, and zero
unclassified intersections under the FMV residency guard. The global
`config/semantic_state.yaml` owns only the longer-lived FMV boot-buffer bounds at
`0x800814BC..0x80081530`; it does not duplicate every overlay-local field.
`symbols/re_symbols.sym` names `0x8003E7C0` and `0x800502C4`, while the less-semantic
`0x800709AC` label must be reconciled with the byte-matched teardown source rather than
trusted by name. The operating method must preserve these ownership/lifetime
boundaries instead of forcing every fact into one registry.

### Movies, fixtures, and capsules

- `analysis/phase4_movie_inventory.json` inventories the 135 centrally provisioned
  files in the tested checkout, including 78 movies and 56 start states, with zero
  undeclared files. The default generator root is that checkout's logical `movies/`
  tree—not the mutable operator checkout. A filename remains only a lead.
- `analysis/phase4_fixture_audit.json` maps 182 unique fixture references across all
  107 rows: 80 have a Phase 2 pristine trigger and 27 retain a blocker.
- `tools/fixtures.sha256`, `analysis/phase0_2_external_fixture_set.json`,
  `tools/build_baselines.json`, `tools/repro_inputs.sha256`, and
  `analysis/phase4_trace_capsule_set.json` define the external identity and
  preservation boundary.
- The retained capsule set is complete for its declared scope: 55 capsules / 55
  movies, 70,589 frames, and 3,391,058,326 external bytes. Independent controls have
  byte-identical frame-domain chunks. Only five flat checkpoints match across
  profiles; the other checkpoint differences are bounded session/host serialization,
  so frame domains—not flat checkpoint hashes—are the stable offline authority.
- The derived catalog has nine external indexes covering 34 rows, 41 movies, ten
  offline artifacts, and 547,064,945 bytes. The opportunity queue has zero
  `offline_ready`, 42 `offline_partial`, and 65 `no_capsule` rows. It describes
  evidence availability and does not schedule work.

Capsules, checkpoints, saves, movies, source snapshots, runtime bundles, and derived
indexes stay external. Git retains hashes, roles, schemas, bounded results, generators,
guards, and links.

### Retained ratchet history

The two completed retained Phase 4 runs under
`~/.local/state/flik-hard-truth-ratchet/runs` contain 16 successful progress
receipts. Five reported a dimension promotion and eleven reported no debt reduction;
one promotion was later demoted, so the net moved from 144 to 148 met dimensions and
closed zero rows. Fourteen campaign-verifier decisions found 18 gaps in ten decisions;
only four were gap-free. The gaps repeatedly involved overbroad frontier/state claims,
observer non-reproducibility, incomplete mutation guards, undeclared cleanup or ASM
dependencies, stale derived evidence, and knowledge/gate durability.

The second run also contains 21 executor process failures caused by network/transport
timeouts. They are an infrastructure reliability signal, not semantic evidence and not
part of the 16-iteration method-yield denominator. They do make small commits,
idempotent external outputs, and restart receipts necessary.

Git history shows productive static reconstruction, targeted causal controls, and
durability repairs interleaved with repeated replay, gate/date repairs, dependency-pin
cascades, and documentation/link corrections. The strongest result of the current
ratchet has been adversarial rejection. Its productivity as an open-ended investigator
is not established.

At the audited evidence endpoint
`824a886562d8b2354a0a8c10493786f62138deaa` and the explicit committer-date cutoff
`2026-07-14 00:00:00 -0400`, the reproducible counts are 274 commits touching
`analysis/phase4*`, 105 touching the Phase 4 execution note, and 18 touching
`src_re/**`. They are computed respectively with:

```text
git rev-list --count --since='2026-07-14 00:00:00 -0400' 824a886562d8b2354a0a8c10493786f62138deaa -- 'analysis/phase4*'
git rev-list --count --since='2026-07-14 00:00:00 -0400' 824a886562d8b2354a0a8c10493786f62138deaa -- 'ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md'
git rev-list --count --since='2026-07-14 00:00:00 -0400' 824a886562d8b2354a0a8c10493786f62138deaa -- 'src_re/**'
```

The endpoint and UTC offset are normative; a date-only `--since` or moving HEAD is not
the same measurement. The ratio is not proof that any individual generated or
documentation commit was wasteful, but together with the verifier receipts it is an
observed warning: joined-hash, gate, and prose repair can dominate semantic-source
progress when banking starts before the lowest-level claim stabilizes.

### Current DuckStation source and API

The audited local fork is `~/duckstation` at revision
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5` with a 95-path dirty source state
identified by the generated manifest, not by the revision alone. The balanced
`KnownMethods` allow-list contains 207 callable methods: 114 at HEAD plus 93
dirty-only; `debugger.capabilities` reports 208 schemas because it also includes the
connection-level `debugger.authenticate` method. `src/duckstation-qt/debuggerrpc.cpp`
hashes to
`14f9e607f6f0b45fac62602b4be81206335b312997ce122ea7dc8ad29c63380b`;
the pinned release executable hashes to
`91cbe22b2c2e22ad83d695988ada36bbabb22c65366cb5ec9e8e30784de93af6`.
The exact source, docs, clients, executable, and runtime identities are retained in
`analysis/phase3_duckstation_rpc_manifest.json`,
`tools/duckstation_rpc_method_manifest.md`, and [[DuckStation API Index]].

The advisory checked `docs/external-debugger.md`,
`docs/external-debugger-determinism.md`,
`docs/external-debugger-experiment-runner.md`,
`docs/external-debugger-movie.md`,
`docs/external-debugger-scenarios.md`,
`docs/external-debugger-trace-capsules.md`, the client README, and the current C++
implementations in `debuggerrpc.cpp`, `debugger_control_service.cpp`,
`trace_capsule.cpp`, and `input_movie.cpp`.

Relevant implemented behavior and limits are:

- `debugger.capabilities` reports API/schema, complete method schemas, source state,
  executable path, and executable SHA-256. A live run must compare it to the declared
  identity, not merely observe that the method exists.
- `scenario.loadStateAndRun` and `scenario.bootAndRun` pause while establishing the
  anchor, checking media, starting a movie, and arming at most 32 allowed observers.
  `scenario.runBatch` accepts 1–128 jobs, but one emulation core serializes them.
  Batch results and resume state are process-local.
- `scenario.runBatch` cannot express every staged experiment. In the current source,
  its movie preparation starts playback with `load_start_state:false`; it cannot put
  `movie.traceToFrame` before precise observers inside one job. A client-driven
  fallback therefore requires a specific predeclared surface gap, not convenience.
- `movie.traceToFrame` clears existing instrumentation and owns two replays from a
  recorded state/from-boot anchor: an uninstrumented cached-interpreter control and
  passive cached-block coverage over 1–16 PC ranges. `comparison.cycle_neutral:false`
  invalidates the result. Its equality signature covers full main RAM, registers,
  cycle, emulator frame, and movie frame—not VRAM, SPU RAM, or every device.
- `capture.atomic` reads CPU/registers, bounded RAM, GPU, movie, SPU, and retained
  traces inside one core-thread closure, so no guest instruction interleaves the
  domains.
- `provenanceLog` unifies CPU, DMA, debugger, and host main-RAM writes.
  `accessLog` alone is not a DMA source oracle. Precise CPU-store attribution,
  `functionTrace`, GPU causality, and reverse execution use the precise interpreter
  observer and can be `cycle_neutral:false`.
- `emulator.loadState` clears non-halting access/exec/history, provenance, transfer,
  function, GPU, SPU, and reverse state. Instrumentation must be armed after every
  load.
- `trace.armWhen` is a synchronous frame-predicate gate that can arm a narrow observer
  after a trigger. It is not one of the arming operations accepted by a scenario
  recipe.
- A trace capsule reconstructs frame-exact registers, RAM, VRAM, and SPU RAM plus
  passive basic-block flow and periodic compatible-runtime checkpoints. It does not
  identify the exact writer instruction, DMA producer, GP0 submission, SPU voice
  event, or every-cycle device state. `complete:false`, `truncated:true`, a nonempty
  error, or an independent-control mismatch rejects it.
- Reverse history is bounded and is invalidated by state load/reset/unload. SPU
  `completed` means emulated voice completion, not host-speaker drain. Full
  checkpoints are compatible-runtime replay aids, not a stable public field schema.

## Bottleneck diagnosis

### Observations

1. Eighty-eight of 91 open rows currently route to static work, while only one routes
   to live work. Sixty-five rows have no retained capsule. A live-first or universal
   capsule campaign contradicts the current evidence distribution.
2. The selected E15 campaign has repeatedly advanced through exact byte/xref/source
   work and narrow controls, but eleven of sixteen retained successful iterations did
   not reduce debt and ten of fourteen fresh verifiers found gaps.
3. Rejections usually occurred at the promotion boundary: a locally plausible fact
   lacked complete ownership, a causal discriminator, a fail-closed mutation, a
   declared external dependency, or a clean knowledge join.
4. Existing derived indexes remove the need to replay 34 rows' covered domains, but a
   capsule cannot answer the precise causal questions now remaining on E15.
5. Central generated artifacts have many joined SHA identities. Updating summaries
   before low-level sources creates pin cascades and repeated repair.
6. Git churn and verifier gaps agree on the same ordering risk: high-level joins are
   repeatedly repaired after the semantic source or dependency boundary changes,
   while only 18 recent commits touched `src_re/**`.

### Inference

The dominant bottleneck is not lack of emulator access or observations. It is
converting a narrowly observed fact into a complete, falsifiable semantic claim without
reopening its source, interface, dependency, or durability boundary. The history ratio
does not by itself prove causality; the repeated verifier reasons supply the independent
link. The most efficient supported method is therefore to localize cheaply, finish
static reconstruction before precise observation, and design the live control and
banking contract together. The ratchet should reject and schedule that work, while a
campaign-local investigator performs it.

This inference is falsifiable through the efficiency measures below. If a six-iteration
trial does not improve verified promotion yield and first-pass verifier acceptance, the
method must be revised.

## Alternatives considered

| Workflow | Support | Failure test and verdict |
|---|---|---|
| Closure ratchet as primary investigator | It enforces clean commits, one-campaign WIP, debt accounting, and fresh attack. | Retained history produced only five promotion events in 16 successful iterations, zero row closures, and verifier gaps in 10/14 decisions. Repeated promotion/repair cycles show that it is strong as scheduler/verifier but inefficient as the default open-ended investigator. Reject as primary; retain as control plane. |
| Local subsystem investigation, then independent ratchet verification | Deep ownership, matching/static work, and campaign context stay coherent; fresh verification caught real overclaims. | Without a mandatory capsule/index check and closure-ledger selection, it can rescan retained evidence, replay too early, or optimize an attractive row outside the active campaign. Accept only inside the chosen hybrid. |
| Capsule-first/offline batch analysis with narrow live escalation | Fifty-five validated capsules and nine derived indexes already support repeatable RAM/VRAM/SPU/register/block-flow mathematics without an emulator. E15 history shows successful passive localization before precise attribution. | It is insufficient as a universal workflow: 65 rows have no capsule, 88 open rows route to static work, and capsules cannot prove exact writer/DMA/GPU/SPU cause or native controls. Accept as the first evidence lane when coverage exists, not as the scheduler or closure oracle. |
| Chosen hybrid: debt-scheduled campaign-local funnel | It combines the scheduler's dependency/WIP policy, offline reuse, static source closure, one bounded causal control, machine-first banking, and an independent attack. | Reject it after trial if it does not meet the reassessment thresholds, causes unplanned replay, or still yields promotion rejections for boundaries the preflight contract should have caught. |

## End-to-end operating workflow

### 1. Establish a clean selection

From the intended base commit:

1. require `git status --short` to be clean or inventory unrelated operator changes;
2. run the capsule preservation check and the offline queue, derived index, closure debt,
   inventory, fixture, and source-identity checks in their documented read-only modes;
3. stop if any input hash, generated identity, row set, or declared external input is
   stale or missing; and
4. select exactly `scheduler.selected_campaigns[0]` from
   `analysis/phase4_closure_debt.json`.

The opportunity queue never schedules work. Do not select the row with the most movie
coverage, the easiest counter, or current MOD demand. The debt generator orders active
campaigns by dependency tier, configured focus, dependency order, remaining
dimensions, dependency unlock count, and stable campaign ID. Change that priority only
through an explicit, reviewed policy change—not an iteration-local preference.
The selected campaign's generated `next_lane` and `next_action` are binding until new
low-level evidence changes and regenerates the ledger.

The normal WIP ceiling is one campaign and at most three rows. Couple two or three rows
only when they share one producer/interface/lifecycle boundary and the same evidence
batch can reduce the same named dimension for each. Otherwise work only the first
selected row. Never open another partial row to escape a difficult selected dimension.

#### Optional `movie-ready` work order

`tools/flik_phase4_method_ratchet.sh --selection-policy movie-ready` is an explicit
alternate scheduling policy; the closure-debt scheduler remains the default. Its
authoritative generated queue is `analysis/phase4_movie_priority_queue.json`, rebuilt
from all 107 closure-debt rows, the current offline queue, central fixture/movie audit,
capsule and derived-index manifests, and the files actually provisioned under the
case-sensitive `movies/Phase4/` tree. It never trusts an authored complete/pass field:
the nine debt leaves are re-derived, and a row is eligible only when its reported
remaining count is positive and agrees, a centrally hash-pinned movie and start state
both verify with eligible pristine media classifications, and no preservation
dependency is missing. Completed A04/A16 therefore cannot re-enter.

The generated score exposes retained capsule/index leverage, typed static ownership,
bounded-frontier quality, controls, remaining debt, and dependency leverage. Movie
quantity contributes zero: a movie is a trigger/evidence anchor, never proof that a
row or dimension is solved. Batches contain at most three rows and require an exact
shared movie, retained index, or active campaign to couple extra rows. `E15_fmv` is
deferred while another eligible movie-backed row exists because its repeated
static/live reassessments just produced no debt reduction. A completed iteration with
no row or dimension reduction rotates to a disjoint packet on the next iteration.
The exhaustive roadmap and every closure criterion remain unchanged.

Every completed `movie-ready` executor iteration receives a fresh independent campaign
verifier, including no-promotion iterations. Structural rejection or verifier gaps are
fed verbatim into the next executor packet; whole-phase closure still requires the
existing final fresh verifier. Every packet and executor/verifier prompt binds the
selected rows, exact movie/start-state hashes, retained capsule/index availability,
score/rationale, and previous attempted packet. The method order remains capsule/index
query, static reconstruction, named and predeclared atomic live escalation only for a
missing domain, then authoritative banking. The historical `C15_checkpoints` ID retains
only safe-respawn-anchor semantics; the game has no player-facing checkpoint mechanic.

### 2. Write the claim and falsifier before collecting evidence

For the first unmet dimension in the closure policy's declared roadmap order—the same
ordered frontier used to derive the selected row's `next_lane`—write a bounded
campaign hypothesis:

- exact row/campaign and dimension;
- observed fact already retained;
- missing fact, owner/interface/state boundary, and non-claims;
- positive and negative control;
- low-level value or edge that must differ;
- evidence limits, saturation/truncation checks, and rejection predicate;
- intended authoritative paths, generator, mutation test, Canon page, Experiment page,
  and future-MOD contract; and
- named residuals with next experiments.

If the proposed result cannot be represented and falsified in those layers, the
experiment is premature.

### 3. Localize offline

Inspect `analysis/phase4_derived_index.json` before reading capsule chunks. Reuse its
exact pinned external index when it covers the movie, row, and domain. Query the pinned
offline reader only for a missing frame/domain question. Good offline questions are:

- when a typed field or register changed;
- the first/last frame of residency or a state transition;
- RAM/VRAM/SPU fingerprints and cross-movie differences;
- block-start counts/order and candidate owner regions; and
- a narrowed positive/negative frame window.

Record commands, input hashes, frame ranges, domain hashes, counts, and
truncation/control status. Offline results may localize or falsify; they may not name an
exact instruction writer or close breadth.

Every counted offline input must be centrally preserved and classified as pristine
authority or derived pristine evidence. Non-pristine images, ALLMODS, and other
derivatives remain comparison evidence only and cannot satisfy an authority-bearing
offline query. Reuse metrics count unique retained input hashes and bytes read; newly
produced outputs are evidence products, not pre-existing external evidence reused.

If no capsule covers the needed oracle, use existing declared movie/state leads to
design a cold-boot or state experiment; do not create a general capsule merely to avoid
the selected static work.

### 4. Reconstruct statically

Before live work, exhaust what pristine binaries, matching source, external pinned ASM,
symbols, schemas, and xrefs can establish:

- exact function/image bounds, entry/exit ABI, direct and computed calls;
- every intersecting reader/writer, callback, transition, and exceptional edge;
- field width, signedness, aliases, domain, capacity, initialization/reset, residency,
  teardown, and owner;
- manifest/table selector coverage and reviewed absence; and
- matching-source status versus documentation-grade semantic C.

Prefer a deterministic generator over an authored list. It must enumerate the
candidate universe first, fail on unclassified entries, pin every source dependency,
and expose a mutation that turns the proposed claim red. Use a symbol only after its
boundary/role is supported. Matching `src/main` C may claim byte identity;
documentation-grade `src_re` C must state that it is non-matching and not a build
input.

When static evidence answers the question, bank it without launching DuckStation. When
it reduces the live window but cannot establish cause, update the predeclared live
escalation with the exact missing domain.

### 5. Escalate to a targeted live experiment

Live work is permitted only when a current `planned` entry in
`analysis/phase4_live_escalations.json` names:

- the selected campaign/rows and hypothesis;
- every relevant capsule/index queried and the exact answers obtained;
- the precise missing instruction, DMA, GPU, SPU, interface, native-control, or
  invalid-capsule fact;
- why static work cannot answer it;
- same-anchor positive/negative controls, bound, expected evidence, limits, and
  cleanup; and
- why no selected offline/static action supersedes the run.

Prefer a validated `tools/phase4_duckstation_batch.py` plan with one to 128 serialized
`loadStateAndRun` or `bootAndRun` jobs. Call `debugger.capabilities`, require the
declared API/schema/source/binary surface, verify `debugger.status` and
`emulator.getMediaInfo`, and hash the pristine CUE and tracks. Inspect a state with
`emulator.getStateInfo` before load. Use a fresh absolute config directory, dedicated
loopback port and token, and stop only the PID owned by that profile.

Load/boot paused, verify the anchor, then arm. Re-arm after every state load. Positive
and negative branches must use the same anchor and execution bound and change only the
declared variable. Use `trace.armWhen`, an exact execute stop, `accessLog`,
`provenanceLog`, `functionTrace`, reverse, GPU causality, transfer/GP0, or SPU tracing
only for the named domain. Prove totals, bounds, pagination, and `truncated:false`.
Capture joined state with `capture.atomic`.

The live anchor is evidence, not an opaque authored digest. Every non-null movie or
save-state hash must resolve through the central fixture audit to a provisioned,
preservation-required pristine fixture. The settings hash must resolve to the retained
settings snapshot carried by the live receipt. Missing, unprovisioned, non-pristine, or
hash-inconsistent anchors invalidate the run before its behavioral result is considered.

A client-driven fallback is allowed only when the escalation identifies an exact
current scenario limitation, such as a required recorded-anchor
`movie.traceToFrame` prelude followed by precise observers. It must preserve all
identity, anchor, control, bound, cleanup, and external-output rules. Repeating a
full-movie precise loop because a script already exists is forbidden.

The distinction is executable: scenario recipes currently accept only
`accessLog.addWatch`, both exec-watch forms, `accessHistory.start`,
`accessTrace.start`, `transferLog.start`, `provenanceLog.start`,
`gp0Trace.start`, `gpu.causality.start`, `spu.trace.start`,
`functionTrace.start`, and `reverse.start`. `trace.armWhen` is synchronous and is
not recipe-armable, while `movie.traceToFrame` clears existing instrumentation.
Therefore a passive recorded-anchor prelude followed by a precise observer is a real
client-fallback case; it is not permission to bypass the batch adapter for ordinary
jobs.

### 6. Require cold-boot/movie behavioral proof at the right boundary

Use a timing-matched cold boot/from-boot movie when:

- the claim concerns original boot, loading, scene/overlay transition, frontend,
  persistence, or a path a save state could have bypassed;
- disc/code/asset bytes changed; or
- a future MOD behavior is being validated against a newly built pristine-base image.

For original behavior, the movie and pristine mounted-media identities must be pinned.
For code/disc/asset changes, independently verify the pristine input, copy it to a new
output, apply the selected modules once, retain its build manifest, and cold boot that
output. Never use ALLMODS or a prior derivative as the patch base.

A named, hash-pinned save state is allowed for a narrow runtime hypothesis after
embedded and mounted media verification. It is not proof of cold-boot reachability or
of code/disc/asset behavior. Instrumentation is re-armed after load. A screenshot
corroborates CPU/RAM evidence; it does not replace it.

### 7. Bank machine knowledge before narrative knowledge

Promote an observation only after all applicable layers below are updated together.
For any intentionally inapplicable layer, record `not_applicable` and the reason rather
than silently omitting it.

| Layer | Required durable result |
|---|---|
| Bytes and ownership | Exact pristine opcode/data/xref evidence; matching `src/main` C where byte-matched; otherwise externally pinned ASM or explicitly non-matching `src_re` semantic C with bounded claims. |
| Symbols and typed state | Function/data symbol reconciled to bytes, owner, address/range, width/signedness, aliases, valid domain, capacity, lifecycle, reset, residency, consumers, and unsafe assumptions in the schema whose lifetime owns it. |
| Registry and campaign | Row binding, exact dimension claim, confidence, authoritative tracked paths, low-level assertions, and non-intersecting residuals in the mechanics/campaign/finding registries. |
| Reproducible evidence | Generator or declarative scenario that recomputes a bounded non-copyrighted artifact from declared hashes; external raw bytes remain in the preservation set. |
| Executable guard | Focused test plus adversarial mutation of the load-bearing byte, event, boundary, hash, truncation, or expected value. A test that trusts an authored `passes` field is insufficient. |
| Canon | Confirmed original-game behavior, ownership, provenance, confidence, residuals, and supersession links. |
| Experiments | Question, fixture, commands, positive/negative observations, failed attempts, inference boundary, artifacts, cleanup, and falsifier. |
| Mods contract | Only future-consumption boundaries or actual MOD-private state/hooks/intended behavior. Do not move original-game facts into Mods. |

Regenerate low-level artifacts, then registries, coverage, queues, debt, inventory,
knowledge closure, assertion pins, gate receipts, and vault checks in dependency order.
Use the bounded dependency reconcilers only when an evidence artifact's dependency
identity changed without changing its retained behavioral payload. The assertion-pin
reconciler may update current SHA identities and SHA-valued joined leaves only; a
behavioral expectation must be changed by new evidence and review.

A reusable finding is finished only when its provenance, authoritative machine
representation, reproducible evidence, executable guard, Obsidian placement/links,
MOD consumption contract, clean-checkout external dependencies, and
confidence/residual/supersession record are all present.

### 8. Obtain a fresh rejection decision

A row or dimension promotion requires a fresh campaign-scoped verifier in a detached,
provisioned clean checkout. Run another verifier at least every third tested iteration
even without promotion. Whole-phase closure always belongs to a separate fresh
verifier.

The verifier recomputes low-level facts, introduces at least one adversarial mutation,
checks external identities, regenerates the joined control plane, and compares semantic
leaves—not only top-level hashes or `valid` booleans. It either accepts the scoped
promotion or returns exact autonomous gaps. The investigator may not self-certify a
promotion.

## Evidence-lane decision table

| Situation | Required action | Exit evidence | Reject/never claim |
|---|---|---|---|
| Complete frontier, typed state, ownership, selector, source status, or reviewed absence is missing | Static pristine C/ASM/symbol/xref/schema reconstruction | Exhaustive enumerator, exact bounds/dependencies, zero unclassified intersections, mutation guard | Do not replay merely to infer what bytes/xrefs already prove; do not claim matching C from documentation C. |
| A valid retained derived index/capsule covers the needed RAM/VRAM/SPU/register/block-flow question | Offline query/mathematics first | Hash-pinned commands, reconstructed domain hashes, frame window, control and truncation status | Do not claim exact instruction/DMA/GPU/SPU cause, every-cycle state, path breadth, or closure. |
| Offline/static work leaves one exact writer, DMA, GPU, SPU, interface, or native-control question | Planned targeted isolated DuckStation experiment | Capability/media/anchor identity, same-anchor controls, bounded precise events, atomic capture, cleanup | Do not run without a named missing domain; reject saturated, truncated, cycle-perturbed, or unpaired evidence. |
| Claim concerns boot/load/transition/frontend reachability or changed disc/code/assets | Pristine-media cold boot plus timing-matched movie | Reproducible from-boot anchor, fixed settings/input/bound, CPU/RAM assertion, build manifest when patched | A save endpoint, screenshot, filename, ALLMODS, or prior derivative cannot substitute. |
| Narrow runtime question begins safely after a validated state | Named save-state experiment | State and mounted-media identity, re-armed observers, fixed input/frame control | Do not generalize to cold boot, other scenes, lifecycle, or campaign breadth. |
| Any row/dimension promotion, every third iteration, or whole-phase claim | Fresh detached verifier | Independent recomputation, falsification, clean checkout, explicit decision | Investigator approval, green summary counts, or a stale verifier is insufficient. |

## Campaign batching and dependency centrality

Batch by a shared semantic boundary, not by file type or available movies. A valid
campaign batch has:

- one selected campaign and no more than three already coupled rows;
- one named dimension per row;
- a shared owner/interface/lifecycle or transition boundary;
- one reusable static enumerator or offline index;
- a bounded matrix of native positive, negative, edge, reset, and transition cases; and
- one banking and verifier boundary.

Start with shared high-centrality producers before dependent variants, as encoded by
the scheduler. Finish common capacity/lifecycle/reset/interfaces before multiplying
enemy, plant, level, or asset variants. Campaign breadth then samples every declared
variant and transition class, not merely the easiest fixture.

Stop the batch when its shared claim is falsified, when evidence reveals different
owners, or after two consecutive tested iterations without an accepted row/dimension
reduction. Change lane or decomposition at that point; do not open a second partial
campaign.

## Clean checkout and external-fixture contract

Before promotion, a disposable clean checkout must:

1. provision every declared fixture/source dependency;
2. verify `tools/build_baselines.json`, `tools/fixtures.sha256`,
   `tools/repro_inputs.sha256`, the external fixture set, capsule/index manifests,
   DuckStation source snapshot/runtime manifest, and executable hashes;
3. regenerate the affected artifacts without reading undeclared operator files;
4. pass the focused tests, mutation guard, knowledge/vault checks, and generated
   freshness checks; and
5. finish clean at the candidate commit.

Absolute operator paths may locate declared evidence, but the identity, role,
preservation requirement, and reprovisioning rule must be machine-readable. Missing
external inputs make a promotion unverified; they do not authorize substituting
ALLMODS or rewriting an expected value. Raw media, movies, saves, capsules, tokens,
captured frames, and copyrighted ASM/binary bytes stay out of Git.

## Concurrent work and ownership

The selected campaign has one integration owner and one authoritative WIP record. If
the operator authorizes concurrent branches:

- allocate disjoint tasks by semantic lane and path ownership—for example one offline
  query, one static owner reconstruction, and one verifier preflight;
- only the integration owner edits central campaign registries and regenerated
  coverage/queue/debt/inventory/pin/gate files;
- no two branches collect the same live fixture/window or edit the same generator,
  schema record, artifact, or Obsidian claim;
- contributors return a clean tested commit, exact base commit, touched-path list,
  input/output hashes, claims/non-claims, and validation receipt;
- the owner integrates low-level source/schema commits first, generators/artifacts
  second, registries and Obsidian joins third, and regenerates central outputs once;
  generated central files are never hand-merged; and
- a fresh verifier starts from the integrated commit, never from a contributor's dirty
  tree.

DuckStation has one emulation core per process and `scenario.runBatch` serializes jobs.
Live work for the selected campaign is therefore assigned to one owner at a time.
Multiple isolated processes do not justify duplicate replay or relax the one-campaign
WIP limit.

## Outage, restart, and checkpoint behavior

Before work, record the base commit, selected debt-leaf snapshot, input hashes,
planned claim/falsifier, escalation/plan ID, external output directory, and ownership
in the run receipt. External collectors and live scripts must refuse overwrite and
write bounded results plus cleanup receipts atomically where supported.

After every independently useful source/schema/generator/guard increment:

1. run focused checks;
2. commit only scoped non-copyrighted work;
3. record tested HEAD and external hashes; and
4. leave the worktree clean.

After interruption:

- compare HEAD and `git status` with the last tested receipt;
- reverify input, source, runtime, movie/state, capsule/index, and raw-result hashes;
- accept a capsule only if its manifest remains complete, untruncated, error-free, and
  control-matched;
- rerun affected `--check` generators before using an authored summary;
- resume a `scenario.runBatch` only if the same server process still owns its
  process-local batch; after process loss, restart pending jobs from their declared
  boot/state anchors; and
- treat an incomplete live trace, transient edit, uncommitted note, or interrupted
  summary regeneration as no evidence.

On restart, do not rerun a long movie until the retained receipt and derived index have
been checked for the named domain. Stop only the PID recorded for the isolated config
directory; never use a broad process-name kill.

Two consecutive controller/service/transport failures against the same immutable work
packet open an outage circuit: stop autonomous retries, bank a tested recovery
checkpoint that records the exact pending command and no debt reduction, and leave the
isolated worktree clean. Restart only after connectivity is independently healthy and
the base commit, scheduler selection, inputs, and external outputs are revalidated.
This rule responds to the retained 21-failure timeout sequence without misclassifying
infrastructure downtime as a semantic iteration.

## Efficiency measures and reassessment

Record these per tested iteration and aggregate them by campaign:

- accepted rows and accepted dimension leaves after fresh verification;
- tested iterations per accepted reduction and wall-clock time to durable banking;
- offline/index queries and external evidence bytes reused;
- DuckStation launches, replay frames, precise-observer frames, and atomic jobs;
- duplicate runs with the same fixture/window/domain and no newly named missing fact;
- first-pass verifier acceptance, verifier gaps by category, and falsifications caught;
- repair-only iterations for stale hashes, links, dates, gates, or undeclared
  dependencies;
- semantic-source/generator commits versus joined-hash, gate, and prose-only repair
  commits, reported as separate counts rather than a quality score;
- infrastructure failures separately from semantic iterations; and
- clean-checkout reproduction and complete machine/Canon/Experiment/Mods joins.

The current `abl-ratchet-phase4-progress/1` receipt is not sufficient for this
measurement. It records the campaign, rows, lane, before/after row and dimension
counts, and promotion booleans, but not elapsed time, offline reuse, live work,
duplicate experiments, verifier categories, commit categories, or knowledge joins.
Those absent historical values are unknown; they must not be reconstructed from prose
or treated as zero.

For a trial of this method, the controller must atomically write exactly one immutable
evidence manifest at
`$RUN_DIR/method-metrics/iteration-<zero-padded-iteration>.json` after each terminal
iteration. `$RUN_DIR` is the retained ratchet run directory. The manifest names
evidence; it does not contain authored counts, classifications, promotion lists, join
booleans, or verifier summaries. The normative
`abl-phase4-method-metrics/2` shape is:

```json
{
  "schema": "abl-phase4-method-metrics/2",
  "iteration": 1,
  "campaign_id": "fmv_playback",
  "row_ids": ["E15_fmv"],
  "base_commit": "40-hex",
  "tested_commit": "40-hex",
  "started_at": "RFC3339",
  "finished_at": "RFC3339",
  "validator": {
    "scope": "repo",
    "path": "tools/phase4_method_metrics.py",
    "sha256": "64-hex"
  },
  "evidence": {
    "debt_before": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "debt_after": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "progress_receipt": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "offline_query_receipts": [],
    "live_run_receipts": [],
    "escalation_ledger_before": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "escalation_ledger_after": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "verifier_decision": null,
    "controller_events": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "command_log": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "validation_report": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "knowledge_report": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "vault_report": {"scope": "run", "path": "relative/path", "sha256": "64-hex"},
    "clean_checkout_report": {"scope": "run", "path": "relative/path", "sha256": "64-hex"}
  }
}
```

Every displayed field is required and additional fields are forbidden.
`verifier_decision` is either `null` or the same closed artifact reference used by
the other evidence fields. An artifact reference has exactly `scope`, `path`, and
`sha256`; `scope` is `repo` or `run`, paths are relative to the tested checkout or
retained run root, and the validator rejects absolute paths, `..`, symlink escape,
missing files, or hash mismatch. Large external evidence is admitted only through a
hash-checked entry in the central preservation manifest named by a referenced offline
or live receipt. This prevents a moving absolute file from silently changing a
measurement.

`iteration`, campaign and row IDs, commits, and timestamps locate the evidence; they
are not accepted as measurements. The validator must prove that:

1. `base_commit` and `tested_commit` exist and the latter is the commit in every
   terminal validation, knowledge, vault, and clean-checkout report;
2. the campaign and row set match the selected campaign in `debt_before` and the
   progress receipt;
3. `started_at` and `finished_at` equal the first and last retained controller event,
   so wall time is their recomputed difference;
4. iteration numbers are contiguous, each `base_commit` equals the preceding
   iteration's `tested_commit`, and each `debt_before` SHA-256 equals the preceding
   iteration's `debt_after` SHA-256. A hash-bound trial-root receipt created before
   work pins the first base commit and first debt SHA-256;
5. each debt snapshot is reproduced byte-for-byte by the pinned closure-debt
   generator at its named commit, rather than accepted merely because it parses; and
6. all referenced evidence uses its producer's closed schema and passes that
   producer's own hash, completeness, and no-error checks.

An infrastructure terminal still has all fields. It points both debt fields at the
same immutable snapshot, uses `base_commit` as `tested_commit`, has no verifier
decision or live/offline result that did not finish, and cites the structured
controller failure and cleanup events. A missing manifest, a missing reference, or
an invalid producer receipt rejects the iteration; it is never silently omitted from
the denominator.

### Pre-trial seed-repair boundary

The controller provisions and re-verifies the centrally declared external fixture set
into its isolated checkout before it creates the trial root. It then requires the v2
validator self-check, the legacy live-deny index, pristine build identity, the Phase-4
gate guards, the recomputed Phase-3 prerequisite (including retained live-artifact
freshness), vault validation, and an empty tracked status. A green Phase-4 exit gate is
not required—the phase is expected to remain open—but a stale prerequisite is not a
trial iteration.

If this boundary is red, a separate pre-trial implement/verify loop gets at most three
attempts to repair only the seed. It may replay stale Phase-3 live artifacts on the
current hash-pinned DuckStation fork, but may not advance a Phase-4 campaign, rewrite
hashes without replay, bless an unavailable historic runtime, or weaken a guard. The
mechanical preflight and a fresh read-only verifier must both accept the committed,
clean repair. The verifier runs from a separately provisioned detached checkout and
must leave its HEAD and status unchanged. The controller also snapshots the complete
107-row Phase-4 debt projection before repair and recomputes it after every attempt.
`tools/phase4_seed_repair_scope.py` rejects any row, nine-dimension, scheduler, or
campaign-debt change. Its permitted diff surface is derived from the immutable base
Phase-3 evidence inventory; all other paths—including new, un-inventoried semantic
sources—are rejected, except explicitly named dependency/control-plane Phase-4
summary refreshes. A path consumed by the immutable Phase-4 campaign inventory stays
protected even when an older Phase-3 inventory also names it; this prevents a
cross-inventory allowlist overlap from carrying Phase-4 progress into seed repair.
Hash-pinned Phase-3 dependency objects are validated against their immutable-base
blobs rather than treated as prose paths.

### Automatic clean-candidate reseeding

A tested trial root cannot remain authoritative after its executor changes the
controller, acceptance contract, accepted operating method, method-metrics/report
producer, legacy-live index, seed validator/repair machinery, pristine-identity
guard, or the classifier itself. `tools/phase4_trial_boundary.py` compares the
iteration base and clean committed candidate, retains both blob identities for every
trial-critical path, and requires a new trial root before closure debt or fixed
reports are interpreted. The old root records the reseed reason but admits no
semantic claim or method-metrics iteration.

The same clean-candidate reseed is required when post-commit debt regeneration or
fixed report validation fails. The new run repeats central fixture provisioning,
seed repair when required, a fresh read-only seed verifier, and trial-root creation
from the candidate commit. Relative/default acceptance contracts and `AGENTS.md` are
read as Git blobs from that seed commit, never from a possibly dirty operator
checkout; explicitly absolute external contracts remain operator-selected inputs.
The controller preserves the parent-run lineage and
reason and retains the same detached controller PID/viewer with process replacement.
There is no lifetime reseed quota and no default ordinary-iteration quota: a clean,
validated candidate with a changed semantic decision or closure-debt projection
continues automatically toward independently verified closure. A progress-sensitive
guard canonicalizes the reseed reason, executor conclusion, closure-debt projection
and bounded failure details. Three consecutive identical signatures open a visible
infrastructure circuit; candidate hashes alone cannot manufacture progress. The
circuit makes no closure or external-blocker inference.
Dirty worktrees, missing commits, invalid controller syntax, and ambiguous candidate
identity remain terminal; self-reprompting must never bless or discard unbanked
operator work.

The verifier's gap-free decision must cite exactly the retained Phase-3 evidence
inventory, Phase-3 gate, and downstream Phase-4 gate, whose low-level freshness,
pristine identity, and recomputed prerequisite leaves are checked. Its validation
reference is a single `abl-phase4-seed-validation/1` report whose fixed identity,
gate, guard, and vault commands are independently replayed. The two accepted
`abl-phase4-verifier-falsifier/1` receipts invoke the immutable
`tools/phase4_seed_falsifiers.py` modes for shared-live-helper drift and retained
artifact drift. Their commands, red guard results, restoration, exit codes, and
outputs must reproduce at the exact clean candidate. Arbitrary scripts, `python -c`,
print-only PASS output, and hash-closed prose are rejected. Only then does
the controller create the immutable trial root and capture
the first debt baseline. These attempts, their logs, and their verifier decisions are
retained outside the trial metrics; they cannot consume the one allowed repair-only
tested iteration or inflate methodology yield.

### Derivation rules, not authored metrics

Before a trial begins, bank `tools/phase4_method_metrics.py`, its schema fixtures,
mutation tests, and a source SHA-256. Every iteration manifest pins that exact
validator. A fresh verifier runs the pinned validator in a clean checkout and then
runs the current validator; disagreement rejects the trial. The validator derives
all material values as follows:

| Measure | Only accepted derivation |
|---|---|
| accepted row | a canonical row changes from non-`complete` in `debt_before` to `complete` in `debt_after`, the progress receipt names that exact transition, and the referenced fresh verifier decision is gap-free and accepts the same tested commit |
| accepted dimension | a canonical `<row>/<dimension>` leaf changes from `gap` or `partial` to `met` across the chained debt snapshots, and the same progress/verifier conditions hold |
| retained reduction | an accepted row or leaf is still complete/met in the sixth iteration's `debt_after`; a later demotion remains visible and removes it from the net result |
| semantic/tested/repair/infrastructure iteration | derived from the terminal controller event, accepted transition, and tested-commit diff using the path rules below; the manifest supplies no classification |
| wall seconds | last minus first timestamp in the closed controller-event stream; both must equal the manifest locators |
| offline queries | number of distinct canonical `{reader_sha256, command, query}` objects in complete `abl-phase4-offline-query/1` result receipts; each receipt pins a tracked Phase-4 reader, names `@query` and every hash-pinned input/output through canonical `@run/...` or `@repo/...` command tokens, retains the zero exit code and exact stdout hash/body, and must independently replay in a disposable output directory with byte-identical outputs before it is counted |
| external bytes reused | sum of byte sizes, recomputed from files, for unique hash identities actually read by those query receipts; repeat use of the same SHA-256 in one iteration is counted once |
| launches and atomic jobs | unique owned server-session records and completed job objects in hash-bound batch/fallback results, each joined to capabilities, media verification, and owned-PID cleanup receipts |
| replay, observer frames, and instructions | differences between typed integer start/stop counters in completed raw run results; trace page counts are accepted only when pagination is complete and no truncation/error flag is set |
| planned live work | every investigator live receipt joins by escalation ID and missing-fact ID to a `planned` entry already present in `escalation_ledger_before` |
| duplicate replay | an investigator experiment key already present in any earlier retained investigator receipt; a new prose label or missing-fact ID does not make it new |
| first decision, gaps, falsifications | parsed from the referenced fresh verifier decision's closed outcome, stable gap-code list, and falsifier-result objects |
| infrastructure failures/retries | terminal failure and retry event objects in the controller stream; transport text and file counts are not used |
| knowledge joins | recomputed from the accepted claim's authoritative paths, generated assertion pins, campaign registry, typed schema/symbol/source paths, and vault report as described below |
| clean-checkout reproduction | the clean-checkout report names `tested_commit`, records zero `git status --short` entries before and after checks, and hash-links every invoked check result |

The iteration path classification is deterministic and may report several commit
touch categories without turning them into a score. The validator source contains
the exact ordered `SEMANTIC_SOURCE`, `GENERATOR_GUARD`, and `JOINED_ONLY` path-pattern
arrays; matches use Python `fnmatch.fnmatchcase` on normalized repository-relative
POSIX paths. Those constants are covered by fixtures and by the validator SHA-256, so
the controller cannot author or alter a category per iteration:

- `semantic_source` is the number of non-merge commits in
  `base_commit..tested_commit` that touch `src/main/**`, `src_re/**`, `symbols/**`,
  `asm/**`, `config/record_types.yaml`, `config/semantic_state.yaml`,
  `config/phase4_*.yaml`, or `analysis/mechanics_baseline.yaml`;
- `generator_guard` is the number that touch `tools/phase4_*.py`,
  `tests/test_phase4_*.py`, `tests/scenarios/**`, or a Phase-4 generator-owned
  artifact. Generator ownership is the exact output-path set parsed from the
  hash-checked before/after `analysis/phase4_generator_inventory.json`, not a filename
  guess;
- `joined_hash_gate` is the number whose changed paths are all hash manifests,
  generated queues/indexes/ledgers/inventories, assertion pins, validation reports,
  or gate outputs enumerated by `JOINED_ONLY`; a generated campaign evidence artifact
  that is not in that closed array remains `generator_guard`, not joined-only;
- `prose_only` is the number whose changed paths are all Markdown; and
- an unclassified changed path is a validation error rather than an implicitly
  favorable category.

The validator obtains the commit list with
`git rev-list --reverse --no-merges <base>..<tested>` and each changed path with
`git diff-tree --no-commit-id --name-status -r`; renames contribute both old and new
paths. `joined_hash_gate` and `prose_only` are exclusive whole-commit categories.
The touch categories may overlap `semantic_source` and `generator_guard`, and their
raw lists, not merely totals, appear in the derived summary.

An iteration is `infrastructure_failure` only when its terminal controller event has a
closed infrastructure failure code, no tested-commit delta, and identical debt
snapshots. It is `repair_only` only when it has no accepted transition and every
changed commit is `joined_hash_gate` or `prose_only`. Every other completed iteration
is `semantic`. A tested iteration is any non-infrastructure iteration, including an
adverse verifier result. Splitting a change across commits therefore cannot remove the
iteration from the denominator.

A complete knowledge join is also derived rather than asserted. The validator starts
with every `authoritative_path` and assertion in each accepted dimension claim,
rechecks those paths and SHA-valued leaves, and requires the corresponding generated
registry/debt entry. It then follows machine links to the applicable Canon and
Experiment notes and verifies them with the vault report. It requires either a linked
Mods note or the campaign registry's machine-readable `mods_disposition:
not_applicable`. Missing applicability data is not equivalent to not applicable.
Each promoted claim must also provide a closed `knowledge_bindings` array with exactly
one entry per asserted artifact. Each entry names the exact inventoried producer, one
or more hash-pinned semantic sources from `src/main`, `src_re`, `symbols`, `asm`, or
`config`, the exact JSON leaf where the produced artifact retains each source hash,
and exact pytest node IDs from authoritative inventoried test paths. The
producer must be the inventory's structural owner of that artifact; comments or
filename substrings do not establish the join. The pinned method validator collects
and executes every named node from the tested checkout and retains both output hashes.
It then changes the bound artifact bytes in place inside the isolated tested checkout,
requires those same nodes to fail, restores the exact bytes in `finally`, and requires
the Git status to return to its pre-falsification state. An unrelated schema, a
comment-only or `assert True` “test,” an uncollected node, or a passing report that
never runs the bound guard rejects the promotion. Only then, and only with the
clean-checkout proof above, is the semantic join complete.

### Canonical live experiment identity

Every completed live operation must be emitted by
`tools/phase4_duckstation_batch.py` or the documented fallback adapter as a
hash-bound `abl-phase4-live-run-receipt/2`; handwritten summaries are not accepted.
The method manifest references the live receipt by SHA-256, and that receipt in turn
references raw API results, pagination data, media/capabilities captures, command
events, the batch/fallback adapter source, and owned-PID cleanup by SHA-256.
Launch/job/frame totals are recomputed from those raw objects, not copied from summary
fields.

The live receipt contains no free-form anchor, bound, window, perturbation, or
control. Its experiment specification has these closed components:

- `executor_role`: `investigator` or `fresh_verifier`; the latter is accepted only
  when the receipt is issued and referenced by the independent verifier decision;
- `anchor`: `kind` is `cold_boot`, `cold_boot_movie`, `save_state`, or
  `movie_start_state`; it includes exact media, settings, movie, and state hashes as
  required by that kind, plus
  `start: {clock, value}` where `clock` is `emulator_frame`, `movie_frame`,
  `cpu_cycle`, or `instruction`;
- `execution`: both `bound` and `capture_window` are
  `{clock, start, stop, stop_inclusive}` with the same closed clock enum,
  nonnegative integer bounds, and `stop >= start`; string ranges and prose such as
  `"[100,120]"` are invalid;
- `domain`: one of `ram`, `register`, `dma`, `gpu`, `spu`, `interface`, or
  `native_control`;
- `observer_plan`: a reference to a strict plan whose operations are closed debugger
  method IDs, typed arguments, and bounded result limits;
- `perturbation_plan`: a reference to a strict plan with either `kind: none` and an
  empty operation list or `kind: operations` and an ordered, contiguous `sequence`.
  The closed operation unions are
  `memory_write(sequence,address,width_bits,before,after)`,
  `register_write(sequence,register_index,before,after)`,
  `input_edit(sequence,port,control_kind,control_index,start_frame,stop_frame,value)`,
  `code_write(sequence,address,original_word,replacement_word)`, and
  `disc_overlay(sequence,lba_start,sector_count,base_extent_sha256,replacement_extent_sha256)`.
  Addresses, values, ports, register/control indexes, frames, and sector bounds are
  range-checked integers; `width_bits` is `8`, `16`, or `32`; `control_kind` is
  `digital_bit` or `axis`; hashes are lowercase 64-hex; unknown fields are rejected;
- `control_plan`: a reference to a strict plan with `role` `baseline`, `positive`, or
  `negative`, the paired run-basis SHA-256 (computed before adding a control), the
  canonical anchor SHA-256, the typed only-difference plan SHA-256, and an
  assertion-plan SHA-256; and
- exact DuckStation source-state, executable, API-surface, observer-plan,
  adapter-source, perturbation-plan, and control-plan SHA-256 identities.

Optional anchor identities are JSON `null`, not empty strings. Kind-specific rules
forbid movie and state hashes on `cold_boot`, require only a movie hash on
`cold_boot_movie`, require only a state hash on `save_state`, require movie and state
hashes on `movie_start_state`, and require the pristine media SHA-256 in every case.
Capsule/index identities may be cited as localization inputs, but cannot masquerade as
a DuckStation execution anchor. The
perturbation operation list is order-sensitive because writes can be order-sensitive;
controls express a deliberate branch through their different typed plan hashes.

The pinned validator first parses every component with duplicate-key detection,
rejects unknown keys, strings in integer fields, floats, non-contiguous operation
sequences, and invalid kind-specific combinations. It then creates the experiment-key
object from the validated `anchor`, `execution`, `domain`, plan SHA-256 identities,
and DuckStation source/executable/API-surface hashes. It deliberately excludes result
hashes, receipt path, executor role, escalation ID, missing-fact ID, timestamps, and
human rationale. Canonical bytes are UTF-8 produced by Python
`json.dumps(object, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
with no trailing newline; floats have already been rejected. The experiment key is
the lowercase SHA-256 of those bytes. Focused fixtures must prove that key order and
whitespace do not change the key, every semantic field does, and the former prose
variants for the same numeric window cannot enter the schema.

The validator retains that hash as the canonical provenance key, and separately
derives the duplicate-detection **semantic key** from the fully parsed anchor,
execution, domain, normalized observer/perturbation documents, control role, and
DuckStation source/executable/API identities. It excludes the adapter-source hash and
the serialized plan-file hashes from the semantic key: comments, whitespace, or a
different JSON serialization cannot turn the same experiment into new work. The
validator builds the semantic-key index across all earlier retained investigator
runs. A differently worded missing fact does not excuse a duplicate because the
retained result should be reused. Positive/negative controls remain distinct through
their normalized perturbation and control roles. A required independent-verifier
reproduction is reported separately and can repeat the semantic key only when it is
joined to the fresh verifier decision; an investigator cannot self-label a run
`fresh_verifier`.

Before the first v2 trial, a fresh verifier must also bank a hash-bound legacy index
over every retained Phase 4 live escalation/result receipt. A legacy receipt is
normalized only when its hashes and typed bounds can be recovered without guessing.
An unnormalizable legacy media/movie/state/domain/window tuple becomes a conservative
deny-list entry: a potentially overlapping investigator run is blocked until the
verifier proves a typed semantic difference. This prevents the new schema from
treating all pre-v2 replay as free.

The legacy entry hash uses a closed historical projection. It pins every authored
field, pre-run audit, execution result, media identity, and retained evidence field,
but excludes the generated top-level `derived_post_run_audit`: that object is a
current-queue recomputation whose global source hash necessarily changes whenever a
new escalation is appended. The generator and independent metrics validator implement
the same named projection, and a regression guard proves that refreshing this one
derived object is admitted while mutating retained execution/media evidence is
rejected.

For a precise run, the validator compares the typed execution and capture bounds with
the referenced passive/cold-boot prelude receipt. It requires the precise window to be
strictly smaller in the same clock. The sole exception is a fresh verifier decision
with stable code `PRECISE_WINDOW_UNAVOIDABLE` naming that live-receipt SHA-256 and
giving a machine-checkable boundary mismatch; a prose explanation cannot waive the
rule.

Trial-v2 hardening additionally requires the adapter to be a tracked, hash-pinned
Phase-4 runner at the tested commit; a run-local script cannot establish that an API
operation occurred. One receipt admits at most the API's 128 jobs, observer and
perturbation structures have finite closed bounds, identity command events retain
their normalized result bodies, and the media/source/binary/API identities join to
the current repository manifest. Every command event names its owned server-session
ID. A counted raw job must join byte-for-byte by ordered job ID to exactly one retained
`scenario.runBatch` event whose plan hash is derived from the typed anchor, execution,
observer, perturbation, and control objects, and to a terminal result-bearing
`scenario.getBatch` event for the same batch reporting `completed`; identity calls
must occur exactly once before `runBatch`, every `getBatch` must follow it, and raw
frame/instruction counters must stay inside the receipt's finite typed bounds.
Identity calls without this atomic execution chain cannot admit authored raw results. Every
investigator receipt—including a passive
prelude—must be hash-listed by the independent campaign verifier before it contributes
to a terminal iteration. A precise receipt must also retain that fully validated
passive receipt in the same iteration. These joins do not cryptographically sign
DuckStation output; their purpose is to make an authored transcript insufficient
without an independent replay/audit and a pinned executable evidence chain.

An offline receipt follows the same anti-transcript principle. Its exact command may
invoke only its tracked reader, must pass the canonical query as `@query`, and must name
every declared input and output as a canonical artifact token. Absolute paths,
traversal, unnamed artifacts, nonzero execution, or stdout/hash disagreement reject
the receipt. The validator substitutes verified retained inputs and disposable output
paths, executes the command again from the tested checkout, and compares every output
byte-for-byte. A pre-authored summary next to an unexecuted command is therefore not an
offline query.

Fixed controller reports are replayed, but replay stability and exit zero are not
enough: each known producer has a positive semantic output contract. Conventional
`FAIL`, `FAILED`, `ERROR`, `FATAL`, nonzero failure/error counts, or `<n> failed`
markers reject the report even when a buggy producer exits zero.

### Aggregation and thresholds

The first method trial cannot start until the v2 validator and mutation fixtures above
are banked. Reproduce each iteration and the chained six-iteration summary with:

```text
python3 tools/phase4_method_metrics.py \
  --run-dir "$RUN_DIR" \
  --check \
  --summary
```

The derived summary retains the evidence manifest hashes, validator hash, exact
transition tuples, per-commit path classifications, experiment keys, source receipt
hashes, adverse verifier outcomes, and any later demotion. It reports both promotion
events and net rows/leaves retained at the trial end; the success threshold uses the
net value. A fresh verifier recomputes the summary from raw referenced artifacts and
does not accept a cached scalar.

The retained baseline is five promotion events in 16 successful iterations, eleven
no-reduction iterations, a net four met leaves, zero rows, and four gap-free verifier
decisions out of 14. Historical fields not present in retained evidence remain
`unknown`, never zero. The candidate method succeeds in its first six tested
iterations only if:

- at least three iterations contribute a distinct independently accepted row or
  dimension transition that remains reduced at the trial end;
- at least four receive a gap-free first verifier decision;
- no investigator live receipt lacks an escalation and missing-fact entry already
  planned in the before-ledger;
- duplicate investigator experiment-key count is zero;
- every precise investigator run has a strictly smaller typed window than its
  passive/cold-boot prelude, except the narrowly coded verifier case above;
- every accepted semantic increment has a complete derived knowledge join and
  clean-checkout proof; and
- no more than one tested iteration derives as repair-only.

Reassess after every six tested iterations, at each campaign boundary, and immediately
after two consecutive no-reduction iterations, any unplanned replay, or a verifier
rejection caused by an omitted preflight layer. A missed threshold requires a method or
lane change and an update to this note through another methodology ratchet. Do not
improve the metric by demoting requirements, splitting bookkeeping commits, editing
derived classifications, relabeling duplicate runs, or excluding adverse verifier
results.

## Verifier acceptance and rejection

Accept this candidate only if a fresh detached verifier reproduces the decisive counts,
source/API identities, representative machine layers, and history measurements and
then fails to find a more efficient supported method under the same requirements.

Reject it if any of the following holds:

- the closure ledger does not deterministically select the claimed campaign/row;
- the method requests live work already answered by a valid retained index/capsule;
- an offline claim requires exact instruction/DMA/GPU/SPU cause or a native control;
- a promoted fact lacks an applicable ASM/C, symbol/schema, registry, generator,
  mutation guard, Canon, Experiment, or Mods-consumption disposition;
- breadth, capacity, lifecycle, reset, transition, cross-system, source, residual, or
  supersession boundaries can be bypassed;
- a clean checkout depends on undeclared operator state or an unpinned dirty
  DuckStation surface;
- concurrent or restart rules allow conflicting central outputs or treat incomplete
  work as evidence;
- efficiency measures cannot be recomputed from retained receipts; or
- the proposal changes Phase 4 evidence, implementation, tests, gates, scores, or
  statuses to make itself look successful.

The verifier should falsify at least one scheduler input, one authoritative low-level
claim, one external dependency/hash, and one truncation/control predicate in disposable
copies. Agreement with this prose is not verification.

## Confidence, residuals, and supersession

**Candidate confidence: medium.** The repository and run-history diagnosis is
well-supported, and every recommended DuckStation capability/limitation was checked
against the current documentation and C++ implementation. The method itself has not
yet been independently attacked or measured over a six-iteration trial.

Residual uncertainties:

- The v2 method-metrics validator and its mutation fixtures are specified here but are
  not yet banked because they are Phase 4 implementation outside this advisory's write
  boundary. A method trial must not begin until a fresh verifier attacks that
  implementation and its pinned path rules.
- The relative yield of static reconstruction across the 88 currently static rows has
  not been measured by family.
- Sixty-five rows lack capsules; future fixture recording cost may alter the best lane
  after their static frontiers are known.
- The 95-path dirty DuckStation fork is hash-pinned but mutable. Any source, method,
  schema, client, runtime, or executable change invalidates the API identity assumed
  here until the generated surface is refreshed and reverified.
- The concurrency and outage rules are derived from current artifacts and observed
  transport failures but have not yet been stress-tested by the methodology verifier.
- A selected campaign can still encounter an exact operator-only movie/fixture need.
  That is a row-level blocker only after static/offline and safe autonomous control
  alternatives are exhausted.

A later method may supersede this one only with retained measurements, explicit failed
predictions, unchanged roadmap definitions, and a fresh hard-truth decision. Preserve
the old decision and receipt; do not rewrite history. Current campaign evidence and
status remain authoritative regardless of this candidate's eventual verdict.

## Independent verifier receipt

- Verifier status: pending.
- Detached checkout and tested commit: not yet supplied.
- Falsification attempts: not yet supplied.
- Acceptance/rejection rationale: not yet supplied.
- Required external input: none known for testing the method candidate itself.

Only the independent hard-truth step may change `status`, `methodology_ratchet`, the
verdict marker, or this receipt from pending to an accepted/verified decision.
