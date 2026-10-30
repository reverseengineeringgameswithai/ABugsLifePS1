---
kind: playbook
id: PLAYBOOK_game_solving_roadmap
name: Game Solving Roadmap - From Reconstruction to Reliable Modding
status: current
created: 2026-07-11
updated: 2026-07-14
confidence: high
related:
  - SYS_decomp_substrate
  - PLAYBOOK_mod_regression_troubleshooting
  - EXP_2026_07_11_ps1_scenario_regression_framework
  - MOD_hook_cave_manifest_validation
  - EXP_2026_07_11_custom_color_renderer_live_register_regression
---

# Game Solving Roadmap - From Reconstruction to Reliable Modding

## Decision

Broad, feature-heavy ALLMODS development is premature. The project has enough
knowledge to run controlled experiments and prove individual changes, but it does not
yet have enough semantic coverage, executable hook contracts, or behavioral coverage
to compose major features reliably.

Implemented does not mean integrated safely. Features such as the grain-counter crate,
new berry types, six seed tiers, custom terrain, and dynamic HUD elements may remain as
isolated experiments, but should not be treated as production-ready ALLMODS components
until their complete dependency paths meet the gates in this note.

This is a temporary change in emphasis, not an abandonment of modding. Modding becomes
the proving ground for the reverse-engineering model rather than the main source of new
scope.

## Pristine-image authority

The hash-verified pristine retail image is immutable and is the sole source image for
investigation builds and MOD builds.

- Never patch ALLMODS, another existing MOD image, or a prior derivative.
- Verify the pristine input hash before each build, copy it to a new output, and apply
  the selected code/assets/modules exactly once to that output.
- Build every module combination independently from pristine; do not construct one
  combination by adding patches to another combination's output.
- ALLMODS may be booted or inspected only to reproduce historical regressions and to
  compare behavior. It is evidence, not a build base or an oracle for original behavior.
- Pristine behavior is the source of truth. A MOD image supplies only the intentional
  delta being tested against it.

This rule is duplicated in the repository `AGENTS.md` so future AI sessions receive it
as an operating constraint even if they have not yet opened this roadmap.

## Honest project state

The game is highly reconstructed but not yet solved as a safely modifiable program.

- The resident campaign reports 287 functions reconstructed in C and 626 in ASM,
  covering 98.209% of classified resident code bytes. ASM reconstruction proves bytes
  and control flow; it does not by itself prove types, ownership, lifetimes, invariants,
  or safe extension points.
- The current goal-directed C notes explicitly cover selected systems and are not a
  whole-game build target.
- The semantic-state registry currently describes only a small fraction of the game's
  important fields and owners.
- The checked-in live scenarios are concentrated around Training, berries, bonus
  challenges, and recent regressions. They are not yet a whole-game behavioral oracle.
- Hook declarations record locations, displaced bytes, delay slots, and claimed
  clobbers; claimed clobbers are now automatically checked against continuation
  liveness and the independently built diagnostic image. The recovered-extent
  `terrain_emitter_color` row remains explicitly degraded rather than being promoted
  to an exact-confidence discharge.
- The active working tree contains a large amount of interdependent WIP. Without
  hash-pinned configurations and named integration points, the working tree itself
  cannot serve as a release definition.

The custom-color renderer regression is the representative failure. Resolved ASM
already showed that `t8` and `t9` remained live after both hook sites, but the build did
not consume that fact as an enforceable ABI. The knowledge was sufficient to diagnose
the fault after it occurred, but the workflow was not sufficient to prevent it.

## Two meanings of "solve"

### Modding-safe solve

A modding-safe solve means that every system crossed by an active mod is understood
end-to-end and guarded well enough that unintended changes are detected automatically.
This is the immediate target and can be reached without first converting the entire
game to C.

### Whole-game solve

A whole-game solve is the longer-term target:

- Matching, reproducible reconstruction of the resident executable and every overlay.
- All game-owned functions separated from PsyQ/SDK code and assigned semantic roles.
- Typed global state, structs, tables, indirect dispatches, readers, writers, and
  lifecycle behavior.
- Confirmed loader, asset, rendering, collision, animation, audio, event, AI, menu,
  save, and scene-transition contracts.
- Deterministic original-game behavioral coverage across representative states in all
  levels.
- Asset schemas with bounded, validated round trips and explicit size/relocation rules.
- A stable extension architecture that does not depend on scattered, manually packed
  caves and out-of-domain native state.

The roadmap solves the pristine game as a whole. MOD work is deferred as a production
architecture until the final closure phase; diagnostic patches are permitted only as
evidence-producing experiments built independently from pristine.

## Definition of Done for a solved subsystem

A subsystem is not called solved until every item below is satisfied.

1. **Original oracle:** original behavior has a deterministic cold-boot reproduction
   with scene/media identity and observable assertions.
2. **Complete frontier:** relevant callers, callees, callbacks, indirect tables,
   overlays, readers, writers, and downstream consumers have been enumerated.
3. **Typed state:** important fields have widths, signedness, ownership, valid domains,
   initialization, reset rules, and confidence-backed evidence.
4. **Lifecycle:** behavior is characterized through creation, repeated use, retirement,
   death/respawn, pause, scene transition, and reload where applicable.
5. **Original interfaces:** call/return, live state, stack/`ra`, `hi/lo`, GTE,
   delay-slot, memory-effect, callback, overlay, and asset-loading contracts are known
   at every boundary the subsystem crosses.
6. **Campaign breadth:** every applicable level, objective, enemy/actor variant,
   special mode, and exceptional path is covered.
7. **Cross-system behavior:** interactions with player state, physics, rendering,
   animation, audio, HUD, objectives, save/load, and scene transitions are validated.
8. **Source closure:** matching or reviewed semantic source represents the complete
   behavior, and remaining byte/layout mismatches are explicitly bounded.
9. **Durable evidence:** Canon describes confirmed original behavior, Experiments hold
   reproductions and causal evidence, and Mods describe private state and intended
   changes.

Passing one demonstration, observing correct patched bytes, or producing matching ASM
does not satisfy this definition.

## Definition of Finished for a reusable finding

The purpose of the solve is not merely to discover how the game works once. It is to
build a durable body of knowledge that later agents and MOD implementations can locate,
verify, and consume without repeating the investigation. A finding is therefore not
**finished** merely because it was demonstrated in one session, described in chat, or
written into an Obsidian note.

Every confirmed finding must complete the following knowledge-banking requirements:

1. **Ground truth and provenance:** identify the hash-verified pristine media, exact
   executable/overlay/asset identity, fixture hashes, trigger, relevant frame or cycle,
   and the observation that supports the claim. Keep observation, inference, and causal
   confirmation explicitly separate.
2. **Authoritative machine representation:** promote the result into the appropriate
   reusable source of truth: byte-exact ASM and symbols for code identity; matching C
   when achieved; typed structs/state schemas for fields and ownership; registries for
   mechanics, dispatch, assets, overlays, hooks, and lifecycles. Documentation-grade C
   or prose must be labelled as such and must not masquerade as matching source.
3. **Reproducible evidence:** preserve the smallest deterministic experiment, movie,
   state, trace summary, or static-analysis procedure that proves the finding. Record
   exact commands/methods and hashes. Raw transient traces may be discarded only after
   the decisive evidence and regeneration method have been banked.
4. **Executable guard:** add a behavioral assertion, unit test, validator, freshness
   check, or other falsifiable guard wherever practical. A generated summary must be
   recomputed from evidence rather than trusting a hand-authored `passes` field. If no
   automated guard is currently possible, record why and name the experiment that can
   reopen the claim.
5. **Knowledge placement and links:** put confirmed original-game behavior and
   provenance in `ObsidianVault/Canon`, runtime work and failed hypotheses in
   `ObsidianVault/Experiments`, and MOD-private state/hooks/intended deltas in
   `ObsidianVault/Mods`. Link the note to the authoritative source, evidence artifact,
   tests, relevant roadmap row, superseded claims, and remaining unknowns.
6. **MOD consumption contract:** state how a future mod may safely use the finding:
   owners, readers/writers, valid domains, initialization/reset/retirement rules,
   continuation ABI or asset constraints, downstream consumers, and known unsafe
   assumptions. An address without its ownership and lifecycle is not a safe extension
   point.
7. **Durability and clean-checkout closure:** commit all non-copyrighted source,
   schemas, generators, validators, and notes required to reproduce the finding. No
   tracked source may depend silently on an untracked file. Operator-owned/copyrighted
   fixtures remain outside Git, but must be centrally hash-pinned, media-classified,
   named in the evidence, and covered by an explicit preservation requirement.
8. **Confidence, residuals, and supersession:** mark the finding as confirmed,
   partial, inferred, disproven, or blocked using evidence-backed vocabulary. List
   unresolved variants and next experiments. When corrected, update machine-readable
   consumers and link the old claim as superseded so future agents do not revive it.

These requirements are inherited by every phase and subsystem exit gate. If any
required item is missing, the result remains **WIP/partial** even when the immediate
experiment passed. Conversation-only conclusions, untracked implementations,
prose-only address discoveries, and non-regenerable summary booleans cannot be counted
as closed roadmap work.

A phase may retain documented blockers where its own exit gate explicitly permits
them, but it may not describe those blockers as solved. Phase closure must include a
knowledge-closure audit showing that its confirmed findings are discoverable from the
roadmap, represented in the authoritative machine layers, linked to evidence, guarded
where practical, and reproducible from a clean checkout plus the declared external
fixture set.

## Operating rule during the whole-game solve

Until the whole-game closure decision in Phase 7:

- Freeze new feature-heavy ALLMODS scope, including promotion of the grain-counter
  crate and other already-implemented experiments.
- Permit regression fixes, diagnostic instrumentation, test infrastructure, semantic
  reconstruction, and work needed to understand the pristine game.
- Preserve experimental implementations, but keep them off the production integration
  path. They are evidence and regression fixtures, not roadmap priorities.
- Prioritize work from the whole-game mechanics/campaign baseline and dependency graph,
  not from whichever MOD most recently failed.
- Do not store custom values outside a native selector's confirmed domain.
- Do not introduce a hook whose continuation liveness has not been reviewed.
- Do not treat a save-state-only result as validation of a disc/code/asset change.

## Phase execution index

The hub owns the decision, sequence, shared Definition of Done, operating rule, and
release gate. Each linked phase note owns its work packages, dependencies, progress,
evidence, exit gate, and handoff.

> [!warning] Phase 4 read-first note
> Before extending or promoting any Phase 4 campaign, read
> [[Phase 4 - Closure Conundrum and Recovery Plan]]. It records the 2026-08-19
> evidence/closure audit, the Phase 4/5/6 scope overlap, and the recovery rules
> intended to prevent more tracing and bookkeeping from substituting for proof.

| Phase | Execution note | Purpose | Depends on | Status |
|---:|---|---|---|---|
| 0 | [[Phase 0 - Stabilize and Establish Identity]] | Establish reproducible artifacts, build identity, and supported module combinations. | Start | **Behavioral gate closed; knowledge partial** — global clean-checkout source blockers remain |
| 1 | [[Phase 1 - Establish the Whole-Game Mechanics and Campaign Baseline]] | Bound every pristine mechanic, stage, objective, actor, system, and known unknown. | Phase 0 | **Behavioral gate closed; knowledge partial** — 107-row registry/census durable, unknown-role MOD contracts remain |
| 2 | [[Phase 2 - Build the Pristine Whole-Game Behavioral Oracle]] | Create deterministic original behavior across the full campaign and lifecycle. | Phases 0-1 | **Behavioral gate qualified; knowledge partial** — oracle valid, action gate 19/20; A07 spin absence claim superseded |
| 3 | [[Phase 3 - Reconstruct Semantic Architecture and State Ownership]] | Map pristine functions, state, assets, overlays, interfaces, and lifetimes. | Phases 1-2 | **COMPLETE** 2026-07-14 — WP1-WP9 and exit gate 5/5 recompute. Ratchet iteration 6 closes the remaining Training and launcher-lifecycle holes: every Training verification regenerates a transient candidate from the paused from-boot movie, exact-matches the central save pin at playback index 6904/emulator frame 6905, and records exact-owned cleanup. The generic launcher now recovers only a uniquely proved config owner and rejects all ambiguous owners. The full twelve-artifact pristine matrix was regenerated on the 203-method, 88-dirty-path fork; transition replay measured 16/16 stages with exact PID/sibling cleanup. The 13-row contradiction ledger has zero open rows. Hook accounting remains 5 proven + 9 exact-confidence discharges + 1 degraded recovered-extent row. A07 remains an `external_lead`; F09/D18 remain `partial`. |
| 4 | [[Phase 4 - Solve Every Gameplay and Engine Subsystem]] · **read first:** [[Phase 4 - Closure Conundrum and Recovery Plan]] | Close every baseline subsystem campaign, with berries/seeds as ordinary members. | Phases 1-3 | Phase-3 dependency satisfied by ratchet iteration 6's deterministic Training regeneration and exact-owned launcher lifecycle, iteration 4's current-source/live-artifact join, iteration 10's immutable transition toolchain, iteration 8's byte-stable render replay, and the dirty-input closure guard. Consume its bounded frontiers and explicit residuals; do not promote A07, F09/D18, LEVEL10, callback ABI, actor vertical ownership, or frontend lifecycle unknowns beyond their recorded confidence. |
| 5 | [[Phase 5 - Prove Cross-System and Full-Campaign Integration]] | Validate real interactions, long lifetimes, 100% paths, failure paths, and transitions. | Phases 2-4 | planned |
| 6 | [[Phase 6 - Complete Matching Source Overlays Assets and Toolchain]] | Reconstruct the complete pristine program/data pipeline and prove behavioral identity. | Phases 3-5 | planned |
| 7 | [[Phase 7 - Whole-Game Closure and Modding Foundation]] | Audit the whole-game solve; only afterward establish production MOD interfaces. | Phases 0-6 | planned |

The phases are ordered gates, but compatible work may overlap when it does not depend
on an unproven behavior or interface. Overlap never weakens an exit gate.

## Emulator-platform migration

The proposed move from the custom DuckStation evidence platform to PCSX-Redux is
governed by [[PCSX-Redux Migration Plan - Retire DuckStation as a Required Dependency]].
It is orthogonal to the solve phases: changing emulators does not close, reopen, or
weaken a phase by itself. DuckStation remains required wherever a current gate still
depends on its movies, states, scenarios, or trace capsules until the migration plan's
machine-checked cutover gate passes.

## Post-closure release gate for future MOD builds

A production integration build must pass:

- Reproducible consolidated build and input/hash manifest.
- Safe unit and asset/format tests.
- Hook, cave, emitted-range, forbidden-range, and liveness validation.
- Cold-boot behavioral suite on freshly built media.
- Pristine native-control comparisons.
- GPU iterator, packet, framebuffer, and visual-union checks.
- SPU/audio event and bounded-voice checks.
- Repeated-use, expiration, death, pause, reload, and transition scenarios.
- Supported module-combination matrix.
- Long-running gameplay soak with no guest exception or state growth.
- Operator acceptance on an actual seed or target hardware after automated validation.

Operator testing remains essential, but it is the final acceptance layer rather than
the first mechanism likely to discover a catastrophic regression.

## Immediate whole-game work package

The next solve milestone is complete when:

1. The pristine source artifact is hash-pinned, immutable, and enforced as the sole
   build base; known-good ALLMODS is retained only as read-only historical evidence.
   — **DONE 2026-07-11** (Phase 0 exit gate passed; see
   [[Phase 0 - Stabilize and Establish Identity]]).
2. New feature promotion is frozen and experiments are explicitly separated.
3. [[Whole-Game Mechanics Baseline]] is reconciled against the pristine disc inventory,
   current Canon, and a verified trigger/fixture plan for every row.
4. All 15 stages, Training, known bonus stages, regular enemy families, bosses, manual
   controls, collectibles, plants/powers, hazards, objectives, frontend, audio, and
   lifecycle systems are represented in the Phase 1 campaign matrix.
5. Phase 2 has produced cold-boot pristine oracles by dependency and campaign
   coverage rather than by MOD priority.
   — **QUALIFIED 2026-07-12**: the executable oracle is
   `tools/phase2_compare.py` and remains mutation-proven, but the retroactive
   knowledge audit superseded the A07 no-spin proof; core-action coverage is 19/20.
6. Phase 3 has a machine-readable ownership/semantic map for the shared player, object,
   render, audio, overlay, and lifecycle substrates needed by those campaigns.
   — **COMPLETE 2026-07-14**: WP1-WP9 are recomputed from low-level evidence and
   reproduced from the centrally provisioned clean-checkout surface. Ratchet iteration
   6 adds deterministic Training regeneration and exact-owned launcher recovery to
   iteration 9's exact debugger-source/toolchain guard, iteration 8's byte-stable
   render replay, and iteration 7's complete shared-helper replay;
   107 facet-complete mechanic rows, 63 semantic entries, 8 typed record views covering
   all 12 required families, full Training/campaign load-unload routing, exhaustive
   call/reader-writer/327-asset reports, and a 13-row contradiction ledger with zero
   open rows.
7. The grain-counter crate, new berries, six-tier seeds, and other feature-heavy
   experiments remain out of production integration until Phase 7 permits it.

## Guiding principle

Solve the pristine behavior, ownership, implementation, and campaign breadth before
building on it. The project becomes materially safer when original-game knowledge is
converted into complete semantic models, behavioral oracles, and lifecycle tests—not
when another isolated patch happens to work once.
