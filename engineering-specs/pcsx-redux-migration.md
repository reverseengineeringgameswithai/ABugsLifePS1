# PCSX-Redux full-migration ratchet contract

## Objective

Implement and independently verify the complete migration defined by:

`ObsidianVault/Playbooks/PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency.md`

The Obsidian plan snapshot captured at ratchet start is authoritative. This contract
adds execution and rejection rules; it does not narrow, reinterpret, defer, or replace
any requirement in the plan.

The terminal outcome is not “Redux gained useful ABL features.” It is:

> PCSX-Redux is fully armed to be the primary and sole emulator required for ordinary
> ABL reverse engineering, deterministic replay, scenario automation, persistent
> offline evidence, and release regression. Frozen DuckStation remains historical
> evidence and an optional independent cross-check, not a daily dependency.

## Repository scope

The ratchet owns two isolated Git branches and worktrees:

- the ABL repository, containing contracts, adapters, scenarios, fixture manifests,
  evidence tooling, tests, and Obsidian knowledge;
- the PCSX-Redux repository, containing the emulator-core and control-surface changes.

The operator checkouts are read-only inputs. The ratchet must never merge, push, reset,
clean, or overwrite either operator checkout. It must preserve unrelated WIP.

The local DuckStation source/runtime is read-only historical and differential evidence.
It may be inspected and run under its documented isolation rules, but it must not be
edited by this migration ratchet.

## Authority and safety

- Read and obey the ABL `AGENTS.md` snapshot and the candidate checkout’s `AGENTS.md`
  completely.
- Use only the hash-verified pristine SCUS-94288 retail media as original-game
  behavioral authority and patch/build base.
- ALLMODS and other derivatives are comparison or known-bad evidence only.
- Never commit retail media, BIOS, memory cards, saves, movies, captures, trace
  capsules, credentials, tokens, or generated disc images.
- Centrally hash-pin, media-classify, and declare every external fixture.
- Use fresh absolute emulator profiles, pinned binaries, verified mounted media, and
  exact-owned process cleanup.
- Keep cold-boot and save-state evidence distinct.
- Diagnose and retain the observation before changing emulator code.
- Do not copy code from the local CC BY-NC-ND DuckStation tree into GPLv2 PCSX-Redux.
  Reimplement from the plan, independently written contracts, tests, public hardware
  behavior, and observations.

## Persistent context

Every implementer and verifier round must read:

1. the immutable run snapshot of this contract;
2. the immutable run snapshot of the Obsidian migration plan;
3. the run-start ABL and Redux source-state inventories;
4. the current candidate versions of the roadmap, plan, machine layers, tests, and
   relevant source;
5. the cumulative progress ledger;
6. the immediately preceding verifier feedback.

An agent may not treat its conversation memory, a prior summary, a generated
`complete` field, or the current dirty operator tree as authority.

## Required migration surface

All WP0–WP10 work packages and every exit-gate checkbox in the Obsidian plan are
binding. At minimum the final candidate must prove all of the following.

### Evidence-platform preservation

- Freshly inventory the exact DuckStation source, binary/runtime, API, movie, save,
  scenario, oracle, capsule, reader, generator, test, and external-fixture surface
  actually consumed by ABL.
- Preserve load-bearing historical evidence and classify obsolete/non-load-bearing
  items without silently dropping dependencies.
- Keep existing DuckStation-native evidence readable after cutover.

### Redux reproducibility

- Pin Redux upstream revision, recursive submodules, toolchain, build flags, resources,
  source status, and runtime binary.
- Build from a clean checkout using only committed source and declared external inputs.
- Expose a machine-readable capability report with source, dirty, binary, runtime,
  API, and schema identities.
- Reject hidden imports from operator or other dirty trees.

### Deterministic input movies

- Implement a core input-source/movie subsystem, not GUI automation or a
  digital-only Lua approximation.
- Support two ports, controller type/connection, every digital button, explicit
  releases, four 8-bit analog axes, analog/config mode, and relevant pad protocol
  state.
- Prevent physical host input leakage during playback.
- Latch effective input at one documented emulation-owned boundary.
- Serialize a 64-bit frame counter and implement exact frame advance.
- Define sample-zero, first-frame, reset/load/unmount, completion, truncation, cursor,
  and error semantics.
- Support verified cold-boot and state anchors.
- Bind movie media, BIOS, settings, memory card, source, binary, runtime, controller,
  state, boundary, and format identity.
- Fail loudly on state deserialization or identity mismatch.

### Determinism and instrumentation neutrality

- Repeated clean-profile cold-boot and state-anchored runs must reproduce all declared
  deterministic domains.
- Compare uninstrumented and instrumented runs at pre-trigger, trigger, and
  post-trigger frames.
- At minimum compare CPU registers/cycle, RAM, scratchpad, GTE, VRAM, SPU RAM, frame
  counter, movie cursor, scene, and declared GPU/SPU/CD/controller state.
- Exercise save/load boundaries and corrupt/truncated fixtures.
- The candidate must retain and guard the known instrumentation/movie-desynchronization
  failure class rather than assuming the new implementation is neutral.

### Automation and scenarios

- Provide isolated, authenticated/local control suitable for unattended ABL work.
- Provide deterministic boot/load/verify/play/instrument/capture recipes.
- Provide declarative, schema-validated emulator-neutral behavioral assertions and a
  Redux adapter.
- Provide batch progress, per-job results, cancellation, named-anchor resumption,
  timeouts, explicit stop reasons, structured errors, and exact-owned cleanup.
- A crash, connection loss, partial result, or host restart must not be reported as a
  successful scenario.

### RE and provenance capability

- Qualify the campaign-required forms of conditional execute/read/write breakpoints,
  bounded access/exec/function traces, complete pagination/truncation accounting,
  instruction attribution, register/GTE/delay-slot/call context, CD/DMA provenance,
  GPU/VRAM/CLUT causality, SPU/voice/pitch provenance, coherent multi-domain capture,
  symbols, typed Ghidra structures, and any accepted reverse-execution replacement.
- Port by real ABL use case, not by matching the DuckStation method count.
- Every timing-sensitive mechanism must pass neutrality controls.

### Persistent offline evidence

- Produce a Redux-native capsule or an explicitly emulator-neutral successor with
  source/binary/media/movie/state/settings identity, no truncation, control
  fingerprints, deterministic readers, corruption detection, and external
  preservation.
- Retain discovery and readability of existing DuckStation capsules.
- Prove representative summary, change-point, range, hotspot, and cross-movie queries
  without a running emulator.

### Fixture and oracle migration

- Machine-classify every load-bearing DuckStation movie and state.
- Recreate emulator-specific state anchors semantically from pristine behavior.
- Preserve operator intent and milestone assertions for re-recorded or converted
  movies.
- Do not accept visual similarity or successful completion as semantic equivalence.
- Run a representative differential pilot covering cold boot, state anchor, player
  action, collision/mover, GPU, SPU/XA, CD/DMA/overlay, and save/frontend lifecycle.
- Then reproduce the complete required Phase-2 oracle and active Phase-4 scenario
  surface, including campaign breadth, transitions, lifecycle, FMV/XA, frontend,
  results, pause, death/respawn, soak, and known-bad mutation sensitivity.
- Adjudicate every load-bearing Redux/DuckStation disagreement rather than selecting
  the convenient result.

### Knowledge closure and cutover

- Update authoritative machine layers before generated summaries and Obsidian prose.
- Keep original facts in Canon, runtime work in Experiments, and MOD-private state in
  Mods.
- Update the roadmap, migration plan, API/capability indexes, fixture and preservation
  manifests, operator docs, skills, and `AGENTS.md` only when the evidence supports the
  new platform status.
- Provide falsifiable generators/tests for every decisive cutover claim.
- Prove a clean-checkout cutover using only the declared external fixture set.
- Preserve a documented, hash-verified way to inspect historical DuckStation evidence.

## Implementer obligations

Each implementer round must:

1. inspect both current candidate worktrees and preserve any interrupted WIP;
2. re-read the immutable plan/contract and the latest verifier feedback;
3. select the highest-leverage unresolved dependency rather than redoing verified work;
4. implement safe autonomous work in the appropriate repository;
5. update authoritative machine representations before documentation;
6. add or strengthen tests and deliberately falsify important guards;
7. validate in proportion to the work, including clean-checkout or external fixtures
   when load-bearing;
8. commit all scoped non-copyrighted changes to the two ratchet branches;
9. leave both implementation worktrees clean;
10. report both exact tested commits and all remaining risks honestly.

The implementer is not allowed to weaken an acceptance criterion, relabel missing
evidence as a bounded residual unless the plan permits it, or declare success based on
future work.

## Hard-ass verifier obligations

Every implementer candidate goes to a fresh detached verifier checkout for both
repositories. The verifier did not implement the candidate and must remain
read-only-in-intent.

The verifier must reject unless PCSX-Redux is **fully armed as the main ABL replacement
in practice**, not merely feature-rich in theory. It must:

- independently regenerate all load-bearing evidence;
- inspect actual Redux C++ behavior and ABL consumers, not only documentation and green
  summary fields;
- falsify capability, freshness, coverage, corruption, identity, truncation,
  isolation, cleanup, and known-bad guards;
- prove the plan’s complete WP0–WP10 surface and every cutover checkbox;
- prove repeated and instrumented/uninstrumented determinism;
- prove the full required oracle and Phase-4 scenario surface on pristine media;
- prove clean-checkout reproduction for both repositories;
- verify external fixture and historical-evidence preservation;
- reject any undeclared source or fixture dependency;
- reject documentation-only, prototype-only, partial-campaign, or
  “implemented but not integrated” closure;
- reject claims that new Redux recordings validate Redux independently;
- reject any migration that makes prior evidence unreadable;
- return exact, reproducible, prioritized gaps for the next implementer.

The verifier may return `accepted` only with no gaps and no required input. It returns
`rejected` whenever safe autonomous work remains. It returns `blocked_external` only
when it confirms an exact operator-only input that cannot be generated, recovered, or
replaced safely.

## Structural and clean-checkout rejection rules

Reject or return to implementation when:

- either reported commit differs from the corresponding candidate HEAD;
- either implementation worktree is dirty when verification begins;
- the verifier changes either detached checkout;
- a required generator depends on untracked source;
- generated artifacts are stale or trust authored pass/closed booleans;
- a fixture is missing, unpinned, misclassified, or absent from the preservation set;
- required validation is skipped because the fixture or runtime is inconvenient;
- an emulator process/profile cannot be tied to an exact owned launch;
- a candidate weakens tests, contracts, roadmap requirements, or prior evidence;
- an accepted verdict contains a gap or required input.

## Loop and terminal states

The controller performs:

1. implementer candidate;
2. fresh hard-ass verifier;
3. if accepted, write a durable result and stop;
4. if rejected, persist the exact verifier gaps and start a fresh implementer;
5. if external input is independently confirmed, persist the exact request and pause.

Agent process, schema, connection, or host failures are infrastructure failures, not
evidence. Preserve both branches, logs, feedback, and controller state, then allow an
exact resume without discarding work.

The ratchet never merges or pushes.

