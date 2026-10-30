---
kind: playbook
id: PLAYBOOK_pcsx_redux_migration
name: PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency
status: proposed
created: 2026-07-30
updated: 2026-07-30
confidence: high
related:
  - PLAYBOOK_game_solving_roadmap
  - PLAYBOOK_game_solving_phase_2
  - PLAYBOOK_game_solving_phase_4
  - DUCKSTATION_API_INDEX
---

# PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency

## Decision

Make PCSX-Redux the intended long-term operational platform for ABL reverse
engineering, deterministic replay, scenario automation, and regression validation.
Do not declare the migration complete merely because Redux can boot the game or replay
newly recorded input.

The desired endpoint is:

> PCSX-Redux is the sole emulator required for ordinary ABL work. The current custom
> DuckStation fork and its exact runtime bundles remain preserved, read-only historical
> evidence and an optional independent cross-emulator control.

This deliberately distinguishes **operational retirement** from **epistemic deletion**.
The project may stop requiring DuckStation in normal workflows after the exit gate in
this note passes. It must not discard DuckStation-native movies, states, trace capsules,
source snapshots, binaries, manifests, or the ability to inspect evidence already
accepted from them.

This migration is tooling work in support of
[[Game Solving Roadmap - From Reconstruction to Reliable Modding]]. It does not change
the Definition of Done for a solved subsystem, weaken any phase gate, or convert an
emulator observation into original-game authority by itself.

## Why migrate

PCSX-Redux is a credible long-term base because it is an open, modifiable PS1
development and reverse-engineering environment with core CPU/GPU/SPU debugging,
Lua callbacks, GDB/Ghidra integration, save states, VSync events, headless startup, and
an existing GPU logger. Those facilities provide appropriate insertion points for an
ABL-specific deterministic movie system, scenario runner, evidence capture, and
provenance tooling.

The custom DuckStation fork remains substantially more capable as an ABL automation
platform today. [[DuckStation_API_Index|DuckStation API Index]] describes the banked
API snapshot, while [[EXP_2026-07-18_phase4_trace_capsules|Phase 4 persistent trace
capsules]] records 50 accepted capsules covering 50,052 movie frames. The repository
also retains a Phase-2 oracle, declarative scenarios, centrally audited saves and
movies, and source/binary-specific evidence. Movie playback alone does not replace
that system.

Redux is therefore selected as the **target foundation**, not declared the current
replacement.

## Authority and non-negotiable constraints

1. The hash-verified pristine SCUS-94288 retail image remains the sole behavioral
   authority and sole patch/build base.
2. ALLMODS remains comparison evidence only. It must never become a Redux baseline,
   movie anchor, or source image for a new build.
3. A new Redux recording is not proof that Redux matches the original game. It may
   silently encode Redux-specific timing, CD, GPU, SPU, controller, or memory-card
   behavior.
4. Existing DuckStation findings retain their recorded confidence only through their
   pinned evidence and guards. They are not automatically promoted or invalidated by
   the migration.
5. DuckStation and Redux save states are emulator-specific. Do not convert one by
   treating its raw bytes as portable machine state.
6. Never copy implementation code from the local CC BY-NC-ND DuckStation tree into
   GPLv2 PCSX-Redux. Reimplement required behavior from an independently written ABL
   contract, public protocol descriptions, tests, and observed behavior.
7. Copyrighted media, BIOS files, memory cards, movies, saves, captures, and capsules
   stay outside Git. Their hashes, roles, schemas, generators, preservation
   requirements, and validation results belong in the repository.
8. Every live run must use an isolated absolute profile/config directory, a pinned
   binary, verified mounted media, and exact-owned process cleanup.
9. Instrumented and uninstrumented replay are separate controls. Instrumentation is not
   assumed neutral merely because playback completes.
10. A clean checkout plus the declared external fixture set must reproduce every
    claimed migration gate.

## Definition of full migration

Full migration is achieved only when all four statements are true:

1. **Operational parity:** every emulator capability actually required by the active
   roadmap has a tested Redux implementation or a documented, accepted replacement
   method.
2. **Evidence continuity:** every load-bearing DuckStation scenario, movie class,
   fixture role, oracle assertion, and retained capsule is preserved, migrated, or
   explicitly classified as historical-only without weakening a gate.
3. **Independent qualification:** Redux repeatedly reproduces the pristine semantic
   assertions under clean profiles, and traced runs remain equivalent to uninstrumented
   controls.
4. **Durable cutover:** source, schemas, generators, tests, manifests, documentation,
   and external preservation requirements reproduce from a clean checkout. The
   roadmap and `AGENTS.md` change only after this proof.

“Redux plays the movie,” “the movie reaches the expected scene,” or “the same address
changed” is not full migration.

## Starting baseline

- Local Redux source: `~/PCSX-Redux-RE`.
- Initial inspected Redux revision:
  `3e10093ad9cc2fb445668928b3d0f87abeccd29c`.
- The Redux revision above is a planning baseline, not yet a repository-pinned runtime
  or accepted evidence generator.
- Redux already exposes core VSync events, two-port pad state, save-state creation and
  loading, Lua breakpoints and memory/register access, CLI Lua startup, GDB/web
  interfaces, Ghidra integration, and GPU command logging.
- Redux does not currently provide an ABL-grade deterministic movie subsystem,
  complete pad-state injection, a sufficient headless scenario API, the current
  DuckStation provenance surface, or validated Redux trace capsules.
- The authoritative counts of DuckStation movies, saves, scenarios, APIs, and required
  evidence must be regenerated by WP1. Counts copied from chat or a stale generated
  index are orientation only.

## Target architecture

The target should have four layers:

1. **Redux core extensions**
   - deterministic effective-input latching;
   - complete pad and frame serialization;
   - exact frame control;
   - coherent state capture;
   - instrumentation hooks that do not depend on GUI timing.
2. **ABL Redux control service**
   - isolated run lifecycle;
   - local authenticated control;
   - media/state/source/binary identity;
   - scenarios, batches, structured progress, timeouts, and errors;
   - owned-PID cleanup.
3. **Emulator-neutral ABL scenario and evidence layer**
   - behavioral assertions expressed independently of DuckStation/Redux method names;
   - adapters for Redux and the frozen DuckStation oracle;
   - fixture and preservation manifests;
   - comparison reports that distinguish behavioral, capture, and emulator differences.
4. **Offline evidence layer**
   - Redux-native trace capsules or an equivalent validated persistent format;
   - deterministic readers and mathematical analysis tools;
   - provenance that binds media, movie, state, source, binary, settings, and capture
     domains.

The emulator-neutral layer prevents another migration from requiring a rewrite of
every behavioral claim.

## Work packages

### WP0 — Freeze and preserve the current evidence platform

Deliverables:

- Regenerate the current DuckStation API/source/binary inventory without trusting the
  stale headline count.
- Hash and preserve the exact runnable DuckStation bundles required by accepted
  evidence.
- Inventory every DuckStation movie, save, scenario, oracle anchor, trace capsule,
  reader, generator, and test by path, role, hash, media class, and preservation set.
- Record which artifacts are load-bearing for Phase 0–4 gates and which are historical
  or diagnostic only.
- Preserve the current platform-gotcha evidence, especially movie desynchronization
  caused by armed instrumentation.

Exit condition:

- A machine-readable preservation manifest can prove that migration work cannot
  accidentally erase or silently orphan accepted DuckStation evidence.

### WP1 — Build the use-case parity matrix

Do not attempt to port every DuckStation RPC method. Enumerate the capabilities that
actual roadmap generators, tests, and scenarios consume.

For each use case record:

- DuckStation method(s) and consumer(s);
- required semantic behavior;
- timing and neutrality requirements;
- input/output schema;
- external fixture dependencies;
- Redux-native equivalent, required extension, or accepted replacement;
- validation fixture and failure detector;
- migration status: `unassessed`, `not_needed`, `prototype`, `qualified`, or
  `blocked`.

Minimum capability families:

- process isolation and media identity;
- deterministic movies and frame control;
- save-state identity and loading;
- memory/register inspection and perturbation;
- breakpoints and conditional actions;
- access, execution, and function traces;
- CPU/DMA/CD/GPU/SPU provenance;
- atomic multi-domain capture;
- reverse or an accepted equivalent investigation workflow;
- screenshots, framebuffer/VRAM/CLUT, and audio observables;
- scenarios, batches, cancellation, resumption, timeouts, and progress;
- symbols and typed Ghidra structures;
- persistent offline evidence.

Exit condition:

- Every load-bearing current consumer maps to a tested Redux path or an explicit
  blocker. No “feature parity” claim is based on API-count similarity.

### WP2 — Establish a reproducible Redux fork

Deliverables:

- Create a dedicated ABL Redux branch/repository with a documented upstream revision.
- Pin recursive submodules, compiler/toolchain versions, build flags, runtime resource
  hashes, and the resulting executable hash.
- Add clean build and core-test instructions for Fedora.
- Add isolated portable-profile launch, exact-owned cleanup, and crash recovery.
- Add a capability endpoint/report containing API/schema versions, source revision,
  source dirty hash, binary hash, feature flags, and method schemas.
- Add CI or a local clean-checkout builder that rejects untracked source
  dependencies.

Exit condition:

- A clean Redux checkout builds the same accepted runtime and produces a verified
  capability report without importing source from the dirty ABL or DuckStation trees.

### WP3 — Implement deterministic movies in Redux core

Implement movies as a core input-source subsystem, not as GUI automation and not as a
digital-only Lua override.

Required movie contract:

- two controller ports;
- controller type and connection state;
- all digital buttons, including explicit forced release;
- four 8-bit analog axes per analog pad;
- analog/config mode and relevant pad protocol state;
- effective input recording after source precedence is resolved;
- deterministic playback precedence that prevents physical-host input leakage;
- stable once-per-emulated-frame latching at a documented VSync boundary;
- a serialized 64-bit emulated frame counter;
- exact `advanceFrames` and `advanceToMovieFrame`;
- defined sample-zero and first-frame behavior;
- cold-boot and save-state anchors;
- reset/load/unmount termination or explicit movie-owned anchor transitions;
- movie cursor, total frames, rerecord count if supported, completion, truncation, and
  structured error reporting;
- versioned format with forward rejection rather than silent reinterpretation.

The movie manifest must bind:

- pristine disc/CUE/track hashes and serial;
- BIOS hash;
- memory-card hashes or explicit clean-card policy;
- emulator source, binary, runtime-resource, and settings hashes;
- controller configuration;
- anchor kind and anchor hash;
- boundary convention and total frames;
- whether the movie ended naturally or was truncated.

Pad protocol state that affects deterministic continuation must be serialized in Redux
save states. A load that fails deserialization or identity validation must fail
explicitly; GUI or transport success cannot masquerade as a successful state load.

Exit condition:

- Repeated isolated playback of a digital and an analog test movie produces identical
  frame counters and selected CPU, RAM, scratchpad, GTE, VRAM, and SPU RAM hashes from
  both cold boot and state anchors.

### WP4 — Prove identity, state, and internal determinism

Deliverables:

- Mounted-media identity from actual CUE and track bytes, not serial alone.
- BIOS, settings, memory-card, source, binary, runtime, and state identity.
- Save-state introspection before loading.
- Complete pad/controller state included in save serialization.
- Coherent checkpoint fingerprints over CPU registers/cycle, RAM, scratchpad, GTE,
  VRAM, SPU RAM, GPU state, SPU state, CD state, and relevant counters.
- Repeated clean-profile playback controls.
- Explicit documentation of fields that are intentionally run-local or
  non-deterministic.

Exit condition:

- Three independent clean-profile runs of every qualification movie reproduce the
  declared deterministic domains. Corrupt media, BIOS, settings, state, and movie
  fixtures are rejected by tests.

### WP5 — Implement the ABL scenario and automation surface

Deliverables:

- Local authenticated control or an equivalently isolated local IPC boundary.
- Atomic “boot/load anchor, verify identity, play input, arm instrumentation, execute,
  and capture” recipes.
- Declarative scenarios with schema validation.
- Batched scenarios with progress, cancellation, restart/resumption from named
  anchors, per-job results, and hard timeouts.
- Exact frame/condition advance with explicit stop reasons.
- Structured errors that distinguish guest failure, assertion failure, timeout,
  truncation, media mismatch, state mismatch, and emulator crash.
- Owned-process lifecycle and cleanup proven under normal exit, failure, cancellation,
  and host restart.
- An emulator-neutral assertion schema with Redux and frozen-DuckStation adapters.

Exit condition:

- The representative migration suite runs unattended, never touches the normal user
  profile, and leaves no unowned emulator process or ambiguous partial result.

### WP6 — Implement the required RE and provenance surface

Port capabilities by campaign need, not by DuckStation method count.

At minimum qualify:

- conditional execute/read/write breakpoints with callbacks;
- bounded non-halting execution, access, and function tracing;
- complete pagination/truncation accounting;
- instruction-attributed reads and writes;
- MIPS register, COP0, GTE, `hi/lo`, delay-slot, and call/return context;
- CD-ROM and DMA provenance into RAM;
- CPU/DMA origins for GPU commands and VRAM/CLUT changes;
- CPU/DMA origins for SPU RAM, voices, and pitch-related state;
- coherent CPU/RAM/GPU/SPU capture;
- symbols, typed records, and Ghidra synchronization;
- a documented substitute for any current reverse-execution use case not ported.

Every timing-sensitive tracer requires an A/B neutrality test against an uninstrumented
movie replay. A zero-hit result is accepted only when the traced window and accounting
prove completeness.

Exit condition:

- One action/state, collision, actor/AI, GPU/render, SPU/audio, and CD/DMA case each
  reproduce a previously banked causal claim without changing the control replay.

### WP7 — Rebuild persistent offline evidence

Deliverables:

- A Redux-native trace-capsule format or a documented emulator-neutral successor.
- Frame-exact manifests for registers, RAM, VRAM, SPU RAM, checkpoints, and block flow.
- Error/truncation accounting and independent pristine-media control fingerprints.
- Deterministic offline readers for summary, change-point, range, hotspot, and
  cross-movie queries.
- External storage and preservation manifests; no copyrighted/game-derived capsule
  bytes in Git.
- A bridge/index that preserves discoverability of existing DuckStation capsules.

Exit condition:

- A representative Redux capsule reproduces byte-identically where expected, detects
  deliberate corruption, and answers the same semantic query without a running
  emulator. Existing DuckStation capsules remain independently readable.

### WP8 — Migrate fixtures and behavioral evidence

Classify every existing movie:

- cold-boot input stream potentially convertible;
- DuckStation-state-anchored and requiring a new Redux semantic anchor;
- historical comparison only;
- obsolete/superseded;
- missing or blocked.

For state-anchored cases:

- reproduce the anchor from pristine cold boot where practical;
- otherwise create a Redux state only after confirming the same scene, actor/object
  roster, player state, counters, and relevant memory fields;
- never accept visual similarity as state equivalence.

For every re-recorded or converted movie:

- hash-pin the external movie and anchor;
- record operator intent and semantic milestones;
- compare against existing pristine assertions;
- preserve both old and new provenance;
- document disagreements instead of normalizing them into the Redux baseline.

Exit condition:

- Every load-bearing Phase-2/Phase-4 fixture has a Redux-native reproduction or a
  documented blocker that prevents operational cutover.

### WP9 — Run differential qualification

Start with a representative pilot:

1. one pristine cold-boot level-completion movie;
2. one state-anchored player action;
3. one collision or mover case;
4. one GPU/render case;
5. one SPU/XA/audio case;
6. one CD/DMA/overlay-loading case;
7. one save/load/frontend lifecycle case.

For each case compare semantic outcomes, not emulator-private serialization:

- scene and objective progression;
- player and actor state;
- counters and lifecycle transitions;
- relevant memory/register fields;
- framebuffer/VRAM assertions;
- SPU/audio assertions;
- disc/overlay/asset identity;
- expected writer or provenance chains.

After the pilot, run:

- Training and all 15 main stages from cold boot;
- bonus stages and special objectives applicable to the oracle;
- FMV, XA, results, frontend, save/load, game-over, and continue paths;
- pause, death/respawn, transition, soak, and repeated-use cases;
- pristine and intentionally known-bad mutation controls.

Every Redux-versus-DuckStation disagreement must be adjudicated using static
disassembly, retained evidence, an additional emulator, or real hardware where
practical. Do not automatically call DuckStation or Redux correct.

Exit condition:

- The complete required oracle passes on Redux, known-bad controls fail in the expected
  detector classes, and all cross-emulator differences are resolved or explicitly
  bounded as non-load-bearing.

### WP10 — Perform clean-checkout cutover and documentation closure

Deliverables:

- Provision a fresh Redux checkout using only committed non-copyrighted source plus the
  declared external fixture set.
- Rebuild and hash-verify Redux.
- Reproduce all migration generators and generated artifacts.
- Run the safe suite, Redux core tests, movie/state corruption tests, scenario tests,
  fixture validators, vault validation, and the executable oracle.
- Prove generated artifacts byte-identical where their schemas promise determinism.
- Update `AGENTS.md`, the roadmap hub, Phase 2, Phase 4, the API index, capsule
  experiment, skills, and operator documentation.
- Mark DuckStation requirements as historical/secondary only after the gate passes.
- Preserve exact DuckStation runtime/source/readers and a documented command for
  inspecting historical evidence.

Exit condition:

- A fresh verifier reproduces the cutover from a clean checkout and rejects at least
  one deliberately corrupted source, runtime, movie, state, capsule, and media input.

## Capability acceptance matrix

| Capability | Current authority | Redux migration requirement | Cutover critical |
|---|---|---|---|
| Pristine media identity | Phase 0 + DuckStation scenarios | CUE/track/serial hash verification after mount | yes |
| Cold-boot movies | DuckStation movie/oracle lane | Core Redux movies with exact frame semantics | yes |
| State-anchored movies | DuckStation-specific states | Semantically recreated Redux anchors | yes |
| Digital and analog input | DuckStation movie v3 | Complete two-port effective-input injection | yes |
| Frame advance | DuckStation RPC | Serialized counter and exact advance/stop reason | yes |
| Behavioral assertions | Phase-2 oracle/scenarios | Emulator-neutral schema and Redux adapter | yes |
| Access/exec/function traces | DuckStation RPC | Bounded, attributed, non-halting Redux trace | yes |
| GPU/SPU/CD/DMA provenance | DuckStation RPC | Qualify cases actually required by campaigns | yes |
| Atomic capture | DuckStation RPC | Coherent Redux multi-domain capture | yes |
| Trace capsules | DuckStation external evidence | Redux/equivalent validated persistent evidence | yes for Phase 4 |
| Reverse execution | DuckStation RPC | Port or prove an accepted use-case replacement | conditional |
| TAS editing/branch UI | DuckStation movies | Optional after deterministic playback | no |
| Historical DuckStation evidence | Preserved runtime bundles | Keep readable and hash-verifiable | yes |
| Independent emulator control | Frozen DuckStation / other | Retain at least one secondary implementation | strongly recommended |

## Instrumentation-neutrality protocol

Every timing-sensitive Redux feature must pass this protocol:

1. Start two fresh isolated profiles from the same verified anchor.
2. Run the same movie once with no instrumentation and once with only the candidate
   instrumentation armed.
3. Capture hashes at multiple pre-trigger, trigger, and post-trigger frames.
4. Compare CPU registers/cycle, RAM, scratchpad, GTE, VRAM, SPU RAM, frame counter,
   scene, movie cursor, and declared device state.
5. Reject on any unexplained difference, dropped event, incomplete page, overrun,
   truncation, or altered input.
6. Repeat at least three times and after a save/load boundary.

This protocol directly guards the failure class recorded by
[[EXP_2026-07-12_phase2_behavioral_oracle|the Phase-2 behavioral oracle]], where armed
instrumentation altered movie behavior.

## Migration milestones

| Milestone | Meaning | DuckStation role |
|---|---|---|
| R0 — preserved | Current evidence platform and fixtures are hash-inventoried | required |
| R1 — movie prototype | Redux records/replays a narrow deterministic digital case | required |
| R2 — qualified pilot | Representative movie/state/GPU/SPU/CD cases pass differential controls | required oracle |
| R3 — campaign-capable | Required Phase-2/4 scenarios and capsules have Redux equivalents | fallback + oracle |
| R4 — operational cutover | Full exit gate and clean-checkout proof pass | optional secondary validator |
| R5 — maintenance mode | Redux is the sole daily dependency; old evidence remains readable | historical/cross-check only |

No milestone may be advanced through documentation wording alone.

## Exit gate — DuckStation no longer required for daily work

All predicates must be mechanically derived and green:

- [ ] WP0 preservation manifest is complete and freshness-checked.
- [ ] WP1 maps every load-bearing current consumer with zero unexplained gaps.
- [ ] Redux source, submodules, toolchain, runtime, and binary are reproducibly pinned.
- [ ] Digital and analog movies pass cold-boot and state-anchor determinism controls.
- [ ] Media, BIOS, settings, cards, states, movies, source, and runtime identity are
      verified and corruption-tested.
- [ ] Instrumented and uninstrumented replays are equivalent for every required trace
      family.
- [ ] The representative pilot passes on pristine and fails on known-bad controls.
- [ ] The complete required Phase-2 oracle and Phase-4 scenario surface pass on Redux.
- [ ] Required DuckStation-native fixtures and capsules are migrated or explicitly
      retained with no orphaned gate dependency.
- [ ] Redux persistent evidence reproduces and remains queryable without the emulator.
- [ ] All unresolved cross-emulator differences are adjudicated or explicitly
      non-load-bearing.
- [ ] A clean-checkout verifier reproduces the runtime, evidence, tests, and gate using
      only the declared external fixture set.
- [ ] Vault, `AGENTS.md`, skills, API indexes, roadmap notes, and operator instructions
      agree on the new primary platform.
- [ ] Frozen DuckStation historical evidence remains hash-verifiable and readable.

The gate must exit nonzero when any predicate or consumed evidence guard fails. It must
not trust hand-authored `passes`, `complete`, or `closed` booleans.

## Remaining role of DuckStation after cutover

After R4/R5, DuckStation is not required for ordinary work, new recordings, scenario
execution, or release regression. It remains relevant for:

- replaying or inspecting evidence that was created natively in DuckStation;
- differential checks when Redux behavior is uncertain;
- distinguishing original-game behavior from a Redux emulation defect;
- preserving the provenance of conclusions already accepted from its exact runtime;
- adjudicating rare GPU, SPU, CD, timing, or controller differences until real
  hardware or another emulator provides the independent control.

Feature parity cannot reproduce the independence benefit. A deterministic Redux can
reproduce a Redux bug deterministically.

## Expected effort and sequencing

Planning estimate for one experienced Redux C++ engineer:

- deterministic digital prototype: roughly 1–2 weeks;
- production-quality two-port digital/analog movies, state identity, exact frame
  control, headless control, and determinism tests: roughly 4–8 engineer-weeks;
- TAS editing/branch/rerecord UI, if wanted: another 2–6 weeks;
- fixture migration and scenario qualification: roughly 1–3 weeks after the required
  platform exists;
- broader provenance/capsule parity: campaign-driven and potentially longer than the
  movie subsystem.

The recommended order is WP0–WP4, then the representative parts of WP5–WP9. Expand
provenance features only when an actual roadmap campaign requires them. Do not postpone
the pilot until every historical DuckStation API is cloned, and do not cut over after
the pilot alone.

## Autonomous implementation ratchet

The durable controller is `tools/pcsx_redux_migration_ratchet.sh`; its immutable
execution/rejection contract is `engineering-specs/pcsx-redux-migration.md`.

Each round owns isolated ABL and Redux branches:

1. a fresh implementation owner reads the immutable plan/contract snapshots, cumulative
   progress ledger, and exact prior verifier gaps, then commits safe work in one or
   both repositories;
2. a different fresh hard-ass verifier receives detached checkouts of both exact
   commits;
3. acceptance ends the run only when Redux is fully armed as the daily ABL replacement
   under every exit predicate in this note;
4. rejection is preserved verbatim for the next implementation owner;
5. an external blocker pauses only after the verifier confirms a precise
   operator-owned input.

The controller is HUP-resistant, maintains atomic stage state, retries transient Codex
process failures, and preserves branch/WIP/log context across a host outage. It never
merges or pushes. A stopped or interrupted run resumes from its run-owned `resume.sh`.

## Current status

**IN PROGRESS — NOT MIGRATED.** Ratchet run
`redux-migration-20260730-015052-955500` began on 2026-07-30 from ABL
`3f70387f5b651a564effdba153dff84a90a59a62` and Redux
`3e10093ad9cc2fb445668928b3d0f87abeccd29c`. Its durable state is under
`~/.local/state/pcsx-redux-migration-ratchet/runs/`.

The local Redux clone and source inspection establish feasibility, not migration
closure. No Redux movie, scenario, oracle, or evidence artifact has passed the complete
cutover gate in this note yet. Only a gap-free hard-ass verifier decision over exact
clean ABL and Redux commits may change this status to migrated.
