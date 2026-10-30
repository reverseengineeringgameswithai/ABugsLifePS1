# Phase 4 Closure — Implement/Verify Acceptance Contract

## Mission

Close **Phase 4 — Solve Every Gameplay and Engine Subsystem** exactly as defined by
the Obsidian roadmap, then have a fresh adversarial verifier reproduce the whole-phase
claim from the committed candidate. This is a subsystem-solving phase for the pristine
PS1 game. It is not permission to resume feature-heavy ALLMODS development or to treat
an existing MOD implementation as original-game authority.

The implementation may proceed campaign by campaign and over many executor iterations.
An iteration is progress, not closure. Phase 4 is closed only when one executor claims
the entire phase is closed and a fresh verifier independently reproduces every
criterion below.

## Authoritative requirements and interpretation order

The binding sources are:

1. `ObsidianVault/Playbooks/Game Solving Roadmap - From Reconstruction to Reliable Modding.md`
2. Its Phase-execution-index link:
   `ObsidianVault/Playbooks/Game Solving Roadmap/Phase 4 - Solve Every Gameplay and Engine Subsystem.md`
3. The inherited `Definition of Finished for a reusable finding` in the roadmap hub.

The hub owns phase sequence, shared closure rules, the operating rule, and the release
gate. The linked Phase 4 note owns Phase 4 purpose, campaign families, child-campaign
requirements, work packages, exit gate, scorecard, and Phase 5 handoff. The hub wins
if prose conflicts. Existing status labels, checkboxes, notes, generated `passes`
fields, model verdicts, and test counts are claims to verify, never authority.

Do not invent a narrower Phase 4. Do not replace the twelve campaign families with a
favorite vertical slice, and do not make berries, seeds, terrain, enemies, or active
MOD demand privileged. Every baseline row and every applicable engine subsystem is in
scope because the roadmap says to solve the game as a whole.

## Repository and operator-safety contract

- Read and obey `AGENTS.md` before acting.
- Preserve operator work. Do not reset, clean, overwrite, or import unrelated dirty or
  untracked files from the operator checkout.
- Begin from the ratchet seed commit. Other branches and operator WIP are leads or
  comparison evidence only; selectively integrate them only after inspecting their
  provenance, reproducing their claims, and satisfying this contract.
- Keep generated discs, retail files, saves, movies, BIOS files, raw captures, tokens,
  credentials, personal media, and copyrighted assets out of Git.
- Store transient captures under `/tmp`. Commit non-copyrighted source, schemas,
  manifests, generators, validators, derived summaries, tests, and notes.
- Never weaken a test, gate, fixture rule, campaign definition, or confidence label to
  obtain a green result.
- Every closure candidate must be committed and the implementation worktree clean.
  No tracked source may silently import or require untracked code.

## Immutable pristine-media authority

The hash-verified pristine retail image is immutable and is the sole authority for
original behavior.

- Never patch ALLMODS, another MOD image, or any derivative. Build each diagnostic
  candidate exactly once from a verified pristine base.
- ALLMODS may be replayed only as historical regression/comparison evidence. It cannot
  establish pristine behavior and is never a patch base.
- Verify `tools/build_baselines.json` and the full staged tree before every build.
- Treat cold-boot movie evidence and save-state evidence as different evidence.
  Disc/code/asset changes require a cold boot and timing-matched input movie. Narrow
  runtime experiments may use centrally pinned saves only after inspecting and
  verifying their media origin; re-arm instrumentation after every load.
- Each DuckStation run must use a fresh absolute config directory, dedicated loopback
  port and ephemeral token, verify the mounted CUE and referenced tracks after
  connecting, record current source/binary/capability identity, and stop only the PID
  owned by that config. Never use the normal user profile or broad process-name kills.
- Discover the current debugger capabilities rather than assuming an older API.
  Prefer declarative scenarios, atomic load/boot recipes, batch execution, unified
  provenance, and trace-equivalence facilities when the running fork reports them.
  Their availability is a method advantage, not evidence by itself.

External inputs may be provisioned from the operator repository only when centrally
declared, media-classified, hash-pinned, and named by the consuming generator. Missing
or mismatched fixtures are failures or exact blockers, never successes. No fixture may
be accepted merely because it exists in the dirty operator checkout.

### Capsule-first evidence hierarchy

Every executor and verifier iteration must validate the central Phase-4 persistent
trace-capsule index and consult the relevant retained capsule before replaying a covered
movie. Use the exact pinned offline reader for frame-boundary registers, RAM, VRAM, SPU
RAM, change points, and declared block-flow evidence. A fresh isolated DuckStation API
run is the last-resort lane: it is allowed only when the capsule lacks the required
domain or temporal precision, exact instruction/DMA/GPU/SPU causality is needed, a
native behavioral control must be executed, or the capsule is missing or invalid. The
experiment must record that escalation reason. Capsules do not prove every-cycle state
and do not close a campaign without the remaining semantic, breadth, lifecycle, Canon,
and executable-guard work. Reusable evidence from a necessary replay must be preserved
or supersede the capsule set under the same external hash-index contract.

A preserved DuckStation executable is not independently runnable evidence unless its
required app-root resources, translations, and companion libraries are retained and
hash-manifested. Live work using the 2026-07-18 trace-capsule toolchain must validate
and launch the complete external runtime bundle, verify the actual running executable
through `debugger.capabilities`, and reject the legacy lone-binary snapshot. Before a
large capture, replay, or clean-checkout copy, preflight `/tmp` quota/free space and use
`/var/tmp` or run-owned scratch when `/tmp` cannot hold the declared work.

The capsule lane is a substantial, machine-scheduled work queue rather than a token
preflight. Before target selection, regenerate
`analysis/phase4_offline_opportunity_queue.json` from the current 107-row registry,
coverage matrix, fixture audit, movie inventory, and capsule index. Every unique row
must carry current source hashes, completion state, family/dependencies, relevant
capsules and domains, exact offline batch queries, offline-answerable questions and
assertions, named unknowns, prior escalation, priority, and one derived classification:
`offline_ready`, `offline_partial`, `live_required`, or `no_capsule`. Guards must reject
stale inputs, duplicate/omitted rows, a row count other than 107, and manually trusted
pass/complete fields.

An iteration normally consumes one coherent subsystem cluster or at least the three
highest-value open `offline_ready` rows. It may not repeatedly deepen one partial row,
refresh a prior phase, or launch DuckStation while higher-ranked offline work remains,
unless retained evidence proves a load-bearing dependency. Repeated cross-movie scans
should use a reproducible external derived index; only its generator, schema, hash
manifest, non-copyrighted summaries, and guards belong in Git.

Every live escalation must be declared first in generated machine-readable
`analysis/phase4_live_escalations.json`: target row and hypothesis, all relevant
capsules and exact offline commands/windows/domains already queried, answers obtained,
the precise unavailable information, the proposed live experiment and native control,
expected new evidence, and the priority/load-bearing reason for not taking another
offline batch. Generic “needs causality/control” text is not sufficient. Each iteration
decision must report queue counts, selected rows, offline results, and any escalation ID.

## Binding Phase 4 purpose

Run evidence-backed subsystem campaigns until every row in the machine-readable twin
of `Whole-Game Mechanics Baseline` satisfies the roadmap's strict Definition of
Finished. A campaign must solve original behavior, state, control flow, assets,
lifecycle, capacity, stage breadth, and safe future consumption—not merely locate an
address or reproduce one successful scene.

Berries and seeds are ordinary campaign members. They do not waive player, physics,
rendering, collectible, object, enemy, boss, frontend, audio, or loading coverage.

## Binding campaign-family coverage

Phase 4 must cover all twelve roadmap families and every baseline row assigned to
them. A machine-readable coverage/scorecard layer must derive the assignment and
status from authoritative evidence and fail on an omitted or duplicated-without-owner
row.

1. **Input and player actions:** run, slow walk, turn, jump, kick, abdomen bounce,
   slide, spin, berry throw, seed manipulation, swinging, and manual camera input.
2. **Player lifecycle:** health, damage, invulnerability, shields, powers, death,
   checkpoints, lives, game over, and continue.
3. **Movement/world physics:** gravity, slopes, ledges, floors, walls, hazards, movers,
   air states, collision response, and camera collision.
4. **Rendering/camera/animation:** world and actor submission, ordering tables, double
   buffering, materials, effects, model/animation state, and normal/special cameras.
5. **Seeds/plants/traversal powers:** every color/tier, carry/mount/plant/uproot,
   mushroom, propeller, dandelion, cannon, leaf platforms, temporary powers, shooters,
   mines, and combinations.
6. **Collectibles/equipment/rewards:** grain, FLIK letters, health leaves, berry
   pickups, seed tokens, telescopes, grain harvester, success tokens, medals, unlocks,
   and bonus entries.
7. **Objects/events/hazards:** contacts, pickups, props, gates, switches, movers,
   dynamic geometry, scripted actors, event VM, objectives, and environmental hazards.
8. **Enemies/combat:** every regular family and variant, AI, attacks, immunities,
   damage, death, drops, respawn, permanent kills, and quotas.
9. **Bosses/special objectives:** Thumper, Bird, Thud, Molt, Hopper, flight/chase,
   rolling arena, bird assembly, companion rescue, and finale mechanics.
10. **HUD/frontend/persistence:** status, pause, results, menus, options, remapping,
    save/load, continue, game over, movie viewer, and unlock persistence.
11. **Audio/cinematics:** SFX, voices, XA/music selection, FMV playback, skip/error
    paths, ownership, pause, stop, and transition behavior.
12. **Loading/overlays/resources:** scene flow, level/MEMORY/FMV overlays, streaming,
    loader fixups, asset residency, unload, and failure paths.

If the baseline or machine registry contains a mechanic/system not literally named in
the examples above, it still belongs to the closest campaign family and cannot be
silently omitted.

## Child-campaign acceptance

Create `Game Solving Campaign - <Subsystem>.md` only when work on that campaign
actually begins. Do not pre-create empty notes. Every completed campaign must contain
and machine-link all of the following:

1. explicit scope, non-scope, owning campaign family, and Phase 1 row IDs;
2. pristine oracle fixtures and original behavior, with hashes and triggers;
3. complete semantic frontier: functions, dispatch, assets, overlays, typed state,
   readers/writers, and still-unknown boundaries;
4. initialization, lifecycle, capacity, allocation/reuse, reset, retirement, unload,
   scene transition, death/respawn, and persistence behavior where applicable;
5. native positive and negative controls measuring outcomes rather than labels;
6. evidence across every applicable stage, variant, lifecycle, and exceptional path;
7. cross-system dependencies and the exact contracts those consumers may rely on;
8. matching-C, semantic-C, ASM, schema, registry, and decompilation status without
   presenting documentation-grade code as matching source;
9. confirmed findings, disproven hypotheses, bounded residuals, next experiments, and
   superseded claims;
10. an executable campaign gate and explicit exit decision derived from low-level
    evidence.

A single address, fixture, level, enemy instance, successful path, or MOD demonstration
cannot close a campaign. A bounded unknown may remain only to the extent permitted by
the Phase 4 exit wording: it must be explicit, evidence-backed, have a named next
experiment, and not invalidate the campaign conclusion or its future-MOD consumption
contract. Unsupported absence claims do not count as reviewed proof that a mechanic is
not present.

## Binding Phase 4 work packages

The candidate must implement and mechanically evidence all six work packages:

1. prioritize campaigns by dependency centrality and pristine coverage gaps, not
   active MOD demand;
2. solve core player/input/lifecycle and shared object/render/audio substrates first;
3. run collectible, plant, enemy, and objective campaigns across every applicable
   level rather than only LEVEL01;
4. complete each regular enemy family and boss individually;
5. complete special-stage mechanics and exceptional overlay paths;
6. update `Whole-Game Mechanics Baseline` only through evidence-backed status changes.

The machine scorecard must reject unchecked, absent, self-certified, or prose-only work
packages. Progress may be partial for many iterations, but closure requires the full
set.

## Exact Phase 4 exit gate

The final Phase 4 gate must recompute these four predicates from retained low-level
evidence and exit nonzero when any predicate is false:

1. **Complete campaign coverage:** every baseline mechanic and engine system has a
   completed campaign or reviewed evidence that it is not present in the pristine PS1
   version.
2. **Subsystem Definition of Done:** every completed campaign satisfies the full
   child-campaign contract and inherited Definition of Finished.
3. **Breadth and generalization:** campaign conclusions generalize across every
   applicable stage, variant, lifecycle, and exceptional path.
4. **Bounded intersections:** no unresolved field, dispatch, asset, overlay, record,
   callback, state owner, or lifecycle intersects a subsystem's behavior without being
   explicitly bounded and represented in the authoritative machine layers.

The gate must enumerate all baseline rows from the authoritative registry at runtime;
it may not rely on a hand-copied count. It must inspect underlying evidence predicates,
not trust campaign `passes`, `complete`, `solved`, or `gate_met` booleans. Deliberately
corrupting or removing a decisive low-level input must turn the relevant campaign and
whole-phase gate red.

## Inherited Definition of Finished for every finding

Every confirmed Phase 4 finding must satisfy all eight roadmap requirements:

1. **Ground truth and provenance:** hash-verified pristine media; exact executable,
   overlay, and asset identity; fixture hashes; trigger; frame/cycle; observation;
   observation/inference/causal-confirmation separation.
2. **Authoritative machine representation:** byte-exact ASM/symbols for code identity;
   matching C when achieved; typed records/state for fields and ownership; mechanics,
   dispatch, asset, overlay, hook, and lifecycle registries as appropriate. Semantic or
   documentation-grade C must be labelled honestly.
3. **Reproducible evidence:** the smallest deterministic scenario, movie, state, trace
   summary, or static procedure; exact commands/methods and hashes; decisive retained
   evidence with a regeneration path.
4. **Executable guard:** behavioral assertion, unit test, validator, freshness check,
   or explicit automation blocker plus reopening experiment. Summaries must be derived
   from evidence rather than accepting high-level success flags.
5. **Knowledge placement and links:** original facts/provenance in `Canon`, runtime
   experiments and failed hypotheses in `Experiments`, and MOD-private state/hooks/
   intended deltas in `Mods`, with reciprocal links to sources, evidence, tests,
   roadmap rows, residuals, and superseded claims.
6. **Future-MOD consumption contract:** owner, readers/writers, valid domains,
   initialization/reset/retirement, continuation ABI or asset constraints, downstream
   consumers, capacity, stage/overlay residency, and known unsafe assumptions.
7. **Clean-checkout durability:** all non-copyrighted dependencies committed; no silent
   untracked imports; every external fixture centrally pinned, media-classified,
   referenced by its generator, and declared for preservation.
8. **Confidence/residual/supersession:** evidence-backed status vocabulary; unresolved
   variants and next experiments; corrected claims propagated to machine consumers and
   linked as superseded.

Conversation-only conclusions, prose-only addresses, dirty-worktree dependencies,
unregenerable summaries, and fixtures pinned only inside one artifact remain partial.

## Evidence, fixture, and generator closure

Build a machine-readable Phase 4 inventory covering every campaign, baseline row,
finding, schema, generator, retained artifact, fixture, test, Canon/Experiment/Mods
note, source/decompilation surface, and downstream consumer. It must detect:

- missing or orphan campaigns and baseline rows;
- generators/artifacts absent from the declared inventory;
- stale derived artifacts or source-helper mismatches;
- individually embedded fixture hashes absent from the central fixture audit;
- untracked imports and provisioned sources absent from clean checkout;
- live artifacts without exact current debugger source/binary/capability provenance;
- saves whose media origin was not inspected before load;
- incomplete logs, page truncation, saturated watches, or unstable replay;
- claims stronger than their retained evidence;
- contradictions between ASM/C, runtime, schemas, registries, tests, and Obsidian;
- unresolved or superseded Phase 3 frontiers promoted beyond their recorded
  confidence.
- an offline opportunity queue that omits/duplicates any of the 107 rows, carries stale
  registry/capsule/fixture hashes, trusts authored completion flags, or permits a live
  escalation without a complete pre-run audit;
- token capsule preflights that skip a higher-ranked subsystem-sized offline batch, or
  cross-movie indexes that are neither externally preserved nor reproducible.

Static, local-media, and live generators must be classified. Deterministic outputs
must reproduce byte-identically; artifacts with justified volatile metadata must have
a canonical semantic comparison that excludes only enumerated volatile fields.

## Phase 3 handoff constraints

Phase 4 inherits Phase 3's verified architecture but must preserve its bounded
frontiers. In particular, do not silently promote A07, F09/D18, LEVEL10, callback ABI,
actor vertical ownership, or frontend lifecycle claims beyond the current machine
evidence. If Phase 4 needs a stronger conclusion, reproduce the missing evidence and
update every authoritative consumer and supersession link.

Preparatory work on other branches—including Thud/rolling-arena investigation or
terrain-authoring experiments—is not automatically part of Phase 4. It may be consumed
only after provenance, pristine authority, machine banking, tests, clean-checkout
durability, and campaign relevance are independently verified.

## Obsidian closure and handoff

Update authoritative machine layers first and Obsidian last. Before claiming closure:

- create and maintain only actual child-campaign notes required by the roadmap;
- place original facts in `ObsidianVault/Canon`, runtime experiments and failed
  hypotheses in `ObsidianVault/Experiments`, and MOD-private contracts in
  `ObsidianVault/Mods`;
- update `Whole-Game Mechanics Baseline` and its machine-readable twin from evidence;
- update the Phase 4 campaign scorecard, work-package checkboxes, exact validation,
  residuals, and Phase 5 handoff;
- update the roadmap hub's Phase 4 status only after the whole-phase gate and
  clean-checkout proof pass;
- preserve reciprocal links among the hub, Phase 4 note, child campaigns, Canon,
  Experiments, Mods, evidence, generators, tests, and superseded claims;
- run the vault validator and reject dead links, misplaced knowledge, stale generated
  indexes, or prose stronger than machine evidence.

The verifier must inspect the Obsidian vault inside the committed candidate. Notes in
the operator checkout or a local-state directory do not satisfy closure.

## Validation and falsification requirements

At minimum, the final candidate and fresh verifier must:

1. verify pristine build/staging identity and protected output rules;
2. regenerate the Phase 4 campaign inventory, scorecard, knowledge audit, fixture
   audit, coverage matrix, and whole-phase gate;
3. run every campaign's static, behavioral, freshness, and fixture guards;
4. run the safe suite, relevant local-media tests, and all required live pristine
   scenarios;
5. preserve Phase 1–3 oracle and architecture guards with no unexplained downgrade;
6. validate hook/cave and diagnostic images against exact pristine-derived builds;
7. validate Obsidian links, placement, evidence policy, indexes, and schemas;
8. prove decisive generators reproduce byte-identically or semantically identically
   under their declared rule;
9. falsify the gates by corrupting representative low-level evidence in disposable
   copies and observing a nonzero result;
10. reproduce the candidate from a fresh clone/archive plus only the declared external
    fixture set, with all required source files tracked and a clean final status.

A skipped test, absent fixture, unavailable live scenario, stale artifact, or dirty
clean-checkout proof must be reported honestly. It cannot be transformed into success
by changing the summary.

## Required implementation order

1. Inventory all 107 baseline rows, twelve campaign families, existing knowledge,
   Phase 3 handoff residuals, fixtures, and current source/decompilation status.
2. Establish a machine-readable Phase 4 campaign registry, coverage matrix, evidence
   inventory, and falsifiable gate before declaring substantive closure.
3. Prioritize campaigns by dependency centrality: core input/player/lifecycle and
   shared object/render/audio substrates first.
4. For each campaign, repair authoritative machine layers and generators before notes;
   then run static/live evidence, guards, stage/lifecycle breadth, and knowledge audit.
5. Run collectible, plant, enemy, boss, objective, special-stage, frontend, audio, and
   loading campaigns across every applicable stage and exceptional path.
6. Reconcile contradictions and regenerate downstream Phase 1–3 consumers whenever a
   Phase 4 finding corrects their assumptions.
7. Update Canon/Experiments/Mods, child notes, Phase 4 note, and roadmap hub last.
8. Commit all scoped non-copyrighted work; leave the implementation worktree clean.
9. Reproduce from a clean checkout plus only centrally declared external fixtures.
10. Have a fresh adversarial verifier rerun the whole contract. Executor confidence is
    never sufficient.

## Decision rules

Return `open_autonomous` while any safe Phase 4 work remains. Include exact gaps and
commands/evidence in the decision so the next executor continues from committed state.

Return `blocked_external` only when Phase 4 genuinely requires a specific recording,
save, movie, asset, or human decision that cannot be produced or replaced by a safe
autonomous pristine experiment. Name the exact input and why alternatives fail. A
fresh verifier must confirm the blocker.

Return `closed` only when:

- every baseline mechanic/system is covered by a completed campaign or reviewed
  pristine-absence proof;
- all completed campaigns satisfy their full subsystem and reusable-finding contracts;
- all four Phase 4 exit predicates are mechanically true from low-level evidence;
- the twelve-family scorecard, machine registry, Obsidian vault, and repository agree;
- all required static, safe, local-media, live, freshness, fixture, and clean-checkout
  validation passes;
- `gaps` is empty, `required_input` is empty, and the tested candidate commit equals
  clean worktree `HEAD`;
- a fresh verifier independently reproduces the whole-phase result.

Anything less is Phase 4 progress, not Phase 4 closure.
