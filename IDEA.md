---
  title: A Bug's Life — Whole-Game Reverse Engineering and Reliable Modding
  project: ABL
  platform: Sony PlayStation
  game_id: SCUS-94288
  status: active
  ---

  # A Bug's Life — Whole-Game Reverse Engineering and Reliable Modding

  ## Project overview

  This project reverse-engineers the USA v1.0 PlayStation release of Disney-Pixar’s *A Bug’s Life* (`SCUS-94288`).

  The long-term goal is to understand and reconstruct the pristine retail game well enough that substantial modifications can be made
  without repeatedly introducing unrelated gameplay, graphics, audio, physics, or memory regressions.

  This is not merely a collection of game patches. It combines:

  - Static reverse engineering and byte-exact ASM reconstruction.
  - Goal-directed C decompilation.
  - Runtime investigation through a custom DuckStation debugger API.
  - Disc, executable, overlay, level, model, audio, and asset-format analysis.
  - Deterministic behavioral tests covering the original game.
  - Machine-readable registries for addresses, mechanics, state, hooks, overlays, and fixtures.
  - An Obsidian knowledge vault designed to preserve findings across AI and human sessions.
  - A guarded modding pipeline that builds every experiment independently from pristine retail data.

  The project distinguishes between reconstructing code bytes and actually understanding the game. Resolved ASM can prove instruction
  identity and control flow, but it does not automatically establish field types, state ownership, valid domains, initialization,
  lifecycle, cross-system dependencies, or safe extension points.

  The central objective is therefore to “solve” the pristine game as an interconnected program before treating feature-heavy modding as
  production-ready.

  ## The two meanings of “solved”

  ### Modding-safe solve

  A subsystem is modding-safe when every dependency crossed by a proposed modification is sufficiently understood and guarded.

  This requires more than knowing an address or successfully applying a patch. The relevant state, readers, writers, callbacks, overlays,
  lifecycle, ABI, asset constraints, and downstream behavior must be known well enough that regressions can be detected automatically.

  A complete C decompilation is not necessarily required for this level, but the affected paths must be semantically understood.

  ### Whole-game solve

  The larger goal is a reusable reconstruction of the entire pristine game:

  - Reproducible resident executable and overlay reconstruction.
  - Game code separated from PsyQ/SDK code.
  - Functions assigned stable semantic roles.
  - Typed globals, structs, tables, callbacks, and dispatch systems.
  - Known state ownership, initialization, reset, and retirement behavior.
  - Characterized gameplay, rendering, animation, physics, collision, audio, AI, HUD, menus, objectives, saving, and scene transitions.
  - Deterministic behavioral coverage across the campaign.
  - Decoded asset schemas with validated round trips.
  - A stable extension architecture that does not rely on unsafe native-state abuse or scattered, manually packed code caves.

  The roadmap in `ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md` is the authoritative
  description of this process. Current phase status should always be read from the repository and validated mechanically; old chat
  summaries are not authoritative.

  ## Pristine retail authority

  The hash-verified pristine retail image is the sole authority for original-game behavior and the sole base for patched builds.

  The following rules are non-negotiable:

  - Never patch ALLMODS, another MOD image, or an earlier derivative.
  - Verify the pristine input before every build.
  - Copy pristine data into a new output and apply each selected module exactly once.
  - Build every module combination independently from pristine.
  - Never construct one MOD by adding patches to another MOD.
  - Treat ALLMODS only as historical comparison and regression evidence.
  - Never treat ALLMODS as an oracle for original behavior.
  - Do not commit copyrighted retail files, disc images, save states, movies, or extracted media.

  The build system pins the expected pristine staging tree and produces manifests recording inputs, modules, toolchain versions, changed
  files, and output hashes.

  A successful byte patch is not a behavioral validation. Disc, code, and asset changes must be exercised through an appropriate cold-boot
  scenario.

  ## The Obsidian vault

  `ObsidianVault/` is the project’s durable knowledge system. It is not intended to be an informal notebook or a replacement for
  authoritative machine-readable data.

  Its purpose is to let future humans and agents locate, evaluate, regenerate, and safely consume prior findings without repeating every
  investigation.

  ### Vault organization

  - `Canon/` contains confirmed knowledge about the pristine original game.
  - `Experiments/` contains runtime investigations, traces, hypotheses, failed attempts, controls, and causal evidence.
  - `Mods/` contains MOD-private state, hooks, cave allocations, intended behavior, and deliberate deviations from retail behavior.
  - `Playbooks/` contains operational workflows, phase plans, exit gates, and troubleshooting procedures.
  - `Sessions/` contains chronological handoffs and work history.
  - `Archive/` preserves superseded, disproven, wrong, or unsorted legacy material for provenance.
  - `_Revamp/` contains vault migration, consistency, conflict, and validation material.

  Canon describes the original game. Mods describe intentional changes. These must never be conflated.

  A claim from Archive must not be promoted back into Canon without new evidence. When a finding is corrected, the old claim should be
  explicitly marked as superseded so another session does not accidentally revive it.

  ## Vault philosophy: bank knowledge, not conclusions

  A finding is not finished because it appeared to work once, was mentioned in chat, or was described in prose.

  A reusable finding should include:

  1. Provenance: pristine media identity, executable or overlay identity, fixture hashes, trigger, frame or cycle, and the exact
  observation.
  2. An authoritative machine representation: symbols, ASM, matching or documentation-grade C, a typed schema, registry, or validator.
  3. Reproducible evidence: the smallest deterministic scenario, movie, state, trace, or static procedure that supports it.
  4. An executable guard: a test, assertion, freshness check, behavioral comparison, or validator that can fail.
  5. Correct vault placement and links to source, evidence, tests, roadmap rows, residuals, and superseded claims.
  6. A future-MOD consumption contract describing ownership, valid domains, lifecycle, ABI, downstream consumers, and unsafe assumptions.
  7. Clean-checkout durability, with all non-copyrighted generators and source committed.
  8. Explicit confidence, residuals, blockers, and conditions that would reopen the finding.

  Conversation-only conclusions and hand-authored `passes: true` summaries are not sufficient.

  Observation, inference, and causal confirmation must be kept distinct. Attractive conclusions should be weakened or rejected when
  retained evidence cannot regenerate them.

  ## Custom DuckStation external-debugger API

  This project relies heavily on a custom local DuckStation fork with an external JSON-RPC debugger API.

  It turns the emulator into a programmable reverse-engineering laboratory rather than relying only on manual gameplay and visual
  inspection.

  The API can provide:

  - CPU registers, disassembly, stack state, symbols, and xrefs.
  - Typed RAM reads, writes, arrays, structs, pointer chains, and scatter operations.
  - Execute, read, write, and conditional breakpoints.
  - Non-halting execution and memory-access tracing.
  - Function entry/exit tracing with arguments, returns, call stacks, and touched memory.
  - Reverse execution through bounded checkpoints and deterministic replay.
  - Save-state inspection and controlled loading.
  - Scripted controller input and timing-matched input movies.
  - Fixed-frame advancement and predicate-based execution.
  - GPU state, VRAM reads, texture decoding, object picking, frame comparisons, and CPU-to-GPU causality.
  - CD/DMA transfer tracing and disc-to-RAM provenance.
  - SPU voice state, audio events, sample-transfer provenance, and pitch information.
  - Atomic CPU/RAM/GPU/movie/SPU captures at a common emulated instant.
  - Declarative experiments that compare controlled baseline and perturbation runs.

  The Canon entry point is:

  `ObsidianVault/Canon/Indexes/DuckStation_API_Index.md`

  The generated method manifest is:

  `tools/duckstation_rpc_method_manifest.md`

  The checked-out `~/duckstation` source, debugger documentation, running binary, and runtime method behavior remain authoritative. The
  fork evolves, and some API features may exist only in uncommitted local work. Record the fork revision, dirty state, and binary hash when
  that affects reproducibility.

  ### DuckStation operating rules

  Every debugger experiment should use:

  - A freshly created absolute config directory.
  - A dedicated loopback port and authentication token.
  - A verified emulator process owned by that config directory.
  - Hash-verified mounted media, not merely a matching serial or filename.
  - A named and hash-pinned fixture where save states or movies are involved.
  - Fixed timing and scripted input.
  - Explicit trace limits and truncation accounting.
  - Cleanup through the same isolated-instance launcher.

  Never use the operator’s normal DuckStation profile. Never broadly kill DuckStation processes.

  Save states and cold boots provide different kinds of evidence:

  - Use save states for narrow runtime experiments against already-loaded pristine code and data.
  - Use a cold boot with a timing-matched input movie for disc, executable, overlay, or asset changes.

  Instrumentation must be re-armed after loading a state. Breakpoints and traces can affect interpreter mode and timing, so instrumented
  and uninstrumented replay should not be assumed equivalent without an A/B check.

  ## Reverse-engineering methodology

  The preferred workflow is:

  1. Read `AGENTS.md` and the applicable roadmap or subsystem note.
  2. Inspect the Git worktree and preserve unrelated operator WIP.
  3. Select one bounded question or hypothesis.
  4. Identify the pristine behavioral oracle and required fixtures.
  5. Reproduce the behavior before changing anything.
  6. Capture media identity, trigger, timing, relevant state, and trace limits.
  7. Compare a positive case with a meaningful negative control.
  8. Distinguish observation from interpretation.
  9. Use controlled runtime perturbation or code analysis to test causality.
  10. Promote a confirmed result into the correct symbol, ASM, C, schema, registry, or validator.
  11. Add a test or behavioral assertion capable of falsifying the claim.
  12. Update and cross-link the appropriate Obsidian notes.
  13. Verify from a clean checkout plus the declared external fixture set.

  Diagnose before patching. A patch should test an already-stated hypothesis, not substitute for understanding.

  ## Static reconstruction and C decompilation

  The repository contains substantial reconstructed ASM and ongoing C decompilation.

  These layers serve different purposes:

  - Resolved ASM establishes byte identity and exact control flow.
  - Symbols give addresses stable semantic names.
  - Documentation-grade C helps explain behavior without claiming a matching build.
  - Matching C becomes a rebuildable representation of the original routine.
  - Typed schemas and registries describe state that cannot be safely represented by code listings alone.

  Do not equate a resolved function with a solved subsystem. A subsystem includes its callers, callbacks, tables, data formats, state
  lifetime, scene variants, and cross-system effects.

  ## Modding architecture

  The modding pipeline supports symbol-driven ASM patches, freestanding MIPS C code caves, and data edits.

  As a general rule:

  - “Where is it?” and “how many exist?” are usually asset or level-data questions.
  - “How does it behave?” is usually a code or state-machine question.

  Typical data lanes include object placement, collectibles, seed actors, terrain, collision, models, textures, and level containers.

  Typical code lanes include player behavior, berry throwing, physics, enemy AI, damage, audio dispatch, HUD logic, and new state machines.

  MOD-private state must have an explicit owner, valid domain, initialization, reset, and retirement contract. Native selectors must not be
  extended outside their confirmed domain without auditing every consumer.

  Hooks must record displaced instructions, delay slots, continuation address, register clobbers, stack behavior, `hi/lo`, GTE state, and
  intentional semantic changes. Hook safety should be checked against the actual built cave, not merely the intended source.

  ## Behavioral oracle and regression prevention

  The project is building an executable oracle for pristine behavior.

  Useful assertions include:

  - Media and scene identity.
  - Player state, health, lives, power state, and movement.
  - Objective and collectible counters.
  - Actor, contact, plant, projectile, and allocation pools.
  - Camera and framebuffer behavior.
  - Entry, completion, death, respawn, pause, transition, and results paths.
  - Frame, GPU, and SPU evidence where appropriate.
  - Long-running and campaign-spanning behavior.
  - Known historical regressions such as broken projectile arcs, missing geometry, allocator hangs, and incorrect audio pitch.

  A behavioral oracle must do both:

  - Pass against verified pristine behavior.
  - Fail against a meaningful known-bad mutation.

  A green test that cannot be made red is not strong closure evidence.

  ## External fixtures and preservation

  Copyrighted or operator-owned fixtures remain outside Git. This may include:

  - Retail disc images and extracted files.
  - Save states.
  - Input movies.
  - Audio and video media.
  - Captures and large generated disc builds.

  Every required external fixture should be:

  - Centrally listed.
  - Hash-pinned.
  - Classified by media type.
  - Referenced by its generator or test.
  - Included in the declared preservation set.
  - Checked for presence and identity before use.

  Tracked code must not silently depend on an untracked local source file.

  ## Project roadmap

  The project is organized into gated phases:

  - Phase 0: establish immutable identity, protected builds, and reproducibility.
  - Phase 1: inventory the whole-game mechanics and campaign surface.
  - Phase 2: build the pristine behavioral oracle.
  - Phase 3: reconstruct semantic architecture and state ownership.
  - Phase 4: solve gameplay and engine subsystems.
  - Phase 5: prove cross-system and full-campaign integration.
  - Phase 6: complete matching source, overlays, assets, and toolchain reconstruction.
  - Phase 7: audit whole-game closure and establish a production MOD foundation.

  Phases may overlap only where later work does not consume unresolved conclusions from an earlier phase.

  The current phase status must be verified from the roadmap, machine-generated gate artifacts, tests, and retained evidence. A phase
  should be reopened when its closure depends on missing, contradictory, irreproducible, or semantically invalid evidence.

  ## Instructions for Hermes Agent

  When working in this project:

  - Treat `AGENTS.md` as mandatory.
  - Preserve dirty operator work.
  - Prefer read-only investigation until the requested scope authorizes changes.
  - Never use ALLMODS as a build base or pristine behavioral authority.
  - Verify hashes rather than trusting names, serials, summaries, or prior chat claims.
  - Use the smallest reproducible experiment.
  - Never manufacture a passing result or weaken a test to obtain closure.
  - Update machine-readable knowledge before updating prose.
  - Record failed hypotheses and platform gotchas.
  - Keep generated discs and copyrighted assets out of commits.
  - Validate from a clean checkout whenever claiming durable completion.
  - Report behavioral closure and knowledge closure separately.
  - State residuals plainly.
  - Do not call a subsystem or phase solved merely because its current gate prints green; inspect whether the gate actually validates the
  underlying semantics.

  ## Definition of success

  Success is not simply adding more features.

  Success is reaching a point where a new feature can be designed against known interfaces, built once from pristine, and evaluated by an
  oracle that identifies unintended changes across the rest of the game.

  The finished project should make reverse-engineering knowledge cumulative, mod behavior intentional, builds reproducible, and regressions
  exceptional rather than routine.
